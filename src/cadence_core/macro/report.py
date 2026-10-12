"""Honest macro report.

Honesty invariant (enforced in code): a macro report *cannot* be produced without
a calibration section. If there are no scored predictions, the report states that
explicitly instead of implying a track record. Every report repeats, verbatim, that
this is context/explanation — not a forecast.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from cadence_core.context.base import ContextItem
from cadence_core.macro.calibration import MacroCalibration
from cadence_core.macro.snapshot import MacroSnapshot

NOT_A_PREDICTION = (
    "This is macro **context and explanation, not a forecast**. FX and rates are "
    "driven by information that is priced in within seconds; a model that reads the "
    "news is structurally behind the market. The value here is a *calibrated* macro "
    "view and an auditable rationale — not a price prediction."
)


@dataclass(frozen=True)
class MacroReportContext:
    title: str
    generated: date
    judge: str
    window_start: date | None
    window_end: date | None
    horizon: int
    data_source: str = "FRED + ECB (keyless)"


def render_macro_report(
    *,
    snapshot: MacroSnapshot,
    calibration: MacroCalibration,
    news_items: list[ContextItem],
    context: MacroReportContext,
) -> str:
    lines: list[str] = []
    lines.append(f"# {context.title}")
    lines.append("")
    lines.append(f"> {NOT_A_PREDICTION}")
    lines.append("")
    lines.append(f"- Generated: {context.generated.isoformat()}")
    lines.append(f"- Judge: `{context.judge}`")
    lines.append(f"- Data source: {context.data_source}")
    if context.window_start and context.window_end:
        lines.append(
            f"- Calibration window: {context.window_start.isoformat()} → "
            f"{context.window_end.isoformat()} (horizon {context.horizon} obs)"
        )
    lines.append("")

    lines.append("## Current macro snapshot")
    lines.append("")
    lines.append(f"_{snapshot.summary()}_")
    lines.append("")
    lines.append("| field | value |")
    lines.append("|---|---|")
    for key, value in snapshot.to_dict().items():
        lines.append(f"| {key} | {value} |")
    lines.append("")

    lines.append("## Calibration of the dollar view")
    lines.append("")
    if calibration.n == 0:
        lines.append(
            "**No calibration data — no calibration claim is made.** "
            "There were no scored predictions in the window (neutral views and "
            "insufficient forward data are excluded)."
        )
        lines.append("")
    else:
        brier = "n/a" if calibration.brier is None else f"{calibration.brier:.3f}"
        ece = "n/a" if calibration.ece is None else f"{calibration.ece:.3f}"
        lines.append(f"- Predictions scored: **{calibration.n}**")
        lines.append(f"- Brier score: **{brier}** (lower is better; 0.25 = coin flip)")
        lines.append(f"- Expected calibration error: **{ece}**")
        lines.append("")
        lines.append("| bin | count | avg prob | empirical |")
        lines.append("|---|---|---|---|")
        for row in calibration.table:
            lines.append(
                f"| {row['bin_lower']:.1f}–{row['bin_upper']:.1f} | {row['count']} | "
                f"{row['avg_prob']:.2f} | {row['empirical']:.2f} |"
            )
        lines.append("")

    lines.append("## News context (official feeds, live)")
    lines.append("")
    if news_items:
        for item in news_items[:20]:
            published = item.published.isoformat() if item.published else "—"
            lines.append(f"- `{published}` [{item.source}] {item.title}")
    else:
        lines.append("_No news items retrieved._")
    lines.append("")

    lines.append("## Method")
    lines.append("")
    lines.append(
        "- All numbers are computed in code from dated observations; the model only "
        "answers fuzzy, typed questions."
    )
    lines.append(
        "- The snapshot is look-ahead-free: it only uses observations dated on or "
        "before the report date."
    )
    lines.append(
        "- The calibration outcome is the realized broad US dollar index "
        "(`DTWEXBGS`); news never enters a calibration claim."
    )
    lines.append("")
    return "\n".join(lines)
