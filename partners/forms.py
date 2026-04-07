from django import forms
from django.forms import inlineformset_factory

from .models import Contact, Partner, PastInterventions, Programs, SocioEconomicProfile


class PartnerForm(forms.ModelForm):
    class Meta:
        model = Partner
        fields = [
            "name",
            "vision",
            "mission",
            "goals",
            "description",
            "core_values",
            "date_established",
            "sec_registration",
            "bir_registration",
            "tin",
            "moa_start_date",
            "moa_end_date",
            "moa_link",
        ]
        widgets = {
            "vision": forms.Textarea(attrs={"rows": 3}),
            "mission": forms.Textarea(attrs={"rows": 3}),
            "goals": forms.Textarea(attrs={"rows": 3}),
            "description": forms.Textarea(attrs={"rows": 3}),
            "core_values": forms.Textarea(attrs={"rows": 3}),
            "date_established": forms.DateInput(attrs={"type": "date"}),
            "moa_start_date": forms.DateInput(attrs={"type": "date"}),
            "moa_end_date": forms.DateInput(attrs={"type": "date"}),
        }


class PartnerCreateStepOneForm(PartnerForm):
    include_programs = forms.BooleanField(required=False, initial=False)
    include_past_interventions = forms.BooleanField(required=False, initial=False)


class ContactForm(forms.ModelForm):
    class Meta:
        model = Contact
        fields = ["name", "position", "designation", "contact_number", "email"]


class ProgramForm(forms.ModelForm):
    class Meta:
        model = Programs
        fields = [
            "name",
            "description",
            "objectives",
            "expected_outcomes",
            "skills_needed",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 2}),
            "objectives": forms.Textarea(attrs={"rows": 2}),
            "expected_outcomes": forms.Textarea(attrs={"rows": 2}),
            "skills_needed": forms.Textarea(attrs={"rows": 2}),
        }


class SocioEconomicProfileForm(forms.ModelForm):
    class Meta:
        model = SocioEconomicProfile
        exclude = ["community_partner"]
        widgets = {
            "population_breakdown": forms.Textarea(attrs={"rows": 2}),
            "livelihoods": forms.Textarea(attrs={"rows": 2}),
            "health_profile": forms.Textarea(attrs={"rows": 2}),
            "sociocultural_profile": forms.Textarea(attrs={"rows": 2}),
            "political_profile": forms.Textarea(attrs={"rows": 2}),
            "partner_networks": forms.Textarea(attrs={"rows": 2}),
            "resources_available": forms.Textarea(attrs={"rows": 2}),
            "vulnerabilities": forms.Textarea(attrs={"rows": 2}),
            "housing": forms.Textarea(attrs={"rows": 2}),
            "transportation": forms.Textarea(attrs={"rows": 2}),
            "electricity": forms.Textarea(attrs={"rows": 2}),
            "water": forms.Textarea(attrs={"rows": 2}),
            "wet_market": forms.Textarea(attrs={"rows": 2}),
            "health_facilities": forms.Textarea(attrs={"rows": 2}),
            "education_facility": forms.Textarea(attrs={"rows": 2}),
            "telecommunication": forms.Textarea(attrs={"rows": 2}),
            "others": forms.Textarea(attrs={"rows": 2}),
        }


class PastInterventionForm(forms.ModelForm):
    class Meta:
        model = PastInterventions
        fields = [
            "name",
            "description",
            "outcomes",
            "formator",
            "date_started",
            "date_ended",
            "output_link",
            "pictures_link",
            "evaluation_link",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 2}),
            "outcomes": forms.Textarea(attrs={"rows": 2}),
            "date_started": forms.DateInput(attrs={"type": "date"}),
            "date_ended": forms.DateInput(attrs={"type": "date"}),
        }


ContactFormSet = inlineformset_factory(
    Partner,
    Contact,
    form=ContactForm,
    extra=1,
    can_delete=False,
)

ProgramFormSet = inlineformset_factory(
    Partner,
    Programs,
    form=ProgramForm,
    extra=1,
    can_delete=False,
)

SocioEconomicProfileFormSet = inlineformset_factory(
    Partner,
    SocioEconomicProfile,
    form=SocioEconomicProfileForm,
    extra=1,
    max_num=1,
    can_delete=False,
)

PastInterventionFormSet = inlineformset_factory(
    Partner,
    PastInterventions,
    form=PastInterventionForm,
    extra=1,
    can_delete=False,
)
