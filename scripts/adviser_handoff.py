"""
Build a structured specialist handoff packet when TaxDE should stop cleanly.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

try:
    from claim_engine import generate_claims
    from document_coverage import build_document_coverage
    from profile_manager import get_profile
except ImportError:
    import os
    import sys

    sys.path.insert(0, os.path.dirname(__file__))
    from claim_engine import generate_claims
    from document_coverage import build_document_coverage
    from profile_manager import get_profile


def _risk_reasons(profile: dict, claims: list[dict], coverage: dict) -> list[dict]:
    employment = profile.get("employment", {})
    housing = profile.get("housing", {})
    special = profile.get("special", {})
    reasons = []

    if special.get("expat") or special.get("dba_relevant"):
        reasons.append(
            {
                "id": "cross_border",
                "priority": "high",
                "reason": "Cross-border tax residence or treaty allocation likely affects the return.",
            }
        )

    if employment.get("type") == "mixed":
        reasons.append(
            {
                "id": "mixed_income",
                "priority": "medium",
                "reason": "Mixed employment and self-employed income usually needs tighter allocation work.",
            }
        )

    if employment.get("type") in {"gewerbe", "freelancer", "freiberufler"} and profile.get("special", {}).get("capital_income"):
        reasons.append(
            {
                "id": "business_plus_investments",
                "priority": "medium",
                "reason": "Business income plus investment income may need a cleaner adviser review pack.",
            }
        )

    if housing.get("rental_property"):
        reasons.append(
            {
                "id": "rental_property",
                "priority": "high",
                "reason": "Rental property deductions, depreciation, and allocation need specialist review.",
            }
        )

    unresolved_high_value = [
        claim for claim in claims
        if claim.get("status") != "ready" and float(claim.get("estimated_refund_effect") or 0.0) >= 200
    ]
    if unresolved_high_value:
        reasons.append(
            {
                "id": "material_uncertainty",
                "priority": "medium",
                "reason": "High-value claims are still estimated or blocked on evidence.",
            }
        )

    missing_docs = coverage.get("missing_count", 0)
    if missing_docs >= 3:
        reasons.append(
            {
                "id": "evidence_gaps",
                "priority": "medium",
                "reason": "Several core documents are still missing, so specialist time should focus on the right gaps.",
            }
        )

    return reasons


def _questions_for_reasons(reasons: list[dict], tax_year: int) -> list[str]:
    questions = []
    reason_ids = {reason["id"] for reason in reasons}

    if "cross_border" in reason_ids:
        questions.append(f"How should tax residence and treaty allocation be handled for {tax_year}?")
        questions.append("Which foreign income items need German reporting, exemption, or credit treatment?")
    if "mixed_income" in reason_ids:
        questions.append("How should costs be allocated between employee and self-employed activity?")
        questions.append("Do advance payments or EÜR presentation change the filing approach?")
    if "business_plus_investments" in reason_ids:
        questions.append("Are there special reporting or loss-offset limits for the business and investment mix?")
    if "rental_property" in reason_ids:
        questions.append("Which property costs are immediately deductible versus depreciated over time?")
        questions.append("Which supporting documents should be prioritized for the rental schedule?")
    if "material_uncertainty" in reason_ids:
        questions.append("Which unresolved claims are worth defending versus dropping to save time?")
    if "evidence_gaps" in reason_ids:
        questions.append("Which missing documents are mission-critical before filing or objection work starts?")

    if not questions:
        questions.append("Can you validate the prepared filing pack and identify any material blind spots?")

    deduped = []
    seen = set()
    for question in questions:
        if question in seen:
            continue
        seen.add(question)
        deduped.append(question)
    return deduped[:8]


def build_adviser_handoff(
    profile: Optional[dict] = None,
    claims: Optional[list[dict]] = None,
    coverage: Optional[dict] = None,
    workspace: Optional[dict] = None,
) -> dict:
    profile = profile or get_profile() or {}
    tax_year = profile.get("meta", {}).get("tax_year", datetime.now().year)
    claims = claims or generate_claims(profile=profile, persist=False)["claims"]
    coverage = coverage or build_document_coverage(profile=profile)
    workspace = workspace or {}

    reasons = _risk_reasons(profile, claims, coverage)
    risk_level = "low"
    if any(reason["priority"] == "high" for reason in reasons):
        risk_level = "high"
    elif reasons:
        risk_level = "medium"

    claims_to_review = [
        {
            "id": claim["id"],
            "title": claim["title"],
            "status": claim["status"],
            "estimated_refund_effect": claim.get("estimated_refund_effect"),
            "evidence_missing": claim.get("evidence_missing", []),
        }
        for claim in claims
        if claim.get("status") != "ready" or float(claim.get("estimated_refund_effect") or 0.0) >= 250
    ][:10]

    documents_ready = []
    for document in coverage.get("documents", []):
        documents_ready.extend(document.get("files_found", []))

    evidence_package = {
        "documents_ready": sorted(set(documents_ready)),
        "documents_missing": [
            document["document"]
            for document in coverage.get("documents", [])
            if document["status"] != "present"
        ],
        "claims_to_review": claims_to_review,
    }

    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "tax_year": tax_year,
        "requires_specialist_review": bool(reasons),
        "risk_level": risk_level,
        "reasons": reasons,
        "questions_for_adviser": _questions_for_reasons(reasons, tax_year),
        "evidence_package": evidence_package,
        "handoff_summary": (
            "Prepare a specialist review packet before filing or objecting."
            if reasons
            else "No specialist trigger detected, but this packet is ready if adviser review becomes useful."
        ),
        "workspace_snapshot": {
            "readiness_pct": workspace.get("readiness_pct"),
            "money_left_on_table_estimate": workspace.get("money_left_on_table_estimate"),
            "open_tasks": workspace.get("open_tasks", [])[:5],
        },
    }


if __name__ == "__main__":
    handoff = build_adviser_handoff()
    print(
        f"Adviser handoff for {handoff['tax_year']}: "
        f"{'required' if handoff['requires_specialist_review'] else 'not required'}"
    )
