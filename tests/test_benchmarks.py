"""Tests for scripts/benchmarks.py — financial metric benchmark context."""

import pytest
from benchmarks import (
    get_savings_rate_context,
    get_emergency_fund_context,
    get_dti_context,
    get_housing_cost_context,
    get_net_worth_context,
    get_full_benchmark_report,
)


# ── Savings rate ──────────────────────────────────────────────────────────────

class TestSavingsRateContext:
    def test_below_p25_is_below_average(self):
        ctx = get_savings_rate_context(0.03, "de")
        assert ctx["label"] == "below average"
        assert ctx["percentile"] == "below average"

    def test_at_p50_is_average(self):
        ctx = get_savings_rate_context(0.11, "de")
        assert ctx["label"] == "average"
        assert ctx["percentile"] == "average"

    def test_between_p50_and_p75_is_above_average(self):
        ctx = get_savings_rate_context(0.18, "de")
        assert ctx["percentile"] == "above average"
        assert ctx["label"] == "good"

    def test_at_p75_is_top25(self):
        ctx = get_savings_rate_context(0.22, "de")
        assert ctx["percentile"] == "top 25%"

    def test_at_p90_is_excellent(self):
        ctx = get_savings_rate_context(0.35, "de")
        assert ctx["label"] == "excellent"
        assert ctx["percentile"] == "top 10%"

    def test_above_p90_is_also_excellent(self):
        ctx = get_savings_rate_context(0.50, "de")
        assert ctx["label"] == "excellent"

    def test_returns_correct_average(self):
        ctx = get_savings_rate_context(0.20, "de")
        assert ctx["average"] == 0.11

    def test_locale_fallback_for_unknown_locale(self):
        ctx = get_savings_rate_context(0.10, "xx")
        assert ctx["source"] == "Eurostat 2023"

    def test_default_locale(self):
        ctx = get_savings_rate_context(0.10)
        assert ctx["source"] == "Eurostat 2023"

    def test_message_included(self):
        ctx = get_savings_rate_context(0.38, "de")
        assert "message" in ctx
        assert len(ctx["message"]) > 10

    def test_none_input_returns_none(self):
        assert get_savings_rate_context(None) is None


# ── Emergency fund ────────────────────────────────────────────────────────────

class TestEmergencyFundContext:
    def test_half_month_is_critical(self):
        ctx = get_emergency_fund_context(0.5)
        assert ctx["label"] == "critical"

    def test_one_month_is_low(self):
        ctx = get_emergency_fund_context(1.5)
        assert ctx["label"] == "low"

    def test_three_months_is_adequate(self):
        ctx = get_emergency_fund_context(3.0)
        assert ctx["label"] == "adequate"

    def test_six_months_is_strong(self):
        ctx = get_emergency_fund_context(6.0)
        assert ctx["label"] == "strong"

    def test_message_included(self):
        ctx = get_emergency_fund_context(2.0)
        assert "message" in ctx

    def test_none_input_returns_none(self):
        assert get_emergency_fund_context(None) is None


# ── DTI ───────────────────────────────────────────────────────────────────────

class TestDtiContext:
    def test_low_dti_is_healthy(self):
        ctx = get_dti_context(10_000, 100_000)   # 0.10
        assert ctx["label"] == "healthy"
        assert abs(ctx["value"] - 0.10) < 0.001

    def test_moderate_dti(self):
        ctx = get_dti_context(20_000, 100_000)   # 0.20
        assert ctx["label"] == "moderate"

    def test_high_dti(self):
        ctx = get_dti_context(40_000, 100_000)   # 0.40
        assert ctx["label"] == "high"

    def test_critical_dti(self):
        ctx = get_dti_context(80_000, 100_000)   # 0.80
        assert ctx["label"] == "critical"

    def test_zero_income_returns_none(self):
        assert get_dti_context(10_000, 0) is None

    def test_none_debt_returns_none(self):
        assert get_dti_context(None, 50_000) is None

    def test_message_included(self):
        ctx = get_dti_context(15_000, 100_000)
        assert "message" in ctx


# ── Housing cost ──────────────────────────────────────────────────────────────

class TestHousingCostContext:
    def test_comfortable(self):
        ctx = get_housing_cost_context(700, 3_000)   # 23%
        assert ctx["label"] == "comfortable"

    def test_stretched(self):
        ctx = get_housing_cost_context(960, 3_000)   # 32%
        assert ctx["label"] == "stretched"

    def test_stressed(self):
        ctx = get_housing_cost_context(1_400, 3_000)  # ~47%
        assert ctx["label"] == "stressed"

    def test_zero_income_returns_none(self):
        assert get_housing_cost_context(1_000, 0) is None

    def test_message_included(self):
        ctx = get_housing_cost_context(700, 3_000)
        assert "message" in ctx


# ── Net worth ─────────────────────────────────────────────────────────────────

class TestNetWorthContext:
    def test_known_bracket_de(self):
        ctx = get_net_worth_context(30_000, 30, "de")
        assert ctx["age_bracket"] == "25-34"
        assert ctx["percentile"] is not None

    def test_above_p75_is_top25(self):
        ctx = get_net_worth_context(100_000, 30, "de")   # p75=72k
        assert ctx["percentile"] == "top 25%"

    def test_below_p25_is_bottom25(self):
        ctx = get_net_worth_context(5_000, 30, "de")     # p25=8k
        assert ctx["percentile"] == "bottom 25%"

    def test_age_outside_range_returns_none_percentile(self):
        ctx = get_net_worth_context(50_000, 22, "de")
        assert ctx["age_bracket"] is None
        assert ctx["percentile"] is None

    def test_locale_fallback_uses_de(self):
        ctx = get_net_worth_context(30_000, 30, "xx")
        assert ctx is not None
        assert ctx["age_bracket"] == "25-34"

    def test_message_included(self):
        ctx = get_net_worth_context(50_000, 40, "de")
        assert "message" in ctx

    def test_none_net_worth_returns_none(self):
        assert get_net_worth_context(None, 35, "de") is None


# ── Full benchmark report ─────────────────────────────────────────────────────

class TestFullBenchmarkReport:
    def _profile(self):
        return {
            "meta": {"locale": "de"},
            "personal": {"date_of_birth": "1990-06-15"},
            "employment": {"annual_gross": 65_000},
        }

    def _financials(self):
        return {
            "savings_rate": 0.20,
            "monthly_expenses": 2_000,
            "total_debt": 15_000,
            "monthly_housing_cost": 1_200,
            "monthly_net_income": 3_500,
            "net_worth": 60_000,
            "emergency_fund_months": 4.0,
        }

    def test_full_data_returns_list_of_dicts(self):
        results = get_full_benchmark_report(self._profile(), self._financials())
        assert isinstance(results, list)
        assert len(results) >= 4

    def test_all_items_have_metric_and_message(self):
        results = get_full_benchmark_report(self._profile(), self._financials())
        for item in results:
            assert "metric" in item
            assert "message" in item

    def test_missing_savings_rate_skipped(self):
        fin = self._financials()
        del fin["savings_rate"]
        results = get_full_benchmark_report(self._profile(), fin)
        metrics = [r["metric"] for r in results]
        assert "savings_rate" not in metrics

    def test_missing_debt_skipped(self):
        fin = self._financials()
        del fin["total_debt"]
        results = get_full_benchmark_report(self._profile(), fin)
        metrics = [r["metric"] for r in results]
        assert "dti" not in metrics

    def test_missing_dob_skips_net_worth(self):
        profile = self._profile()
        del profile["personal"]["date_of_birth"]
        results = get_full_benchmark_report(profile, self._financials())
        metrics = [r["metric"] for r in results]
        assert "net_worth" not in metrics

    def test_empty_financials_returns_empty_list(self):
        results = get_full_benchmark_report(self._profile(), {})
        assert results == []
