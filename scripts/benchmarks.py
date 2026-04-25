"""
Benchmark reference data for financial metrics.

Provides percentile context for savings rate, emergency fund, debt-to-income,
housing costs, investment allocation, and net worth — sourced from Eurostat,
ONS, Banque de France, CBS, GUS, and ECB HFCS.

No network calls. All data is embedded directly.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

# ── Static reference data ─────────────────────────────────────────────────────

SAVINGS_RATE_BENCHMARKS = {
    "de": {"p25": 0.06, "p50": 0.11, "p75": 0.22, "p90": 0.35, "source": "Bundesbank 2023"},
    "uk": {"p25": 0.03, "p50": 0.08, "p75": 0.18, "p90": 0.30, "source": "ONS 2023"},
    "fr": {"p25": 0.05, "p50": 0.12, "p75": 0.22, "p90": 0.33, "source": "Banque de France 2023"},
    "nl": {"p25": 0.07, "p50": 0.14, "p75": 0.25, "p90": 0.38, "source": "CBS 2023"},
    "pl": {"p25": 0.03, "p50": 0.08, "p75": 0.17, "p90": 0.28, "source": "GUS 2023"},
    "default": {"p25": 0.05, "p50": 0.10, "p75": 0.20, "p90": 0.32, "source": "Eurostat 2023"},
}

EMERGENCY_FUND_BENCHMARKS = {
    "default": {"p25": 0.5, "p50": 1.5, "p75": 3.0, "p90": 6.0, "recommended_min": 3.0},
}

DTI_BENCHMARKS = {
    "default": {
        "low": 0.15,
        "moderate": 0.36,
        "high": 0.50,
        "critical": 0.75,
    }
}

HOUSING_COST_BENCHMARKS = {
    "default": {
        "comfortable": 0.28,
        "stretched": 0.35,
        "stressed": 0.50,
    }
}

INVESTMENT_ALLOCATION_BENCHMARKS = {
    "default": {"conservative": 0.30, "balanced": 0.60, "growth": 0.80}
}

NET_WORTH_BY_AGE = {
    "de": {
        "25-34": {"p25": 8_000,  "p50": 28_000,  "p75": 72_000},
        "35-44": {"p25": 22_000, "p50": 68_000,  "p75": 180_000},
        "45-54": {"p25": 45_000, "p50": 130_000, "p75": 320_000},
        "55-64": {"p25": 60_000, "p50": 185_000, "p75": 450_000},
    },
    "uk": {
        "25-34": {"p25": 6_000,  "p50": 22_000,  "p75": 60_000},
        "35-44": {"p25": 18_000, "p50": 58_000,  "p75": 155_000},
        "45-54": {"p25": 38_000, "p50": 110_000, "p75": 280_000},
        "55-64": {"p25": 52_000, "p50": 160_000, "p75": 390_000},
    },
    "fr": {
        "25-34": {"p25": 7_000,  "p50": 25_000,  "p75": 65_000},
        "35-44": {"p25": 20_000, "p50": 62_000,  "p75": 170_000},
        "45-54": {"p25": 42_000, "p50": 120_000, "p75": 300_000},
        "55-64": {"p25": 56_000, "p50": 175_000, "p75": 430_000},
    },
    "nl": {
        "25-34": {"p25": 9_000,  "p50": 30_000,  "p75": 78_000},
        "35-44": {"p25": 25_000, "p50": 75_000,  "p75": 195_000},
        "45-54": {"p25": 50_000, "p50": 140_000, "p75": 340_000},
        "55-64": {"p25": 65_000, "p50": 200_000, "p75": 480_000},
    },
    "pl": {
        # Roughly 30-40% of DE values (NBP 2021)
        "25-34": {"p25": 2_500,  "p50": 9_000,   "p75": 24_000},
        "35-44": {"p25": 7_000,  "p50": 22_000,  "p75": 60_000},
        "45-54": {"p25": 15_000, "p50": 44_000,  "p75": 108_000},
        "55-64": {"p25": 20_000, "p50": 62_000,  "p75": 155_000},
    },
}

_AGE_BRACKETS = ["25-34", "35-44", "45-54", "55-64"]


# ── Internal helpers ──────────────────────────────────────────────────────────

def _resolve_locale(locale: str, table: dict) -> dict:
    key = (locale or "").lower()
    return table.get(key, table["default"])


def _savings_percentile_label(rate: float, benchmarks: dict) -> tuple[str, str]:
    """Return (percentile_str, label) from benchmark thresholds."""
    if rate >= benchmarks["p90"]:
        return "top 10%", "excellent"
    if rate >= benchmarks["p75"]:
        return "top 25%", "good"
    if rate > benchmarks["p50"]:
        return "above average", "good"
    if rate >= benchmarks["p25"]:
        return "average", "average"
    return "below average", "below average"


def _age_bracket(age: int) -> Optional[str]:
    if 25 <= age <= 34:
        return "25-34"
    if 35 <= age <= 44:
        return "35-44"
    if 45 <= age <= 54:
        return "45-54"
    if 55 <= age <= 64:
        return "55-64"
    return None


def _net_worth_percentile(net_worth: float, brackets: dict) -> str:
    if net_worth >= brackets["p75"]:
        return "top 25%"
    if net_worth >= brackets["p50"]:
        return "top 50%"
    if net_worth >= brackets["p25"]:
        return "above bottom 25%"
    return "bottom 25%"


# ── Public API ────────────────────────────────────────────────────────────────

def get_savings_rate_context(rate: float, locale: str = "default") -> Optional[dict]:
    """Return benchmark context for a savings rate value."""
    if rate is None:
        return None

    benchmarks = _resolve_locale(locale, SAVINGS_RATE_BENCHMARKS)
    percentile, label = _savings_percentile_label(rate, benchmarks)
    average = benchmarks["p50"]
    locale_name = locale.upper() if locale != "default" else "European"

    pct_str = f"{rate:.0%}"
    avg_str = f"{average:.0%}"
    message = (
        f"Your savings rate of {pct_str} is {label} — {percentile} for {locale_name} households. "
        f"Average is {avg_str}."
    )

    return {
        "metric": "savings_rate",
        "value": rate,
        "percentile": percentile,
        "label": label,
        "average": average,
        "message": message,
        "source": benchmarks["source"],
    }


def get_emergency_fund_context(months_covered: float) -> Optional[dict]:
    """Return benchmark context for emergency fund months covered."""
    if months_covered is None:
        return None

    bench = EMERGENCY_FUND_BENCHMARKS["default"]
    recommended_min = bench["recommended_min"]

    if months_covered < 1.0:
        label = "critical"
        message = (
            f"Your emergency fund covers {months_covered:.1f} months — critical. "
            f"Aim for at least {recommended_min:.0f} months of expenses."
        )
    elif months_covered < recommended_min:
        label = "low"
        message = (
            f"Your emergency fund covers {months_covered:.1f} months — below the recommended "
            f"minimum of {recommended_min:.0f} months."
        )
    elif months_covered < bench["p90"]:
        label = "adequate"
        message = (
            f"Your emergency fund covers {months_covered:.1f} months — adequate. "
            f"The recommended range is 3–6 months."
        )
    else:
        label = "strong"
        message = (
            f"Your emergency fund covers {months_covered:.1f} months — strong. "
            f"You exceed the recommended 6-month target."
        )

    return {
        "metric": "emergency_fund",
        "value": months_covered,
        "label": label,
        "recommended_min": recommended_min,
        "message": message,
        "source": "Financial planning consensus",
    }


def get_dti_context(total_debt: float, annual_gross_income: float) -> Optional[dict]:
    """Return benchmark context for debt-to-income ratio."""
    if total_debt is None or annual_gross_income is None or annual_gross_income == 0:
        return None

    ratio = total_debt / annual_gross_income
    bench = DTI_BENCHMARKS["default"]

    if ratio < bench["low"]:
        label = "healthy"
        note = "Well within mortgage qualification limits."
        message = f"Your DTI ratio is {ratio:.2f} — healthy. {note}"
    elif ratio < bench["moderate"]:
        label = "moderate"
        note = f"Below the {bench['moderate']:.0%} mortgage qualification threshold."
        message = f"Your DTI ratio is {ratio:.2f} — moderate. {note}"
    elif ratio < bench["high"]:
        label = "high"
        note = f"Above the {bench['moderate']:.0%} mortgage qualification threshold — lenders may be cautious."
        message = f"Your DTI ratio is {ratio:.2f} — high. {note}"
    else:
        label = "critical"
        note = "Financial stress territory — prioritise debt reduction."
        message = f"Your DTI ratio is {ratio:.2f} — critical. {note}"

    return {
        "metric": "dti",
        "value": round(ratio, 4),
        "label": label,
        "mortgage_threshold": bench["moderate"],
        "message": message,
        "source": "ECB / mortgage industry standard",
    }


def get_housing_cost_context(monthly_housing: float, monthly_net_income: float) -> Optional[dict]:
    """Return benchmark context for housing cost as % of net income."""
    if monthly_housing is None or monthly_net_income is None or monthly_net_income == 0:
        return None

    ratio = monthly_housing / monthly_net_income
    bench = HOUSING_COST_BENCHMARKS["default"]

    if ratio < bench["comfortable"]:
        label = "comfortable"
        message = (
            f"Your housing costs are {ratio:.0%} of net income — comfortable "
            f"(below the {bench['comfortable']:.0%} guideline)."
        )
    elif ratio < bench["stretched"]:
        label = "stretched"
        message = (
            f"Your housing costs are {ratio:.0%} of net income — stretched "
            f"(between {bench['comfortable']:.0%} and {bench['stretched']:.0%})."
        )
    else:
        label = "stressed"
        message = (
            f"Your housing costs are {ratio:.0%} of net income — stressed "
            f"(above the {bench['stretched']:.0%} Eurostat affordability threshold)."
        )

    return {
        "metric": "housing_cost",
        "value": round(ratio, 4),
        "label": label,
        "message": message,
        "source": "Eurostat housing affordability 2023",
    }


def get_net_worth_context(net_worth: float, age: int, locale: str = "default") -> Optional[dict]:
    """Return percentile context for net worth given age and locale."""
    if net_worth is None or age is None:
        return None

    bracket = _age_bracket(age)
    if bracket is None:
        return {
            "metric": "net_worth",
            "value": net_worth,
            "age_bracket": None,
            "percentile": None,
            "message": "Net worth benchmark not available for this age range (covered: 25–64).",
            "source": "ECB HFCS 2021",
        }

    locale_key = (locale or "").lower()
    locale_data = NET_WORTH_BY_AGE.get(locale_key) or NET_WORTH_BY_AGE.get("de")
    brackets = locale_data[bracket]

    percentile = _net_worth_percentile(net_worth, brackets)
    locale_name = locale_key.upper() if locale_key in NET_WORTH_BY_AGE else "German"

    message = (
        f"Your net worth of €{net_worth:,.0f} puts you in the {percentile} for "
        f"{locale_name} households aged {bracket}. "
        f"Median is €{brackets['p50']:,.0f}."
    )

    return {
        "metric": "net_worth",
        "value": net_worth,
        "age_bracket": bracket,
        "percentile": percentile,
        "median": brackets["p50"],
        "message": message,
        "source": "ECB HFCS 2021",
    }


def get_full_benchmark_report(profile: dict, financials: dict) -> list[dict]:
    """
    Aggregate benchmark context for all applicable metrics.

    profile keys used: personal.date_of_birth, meta.locale, employment.annual_gross
    financials keys used: savings_rate, monthly_expenses, total_debt,
        monthly_housing_cost, monthly_net_income, net_worth, emergency_fund_months
    """
    results = []

    locale = (profile.get("meta") or {}).get("locale", "default")

    # Savings rate
    savings_rate = financials.get("savings_rate")
    if savings_rate is not None:
        ctx = get_savings_rate_context(savings_rate, locale)
        if ctx:
            results.append(ctx)

    # Emergency fund
    emergency_months = financials.get("emergency_fund_months")
    if emergency_months is not None:
        ctx = get_emergency_fund_context(emergency_months)
        if ctx:
            results.append(ctx)

    # DTI
    total_debt = financials.get("total_debt")
    annual_gross = (profile.get("employment") or {}).get("annual_gross")
    if total_debt is not None and annual_gross:
        ctx = get_dti_context(total_debt, annual_gross)
        if ctx:
            results.append(ctx)

    # Housing cost
    monthly_housing = financials.get("monthly_housing_cost")
    monthly_net = financials.get("monthly_net_income")
    if monthly_housing is not None and monthly_net:
        ctx = get_housing_cost_context(monthly_housing, monthly_net)
        if ctx:
            results.append(ctx)

    # Net worth
    net_worth = financials.get("net_worth")
    dob_str = (profile.get("personal") or {}).get("date_of_birth")
    if net_worth is not None and dob_str:
        try:
            dob = date.fromisoformat(dob_str)
            today = date.today()
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            ctx = get_net_worth_context(net_worth, age, locale)
            if ctx:
                results.append(ctx)
        except (ValueError, TypeError):
            pass

    return results
