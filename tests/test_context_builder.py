"""Tests for WalletTokenContextBuilder."""
from pmresearch.builder import WalletTokenContextBuilder

from helpers import make_market_stats, make_metadata, make_wallet_stats


def test_build_joins_all_three_by_token_id():
    ws = [make_wallet_stats(1), make_wallet_stats(2)]
    ms = [make_market_stats(1), make_market_stats(2)]
    meta = [make_metadata(1), make_metadata(2)]

    builder = WalletTokenContextBuilder()
    contexts = builder.build(ws, ms, meta)

    assert len(contexts) == 2
    by_id = {c.wallet_stats.token_id: c for c in contexts}
    assert by_id[1].market_stats.token_id == 1
    assert by_id[1].metadata.token_id == 1
    assert by_id[2].market_stats.token_id == 2
    assert by_id[2].metadata.token_id == 2


def test_build_missing_market_stats_sets_none():
    ws = [make_wallet_stats(1), make_wallet_stats(2)]
    ms = [make_market_stats(2)]  # token 1 absent
    meta = [make_metadata(1), make_metadata(2)]

    contexts = WalletTokenContextBuilder().build(ws, ms, meta)
    by_id = {c.wallet_stats.token_id: c for c in contexts}

    assert by_id[1].market_stats is None
    assert by_id[2].market_stats is not None


def test_build_missing_metadata_sets_none():
    ws = [make_wallet_stats(1), make_wallet_stats(2)]
    ms = [make_market_stats(1), make_market_stats(2)]
    meta = [make_metadata(1)]  # token 2 absent

    contexts = WalletTokenContextBuilder().build(ws, ms, meta)
    by_id = {c.wallet_stats.token_id: c for c in contexts}

    assert by_id[2].metadata is None
    assert by_id[1].metadata is not None


def test_build_both_missing_sets_none():
    ws = [make_wallet_stats(99)]
    contexts = WalletTokenContextBuilder().build(ws, [], [])

    assert len(contexts) == 1
    assert contexts[0].market_stats is None
    assert contexts[0].metadata is None


def test_build_preserves_wallet_stats_order():
    ws = [make_wallet_stats(3), make_wallet_stats(1), make_wallet_stats(2)]
    contexts = WalletTokenContextBuilder().build(ws, [], [])

    assert [c.wallet_stats.token_id for c in contexts] == [3, 1, 2]


def test_build_empty_wallet_stats_returns_empty():
    contexts = WalletTokenContextBuilder().build([], [], [])
    assert contexts == []
