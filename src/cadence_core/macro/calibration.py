"""Calibrate the macro dollar view against realized USD-index moves.

This is the honest core of the macro engine: the model's ``dollar_strength`` score
is mapped to a probability that the broad US dollar index rises over the next
``horizon`` observations, and that probability is scored with the shared
Brier/ECE math. If the view is not calibrated, the number says so.

The outcome is the USD index (``DTWEXBGS``), which is keyless and available
historically — so the macro regime view is measurable, not asserted. News is *not*
used here: it cannot be backtested reliably, so it never enters a calibration claim.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, timedelta

from cadence_core.calibration import (
    brier_score,
    calibration_table,
    expected_calibration_error,
)
from cadence_core.judgment.base import Judgment, JudgmentModel
from cadence_core.macro.questions import MACRO_QUESTIONS
from cadence_core.macro.snapshot import build_macro_snapshot
from cadence_core.macro.sources import Observation

# The score levels are probability anchors: choosing a level *is* the estimate.
DOLLAR_LEVEL_PROB_UP: dict[str, float] = {
    "much weaker": 0.05,
    "weaker": 0.25,
    "unchanged": 0.5,
    "stronger": 0.75,
    "much stronger": 0.95,
}
NEUTRAL_LEVELS = {"unchanged"}


@dataclass(frozen=True)
class MacroPrediction:
    ts: date
    prob_up: float
    went_up: bool


@dataclass(frozen=True)
class MacroCalibration:
    n: int
    brier: float | None
    ece: float | None
    table: list[dict]


def level_prob_up(judgment: Judgment | None) -> float | None:
    """Map a ``dollar_strength`` score judgment to P(USD up); neutral -> None."""
    if judgment is None:
        return None
    level = str(judgment.value).strip().lower()
    if level in NEUTRAL_LEVELS:
        return None
    return DOLLAR_LEVEL_PROB_UP.get(level)


class MacroCalibrationRecorder:
    def __init__(self, usd_index: Sequence[Observation], *, horizon: int = 5) -> None:
        self._usd = sorted(usd_index)
        self._horizon = horizon
        self.predictions: list[MacroPrediction] = []

    def record(self, ts: date, judgments: Mapping[str, Judgment]) -> None:
        prob_up = level_prob_up(judgments.get("dollar_strength"))
        if prob_up is None:
            return
        went_up = self._usd_went_up(ts)
        if went_up is None:
            return
        self.predictions.append(MacroPrediction(ts=ts, prob_up=prob_up, went_up=went_up))

    def _usd_went_up(self, ts: date) -> bool | None:
        base_index = next((i for i, (d, _) in enumerate(self._usd) if d >= ts), None)
        if base_index is None:
            return None
        future_index = base_index + self._horizon
        if future_index >= len(self._usd):
            return None
        return self._usd[future_index][1] > self._usd[base_index][1]


def build_macro_calibration(predictions: Sequence[MacroPrediction]) -> MacroCalibration:
    return MacroCalibration(
        n=len(predictions),
        brier=brier_score(predictions),
        ece=expected_calibration_error(predictions),
        table=calibration_table(predictions),
    )


def run_macro_calibration(
    series: Mapping[str, Sequence[Observation]],
    judge: JudgmentModel,
    *,
    start: date,
    end: date,
    horizon: int = 5,
    step: int = 5,
    questions: dict | None = None,
) -> tuple[MacroCalibration, list[MacroPrediction]]:
    """Walk a window, judge each day's macro snapshot, and score the dollar view."""
    questions = questions or MACRO_QUESTIONS
    recorder = MacroCalibrationRecorder(series.get("usd_index", ()), horizon=horizon)
    day = start
    while day <= end:
        snapshot = build_macro_snapshot(series, as_of=day)
        recorder.record(day, judge.judge(snapshot.to_dict(), questions))
        day += timedelta(days=step)
    return build_macro_calibration(recorder.predictions), recorder.predictions
