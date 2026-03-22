"""
Annual TaxDE timeline and seasonal action planner.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

try:
    from tax_dates import format_deadline_label, get_filing_deadline
except ImportError:
    import os
    import sys

    sys.path.insert(0, os.path.dirname(__file__))
    from tax_dates import format_deadline_label, get_filing_deadline


PHASES = (
    {
        "id": "document_and_law_change_check",
        "title": "January reset",
        "months": {1},
        "objective": "Collect annual documents, refresh source status, and start with a clean workspace.",
        "default_actions": [
            "Collect payroll, insurance, and pension statements as they arrive.",
            "Refresh the supported rule year and source snapshot before using fresh-year figures.",
        ],
    },
    {
        "id": "filing_preparation",
        "title": "Filing preparation",
        "months": {2, 3, 4, 5, 6, 7},
        "objective": "Turn the year into a filing-ready workspace with confirmed claims and fewer surprises.",
        "default_actions": [
            "Confirm the highest-value deductions before moving into forms.",
            "Resolve missing documents early so filing does not stall near the deadline.",
        ],
    },
    {
        "id": "bescheid_review",
        "title": "Bescheid review",
        "months": {8, 9, 10},
        "objective": "Review the assessment notice quickly and challenge worthwhile differences in time.",
        "default_actions": [
            "Compare the assessment against the expected filing values.",
            "Track the one-month objection deadline from the notice date if something looks wrong.",
        ],
    },
    {
        "id": "year_end_optimization",
        "title": "Year-end optimization",
        "months": {11, 12},
        "objective": "Use the remaining weeks of the tax year for high-value, evidence-backed moves.",
        "default_actions": [
            "Prioritize deductible spending or contributions that only count in this calendar year.",
            "Log receipts immediately so year-end actions do not disappear into a folder later.",
        ],
    },
)


def _phase_for_month(month: int) -> dict:
    for phase in PHASES:
        if month in phase["months"]:
            return phase
    return PHASES[1]


def _unique(items: list[str]) -> list[str]:
    seen = set()
    result = []
    for item in items:
        if not item or item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def build_tax_timeline(
    tax_year: int,
    workspace: Optional[dict] = None,
    profile: Optional[dict] = None,
    today: Optional[date] = None,
) -> dict:
    today = today or date.today()
    phase = _phase_for_month(today.month)
    workspace = workspace or {}
    profile = profile or {}
    coverage = workspace.get("document_coverage", {})

    actions = list(phase["default_actions"])
    missing_docs = coverage.get("missing_count", 0)
    partial_docs = coverage.get("partial_count", 0)
    open_tasks = workspace.get("open_tasks", [])
    money_left = float(workspace.get("money_left_on_table_estimate") or 0.0)

    if phase["id"] == "document_and_law_change_check":
        if missing_docs:
            actions.append(f"Chase the {missing_docs} missing core document(s) before filing season starts.")
        if profile.get("current_year_receipts"):
            actions.append("Review last year's receipt log and close open evidence gaps now.")

    elif phase["id"] == "filing_preparation":
        if missing_docs:
            actions.append(f"Collect the {missing_docs} missing document(s) blocking the return.")
        if partial_docs:
            actions.append(f"Complete the missing extracted fields on {partial_docs} partially-covered document(s).")
        if money_left > 0:
            actions.append(f"Resolve the open claims worth about EUR {money_left:,.0f} before filing.")
        if open_tasks:
            actions.append(open_tasks[0])

    elif phase["id"] == "bescheid_review":
        actions.append("Save the notice date so the objection deadline is computed exactly.")
        if open_tasks:
            actions.append("Use the saved filing pack as the baseline before drafting any objection.")

    elif phase["id"] == "year_end_optimization":
        if money_left > 0:
            actions.append(f"Focus on the open opportunities still worth about EUR {money_left:,.0f}.")
        top_opportunities = workspace.get("top_opportunities", [])
        for claim in top_opportunities:
            if claim.get("status") != "ready":
                actions.append(f"{claim['title']}: {claim.get('next_action') or 'resolve this before year-end.'}")
                break
        actions.append("Check whether planned purchases should happen before or after December 31.")

    standard_deadline = get_filing_deadline(tax_year, advised=False)
    advised_deadline = get_filing_deadline(tax_year, advised=True)
    deadlines = [
        {
            "type": "standard",
            "date": standard_deadline.isoformat(),
            "label": format_deadline_label(tax_year, advised=False),
        },
        {
            "type": "advised",
            "date": advised_deadline.isoformat(),
            "label": format_deadline_label(tax_year, advised=True),
        },
    ]

    next_deadline = None
    upcoming = sorted(
        (entry for entry in deadlines if date.fromisoformat(entry["date"]) >= today),
        key=lambda entry: entry["date"],
    )
    if upcoming:
        next_deadline = upcoming[0]

    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "tax_year": tax_year,
        "today": today.isoformat(),
        "phase_id": phase["id"],
        "phase_title": phase["title"],
        "objective": phase["objective"],
        "actions": _unique(actions)[:8],
        "next_deadline": next_deadline,
        "deadlines": deadlines,
    }


def format_tax_timeline_display(timeline: dict) -> str:
    lines = [
        f"Tax timeline for {timeline['tax_year']}",
        f"Phase: {timeline['phase_title']}",
        f"Objective: {timeline['objective']}",
    ]
    if timeline.get("next_deadline"):
        lines.append(f"Next deadline: {timeline['next_deadline']['label']}")
    lines.append("")
    lines.append("Actions:")
    for action in timeline.get("actions", []):
        lines.append(f"- {action}")
    return "\n".join(lines)


if __name__ == "__main__":
    print(format_tax_timeline_display(build_tax_timeline(datetime.now().year)))
