from __future__ import annotations

from collections import defaultdict

import numpy as np

from ..models import WalletMarketUniverseResult, WalletTokenContext
from .metrics import calc_roi, calc_time_to_end_hours
from .models import TagAnalysisResult, TagMetricArrays


class TagMetricsBuilder:
    def build(
        self,
        tokens: list[WalletTokenContext],
        tags: list[str],
    ) -> TagAnalysisResult:
        tag_set = set(tags)
        groups: dict[str, list[WalletTokenContext]] = defaultdict(list)

        for ctx in tokens:
            if ctx.metadata is None:
                continue
            for t in ctx.metadata.tags:
                if t in tag_set:
                    groups[t].append(ctx)

        by_tag = {tag: self._build_arrays(tag, groups.get(tag, [])) for tag in tags}
        return TagAnalysisResult(tags=list(tags), by_tag=by_tag)

    def build_from_universe_result(
        self,
        result: WalletMarketUniverseResult,
        tags: list[str],
    ) -> TagAnalysisResult:
        return self.build(result.selection.selected, tags)

    # ── private ───────────────────────────────────────────────────────────────

    def _build_arrays(self, tag: str, contexts: list[WalletTokenContext]) -> TagMetricArrays:
        if not contexts:
            return _empty_arrays(tag)

        token_ids: list = []
        market_ids: list = []
        questions: list = []
        slugs: list = []
        pnls: list[float] = []
        rois: list[float] = []
        buy_vols: list[float] = []
        avg_prices: list[float] = []
        times_to_end: list[float] = []
        mkt_trades: list[float] = []
        mkt_vols: list[float] = []
        uniq_traders: list[float] = []

        for ctx in contexts:
            ws = ctx.wallet_stats
            ms = ctx.market_stats
            meta = ctx.metadata  # guaranteed non-None (filtered in build())

            token_ids.append(ws.token_id)
            market_ids.append(meta.market_id)
            questions.append(meta.question)
            slugs.append(meta.slug)

            usd_buy = float(ws.wallet_buy_usd_volume)
            buy_vols.append(usd_buy)

            pnl = self._extract_pnl(ctx)
            pnls.append(pnl)
            rois.append(calc_roi(pnl, usd_buy))

            avg_prices.append(self._extract_avg_buy_price(ctx))

            times_to_end.append(
                calc_time_to_end_hours(ws.wallet_first_trade_ts, meta.end_ts)
            )

            if ms is not None:
                mkt_trades.append(float(ms.market_trades_count))
                mkt_vols.append(float(ms.market_volume))
                uniq_traders.append(float(ms.unique_traders_count))
            else:
                mkt_trades.append(float("nan"))
                mkt_vols.append(float("nan"))
                uniq_traders.append(float("nan"))

        pnl_arr = np.array(pnls, dtype=float)
        buy_vol_arr = np.array(buy_vols, dtype=float)

        return TagMetricArrays(
            tag=tag,
            token_ids=np.array(token_ids, dtype=object),
            market_ids=np.array(market_ids, dtype=object),
            questions=np.array(questions, dtype=object),
            slugs=np.array(slugs, dtype=object),
            pnl=pnl_arr,
            roi=np.array(rois, dtype=float),
            usd_buy_volume=buy_vol_arr,
            avg_buy_price=np.array(avg_prices, dtype=float),
            time_to_end_at_entry_hours=np.array(times_to_end, dtype=float),
            market_trades_count=np.array(mkt_trades, dtype=float),
            market_volume=np.array(mkt_vols, dtype=float),
            unique_traders_count=np.array(uniq_traders, dtype=float),
            pnl_vs_buy_volume_x=buy_vol_arr.copy(),
            pnl_vs_buy_volume_y=pnl_arr.copy(),
        )

    @staticmethod
    def _extract_pnl(ctx: WalletTokenContext) -> float:
        ws = ctx.wallet_stats
        ms = ctx.market_stats
        # Both volumes are in raw token units (1e6 = 1 human token):
        #   buy_token_volume  = sum(amount * 10000 / price)  [side=0, amount=micro-USDC]
        #   sell_token_volume = sum(amount)                   [side=1, amount=raw token units]
        remaining = max(0.0, ws.wallet_buy_token_volume - ws.wallet_sell_token_volume)
        if remaining > 0:
            if ms is None:
                return float("nan")
            # last_price is price_real * 10000; convert remaining raw units → USDC
            unrealized = remaining * ms.last_price / (10_000 * 1_000_000)
        else:
            unrealized = 0.0
        return ws.wallet_sell_usd_volume + unrealized - ws.wallet_buy_usd_volume

    @staticmethod
    def _extract_avg_buy_price(ctx: WalletTokenContext) -> float:
        ws = ctx.wallet_stats
        if ws.wallet_buy_token_volume == 0:
            return float("nan")
        # buy_token_volume is in raw units (1e6 = 1 token); result in USDC/token
        return ws.wallet_buy_usd_volume * 1_000_000 / ws.wallet_buy_token_volume


def _empty_arrays(tag: str) -> TagMetricArrays:
    empty_f = np.array([], dtype=float)
    empty_o = np.array([], dtype=object)
    return TagMetricArrays(
        tag=tag,
        token_ids=empty_o.copy(),
        market_ids=empty_o.copy(),
        questions=empty_o.copy(),
        slugs=empty_o.copy(),
        pnl=empty_f.copy(),
        roi=empty_f.copy(),
        usd_buy_volume=empty_f.copy(),
        avg_buy_price=empty_f.copy(),
        time_to_end_at_entry_hours=empty_f.copy(),
        market_trades_count=empty_f.copy(),
        market_volume=empty_f.copy(),
        unique_traders_count=empty_f.copy(),
        pnl_vs_buy_volume_x=empty_f.copy(),
        pnl_vs_buy_volume_y=empty_f.copy(),
    )
