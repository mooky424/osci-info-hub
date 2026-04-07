from django.contrib import admin

from .models import Partner


@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    list_display = ("name", "moa_start_date", "moa_end_date", "updated_at", "updated_by")
    search_fields = ("name",)
