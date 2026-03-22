"""
Build structured TaxDE deliverables beyond a single chat response.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

try:
    from adviser_handoff import build_adviser_handoff
    from bescheid_diff import compare_bescheid
    from claim_engine import generate_claims
    from document_coverage import build_document_coverage
    from filing_pack import build_filing_pack
    from profile_manager import get_profile
    from tax_timeline import build_tax_timeline
    from taxde_storage import get_output_suite_path, save_json
    from workspace_builder import build_workspace
except ImportError:
    import os
    import sys

    sys.path.insert(0, os.path.dirname(__file__))
    from adviser_handoff import build_adviser_handoff
    from bescheid_diff import compare_bescheid
    from claim_engine import generate_claims
    from document_coverage import build_document_coverage
    from filing_pack import build_filing_pack
    from profile_manager import get_profile
    from tax_timeline import build_tax_timeline
    from taxde_storage import get_output_suite_path, save_json
    from workspace_builder import build_workspace


def _build_yearly_tax_summary(workspace: dict, timeline: dict) -> dict:
    return {
        "headline": (
            f"About EUR {float(workspace.get('estimated_refund') or 0.0):,.0f} estimated refund "
            f"with {workspace.get('readiness_pct', 0)}% filing readiness."
        ),
        "estimated_refund": workspace.get("estimated_refund"),
        "readiness_pct": workspace.get("readiness_pct"),
        "evidence_coverage_pct": workspace.get("evidence_coverage_pct"),
        "refund_confidence_pct": workspace.get("refund_confidence_pct"),
        "money_left_on_table_estimate": workspace.get("money_left_on_table_estimate"),
        "next_deadline": timeline.get("next_deadline"),
        "current_phase": timeline.get("phase_title"),
    }


def _build_claim_checklist(claims: list[dict]) -> list[dict]:
    return [
        {
            "id": claim["id"],
            "title": claim["title"],
            "status": claim["status"],
            "amount_deductible": claim.get("amount_deductible"),
            "estimated_refund_effect": claim.get("estimated_refund_effect"),
            "confidence": claim.get("confidence"),
            "evidence_missing": claim.get("evidence_missing", []),
            "next_action": claim.get("next_action"),
        }
        for claim in claims
    ]


def _build_missing_document_checklist(coverage: dict) -> list[dict]:
    return [
        {
            "document": doc["document"],
            "status": doc["status"],
            "files_found": doc.get("files_found", []),
            "fields_missing": doc.get("fields_missing", []),
            "forms": doc.get("forms", []),
        }
        for doc in coverage.get("documents", [])
        if doc["status"] != "present"
    ]


def _build_year_end_action_list(workspace: dict, timeline: dict) -> list[str]:
    actions = list(timeline.get("actions", []))
    for claim in workspace.get("top_opportunities", []):
        if claim.get("status") == "ready":
            continue
        actions.append(
            f"{claim['title']}: {claim.get('next_action') or 'resolve this before the year closes.'}"
        )
    for task in workspace.get("open_tasks", []):
        actions.append(task)
    deduped = []
    seen = set()
    for action in actions:
        if action in seen:
            continue
        seen.add(action)
        deduped.append(action)
    return deduped[:10]


def build_output_suite(
    profile: Optional[dict] = None,
    manifest: Optional[dict] = None,
    assessed: Optional[dict] = None,
    persist: bool = True,
    today: Optional[date] = None,
) -> dict:
    profile = profile or get_profile() or {}
    tax_year = profile.get("meta", {}).get("tax_year", datetime.now().year)
    claims_payload = generate_claims(profile=profile, persist=persist)
    coverage = build_document_coverage(profile=profile, manifest=manifest)
    workspace = build_workspace(profile=profile, manifest=manifest, today=today, persist=persist)
    timeline = build_tax_timeline(
        tax_year=tax_year,
        workspace=workspace,
        profile=profile,
        today=today,
    )
    workspace["timeline"] = timeline
    filing_pack = build_filing_pack(
        profile=profile,
        claims_payload=claims_payload,
        coverage=coverage,
        persist=persist,
    )
    adviser_handoff = build_adviser_handoff(
        profile=profile,
        claims=claims_payload["claims"],
        coverage=coverage,
        workspace=workspace,
    )

    suite = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "tax_year": tax_year,
        "yearly_tax_summary": _build_yearly_tax_summary(workspace, timeline),
        "claim_checklist": _build_claim_checklist(claims_payload["claims"]),
        "missing_document_checklist": _build_missing_document_checklist(coverage),
        "filing_pack": filing_pack,
        "bescheid_review_pack": (
            compare_bescheid(assessed, filing_pack=filing_pack) if assessed else None
        ),
        "steuerberater_briefing": adviser_handoff,
        "year_end_action_list": _build_year_end_action_list(workspace, timeline),
        "timeline": timeline,
    }
    if persist:
        save_json(get_output_suite_path(tax_year), suite)
    return suite


def format_output_suite_display(suite: dict) -> str:
    summary = suite["yearly_tax_summary"]
    lines = [
        f"TaxDE output suite for {suite['tax_year']}",
        summary["headline"],
        "",
        "Top year-end / next actions:",
    ]
    for action in suite.get("year_end_action_list", [])[:5]:
        lines.append(f"- {action}")
    lines.append("")
    lines.append(
        f"Specialist handoff: "
        f"{'yes' if suite['steuerberater_briefing']['requires_specialist_review'] else 'not currently'}"
    )
    return "\n".join(lines)


if __name__ == "__main__":
    print(format_output_suite_display(build_output_suite(persist=False)))
