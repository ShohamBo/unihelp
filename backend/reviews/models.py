from django.db import models

# Use VectorField when pgvector extension is available (production/Docker).
# Fall back to BinaryField for local dev without pgvector installed.
try:
    from pgvector.django import VectorField
    _PGVECTOR_AVAILABLE = True
except Exception:  # pragma: no cover
    VectorField = None
    _PGVECTOR_AVAILABLE = False

THEME_CHOICES = [
    "workload", "professor_quality", "content_relevance", "job_prospects",
    "social_atmosphere", "admin_quality", "exam_difficulty", "grading_fairness",
    "facilities", "location", "value_for_money", "prestige",
]


class ReviewSource(models.Model):
    name = models.CharField(max_length=100, unique=True)
    base_url = models.URLField()
    is_active = models.BooleanField(default=True)
    rate_limit_per_minute = models.IntegerField(default=10)

    class Meta:
        verbose_name = "מקור ביקורות"
        verbose_name_plural = "מקורות ביקורות"

    def __str__(self):
        return self.name


class ReviewSnippet(models.Model):
    source = models.ForeignKey(ReviewSource, on_delete=models.CASCADE, related_name="snippets")
    source_url = models.URLField()
    external_id = models.CharField(max_length=300)  # source's native ID for dedup
    raw_text = models.TextField()
    language = models.CharField(max_length=5, default="he")
    posted_at = models.DateTimeField(null=True, blank=True)
    scraped_at = models.DateTimeField(auto_now_add=True)
    author_handle = models.CharField(max_length=200, blank=True)
    metadata = models.JSONField(default=dict)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["source", "external_id"], name="unique_snippet_source_external_id")
        ]
        indexes = [
            models.Index(fields=["posted_at"]),
            models.Index(fields=["scraped_at"]),
        ]
        verbose_name = "קטע ביקורת"
        verbose_name_plural = "קטעי ביקורת"

    def __str__(self):
        return f"{self.source.name} — {self.external_id}"


class ProgramReviewLink(models.Model):
    snippet = models.ForeignKey(ReviewSnippet, on_delete=models.CASCADE, related_name="program_links")
    program = models.ForeignKey("programs.Program", on_delete=models.CASCADE, related_name="review_links")
    confidence = models.FloatField()
    method = models.CharField(max_length=50)  # 'exact_match', 'fuzzy', 'llm_classified'

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["snippet", "program"], name="unique_link_snippet_program")
        ]
        verbose_name = "קישור ביקורת לתוכנית"
        verbose_name_plural = "קישורי ביקורת לתוכניות"


class ReviewAnalysis(models.Model):
    snippet = models.OneToOneField(ReviewSnippet, on_delete=models.CASCADE, related_name="analysis")
    sentiment = models.FloatField()  # -1 to 1
    themes = models.JSONField()  # list of theme strings from THEME_CHOICES
    summary_he = models.TextField()
    embedding = VectorField(dimensions=1536, null=True, blank=True) if _PGVECTOR_AVAILABLE else models.BinaryField(null=True, blank=True)
    analyzed_at = models.DateTimeField(auto_now_add=True)
    model_version = models.CharField(max_length=50)

    class Meta:
        verbose_name = "ניתוח ביקורת"
        verbose_name_plural = "ניתוחי ביקורות"

    def __str__(self):
        return f"Analysis for {self.snippet}"


class ProgramSummary(models.Model):
    program = models.OneToOneField("programs.Program", on_delete=models.CASCADE, related_name="summary")
    summary_he = models.TextField()
    pros_he = models.JSONField(default=list)
    cons_he = models.JSONField(default=list)
    themes_breakdown = models.JSONField()  # {'workload': 0.8, ...}
    snippet_count = models.IntegerField()
    last_generated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "סיכום תוכנית"
        verbose_name_plural = "סיכומי תוכניות"

    def __str__(self):
        return f"Summary — {self.program}"


class RawScrape(models.Model):
    source = models.ForeignKey(ReviewSource, on_delete=models.CASCADE, related_name="raw_scrapes")
    url = models.URLField()
    raw_content = models.TextField()
    scraped_at = models.DateTimeField(auto_now_add=True)
    processing_status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("processed", "Processed"),
            ("failed", "Failed"),
            ("skipped", "Skipped"),
        ],
        default="pending",
    )
    error = models.TextField(blank=True)

    class Meta:
        indexes = [models.Index(fields=["processing_status", "scraped_at"])]
        verbose_name = "גרידה גולמית"
        verbose_name_plural = "גרידות גולמיות"
