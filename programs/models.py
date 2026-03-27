from django.db import models


class Section(models.Model):
    academic_year = models.CharField(max_length=20)
    semester = models.CharField(max_length=20)
    course = models.CharField(max_length=100)
    section = models.CharField(max_length=50)
    classroom = models.CharField(max_length=100, blank=True)
    faculty = models.CharField(max_length=255)
    schedule = models.CharField(max_length=255, blank=True)
    num_students = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.course} {self.section} ({self.academic_year} {self.semester})"


class AreaEngagement(models.Model):
    PROGRAM_CHOICES = [
        ("Binhi", "Binhi"),
        ("Punla", "Punla"),
        ("Bigkis", "Bigkis"),
    ]
    MODE_CHOICES = [
        ("2-day Live Out", "2-day Live Out"),
        ("3-day Live Out", "3-day Live Out"),
        ("Stay In", "Stay In"),
    ]
    STATUS_CHOICE = [
        ("Go", "Go"),
        ("Accomplished", "Accomplished"),
        ("Postponed", "Postponed"),
        ("Dissolved", "Dissolved"),
    ]

    section = models.ForeignKey(
        Section,
        on_delete=models.CASCADE,
        related_name="area_engagements",
    )
    partner = models.ForeignKey(
        "partners.Partner",
        on_delete=models.CASCADE,
        related_name="area_engagements",
    )

    type = models.CharField(
        max_length=10,
        choices=PROGRAM_CHOICES,
        blank=True,
    )
    mode = models.CharField(
        max_length=15,
        blank=True,
        choices=MODE_CHOICES,
    )
    formator = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="area_engagements_as_formator",
    )
    deputies = models.ManyToManyField(
        "users.User",
        blank=True,
        related_name="area_engagements_as_deputy",
    )

    week = models.PositiveIntegerField()
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=50, blank=True, choices=STATUS_CHOICE)
    num_slots = models.PositiveIntegerField(default=0)
    num_groups = models.PositiveIntegerField(default=0)
    max_members_per_group = models.PositiveIntegerField(default=0)

    num_deputies_needed = models.PositiveIntegerField(default=0)
    special_remarks = models.TextField(blank=True)

    course_orientation = models.DateTimeField(null=True, blank=True)
    binhi_orientation = models.DateTimeField(null=True, blank=True)
    binhi_orientation_venue = models.CharField(max_length=255, blank=True)
    integration_session = models.DateTimeField(null=True, blank=True)
    integration_session_venue = models.CharField(max_length=255, blank=True)
    area_engagement_assembly = models.DateTimeField(null=True, blank=True)
    processing_session = models.DateTimeField(null=True, blank=True)
    processing_session_venue = models.CharField(max_length=255, blank=True)
    integration_presentation = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.section} - {self.partner} week {self.week}"


class EngagementTransportation(models.Model):
    area_engagement = models.OneToOneField(
        AreaEngagement,
        on_delete=models.CASCADE,
        related_name="transportation",
    )

    mode_of_transportation = models.CharField(max_length=100, blank=True)
    duration_days = models.PositiveIntegerField(default=0)
    total_passengers = models.PositiveIntegerField(default=0)
    num_vehicles_needed = models.PositiveIntegerField(default=0)

    cash_advance_commute = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    km_two_way = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    driver_assembly_time = models.TimeField(null=True, blank=True)
    admu_arrival_time = models.TimeField(null=True, blank=True)
    meetup_place = models.CharField(max_length=255, blank=True)
    excess_km = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    km_formula_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    subtotal_km_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    total_hours = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    excess_hours = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    time_formula_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    net_amount = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    total_cost_with_permits = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )

    def __str__(self):
        return f"Transportation for {self.area_engagement}"
