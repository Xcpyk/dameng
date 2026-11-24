"""题库加载、校验与多语言合并。中文是源语言，其他语言是 content/i18n/<code>.json。"""
from __future__ import annotations

import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONTENT = ROOT / "content"
I18N = CONTENT / "i18n"
BASE_LANG = "zh"


def load_meta() -> dict:
    return json.loads((CONTENT / "bank_meta.json").read_text(encoding="utf-8"))


def load_modules() -> list[dict]:
    modules = []
    for path in sorted((CONTENT / "modules").glob("M*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        questions = []
        for q in data["questions"]:
            q = dict(q)
            q["full_id"] = f"{data['id']}.{q['id']}"
            q["module_id"] = data["id"]
            q["module_title"] = data["title"]
            questions.append(q)
        data = dict(data)
        data["questions"] = questions
        modules.append(data)
    return modules


def available_languages() -> list[dict]:
    path = I18N / "languages.json"
    if not path.exists():
        return [{"code": BASE_LANG, "name": "中文", "english": "Chinese"}]
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_lang(lang: str | None) -> str:
    codes = {x["code"] for x in available_languages()}
    return lang if lang in codes else BASE_LANG


def load_ui(lang: str = BASE_LANG) -> dict:
    path = I18N / "ui.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    base = data.get(BASE_LANG, {})
    if lang == BASE_LANG:
        return dict(base)
    merged = dict(base)
    merged.update(data.get(lang, {}))
    return merged


def load_pack(lang: str) -> dict:
    if lang == BASE_LANG:
        return {}
    path = I18N / f"{lang}.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def apply_pack(modules: list[dict], pack: dict) -> list[dict]:
    """把语言包覆盖到中文题库上；缺失字段回退中文。"""
    mods = copy.deepcopy(modules)
    pack_modules = pack.get("modules", {}) if pack else {}
    scales = pack.get("scales", {}) if pack else {}
    for m in mods:
        t = pack_modules.get(m["id"], {})
        for key in ("title", "subtitle", "why", "time"):
            if t.get(key):
                m[key] = t[key]
        qmap = t.get("questions", {})
        for q in m["questions"]:
            tq = qmap.get(q["id"], {})
            for key in ("title", "prompt", "hint"):
                if tq.get(key):
                    q[key] = tq[key]
            if isinstance(tq.get("probes"), list) and tq["probes"]:
                q["probes"] = list(tq["probes"])
            # 量表两端的标签
            st = scales.get(q["full_id"], {})
            for key in ("left", "right"):
                if st.get(key):
                    q[key] = st[key]
                elif tq.get(key):
                    q[key] = tq[key]
            q["module_title"] = m["title"]
    return mods


def merged_meta(lang: str, pack: dict | None = None) -> dict:
    meta = load_meta()
    pack = load_pack(lang) if pack is None else pack
    pm = pack.get("meta", {}) if pack else {}
    out = dict(meta)
    for key in ("title", "subtitle", "intro", "ethics"):
        if pm.get(key):
            out[key] = pm[key]
    if isinstance(pm.get("rules"), list) and len(pm["rules"]) == len(meta.get("rules", [])):
        out["rules"] = list(pm["rules"])
    if isinstance(pm.get("tiers"), dict):
        out["tiers"] = {**meta.get("tiers", {}), **pm["tiers"]}
    out["lang"] = lang
    return out


def load_bank(lang: str | None = None) -> dict:
    lang = normalize_lang(lang)
    pack = load_pack(lang)
    return {
        "meta": merged_meta(lang, pack),
        "modules": apply_pack(load_modules(), pack),
        "ui": load_ui(lang),
        "languages": available_languages(),
        "lang": lang,
    }


def all_questions() -> list[dict]:
    return [q for m in load_modules() for q in m["questions"]]


def core_questions() -> list[dict]:
    return [q for q in all_questions() if q.get("core")]


def question_map() -> dict[str, dict]:
    return {q["full_id"]: q for q in all_questions()}


def validate() -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    for m in load_modules():
        if not m.get("id") or not m.get("title"):
            errors.append(f"模块缺少 id/title: {m}")
        for q in m["questions"]:
            qid = q["full_id"]
            if qid in seen:
                errors.append(f"重复题目: {qid}")
            seen.add(qid)
            for field in ("title", "prompt", "type"):
                if not q.get(field):
                    errors.append(f"{qid} 缺少 {field}")
            if q["type"] not in {"text", "longtext", "scale", "choice", "multi"}:
                errors.append(f"{qid} 未知类型 {q['type']}")
            if q["type"] == "scale" and not (q.get("left") and q.get("right")):
                errors.append(f"{qid} 量表缺少左右标签")
    return errors


def validate_language(lang: str) -> list[str]:
    """检查一个语言包是否覆盖全部题目。"""
    errors: list[str] = []
    if lang == BASE_LANG:
        return errors
    pack = load_pack(lang)
    if not pack:
        return [f"{lang}: 语言包不存在"]
    base = load_modules()
    meta = pack.get("meta", {})
    base_meta = load_meta()
    for key in ("title", "subtitle", "intro", "ethics"):
        if not meta.get(key):
            errors.append(f"{lang}.meta: 缺 {key}")
    if len(meta.get("rules") or []) != len(base_meta.get("rules") or []):
        errors.append(f"{lang}.meta: rules 数量不一致")
    for key in (base_meta.get("tiers") or {}):
        if not (meta.get("tiers") or {}).get(key):
            errors.append(f"{lang}.meta.tiers: 缺 {key}")
    pm = pack.get("modules", {})
    scales = pack.get("scales", {})
    for m in base:
        tm = pm.get(m["id"])
        if not tm:
            errors.append(f"{lang}.{m['id']}: 缺整个模块")
            continue
        for key in ("title", "subtitle", "why", "time"):
            if not tm.get(key):
                errors.append(f"{lang}.{m['id']}: 缺 {key}")
        for q in m["questions"]:
            tq = tm.get("questions", {}).get(q["id"])
            if not tq:
                errors.append(f"{lang}.{m['id']}.{q['id']}: 缺题目")
                continue
            for key in ("title", "prompt", "hint"):
                if not tq.get(key):
                    errors.append(f"{lang}.{m['full_id']}: 缺 {key}")
            src_probes = q.get("probes") or []
            dst_probes = tq.get("probes") or []
            if len(src_probes) != len(dst_probes):
                errors.append(
                    f"{lang}.{m['full_id']}: probes 数量 {len(dst_probes)} != {len(src_probes)}"
                )
            if q["type"] == "scale":
                st = scales.get(q["full_id"], {})
                if not (st.get("left") and st.get("right")):
                    errors.append(f"{lang}.{m['full_id']}: 量表缺 left/right")
    return errors


if __name__ == "__main__":
    errs = validate()
    qs = all_questions()
    print(f"模块 {len(load_modules())} · 题目 {len(qs)} · 主线 {len(core_questions())}")
    print("语言：" + "、".join(f"{x['code']}({x['name']})" for x in available_languages()))
    if errs:
        print("\n".join(errs))
    else:
        print("中文题库校验通过")
    for lang in [x["code"] for x in available_languages() if x["code"] != BASE_LANG]:
        le = validate_language(lang)
        print(f"{lang}: {'通过' if not le else str(len(le)) + ' 个问题'}")
