from datetime import datetime, timezone

import pytest

from pmresearch.filters import (
    ActiveMarketFilter,
    BinaryOutcomeFilter,
    ExcludeTagsFilter,
    IncludeTagsFilter,
    MinTradesFilter,
)

from helpers import make_token

NOW = datetime(2025, 1, 1, tzinfo=timezone.utc)


# ── ExcludeTagsFilter ────────────────────────────────────────────────────────

def test_exclude_rejects_matching_tag():
    f = ExcludeTagsFilter({"Crypto"})
    d = f(make_token(tags=("Crypto", "DeFi")))
    assert not d.keep
    assert "Crypto" in d.reason

def test_exclude_keeps_non_matching():
    f = ExcludeTagsFilter({"Crypto"})
    assert f(make_token(tags=("Sports",))).keep

def test_exclude_keeps_empty_tags():
    f = ExcludeTagsFilter({"Crypto"})
    assert f(make_token(tags=())).keep


# ── IncludeTagsFilter ────────────────────────────────────────────────────────

def test_include_keeps_matching():
    f = IncludeTagsFilter({"Politics"})
    assert f(make_token(tags=("Politics", "US"))).keep

def test_include_rejects_no_match():
    f = IncludeTagsFilter({"Politics"})
    d = f(make_token(tags=("Sports",)))
    assert not d.keep


# ── ActiveMarketFilter ───────────────────────────────────────────────────────

def test_active_keeps_future_end_ts():
    f = ActiveMarketFilter(now=NOW)
    assert f(make_token(end_ts=datetime(2026, 1, 1, tzinfo=timezone.utc))).keep

def test_active_rejects_past_end_ts():
    f = ActiveMarketFilter(now=NOW)
    d = f(make_token(end_ts=datetime(2024, 1, 1, tzinfo=timezone.utc)))
    assert not d.keep

def test_active_keeps_none_end_ts():
    assert ActiveMarketFilter(now=NOW)(make_token(end_ts=None)).keep

def test_active_handles_naive_end_ts():
    f = ActiveMarketFilter(now=NOW)
    # naive datetime treated as UTC
    assert f(make_token(end_ts=datetime(2026, 6, 1))).keep


# ── MinTradesFilter ──────────────────────────────────────────────────────────

def test_min_trades_exact_boundary():
    f = MinTradesFilter(5)
    assert f(make_token(trades_count=5)).keep
    assert not f(make_token(trades_count=4)).keep

def test_min_trades_reason_contains_counts():
    d = MinTradesFilter(10)(make_token(trades_count=3))
    assert "3" in d.reason and "10" in d.reason


# ── BinaryOutcomeFilter ──────────────────────────────────────────────────────

@pytest.mark.parametrize("outcome", ["Yes", "No", "yes", "no", " Yes "])
def test_binary_keeps_valid(outcome):
    assert BinaryOutcomeFilter()(make_token(outcome=outcome)).keep

@pytest.mark.parametrize("outcome", ["Draw", "Maybe", "Higher", ""])
def test_binary_rejects_invalid(outcome):
    assert not BinaryOutcomeFilter()(make_token(outcome=outcome)).keep
