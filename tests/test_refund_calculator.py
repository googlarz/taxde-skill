import pathlib
import sys
import unittest


SCRIPTS_DIR = pathlib.Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from refund_calculator import calculate_refund  # noqa: E402


class RefundCalculatorTest(unittest.TestCase):
    def test_childcare_2025_uses_80_percent_and_4800_cap(self):
        profile = {
            "meta": {"tax_year": 2025},
            "personal": {"bundesland": "Berlin", "kirchensteuer": False},
            "employment": {"type": "angestellter", "steuerklasse": "I", "annual_gross": 65_000},
            "family": {
                "status": "single",
                "children": [{"birth_year": 2020, "kita": True, "kita_annual_cost": 10_000}],
            },
            "housing": {},
            "insurance": {"riester": False, "ruerup": False, "bav": False},
            "special": {},
            "current_year_receipts": [],
        }

        result = calculate_refund(profile)

        self.assertEqual(result["breakdown"]["total_sonderausgaben"], 4_836.0)

    def test_equipment_receipt_uses_annualized_deduction_when_missing_precomputed_amount(self):
        profile = {
            "meta": {"tax_year": 2024},
            "personal": {"bundesland": "Berlin", "kirchensteuer": False},
            "employment": {"type": "angestellter", "steuerklasse": "I", "annual_gross": 65_000},
            "family": {"status": "single", "children": []},
            "housing": {},
            "insurance": {"riester": False, "ruerup": False, "bav": False},
            "special": {},
            "current_year_receipts": [
                {
                    "category": "equipment",
                    "amount": 1_299.0,
                    "business_use_pct": 100,
                    "description": "Laptop Dell XPS 13",
                }
            ],
        }

        result = calculate_refund(profile)

        self.assertEqual(result["breakdown"]["werbungskosten_detail"]["arbeitsmittel"], 433.0)


if __name__ == "__main__":
    unittest.main()

