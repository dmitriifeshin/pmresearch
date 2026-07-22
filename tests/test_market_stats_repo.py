"""Tests for TokenMarketStatsRepository — verifies external_data usage without a real DB."""
from datetime import datetime, timezone

from pmresearch.repositories import TokenMarketStatsRepository


class _FakeResult:
    def __init__(self, rows=None):
        self.result_rows = rows or []


class _CapturingClient:
    def __init__(self, rows=None):
        self.calls: list[dict] = []
        self._rows = rows or []

    def query(self, sql, parameters=None, external_data=None):
        self.calls.append({"sql": sql, "parameters": parameters, "external_data": external_data})
        return _FakeResult(self._rows)


# ── empty input ───────────────────────────────────────────────────────────────

def test_empty_token_ids_returns_empty_without_query():
    client = _CapturingClient()
    repo = TokenMarketStatsRepository(client)
    result = repo.get_stats([])
    assert result == []
    assert client.calls == []


# ── external_data ─────────────────────────────────────────────────────────────

def test_uses_external_data():
    client = _CapturingClient()
    repo = TokenMarketStatsRepository(client)
    repo.get_stats([1])
    assert client.calls[0]["external_data"] is not None


def test_external_data_named_input_tokens():
    client = _CapturingClient()
    repo = TokenMarketStatsRepository(client)
    repo.get_stats([1])
    ext = client.calls[0]["external_data"]
    assert ext.files[0].name == "input_tokens"


# ── no IN clause ──────────────────────────────────────────────────────────────

def test_no_in_clause():
    client = _CapturingClient()
    repo = TokenMarketStatsRepository(client)
    repo.get_stats([1, 2, 3])
    sql = client.calls[0]["sql"]
    assert "IN (" not in sql


def test_uses_inner_join_on_input_tokens():
    client = _CapturingClient()
    repo = TokenMarketStatsRepository(client)
    repo.get_stats([1])
    sql = client.calls[0]["sql"].lower()
    assert "inner join" in sql
    assert "input_tokens" in sql


def test_rounds_last_price_for_resolved_tokens():
    client = _CapturingClient()
    repo = TokenMarketStatsRepository(client)
    repo.get_stats([1])

    normalized_sql = " ".join(client.calls[0]["sql"].lower().split())
    assert "left join default.tokens_new as t final" in normalized_sql
    assert "any(t.resolve)" in normalized_sql
    assert "argmax(tr.price, tr.block_ts) >= 5000" in normalized_sql
    assert "10000, 0" in normalized_sql


# ── since / until parameters ──────────────────────────────────────────────────

def test_no_since_until_passes_no_parameters():
    client = _CapturingClient()
    repo = TokenMarketStatsRepository(client)
    repo.get_stats([1])
    assert client.calls[0]["parameters"] is None


def test_since_passed_as_parameter():
    ts = datetime(2024, 1, 1, tzinfo=timezone.utc)
    client = _CapturingClient()
    repo = TokenMarketStatsRepository(client)
    repo.get_stats([1], since=ts)
    params = client.calls[0]["parameters"]
    assert params is not None
    assert params["since"] == ts


def test_until_passed_as_parameter():
    ts = datetime(2024, 12, 31, tzinfo=timezone.utc)
    client = _CapturingClient()
    repo = TokenMarketStatsRepository(client)
    repo.get_stats([1], until=ts)
    params = client.calls[0]["parameters"]
    assert params is not None
    assert params["until"] == ts


def test_since_not_interpolated_into_sql():
    ts = datetime(2024, 1, 1, tzinfo=timezone.utc)
    client = _CapturingClient()
    repo = TokenMarketStatsRepository(client)
    repo.get_stats([1], since=ts)
    assert "2024-01-01" not in client.calls[0]["sql"]


def test_both_since_and_until_in_parameters():
    since = datetime(2024, 1, 1, tzinfo=timezone.utc)
    until = datetime(2024, 12, 31, tzinfo=timezone.utc)
    client = _CapturingClient()
    repo = TokenMarketStatsRepository(client)
    repo.get_stats([1], since=since, until=until)
    params = client.calls[0]["parameters"]
    assert params["since"] == since
    assert params["until"] == until


# ── result mapping ────────────────────────────────────────────────────────────

def test_maps_rows_to_token_market_stats():
    ts = datetime(2024, 6, 1, tzinfo=timezone.utc)
    # columns: token_id, market_first_trade_ts, market_last_trade_ts, last_price,
    #          market_trades_count, market_volume, unique_traders_count
    fake_row = (42, ts, ts, 7500, 200, 100_000, 35)
    client = _CapturingClient(rows=[fake_row])
    repo = TokenMarketStatsRepository(client)
    result = repo.get_stats([42])

    assert len(result) == 1
    r = result[0]
    assert r.token_id == 42
    assert r.last_price == 7500
    assert r.market_trades_count == 200
    assert r.market_volume == 100_000
    assert r.unique_traders_count == 35
