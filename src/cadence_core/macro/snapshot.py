"""Deterministic macro snapshot.

Every number here is computed in code from dated observations — the model never
does arithmetic. The snapshot is look-ahead-free: ``build_macro_snapshot`` only
uses observations dated on or before ``as_of``, so it is safe to use at any bar.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, timedelta

from cadence_core.macro.sources import Observation

TRADING_DAYS = 252


@dataclass(frozen=True)
class MacroSnapshot:
    as_of: date
    us_rate: float | None
    eu_rate: float | None
    rate_diff: float | None
    us_cpi_yoy: float | None
    eu_hicp_yoy: float | None
    usd_index: float | None
    usd_momentum_5d: float | None
    usd_momentum_20d: float | None
    realized_vol: float | None

    def to_dict(self) -> dict:
        return {
            "as_of": self.as_of.isoformat(),
            "us_rate": self.us_rate,
            "eu_rate": self.eu_rate,
            "rate_diff": self.rate_diff,
            "us_cpi_yoy": self.us_cpi_yoy,
            "eu_hicp_yoy": self.eu_hicp_yoy,
            "usd_index": self.usd_index,
            "usd_momentum_5d": self.usd_momentum_5d,
            "usd_momentum_20d": self.usd_momentum_20d,
            "realized_vol": self.realized_vol,
        }

    def summary(self) -> str:
        """A compact, human-readable one-block summary for the context digest."""
        return (
            f"Macro as of {self.as_of.isoformat()}: "
            f"US rate {_rate(self.us_rate)}, EU rate {_rate(self.eu_rate)}, "
            f"rate differential {_rate(self.rate_diff)}; "
            f"US CPI YoY {_pct(self.us_cpi_yoy)}, euro-area HICP YoY {_pct(self.eu_hicp_yoy)}; "
            f"USD index {_num(self.usd_index)} "
            f"(5d {_pct(self.usd_momentum_5d)}, 20d {_pct(self.usd_momentum_20d)}); "
            f"realized FX vol {_pct(self.realized_vol)}."
        )


def build_macro_snapshot(
    series: Mapping[str, Sequence[Observation]], as_of: date
) -> MacroSnapshot:
    us_rate = _latest(series.get("us_rate", ()), as_of)
    eu_rate = _latest(series.get("eu_rate", ()), as_of)
    rate_diff = None if us_rate is None or eu_rate is None else us_rate - eu_rate

    usd = series.get("usd_index", ())
    return MacroSnapshot(
        as_of=as_of,
        us_rate=us_rate,
        eu_rate=eu_rate,
        rate_diff=rate_diff,
        us_cpi_yoy=_yoy(series.get("us_cpi", ()), as_of),
        eu_hicp_yoy=_yoy(series.get("eu_hicp", ()), as_of),
        usd_index=_latest(usd, as_of),
        usd_momentum_5d=_pct_change_over(usd, as_of, 5),
        usd_momentum_20d=_pct_change_over(usd, as_of, 20),
        realized_vol=_realized_vol(series.get("eurusd", ()), as_of),
    )


def _upto(series: Sequence[Observation], as_of: date) -> list[Observation]:
    """Observations dated on or before `as_of`, sorted ascending (look-ahead guard)."""
    return sorted((d, v) for d, v in series if d <= as_of)


def _latest(series: Sequence[Observation], as_of: date) -> float | None:
    rows = _upto(series, as_of)
    return rows[-1][1] if rows else None


def _pct_change_over(series: Sequence[Observation], as_of: date, n: int) -> float | None:
    rows = _upto(series, as_of)
    if len(rows) <= n:
        return None
    base = rows[-1 - n][1]
    if base == 0:
        return None
    return rows[-1][1] / base - 1.0


def _yoy(series: Sequence[Observation], as_of: date) -> float | None:
    rows = _upto(series, as_of)
    if not rows:
        return None
    latest_date, latest_value = rows[-1]
    cutoff = latest_date - timedelta(days=365)
    past = [(d, v) for d, v in rows if d <= cutoff]
    if not past:
        return None
    _, base_value = past[-1]
    if base_value == 0:
        return None
    return latest_value / base_value - 1.0


def _realized_vol(series: Sequence[Observation], as_of: date, window: int = 20) -> float | None:
    rows = _upto(series, as_of)
    if len(rows) <= window:
        return None
    closes = [v for _, v in rows[-(window + 1) :]]
    returns = [
        math.log(closes[i] / closes[i - 1])
        for i in range(1, len(closes))
        if closes[i - 1] > 0 and closes[i] > 0
    ]
    if len(returns) < 2:
        return None
    mean = sum(returns) / len(returns)
    variance = sum((r - mean) ** 2 for r in returns) / (len(returns) - 1)
    return math.sqrt(variance) * math.sqrt(TRADING_DAYS)


def _num(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.3f}"


def _pct(value: float | None) -> str:
    """Format a fraction (0.03) as a signed percentage (+3.00%)."""
    return "n/a" if value is None else f"{value:+.2%}"


def _rate(value: float | None) -> str:
    """Format a rate already expressed in percentage points (3.88 -> 3.88%)."""
    return "n/a" if value is None else f"{value:.2f}%"
