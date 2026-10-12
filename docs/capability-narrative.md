# Capability narrative

A 2-minute read for a technical evaluator (a hiring manager, a client, a peer).

## One-liner

An **asset-agnostic core** for a trading platform: a **calibrated AI judgment layer
(Jev)**, Brier/ECE calibration, a deterministic context digest, and a **macro context
engine** that turns keyless macro data (FRED + ECB) and official news into a macro view
that is *measured* rather than asserted — built from scratch in dependency-light
Python, with honesty enforced in code rather than promised in a README.

## What I built

The shared spine of the Cadence platform, plus its first real module — the macro
context engine:

```
Macro data (FRED/ECB, keyless) ─┐
                                ├─▶ deterministic MacroSnapshot ─▶ ContextProvider ─▶ digest
News (official RSS + GDELT)    ─┘                                        │
                                                                          ▼
                          Judgment (Jev: choice/score/noul) ◀─ macro questions
                                        │
                                        ▼
                          Calibration (Brier / ECE vs realized USD index)
```

- **Judgment layer** — a pluggable model. **Jev** (TypeSafe "System One") returns
  *typed, calibrated* decisions — `choice`, `score`, `noul` — instead of text; a
  deterministic rule judge is the offline comparator.
- **Calibration** — Brier score and Expected Calibration Error, reusing one small
  math module for both price-direction and macro judgments.
- **Data layer** — standard-library HTTP with an on-disk cache and a rate limiter; no
  vendor SDK.
- **Macro engine** — deterministic snapshot (rate differential, inflation, USD index
  momentum, realized FX vol), typed macro questions, and a calibration harness whose
  outcome is the realized broad US dollar index.
- **News context** — official central-bank/statistics RSS as the primary source,
  GDELT as a strictly throttled flank with a graceful fallback.

## Key engineering decisions

1. **Code computes, the model judges.** Every number is derived in code from dated
   observations; the model only answers fuzzy, typed questions. Prompts are
   reproducible because the digest is a pure function of its inputs.
2. **Honesty is structural.** A macro report *cannot* be produced without a
   calibration section; with no scored predictions it says so explicitly. The
   snapshot is look-ahead-free. News never enters a calibration claim.
3. **The offline comparator is always present.** If the rule judge scores as well as
   the model, the model is not adding value — and the numbers say so.
4. **Keyless where possible.** The macro backbone needs no API key: FRED and ECB are
   fetched from their public CSV endpoints, verified end-to-end.

## What it is not

- **Not a forecast.** FX and rates are priced in within seconds; a model that reads
  the news is structurally behind the market. This is context and explanation.
- **Not a trading system.** It moves no money and emits no orders.
- **Not a black box.** Pure Python, no pandas/numpy/LLM SDK; the whole stack is
  auditable and testable offline (network is injected).

## How to verify yourself

```bash
uv run --group dev pytest -q                       # 47 tests, all offline
uv run python -m cadence_core.cli doctor           # live: probe the keyless sources
uv run python -m cadence_core.cli macro-calibrate  # Brier/ECE of the dollar view
uv run python -m cadence_core.cli macro-report     # a full, honest Markdown report
```

The first `macro-calibrate` run against the offline rule judge returns a **poorly
calibrated** dollar view (Brier ≈ 0.35, worse than a coin flip) — and reports it. That
is the point: the engine measures the view and publishes the result, good or bad.
