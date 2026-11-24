# 翻译规范

界面支持中文、English、日本語、한국어。中文是源语言，其余为语言包。

## 文件结构

```
content/i18n/
├── languages.json        语言列表（菜单用）
├── ui.json               界面文案（四种语言）
├── meta/
│   ├── en.json           总说明、规则、伦理
│   ├── ja.json
│   └── ko.json
├── parts/                翻译中间件（每个语言两半）
│   ├── en-1.json         M01–M07
│   ├── en-2.json         M08–M14
│   └── ...
├── en.json               合并后的语言包（由 tools/i18n_build.py 生成）
└── export/               导出模板（每个语言一个文件夹）
    ├── zh/
    │   ├── prompt.md     蒸馏任务书正文
    │   ├── next.md       导出文件夹里的“下一步”
    │   └── strings.json  标题、表头、标签、建议模板、文件名
    ├── en/
    ├── ja/
    └── ko/
```

## 语言包结构

```json
{
  "code": "en",
  "name": "English",
  "meta": {
    "title": "Dameng · Life Survey",
    "subtitle": "A life survey, distilled into a digital twin",
    "intro": "……",
    "rules": ["……", "……", "……", "……", "……"],
    "tiers": { "core": "……", "deep": "……", "sample": "……" },
    "ethics": "……"
  },
  "modules": {
    "M01": {
      "title": "Where You Are Now",
      "subtitle": "Put yourself back in this moment",
      "why": "……",
      "time": "About 25 min",
      "questions": {
        "Q01": {
          "title": "Three sentences",
          "prompt": "……",
          "hint": "……",
          "probes": ["……", "……"]
        }
      }
    }
  }
}
```

中间件 `parts/*.json` 只包含 `modules`，合并脚本会把两半和 `meta` 拼起来。

## 导出材料

导出不能只换界面：`人生档案.md`、`蒸馏指令.md`、`覆盖报告.md`、`下一步.md` 和文件名都要用当前语言。

每个语言一个文件夹：

- `prompt.md`：整份蒸馏任务书，结尾必须是 `# Source archive` / `# 元のアーカイブ` / `# 원본 아카이브` 这样的“原始档案”标题；运行时会把档案接在后面。
- `next.md`：导出文件夹里的“下一步”，引用本地化后的文件名。
- `strings.json`：`files`（文件名）、`labels`（展示名）、`dossier`（档案标题/表头/问答标签）、`coverage`（报告标题/表头）、`suggestions`（建议模板）。

硬规则：

1. **占位符原样保留**：`{name} {date} {answered} {total} {core_answered} {core_total} {chars} {pct} {core_pct} {n} {names}`。
2. **JSON 键不改**，只翻译值。
3. **prompt.md 的输出要求要改语言**：中文版是“用 Markdown，中文”，英文版必须要求英文，日文版要求日文，韩文版要求韩文。
4. **文件名要和 `next.md` 一致**，否则导出文件夹里的引用会对不上。
5. 回答原文不翻译；只翻译模板。用户用中文写的答案，在英文档案里仍然是中文原文。

## 翻译原则

1. **保留具体**：这是口述史，不是心理测试。不要把「你妈三天不说话」翻成「家庭沟通存在挑战」。
2. **保留直接**：原文是克制的、口语的、偶尔扎人的。不要加「请」「或许」「温柔地」。
3. **第二人称**：英文用 you；日文尽量省略主语，必要时用「あなた」；韩文用 해요체。
4. **不添加建议**：提示是「怎么写更好」，不是标准答案。
5. **长度随语言**：英文会比中文长，日文/韩文可略长；不要为了对齐硬缩。
6. **文化词**：高考、彩礼、体制内、原生家庭等，用目标语言里最接近的说法，必要时保留一个简短解释，不要音译了事。
7. **同一概念统一**：例如「主线」英文统一 Core，「私密」private，「数字人」digital twin。
8. **不改结构**：id、顺序、probes 数量必须与源文件一致。

## 质量检查

```bash
python3 tools/i18n_build.py --check
```

检查项：

- 14 个模块齐全
- 140 道题齐全
- 每个字段非空
- `probes` 数量与中文源一致
- JSON 可解析
- 导出模板的 `strings.json` 键集合与中文一致、占位符不缺
- `next.md` 里引用的文件名与 `files` 一致

## 新增一种语言

1. 在 `languages.json` 加一项。
2. 复制 `content/modules/*.json`，按上述结构翻译成 `parts/<lang>-1.json`、`<lang>-2.json`。
3. 写 `meta/<lang>.json`，在 `ui.json` 加该语言的界面文案。
4. 复制 `content/i18n/export/zh/` 到 `export/<lang>/`，翻译 `prompt.md`、`next.md`、`strings.json`，并把 `strings.json` 的 `files` 换成该语言的文件名。
5. 运行 `python3 tools/i18n_build.py`。
6. 刷新页面，菜单会自动出现新语言；导出也会自动用新模板。
