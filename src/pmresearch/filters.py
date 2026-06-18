from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol

from .models import EnrichedTradedToken, FilterDecision


class Filter(Protocol):
    def __call__(self, token: EnrichedTradedToken) -> FilterDecision: ...


class ExcludeTagsFilter:
    def __init__(self, excluded_tags: set[str]) -> None:
        self._excluded = excluded_tags

    def __call__(self, token: EnrichedTradedToken) -> FilterDecision:
        matched = self._excluded & set(token.metadata.tags)
        if matched:
            return FilterDecision(keep=False, reason=f"excluded tags: {sorted(matched)}")
        return FilterDecision(keep=True)


class IncludeTagsFilter:
    """Keep only tokens that have at least one of the required tags."""

    def __init__(self, required_tags: set[str]) -> None:
        self._required = required_tags

    def __call__(self, token: EnrichedTradedToken) -> FilterDecision:
        if self._required & set(token.metadata.tags):
            return FilterDecision(keep=True)
        return FilterDecision(
            keep=False,
            reason=f"missing required tags (need any of: {sorted(self._required)})",
        )


class ActiveMarketFilter:
    """Keep tokens whose market hasn't ended yet."""

    def __init__(self, now: datetime | None = None) -> None:
        self._now = now

    def __call__(self, token: EnrichedTradedToken) -> FilterDecision:
        end_ts = token.metadata.end_ts
        if end_ts is None:
            return FilterDecision(keep=True)

        now = self._now or datetime.now(tz=timezone.utc)
        # normalise to UTC-aware for safe comparison
        if end_ts.tzinfo is None:
            end_ts = end_ts.replace(tzinfo=timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        if end_ts > now:
            return FilterDecision(keep=True)
        return FilterDecision(keep=False, reason=f"market ended at {end_ts.isoformat()}")


class MinTradesFilter:
    def __init__(self, min_trades: int) -> None:
        self._min = min_trades

    def __call__(self, token: EnrichedTradedToken) -> FilterDecision:
        if token.traded.trades_count >= self._min:
            return FilterDecision(keep=True)
        return FilterDecision(
            keep=False,
            reason=f"only {token.traded.trades_count} trades, need >= {self._min}",
        )


class BinaryOutcomeFilter:
    """Keep only tokens with a clear Yes/No outcome (case-insensitive)."""

    _VALID = {"yes", "no"}

    def __call__(self, token: EnrichedTradedToken) -> FilterDecision:
        outcome = token.metadata.outcome.strip().lower()
        if outcome in self._VALID:
            return FilterDecision(keep=True)
        return FilterDecision(
            keep=False,
            reason=f"non-binary outcome: '{token.metadata.outcome}'",
        )
