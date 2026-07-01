"""Tests for TagMetricsBuilder — pure logic, no ClickHouse."""
import math

import numpy as np
import pytest

from pmresearch.tag_analysis import TagMetricsBuilder
from pmresearch.tag_analysis.metrics import calc_roi, calc_time_to_end_hours, calc_winrate

from helpers import make_context, make_market_stats, make_wallet_stats
from pmresearch.models import WalletTokenContext


# ── grouping ──────────────────────────────────────────────────────────────────

def test_token_goes_to_matching_tag():
    ctx = make_context(token_id=1, tags=("Politics",))
    result = TagMetricsBuilder().build([ctx], tags=["Politics"])
    assert result.get("Politics").tokens_count == 1


def test_token_with_multiple_tags_goes_to_each_group():
    ctx = make_context(token_id=1, tags=("Politics", "Elections"))
    result = TagMetricsBuilder().build([ctx], tags=["Politics", "Elections", "Sports"])
    assert result.get("Politics").tokens_count == 1
    assert result.get("Elections").tokens_count == 1
    assert result.get("Sports").tokens_count == 0


def test_token_without_metadata_is_skipped():
    ctx = make_context(token_id=1, include_metadata=False)
    result = TagMetricsBuilder().build([ctx], tags=["Politics"])
    assert result.get("Politics").tokens_count == 0


def test_token_without_metadata_does_not_raise():
    ctx = make_context(token_id=1, include_metadata=False)
    result = TagMetricsBuilder().build([ctx], tags=["Politics"])
    assert result is not None


def test_token_not_matching_any_tag_not_included():
    ctx = make_context(token_id=1, tags=("Crypto",))
    result = TagMetricsBuilder().build([ctx], tags=["Politics"])
    assert result.get("Politics").tokens_count == 0


def test_multiple_tokens_same_tag():
    contexts = [make_context(token_id=i, tags=("Politics",)) for i in range(5)]
    result = TagMetricsBuilder().build(contexts, tags=["Politics"])
    assert result.get("Politics").tokens_count == 5


# ── array lengths are consistent ──────────────────────────────────────────────

def test_all_per_token_arrays_have_same_length():
    contexts = [make_context(token_id=i, tags=("Politics",)) for i in range(3)]
    arrays = TagMetricsBuilder().build(contexts, tags=["Politics"]).get("Politics")
    n = arrays.tokens_count
    assert len(arrays.pnl) == n
    assert len(arrays.roi) == n
    assert len(arrays.usd_buy_volume) == n
    assert len(arrays.avg_buy_price) == n
    assert len(arrays.time_to_end_at_entry_hours) == n
    assert len(arrays.market_trades_count) == n
    assert len(arrays.market_volume) == n
    assert len(arrays.unique_traders_count) == n
    assert len(arrays.pnl_vs_buy_volume_x) == n
    assert len(arrays.pnl_vs_buy_volume_y) == n
    assert len(arrays.market_ids) == n
    assert len(arrays.questions) == n
    assert len(arrays.slugs) == n


# ── missing market_stats → nan ────────────────────────────────────────────────

def test_missing_market_stats_yields_nan_in_market_metrics():
    ctx = make_context(token_id=1, tags=("Politics",), include_market_stats=False)
    arrays = TagMetricsBuilder().build([ctx], tags=["Politics"]).get("Politics")
    assert math.isnan(arrays.market_trades_count[0])
    assert math.isnan(arrays.market_volume[0])
    assert math.isnan(arrays.unique_traders_count[0])


def test_present_market_stats_fills_market_metrics():
    ctx = make_context(token_id=1, tags=("Politics",), market_trades_count=250)
    arrays = TagMetricsBuilder().build([ctx], tags=["Politics"]).get("Politics")
    assert arrays.market_trades_count[0] == 250.0


# ── usd_buy_volume from wallet stats ─────────────────────────────────────────

def test_usd_buy_volume_taken_from_wallet_stats():
    ws = make_wallet_stats(token_id=1, wallet_buy_usd_volume=42.5)
    ctx = make_context(token_id=1, tags=("Politics",))
    # rebuild with custom wallet stats via direct WalletTokenContext
    from pmresearch.models import WalletTokenContext
    from helpers import make_metadata, make_market_stats
    ctx2 = WalletTokenContext(
        wallet_stats=ws,
        market_stats=make_market_stats(1),
        metadata=make_metadata(1, tags=("Politics",)),
    )
    arrays = TagMetricsBuilder().build([ctx2], tags=["Politics"]).get("Politics")
    assert arrays.usd_buy_volume[0] == pytest.approx(42.5)


# ── roi ───────────────────────────────────────────────────────────────────────

def test_roi_is_nan_when_pnl_is_nan():
    ctx = make_context(token_id=1, tags=("Politics",))
    arrays = TagMetricsBuilder().build([ctx], tags=["Politics"]).get("Politics")
    assert math.isnan(arrays.roi[0])


def test_calc_roi_zero_denominator_returns_nan():
    assert math.isnan(calc_roi(10.0, 0.0))


def test_calc_roi_normal():
    assert calc_roi(5.0, 20.0) == pytest.approx(0.25)


# ── pnl / avg_buy_price are nan (TODO) ───────────────────────────────────────

def test_pnl_is_nan_todo():
    ctx = make_context(token_id=1, tags=("Politics",))
    arrays = TagMetricsBuilder().build([ctx], tags=["Politics"]).get("Politics")
    assert all(math.isnan(v) for v in arrays.pnl)


def test_avg_buy_price_is_nan_todo():
    ctx = make_context(token_id=1, tags=("Politics",))
    arrays = TagMetricsBuilder().build([ctx], tags=["Politics"]).get("Politics")
    assert all(math.isnan(v) for v in arrays.avg_buy_price)


# ── time_to_end ───────────────────────────────────────────────────────────────

def test_time_to_end_positive_when_market_not_yet_ended():
    from datetime import datetime, timezone, timedelta
    first_trade = datetime(2025, 1, 1, tzinfo=timezone.utc)
    end_ts = first_trade + timedelta(hours=48)
    hours = calc_time_to_end_hours(first_trade, end_ts)
    assert hours == pytest.approx(48.0)


def test_time_to_end_nan_when_end_ts_missing():
    from datetime import datetime, timezone
    assert math.isnan(calc_time_to_end_hours(datetime(2025, 1, 1, tzinfo=timezone.utc), None))


def test_time_to_end_nan_when_first_trade_missing():
    from datetime import datetime, timezone
    assert math.isnan(calc_time_to_end_hours(None, datetime(2025, 1, 1, tzinfo=timezone.utc)))


# ── summary table / properties ────────────────────────────────────────────────

def test_summary_table_returns_one_row_per_tag():
    ctx = make_context(token_id=1, tags=("Politics",))
    result = TagMetricsBuilder().build([ctx], tags=["Politics", "Sports"])
    table = result.summary_table()
    assert len(table) == 2
    assert {r["tag"] for r in table} == {"Politics", "Sports"}


def test_summary_table_tokens_count():
    contexts = [make_context(token_id=i, tags=("Politics",)) for i in range(3)]
    result = TagMetricsBuilder().build(contexts, tags=["Politics"])
    row = result.summary_table()[0]
    assert row["tokens_count"] == 3


def test_summary_table_total_usd_buy_volume():
    from helpers import make_metadata, make_market_stats
    contexts = []
    for i, vol in enumerate([10.0, 20.0, 30.0]):
        ws = make_wallet_stats(token_id=i, wallet_buy_usd_volume=vol)
        ctx = WalletTokenContext(
            wallet_stats=ws,
            market_stats=make_market_stats(i),
            metadata=make_metadata(i, tags=("Politics",)),
        )
        contexts.append(ctx)
    result = TagMetricsBuilder().build(contexts, tags=["Politics"])
    row = result.summary_table()[0]
    assert row["total_usd_buy_volume"] == pytest.approx(60.0)


def test_winrate_with_all_nan_pnl_is_nan():
    ctx = make_context(token_id=1, tags=("Politics",))
    arrays = TagMetricsBuilder().build([ctx], tags=["Politics"]).get("Politics")
    assert math.isnan(arrays.winrate)


def test_winrate_logic():
    pnl = np.array([1.0, -1.0, 2.0, float("nan")])
    assert calc_winrate(pnl) == pytest.approx(2 / 3)


def test_empty_tag_returns_zero_tokens():
    result = TagMetricsBuilder().build([], tags=["Politics"])
    assert result.get("Politics").tokens_count == 0


# ── build_from_universe_result ────────────────────────────────────────────────

def test_build_from_universe_result_delegates_to_build():
    from pmresearch.models import WalletMarketUniverseResult, SelectionResult
    ctx = make_context(token_id=1, tags=("Politics",))
    universe = WalletMarketUniverseResult(
        wallet_stats_count=1,
        market_stats_count=1,
        metadata_count=1,
        contexts_count=1,
        selected_count=1,
        rejected_count=0,
        pairs=[],
        selection=SelectionResult(selected=[ctx], rejected=[]),
    )
    result = TagMetricsBuilder().build_from_universe_result(universe, tags=["Politics"])
    assert result.get("Politics").tokens_count == 1
