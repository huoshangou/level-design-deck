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
└── outputs/
    └── (生成的 HTML 文档放这里)
```

**约束**：
- 每个 Python 工具 < 300 行
- editor.html 单文件 < 300 行
- 没有 build step（npm/webpack 不要）
- 离线可用（CDN 依赖只允许 jsonschema、Mermaid 一类必须的）

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

---

## 配套文档（M0 内会补）

- `CLAUDE.md` —— 给 AI 的硬约束（反污染清单）
- `INHERITANCE.md` —— 详细列从 pipeline 拿什么 / 不拿什么
