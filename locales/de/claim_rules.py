"""
German-specific claim generation — ported from TaxDE claim_engine.py.

Generates tax deduction claims from a Finance Assistant profile using
the German locale's tax rules.
"""

from __future__ import annotations
from datetime import datetime
from typing import Optional

from locales.de.tax_rules import get_tax_year_rules
from locales.de.tax_calculator import calculate_refund


def generate_german_claims(profile: dict, year: int = None) -> list[dict]:
    """Generate German tax claims from profile. Returns list of claim dicts."""
    year = year or profile.get("meta", {}).get("tax_year", datetime.now().year)
    rules = get_tax_year_rules(year)

    tax_extra = profile.get("tax_profile", {}).get("extra", {})
    emp = profile.get("employment", {})
    fam = profile.get("family", {})
    housing = profile.get("housing", {})
    receipts = profile.get("current_year_receipts", [])

    emp_type = emp.get("type", "")
    is_employee = emp_type in ("employed", "angestellter")

    claims = []

    # Homeoffice
    ho_days_pw = housing.get("homeoffice_days_per_week")
    if ho_days_pw is None and is_employee:
        claims.append(_claim(year, "werbungskosten", "Homeoffice-Pauschale", "homeoffice",
                             "needs_input", None, None, "likely",
                             "§4 Abs. 5 Nr. 6b EStG", "Confirm home-office days per week."))
    elif ho_days_pw:
        days = min(int(ho_days_pw * 46), rules["homeoffice_max_days"])
        amount = min(days * rules["homeoffice_tagespauschale"], rules["homeoffice_max_annual"])
        claims.append(_claim(year, "werbungskosten", "Homeoffice-Pauschale", "homeoffice",
                             "ready", amount, None, "definitive",
                             "§4 Abs. 5 Nr. 6b EStG", "Keep a day log."))

    # Commute
    commute_km = housing.get("commute_km")
    commute_days = housing.get("commute_days_per_year")
    if is_employee and not (commute_km and commute_days):
        claims.append(_claim(year, "werbungskosten", "Pendlerpauschale", "commute",
                             "needs_input", None, None, "likely",
                             "§9 Abs. 1 Nr. 4 EStG", "Confirm commute distance and office days."))
    elif commute_km and commute_days:
        short = min(commute_km, 20)
        long = max(commute_km - 20, 0)
        amount = commute_days * (short * rules["pendlerpauschale_short"] + long * rules["pendlerpauschale_long"])
        claims.append(_claim(year, "werbungskosten", "Pendlerpauschale", "commute",
                             "ready", amount, None, "definitive",
                             "§9 Abs. 1 Nr. 4 EStG", "Use actual commute days."))

    # Equipment from receipts
    equip_receipts = [r for r in receipts if r.get("category") == "equipment"]
    if equip_receipts:
        amount = sum(float(r.get("deductible_amount") or r.get("amount", 0)) for r in equip_receipts)
        claims.append(_claim(year, "werbungskosten", "Arbeitsmittel", "equipment",
                             "ready", amount, None, "likely",
                             "§9 Abs. 1 Nr. 6 EStG", "Keep invoices with business-use note."))
    elif is_employee:
        claims.append(_claim(year, "werbungskosten", "Arbeitsmittel", "equipment_opportunity",
                             "detected", None, None, "likely",
                             "§9 Abs. 1 Nr. 6 EStG", "Check if you bought work gear this year."))

    # Donations
    don_receipts = [r for r in receipts if r.get("category") == "donation"]
    if don_receipts:
        amount = sum(float(r.get("deductible_amount") or r.get("amount", 0)) for r in don_receipts)
        claims.append(_claim(year, "sonderausgaben", "Spenden", "donation",
                             "ready", amount, None, "definitive",
                             "§10b EStG", "Keep donation receipts."))

    # Childcare
    children = fam.get("children", [])
    for i, child in enumerate(children, 1):
        birth_year = child.get("birth_year")
        age = year - birth_year if birth_year else 99
        childcare = child.get("childcare") or child.get("kita")
        cost = child.get("childcare_annual_cost") or child.get("kita_annual_cost") or 0
        if age < 14 and childcare:
            if cost:
                amount = min(cost * rules["kinderbetreuung_pct"], rules["kinderbetreuung_max"])
                claims.append(_claim(year, "sonderausgaben", f"Kinderbetreuung (child {i})",
                                     f"childcare_{i}", "ready", amount, None, "definitive",
                                     "§10 Abs. 1 Nr. 5 EStG", "Keep invoice and bank transfer proof."))
            else:
                claims.append(_claim(year, "sonderausgaben", f"Kinderbetreuung (child {i})",
                                     f"childcare_{i}", "needs_evidence", None, None, "definitive",
                                     "§10 Abs. 1 Nr. 5 EStG", "Add annual childcare cost."))

    # Riester
    if tax_extra.get("riester"):
        contrib = float(tax_extra.get("riester_contribution") or 0)
        if contrib:
            claims.append(_claim(year, "sonderausgaben", "Riester", "riester",
                                 "ready", min(contrib, rules["riester_max"]), None, "definitive",
                                 "§10a EStG", "Keep provider statement for Anlage AV."))
        else:
            claims.append(_claim(year, "sonderausgaben", "Riester", "riester",
                                 "needs_evidence", None, None, "definitive",
                                 "§10a EStG", "Add annual Riester contribution."))

    # Rürup
    if tax_extra.get("ruerup"):
        contrib = float(tax_extra.get("ruerup_contribution") or 0)
        if contrib:
            cap = rules.get("ruerup_max_single")
            amount = contrib if cap is None else min(contrib, cap)
            claims.append(_claim(year, "sonderausgaben", "Rürup / Basisrente", "ruerup",
                                 "ready", amount, None, "likely" if cap is None else "definitive",
                                 "§10 Abs. 1 Nr. 2b EStG", "Keep provider statement."))

    # Union dues
    union = float(tax_extra.get("gewerkschaft_beitrag") or 0)
    if union > 0:
        claims.append(_claim(year, "werbungskosten", "Gewerkschaftsbeiträge", "union_dues",
                             "ready", union, None, "definitive",
                             "§9 Abs. 1 Nr. 3d EStG", "Keep union statement."))

    # Disability
    disability = int(tax_extra.get("disability_grade") or 0)
    if disability >= 20:
        g = (disability // 10) * 10
        amount = rules["behindertenpauschbetrag"].get(g, 0)
        claims.append(_claim(year, "aussergewoehnliche_belastungen", "Behinderten-Pauschbetrag",
                             "disability", "ready", amount, None, "definitive",
                             "§33b EStG", "Keep disability certificate."))

    # Sort: ready first, then by amount descending
    claims.sort(key=lambda c: (
        {"ready": 0, "needs_evidence": 1, "needs_input": 2, "detected": 3}.get(c["status"], 9),
        -(c.get("amount_deductible") or 0),
        c["title"],
    ))

    return claims


def _claim(year, category, title, claim_id, status, amount, refund_effect, confidence, legal_basis, next_action):
    return {
        "id": claim_id,
        "tax_year": year,
        "category": category,
        "title": title,
        "status": status,
        "amount_deductible": round(amount, 2) if amount is not None else None,
        "estimated_refund_effect": round(refund_effect, 2) if refund_effect is not None else None,
        "confidence": confidence,
        "legal_basis": legal_basis,
        "next_action": next_action,
    }
