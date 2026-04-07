from django.core.validators import RegexValidator
from django.db import models
from users.models import User

contact_validator = RegexValidator(
    regex=r"^09\d{9}$",
    message="Please input a valid mobile number (09XXXXXXXXX)",
)


class Partner(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    vision = models.TextField(blank=True)
    mission = models.TextField(blank=True)
    goals = models.TextField(blank=True)
    description = models.TextField(blank=True)
    core_values = models.TextField(blank=True)
    date_established = models.DateField()
    sec_registration = models.CharField(max_length=255)
    bir_registration = models.CharField(max_length=255)
    tin = models.CharField(max_length=255)
    moa_start_date = models.DateField(blank=True, null=True)
    moa_end_date = models.DateField(blank=True, null=True)
    moa_link = models.URLField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_partners",
    )

class Contact(models.Model):
    id = models.AutoField(primary_key=True)
    community_partner = models.ForeignKey(Partner, on_delete=models.CASCADE, related_name='contacts')
    name = models.CharField(max_length=255)
    position = models.CharField(max_length=255)
    designation = models.CharField(max_length=255)
    contact_number = models.CharField(max_length=11, validators=[contact_validator])
    email = models.EmailField(blank=True)

class Programs(models.Model):
    id = models.AutoField(primary_key=True)
    community_partner = models.ForeignKey(Partner, on_delete=models.CASCADE, related_name='programs')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    objectives = models.TextField(blank=True)
    expected_outcomes = models.TextField(blank=True)
    skills_needed = models.TextField(blank=True)

class SocioEconomicProfile(models.Model):
    id = models.AutoField(primary_key=True)
    community_partner = models.ForeignKey(Partner, on_delete=models.CASCADE, related_name='socioeconomic_profiles')
    population_size = models.IntegerField()
    population_breakdown = models.TextField(blank=True)
    livelihoods = models.TextField(blank=True)
    health_profile = models.TextField(blank=True)
    sociocultural_profile = models.TextField(blank=True)
    political_profile = models.TextField(blank=True)
    partner_networks = models.TextField(blank=True)
    resources_available = models.TextField(blank=True)
    vulnerabilities = models.TextField(blank=True)
    housing = models.TextField(blank=True)
    transportation = models.TextField(blank=True)
    electricity = models.TextField(blank=True)
    water = models.TextField(blank=True)
    wet_market = models.TextField(blank=True)
    health_facilities = models.TextField(blank=True)
    education_facility = models.TextField(blank=True)
    telecommunication = models.TextField(blank=True)
    others = models.TextField(blank=True)

class PastInterventions(models.Model):
    id = models.AutoField(primary_key=True)
    community_partner = models.ForeignKey(Partner, on_delete=models.CASCADE, related_name='past_interventions')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    outcomes = models.TextField(blank=True)
    formator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)    
    date_started = models.DateField()
    date_ended = models.DateField(blank=True, null=True)
    output_link = models.URLField(blank=True)
    pictures_link = models.URLField(blank=True)
    evaluation_link = models.URLField(blank=True)
