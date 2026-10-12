"""CLI parser tests (no network)."""

from __future__ import annotations

from cadence_core.cli import build_parser, main


def test_parser_has_expected_commands():
    parser = build_parser()
    for command in ("doctor", "probe", "macro-digest", "macro-calibrate", "macro-report"):
        args = parser.parse_args([command])
        assert args.command == command
        assert callable(args.func)


def test_calibrate_defaults():
    args = build_parser().parse_args(["macro-calibrate"])
    assert args.judge == "rules"
    assert args.horizon == 5
    assert args.step == 5


def test_doctor_check_gdelt_flag():
    args = build_parser().parse_args(["doctor", "--check-gdelt"])
    assert args.check_gdelt is True


def test_main_returns_int_for_bad_config(monkeypatch):
    monkeypatch.setenv("GDELT_MIN_INTERVAL", "not-a-number")
    assert isinstance(main(["macro-digest", "--no-news"]), int)
