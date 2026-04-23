from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    add_fieldsets = UserAdmin.add_fieldsets
    list_display = ("username", "email", "name", "role", "is_staff")
    list_filter = ("role", "is_staff", "is_superuser", "is_active")

    def get_fieldsets(self, request, obj=None):
        fieldsets = list(super().get_fieldsets(request, obj))
        fieldsets.append(("Profile", {"fields": ("name", "role")}))
        return fieldsets
