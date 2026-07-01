from __future__ import annotations

import numpy as np
import matplotlib.figure
import matplotlib.pyplot as plt

from .models import TagAnalysisResult, TagMetricArrays

_MARKET_POPULARITY_FIELDS = {
    "market_trades_count": ("Market trades", "trades"),
    "market_volume": ("Market volume", "raw volume"),
    "unique_traders_count": ("Unique traders", "traders"),
}


class TagMetricsPlotter:
    def __init__(self, result: TagAnalysisResult) -> None:
        self.result = result

    # ── per-tag single plots ──────────────────────────────────────────────────

    def plot_roi_distribution(self, tag: str) -> matplotlib.figure.Figure:
        arrays = self.result.get(tag)
        values = _drop_nan(arrays.roi)
        fig, ax = plt.subplots()
        if len(values) == 0:
            _no_data(ax, f"ROI distribution — {tag}")
        else:
            ax.hist(values, bins=30, color="steelblue", edgecolor="white")
            ax.axvline(float(np.median(values)), color="red", linestyle="--",
                       label=f"median {np.median(values):.2f}")
            ax.legend()
            ax.set_title(f"ROI distribution — {tag}  (n={len(values)})")
            ax.set_xlabel("ROI")
            ax.set_ylabel("count")
        fig.tight_layout()
        return fig

    def plot_pnl_distribution(self, tag: str) -> matplotlib.figure.Figure:
        arrays = self.result.get(tag)
        values = _drop_nan(arrays.pnl)
        fig, ax = plt.subplots()
        if len(values) == 0:
            _no_data(ax, f"PnL distribution — {tag}")
        else:
            ax.hist(values, bins=30, color="mediumseagreen", edgecolor="white")
            ax.axvline(0, color="black", linestyle=":", linewidth=1)
            ax.axvline(float(np.median(values)), color="red", linestyle="--",
                       label=f"median {np.median(values):.4f}")
            ax.legend()
            ax.set_title(f"PnL distribution — {tag}  (n={len(values)})")
            ax.set_xlabel("PnL (USD)")
            ax.set_ylabel("count")
        fig.tight_layout()
        return fig

    def plot_usd_buy_volume_distribution(self, tag: str) -> matplotlib.figure.Figure:
        arrays = self.result.get(tag)
        values = _drop_nan(arrays.usd_buy_volume)
        fig, ax = plt.subplots()
        if len(values) == 0:
            _no_data(ax, f"USD buy volume — {tag}")
        else:
            ax.hist(values, bins=30, color="darkorange", edgecolor="white")
            ax.axvline(float(np.median(values)), color="red", linestyle="--",
                       label=f"median {np.median(values):.2f}")
            ax.legend()
            ax.set_title(f"USD buy volume — {tag}  (n={len(values)})")
            ax.set_xlabel("USD buy volume")
            ax.set_ylabel("count")
        fig.tight_layout()
        return fig

    def plot_time_to_end_distribution(self, tag: str) -> matplotlib.figure.Figure:
        arrays = self.result.get(tag)
        values = _drop_nan(arrays.time_to_end_at_entry_hours)
        fig, ax = plt.subplots()
        if len(values) == 0:
            _no_data(ax, f"Time to end at entry — {tag}")
        else:
            ax.hist(values, bins=30, color="mediumpurple", edgecolor="white")
            ax.axvline(float(np.median(values)), color="red", linestyle="--",
                       label=f"median {np.median(values):.1f} h")
            ax.legend()
            ax.set_title(f"Time to market end at entry — {tag}  (n={len(values)})")
            ax.set_xlabel("hours until end_ts")
            ax.set_ylabel("count")
        fig.tight_layout()
        return fig

    def plot_market_popularity_distribution(
        self,
        tag: str,
        kind: str = "market_trades_count",
    ) -> matplotlib.figure.Figure:
        if kind not in _MARKET_POPULARITY_FIELDS:
            raise ValueError(
                f"Unknown kind {kind!r}. Choose from: {list(_MARKET_POPULARITY_FIELDS)}"
            )
        label, xlabel = _MARKET_POPULARITY_FIELDS[kind]
        arrays = self.result.get(tag)
        values = _drop_nan(getattr(arrays, kind))
        fig, ax = plt.subplots()
        if len(values) == 0:
            _no_data(ax, f"{label} — {tag}")
        else:
            ax.hist(values, bins=30, color="teal", edgecolor="white")
            ax.axvline(float(np.median(values)), color="red", linestyle="--",
                       label=f"median {np.median(values):.0f}")
            ax.legend()
            ax.set_title(f"{label} — {tag}  (n={len(values)})")
            ax.set_xlabel(xlabel)
            ax.set_ylabel("count")
        fig.tight_layout()
        return fig

    def plot_pnl_vs_buy_volume(self, tag: str) -> matplotlib.figure.Figure:
        arrays = self.result.get(tag)
        mask = ~(np.isnan(arrays.pnl_vs_buy_volume_x) | np.isnan(arrays.pnl_vs_buy_volume_y))
        x = arrays.pnl_vs_buy_volume_x[mask]
        y = arrays.pnl_vs_buy_volume_y[mask]
        fig, ax = plt.subplots()
        if len(x) == 0:
            _no_data(ax, f"PnL vs USD buy volume — {tag}")
        else:
            ax.scatter(x, y, alpha=0.5, color="steelblue", s=20)
            ax.axhline(0, color="black", linestyle=":", linewidth=1)
            ax.set_title(f"PnL vs USD buy volume — {tag}  (n={len(x)})")
            ax.set_xlabel("USD buy volume")
            ax.set_ylabel("PnL (USD)")
        fig.tight_layout()
        return fig

    def plot_all_for_tag(self, tag: str) -> list[matplotlib.figure.Figure]:
        return [
            self.plot_roi_distribution(tag),
            self.plot_pnl_distribution(tag),
            self.plot_usd_buy_volume_distribution(tag),
            self.plot_time_to_end_distribution(tag),
            self.plot_market_popularity_distribution(tag, kind="market_trades_count"),
            self.plot_pnl_vs_buy_volume(tag),
        ]

    # ── cross-tag overview ────────────────────────────────────────────────────

    def plot_total_pnl_by_tag(self) -> matplotlib.figure.Figure:
        rows = self.result.summary_table()
        return _bar_chart(
            labels=[r["tag"] for r in rows],
            values=[r["total_pnl"] for r in rows],
            title="Total PnL by tag",
            ylabel="PnL (USD)",
            color="mediumseagreen",
        )

    def plot_median_roi_by_tag(self) -> matplotlib.figure.Figure:
        rows = self.result.summary_table()
        return _bar_chart(
            labels=[r["tag"] for r in rows],
            values=[r["median_roi"] for r in rows],
            title="Median ROI by tag",
            ylabel="ROI",
            color="steelblue",
        )

    def plot_total_buy_volume_by_tag(self) -> matplotlib.figure.Figure:
        rows = self.result.summary_table()
        return _bar_chart(
            labels=[r["tag"] for r in rows],
            values=[r["total_usd_buy_volume"] for r in rows],
            title="Total USD buy volume by tag",
            ylabel="USD buy volume",
            color="darkorange",
        )

    def plot_tokens_count_by_tag(self) -> matplotlib.figure.Figure:
        rows = self.result.summary_table()
        return _bar_chart(
            labels=[r["tag"] for r in rows],
            values=[r["tokens_count"] for r in rows],
            title="Token count by tag",
            ylabel="tokens",
            color="mediumpurple",
        )


# ── helpers ───────────────────────────────────────────────────────────────────

def _drop_nan(arr: np.ndarray) -> np.ndarray:
    return arr[~np.isnan(arr.astype(float))]


def _no_data(ax: plt.Axes, title: str) -> None:
    ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes,
            fontsize=12, color="gray")
    ax.set_title(title)


def _bar_chart(
    labels: list,
    values: list,
    title: str,
    ylabel: str,
    color: str,
) -> matplotlib.figure.Figure:
    fig, ax = plt.subplots()
    if not labels:
        _no_data(ax, title)
        fig.tight_layout()
        return fig
    x = range(len(labels))
    ax.bar(x, values, color=color, edgecolor="white")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, rotation=30, ha="right")
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    fig.tight_layout()
    return fig
