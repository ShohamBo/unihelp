import asyncio
import importlib

from celery import shared_task

from .common.logger_manager import scraper_logger

logger = scraper_logger.get_child("tasks")


def _load_class(class_path: str):
    module_path, class_name = class_path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def run_scraper(self, scraper_class_path: str, **kwargs):
    """
    Generic Celery task for any AbstractScraper subclass.
    The scraper's run() method handles both scraping and persistence.

    scraper_class_path examples:
      'scrapers.thestudent.scraper.TheStudentScraper'
      'scrapers.reddit.scraper.RedditScraper'
      'scrapers.tau.scraper.TauScraper'
    """
    scraper_class = _load_class(scraper_class_path)
    scraper = scraper_class(**kwargs)
    try:
        result = asyncio.run(scraper.run())
        summary = {
            "source": scraper.source_slug,
            "degrees": len(result.degrees),
            "courses": len(result.courses),
            "reviews": len(result.reviews),
            "errors": result.errors,
        }
        logger.info(f"[{scraper.source_slug}] Done: {summary}")
        return summary
    except Exception as e:
        logger.error(f"[{scraper_class_path}] Task failed: {e}", exc_info=True)
        raise self.retry(exc=e)
