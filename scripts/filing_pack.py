"""
Build an ELSTER/WISO preparation pack from the current TaxDE workspace.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

try:
    from claim_engine import generate_claims
    from document_coverage import build_document_coverage
    from profile_manager import get_profile
    from refund_calculator import calculate_refund
    from taxde_storage import get_filing_pack_path, save_json
except ImportError:
    import os
    import sys

    sys.path.insert(0, os.path.dirname(__file__))
    from claim_engine import generate_claims
    from document_coverage import build_document_coverage
    from profile_manager import get_profile
    from refund_calculator import calculate_refund
    from taxde_storage import get_filing_pack_path, save_json


def _infer_forms(profile: dict, coverage: dict) -> list[dict]:
    employment = profile.get("employment", {})
    family = profile.get("family", {})
    insurance = profile.get("insurance", {})
    special = profile.get("special", {})

    forms = [{"form": "Mantelbogen", "reason": "Core tax return cover sheet", "status": "ready"}]

    def _status_for_categories(*categories: str) -> str:
        docs = [doc for doc in coverage.get("documents", []) if doc.get("category") in categories]
        if not docs:
            return "ready"
        if all(doc["status"] == "present" for doc in docs):
            return "ready"
        if any(doc["status"] == "missing" for doc in docs):
            return "needs_documents"
        return "partial"

    if employment.get("type") == "angestellter":
        forms.append(
            {
                "form": "Anlage N",
                "reason": "Employment income and work-related deductions",
                "status": _status_for_categories("income", "equipment"),
            }
        )

    if family.get("children"):
        forms.append(
            {
                "form": "Anlage Kind",
                "reason": "Children, childcare, and family-related claims",
                "status": _status_for_categories("childcare", "kindergeld"),
            }
        )

    if insurance.get("riester"):
        forms.append(
            {"form": "Anlage AV", "reason": "Riester contributions", "status": _status_for_categories("riester")}
        )

    if insurance.get("riester") or insurance.get("ruerup") or insurance.get("krankenkasse_type"):
        forms.append(
            {
                "form": "Anlage Vorsorgeaufwand",
                "reason": "Insurance and pension contributions",
                "status": _status_for_categories("insurance_kv", "ruerup", "bav"),
            }
        )

    if special.get("capital_income"):
        forms.append(
            {"form": "Anlage KAP", "reason": "Capital income and withholding tax", "status": _status_for_categories("investment")}
        )

    if employment.get("type") in {"freelancer", "freiberufler"}:
        forms.append({"form": "Anlage S", "reason": "Freelance income", "status": "partial"})
        forms.append({"form": "EÜR", "reason": "Income surplus statement", "status": "partial"})

    if employment.get("type") == "gewerbe":
        forms.append({"form": "Anlage G", "reason": "Trade income", "status": "partial"})
        forms.append({"form": "EÜR", "reason": "Income surplus statement", "status": "partial"})

    return forms


def build_filing_pack(
    profile: Optional[dict] = None,
    claims_payload: Optional[dict] = None,
    coverage: Optional[dict] = None,
    persist: bool = True,
) -> dict:
    profile = profile or get_profile() or {}
    tax_year = profile.get("meta", {}).get("tax_year", datetime.now().year)
    claims_payload = claims_payload or generate_claims(profile=profile, persist=persist)
    coverage = coverage or build_document_coverage(profile=profile)
    refund = calculate_refund(profile)

    forms = _infer_forms(profile, coverage)
    ready_claims = [
        claim for claim in claims_payload["claims"]
        if claim["status"] == "ready" and (claim.get("amount_deductible") or 0) > 0
    ]
    pending_claims = [
        claim for claim in claims_payload["claims"]
        if claim["status"] != "ready"
    ]

    missing_documents = [
        doc for doc in coverage.get("documents", [])
        if doc["status"] != "present"
    ]
    next_steps = [claim["next_action"] for claim in pending_claims[:5]]
    next_steps += [f"Get document: {doc['document']}" for doc in missing_documents[:5]]

    pack = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "tax_year": tax_year,
        "summary": {
            "estimated_refund": refund.get("estimated_refund"),
            "confidence_pct": refund.get("confidence_pct"),
            "ready_claim_count": len(ready_claims),
            "pending_claim_count": len(pending_claims),
            "missing_document_count": len(missing_documents),
        },
        "forms": forms,
        "confirmed_claims": ready_claims,
        "pending_claims": pending_claims,
        "missing_documents": missing_documents,
        "next_steps": next_steps[:8],
    }
    if persist:
        save_json(get_filing_pack_path(tax_year), pack)
    return pack


if __name__ == "__main__":
    pack = build_filing_pack()
    print(f"Built filing pack for {pack['tax_year']} with {len(pack['forms'])} forms.")
