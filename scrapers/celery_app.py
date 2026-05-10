import os
from celery import Celery
from celery.schedules import crontab

app = Celery("maslul_scrapers")
app.conf.broker_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
app.conf.result_backend = os.getenv("REDIS_URL", "redis://localhost:6379/0")
app.conf.task_serializer = "json"
app.conf.result_serializer = "json"
app.conf.accept_content = ["json"]
app.conf.task_routes = {"scrapers.tasks.*": {"queue": "scrapers"}}
app.autodiscover_tasks(["scrapers"])

# Each scraper at its own cadence. All routed through the same run_scraper task.
app.conf.beat_schedule = {
    # Reviews — TheStudent weekly (Monday 02:00)
    "thestudent-weekly": {
        "task": "scrapers.tasks.run_scraper",
        "schedule": crontab(hour=2, minute=0, day_of_week=1),
        "args": ["scrapers.thestudent.scraper.TheStudentScraper"],
    },
    # Reviews — Study.co.il weekly (Tuesday 03:00)
    "study-weekly": {
        "task": "scrapers.tasks.run_scraper",
        "schedule": crontab(hour=3, minute=0, day_of_week=2),
        "args": ["scrapers.study.scraper.StudyScraper"],
    },
    # Reviews — Reddit every 6 hours
    "reddit-6h": {
        "task": "scrapers.tasks.run_scraper",
        "schedule": crontab(minute=0, hour="*/6"),
        "args": ["scrapers.reddit.scraper.RedditScraper"],
    },
    # Programs — TAU catalog weekly (Wednesday 04:00)
    "tau-programs-weekly": {
        "task": "scrapers.tasks.run_scraper",
        "schedule": crontab(hour=4, minute=0, day_of_week=3),
        "args": ["scrapers.tau.scraper.TauScraper"],
    },
}
