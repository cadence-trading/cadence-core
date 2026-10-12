"""Cache and rate-limiter tests (injected clock/sleep; no real time)."""

from __future__ import annotations

from cadence_core.data.cache import HttpCache, RateLimiter


def test_cache_put_get(tmp_path):
    cache = HttpCache(tmp_path, ttl=100.0, clock=lambda: 0.0)
    assert cache.get("http://x") is None
    cache.put("http://x", "hello")
    assert cache.get("http://x") == "hello"


def test_cache_expires(tmp_path):
    now = {"t": 0.0}
    cache = HttpCache(tmp_path, ttl=10.0, clock=lambda: now["t"])
    cache.put("http://x", "hello")
    now["t"] = 5.0
    assert cache.get("http://x") == "hello"
    now["t"] = 11.0
    assert cache.get("http://x") is None


def test_cache_negative_ttl_never_expires(tmp_path):
    now = {"t": 0.0}
    cache = HttpCache(tmp_path, ttl=-1.0, clock=lambda: now["t"])
    cache.put("http://x", "hello")
    now["t"] = 10_000.0
    assert cache.get("http://x") == "hello"


def test_rate_limiter_enforces_gap():
    now = {"t": 0.0}
    slept: list[float] = []

    def sleep(seconds: float) -> None:
        slept.append(seconds)
        now["t"] += seconds

    limiter = RateLimiter(5.0, clock=lambda: now["t"], sleep=sleep)
    limiter.wait()  # first call: no wait
    assert slept == []
    limiter.wait()  # immediately after: waits ~5s
    assert slept == [5.0]


def test_rate_limiter_no_wait_when_elapsed():
    now = {"t": 0.0}
    slept: list[float] = []
    limiter = RateLimiter(
        5.0, clock=lambda: now["t"], sleep=lambda s: (slept.append(s), now.update(t=now["t"] + s))
    )
    limiter.wait()
    now["t"] = 10.0
    limiter.wait()
    assert slept == []
