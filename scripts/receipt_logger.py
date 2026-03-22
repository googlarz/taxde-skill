"""
TaxDE Receipt Logger
Logs individual receipts throughout the year and maintains running totals.
All receipts are stored in the project TaxDE profile under current_year_receipts.
"""

from __future__ import annotations
from datetime import datetime
from typing import Optional

try:
    from profile_manager import get_profile, update_profile
    from tax_rules import (
        calculate_equipment_deduction,
        coerce_receipt_deductible_amount,
        equipment_useful_life,
        get_tax_year_rules,
    )
except ImportError:
    import sys, os
    sys.path.insert(0, os.path.dirname(__file__))
    from profile_manager import get_profile, update_profile
    from tax_rules import (
        calculate_equipment_deduction,
        coerce_receipt_deductible_amount,
        equipment_useful_life,
        get_tax_year_rules,
    )

# ── Category definitions ──────────────────────────────────────────────────────

CATEGORIES = {
    "equipment":    "Arbeitsmittel (§9 Abs.1 Nr.6 EStG)",
    "homeoffice":   "Homeoffice Pauschale (§4 Abs.5 Nr.6b EStG)",
    "commute":      "Pendlerpauschale (§9 Abs.1 Nr.4 EStG)",
    "fortbildung":  "Fortbildung (§9 Abs.1 Nr.6 EStG)",
    "books":        "Fachliteratur (§9 Abs.1 Nr.6 EStG)",
    "internet":     "Internet/Telefon (§9 EStG)",
    "donation":     "Spenden (§10b EStG)",
    "insurance":    "Versicherungen (§10 Abs.1 Nr.2 EStG)",
    "kita":         "Kinderbetreuung (§10 Abs.1 Nr.5 EStG)",
    "handwerker":   "Handwerkerleistungen §35a EStG",
    "haushalts":    "Haushaltsnahe Dienstleistungen §35a EStG",
    "medical":      "Krankheitskosten (§33 EStG)",
    "pension":      "Altersvorsorgezulage",
    "other":        "Sonstiges",
}

# Thresholds and caps.
# Year-specific childcare percentages and caps are pulled from tax_rules.py.
THRESHOLDS = {
    "equipment": {
        "gwg_net": 800,           # GWG threshold net — above this: depreciate over useful life
        "gwg_gross": 952,         # including 19% VAT
        "soft_scrutiny": 2_000,   # unofficial threshold where Finanzamt looks harder
    },
    "donation": {
        "simplified_max": 300,    # Vereinfachter Zuwendungsnachweis (no Quittung needed)
        "income_max_pct": 0.20,   # 20% of income — hard cap
    },
    "homeoffice": {
        "max_days": 210,
        "rate": 6,
        "max_annual": 1_260,
    },
    "riester": {"max": 2_100},
    "ruerup": {"note": "see refund_calculator for annual max"},
    "internet": {
        "typical_max": 240,       # ~€20/month × 12, ~20% of line rental
    },
    "handwerker": {
        "labor_only_max": 6_000,  # §35a: 20% of up to €6,000 labor = €1,200 credit
        "max_credit": 1_200,
    },
    "haushalts": {
        "max": 20_000,            # §35a: 20% of up to €20,000 = €4,000 credit
        "max_credit": 4_000,
    },
}


# ── Add Receipt ───────────────────────────────────────────────────────────────

def add_receipt(
    date: str,
    category: str,
    description: str,
    amount: float,
    business_use_pct: float = 100.0,
    document_ref: Optional[str] = None,
) -> dict:
    """
    Add a receipt to the current year log.
    Returns a dict with the new receipt plus updated category totals and any warnings.
    """
    if category not in CATEGORIES:
        # Try fuzzy match
        for k in CATEGORIES:
            if k in category.lower() or category.lower() in k:
                category = k
                break
        else:
            category = "other"

    # Normalise date
    try:
        datetime.fromisoformat(date)
    except ValueError:
        date = datetime.now().date().isoformat()

    profile = get_profile() or {}
    tax_year = profile.get("meta", {}).get("tax_year", datetime.now().year)
    receipt = {
        "date": date,
        "category": category,
        "description": description,
        "amount": round(amount, 2),
        "business_use_pct": business_use_pct,
        "document_ref": document_ref,
    }
    receipt["deductible_amount"] = coerce_receipt_deductible_amount(receipt, tax_year)
    receipts = profile.get("current_year_receipts", [])
    receipts.append(receipt)
    update_profile({"current_year_receipts": receipts})

    totals = get_totals()
    warnings = check_thresholds()

    return {
        "receipt_added": receipt,
        "category_total": totals.get(category, {}),
        "warnings": warnings,
        "display": _format_receipt_added(receipt, totals, warnings),
    }


# ── Totals ────────────────────────────────────────────────────────────────────

def get_totals() -> dict:
    """Return current year totals by category with deductible amounts."""
    profile = get_profile() or {}
    receipts = profile.get("current_year_receipts", [])

    totals: dict = {}
    for r in receipts:
        cat = r.get("category", "other")
        if cat not in totals:
            totals[cat] = {
                "count": 0,
                "gross_total": 0.0,
                "deductible_total": 0.0,
                "label": CATEGORIES.get(cat, cat),
            }
        totals[cat]["count"] += 1
        totals[cat]["gross_total"] += r.get("amount", 0)
        totals[cat]["deductible_total"] += r.get("deductible_amount", 0)

    # Round
    for cat in totals:
        totals[cat]["gross_total"] = round(totals[cat]["gross_total"], 2)
        totals[cat]["deductible_total"] = round(totals[cat]["deductible_total"], 2)

    return totals


# ── Summary Display ───────────────────────────────────────────────────────────

def get_summary_display() -> str:
    """Return a formatted running summary for user display."""
    totals = get_totals()
    if not totals:
        return "No receipts logged yet for this year."

    lines = ["📋 Running receipt log\n"]
    grand_total = 0.0
    for cat, data in sorted(totals.items()):
        label = data["label"]
        count = data["count"]
        ded = data["deductible_total"]
        grand_total += ded
        lines.append(f"  {label[:40]:<40} {count:>3} receipts  €{ded:>8,.2f}")

    lines.append(f"\n  {'Total deductible':<43} €{grand_total:>8,.2f}")

    warnings = check_thresholds()
    if warnings:
        lines.append("\n⚠️  Threshold alerts:")
        for w in warnings:
            lines.append(f"  • {w['message']}")

    return "\n".join(lines)


# ── Threshold Checks ──────────────────────────────────────────────────────────

def check_thresholds() -> list:
    """Return list of threshold warnings."""
    profile = get_profile() or {}
    receipts = profile.get("current_year_receipts", [])
    gross = profile.get("employment", {}).get("annual_gross", 0) or 0
    warnings = []

    totals = get_totals()

    # Equipment GWG
    equip = totals.get("equipment", {})
    if equip:
        equip_total = equip["deductible_total"]
        if equip_total > THRESHOLDS["equipment"]["soft_scrutiny"]:
            warnings.append({
                "category": "equipment",
                "level": "info",
                "message": (f"Arbeitsmittel total €{equip_total:,.0f} exceeds €2,000 soft scrutiny threshold. "
                             "Keep all invoices and be prepared to explain business use."),
            })
        for r in receipts:
            if r.get("category") == "equipment":
                if r.get("amount", 0) > THRESHOLDS["equipment"]["gwg_gross"]:
                    warnings.append({
                        "category": "equipment",
                        "level": "warning",
                        "message": (f"Receipt '{r['description']}' €{r['amount']:,.2f} exceeds GWG threshold "
                                     "(€800 net). Must be depreciated over useful life, not expensed in full."),
                    })

    # Donations income cap
    donations = totals.get("donation", {})
    if donations and gross > 0:
        don_total = donations["deductible_total"]
        income_max = gross * THRESHOLDS["donation"]["income_max_pct"]
        if don_total > income_max:
            warnings.append({
                "category": "donation",
                "level": "warning",
                "message": f"Donations €{don_total:,.0f} exceed 20% income cap (€{income_max:,.0f}). Excess carries forward.",
            })

    # Homeoffice days approaching max
    ho_receipts = [r for r in receipts if r.get("category") == "homeoffice"]
    if ho_receipts:
        ho_days = sum(r.get("amount", 0) / THRESHOLDS["homeoffice"]["rate"] for r in ho_receipts)
        max_days = THRESHOLDS["homeoffice"]["max_days"]
        if ho_days >= max_days:
            warnings.append({
                "category": "homeoffice",
                "level": "info",
                "message": f"Homeoffice maximum reached: {int(ho_days)}/{max_days} days = €{int(ho_days)*6:,}.",
            })
        elif ho_days >= max_days * 0.85:
            remaining = max_days - int(ho_days)
            warnings.append({
                "category": "homeoffice",
                "level": "tip",
                "message": (f"Homeoffice: {int(ho_days)}/{max_days} days logged. "
                             f"{remaining} days left to reach annual maximum €{max_days*6:,}."),
            })

    # Handwerker labor check
    hw = totals.get("handwerker", {})
    if hw:
        hw_labor = hw["deductible_total"]
        max_labor = THRESHOLDS["handwerker"]["labor_only_max"]
        credit = min(hw_labor, max_labor) * 0.20
        if hw_labor >= max_labor * 0.80:
            warnings.append({
                "category": "handwerker",
                "level": "tip",
                "message": (f"Handwerker labor costs €{hw_labor:,.0f}. "
                             f"§35a credit so far: €{credit:,.0f} (max credit €1,200). "
                             "Ensure invoices split labor from materials."),
            })

    return warnings


# ── Formatting Helpers ─────────────────────────────────────────────────────────

def _format_receipt_added(receipt: dict, totals: dict, warnings: list) -> str:
    cat = receipt["category"]
    cat_data = totals.get(cat, {})
    cat_total = cat_data.get("deductible_total", 0)
    label = CATEGORIES.get(cat, cat)
    tax_year = (get_profile() or {}).get("meta", {}).get("tax_year", datetime.now().year)
    year_rules = get_tax_year_rules(tax_year)

    lines = [
        f"✅ Receipt logged: {receipt['description']}",
        f"   Amount: €{receipt['amount']:,.2f}  |  Deductible: €{receipt['deductible_amount']:,.2f}",
        f"   Category: {label}",
        f"   Running total for this category: €{cat_total:,.2f}",
    ]

    # Category-specific tips
    if cat == "equipment":
        if receipt["amount"] > THRESHOLDS["equipment"]["gwg_gross"]:
            years = equipment_useful_life(receipt["description"])
            annual = calculate_equipment_deduction(
                receipt["amount"],
                receipt["description"],
                receipt.get("business_use_pct", 100.0),
                tax_year,
            )
            lines.append(f"   ℹ️  Above GWG (€952 gross) → depreciate over {years} years: €{annual:,.2f}/year")
        else:
            lines.append(f"   ℹ️  Below GWG — fully deductible in year of purchase")

    elif cat == "handwerker":
        credit = receipt["deductible_amount"] * 0.20
        lines.append(f"   ℹ️  §35a credit on this invoice: €{credit:,.2f} (20% of labor costs)")
        lines.append(f"   ⚠️  Must pay by bank transfer — cash payments not accepted!")

    elif cat == "donation":
        if receipt["amount"] <= 300:
            lines.append(f"   ✅ Under €300 — simplified proof (Kontoauszug) sufficient")
        else:
            lines.append(f"   ⚠️  Over €300 — Zuwendungsbestätigung from the charity required")

    elif cat == "kita":
        pct = int(year_rules["kinderbetreuung_pct"] * 100)
        cap = year_rules["kinderbetreuung_max"]
        lines.append(f"   ℹ️  {pct}% deductible for tax year {tax_year}, up to €{cap:,.0f} per child")

    if warnings:
        lines.append("")
        for w in warnings[:2]:  # Show max 2 warnings
            lines.append(f"   ⚠️  {w['message']}")

    return "\n".join(lines)
if __name__ == "__main__":
    from profile_manager import delete_profile, update_profile as up
    delete_profile()
    up({"meta": {"tax_year": 2024}, "employment": {"annual_gross": 65000}})

    result = add_receipt("2024-03-15", "equipment", "Laptop Dell XPS 13", 1_299.00)
    print(result["display"])
    print()

    add_receipt("2024-04-01", "equipment", "Webcam Logitech C920", 79.99)
    add_receipt("2024-05-10", "donation", "UNHCR Spende", 150.00)
    add_receipt("2024-06-20", "handwerker", "Malerarbeiten Arbeitszimmer (Lohn)", 800.00)

    print(get_summary_display())
    delete_profile()
    print("\nAll receipt_logger tests passed.")
