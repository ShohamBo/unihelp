import asyncio
from functools import wraps
from typing import Callable
from inspect import iscoroutinefunction


class RetriesExhausted(Exception):
    def __init__(self, retries: int, msg="Coroutine failed after {retries} retries"):
        super().__init__(msg.format(retries=retries))


def async_retry(logger, exception_to_retry=Exception, max_attempts: int = 3, delay: float = 1.0):
    """Retry decorator with exponential backoff for async functions."""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            assert max_attempts >= 1, f"attempts value must be at least 1, currently {max_attempts}"
            assert iscoroutinefunction(func), "wrapped function is not a coroutine"

            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exception_to_retry as e:
                    last_exception = e
                    logger.info(f"Attempt {attempt + 1}/{max_attempts} failed: {e}. Retrying in {delay}s...")
                except Exception as e:
                    logger.error(f"Non-retryable exception: {e}")
                    raise e
                await asyncio.sleep(delay * (2 ** attempt))

            logger.error(f"All {max_attempts} attempts failed")
            raise RetriesExhausted(retries=max_attempts) from last_exception

        return wrapper
    return decorator
