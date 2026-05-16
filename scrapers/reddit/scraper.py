import asyncio
import os
from datetime import datetime, timezone

import praw
from bs4 import BeautifulSoup

from ..abstract_scraper import AbstractScraper
from ..models import PageContext, Degree, Course, Review, ScraperResult
from .consts import (
    SOURCE_SLUG, TARGET_SUBREDDITS, SEARCH_QUERIES,
    MIN_TEXT_LENGTH, MAX_POSTS_PER_QUERY, TIME_FILTER,
)


class RedditScraper(AbstractScraper):
    """
    Scrapes Reddit for posts/comments mentioning Israeli academic programs.
    Uses praw (sync API) in asyncio.run_in_executor — not HTTP-based.
    Overrides _scrape() instead of run() so persistence still happens in the base run().
    degree_id is left empty; resolved later by ProgramMapper from review text.
    """

    source_slug = SOURCE_SLUG

    def __init__(self, proxy: str | None = None):
        super().__init__(proxy=proxy)
        self._reddit = praw.Reddit(
            client_id=os.environ["REDDIT_CLIENT_ID"],
            client_secret=os.environ["REDDIT_CLIENT_SECRET"],
            user_agent=os.getenv("REDDIT_USER_AGENT", "maslul-scraper/1.0"),
            ratelimit_seconds=60,
        )

    async def get_subpages(self, soup: BeautifulSoup, directory_url: str) -> list[str]:
        return []

    async def parse_page(self, ctx: PageContext) -> list[Degree | Course | Review]:
        return []

    def _fetch_subreddit(self, subreddit_name: str, query: str) -> list[dict]:
        """Synchronous praw call — executed via executor to avoid blocking the event loop."""
        results = []
        sub = self._reddit.subreddit(subreddit_name)
        try:
            for submission in sub.search(query, limit=MAX_POSTS_PER_QUERY, time_filter=TIME_FILTER):
                if submission.selftext and len(submission.selftext) >= MIN_TEXT_LENGTH:
                    results.append({
                        "id": f"post_{submission.id}",
                        "text": f"{submission.title}\n\n{submission.selftext}",
                        "url": f"https://reddit.com{submission.permalink}",
                        "created_at": submission.created_utc,
                        "subreddit": subreddit_name,
                        "type": "post",
                        "metadata": {"title": submission.title, "score": submission.score, "query": query},
                    })
                submission.comments.replace_more(limit=0)
                for comment in submission.comments.list():
                    if comment.body and len(comment.body) >= MIN_TEXT_LENGTH:
                        results.append({
                            "id": f"comment_{comment.id}",
                            "text": comment.body,
                            "url": f"https://reddit.com{submission.permalink}",
                            "created_at": comment.created_utc,
                            "subreddit": subreddit_name,
                            "type": "comment",
                            "metadata": {"post_title": submission.title, "score": comment.score, "query": query},
                        })
        except Exception as e:
            self.logger.warning(f"Error in r/{subreddit_name} search '{query}': {e}")
        return results

    def _to_review(self, item: dict) -> Review:
        posted_at = (
            datetime.fromtimestamp(item["created_at"], tz=timezone.utc)
            if item.get("created_at") else None
        )
        return Review(
            degree_id="",
            source_slug=self.source_slug,
            source_url=item["url"],
            source_id=item["id"],
            raw_text=item["text"],
            language="he",
            posted_at=posted_at,
            author_handle="",  # never store Reddit handles
            metadata={"subreddit": item["subreddit"], "type": item["type"], **item.get("metadata", {})},
        )

    async def _scrape(self) -> ScraperResult:
        result = ScraperResult(source_slug=self.source_slug)
        loop = asyncio.get_running_loop()
        seen_ids: set[str] = set()
        self.logger.info(
            f"Reddit: {len(TARGET_SUBREDDITS)} subreddits × {len(SEARCH_QUERIES)} queries"
        )
        for sub in TARGET_SUBREDDITS:
            for query in SEARCH_QUERIES:
                self.logger.info(f"Searching r/{sub} for '{query}'")
                raw_items = await loop.run_in_executor(None, self._fetch_subreddit, sub, query)
                for item in raw_items:
                    if item["id"] not in seen_ids:
                        seen_ids.add(item["id"])
                        result.reviews.append(self._to_review(item))
        return result
