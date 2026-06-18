from pmresearch.filters import BinaryOutcomeFilter, ExcludeTagsFilter, MinTradesFilter
from pmresearch.selector import TokenSelector

from helpers import make_token


def test_all_pass():
    selector = TokenSelector([MinTradesFilter(1)])
    result = selector.select([make_token(trades_count=5), make_token(token_id=2, trades_count=10)])
    assert len(result.selected) == 2
    assert len(result.rejected) == 0


def test_all_rejected():
    selector = TokenSelector([MinTradesFilter(100)])
    result = selector.select([make_token(trades_count=5)])
    assert len(result.selected) == 0
    assert len(result.rejected) == 1


def test_stops_at_first_failing_filter():
    calls = []

    class TrackingFilter:
        def __init__(self, name, keep):
            self.name = name
            self._keep = keep

        def __call__(self, token):
            calls.append(self.name)
            from pmresearch.models import FilterDecision
            return FilterDecision(keep=self._keep, reason=f"{self.name} rejected")

    selector = TokenSelector([
        TrackingFilter("first", keep=False),
        TrackingFilter("second", keep=True),
    ])
    selector.select([make_token()])

    assert "first" in calls
    assert "second" not in calls  # short-circuit


def test_rejection_reason_recorded():
    selector = TokenSelector([MinTradesFilter(50)])
    result = selector.select([make_token(trades_count=3)])
    assert result.rejected[0].reason
    assert "3" in result.rejected[0].reason


def test_stats_counts_by_reason():
    selector = TokenSelector([ExcludeTagsFilter({"Crypto"}), MinTradesFilter(50)])
    tokens = [
        make_token(token_id=1, tags=("Crypto",), trades_count=100),
        make_token(token_id=2, tags=("Crypto",), trades_count=100),
        make_token(token_id=3, tags=(), trades_count=1),
    ]
    result = selector.select(tokens)
    stats = result.stats
    assert stats.get("excluded tags: ['Crypto']") == 2
    assert len(result.selected) == 0


def test_mixed_pass_and_reject():
    selector = TokenSelector([BinaryOutcomeFilter(), MinTradesFilter(5)])
    tokens = [
        make_token(token_id=1, outcome="Yes", trades_count=10),   # pass
        make_token(token_id=2, outcome="Draw", trades_count=10),  # rejected by binary
        make_token(token_id=3, outcome="No", trades_count=2),     # rejected by min_trades
    ]
    result = selector.select(tokens)
    assert len(result.selected) == 1
    assert result.selected[0].traded.token_id == 1
    assert len(result.rejected) == 2
