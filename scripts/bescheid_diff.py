"""
Compare expected filing values against a received tax assessment.
"""

from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime
from typing import Optional

try:
    from filing_pack import build_filing_pack
except ImportError:
    import os
    import sys

    sys.path.insert(0, os.path.dirname(__file__))
    from filing_pack import build_filing_pack


def _add_one_calendar_month(value: date) -> date:
    month = 1 if value.month == 12 else value.month + 1
    year = value.year + 1 if value.month == 12 else value.year
    day = min(value.day, monthrange(year, month)[1])
    return date(year, month, day)


def compare_bescheid(
    assessed: dict,
    filing_pack: Optional[dict] = None,
) -> dict:
    filing_pack = filing_pack or build_filing_pack(persist=False)
    expected_claims = {claim["id"]: claim for claim in filing_pack.get("confirmed_claims", [])}
    accepted_claims = assessed.get("accepted_claims", {})
    rejected_claims = set(assessed.get("rejected_claims", []))
    reviewed_claims = []

    for claim_id, claim in expected_claims.items():
        accepted_amount = accepted_claims.get(claim_id)
        expected_amount = float(claim.get("amount_deductible") or 0.0)
        if claim_id in rejected_claims:
            status = "rejected"
            accepted_amount = 0.0
        elif accepted_amount is None:
            status = "unknown"
        elif round(float(accepted_amount), 2) == round(expected_amount, 2):
            status = "accepted"
        elif float(accepted_amount) <= 0:
            status = "rejected"
        else:
            status = "reduced"

        reviewed_claims.append(
            {
                "id": claim_id,
                "title": claim["title"],
                "expected_amount": round(expected_amount, 2),
                "accepted_amount": None if accepted_amount is None else round(float(accepted_amount), 2),
                "status": status,
                "confidence": claim.get("confidence"),
                "evidence_present": claim.get("evidence_present", []),
                "evidence_missing": claim.get("evidence_missing", []),
                "likely_reason": (
                    "Supporting evidence may be missing."
                    if status in {"reduced", "rejected"} and claim.get("evidence_missing")
                    else (
                        "The Finanzamt appears to have reduced or rejected the claimed amount."
                        if status in {"reduced", "rejected"}
                        else None
                    )
                ),
            }
        )

    expected_refund = float(filing_pack.get("summary", {}).get("estimated_refund") or 0.0)
    assessed_refund = assessed.get("assessed_refund")
    variance = None if assessed_refund is None else round(float(assessed_refund) - expected_refund, 2)

    notice_date_raw = assessed.get("notice_date")
    deadline = None
    if notice_date_raw:
        notice_date = date.fromisoformat(str(notice_date_raw))
        deadline = _add_one_calendar_month(notice_date).isoformat()

    disagreed = [item for item in reviewed_claims if item["status"] in {"reduced", "rejected"}]
    objection_candidate = bool(
        disagreed
        and sum((item["expected_amount"] - (item["accepted_amount"] or 0.0)) for item in disagreed) >= 100
    )
    accepted = [item for item in reviewed_claims if item["status"] == "accepted"]
    reduced = [item for item in reviewed_claims if item["status"] == "reduced"]
    rejected = [item for item in reviewed_claims if item["status"] == "rejected"]
    supporting_evidence = sorted(
        {
            evidence
            for item in disagreed
            for evidence in item.get("evidence_present", [])
            if evidence
        }
    )
    if disagreed:
        draft_response = "\n".join(
            [
                f"I would like a review of the assessment for tax year {filing_pack.get('tax_year')}.",
                *[
                    (
                        f"- {item['title']}: expected EUR {item['expected_amount']:,.0f}, "
                        f"accepted EUR {(item['accepted_amount'] or 0):,.0f}. "
                        f"Evidence: {', '.join(item.get('evidence_present', [])) or 'see supporting documents'}."
                    )
                    for item in disagreed[:5]
                ],
            ]
        )
    else:
        draft_response = "No obvious objection points detected from the structured comparison."

    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "tax_year": filing_pack.get("tax_year"),
        "expected_refund": expected_refund,
        "assessed_refund": assessed_refund,
        "refund_variance": variance,
        "einspruch_deadline": deadline,
        "claims": reviewed_claims,
        "accepted_claims": accepted,
        "reduced_claims": reduced,
        "rejected_claims": rejected,
        "objection_candidate": objection_candidate,
        "supporting_evidence": supporting_evidence,
        "draft_points": [
            f"Question difference in {item['title']}: expected €{item['expected_amount']:,.0f}, accepted €{(item['accepted_amount'] or 0):,.0f}."
            for item in disagreed[:5]
        ],
        "draft_response": draft_response,
    }
