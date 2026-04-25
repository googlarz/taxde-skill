"""
Life Events — significant life events that contextualise financial changes.

event_type: 'job_change' | 'move' | 'marriage' | 'child' | 'health'
          | 'windfall' | 'major_purchase' | 'other'
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta
from typing import Optional

try:
    from db import get_conn
except ImportError:
    import sys, os
    sys.path.insert(0, os.path.dirname(__file__))
    from db import get_conn


_CREATE_SQL = """
CREATE TABLE IF NOT EXISTS life_events (
    id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    event_date TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    financial_note TEXT,
    created_at TEXT NOT NULL
)
"""


def _ensure_table(conn) -> None:
    conn.execute(_CREATE_SQL)


def _row_to_dict(row) -> dict:
    return dict(row)


def add_event(
    event_type: str,
    title: str,
    event_date: str = None,
    description: str = "",
    financial_note: str = "",
) -> dict:
    """Add a life event and return the saved dict."""
    ev_date = event_date or date.today().isoformat()
    now = datetime.utcnow().isoformat()
    event_id = str(uuid.uuid4())[:8] + "-" + ev_date

    row = {
        "id": event_id,
        "event_type": event_type,
        "event_date": ev_date,
        "title": title,
        "description": description,
        "financial_note": financial_note,
        "created_at": now,
    }

    with get_conn() as conn:
        _ensure_table(conn)
        conn.execute(
            """
            INSERT INTO life_events
                (id, event_type, event_date, title, description,
                 financial_note, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                row["id"], row["event_type"], row["event_date"],
                row["title"], row["description"],
                row["financial_note"], row["created_at"],
            ],
        )
    return dict(row)


def get_events(months: int = 24) -> list[dict]:
    """Return all events ordered by event_date desc."""
    cutoff = (date.today() - timedelta(days=months * 30)).isoformat()
    with get_conn() as conn:
        _ensure_table(conn)
        rows = conn.execute(
            """
            SELECT * FROM life_events
            WHERE event_date >= ?
            ORDER BY event_date DESC
            """,
            [cutoff],
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_events_near(month: str, window_months: int = 1) -> list[dict]:
    """
    Return events within ±window_months of the given YYYY-MM.
    Used by timeline_engine to contextualise anomalies.
    """
    try:
        year, mon = int(month[:4]), int(month[5:7])
    except (ValueError, IndexError):
        return []

    center = date(year, mon, 1)
    delta = timedelta(days=window_months * 30)
    start = (center - delta).isoformat()
    end = (center + delta + timedelta(days=30)).isoformat()  # include full end month

    with get_conn() as conn:
        _ensure_table(conn)
        rows = conn.execute(
            """
            SELECT * FROM life_events
            WHERE event_date >= ? AND event_date <= ?
            ORDER BY event_date ASC
            """,
            [start, end],
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_context_for_anomaly(month: str, metric: str) -> Optional[str]:
    """
    If a life event exists near this month, return a human-readable explanation.
    Example: "You moved in March — that may explain the spending spike."
    Returns None if no nearby event.
    """
    events = get_events_near(month, window_months=1)
    if not events:
        return None

    event = events[0]
    title = event["title"]
    try:
        ev_date = date.fromisoformat(event["event_date"])
        month_name = ev_date.strftime("%B")
    except ValueError:
        month_name = event["event_date"]

    note = event.get("financial_note", "")
    if note:
        explanation = f"{title} in {month_name} — {note}"
    else:
        explanation = f"{title} in {month_name} — that may explain the {metric} change."

    return explanation
