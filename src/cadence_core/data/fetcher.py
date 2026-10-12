"""A fetch front-end that combines the cache and the rate limiter.

``Fetcher`` is the single seam through which the macro layer touches the network,
so tests inject a fake ``get_text`` and never hit the wire.
"""

from __future__ import annotations

from collections.abc import Callable

from cadence_core.config import DEFAULT_USER_AGENT
from cadence_core.data.cache import HttpCache, RateLimiter
from cadence_core.data.http import http_get_text


class Fetcher:
    def __init__(
        self,
        *,
        cache: HttpCache | None = None,
        limiter: RateLimiter | None = None,
        timeout: float = 15.0,
        user_agent: str = DEFAULT_USER_AGENT,
        get_text: Callable[..., str] = http_get_text,
    ) -> None:
        self._cache = cache
        self._limiter = limiter
        self._timeout = timeout
        self._user_agent = user_agent
        self._get_text = get_text

    def text(self, url: str, *, headers: dict[str, str] | None = None) -> str:
        if self._cache is not None:
            cached = self._cache.get(url)
            if cached is not None:
                return cached
        if self._limiter is not None:
            self._limiter.wait()
        text = self._get_text(url, headers=headers, timeout=self._timeout, user_agent=self._user_agent)
        if self._cache is not None:
            self._cache.put(url, text)
        return text
