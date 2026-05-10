import asyncio
import time


class TokenBucket:
    """Rate limiting shared across async coroutines via a token bucket."""
    def __init__(self, tokens_per_second: float, burst: int):
        self.capacity = burst
        self.tokens = burst
        self.rate = tokens_per_second
        self.timestamp = time.monotonic()
        self.lock = asyncio.Lock()

    async def acquire(self):
        async with self.lock:
            now = time.monotonic()
            elapsed = now - self.timestamp
            self.timestamp = now

            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)

            if self.tokens < 1:
                wait = (1 - self.tokens) / self.rate
                await asyncio.sleep(wait)
                self.tokens = 0
            else:
                self.tokens -= 1
