from django import forms
from django.forms import inlineformset_factory

from .models import MOA, Partner, PartnerStatus


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


class PartnerStatusForm(forms.ModelForm):
    class Meta:
        model = PartnerStatus
        fields = ["status"]


class MOAForm(forms.ModelForm):
    class Meta:
        model = MOA
        fields = [
            "date_issued",
            "termination_date",
            "with_amendment",
            "programs_included",
            "formator",
            "scanned_moa",
        ]
        labels = {
            "with_amendment": "Amended?",
        }
        widgets = {
            "date_issued": forms.DateInput(attrs={"type": "date"}),
            "termination_date": forms.DateInput(attrs={"type": "date"}),
            "programs_included": forms.Textarea(attrs={"rows": 2}),
        }


PartnerStatusFormSet = inlineformset_factory(
    Partner,
    PartnerStatus,
    form=PartnerStatusForm,
    extra=1,
    can_delete=False,
)

MOAFormSet = inlineformset_factory(
    Partner,
    MOA,
    form=MOAForm,
    extra=1,
    can_delete=False,
)
