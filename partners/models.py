from django.core.validators import RegexValidator
from django.db import models
from users.models import User

contact_validator = RegexValidator(
    regex=r"^09\d{9}$",
    message="Please input a valid mobile number (09XXXXXXXXX)",
)


class Partner(models.Model):
    SECTOR_CHOICES = [
        ("Urban Poor", "Urban Poor"),
        ("Rural Poor", "Rural Poor"),
        ("Environment", "Environment"),
        ("Education", "Education"),
        ("Health", "Health"),
        ("Disaster", "Disaster"),
        ("Indigenous Peoples", "Indigenous Peoples"),
        ("Workers", "Workers"),
        ("Women", "Women"),
        ("Youth", "Youth"),
        ("Persons with Disabilities", "Persons with Disabilities"),
        ("Elderly", "Elderly"),
        ("Others", "Others"),
    ]

    NCR_CHOICES = [
        ("NCR+", "NCR+"),
        ("Province", "Province"),
    ]

    name = models.CharField(max_length=100)
    acronym = models.CharField(max_length=20, blank=True)
    area_code = models.CharField(max_length=20, unique=True)
    sector = models.CharField(max_length=50, choices=SECTOR_CHOICES)
    description = models.TextField(blank=True)
    address = models.CharField(max_length=255)
    google_maps_link = models.URLField(max_length=500, blank=True)
    ncr_or_province = models.CharField(
        max_length=10, choices=NCR_CHOICES, blank=True
    )
    point_person = models.CharField(max_length=100)
    head_of_office = models.CharField(max_length=100)
    contact_no = models.CharField(max_length=11, validators=[contact_validator])
    contact_email = models.EmailField(blank=True)

    def __str__(self):
        if self.acronym:
            return f"{self.name} ({self.acronym})"
        return self.name

    @property
    def current_status(self):
        return self.statuses.order_by("-date").first()

    @property
    def active_contract(self):
        from django.utils import timezone

        return (
            self.moas.filter(termination_date__gte=timezone.now().date())
            .order_by("-date_issued")
            .first()
        )


class PartnerStatus(models.Model):
    STATUS_CHOICES = [
        ("Active", "Active"),
        ("Inactive", "Inactive"),
        ("On Hold", "On Hold"),
    ]

    partner = models.ForeignKey(
        Partner,
        on_delete=models.CASCADE,
        related_name="statuses",
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    date = models.DateField(auto_now_add=True)
    updated_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True
    )

    class Meta:
        ordering = ["-date"]
        get_latest_by = "date"

    def __str__(self):
        return f"{self.partner} - {self.status} ({self.date})"


class MOA(models.Model):
    partner = models.ForeignKey(
        Partner,
        on_delete=models.CASCADE,
        related_name="moas",
    )
    date_issued = models.DateField()
    termination_date = models.DateField()
    with_amendment = models.BooleanField(default=False)
    programs_included = models.TextField(blank=True)
    formator = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="moas_as_formator",
    )
    scanned_moa = models.URLField(max_length=500, blank=True)

    class Meta:
        ordering = ["-date_issued"]
        get_latest_by = "date_issued"
        verbose_name = "MOA"
        verbose_name_plural = "MOAs"

    def __str__(self):
        return f"{self.partner} MOA ({self.date_issued} - {self.termination_date})"

    @property
    def duration(self):
        return (self.termination_date - self.date_issued).days
