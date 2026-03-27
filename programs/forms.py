from django import forms

from .models import AreaEngagement, EngagementTransportation, Section


class SectionForm(forms.ModelForm):
    class Meta:
        model = Section
        fields = [
            "academic_year",
            "semester",
            "course",
            "section",
            "classroom",
            "faculty",
            "schedule",
            "num_students",
        ]


class AreaEngagementForm(forms.ModelForm):
    class Meta:
        model = AreaEngagement
        fields = [
            "partner",
            "type",
            "mode",
            "formator",
            "week",
            "start_date",
            "end_date",
            "status",
            "num_deputies_needed",
            "special_remarks",
            "course_orientation",
            "binhi_orientation",
            "binhi_orientation_venue",
            "integration_session",
            "integration_session_venue",
            "area_engagement_assembly",
            "processing_session",
            "processing_session_venue",
            "integration_presentation",
        ]
        widgets = {
            "special_remarks": forms.Textarea(attrs={"rows": 2}),
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
            "course_orientation": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "binhi_orientation": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "integration_session": forms.DateTimeInput(
                attrs={"type": "datetime-local"}
            ),
            "area_engagement_assembly": forms.DateTimeInput(
                attrs={"type": "datetime-local"}
            ),
            "processing_session": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "integration_presentation": forms.DateTimeInput(
                attrs={"type": "datetime-local"}
            ),
        }


class EngagementTransportationForm(forms.ModelForm):
    class Meta:
        model = EngagementTransportation
        exclude = ["area_engagement"]
        widgets = {
            "driver_assembly_time": forms.TimeInput(attrs={"type": "time"}),
            "admu_arrival_time": forms.TimeInput(attrs={"type": "time"}),
        }
