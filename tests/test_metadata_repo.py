"""
Tests for TokenMetadataRepository.enrich — verifies external_data usage without a real DB.
"""
from datetime import datetime, timezone

from pmresearch.repositories import TokenMetadataRepository

from helpers import make_traded_stats


class _FakeResult:
    def __init__(self, rows=None):
        self.result_rows = rows or []


class _CapturingClient:
    """Records every query() call for assertion."""

    def __init__(self, rows=None):
        self.calls: list[dict] = []
        self._rows = rows or []

    def query(self, sql, parameters=None, external_data=None):
        self.calls.append({"sql": sql, "parameters": parameters, "external_data": external_data})
        return _FakeResult(self._rows)


# ── no IN clause ─────────────────────────────────────────────────────────────

def test_enrich_does_not_use_in_clause():
    client = _CapturingClient()
    repo = TokenMetadataRepository(client)
    repo.enrich([make_traded_stats(token_id=42)])

    sql = client.calls[0]["sql"]
    assert "IN (" not in sql


# ── external_data presence and name ──────────────────────────────────────────

def test_enrich_passes_external_data():
    client = _CapturingClient()
    repo = TokenMetadataRepository(client)
    repo.enrich([make_traded_stats(token_id=1)])

    ext = client.calls[0]["external_data"]
    assert ext is not None


def test_enrich_external_data_named_input_tokens():
    client = _CapturingClient()
    repo = TokenMetadataRepository(client)
    repo.enrich([make_traded_stats(token_id=1)])

    ext = client.calls[0]["external_data"]
    assert ext.files[0].name == "input_tokens"


# ── metadata_as_of ────────────────────────────────────────────────────────────

def test_enrich_no_metadata_as_of_passes_no_parameters():
    client = _CapturingClient()
    repo = TokenMetadataRepository(client)
    repo.enrich([make_traded_stats()])

    assert client.calls[0]["parameters"] is None


def test_enrich_metadata_as_of_passed_as_parameter():
    ts = datetime(2025, 6, 1, tzinfo=timezone.utc)
    client = _CapturingClient()
    repo = TokenMetadataRepository(client)
    repo.enrich([make_traded_stats()], metadata_as_of=ts)

    params = client.calls[0]["parameters"]
    assert params is not None
    assert params["metadata_as_of"] == ts


def test_enrich_metadata_as_of_not_in_sql_string():
    ts = datetime(2025, 6, 1, tzinfo=timezone.utc)
    client = _CapturingClient()
    repo = TokenMetadataRepository(client)
    repo.enrich([make_traded_stats()], metadata_as_of=ts)

    # timestamp must not be interpolated directly into SQL
    assert "2025-06-01" not in client.calls[0]["sql"]


# ── empty input ───────────────────────────────────────────────────────────────

def test_enrich_empty_returns_empty_without_query():
    client = _CapturingClient()
    repo = TokenMetadataRepository(client)
    result = repo.enrich([])

    assert result == []
    assert client.calls == []


# ── result mapping ────────────────────────────────────────────────────────────

def test_enrich_maps_rows_to_enriched_tokens():
    traded = make_traded_stats(token_id=99)
    fake_row = (
        99, "Yes", 7, "cond_x", "Will it?", "will-it", None, ["Politics"],
    )
    client = _CapturingClient(rows=[fake_row])
    repo = TokenMetadataRepository(client)
    result = repo.enrich([traded])

    assert len(result) == 1
    assert result[0].traded.token_id == 99
    assert result[0].metadata.outcome == "Yes"
    assert result[0].metadata.tags == ("Politics",)


def test_enrich_skips_tokens_without_metadata():
    traded = make_traded_stats(token_id=7)
    client = _CapturingClient(rows=[])  # DB returns nothing
    repo = TokenMetadataRepository(client)
    result = repo.enrich([traded])

    assert result == []
