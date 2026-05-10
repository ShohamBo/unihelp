import itertools
import logging
import os

logger = logging.getLogger("maslul.scrapers.proxy")


class ProxyRotator:
    """
    Rotates through configured proxy URLs.
    Set SCRAPER_PROXIES env var as comma-separated proxy URLs.
    """

    def __init__(self):
        raw = os.getenv("SCRAPER_PROXIES", "")
        self._proxies = [p.strip() for p in raw.split(",") if p.strip()]
        if not self._proxies:
            logger.warning("No proxies configured — direct connection will be used")
        self._cycle = itertools.cycle(self._proxies) if self._proxies else itertools.cycle([None])

    def next(self) -> str | None:
        return next(self._cycle)

    @property
    def has_proxies(self) -> bool:
        return bool(self._proxies)


proxy_rotator = ProxyRotator()
