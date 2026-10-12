"""Shared test helpers."""

from __future__ import annotations

from datetime import date, timedelta

from cadence_core.macro.sources import Observation


def series(values: list[float], start: date = date(2023, 1, 1), step: int = 1) -> list[Observation]:
    """Build a dated series on consecutive (or `step`-spaced) days."""
    out: list[Observation] = []
    day = start
    for value in values:
        out.append((day, float(value)))
        day += timedelta(days=step)
    return out


def constant(value: float, n: int, start: date = date(2023, 1, 1)) -> list[Observation]:
    return series([value] * n, start=start)
