from datetime import datetime, timezone

from pmresearch.models import EnrichedTradedToken, TokenMetadata, TradedTokenStats


def make_token(
    token_id: int = 1,
    outcome: str = "Yes",
    tags: tuple[str, ...] = (),
    end_ts: datetime | None = None,
    trades_count: int = 10,
    condition_id: str | None = "cond_abc",
    market_id: int = 42,
) -> EnrichedTradedToken:
    return EnrichedTradedToken(
        traded=TradedTokenStats(
            token_id=token_id,
            first_trade_ts=datetime(2024, 1, 1, tzinfo=timezone.utc),
            last_trade_ts=datetime(2024, 6, 1, tzinfo=timezone.utc),
            trades_count=trades_count,
            volume=1_000,
            buy_count=6,
            sell_count=4,
            last_price=50,
            buy_token_volume=600.0,
            sell_token_volume=400,
            buy_usd_volume=30.0,
            sell_usd_volume=20.0,
        ),
        metadata=TokenMetadata(
            token_id=token_id,
            outcome=outcome,
            market_id=market_id,
            condition_id=condition_id,
            question="Will X happen?",
            slug="will-x-happen",
            end_ts=end_ts,
            tags=tags,
        ),
    )
