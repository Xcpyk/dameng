#!/usr/bin/env python3
"""Regenerate plugin data from the repository's content/ i18n sources.

Run from the repository root:
    python3 plugin/dameng/scripts/build_data.py
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
import bank  # noqa: E402

DATA = Path(__file__).resolve().parents[1] / "data"


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    langs = bank.available_languages()
    out = {"version": 1, "languages": langs, "meta": {}, "modules": {}}
    for entry in langs:
        code = entry["code"]
        b = bank.load_bank(code)
        out["meta"][code] = {
            "title": b["meta"].get("title"),
            "subtitle": b["meta"].get("subtitle"),
            "intro": b["meta"].get("intro"),
            "rules": b["meta"].get("rules", []),
            "ethics": b["meta"].get("ethics", ""),
        }
        out["modules"][code] = [
            {
                "id": m["id"],
                "title": m["title"],
                "subtitle": m["subtitle"],
                "why": m["why"],
                "time": m["time"],
                "questions": [
                    {
                        "full_id": q["full_id"],
                        "id": q["id"],
                        "title": q["title"],
                        "prompt": q["prompt"],
                        "hint": q.get("hint", ""),
                        "probes": q.get("probes", []),
                        "core": bool(q.get("core")),
                        "type": q.get("type", "text"),
                        "left": q.get("left"),
                        "right": q.get("right"),
                        "tags": q.get("tags", []),
                    }
                    for q in m["questions"]
                ],
            }
            for m in b["modules"]
        ]
        dst = DATA / "export" / code
        dst.mkdir(parents=True, exist_ok=True)
        for name in ("prompt.md", "next.md", "strings.json"):
            shutil.copy2(ROOT / "content" / "i18n" / "export" / code / name, dst / name)
    (DATA / "bank.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    shutil.copy2(Path(__file__).resolve().parents[1] / "docs" / "GUIDE.zh.md", DATA / "guide.md")
    print("wrote", DATA / "bank.json")


if __name__ == "__main__":
    main()
