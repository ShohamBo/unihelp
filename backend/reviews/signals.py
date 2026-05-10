from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender="reviews.ReviewSnippet")
def on_snippet_created(sender, instance, created, **kwargs):
    """Queue AI analysis for every newly scraped snippet."""
    if not created:
        return
    from reviews.tasks import analyze_snippet
    analyze_snippet.delay(instance.id)
