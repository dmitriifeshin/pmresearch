"""
Tests for OutcomePairResolver use the pure `build_pairs` helper —
no ClickHouse connection required.
"""
from pmresearch.resolver import build_pairs, _index_by_condition

from helpers import make_context, make_metadata, make_wallet_stats
from pmresearch.models import WalletTokenContext


def _row(token_id, outcome, condition_id, market_id=1, question="Q?", slug="q", end_ts=None, tags=None):
    """Build a fake market_row tuple matching resolver column order."""
    return (token_id, outcome, condition_id, market_id, question, slug, end_ts, tags or [])


# ── _index_by_condition ──────────────────────────────────────────────────────

def test_index_skips_tokens_without_condition():
    token = make_context(condition_id=None)
    assert _index_by_condition([token]) == {}


def test_index_skips_tokens_without_metadata():
    token = make_context(include_metadata=False)
    assert _index_by_condition([token]) == {}


def test_index_prefers_higher_trade_count():
    t1 = make_context(token_id=1, wallet_trades_count=5, condition_id="c1")
    t2 = make_context(token_id=2, wallet_trades_count=20, condition_id="c1")
    index = _index_by_condition([t1, t2])
    assert index["c1"].wallet_stats.token_id == 2


# ── build_pairs ──────────────────────────────────────────────────────────────

def test_basic_pair():
    wallet = {"c1": make_context(token_id=100, outcome="Yes", condition_id="c1")}
    rows = [
        _row(100, "Yes", "c1"),
        _row(200, "No",  "c1"),
    ]
    pairs = build_pairs(wallet, rows)
    assert len(pairs) == 1
    p = pairs[0]
    assert p.yes_token_id == 100
    assert p.no_token_id == 200
    assert p.wallet_traded_token_id == 100
    assert p.wallet_traded_outcome == "yes"


def test_wallet_traded_no_side():
    wallet = {"c1": make_context(token_id=200, outcome="No", condition_id="c1")}
    rows = [
        _row(100, "Yes", "c1"),
        _row(200, "No",  "c1"),
    ]
    pairs = build_pairs(wallet, rows)
    assert pairs[0].wallet_traded_outcome == "no"
    assert pairs[0].wallet_traded_token_id == 200


def test_multi_outcome_market_skipped():
    wallet = {"c1": make_context(token_id=1, outcome="Yes", condition_id="c1")}
    rows = [
        _row(1, "Yes",    "c1"),
        _row(2, "No",     "c1"),
        _row(3, "Draw",   "c1"),  # third outcome — yes+no still found, pair is formed
    ]
    pairs = build_pairs(wallet, rows)
    assert len(pairs) == 1


def test_incomplete_market_skipped():
    """Market with only a Yes token (No not found) → skip."""
    wallet = {"c1": make_context(token_id=1, outcome="Yes", condition_id="c1")}
    rows = [_row(1, "Yes", "c1")]
    assert build_pairs(wallet, rows) == []


def test_multiple_conditions():
    wallet = {
        "c1": make_context(token_id=10, outcome="Yes", condition_id="c1"),
        "c2": make_context(token_id=30, outcome="No",  condition_id="c2"),
    }
    rows = [
        _row(10, "Yes", "c1"),
        _row(20, "No",  "c1"),
        _row(30, "No",  "c2"),
        _row(40, "Yes", "c2"),
    ]
    pairs = build_pairs(wallet, rows)
    assert len(pairs) == 2
    by_cid = {p.condition_id: p for p in pairs}
    assert by_cid["c1"].yes_token_id == 10
    assert by_cid["c2"].no_token_id == 30


def test_unknown_condition_in_rows_ignored():
    wallet = {"c1": make_context(token_id=1, outcome="Yes", condition_id="c1")}
    rows = [
        _row(1,  "Yes", "c1"),
        _row(2,  "No",  "c1"),
        _row(99, "Yes", "c_other"),  # not in wallet index
    ]
    pairs = build_pairs(wallet, rows)
    assert len(pairs) == 1
    assert pairs[0].condition_id == "c1"


def test_build_pairs_without_metadata_uses_empty_outcome():
    ws = make_wallet_stats(token_id=100)
    ctx = WalletTokenContext(wallet_stats=ws, market_stats=None, metadata=None)
    wallet = {"c1": ctx}
    rows = [
        _row(100, "Yes", "c1"),
        _row(200, "No",  "c1"),
    ]
    pairs = build_pairs(wallet, rows)
    assert len(pairs) == 1
    assert pairs[0].wallet_traded_outcome == ""
