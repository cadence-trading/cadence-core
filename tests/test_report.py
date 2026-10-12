"""Report tests: the honesty invariant must hold in code."""

from __future__ import annotations

from datetime import date

from cadence_core.context.base import ContextItem
from cadence_core.macro.calibration import build_macro_calibration
from cadence_core.macro.report import (
    NOT_A_PREDICTION,
    MacroReportContext,
    render_macro_report,
)
from cadence_core.macro.snapshot import build_macro_snapshot
from tests.helpers import series


def _snapshot():
    return build_macro_snapshot(
        {
            "usd_index": series([100.0 + i for i in range(40)]),
            "us_rate": series([4.0] * 40),
            "eu_rate": series([2.0] * 40),
        },
        as_of=date(2023, 2, 9),
    )


def _context():
    return MacroReportContext(
        title="Cadence — macro context report",
        generated=date(2026, 10, 12),
        judge="rules",
        window_start=date(2024, 1, 1),
        window_end=date(2026, 10, 1),
        horizon=5,
    )


def test_report_always_states_not_a_prediction():
    markdown = render_macro_report(
        snapshot=_snapshot(),
        calibration=build_macro_calibration([]),
        news_items=[],
        context=_context(),
    )
    assert NOT_A_PREDICTION in markdown


def test_report_without_calibration_makes_no_claim():
    markdown = render_macro_report(
        snapshot=_snapshot(),
        calibration=build_macro_calibration([]),
        news_items=[],
        context=_context(),
    )
    assert "No calibration data" in markdown
    assert "Brier score" not in markdown


def test_report_with_calibration_reports_brier():
    from cadence_core.macro.calibration import MacroPrediction

    predictions = [
        MacroPrediction(date(2025, 1, 1), 0.75, True),
        MacroPrediction(date(2025, 1, 6), 0.25, False),
    ]
    markdown = render_macro_report(
        snapshot=_snapshot(),
        calibration=build_macro_calibration(predictions),
        news_items=[ContextItem("rss:central_banks", "ECB holds rates", "", published=date(2026, 10, 1))],
        context=_context(),
    )
    assert "Brier score" in markdown
    assert "Predictions scored: **2**" in markdown
    assert "ECB holds rates" in markdown
