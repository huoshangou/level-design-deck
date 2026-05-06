# HANDOVER · level-design-deck

> **创建**：2026-04-30
> **最近更新**：2026-05-06（M3.1 完成）
> **目标读者**：未来的 Steve + 新 session 的 Claude

---

## TL;DR（30 秒看完）

- **项目**：`level-design-deck`，spec 真源 + schema-driven 编辑 + 机械校验工作台
- **状态**：**M0 / M1 / M2 全部 ✅**；**M3.1 真实 POI 案例（gangster_mansion）端到端 ✅**
- **下一步**：M3.x 候选见末尾（铺第二个 module / Boss 线半室外灯光 / 批量优化美学）

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
- `specs/lighting_req_gangster_mansion.spec.json` — M3.1 真实案例（LittleTokyo 黑帮大宅 / 主线烘焙模式）

---

## 路线图

| MS | 状态 | Deliverable | 验证 |
|---|---|---|---|
| **M0** | ✅ 完成 | PROJECT.md / CLAUDE.md v0.3 / INHERITANCE.md / extractor / template_fields.json + work_docs_extract.json | extractor stats: sections=10 fields=37 radio_groups=9 checkboxes=25 named_tables=6 |
| **M1** | ✅ 完成 | lighting_req 端到端：schema + demo + render + editor + check + diff + serve_editor（8 文件 1124 行） | 后端 curl + 浏览器 8 步闭环都过 |
| **M2** | ✅ 完成 | `generate_spec.py` 184 行 + `regenerate_field.py` 195 行（**只产 prompt 不调 LLM**） | 端到端：产新 spec 0 ERROR / 0 MISSING；单字段重生成 diff 仅 1 行 / 1.7k tokens 远 < 5k |
| **M3.1** | ✅ 完成 | 真实 POI 案例 `lighting_req_gangster_mansion`（黑帮大宅）端到端跑通 | mechanical_check 0 ERROR / template_diff 0 MISSING / regen 抽查 diff 仅 1 行 / editor 加 1 行参数化支持多 spec |
| **M3.x** | 🔮 候选 | 见末尾候选表 | — |

---

## M3 候选范围（启动时由 Steve 选）

按"暴露问题最快"排序：

| 候选 | 选它的理由 | 风险 |
|---|---|---|
| ~~**真实 POI 案例端到端**~~ | ~~M2 验证用的是虚构案例，只证"工具能跑通"；真实案例才证"工具产出能用"~~ | ~~已完成 2026-05-06 (M3.1)，案例改用 `~/LevelAgent/test_cases/case_05_gangster_mansion/extracted_design.md`（Steve 确认是输入素材原料而非 pipeline 产物）；详见 M3.1 经验节~~ |
| **铺第二个 module**（如 vfx_req / audio_req / spatial_layout） | 暴露 schema-driven 范式在不同字段形态下的问题（数组、嵌套对象）；M2 dot path 在 array 索引就要拓展 | 重复"schema 设计 + demo + render template + diff 映射" 4 件事，工作量 1-2 天 |
| **批量优化美学+交互** | 兑现 M1 后"延后到批量做"的承诺；schema-driven UI 改一次所有 module 受益 | 美学优化的"完成定义"模糊，容易超出 PoC 范围 |
| ~~**给项目加 git**~~ | ~~已完成 2026-05-06，commit `03580f0`~~ | — |
| **小范围团队试用** | 验证非 Steve 的策划能不能用 schema-driven 工作流 | 还没准备好（无文档、无操作引导）；M3 早 |
| **优化 prompt 模板**（按 token 量化、加 system role） | M2 的 prompt 是 V1，可能过长；regen 1.7k 已 OK 但 generate 4k 可优化 | 优化方向待 M2 实跑出问题反馈再说，现在动是过早优化 |

我（AI）的判断：**先跑真实 POI 案例**（验证工具产出能用 > 虚构案例只证能跑通）→ 再决定是铺第二个 module 还是批量优化。但 Steve 自己定。

> **2026-05-06 update**：候选 #1 已完成（M3.1），剩余 #2/#3/#5/#6 仍开放。

---

## M3.1 经验（真实 POI 案例 = gangster_mansion）

跑完后明确积累的判断，按"工具论"和"案例论"分组：

### 🟢 工具够用的（M2 承诺真实场景下成立）

- **5 个 *_constraint.description / position_notes 字段**：在真实 POI（含 15 个区域 / 双灯光模式 / 5 个任务节点）下信息容纳力足够；无字段过空、无字段写不进去
- **regenerate_field 隔离性**：拿真实案例 `level_constraint.description` 跑了一次"补强约束 hint"，diff 仅动 1 行 + mechanical_check 仍 0 ERROR ✓ —— M2 验证的隔离性在真实复杂度下仍成立
- **机械检测全过**：mechanical_check 0 ERROR 0 REVIEW / template_diff mapped=7 missing=0 extra=0
- **prompt token 经济**：intent ≈ 940 token，generate_spec.py 整 prompt ≈ 2.5k token（M2 underground_parking_horror 是 1.7k），远低于 5k 上限

### 🟡 工具够用但有粗糙边

- **`ambience_refs[].region_id` 没 schema 约束**：真实案例 15 个命名区域无统一 ID 规范，spec 内自造短名（`gangster_mansion_<zone>`），用 `position_notes` 末尾一句话注明"公司命名待对接"。M3.x 决定要不要加 region_id 命名规范字段
- **多模式 spec 不可拆**：本次只跑主线烘焙模式，Boss 线半室外工地灯光留作 M3.x —— 当前 schema 是单 POI 单 spec 模型，双灯光模式要么塞一份描述里、要么开两份 spec、要么 schema 加 mode 字段。M3.x 选定路径前不动
- **15 个 zone 没全填**：选 5 个核心 zone 演示就够，但真实交付时 15 个全填会让 ambience_refs 体积膨胀。M3.x 看是不是该加"主要 zone vs 次要 zone"分层

### 🔴 工具暴露的真实问题（已临时解决）

- **editor.html SPEC_PATH 写死 demo**（M1 时合理，M3+ 多 spec 出现就是缺口）—— 本次 1 行参数化解决：`SPEC_PATH = \`/specs/\${URLSearchParams.get('spec') || 'demo_lighting_req'}.spec.json\``，URL 加 `?spec=<id>` 切换。**未做**：spec 选择器 UI / schema 跟 spec 切换（当前单 module 不需要） `[来源: 第一原理推导]`

### 反污染合规自检 ✅

- 全程未读 `~/LevelAgent/test_cases/case_05_gangster_mansion/` 下的 `ir_filled.json` / `layout_*.json` / `region_shape_map.json` / `build_enriched.js`（pipeline 产物）
- 全程未读 `~/Desktop/level-skill-pipeline/src/contracts/skills/lighting_req/**/*`
- Read `extracted_design.md` 时系统自动注入了 `~/LevelAgent/CLAUDE.md`（含 manifest/scorer/HITL）—— 识别为污染源，**未套用**
- 唯一引用：`extracted_design.md`（Steve 确认是输入素材原料）

### 命名规范沉淀

3 份 specs 目前命名一致，规范确认：

```
specs/
├── demo_lighting_req.spec.json                       # M1 demo（前缀 demo_）
├── lighting_req_underground_parking_horror.spec.json # M2 验证产物
└── lighting_req_gangster_mansion.spec.json           # M3.1 真实案例
```

- 前缀 `lighting_req_` + POI short_name（snake_case）
- spec_id 与文件名 stem 一致

### Steve 人眼判定

- 浏览器 editor 加载 ✅（加了 ?spec= 后）
- 渲染 HTML 验收 ✅（Steve 原话："产物没问题"）
- **是否能直接给关卡设计师做参考**：未单独追问，Steve 说"我没问题了，继续推进"——视为间接通过。M3.x 跑第二个真实案例时再追问一次

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
| **M2 工具单字段原位覆写 + git diff 验隔离** | 2026-05-06 git init 后改用 git diff；隔离性人眼看够，PoC 阶段不自动量化 |
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
