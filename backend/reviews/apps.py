from django.apps import AppConfig


class ReviewsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "reviews"
    verbose_name = "ביקורות"

    def ready(self):
        import reviews.signals  # noqa: F401 — connects post_save signal
