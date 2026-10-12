"""Macro context provider tests (plugs into the shared ContextProvider contract)."""

from __future__ import annotations

from datetime import date

from cadence_core.context.digest import build_digest
from cadence_core.data.fetcher import Fetcher
from cadence_core.macro.news import MacroNewsProvider, NewsTheme
from cadence_core.macro.provider import MacroContextProvider
from tests.helpers import series

RSS_FIXTURE = (
    "<rss><channel><item><title>ECB holds</title>"
    "<pubDate>Mon, 12 Oct 2026 09:00:00 GMT</pubDate></item></channel></rss>"
)


def _series_map():
    return {
        "usd_index": series([100.0 + i for i in range(40)]),
        "us_rate": series([4.0] * 40),
        "eu_rate": series([2.0] * 40),
    }


def test_provider_emits_macro_item():
    provider = MacroContextProvider(_series_map())
    day = date(2023, 2, 9)
    items = provider.items(["MACRO"], day, day)
    assert len(items) == 1
    assert items[0].source == "macro"
    assert items[0].published == day
    assert "Macro as of" in items[0].text


def test_provider_digest_is_reproducible():
    provider = MacroContextProvider(_series_map())
    day = date(2023, 2, 9)
    a = build_digest(provider.items(["MACRO"], day, day))
    b = build_digest(provider.items(["MACRO"], day, day))
    assert a == b
    assert "Macro snapshot" in a


def test_provider_includes_news():
    news = MacroNewsProvider(
        fetcher=Fetcher(get_text=lambda url, **_: RSS_FIXTURE),
        themes=(NewsTheme("central_banks", "ecb", ("https://feed",)),),
        gdelt=None,
    )
    provider = MacroContextProvider(_series_map(), news=news)
    items = provider.items(["MACRO"], date(2026, 10, 1), date(2026, 10, 31))
    assert any(i.source == "rss:central_banks" for i in items)
