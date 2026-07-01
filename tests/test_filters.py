from datetime import datetime, timezone

import pytest

from pmresearch.filters import (
    ActiveMarketFilter,
    BinaryOutcomeFilter,
    ExcludeTagsFilter,
    IncludeTagsFilter,
    MinMarketTradesFilter,
    MinMarketVolumeFilter,
    MinTradesFilter,
    MinWalletTradesFilter,
)

from helpers import make_context

NOW = datetime(2025, 1, 1, tzinfo=timezone.utc)


# ── ExcludeTagsFilter ────────────────────────────────────────────────────────

def test_exclude_rejects_matching_tag():
    f = ExcludeTagsFilter({"Crypto"})
    d = f(make_context(tags=("Crypto", "DeFi")))
    assert not d.keep
    assert "Crypto" in d.reason

def test_exclude_keeps_non_matching():
    f = ExcludeTagsFilter({"Crypto"})
    assert f(make_context(tags=("Sports",))).keep

def test_exclude_keeps_empty_tags():
    f = ExcludeTagsFilter({"Crypto"})
    assert f(make_context(tags=())).keep

def test_exclude_missing_metadata_rejects():
    f = ExcludeTagsFilter({"Crypto"})
    d = f(make_context(include_metadata=False))
    assert not d.keep
    assert d.reason == "missing_metadata"


# ── IncludeTagsFilter ────────────────────────────────────────────────────────

def test_include_keeps_matching():
    f = IncludeTagsFilter({"Politics"})
    assert f(make_context(tags=("Politics", "US"))).keep

def test_include_rejects_no_match():
    f = IncludeTagsFilter({"Politics"})
    d = f(make_context(tags=("Sports",)))
    assert not d.keep

def test_include_missing_metadata_rejects():
    f = IncludeTagsFilter({"Politics"})
    d = f(make_context(include_metadata=False))
    assert not d.keep
    assert d.reason == "missing_metadata"


# ── ActiveMarketFilter ───────────────────────────────────────────────────────

def test_active_keeps_future_end_ts():
    f = ActiveMarketFilter(now=NOW)
    assert f(make_context(end_ts=datetime(2026, 1, 1, tzinfo=timezone.utc))).keep

def test_active_rejects_past_end_ts():
    f = ActiveMarketFilter(now=NOW)
    d = f(make_context(end_ts=datetime(2024, 1, 1, tzinfo=timezone.utc)))
    assert not d.keep

def test_active_keeps_none_end_ts():
    assert ActiveMarketFilter(now=NOW)(make_context(end_ts=None)).keep

def test_active_handles_naive_end_ts():
    f = ActiveMarketFilter(now=NOW)
    assert f(make_context(end_ts=datetime(2026, 6, 1))).keep

def test_active_missing_metadata_rejects():
    f = ActiveMarketFilter(now=NOW)
    d = f(make_context(include_metadata=False))
    assert not d.keep
    assert d.reason == "missing_metadata"


# ── MinWalletTradesFilter / MinTradesFilter alias ────────────────────────────

def test_min_wallet_trades_exact_boundary():
    f = MinWalletTradesFilter(5)
    assert f(make_context(wallet_trades_count=5)).keep
    assert not f(make_context(wallet_trades_count=4)).keep

def test_min_wallet_trades_reason_contains_counts():
    d = MinWalletTradesFilter(10)(make_context(wallet_trades_count=3))
    assert "3" in d.reason and "10" in d.reason

def test_min_trades_alias_works():
    f = MinTradesFilter(5)
    assert f(make_context(wallet_trades_count=5)).keep
    assert not f(make_context(wallet_trades_count=4)).keep


# ── MinMarketTradesFilter ────────────────────────────────────────────────────

def test_min_market_trades_exact_boundary():
    f = MinMarketTradesFilter(50)
    assert f(make_context(market_trades_count=50)).keep
    assert not f(make_context(market_trades_count=49)).keep

def test_min_market_trades_reason_contains_counts():
    d = MinMarketTradesFilter(100)(make_context(market_trades_count=30))
    assert "30" in d.reason and "100" in d.reason

def test_min_market_trades_missing_market_stats_rejects():
    f = MinMarketTradesFilter(10)
    d = f(make_context(include_market_stats=False))
    assert not d.keep
    assert d.reason == "missing_market_stats"


# ── MinMarketVolumeFilter ────────────────────────────────────────────────────

def test_min_market_volume_keeps_above_threshold():
    f = MinMarketVolumeFilter(10_000)
    assert f(make_context(market_volume=10_000)).keep
    assert not f(make_context(market_volume=9_999)).keep

def test_min_market_volume_missing_market_stats_rejects():
    f = MinMarketVolumeFilter(1)
    d = f(make_context(include_market_stats=False))
    assert not d.keep
    assert d.reason == "missing_market_stats"


# ── BinaryOutcomeFilter ──────────────────────────────────────────────────────

@pytest.mark.parametrize("outcome", ["Yes", "No", "yes", "no", " Yes ", "Up", "Down", "up", "down", " Up "])
def test_binary_keeps_valid(outcome):
    assert BinaryOutcomeFilter()(make_context(outcome=outcome)).keep

@pytest.mark.parametrize("outcome", ["Draw", "Maybe", "Higher", ""])
def test_binary_rejects_invalid(outcome):
    assert not BinaryOutcomeFilter()(make_context(outcome=outcome)).keep

def test_binary_missing_metadata_rejects():
    d = BinaryOutcomeFilter()(make_context(include_metadata=False))
    assert not d.keep
    assert d.reason == "missing_metadata"


# ── normalize_binary_outcome ──────────────────────────────────────────────────

from pmresearch.filters import normalize_binary_outcome

@pytest.mark.parametrize("outcome,expected", [
    ("Yes", "yes"), ("yes", "yes"), (" Yes ", "yes"),
    ("No", "no"),  ("no", "no"),
    ("Up", "yes"), ("up", "yes"), (" Up ", "yes"),
    ("Down", "no"), ("down", "no"),
])
def test_normalize_binary_outcome_known(outcome, expected):
    assert normalize_binary_outcome(outcome) == expected

@pytest.mark.parametrize("outcome", ["Draw", "Maybe", "", "Higher"])
def test_normalize_binary_outcome_unknown_returns_none(outcome):
    assert normalize_binary_outcome(outcome) is None
