from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404

from .forms import MOAFormSet, PartnerForm, PartnerStatusFormSet
from .models import MOA, Partner, PartnerStatus


def partner_list(request):
    partners = Partner.objects.prefetch_related("statuses", "moas").all()
    return render(request, "partners/partner_list.html", {"partners": partners})


def partner_detail(request, pk):
    partner = get_object_or_404(Partner, pk=pk)
    return render(
        request,
        "partners/partner_detail.html",
        {
            "partner": partner,
            "statuses": partner.statuses.all(),
            "moas": partner.moas.all(),
        },
    )


def partner_create(request):
    if request.method == "POST":
        form = PartnerForm(request.POST)
        if form.is_valid():
            partner = form.save()
            status_formset = PartnerStatusFormSet(
                request.POST, instance=partner, prefix="status"
            )
            moa_formset = MOAFormSet(request.POST, instance=partner, prefix="moa")
            if status_formset.is_valid() and moa_formset.is_valid():
                statuses = status_formset.save(commit=False)
                for s in statuses:
                    s.updated_by = request.user if request.user.is_authenticated else None
                    s.save()
                moa_formset.save()
            return HttpResponse(status=204, headers={"HX-Trigger": "partnerChanged"})
        status_formset = PartnerStatusFormSet(request.POST, prefix="status")
        moa_formset = MOAFormSet(request.POST, prefix="moa")
        return render(
            request,
            "partners/partner_form.html",
            {
                "form": form,
                "status_formset": status_formset,
                "moa_formset": moa_formset,
            },
        )

    form = PartnerForm()
    status_formset = PartnerStatusFormSet(prefix="status")
    moa_formset = MOAFormSet(prefix="moa")
    return render(
        request,
        "partners/partner_form.html",
        {
            "form": form,
            "status_formset": status_formset,
            "moa_formset": moa_formset,
        },
    )


def partner_update(request, pk):
    partner = get_object_or_404(Partner, pk=pk)
    empty_statuses = PartnerStatus.objects.none()
    empty_moas = MOA.objects.none()

    if request.method == "POST":
        form = PartnerForm(request.POST, instance=partner, is_edit=True)
        status_formset = PartnerStatusFormSet(
            request.POST, instance=partner, prefix="status",
            queryset=empty_statuses,
        )
        moa_formset = MOAFormSet(
            request.POST, instance=partner, prefix="moa",
            queryset=empty_moas,
        )
        if form.is_valid() and status_formset.is_valid() and moa_formset.is_valid():
            form.save()
            statuses = status_formset.save(commit=False)
            for s in statuses:
                s.updated_by = request.user if request.user.is_authenticated else None
                s.save()
            moa_formset.save()
            return HttpResponse(status=204, headers={"HX-Trigger": "partnerChanged"})
        return render(
            request,
            "partners/partner_form.html",
            {
                "form": form,
                "status_formset": status_formset,
                "moa_formset": moa_formset,
                "partner": partner,
                "is_edit": True,
            },
        )

    form = PartnerForm(instance=partner, is_edit=True)
    status_formset = PartnerStatusFormSet(
        instance=partner, prefix="status", queryset=empty_statuses,
    )
    moa_formset = MOAFormSet(
        instance=partner, prefix="moa", queryset=empty_moas,
    )
    return render(
        request,
        "partners/partner_form.html",
        {
            "form": form,
            "partner": partner,
            "status_formset": status_formset,
            "moa_formset": moa_formset,
            "is_edit": True,
        },
    )

def partner_delete(request, pk):
    partner = get_object_or_404(Partner, pk=pk)
    if request.method == "DELETE":
        partner.delete()
        return HttpResponse(
            headers={"HX-Trigger": "partnerChanged"},
        )
    return HttpResponse(status=405)