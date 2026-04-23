from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMINISTRATOR = "administrator", "Administrator"
        FORMATOR = "formator", "Formator"

    name = models.CharField(max_length=255, blank=True, default="")
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.ADMINISTRATOR,
    )

    @property
    def is_administrator(self):
        return self.role == self.Role.ADMINISTRATOR
