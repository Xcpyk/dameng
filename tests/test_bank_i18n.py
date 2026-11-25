from __future__ import annotations

import json
import unittest
from pathlib import Path

import bank
import export_i18n

ROOT = Path(__file__).resolve().parents[1]


class BankTest(unittest.TestCase):
    def test_base_bank_valid(self) -> None:
        self.assertEqual(bank.validate(), [])
        self.assertEqual(len(bank.all_questions()), 140)
        self.assertEqual(len(bank.core_questions()), 64)

    def test_language_packs_valid(self) -> None:
        for entry in bank.available_languages():
            code = entry["code"]
            self.assertEqual(bank.validate_language(code), [], code)

    def test_export_strings_have_privacy_keys(self) -> None:
        for code in ("zh", "en", "ja", "ko"):
            strings = export_i18n.load(code)["strings"]
            self.assertTrue(strings["dossier"]["privateOmitted"])
            self.assertTrue(strings["dossier"]["privateWarning"])

    def test_ui_keys_match(self) -> None:
        data = json.loads((ROOT / "content" / "i18n" / "ui.json").read_text(encoding="utf-8"))
        base = set(data["zh"])
        for code in ("en", "ja", "ko"):
            self.assertEqual(set(data[code]), base, code)


if __name__ == "__main__":
    unittest.main()
