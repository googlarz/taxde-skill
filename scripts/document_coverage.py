"""
Document coverage model for TaxDE.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

try:
    from profile_manager import get_profile
except ImportError:
    import os
    import sys

    sys.path.insert(0, os.path.dirname(__file__))
    from profile_manager import get_profile


def _expected_documents(profile: dict) -> list[dict]:
    expected = []
    employment = profile.get("employment", {})
    family = profile.get("family", {})
    insurance = profile.get("insurance", {})
    special = profile.get("special", {})
    receipts = profile.get("current_year_receipts", [])

    if employment.get("type") == "angestellter":
        expected.append(
            {
                "id": "lohnsteuerbescheinigung",
                "document": "Lohnsteuerbescheinigung",
                "category": "income",
                "required_fields": ["gross", "lohnsteuer"],
                "forms": ["Mantelbogen", "Anlage N"],
                "why": "Base employment income document for a German return.",
            }
        )

    expected.append(
        {
            "id": "kv_statement",
            "document": "Krankenversicherung Beitragsbescheinigung",
            "category": "insurance_kv",
            "required_fields": ["primary_amount"],
            "forms": ["Anlage Vorsorgeaufwand"],
            "why": "Needed to confirm deductible health-insurance contributions.",
        }
    )

    if insurance.get("riester"):
        expected.append(
            {
                "id": "riester_statement",
                "document": "Riester provider statement",
                "category": "riester",
                "required_fields": ["primary_amount"],
                "forms": ["Anlage AV"],
                "why": "Needed for Riester support and any Günstigerprüfung.",
            }
        )

    if insurance.get("ruerup"):
        expected.append(
            {
                "id": "ruerup_statement",
                "document": "Ruerup / Basisrente statement",
                "category": "ruerup",
                "required_fields": ["primary_amount"],
                "forms": ["Anlage Vorsorgeaufwand"],
                "why": "Confirms annual Ruerup contributions.",
            }
        )

    if family.get("children") and any(child.get("kita") for child in family.get("children", [])):
        expected.append(
            {
                "id": "childcare_invoice",
                "document": "Kita annual invoice / childcare statement",
                "category": "childcare",
                "required_fields": ["primary_amount"],
                "forms": ["Anlage Kind"],
                "why": "Required to support childcare deductions.",
            }
        )

    if special.get("capital_income"):
        expected.append(
            {
                "id": "investment_statement",
                "document": "Jahressteuerbescheinigung (bank/broker)",
                "category": "investment",
                "required_fields": ["kest_paid"],
                "forms": ["Anlage KAP"],
                "why": "Required to reconcile capital income and withholding tax.",
            }
        )

    if any(receipt.get("category") == "equipment" for receipt in receipts):
        expected.append(
            {
                "id": "equipment_invoices",
                "document": "Work equipment invoices",
                "category": "equipment",
                "required_fields": ["primary_amount"],
                "forms": ["Anlage N"],
                "why": "Useful to support work-equipment deductions and depreciation.",
            }
        )

    if any(receipt.get("category") == "donation" for receipt in receipts):
        expected.append(
            {
                "id": "donation_receipts",
                "document": "Donation receipts",
                "category": "donation",
                "required_fields": ["primary_amount"],
                "forms": ["Sonderausgaben"],
                "why": "Supports charitable deduction claims.",
            }
        )

    return expected


def build_document_coverage(profile: Optional[dict] = None, manifest: Optional[dict] = None) -> dict:
    profile = profile or get_profile() or {}
    tax_year = profile.get("meta", {}).get("tax_year", datetime.now().year)
    expected = _expected_documents(profile)

    classified = manifest.get("classified", []) if manifest else []
    extracted_data = manifest.get("extracted_data", {}) if manifest else {}
    docs = []

    for item in expected:
        matches = [entry for entry in classified if entry.get("category") == item["category"]]
        present_fields = set()
        for match in matches:
            data = extracted_data.get(match["original"], {})
            for key, value in data.items():
                if value not in (None, "", 0):
                    present_fields.add(key)

        if not matches:
            status = "missing"
        elif all(field in present_fields for field in item["required_fields"]):
            status = "present"
        else:
            status = "partial"

        docs.append(
            {
                **item,
                "status": status,
                "files_found": [match["original"] for match in matches],
                "fields_present": sorted(present_fields),
                "fields_missing": [
                    field for field in item["required_fields"] if field not in present_fields
                ],
            }
        )

    score_weights = {"present": 1.0, "partial": 0.5, "missing": 0.0}
    total_score = sum(score_weights[doc["status"]] for doc in docs)
    max_score = len(docs) or 1
    readiness = round(total_score / max_score * 100)

    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "tax_year": tax_year,
        "documents": docs,
        "document_count": len(docs),
        "present_count": sum(doc["status"] == "present" for doc in docs),
        "partial_count": sum(doc["status"] == "partial" for doc in docs),
        "missing_count": sum(doc["status"] == "missing" for doc in docs),
        "coverage_pct": readiness,
        "review_queue": [entry["original"] for entry in manifest.get("unclassified", [])] if manifest else [],
    }
