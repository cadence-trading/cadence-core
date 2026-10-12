"""Macro news context: official RSS feeds (primary) + GDELT (flanked).

The macro context must be *honest*: it explains and structures the backdrop, it
does not predict prices. Official central-bank / statistics feeds are the primary
source — high-signal, low-volume, keyless. GDELT is used only as a flanking signal
for global coverage volume, strictly rate-limited and with a graceful fallback: if
GDELT throttles or blocks, the provider degrades to RSS instead of failing.
"""

from __future__ import annotations

import json
import urllib.parse
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import date, datetime
from email.utils import parsedate_to_datetime

from cadence_core.context.base import ContextItem
from cadence_core.data.base import DataError
from cadence_core.data.fetcher import Fetcher

GDELT_DOC_URL = "https://api.gdeltproject.org/api/v2/doc/doc"

ECB_PRESS_RSS = "https://www.ecb.europa.eu/rss/press.html"
ECB_BLOG_RSS = "https://www.ecb.europa.eu/rss/blog.html"
FED_PRESS_RSS = "https://www.federalreserve.gov/feeds/press_all.xml"
FED_MONETARY_RSS = "https://www.federalreserve.gov/feeds/press_monetary.xml"


@dataclass(frozen=True)
class NewsTheme:
    key: str
    query: str
    rss_urls: tuple[str, ...] = ()


DEFAULT_THEMES: tuple[NewsTheme, ...] = (
    NewsTheme(
        "central_banks",
        "central bank OR federal reserve OR ECB OR interest rate decision",
        (ECB_PRESS_RSS, FED_PRESS_RSS),
    ),
    NewsTheme("inflation", "inflation OR consumer prices OR CPI", (FED_MONETARY_RSS, ECB_BLOG_RSS)),
    NewsTheme("geopolitics", "war OR sanctions OR tariffs OR conflict", ()),
)


def _localname(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def _child_text(element: ET.Element, name: str) -> str | None:
    for child in element:
        if _localname(child.tag) == name and child.text:
            return child.text.strip()
    return None


def _parse_pubdate(raw: str | None) -> date | None:
    if not raw:
        return None
    text = raw.strip()
    try:  # RFC 822 (RSS pubDate)
        return parsedate_to_datetime(text).date()
    except (TypeError, ValueError):
        pass
    try:  # ISO 8601 (Atom; Python 3.11+ accepts a trailing 'Z')
        return datetime.fromisoformat(text).date()
    except ValueError:
        return None


def parse_rss(text: str, *, source: str) -> list[ContextItem]:
    """Parse an RSS 2.0 or Atom feed into context items (title + published date)."""
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        raise DataError(f"invalid RSS/Atom for {source}") from exc

    items: list[ContextItem] = []
    for element in root.iter():
        if _localname(element.tag) not in {"item", "entry"}:
            continue
        title = _child_text(element, "title")
        if not title:
            continue
        published = _parse_pubdate(
            _child_text(element, "pubdate")
            or _child_text(element, "published")
            or _child_text(element, "updated")
        )
        items.append(
            ContextItem(
                source=f"rss:{source}",
                title=" ".join(title.split()),
                text="",
                published=published,
            )
        )
    return items


def _parse_gdelt_date(raw: object) -> date:
    text = str(raw)
    try:
        return datetime.fromisoformat(text).date()
    except ValueError:
        pass
    if len(text) >= 8 and text[:8].isdigit():
        return date(int(text[0:4]), int(text[4:6]), int(text[6:8]))
    raise ValueError(f"unrecognised GDELT date {raw!r}")


class GdeltClient:
    """Minimal GDELT DOC 2.0 client for coverage-volume timelines."""

    def __init__(self, fetcher: Fetcher, *, base_url: str = GDELT_DOC_URL) -> None:
        self._fetcher = fetcher
        self._base = base_url.rstrip("/")

    def coverage(self, query: str, *, timespan: str = "1d") -> list[tuple[date, float]]:
        params = urllib.parse.urlencode(
            {"query": query, "mode": "timelinevol", "format": "json", "timespan": timespan}
        )
        raw = self._fetcher.text(f"{self._base}?{params}")
        if not raw.lstrip().startswith("{"):
            raise DataError("GDELT returned a non-JSON notice (likely rate-limited)")
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise DataError("invalid JSON from GDELT") from exc
        timeline = data.get("timeline") or []
        if not timeline:
            return []
        points = timeline[0].get("data", [])
        out: list[tuple[date, float]] = []
        for point in points:
            try:
                out.append((_parse_gdelt_date(point.get("date")), float(point.get("value"))))
            except (TypeError, ValueError):
                continue
        return out


@dataclass
class MacroNewsProvider:
    """Official RSS (primary) + GDELT (flanked) news context with graceful fallback."""

    fetcher: Fetcher
    themes: tuple[NewsTheme, ...] = DEFAULT_THEMES
    gdelt: GdeltClient | None = None
    allow_gdelt: bool = True
    degraded: list[str] = field(default_factory=list)

    def items(self, symbols: list[str], start: date, end: date) -> list[ContextItem]:
        self.degraded = []
        out: list[ContextItem] = []
        for theme in self.themes:
            for url in theme.rss_urls:
                try:
                    out.extend(parse_rss(self.fetcher.text(url), source=theme.key))
                except DataError as exc:
                    self.degraded.append(f"rss:{url} ({exc})")
            if self.gdelt is not None and self.allow_gdelt:
                try:
                    coverage = self.gdelt.coverage(theme.query)
                except DataError as exc:
                    self.degraded.append(f"gdelt:{theme.key} ({exc})")
                    continue
                if coverage:
                    latest_date, latest_value = coverage[-1]
                    out.append(
                        ContextItem(
                            source=f"gdelt:{theme.key}",
                            title=f"Global {theme.key} coverage {latest_value:.2%}",
                            text="",
                            published=latest_date,
                        )
                    )
        # Look-ahead guard: never surface an item dated after the requested window.
        return [i for i in out if i.published is None or start <= i.published <= end]
