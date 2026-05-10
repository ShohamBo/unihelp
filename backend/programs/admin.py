from django.contrib import admin
from .models import Program, ProgramVersion, AdmissionRequirement, ProgramAlias


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ["name_he", "institution", "faculty", "degree_level", "duration_years", "is_dual_major"]
    list_filter = ["degree_level", "institution", "is_dual_major", "is_extended"]
    search_fields = ["name_he", "name_en", "slug"]
    raw_id_fields = ["institution", "faculty"]


@admin.register(ProgramVersion)
class ProgramVersionAdmin(admin.ModelAdmin):
    list_display = ["program", "academic_year", "scraped_at"]
    list_filter = ["academic_year"]
    raw_id_fields = ["program"]


@admin.register(AdmissionRequirement)
class AdmissionRequirementAdmin(admin.ModelAdmin):
    list_display = ["program", "psychometric_min", "sechem_min", "last_year_threshold"]
    raw_id_fields = ["program"]


@admin.register(ProgramAlias)
class ProgramAliasAdmin(admin.ModelAdmin):
    list_display = ["alias_text", "program", "language", "source_type"]
    list_filter = ["language", "source_type"]
    search_fields = ["alias_text"]
    raw_id_fields = ["program"]
