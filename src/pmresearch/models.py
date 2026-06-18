from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class TradedTokenStats:
    token_id: int
    first_trade_ts: datetime
    last_trade_ts: datetime
    trades_count: int
    volume: int
    buy_count: int
    sell_count: int
    last_price: int


@dataclass(frozen=True, slots=True)
class TokenMetadata:
    token_id: int
    outcome: str
    market_id: int | None
    condition_id: str | None
    question: str | None
    slug: str | None
    end_ts: datetime | None
    tags: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EnrichedTradedToken:
    traded: TradedTokenStats
    metadata: TokenMetadata


@dataclass(frozen=True, slots=True)
class TokenPair:
    condition_id: str | None
    market_id: int | None
    question: str | None
    slug: str | None
    end_ts: datetime | None
    tags: tuple[str, ...]
    yes_token_id: int
    no_token_id: int
    wallet_traded_token_id: int
    wallet_traded_outcome: str  # "yes" | "no"


@dataclass(frozen=True, slots=True)
class FilterDecision:
    keep: bool
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class RejectedToken:
    token: EnrichedTradedToken
    reason: str


@dataclass(slots=True)
class SelectionResult:
    selected: list[EnrichedTradedToken]
    rejected: list[RejectedToken]

    @property
    def stats(self) -> dict[str, int]:
        return dict(Counter(r.reason for r in self.rejected))


@dataclass(slots=True)
class WalletMarketUniverseResult:
    traded_count: int
    enriched_count: int
    selected_count: int
    rejected_count: int
    pairs: list[TokenPair]
    selection: SelectionResult
