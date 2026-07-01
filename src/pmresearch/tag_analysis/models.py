from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .metrics import calc_winrate, nanmean_safe, nanmedian_safe


@dataclass(slots=True)
class TagMetricArrays:
    """Per-tag metric arrays. All per-token arrays have the same length."""

    tag: str

    # Identity (dtype=object — token_id is UInt256 and can exceed int64)
    token_ids: np.ndarray
    market_ids: np.ndarray
    questions: np.ndarray
    slugs: np.ndarray

    # Core per-token metrics
    pnl: np.ndarray                      # gross pnl in USD (sell_usd + unrealized - buy_usd)
    roi: np.ndarray                      # pnl / usd_buy_volume; np.nan when usd_buy_volume=0 or pnl=nan
    net_pnl: np.ndarray                  # pnl - fee_usd
    net_roi: np.ndarray                  # net_pnl / usd_buy_volume
    usd_buy_volume: np.ndarray           # wallet_buy_usd_volume (USD spent on buys)
    avg_buy_price: np.ndarray            # avg entry price in USD/token
    time_to_end_at_entry_hours: np.ndarray  # metadata.end_ts - wallet_first_trade_ts in hours

    # Market popularity (np.nan when market_stats is None)
    market_trades_count: np.ndarray
    market_volume: np.ndarray
    unique_traders_count: np.ndarray

    # Scatter: x=usd_buy_volume, y=pnl (same length; plotter filters nan pairs)
    pnl_vs_buy_volume_x: np.ndarray
    pnl_vs_buy_volume_y: np.ndarray

    # ── summary properties ────────────────────────────────────────────────────

    @property
    def tokens_count(self) -> int:
        return len(self.token_ids)

    @property
    def total_pnl(self) -> float:
        return float(np.nansum(self.pnl))

    @property
    def total_net_pnl(self) -> float:
        return float(np.nansum(self.net_pnl))

    @property
    def total_usd_buy_volume(self) -> float:
        return float(np.nansum(self.usd_buy_volume))

    @property
    def mean_roi(self) -> float:
        return nanmean_safe(self.roi)

    @property
    def median_roi(self) -> float:
        return nanmedian_safe(self.roi)

    @property
    def mean_net_roi(self) -> float:
        return nanmean_safe(self.net_roi)

    @property
    def median_net_roi(self) -> float:
        return nanmedian_safe(self.net_roi)

    @property
    def winrate(self) -> float:
        return calc_winrate(self.pnl)

    @property
    def net_winrate(self) -> float:
        return calc_winrate(self.net_pnl)


@dataclass(slots=True)
class TagAnalysisResult:
    tags: list[str]
    by_tag: dict[str, TagMetricArrays]

    def get(self, tag: str) -> TagMetricArrays:
        return self.by_tag[tag]

    def available_tags(self) -> list[str]:
        return list(self.by_tag.keys())

    def summary_table(self) -> list[dict]:
        return [
            {
                "tag": tag,
                "tokens_count": self.by_tag[tag].tokens_count,
                "total_usd_buy_volume": self.by_tag[tag].total_usd_buy_volume,
                "total_pnl": self.by_tag[tag].total_pnl,
                "total_net_pnl": self.by_tag[tag].total_net_pnl,
                "mean_roi": self.by_tag[tag].mean_roi,
                "median_roi": self.by_tag[tag].median_roi,
                "mean_net_roi": self.by_tag[tag].mean_net_roi,
                "median_net_roi": self.by_tag[tag].median_net_roi,
                "winrate": self.by_tag[tag].winrate,
                "net_winrate": self.by_tag[tag].net_winrate,
            }
            for tag in self.tags
            if tag in self.by_tag
        ]
