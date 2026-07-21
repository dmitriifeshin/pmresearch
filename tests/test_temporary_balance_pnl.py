from datetime import datetime
from types import SimpleNamespace

import pytest

from pmresearch.models import (
    SelectionResult,
    TokenMarketStats,
    WalletTokenBalance,
    WalletTokenContext,
)
from pmresearch.temporary_balance_pnl import TemporaryBalancePnlCalculator


class FakeBalancesRepository:
    def __init__(self, balances):
        self.balances = balances

    def get_balances(self, address):
        return self.balances


class FakeUniverseBuilder:
    def __init__(self, contexts):
        self.contexts = contexts

    def build(self, **kwargs):
        assert kwargs["only_taker"] is False
        return SimpleNamespace(
            selection=SelectionResult(selected=self.contexts, rejected=[]),
        )


def context(token_id: int, last_price: int) -> WalletTokenContext:
    now = datetime(2026, 1, 1)
    stats = TokenMarketStats(token_id, now, now, last_price, 1, 1, 1)
    return WalletTokenContext(wallet_stats=None, market_stats=stats, metadata=None)


def test_integer_pnl_from_collateral_and_marked_positions():
    balances = [
        WalletTokenBalance(token_id=0, balance=-40_000_000),
        WalletTokenBalance(token_id=11, balance=100_000_000),
    ]
    calculator = TemporaryBalancePnlCalculator(
        FakeBalancesRepository(balances),
        FakeUniverseBuilder([context(11, 7_000)]),
    )

    result = calculator.calculate("0xabc")

    assert result.positions_value_micro_usd == 70_000_000
    assert result.pnl_micro_usd == 30_000_000
    assert result.pnl_usd == 30.0


def test_missing_price_for_open_position_is_error():
    calculator = TemporaryBalancePnlCalculator(
        FakeBalancesRepository([WalletTokenBalance(token_id=11, balance=1_000_000)]),
        FakeUniverseBuilder([]),
    )

    with pytest.raises(ValueError, match="token_id=11"):
        calculator.calculate("0xabc")
