import pathlib
import sys
import unittest
from datetime import date


SCRIPTS_DIR = pathlib.Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from tax_dates import get_filing_deadline  # noqa: E402


class TaxDatesTest(unittest.TestCase):
    def test_2024_advised_deadline_uses_transition_rule(self):
        self.assertEqual(get_filing_deadline(2024, advised=True), date(2026, 4, 30))

    def test_2025_regular_deadline_is_july_31_following_year(self):
        self.assertEqual(get_filing_deadline(2025, advised=False), date(2026, 7, 31))

    def test_2025_advised_deadline_returns_regular_ao_deadline(self):
        self.assertEqual(get_filing_deadline(2025, advised=True), date(2027, 2, 28))


if __name__ == "__main__":
    unittest.main()

