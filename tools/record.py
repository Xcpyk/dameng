#!/usr/bin/env python3
"""访谈记录工具：把对话里的回答写进同一个数据库。

    python3 tools/record.py M03.Q02 "她从来不道歉，只会给我削苹果。"
    python3 tools/record.py M03.Q02 --stdin
    python3 tools/record.py --missing core
    python3 tools/record.py --coverage
    python3 tools/record.py --show M03.Q02
    python3 tools/record.py --import-json examples/sample_answers.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import bank  # noqa: E402
import distill  # noqa: E402
import store  # noqa: E402


def read_text(text: str | None, use_stdin: bool) -> str:
    if text:
        return text
    if use_stdin or not sys.stdin.isatty():
        return sys.stdin.read()
    return ""


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="大梦 · 访谈记录")
    ap.add_argument("qid", nargs="?", help="题目编号，如 M03.Q02")
    ap.add_argument("text", nargs="?", help="回答原文；省略则从标准输入读")
    ap.add_argument("--stdin", action="store_true", help="强制从标准输入读")
    ap.add_argument("--db", help="自定义数据库路径")
    ap.add_argument("--coverage", action="store_true", help="打印覆盖报告")
    ap.add_argument("--missing", choices=["core", "all"], help="列出未答题目")
    ap.add_argument("--show", metavar="QID", help="查看某题当前答案")
    ap.add_argument("--import-json", metavar="PATH", help="批量导入 {name, answers} 或 [{qid,text}]")
    args = ap.parse_args(argv)

    store.init_db(args.db)

    if args.coverage or args.missing:
        answers = {k: v["text"] for k, v in store.all_answers(args.db).items()}
        if args.coverage:
            print(distill.coverage_markdown(answers))
        if args.missing:
            qs = bank.core_questions() if args.missing == "core" else bank.all_questions()
            miss = [q for q in qs if not (answers.get(q["full_id"]) or "").strip()]
            print(f"未答 {len(miss)} 题：")
            for q in miss:
                print(f"  {q['full_id']}  {q['title']}")
        return 0

    if args.show:
        row = store.get_answer(args.show, args.db)
        if not row:
            print(f"{args.show}：未答")
        else:
            print(f"{args.show} · {row['updated_at']}\n")
            print(row["text"])
        return 0

    if args.import_json:
        data = json.loads(Path(args.import_json).read_text(encoding="utf-8"))
        if isinstance(data, list):
            answers = {x["qid"]: x["text"] for x in data}
        else:
            raw = data.get("answers", {})
            answers = {x["qid"]: x["text"] for x in raw} if isinstance(raw, list) else dict(raw)
        qmap = bank.question_map()
        unknown = [q for q in answers if q not in qmap]
        if unknown:
            print("以下题号不存在，已跳过：" + "、".join(unknown))
        clean = {k: v for k, v in answers.items() if k in qmap}
        store.upsert_many(clean, args.db)
        cov = distill.coverage({k: v["text"] for k, v in store.all_answers(args.db).items()})
        print(f"导入 {len(clean)} 题。当前进度：{cov['answered']}/{cov['total']}，主线 {cov['core_answered']}/{cov['core_total']}")
        return 0

    if not args.qid:
        ap.print_help()
        return 1

    qmap = bank.question_map()
    if args.qid not in qmap:
        print(f"没有这道题：{args.qid}")
        print("用 python3 tools/record.py --missing core 查看缺哪些。")
        return 1

    text = read_text(args.text, args.stdin).strip()
    if not text:
        print("没有内容。把回答作为第二个参数传入，或用 --stdin 从标准输入读。")
        return 1

    store.upsert_answer(args.qid, text, args.db)
    q = qmap[args.qid]
    answers = {k: v["text"] for k, v in store.all_answers(args.db).items()}
    cov = distill.coverage(answers)
    print(f"已记录 {args.qid} · {q['title']}（{len(text)} 字符）")
    print(f"进度：{cov['answered']}/{cov['total']}，主线 {cov['core_answered']}/{cov['core_total']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
