# HANDOVER · level-design-deck

> **创建**：2026-04-30
> **最近更新**：2026-05-07（M3.4 完成）
> **目标读者**：未来的 Steve + 新 session 的 Claude

---

## TL;DR（30 秒看完）

- **项目**：`level-design-deck`，spec 真源 + schema-driven 编辑 + 机械校验工作台
- **状态**：**M0 / M1 / M2 全部 ✅**；**M3.1 真实 POI 案例（gangster_mansion）端到端 ✅**；**M3.2 第二个 module（bubble_diagram，图状数据 + Mermaid 渲染）端到端 ✅**；**M3.3 bubble_diagram editor 图状专用视图 ✅**（嵌 Mermaid 实时预览 + 双向高亮 + 4 种图操作 popover）；**M3.4 HUB 结构第二真实关卡案例（gangster_mansion_boss，13 节点 / 14 边）✅**
- **下一步**：M3.x 剩余候选（bubble_diagram schema 补字段 / 第三个 module / 批量优化美学）

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
- `specs/demo_bubble_diagram.spec.json` — M3.2 手填 demo（虚构废弃实验室渗透流程，6 节点 / 7 边 / 覆盖 entry/scene/combat/choice/puzzle/exit + sequential/branch/loop edge）— 留作 generate_spec.py few-shot
- `specs/bubble_diagram_gangster_mansion.spec.json` — M3.2 真实案例（黑帮大宅 Part 1 区域主动线 5 Beat 流程，11 节点 / 10 边）— 素材来源 `cases/case_05_gangster_mansion__extracted_design.md` Page 22-28
- `specs/bubble_diagram_gangster_mansion_boss.spec.json` — M3.4 真实案例（黑帮大宅 Part 2 = 稻泽薰 40 体 boss，HUB 结构 + 3 阶段，13 节点 / 14 边，含 2 条 loop 回流）— 素材来源 `cases/case_05_gangster_mansion__extracted_design.md` Page 29-32

---

## 路线图

| MS | 状态 | Deliverable | 验证 |
|---|---|---|---|
| **M0** | ✅ 完成 | PROJECT.md / CLAUDE.md v0.3 / INHERITANCE.md / extractor / template_fields.json + work_docs_extract.json | extractor stats: sections=10 fields=37 radio_groups=9 checkboxes=25 named_tables=6 |
| **M1** | ✅ 完成 | lighting_req 端到端：schema + demo + render + editor + check + diff + serve_editor（8 文件 1124 行） | 后端 curl + 浏览器 8 步闭环都过 |
| **M2** | ✅ 完成 | `generate_spec.py` 184 行 + `regenerate_field.py` 195 行（**只产 prompt 不调 LLM**） | 端到端：产新 spec 0 ERROR / 0 MISSING；单字段重生成 diff 仅 1 行 / 1.7k tokens 远 < 5k |
| **M3.1** | ✅ 完成 | 真实 POI 案例 `lighting_req_gangster_mansion`（黑帮大宅）端到端跑通 | mechanical_check 0 ERROR / template_diff 0 MISSING / regen 抽查 diff 仅 1 行 / editor 加 1 行参数化支持多 spec |
| **M3.2** | ✅ 完成 | 第二个 module = `bubble_diagram`（节点级 schema + Mermaid 渲染）+ 真实案例端到端 | demo 0/0 ✓；**真实 case `bubble_diagram_gangster_mansion`（11 节点 / 10 边，主动线 5 Beat）0/0 ✓**；template_diff skipped；4 项故意破坏命中预期；regenerate by-id 切对 sub-schema；editor 加 spec 选择器（318 行 < 400 bumped）|
| **M3.3** | ✅ 完成 | bubble_diagram editor 图状专用视图：嵌 Mermaid 实时预览 + 节点 type 上色卡片 + 双向高亮 + 4 种图操作 popover（在此后插入 / 分叉 / 编辑边 / 删除节点 / 添加孤立） | editor.html 318 → 820 行（< 900 bumped，下次再超强制拆 .js）；module 分发让 lighting_req 通用 form 路径完全不变（回归 ✓）|
| **M3.4** | ✅ 完成 | 第二个真实关卡 bubble_diagram 案例（HUB 结构）= `bubble_diagram_gangster_mansion_boss`（13 节点 / 14 边，Phase I/II/III）| mechanical_check 0/0 ✓；template_diff skipped ✓；render Mermaid 出图 ✓；HUB 中央节点（4 出 3 入）+ loop 回流边表达成立。schema 暴露 4 项缺字段（前置依赖合取条件 / 物件依赖 / Phase 归属 / 估时 / TBD 标记）记入候选表。详见 M3.4 经验节 |
| **M3.x** | 🔮 候选 | 见末尾候选表 | — |

---

## M3 候选范围（启动时由 Steve 选）

按"暴露问题最快"排序：

| 候选 | 选它的理由 | 风险 |
|---|---|---|
| ~~**真实 POI 案例端到端**~~ | ~~M2 验证用的是虚构案例，只证"工具能跑通"；真实案例才证"工具产出能用"~~ | ~~已完成 2026-05-06 (M3.1)，案例改用 `~/LevelAgent/test_cases/case_05_gangster_mansion/extracted_design.md`（Steve 确认是输入素材原料而非 pipeline 产物）；详见 M3.1 经验节~~ |
| ~~**铺第二个 module**（如 vfx_req / audio_req / spatial_layout）~~ | ~~暴露 schema-driven 范式在不同字段形态下的问题（数组、嵌套对象）；M2 dot path 在 array 索引就要拓展~~ | ~~已完成 2026-05-06 (M3.2)，选了 bubble_diagram（图状数据，比克隆型暴露问题更多）；详见 M3.2 经验节~~ |
| ~~**真实关卡 bubble_diagram 案例**~~ | ~~验证 schema-driven 对图在真实关卡复杂度下成立；Mermaid 自动布局是否够用要真实节点数才知道~~ | ~~已完成 2026-05-06（M3.2 同日补做），跑了 case_05 黑帮大宅 Part 1 主动线 11 节点 / 10 边~~ |
| ~~**第二个真实关卡 bubble_diagram 案例（HUB 结构）**~~ | ~~case_05 Part 2 = 稻泽薰 40 体 boss = HUB 分支循环结构~~ | ~~已完成 2026-05-07 (M3.4)，详见 M3.4 经验节~~ |
| **第三个 module**（如 vfx_req / spatial_layout / audio_req） | 看是否暴露第三种维度（如 spatial_layout 的几何/坐标） | 重复 M3.2 同款流程，但 vfx_req 等近似克隆，价值递减 |
| **bubble_diagram schema 补字段（前置依赖 / Phase / 估时 / TBD）** | M3.4 暴露 4 项缺字段，逐项决定加哪个：(a) edges[] 的 `requires:[node_id]` 表达合取前置 (b) nodes[] 的 `phase:string` 标 Phase 归属 (c) nodes[] 的 `est_minutes:[min,max]` (d) nodes[] 的 `tbd:bool` + `tbd_reason` | 加一个字段就要改 schema + mechanical_check + render(mermaid 子图分组) + editor 卡片 4 处；范围比想象大，按真实需求驱动单独加 |
| ~~**bubble_diagram editor 图状专用视图**~~ | ~~M3.2 暴露通用 schema-driven form 对图状数据功能性不可用~~ | ~~已完成 2026-05-07 (M3.3)，详见 M3.3 经验节~~ |
| **批量优化美学+交互** | 兑现 M1 后"延后到批量做"的承诺；schema-driven UI 改一次所有 module 受益（注意：bubble_diagram 已走专用视图，批量美学只惠及 lighting_req 类通用 form） | 美学优化的"完成定义"模糊，容易超出 PoC 范围 |
| ~~**给项目加 git**~~ | ~~已完成 2026-05-06，commit `03580f0`~~ | — |
| **小范围团队试用** | 验证非 Steve 的策划能不能用 schema-driven 工作流 | 还没准备好（无文档、无操作引导）；M3 早 |
| **优化 prompt 模板**（按 token 量化、加 system role） | M2 的 prompt 是 V1，可能过长；regen 1.7k 已 OK 但 generate 4k 可优化 | 优化方向待 M2 实跑出问题反馈再说，现在动是过早优化 |

我（AI）的判断：**先跑真实 POI 案例**（验证工具产出能用 > 虚构案例只证能跑通）→ 再决定是铺第二个 module 还是批量优化。但 Steve 自己定。

> **2026-05-06 update**：候选 #1 已完成（M3.1）；候选 #2 已完成（M3.2，选 bubble_diagram）；新增候选"真实关卡 bubble_diagram 案例"和"第三个 module"，批量美学/团队试用/prompt 优化仍开放。
>
> **2026-05-07 update**：bubble_diagram editor 图状专用视图已完成（M3.3）。剩余优先级建议：HUB 案例 > 第三个 module > 批量美学。
>
> **2026-05-07 update 2**：HUB 案例已完成（M3.4，bubble_diagram_gangster_mansion_boss）。剩余优先级建议：bubble_diagram schema 补字段（驱动力强：M3.4 暴露 4 项实际缺字段，1 项已用 notes 文字 fallback）> 第三个 module > 批量美学。

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

## M3.2 经验（第二个 module = bubble_diagram，图状数据）

跑完后明确积累的判断，按"工具论"和"案例论"分组：

### 🟢 schema-driven 范式对图状数据成立

- **节点级粒度选对了**：spec.nodes[]/edges[] 是真源，每节点/边可独立 dot path 寻址；mechanical_check 在图级（id 唯一 / edge 端点存在 / 入口出口 / 孤立节点）有抓手；regenerate_field 重生成单节点 label 不动其他节点
- **mechanical_check 框架可拓展**：原通用 schema validator 不动，加一个 `SEMANTIC_CHECKS` dispatcher 按 module 派发图级断言。176 → 226 行，仍 < 300 OK。范式：schema 表达不了的"非局部"约束放语义层
- **template_diff 优雅 noop**：bubble_diagram 走 skip 分支输出 mapped/missing/extra=0/0/0 + rationale；不强行套字段清单 diff = 反污染胜利。下个非字段类 module 可复用此分支
- **render.py 加 enrich hook 不破坏纯净性**：通用模板引擎 `{{path}}` + `{{#each}}` 不改一行，只在 render() 第一行调用 `spec = enrich_for_render(spec)`。bubble_diagram enricher 把 `__derived__.mermaid_source` 注入 spec，模板用 `{{__derived__.mermaid_source}}` 取
- **dot path by-id + by-index 双支持的兑现**：`nodes[entry].label`（by-id，按 array items.id 字段匹配） + `nodes[0].label`（by-index 兜底）。M2 → M3 留的 TODO 闭环

### 🟡 PoC 接受但未来要看的粗糙边

- **Mermaid 自动布局精度**：demo 6 节点 7 边布局尚可，真实关卡（10+ 节点 / 复杂分支）能否接受未知。M3.x 真实案例 case 跑了再说；如不够用考虑加 `nodes[].rank` 或 layout hint 字段
- **node/edge type 闭合枚举可能撑不住真实需求**：8 种 node type / 5 种 edge type 是第一原理推导的最小集；真实关卡可能要"商店 / 训练场 / 解锁点"等。新需求来了走 schema bump（追加枚举值 + PROJECT.md 决策记录）
- **Mermaid 文本里的特殊字符 escape**：当前 spec_to_mermaid 对 label 里的 `"` 简单 `\\"` escape，Mermaid 真实语法是 `&quot;`；demo label 全中文未触发，遇到带英文引号的 label 要补
- **`exit` 作为 node id**：Mermaid v10 不是保留字，但 `end` 是；后续若用 `end` 作 id 会炸。schema 应加保留字黑名单 pattern？暂未做，未触发再说

### 🔴 工具暴露的真实问题（已解决）

- **serve_editor.py 的 `_run_check` / `_run_render` 写死 demo_lighting_req**（M3.1 已警示，M3.2 顺手修）—— 改造为 spec_id-aware：API 接受 `?spec=<id>` 参数，server 端 `infer_paths(spec_id)` 函数集中维护 spec_id → schema/template 推断。同时新增 `GET /api/specs` + `GET /api/paths` 让 client 不重复推断。`[来源: 第一原理推导]`
- **editor.html 行数约束**：原 < 300 加 spec 选择器后 318 行突破，bump 到 < 400。CLAUDE.md v0.3 → v0.4 + PROJECT.md 决策记录追加。**单文件 self-contained 原则保持**（不拆 .js）

### 反污染合规自检 ✅

- 全程未读 pipeline 的 `/bubble-diagram` 命令实现（Steve 提示已废弃，按 CLAUDE.md 禁读 `contracts/skills/**/*` 自查）
- 全程未读 pipeline 的 ELK 渲染实现（Steve 已踩坑结论，本次走 Mermaid）
- node/edge type 枚举从第一原理 + 通用图论/关卡设计常识推导，不参考 pipeline 字段名
- generate_spec.py 注册新 module 时 `workdoc_key=None` 优雅 fallback 到"schema 即真源"，不强行套 work_docs

### 4 项故意破坏验证（机械检测健壮性）

| # | 破坏 | 期望 | 实际 |
|---|---|---|---|
| 1 | edge.to → 不存在的 ghost_node | ERROR ref_integrity | ✅ 命中 |
| 2 | entry node type 改成 scene（无 entry） | ERROR graph_entry | ✅ 命中 |
| 3 | 第 3 节点 id 改成 entry（重复） | ERROR unique_id | ✅ 命中（附带 ref_integrity 连锁，合理）|
| 4 | 加孤立 orphan_room 节点 | REVIEW isolated | ✅ 命中 |

### 命名规范沉淀

```
specs/demo_bubble_diagram.spec.json — 文件 stem 不与 spec_id 完全一致
                                       内部 spec_id = bubble_diagram_demo_abandoned_lab
```

- 文件名规则：demo 前缀直接放文件名（如 `demo_bubble_diagram.spec.json`）
- spec_id 规则：必须 `<module>_<rest>` 模式（demo 在 rest 内，如 `bubble_diagram_demo_abandoned_lab`）
- 这个文件名 ≠ spec_id 的不一致是 M1 demo_lighting_req 留下的历史规范，M3.2 沿用，未来不必强制对齐

### 真实案例 = bubble_diagram_gangster_mansion（必看）

**源素材**：`cases/case_05_gangster_mansion__extracted_design.md`（已从 `~/LevelAgent/test_cases/case_05_gangster_mansion/extracted_design.md` 复制到项目内防丢失，1572 行 / 38 KB）

**取材范围**：Page 22-28 = Part 1 区域主动线 5 Beat（潜入 → 侦查 → 营救 → 追逃 → 决战 → 撤离）

**未取范围**：Page 29-32 = Part 2 稻泽薰 40 体 boss（HUB 结构 + 3 阶段 + Key 收集），更适合作 M3.x 第二个真实案例（验证 HUB 图状结构）

**spec 落盘 + 验证**：
- `specs/bubble_diagram_gangster_mansion.spec.json` 11 节点 / 10 边
- mechanical_check **0 ERROR / 0 REVIEW** ✓
- template_diff **skipped (graph-type)** ✓
- render `outputs/bubble_diagram_gangster_mansion.html` 9244 chars，Mermaid 出图

**反污染合规**：全程未读 `~/LevelAgent/test_cases/case_05/` 下的 `ir_filled.json`/`layout_*.json`/`build_enriched.js`/`region_shape_map.json`（全部 pipeline 产物）。仅引用 `extracted_design.md`（Steve 确认是输入素材）。

**节点 type 真实使用情况**：entry / choice / scene / combat / cutscene / exit 6 种；puzzle / dialogue 未用（Part 1 不含）；闭合枚举 8 种类型在真实关卡足够。

**反思**：M3.2 一开始我先做了虚构 demo（demo_abandoned_lab）才想起真实案例，被 lighting_req「demo + 真实分两步」模板带偏。修正：M3.x 引入新 module 时直接以真实案例为验收基准，demo 只为 generate_spec.py few-shot 服务（保留但不当主验证）。

### Steve 人眼判定

- Mermaid 图渲染：见 `outputs/bubble_diagram_gangster_mansion.html`（真实案例）和 `outputs/demo_bubble_diagram.html`（虚构 demo）
- editor 切换 spec：spec 选择器 + spec_id-aware API 已工作，curl 后端验证全过
- **2026-05-07 Steve 反馈**：渲染 OK 但 editor 全是问题（图与 form 无关联 / 加分支断裂操作）→ 触发 M3.3。

---

## M3.3 经验（bubble_diagram editor 图状专用视图）

### 触发原因

M3.2 通用 schema-driven form 对图状数据 **功能性不可用**（不是美学问题）：
- nodes/edges 上下两块 `dashed` 框无 type 区分，节点多时按数组顺序找点困难
- Mermaid 渲染图与表单卡片之间无视觉关联，"图上某点对应表单哪段"找不到
- "在某节点后加分支"要分别去 nodes 区 push 节点 + 去 edges 区 push 边，三步割裂

Steve 原话："2026 年简直不敢想象，非常糟糕。"

### 设计取舍

走 A 方案（嵌 Mermaid + 双向高亮 + 图操作按钮），不走 B 方案（拖拽 GUI）。
- A：~370 行新增，PoC 期能用；B：拖拽连线工作量是 A 的 3-5 倍且违反"先验证流程"
- B 推到 M3.4+ 评估，A 跑通后看是否还有刚需

### 落地（编辑器单文件）

editor.html `renderForm()` 加 module 分发：
```js
if (specId.startsWith('bubble_diagram_')) {
  root.innerHTML = renderBubbleDiagramView(SPEC, SCHEMA);
  bindBubbleDiagramHandlers(root);
  refreshMermaid(true);
} else {
  root.innerHTML = renderObject(SPEC, SCHEMA, '');  // 原通用路径完全不变
  bindInputs(root);
}
```

新增能力清单：
1. **顶部 Mermaid 实时预览**（sticky；client-side specToMermaid 重写一份；debounce 200ms 避免每输入字符卡顿；mermaid v10 securityLevel=loose）
2. **双向高亮**：mermaid 节点 click → 滚到 form 卡片 + flash；form 卡片 hover/focus → mermaid 节点 stroke 高亮
3. **节点卡片 type 上色**：8 种 type 各自颜色（entry 绿/exit 灰/combat 红/choice/puzzle 橙/scene 蓝/dialogue 紫/cutscene 粉），左边粗 4px 色边
4. **edges 按节点归属重组**：每节点卡片底部"出边/入边"chip，点 chip 弹编辑 popover；不再底部独立罗列 edges 数组
5. **4 种图操作 popover**：
   - `+ 在此后插入`：1 操作完成 2 spec 修改（push node + push sequential edge）
   - `+ 分叉`：选「+ 新节点」或已有节点 + 选 edge type，新节点路径会同时新建节点
   - `编辑边`：from/to/type 都用下拉只列现有 node id，根上不允许写不存在引用
   - `🗑 删除节点`：confirm 后同时删节点 + 所有相关边
   - `+ 添加孤立节点`（顶层，会触发 REVIEW isolated 提示）
6. **id 字段失焦后全量 renderForm**：因 id 变会让 edges chips 引用失效

### 🟢 范式胜利

- **schema-driven 通用 form 不是万能的**，按 module 分发是承认这个事实的最小代价；通用路径（lighting_req）一行代码不动
- **client-side specToMermaid 双实现**接受同步成本换实时反馈：用户改 label/notes 200ms 看到图刷新，体验上质变
- **图操作语义层 ≠ schema array 操作层**："加分支" 的用户心智是 1 操作，对应 spec 是 2-3 个 array push；popover 是这层翻译的最小载体

### 🟡 PoC 接受但未来要看的粗糙边

- **id 字段编辑体验**：边输入边 mermaid 重渲，但需要失焦才全量刷新卡片间引用。改 id 时短暂状态不一致，能用但不优雅
- **popover 用 confirm() 删除**：M3.3 复用浏览器原生 confirm 简化；体验差但不挡路
- **mermaid 大图布局**：bubble_diagram_gangster_mansion 11 节点尚可，HUB 结构（M3.x 候选）20+ 节点能否接受未知
- **行数 820 接近 < 900 上限**：再加一个图状 module 必拆 .js（已在 PROJECT.md 决策追加约定）
- **specToMermaid 双实现 drift 风险**：python（render.py）和 js（editor.html）两份，新增 type 时两处都改；约定靠注释互引，未来有回归测试再加

### 🔴 工具暴露的真实问题（M3.3 已解决）

- M3.2 暴露的 schema-driven 通用 form 对图状数据无解 —— M3.3 走专用视图解决

### Steve 人眼验收点

启动：
```bash
cd ~/Desktop/level-design-deck
python3 tools/serve_editor.py --port 8765
```
浏览器：`http://127.0.0.1:8765/editor/editor.html?spec=bubble_diagram_gangster_mansion`

验收清单：
1. 顶部 Mermaid 图正常渲染（11 节点 / 10 边），sticky 不被 toolbar 遮
2. 点 mermaid 上 `gate_arrival` → 滚到 form 对应卡片 + 1.5s flash 高亮
3. 节点卡片按 type 颜色区分（entry 绿 / combat 红 / choice 橙 / cutscene 粉等）
4. 卡片 hover → mermaid 对应节点 stroke 高亮（可视联动）
5. 改 label / 改 notes → 200ms 内 mermaid 重渲
6. 点 `+ 在此后插入` → popover → 填 id/type/label → 保存 → 新节点出现 + 自动连边
7. 点 `+ 分叉` → 选「+ 新节点」或已有节点 + 选 edge type → 保存 → 新边出现
8. 点节点卡片底部"出边" chip → 弹 popover 改 from/to/type/label / 删除边
9. 点 `🗑 删除节点` → confirm → 节点 + 相关边都删
10. 切到 `?spec=lighting_req_gangster_mansion` → 通用 form 完全不变（**回归 ✓**）

---

## M3.4 经验（第二个真实关卡 bubble_diagram 案例 = HUB 结构 = boss）

### 触发原因

M3.2 真实案例 `bubble_diagram_gangster_mansion`（Part 1）是线性 5 Beat，schema 表达力没被压到。HUB 结构（多 Key 收集 + 中央分流点 + 知识锁 + 回流循环）是 schema 第二种压力测试，验证 8 种 node type / 5 种 edge type 闭合枚举在非线性流程下是否成立。

### 落盘

**素材来源**：`cases/case_05_gangster_mansion__extracted_design.md` Page 29-32

**spec**：`specs/bubble_diagram_gangster_mansion_boss.spec.json` 13 节点 / 14 边

**拓扑**：
- Phase I (Linear)：side_entrance(entry) → discover_secret(scene)
- Phase II (Hub)：butsudo_first_visit(scene) → **butsudo_hub(choice，4 出 3 入)**
  - 分支 B：→ side_courtyard_path → ayami_room_key02 ==loop=> butsudo_hub
  - 分支 A：→ training_hall_path → closet_dorm_key03 ==loop=> butsudo_hub
- Phase III：butsudo_hub → knowledge_lock(puzzle) → secret_passage → boss_meet(cutscene) → boss_battle(combat) → ending_resolution(exit)

**验证全过**：mechanical_check 0/0 ✓ / template_diff skipped ✓ / render Mermaid 出图 ✓ / 11306 chars HTML

**节点 type 真实使用**：entry / scene / choice / puzzle / cutscene / combat / exit 共 7 种；dialogue 未用。Part 1+Part 2 合计 7/8 type 使用过，schema 第一原理推导的闭合枚举在两个真实案例下成立。

**edge type 真实使用**：sequential / branch / loop 共 3 种；optional / failure 未用。**loop 在 HUB 回流场景首次被真实使用**（Part 1 全 sequential/branch），M3.2 当时担心的"loop 用不上"被推翻。

### 🟢 工具够用的（M3.2 范式在 HUB 下成立）

- **8 种 node type / 5 种 edge type 闭合枚举对 HUB 结构表达足够**：choice 节点天然承担 hub 角色，loop 边天然承担回流角色，无需扩枚举
- **mechanical_check 语义层对 HUB 一次过**：图级断言（id 唯一 / edge 端点存在 / 入口出口 / 孤立节点）对 HUB 结构无误报无漏报；M3.2 写的 4 项断言对非线性图同样工作
- **client-side specToMermaid 对 HUB 节点形状无分歧**：choice→菱形 `{...}` 和 loop→`==>` 加粗箭头，python/js 双实现都对
- **Mermaid TD 默认布局对 13 节点 HUB 结构「够用」**：Steve 2026-05-07 浏览器实测原话「布局还不错，可以接受」→ 即 4 出 3 入中央节点 + 2 条 loop 回流不致纠缠，PoC 期不需要 layout hint；M3.x 候选表对应项可降优先级

### 🟡 PoC 接受但未来要看的粗糙边

- **HUB 结构 Mermaid 自动布局是否清爽**：13 节点（Part 1 是 11）+ 中央节点 4 出 3 入 + 2 条 loop 回流 + 1 条直通 Phase III，TD 布局会不会把 hub 周围挤乱待 Steve 浏览器看；不行就候选「加 layout hint」（如 nodes[].rank 或 nodes[].subgraph_phase）
- **edge label 啰嗦**：本次为兜住"前置合取条件无字段"在 `butsudo_hub → knowledge_lock` 边的 label 里塞了"（合取条件无字段，见 notes）"，10 字以上 label 在 Mermaid 上会撑长边长。schema 加 `requires` 字段后该 label 应缩为 "Key02 + Key03 齐"
- **Phase 归属混在 notes 文字前缀**：node.notes 字段以 "Phase II 起。..." 开头，无结构化 phase 字段，无法做"按 Phase 折叠/分组渲染"。Mermaid subgraph 语法支持分组，但当前 spec 表达不出来
- **Loop 边视觉对回流语义不够强**：Mermaid `==>` 加粗箭头表达"强连接"，但用户心智里 loop 是"返回"。理想做法是 mermaid 的曲线返回箭头，但 Mermaid v10 没原生支持

### 🔴 schema 缺字段（M3.4 暴露 4 项，候选记入路线图候选表）

按"刚需程度"排序：

1. **edges[] 的 `requires:[node_id]` 表达合取前置条件** ⭐ 最刚需
   - 场景：knowledge_lock 入边需要 "Key02 ∧ Key03 已收集" 这种合取
   - 当前 fallback：edge.label 文字描述"Key02 + Key03 齐"
   - 加完后 mechanical_check 可校验"requires 引用的 node id 必须存在且必须是 knowledge_lock 的祖先节点"
   - 风险：合取/析取混合（"Key02 ∧ (Key03 ∨ Key03_alt)"）会让字段结构复杂化，PoC 阶段先只支持合取
2. **nodes[] 的 `phase:string` 标 Phase 归属**
   - 场景：本 spec 13 节点天然分 3 阶段（Phase I/II/III），文档/编辑器若按 phase 分组会大幅提升可读性
   - 当前 fallback：node.notes 文字前缀
   - 加完后 render.py 可生成 Mermaid `subgraph Phase_II` 分组
3. **nodes[] 的 `est_minutes:[min,max]` 估时**
   - 场景：Page 30 给"5-8 mins"估时，Part 1 也有节点估时
   - 当前 fallback：写在 notes 里
   - 优先级低：估时不影响图结构，文档侧加一个 badge 即可
4. **nodes[] 的 `tbd:bool` + `tbd_reason:string`**
   - 场景：Page 31-32 标"此处分镜和参考待世界观补充"
   - 当前 fallback：notes 末尾写 [限制: ...]
   - 优先级低：可视化提示价值有限，更适合 mechanical_check 加 REVIEW

**决策**：M3.x 候选表已加"bubble_diagram schema 补字段"项，按真实需求驱动单独加，不批量推。第 1 项 `requires` 最高优先级。

### 反污染合规自检 ✅

- 全程未读 pipeline 的 `/bubble-diagram` 命令实现 / ELK 渲染实现 / contracts/skills/**
- 全程未读 case_05 下的 ir_filled.json / layout_*.json / build_enriched.js / region_shape_map.json（pipeline 产物）
- 唯一引用：`cases/case_05_gangster_mansion__extracted_design.md` Page 29-32（Steve 确认是输入素材）
- node 拓扑设计 / 阶段切分 / Key 收集回流逻辑均从 case_05 原文 + 第一原理推导，未参考任何 pipeline 字段

### Steve 人眼验收点

启动：
```bash
cd ~/Desktop/level-design-deck
python3 tools/serve_editor.py --port 8765
```

验收清单：
1. 渲染 HTML：`open outputs/bubble_diagram_gangster_mansion_boss.html` → Mermaid TD 图正常出图，13 节点 14 边
2. **关键观察点**：HUB 节点 `butsudo_hub`（菱形 choice）周围布局是否够看（4 出 3 入是否纠缠）
3. **关键观察点**：2 条 loop 回流边（`==>` 加粗箭头从 ayami/closet 回 hub）是否视觉清晰，能否被识别为"返回"
4. editor `?spec=bubble_diagram_gangster_mansion_boss` → 顶部 Mermaid 实时预览 / 双向高亮 / 13 张节点卡片 / type 上色（entry 绿 / choice 橙 / puzzle 橙 / cutscene 粉 / combat 红 / exit 灰 / scene 蓝）
5. 切回 `?spec=bubble_diagram_gangster_mansion`（Part 1，11 节点）→ M3.3 已验回归 ✓ 这次复测一遍
6. 切到 `?spec=lighting_req_gangster_mansion` → 通用 form 路径完全不变（**回归 ✓**）

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
