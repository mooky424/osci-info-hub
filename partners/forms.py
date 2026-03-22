from django import forms

from .models import Partner


class PartnerForm(forms.ModelForm):
    class Meta:
        model = Partner
        fields = [
            "name",
            "acronym",
            "area_code",
            "sector",
            "description",
            "address",
            "google_maps_link",
            "ncr_or_province",
            "point_person",
            "head_of_office",
            "contact_no",
            "contact_email",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }
