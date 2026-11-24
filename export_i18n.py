"""导出材料的语言包：档案、蒸馏指令、覆盖报告、下一步、文件名。

目录：content/i18n/export/<lang>/
    prompt.md      蒸馏任务书（正文，不含档案）
    next.md        导出文件夹里的“下一步”
    strings.json   标题、表头、标签、建议模板、文件名
"""
from __future__ import annotations

import json
from pathlib import Path

import bank

ROOT = Path(__file__).resolve().parent
EXPORT_DIR = ROOT / "content" / "i18n" / "export"


def normalize(lang: str | None) -> str:
    return bank.normalize_lang(lang)


def load(lang: str | None = "zh") -> dict:
    code = normalize(lang)
    folder = EXPORT_DIR / code
    if not folder.is_dir():
        code = bank.BASE_LANG
        folder = EXPORT_DIR / code
    strings = json.loads((folder / "strings.json").read_text(encoding="utf-8"))
    prompt = (folder / "prompt.md").read_text(encoding="utf-8")
    next_text = (folder / "next.md").read_text(encoding="utf-8")
    return {
        "lang": code,
        "strings": strings,
        "files": strings.get("files", {}),
        "labels": strings.get("labels", {}),
        "prompt": prompt,
        "next": next_text,
    }
