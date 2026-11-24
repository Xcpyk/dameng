# 示例：沈知微

这是一个**虚构人物**，用来演示从回答到数字人的完整流程。所有细节均为创作，不对应任何真实的人。

## 这个示例有多大

- 69 个回答，主线 64/64，约 4,900 字。
- 这是一份**压缩演示**。真实使用中，69 个回答通常会写到 15,000–30,000 字；这个示例为了可读性做了压缩。
- 即使压缩，也已经能看出「具体场景 + 原话 + 矛盾」对 persona 的作用。

## 按什么顺序读

1. [`沈知微_数字人.md`](沈知微_数字人.md) —— 蒸馏后的 persona。先看这个，感受十层结构。
2. [`沈知微_对话样例.md`](沈知微_对话样例.md) —— 12 段对话，看语气、判断和边界。
3. [`沈知微_导出/人生档案.md`](沈知微_导出/人生档案.md) —— 原始证据。对比 persona，看哪些是原话、哪些是推断。
4. [`沈知微_导出/蒸馏指令.md`](沈知微_导出/蒸馏指令.md) —— 交给模型的任务书全文。
5. [`sample_answers.json`](sample_answers.json) —— 原始回答，可以导入数据库继续改。

## 重新生成

```bash
python3 distill.py --sample examples/sample_answers.json --out examples/沈知微_导出
```

导入本地数据库：

```bash
python3 tools/record.py --db /tmp/demo.db --import-json examples/sample_answers.json
python3 app.py --db /tmp/demo.db
```

## 注意

- persona 是**按流程手工蒸馏**的示例，不是 `distill.py` 自动生成的。`distill.py` 负责证据汇编和任务书；persona 必须由模型按任务书推断，或由你自己写。
- 示例里的私密内容（羞耻、谎言、黑暗念头）只用于演示分层；真实使用时默认不进入对外对话。
