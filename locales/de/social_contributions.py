"""
German social contribution calculation — extracted from TaxDE scenario_engine.py.
"""

from __future__ import annotations

SOCIAL_CAPS = {
    2024: {"rv_alv": 90_600, "gkv_pv": 62_100},
    2025: {"rv_alv": 96_600, "gkv_pv": 66_150},
    2026: {"rv_alv": 101_400, "gkv_pv": 69_750},
}

SOCIAL_RATES = {
    "rv_employee": 0.093,
    "alv_employee": 0.013,
    "gkv_employee": 0.0815,
    "pv_employee": 0.018,
}


def estimate_employee_social_contributions(annual_gross: float, year: int) -> dict:
    caps = SOCIAL_CAPS.get(year, SOCIAL_CAPS[max(SOCIAL_CAPS)])
    rv_base = min(annual_gross, caps["rv_alv"])
    gkv_base = min(annual_gross, caps["gkv_pv"])
    breakdown = {
        "pension": round(rv_base * SOCIAL_RATES["rv_employee"], 2),
        "unemployment": round(rv_base * SOCIAL_RATES["alv_employee"], 2),
        "health": round(gkv_base * SOCIAL_RATES["gkv_employee"], 2),
        "care": round(gkv_base * SOCIAL_RATES["pv_employee"], 2),
    }
    breakdown["total"] = round(sum(breakdown.values()), 2)
    return breakdown
