from django.db import models


class Program(models.Model):
    institution_slug = models.SlugField(max_length=100, db_index=True)
    faculty_slug = models.SlugField(max_length=100, blank=True)
    slug = models.SlugField()
    name_he = models.CharField(max_length=300)
    name_en = models.CharField(max_length=300, blank=True)
    degree_level = models.CharField(
        max_length=5,
        choices=[("ba", "תואר ראשון"), ("ma", "תואר שני"), ("phd", "דוקטורט")],
    )
    duration_years = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    total_credits = models.IntegerField(null=True, blank=True)
    is_dual_major = models.BooleanField(default=False)
    is_extended = models.BooleanField(default=False)
    description_he = models.TextField(blank=True)
    canonical_url = models.URLField(blank=True)
    last_scraped_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["institution_slug", "slug"], name="unique_program_institution_slug")
        ]
        indexes = [models.Index(fields=["institution_slug", "degree_level"])]
        verbose_name = "תוכנית"
        verbose_name_plural = "תוכניות"

    def __str__(self):
        return f"{self.institution_slug} — {self.name_he} ({self.degree_level})"


class ProgramVersion(models.Model):
    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name="versions")
    academic_year = models.CharField(max_length=10)
    raw_catalog_data = models.JSONField()
    scraped_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["program", "academic_year"], name="unique_version_program_year")
        ]
        verbose_name = "גרסת תוכנית"
        verbose_name_plural = "גרסאות תוכניות"

    def __str__(self):
        return f"{self.program} — {self.academic_year}"


class AdmissionRequirement(models.Model):
    program = models.OneToOneField(Program, on_delete=models.CASCADE, related_name="admission")
    psychometric_min = models.IntegerField(null=True, blank=True)
    sechem_min = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    bagrut_requirements_he = models.TextField(blank=True)
    additional_requirements_he = models.TextField(blank=True)
    last_year_threshold = models.IntegerField(null=True, blank=True)
    metadata = models.JSONField(default=dict)

    class Meta:
        verbose_name = "דרישות קבלה"
        verbose_name_plural = "דרישות קבלה"

    def __str__(self):
        return f"דרישות קבלה — {self.program}"


class Course(models.Model):
    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name="courses", null=True, blank=True)
    institution_slug = models.SlugField(max_length=100)
    name_he = models.CharField(max_length=300)
    name_en = models.CharField(max_length=300, blank=True)
    course_code = models.CharField(max_length=50, blank=True)
    credits = models.IntegerField(null=True, blank=True)
    semester = models.CharField(max_length=20, blank=True)
    is_mandatory = models.BooleanField(default=True)
    description_he = models.TextField(blank=True)
    metadata = models.JSONField(default=dict)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["program", "course_code"],
                condition=models.Q(course_code__gt=""),
                name="unique_course_program_code",
            )
        ]
        verbose_name = "קורס"
        verbose_name_plural = "קורסים"

    def __str__(self):
        return f"{self.program} — {self.name_he}"


class ProgramAlias(models.Model):
    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name="aliases")
    alias_text = models.CharField(max_length=300)
    language = models.CharField(max_length=5, default="he")
    source_type = models.CharField(
        max_length=20,
        choices=[("manual", "Manual"), ("learned", "Learned"), ("official", "Official")],
        default="manual",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["program", "alias_text"], name="unique_alias")
        ]
        verbose_name = "כינוי תוכנית"
        verbose_name_plural = "כינויי תוכנית"

    def __str__(self):
        return f"{self.alias_text} → {self.program}"
