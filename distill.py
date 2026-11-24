#!/usr/bin/env python3
"""把回答蒸馏成四份材料：人生档案、覆盖报告、蒸馏任务书、下一步。

用法：
    python3 distill.py                     # 用本机 data/dream.db，中文导出
    python3 distill.py --name 我 --lang en # 导出英文模板
    python3 distill.py --sample examples/sample_answers.json --out exports/demo
    python3 distill.py --coverage --lang ja
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

import bank
import export_i18n
import store

ROOT = Path(__file__).resolve().parent
EXPORT_DIR = ROOT / "exports"

PRIVATE_TAGS = {"private", "secret", "shame", "shadow"}


def chars(text: str) -> int:
    return len(re.sub(r"\s", "", text or ""))


def load_sample(path: str | Path) -> tuple[str, dict[str, str]]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, list):
        name, items = "我", data
        answers = {x["qid"]: x["text"] for x in items}
    else:
        name = data.get("name", "我")
        raw = data.get("answers", {})
        if isinstance(raw, list):
            answers = {x["qid"]: x["text"] for x in raw}
        else:
            answers = dict(raw)
    return name, answers


def _modules(lang: str) -> list[dict]:
    return bank.load_modules() if lang == bank.BASE_LANG else bank.load_bank(lang)["modules"]


def coverage(answers: dict[str, str], lang: str = "zh") -> dict:
    lang = export_i18n.normalize(lang)
    modules = []
    for m in _modules(lang):
        qs = m["questions"]
        core = [q for q in qs if q.get("core")]
        answered = [q for q in qs if (answers.get(q["full_id"]) or "").strip()]
        core_answered = [q for q in core if (answers.get(q["full_id"]) or "").strip()]
        modules.append(
            {
                "id": m["id"],
                "title": m["title"],
                "total": len(qs),
                "answered": len(answered),
                "core_total": len(core),
                "core_answered": len(core_answered),
                "chars": sum(chars(answers.get(q["full_id"], "")) for q in answered),
                "private_answered": sum(
                    1 for q in answered if PRIVATE_TAGS & set(q.get("tags", []))
                ),
            }
        )
    total = sum(x["total"] for x in modules)
    answered_n = sum(x["answered"] for x in modules)
    core_total = sum(x["core_total"] for x in modules)
    core_n = sum(x["core_answered"] for x in modules)
    return {
        "modules": modules,
        "total": total,
        "answered": answered_n,
        "core_total": core_total,
        "core_answered": core_n,
        "chars": sum(chars(t) for t in answers.values()),
        "ratio": round(answered_n / total, 3) if total else 0,
        "core_ratio": round(core_n / core_total, 3) if core_total else 0,
    }


def suggestions(cov: dict, answers: dict[str, str], lang: str = "zh") -> list[str]:
    ex = export_i18n.load(lang)
    s = ex["strings"]
    tpl = s["suggestions"]
    out: list[str] = []

    missing_core = cov["core_total"] - cov["core_answered"]
    if missing_core:
        out.append(tpl["missingCore"].format(n=missing_core))

    by_id = {m["id"]: m for m in cov["modules"]}
    m13 = by_id.get("M13")
    if m13 and m13["answered"] < 3:
        out.append(tpl["languageSamples"])

    weak = [m for m in cov["modules"] if m["total"] and m["answered"] / m["total"] < 0.35]
    if weak:
        names = s["listSeparator"].join(f"{m['id']} {m['title']}" for m in weak[:4])
        out.append(tpl["weakChapters"].format(names=names))

    long_core = [
        q
        for q in bank.core_questions()
        if (answers.get(q["full_id"]) or "").strip() and chars(answers[q["full_id"]]) < 40
    ]
    if len(long_core) > 8:
        out.append(tpl["shortAnswers"].format(n=len(long_core)))

    if not any(
        PRIVATE_TAGS & set(q.get("tags", []))
        for q in bank.all_questions()
        if (answers.get(q["full_id"]) or "").strip()
    ):
        out.append(tpl["shadowEmpty"])

    if not out:
        out.append(tpl["allGood"])
    return out


def _quote(text: str) -> str:
    lines = (text or "").strip().splitlines()
    return "\n".join("> " + line if line.strip() else ">" for line in lines)


def dossier(answers: dict[str, str], name: str = "我", lang: str = "zh") -> str:
    lang = export_i18n.normalize(lang)
    ex = export_i18n.load(lang)
    lang = ex["lang"]
    d = ex["strings"]["dossier"]
    cov = coverage(answers, lang)
    modules = _modules(lang)
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines = [
        d["title"].format(name=name),
        "",
        d["meta"].format(
            date=stamp,
            answered=cov["answered"],
            total=cov["total"],
            core_answered=cov["core_answered"],
            core_total=cov["core_total"],
            chars=f"{cov['chars']:,}",
        ),
        ">",
        d["noteEvidence"],
        d["notePrivate"],
        "",
        d["coverage"],
        "",
        f"| {d['tableModule']} | {d['tableAnswered']} | {d['tableCore']} | {d['tableChars']} |",
        "| --- | --- | --- | --- |",
    ]
    for m in cov["modules"]:
        lines.append(
            f"| {m['id']} {m['title']} | {m['answered']}/{m['total']} | "
            f"{m['core_answered']}/{m['core_total']} | {m['chars']:,} |"
        )
    lines += ["", "---", ""]

    for m in modules:
        answered = [q for q in m["questions"] if (answers.get(q["full_id"]) or "").strip()]
        lines += [f"## {m['id']} {m['title']}", "", f"*{m['subtitle']}*", ""]
        if not answered:
            lines += [d["chapterEmpty"], ""]
            continue
        for q in answered:
            text = answers[q["full_id"]].strip()
            tags = []
            if q.get("core"):
                tags.append(d["core"])
            if PRIVATE_TAGS & set(q.get("tags", [])):
                tags.append(d["private"])
            label = d["tagPrefix"] + d["tagSeparator"].join(tags) if tags else ""
            lines += [
                f"### {q['full_id']} {q['title']}{label}",
                "",
                f"**{d['question']}**{d['labelSeparator']}{q['prompt']}",
                "",
                f"**{d['answer']}**{d['labelSeparator']}",
                "",
                _quote(text),
                "",
            ]

    all_q = [q for m in modules for q in m["questions"]]
    gaps = [q for q in all_q if not (answers.get(q["full_id"]) or "").strip()]
    if gaps:
        lines += ["---", "", d["gapsTitle"], ""]
        for m in modules:
            miss = [q for q in gaps if q["module_id"] == m["id"]]
            if miss:
                lines.append(
                    f"- **{m['id']} {m['title']}**{d['labelSeparator']}"
                    + ex["strings"]["listSeparator"].join(
                        f"{q['id']} {q['title']}" for q in miss
                    )
                )
        lines.append("")
        lines += d["gapsNote"].splitlines()
        lines.append("")
    return "\n".join(lines)


def coverage_markdown(answers: dict[str, str], name: str = "我", lang: str = "zh") -> str:
    lang = export_i18n.normalize(lang)
    ex = export_i18n.load(lang)
    lang = ex["lang"]
    c = ex["strings"]["coverage"]
    cov = coverage(answers, lang)
    lines = [
        c["title"].format(name=name),
        "",
        c["overall"].format(
            answered=cov["answered"],
            total=cov["total"],
            pct=round(cov["ratio"] * 100),
        ),
        c["coreLine"].format(
            core_answered=cov["core_answered"],
            core_total=cov["core_total"],
            core_pct=round(cov["core_ratio"] * 100),
        ),
        c["charsLine"].format(chars=f"{cov['chars']:,}"),
        c["privateLine"].format(
            n=sum(m["private_answered"] for m in cov["modules"])
        ),
        "",
        c["byChapter"],
        "",
        f"| {c['tableModule']} | {c['tableAnswered']} | {c['tableCore']} | {c['tableChars']} | {c['tableProgress']} |",
        "| --- | --- | --- | --- | --- |",
    ]
    for m in cov["modules"]:
        pct = round(m["answered"] / m["total"] * 100) if m["total"] else 0
        bar = "█" * (pct // 10) + "░" * (10 - pct // 10)
        lines.append(
            f"| {m['id']} {m['title']} | {m['answered']}/{m['total']} | "
            f"{m['core_answered']}/{m['core_total']} | {m['chars']:,} | {bar} {pct}% |"
        )
    lines += ["", c["nextSteps"], ""]
    for s in suggestions(cov, answers, lang):
        lines.append(f"- {s}")
    lines.append("")
    return "\n".join(lines)


def distill_prompt(answers: dict[str, str], name: str = "我", lang: str = "zh") -> str:
    ex = export_i18n.load(lang)
    return ex["prompt"].rstrip() + "\n\n" + dossier(answers, name, ex["lang"]) + "\n"


def export_all(
    answers: dict[str, str] | None = None,
    name: str = "我",
    out_dir: str | Path | None = None,
    db_path: str | Path | None = None,
    stamp: str | None = None,
    lang: str = "zh",
) -> dict:
    lang = export_i18n.normalize(lang)
    ex = export_i18n.load(lang)
    lang = ex["lang"]
    if answers is None:
        answers = {k: v["text"] for k, v in store.all_answers(db_path).items()}

    safe = re.sub(r"[^\w\u4e00-\u9fff-]+", "_", name).strip("_") or "我"
    stamp = stamp or datetime.now().strftime("%Y-%m-%d_%H%M%S")
    folder = Path(out_dir) if out_dir else EXPORT_DIR / f"{stamp}_{safe}"
    folder.mkdir(parents=True, exist_ok=True)

    kinds = ("dossier", "prompt", "coverage", "backup", "next")
    paths = {k: folder / ex["files"][k] for k in kinds}

    paths["dossier"].write_text(dossier(answers, name, lang), encoding="utf-8")
    paths["prompt"].write_text(distill_prompt(answers, name, lang), encoding="utf-8")
    paths["coverage"].write_text(coverage_markdown(answers, name, lang), encoding="utf-8")
    paths["backup"].write_text(
        json.dumps(
            {
                "name": name,
                "lang": lang,
                "exported_at": datetime.now().isoformat(timespec="seconds"),
                "answers": answers,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    paths["next"].write_text(ex["next"], encoding="utf-8")

    cov = coverage(answers, lang)
    return {
        "dir": str(folder),
        "lang": lang,
        "files": [
            {"label": ex["labels"][k], "path": str(paths[k]), "kind": k}
            for k in kinds
        ],
        "coverage": cov,
        "suggestions": suggestions(cov, answers, lang),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="大梦 · 导出与蒸馏")
    ap.add_argument("--name", default="我", help="档案主人称呼")
    ap.add_argument("--lang", default="zh", help="导出语言：zh / en / ja / ko")
    ap.add_argument("--sample", help="从示例 JSON 读取回答，而不是本机数据库")
    ap.add_argument("--out", help="输出目录（默认 exports/<时间>_<名字>/）")
    ap.add_argument("--coverage", action="store_true", help="只打印覆盖情况")
    args = ap.parse_args(argv)
    lang = export_i18n.normalize(args.lang)

    if args.sample:
        name, answers = load_sample(args.sample)
        name = args.name if args.name != "我" else name
    else:
        store.init_db()
        answers = {k: v["text"] for k, v in store.all_answers().items()}
        name = args.name

    cov = coverage(answers, lang)
    if args.coverage:
        print(coverage_markdown(answers, name, lang))
        return 0

    result = export_all(answers=answers, name=name, out_dir=args.out, lang=lang)
    print(f"已导出到 {result['dir']}（{lang}）")
    print(
        f"进度：{cov['answered']}/{cov['total']}，主线 "
        f"{cov['core_answered']}/{cov['core_total']}，{cov['chars']:,} 字符"
    )
    for s in result["suggestions"]:
        print(" · " + s)
    return 0


if __name__ == "__main__":
    sys.exit(main())
