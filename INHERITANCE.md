# 承袭清单

> level-design-deck 与 `~/Desktop/level-skill-pipeline/` 的资产关系。
> 本表是 [CLAUDE.md](CLAUDE.md) 反污染条款的详细展开。

---

## 承袭表（明确拿什么）

M3.7 之前只 **1 项**；M3.7 + M3.7+（2026-05-09 / 2026-05-11）有限解锁 spatial_layout 相关 4 项（按"参考可读"和"运行时资产可复制"两个层级）。

### 层级 ① 作为参考可读（Read 级别）

| 资产 | 路径 | 用法 | 复用方式 | 复用边界 |
|---|---|---|---|---|
| `ir_schema.json` v3.1 | `~/Desktop/level-skill-pipeline/src/contracts/ir_schema.json` | 作为 spec 的**上游输入参考**：spec schema 中需要 IR 字段时，引用 IR 的字段路径（如 `FEEL.overall_tone`） | **只读引用，不复制** | spec 设计**仅消费 IR 已有字段**，不得反向修改 IR |
| `spatial_layout/template.html` | `~/Desktop/level-skill-pipeline/src/contracts/skills/spatial_layout/template.html` | 用作 deck `templates/spatial_layout.html.tmpl` 渲染基线（M3.7 决：spatial_layout 最终呈现和 pipeline 一致） | 复制到 deck `templates/`，改占位符（`{{LAYOUT_JSON}}` → `{{__derived__.layout_json}}` 等）+ 加 deck spec 标识 | 仅当**渲染产物模板**用，不读其工程实现（contract.yaml / scorer / manifest 等仍禁读）|
| `case_05_gangster_mansion/layout_data.json` | `~/Desktop/level-skill-pipeline/src/test_cases/case_05_gangster_mansion/layout_data.json` | 真实案例输入素材（41 shapes / 6 layers） | 复制到 deck `cases/case_05_gangster_mansion__layout_data.json` | 仅作 spec 真实案例验收数据 |

### 层级 ② 作为运行时资产可复制（cp 级别，**禁读源码、不参考架构**）

| 资产 | 路径 | 用法 | 复用方式 | 复用边界 |
|---|---|---|---|---|
| LevelCraft 2D 编辑器 web app | `~/Desktop/level-skill-pipeline/src/contracts/skills/spatial_layout/editor.html` + `levelcraft/` bundle | deck spatial_layout 流程的**外部编辑工具**：用户在 LevelCraft 编辑布局后导出 JSON，deck 通过 Import JSON 替换 spec.layout | 复制到 deck `tools/levelcraft/`（保留原相对路径结构）；deck editor.html 通过 `window.open('/tools/levelcraft/editor.html')` 调起 | **当 web app bundle 用**（类似 Mermaid CDN 角色），绝不 grep / Read / 参考其代码风格 / 学习其架构。Read 这些文件视为反污染清单违规 |

---

## 反承袭表（明确不拿，附理由）

| 资产 | 路径 | 不拿的理由 |
|---|---|---|
| pipeline 11 模块结构 | `~/Desktop/level-skill-pipeline/src/contracts/skills/{module}/` | 按团队职能拆（lighting_req / vfx_req / audio_req）是过渡期债务；新 spec 应按"AI 可消费的最小指令单元"重新划分 |
| `manifest_schema.json` + 状态机 | `~/Desktop/level-skill-pipeline/src/contracts/manifest_schema.json` | 重型机制（pending → generated → confirmed → locked）；M0-M2 单人 PoC 不需要 |
| `scorer.js` + 14 项打分 | `~/Desktop/level-skill-pipeline/src/pipeline/scorer.js` | 评的是文档质量；新方向是机械检测 + 可执行性，第一原理重新设计 |
| HITL 三段确认 | `~/Desktop/level-skill-pipeline/src/commands/design-level.md` | 与 manifest 配套；本项目用更轻的"看告警 → 改字段"循环替代 |
| `render_standards.md` | `~/Desktop/level-skill-pipeline/src/contracts/render_standards.md` | 给文档的视觉规范（奶油色出版风）；spec 编辑器用 schema-driven UI，不该 carry 视觉债 |
| `level_type_rules.md` | `~/Desktop/level-skill-pipeline/src/contracts/level_type_rules.md` | 玩法 vs 关卡的术语切换是 pipeline 内部裁剪机制；本项目 spec 不区分这种分裂 |
| `changelog.md` | `~/Desktop/level-skill-pipeline/src/changelog.md` | 避免被旧决策框死；本项目演进记到 [PROJECT.md](PROJECT.md) 决策表 |
| `contracts/views/deck/*` | `~/Desktop/level-skill-pipeline/src/contracts/views/deck/` | iframe 包装 11 模块的 deck view 是 pipeline 的展示形态，本项目不抄 |
| `contracts/skills/lighting_req/*` | `~/Desktop/level-skill-pipeline/src/contracts/skills/lighting_req/` | **关键反污染点**：M1 设计 lighting spec schema 时**绝不读这个目录**，从 IR + `template_fields.json` 反推 |
| `spatial_layout/contract.yaml` / `scorer*` / `manifest*` / `EDITOR_ENHANCEMENT_PLAN.md` | 同 spatial_layout 目录下 | M3.7 例外**不扩散**到这些工程实现：它们是设计/校验/状态机思路（污染源），与 template.html / editor.html / levelcraft/（产物 / 运行时资产）边界明确 |
| `gameplay_template.html`（原文件） | `/Users/mofashu/Library/Containers/com.xunmeng.knock/5aK69tk2Dw6H/files/gameplay_template.html` | 4000 行 hand-coded UI，有强结构 / 命名 / 视觉污染。已一次性快照 + 提取字段清单后归档，**之后只读 `reference/template_fields.json`** |

---

## Template 处理特殊说明

template 是个特殊污染源——它是个 4000 行的成品 HTML，AI 一旦 read 就会被它的章节结构（6.x）/ 字段命名风格（"3C 限制矩阵"）/ 视觉规范带偏。

处理策略 = **物理隔断 + 文档约束** 双保险：

1. **物理隔断**：原文件复制到 `reference/templates_snapshot/`，加 README 注明"AI 不读"
2. **机械提取**：跑 `tools/template_field_extractor.py` 一次，产出 `reference/template_fields.json` —— 纯字段清单，无业务叙述
3. **后续 AI 只读 JSON**：M1+ 设计 spec / 写 diff 工具时，**只读** `template_fields.json`，**不读** `templates_snapshot/`

**何时需要重新提取**：
- template 原文件升级、字段集变化
- 步骤：删除 snapshot 重新 cp → 重跑 extractor → PROJECT.md 决策记录追加一行

---

## 边界检查清单（每个 session 自查）

接到任务想动手前，自问：

- [ ] 我有没有打算 Read 上面"反承袭表"里的任何文件？
- [ ] 我有没有打算抄旧 module 的字段名（lighting_req / vfx_req / audio_req 等）？
- [ ] 我有没有打算把 "我们应该有 manifest / scorer / HITL" 当默认前提？
- [ ] 我提议的"机制"是因为它真的对，还是因为我熟悉 pipeline 里的对应物？

任何一个 ✅ → 停下，回看 [CLAUDE.md](CLAUDE.md) 第 4 节"思维反污染"。

---

## 版本

INHERITANCE.md（承袭清单）v0.2（2026-04-30 创建；2026-04-30 改文件名避免中文链接编码问题；2026-05-09 M3.7 加 spatial_layout 解锁 2 项；2026-05-11 M3.7+ 承袭表分两个层级"参考可读"和"运行时资产可复制"，加 LevelCraft web app bundle）
