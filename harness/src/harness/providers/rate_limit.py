"""A minimal rate limiter shared by the real providers.

Blocks the caller just long enough to keep calls at or below
`calls_per_minute`. Deliberately simple (not a token bucket) since the
harness calls providers sequentially from a single process.
"""

from __future__ import annotations

import time


class RateLimiter:
    def __init__(self, calls_per_minute: float) -> None:
        if calls_per_minute <= 0:
            raise ValueError("calls_per_minute must be positive")
        self.min_interval = 60.0 / calls_per_minute
        self._last_call: float | None = None

    def wait(self) -> None:
        now = time.monotonic()
        if self._last_call is not None:
            elapsed = now - self._last_call
            remaining = self.min_interval - elapsed
            if remaining > 0:
                time.sleep(remaining)
        self._last_call = time.monotonic()
