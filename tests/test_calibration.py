"""Macro calibration tests (Brier/ECE reuse; USD-index outcome)."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from cadence_core.judgment.base import Judgment
from cadence_core.macro.calibration import (
    MacroCalibrationRecorder,
    build_macro_calibration,
    level_prob_up,
    run_macro_calibration,
)
from cadence_core.macro.rules import MacroRuleJudge
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


def test_level_prob_up_mapping():
    assert level_prob_up(Judgment("dollar_strength", "much stronger", 0.9)) == pytest.approx(0.95)
    assert level_prob_up(Judgment("dollar_strength", "weaker", 0.5)) == pytest.approx(0.25)
    assert level_prob_up(Judgment("dollar_strength", "unchanged", 0.5)) is None
    assert level_prob_up(None) is None


def test_recorder_marks_up_when_usd_rises():
    usd = series([100.0 + i for i in range(20)])
    recorder = MacroCalibrationRecorder(usd, horizon=5)
    recorder.record(usd[0][0], {"dollar_strength": Judgment("dollar_strength", "stronger", 0.75)})
    assert len(recorder.predictions) == 1
    assert recorder.predictions[0].went_up is True


def test_recorder_skips_when_no_future():
    usd = series([100.0 + i for i in range(3)])
    recorder = MacroCalibrationRecorder(usd, horizon=5)
    recorder.record(usd[0][0], {"dollar_strength": Judgment("dollar_strength", "stronger", 0.75)})
    assert recorder.predictions == []


def test_build_calibration_reuses_brier():
    usd = series([100.0 + i for i in range(20)])
    recorder = MacroCalibrationRecorder(usd, horizon=5)
    for day, _ in usd[:5]:
        recorder.record(day, {"dollar_strength": Judgment("dollar_strength", "stronger", 0.75)})
    calibration = build_macro_calibration(recorder.predictions)
    assert calibration.n == len(recorder.predictions)
    assert calibration.brier is not None
    assert 0.0 <= calibration.brier <= 1.0


def test_run_calibration_produces_predictions():
    data = _series_map()
    end = date(2023, 1, 1) + timedelta(days=N - 1)
    start = end - timedelta(days=120)
    calibration, predictions = run_macro_calibration(
        data, MacroRuleJudge(), start=start, end=end, horizon=5, step=5
    )
    assert predictions
    assert calibration.n == len(predictions)
    assert calibration.ece is not None


def test_empty_calibration_is_none():
    calibration = build_macro_calibration([])
    assert calibration.n == 0
    assert calibration.brier is None
    assert calibration.ece is None
