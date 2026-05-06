# templates_snapshot/

## ⚠️ AI 不要读这个目录

本目录是 template 原文件的一次性快照，**仅供人类参考与 extractor 脚本消费**。

AI（含未来 session 的 Claude）做任何 spec / schema / editor / 检测器设计时，**不要** Read 本目录任何文件——只读 `../template_fields.json`。

理由：原文件 4000+ 行，含 6.x 章节结构、字段命名风格、视觉规范等强污染源。一旦 AI 读了，会自动复用其结构和命名，前面所有反污染努力作废。详见 `../../INHERITANCE.md` 和 `../../CLAUDE.md`。

## 内容

| 文件 | 来源 | 复制时间 |
|---|---|---|
| `gameplay_template.html` | `/Users/mofashu/Library/Containers/com.xunmeng.knock/5aK69tk2Dw6H/files/gameplay_template.html` | 2026-04-30 |

## 用法

只用一次：跑 `tools/template_field_extractor.py` 提取字段清单到 `../template_fields.json`。之后本目录冷藏。

如果原文件升级、字段有变，需要重新提取：
1. 删除并重新 `cp` 一份到本目录
2. 重跑 extractor
3. 在 PROJECT.md 决策记录追加一行
