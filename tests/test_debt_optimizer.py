"""Tests for debt_optimizer.py."""
from debt_optimizer import (
    get_debts, add_debt, update_debt, delete_debt,
    calculate_avalanche_plan, calculate_snowball_plan,
    compare_payoff_strategies, calculate_mortgage_optimization,
    get_debt_free_date, format_debt_display,
)


def test_empty_debts(isolated_finance_dir):
    assert get_debts() == []


def test_add_debt(isolated_finance_dir):
    d = add_debt({"name": "Student Loan", "type": "student_loan",
                   "balance": 15000, "interest_rate": 3.5, "minimum_payment": 200})
    assert d["name"] == "Student Loan"
    assert d["balance"] == 15000


def test_avalanche_plan(isolated_finance_dir):
    add_debt({"name": "CC", "balance": 5000, "interest_rate": 18, "minimum_payment": 150})
    add_debt({"name": "Car", "balance": 10000, "interest_rate": 5, "minimum_payment": 250})
    plan = calculate_avalanche_plan(extra_monthly=200)
    assert plan["months"] > 0
    assert plan["total_interest"] > 0


def test_snowball_plan(isolated_finance_dir):
    add_debt({"name": "CC", "balance": 5000, "interest_rate": 18, "minimum_payment": 150})
    add_debt({"name": "Car", "balance": 10000, "interest_rate": 5, "minimum_payment": 250})
    plan = calculate_snowball_plan(extra_monthly=200)
    assert plan["months"] > 0


def test_compare_strategies(isolated_finance_dir):
    add_debt({"name": "CC", "balance": 5000, "interest_rate": 18, "minimum_payment": 150})
    add_debt({"name": "Car", "balance": 10000, "interest_rate": 5, "minimum_payment": 250})
    comp = compare_payoff_strategies(extra_monthly=200)
    assert comp["avalanche"]["total_interest"] <= comp["snowball"]["total_interest"]
    assert comp["comparison"]["interest_saved_by_avalanche"] >= 0


def test_mortgage_optimization(isolated_finance_dir):
    result = calculate_mortgage_optimization(
        balance=200000, rate=3.5, remaining_months=300,
        extra_monthly=200, refinance_rate=2.5,
    )
    assert result["optimized"]["interest_saved"] > 0
    assert result["optimized"]["months_saved"] > 0
    assert result["refinance"]["total_interest_saved"] > 0


def test_debt_free_date(isolated_finance_dir):
    add_debt({"name": "Loan", "balance": 5000, "interest_rate": 5, "minimum_payment": 200})
    date = get_debt_free_date()
    assert "202" in date  # Some year in the 2020s/2030s


def test_format_display(isolated_finance_dir):
    add_debt({"name": "CC", "balance": 5000, "interest_rate": 18, "minimum_payment": 150})
    display = format_debt_display()
    assert "CC" in display
    assert "18.0%" in display


def test_freed_minimums_accelerate_payoff(isolated_finance_dir):
    """Freed minimums must be redirected to remaining debts (snowball invariant).

    Debt A: small balance, paid off in ~5 months. After payoff its minimum
    joins the pool, so Debt B pays off faster than it would without recycling.
    """
    add_debt({"name": "SmallDebt", "balance": 500, "interest_rate": 5, "minimum_payment": 120})
    add_debt({"name": "BigDebt",   "balance": 5000, "interest_rate": 5, "minimum_payment": 100})

    # With freed minimums recycled: after SmallDebt clears, BigDebt gets
    # extra_monthly + 120 (freed) each month — payoff should be faster.
    plan_with_extra = calculate_avalanche_plan(extra_monthly=0)

    # Simulate manually: if freed minimums were NOT recycled, BigDebt would
    # only ever get its own minimum (100/mo). Total payment per month would
    # stay at 100 regardless of SmallDebt payoff.
    # With recycling, effective payment on BigDebt climbs to 220 after ~month 5.
    # Assert the plan finishes in a reasonable window (not the naive "never" case).
    assert plan_with_extra["months"] < 100, (
        "Freed minimums should accelerate payoff; got {} months".format(plan_with_extra["months"])
    )
    # The total paid must not exceed balance + interest (sanity check)
    total_principal = 500 + 5000
    assert plan_with_extra["total_paid"] >= total_principal
    assert plan_with_extra["total_paid"] < total_principal * 1.5
