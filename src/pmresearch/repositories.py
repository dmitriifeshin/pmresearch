from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol

from .models import EnrichedTradedToken, TokenMetadata, TradedTokenStats


class ClickHouseClient(Protocol):
    def query(self, sql: str, parameters: dict[str, Any] | None = None) -> Any: ...


def _strip_0x(address: str) -> str:
    return address[2:] if address.startswith(("0x", "0X")) else address


class WalletTradedTokenRepository:
    def __init__(self, client: ClickHouseClient) -> None:
        self._ch = client

    def get_traded_tokens(
        self,
        address: str,
        since: datetime | None = None,
        until: datetime | None = None,
        only_taker: bool = True,
    ) -> list[TradedTokenStats]:
        hex_addr = _strip_0x(address).upper()

        conditions = [f"address = unhex('{hex_addr}')"]
        if only_taker:
            conditions.append("trade_type = 'taker'")
        if since:
            conditions.append(f"block_ts >= '{since.strftime('%Y-%m-%d %H:%M:%S')}'")
        if until:
            conditions.append(f"block_ts <= '{until.strftime('%Y-%m-%d %H:%M:%S')}'")

        where = " AND ".join(conditions)
        sql = f"""
            SELECT
                token_id,
                min(block_ts)     AS first_trade_ts,
                max(block_ts)     AS last_trade_ts,
                count()           AS trades_count,
                sum(amount)       AS volume,
                countIf(side = 0) AS buy_count,
                countIf(side = 1) AS sell_count,
                argMax(price, block_ts)                                    AS last_price,
                sumIf(toFloat64(amount) * 10000 / price, side = 0)        AS buy_token_volume,
                sumIf(amount, side = 1)                                    AS sell_token_volume,
                sumIf(amount, side = 0) / 1e6                             AS buy_usd_volume,
                sumIf(toFloat64(amount) * price / 10000, side = 1) / 1e6  AS sell_usd_volume
            FROM default.trades_bq
            WHERE {where}
            GROUP BY token_id
        """
        rows = self._ch.query(sql).result_rows
        return [
            TradedTokenStats(
                token_id=r[0],
                first_trade_ts=r[1],
                last_trade_ts=r[2],
                trades_count=r[3],
                volume=r[4],
                buy_count=r[5],
                sell_count=r[6],
                last_price=r[7],
                buy_token_volume=r[8],
                sell_token_volume=r[9],
                buy_usd_volume=r[10],
                sell_usd_volume=r[11],
            )
            for r in rows
        ]


class TokenMetadataRepository:
    def __init__(self, client: ClickHouseClient) -> None:
        self._ch = client

    def enrich(self, traded_tokens: list[TradedTokenStats]) -> list[EnrichedTradedToken]:
        if not traded_tokens:
            return []

        # TODO: for lists > ~10k tokens replace IN with an external temporary table + JOIN
        ids_sql = ", ".join(f"toUInt256('{t.token_id}')" for t in traded_tokens)
        sql = f"""
            SELECT
                token_id,
                argMax(outcome,      ts) AS outcome,
                argMax(market_id,    ts) AS market_id,
                argMax(condition_id, ts) AS condition_id,
                argMax(question,     ts) AS question,
                argMax(slug,         ts) AS slug,
                argMax(end_ts,       ts) AS end_ts,
                argMax(tags,         ts) AS tags
            FROM default.tokens
            WHERE token_id IN ({ids_sql})
            GROUP BY token_id
        """
        rows = self._ch.query(sql).result_rows
        meta_by_id: dict[int, TokenMetadata] = {
            r[0]: TokenMetadata(
                token_id=r[0],
                outcome=r[1] or "",
                market_id=r[2],
                condition_id=r[3],
                question=r[4],
                slug=r[5],
                end_ts=r[6],
                tags=tuple(r[7]) if r[7] else (),
            )
            for r in rows
        }

        return [
            EnrichedTradedToken(traded=t, metadata=meta_by_id[t.token_id])
            for t in traded_tokens
            if t.token_id in meta_by_id
        ]
