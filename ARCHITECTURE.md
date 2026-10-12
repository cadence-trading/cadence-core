# Architecture

`cadence-core` is the asset-agnostic layer of the Cadence platform. The asset-class
repos (stocks, crypto) depend on it for the judgment, calibration, context and macro
pieces; they own only their data providers and strategies.

```
                 ┌──────────────────────── cadence-core ────────────────────────┐
   macro data ─▶ │ macro.sources (FRED/ECB)  ─┐                                 │
   news       ─▶ │ macro.news (RSS + GDELT)  ─┼─▶ macro.snapshot (code only)   │
                 │                            │        │                        │
                 │                            │        ▼                        │
                 │                            │   macro.provider ──▶ context.digest
                 │                            │        │                        │
                 │                            │        ▼                        │
                 │   judgment.jev (choice/score/noul) ◀─ macro.questions         │
                 │        │                                                      │
                 │        ▼                                                      │
                 │   macro.calibration (reuses calibration.Brier/ECE)            │
                 └──────────────────────────────────────────────────────────────┘
                                        │
                    consumed by asset-class strategies via ContextProvider /
                    JudgmentModel — no strategy changes required.
```

## Boundaries

- **Code computes; the model judges.** `macro.snapshot` derives every number from
  dated observations; the model only answers fuzzy, typed questions. This keeps
  prompts reproducible and the math auditable.
- **The network is one seam.** `data.fetcher.Fetcher` is the only place the macro
  layer touches the wire, so tests inject a fake `get_text` and run fully offline.
- **Honesty is structural.** The report renderer requires a calibration object; the
  snapshot is look-ahead-free; news is excluded from calibration.

## Data flow for one decision

1. `MacroContextProvider.items(symbols, day, day)` builds a `MacroSnapshot` as of `day`
   (look-ahead-free) and, optionally, news items filtered to the window.
2. `context.digest.build_digest` condenses the items into a token-budgeted block.
3. The judgment model answers `macro.questions` (Jev or the rule comparator).
4. `macro.calibration` maps the `dollar_strength` score to a probability and scores it
   against the realized USD index (Brier/ECE).

## Why GDELT is flanked, not primary

GDELT DOC 2.0 allows one request every five seconds and returns a non-JSON notice when
exceeded (and can block an IP for longer). It is therefore used only for a coverage
signal, strictly throttled and cached, with a graceful fallback to the official RSS
feeds. The engine never depends on GDELT being reachable.
