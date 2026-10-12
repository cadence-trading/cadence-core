# Cadence core

**Asset-agnostic core for the Cadence trading platform.**

`cadence-core` holds the parts of [Cadence](https://github.com/cadence-trading) that
are the same regardless of asset class: the **calibrated judgment layer (Jev)**, the
**Brier/ECE calibration** math, the **context digest**, a dependency-light HTTP layer
with an on-disk cache and a rate limiter, and a **macro context engine** that turns
keyless macro data (FRED + ECB) and curated news into a calibrated macro view.

It moves no money and makes no price forecasts. The macro engine exists to **explain
and calibrate** the macro backdrop — and to be measured honestly.

> **Not investment advice. No trading. This is context and explanation, not a
> forecast.** See [DISCLAIMER.md](DISCLAIMER.md).

## What the macro engine does

FX and rates are the most macro-driven asset class there is — so "read the global news
first" is not a luxury there, it is the core. But a language model that reads a
headline is *structurally behind the market*: the information is priced in within
seconds. So this engine does not try to predict the rate. It does three honest things:

1. **Structures the macro state** deterministically (rate differential, inflation,
   USD index and its momentum, realized FX vol) — all arithmetic in code.
2. **Asks a calibrated model (Jev)** typed macro questions — `choice` (risk-on /
   neutral / risk-off), `score` (dollar strength), `noul` (hawkish surprise?) —
   and records the rationale.
3. **Measures whether that view is calibrated** (Brier / ECE) against the realized
   USD index. If it is not calibrated, the number says so.

It plugs into any judgment strategy with **zero changes**: `MacroContextProvider`
implements the shared `ContextProvider` contract, so the strategy just calls
`items(symbols, day, day)` and gets a look-ahead-free macro digest.

## Keyless by design

The macro backbone needs **no API key**:

| Source | Endpoint | Used for |
|---|---|---|
| **FRED** | `fred.stlouisfed.org/graph/fredgraph.csv?id=<ID>` | USD index, rates, CPI, HICP |
| **ECB** | `data-api.ecb.europa.eu/service/data/<KEY>?format=csvdata` | EUR/USD reference rate |
| **Official RSS** | ECB / Federal Reserve press feeds | primary news context |
| **GDELT** | `api.gdeltproject.org/api/v2/doc/doc` | flanking coverage-volume signal |

GDELT allows one request every 5 seconds and blocks aggressively; the provider
**throttles, caches, and degrades to RSS** rather than failing.

## Quick start

```bash
# Requires uv (https://docs.astral.sh/uv/)
uv run --group dev pytest -q                       # all tests, offline
uv run python -m cadence_core.cli doctor           # probe the keyless sources
uv run python -m cadence_core.cli macro-calibrate  # Brier/ECE of the dollar view
uv run python -m cadence_core.cli macro-report     # write an honest Markdown report
```

To exercise the Jev judgment layer you need an API key (route re-evaluated
periodically — OpenRouter or direct):

```bash
export JEV_API_KEY=...
uv run python -m cadence_core.cli probe            # live macro snapshot -> typed judgments
uv run python -m cadence_core.cli macro-calibrate --judge jev
```

## Layout

```
src/cadence_core/
  config.py          settings (Jev route, cache, GDELT throttle)
  calibration.py     Brier score, ECE, calibration table
  data/              stdlib HTTP + on-disk cache + rate limiter
  context/           ContextItem + deterministic digest
  judgment/          Judgment interface + Jev client/adapter (choice/score/noul)
  macro/             sources · snapshot · news · questions · provider · calibration · report
  cli.py             doctor · probe · macro-digest · macro-calibrate · macro-report
tests/               all offline (network is injected)
```

## Honesty invariants (enforced in code)

- A macro report **cannot** be produced without a calibration section; with no scored
  predictions it states "no calibration claim is made" instead of implying a record.
- The macro snapshot is **look-ahead-free**: only observations dated on or before the
  report date are used.
- The calibration outcome is the realized USD index — **news never enters a
  calibration claim** (it cannot be backtested reliably).
- The offline rule judge is always the comparator: if the rules score as well as the
  model, the model is not adding value.

## Licence

MIT — see [LICENSE](LICENSE).
