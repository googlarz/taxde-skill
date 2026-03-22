"""
Scenario tools for package comparisons and freelance break-even analysis.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Optional

try:
    from profile_manager import get_profile
    from refund_calculator import calculate_refund
    from tax_rules import calculate_income_tax, get_tax_year_rules
except ImportError:
    import os
    import sys

    sys.path.insert(0, os.path.dirname(__file__))
    from profile_manager import get_profile
    from refund_calculator import calculate_refund
    from tax_rules import calculate_income_tax, get_tax_year_rules


SOCIAL_CAPS = {
    2024: {"rv_alv": 90_600, "gkv_pv": 62_100},
    2025: {"rv_alv": 96_600, "gkv_pv": 66_150},
    2026: {"rv_alv": 101_400, "gkv_pv": 69_750},
}

SOCIAL_RATES = {
    "rv_employee": 0.093,
    "alv_employee": 0.013,
    "gkv_employee": 0.0815,   # 7.3% plus a typical employee Zusatzbeitrag share
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


def estimate_employee_package_net(
    package: dict,
    profile: Optional[dict] = None,
) -> dict:
    profile = deepcopy(profile or get_profile() or {})
    year = package.get("tax_year") or profile.get("meta", {}).get("tax_year", datetime.now().year)
    annual_gross = float(package.get("annual_gross") or 0.0)
    bav = float(package.get("bav_contribution") or 0.0)
    jobticket_value = float(package.get("jobticket_value") or 0.0)
    company_car_taxable_benefit = float(package.get("company_car_taxable_benefit") or 0.0)

    profile.setdefault("meta", {})["tax_year"] = year
    profile.setdefault("employment", {})
    profile["employment"]["annual_gross"] = annual_gross + company_car_taxable_benefit
    profile.setdefault("insurance", {})
    profile["insurance"]["bav"] = bav > 0
    profile["insurance"]["bav_contribution"] = bav

    tax_result = calculate_refund(profile)
    tax_due = float(tax_result["breakdown"]["total_tax_due"])
    social = estimate_employee_social_contributions(annual_gross + company_car_taxable_benefit, year)
    annual_net = annual_gross - bav - tax_due - social["total"] + jobticket_value

    return {
        "label": package.get("label", "package"),
        "tax_year": year,
        "annual_gross": annual_gross,
        "bav_contribution": bav,
        "jobticket_value": jobticket_value,
        "company_car_taxable_benefit": company_car_taxable_benefit,
        "tax_due": round(tax_due, 2),
        "social_contributions": social,
        "annual_net": round(annual_net, 2),
        "monthly_net": round(annual_net / 12, 2),
        "assumptions": [
            "Income tax is derived from the bundled TaxDE calculator.",
            "Employee social contributions are estimated with capped employee-side rates.",
            "Benefits such as company car are modeled as taxable benefit estimates, not full fleet-cost analysis.",
        ],
    }


def compare_salary_packages(
    packages: list[dict],
    profile: Optional[dict] = None,
    projection_years: int = 3,
    annual_raise_pct: float = 0.0,
) -> dict:
    if not packages:
        return {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "tax_year": None,
            "packages": [],
            "best_option": None,
            "baseline": None,
            "projection_years": projection_years,
        }

    raw_evaluations = [estimate_employee_package_net(package, profile=profile) for package in packages]
    baseline = raw_evaluations[0]
    evaluations = []

    for package, evaluation in zip(packages, raw_evaluations):
        projections = []
        for offset in range(projection_years):
            projected_package = dict(package)
            projected_package["tax_year"] = int(evaluation["tax_year"]) + offset
            projected_package["annual_gross"] = round(
                float(package.get("annual_gross") or 0.0) * ((1 + annual_raise_pct) ** offset),
                2,
            )
            projected_package["jobticket_value"] = round(
                float(package.get("jobticket_value") or 0.0) * ((1 + annual_raise_pct) ** offset),
                2,
            )
            projected_package["bav_contribution"] = round(
                float(package.get("bav_contribution") or 0.0) * ((1 + annual_raise_pct) ** offset),
                2,
            )
            projected_eval = estimate_employee_package_net(projected_package, profile=profile)
            projections.append(
                {
                    "year": projected_eval["tax_year"],
                    "annual_net": projected_eval["annual_net"],
                    "tax_due": projected_eval["tax_due"],
                    "social_contributions": projected_eval["social_contributions"]["total"],
                }
            )

        enriched = dict(evaluation)
        enriched["delta_vs_baseline"] = {
            "tax_effect": round(evaluation["tax_due"] - baseline["tax_due"], 2),
            "social_contribution_effect": round(
                evaluation["social_contributions"]["total"] - baseline["social_contributions"]["total"],
                2,
            ),
            "net_cash_effect": round(evaluation["annual_net"] - baseline["annual_net"], 2),
        }
        enriched["multi_year_projection"] = projections
        enriched["multi_year_net_total"] = round(sum(item["annual_net"] for item in projections), 2)
        evaluations.append(enriched)

    baseline_total = evaluations[0]["multi_year_net_total"]
    for evaluation in evaluations:
        evaluation["multi_year_delta_vs_baseline"] = round(
            evaluation["multi_year_net_total"] - baseline_total,
            2,
        )

    best_option = max(evaluations, key=lambda item: item["annual_net"])
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "tax_year": evaluations[0]["tax_year"],
        "packages": evaluations,
        "best_option": best_option,
        "baseline": evaluations[0],
        "projection_years": projection_years,
    }


def estimate_freelance_day_rate_to_match_net(
    profile: Optional[dict] = None,
    billable_days: int = 200,
    business_expense_pct: float = 0.12,
    annual_health_cost: float = 7_200.0,
    annual_pension_contribution: float = 0.0,
) -> dict:
    profile = profile or get_profile() or {}
    year = profile.get("meta", {}).get("tax_year", datetime.now().year)
    current_gross = float(profile.get("employment", {}).get("annual_gross") or 0.0)
    if current_gross <= 0:
        raise ValueError("Current employment gross income is required for freelance break-even analysis.")

    baseline = estimate_employee_package_net({"label": "current employment", "annual_gross": current_gross, "tax_year": year}, profile=profile)
    target_net = baseline["annual_net"]
    married = profile.get("family", {}).get("status") in {"married", "civil_partnership"}
    rules = get_tax_year_rules(year)

    def freelancer_net(day_rate: float) -> float:
        revenue = day_rate * billable_days
        business_expenses = revenue * business_expense_pct
        taxable_profit = max(0.0, revenue - business_expenses - annual_health_cost - annual_pension_contribution)
        zvE = max(0.0, taxable_profit - rules["sonderausgaben_pauschbetrag"])
        tax_due = calculate_income_tax(zvE / 2, year) * 2 if married else calculate_income_tax(zvE, year)
        return revenue - business_expenses - annual_health_cost - annual_pension_contribution - tax_due

    low, high = 50.0, 2_000.0
    for _ in range(40):
        mid = (low + high) / 2
        if freelancer_net(mid) >= target_net:
            high = mid
        else:
            low = mid

    recommended_day_rate = round(high, 2)
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "tax_year": year,
        "target_annual_net": round(target_net, 2),
        "recommended_day_rate": recommended_day_rate,
        "billable_days": billable_days,
        "assumptions": {
            "business_expense_pct": business_expense_pct,
            "annual_health_cost": annual_health_cost,
            "annual_pension_contribution": annual_pension_contribution,
        },
        "current_employment": baseline,
    }


if __name__ == "__main__":
    profile = get_profile() or {
        "meta": {"tax_year": 2025},
        "employment": {"annual_gross": 78_000},
        "family": {"status": "single"},
        "insurance": {},
    }
    print(compare_salary_packages([
        {"label": "base", "annual_gross": 78_000, "tax_year": profile.get("meta", {}).get("tax_year", 2025)},
        {"label": "benefits", "annual_gross": 74_000, "jobticket_value": 588, "bav_contribution": 2_400, "tax_year": profile.get("meta", {}).get("tax_year", 2025)},
    ], profile=profile))
