"""Macro source parsing tests (FRED CSV + ECB SDMX CSV)."""

from __future__ import annotations

import pytest

from cadence_core.data.base import DataError
from cadence_core.data.fetcher import Fetcher
from cadence_core.macro.sources import (
    SeriesSpec,
    load_series,
    parse_ecb_csv,
    parse_fred_csv,
    series_url,
)

FRED_FIXTURE = "DATE,DTWEXBGS\n2026-09-30,121.1\n2026-10-01,.\n2026-10-02,121.4\n"

ECB_FIXTURE = (
    "KEY,TIME_PERIOD,OBS_VALUE\n"
    "EXR.D.USD.EUR.SP00.A,2026-10-09,1.1206\n"
    "EXR.D.USD.EUR.SP00.A,2026-10-12,1.1181\n"
)


def test_parse_fred_csv_skips_missing():
    rows = parse_fred_csv(FRED_FIXTURE)
    assert [v for _, v in rows] == [121.1, 121.4]
    assert rows[0][0].isoformat() == "2026-09-30"


def test_parse_ecb_csv():
    rows = parse_ecb_csv(ECB_FIXTURE)
    assert len(rows) == 2
    assert rows[-1][1] == pytest.approx(1.1181)


def test_series_url():
    assert series_url(SeriesSpec("x", "fred", "DFF")).endswith("id=DFF")
    assert "data-api.ecb.europa.eu" in series_url(SeriesSpec("x", "ecb", "EXR/D.USD.EUR.SP00.A"))


def test_series_url_unknown_source():
    with pytest.raises(DataError):
        series_url(SeriesSpec("x", "bogus", "y"))


def test_load_series_with_fake_fetcher():
    fetcher = Fetcher(get_text=lambda url, **_: FRED_FIXTURE)
    rows = load_series(SeriesSpec("usd_index", "fred", "DTWEXBGS"), fetcher)
    assert len(rows) == 2


def test_load_series_empty_raises():
    fetcher = Fetcher(get_text=lambda url, **_: "DATE,V\n")
    with pytest.raises(DataError):
        load_series(SeriesSpec("usd_index", "fred", "DTWEXBGS"), fetcher)
