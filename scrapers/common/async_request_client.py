import logging
import aiohttp
from enum import Enum
from typing import Callable, AsyncContextManager

from .token_bucket import TokenBucket
from .logger_manager import scraper_logger

AiohttpRequestFunc = Callable[..., AsyncContextManager[aiohttp.ClientResponse]]

default_logger = scraper_logger.get_child("http")


class RequestType(str, Enum):
    GET = "get"
    POST = "post"
    HEAD = "head"


class RetriesExhausted(Exception):
    def __init__(self, msg="Exhausted retries for request"):
        super().__init__(msg)


class ServerErrorException(Exception):
    def __init__(self, http_code: int):
        self.http_code = http_code
        super().__init__(f"HTTP {http_code} server error")


class ClientErrorException(Exception):
    def __init__(self, http_code: int):
        self.http_code = http_code
        super().__init__(f"HTTP {http_code} client error")


class AsyncRequestClient:
    """
    Async HTTP client with token-bucket rate limiting and automatic retries.
    Supports GET, POST, HEAD. Returns text, bytes, or headers depending on request type.
    """

    def __init__(
        self,
        rate_limit: float,
        logger: logging.Logger = default_logger,
        retries: int = 3,
        ignore_http_errors: bool = False,
        proxy: str | None = None,
        follow_redirects: bool = True,
    ):
        assert rate_limit >= 0, f"invalid rate limit {rate_limit}"
        assert retries >= 0, f"invalid retry count {retries}"

        self._raw_proxy = proxy
        self.client: aiohttp.ClientSession | None = None
        self.token_bucket = TokenBucket(tokens_per_second=rate_limit, burst=max(1, int(rate_limit // 2)))
        self.retries = retries
        self.logger = logger
        self.ignore_http_errors = ignore_http_errors
        self.follow_redirects = follow_redirects
        self._proxy: str | None = None

    def _build_session(self) -> aiohttp.ClientSession:
        proxy = self._raw_proxy
        if proxy and proxy.startswith(("socks4://", "socks5://", "socks5h://")):
            from aiohttp_socks import ProxyConnector
            normalized = proxy.replace("socks5h://", "socks5://", 1)
            connector = ProxyConnector.from_url(normalized, force_close=True)
            self._proxy = None
        else:
            connector = aiohttp.TCPConnector(force_close=True)
            self._proxy = proxy
        return aiohttp.ClientSession(connector=connector, trust_env=True)

    async def __aenter__(self):
        self.client = self._build_session()
        await self.client.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.__aexit__(exc_type, exc_val, exc_tb)

    def _get_request_func(self, request_type: RequestType) -> AiohttpRequestFunc:
        assert self.client is not None, "AsyncRequestClient must be used as an async context manager"
        match request_type:
            case RequestType.GET:
                return self.client.get
            case RequestType.POST:
                return self.client.post
            case RequestType.HEAD:
                return self.client.head
            case _:
                raise RuntimeError(f"unrecognized request type {request_type}")

    async def _send(
        self,
        url: str,
        request_type: RequestType,
        headers: dict,
        params: dict,
        return_bytes: bool,
    ) -> str | bytes | dict:
        request_func = self._get_request_func(request_type)
        kwargs = {"url": url, "headers": headers, "params": params, "allow_redirects": self.follow_redirects}
        if self._proxy:
            kwargs["proxy"] = self._proxy

        async with request_func(**kwargs) as resp:
            if not self.ignore_http_errors:
                if resp.status >= 500:
                    raise ServerErrorException(resp.status)
                elif 400 <= resp.status < 500:
                    raise ClientErrorException(resp.status)

            if return_bytes:
                return await resp.read()
            if request_type == RequestType.HEAD:
                return dict(resp.headers)
            return await resp.text()

    async def send_request(
        self,
        url: str,
        request_type: RequestType = RequestType.GET,
        headers: dict | None = None,
        params: dict | None = None,
        return_bytes: bool = False,
    ) -> str | bytes | dict:
        """Rate-limited request with retries on server errors."""
        headers = headers or {}
        params = params or {}

        for attempt in range(self.retries):
            try:
                await self.token_bucket.acquire()
                return await self._send(url, request_type, headers, params, return_bytes)
            except ServerErrorException as e:
                self.logger.warning(
                    f"Server error {e.http_code} on {url}, retrying ({self.retries - attempt - 1} left)"
                )
            except ClientErrorException:
                raise
            except Exception as e:
                self.logger.error(f"Unexpected error on {url}: {e}")
                raise

        raise RetriesExhausted()
