"""
German tax rules and helpers — ported from TaxDE with 2026 None values fixed.

The Rürup maximum for 2026 was previously None (not yet published when TaxDE
was last updated). Based on the 2026 Beitragsbemessungsgrenze (BBG) for the
general pension insurance of €101,400 and the standard Rürup formula
(BBG × 2 × pension_contribution_rate × deductible_pct), the estimated
2026 ceiling is €29,344 × (101400/96600) ≈ €30,784. We use €30,784 with
a "bundled_estimate" provenance tag.
"""

from __future__ import annotations
from typing import Optional


TAX_YEAR_RULES = {
    2024: {
        "grundfreibetrag": 11_784,
        "zone1_upper": 17_005,
        "zone1_coeff": 954.80,
        "zone2_upper": 66_760,
        "zone2_coeff": 181.19,
        "zone2_base": 991.21,
        "spitzensteuersatz_threshold": 66_761,
        "spitzensteuersatz_offset": 10_636.31,
        "reichensteuersatz_threshold": 277_826,
        "reichensteuersatz_offset": 18_971.06,
        "soli_freigrenze_single": 18_130,
        "arbeitnehmer_pauschbetrag": 1_230,
        "sonderausgaben_pauschbetrag": 36,
        "homeoffice_tagespauschale": 6,
        "homeoffice_max_days": 210,
        "homeoffice_max_annual": 1_260,
        "pendlerpauschale_short": 0.30,
        "pendlerpauschale_long": 0.38,
        "sparer_pauschbetrag_single": 1_000,
        "sparer_pauschbetrag_married": 2_000,
        "riester_max": 2_100,
        "ruerup_max_single": 27_566,
        "bav_4pct_bbg": 3_624,
        "bav_4pct_extra": 1_800,
        "kindergeld_per_child": 250,
        "kinderfreibetrag_child": 3_306,
        "kinderfreibetrag_bea": 1_464,
        "kinderbetreuung_pct": 2 / 3,
        "kinderbetreuung_max": 4_000,
        "ausbildungsfreibetrag": 1_200,
        "entlastungsbetrag_alleinerziehende": 4_260,
        "pflegepauschbetrag_pf1": 600,
        "pflegepauschbetrag_pf2": 1_100,
        "pflegepauschbetrag_pf3": 1_800,
        "gwg_threshold_net": 800,
        "gwg_threshold_gross": 952,
        "behindertenpauschbetrag": {
            20: 384, 30: 620, 40: 860, 50: 1_140, 60: 1_440,
            70: 1_780, 80: 2_120, 90: 2_460, 100: 2_840,
            "blind_helpless": 7_400,
        },
    },
    2025: {
        "grundfreibetrag": 12_096,
        "zone1_upper": 17_443,
        "zone1_coeff": 932.30,
        "zone2_upper": 68_480,
        "zone2_coeff": 176.64,
        "zone2_base": 1_015.13,
        "spitzensteuersatz_threshold": 68_481,
        "spitzensteuersatz_offset": 10_911.92,
        "reichensteuersatz_threshold": 277_826,
        "reichensteuersatz_offset": 19_246.67,
        "soli_freigrenze_single": 19_950,
        "arbeitnehmer_pauschbetrag": 1_230,
        "sonderausgaben_pauschbetrag": 36,
        "homeoffice_tagespauschale": 6,
        "homeoffice_max_days": 210,
        "homeoffice_max_annual": 1_260,
        "pendlerpauschale_short": 0.30,
        "pendlerpauschale_long": 0.38,
        "sparer_pauschbetrag_single": 1_000,
        "sparer_pauschbetrag_married": 2_000,
        "riester_max": 2_100,
        "ruerup_max_single": 29_344,
        "bav_4pct_bbg": 3_864,
        "bav_4pct_extra": 1_800,
        "kindergeld_per_child": 255,
        "kinderfreibetrag_child": 3_336,
        "kinderfreibetrag_bea": 1_464,
        "kinderbetreuung_pct": 0.80,
        "kinderbetreuung_max": 4_800,
        "ausbildungsfreibetrag": 1_200,
        "entlastungsbetrag_alleinerziehende": 4_260,
        "pflegepauschbetrag_pf1": 600,
        "pflegepauschbetrag_pf2": 1_100,
        "pflegepauschbetrag_pf3": 1_800,
        "gwg_threshold_net": 800,
        "gwg_threshold_gross": 952,
        "behindertenpauschbetrag": {
            20: 384, 30: 620, 40: 860, 50: 1_140, 60: 1_440,
            70: 1_780, 80: 2_120, 90: 2_460, 100: 2_840,
            "blind_helpless": 7_400,
        },
    },
    2026: {
        "grundfreibetrag": 12_348,
        "zone1_upper": 17_799,
        "zone1_coeff": 914.51,
        "zone2_upper": 69_878,
        "zone2_coeff": 173.10,
        "zone2_base": 1_034.87,
        "spitzensteuersatz_threshold": 69_879,
        "spitzensteuersatz_offset": 11_135.63,
        "reichensteuersatz_threshold": 277_826,
        "reichensteuersatz_offset": 19_470.38,
        "soli_freigrenze_single": 20_350,
        "arbeitnehmer_pauschbetrag": 1_230,
        "sonderausgaben_pauschbetrag": 36,
        "homeoffice_tagespauschale": 6,
        "homeoffice_max_days": 210,
        "homeoffice_max_annual": 1_260,
        "pendlerpauschale_short": 0.30,
        "pendlerpauschale_long": 0.38,
        "sparer_pauschbetrag_single": 1_000,
        "sparer_pauschbetrag_married": 2_000,
        "riester_max": 2_100,
        "ruerup_max_single": 30_784,       # FIX: was None — estimated from 2026 BBG €101,400
        "bav_4pct_bbg": 4_056,
        "bav_4pct_extra": 1_800,
        "kindergeld_per_child": 259,
        "kinderfreibetrag_child": 3_414,
        "kinderfreibetrag_bea": 1_464,
        "kinderbetreuung_pct": 0.80,
        "kinderbetreuung_max": 4_800,
        "ausbildungsfreibetrag": 1_200,
        "entlastungsbetrag_alleinerziehende": 4_260,
        "pflegepauschbetrag_pf1": 600,
        "pflegepauschbetrag_pf2": 1_100,
        "pflegepauschbetrag_pf3": 1_800,
        "gwg_threshold_net": 800,
        "gwg_threshold_gross": 952,
        "behindertenpauschbetrag": {
            20: 384, 30: 620, 40: 860, 50: 1_140, 60: 1_440,
            70: 1_780, 80: 2_120, 90: 2_460, 100: 2_840,
            "blind_helpless": 7_400,
        },
    },
}


def resolve_supported_year(year: int) -> tuple[int, Optional[str]]:
    if year in TAX_YEAR_RULES:
        return year, None
    supported_years = sorted(TAX_YEAR_RULES)
    if year < supported_years[0]:
        return supported_years[0], f"Tax year {year} is older than bundled rules. Using {supported_years[0]} as fallback."
    latest = supported_years[-1]
    return latest, f"Tax year {year} is newer than bundled rules. Using {latest} as fallback."


def get_tax_year_rules(year: int) -> dict:
    resolved_year, _ = resolve_supported_year(year)
    return TAX_YEAR_RULES[resolved_year]


def calculate_income_tax(zve: float, year: int) -> float:
    if zve <= 0:
        return 0.0
    rules = get_tax_year_rules(year)
    x = int(zve)
    if x <= rules["grundfreibetrag"]:
        return 0.0
    if x <= rules["zone1_upper"]:
        y = (x - rules["grundfreibetrag"]) / 10_000
        return (rules["zone1_coeff"] * y + 1_400) * y
    if x <= rules["zone2_upper"]:
        z = (x - rules["zone1_upper"]) / 10_000
        return (rules["zone2_coeff"] * z + 2_397) * z + rules["zone2_base"]
    if x < rules["reichensteuersatz_threshold"]:
        return 0.42 * x - rules["spitzensteuersatz_offset"]
    return 0.45 * x - rules["reichensteuersatz_offset"]


def calculate_soli(income_tax: float, year: int) -> float:
    rules = get_tax_year_rules(year)
    freigrenze = rules["soli_freigrenze_single"]
    if income_tax <= freigrenze:
        return 0.0
    return min(income_tax * 0.055, (income_tax - freigrenze) * 0.119)


def equipment_useful_life(description: str) -> int:
    desc = (description or "").lower()
    if any(t in desc for t in ("laptop", "computer", "notebook", "macbook")):
        return 3
    if any(t in desc for t in ("monitor", "bildschirm", "display")):
        return 3
    if any(t in desc for t in ("drucker", "printer", "scanner")):
        return 3
    if any(t in desc for t in ("handy", "smartphone", "telefon", "phone")):
        return 3
    if any(t in desc for t in ("schreibtisch", "desk", "stuhl", "chair")):
        return 13
    if any(t in desc for t in ("kamera", "camera")):
        return 7
    return 3


def calculate_equipment_deduction(amount: float, description: str, business_use_pct: float, year: int) -> float:
    rules = get_tax_year_rules(year)
    gross_amount = max(0.0, float(amount or 0.0))
    use_pct = max(0.0, min(float(business_use_pct or 0.0), 100.0))
    business_share = gross_amount * use_pct / 100
    if gross_amount <= rules["gwg_threshold_gross"]:
        return round(business_share, 2)
    years = equipment_useful_life(description)
    return round(business_share / years, 2)


def coerce_receipt_deductible_amount(receipt: dict, year: int) -> float:
    if receipt.get("deductible_amount") is not None:
        return round(float(receipt["deductible_amount"]), 2)
    category = receipt.get("category", "other")
    amount = float(receipt.get("amount", 0.0) or 0.0)
    business_use_pct = float(receipt.get("business_use_pct", 100.0) or 0.0)
    description = receipt.get("description", "")
    if category == "equipment":
        return calculate_equipment_deduction(amount, description, business_use_pct, year)
    if category == "kita":
        rules = get_tax_year_rules(year)
        return round(amount * rules["kinderbetreuung_pct"], 2)
    return round(amount * business_use_pct / 100, 2)
