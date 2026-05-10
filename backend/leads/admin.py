from django.contrib import admin
from .models import Lead


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ["full_name", "email", "phone", "program", "status", "created_at"]
    list_filter = ["status", "consent_marketing"]
    search_fields = ["full_name", "email", "phone"]
    date_hierarchy = "created_at"
    raw_id_fields = ["program"]
