from django.db import models


class Lead(models.Model):
    program = models.ForeignKey(
        "programs.Program", on_delete=models.SET_NULL, null=True, blank=True, related_name="leads"
    )
    full_name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=30)
    psychometric_score = models.IntegerField(null=True, blank=True)
    bagrut_average = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True)
    consent_marketing = models.BooleanField(default=False)
    consent_timestamp = models.DateTimeField(null=True, blank=True)
    source_page = models.URLField(blank=True)
    utm_data = models.JSONField(default=dict)
    status = models.CharField(
        max_length=20,
        choices=[("new", "New"), ("contacted", "Contacted"), ("rejected", "Rejected")],
        default="new",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "ליד"
        verbose_name_plural = "לידים"
        indexes = [models.Index(fields=["status", "created_at"])]

    def __str__(self):
        return f"{self.full_name} — {self.email}"
