"""Tests for scenario_engine.py."""
from scenario_engine import (
    compare_salary_packages, compare_mortgage_options,
    project_fire_timeline, compare_debt_payoff_vs_invest,
    compare_rent_vs_buy,
)


def test_salary_comparison():
    result = compare_salary_packages([
        {"label": "Current", "annual_gross": 65000},
        {"label": "New Offer", "annual_gross": 75000, "benefits_value": 1200},
    ])
    assert len(result["packages"]) == 2
    assert result["best_option"]["label"] == "New Offer"


def test_mortgage_comparison():
    result = compare_mortgage_options([
        {"label": "Bank A", "loan_amount": 300000, "interest_rate": 3.5, "term_years": 25},
        {"label": "Bank B", "loan_amount": 300000, "interest_rate": 3.0, "term_years": 30},
    ])
    assert len(result["options"]) == 2
    assert result["best_option"] is not None


def test_fire_projection():
    result = project_fire_timeline(
        current_savings=50000, monthly_contribution=1500,
        annual_expenses=30000,
    )
    assert result["fire_number"] == 750000.0
    assert result["years_to_fire"] > 0
    assert result["achievable"] is True
    assert len(result["milestones"]) > 0
    # real_return_used must be present and differ from nominal when inflation > 0
    assert "real_return_used" in result
    assert result["real_return_used"] < result["annual_return_pct"]


def test_fire_unreachable():
    result = project_fire_timeline(
        current_savings=0, monthly_contribution=10,
        annual_expenses=100000,
    )
    assert result["fire_number"] == 2500000.0


def test_fire_inflation_affects_timeline():
    """inflation_rate must affect the projection — real return differs from nominal."""
    base = project_fire_timeline(
        current_savings=50000, monthly_contribution=1500,
        annual_expenses=30000, annual_return_pct=0.07, inflation_rate=0.0,
    )
    inflated = project_fire_timeline(
        current_savings=50000, monthly_contribution=1500,
        annual_expenses=30000, annual_return_pct=0.07, inflation_rate=0.03,
    )
    # With higher inflation, real return is lower → takes longer to reach FIRE
    assert inflated["months_to_fire"] > base["months_to_fire"], (
        "Higher inflation should increase time to FIRE"
    )
    assert inflated["real_return_used"] < base["real_return_used"]


def test_fire_real_equals_nominal_when_real_false():
    """When real=False, nominal return is used unchanged."""
    result = project_fire_timeline(
        current_savings=50000, monthly_contribution=1500,
        annual_expenses=30000, annual_return_pct=0.07, inflation_rate=0.02,
        real=False,
    )
    assert abs(result["real_return_used"] - 0.07) < 1e-9


def test_debt_vs_invest():
    result = compare_debt_payoff_vs_invest(
        debt_balance=10000, debt_rate=5,
        investment_return=8, monthly_available=500,
    )
    assert result["recommendation"] in ("pay_debt_first", "invest")
    assert result["difference"] > 0


def test_rent_vs_buy():
    result = compare_rent_vs_buy(
        monthly_rent=1200, home_price=400000,
        down_payment=80000, mortgage_rate=3.5,
    )
    assert result["recommendation"] in ("buy", "rent")
    assert result["buy"]["monthly_mortgage"] > 0
    assert result["rent"]["total_rent_paid"] > 0
    assert result["years"] == 30
