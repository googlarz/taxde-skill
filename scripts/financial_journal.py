"""
Financial Journal — longitudinal memory of the user's financial journey.

Stores decisions, commitments, milestones, and observations with outcomes.

entry_type: 'decision' | 'commitment' | 'milestone' | 'observation'
status:     'open' | 'kept' | 'missed' | 'superseded'
"""

from __future__ import annotations

import json
import uuid
from datetime import date, datetime
from typing import Optional

try:
    from db import get_conn
except ImportError:
    import sys, os
    sys.path.insert(0, os.path.dirname(__file__))
    from db import get_conn


_CREATE_SQL = """
CREATE TABLE IF NOT EXISTS journal_entries (
    id TEXT PRIMARY KEY,
    entry_type TEXT NOT NULL,
    date TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'open',
    outcome TEXT,
    linked_metrics TEXT,
    due_date TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""


def _ensure_table(conn) -> None:
    conn.execute(_CREATE_SQL)


def _row_to_dict(row) -> dict:
    d = dict(row)
    if d.get("linked_metrics"):
        try:
            d["linked_metrics"] = json.loads(d["linked_metrics"])
        except (ValueError, TypeError):
            d["linked_metrics"] = []
    else:
        d["linked_metrics"] = []
    return d


def add_entry(
    entry_type: str,
    title: str,
    description: str = "",
    date: str = None,
    due_date: str = None,
    linked_metrics: list[str] = None,
) -> dict:
    """Add a journal entry and return the saved dict."""
    from datetime import date as _date
    entry_date = date or _date.today().isoformat()
    now = datetime.utcnow().isoformat()
    entry_id = str(uuid.uuid4())[:8] + "-" + entry_date
    metrics_json = json.dumps(linked_metrics or [])

    row = {
        "id": entry_id,
        "entry_type": entry_type,
        "date": entry_date,
        "title": title,
        "description": description,
        "status": "open",
        "outcome": None,
        "linked_metrics": metrics_json,
        "due_date": due_date,
        "created_at": now,
        "updated_at": now,
    }

    with get_conn() as conn:
        _ensure_table(conn)
        conn.execute(
            """
            INSERT INTO journal_entries
                (id, entry_type, date, title, description, status, outcome,
                 linked_metrics, due_date, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                row["id"], row["entry_type"], row["date"], row["title"],
                row["description"], row["status"], row["outcome"],
                row["linked_metrics"], row["due_date"],
                row["created_at"], row["updated_at"],
            ],
        )

    result = dict(row)
    result["linked_metrics"] = linked_metrics or []
    return result


def record_outcome(entry_id: str, outcome: str, status: str) -> dict:
    """Update status, outcome, and updated_at for an existing entry."""
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        _ensure_table(conn)
        conn.execute(
            "UPDATE journal_entries SET outcome = ?, status = ?, updated_at = ? WHERE id = ?",
            [outcome, status, now, entry_id],
        )
        row = conn.execute(
            "SELECT * FROM journal_entries WHERE id = ?", [entry_id]
        ).fetchone()
    if row is None:
        raise KeyError(f"No journal entry with id={entry_id!r}")
    return _row_to_dict(row)


def get_open_commitments() -> list[dict]:
    """Return all commitments with status='open', ordered by due_date."""
    with get_conn() as conn:
        _ensure_table(conn)
        rows = conn.execute(
            """
            SELECT * FROM journal_entries
            WHERE entry_type = 'commitment' AND status = 'open'
            ORDER BY due_date ASC
            """
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_overdue_commitments() -> list[dict]:
    """Return open commitments whose due_date is before today."""
    today = datetime.utcnow().date().isoformat()
    with get_conn() as conn:
        _ensure_table(conn)
        rows = conn.execute(
            """
            SELECT * FROM journal_entries
            WHERE entry_type = 'commitment'
              AND status = 'open'
              AND due_date IS NOT NULL
              AND due_date < ?
            ORDER BY due_date ASC
            """,
            [today],
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_entry_history(months: int = 12, entry_type: str = None) -> list[dict]:
    """Return entries ordered by date desc, optionally filtered by entry_type."""
    from datetime import timedelta
    cutoff = (datetime.utcnow().date() - timedelta(days=months * 30)).isoformat()

    with get_conn() as conn:
        _ensure_table(conn)
        if entry_type:
            rows = conn.execute(
                """
                SELECT * FROM journal_entries
                WHERE date >= ? AND entry_type = ?
                ORDER BY date DESC
                """,
                [cutoff, entry_type],
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT * FROM journal_entries
                WHERE date >= ?
                ORDER BY date DESC
                """,
                [cutoff],
            ).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_decision_outcomes() -> list[dict]:
    """Return decisions that have a recorded outcome (status in kept/missed)."""
    with get_conn() as conn:
        _ensure_table(conn)
        rows = conn.execute(
            """
            SELECT * FROM journal_entries
            WHERE entry_type = 'decision'
              AND status IN ('kept', 'missed')
            ORDER BY date DESC
            """
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_financial_narrative(months: int = 12) -> str:
    """
    Generate a plain-English paragraph summarising the last N months.

    Example:
        "In January you decided to pay off the credit card before investing.
         By June it was cleared. You've kept 3 of 4 commitments this year."
    """
    entries = get_entry_history(months=months)
    if not entries:
        return "No journal entries recorded yet."

    # Collect stats
    decisions = [e for e in entries if e["entry_type"] == "decision"]
    commitments = [e for e in entries if e["entry_type"] == "commitment"]
    milestones = [e for e in entries if e["entry_type"] == "milestone"]
    observations = [e for e in entries if e["entry_type"] == "observation"]

    kept = sum(1 for c in commitments if c["status"] == "kept")
    missed = sum(1 for c in commitments if c["status"] == "missed")
    total_closed = kept + missed

    parts = []

    # Lead with oldest notable decision
    if decisions:
        oldest = decisions[-1]
        try:
            d = date.fromisoformat(oldest["date"])
            month_name = d.strftime("%B")
        except ValueError:
            month_name = oldest["date"]
        parts.append(f"In {month_name} you decided to {oldest['title'].lower()}.")
        if oldest.get("outcome"):
            parts.append(oldest["outcome"])

    # Milestones
    if milestones:
        reached = [m for m in milestones if m["status"] in ("kept", "open")]
        if reached:
            parts.append(
                f"You recorded {len(reached)} milestone(s), including: {reached[0]['title']}."
            )

    # Commitment score
    if total_closed > 0:
        parts.append(
            f"You've kept {kept} of {total_closed} commitment(s) in the past {months} months."
        )
    elif commitments:
        open_count = len([c for c in commitments if c["status"] == "open"])
        if open_count:
            parts.append(f"You have {open_count} open commitment(s) in progress.")

    # Observations
    if observations:
        parts.append(f"You logged {len(observations)} observation(s) along the way.")

    return " ".join(parts) if parts else "No significant journal activity in the selected period."
