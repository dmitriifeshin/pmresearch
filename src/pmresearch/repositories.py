from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol

from clickhouse_connect.driver.external import ExternalData

from .models import TokenMarketStats, TokenMetadata, WalletTokenStats


class ClickHouseClient(Protocol):
    def query(
        self,
        sql: str,
        parameters: dict[str, Any] | None = None,
        external_data: Any | None = None,
    ) -> Any: ...


def _strip_0x(address: str) -> str:
    return address[2:] if address.startswith(("0x", "0X")) else address


class WalletTokenStatsRepository:
    def __init__(self, client: ClickHouseClient) -> None:
        self._ch = client

    def get_stats(
        self,
        address: str,
        since: datetime | None = None,
        until: datetime | None = None,
        only_taker: bool = True,
    ) -> list[WalletTokenStats]:
        hex_addr = _strip_0x(address).upper()

        conditions = [f"address = unhex('{hex_addr}')"]
        if only_taker:
            conditions.append("trade_type = 'taker'")

        params: dict[str, Any] = {}
        if since is not None:
            conditions.append("block_ts >= %(since)s")
            params["since"] = since
        if until is not None:
            conditions.append("block_ts <= %(until)s")
            params["until"] = until

        where = " AND ".join(conditions)
        sql = f"""
            SELECT
                token_id,
                min(block_ts)                                              AS wallet_first_trade_ts,
                max(block_ts)                                              AS wallet_last_trade_ts,
                count()                                                    AS wallet_trades_count,
                countIf(side = 0)                                          AS wallet_buy_count,
                countIf(side = 1)                                          AS wallet_sell_count,
                sumIf(toFloat64(amount) * 10000 / price, side = 0)                                  AS wallet_buy_token_volume,
                sumIf(amount, side = 1)                                                              AS wallet_sell_token_volume,
                sumIf(amount, side = 0) / 1e6                                                       AS wallet_buy_usd_volume,
                sumIf(toFloat64(amount) * price / 10000, side = 1) / 1e6                            AS wallet_sell_usd_volume,
                (sumIf(toFloat64(fee) * price / 10000, side = 1) + sumIf(toFloat64(fee), side = 0)) / 1e6  AS wallet_fee_usd
            FROM default.trades_bq
            WHERE {where}
            GROUP BY token_id
        """
        rows = self._ch.query(sql, parameters=params or None).result_rows
        return [
            WalletTokenStats(
                token_id=r[0],
                wallet_first_trade_ts=r[1],
                wallet_last_trade_ts=r[2],
                wallet_trades_count=r[3],
                wallet_buy_count=r[4],
                wallet_sell_count=r[5],
                wallet_buy_token_volume=r[6],
                wallet_sell_token_volume=r[7],
                wallet_buy_usd_volume=r[8],
                wallet_sell_usd_volume=r[9],
                wallet_fee_usd=r[10],
            )
            for r in rows
        ]


class TokenMarketStatsRepository:
    def __init__(self, client: ClickHouseClient) -> None:
        self._ch = client

    def get_stats(
        self,
        token_ids: list[int],
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> list[TokenMarketStats]:
        if not token_ids:
            return []

        token_id_strs = sorted({str(tid) for tid in token_ids})
        external_data = ExternalData(
            data="\n".join(token_id_strs).encode(),
            file_name="input_tokens",
            fmt="TSV",
            structure="token_id UInt256",
        )

        conditions: list[str] = []
        params: dict[str, Any] = {}
        if since is not None:
            conditions.append("tr.block_ts >= %(since)s")
            params["since"] = since
        if until is not None:
            conditions.append("tr.block_ts <= %(until)s")
            params["until"] = until

        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        sql = f"""
            SELECT
                tr.token_id,
                min(tr.block_ts)              AS market_first_trade_ts,
                max(tr.block_ts)              AS market_last_trade_ts,
                argMax(tr.price, tr.block_ts) AS last_price,
                count()                       AS market_trades_count,
                sum(tr.amount)                AS market_volume,
                uniqExact(tr.address)         AS unique_traders_count
            FROM default.trades_bq AS tr
            INNER JOIN input_tokens AS it ON tr.token_id = it.token_id
            {where_clause}
            GROUP BY tr.token_id
        """

        rows = self._ch.query(
            sql,
            parameters=params or None,
            external_data=external_data,
        ).result_rows

        return [
            TokenMarketStats(
                token_id=r[0],
                market_first_trade_ts=r[1],
                market_last_trade_ts=r[2],
                last_price=r[3],
                market_trades_count=r[4],
                market_volume=r[5],
                unique_traders_count=r[6],
            )
            for r in rows
        ]


class TokenMetadataRepository:
    def __init__(self, client: ClickHouseClient) -> None:
        self._ch = client

    def get_metadata(
        self,
        token_ids: list[int],
        metadata_as_of: datetime | None = None,
    ) -> list[TokenMetadata]:
        if not token_ids:
            return []

        unique_ids = sorted({str(tid) for tid in token_ids})
        external_data = ExternalData(
            data="\n".join(unique_ids).encode(),
            file_name="input_tokens",
            fmt="TSV",
            structure="token_id UInt256",
        )

        params: dict[str, Any] = {}
        where_clause = ""
        if metadata_as_of is not None:
            where_clause = "WHERE t.ts <= %(metadata_as_of)s"
            params["metadata_as_of"] = metadata_as_of

        sql = f"""
            SELECT
                t.token_id,
                argMax(t.outcome,      t.ts) AS outcome,
                argMax(t.market_id,    t.ts) AS market_id,
                argMax(t.condition_id, t.ts) AS condition_id,
                argMax(t.question,     t.ts) AS question,
                argMax(t.market_slug,  t.ts) AS market_slug,
                argMax(t.end_ts,       t.ts) AS end_ts,
                argMax(t.tag_slugs,         t.ts) AS tag_slugs
            FROM default.tokens_new AS t FINAL
            INNER JOIN input_tokens AS it ON t.token_id = it.token_id
            {where_clause}
            GROUP BY t.token_id
        """

        rows = self._ch.query(
            sql,
            parameters=params or None,
            external_data=external_data,
        ).result_rows

        return [
            TokenMetadata(
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
        ]
