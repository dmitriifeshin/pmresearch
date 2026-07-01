from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class WalletTokenStats:
    token_id: int
    wallet_first_trade_ts: datetime
    wallet_last_trade_ts: datetime
    wallet_trades_count: int
    wallet_volume: int          # raw sum(amount)
    wallet_buy_count: int
    wallet_sell_count: int
    wallet_buy_token_volume: float   # tokens bought: sum(amount_usd * 10000 / price)
    wallet_sell_token_volume: int    # tokens sold: sum(amount) for sells
    wallet_buy_usd_volume: float     # USD spent on buys: sum(amount) / 1e6
    wallet_sell_usd_volume: float    # USD received from sells: sum(amount * price / 10000) / 1e6


@dataclass(frozen=True, slots=True)
class TokenMarketStats:
    token_id: int
    market_first_trade_ts: datetime
    market_last_trade_ts: datetime  # == last_trade_ts; last_price is argMax over this
    last_price: int
    market_trades_count: int
    market_volume: int
    unique_traders_count: int


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
class WalletTokenContext:
    wallet_stats: WalletTokenStats
    market_stats: TokenMarketStats | None
    metadata: TokenMetadata | None


@dataclass(frozen=True, slots=True)
class FilterDecision:
    keep: bool
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class RejectedToken:
    token: WalletTokenContext
    reason: str


@dataclass(slots=True)
class SelectionResult:
    selected: list[WalletTokenContext]
    rejected: list[RejectedToken]

    @property
    def stats(self) -> dict[str, int]:
        return dict(Counter(r.reason for r in self.rejected))


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


@dataclass(slots=True)
class WalletMarketUniverseResult:
    wallet_stats_count: int
    market_stats_count: int
    metadata_count: int
    contexts_count: int
    selected_count: int
    rejected_count: int
    pairs: list[TokenPair]
    selection: SelectionResult

    def pipeline_summary(self) -> list[dict]:
        """Pipeline funnel as list[dict] — wrap in pd.DataFrame() in a notebook."""
        return [
            {"stage": "wallet_stats",  "count": self.wallet_stats_count},
            {"stage": "market_stats",  "count": self.market_stats_count},
            {"stage": "metadata",      "count": self.metadata_count},
            {"stage": "contexts",      "count": self.contexts_count},
            {"stage": "selected",      "count": self.selected_count},
            {"stage": "rejected",      "count": self.rejected_count},
            {"stage": "pairs",         "count": len(self.pairs)},
        ]

    def rejection_summary(self) -> list[dict]:
        """Rejection counts by reason, sorted descending — wrap in pd.DataFrame()."""
        return [
            {"reason": reason, "count": count}
            for reason, count in sorted(
                self.selection.stats.items(), key=lambda x: x[1], reverse=True
            )
        ]
