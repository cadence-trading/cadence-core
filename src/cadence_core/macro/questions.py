"""The shared macro judgment questions (typed for the Jev primitives).

One question set serves every judgment model: the offline ``MacroRuleJudge`` keys
on the question *names*, while ``JevAdapter`` sends the typed ``choice``/``score``/
``noul`` objects to Jev. These are deliberately *macro* questions — fresh inputs a
price-only model cannot derive — which is where a calibrated judgment adds value.
"""

from __future__ import annotations

from cadence_core.judgment.jev import choice, noul, score

# Ordered from "USD falls" to "USD rises"; the anchor probabilities live in
# macro.calibration so the score is directly calibratable.
DOLLAR_LEVELS: tuple[str, ...] = (
    "much weaker",
    "weaker",
    "unchanged",
    "stronger",
    "much stronger",
)

REGIME_OPTIONS: dict[str, str] = {
    "risk_on": "risk appetite is improving",
    "neutral": "mixed / unclear",
    "risk_off": "risk aversion is rising",
}

MACRO_QUESTIONS: dict[str, dict] = {
    "regime": choice(
        "Is the global macro backdrop risk-on, risk-off or neutral for risk assets?",
        REGIME_OPTIONS,
    ),
    "dollar_strength": score(
        "Over the next week, where is the broad US dollar index headed?",
        list(DOLLAR_LEVELS),
    ),
    "policy_surprise": noul(
        "Has a major central bank delivered a hawkish surprise since the previous bar?"
    ),
}
