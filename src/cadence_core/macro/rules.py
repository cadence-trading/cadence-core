"""Deterministic offline macro judgment model.

A transparent, rule-based judge that reads the same macro snapshot as the AI model
and answers the same questions. It is the offline fallback (no key, CI-safe) and a
comparator that keeps the pipeline honest: if the rules score as well as the model,
the model is not adding value.
"""

from __future__ import annotations

from cadence_core.judgment.base import Judgment, JudgmentModel
from cadence_core.macro.questions import DOLLAR_LEVELS

HIGH_VOL = 0.15


class MacroRuleJudge(JudgmentModel):
    def judge(self, snapshot: dict, questions: dict) -> dict[str, Judgment]:
        score = _dollar_score(snapshot)
        level = DOLLAR_LEVELS[score + 2]
        dollar_conf = min(0.5 + 0.15 * abs(score), 0.9)

        result: dict[str, Judgment] = {}
        for name in questions:
            if name == "dollar_strength":
                result[name] = Judgment(
                    name=name,
                    value=level,
                    confidence=dollar_conf,
                    rationale=f"rule score {score:+d} from rate differential and USD momentum",
                )
            elif name == "regime":
                regime, regime_conf = _regime(snapshot)
                result[name] = Judgment(
                    name=name,
                    value=regime,
                    confidence=regime_conf,
                    rationale="rule regime from realized vol and USD momentum",
                )
            elif name == "policy_surprise":
                prob = _policy_surprise(snapshot)
                result[name] = Judgment(
                    name=name,
                    value=f"{prob:.2f}",
                    confidence=prob,
                    rationale="rule baseline for a hawkish surprise",
                )
        return result


def _dollar_score(snapshot: dict) -> int:
    score = 0
    rate_diff = snapshot.get("rate_diff")
    if isinstance(rate_diff, (int, float)):
        score += 1 if rate_diff > 0 else -1 if rate_diff < 0 else 0
    for key in ("usd_momentum_20d", "usd_momentum_5d"):
        value = snapshot.get(key)
        if isinstance(value, (int, float)):
            score += 1 if value > 0 else -1 if value < 0 else 0
    return max(-2, min(2, score))


def _regime(snapshot: dict) -> tuple[str, float]:
    vol = snapshot.get("realized_vol")
    momentum = snapshot.get("usd_momentum_20d")
    if isinstance(vol, (int, float)) and vol >= HIGH_VOL:
        return "risk_off", 0.7
    if isinstance(momentum, (int, float)) and momentum < 0 and (
        not isinstance(vol, (int, float)) or vol < HIGH_VOL
    ):
        return "risk_on", 0.6
    return "neutral", 0.5


def _policy_surprise(snapshot: dict) -> float:
    momentum = snapshot.get("usd_momentum_20d")
    if isinstance(momentum, (int, float)) and momentum > 0.01:
        return 0.6
    if isinstance(momentum, (int, float)) and momentum < -0.01:
        return 0.4
    return 0.5
