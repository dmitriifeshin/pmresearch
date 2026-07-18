from datetime import datetime, timezone

from pmresearch.models import TokenMarketStats, TokenMetadata, WalletTokenContext, WalletTokenStats


def make_wallet_stats(
    token_id: int = 1,
    wallet_trades_count: int = 10,
    wallet_buy_count: int = 6,
    wallet_sell_count: int = 4,
    wallet_buy_token_volume: float = 600.0,
    wallet_sell_token_volume: int = 400,
    wallet_buy_usd_volume: float = 30.0,
    wallet_sell_usd_volume: float = 20.0,
    wallet_buy_fee_token_volume: float = 0.0,
    wallet_sell_fee_usd: float = 0.0,
    wallet_fee_usd: float = 1.0,
) -> WalletTokenStats:
    return WalletTokenStats(
        token_id=token_id,
        wallet_first_trade_ts=datetime(2024, 1, 1, tzinfo=timezone.utc),
        wallet_last_trade_ts=datetime(2024, 6, 1, tzinfo=timezone.utc),
        wallet_trades_count=wallet_trades_count,
        wallet_buy_count=wallet_buy_count,
        wallet_sell_count=wallet_sell_count,
        wallet_buy_token_volume=wallet_buy_token_volume,
        wallet_sell_token_volume=wallet_sell_token_volume,
        wallet_buy_usd_volume=wallet_buy_usd_volume,
        wallet_sell_usd_volume=wallet_sell_usd_volume,
        wallet_buy_fee_token_volume=wallet_buy_fee_token_volume,
        wallet_sell_fee_usd=wallet_sell_fee_usd,
        wallet_fee_usd=wallet_fee_usd,
    )


def make_market_stats(
    token_id: int = 1,
    market_trades_count: int = 100,
    market_volume: int = 50_000,
    last_price: int = 5000,
) -> TokenMarketStats:
    return TokenMarketStats(
        token_id=token_id,
        market_first_trade_ts=datetime(2023, 1, 1, tzinfo=timezone.utc),
        market_last_trade_ts=datetime(2024, 6, 1, tzinfo=timezone.utc),
        last_price=last_price,
        market_trades_count=market_trades_count,
        market_volume=market_volume,
        unique_traders_count=20,
    )


def make_metadata(
    token_id: int = 1,
    outcome: str = "Yes",
    tags: tuple[str, ...] = (),
    end_ts: datetime | None = None,
    condition_id: str | None = "cond_abc",
    market_id: int = 42,
) -> TokenMetadata:
    return TokenMetadata(
        token_id=token_id,
        outcome=outcome,
        market_id=market_id,
        condition_id=condition_id,
        question="Will X happen?",
        slug="will-x-happen",
        end_ts=end_ts,
        tags=tags,
    )


def make_context(
    token_id: int = 1,
    outcome: str = "Yes",
    tags: tuple[str, ...] = (),
    end_ts: datetime | None = None,
    wallet_trades_count: int = 10,
    market_trades_count: int = 100,
    market_volume: int = 50_000,
    condition_id: str | None = "cond_abc",
    market_id: int = 42,
    include_market_stats: bool = True,
    include_metadata: bool = True,
) -> WalletTokenContext:
    ws = make_wallet_stats(token_id=token_id, wallet_trades_count=wallet_trades_count)
    ms = make_market_stats(token_id=token_id, market_trades_count=market_trades_count, market_volume=market_volume) if include_market_stats else None
    meta = make_metadata(token_id=token_id, outcome=outcome, tags=tags, end_ts=end_ts, condition_id=condition_id, market_id=market_id) if include_metadata else None
    return WalletTokenContext(wallet_stats=ws, market_stats=ms, metadata=meta)
