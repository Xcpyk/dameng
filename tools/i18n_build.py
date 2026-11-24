#!/usr/bin/env python3
"""把 content/i18n/parts/*.json 和 meta/*.json 合并成语言包，并检查覆盖率。

    python3 tools/i18n_build.py            # 合并 + 检查
    python3 tools/i18n_build.py --check    # 只检查已合并的语言包
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import bank  # noqa: E402

I18N = ROOT / "content" / "i18n"
EXPORT_I18N = I18N / "export"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def flat(d: dict, prefix: str = "") -> dict:
    out = {}
    for k, v in d.items():
        if isinstance(v, dict):
            out.update(flat(v, prefix + k + "."))
        else:
            out[prefix + k] = str(v)
    return out


def check_export() -> list[str]:
    """导出模板：键集合、占位符、文件齐全。"""
    errors: list[str] = []
    base = flat(read_json(EXPORT_I18N / "zh" / "strings.json"))
    for lang in [x["code"] for x in bank.available_languages() if x["code"] != bank.BASE_LANG]:
        folder = EXPORT_I18N / lang
        for name in ("prompt.md", "next.md", "strings.json"):
            if not (folder / name).exists():
                errors.append(f"export.{lang}: 缺 {name}")
        if not (folder / "strings.json").exists():
            continue
        target = flat(read_json(folder / "strings.json"))
        if set(target) != set(base):
            errors.append(f"export.{lang}: strings.json 键集合不一致")
        for key in set(target) & set(base):
            a = set(re.findall(r"\{[a-z_]+\}", base[key]))
            b = set(re.findall(r"\{[a-z_]+\}", target[key]))
            if a != b:
                errors.append(f"export.{lang}.{key}: 占位符 {a} != {b}")
        files = read_json(folder / "strings.json").get("files", {})
        for name in ("dossier", "prompt", "coverage", "backup", "next"):
            if not files.get(name):
                errors.append(f"export.{lang}.files: 缺 {name}")
    return errors


def merge_parts(lang: str) -> tuple[dict, list[str]]:
    """合并 <lang>-1.json / <lang>-2.json 的 modules。"""
    modules: dict = {}
    errors: list[str] = []
    found = 0
    for n in (1, 2):
        path = I18N / "parts" / f"{lang}-{n}.json"
        if not path.exists():
            errors.append(f"缺少 {path.relative_to(ROOT)}")
            continue
        found += 1
        data = read_json(path)
        for mid, mod in (data.get("modules") or {}).items():
            if mid in modules:
                errors.append(f"{lang}: 模块 {mid} 重复")
            modules[mid] = mod
    if found == 0:
        errors.append(f"{lang}: 没有任何 part")
    return {"modules": modules}, errors


def build(lang: str) -> tuple[dict, list[str]]:
    errors: list[str] = []
    parts, part_errors = merge_parts(lang)
    errors += part_errors
    meta_path = I18N / "meta" / f"{lang}.json"
    if not meta_path.exists():
        errors.append(f"缺少 {meta_path.relative_to(ROOT)}")
        meta = {}
    else:
        meta = read_json(meta_path)
    scales_path = I18N / "scales.json"
    scales = read_json(scales_path).get(lang, {}) if scales_path.exists() else {}
    languages = bank.available_languages()
    info = next((x for x in languages if x["code"] == lang), {"code": lang, "name": lang})
    pack = {
        "code": lang,
        "name": info.get("name", lang),
        "meta": meta,
        "scales": scales,
        "modules": parts["modules"],
    }
    return pack, errors


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="大梦 · 语言包合并")
    ap.add_argument("--check", action="store_true", help="只检查，不写文件")
    args = ap.parse_args(argv)

    codes = [x["code"] for x in bank.available_languages() if x["code"] != bank.BASE_LANG]
    failed = 0
    for lang in codes:
        pack, errors = build(lang)
        out = I18N / f"{lang}.json"
        if not args.check:
            if errors:
                print(f"{lang}: 未写入（{len(errors)} 个结构问题）")
                for e in errors[:8]:
                    print("  · " + e)
                failed += 1
                continue
            out.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        langs_errors = bank.validate_language(lang)
        total = sum(len(m["questions"]) for m in bank.load_modules())
        done = sum(
            len(m.get("questions", {}))
            for m in pack.get("modules", {}).values()
        )
        print(f"{lang}: {len(pack.get('modules', {}))}/14 模块，{done}/{total} 题", end="")
        if langs_errors:
            failed += 1
            print(f"，{len(langs_errors)} 个问题")
            for e in langs_errors[:10]:
                print("  · " + e)
        else:
            print("，通过" if not errors else "，结构有缺")
    export_errors = check_export()
    print("导出模板：" + ("通过" if not export_errors else f"{len(export_errors)} 个问题"))
    for e in export_errors[:12]:
        print("  · " + e)
    return 1 if (failed or export_errors) else 0


if __name__ == "__main__":
    raise SystemExit(main())
