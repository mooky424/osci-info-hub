from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render

from .forms import AreaEngagementForm, EngagementTransportationForm, SectionForm
from .models import AreaEngagement, EngagementTransportation, Section


def area_engagement_list(request):
    engagements = (
        AreaEngagement.objects.select_related("partner", "section", "formator")
        .all()
        .order_by(
            "section__academic_year",
            "section__semester",
            "section__course",
            "section__section",
            "week",
            "start_date",
            "end_date",
            "id",
        )
    )
    return render(
        request,
        "programs/area_engagement_list.html",
        {"engagements": engagements},
    )


def area_engagement_create(request):
    if request.method == "POST":
        section_form = SectionForm(request.POST)
        engagement_form = AreaEngagementForm(request.POST)
        transportation_form = EngagementTransportationForm(
            request.POST, prefix="transport"
        )

        if (
            section_form.is_valid()
            and engagement_form.is_valid()
            and transportation_form.is_valid()
        ):
            section = section_form.save()

            engagement: AreaEngagement = engagement_form.save(commit=False)
            engagement.section = section
            engagement.save()
            engagement_form.save_m2m()

            transportation: EngagementTransportation = transportation_form.save(
                commit=False
            )
            transportation.area_engagement = engagement
            transportation.save()
            return HttpResponse(
                status=204,
                headers={"HX-Trigger": "areaEngagementChanged"},
            )

        return render(
            request,
            "programs/area_engagement_form.html",
            {
                "section_form": section_form,
                "engagement_form": engagement_form,
                "transportation_form": transportation_form,
            },
        )

    section_form = SectionForm()
    engagement_form = AreaEngagementForm()
    transportation_form = EngagementTransportationForm(prefix="transport")
    return render(
        request,
        "programs/area_engagement_form.html",
        {
            "section_form": section_form,
            "engagement_form": engagement_form,
            "transportation_form": transportation_form,
        },
    )


def area_engagement_detail(request, pk):
    if request.method != "GET":
        return HttpResponse(status=405)

    engagement = get_object_or_404(
        AreaEngagement.objects.select_related("partner", "section", "formator"),
        pk=pk,
    )

    transportation = getattr(engagement, "transportation", None)
    return render(
        request,
        "programs/area_engagement_detail.html",
        {"engagement": engagement, "transportation": transportation},
    )
