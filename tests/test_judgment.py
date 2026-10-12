"""Judgment layer tests: Jev primitives, adapter parsing, macro rule judge."""

from __future__ import annotations

import pytest

from cadence_core.judgment.base import Judgment
from cadence_core.judgment.jev import (
    JevAdapter,
    JevUnavailableError,
    choice,
    noul,
    score,
)
from cadence_core.macro.questions import MACRO_QUESTIONS
from cadence_core.macro.rules import MacroRuleJudge


def test_question_primitives():
    assert choice("q", {"a": "x"})["type"] == "choice"
    assert score("q", ["low", "high"])["levels"] == ["low", "high"]
    assert noul("s")["type"] == "noul"


def test_adapter_requires_client_or_predict():
    with pytest.raises(JevUnavailableError):
        JevAdapter().judge({}, MACRO_QUESTIONS)


def test_adapter_with_injected_predict():
    def predict(snapshot, questions):
        return {name: Judgment(name, "neutral", 0.5) for name in questions}

    judgments = JevAdapter(predict=predict).judge({}, MACRO_QUESTIONS)
    assert set(judgments) == set(MACRO_QUESTIONS)


def test_adapter_parses_raw_answers():
    client = JevAdapter.__new__(JevAdapter)  # bypass __init__ for a stub client
    from cadence_core.judgment.jev import _to_judgment

    q = choice("q", {"up": "a", "down": "b"})
    j = _to_judgment("regime", q, {"choice": "risk_on", "confidence": 0.8})
    assert j.value == "risk_on"
    assert j.confidence == pytest.approx(0.8)
    assert client is not None


def test_rule_judge_answers_all_questions():
    snapshot = {
        "rate_diff": 2.0,
        "usd_momentum_20d": 0.02,
        "usd_momentum_5d": 0.01,
        "realized_vol": 0.05,
    }
    judgments = MacroRuleJudge().judge(snapshot, MACRO_QUESTIONS)
    assert judgments["dollar_strength"].value == "much stronger"
    assert judgments["regime"].value in {"risk_on", "neutral", "risk_off"}
    assert 0.0 <= judgments["policy_surprise"].confidence <= 1.0


def test_rule_judge_weak_dollar():
    snapshot = {"rate_diff": -1.0, "usd_momentum_20d": -0.02, "usd_momentum_5d": -0.01}
    judgments = MacroRuleJudge().judge(snapshot, MACRO_QUESTIONS)
    assert judgments["dollar_strength"].value == "much weaker"
