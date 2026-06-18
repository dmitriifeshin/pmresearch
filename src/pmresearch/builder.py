from __future__ import annotations

from datetime import datetime

from .models import WalletMarketUniverseResult
from .repositories import TokenMetadataRepository, WalletTradedTokenRepository
from .resolver import OutcomePairResolver
from .selector import TokenSelector


class WalletMarketUniverseBuilder:
    def __init__(
        self,
        wallet_repo: WalletTradedTokenRepository,
        metadata_repo: TokenMetadataRepository,
        selector: TokenSelector,
        resolver: OutcomePairResolver,
    ) -> None:
        self._wallet_repo = wallet_repo
        self._metadata_repo = metadata_repo
        self._selector = selector
        self._resolver = resolver

    def build(
        self,
        address: str,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> WalletMarketUniverseResult:
        traded = self._wallet_repo.get_traded_tokens(address, since=since, until=until)
        enriched = self._metadata_repo.enrich(traded)
        selection = self._selector.select(enriched)
        pairs = self._resolver.resolve_pairs(selection.selected)

        return WalletMarketUniverseResult(
            traded_count=len(traded),
            enriched_count=len(enriched),
            selected_count=len(selection.selected),
            rejected_count=len(selection.rejected),
            pairs=pairs,
            selection=selection,
        )
