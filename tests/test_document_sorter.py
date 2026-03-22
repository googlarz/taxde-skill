import pathlib
import sys
import unittest


SCRIPTS_DIR = pathlib.Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from document_sorter import build_new_name  # noqa: E402


class DocumentSorterTest(unittest.TestCase):
    def test_equipment_rename_preserves_image_extension(self):
        name = build_new_name("equipment", "2024", 950.0, "Dell", "receipt.jpg")
        self.assertEqual(name, "2024_Equipment_Dell_950.jpg")

    def test_unknown_rename_preserves_original_extension(self):
        name = build_new_name("unknown", "2024", None, "Unknown", "scan.png")
        self.assertEqual(name, "REVIEW_scan.png")


if __name__ == "__main__":
    unittest.main()

