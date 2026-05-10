from django.contrib import admin
from .models import Institution, Faculty


@admin.register(Institution)
class InstitutionAdmin(admin.ModelAdmin):
    list_display = ["name_he", "name_en", "type", "city", "is_active"]
    list_filter = ["type", "is_active", "city"]
    search_fields = ["name_he", "name_en", "slug"]
    prepopulated_fields = {"slug": ("name_en",)}


@admin.register(Faculty)
class FacultyAdmin(admin.ModelAdmin):
    list_display = ["name_he", "name_en", "institution"]
    list_filter = ["institution"]
    search_fields = ["name_he", "name_en"]
    raw_id_fields = ["institution"]
