from .base import *
import dj_database_url
from decouple import config

DEBUG = True
ALLOWED_HOSTS = ["*"]

database_url = config("DATABASE_URL", default=None)
if database_url:
    parsed = dj_database_url.parse(database_url)
    parsed.setdefault("OPTIONS", {})
    parsed["OPTIONS"].update(DATABASES["default"].get("OPTIONS", {}))
    DATABASES["default"] = parsed

CORS_ALLOW_ALL_ORIGINS = True

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
    },
    "root": {
        "handlers": ["console"],
        "level": "DEBUG",
    },
    "loggers": {
        "django": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}
