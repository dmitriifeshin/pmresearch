"""Tests for TagMetricsPlotter — verifies Figure output and nan-safety."""
import math

import matplotlib
import matplotlib.figure
import numpy as np
import pytest

matplotlib.use("Agg")  # no display needed in CI / headless

from pmresearch.tag_analysis import TagMetricsBuilder, TagMetricsPlotter
from pmresearch.tag_analysis.models import TagAnalysisResult, TagMetricArrays

from helpers import make_context


# ── fixtures ──────────────────────────────────────────────────────────────────

def _make_arrays(tag: str, n: int = 5, all_nan: bool = False) -> TagMetricArrays:
    if n == 0 or all_nan:
        vals = np.full(n, float("nan"))
    else:
        vals = np.arange(1, n + 1, dtype=float)

    return TagMetricArrays(
        tag=tag,
        token_ids=np.arange(n, dtype=object),
        market_ids=np.arange(n, dtype=object),
        questions=np.array([f"Q{i}" for i in range(n)], dtype=object),
        slugs=np.array([f"slug-{i}" for i in range(n)], dtype=object),
        pnl=vals.copy(),
        roi=vals.copy() * 0.1,
        usd_buy_volume=vals.copy() * 10,
        avg_buy_price=vals.copy() * 0.5,
        time_to_end_at_entry_hours=vals.copy() * 24,
        market_trades_count=vals.copy() * 100,
        market_volume=vals.copy() * 1000,
        unique_traders_count=vals.copy() * 20,
        pnl_vs_buy_volume_x=vals.copy() * 10,
        pnl_vs_buy_volume_y=vals.copy(),
    )


def _make_result(tag: str = "Politics", n: int = 5) -> TagAnalysisResult:
    return TagAnalysisResult(
        tags=[tag],
        by_tag={tag: _make_arrays(tag, n=n)},
    )


def _plotter(tag: str = "Politics", n: int = 5) -> TagMetricsPlotter:
    return TagMetricsPlotter(_make_result(tag=tag, n=n))


# ── each method returns a Figure ──────────────────────────────────────────────

def test_plot_roi_distribution_returns_figure():
    fig = _plotter().plot_roi_distribution("Politics")
    assert isinstance(fig, matplotlib.figure.Figure)


def test_plot_pnl_distribution_returns_figure():
    fig = _plotter().plot_pnl_distribution("Politics")
    assert isinstance(fig, matplotlib.figure.Figure)


def test_plot_usd_buy_volume_distribution_returns_figure():
    fig = _plotter().plot_usd_buy_volume_distribution("Politics")
    assert isinstance(fig, matplotlib.figure.Figure)


def test_plot_time_to_end_distribution_returns_figure():
    fig = _plotter().plot_time_to_end_distribution("Politics")
    assert isinstance(fig, matplotlib.figure.Figure)


def test_plot_market_popularity_distribution_returns_figure():
    fig = _plotter().plot_market_popularity_distribution("Politics")
    assert isinstance(fig, matplotlib.figure.Figure)


def test_plot_pnl_vs_buy_volume_returns_figure():
    fig = _plotter().plot_pnl_vs_buy_volume("Politics")
    assert isinstance(fig, matplotlib.figure.Figure)


def test_plot_all_for_tag_returns_list_of_figures():
    figs = _plotter().plot_all_for_tag("Politics")
    assert isinstance(figs, list)
    assert len(figs) == 6
    assert all(isinstance(f, matplotlib.figure.Figure) for f in figs)


# ── cross-tag overview ────────────────────────────────────────────────────────

def _multi_plotter() -> TagMetricsPlotter:
    result = TagAnalysisResult(
        tags=["Politics", "Sports", "Crypto"],
        by_tag={
            "Politics": _make_arrays("Politics", n=5),
            "Sports": _make_arrays("Sports", n=3),
            "Crypto": _make_arrays("Crypto", n=0),
        },
    )
    return TagMetricsPlotter(result)


def test_plot_total_pnl_by_tag_returns_figure():
    assert isinstance(_multi_plotter().plot_total_pnl_by_tag(), matplotlib.figure.Figure)


def test_plot_median_roi_by_tag_returns_figure():
    assert isinstance(_multi_plotter().plot_median_roi_by_tag(), matplotlib.figure.Figure)


def test_plot_total_buy_volume_by_tag_returns_figure():
    assert isinstance(_multi_plotter().plot_total_buy_volume_by_tag(), matplotlib.figure.Figure)


def test_plot_tokens_count_by_tag_returns_figure():
    assert isinstance(_multi_plotter().plot_tokens_count_by_tag(), matplotlib.figure.Figure)


# ── nan safety ────────────────────────────────────────────────────────────────

def test_plot_roi_distribution_with_all_nan_does_not_raise():
    plotter = TagMetricsPlotter(TagAnalysisResult(
        tags=["Politics"],
        by_tag={"Politics": _make_arrays("Politics", n=5, all_nan=True)},
    ))
    fig = plotter.plot_roi_distribution("Politics")
    assert isinstance(fig, matplotlib.figure.Figure)


def test_plot_pnl_vs_buy_volume_with_all_nan_does_not_raise():
    plotter = TagMetricsPlotter(TagAnalysisResult(
        tags=["Politics"],
        by_tag={"Politics": _make_arrays("Politics", n=5, all_nan=True)},
    ))
    fig = plotter.plot_pnl_vs_buy_volume("Politics")
    assert isinstance(fig, matplotlib.figure.Figure)


# ── empty tag ─────────────────────────────────────────────────────────────────

def test_plot_roi_distribution_empty_tag_returns_figure():
    fig = _plotter(n=0).plot_roi_distribution("Politics")
    assert isinstance(fig, matplotlib.figure.Figure)


def test_plot_all_for_tag_empty_returns_six_figures():
    figs = _plotter(n=0).plot_all_for_tag("Politics")
    assert len(figs) == 6
    assert all(isinstance(f, matplotlib.figure.Figure) for f in figs)


# ── integration: builder → plotter ────────────────────────────────────────────

def test_builder_to_plotter_end_to_end():
    contexts = [make_context(token_id=i, tags=("Politics",)) for i in range(3)]
    result = TagMetricsBuilder().build(contexts, tags=["Politics"])
    plotter = TagMetricsPlotter(result)
    fig = plotter.plot_usd_buy_volume_distribution("Politics")
    assert isinstance(fig, matplotlib.figure.Figure)


# ── invalid kind raises ValueError ────────────────────────────────────────────

def test_plot_market_popularity_invalid_kind_raises():
    with pytest.raises(ValueError, match="Unknown kind"):
        _plotter().plot_market_popularity_distribution("Politics", kind="bogus")
