from __future__ import annotations

from datetime import datetime

from .models import (
    TokenMarketStats,
    TokenMetadata,
    WalletMarketUniverseResult,
    WalletTokenContext,
    WalletTokenStats,
)
from .repositories import TokenMarketStatsRepository, TokenMetadataRepository, WalletTokenStatsRepository
from .resolver import OutcomePairResolver
from .selector import TokenSelector


class WalletTokenContextBuilder:
    def build(
        self,
        wallet_stats: list[WalletTokenStats],
        market_stats: list[TokenMarketStats],
        metadata: list[TokenMetadata],
    ) -> list[WalletTokenContext]:
        market_by_token = {m.token_id: m for m in market_stats}
        meta_by_token = {m.token_id: m for m in metadata}

        return [
            WalletTokenContext(
                wallet_stats=ws,
                market_stats=market_by_token.get(ws.token_id),
                metadata=meta_by_token.get(ws.token_id),
            )
            for ws in wallet_stats
        ]


class WalletMarketUniverseBuilder:
    def __init__(
        self,
        wallet_stats_repo: WalletTokenStatsRepository,
        market_stats_repo: TokenMarketStatsRepository,
        metadata_repo: TokenMetadataRepository,
        context_builder: WalletTokenContextBuilder,
        selector: TokenSelector,
        resolver: OutcomePairResolver,
    ) -> None:
        self._wallet_stats_repo = wallet_stats_repo
        self._market_stats_repo = market_stats_repo
        self._metadata_repo = metadata_repo
        self._context_builder = context_builder
        self._selector = selector
        self._resolver = resolver

    def build(
        self,
        address: str,
        since: datetime | None = None,
        until: datetime | None = None,
        metadata_as_of: datetime | None = None,
    ) -> WalletMarketUniverseResult:
        wallet_stats = self._wallet_stats_repo.get_stats(address, since=since, until=until)
        token_ids = [ws.token_id for ws in wallet_stats]
        market_stats = self._market_stats_repo.get_stats(token_ids, since=since, until=until)
        metadata = self._metadata_repo.get_metadata(token_ids, metadata_as_of=metadata_as_of)
        contexts = self._context_builder.build(wallet_stats, market_stats, metadata)
        selection = self._selector.select(contexts)
        pairs = self._resolver.resolve_pairs(selection.selected)

        return WalletMarketUniverseResult(
            wallet_stats_count=len(wallet_stats),
            market_stats_count=len(market_stats),
            metadata_count=len(metadata),
            contexts_count=len(contexts),
            selected_count=len(selection.selected),
            rejected_count=len(selection.rejected),
            pairs=pairs,
            selection=selection,
        )
