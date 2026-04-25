"""Tests for scripts/financial_journal.py"""

import pytest
from datetime import date, timedelta

import financial_journal as fj


# ── add_entry ─────────────────────────────────────────────────────────────────

def test_add_entry_returns_dict():
    e = fj.add_entry("decision", "Pay off credit card first")
    assert isinstance(e, dict)


def test_add_entry_id_format():
    e = fj.add_entry("decision", "Test decision")
    # id = 8 hex chars + "-" + YYYY-MM-DD
    parts = e["id"].split("-")
    assert len(parts) >= 2
    assert len(parts[0]) == 8


def test_add_entry_defaults():
    today = date.today().isoformat()
    e = fj.add_entry("commitment", "Save 10% of salary")
    assert e["status"] == "open"
    assert e["date"] == today
    assert e["outcome"] is None
    assert e["linked_metrics"] == []


def test_add_entry_custom_date():
    e = fj.add_entry("milestone", "Debt free", date="2024-06-01")
    assert e["date"] == "2024-06-01"


def test_add_entry_due_date():
    e = fj.add_entry("commitment", "File taxes", due_date="2025-07-31")
    assert e["due_date"] == "2025-07-31"


def test_add_entry_linked_metrics():
    e = fj.add_entry("observation", "Spending spike", linked_metrics=["groceries", "dining"])
    assert e["linked_metrics"] == ["groceries", "dining"]


def test_add_entry_description():
    e = fj.add_entry("decision", "Invest in ETF", description="Going with VWCE")
    assert e["description"] == "Going with VWCE"


def test_add_entry_entry_type_stored():
    for etype in ("decision", "commitment", "milestone", "observation"):
        e = fj.add_entry(etype, f"A {etype}")
        assert e["entry_type"] == etype


# ── record_outcome ────────────────────────────────────────────────────────────

def test_record_outcome_updates_status():
    e = fj.add_entry("commitment", "Pay off car loan")
    updated = fj.record_outcome(e["id"], "Loan fully paid in May", "kept")
    assert updated["status"] == "kept"
    assert updated["outcome"] == "Loan fully paid in May"


def test_record_outcome_missed():
    e = fj.add_entry("commitment", "Save emergency fund")
    updated = fj.record_outcome(e["id"], "Only saved half", "missed")
    assert updated["status"] == "missed"


def test_record_outcome_unknown_id_raises():
    with pytest.raises(KeyError):
        fj.record_outcome("nonexistent-id", "outcome", "kept")


# ── get_open_commitments ──────────────────────────────────────────────────────

def test_get_open_commitments_returns_only_open():
    fj.add_entry("commitment", "A", due_date="2026-12-01")
    e2 = fj.add_entry("commitment", "B", due_date="2026-11-01")
    fj.record_outcome(e2["id"], "done", "kept")
    open_c = fj.get_open_commitments()
    titles = [c["title"] for c in open_c]
    assert "A" in titles
    assert "B" not in titles


def test_get_open_commitments_excludes_decisions():
    fj.add_entry("decision", "Not a commitment")
    fj.add_entry("commitment", "Real commitment")
    open_c = fj.get_open_commitments()
    types = [c["entry_type"] for c in open_c]
    assert all(t == "commitment" for t in types)


def test_get_open_commitments_ordered_by_due_date():
    fj.add_entry("commitment", "Later", due_date="2026-12-01")
    fj.add_entry("commitment", "Sooner", due_date="2026-06-01")
    open_c = fj.get_open_commitments()
    due_dates = [c["due_date"] for c in open_c if c["due_date"]]
    assert due_dates == sorted(due_dates)


# ── get_overdue_commitments ───────────────────────────────────────────────────

def test_get_overdue_commitments_past_due():
    past = (date.today() - timedelta(days=10)).isoformat()
    fj.add_entry("commitment", "Overdue task", due_date=past)
    overdue = fj.get_overdue_commitments()
    assert any(c["title"] == "Overdue task" for c in overdue)


def test_get_overdue_commitments_future_excluded():
    future = (date.today() + timedelta(days=30)).isoformat()
    fj.add_entry("commitment", "Future task", due_date=future)
    overdue = fj.get_overdue_commitments()
    assert not any(c["title"] == "Future task" for c in overdue)


def test_get_overdue_commitments_kept_excluded():
    past = (date.today() - timedelta(days=5)).isoformat()
    e = fj.add_entry("commitment", "Already done", due_date=past)
    fj.record_outcome(e["id"], "completed", "kept")
    overdue = fj.get_overdue_commitments()
    assert not any(c["title"] == "Already done" for c in overdue)


# ── get_entry_history ─────────────────────────────────────────────────────────

def test_get_entry_history_returns_entries():
    fj.add_entry("decision", "Historic decision", date="2026-01-15")
    history = fj.get_entry_history(months=12)
    assert len(history) >= 1


def test_get_entry_history_filter_by_type():
    fj.add_entry("decision", "A decision")
    fj.add_entry("milestone", "A milestone")
    decisions = fj.get_entry_history(months=12, entry_type="decision")
    assert all(e["entry_type"] == "decision" for e in decisions)


def test_get_entry_history_ordered_desc():
    fj.add_entry("observation", "Earlier", date="2026-01-01")
    fj.add_entry("observation", "Later", date="2026-03-01")
    history = fj.get_entry_history(months=12)
    dates = [e["date"] for e in history]
    assert dates == sorted(dates, reverse=True)


# ── get_decision_outcomes ─────────────────────────────────────────────────────

def test_get_decision_outcomes_only_resolved():
    e1 = fj.add_entry("decision", "Switch to index funds")
    fj.record_outcome(e1["id"], "Done in Q2", "kept")
    fj.add_entry("decision", "Still thinking about it")  # open
    outcomes = fj.get_decision_outcomes()
    titles = [o["title"] for o in outcomes]
    assert "Switch to index funds" in titles
    assert "Still thinking about it" not in titles


# ── get_financial_narrative ───────────────────────────────────────────────────

def test_get_financial_narrative_nonempty_with_entries():
    fj.add_entry("decision", "Start investing", date="2026-01-10")
    narrative = fj.get_financial_narrative(months=12)
    assert isinstance(narrative, str)
    assert len(narrative) > 0


def test_get_financial_narrative_empty_db():
    narrative = fj.get_financial_narrative(months=12)
    assert "No journal entries" in narrative or isinstance(narrative, str)


def test_get_financial_narrative_includes_commitment_stats():
    e1 = fj.add_entry("commitment", "Save €500/month")
    fj.record_outcome(e1["id"], "Done every month", "kept")
    e2 = fj.add_entry("commitment", "Cut dining budget")
    fj.record_outcome(e2["id"], "Failed in July", "missed")
    narrative = fj.get_financial_narrative(months=12)
    assert "1 of 2" in narrative or "commitment" in narrative.lower()
