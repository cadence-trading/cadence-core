"""Command-line entry point for the macro context engine.

Commands:
  * ``doctor``          — verify settings and the keyless macro sources (FRED/ECB) + GDELT.
  * ``probe``           — send a live macro snapshot + typed questions to Jev.
  * ``macro-digest``    — print the current macro snapshot and the news digest.
  * ``macro-calibrate`` — score the dollar view over a window (Brier/ECE).
  * ``macro-report``    — write a publishable, honest Markdown macro report.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from datetime import date, timedelta

from cadence_core.config import ConfigError, Settings, load_settings
from cadence_core.context.digest import build_digest
from cadence_core.data.base import DataError
from cadence_core.data.cache import HttpCache, RateLimiter
from cadence_core.data.fetcher import Fetcher
from cadence_core.judgment.base import JudgmentModel
from cadence_core.judgment.jev import JevAdapter, JevClient, JevError
from cadence_core.macro.calibration import run_macro_calibration
from cadence_core.macro.news import GdeltClient, MacroNewsProvider
from cadence_core.macro.provider import MacroContextProvider
from cadence_core.macro.questions import MACRO_QUESTIONS
from cadence_core.macro.report import MacroReportContext, render_macro_report
from cadence_core.macro.rules import MacroRuleJudge
from cadence_core.macro.snapshot import build_macro_snapshot
from cadence_core.macro.sources import DEFAULT_SERIES, load_series


def _macro_fetcher(settings: Settings) -> Fetcher:
    return Fetcher(
        cache=HttpCache(settings.cache_dir),
        timeout=settings.http_timeout,
        user_agent=settings.user_agent,
    )


def _gdelt_fetcher(settings: Settings) -> Fetcher:
    return Fetcher(
        cache=HttpCache(settings.cache_dir),
        limiter=RateLimiter(settings.gdelt_min_interval),
        timeout=settings.http_timeout,
        user_agent=settings.user_agent,
    )


def _build_judge(name: str, settings: Settings) -> JudgmentModel:
    key = name.strip().lower()
    if key == "rules":
        return MacroRuleJudge()
    if key == "jev":
        return JevAdapter(JevClient(settings))
    raise ConfigError(f"unknown judge {name!r}; choose rules or jev")


def _load_series_map(fetcher: Fetcher) -> tuple[dict, list[str]]:
    """Load every series, tolerating individual failures (report them)."""
    loaded: dict[str, list] = {}
    failed: list[str] = []
    for spec in DEFAULT_SERIES:
        try:
            loaded[spec.name] = load_series(spec, fetcher)
        except DataError as exc:
            failed.append(f"{spec.name} ({exc})")
    return loaded, failed


def cmd_doctor(args: argparse.Namespace) -> int:
    try:
        settings = load_settings()
    except ConfigError as exc:
        print(f"[FAIL] invalid configuration: {exc}")
        return 1

    print("Cadence :: macro doctor")
    print(f"  cache dir        = {settings.cache_dir}")
    print(f"  http timeout     = {settings.http_timeout}s")
    print(f"  GDELT min gap    = {settings.gdelt_min_interval}s")
    print(f"  JEV key set      = {bool(settings.jev_api_key)}")
    print()

    ok = True
    fetcher = _macro_fetcher(settings)
    for spec in DEFAULT_SERIES:
        try:
            rows = load_series(spec, fetcher)
        except DataError as exc:
            print(f"  [FAIL] {spec.source:<4} {spec.name:<10} {exc}")
            ok = False
        else:
            last = rows[-1]
            print(f"  [OK]   {spec.source:<4} {spec.name:<10} {len(rows)} obs, last {last[0]}")

    if args.check_gdelt:
        gdelt = GdeltClient(_gdelt_fetcher(settings))
        try:
            coverage = gdelt.coverage("central bank OR inflation")
        except DataError as exc:
            print(f"  [DEGRADED] gdelt: {exc}")
        else:
            print(f"  [OK]   gdelt: {len(coverage)} points")

    return 0 if ok else 1


def cmd_probe(args: argparse.Namespace) -> int:
    settings = load_settings()
    fetcher = _macro_fetcher(settings)
    loaded, failed = _load_series_map(fetcher)
    for note in failed:
        print(f"[WARN] missing series: {note}")
    snapshot = build_macro_snapshot(loaded, as_of=date.today())

    adapter = JevAdapter(JevClient(settings))
    print("Cadence :: macro probe")
    print(f"  model = {settings.jev_model} @ {settings.jev_base_url}")
    print(f"  state = {snapshot.summary()}")
    print()
    try:
        judgments = adapter.judge(snapshot.to_dict(), MACRO_QUESTIONS)
    except JevError as exc:
        print(f"[FAIL] {exc}")
        return 1

    print(f"  {'question':<18}{'value':<16}{'confidence':>11}")
    print(f"  {'-' * 18}{'-' * 16}{'-' * 11}")
    for name in MACRO_QUESTIONS:
        j = judgments.get(name)
        if j is None:
            print(f"  {name:<18}{'n/a':<16}{'n/a':>11}")
        else:
            print(f"  {name:<18}{j.value:<16}{j.confidence:>11.2f}")
    return 0


def cmd_macro_digest(args: argparse.Namespace) -> int:
    settings = load_settings()
    fetcher = _macro_fetcher(settings)
    loaded, failed = _load_series_map(fetcher)
    for note in failed:
        print(f"[WARN] missing series: {note}")

    provider = MacroContextProvider(loaded)
    if not args.no_news:
        provider = MacroContextProvider(
            loaded,
            news=MacroNewsProvider(
                fetcher=_macro_fetcher(settings),
                gdelt=GdeltClient(_gdelt_fetcher(settings)),
                allow_gdelt=not args.no_gdelt,
            ),
        )

    today = date.today()
    items = provider.items(symbols=["MACRO"], start=today - timedelta(days=2), end=today)
    print("Cadence :: macro digest")
    print()
    print(build_digest(items))
    return 0


def cmd_macro_calibrate(args: argparse.Namespace) -> int:
    settings = load_settings()
    fetcher = _macro_fetcher(settings)
    loaded, failed = _load_series_map(fetcher)
    for note in failed:
        print(f"[WARN] missing series: {note}")
    if "usd_index" not in loaded:
        print("[FAIL] usd_index series unavailable; cannot calibrate")
        return 1

    end = date.fromisoformat(args.end) if args.end else date.today()
    start = date.fromisoformat(args.start) if args.start else end - timedelta(days=args.days)

    judge = _build_judge(args.judge, settings)
    try:
        calibration, _ = run_macro_calibration(
            loaded, judge, start=start, end=end, horizon=args.horizon, step=args.step
        )
    except JevError as exc:
        print(f"[FAIL] {exc}")
        return 1

    print("Cadence :: macro-calibrate")
    print(f"  judge   = {args.judge}")
    print(f"  window  = {start} → {end} (step {args.step}, horizon {args.horizon})")
    print(f"  n preds = {calibration.n}")
    print(f"  brier   = {'n/a' if calibration.brier is None else f'{calibration.brier:.3f}'}")
    print(f"  ECE     = {'n/a' if calibration.ece is None else f'{calibration.ece:.3f}'}")
    print()
    print(f"  {'bin':<14}{'count':>7}{'avg prob':>11}{'empirical':>11}")
    print(f"  {'-' * 14}{'-' * 7}{'-' * 11}{'-' * 11}")
    for row in calibration.table:
        print(
            f"  {row['bin_lower']:.1f}-{row['bin_upper']:.1f}"
            f"{row['count']:>11}{row['avg_prob']:>11.2f}{row['empirical']:>11.2f}"
        )
    return 0


def cmd_macro_report(args: argparse.Namespace) -> int:
    settings = load_settings()
    fetcher = _macro_fetcher(settings)
    loaded, failed = _load_series_map(fetcher)
    for note in failed:
        print(f"[WARN] missing series: {note}")
    if "usd_index" not in loaded:
        print("[FAIL] usd_index series unavailable; cannot calibrate")
        return 1

    today = date.today()
    end = date.fromisoformat(args.end) if args.end else today
    start = date.fromisoformat(args.start) if args.start else end - timedelta(days=args.days)
    judge_name = args.judge
    judge = _build_judge(judge_name, settings)
    try:
        calibration, _ = run_macro_calibration(
            loaded, judge, start=start, end=end, horizon=args.horizon, step=args.step
        )
    except JevError as exc:
        print(f"[FAIL] {exc}")
        return 1

    news_items = []
    if not args.no_news:
        news = MacroNewsProvider(
            fetcher=_macro_fetcher(settings),
            gdelt=GdeltClient(_gdelt_fetcher(settings)),
            allow_gdelt=not args.no_gdelt,
        )
        news_items = news.items(["MACRO"], today - timedelta(days=7), today)
        for note in news.degraded:
            print(f"[DEGRADED] {note}")

    snapshot = build_macro_snapshot(loaded, as_of=end)
    markdown = render_macro_report(
        snapshot=snapshot,
        calibration=calibration,
        news_items=news_items,
        context=MacroReportContext(
            title=args.title,
            generated=today,
            judge=judge_name,
            window_start=start,
            window_end=end,
            horizon=args.horizon,
        ),
    )

    from pathlib import Path

    out = Path(args.out) if args.out else Path("var/reports") / f"{today:%Y%m%d}_macro.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(markdown, encoding="utf-8")
    print(f"wrote {out}")
    return 0


def _add_window_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--start", default=None, help="ISO start date (inclusive)")
    p.add_argument("--end", default=None, help="ISO end date (inclusive)")
    p.add_argument("--days", type=int, default=730, help="window length if --start is omitted")
    p.add_argument("--step", type=int, default=5, help="calendar-day step between decisions")
    p.add_argument("--horizon", type=int, default=5, help="forward observations for the outcome")
    p.add_argument("--judge", default="rules", choices=["rules", "jev"])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cadence-core")
    sub = parser.add_subparsers(dest="command", required=True)

    doctor = sub.add_parser("doctor", help="verify settings and the keyless macro sources")
    doctor.add_argument("--check-gdelt", action="store_true", help="also probe GDELT")
    doctor.set_defaults(func=cmd_doctor)

    probe = sub.add_parser("probe", help="send a live macro snapshot + questions to Jev")
    probe.set_defaults(func=cmd_probe)

    digest = sub.add_parser("macro-digest", help="print the macro snapshot and news digest")
    digest.add_argument("--no-news", action="store_true", help="skip the news layer")
    digest.add_argument("--no-gdelt", action="store_true", help="skip the GDELT flank")
    digest.set_defaults(func=cmd_macro_digest)

    calibrate = sub.add_parser("macro-calibrate", help="score the dollar view (Brier/ECE)")
    _add_window_args(calibrate)
    calibrate.set_defaults(func=cmd_macro_calibrate)

    report = sub.add_parser("macro-report", help="write an honest Markdown macro report")
    _add_window_args(report)
    report.add_argument("--out", default=None, help="output markdown path")
    report.add_argument("--title", default="Cadence — macro context report")
    report.add_argument("--no-news", action="store_true", help="skip the news layer")
    report.add_argument("--no-gdelt", action="store_true", help="skip the GDELT flank")
    report.set_defaults(func=cmd_macro_report)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except ConfigError as exc:
        print(f"[FAIL] invalid configuration: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
