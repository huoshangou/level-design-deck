# HANDOVER · level-design-deck

> **创建**：2026-04-30
> **最近更新**：2026-05-06（M2 完成）
> **目标读者**：未来的 Steve + 新 session 的 Claude

---

## TL;DR（30 秒看完）

- **项目**：`level-design-deck`，spec 真源 + schema-driven 编辑 + 机械校验工作台
- **状态**：**M0 / M1 / M2 全部 ✅**。lighting_req 单 module 端到端走通：编辑器闭环 + AI 生成 + 单字段重生成
- **下一步**：M3 范围由 Steve 启动时定（候选见末尾）

---

## 当前形态（你能用什么）

```bash
cd ~/Desktop/level-design-deck

# 启编辑器（M1 闭环：看告警 → 改字段 → 保存 → 重渲染）
python3 tools/serve_editor.py --port 8765
# 浏览器 http://127.0.0.1:8765/editor/editor.html

# AI 生成新 spec（M2）
python3 tools/generate_spec.py --module lighting_req --intent "POI: 夜间港口仓库, 紧张潜行" > /tmp/p.md
# 把 /tmp/p.md 内容贴给对话窗口的 Claude → 它产 spec JSON → 用 Write 落 specs/

# AI 单字段重生成（M2）
python3 tools/regenerate_field.py specs/<id>.spec.json map_constraint.description --hint "改成晨雾" > /tmp/r.md
# 把 /tmp/r.md 内容贴给 Claude → 给新值 → 用 Edit 原位覆写

# 机械校验 + 模板 diff（M1，每次改完都跑）
python3 tools/mechanical_check.py specs/<id>.spec.json schema/lighting_req.schema.json
python3 tools/template_diff.py     specs/<id>.spec.json
# 都应输出 0 ERROR / 0 MISSING

# 渲染 HTML
python3 tools/render.py specs/<id>.spec.json templates/lighting_req.html.tmpl outputs/<id>.html
```

**已落盘的 specs**：
- `specs/demo_lighting_req.spec.json` — M1 手填 demo
- `specs/lighting_req_underground_parking_horror.spec.json` — M2 端到端验证产物

---

## 路线图

| MS | 状态 | Deliverable | 验证 |
|---|---|---|---|
| **M0** | ✅ 完成 | PROJECT.md / CLAUDE.md v0.3 / INHERITANCE.md / extractor / template_fields.json + work_docs_extract.json | extractor stats: sections=10 fields=37 radio_groups=9 checkboxes=25 named_tables=6 |
| **M1** | ✅ 完成 | lighting_req 端到端：schema + demo + render + editor + check + diff + serve_editor（8 文件 1124 行） | 后端 curl + 浏览器 8 步闭环都过 |
| **M2** | ✅ 完成 | `generate_spec.py` 184 行 + `regenerate_field.py` 195 行（**只产 prompt 不调 LLM**） | 端到端：产新 spec 0 ERROR / 0 MISSING；单字段重生成 diff 仅 1 行 / 1.7k tokens 远 < 5k |
| **M3** | 🔮 未启动 | 范围待定（候选见下方） | — |

---

## M3 候选范围（启动时由 Steve 选）

按"暴露问题最快"排序：

| 候选 | 选它的理由 | 风险 |
|---|---|---|
| **铺第二个 module**（如 vfx_req / audio_req / spatial_layout） | 暴露 schema-driven 范式在不同字段形态下的问题（数组、嵌套对象）；M2 dot path 在 array 索引就要拓展 | 重复"schema 设计 + demo + render template + diff 映射" 4 件事，工作量 1-2 天 |
| **批量优化美学+交互** | 兑现 M1 后"延后到批量做"的承诺；schema-driven UI 改一次所有 module 受益 | 美学优化的"完成定义"模糊，容易超出 PoC 范围 |
| **给项目加 git** | 当前 spec 改动只能靠人眼 cp+diff，git 后能用 `git diff`；M2 验证流程可去掉 cp 步骤 | 一次性的基础设施动作，5 分钟搞定 |
| **小范围团队试用** | 验证非 Steve 的策划能不能用 schema-driven 工作流 | 还没准备好（无文档、无操作引导）；M3 早 |
| **优化 prompt 模板**（按 token 量化、加 system role） | M2 的 prompt 是 V1，可能过长；regen 1.7k 已 OK 但 generate 4k 可优化 | 优化方向待 M2 实跑出问题反馈再说，现在动是过早优化 |

我（AI）的判断：**git init 先做（5 分钟低成本）→ 然后选铺第二个 module**（暴露 schema 范式问题最有价值）。但 Steve 自己定。

---

## 反污染常驻提醒

⚠️ AI 默认会"回到熟悉状态"。每次涉及 level-design-deck，请记住：

| 陷阱 | 提醒 |
|---|---|
| 顺手读旧 `lighting_req` 实现作参考 | **不要**。schema 设计从 IR + work_docs_extract.json 反推 |
| 觉得"这事得有 manifest / scorer / HITL 三段" | **不要**。这些是过渡期重型机制，本项目不抄 |
| 想用 pipeline 的奶油色出版风、或者 template 的深色 nav 科技感 | **不要**。schema-driven UI 不带视觉规范 |
| 想"先写完整字段集再开始 schema" | **不要**。schema 慢工出细活，每加一个字段都问"AI 真的需要它才能消费吗" |
| 想加打分机制评 spec 质量 | **不要**。新方向是机械检测 + 可执行性，不抄 scorer.js |
| 想抽公共 prompt helper | **不要**。M2 决策：工具自包含、字面常量重复 + 注释同步维护，避免依赖耦合 |

完整反污染规则：[CLAUDE.md](CLAUDE.md) 第 1 / 4 节。

---

## 关键决策的"为什么"（防忘记走回头路）

| 决策 | 为什么 |
|---|---|
| 独立于 `level-skill-pipeline`，新建 `level-design-deck` | pipeline 把 AI 产物当 opaque 整块、改一小段要重生成整模块；新项目从"字段级精度 + spec 真源"重做 |
| 单层 schema-driven UI（不做双层渲染层） | 先验证轻便流程；丑可接受。批量铺 module 时再统一优化 |
| 第一个 module = lighting_req | 字段相对结构化（颜色/强度/角度），适合验证 schema 思路 |
| 承袭项只取 `ir_schema.json` | 其他 pipeline 资产是过渡期债务，不抄 |
| template 借鉴 = 字段清单 diff，不读结构 | template 4000 行有强结构/命名/视觉污染，机械提取后归档 |
| 机械检测 > AI confidence | LLM 自评校准极差；Python 报错才是硬约束 |
| **M2 工具不调 LLM** | 保仓库零外部依赖、防火墙友好；AI 调用集中在对话窗口 |
| **M2 工具单字段原位覆写 + cp/diff 验隔离** | 项目暂未 git init；隔离性人眼看够，PoC 阶段不自动量化 |
| **美学/交互优化延后** | schema-driven 红利：改一次所有 module 受益。批量做避免重复优化 |

完整决策史在 [PROJECT.md](PROJECT.md) 末尾"决策记录"表。

---

## 如果你开新 session（AI 完全没上下文）

复制粘贴这段给 Claude：

> 我继续 `level-design-deck` 项目。请按这个顺序读：
> 1. `~/Desktop/level-design-deck/HANDOVER.md`
> 2. `~/Desktop/level-design-deck/PROJECT.md`
> 3. `~/Desktop/level-design-deck/CLAUDE.md`
> 4. `~/Desktop/level-design-deck/INHERITANCE.md`
>
> 读完告诉我项目当前状态、M3 候选你倾向哪个，然后我们决定下一步。

新 AI 应该能自动续上。**项目根目录的 `CLAUDE.md` 会自动加载**，反污染约束第一时间生效。

---

## Memory 同步

`~/.claude/projects/-Users-mofashu/memory/project_level_design_deck.md` 已同步到 M2 ✅ 状态，新 session 启动时（任何 cwd）会自动加载项目存在的事实。

---

## 时间戳

- HANDOVER 创建：2026-04-30
- 项目根目录：`~/Desktop/level-design-deck/`
- 真源 pipeline 引用（唯一）：`~/Desktop/level-skill-pipeline/src/contracts/ir_schema.json`
- Template 原文件位置（不要读）：`/Users/mofashu/Library/Containers/com.xunmeng.knock/5aK69tk2Dw6H/files/gameplay_template.html`
