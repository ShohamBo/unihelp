from django.contrib import admin
from .models import ReviewSource, ReviewSnippet, ProgramReviewLink, ReviewAnalysis, ProgramSummary, RawScrape


@admin.register(ReviewSource)
class ReviewSourceAdmin(admin.ModelAdmin):
    list_display = ["name", "base_url", "is_active", "rate_limit_per_minute"]
    list_filter = ["is_active"]


@admin.register(ReviewSnippet)
class ReviewSnippetAdmin(admin.ModelAdmin):
    list_display = ["source_slug", "external_id", "language", "posted_at", "scraped_at"]
    list_filter = ["source_slug", "language"]
    search_fields = ["raw_text", "external_id"]
    date_hierarchy = "scraped_at"


@admin.register(ProgramReviewLink)
class ProgramReviewLinkAdmin(admin.ModelAdmin):
    list_display = ["snippet", "program", "confidence", "method"]
    list_filter = ["method"]
    raw_id_fields = ["snippet", "program"]


@admin.register(ReviewAnalysis)
class ReviewAnalysisAdmin(admin.ModelAdmin):
    list_display = ["snippet", "sentiment", "analyzed_at", "model_version"]
    list_filter = ["model_version"]
    raw_id_fields = ["snippet"]


@admin.register(ProgramSummary)
class ProgramSummaryAdmin(admin.ModelAdmin):
    list_display = ["program", "snippet_count", "last_generated_at"]
    raw_id_fields = ["program"]


@admin.register(RawScrape)
class RawScrapeAdmin(admin.ModelAdmin):
    list_display = ["source", "url", "processing_status", "scraped_at"]
    list_filter = ["source", "processing_status"]
    date_hierarchy = "scraped_at"
