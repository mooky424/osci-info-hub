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

    def __init__(self, *args, **kwargs):
        is_edit = kwargs.pop("is_edit", False)
        super().__init__(*args, **kwargs)
        if is_edit:
            self.fields["name"].disabled = True
