from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404

from .forms import PartnerForm
from .models import Partner


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
            form.save()
            return HttpResponse(
                headers={"HX-Trigger": "partnerChanged"},
            )
        return render(request, "partners/partner_form.html", {"form": form})

    form = PartnerForm()
    return render(request, "partners/partner_form.html", {"form": form})


def partner_update(request, pk):
    partner = get_object_or_404(Partner, pk=pk)
    if request.method == "POST":
        form = PartnerForm(request.POST, instance=partner)
        if form.is_valid():
            form.save()
            return HttpResponse(
                headers={"HX-Trigger": "partnerChanged"},
            )
        return render(request, "partners/partner_form.html", {"form": form})

    form = PartnerForm(instance=partner, is_edit=True)
    return render(request, "partners/partner_form.html", {"form": form, "is_edit": True})

def partner_delete(request, pk):
    partner = get_object_or_404(Partner, pk=pk)
    if request.method == "DELETE":
        partner.delete()
        return HttpResponse(
            headers={"HX-Trigger": "partnerChanged"},
        )
    return HttpResponse(status=405)