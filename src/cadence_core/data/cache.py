"""On-disk HTTP cache and a monotonic rate limiter.

Both are injectable so the network layer is fully testable offline:

  * ``HttpCache`` keeps responses under a directory with a TTL;
  * ``RateLimiter`` enforces a minimum interval between calls — GDELT allows one
    request every 5 seconds and returns a rate-limit notice when exceeded.
"""

from __future__ import annotations

import hashlib
import time
from collections.abc import Callable
from pathlib import Path


class HttpCache:
    """A tiny filesystem cache keyed by the request URL."""

    def __init__(
        self,
        root: Path | str,
        ttl: float = 86_400.0,
        *,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._root = Path(root)
        self._ttl = ttl
        self._clock = clock

    def _path(self, key: str) -> Path:
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:32]
        return self._root / f"{digest}.txt"

    def get(self, key: str) -> str | None:
        path = self._path(key)
        if not path.exists():
            return None
        raw = path.read_text(encoding="utf-8")
        stamp, _, body = raw.partition("\n")
        try:
            written = float(stamp)
        except ValueError:
            return None
        if self._ttl >= 0 and (self._clock() - written) > self._ttl:
            return None
        return body

    def put(self, key: str, text: str) -> None:
        self._root.mkdir(parents=True, exist_ok=True)
        self._path(key).write_text(f"{self._clock()}\n{text}", encoding="utf-8")


class RateLimiter:
    """Blocks so that consecutive calls are at least ``min_interval`` apart."""

    def __init__(
        self,
        min_interval: float = 0.0,
        *,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._min_interval = max(0.0, min_interval)
        self._clock = clock
        self._sleep = sleep
        self._last: float | None = None

    def wait(self) -> None:
        if self._min_interval <= 0:
            return
        now = self._clock()
        if self._last is not None:
            remaining = self._min_interval - (now - self._last)
            if remaining > 0:
                self._sleep(remaining)
                now = self._clock()
        self._last = now
