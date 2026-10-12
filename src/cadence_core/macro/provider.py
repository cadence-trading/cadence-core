"""Macro context provider.

Implements the shared ``ContextProvider`` contract, so it plugs into any judgment
strategy with **zero changes**: the strategy calls ``items(symbols, day, day)``, the
provider returns the macro snapshot (computed as of that day, look-ahead-free) plus
any news items, and the shared digest turns them into a prompt block.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date

from cadence_core.context.base import ContextItem, ContextProvider
from cadence_core.macro.news import MacroNewsProvider
from cadence_core.macro.snapshot import MacroSnapshot, build_macro_snapshot
from cadence_core.macro.sources import Observation


class MacroContextProvider(ContextProvider):
    def __init__(
        self,
        series: Mapping[str, Sequence[Observation]],
        *,
        news: MacroNewsProvider | None = None,
    ) -> None:
        self._series = series
        self._news = news

    def snapshot(self, as_of: date) -> MacroSnapshot:
        return build_macro_snapshot(self._series, as_of=as_of)

    def items(self, symbols: list[str], start: date, end: date) -> list[ContextItem]:
        snap = self.snapshot(end)
        items = [
            ContextItem(
                source="macro",
                title="Macro snapshot",
                text=snap.summary(),
                published=end,
            )
        ]
        if self._news is not None:
            items.extend(self._news.items(symbols, start, end))
        return items
