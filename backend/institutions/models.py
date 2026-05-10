from django.db import models


class Institution(models.Model):
    slug = models.SlugField(unique=True)
    name_he = models.CharField(max_length=200)
    name_en = models.CharField(max_length=200)
    type = models.CharField(
        max_length=20,
        choices=[
            ("university", "אוניברסיטה"),
            ("mechlala", "מכללה"),
            ("mechlala_academic", "מכללה אקדמית"),
        ],
    )
    city = models.CharField(max_length=100)
    website = models.URLField()
    logo_url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict)

    class Meta:
        verbose_name = "מוסד"
        verbose_name_plural = "מוסדות"

    def __str__(self):
        return self.name_he


class Faculty(models.Model):
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name="faculties")
    slug = models.SlugField()
    name_he = models.CharField(max_length=200)
    name_en = models.CharField(max_length=200, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["institution", "slug"], name="unique_faculty_institution_slug")
        ]
        verbose_name = "פקולטה"
        verbose_name_plural = "פקולטות"

    def __str__(self):
        return f"{self.institution.name_he} — {self.name_he}"
