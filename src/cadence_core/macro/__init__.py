"""The macro context engine.

Structured macro data (FRED + ECB, keyless) and curated news feed a calibrated
judgment layer. It explains and measures the macro backdrop; it does not predict
prices.
"""

from __future__ import annotations

from cadence_core.macro.calibration import (
    MacroCalibration,
    MacroCalibrationRecorder,
    MacroPrediction,
    build_macro_calibration,
    level_prob_up,
    run_macro_calibration,
)
from cadence_core.macro.news import (
    DEFAULT_THEMES,
    GdeltClient,
    MacroNewsProvider,
    NewsTheme,
    parse_rss,
)
from cadence_core.macro.provider import MacroContextProvider
from cadence_core.macro.questions import DOLLAR_LEVELS, MACRO_QUESTIONS, REGIME_OPTIONS
from cadence_core.macro.report import (
    NOT_A_PREDICTION,
    MacroReportContext,
    render_macro_report,
)
from cadence_core.macro.rules import MacroRuleJudge
from cadence_core.macro.snapshot import MacroSnapshot, build_macro_snapshot
from cadence_core.macro.sources import (
    DEFAULT_SERIES,
    SeriesSpec,
    load_series,
    load_series_map,
    parse_ecb_csv,
    parse_fred_csv,
    series_url,
)

__all__ = [
    "DEFAULT_SERIES",
    "DEFAULT_THEMES",
    "DOLLAR_LEVELS",
    "MACRO_QUESTIONS",
    "NOT_A_PREDICTION",
    "REGIME_OPTIONS",
    "GdeltClient",
    "MacroCalibration",
    "MacroCalibrationRecorder",
    "MacroContextProvider",
    "MacroNewsProvider",
    "MacroPrediction",
    "MacroReportContext",
    "MacroRuleJudge",
    "MacroSnapshot",
    "NewsTheme",
    "SeriesSpec",
    "build_macro_calibration",
    "build_macro_snapshot",
    "level_prob_up",
    "load_series",
    "load_series_map",
    "parse_ecb_csv",
    "parse_fred_csv",
    "parse_rss",
    "render_macro_report",
    "run_macro_calibration",
    "series_url",
]
