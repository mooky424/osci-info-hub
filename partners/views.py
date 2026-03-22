from django.shortcuts import render, get_object_or_404

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
