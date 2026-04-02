"""
German locale plugin for Finance Assistant.

Bundles tax rules, social contributions, and filing deadlines for 2024-2026.
Ported directly from TaxDE with all original modules preserved.
"""

from __future__ import annotations

import os
import sys

# Ensure the scripts directory is on path for shared imports
_scripts_dir = os.path.join(os.path.dirname(__file__), "..", "..", "scripts")
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)

# Import from co-located locale modules
from locales.de.tax_rules import (
    TAX_YEAR_RULES,
    calculate_income_tax,
    calculate_soli,
    get_tax_year_rules,
    resolve_supported_year,
    calculate_equipment_deduction,
    coerce_receipt_deductible_amount,
    equipment_useful_life,
)
from locales.de.tax_calculator import calculate_refund, format_refund_display
from locales.de.tax_dates import get_filing_deadline, format_deadline_label

LOCALE_CODE = "de"
LOCALE_NAME = "Germany"
SUPPORTED_YEARS = [2024, 2025, 2026]
CURRENCY = "EUR"


def get_tax_rules(year: int) -> dict:
    return get_tax_year_rules(year)


def calculate_tax(profile: dict, year: int = None) -> dict:
    if year:
        profile = dict(profile)
        profile.setdefault("meta", {})["tax_year"] = year
    return calculate_refund(profile)


def get_filing_deadlines(year: int) -> list[dict]:
    return [
        {
            "type": "standard",
            "deadline": get_filing_deadline(year, advised=False).isoformat(),
            "label": format_deadline_label(year, advised=False),
        },
        {
            "type": "with_adviser",
            "deadline": get_filing_deadline(year, advised=True).isoformat(),
            "label": format_deadline_label(year, advised=True),
        },
    ]


def get_social_contributions(gross: float, year: int) -> dict:
    from locales.de.social_contributions import estimate_employee_social_contributions
    return estimate_employee_social_contributions(gross, year)


def get_deduction_categories() -> list[dict]:
    return [
        {"id": "homeoffice", "name": "Homeoffice-Pauschale", "basis": "§4 Abs. 5 Nr. 6b EStG"},
        {"id": "commute", "name": "Pendlerpauschale", "basis": "§9 Abs. 1 Nr. 4 EStG"},
        {"id": "equipment", "name": "Arbeitsmittel", "basis": "§9 Abs. 1 Nr. 6 EStG"},
        {"id": "education", "name": "Fortbildungskosten", "basis": "§9 Abs. 1 Nr. 6 EStG"},
        {"id": "donation", "name": "Spenden", "basis": "§10b EStG"},
        {"id": "childcare", "name": "Kinderbetreuungskosten", "basis": "§10 Abs. 1 Nr. 5 EStG"},
        {"id": "riester", "name": "Riester", "basis": "§10a EStG"},
        {"id": "ruerup", "name": "Rürup / Basisrente", "basis": "§10 Abs. 1 Nr. 2b EStG"},
        {"id": "bav", "name": "bAV", "basis": "§3 Nr. 63 EStG"},
        {"id": "union_dues", "name": "Gewerkschaftsbeiträge", "basis": "§9 Abs. 1 Nr. 3d EStG"},
        {"id": "disability", "name": "Behinderten-Pauschbetrag", "basis": "§33b EStG"},
    ]


def generate_tax_claims(profile: dict, year: int = None) -> list[dict]:
    from locales.de.claim_rules import generate_german_claims
    return generate_german_claims(profile, year)
