"""
TaxDE Refund Calculator
Maintains a running refund estimate with confidence scoring.
All formulas are based on German income tax law (EStG).

Bundled rules cover 2024-2026 and should still be cross-checked against the
latest BMF publications before filing.
"""

from __future__ import annotations

from typing import Optional

try:
    from tax_rules import (
        calculate_income_tax,
        calculate_soli,
        coerce_receipt_deductible_amount,
        get_tax_year_rules,
        resolve_supported_year,
    )
except ImportError:
    import os
    import sys

    sys.path.insert(0, os.path.dirname(__file__))
    from tax_rules import (
        calculate_income_tax,
        calculate_soli,
        coerce_receipt_deductible_amount,
        get_tax_year_rules,
        resolve_supported_year,
    )


# ── Main Calculator ───────────────────────────────────────────────────────────

def calculate_refund(profile: dict, deductions: Optional[dict] = None) -> dict:
    """
    Returns a full refund estimate dict with breakdown and confidence score.

    profile: taxde_profile dict (from profile_manager)
    deductions: optional override dict; keys match deduction categories.
                If None, deductions are estimated from profile alone.
    """
    requested_year = profile.get("meta", {}).get("tax_year", 2024)
    year, year_note = resolve_supported_year(requested_year)
    p = get_tax_year_rules(year)
    emp = profile.get("employment", {})
    fam = profile.get("family", {})
    housing = profile.get("housing", {})
    ins = profile.get("insurance", {})
    special = profile.get("special", {})

    gross = emp.get("annual_gross") or 0.0
    nebenjob_income = emp.get("nebenjob_income") or 0.0
    steuerklasse = emp.get("steuerklasse", "I")
    married = fam.get("status") in ("married", "civil_partnership")
    children = fam.get("children", [])
    bundesland = profile.get("personal", {}).get("bundesland", "")
    kirchensteuer = profile.get("personal", {}).get("kirchensteuer", False)

    confidence = 100
    confidence_detractors = []
    missing_data_impact = []

    if year_note:
        confidence -= 10
        confidence_detractors.append(year_note)

    # ── Werbungskosten ────────────────────────────────────────────────────────
    werbungskosten = 0.0

    # Homeoffice
    ho_days_pw = housing.get("homeoffice_days_per_week")
    if ho_days_pw is not None:
        annual_ho_days = min(int(ho_days_pw * 46), p["homeoffice_max_days"])  # ~46 working weeks
        ho_pauschale = min(annual_ho_days * p["homeoffice_tagespauschale"], p["homeoffice_max_annual"])
    else:
        ho_pauschale = 0.0
        confidence -= 10
        confidence_detractors.append("Homeoffice days not confirmed — using 0")
        missing_data_impact.append({"field": "housing.homeoffice_days_per_week",
                                     "potential_additional_refund": p["homeoffice_max_annual"] * 0.30})

    # Pendlerpauschale
    commute_km = housing.get("commute_km") or 0.0
    commute_days = housing.get("commute_days_per_year") or 0
    if commute_km > 0 and commute_days > 0:
        short_km = min(commute_km, 20)
        long_km = max(commute_km - 20, 0)
        pendler = commute_days * (short_km * p["pendlerpauschale_short"] + long_km * p["pendlerpauschale_long"])
    else:
        pendler = 0.0
        if emp.get("type") == "angestellter":
            confidence -= 5
            missing_data_impact.append({"field": "housing.commute_km",
                                         "potential_additional_refund": 200.0})

    # Arbeitsmittel (from receipt log)
    receipts = profile.get("current_year_receipts", [])
    arbeitsmittel = sum(
        coerce_receipt_deductible_amount(r, year)
        for r in receipts if r.get("category") == "equipment"
    )

    # Fortbildung
    fortbildung = sum(
        coerce_receipt_deductible_amount(r, year)
        for r in receipts if r.get("category") == "fortbildung"
    )

    # Gewerkschaft
    gewerkschaft = special.get("gewerkschaft_beitrag") or 0.0

    total_werbungskosten = max(
        p["arbeitnehmer_pauschbetrag"],
        ho_pauschale + pendler + arbeitsmittel + fortbildung + gewerkschaft
    )
    werbungskosten = total_werbungskosten

    # ── Sonderausgaben ────────────────────────────────────────────────────────
    sonderausgaben = p["sonderausgaben_pauschbetrag"] * (2 if married else 1)

    # Riester
    riester = ins.get("riester_contribution") or 0.0
    if ins.get("riester"):
        riester = min(riester, p["riester_max"])
        sonderausgaben += riester

    # Rürup
    ruerup_contrib = ins.get("ruerup_contribution") or 0.0
    if ins.get("ruerup"):
        ruerup_cap = p.get("ruerup_max_single")
        ruerup_deductible = ruerup_contrib if ruerup_cap is None else min(ruerup_contrib, ruerup_cap)
        if ruerup_cap is None:
            confidence -= 5
            confidence_detractors.append(
                f"{year} Ruerup annual ceiling is not bundled — refund assumes the entered contribution is deductible."
            )
        sonderausgaben += ruerup_deductible

    # bAV
    bav = ins.get("bav_contribution") or 0.0
    # bAV reduces gross directly (Entgeltumwandlung) — already in gross figure if employer-side
    # Here we treat it as reducing taxable income if not already reflected
    bav_deductible = min(bav, p["bav_4pct_bbg"])

    # Kinderbetreuung
    kita_total = 0.0
    for child in children:
        birth_year = child.get("birth_year")
        child_age = year - birth_year if birth_year else 99
        if child_age < 14 and child.get("kita"):
            cost = child.get("kita_annual_cost") or 0.0
            kita_total += min(cost * p["kinderbetreuung_pct"], p["kinderbetreuung_max"])
    sonderausgaben += kita_total

    # Donations from receipts
    donations = sum(r.get("amount", 0) for r in receipts if r.get("category") == "donation")
    sonderausgaben += donations

    # Kirchensteuer (§10 Abs 1 Nr 4 — itself deductible)
    if kirchensteuer and gross > 0:
        kt_rate = 0.08 if bundesland in ("Baden-Württemberg", "Bayern") else 0.09
        # rough KiSt estimate — deductible as Sonderausgaben
        approx_lst = gross * 0.22  # rough average rate
        kirchensteuer_paid = approx_lst * kt_rate
        sonderausgaben += kirchensteuer_paid

    # ── Außergewöhnliche Belastungen ──────────────────────────────────────────
    agb = 0.0
    disability_grade = special.get("disability_grade") or 0
    if disability_grade >= 20:
        grades = p["behindertenpauschbetrag"]
        # Round down to nearest 10
        g = (disability_grade // 10) * 10
        agb += grades.get(g, 0)

    # ── Kinderfreibetrag vs Kindergeld Günstigerprüfung ───────────────────────
    kindergeld_annual = len(children) * p["kindergeld_per_child"] * 12
    kinderfreibetrag_total = len(children) * (
        (p["kinderfreibetrag_child"] + p["kinderfreibetrag_bea"]) * (2 if married else 1)
    )

    # ── ZVE Calculation ───────────────────────────────────────────────────────
    total_income = gross + nebenjob_income

    if emp.get("type") in ("freelancer", "freiberufler", "gewerbe"):
        confidence -= 10
        confidence_detractors.append("Freelance income — EÜR not confirmed")
        missing_data_impact.append({"field": "freelance.net_profit",
                                     "potential_additional_refund": 300.0})

    zve = max(0, total_income - werbungskosten - sonderausgaben - agb - bav_deductible)

    # Splitting for married couples
    if married:
        tax = calculate_income_tax(zve / 2, year) * 2
    else:
        tax = calculate_income_tax(zve, year)

    # Kinderfreibetrag Günstigerprüfung
    if children:
        zve_with_kfb = max(0, zve - kinderfreibetrag_total)
        if married:
            tax_with_kfb = calculate_income_tax(zve_with_kfb / 2, year) * 2
        else:
            tax_with_kfb = calculate_income_tax(zve_with_kfb, year)
        kfb_advantage = tax - tax_with_kfb - kindergeld_annual
        if kfb_advantage > 0:
            tax = tax_with_kfb  # Günstigerprüfung → KFB is better

    soli = calculate_soli(tax, year)
    total_tax_due = tax + soli

    # Estimate LSt already paid (simplified — should come from Lohnsteuerbescheinigung)
    # We approximate using standard LSt tables
    bereits_gezahlt = _estimate_lohnsteuer_paid(gross, steuerklasse, married, year)
    if bereits_gezahlt is None:
        confidence -= 15
        confidence_detractors.append("Lohnsteuerbescheinigung not confirmed — LSt estimated")
        missing_data_impact.append({"field": "lohnsteuerbescheinigung.lohnsteuer",
                                     "potential_additional_refund": 150.0})
        bereits_gezahlt = gross * _lohnsteuer_avg_rate(steuerklasse)

    estimated_refund = bereits_gezahlt - total_tax_due

    # ── Confidence Score ──────────────────────────────────────────────────────
    if not profile.get("personal", {}).get("name"):
        confidence -= 5
    if not ins.get("krankenkasse_type"):
        confidence -= 5
        confidence_detractors.append("Krankenversicherung type unknown")

    # Foreign income
    if special.get("expat") and special.get("dba_relevant"):
        confidence -= 20
        confidence_detractors.append("Foreign income — Progressionsvorbehalt not modelled")

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
            "nebenjob_income": nebenjob_income,
            "total_werbungskosten": round(werbungskosten, 2),
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


def _lohnsteuer_avg_rate(steuerklasse: str) -> float:
    """Rough average LSt rate by Steuerklasse for estimation fallback."""
    rates = {"I": 0.18, "II": 0.16, "III": 0.12, "IV": 0.18, "V": 0.30, "VI": 0.35}
    return rates.get(steuerklasse, 0.18)


def _estimate_lohnsteuer_paid(gross: float, steuerklasse: str,
                               married: bool, year: int) -> Optional[float]:
    """
    Rough LSt estimate for fallback only. Returns None to signal low confidence.
    In practice, the Lohnsteuerbescheinigung provides the exact figure.
    """
    if not gross:
        return None
    # Use the actual tax formula with Steuerklasse-specific deductions
    # This is an approximation — real LSt uses monthly tables
    p = get_tax_year_rules(year)
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
        # No deductions in V — very high withholding
        return calculate_income_tax(max(0, gross), year) * 1.15
    return None


def format_refund_display(result: dict) -> str:
    """Return a formatted string for showing to the user."""
    refund = result["estimated_refund"]
    confidence = result["confidence_pct"]
    label = result["confidence_label"]
    bd = result["breakdown"]

    sign = "+" if refund >= 0 else ""
    lines = [
        f"💰 Estimated refund: {sign}€{refund:,.0f}",
        f"   Confidence: {label} ({confidence}%)\n",
        "── Breakdown ──────────────────────────────",
        f"Gross income:          €{bd['gross_income']:>10,.0f}",
    ]
    if bd.get("nebenjob_income"):
        lines.append(f"Nebenjob income:       €{bd['nebenjob_income']:>10,.0f}")

    lines += [
        f"Werbungskosten:       −€{bd['total_werbungskosten']:>10,.0f}",
    ]
    wk = bd.get("werbungskosten_detail", {})
    if wk.get("homeoffice_pauschale"):
        lines.append(f"  Homeoffice:          €{wk['homeoffice_pauschale']:>10,.0f}")
    if wk.get("pendlerpauschale"):
        lines.append(f"  Pendler:             €{wk['pendlerpauschale']:>10,.0f}")
    if wk.get("arbeitsmittel"):
        lines.append(f"  Arbeitsmittel:       €{wk['arbeitsmittel']:>10,.0f}")

    lines += [
        f"Sonderausgaben:       −€{bd['total_sonderausgaben']:>10,.0f}",
        f"Außergew. Belast.:    −€{bd['total_agb']:>10,.0f}",
        "──────────────────────────────────────────",
        f"Zu verst. Einkommen:   €{bd['zu_versteuerndes_einkommen']:>10,.0f}",
        f"Income tax:           −€{bd['estimated_tax']:>10,.0f}",
        f"Solidaritätszuschlag: −€{bd['soli']:>10,.0f}",
        f"Total tax due:        −€{bd['total_tax_due']:>10,.0f}",
        f"LSt already paid:     +€{bd['bereits_gezahlte_lohnsteuer']:>10,.0f}",
        "══════════════════════════════════════════",
        f"Estimated refund:     {sign}€{refund:>10,.0f}",
    ]

    if result["confidence_detractors"]:
        lines.append("\n⚠️  Confidence limited by:")
        for d in result["confidence_detractors"]:
            lines.append(f"   • {d}")

    if result["missing_data_impact"]:
        lines.append("\n📈 Confirm these to improve accuracy:")
        for m in result["missing_data_impact"]:
            lines.append(f"   • {m['field']}: up to €{m['potential_additional_refund']:,.0f} additional")

    return "\n".join(lines)


if __name__ == "__main__":
    sample_profile = {
        "meta": {"tax_year": 2024},
        "personal": {"bundesland": "Berlin", "kirchensteuer": False},
        "employment": {
            "type": "angestellter",
            "steuerklasse": "I",
            "annual_gross": 65_000,
            "nebenjob": False,
        },
        "family": {"status": "single", "children": []},
        "housing": {
            "homeoffice_days_per_week": 3.0,
            "commute_km": 18,
            "commute_days_per_year": 100,
        },
        "insurance": {"riester": False, "ruerup": False, "bav": False},
        "special": {"expat": False, "disability": False, "gewerkschaft": False},
        "current_year_receipts": [
            {"category": "equipment", "amount": 950, "business_use_pct": 100},
        ],
    }
    result = calculate_refund(sample_profile)
    print(format_refund_display(result))
