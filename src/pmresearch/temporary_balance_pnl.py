"""Temporary integer PnL calculation over `wallet_token_balances`."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .builder import WalletMarketUniverseBuilder
from .repositories import WalletTokenBalanceRepository


COLLATERAL_TOKEN_ID = 0
PRICE_SCALE = 10_000
RAW_UNIT_SCALE = 1_000_000


@dataclass(frozen=True, slots=True)
class TokenBalanceValuation:
    token_id: int
    balance: int
    last_price: int
    value_micro_usd: int


@dataclass(frozen=True, slots=True)
class TemporaryWalletPnl:
    address: str
    collateral_micro_usd: int
    positions_value_micro_usd: int
    pnl_micro_usd: int
    positions: tuple[TokenBalanceValuation, ...]

    @property
    def pnl_usd(self) -> float:
        return self.pnl_micro_usd / RAW_UNIT_SCALE


class TemporaryBalancePnlCalculator:
    """Values saved wallet balances using builder-provided last prices."""

    def __init__(
        self,
        balances_repo: WalletTokenBalanceRepository,
        universe_builder: WalletMarketUniverseBuilder,
    ) -> None:
        self._balances_repo = balances_repo
        self._universe_builder = universe_builder

    def calculate(
        self,
        address: str,
        since: datetime | None = None,
        until: datetime | None = None,
        metadata_as_of: datetime | None = None,
    ) -> TemporaryWalletPnl:
        balances = self._balances_repo.get_balances(address)
        universe = self._universe_builder.build(
            address=address,
            since=since,
            until=until,
            metadata_as_of=metadata_as_of,
            only_taker=False,
        )

        contexts = [
            *universe.selection.selected,
            *(rejected.token for rejected in universe.selection.rejected),
        ]
        market_stats_by_token = {
            context.market_stats.token_id: context.market_stats
            for context in contexts
            if context.market_stats is not None
        }

        collateral = 0
        position_values: list[TokenBalanceValuation] = []
        positions_value = 0

        for item in balances:
            if item.token_id == COLLATERAL_TOKEN_ID:
                collateral += item.balance
                continue
            if item.balance == 0:
                continue

            market_stats = market_stats_by_token.get(item.token_id)
            if market_stats is None:
                raise ValueError(
                    f"missing market_stats.last_price for non-zero token_id={item.token_id}"
                )

            value = _scaled_value(item.balance, market_stats.last_price)
            positions_value += value
            position_values.append(
                TokenBalanceValuation(
                    token_id=item.token_id,
                    balance=item.balance,
                    last_price=market_stats.last_price,
                    value_micro_usd=value,
                )
            )

        return TemporaryWalletPnl(
            address=address,
            collateral_micro_usd=collateral,
            positions_value_micro_usd=positions_value,
            pnl_micro_usd=collateral + positions_value,
            positions=tuple(position_values),
        )


def _scaled_value(balance: int, last_price: int) -> int:
    if last_price < 0:
        raise ValueError(f"last_price must be non-negative, got {last_price}")
    # `//` floors negative values in Python. Apply the sign separately so the
    # integer conversion always truncates towards zero.
    sign = -1 if balance < 0 else 1
    return sign * (abs(balance) * last_price // PRICE_SCALE)
