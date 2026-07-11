from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol

from .models import FilterDecision, WalletTokenContext


class Filter(Protocol):
    def __call__(self, token: WalletTokenContext) -> FilterDecision: ...


class ExcludeTagsFilter:
    def __init__(self, excluded_tags: set[str]) -> None:
        self._excluded = excluded_tags

    def __call__(self, token: WalletTokenContext) -> FilterDecision:
        if token.metadata is None:
            return FilterDecision(keep=False, reason="missing_metadata")
        matched = self._excluded & set(token.metadata.tags)
        if matched:
            return FilterDecision(keep=False, reason=f"excluded tags: {sorted(matched)}")
        return FilterDecision(keep=True)


class IncludeTagsFilter:
    """Keep only tokens that have at least one of the required tags."""

    def __init__(self, required_tags: set[str]) -> None:
        self._required = required_tags

    def __call__(self, token: WalletTokenContext) -> FilterDecision:
        if token.metadata is None:
            return FilterDecision(keep=False, reason="missing_metadata")
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

    def __call__(self, token: WalletTokenContext) -> FilterDecision:
        if token.metadata is None:
            return FilterDecision(keep=False, reason="missing_metadata")

        end_ts = token.metadata.end_ts
        if end_ts is None:
            return FilterDecision(keep=True)

        now = self._now or datetime.now(tz=timezone.utc)
        if end_ts.tzinfo is None:
            end_ts = end_ts.replace(tzinfo=timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        if end_ts > now:
            return FilterDecision(keep=True)
        return FilterDecision(keep=False, reason=f"market ended at {end_ts.isoformat()}")


class MinWalletTradesFilter:
    def __init__(self, min_trades: int) -> None:
        self._min = min_trades

    def __call__(self, token: WalletTokenContext) -> FilterDecision:
        count = token.wallet_stats.wallet_trades_count
        if count >= self._min:
            return FilterDecision(keep=True)
        return FilterDecision(
            keep=False,
            reason=f"only {count} wallet trades, need >= {self._min}",
        )


class MinMarketTradesFilter:
    def __init__(self, min_trades: int) -> None:
        self._min = min_trades

    def __call__(self, token: WalletTokenContext) -> FilterDecision:
        if token.market_stats is None:
            return FilterDecision(keep=False, reason="missing_market_stats")
        count = token.market_stats.market_trades_count
        if count >= self._min:
            return FilterDecision(keep=True)
        return FilterDecision(
            keep=False,
            reason=f"only {count} market trades, need >= {self._min}",
        )


class MinMarketVolumeFilter:
    def __init__(self, min_volume: int) -> None:
        self._min = min_volume

    def __call__(self, token: WalletTokenContext) -> FilterDecision:
        if token.market_stats is None:
            return FilterDecision(keep=False, reason="missing_market_stats")
        vol = token.market_stats.market_volume
        if vol >= self._min:
            return FilterDecision(keep=True)
        return FilterDecision(
            keep=False,
            reason=f"market volume {vol} < {self._min}",
        )


# Canonical mapping: raw outcome (lowercased) → "yes" | "no"
# Up/Down are directional aliases used on some Polymarket markets.
_BINARY_OUTCOME_MAP: dict[str, str] = {
    "yes": "yes",
    "no": "no",
    "up": "yes",
    "down": "no",
}


def normalize_binary_outcome(outcome: str) -> str | None:
    """Return 'yes' or 'no' for any recognised binary outcome, else None."""
    return _BINARY_OUTCOME_MAP.get(outcome.strip().lower())


class BinaryOutcomeFilter:
    """Keep only tokens with a recognised binary outcome (Yes/No/Up/Down)."""

    def __call__(self, token: WalletTokenContext) -> FilterDecision:
        if token.metadata is None:
            return FilterDecision(keep=False, reason="missing_metadata")
        if normalize_binary_outcome(token.metadata.outcome) is not None:
            return FilterDecision(keep=True)
        return FilterDecision(
            keep=False,
            reason=f"non-binary outcome: '{token.metadata.outcome}'",
        )
