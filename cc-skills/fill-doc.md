# /fill-doc — 设计文档填写 skill

帮助设计师快速填写 gameplay / prop 等富文本设计文档，输出可注入模板的 snapshot JSON。

---

## 调用方式

```
/fill-doc gameplay <doc_name> [<设计草稿或描述>]
/fill-doc prop <doc_name> [<设计草稿或描述>]
```

**参数：**
- `gameplay` / `prop`：模板类型（对应 `templates/html/` 下的模板）
- `<doc_name>`：文档名称，如"居酒屋夜战"、"可破坏木箱"
- `<设计草稿>`（可选）：直接贴入大段设计描述，skill 自动提取并跳过对应问题

**示例：**
```
/fill-doc gameplay 居酒屋夜战
/fill-doc prop 仓库大门 这是一扇双开仓库大门，玩家可以从外侧用 F 键开门...
```

---

## 执行流程

### Phase 0 · 准备

1. 读取对应模板的字段摘要：`tools/extract_doc_fields.py` 已预生成 `templates/html/{kind}_template_*_fields.json`
   - 若 fields.json 不存在，提示设计师先运行：
     ```bash
     python3 tools/extract_doc_fields.py --all
     ```
2. 确认 `doc_name`，设定输出路径：`docs/{kind}_{doc_name}.snapshot.json`

### Phase 1 · 信息收集

按以下顺序逐 section 提问，**每次最多问 3 个核心问题**，避免信息轰炸：

#### 必填（所有文档都要问）

**基础信息**
- 这个{玩法/物件}的中文名和英文名是什么？
- 属于哪个关卡/POI？设定背景是什么？
- T 几级？（T0 核心体验 / T1 主要体验 / T2 常规 / T3 点缀）

**设计概述**
- 用一两句话描述核心体验目标：玩家做什么、感受什么？
- 基本流程/状态机是什么？（可以是简单的文字描述，之后会转成 Mermaid 图）

#### 按需问（根据设计草稿判断是否跳过）

**Gameplay 专项**
- 哪些需求章节是必须的？（参考 checklist：物理/3C/系统/任务/战斗/AI/载具/动画/灯光/特效/音效）
- 3C 限制：进入这个区域/玩法后，有没有移动/战斗/载具限制？
- 是否需要地图系统支持（大小地图显示、迷雾/解锁等）？

**Prop 专项**
- 物件有没有碰撞体？能站、能攀爬、能射穿吗？
- 是否可交互？交互方式（F 键 / 直接触发 / 特殊条件）？
- 是否可破坏/可移动？（决定物理需求）
- 引导模板：用哪种交互模板？（一级/二级/三级交互物）

#### 结束确认

所有 section 收集完后，列出已填/未填字段摘要，问设计师：
- "以上信息是否需要补充或修改？"
- "哪些需求章节确认需要？"（显示 checklist 状态）

### Phase 2 · 生成 snapshot JSON

根据收集的信息，生成符合模板 snapshot 格式的 JSON：

```json
{
  "field:gameplay_name_cn": "居酒屋夜战",
  "field:gameplay_name_en": "Izakaya Night Raid",
  "field:info_level": "T2",
  "field:design_goal": "<p>玩家...</p>",
  "field:mermaid_flowchart": "flowchart TD\n    A[触发] --> B[核心循环]\n    B --> C{成功条件}\n    C -->|达成| D[奖励结算]\n    C -->|未达成| B",
  "checkbox:chk-3c": true,
  "checklist:req-3c": true,
  "radio:3c-combat": "禁武器",
  ...
}
```

**格式规则：**
- 文本字段用 `<p>内容</p>` HTML 包裹（模板 contenteditable 格式）
- Select 字段存 value 值（如 `"T2"`）
- Radio 字段存选中的 value
- Checkbox 存 `true/false`
- Checklist 控制项：`"checklist:{section_id}": true/false` 控制章节显隐

### Phase 3 · 输出

1. 将 snapshot JSON 写入 `docs/{kind}_{doc_name}.snapshot.json`
2. 输出操作指引：

```
✅ snapshot 已生成：docs/gameplay_居酒屋夜战.snapshot.json

注入模板步骤：
1. 在 webapp 顶栏点「📄 文档模板」→「玩法设计」，新标签打开空白模板
2. 点模板左侧「导入已有文档」按钮，选择上面生成的 snapshot 文件
3. 核查各章节内容，补充图片/白盒截图等无法文字描述的内容
4. Ctrl+S 保存为本地工作文件
5. 填写完成后「导出纯净 HTML」供其他组审阅
```

---

## 鲁棒性设计原则

**模板版本无关：** skill 不硬编码字段名。通过读取 `_fields.json`（由 `extract_doc_fields.py` 从最新模板自动生成）得到当前字段列表。模板新增/删除字段，skill 自动适配。

**新模板类型支持：** 在 `templates/html/` 放入新模板文件，运行 `python3 tools/extract_doc_fields.py --all` 生成 `_fields.json`，skill 即可识别新类型，无需改 skill 本身。

**增量更新：** 若 `docs/` 下已有同名 snapshot，提示设计师是否基于旧版更新（diff 模式）还是全新填写。

**跳过机制：** 设计师贴入大段草稿时，先用 subagent 提取有效信息，自动填充对应字段，跳过已覆盖的问题。

---

## 与 /design-deck 的关系

| | /design-deck | /fill-doc |
|---|---|---|
| 输出格式 | spec.json（结构化 JSON） | snapshot JSON（注入 HTML 模板） |
| 机械校验 | ✅ mechanical_check | ❌（富文本，不做校验） |
| 渲染 | render.py → HTML | 模板本身即文档 |
| 适用场景 | 关卡设计数据（bubble/lighting/spatial 等） | 跨组需求文档（玩法/物件） |
| cc 直接写入 | ✅（Write tool → specs/） | ❌（生成 snapshot，人工导入模板） |

两套系统并行，通过 level_id / 关卡名称关联，不合并。

---

## 文件约定

```
templates/html/
  gameplay_template_v1.5.html     ← 空白可编辑模板（进 git）
  gameplay_template_v1.5_fields.json  ← 提取的字段摘要（进 git）
  prop_template_v1.5.html
  prop_template_v1.5_fields.json

docs/                              ← 填写实例（不进 git，本地/后端管理）
  gameplay_居酒屋夜战.snapshot.json
  prop_仓库大门.snapshot.json
```

`.gitignore` 追加：
```
docs/
```
