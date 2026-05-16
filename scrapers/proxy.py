import os


def get_default_proxy() -> str | None:
    """Return the configured default proxy URL (any scheme: http, socks5h, etc.)."""
    return os.getenv("PROXY_URL") or None
