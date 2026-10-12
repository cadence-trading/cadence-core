"""News layer tests: RSS parsing, GDELT client, graceful degradation."""

from __future__ import annotations

from datetime import date

import pytest

from cadence_core.data.base import DataError
from cadence_core.data.fetcher import Fetcher
from cadence_core.macro.news import (
    GdeltClient,
    MacroNewsProvider,
    NewsTheme,
    parse_rss,
)

RSS_FIXTURE = """<?xml version="1.0"?>
<rss version="2.0"><channel>
  <item><title>ECB holds rates steady</title><pubDate>Mon, 12 Oct 2026 09:00:00 GMT</pubDate></item>
  <item><title>Inflation cools</title><pubDate>Sun, 11 Oct 2026 08:00:00 GMT</pubDate></item>
</channel></rss>
"""

ATOM_FIXTURE = """<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry><title>Fed minutes released</title><updated>2026-10-10T12:00:00Z</updated></entry>
</feed>
"""

GDELT_FIXTURE = (
    '{"timeline":[{"data":[{"date":"20261010T000000Z","value":0.021},'
    '{"date":"20261011T000000Z","value":0.019}]}]}'
)


def test_parse_rss_rss2():
    items = parse_rss(RSS_FIXTURE, source="central_banks")
    assert len(items) == 2
    assert items[0].title == "ECB holds rates steady"
    assert items[0].published == date(2026, 10, 12)


def test_parse_rss_atom():
    items = parse_rss(ATOM_FIXTURE, source="central_banks")
    assert len(items) == 1
    assert items[0].published == date(2026, 10, 10)


def test_parse_rss_invalid_raises():
    with pytest.raises(DataError):
        parse_rss("not xml", source="x")


def test_gdelt_coverage_parses():
    fetcher = Fetcher(get_text=lambda url, **_: GDELT_FIXTURE)
    coverage = GdeltClient(fetcher).coverage("inflation")
    assert coverage == [(date(2026, 10, 10), 0.021), (date(2026, 10, 11), 0.019)]


def test_gdelt_non_json_raises():
    fetcher = Fetcher(get_text=lambda url, **_: "Please limit requests to one every 5 seconds")
    with pytest.raises(DataError):
        GdeltClient(fetcher).coverage("inflation")


def test_provider_degrades_when_gdelt_blocked():
    def get_text(url, **_):
        if "gdeltproject" in url:
            return "rate limited"
        return RSS_FIXTURE

    fetcher = Fetcher(get_text=get_text)
    provider = MacroNewsProvider(
        fetcher=fetcher,
        themes=(NewsTheme("central_banks", "ecb", ("https://feed",)),),
        gdelt=GdeltClient(fetcher),
    )
    items = provider.items(["MACRO"], date(2026, 10, 1), date(2026, 10, 31))
    assert provider.degraded  # GDELT failure recorded, not raised
    assert any(i.source == "rss:central_banks" for i in items)


def test_provider_look_ahead_filter():
    fetcher = Fetcher(get_text=lambda url, **_: RSS_FIXTURE)
    provider = MacroNewsProvider(
        fetcher=fetcher,
        themes=(NewsTheme("central_banks", "ecb", ("https://feed",)),),
        gdelt=None,
    )
    # Window ends before the feed items -> nothing surfaces.
    items = provider.items(["MACRO"], date(2026, 10, 1), date(2026, 10, 5))
    assert items == []
