"""
Build a persistent tax-year workspace for TaxDE.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

try:
    from claim_engine import generate_claims
    from document_coverage import build_document_coverage
    from document_sorter import sort_folder
    from profile_manager import get_profile
    from refund_calculator import calculate_refund
    from rule_registry import get_rule_registry
    from tax_timeline import build_tax_timeline
    from taxde_storage import get_claims_path, get_workspace_path, save_json
except ImportError:
    import os
    import sys

    sys.path.insert(0, os.path.dirname(__file__))
    from claim_engine import generate_claims
    from document_coverage import build_document_coverage
    from document_sorter import sort_folder
    from profile_manager import get_profile
    from refund_calculator import calculate_refund
    from rule_registry import get_rule_registry
    from tax_timeline import build_tax_timeline
    from taxde_storage import get_claims_path, get_workspace_path, save_json


def _top_opportunities(claims: list[dict], limit: int = 5) -> list[dict]:
    ranked = sorted(
        claims,
        key=lambda claim: (claim.get("estimated_refund_effect") or 0.0, claim.get("amount_deductible") or 0.0),
        reverse=True,
    )
    return ranked[:limit]


def _open_tasks(claims: list[dict], coverage: dict) -> list[str]:
    tasks = []
    for doc in coverage.get("documents", []):
        if doc["status"] != "present":
            tasks.append(f"Document: {doc['document']} ({doc['status']})")
    for claim in claims:
        if claim["status"] in {"needs_input", "needs_evidence", "detected"}:
            tasks.append(f"{claim['title']}: {claim['next_action']}")
    deduped = []
    seen = set()
    for task in tasks:
        if task in seen:
            continue
        seen.add(task)
        deduped.append(task)
    return deduped[:10]


def build_workspace(
    profile: Optional[dict] = None,
    folder_path: Optional[str] = None,
    manifest: Optional[dict] = None,
    today: Optional[date] = None,
    persist: bool = True,
) -> dict:
    profile = profile or get_profile() or {}
    tax_year = profile.get("meta", {}).get("tax_year", datetime.now().year)

    if folder_path and manifest is None:
        manifest = sort_folder(folder_path, dry_run=True, profile=profile)

    claims_payload = generate_claims(profile=profile, persist=persist)
    claims = claims_payload["claims"]
    coverage = build_document_coverage(profile=profile, manifest=manifest)
    refund = calculate_refund(profile)
    registry = get_rule_registry(tax_year)

    claim_weights = {"ready": 1.0, "needs_evidence": 0.55, "needs_input": 0.35, "detected": 0.25}
    claim_score = (
        sum(claim_weights.get(claim["status"], 0.0) for claim in claims) / (len(claims) or 1)
    )
    document_score = coverage.get("coverage_pct", 0) / 100
    refund_score = refund.get("confidence_pct", 0) / 100
    readiness_pct = round((claim_score * 0.35 + document_score * 0.40 + refund_score * 0.25) * 100)

    money_left_on_table = round(
        sum((claim.get("estimated_refund_effect") or 0.0) for claim in claims if claim["status"] != "ready"),
        2,
    )

    workspace = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "tax_year": tax_year,
        "readiness_pct": readiness_pct,
        "evidence_coverage_pct": coverage.get("coverage_pct", 0),
        "refund_confidence_pct": refund.get("confidence_pct", 0),
        "money_left_on_table_estimate": money_left_on_table,
        "estimated_refund": refund.get("estimated_refund"),
        "top_opportunities": _top_opportunities(claims),
        "open_tasks": _open_tasks(claims, coverage),
        "claim_count": len(claims),
        "claims_path": str(get_claims_path(tax_year)),
        "recent_receipts": profile.get("current_year_receipts", [])[-5:],
        "document_coverage": coverage,
        "refund_summary": refund,
        "rule_registry": {
            "requested_year": registry["requested_year"],
            "resolved_year": registry["resolved_year"],
            "fallback_note": registry.get("fallback_note"),
            "deadlines": registry.get("deadlines", {}),
        },
    }
    workspace["timeline"] = build_tax_timeline(
        tax_year=tax_year,
        workspace=workspace,
        profile=profile,
        today=today,
    )
    if persist:
        save_json(get_workspace_path(tax_year), workspace)
    return workspace


def format_workspace_display(workspace: dict) -> str:
    lines = [
        f"TaxDE workspace for {workspace['tax_year']}",
        f"Readiness: {workspace['readiness_pct']}%",
        f"Evidence coverage: {workspace['evidence_coverage_pct']}%",
        f"Refund confidence: {workspace['refund_confidence_pct']}%",
        f"Estimated refund: €{workspace['estimated_refund']:,.0f}",
        f"Money left on table: €{workspace['money_left_on_table_estimate']:,.0f}",
        "",
        "Top opportunities:",
    ]
    for claim in workspace.get("top_opportunities", []):
        lines.append(
            f"- {claim['title']} [{claim['status']}] "
            f"€{(claim.get('estimated_refund_effect') or 0):,.0f} impact"
        )
    if workspace.get("open_tasks"):
        lines.append("")
        lines.append("Open tasks:")
        for task in workspace["open_tasks"]:
            lines.append(f"- {task}")
    return "\n".join(lines)


if __name__ == "__main__":
    print(format_workspace_display(build_workspace()))
