from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLE_CHOICES = [
        ("OSCI Staff", "OSCI Staff"),
        ("Assistant Director", "Assistant Director"),
        ("Formator", "Formator"),
    ]
    role = models.CharField(max_length=50, choices=ROLE_CHOICES)
