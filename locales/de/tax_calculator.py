"""
German tax refund calculator — ported from TaxDE refund_calculator.py.

Adapted to work with the Finance Assistant's expanded profile schema
while preserving all original calculation logic.
"""

from __future__ import annotations
from typing import Optional

from locales.de.tax_rules import (
    calculate_income_tax,
    calculate_soli,
    coerce_receipt_deductible_amount,
    get_tax_year_rules,
    resolve_supported_year,
)


def _extract_german_fields(profile: dict) -> dict:
    """Map Finance Assistant profile to German tax fields."""
    tax_extra = profile.get("tax_profile", {}).get("extra", {})
    emp = profile.get("employment", {})
    fam = profile.get("family", {})
    housing = profile.get("housing", {})
    personal = profile.get("personal", {})

    # Map employment type back to German terms for internal use
    emp_type = emp.get("type", "")
    type_map = {"employed": "angestellter", "freelancer": "freelancer",
                "self_employed": "gewerbe", "mixed": "mixed", "retired": "rentner"}
    german_type = type_map.get(emp_type, emp_type)

    return {
        "type": german_type,
        "annual_gross": emp.get("annual_gross") or 0.0,
        "nebenjob_income": emp.get("side_income") or 0.0,
        "steuerklasse": profile.get("tax_profile", {}).get("tax_class") or "I",
        "married": fam.get("status") in ("married", "civil_partnership"),
        "children": fam.get("children", []),
        "bundesland": personal.get("region", ""),
        "kirchensteuer": profile.get("tax_profile", {}).get("church_tax", False),
        "homeoffice_days_per_week": housing.get("homeoffice_days_per_week"),
        "commute_km": housing.get("commute_km") or 0.0,
        "commute_days_per_year": housing.get("commute_days_per_year") or 0,
        "riester": tax_extra.get("riester", False),
        "riester_contribution": tax_extra.get("riester_contribution") or 0.0,
        "ruerup": tax_extra.get("ruerup", False),
        "ruerup_contribution": tax_extra.get("ruerup_contribution") or 0.0,
        "bav": tax_extra.get("bav", False),
        "bav_contribution": tax_extra.get("bav_contribution") or 0.0,
        "gewerkschaft_beitrag": tax_extra.get("gewerkschaft_beitrag") or 0.0,
        "disability_grade": tax_extra.get("disability_grade") or 0,
        "expat": tax_extra.get("expat", False),
        "dba_relevant": tax_extra.get("dba_relevant", False),
        "receipts": profile.get("current_year_receipts", []),
    }


def calculate_refund(profile: dict) -> dict:
    """Full refund estimate with breakdown and confidence scoring."""
    requested_year = profile.get("meta", {}).get("tax_year", 2024)
    year, year_note = resolve_supported_year(requested_year)
    p = get_tax_year_rules(year)
    g = _extract_german_fields(profile)

    gross = g["annual_gross"]
    confidence = 100
    confidence_detractors = []
    missing_data_impact = []

    if year_note:
        confidence -= 10
        confidence_detractors.append(year_note)

    # ── Werbungskosten ───────────────────────────────────────────────────
    ho_days_pw = g["homeoffice_days_per_week"]
    if ho_days_pw is not None:
        annual_ho_days = min(int(ho_days_pw * 46), p["homeoffice_max_days"])
        ho_pauschale = min(annual_ho_days * p["homeoffice_tagespauschale"], p["homeoffice_max_annual"])
    else:
        ho_pauschale = 0.0
        if g["type"] == "angestellter":
            confidence -= 10
            confidence_detractors.append("Homeoffice days not confirmed — using 0")
            missing_data_impact.append({"field": "housing.homeoffice_days_per_week",
                                         "potential_additional_refund": p["homeoffice_max_annual"] * 0.30})

    commute_km = g["commute_km"]
    commute_days = g["commute_days_per_year"]
    if commute_km > 0 and commute_days > 0:
        short_km = min(commute_km, 20)
        long_km = max(commute_km - 20, 0)
        pendler = commute_days * (short_km * p["pendlerpauschale_short"] + long_km * p["pendlerpauschale_long"])
    else:
        pendler = 0.0
        if g["type"] == "angestellter":
            confidence -= 5
            missing_data_impact.append({"field": "housing.commute_km", "potential_additional_refund": 200.0})

    receipts = g["receipts"]
    arbeitsmittel = sum(coerce_receipt_deductible_amount(r, year) for r in receipts if r.get("category") == "equipment")
    fortbildung = sum(coerce_receipt_deductible_amount(r, year) for r in receipts if r.get("category") == "fortbildung")
    gewerkschaft = g["gewerkschaft_beitrag"]

    total_werbungskosten = max(p["arbeitnehmer_pauschbetrag"],
                                ho_pauschale + pendler + arbeitsmittel + fortbildung + gewerkschaft)

    # ── Sonderausgaben ───────────────────────────────────────────────────
    married = g["married"]
    sonderausgaben = p["sonderausgaben_pauschbetrag"] * (2 if married else 1)

    if g["riester"]:
        sonderausgaben += min(g["riester_contribution"], p["riester_max"])
    if g["ruerup"]:
        ruerup_cap = p.get("ruerup_max_single")
        ruerup_deductible = g["ruerup_contribution"] if ruerup_cap is None else min(g["ruerup_contribution"], ruerup_cap)
        if ruerup_cap is None:
            confidence -= 5
            confidence_detractors.append(f"{year} Ruerup annual ceiling not bundled — using entered contribution.")
        sonderausgaben += ruerup_deductible

    bav_deductible = min(g["bav_contribution"], p["bav_4pct_bbg"])

    children = g["children"]
    kita_total = 0.0
    for child in children:
        birth_year = child.get("birth_year")
        child_age = year - birth_year if birth_year else 99
        childcare = child.get("childcare") or child.get("kita")
        cost = child.get("childcare_annual_cost") or child.get("kita_annual_cost") or 0.0
        if child_age < 14 and childcare and cost:
            kita_total += min(cost * p["kinderbetreuung_pct"], p["kinderbetreuung_max"])
    sonderausgaben += kita_total

    donations = sum(r.get("amount", 0) for r in receipts if r.get("category") == "donation")
    sonderausgaben += donations

    kirchensteuer_paid = 0.0
    if g["kirchensteuer"] and gross > 0:
        kt_rate = 0.08 if g["bundesland"] in ("Baden-Württemberg", "Bayern") else 0.09
        kirchensteuer_paid = gross * 0.22 * kt_rate
        sonderausgaben += kirchensteuer_paid

    # ── Außergewöhnliche Belastungen ─────────────────────────────────────
    agb = 0.0
    disability_grade = g["disability_grade"]
    if disability_grade >= 20:
        g_rounded = (disability_grade // 10) * 10
        agb += p["behindertenpauschbetrag"].get(g_rounded, 0)

    # ── Kinderfreibetrag vs Kindergeld ───────────────────────────────────
    kindergeld_annual = len(children) * p["kindergeld_per_child"] * 12
    kinderfreibetrag_total = len(children) * (
        (p["kinderfreibetrag_child"] + p["kinderfreibetrag_bea"]) * (2 if married else 1)
    )

    # ── ZVE ──────────────────────────────────────────────────────────────
    total_income = gross + g["nebenjob_income"]
    if g["type"] in ("freelancer", "freiberufler", "gewerbe"):
        confidence -= 10
        confidence_detractors.append("Freelance income — EÜR not confirmed")

    zve = max(0, total_income - total_werbungskosten - sonderausgaben - agb - bav_deductible)
    tax = calculate_income_tax(zve / 2, year) * 2 if married else calculate_income_tax(zve, year)

    if children:
        zve_kfb = max(0, zve - kinderfreibetrag_total)
        tax_kfb = calculate_income_tax(zve_kfb / 2, year) * 2 if married else calculate_income_tax(zve_kfb, year)
        if (tax - tax_kfb - kindergeld_annual) > 0:
            tax = tax_kfb

    soli = calculate_soli(tax, year)
    total_tax_due = tax + soli

    steuerklasse = g["steuerklasse"]
    bereits_gezahlt = _estimate_lohnsteuer_paid(gross, steuerklasse, married, year, p)
    if bereits_gezahlt is None:
        confidence -= 15
        confidence_detractors.append("Lohnsteuerbescheinigung not confirmed — LSt estimated")
        rates = {"I": 0.18, "II": 0.16, "III": 0.12, "IV": 0.18, "V": 0.30, "VI": 0.35}
        bereits_gezahlt = gross * rates.get(steuerklasse, 0.18)

    estimated_refund = bereits_gezahlt - total_tax_due
    confidence = max(0, min(100, confidence))

    if confidence >= 85:
        label = "Very High"
    elif confidence >= 70:
        label = "High"
    elif confidence >= 50:
        label = "Medium"
    else:
        label = "Low"

    return {
        "estimated_refund": round(estimated_refund, 2),
        "confidence_pct": confidence,
        "confidence_label": label,
        "breakdown": {
            "gross_income": gross,
            "nebenjob_income": g["nebenjob_income"],
            "total_werbungskosten": round(total_werbungskosten, 2),
            "werbungskosten_detail": {
                "homeoffice_pauschale": round(ho_pauschale, 2),
                "pendlerpauschale": round(pendler, 2),
                "arbeitsmittel": round(arbeitsmittel, 2),
                "fortbildung": round(fortbildung, 2),
                "gewerkschaft": round(gewerkschaft, 2),
            },
            "total_sonderausgaben": round(sonderausgaben, 2),
            "total_agb": round(agb, 2),
            "bav_deductible": round(bav_deductible, 2),
            "zu_versteuerndes_einkommen": round(zve, 2),
            "estimated_tax": round(tax, 2),
            "soli": round(soli, 2),
            "total_tax_due": round(total_tax_due, 2),
            "bereits_gezahlte_lohnsteuer": round(bereits_gezahlt, 2),
            "estimated_refund": round(estimated_refund, 2),
        },
        "missing_data_impact": missing_data_impact,
        "confidence_detractors": confidence_detractors,
    }


def _estimate_lohnsteuer_paid(gross, steuerklasse, married, year, p) -> Optional[float]:
    if not gross:
        return None
    if steuerklasse == "III":
        wk = p["arbeitnehmer_pauschbetrag"]
        sa = p["sonderausgaben_pauschbetrag"] * 2
        zve = max(0, gross * 2 - wk - sa)
        return calculate_income_tax(zve / 2, year)
    elif steuerklasse in ("I", "IV"):
        wk = p["arbeitnehmer_pauschbetrag"]
        sa = p["sonderausgaben_pauschbetrag"]
        zve = max(0, gross - wk - sa)
        return calculate_income_tax(zve, year)
    elif steuerklasse == "II":
        wk = p["arbeitnehmer_pauschbetrag"]
        sa = p["sonderausgaben_pauschbetrag"]
        entl = p["entlastungsbetrag_alleinerziehende"]
        zve = max(0, gross - wk - sa - entl)
        return calculate_income_tax(zve, year)
    elif steuerklasse == "V":
        return calculate_income_tax(max(0, gross), year) * 1.15
    return None


def format_refund_display(result: dict) -> str:
    refund = result["estimated_refund"]
    bd = result["breakdown"]
    sign = "+" if refund >= 0 else ""
    lines = [
        f"Estimated refund: {sign}EUR {refund:,.0f}",
        f"Confidence: {result['confidence_label']} ({result['confidence_pct']}%)",
        "",
        f"Gross: EUR {bd['gross_income']:,.0f}",
        f"Deductions: EUR {bd['total_werbungskosten']:,.0f}",
        f"Tax due: EUR {bd['total_tax_due']:,.0f}",
        f"Already paid: EUR {bd['bereits_gezahlte_lohnsteuer']:,.0f}",
        f"Refund: {sign}EUR {refund:,.0f}",
    ]
    if result["confidence_detractors"]:
        lines.append("\nLimited by:")
        for d in result["confidence_detractors"]:
            lines.append(f"  - {d}")
    return "\n".join(lines)
