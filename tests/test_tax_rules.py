import pathlib
import sys
import unittest


SCRIPTS_DIR = pathlib.Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from tax_rules import (  # noqa: E402
    calculate_equipment_deduction,
    calculate_income_tax,
    get_tax_year_rules,
    resolve_supported_year,
)


class TaxRulesTest(unittest.TestCase):
    def test_2026_rules_bundle_current_family_values(self):
        rules = get_tax_year_rules(2026)

        self.assertEqual(rules["grundfreibetrag"], 12_348)
        self.assertEqual(rules["kindergeld_per_child"], 259)
        self.assertEqual(rules["kinderfreibetrag_child"], 3_414)
        self.assertAlmostEqual(rules["kinderbetreuung_pct"], 0.80)
        self.assertEqual(rules["kinderbetreuung_max"], 4_800)

    def test_equipment_above_gwg_is_annualized(self):
        self.assertEqual(
            calculate_equipment_deduction(1_299, "Laptop Dell XPS 13", 100, 2024),
            433.0,
        )

    def test_tariff_uses_exact_ground_allowances(self):
        self.assertEqual(calculate_income_tax(11_784, 2024), 0.0)
        self.assertEqual(calculate_income_tax(12_096, 2025), 0.0)
        self.assertEqual(calculate_income_tax(12_348, 2026), 0.0)

    def test_future_year_falls_back_to_latest_bundle(self):
        resolved_year, note = resolve_supported_year(2027)

        self.assertEqual(resolved_year, 2026)
        self.assertIn("2027", note)
        self.assertIn("2026", note)


if __name__ == "__main__":
    unittest.main()

