"""
Views for the ``partners`` app.

This module contains every view for managing Community Partner Organizations
(CPOs) and their related sub-entities: contacts, needs, socioeconomic
profiles, and past interventions.

Architecture
------------
The partner-creation flow uses a **session-based multi-step wizard** (4
steps) rather than Django's built-in ``FormWizard``.  This was chosen so
that:

* Users can save a **draft** at any step and resume later.
* Steps 3 (Needs) and 4 (Past Interventions) are *optional* — they are
  skipped unless the user ticked the corresponding checkbox in Step 1.
* All wizard state lives in ``request.session`` under a single key, making
  it easy to clear in one operation.

Wizard step overview::

    Step 1 — Partner details + contacts
        Collects core fields (name, vision, mission, …) and one-or-more
        contact persons via an inline formset.  Two boolean flags
        (``include_needs``, ``include_past_interventions``) decide whether
        steps 3 and 4 are shown.

    Step 2 — Socioeconomic profile
        Collects demographic / infrastructure data via a single-row inline
        formset.

    Step 3 — Needs repository  *(conditional)*
        Collects one-or-more needs.  Skipped automatically when
        ``include_needs`` is False.

    Step 4 — Past interventions  *(conditional)*
        Collects one-or-more past interventions.  Skipped automatically when
        ``include_past_interventions`` is False.

        On valid submission, **all** collected data is written to the
        database inside a single ``transaction.atomic()`` block.
"""

import os
from datetime import date, datetime
from io import BytesIO, StringIO
from pathlib import Path
from tempfile import NamedTemporaryFile

from django.contrib.auth.decorators import login_required
from django.core.management import call_command
from django.core.paginator import Paginator
from django.db import connection, models, transaction
from django.db.models import Q
from django.http import (FileResponse, Http404, HttpResponse,
                         HttpResponseRedirect, QueryDict)
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (HRFlowable, PageBreak, Paragraph,
                                SimpleDocTemplate, Spacer, Table, TableStyle)

from .forms import (ContactFormSet, NeedForm, NeedFormSet,
                    PartnerCreateStepOneForm, PartnerForm,
                    PastInterventionForm, PastInterventionFormSet,
                    SocioEconomicProfileFormSet)
from .models import Needs, Partner, PastInterventions

# ── Constants ─────────────────────────────────────────────────────

CREATE_STEP_SESSION_KEY = "partner_create_wizard"

# Number of partners shown per page in the list view.
PAGE_SIZE = 20


# ── Session / Wizard Helpers ──────────────────────────────────────


def _build_step_one_initial_from_session(data):
    """Build initial form data for Step 1 from saved wizard state.

    Extracts the partner field values and the boolean flags that control
    whether Steps 3 (Needs) and 4 (Past Interventions) are shown.
    """
    initial = data.get("partner", {}).copy()
    initial["include_needs"] = data.get("include_needs", False)
    initial["include_past_interventions"] = data.get(
        "include_past_interventions", False
    )
    return initial


def _clear_create_wizard(request):
    """Remove all wizard data from the session."""
    if CREATE_STEP_SESSION_KEY in request.session:
        del request.session[CREATE_STEP_SESSION_KEY]


def _serialize_post_data(post_data):
    """Convert a ``QueryDict`` into a plain ``dict`` of lists.

    Django's session backend cannot serialize ``QueryDict`` objects
    directly, so we extract the underlying list-of-values mapping.
    Used when saving a draft of the current step.
    """
    return {key: values for key, values in post_data.lists()}


def _deserialize_post_data(serialized_data):
    """Reconstruct a mutable ``QueryDict`` from serialized session data."""
    query_dict = QueryDict("", mutable=True)
    for key, values in serialized_data.items():
        query_dict.setlist(key, values)
    return query_dict


def _make_session_safe(value):
    """Recursively convert a value into a JSON-serializable form.

    Handles ``date``/``datetime`` → ISO string, ``Model`` → pk,
    and recurses into ``dict`` / ``list``.  Required because Django's
    session serializer only supports basic JSON types.
    """
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, models.Model):
        return value.pk
    if isinstance(value, dict):
        return {key: _make_session_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_make_session_safe(item) for item in value]
    return value


def _redirect_create(step=None, reset=False):
    """Return a redirect response to the partner-create wizard.

    Args:
        step: Wizard step number (1-4).  ``None`` means step 1.
        reset: If ``True``, appends ``reset=1`` to trigger session
               cleanup on the next request.
    """
    base_url = reverse("partner-create")
    query = []
    if step is not None:
        query.append(f"step={step}")
    if reset:
        query.append("reset=1")
    if query:
        return HttpResponseRedirect(f"{base_url}?{'&'.join(query)}")
    return HttpResponseRedirect(base_url)


# ── Partner List ──────────────────────────────────────────────────


def partner_list(request):
    """Display a paginated, filterable, searchable list of active partners.

    Search behaviour
        * **PostgreSQL** — uses ``SearchVector`` + ``SearchRank`` for
          relevance-ranked full-text search.
        * **SQLite** — falls back to case-insensitive ``icontains``
          lookups across text fields.

    Supported filters (all optional, via GET parameters):
        ``q``, ``updated_by``, ``has_moa_link``,
        ``date_established_from/to``, ``moa_start_from/to``,
        ``moa_end_from/to``, ``updated_from/to``, ``sort``.

    Template:
        ``partners/partner_list.html``
    """
    # ── Base queryset: only active (non-archived) partners ──
    partners = (
        Partner.objects.select_related("updated_by")
        .prefetch_related(
            "contacts",
            "needs",
            "past_interventions",
            "socioeconomic_profiles",
        )
        .filter(is_archived=False)
        .all()
    )

    # ── Read filter parameters from GET ──
    q = request.GET.get("q", "").strip()
    updated_by = request.GET.get("updated_by", "").strip()
    has_moa_link = request.GET.get("has_moa_link", "").strip()

    date_established_from = request.GET.get("date_established_from", "").strip()
    date_established_to = request.GET.get("date_established_to", "").strip()
    moa_start_from = request.GET.get("moa_start_from", "").strip()
    moa_start_to = request.GET.get("moa_start_to", "").strip()
    moa_end_from = request.GET.get("moa_end_from", "").strip()
    moa_end_to = request.GET.get("moa_end_to", "").strip()
    updated_from = request.GET.get("updated_from", "").strip()
    updated_to = request.GET.get("updated_to", "").strip()
    sort = request.GET.get("sort", "updated_desc").strip()

    # ── Free-text search ──
    if q:
        if connection.vendor == "postgresql":
            from django.contrib.postgres.search import (SearchQuery,
                                                        SearchRank,
                                                        SearchVector)

            vector = SearchVector(
                "name",
                "vision",
                "mission",
                "goals",
                "description",
                "core_values",
                "sec_registration",
                "bir_registration",
                "tin",
            )
            query = SearchQuery(q)
            partners = (
                partners.annotate(search=vector, rank=SearchRank(vector, query))
                .filter(Q(search=query) | Q(name__icontains=q))
                .order_by("-rank", "-updated_at")
            )
        else:
            # SQLite fallback: simple icontains across the same fields
            partners = partners.filter(
                Q(name__icontains=q)
                | Q(vision__icontains=q)
                | Q(mission__icontains=q)
                | Q(goals__icontains=q)
                | Q(description__icontains=q)
                | Q(core_values__icontains=q)
                | Q(sec_registration__icontains=q)
                | Q(bir_registration__icontains=q)
                | Q(tin__icontains=q)
            ).order_by("-updated_at")

    # ── Individual field filters ──
    if updated_by.isdigit():
        partners = partners.filter(updated_by_id=int(updated_by))

    if has_moa_link == "true":
        partners = partners.exclude(moa_link="")
    elif has_moa_link == "false":
        partners = partners.filter(moa_link="")

    if date_established_from:
        partners = partners.filter(date_established__gte=date_established_from)
    if date_established_to:
        partners = partners.filter(date_established__lte=date_established_to)
    if moa_start_from:
        partners = partners.filter(moa_start_date__gte=moa_start_from)
    if moa_start_to:
        partners = partners.filter(moa_start_date__lte=moa_start_to)
    if moa_end_from:
        partners = partners.filter(moa_end_date__gte=moa_end_from)
    if moa_end_to:
        partners = partners.filter(moa_end_date__lte=moa_end_to)
    if updated_from:
        partners = partners.filter(updated_at__date__gte=updated_from)
    if updated_to:
        partners = partners.filter(updated_at__date__lte=updated_to)

    # ── Sorting (only applied when there is no search query) ──
    if not q:
        sort_map = {
            "name_asc": ["name", "-updated_at"],
            "name_desc": ["-name", "-updated_at"],
            "updated_desc": ["-updated_at"],
            "updated_asc": ["updated_at"],
            "established_desc": ["-date_established"],
            "established_asc": ["date_established"],
        }
        partners = partners.order_by(*sort_map.get(sort, sort_map["updated_desc"]))

    # ── Pagination ──
    paginator = Paginator(partners, PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get("page"))

    # Keep a copy of the current filters (minus "page") so pagination
    # links can preserve the active filter state.
    filter_querydict = request.GET.copy()
    filter_querydict.pop("page", None)

    def _build_filter_url_without(*keys):
        """Return the partner-list URL with the given filter keys removed.

        Used by the template to render "clear this filter" links.
        """
        querydict = filter_querydict.copy()
        for key in keys:
            querydict.pop(key, None)
        encoded = querydict.urlencode()
        if encoded:
            return f"{reverse('partner-list')}?{encoded}"
        return reverse("partner-list")

    # Distinct list of users who have updated at least one partner,
    # for the "updated by" filter dropdown.
    users = (
        Partner.objects.exclude(updated_by=None)
        .values("updated_by_id", "updated_by__name", "updated_by__username")
        .distinct()
        .order_by("updated_by__name")
    )

    context = {
        "partners": page_obj,
        "page_obj": page_obj,
        "updated_by_users": users,
        "filters": {
            "q": q,
            "updated_by": updated_by,
            "has_moa_link": has_moa_link,
            "date_established_from": date_established_from,
            "date_established_to": date_established_to,
            "moa_start_from": moa_start_from,
            "moa_start_to": moa_start_to,
            "moa_end_from": moa_end_from,
            "moa_end_to": moa_end_to,
            "updated_from": updated_from,
            "updated_to": updated_to,
            "sort": sort,
        },
        "filter_query": filter_querydict.urlencode(),
        "total_count": paginator.count,
        "clear_filter_urls": {
            "q": _build_filter_url_without("q"),
            "updated_by": _build_filter_url_without("updated_by"),
            "has_moa_link": _build_filter_url_without("has_moa_link"),
            "date_established_from": _build_filter_url_without("date_established_from"),
            "date_established_to": _build_filter_url_without("date_established_to"),
            "moa_start_from": _build_filter_url_without("moa_start_from"),
            "moa_start_to": _build_filter_url_without("moa_start_to"),
            "moa_end_from": _build_filter_url_without("moa_end_from"),
            "moa_end_to": _build_filter_url_without("moa_end_to"),
            "updated_from": _build_filter_url_without("updated_from"),
            "updated_to": _build_filter_url_without("updated_to"),
            "sort": _build_filter_url_without("sort"),
        },
    }
    return render(request, "partners/partner_list.html", context)


# ── Partner Bulk Import ──────────────────────────────────────────


@login_required
def partner_bulk_import(request):
    """Upload a CSV file and import partners in bulk.

    Delegates the actual parsing to the ``import_partner_csv`` management
    command.  Supports a **dry-run** mode (``--dry-run``) that validates
    the file without writing to the database.

    Template:
        ``partners/partner_bulk_import.html``
    """
    context = {
        "command_output": "",
        "command_error": "",
        "dry_run": True,
    }

    if request.method == "POST":
        uploaded_csv = request.FILES.get("csv_file")
        dry_run = request.POST.get("dry_run") == "on"
        context["dry_run"] = dry_run

        if not uploaded_csv:
            context["command_error"] = "Please select a CSV file to import."
            return render(request, "partners/partner_bulk_import.html", context)

        if not uploaded_csv.name.lower().endswith(".csv"):
            context["command_error"] = "Only .csv files are supported."
            return render(request, "partners/partner_bulk_import.html", context)

        # Write the uploaded file to a temporary path so the management
        # command can read it from disk.
        temp_path = ""
        try:
            with NamedTemporaryFile(suffix=".csv", delete=False) as temp_file:
                for chunk in uploaded_csv.chunks():
                    temp_file.write(chunk)
                temp_path = temp_file.name

            stdout = StringIO()
            stderr = StringIO()

            call_command_kwargs = {
                "stdout": stdout,
                "stderr": stderr,
            }
            if request.user.is_authenticated:
                call_command_kwargs["user"] = request.user.username

            if dry_run:
                call_command(
                    "import_partner_csv",
                    temp_path,
                    "--dry-run",
                    **call_command_kwargs,
                )
            else:
                call_command(
                    "import_partner_csv",
                    temp_path,
                    **call_command_kwargs,
                )

            context["command_output"] = stdout.getvalue()
            context["command_error"] = stderr.getvalue()
        except Exception as exc:
            context["command_error"] = str(exc)
        finally:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)

    return render(request, "partners/partner_bulk_import.html", context)


@login_required
def partner_bulk_import_template_download(request):
    """Download the blank CSV template used for bulk imports.

    Returns:
        ``FileResponse`` with ``partner_import_template.csv``.
    """
    template_path = Path(__file__).resolve().parents[1] / "template.csv"
    if not template_path.exists():
        raise Http404("Template CSV file not found.")

    return FileResponse(
        open(template_path, "rb"),
        as_attachment=True,
        filename="partner_import_template.csv",
        content_type="text/csv",
    )


# ── Partner Detail ───────────────────────────────────────────────


def partner_detail(request, pk):
    """Display the full profile of a single active partner.

    Eagerly loads related contacts, needs, socioeconomic profiles,
    and past interventions to avoid N+1 queries.

    Template:
        ``partners/partner_detail.html``
    """
    partner = get_object_or_404(
        Partner.objects.prefetch_related(
            "contacts",
            "needs",
            "socioeconomic_profiles",
            "past_interventions",
        ),
        pk=pk,
        is_archived=False,
    )
    return render(
        request,
        "partners/partner_detail.html",
        {
            "partner": partner,
            "contacts": partner.contacts.all(),
            "needs": partner.needs.filter(is_archived=False),
            "socioeconomic_profiles": partner.socioeconomic_profiles.all(),
            "past_interventions": partner.past_interventions.filter(is_archived=False),
        },
    )


# ── Partner PDF Export ───────────────────────────────────────────


def _get_pdf_styles():
    """Return a dict of reportlab ``ParagraphStyle`` objects used in exports.

    Styles are derived from the built-in stylesheet and customised for:
    - Cover page (header, title, partner name, subtitle)
    - Section headings
    - Table label / value cells
    """
    styles = getSampleStyleSheet()

    return {
        "cover_header": ParagraphStyle(
            "CoverHeader",
            parent=styles["Normal"],
            fontName="Times-Roman",
            fontSize=13,
            alignment=1,
            leading=16,
        ),
        "cover_title": ParagraphStyle(
            "CoverTitle",
            parent=styles["Title"],
            fontName="Times-Bold",
            fontSize=28,
            alignment=1,
            spaceAfter=20,
        ),
        "cover_partner": ParagraphStyle(
            "CoverPartner",
            parent=styles["Heading1"],
            fontName="Times-Bold",
            fontSize=24,
            alignment=1,
            leading=29,
        ),
        "cover_sub": ParagraphStyle(
            "CoverSub",
            parent=styles["Normal"],
            fontName="Times-Bold",
            fontSize=14,
            alignment=1,
            leading=18,
        ),
        "section_heading": ParagraphStyle(
            "SectionHeading",
            parent=styles["Heading1"],
            fontName="Times-Bold",
            fontSize=20,
            spaceAfter=8,
        ),
        "table_label": ParagraphStyle(
            "TableLabel",
            parent=styles["Normal"],
            fontName="Times-Bold",
            fontSize=11,
            leading=14,
        ),
        "table_value": ParagraphStyle(
            "TableValue",
            parent=styles["Normal"],
            fontSize=10,
            leading=13,
        ),
    }


# Common table style used for both description and profile tables.
_TABLE_STYLE = TableStyle(
    [
        ("GRID", (0, 0), (-1, -1), 1.2, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]
)


def _text(value):
    """Format a value for use inside a reportlab ``Paragraph``.

    Returns ``"-"`` for empty / falsy values.  Otherwise, converts to a
    string, strips whitespace, and replaces newlines with ``<br/>`` tags
    (reportlab's Paragraph supports basic HTML markup).
    """
    if not value:
        return "-"
    return str(value).strip().replace("\n", "<br/>")


@login_required
def partner_export_pdf(request, pk):
    """Generate and download a PDF profile for a single partner.

    The PDF has two parts:
        **Part 1 — Description of the CPO**
            A two-column table covering vision, mission, goals, needs,
            contacts, registration info, etc.

        **Part 2 — Socioeconomic Profile and Interventions** *(if data exists)*
            A two-column socioeconomic profile table, followed by a
            five-column past-interventions table.

    Returns:
        ``HttpResponse`` with ``Content-Disposition: attachment``.
    """
    partner = get_object_or_404(
        Partner.objects.prefetch_related(
            "contacts",
            "needs",
            "socioeconomic_profiles",
            "past_interventions",
        ),
        pk=pk,
        is_archived=False,
    )

    # ── Set up the PDF document ──
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=f"Partner Export - {partner.name}",
    )

    pdf_styles = _get_pdf_styles()

    # ── Prefetch related objects ──
    contacts = list(partner.contacts.all())
    needs = list(partner.needs.filter(is_archived=False))
    profiles = list(partner.socioeconomic_profiles.all())
    interventions = list(partner.past_interventions.filter(is_archived=False))

    head_contact = contacts[0] if contacts else None

    # ── Build HTML fragments for multi-value cells ──

    needs_html = "<br/><br/>".join(
        [
            (
                f"• <b>{_text(need.name)}</b>: {_text(need.description)}"
                f"<br/>Objectives: {_text(need.objectives)}"
                f"<br/>Expected Outcomes: {_text(need.expected_outcomes)}"
            )
            for need in needs
        ]
    )
    if not needs_html:
        needs_html = "-"

    contacts_html = "<br/><br/>".join(
        [
            (
                f"<b>{_text(contact.name)}</b><br/>"
                f"{_text(contact.position)}"
                f"{_text(contact.contact_number)}<br/>"
                f"{_text(contact.email)}"
            )
            for contact in contacts
        ]
    )
    if not contacts_html:
        contacts_html = "-"

    # Social references: MOA link + output links from interventions
    social_refs = []
    if partner.moa_link:
        social_refs.append(f"MOA Link: {_text(partner.moa_link)}")
    for intervention in interventions:
        if intervention.output_link:
            social_refs.append(
                f"Output ({_text(intervention.name)}): "
                f"{_text(intervention.output_link)}"
            )
    social_refs_html = "<br/>".join(social_refs) if social_refs else "-"

    # ── Part 1: Description of the CPO ──

    description_rows = [
        ["Vision", _text(partner.vision)],
        ["Mission", _text(partner.mission)],
        ["Goals and Objectives", _text(partner.goals)],
        ["Needs Repository and Services Offered", needs_html],
        ["Core Values", _text(partner.core_values)],
        [
            "Head Of Organization and Designation<br/><i>(For MOA Purposes)</i>",
            (
                f"<b>{_text(head_contact.name if head_contact else '-')}</b><br/>"
                f"{_text(head_contact.position if head_contact else '-')}<br/>"
                f"{_text(head_contact.email if head_contact else '-')}"
            ),
        ],
        ["Area Coordinators and Contact Details", contacts_html],
        ["Short Description and Background of CPO", _text(partner.description)],
        ["Social Media Platforms/References", social_refs_html],
        [
            "Date Established<br/>SEC Registration<br/><br/>"
            "BIR Certificate of Registration<br/>TIN",
            (
                f"{_text(partner.date_established)}<br/>"
                f"{_text(partner.sec_registration)}"
                f"<br/><br/>{_text(partner.bir_registration)}<br/>"
                f"{_text(partner.tin)}"
            ),
        ],
    ]

    table_rows = [
        [
            Paragraph(label, pdf_styles["table_label"]),
            Paragraph(value, pdf_styles["table_value"]),
        ]
        for label, value in description_rows
    ]

    # ── Build the PDF story (cover page + Part 1) ──

    story = []

    # Cover page
    story.append(Spacer(1, 28 * mm))
    story.append(
        Paragraph(
            "OFFICE FOR SOCIAL CONCERN AND INVOLVEMENT",
            pdf_styles["cover_header"],
        )
    )
    story.append(Paragraph("ATENEO DE MANILA UNIVERSITY", pdf_styles["cover_header"]))
    story.append(Spacer(1, 3 * mm))
    story.append(
        HRFlowable(width="72%", thickness=1, color=colors.black, spaceAfter=22)
    )
    story.append(
        Paragraph(
            "Community Partner Organization Profile",
            pdf_styles["cover_title"],
        )
    )
    story.append(Spacer(1, 50 * mm))
    story.append(Paragraph(partner.name.upper(), pdf_styles["cover_partner"]))
    if head_contact and head_contact.position:
        story.append(Spacer(1, 3 * mm))
        story.append(Paragraph(_text(head_contact.position), pdf_styles["cover_sub"]))
    story.append(PageBreak())

    # Part 1 table
    story.append(
        Paragraph("PART 1: DESCRIPTION OF THE CPO", pdf_styles["section_heading"])
    )
    description_table = Table(table_rows, colWidths=[62 * mm, 118 * mm])
    description_table.setStyle(_TABLE_STYLE)
    story.append(description_table)

    # ── Part 2: Socioeconomic Profile and Interventions ──

    if profiles or interventions:
        story.append(PageBreak())
        story.append(
            Paragraph(
                "PART 2: SOCIOECONOMIC PROFILE AND INTERVENTIONS",
                pdf_styles["section_heading"],
            )
        )

    # Socioeconomic profile table
    if profiles:
        profile_field_labels = [
            ("population_size", "Population Size"),
            ("population_breakdown", "Population Breakdown"),
            ("livelihoods", "Livelihoods"),
            ("health_profile", "Health Profile"),
            ("sociocultural_profile", "Sociocultural Profile"),
            ("political_profile", "Political Profile"),
            ("partner_networks", "Partner Networks"),
            ("resources_available", "Resources Available"),
            ("vulnerabilities", "Vulnerabilities"),
            ("housing", "Housing"),
            ("transportation", "Transportation"),
            ("electricity", "Electricity"),
            ("water", "Water"),
            ("wet_market", "Wet Market"),
            ("health_facilities", "Health Facilities"),
            ("education_facility", "Education Facility"),
            ("telecommunication", "Telecommunication"),
            ("others", "Others"),
        ]

        profile_rows = []
        for profile in profiles:
            profile_rows.extend(
                [label, _text(getattr(profile, attr))]
                for attr, label in profile_field_labels
            )

        profile_table = Table(
            [
                [
                    Paragraph(label, pdf_styles["table_label"]),
                    Paragraph(value, pdf_styles["table_value"]),
                ]
                for label, value in profile_rows
            ],
            colWidths=[62 * mm, 118 * mm],
        )
        profile_table.setStyle(_TABLE_STYLE)
        story.append(profile_table)
        story.append(Spacer(1, 8))

    # Past interventions table
    if interventions:
        intervention_rows = [["Name", "Dates", "Formator", "Outcomes", "Links"]]
        for intervention in interventions:
            date_range = _text(intervention.date_started)
            if intervention.date_ended:
                date_range = f"{date_range} to {intervention.date_ended}"

            links = [
                link
                for link in [
                    intervention.output_link,
                    intervention.pictures_link,
                    intervention.evaluation_link,
                ]
                if link
            ]

            intervention_rows.append(
                [
                    _text(intervention.name),
                    _text(date_range),
                    _text(intervention.formator),
                    _text(intervention.outcomes),
                    _text(" | ".join(links) if links else "-"),
                ]
            )

        intervention_table = Table(
            intervention_rows,
            colWidths=[32 * mm, 30 * mm, 30 * mm, 46 * mm, 42 * mm],
            repeatRows=1,
        )
        intervention_table.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 1.0, colors.black),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f2f2f2")),
                    ("FONTNAME", (0, 0), (-1, 0), "Times-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        story.append(intervention_table)

    # ── Build the PDF and return it ──
    document.build(story)
    pdf = buffer.getvalue()
    buffer.close()

    filename = f"partner_{partner.pk}_details.pdf"
    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


# ── Partner Create (Multi-step Wizard) ───────────────────────────


@login_required
def partner_create(request):
    """Create a new partner via a 4-step session-based wizard.

    Flow::

        GET  /partners/create/           → Step 1 (or resume from last step)
        GET  /partners/create/?step=2    → Step 2
        ...
        POST /partners/create/?step=4    → validate & save everything

    Special POST parameters:
        ``save_draft``
            When ``"1"``, the current step's POST data is serialised into
            the session and the user is redirected to the partner list.
            The next time they visit ``/partners/create/`` they will be
            automatically redirected to the step they were on.

        ``reset=1`` (query param)
            Clears all wizard state and returns to Step 1.

    The step number is passed via the ``step`` query parameter (default
    ``"1"``).  All intermediate data is stored in ``request.session``
    under the key ``partner_create_wizard``.

    Template:
        ``partners/partner_form.html``  (shared across all steps)
    """
    step = request.GET.get("step", "1")

    # ── Reset: clear session and start over ──
    if request.GET.get("reset") == "1":
        _clear_create_wizard(request)
        return _redirect_create(step=1)

    wizard_data = request.session.get(CREATE_STEP_SESSION_KEY, {})

    # ── Auto-resume: if user navigated directly to /create/ without a
    #    step param, send them to the last step they were on. ──
    if request.method == "GET" and "step" not in request.GET:
        resume_step = wizard_data.get("last_step")
        if resume_step and resume_step != "1":
            return _redirect_create(step=resume_step)

    # ── POST handling (form validation + wizard advancement) ──
    if request.method == "POST":
        # Draft-save: stash POST data in session, go back to list
        if request.POST.get("save_draft") == "1":
            wizard_data["last_step"] = step
            wizard_data[f"draft_step_{step}"] = _serialize_post_data(request.POST)
            request.session[CREATE_STEP_SESSION_KEY] = wizard_data
            return redirect("partner-list")

        # --- Step 1: Partner details + contacts ---
        if step == "1":
            return _handle_create_step_1(request, wizard_data)

        # --- Step 2: Socioeconomic profile ---
        if step == "2":
            return _handle_create_step_2(request, wizard_data)

        # --- Step 3: Needs repository (conditional) ---
        if step == "3":
            return _handle_create_step_3(request, wizard_data)

        # --- Step 4: Past interventions (conditional) + final save ---
        if step == "4":
            return _handle_create_step_4(request, wizard_data)

    # ── GET handling (render the appropriate step) ──

    # Step 1 — always accessible
    if step == "1":
        return _render_create_step_1(request, wizard_data)

    # Steps 2-4 require that Step 1 was completed (partner data exists)
    if not wizard_data.get("partner"):
        return _redirect_create(step=1)

    if step == "2":
        return _render_create_step_2(request, wizard_data)

    if step == "3":
        return _render_create_step_3(request, wizard_data)

    if step == "4":
        return _render_create_step_4(request, wizard_data)

    return _redirect_create(step=1)


# ── Wizard POST handlers ─────────────────────────────────────────


def _handle_create_step_1(request, wizard_data):
    """Validate Step 1 (partner details + contacts) and advance to Step 2."""
    form = PartnerCreateStepOneForm(request.POST)
    contact_formset = ContactFormSet(request.POST, prefix="contact")

    if form.is_valid() and contact_formset.is_valid():
        # Store partner fields (exclude the extra boolean flags)
        wizard_data["partner"] = {
            k: _make_session_safe(v)
            for k, v in form.cleaned_data.items()
            if k in form.Meta.fields
        }
        wizard_data["include_needs"] = form.cleaned_data.get("include_needs", False)
        wizard_data["include_past_interventions"] = form.cleaned_data.get(
            "include_past_interventions", False
        )
        wizard_data["contacts"] = [
            _make_session_safe(cf.cleaned_data)
            for cf in contact_formset.forms
            if cf.cleaned_data
        ]
        wizard_data.pop("draft_step_1", None)
        wizard_data["last_step"] = "2"
        request.session[CREATE_STEP_SESSION_KEY] = wizard_data
        return _redirect_create(step=2)

    # Validation failed — re-render with errors
    return render(
        request,
        "partners/partner_form.html",
        {
            "step": 1,
            "step_title": "Partner Details and Contacts",
            "form": form,
            "contact_formset": contact_formset,
        },
    )


def _handle_create_step_2(request, wizard_data):
    """Validate Step 2 (socioeconomic profile) and advance to Step 3."""
    socioeconomic_formset = SocioEconomicProfileFormSet(
        request.POST, prefix="socioeconomic"
    )

    if socioeconomic_formset.is_valid():
        wizard_data["socioeconomic_profiles"] = [
            _make_session_safe(sf.cleaned_data)
            for sf in socioeconomic_formset.forms
            if sf.cleaned_data
        ]
        wizard_data.pop("draft_step_2", None)
        wizard_data["last_step"] = "3"
        request.session[CREATE_STEP_SESSION_KEY] = wizard_data
        return _redirect_create(step=3)

    return render(
        request,
        "partners/partner_form.html",
        {
            "step": 2,
            "step_title": "Socioeconomic Profile",
            "socioeconomic_formset": socioeconomic_formset,
            "include_needs": wizard_data.get("include_needs", False),
            "include_past_interventions": wizard_data.get(
                "include_past_interventions", False
            ),
        },
    )


def _handle_create_step_3(request, wizard_data):
    """Validate Step 3 (needs) and advance to Step 4.

    If the user unchecked ``include_needs`` in Step 1, this step is
    skipped entirely by redirecting to Step 4.
    """
    if not wizard_data.get("include_needs", False):
        return _redirect_create(step=4)

    need_formset = NeedFormSet(request.POST, prefix="need")

    if need_formset.is_valid():
        wizard_data["needs"] = [
            _make_session_safe(pf.cleaned_data)
            for pf in need_formset.forms
            if pf.cleaned_data
        ]
        wizard_data.pop("draft_step_3", None)
        wizard_data["last_step"] = "4"
        request.session[CREATE_STEP_SESSION_KEY] = wizard_data
        return _redirect_create(step=4)

    return render(
        request,
        "partners/partner_form.html",
        {
            "step": 3,
            "step_title": "Needs Repository",
            "need_formset": need_formset,
            "include_needs": True,
            "include_past_interventions": wizard_data.get(
                "include_past_interventions", False
            ),
        },
    )


def _handle_create_step_4(request, wizard_data):
    """Validate Step 4 (past interventions) and commit everything to the DB.

    If ``include_past_interventions`` is False, skips validation and
    saves with no intervention data.  All models are created inside a
    single ``transaction.atomic()`` block to prevent partial saves.
    """
    if not wizard_data.get("include_past_interventions", False):
        intervention_formset = PastInterventionFormSet(prefix="intervention")
        intervention_cleaned = []
    else:
        intervention_formset = PastInterventionFormSet(
            request.POST, prefix="intervention"
        )
        if not intervention_formset.is_valid():
            return render(
                request,
                "partners/partner_form.html",
                {
                    "step": 4,
                    "step_title": "Past Interventions",
                    "intervention_formset": intervention_formset,
                    "include_needs": wizard_data.get("include_needs", False),
                    "include_past_interventions": True,
                },
            )
        intervention_cleaned = [
            _make_session_safe(inf.cleaned_data)
            for inf in intervention_formset.forms
            if inf.cleaned_data
        ]
        wizard_data["past_interventions"] = intervention_cleaned
        wizard_data.pop("draft_step_4", None)
        request.session[CREATE_STEP_SESSION_KEY] = wizard_data

    # Guard: partner data from Step 1 must exist
    partner_payload = wizard_data.get("partner")
    if not partner_payload:
        return _redirect_create(step=1)

    # ── Persist everything in a single transaction ──
    with transaction.atomic():
        partner = Partner.objects.create(
            **partner_payload,
            updated_by=(request.user if request.user.is_authenticated else None),
        )

        for contact_data in wizard_data.get("contacts", []):
            contact_data.pop("id", None)
            partner.contacts.create(**contact_data)

        for profile_data in wizard_data.get("socioeconomic_profiles", []):
            profile_data.pop("id", None)
            partner.socioeconomic_profiles.create(**profile_data)

        for need_data in wizard_data.get("needs", []):
            need_data.pop("id", None)
            partner.needs.create(**need_data)

        for intervention_data in intervention_cleaned:
            intervention_data.pop("id", None)
            # The ``formator`` field is a FK — convert value to
            # ``formator_id`` for ``create()``.
            if intervention_data.get("formator") is not None:
                intervention_data["formator_id"] = intervention_data.pop("formator")
            partner.past_interventions.create(**intervention_data)

    _clear_create_wizard(request)
    return redirect("partner-detail", pk=partner.pk)


# ── Wizard GET renderers ─────────────────────────────────────────


def _render_create_step_1(request, wizard_data):
    """Render Step 1 form, restoring either a saved draft or previous data."""
    step_one_draft = wizard_data.get("draft_step_1")
    if step_one_draft:
        # User saved a draft — restore the exact POST data
        draft_data = _deserialize_post_data(step_one_draft)
        form = PartnerCreateStepOneForm(draft_data)
        contact_formset = ContactFormSet(draft_data, prefix="contact")
    else:
        # Fresh or previously-validated — use initial data from session
        form = PartnerCreateStepOneForm(
            initial=_build_step_one_initial_from_session(wizard_data)
        )
        contact_initial = (
            wizard_data.get("contacts") if wizard_data.get("contacts") else None
        )
        contact_formset = ContactFormSet(prefix="contact", initial=contact_initial)

    return render(
        request,
        "partners/partner_form.html",
        {
            "step": 1,
            "step_title": "Partner Details and Contacts",
            "form": form,
            "contact_formset": contact_formset,
        },
    )


def _render_create_step_2(request, wizard_data):
    """Render Step 2 (socioeconomic profile)."""
    step_two_draft = wizard_data.get("draft_step_2")
    if step_two_draft:
        socioeconomic_formset = SocioEconomicProfileFormSet(
            _deserialize_post_data(step_two_draft), prefix="socioeconomic"
        )
    else:
        socioeconomic_initial = (
            wizard_data.get("socioeconomic_profiles")
            if wizard_data.get("socioeconomic_profiles")
            else None
        )
        socioeconomic_formset = SocioEconomicProfileFormSet(
            prefix="socioeconomic", initial=socioeconomic_initial
        )

    return render(
        request,
        "partners/partner_form.html",
        {
            "step": 2,
            "step_title": "Socioeconomic Profile",
            "socioeconomic_formset": socioeconomic_formset,
            "include_needs": wizard_data.get("include_needs", False),
            "include_past_interventions": wizard_data.get(
                "include_past_interventions", False
            ),
        },
    )


def _render_create_step_3(request, wizard_data):
    """Render Step 3 (needs).  Redirects to Step 4 if needs were not included."""
    if not wizard_data.get("include_needs", False):
        return _redirect_create(step=4)

    step_three_draft = wizard_data.get("draft_step_3")
    if step_three_draft:
        need_formset = NeedFormSet(
            _deserialize_post_data(step_three_draft), prefix="need"
        )
    else:
        need_initial = wizard_data.get("needs") if wizard_data.get("needs") else None
        need_formset = NeedFormSet(prefix="need", initial=need_initial)

    return render(
        request,
        "partners/partner_form.html",
        {
            "step": 3,
            "step_title": "Needs Repository",
            "need_formset": need_formset,
            "include_needs": True,
            "include_past_interventions": wizard_data.get(
                "include_past_interventions", False
            ),
        },
    )


def _render_create_step_4(request, wizard_data):
    """Render Step 4 (past interventions).

    If interventions were not included, renders an empty (hidden)
    formset so the final save can proceed.
    """
    if wizard_data.get("include_past_interventions", False):
        step_four_draft = wizard_data.get("draft_step_4")
        if step_four_draft:
            intervention_formset = PastInterventionFormSet(
                _deserialize_post_data(step_four_draft),
                prefix="intervention",
            )
        else:
            intervention_initial = (
                wizard_data.get("past_interventions")
                if wizard_data.get("past_interventions")
                else None
            )
            intervention_formset = PastInterventionFormSet(
                prefix="intervention", initial=intervention_initial
            )
    else:
        intervention_formset = PastInterventionFormSet(prefix="intervention")

    return render(
        request,
        "partners/partner_form.html",
        {
            "step": 4,
            "step_title": "Past Interventions",
            "intervention_formset": intervention_formset,
            "include_needs": wizard_data.get("include_needs", False),
            "include_past_interventions": wizard_data.get(
                "include_past_interventions", False
            ),
        },
    )


# ── Partner Update / Delete ──────────────────────────────────────


@login_required
def partner_update(request, pk):
    """Edit an existing partner's core fields.

    Uses ``PartnerForm`` (not the multi-step wizard).  On successful
    save, redirects to the partner detail page.

    Template:
        ``partners/partner_form.html``  (with ``is_edit=True``)
    """
    partner = get_object_or_404(Partner, pk=pk, is_archived=False)

    if request.method == "POST":
        form = PartnerForm(request.POST, instance=partner)

        if form.is_valid():
            partner_obj = form.save(commit=False)
            partner_obj.updated_by = (
                request.user if request.user.is_authenticated else None
            )
            partner_obj.save()
            return redirect("partner-detail", pk=partner.pk)

        return render(
            request,
            "partners/partner_form.html",
            {
                "form": form,
                "partner": partner,
                "is_edit": True,
            },
        )

    form = PartnerForm(instance=partner)

    return render(
        request,
        "partners/partner_form.html",
        {
            "form": form,
            "partner": partner,
            "is_edit": True,
        },
    )


@login_required
def partner_delete(request, pk):
    """Soft-delete a partner by setting ``is_archived=True``.

    Only accepts POST requests.  GET requests are redirected to the
    partner detail page (the template should render a confirmation form).
    """
    partner = get_object_or_404(Partner, pk=pk, is_archived=False)
    if request.method == "POST":
        partner.is_archived = True
        partner.save(update_fields=["is_archived"])
        return redirect("partner-list")
    return redirect("partner-detail", pk=pk)


# ── Needs CRUD ───────────────────────────────────────────────────


@login_required
def need_create(request, partner_pk):
    """Add a new need to a partner.

    The ``community_partner`` FK is set manually after ``save(commit=False)``
    so the form doesn't need to include it as a field.

    Template:
        ``partners/generic_sub_form.html``
    """
    partner = get_object_or_404(Partner, pk=partner_pk, is_archived=False)
    if request.method == "POST":
        form = NeedForm(request.POST)
        if form.is_valid():
            need = form.save(commit=False)
            need.community_partner = partner
            need.save()
            return redirect("partner-detail", pk=partner.pk)
    else:
        form = NeedForm()
    return render(
        request,
        "partners/generic_sub_form.html",
        {
            "form": form,
            "partner": partner,
            "title": "Add Need",
            "section_label": "Need Details",
        },
    )


def need_detail(request, pk):
    """Display a single need and its parent partner.

    Template:
        ``partners/need_detail.html``
    """
    need = get_object_or_404(Needs, pk=pk, is_archived=False)
    return render(
        request,
        "partners/need_detail.html",
        {"need": need, "partner": need.community_partner},
    )


@login_required
def need_update(request, pk):
    """Edit an existing need.

    Template:
        ``partners/generic_sub_form.html``
    """
    need = get_object_or_404(Needs, pk=pk, is_archived=False)
    partner = need.community_partner
    if request.method == "POST":
        form = NeedForm(request.POST, instance=need)
        if form.is_valid():
            form.save()
            return redirect("partner-detail", pk=partner.pk)
    else:
        form = NeedForm(instance=need)
    return render(
        request,
        "partners/generic_sub_form.html",
        {
            "form": form,
            "partner": partner,
            "title": "Edit Need",
            "section_label": "Need Details",
        },
    )


@login_required
def need_delete(request, pk):
    """Soft-delete a need by setting ``is_archived=True``.

    Only acts on POST; GET redirects to the partner detail page.
    """
    need = get_object_or_404(Needs, pk=pk, is_archived=False)
    partner_pk = need.community_partner.pk
    if request.method == "POST":
        need.is_archived = True
        need.save(update_fields=["is_archived"])
    return redirect("partner-detail", pk=partner_pk)


# ── Past Intervention CRUD ──────────────────────────────────────


@login_required
def intervention_create(request, partner_pk):
    """Add a new past intervention to a partner.

    Template:
        ``partners/generic_sub_form.html``
    """
    partner = get_object_or_404(Partner, pk=partner_pk, is_archived=False)
    if request.method == "POST":
        form = PastInterventionForm(request.POST)
        if form.is_valid():
            intervention = form.save(commit=False)
            intervention.community_partner = partner
            intervention.save()
            return redirect("partner-detail", pk=partner.pk)
    else:
        form = PastInterventionForm()
    return render(
        request,
        "partners/generic_sub_form.html",
        {
            "form": form,
            "partner": partner,
            "title": "Add Past Intervention",
            "section_label": "Intervention Details",
        },
    )


def intervention_detail(request, pk):
    """Display a single past intervention and its parent partner.

    Template:
        ``partners/intervention_detail.html``
    """
    intervention = get_object_or_404(PastInterventions, pk=pk, is_archived=False)
    return render(
        request,
        "partners/intervention_detail.html",
        {
            "intervention": intervention,
            "partner": intervention.community_partner,
        },
    )


@login_required
def intervention_update(request, pk):
    """Edit an existing past intervention.

    Template:
        ``partners/generic_sub_form.html``
    """
    intervention = get_object_or_404(PastInterventions, pk=pk, is_archived=False)
    partner = intervention.community_partner
    if request.method == "POST":
        form = PastInterventionForm(request.POST, instance=intervention)
        if form.is_valid():
            form.save()
            return redirect("partner-detail", pk=partner.pk)
    else:
        form = PastInterventionForm(instance=intervention)
    return render(
        request,
        "partners/generic_sub_form.html",
        {
            "form": form,
            "partner": partner,
            "title": "Edit Past Intervention",
            "section_label": "Intervention Details",
        },
    )


@login_required
def intervention_delete(request, pk):
    """Soft-delete an intervention by setting ``is_archived=True``.

    Only acts on POST; GET redirects to the partner detail page.
    """
    intervention = get_object_or_404(PastInterventions, pk=pk, is_archived=False)
    partner_pk = intervention.community_partner.pk
    if request.method == "POST":
        intervention.is_archived = True
        intervention.save(update_fields=["is_archived"])
    return redirect("partner-detail", pk=partner_pk)
