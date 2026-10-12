"""Minimal HTTP helpers built on the standard library.

Deliberately no third-party HTTP client: the data layer stays dependency-light and
auditable. Timeouts are mandatory so a hung feed can never wedge a caller.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request

from cadence_core.config import DEFAULT_USER_AGENT
from cadence_core.data.base import DataError


def _open(
    url: str,
    *,
    method: str,
    headers: dict[str, str] | None,
    data: bytes | None,
    timeout: float,
    user_agent: str,
) -> bytes:
    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"User-Agent": user_agent, **(headers or {})},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8", errors="replace")[:200]
        except Exception:  # noqa: BLE001 — best-effort detail only
            detail = ""
        suffix = f": {detail}" if detail else ""
        raise DataError(f"HTTP {exc.code} for {url}{suffix}") from exc
    except urllib.error.URLError as exc:
        raise DataError(f"network error for {url}: {exc.reason}") from exc


def http_get_text(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    timeout: float = 15.0,
    user_agent: str = DEFAULT_USER_AGENT,
) -> str:
    return _open(
        url, method="GET", headers=headers, data=None, timeout=timeout, user_agent=user_agent
    ).decode("utf-8", errors="replace")


def http_get_json(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    timeout: float = 15.0,
    user_agent: str = DEFAULT_USER_AGENT,
) -> dict:
    raw = _open(url, method="GET", headers=headers, data=None, timeout=timeout, user_agent=user_agent)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise DataError(f"invalid JSON from {url}") from exc


def http_post_json(
    url: str,
    payload: dict,
    *,
    headers: dict[str, str] | None = None,
    timeout: float = 15.0,
    user_agent: str = DEFAULT_USER_AGENT,
) -> dict:
    body = json.dumps(payload).encode("utf-8")
    raw = _open(
        url,
        method="POST",
        headers={"Content-Type": "application/json", **(headers or {})},
        data=body,
        timeout=timeout,
        user_agent=user_agent,
    )
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise DataError(f"invalid JSON from {url}") from exc
