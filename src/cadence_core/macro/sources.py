"""Keyless macro data sources: FRED CSV and ECB SDMX CSV.

Both endpoints are keyless (verified) and return dated observations, which makes
the macro backbone reproducible without an API key:

  * FRED:  https://fred.stlouisfed.org/graph/fredgraph.csv?id=<ID>
  * ECB:   https://data-api.ecb.europa.eu/service/data/<KEY>?format=csvdata

The default manifest mixes both sources on purpose: it exercises the FRED and ECB
parsers and keeps the series auditable.
"""

from __future__ import annotations

import csv
import io
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from cadence_core.data.base import DataError
from cadence_core.data.fetcher import Fetcher

FRED_CSV_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={spec}"
ECB_CSV_URL = "https://data-api.ecb.europa.eu/service/data/{spec}?format=csvdata"

Observation = tuple[date, float]


@dataclass(frozen=True)
class SeriesSpec:
    name: str  # canonical name used by the snapshot
    source: str  # "fred" | "ecb"
    spec: str  # FRED series id, or ECB data key
    frequency: str = "daily"
    description: str = ""


DEFAULT_SERIES: tuple[SeriesSpec, ...] = (
    SeriesSpec("usd_index", "fred", "DTWEXBGS", "daily", "Nominal broad U.S. dollar index"),
    SeriesSpec("us_rate", "fred", "DFF", "daily", "US effective federal funds rate"),
    SeriesSpec("eu_rate", "fred", "ECBDFR", "daily", "ECB deposit facility rate"),
    SeriesSpec("us_cpi", "fred", "CPIAUCSL", "monthly", "US CPI, all urban consumers"),
    SeriesSpec(
        "eu_hicp",
        "fred",
        "CP0000EZ19M086NEST",
        "monthly",
        "Euro area HICP, all items",
    ),
    SeriesSpec("eurusd", "ecb", "EXR/D.USD.EUR.SP00.A", "daily", "ECB EUR/USD reference rate"),
)


def series_url(spec: SeriesSpec) -> str:
    if spec.source == "fred":
        return FRED_CSV_URL.format(spec=spec.spec)
    if spec.source == "ecb":
        return ECB_CSV_URL.format(spec=spec.spec)
    raise DataError(f"unknown source {spec.source!r} for series {spec.name!r}")


def parse_fred_csv(text: str) -> list[Observation]:
    """Parse a FRED ``fredgraph.csv`` body (DATE,value; '.' marks a missing value)."""
    rows: list[Observation] = []
    for line in text.splitlines()[1:]:
        if "," not in line:
            continue
        raw_date, _, raw_value = line.partition(",")
        value = raw_value.strip()
        if value in {"", "."}:
            continue
        try:
            rows.append((date.fromisoformat(raw_date.strip()), float(value)))
        except ValueError:
            continue
    return rows


def parse_ecb_csv(text: str) -> list[Observation]:
    """Parse an ECB SDMX ``csvdata`` body (uses the TIME_PERIOD/OBS_VALUE columns)."""
    rows: list[Observation] = []
    reader = csv.DictReader(io.StringIO(text))
    for record in reader:
        raw_date = record.get("TIME_PERIOD")
        raw_value = record.get("OBS_VALUE")
        if not raw_date or not raw_value:
            continue
        try:
            rows.append((date.fromisoformat(raw_date.strip()), float(raw_value)))
        except ValueError:
            continue
    return rows


def parse_series(text: str, source: str) -> list[Observation]:
    if source == "fred":
        return parse_fred_csv(text)
    if source == "ecb":
        return parse_ecb_csv(text)
    raise DataError(f"unknown source {source!r}")


def load_series(spec: SeriesSpec, fetcher: Fetcher) -> list[Observation]:
    text = fetcher.text(series_url(spec))
    rows = parse_series(text, spec.source)
    if not rows:
        raise DataError(f"no observations parsed for series {spec.name!r} ({spec.spec})")
    return rows


def load_series_map(
    fetcher: Fetcher, specs: Sequence[SeriesSpec] = DEFAULT_SERIES
) -> dict[str, list[Observation]]:
    return {spec.name: load_series(spec, fetcher) for spec in specs}
