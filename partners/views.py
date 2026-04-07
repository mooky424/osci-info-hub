from django.shortcuts import get_object_or_404, redirect, render
from django.http import QueryDict
from django.http import HttpResponseRedirect
from django.urls import reverse
from datetime import date, datetime

from django.db import models, transaction

from .forms import (
    ContactFormSet,
    PartnerCreateStepOneForm,
    PartnerForm,
    PastInterventionForm,
    PastInterventionFormSet,
    ProgramForm,
    ProgramFormSet,
    SocioEconomicProfileFormSet,
)
from .models import Partner, Programs, PastInterventions


CREATE_STEP_SESSION_KEY = "partner_create_wizard"


def _build_step_one_initial_from_session(data):
    initial = data.get("partner", {}).copy()
    initial["include_programs"] = data.get("include_programs", False)
    initial["include_past_interventions"] = data.get("include_past_interventions", False)
    return initial


def _clear_create_wizard(request):
    if CREATE_STEP_SESSION_KEY in request.session:
        del request.session[CREATE_STEP_SESSION_KEY]


def _serialize_post_data(post_data):
    return {key: values for key, values in post_data.lists()}


def _deserialize_post_data(serialized_data):
    query_dict = QueryDict("", mutable=True)
    for key, values in serialized_data.items():
        query_dict.setlist(key, values)
    return query_dict


def _make_session_safe(value):
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
    base_url = reverse("partner-create")
    query = []
    if step is not None:
        query.append(f"step={step}")
    if reset:
        query.append("reset=1")
    if query:
        return HttpResponseRedirect(f"{base_url}?{'&'.join(query)}")
    return HttpResponseRedirect(base_url)


def partner_list(request):
    partners = (
        Partner.objects.select_related("updated_by")
        .prefetch_related(
            "contacts",
            "programs",
            "past_interventions",
            "socioeconomic_profiles",
        )
        .all()
    )
    return render(request, "partners/partner_list.html", {"partners": partners})


def partner_detail(request, pk):
    partner = get_object_or_404(
        Partner.objects.prefetch_related(
            "contacts",
            "programs",
            "socioeconomic_profiles",
            "past_interventions",
        ),
        pk=pk,
    )
    return render(
        request,
        "partners/partner_detail.html",
        {
            "partner": partner,
            "contacts": partner.contacts.all(),
            "programs": partner.programs.all(),
            "socioeconomic_profiles": partner.socioeconomic_profiles.all(),
            "past_interventions": partner.past_interventions.all(),
        },
    )


def partner_create(request):
    step = request.GET.get("step", "1")
    if request.GET.get("reset") == "1":
        _clear_create_wizard(request)
        return _redirect_create(step=1)

    wizard_data = request.session.get(CREATE_STEP_SESSION_KEY, {})

    if request.method == "GET" and "step" not in request.GET:
        resume_step = wizard_data.get("last_step")
        if resume_step and resume_step != "1":
            return _redirect_create(step=resume_step)

    if request.method == "POST":
        if request.POST.get("save_draft") == "1":
            wizard_data["last_step"] = step
            wizard_data[f"draft_step_{step}"] = _serialize_post_data(request.POST)
            request.session[CREATE_STEP_SESSION_KEY] = wizard_data
            return redirect("partner-list")

        if step == "1":
            form = PartnerCreateStepOneForm(request.POST)
            contact_formset = ContactFormSet(request.POST, prefix="contact")
            if form.is_valid() and contact_formset.is_valid():
                wizard_data["partner"] = {
                    k: _make_session_safe(v)
                    for k, v in form.cleaned_data.items()
                    if k in form.Meta.fields
                }
                wizard_data["include_programs"] = form.cleaned_data.get(
                    "include_programs", False
                )
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

        if step == "2":
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
                    "include_programs": wizard_data.get("include_programs", False),
                    "include_past_interventions": wizard_data.get(
                        "include_past_interventions", False
                    ),
                },
            )

        if step == "3":
            if not wizard_data.get("include_programs", False):
                return _redirect_create(step=4)

            program_formset = ProgramFormSet(request.POST, prefix="program")
            if program_formset.is_valid():
                wizard_data["programs"] = [
                    _make_session_safe(pf.cleaned_data)
                    for pf in program_formset.forms
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
                    "step_title": "Programs",
                    "program_formset": program_formset,
                    "include_programs": True,
                    "include_past_interventions": wizard_data.get(
                        "include_past_interventions", False
                    ),
                },
            )

        if step == "4":
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
                            "include_programs": wizard_data.get(
                                "include_programs", False
                            ),
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

            partner_payload = wizard_data.get("partner")
            if not partner_payload:
                return _redirect_create(step=1)

            with transaction.atomic():
                partner = Partner.objects.create(
                    **partner_payload,
                    updated_by=request.user if request.user.is_authenticated else None,
                )

                for contact_data in wizard_data.get("contacts", []):
                    contact_data.pop("id", None)
                    partner.contacts.create(**contact_data)

                for profile_data in wizard_data.get("socioeconomic_profiles", []):
                    profile_data.pop("id", None)
                    partner.socioeconomic_profiles.create(**profile_data)

                for program_data in wizard_data.get("programs", []):
                    program_data.pop("id", None)
                    partner.programs.create(**program_data)

                for intervention_data in intervention_cleaned:
                    intervention_data.pop("id", None)
                    if intervention_data.get("formator") is not None:
                        intervention_data["formator_id"] = intervention_data.pop("formator")
                    partner.past_interventions.create(**intervention_data)

            _clear_create_wizard(request)
            return redirect("partner-detail", pk=partner.pk)

    if step == "1":
        step_one_draft = wizard_data.get("draft_step_1")
        if step_one_draft:
            draft_data = _deserialize_post_data(step_one_draft)
            form = PartnerCreateStepOneForm(draft_data)
            contact_formset = ContactFormSet(draft_data, prefix="contact")
        else:
            form = PartnerCreateStepOneForm(initial=_build_step_one_initial_from_session(wizard_data))
            contact_initial = wizard_data.get("contacts") if wizard_data.get("contacts") else None
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

    if not wizard_data.get("partner"):
        return _redirect_create(step=1)

    if step == "2":
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
                "include_programs": wizard_data.get("include_programs", False),
                "include_past_interventions": wizard_data.get(
                    "include_past_interventions", False
                ),
            },
        )

    if step == "3":
        if not wizard_data.get("include_programs", False):
            return _redirect_create(step=4)
        step_three_draft = wizard_data.get("draft_step_3")
        if step_three_draft:
            program_formset = ProgramFormSet(
                _deserialize_post_data(step_three_draft), prefix="program"
            )
        else:
            program_initial = wizard_data.get("programs") if wizard_data.get("programs") else None
            program_formset = ProgramFormSet(prefix="program", initial=program_initial)
        return render(
            request,
            "partners/partner_form.html",
            {
                "step": 3,
                "step_title": "Programs",
                "program_formset": program_formset,
                "include_programs": True,
                "include_past_interventions": wizard_data.get(
                    "include_past_interventions", False
                ),
            },
        )

    if step == "4":
        if wizard_data.get("include_past_interventions", False):
            step_four_draft = wizard_data.get("draft_step_4")
            if step_four_draft:
                intervention_formset = PastInterventionFormSet(
                    _deserialize_post_data(step_four_draft), prefix="intervention"
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
                "include_programs": wizard_data.get("include_programs", False),
                "include_past_interventions": wizard_data.get(
                    "include_past_interventions", False
                ),
            },
        )

    return _redirect_create(step=1)


def partner_update(request, pk):
    partner = get_object_or_404(Partner, pk=pk)

    if request.method == "POST":
        form = PartnerForm(request.POST, instance=partner)

        if form.is_valid():
            partner_obj = form.save(commit=False)
            partner_obj.updated_by = request.user if request.user.is_authenticated else None
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


def partner_delete(request, pk):
    partner = get_object_or_404(Partner, pk=pk)
    if request.method == "POST":
        partner.delete()
        return redirect("partner-list")
    return redirect("partner-detail", pk=pk)

def program_create(request, partner_pk):
    partner = get_object_or_404(Partner, pk=partner_pk)
    if request.method == "POST":
        form = ProgramForm(request.POST)
        if form.is_valid():
            program = form.save(commit=False)
            program.community_partner = partner
            program.save()
            return redirect("partner-detail", pk=partner.pk)
    else:
        form = ProgramForm()
    return render(
        request,
        "partners/generic_sub_form.html",
        {"form": form, "partner": partner, "title": "Add Program", "section_label": "Program Details"}
    )

def program_detail(request, pk):
    program = get_object_or_404(Programs, pk=pk)
    return render(request, "partners/program_detail.html", {"program": program, "partner": program.community_partner})

def program_update(request, pk):
    program = get_object_or_404(Programs, pk=pk)
    partner = program.community_partner
    if request.method == "POST":
        form = ProgramForm(request.POST, instance=program)
        if form.is_valid():
            form.save()
            return redirect("partner-detail", pk=partner.pk)
    else:
        form = ProgramForm(instance=program)
    return render(
        request,
        "partners/generic_sub_form.html",
        {"form": form, "partner": partner, "title": "Edit Program", "section_label": "Program Details"}
    )

def program_delete(request, pk):
    program = get_object_or_404(Programs, pk=pk)
    partner_pk = program.community_partner.pk
    if request.method == "POST":
        program.delete()
    return redirect("partner-detail", pk=partner_pk)

def intervention_create(request, partner_pk):
    partner = get_object_or_404(Partner, pk=partner_pk)
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
        {"form": form, "partner": partner, "title": "Add Past Intervention", "section_label": "Intervention Details"}
    )

def intervention_detail(request, pk):
    intervention = get_object_or_404(PastInterventions, pk=pk)
    return render(request, "partners/intervention_detail.html", {"intervention": intervention, "partner": intervention.community_partner})

def intervention_update(request, pk):
    intervention = get_object_or_404(PastInterventions, pk=pk)
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
        {"form": form, "partner": partner, "title": "Edit Past Intervention", "section_label": "Intervention Details"}
    )

def intervention_delete(request, pk):
    intervention = get_object_or_404(PastInterventions, pk=pk)
    partner_pk = intervention.community_partner.pk
    if request.method == "POST":
        intervention.delete()
    return redirect("partner-detail", pk=partner_pk)
