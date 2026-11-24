#!/usr/bin/env python3
"""大梦 · 本地问答服务。

只绑定 127.0.0.1，回答写入 data/dream.db，不联网。
    python3 app.py            # 打开 http://127.0.0.1:8765
    python3 app.py --port 9000 --no-open
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import threading
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

import bank
import distill
import store

ROOT = Path(__file__).resolve().parent
WEB = ROOT / "web"
EXPORTS = ROOT / "exports"
MAX_BODY = 2 * 1024 * 1024


class Handler(SimpleHTTPRequestHandler):
    server_version = "DaMeng/1.0"
    db_path: Path | None = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB), **kwargs)

    # ---------- helpers ----------
    def send_json(self, obj, status: int = 200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def read_json(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return {}
        if length > MAX_BODY:
            raise ValueError("内容过大")
        raw = self.rfile.read(length)
        data = json.loads(raw.decode("utf-8"))
        if not isinstance(data, dict):
            raise ValueError("需要 JSON 对象")
        return data

    def answers_dict(self) -> dict[str, str]:
        return {k: v["text"] for k, v in store.all_answers(self.db_path).items()}

    def end_headers(self):
        if self.path.startswith("/api/"):
            self.send_header("Cache-Control", "no-store")
        else:
            self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def log_message(self, fmt, *args):
        if "/api/" in self.path or self.command == "POST":
            super().log_message(fmt, *args)

    # ---------- GET ----------
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        try:
            if path == "/api/health":
                return self.send_json({"ok": True, "version": 1})
            if path == "/api/bank":
                lang = parse_qs(parsed.query).get("lang", ["zh"])[0]
                b = bank.load_bank(lang)
                b["coverage"] = distill.coverage(self.answers_dict())
                return self.send_json(b)
            if path == "/api/answers":
                answers = store.all_answers(self.db_path)
                return self.send_json(
                    {"answers": {k: v["text"] for k, v in answers.items()},
                     "updated_at": {k: v["updated_at"] for k, v in answers.items()},
                     "coverage": distill.coverage({k: v["text"] for k, v in answers.items()})}
                )
            if path == "/api/coverage":
                return self.send_json(distill.coverage(self.answers_dict()))
            if path == "/api/download":
                return self.download(parse_qs(parsed.query).get("path", [""])[0])
            if path == "/favicon.ico":
                self.send_response(204)
                self.end_headers()
                return
            return super().do_GET()
        except BrokenPipeError:
            pass
        except Exception as exc:  # noqa: BLE001
            self.send_json({"error": str(exc)}, 500)

    def download(self, rel: str):
        if not rel:
            return self.send_json({"error": "缺少 path"}, 400)
        target = (ROOT / rel).resolve() if not Path(rel).is_absolute() else Path(rel).resolve()
        allowed = [EXPORTS.resolve(), (ROOT / "examples").resolve()]
        if not any(target == a or a in target.parents for a in allowed) or not target.is_file():
            return self.send_json({"error": "不允许的文件"}, 403)
        ctype = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        data = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header(
            "Content-Disposition",
            f"attachment; filename=download{target.suffix}; filename*=UTF-8''{quote(target.name)}",
        )
        self.end_headers()
        self.wfile.write(data)

    # ---------- POST ----------
    def do_POST(self):
        path = urlparse(self.path).path
        try:
            if path == "/api/answers":
                return self.save_answers()
            if path == "/api/export":
                return self.export()
            return self.send_json({"error": "未知接口"}, 404)
        except json.JSONDecodeError:
            self.send_json({"error": "JSON 解析失败"}, 400)
        except Exception as exc:  # noqa: BLE001
            self.send_json({"error": str(exc)}, 500)

    def save_answers(self):
        data = self.read_json()
        qmap = bank.question_map()
        if "answers" in data:
            items = data["answers"]
            if not isinstance(items, dict):
                return self.send_json({"error": "answers 需要是对象"}, 400)
        elif "id" in data:
            items = {data["id"]: data.get("text", "")}
        else:
            return self.send_json({"error": "缺少 answers 或 id"}, 400)

        clean: dict[str, str] = {}
        for qid, text in items.items():
            if qid not in qmap:
                return self.send_json({"error": f"未知题目 {qid}"}, 400)
            if not isinstance(text, str):
                return self.send_json({"error": f"{qid} 的答案必须是文本"}, 400)
            if len(text) > 20000:
                return self.send_json({"error": f"{qid} 超过 20000 字"}, 400)
            clean[qid] = text

        store.upsert_many(clean, self.db_path)
        answers = self.answers_dict()
        return self.send_json(
            {"ok": True, "saved": len(clean), "coverage": distill.coverage(answers)}
        )

    def export(self):
        data = self.read_json()
        name = (data.get("name") or "我").strip()[:40] or "我"
        lang = bank.normalize_lang(data.get("lang"))
        answers = self.answers_dict()
        if len(answers) == 0:
            return self.send_json({"error": "还没有任何回答"}, 400)
        result = distill.export_all(answers=answers, name=name, lang=lang)
        result["ok"] = True
        return self.send_json(result)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="大梦 · 人生调研")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-open", action="store_true")
    ap.add_argument("--db", help="自定义数据库路径")
    args = ap.parse_args(argv)

    errors = bank.validate()
    if errors:
        print("题库校验失败：")
        print("\n".join(errors))
        return 1

    store.init_db(args.db)
    Handler.db_path = Path(args.db) if args.db else None

    httpd = None
    port = args.port
    for candidate in range(args.port, args.port + 20):
        try:
            httpd = ThreadingHTTPServer(("127.0.0.1", candidate), Handler)
            port = candidate
            break
        except OSError:
            continue
    if httpd is None:
        print(f"端口 {args.port}–{args.port + 19} 都被占用，请用 --port 指定。")
        return 1

    url = f"http://127.0.0.1:{port}"
    answers = {k: v["text"] for k, v in store.all_answers(args.db).items()}
    cov = distill.coverage(answers)
    print(flush=True)
    print("  大梦 · 人生调研")
    print(f"  {url}")
    print(f"  数据  {Path(args.db) if args.db else store.DEFAULT_DB}")
    print(f"  进度  {cov['answered']}/{cov['total']} 题 · 主线 {cov['core_answered']}/{cov['core_total']}")
    print("  Ctrl+C 停止")
    print()

    if not args.no_open:
        threading.Timer(0.7, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止。回答还在 data/dream.db 里。")
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
