import pathlib
import sys
import unittest
from datetime import date


SCRIPTS_DIR = pathlib.Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from tax_rule_updater import (  # noqa: E402
    clean_source_text,
    collect_snapshot,
    derive_proposed_updates,
    flatten_snapshot_values,
    patch_deduction_rules_text,
    patch_tax_dates_text,
    patch_tax_rules_text,
)


class TaxRuleUpdaterTest(unittest.TestCase):
    def test_collect_snapshot_extracts_official_values_from_fixtures(self):
        fixtures = {
            "https://www.bundesfinanzministerium.de/Monatsberichte/Ausgabe/2025/01/Inhalte/Kapitel-2-Fokus/die-wichtigsten-steuerlichen-aenderungen-2025.html?nn=237786": """
                <p>Mit der Anhebung des in den Einkommensteuertarif integrierten
                Grundfreibetrags um 312 Euro auf 12.096 Euro wird ...</p>
                <p>Zudem wurde das Kindergeld von bisher 250 Euro zum 1. Januar 2025
                um 5 Euro auf 255 Euro sowie zum 1. Januar 2026 um weitere 4 Euro
                auf 259 Euro pro Kind und Monat erhöht.</p>
                <p>... auf insgesamt 4.800 Euro pro Elternteil beziehungsweise
                9.600 Euro pro Kind.</p>
                <p>Als familienpolitische Maßnahme wurde ab dem
                Veranlagungszeitraum 2025 die Begrenzung auf 80 Prozent der
                Aufwendungen und der Höchstbetrag der als Sonderausgaben
                abzugsfähigen Kinderbetreuungskosten auf 4.800 Euro je Kind erhöht.</p>
            """,
            "https://www.bundesfinanzministerium.de/Content/DE/Standardartikel/Themen/Steuern/das-aendert-sich-2026.html": """
                <p>Der steuerliche Grundfreibetrag sorgt dafür, dass das
                Existenzminimum für alle steuerfrei bleibt. 2026 steigt er um
                252 Euro auf 12.348 Euro.</p>
                <p>Das Kindergeld steigt um 4 Euro auf 259 Euro pro Kind und Monat.
                Der Kinderfreibetrag steigt 2026 um 156 Euro auf 9.756 Euro.</p>
            """,
            "https://erbsth.bundesfinanzministerium.de/ao/2024/Anhaenge/BMF-Schreiben-und-gleichlautende-Laendererlasse/Anhang-51/inhalt.html": """
                <p>für den Besteuerungszeitraum 2024: der 30. April 2026</p>
                <p>für den Besteuerungszeitraum 2024: der 30. September 2026</p>
            """,
        }

        def fetcher(url: str) -> str:
            return fixtures[url]

        snapshot, lookup = collect_snapshot(fetcher=fetcher)
        values = flatten_snapshot_values(snapshot)
        proposed, derived_lookup = derive_proposed_updates(values, lookup)

        self.assertEqual(proposed["tax_rules"][2025]["grundfreibetrag"], 12_096)
        self.assertEqual(proposed["tax_rules"][2025]["kindergeld_per_child"], 255)
        self.assertEqual(proposed["tax_rules"][2025]["kinderfreibetrag_child"], 3_336)
        self.assertAlmostEqual(proposed["tax_rules"][2025]["kinderbetreuung_pct"], 0.80)
        self.assertEqual(proposed["tax_rules"][2025]["kinderbetreuung_max"], 4_800)
        self.assertEqual(proposed["tax_rules"][2026]["grundfreibetrag"], 12_348)
        self.assertEqual(proposed["tax_rules"][2026]["kindergeld_per_child"], 259)
        self.assertEqual(proposed["tax_rules"][2026]["kinderfreibetrag_child"], 3_414)
        self.assertEqual(proposed["tax_dates"][False][2024], date(2026, 4, 30))
        self.assertEqual(proposed["tax_dates"][True][2024], date(2026, 9, 30))
        self.assertEqual(
            derived_lookup["tax_rules.2026.kinderfreibetrag_child"]["derived_from"],
            "tax_rules.2026.kinderfreibetrag_total",
        )

    def test_patch_tax_rules_text_updates_selected_values(self):
        original = """
TAX_YEAR_RULES = {
    2026: {
        "grundfreibetrag": 12_000,
        "kindergeld_per_child": 250,
        "kinderfreibetrag_bea": 1_464,
        "kinderfreibetrag_child": 3_300,
        "kinderbetreuung_pct": 0.67,
        "kinderbetreuung_max": 4_000,
        "behindertenpauschbetrag": {
            20: 384,
        },
    },
}
"""
        updated = patch_tax_rules_text(
            original,
            {
                2026: {
                    "grundfreibetrag": 12_348,
                    "kindergeld_per_child": 259,
                    "kinderfreibetrag_child": 3_414,
                    "kinderbetreuung_pct": 0.80,
                    "kinderbetreuung_max": 4_800,
                }
            },
        )

        self.assertIn('"grundfreibetrag": 12_348', updated)
        self.assertIn('"kindergeld_per_child": 259', updated)
        self.assertIn('"kinderfreibetrag_child": 3_414', updated)
        self.assertIn('"kinderbetreuung_pct": 0.80', updated)
        self.assertIn('"kinderbetreuung_max": 4_800', updated)
        self.assertIn("20: 384", updated)

    def test_patch_tax_dates_text_updates_transitional_deadlines(self):
        original = """
ADVISED_DEADLINES = {
    False: {
        2024: date(2026, 1, 1),
    },
    True: {
        2024: date(2026, 2, 2),
    },
}
"""
        updated = patch_tax_dates_text(
            original,
            {
                False: {2024: date(2026, 4, 30)},
                True: {2024: date(2026, 9, 30)},
            },
        )

        self.assertIn("2024: date(2026, 4, 30)", updated)
        self.assertIn("2024: date(2026, 9, 30)", updated)

    def test_patch_deduction_rules_text_updates_table_cells(self):
        original = """| Item | 2023 | 2024 | 2025 | 2026 | Source |
|------|------|------|------|------|--------|
| Grundfreibetrag | €10,908 | €11,784 | €11,999 | €12,000 | source |
| Kindergeld per child | €250/mo | €250/mo | €250/mo | €250/mo | source |
| Kinderfreibetrag (Sachbedarf/Elternteil) | €3,012 | €3,306 | €3,300 | €3,300 | source |
| Kinderbetreuung deductible share | 2/3 | 2/3 | 2/3 | 2/3 | source |
| Kinderbetreuung max per child | €4,000 | €4,000 | €4,000 | €4,000 | source |
"""
        updated = patch_deduction_rules_text(
            original,
            {
                2025: {
                    "grundfreibetrag": 12_096,
                    "kindergeld_per_child": 255,
                    "kinderfreibetrag_child": 3_336,
                    "kinderbetreuung_pct": 0.80,
                    "kinderbetreuung_max": 4_800,
                },
                2026: {
                    "grundfreibetrag": 12_348,
                    "kindergeld_per_child": 259,
                    "kinderfreibetrag_child": 3_414,
                },
            },
        )

        self.assertIn("| Grundfreibetrag | €10,908 | €11,784 | €12,096 | €12,348 |", updated)
        self.assertIn("| Kindergeld per child | €250/mo | €250/mo | €255/mo | €259/mo |", updated)
        self.assertIn(
            "| Kinderfreibetrag (Sachbedarf/Elternteil) | €3,012 | €3,306 | €3,336 | €3,414 |",
            updated,
        )
        self.assertIn("| Kinderbetreuung deductible share | 2/3 | 2/3 | 80% | 2/3 |", updated)
        self.assertIn("| Kinderbetreuung max per child | €4,000 | €4,000 | €4,800 | €4,000 |", updated)

    def test_clean_source_text_strips_html_and_collapses_whitespace(self):
        cleaned = clean_source_text("<p>Hallo&nbsp;&nbsp;<strong>Welt</strong></p>")
        self.assertEqual(cleaned, "Hallo Welt")


if __name__ == "__main__":
    unittest.main()
