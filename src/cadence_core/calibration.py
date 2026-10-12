"""Probability calibration (Brier score, ECE).

The credibility rule requires that a confidence actually means something: if a
model says P=0.8, events tagged 0.8 should happen ~80% of the time.

``brier_score``, ``calibration_table`` and ``expected_calibration_error`` operate
on any object exposing ``prob_up`` (0..1) and ``went_up`` (bool) — so the same
math calibrates price-direction judgments and the macro dollar view.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from cadence_core.judgment.base import Judgment


@dataclass(frozen=True)
class Prediction:
    symbol: str
    ts: datetime
    prob_up: float
    went_up: bool


def judgment_prob_up(judgment: Judgment) -> float | None:
    """Map an up/flat/down direction judgment to P(up); neutral -> None."""
    if judgment.value == "up":
        return judgment.confidence
    if judgment.value == "down":
        return 1.0 - judgment.confidence
    return None


def brier_score(predictions: Sequence[Prediction]) -> float | None:
    if not predictions:
        return None
    total = sum((p.prob_up - (1.0 if p.went_up else 0.0)) ** 2 for p in predictions)
    return total / len(predictions)


def calibration_table(predictions: Sequence[Prediction], n_bins: int = 10) -> list[dict]:
    buckets: list[list[Prediction]] = [[] for _ in range(n_bins)]
    for prediction in predictions:
        index = min(int(prediction.prob_up * n_bins), n_bins - 1)
        buckets[index].append(prediction)

    table: list[dict] = []
    for i, bucket in enumerate(buckets):
        if not bucket:
            continue
        avg_prob = sum(p.prob_up for p in bucket) / len(bucket)
        empirical = sum(1 for p in bucket if p.went_up) / len(bucket)
        table.append(
            {
                "bin_lower": i / n_bins,
                "bin_upper": (i + 1) / n_bins,
                "count": len(bucket),
                "avg_prob": avg_prob,
                "empirical": empirical,
            }
        )
    return table


def expected_calibration_error(
    predictions: Sequence[Prediction], n_bins: int = 10
) -> float | None:
    if not predictions:
        return None
    table = calibration_table(predictions, n_bins)
    n = len(predictions)
    return sum((row["count"] / n) * abs(row["avg_prob"] - row["empirical"]) for row in table)
