from __future__ import annotations

from collections import defaultdict
from typing import Any, Protocol

from clickhouse_connect.driver.external import ExternalData

from .filters import normalize_binary_outcome
from .models import TokenPair, WalletTokenContext


class ClickHouseClient(Protocol):
    def query(self, sql: str, parameters: dict[str, Any] | None = None, external_data: Any | None = None) -> Any: ...


class OutcomePairResolver:
    def __init__(self, client: ClickHouseClient) -> None:
        self._ch = client

    def resolve_pairs(self, tokens: list[WalletTokenContext]) -> list[TokenPair]:
        if not tokens:
            return []

        wallet_by_condition = _index_by_condition(tokens)
        if not wallet_by_condition:
            return []

        cids = sorted(wallet_by_condition.keys())
        print(len(cids))
        external_data = ExternalData(
            data="\n".join(cids).encode(),
            file_name="input_conditions",
            fmt="TSV",
            structure="condition_id String",
        )
        sql = """
            SELECT
                t.token_id,
                argMax(t.outcome,      t.ts) AS outcome,
                argMax(t.condition_id, t.ts) AS condition_id,
                argMax(t.market_id,    t.ts) AS market_id,
                argMax(t.question,     t.ts) AS question,
                argMax(t.market_slug,  t.ts) AS slug,
                argMax(t.end_ts,       t.ts) AS end_ts,
                argMax(t.tag_slugs,    t.ts) AS tags
            FROM default.tokens_new AS t FINAL
            INNER JOIN input_conditions AS ic ON t.condition_id = ic.condition_id
            GROUP BY t.token_id
        """
        rows = self._ch.query(sql, external_data=external_data).result_rows
        return build_pairs(wallet_by_condition, rows)


def _index_by_condition(
    tokens: list[WalletTokenContext],
) -> dict[str, WalletTokenContext]:
    """Return one wallet context per condition_id (prefer higher wallet trade count)."""
    index: dict[str, WalletTokenContext] = {}
    for token in tokens:
        if token.metadata is None:
            print("Token no metadata")
            continue
        cid = token.metadata.condition_id
        if cid is None:
            print("Token no cid")
            continue
        existing = index.get(cid)
        if existing is None or token.wallet_stats.wallet_trades_count > existing.wallet_stats.wallet_trades_count:
            index[cid] = token
    return index


def build_pairs(
    wallet_by_condition: dict[str, WalletTokenContext],
    market_rows: list[tuple],
) -> list[TokenPair]:
    """
    Pure function — testable without a DB connection.

    market_rows columns (by position):
        0: token_id, 1: outcome, 2: condition_id, 3: market_id,
        4: question, 5: market_slug, 6: end_ts, 7: tags
    """
    by_condition: dict[str, list[tuple]] = defaultdict(list)
    for row in market_rows:
        cid = row[2]
        if cid:
            by_condition[cid].append(row)

    pairs: list[TokenPair] = []
    for cid, rows in by_condition.items():
        wallet_context = wallet_by_condition.get(cid)
        if wallet_context is None:
            continue

        yes_row = None
        no_row = None
        for row in rows:
            normalized = normalize_binary_outcome(row[1] or "")
            if normalized == "yes":
                yes_row = row
            elif normalized == "no":
                no_row = row

        if yes_row is None or no_row is None:
            print("AAAAAAAA")
            continue

        wallet_outcome = ""
        if wallet_context.metadata is not None:
            wallet_outcome = normalize_binary_outcome(wallet_context.metadata.outcome) or ""

        pairs.append(
            TokenPair(
                condition_id=cid,
                market_id=yes_row[3],
                question=yes_row[4],
                slug=yes_row[5],
                end_ts=yes_row[6],
                tags=tuple(yes_row[7]) if yes_row[7] else (),
                yes_token_id=yes_row[0],
                no_token_id=no_row[0],
                wallet_traded_token_id=wallet_context.wallet_stats.token_id,
                wallet_traded_outcome=wallet_outcome,
            )
        )

    return pairs
