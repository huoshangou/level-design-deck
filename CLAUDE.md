# level-design-deck — AI 协作约束

> 本文件给 AI（含未来 session 的 Claude）的硬约束。
> 新 session 入口顺序：[PROJECT.md](PROJECT.md) → 本文 → [INHERITANCE.md](INHERITANCE.md)。

## 一句话项目定位

把"AI 产文档、人通读改文档"换成"AI 产 spec、Python 标问题、人定向改字段"。

---

## 1. 反污染（最重要，第一段）

本项目**独立于** `~/Desktop/level-skill-pipeline/`。

### 不引用什么
- ❌ pipeline 的字段名（lighting_req / vfx_req / audio_req / spatial_layout 等任何旧 module 名）
- ❌ pipeline 的模块边界（按团队职能拆是过渡期债务）
- ❌ pipeline 的视觉规范（奶油色出版风是给文档的，对 spec 编辑器是噪音）
- ❌ pipeline 的术语切换机制（玩法 vs 关卡）
- ❌ pipeline 的状态机（manifest）/ 评分（scorer.js）/ HITL 三段

### 禁读文件清单
**绝不要 Read 这些文件**（哪怕看一眼也会污染）：
- `~/Desktop/level-skill-pipeline/src/contracts/skills/**/*`（11 个旧 module 实现）
- `~/Desktop/level-skill-pipeline/src/contracts/render_standards.md`（视觉污染源）
- `~/Desktop/level-skill-pipeline/src/contracts/level_type_rules.md`（术语切换）
- `~/Desktop/level-skill-pipeline/src/contracts/manifest_schema.json`（重型机制）
- `~/Desktop/level-skill-pipeline/src/changelog.md`（避免被旧决策框死）
- `~/Desktop/level-skill-pipeline/src/contracts/views/**/*`（deck 视图）
- 本项目内 `reference/templates_snapshot/**/*`（template 原文件已归档，只读 `reference/template_fields.json`）

### 唯一允许引用的 pipeline 资产
- ✅ `~/Desktop/level-skill-pipeline/src/contracts/ir_schema.json` —— IR v3.1 schema，作为 spec 的上游输入参考

### M3.7 例外（2026-05-09 解锁 / 2026-05-11 扩展）

Steve 直接指示（2026-05-09）：spatial_layout 模块的"最终呈现"和 pipeline 对应同名部分保持一致。
Steve 直接指示（2026-05-11）：保留 LevelCraft 2D 编辑器作为 deck spatial_layout 流程的**外部编辑工具**，复制其 web app 到 deck 内供运行时使用。

为此**有限解锁**以下 pipeline 资产：

**作为参考可读**（Read 级别）：
- ✅ `~/Desktop/level-skill-pipeline/src/contracts/skills/spatial_layout/template.html`
  （用作 deck `templates/spatial_layout.html.tmpl` 渲染基线）
- ✅ `~/Desktop/level-skill-pipeline/src/test_cases/case_05_gangster_mansion/layout_data.json`
  （真实案例输入素材，复制到 deck `cases/`）

**作为运行时资产可复制**（cp 级别，**不读其源码、不参考其架构**）：
- ✅ `~/Desktop/level-skill-pipeline/src/contracts/skills/spatial_layout/editor.html`（LevelCraft 2D 编辑器入口）
- ✅ `~/Desktop/level-skill-pipeline/src/contracts/skills/spatial_layout/levelcraft/`（编辑器依赖 bundle：app.js / game.css / lib.min.js / 等）
  → 复制目标：deck `tools/levelcraft/`（保留原相对路径结构）
  → 用法：deck editor.html 通过 `window.open('/tools/levelcraft/editor.html')` 调起；用户在 LevelCraft 编辑后导出 JSON，deck 通过 Import JSON 按钮替换 spec.layout
  → **运行时资产 ≠ 思维污染源**：类似 Mermaid CDN 角色，只是当 web app bundle 用，绝不 grep / Read / 参考其代码风格

**仍禁读 / 仍禁复制**（M3.7 解锁不扩散）：
- ❌ spatial_layout 的 `contract.yaml` / `scorer` / `manifest` / `EDITOR_ENHANCEMENT_PLAN.md` 等工程实现（这些是设计/校验/状态机思路，是污染源）
- ❌ pipeline 其它 skill（lighting_req / bubble_chart / audio_req / vfx_req 等）—— 仍走第一原理

`[来源: Steve 直接指示（2026-05-09 / 2026-05-11）]`

详细承袭/反承袭表见 [INHERITANCE.md](INHERITANCE.md)。

---

## 2. 核心理念（4 条不可妥协）

1. **`spec.json` 是真源、HTML 是派生**——一旦反过来，整个项目失败
2. **schema 改了字段才存在**——AI 不能凭空加字段；想加先改 schema
3. **机械检测 > AI confidence**——Python 报错是硬约束，AI 自评只配做 hint
4. **template 是 checklist，不是模板**——只用 `reference/template_fields.json` 做 diff，不读 template 原文件

---

## 3. 代码约束

- **Python 工具**单文件 < 300 行，**优先标准库**（避免公司防火墙下 pip install 麻烦，详见 user `MEMORY.md` 的"公司防火墙"条）
- **`editor.html`** < 900 行，单文件 self-contained（M3.2 从 < 300 bump 到 < 400，M3.3 从 < 400 bump 到 < 900 因加 bubble_diagram 图状专用视图，理由见 PROJECT.md 决策记录 2026-05-06 / 2026-05-07）。**下次（M3.4+）再超 900 强制拆 `editor/views/<module>.js`**
- **无 build step**（不要 npm / webpack / vite）
- **离线可用**，CDN 依赖只允许必须的（如 jsonschema、Mermaid）
- **fail loud**：解析/校验失败必须明确报错，不静默 skip
- 不写注释，除非有非显然的"为什么"

### webapp/ 例外子节（B 阶段，2026-05-15+）

`webapp/` 子目录约束见 [PROJECT.md "webapp/ 例外块"](PROJECT.md)。AI 在 webapp/ 内可：
- 跨多个 Python 文件（每文件仍 < 300 行）
- 引入声明在 `webapp/wheels/` 的 pip 依赖
- 用 React/Vite/TS 构建前端（仅 `webapp/frontend/`）
- 写 ABC + namespace 抽象层

AI 在原 `tools/` + `editor/` + `cc-skills/` + `lib/` 内**不放宽**任何约束。

---

## 4. 思维反污染（L3 防线）

L3 防线由**两个机制**组成：自问（4.A）+ 决策来源标签（4.B）。前者是软自律、后者是硬契约。

### 4.A · 自问（最低门槛）

每次想用 pipeline 模式（manifest / scorer / HITL 三段 / 11 模块边界 / iframe deck wrap 等），**强制自问**：

> "我推荐这个，是因为它真的对，还是因为我熟悉？"

如果答案是"熟悉"——**放弃这个建议，从第一原理重新设计**。

### 4.B · 决策来源标签（输出契约）

涉及**架构 / 字段命名 / 模块边界 / 机制选择 / 视觉规范**的建议，必须以这种格式向 Steve 呈现：

```
建议: <内容>
[来源: <枚举之一>]
```

**允许的 7 种来源**：
- `[来源: PROJECT.md]` — 项目定盘星
- `[来源: INHERITANCE.md]` — 承袭/反承袭决策
- `[来源: ir_schema.json]` — 唯一允许的 pipeline 资产
- `[来源: template_fields.json]` — 玩法 template 字段清单
- `[来源: work_docs_extract.json]` — POI/玩法 公司文档提取产物（含 POI 灯光等字段定义）
- `[来源: Steve 直接指示（YYYY-MM-DD）]` — 用户对话中当场决策，含日期防失效
- `[来源: 第一原理推导]` — 从问题本质重新设计（**最可疑，需 Steve 重点审**）

> **`reference/*` 任意机械化提取产物都可作为来源**，未来若新增 `poi_template_fields.json` 等新工件，按命名直接引用，不需再改 CLAUDE.md。

**禁用来源**（出现即拒绝该建议）：
- ❌ `[来源: pipeline 经验 / level-skill-pipeline / 旧实现 / 我熟悉 / 行业惯例]`

**必须标的场景**：
- spec 字段命名 / 类型 / 默认值 / required 属性
- module 边界划分
- 机制选择（验证 / 校验 / 编辑 / 渲染 / 状态管理）
- 视觉规范决策
- 任何"应该是 X"的架构断言
- **方向反问**（如"先做 A 还是 B"）也要在选项后标各自来源

**不需要标的场景**：
- 纯执行（实现已定 schema 的 form / 跑测试 / 修语法 bug）
- 文档措辞 / 排版 / 字段中文翻译
- 流程性操作（创建目录、复制文件、grep）
- 总结、汇报、状态查询

**Steve 的检查动作**：
- 没标来源的架构建议 → 拷打"来源是什么？"
- 看到禁用来源 → 拒绝
- 看到 `[来源: 第一原理推导]` → 重点审，因为这是 AI 最容易"借第一原理之名行 pipeline 之实"的标签

**反激励防御**：本机制不为减少建议数量，**为让建议透明**。AI 不应因标注成本抑制主动性。如果某个建议在 5 种来源里找不到归属、又不能算"第一原理"，那就是**没想清楚** —— 应该说"我没想清楚来源"，而不是硬塞一个标签。

---

## 5. 变更纪律

- **schema 改动** → bump version + 在 PROJECT.md 决策记录追加一行（why）
- **核心架构决策** → PROJECT.md 决策记录表追加
- **承袭清单改动** → 改 `INHERITANCE.md` + PROJECT.md 决策记录追加
- **不要**改 PROJECT.md 的历史决策行（只追加新行）

---

## 6. 验证纪律

- 改完代码主动跑：
  - `python3 tools/template_field_extractor.py`（M0 后任何 template 变更）
  - 后续 M1 加 `python3 tools/mechanical_check.py specs/<file>` / `python3 tools/template_diff.py specs/<file>`
- 验证用具体输出（stats、抽查）证明，不要只说"应该没问题"

---

## 7. 红线（必须先问 Steve）

- 删除已 commit 到 git 的任何文件
- 修改 PROJECT.md 的"是什么/不是什么"或"核心理念"
- 修改本文件（CLAUDE.md）的反污染清单
- 修改 `INHERITANCE.md` 的承袭/反承袭表
- 在 webapp/ 之外引入新外部依赖（pip install / npm install）；webapp/ 内按已批准 plan 范围内不重复问
- 给项目加新里程碑（M3+）

---

## 8. Session 启动流程（cc 进 LDD 工作目录时自动）

每次 cc 在 LDD 工作目录启动新对话，**第一动作**：

1. 检查 `memory/pending_review.md` 是否存在且非空
   - 若有内容：给 Steve 展示最近 session 的 [决策] / [待定] / [风险] / [需求] / [迭代]
     摘要，**问他**要不要合并到正式位置（PROJECT.md 决策记录 / 某 module 的 spec 备注 /
     本文约束清单等）；合并完后**清空** `pending_review.md`（保留文件，写入"已清空"标记
     或直接删除内容）
   - 若空 / 不存在：跳过
2. 列 `memory/*.md` 提示是否要继续某个未结话题
3. 然后才进 9 节"新 session 入口"必读顺序

`memory/pending_review.md` 由 `tools/stop_hook.py` 在 cc 对话结束时自动追加（通过
`.claude/settings.json` 的 Stop hook 注册）。**禁止**人工直接编辑此文件 — 它是机器自动落盘
的暂存区，正式去处由你跟 Steve 合并后定。

## 9. 新 session 入口

新 session 必读顺序（30 秒内）：
1. **PROJECT.md** —— 项目定位 + 5 步流程 + 3 里程碑
2. **本文（CLAUDE.md）** —— 反污染 + 代码约束
3. **INHERITANCE.md** —— 详细承袭/反承袭表
4. 任务相关：`reference/template_fields.json`（M1+ 设计 spec 时必看）

**不要**：在没读上述文件的情况下凭印象做架构决策。

---

## 版本

CLAUDE.md v0.9（2026-04-30 创建；2026-05-06 加 4.B 决策来源标签输出契约；2026-05-06 同日：补 work_docs_extract.json 和 Steve 直接指示 2 种来源枚举；2026-05-06 M3.2：editor.html 行数约束从 < 300 bump 到 < 400；2026-05-07 M3.3：editor.html 从 < 400 bump 到 < 900，加 bubble_diagram 图状专用视图；2026-05-09 M3.7：加反污染 M3.7 例外块，有限解锁 pipeline spatial_layout/template.html + test_cases/case_05/layout_data.json；2026-05-11 M3.7 扩展：例外块加"运行时资产可复制"层级，解锁 LevelCraft editor.html + levelcraft/ bundle 复制到 deck 内供 spatial_layout 流程使用；2026-05-15 v0.7→v0.8 加 webapp/ 例外子节（B 阶段 M4 启动）+ 红线第 5 条加 webapp/ 范围限定；2026-05-27 v0.8→v0.9 加第 8 节 Session 启动流程 + 引入 memory/pending_review.md 自动落盘机制，原 8 节顺延到 9）
