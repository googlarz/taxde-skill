import os
import pathlib
import sys
import tempfile
import unittest
from datetime import date


SCRIPTS_DIR = pathlib.Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from adviser_handoff import build_adviser_handoff  # noqa: E402
from bescheid_diff import compare_bescheid  # noqa: E402
from claim_engine import generate_claims  # noqa: E402
from document_coverage import build_document_coverage  # noqa: E402
from filing_pack import build_filing_pack  # noqa: E402
from output_builder import build_output_suite  # noqa: E402
from rule_registry import get_rule_registry  # noqa: E402
from scenario_engine import compare_salary_packages, estimate_freelance_day_rate_to_match_net  # noqa: E402
from tax_timeline import build_tax_timeline  # noqa: E402
from taxde_storage import get_claims_path, get_output_suite_path, get_workspace_path  # noqa: E402
from workspace_builder import build_workspace  # noqa: E402


class V2WorkflowTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.previous_project_dir = os.environ.get("TAXDE_PROJECT_DIR")
        os.environ["TAXDE_PROJECT_DIR"] = self.tempdir.name
        self.addCleanup(self._restore_env)

    def _restore_env(self):
        if self.previous_project_dir is None:
            os.environ.pop("TAXDE_PROJECT_DIR", None)
        else:
            os.environ["TAXDE_PROJECT_DIR"] = self.previous_project_dir

    def _sample_profile(self):
        return {
            "meta": {"tax_year": 2025},
            "personal": {"name": "Alex", "bundesland": "Berlin", "kirchensteuer": False},
            "employment": {"type": "angestellter", "steuerklasse": "I", "annual_gross": 78_000},
            "family": {
                "status": "single",
                "children": [{"birth_year": 2020, "kita": True, "kita_annual_cost": 6_000}],
            },
            "housing": {
                "homeoffice_days_per_week": 3,
                "commute_km": 18,
                "commute_days_per_year": 120,
            },
            "insurance": {
                "krankenkasse_type": "gesetzlich",
                "riester": True,
                "riester_contribution": 1_500,
                "ruerup": False,
                "bav": True,
                "bav_contribution": 2_400,
            },
            "special": {
                "capital_income": True,
                "gewerkschaft_beitrag": 240,
            },
            "current_year_receipts": [
                {
                    "category": "equipment",
                    "amount": 1_299.0,
                    "business_use_pct": 100,
                    "description": "Laptop Dell XPS 13",
                    "deductible_amount": 433.0,
                },
                {
                    "category": "donation",
                    "amount": 150.0,
                    "business_use_pct": 100,
                    "description": "Donation to Red Cross",
                    "deductible_amount": 150.0,
                },
            ],
        }

    def _sample_manifest(self):
        return {
            "classified": [
                {"original": "lohnsteuer.pdf", "category": "income"},
                {"original": "kita.pdf", "category": "childcare"},
                {"original": "equipment.pdf", "category": "equipment"},
                {"original": "depot.pdf", "category": "investment"},
            ],
            "unclassified": [{"original": "mystery.pdf"}],
            "extracted_data": {
                "lohnsteuer.pdf": {"gross": 78_000, "lohnsteuer": 16_000, "primary_amount": 78_000},
                "kita.pdf": {"primary_amount": 6_000},
                "equipment.pdf": {"primary_amount": 1_299},
                "depot.pdf": {"kest_paid": 300, "primary_amount": 300},
            },
        }

    def test_rule_registry_exposes_provenance_and_deadlines(self):
        registry = get_rule_registry(2025)

        self.assertEqual(registry["resolved_year"], 2025)
        self.assertEqual(registry["rules"]["grundfreibetrag"]["value"], 12_096)
        self.assertIn("bundesfinanzministerium.de", registry["rules"]["grundfreibetrag"]["source_url"])
        self.assertEqual(registry["deadlines"]["standard"]["value"], "2026-07-31")

    def test_generate_claims_persists_claim_file(self):
        profile = self._sample_profile()
        payload = generate_claims(profile=profile, persist=True)
        claim_ids = {claim["id"] for claim in payload["claims"]}

        self.assertIn("homeoffice", claim_ids)
        self.assertIn("commute", claim_ids)
        self.assertIn("equipment", claim_ids)
        self.assertIn("childcare", claim_ids)
        self.assertIn("riester", claim_ids)
        self.assertTrue(get_claims_path(2025).exists())

    def test_document_coverage_reflects_manifest_status(self):
        coverage = build_document_coverage(profile=self._sample_profile(), manifest=self._sample_manifest())
        docs = {doc["id"]: doc for doc in coverage["documents"]}

        self.assertEqual(docs["lohnsteuerbescheinigung"]["status"], "present")
        self.assertEqual(docs["childcare_invoice"]["status"], "present")
        self.assertEqual(docs["investment_statement"]["status"], "present")
        self.assertEqual(docs["kv_statement"]["status"], "missing")
        self.assertIn("mystery.pdf", coverage["review_queue"])

    def test_workspace_and_filing_pack_are_persisted_and_structured(self):
        profile = self._sample_profile()
        manifest = self._sample_manifest()
        workspace = build_workspace(profile=profile, manifest=manifest, persist=True)
        filing_pack = build_filing_pack(
            profile=profile,
            claims_payload=generate_claims(profile=profile, persist=False),
            coverage=build_document_coverage(profile=profile, manifest=manifest),
            persist=True,
        )

        form_names = {entry["form"] for entry in filing_pack["forms"]}
        self.assertGreater(workspace["readiness_pct"], 0)
        self.assertTrue(get_workspace_path(2025).exists())
        self.assertIn("Anlage N", form_names)
        self.assertIn("Anlage Kind", form_names)
        self.assertIn("Anlage AV", form_names)
        self.assertGreaterEqual(filing_pack["summary"]["missing_document_count"], 1)

    def test_bescheid_diff_flags_reduced_and_rejected_claims(self):
        profile = self._sample_profile()
        manifest = self._sample_manifest()
        filing_pack = build_filing_pack(
            profile=profile,
            claims_payload=generate_claims(profile=profile, persist=False),
            coverage=build_document_coverage(profile=profile, manifest=manifest),
            persist=False,
        )
        result = compare_bescheid(
            {
                "notice_date": "2026-08-15",
                "assessed_refund": 1_250,
                "accepted_claims": {
                    "homeoffice": 500,
                    "commute": 648,
                    "equipment": 300,
                    "riester": 1_500,
                },
                "rejected_claims": ["donation"],
            },
            filing_pack=filing_pack,
        )

        statuses = {claim["id"]: claim["status"] for claim in result["claims"]}
        self.assertEqual(result["einspruch_deadline"], "2026-09-15")
        self.assertEqual(statuses["homeoffice"], "reduced")
        self.assertEqual(statuses["donation"], "rejected")
        self.assertTrue(result["objection_candidate"])
        self.assertGreaterEqual(len(result["reduced_claims"]), 1)
        self.assertGreaterEqual(len(result["rejected_claims"]), 1)
        self.assertIn("review of the assessment", result["draft_response"])

    def test_scenario_engine_supports_package_comparison_and_break_even(self):
        profile = self._sample_profile()
        comparison = compare_salary_packages(
            [
                {"label": "base", "annual_gross": 78_000, "tax_year": 2025},
                {
                    "label": "benefits",
                    "annual_gross": 76_000,
                    "jobticket_value": 1_200,
                    "bav_contribution": 2_400,
                    "tax_year": 2025,
                },
            ],
            profile=profile,
        )
        break_even = estimate_freelance_day_rate_to_match_net(profile=profile, billable_days=200)

        self.assertEqual(len(comparison["packages"]), 2)
        self.assertEqual(comparison["projection_years"], 3)
        self.assertEqual(len(comparison["packages"][0]["multi_year_projection"]), 3)
        self.assertIn("net_cash_effect", comparison["packages"][1]["delta_vs_baseline"])
        self.assertIn("annual_net", comparison["best_option"])
        self.assertGreater(break_even["recommended_day_rate"], 100)

    def test_timeline_output_suite_and_handoff_are_built(self):
        profile = self._sample_profile()
        manifest = self._sample_manifest()
        workspace = build_workspace(
            profile=profile,
            manifest=manifest,
            today=date(2026, 3, 22),
            persist=True,
        )
        timeline = build_tax_timeline(
            tax_year=2025,
            workspace=workspace,
            profile=profile,
            today=date(2026, 3, 22),
        )
        suite = build_output_suite(
            profile=profile,
            manifest=manifest,
            persist=True,
            today=date(2026, 3, 22),
        )

        self.assertEqual(timeline["phase_id"], "filing_preparation")
        self.assertEqual(suite["timeline"]["phase_id"], "filing_preparation")
        self.assertIn("yearly_tax_summary", suite)
        self.assertTrue(get_output_suite_path(2025).exists())
        self.assertGreater(len(suite["claim_checklist"]), 0)
        self.assertGreater(len(suite["year_end_action_list"]), 0)

    def test_adviser_handoff_flags_specialist_cases(self):
        profile = self._sample_profile()
        profile["special"]["expat"] = True
        profile["special"]["dba_relevant"] = True
        profile["housing"]["rental_property"] = True

        handoff = build_adviser_handoff(profile=profile, coverage=build_document_coverage(profile=profile))
        reason_ids = {reason["id"] for reason in handoff["reasons"]}

        self.assertTrue(handoff["requires_specialist_review"])
        self.assertIn("cross_border", reason_ids)
        self.assertIn("rental_property", reason_ids)
        self.assertGreater(len(handoff["questions_for_adviser"]), 1)


if __name__ == "__main__":
    unittest.main()
