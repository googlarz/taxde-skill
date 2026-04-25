"""Tests for scripts/life_events.py"""

import pytest
from datetime import date, timedelta

import life_events as le


# ── add_event ─────────────────────────────────────────────────────────────────

def test_add_event_returns_dict():
    e = le.add_event("move", "Moved to Berlin")
    assert isinstance(e, dict)


def test_add_event_id_format():
    e = le.add_event("job_change", "New job at Acme")
    parts = e["id"].split("-")
    assert len(parts) >= 2
    assert len(parts[0]) == 8


def test_add_event_defaults():
    today = date.today().isoformat()
    e = le.add_event("other", "Misc event")
    assert e["event_date"] == today
    assert e["description"] == ""
    assert e["financial_note"] == ""


def test_add_event_custom_date():
    e = le.add_event("child", "Baby born", event_date="2025-03-15")
    assert e["event_date"] == "2025-03-15"


def test_add_event_financial_note():
    e = le.add_event("windfall", "Inheritance", financial_note="€20 000 received")
    assert e["financial_note"] == "€20 000 received"


def test_add_event_all_types():
    types = ["job_change", "move", "marriage", "child", "health",
             "windfall", "major_purchase", "other"]
    for etype in types:
        e = le.add_event(etype, f"Event: {etype}")
        assert e["event_type"] == etype


# ── get_events ────────────────────────────────────────────────────────────────

def test_get_events_returns_list():
    le.add_event("move", "Moved flats")
    events = le.get_events()
    assert isinstance(events, list)
    assert len(events) >= 1


def test_get_events_ordered_desc():
    le.add_event("health", "Surgery", event_date="2025-01-01")
    le.add_event("job_change", "Promotion", event_date="2025-06-01")
    events = le.get_events(months=24)
    dates = [e["event_date"] for e in events]
    assert dates == sorted(dates, reverse=True)


# ── get_events_near ───────────────────────────────────────────────────────────

def test_get_events_near_finds_nearby():
    le.add_event("move", "Moved house", event_date="2026-03-15")
    nearby = le.get_events_near("2026-03", window_months=1)
    assert any(e["title"] == "Moved house" for e in nearby)


def test_get_events_near_excludes_distant():
    le.add_event("marriage", "Got married", event_date="2026-01-10")
    nearby = le.get_events_near("2026-06", window_months=1)
    assert not any(e["title"] == "Got married" for e in nearby)


def test_get_events_near_invalid_month_returns_empty():
    result = le.get_events_near("not-a-month")
    assert result == []


# ── get_context_for_anomaly ───────────────────────────────────────────────────

def test_get_context_for_anomaly_match():
    le.add_event("move", "Moved to new city", event_date="2026-03-10",
                 financial_note="high moving costs")
    ctx = le.get_context_for_anomaly("2026-03", "spending")
    assert ctx is not None
    assert "Moved to new city" in ctx


def test_get_context_for_anomaly_no_match():
    ctx = le.get_context_for_anomaly("2020-01", "spending")
    assert ctx is None


def test_get_context_for_anomaly_uses_financial_note():
    le.add_event("windfall", "Bonus received", event_date="2026-04-20",
                 financial_note="€5 000 one-time bonus")
    ctx = le.get_context_for_anomaly("2026-04", "income")
    assert ctx is not None
    assert "€5 000 one-time bonus" in ctx


def test_get_context_for_anomaly_fallback_without_note():
    le.add_event("health", "Hospital stay", event_date="2026-02-05")
    ctx = le.get_context_for_anomaly("2026-02", "expenses")
    assert ctx is not None
    assert "Hospital stay" in ctx
    assert "expenses" in ctx
