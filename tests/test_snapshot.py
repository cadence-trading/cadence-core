"""Macro snapshot tests (deterministic; look-ahead-free)."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from cadence_core.macro.snapshot import build_macro_snapshot
from tests.helpers import constant, series

N = 800


def _series_map():
    return {
        "usd_index": series([100.0 * 1.0005**i for i in range(N)]),
        "us_rate": constant(4.0, N),
        "eu_rate": constant(2.0, N),
        "us_cpi": series([100.0 * 1.00008**i for i in range(N)]),
        "eu_hicp": series([100.0 * 1.00005**i for i in range(N)]),
        "eurusd": series([1.1 + 0.01 * ((i % 5) - 2) for i in range(N)]),
    }


def test_rate_differential():
    as_of = date(2023, 1, 1) + timedelta(days=N - 1)
    snap = build_macro_snapshot(_series_map(), as_of=as_of)
    assert snap.us_rate == 4.0
    assert snap.eu_rate == 2.0
    assert snap.rate_diff == pytest.approx(2.0)


def test_usd_momentum_positive():
    as_of = date(2023, 1, 1) + timedelta(days=N - 1)
    snap = build_macro_snapshot(_series_map(), as_of=as_of)
    assert snap.usd_momentum_5d > 0
    assert snap.usd_momentum_20d > 0


def test_yoy_approx_annual():
    as_of = date(2023, 1, 1) + timedelta(days=N - 1)
    snap = build_macro_snapshot(_series_map(), as_of=as_of)
    assert snap.us_cpi_yoy == pytest.approx(0.0296, abs=0.005)
    assert snap.eu_hicp_yoy == pytest.approx(0.0184, abs=0.005)


def test_realized_vol_positive():
    as_of = date(2023, 1, 1) + timedelta(days=N - 1)
    snap = build_macro_snapshot(_series_map(), as_of=as_of)
    assert snap.realized_vol is not None
    assert snap.realized_vol > 0


def test_look_ahead_guard_ignores_future():
    base = series([100.0 * 1.0005**i for i in range(60)])
    as_of = base[-1][0]
    future = [(as_of + timedelta(days=1), 999.0)]
    snap = build_macro_snapshot({"usd_index": base + future}, as_of=as_of)
    assert snap.usd_index == pytest.approx(base[-1][1])
    assert snap.usd_index != 999.0


def test_summary_formats_rates_in_percentage_points():
    as_of = date(2023, 1, 1) + timedelta(days=N - 1)
    summary = build_macro_snapshot(_series_map(), as_of=as_of).summary()
    assert "US rate 4.00%" in summary
    assert "rate differential 2.00%" in summary
    assert "388" not in summary


def test_missing_series_gives_none():
    snap = build_macro_snapshot({}, as_of=date(2024, 1, 1))
    assert snap.us_rate is None
    assert snap.rate_diff is None
    assert snap.usd_index is None
    assert "n/a" in snap.summary()
