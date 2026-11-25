from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import distill

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = json.loads((ROOT / "examples" / "sample_answers.json").read_text(encoding="utf-8"))["answers"]


class ExportPrivacyTest(unittest.TestCase):
    def test_coverage_matches_sample(self) -> None:
        cov = distill.coverage(SAMPLE)
        self.assertEqual(cov["total"], 140)
        self.assertEqual(cov["answered"], 69)
        self.assertEqual(cov["core_total"], 64)
        self.assertEqual(cov["core_answered"], 64)

    def test_public_dossier_redacts_private_text(self) -> None:
        secret = SAMPLE["M08.Q04"]
        public = distill.dossier(SAMPLE, "测试", "zh")
        self.assertNotIn(secret, public)
        self.assertIn("（私密层，未导出）", public)
        with_private = distill.dossier(SAMPLE, "测试", "zh", include_private=True)
        self.assertIn(secret, with_private)
        self.assertIn("包含私密层原文", with_private)

    def test_public_prompt_redacts_private_text(self) -> None:
        secret = SAMPLE["M08.Q04"]
        public = distill.distill_prompt(SAMPLE, "测试", "zh")
        self.assertNotIn(secret, public)
        private = distill.distill_prompt(SAMPLE, "测试", "zh", include_private=True)
        self.assertIn(secret, private)

    def test_export_and_backup_privacy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            public = distill.export_all(SAMPLE, name="测试", out_dir=tmp, lang="zh")
            self.assertFalse(public["private_included"])
            public_backup = json.loads(
                (Path(public["dir"]) / "回答备份.json").read_text(encoding="utf-8")
            )
            self.assertFalse(public_backup["private_included"])
            self.assertTrue(public_backup["private_omitted"])
            self.assertLess(len(public_backup["answers"]), len(SAMPLE))
            self.assertNotIn(SAMPLE["M08.Q04"], public_backup["answers"].values())

        with tempfile.TemporaryDirectory() as tmp:
            private = distill.export_all(
                SAMPLE, name="测试", out_dir=tmp, lang="zh", include_private=True
            )
            self.assertTrue(private["private_included"])
            private_backup = json.loads(
                (Path(private["dir"]) / "回答备份.json").read_text(encoding="utf-8")
            )
            self.assertTrue(private_backup["private_included"])
            self.assertEqual(len(private_backup["answers"]), len(SAMPLE))

    def test_english_export_keeps_labels(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = distill.export_all(SAMPLE, name="Test", out_dir=tmp, lang="en")
            names = {Path(f["path"]).name for f in result["files"]}
            self.assertIn("Life-Archive.md", names)
            dossier = (Path(tmp) / "Life-Archive.md").read_text(encoding="utf-8")
            self.assertIn("[Private layer, omitted]", dossier)
            self.assertNotIn(SAMPLE["M08.Q04"], dossier)


if __name__ == "__main__":
    unittest.main()
