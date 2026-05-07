# level-design-deck

> 关卡设计的 spec 真源 + schema-driven 编辑 + 机械校验工作台。
> 不是 word，不是 wiki，不是文档生成器。

**版本**：v0.1（2026-04-30 创建）
**所有者**：Steve
**当前阶段**：M0 规划

---

## 一句话定位

把"AI 产文档、人通读改文档"的旧范式，换成"AI 产 spec、Python 标问题、人定向改字段"的新范式。

## 是什么 / 不是什么

| 是 ✅ | 不是 ❌ |
|---|---|
| **spec.json 真源 + 渲染分离**：spec 是 git 管控的数据，HTML 是固定模板的派生 | 富文本编辑器（不允许格式自由） |
| **schema-driven UI**：表单由 JSON Schema 自动生成，加字段先改 schema | hand-coded 表单（每个字段单独写 HTML） |
| **机械检测优先**：Python 跑强/中/弱三档检查，挑出"AI 没把握的"字段 | 通读式人工 review |
| **template diff**：template 字段清单当完备性 checklist，不抄结构 | 1:1 复刻 template 的 4000 行结构 |
| **轻便、单文件、离线、可改**：每个工具都该 < 300 行 | 重型管线（manifest / 状态机 / scorer） |

## 谁用、怎么用

**当前**：Steve 自己（PoC 期）

**典型流程**（5 步）：
1. Steve 跟 Claude 对话敲定设计
2. Claude 产出 spec.json + 渲染成文档 HTML
3. 编辑器打开 → Python 自动跑：
   - 机械检测：占位符 / 类型越界 / 缺字段
   - template diff：vs template 字段清单，标"缺什么 / 多什么"
4. Steve 看告警清单 → 点字段 → 改值 → 保存
5. 重渲染

**未来**（M3+，看 M2 跑通后再说）：小范围团队试用。

## 核心理念（不可妥协的 4 条）

1. **spec.json 是真源、HTML 是派生**——一旦反过来，整个项目失败
2. **schema 改了字段才存在**——AI 不能凭空加字段
3. **机械检测 > AI confidence**——Python 报错是硬约束，AI 自评只配做 hint
4. **template 是 checklist，不是模板**——只用 grep 出的字段清单做 diff，原文件不读

---

## 反污染（关键）

本项目独立于 [`level-skill-pipeline`](../../Desktop/level-skill-pipeline/)。

**承袭清单**（只拿确定有用的）：
- ✅ `ir_schema.json`（IR v3.1）—— 中间表示规范

**反承袭清单**（明确不拿）：
- ❌ pipeline 的 11 模块结构（lighting_req / vfx_req / audio_req 等按职能拆是过渡债务）
- ❌ pipeline 的 manifest / scorer / HITL 三段机制（重型，本项目不需要）
- ❌ pipeline 的 `render_standards.md`（奶油色出版风是给文档的，对 spec 编辑器是噪音）
- ❌ pipeline 的 `changelog.md`（避免被旧决策框死）
- ❌ `gameplay_template.html`（4000 行 hand-coded UI，是要逃离的反例）—— **只通过 `template_field_extractor.py` 提取字段清单后归档，AI 之后不再读原文件**

**思维反污染**：每次 Claude 想说"用 pipeline 的 X 模式"时，Steve 强制反问"这是真的对，还是只是熟悉？"——这是机械办法挡不住的，唯一防线是人。

---

## 架构

```
level-design-deck/
├── PROJECT.md                  # 本文件
├── CLAUDE.md                   # 反污染清单 + 项目约定（M0 产出）
├── schema/
│   └── lighting_req.schema.json     # spec schema（M1）
├── specs/
│   └── demo_lighting_req.spec.json  # 手填 demo（M1）
├── templates/
│   └── lighting_req.html.tmpl       # 固定渲染模板（M1）
├── editor/
│   └── editor.html                  # schema-driven form（M1, < 300 行）
├── tools/
│   ├── template_field_extractor.py  # 一次性提取 template → fields.json（M0）
│   ├── mechanical_check.py          # 强/中/弱三档检测（M1）
│   └── template_diff.py             # spec vs template_fields.json（M1）
├── reference/
│   └── template_fields.json         # template 提取出的字段清单（不再读原文件）
├── cases/                              # 真实案例素材副本（M3.2 起）
│   └── case_05_gangster_mansion__extracted_design.md
└── outputs/
    └── (生成的 HTML 文档放这里)
```

**约束**：
- 每个 Python 工具 < 300 行
- editor.html 单文件 < 900 行（M3.2 从 < 300 bump 到 < 400；M3.3 再 bump 到 < 900 加 bubble_diagram 图状专用视图。下次再超强制拆 `editor/views/<module>.js`）
- 没有 build step（npm/webpack 不要）
- 离线可用（CDN 依赖只允许 jsonschema、Mermaid 一类必须的）

**`cases/` 目录约定（M3.2 起）**：
- 真实案例的"输入素材原料"复制到这里（不是 pipeline 产物，不污染）
- 命名 `<case_id>__<orig_filename>.md`（双下划线分隔 case_id 和原文件名）
- 引入新真实案例时，Claude 应主动复制对应素材到此目录，避免下次找不到

---

## 里程碑

### M0 · 项目骨架（当前）

**目标**：建立反污染防线 + 提取 template 字段清单

**Deliverables**：
- [x] `PROJECT.md`（本文件）
- [x] `CLAUDE.md`（反污染清单 + 项目约定）
- [x] `INHERITANCE.md`（明确从 pipeline 拿什么 / 不拿什么）
- [x] `tools/template_field_extractor.py` + `reference/template_fields.json`
- [x] `reference/templates_snapshot/README.md`（"AI 不读"标记）

**验证**：
- CLAUDE.md 反污染条款读起来明确不容误解
- template 字段清单提取完成，原文件归档（不再读）
- 承袭项 < 5

**决策点**：完成后 HITL —— Steve 审一遍 CLAUDE.md 和承袭清单。

### M1 · lighting_req 端到端 PoC

**目标**：用一个 module 跑通"spec → 编辑 → 检测 → 重渲染"全流程

**Deliverables**：
- [x] `schema/lighting_req.schema.json` —— spec schema（参考 IR + work_docs_extract.json，**未读旧 lighting_req 文件**）
- [x] `specs/demo_lighting_req.spec.json` —— 手填 demo（虚构 POI: demo_warehouse_night）
- [x] `templates/lighting_req.html.tmpl` —— 固定渲染模板（74 行）
- [x] `editor/editor.html` —— schema-driven form（295 行 < 300 ✓）
- [x] `tools/mechanical_check.py` —— 检测器（176 行）
- [x] `tools/template_diff.py` —— diff 工具（167 行）
- [x] `tools/render.py` —— 渲染（95 行，plan 增补）
- [x] `tools/serve_editor.py` —— 本地 server 防 CORS（109 行，plan 增补）

**验证**（2026-05-06 通过）：
- 后端 ✅ curl 全链路 + 干净/污染对照
- 浏览器闭环 ✅ Steve 自跑 8 步无操作硬伤
- **美学/交互优化延后**到所有 module 完成后统一做（schema-driven 红利）

**决策点**：
- M1 验证后决定**编辑器形态够不够用** → 暂判定够用，后续批量优化
- 决定**机械检测项是否齐** → 暂未补，保留观察

### M2 · 接 AI 生成

**目标**：从对话到落地的全链路

**Deliverables**：
- [x] `tools/generate_spec.py`（184 行）— `--module lighting_req --intent "..."` → 自包含 prompt，**只产不调 LLM**
- [x] `tools/regenerate_field.py`（195 行）— `<spec> <field.path> [--hint]` → 自包含 prompt
- [x] Module 注册 dict（M3 拓展点）+ dot path schema 切片 + 错误路径列出该层有效 keys

**验证**（2026-05-06 通过）：
- regen prompt 5.3k 字符 ≈ 1.7k tokens，**远低于 5k 上限** ✓
- 端到端：产 `specs/lighting_req_underground_parking_horror.spec.json` → mechanical_check 0 ERROR / template_diff 0 MISSING
- 单字段改动隔离性：cp before/after diff 仅动 1 行 ✓ / 改后 mechanical_check 仍 0 ERROR ✓

**决策点**：M2 跑通后再决定 M3+ 做什么（扩展模块？双层 UI？小范围团队试用？）— 待 Steve 选定。

---

## 风险

| 风险 | 危险度 | 缓解 |
|---|---|---|
| schema 设计错（基础设施错，全错） | 🔴 高 | M1 慢工出细活；schema 先纸面 review 再落代码 |
| schema-driven UI 太丑团队拒绝 | 🟡 中 | M1/M2 期暂不开放团队；M2 后看接受度再决定双层 UI |
| 反污染失败（聊着回到 pipeline 范式） | 🟡 中 | CLAUDE.md 硬约束 + Steve 主动 review Claude 的提议 |
| 范围蔓延（M1 跑通就想加功能） | 🟡 中 | 每个 MS 之间设 HITL；M3+ 的事现在不讨论 |
| template diff 漏掉真实需求 | 🟢 低 | template 字段清单 ~100 项已覆盖大部分；M1 验证后看缺口 |

---

## 不做什么（明确边界）

- ❌ 不做富文本编辑（保 spec 纯净）
- ❌ 不做 UI 美化（先验证流程通不通）
- ❌ 不做团队权限 / 多人协作（PoC 期单人）
- ❌ 不做版本管理（用 git 就行）
- ❌ 不做 manifest / 状态机（违背"轻便"）
- ❌ 不做 scorer.js 那种 14 项打分（过渡期重型机制不抄）
- ❌ 不做插件系统 / 主题切换（M3+ 再说，且很可能永远不做）

---

## 决策记录

| 日期 | 决策 | 理由 |
|---|---|---|
| 2026-04-30 | 项目命名 `level-design-deck` | "deck" 暗示工作台；与 pipeline deck view 形成对话感 |
| 2026-04-30 | 单层 schema-driven UI（不做双层） | 先验证轻便流程；丑可接受 |
| 2026-04-30 | 第一个 module = `lighting_req` | 字段相对结构化（颜色/强度/角度）适合验证 schema |
| 2026-04-30 | 承袭项只取 `ir_schema.json` | 其他 pipeline 资产是过渡债务，不抄 |
| 2026-04-30 | template 借鉴 = 字段清单 diff，不读结构 | 用 `template_field_extractor.py` 机械阻断 |
| 2026-04-30 | M0 完成 | 4 deliverables 落地，extractor 跑通：sections=10 / fields=37 / radio_groups=9 / checkboxes=25 / named_tables=6（5 个匿名 tbody 无 id 抓不到，符合预期） |
| 2026-04-30 | `承袭清单.md` 改名 `INHERITANCE.md` | 中文文件名在某些 IDE 链接打不开（编码问题）；正文中"承袭清单"作为名词保留 |
| 2026-04-30 | 新增 2 项未决（HANDOVER 已记） | Steve 反馈：玩法/POI 应双模板分离；反污染需更强机制（候选 a/b/c）。长假后决策 |
| 2026-05-06 | 长假结束，重启项目 | 机械验证通过：4 文档 + extractor stats 不变 |
| 2026-05-06 | 反污染 #3 决：选 a · 决策来源标签 | CLAUDE.md bump v0.1→v0.2，加第 4.B 节"输出契约"。AI 提架构建议必须标 `[来源: ...]`，5 种允许 / 禁用 pipeline 经验类标签 |
| 2026-05-06 | lighting 是 POI-only | Steve 直接告知；玩法文档不涉及灯光需求。M1 lighting spec 顶层定位为 POI-only module |
| 2026-05-06 | spawn subagent 提取 `~/Downloads/work/` POI/玩法 公司文档 | 产出 `reference/work_docs_extract.json`：34 POI 字段 + 7 lighting 字段 + 27 玩法字段；交叉验证玩法不含 lighting 结构化字段 |
| 2026-05-06 | CLAUDE.md bump v0.2→v0.3 | 4.B 来源枚举从 5 种扩到 7 种，新增 `work_docs_extract.json` 和 `Steve 直接指示（含日期）`。规则迭代触发条件：机制 self-test 立刻发现 gap |
| 2026-05-06 | M1 后端实现完成 | 8 个 deliverable 全部落地（plan 6 个 + 增补 render.py / serve_editor.py），新增代码 1124 行，无外部依赖；后端 curl 全链路验证通过 |
| 2026-05-06 | M1 plan 增补 `render.py` + `serve_editor.py` | render 把 spec 套模板出 HTML（plan 隐含但漏列）；serve_editor 防 file:// CORS + 提供 PUT/POST 让闭环真闭。`[来源: 第一原理推导]` |
| 2026-05-06 | M1 浏览器闭环验证通过 | Steve 自跑 8 步闭环，无操作硬伤；美学/交互优化延后到所有 module 完成后统一做（schema-driven 红利） |
| 2026-05-06 | M2 ✅ 完成 | `tools/generate_spec.py` 184 行 + `tools/regenerate_field.py` 195 行，**只产 prompt 不调 LLM**（标准库 only）。端到端跑通：产 `lighting_req_underground_parking_horror` spec → 0 ERROR / 0 MISSING；改 `map_constraint.description` → diff 仅动 1 行 / 仍 0 ERROR；regen prompt ≈ 1.7k tokens 远低于 5k 上限 |
| 2026-05-06 | M2 关键架构决策 · Module 注册 dict | `MODULES` 字典留 M3 拓展点（加 module = 加一行 dict）。M2 仅注册 lighting_req。`[来源: 第一原理推导]` |
| 2026-05-06 | M2 关键架构决策 · 不抽 prompt helper | 占位符/caveat 字面量在两个工具内重复 + 注释`[来源: tools/mechanical_check.py 同步维护]`。理由：避免依赖耦合，工具仍 < 200 行。`[来源: 第一原理推导]` |
| 2026-05-06 | M2 关键架构决策 · dot path 不支持 array 索引 | 遇 array 报错 + 提示"M2 不支持"。理由：M2 lighting_req 字段最深 3 层都是 object，array 拓展（如 `ambience_refs[0].region_id`）推到 M3。`[来源: 第一原理推导]` |
| 2026-05-06 | git init + 首次 commit `03580f0` | 22 文件 6486 行；分支 `main`；`.gitignore` 排除 outputs/*.html / .warnings.json / .diff.json / __pycache__ / .DS_Store。template snapshot **进 git**（INHERITANCE.md "物理隔断"那一半的物理依据）。M2 决策"cp/diff 验隔离"现在可改用 `git diff` |
| 2026-05-06 | M3.1 真实 POI 案例（gangster_mansion）端到端通过 | spec `lighting_req_gangster_mansion.spec.json` 落盘 → mechanical_check 0 ERROR / template_diff 0 MISSING / render HTML / regen 抽查 `level_constraint.description` diff 仅动 1 行 + 仍 0 ERROR。intent 940 token / generate_prompt 2.5k token，远低于 5k 上限。**暴露问题 1 项**：editor.html 的 SPEC_PATH 写死，本次加 1 行参数化（`?spec=` URL query）解决。详见 HANDOVER.md M3.1 经验节。`[来源: 第一原理推导 + extracted_design.md 案例素材]` |
| 2026-05-06 | M3.2 启动：选 bubble_diagram 作第二个 module | 3 个理由：(1) 图状数据是当前架构最大未覆盖维度（节点+边 vs 字段平铺）；(2) 触发 M2 留 TODO 的 dot path array 索引扩展；(3) vfx_req 等克隆型不暴露新问题留到后面。`[来源: Steve 直接指示（2026-05-06）]` |
| 2026-05-06 | M3.2 schema 决策 · 节点级粒度 | spec.nodes[] / spec.edges[] 是真源，每节点/边可独立 dot path 寻址。AI 一次产整图 JSON，重生成按 id 改单节点。mechanical_check 有图级断言抓手。代价：dot path 必须支持 array 索引（M2 → M3 的拓展兑现）。`[来源: Steve 直接指示（2026-05-06）]` |
| 2026-05-06 | M3.2 渲染决策 · Mermaid（零依赖 + CDN 一行） | 文本 grep/git diff 友好；ELK pipeline 已踩坑结论复用。代价：Mermaid 自动布局不可精控，PoC 接受。`[来源: Steve 直接指示（2026-05-06）]` |
| 2026-05-06 | M3.2 node/edge type 闭合枚举 | node: entry/scene/combat/puzzle/dialogue/choice/cutscene/exit；edge: sequential/branch/optional/loop/failure。理由：CLAUDE.md 第 2 条核心理念"schema 改了字段才存在"；自由字符串等于放弃机械约束。新需求扩枚举走 schema bump。`[来源: 第一原理推导]` |
| 2026-05-06 | M3.2 dot path 扩展 · 同时支持 by-id 和 by-index | `nodes[entry].label` by-id（按 array items.id 唯一字段匹配） / `nodes[0].label` by-index（兜底）。by-id 优先因更稳（数组重排不失效）。M2 留 TODO 兑现。`[来源: 第一原理推导]` |
| 2026-05-06 | M3.2 template_diff 对图状 module 走 noop | bubble_diagram 走跳过分支，输出 mapped/missing/extra=0/0/0 + rationale。理由：template_fields.json 是字段填空型 derived from gameplay_template.html，对图状 spec 强行套是反污染失误。`[来源: 第一原理推导]` |
| 2026-05-06 | editor.html 行数约束 bump < 300 → < 400 | M3.2 加 spec 选择器 UI 后 295 → 318 行；原约束本意防大杂烩，spec 选择器是合理增量（多 spec 场景已确立）。后续仍需克制，每次 bump 在本表追加。`[来源: Steve 直接指示（2026-05-06）]` |
| 2026-05-06 | M3.2 ✅ 完成 | 4 文件新建（schema/spec/template + outputs 派生）+ 7 文件修改（render/check/diff/generate/regen/serve/editor）+ 3 文档同步。验证：demo_bubble_diagram 0 ERROR / 0 REVIEW / template_diff skipped / Mermaid HTML 渲染成功；4 项故意破坏全部命中预期 ERROR/REVIEW；regenerate by-id 切出正确 sub-schema。`[来源: 第一原理推导]` |
| 2026-05-06 | M3.2 真实案例补做（同日） | Steve 反馈"为什么用虚构？"——意识到被 lighting_req 「demo+真实分两步」模板带偏。**修正**：M3.x 引入新 module 时直接以真实案例为验收基准。落 `bubble_diagram_gangster_mansion`（11 节点 / 10 边，主动线 5 Beat）0 ERROR / 0 REVIEW / template_diff skipped / Mermaid 出图。新建 `cases/` 目录复制 `case_05_gangster_mansion__extracted_design.md` 防 future Claude 又找不到。`[来源: Steve 直接指示（2026-05-06）]` |
| 2026-05-07 | M3.3 启动 · bubble_diagram editor 走专用视图 | Steve 实测 M3.2 后反馈：通用 schema-driven form 对图状数据**功能性不可用**（不是美学）—— nodes/edges 上下两块 dashed 框无 type 区分；图与表单无视觉关联；"加分支"要分别在 nodes/edges 区 push 三步，违反图操作直觉。**决策**：renderForm() 按 spec_id 前缀分发，bubble_diagram 走专用视图（嵌 Mermaid 实时预览 + 双向高亮 + type 上色卡片 + 图操作 popover），lighting_req 通用路径完全不变。`[来源: 第一原理推导 + Steve 直接指示（2026-05-07）]` |
| 2026-05-07 | M3.3 渲染同步决策 · client-side specToMermaid 重写 | editor 内 JS port 一份 specToMermaid（< 30 行），与 [tools/render.py:88-112](tools/render.py) 的 `spec_to_mermaid` 逻辑一致。理由：实时反馈优先于 DRY；走 server round trip 200-500ms 卡顿严重。代价：python/js 双实现同步成本（新增 node/edge type 时两处都改）。约定代码注释互引。`[来源: 第一原理推导]` |
| 2026-05-07 | editor.html 行数约束再 bump < 400 → < 900 | M3.3 加图状专用视图后 318 → 820 行（CSS 70 行 / specToMermaid+双向高亮 50 行 / renderBubbleDiagramView+卡片 130 行 / 6 个图操作 handler+popover 230 行 + HTML 结构 30 行）。比预算 < 700 多出，主因 popover handlers 字面量 HTML 较啰嗦。**强制约定**：下次 M3.4+ 再超 900 必须拆 `editor/views/<module>.js`，不再 bump。`[来源: Steve 直接指示（2026-05-07）]` |
| 2026-05-07 | M3.3 ✅ 完成 | 1 文件修改（editor.html 318 → 820）+ 3 文档同步。新增能力：(1) 顶部 Mermaid 实时预览（debounce 200ms）；(2) Mermaid 节点 click 滚到 form 卡片 + 卡片 hover 反向高亮 mermaid；(3) 节点卡片按 type 上色（8 种）+ 紧凑 id/label/notes 编辑；(4) 出/入边按节点归属就地显示 chip；(5) 4 种图操作 popover（在此后插入 / 分叉 / 编辑边 / 删除节点 / 添加孤立）；(6) Esc 关闭。lighting_req 通用 form 路径未动（回归通过）。`[来源: 第一原理推导]` |
| 2026-05-07 | git 补 commit `4cfba80` = M3.2 + M3.3 合并 | M3.2 整批从未 commit + M3.3 也未 commit；editor.html 中间态 318 行版本已不可还原，强分两段为伪历史 → 合一个 commit + message 内分段说明范围 |
| 2026-05-07 | M3.4 启动 · 第二个真实关卡案例 = HUB 结构 = gangster_mansion_boss | Part 1 是线性 5 Beat，schema 表达力没被压到；HUB 结构（多 Key 收集 + 中央分流点 + 知识锁 + 回流循环）是 schema 第二种压力测试，也是 M3.x 候选表里"暴露问题最快"项。`[来源: Steve 直接指示（2026-05-07）]` |
| 2026-05-07 | M3.4 ✅ 完成 | 1 spec 新建 `bubble_diagram_gangster_mansion_boss`（13 节点 / 14 边，Phase I/II/III）；mechanical_check 0/0 ✓，template_diff skipped ✓，Mermaid 渲染 11306 chars。**关键验证**：(a) 8 种 node type / 5 种 edge type 闭合枚举对 HUB 结构表达足够（未触枚举扩展）；(b) loop 边在 HUB 回流场景首次被真实使用（Part 1 全 sequential/branch）；(c) 7/8 node type / 3/5 edge type 在两个真实案例下使用过，闭合枚举的"够用度"得到二次确认。`[来源: 第一原理推导 + extracted_design.md Page 29-32]` |
| 2026-05-07 | M3.4 暴露 4 项 schema 缺字段（候选） | 按刚需排序：(1) edges[] 的 `requires:[node_id]` 表达合取前置（knowledge_lock 入边的 Key02∧Key03，最刚需）；(2) nodes[] 的 `phase:string` 标 Phase 归属（13 节点天然分 3 阶段，加完可 Mermaid subgraph 分组）；(3) nodes[] 的 `est_minutes:[min,max]` 估时；(4) nodes[] 的 `tbd:bool` + `tbd_reason`。**决策**：候选表加"bubble_diagram schema 补字段"项，按真实需求驱动单独加，不批量推。`[来源: 第一原理推导 + M3.4 实跑暴露]` |
| 2026-05-07 | M3.4 Steve 浏览器实测判定 · HUB 布局够用 | Steve 原话「布局还不错，可以接受」→ Mermaid TD 默认布局对 4 出 3 入中央节点 + 2 条 loop 回流不纠缠；PoC 期不需要 layout hint。M3.x 候选表「加 layout hint」对应项可降优先级。`[来源: Steve 直接指示（2026-05-07）]` |

---

## 配套文档（M0 内会补）

- `CLAUDE.md` —— 给 AI 的硬约束（反污染清单）
- `INHERITANCE.md` —— 详细列从 pipeline 拿什么 / 不拿什么
