# /fill-gamedoc — 对话式引导填充物件/玩法需求文档

通过对话引导用户填写 prop 或 gameplay v1.5 模板，输出落盘到 `docs/`，webapp 自动预览。

支持三种入口：
- **从零对话**：用户说"我要写一个 XX 物件文档"，AI 主动引导
- **已有材料**：用户拖文件/聊天记录/图片，AI 提取后补问缺口
- **接力修改**：基于 `docs/` 里已有的文档继续改

填好的 HTML 顶部含**可点击锚点摘要框**，不确定字段用 `ai-flag` span 高亮标注。

---

## 工具使用纪律（最重要 · 必须遵守）

本 skill 在 webapp 沙箱内运行，**只允许这些工具组合**：

| 操作 | 必须用 | 禁止 |
|------|--------|------|
| 读模板 / fields.json / 用户文件 | `Read` | ❌ `cat` / `head` |
| 搜字段位置 | `Grep` / `Glob` | ❌ Bash 的 grep / find |
| 复制模板到 docs/ | `Read` 原模板 → `Write` 到 docs/ | ❌ `cp` 命令、❌ 写 Python 脚本 |
| 替换字段内容 | `Edit`（精确字符串替换） | ❌ `sed` / `awk` / 自写 Python |
| 提取 PDF/DOCX/XLSX | `Bash(python3 /Users/mofashu/scripts/*2text.py <path>)` | ❌ 自己写新提取脚本 |
| 增量改字段 | `Edit`（找到唯一 old_string → 替换） | ❌ 用 `Write` 重写整文件 |

**绝对禁止**：
- ❌ 写任何临时 Python 脚本（`/tmp/*.py` 之类）
- ❌ 用 heredoc / sed / awk 操作文件
- ❌ 调用 `cp` / `mv` 之类的 Bash 文件操作
- ❌ 试图改 `.claude/settings.json` 自救加权限
- ❌ 用 `Write` 覆盖整个 docs/ 已有文件（除了首次创建）

**如果需要的工具不在白名单**：直接告诉用户"当前 webapp 沙箱不允许此操作，需要扩展白名单"，**不要反复试**。

---

## 环境路径

```
模板目录:      ~/Desktop/level-design-deck/templates/html/
prop 模板:     templates/html/prop_template_v1.5.html      (5046 行)
gameplay 模板: templates/html/gameplay_template_v1.5.html  (4518 行)
字段定义:      templates/html/prop_template_v1.5_fields.json
              templates/html/gameplay_template_v1.5_fields.json
输出目录:      ~/Desktop/level-design-deck/docs/  ← 用 Write 直接落盘
```

---

## 输入

$ARGUMENTS

支持形式：
- `/fill-gamedoc` — 从零对话开始
- `/fill-gamedoc <文件路径>` — 从已有材料开始
- `/fill-gamedoc --kind=prop|gameplay` — 跳过类型确认
- `/fill-gamedoc --resume docs/<已有文档>.html` — 接力修改已有文档

---

## Phase 0 — 类型确认 + 基础信息

### 0.1 文档类型

若用户未通过 `--kind` 声明：
- 询问："是物件需求文档（prop）还是玩法设计文档（gameplay）？"
- 不要两个都做

若从材料提取，按关键词自动判断：
- 含「物件分类」/「可交互」/「碰撞处理」/「物件功能」 → **prop**
- 含「玩法流程」/「核心循环」/「设计目标」/「玩法判定」 → **gameplay**
- 模糊时仍询问用户

### 0.2 基础信息（一次性问完）

```
1. 物件/玩法的中文名 + 英文名
2. 所属场景/区域（如 LittleTokyo、商业区）
3. 设计师英文缩写（用于文件命名，例：FNR）
4. 优先级（T0/T1/T2/T3，不知道则跳过）
```

一次性问，不要分四次问。

### 0.3 材料提取（如有）

| 格式 | 处理方式 |
|------|---------|
| `.html`（旧填充版 / group_doc） | `Read` → 正则解析 `data-field` 和 `<span class="value">` |
| `.txt` / `.md` / 聊天记录 | `Read` 直接读 |
| `.pdf` / `.docx` / `.pptx` / `.xlsx` | `Bash(python3 /Users/mofashu/scripts/<格式>2text.py <路径>)` |
| `.json`（IR 等结构化数据） | `Read` + `JSON.parse` |
| 图片 | 视觉读取后进文本流程，否则告诉用户先描述 |

提取后：用一段话总结已知信息（不超过 200 字），列出已知/未知字段清单，进入 Phase 1。

### 0.4 输出文件名

```
prop：     {物件英文名}-设计文档-{设计师缩写}.html
gameplay：【玩法】{玩法名}-设计文档-{设计师缩写}.html
```

如不确定，问用户确认后再用。

---

## Phase 1 — Checklist 对话（决定哪些组介入）

`Read` `templates/html/{kind}_template_v1.5_fields.json`，按 `checklist_items` 的 `group` 字段分组询问。

**询问原则：一组一问，不逐条问。每轮最多 3 个问题，编号列出。**

按顺序逐组确认（材料里已明确的跳过）：

```
文案组：    "需要提文案包装需求吗？（玩法包装 / 物件包装）"
角色组：    "涉及角色动作或3C需求吗？"
物理组：    "有物理表现需求吗？（非破坏类物理 / 可破坏物）"
系统组：    "需要系统组介入吗？（系统合作 / 地图系统 / UIUX）"
           ↳ 若 UIUX=是，追问："需要地图icon吗？功能交互提示？"
地图组：    "需要专门的灯光需求吗？"
载具/AI/战斗/任务组：按物件特性一次列出，"以下哪些组需要介入？"
GPP：      "有引擎动画需求吗？"
美术：     "原画/模型默认需要，特效和音效呢？骨骼动画？"
```

**硬性门槛（不能跳过）：**

- **prop**：询问"有白盒视频吗？" — 非极度简单的物件必须提供
- **gameplay**：3C需求是强制模块，直接激活，不询问
- **两类共用**：可配置项必须区分"模板参数"vs"动态实例参数"

记录激活的 checklist items → 进入 Phase 2。

---

## Phase 2 — 内容整理（脑子里，不动文件）

对每个激活的 section（`checklist_controlled: true` 的按 Phase 1 激活，`false` 的全部激活），整理填充内容。

### 三档置信度

| 置信度 | 条件 | 输出格式 |
|--------|------|---------|
| 高 | 信息明确无歧义 | 直接填入 |
| 中 | 有信息但存在推断 | 填入内容 + `【待确认】` |
| 低/缺 | 无相关信息 | `【待填写：<原因/需要什么>】` |

### 分组批量补问

如果多个 section 都缺核心信息，一次性汇总问，不要逐 section 拷问：

```
以下信息我还需要：
1. 物件尺寸（影响模型精度和资产命名）
2. 是否有交互行为及方式
3. 破坏物的破碎方式（Single / Cumulative / StageDeductions）

以上哪些你能给？没有的跳过，我会标注待确认。
```

### gameplay 强制校验

- 玩法判定四字段（触发区域 / 执行范围 / 完成条件 / 中止条件）**必须全部填写**
- 3C需求 section 必须激活

### prop 强制校验

- 激活 `chk-physics-destructive` → 必须询问破碎方式
- 可配置项 → 强制区分"全类一致→模板参数"vs"实例变化→动态实例参数"

整理完，对每个字段记录：`{key, value, confidence, flag_id?}`，进入 Phase 3 落盘。

---

## Phase 3 — 落盘生成（纯 Read / Write / Edit 流程）

### 3.1 复制模板到 docs/（仅首次）

**Step A：** `Read` 模板原文件
```
Read: ~/Desktop/level-design-deck/templates/html/{kind}_template_v1.5.html
```

**Step B：** `Write` 整个模板内容到 docs/ 目标路径
（白名单允许 Write 任意路径）

**Step C：** 一次性 `Grep -n 'data-field' docs/<文件名>` 拿到所有字段位置，记在脑子里备用。
**不要每改一个字段就重新 Read 一遍**——这非常浪费 token。

### 3.1.5 头部 meta 必填 checklist（**强制顺序：先填头部再填正文字段**）

**踩坑记录**：cc 经常默认从 6.x 玩法需求开始填，把抬头/标题/版本等头部字段当成可选→生成出的文档浏览器 tab 名、侧边栏导航、H1、版本/日期/策划名全是 `XXX 玩法` 之类的占位，用户必须事后手动指出才补。**这是 fill-gamedoc 的最高频 bug。**

**Step A：进入 3.2 字段替换循环之前，先把下列 13 项全填掉。**

| # | 位置 | data-field / HTML 锚点 | 来源策略 |
|---|---|---|---|
| 1 | HTML `<title>` 标签（行 ~8） | `<title>...</title>`（**非 data-field**，Grep 锚点 `<title>`）| `{中文名} - 玩法设计文档` |
| 2 | 侧边栏导航标题（行 ~1100） | `id="nav-title"`（**非 data-field**，Grep 锚点 `nav-title`）| `{中文名}<br>玩法设计` |
| 3 | 文档头主标题 H1 | `data-field="gameplay_name_cn"` | 中文名（用户素材里有，必给）|
| 4 | 文档头副标题 | `data-field="gameplay_name_en"` | 英文名 + 一句话定位（如 `Dynamic Truck Boarding — 开放世界机会性载具交互`）|
| 5 | 版本号 | `data-field="version_num"` | 默认 `v1.0`（首次生成）|
| 6 | 日期 | `data-field="header_date"` | 今天日期 `YYYY-MM-DD`（用 Bash 跑 `date +%Y-%m-%d` 不要猜）|
| 7 | 状态 | `data-field="status"` | 默认 `设计中`（首次生成）|
| 8 | 策划名 | `data-field="designer"` | 走 profile_prompt_block 注入的设计者信息（如 `芬里尔 (FNR)`），**禁止留空 / 禁止写"待填写"** |
| 9 | 02 玩法信息 · 中文名 | `data-field="info_name_cn"` | 同 #3 |
| 10 | 02 玩法信息 · 英文名 | `data-field="info_name_en"` | 同 #4（去掉一句话定位部分，只留英文名）|
| 11 | 02 玩法信息 · 版本 | `data-field="info_version"` | 同 #5 |
| 12 | 02 玩法信息 · 设定 | `data-field="info_setting"` | 用户素材里通常有（如 `现代开放世界（大都市）`）|
| 13 | 02 玩法信息 · 地块 | `data-field="info_region"` | 用户素材里通常有（如 `许可路段（高架路 / 工业区干道 / 城郊连接道路）`）|

**Step B：每项标"已知/推断/待用户确认"**
- 用户素材直接有 → 已知，填
- 素材里有迹象可推断 → 推断，填上 + 用 `ai-flag ai-uncertain` 包裹（除非是 #1 #2 #5 #6 #7 这类 deterministic 字段不需要 flag）
- 完全没线索 → 这是**少数情况**（基本字段而已），当场问用户**1 个问题**拿到答案，禁止直接填"待填写"占位让用户事后补

**Step C：完成头部 13 项后，再进 3.2 通用字段循环。**

**反例（cc 历史踩过的坑）**：
- ❌ `<title>` 留默认 `玩法设计文档` 不改 → 浏览器 tab 名永远是"玩法设计文档"
- ❌ `gameplay_name_en` 写 `XXX 玩法` 当占位 → 用户看 H1 副标题以为还没改
- ❌ `designer` 留空 → 文档没归属
- ❌ `header_date` 写 `YYYY-MM-DD` 字面字符串 → 设计师以为日期控件坏了

### 3.2 用 Edit 逐字段替换

对每个待填字段，用 `Edit` 工具找到模板原占位（通常是空 `<td></td>`、`<div contenteditable="true"></div>` 或 `<span class="fill-placeholder">...</span>`），原位替换成内容。

**定位锚点技巧：**
- `_fields.json` 的字段 `key` 对应模板内 `data-field="<key>"` 属性
- 在模板里 `Grep` 字段相邻的 label 文本（如「中文名」「英文名」），保证 `old_string` 唯一
- 富文本字段用 `<p>` 包裹多段内容

**置信度标注用 span 包裹：**

```html
<!-- 待确认字段（中置信） -->
<span class="ai-flag ai-uncertain" id="flag-1">推断内容 <sup style="color:#856404;font-size:0.75em">⚠ 待确认</sup></span>

<!-- 待填写字段（低置信/缺信息） -->
<span class="ai-flag ai-missing" id="flag-2"><em style="color:#721c24">【待填写：请补充物件尺寸，影响资产命名】</em></span>
```

`flag-N` 按出现顺序从 1 递增。

### 3.3 Radio / Checkbox 状态

根据 Phase 1 / Phase 2 的结果，用 `Edit` 把对应 `<input type="checkbox" id="chk-xxx">` 加 `checked`，对应 radio 加 `checked`。

**陷阱（来自附录 C.1）：字符串匹配先检测否定形式**

```
'不可破坏'.includes('可破坏') === true！
所以先判断 '不可破坏'，再判断 '可破坏'
（不可移动/可移动、不可交互/可交互 同理）
```

### 3.4 Mermaid 流程图

模板默认有 mermaid 占位：
- prop：`stateDiagram-v2` 默认骨架
- gameplay：`flowchart TD` 默认骨架

如果用户提供了 mermaid 源码，用 `Edit` 替换 `data-field="mermaid_flowchart"` 容器内的内容。

如果未提供，标 `【待填写：请提供 Mermaid 流程图源码，可在预览栏双击图直接编辑】`。

### 3.5 注入 ai-flag 摘要框

在 `<body>` 标签后用 `Edit` 插入：

```html
<body>
<details id="ai-review-box" style="position:sticky;top:0;z-index:999;background:#FAF3E8;border-bottom:2px solid #CC785C;font-family:-apple-system,'Helvetica Neue',sans-serif;font-size:13px;">
  <summary style="padding:8px 16px;cursor:pointer;list-style:none;display:flex;gap:14px;align-items:center;flex-wrap:wrap;">
    <strong style="white-space:nowrap">📋 AI 填充摘要</strong>
    <span style="white-space:nowrap">✅ <strong>N_FILLED</strong></span>
    <span style="white-space:nowrap;color:#856404">⚠️ <strong>N_UNCERTAIN</strong></span>
    <span style="white-space:nowrap;color:#B33B3B">❌ <strong>N_MISSING</strong></span>
    <span style="margin-left:auto;color:#888;font-size:11px;white-space:nowrap">点击展开详情 · 检视完成后删除此框</span>
  </summary>
  <div style="padding:6px 16px 12px;line-height:1.8;border-top:1px solid #E8DCC8;">
    ⚠️ 待确认：<a href="#flag-1" style="color:#856404">字段名</a> &nbsp;
    ❌ 待填写：<a href="#flag-2" style="color:#B33B3B">字段名</a>
  </div>
</details>
<style>
  #ai-review-box summary::-webkit-details-marker { display:none }
  #ai-review-box summary::after { content:"▸"; font-size:11px; color:#888; }
  #ai-review-box[open] summary::after { content:"▾"; }
  @media print { #ai-review-box { display:none } }
</style>
```

**默认折叠**（不写 `open` 属性），只占一行不挤占预览栏，点击展开看详情。替换规则：
- `N_FILLED` / `N_UNCERTAIN` / `N_MISSING` → 实际数量（为 0 时仍保留 chip 显示 `0`，让设计师一眼看出"已全部清干净"）
- `<details>` 内的待确认 / 待填写锚点按实际 flag-N 全部列出；如果某类为 0，对应整行去掉

### 3.6 完成报告

**写完成报告前必须先跑头部 meta sweep**（3.1.5 配套完工 gate）：

```bash
# 任意一项非空才允许写完成报告；空 / 占位 / "XXX" / "待填写" 一律算 fail
Grep -n 'data-field="(gameplay_name_cn|gameplay_name_en|version_num|header_date|status|designer|info_name_cn|info_name_en|info_version|info_setting|info_region)"' <docs/文件名>
Grep -n '<title>' <docs/文件名>  # 不能是默认 "玩法设计文档"
Grep -n 'nav-title' <docs/文件名>  # 不能是默认 "XXX 玩法"
```

任意头部字段未填 / 仍是占位 → 回 3.1.5 补，**禁止写"完成"**。

完成模板：

```
✅ 文档已生成：docs/{文件名}

头部 meta（13 项）：全部已填 ✅

摘要：
- 自动填入 N 项
- 待确认 M 项（点摘要框锚点跳转）
- 待填写 K 项（点摘要框锚点跳转）

⚠️ 以下动态模块无法静态注入，需在预览栏手动添加：
- 音效需求表
- 配置参数组
- 资产列表（如有多条）

webapp 应已自动在预览栏打开新文档。
```

---

## Phase 4 — 增量修改（用户提"改一下 XX"时）

**绝对原则：用 `Edit` 精确替换，不要 `Write` 重写整文件。**

### 4.1 定位

用户说"把 6.6 字段改成 XX"或"流程图回退一下"时：
1. `Grep -n` 字段相邻 label 或字段名定位
2. 用 `Edit` 找到唯一的 `old_string`（带足够上下文确保唯一）
3. 替换为新内容

### 4.2 ai-flag 的处理

如果用户修改的是已标 ai-flag 的字段，**一并去掉 flag span 包裹**：

```html
<!-- 修改前 -->
<span class="ai-flag ai-uncertain" id="flag-3">推断的尺寸 <sup>⚠ 待确认</sup></span>

<!-- 修改后（用户确认了实际值） -->
90×10×270cm
```

### 4.3 摘要框更新

修改完成后，如果调整了 ai-flag 数量，用 `Edit` 同步更新顶部摘要框的统计数字和锚点列表。

### 4.4 接力修改（用户给新方案推翻旧方案 / 大改）

**触发条件**：用户在已有文档基础上说"现在改用 XX 方案"、"流程改成 A→B→C"、"把 30m 改成 50m"、"半接管去掉换成 QTE" 等，**任何会让多个字段同时失效的方案级改动**。

**强制纪律**：按字段 checklist 改必漏。旧术语会零散散布在 `design_goal` / `uiux_requirement` / `sfx_requirement` / `anim_requirement` / `gameplay_name_en` 副标题 / 摘要描述等各种地方，单凭印象改完不能算完工。

**必须执行的三步**：

**步 1：先产出"旧→新术语映射表"**（在 thinking 里列清，不要跳过）
```
旧术语 → 新术语
- "30m" → "50m"
- "半接管" → "QTE 接入"
- "一段 / 二段 / 双段接入" → "单段 QTE"
- "意图区" → "标记区"
- "玩家手动追近+系统接管" → "玩家手动驾驶+QTE+Cutscene 校正"
```

**步 2：按映射表逐项 Grep + Edit**
- 每个旧术语跑 `Grep -i "旧术语" 文件`，对每个 hit 判断是合法保留（如 changelog 摘要 / 反例说明）还是要替换
- 用 Edit 替换需要改的 hit；保留的 hit 写明理由
- 不要"按字段顺序通读改"——那样一定漏

**步 3：完成后必须跑"旧术语 sweep 验证"**（这是完工判据，不是可选）
- 把映射表里所有旧术语用一条 Bash 命令 grep 一遍
- 输出格式：
  ```
  旧术语 sweep 验证：
  - "30m": 0 hits ✅
  - "半接管": 1 hit（L1077 changelog 摘要，合法保留）✅
  - "意图区": 0 hits ✅
  ...
  ```
- 任意一项有非白名单 hit → **不能写"修改完成"**，必须继续改

**白名单**（合法保留旧术语的位置）：
- ai-review-box 摘要框里的"已删除 X / 已替换 X→Y"changelog 行
- 注释里明确写"⚠ 旧方案，已废弃"的对照说明

### 4.5 用户报告 diff 不对时（"没看到改动 / 还是旧的 / 没生效"）

**禁止反射**：第一句话不要说"浏览器缓存 / 硬刷新 / 清缓存"。这是 cc 历史上反复踩的坑——文件没改干净时让用户去清缓存，浪费双方时间。

**必须反射**（按顺序）：
1. **先 Grep 验证文件实际状态**：用用户提到的关键词跑 `Grep -i "关键词" 文件`
2. **看是否真改了**：
   - 文件里还有旧内容 → 是 **cc 的问题**，承认遗漏并继续改
   - 文件里已经是新内容 → 才考虑外部因素（浏览器缓存 / iframe 没刷新 / 预览栏没指向最新文件等）
3. **承认遗漏时的措辞**：直接说"我之前漏了 X / Y / Z 处，现在补"，不要找借口

### 4.6 mermaid 流程图字段编辑（硬规则）

**只允许整段替换**：mermaid 字段的 Edit `old_string` 必须 = 完整的 `<div class="mermaid" ... data-field="mermaid_flowchart">...完整 flowchart 源码...</div>`，含开标签和闭标签。

**禁止局部替换**：禁止只换 mermaid 节内某几行节点 / 某条边。
- **理由**：mermaid 解析器对未定义节点容错差，残留一行 `B --> C{xxx}` 会让整张图渲染失败。Edit 局部替换时极容易把旧节点连接的尾巴留下变成孤立节点。
- **代价对比**：整段替换的 `old_string` 长一些，但保证图能渲染；局部替换省字符但坏图概率高。

**实操**：
1. `Grep -n "data-field=\"mermaid_flowchart\"" 文件` 定位 mermaid 节起点
2. `Read` 起点+50 行，确认看到 `</div>` 闭标签
3. Edit 时 `old_string` 包含从 `<div class="mermaid"` 到 `</div>` 的完整段
4. `new_string` 重写整段 mermaid 源码（含 `flowchart TD`、所有节点、所有 style）

---

## 行为约束

- **不要一次问太多**：每轮最多 3 个问题，编号列出
- **不要重复已知信息**：材料里已提取到的字段不再询问
- **不要自创字段**：只填 `_fields.json` 中存在的字段
- **不要假设资产路径**：白盒视频路径、p4 路径、归档路径等没明确就标 `【待填写】`
- **命名不要猜**：资产命名（模型名、BP名、特效名）必须用户确认或标 `【待确认】`
- **不要跳过硬性门槛**：白盒视频（prop）、3C需求+判定四字段（gameplay）是必填
- **绝不写 Python**：所有文件操作走 Read/Edit/Write
- **绝不重写整文件**：增量修改一律用 Edit 精确替换

---

## 参考规范（填写时内化，不向用户输出）

**资产命名格式：**
- 模型：`功能物件名_布设环境大类_尺寸_编号_拆分部件`（如 `ElectronicDoor_Residential_90×10×270_01_Frame`）
- BP：`BP_物件英文名`
- 特效：`NS_Level_Gadget_特效名`（前缀不能新增下划线）

**参数类型判断：**
- 全类一致、不频繁修改 → 模板参数（Template Params）
- 按实例单独调整 → 动态实例参数（Dynamic Instance Params）

**特效/音效**：初次提需简写表现意图即可，详细 sheet 可后补

**资产路径：** 不允许外组复用的路径归 `/ALL/Game/Props/Level/物件文件夹/MeshAndPhysics`

---

## 附录 A — Prop 模板核心字段速查（v1.5）

### 静态字段（`data-field="<key>"`）

```
prop_name_cn / prop_name_en       物件名（中英）
version_num / status / designer   header 区
info_version / info_setting / info_region / info_level / info_name_cn / info_name_en
whitebox_p4_path                  白盒视频 p4 路径
prop_description / gameplay_description / prop_function_desc  富文本三件套
mermaid_flowchart                 Mermaid 源码
reward_yn / reward_timing         奖励
map_display / map_fog / map_destroy / map_dynamic / map_priority  地图配置
mission_requirement / anim_requirement / light_requirement / placement_rules  富文本
```

### Radio 枚举（**先检否定形式**）

```
collision           有碰撞体 | 无碰撞体
art-precision       细精度 | 一般精度
interactable        可交互 | 不可交互       ← 先检 "不可交互"
scan-highlight      全部高亮 | 局部高亮 | 不用高亮
destructible        可破坏 | 不可破坏        ← 先检 "不可破坏"
movable             可移动 | 不可移动        ← 先检 "不可移动"
impulse-response    单次冲击 | 累计冲击
mp-host / mp-guest  yes | no
```

### Checkbox（ID）

```
col-no-stand         不可站立
col-no-climb         不可攀爬
col-see-through      视线可穿透
col-shoot-through    可射穿（精确匹配，注意别匹配 col-shoot-vfx）
col-shoot-vfx        可射穿-特效
col-no-cover         不可作为掩体
chk-sfx              音效需求
chk-mission          任务需求
chk-map              地图系统
chk-system           系统需求
chk-physics-destructive  可破坏物
chk-ux               UIUX（默认勾选）
chk-concept          原画（默认勾选）
chk-model            模型（默认勾选）
```

### 动态模块（无法静态注入，标 `【待填写】` 让用户预览栏内手填）

```
interact-method-body    交互方式表格行
config-form-groups      模板参数分组
config-scene-groups     动态实例参数分组
art-items-container     概念/模型需求条目
sfx-table-body          音效需求表格行
stim-items-container    刺激源列表
```

---

## 附录 B — Gameplay 模板差异

与 Prop 共用大部分字段，差异：

```
gameplay_name_cn        玩法中文名（替代 prop_name_cn）
gameplay_name_en        英文名 — 一句话描述
design_goal             设计目标与体验（富文本）
gameplay_description    玩法描述（富文本）
validation_items        校验项（富文本）← 填审核维度，不是真实测试点
flowchart_description   流程图补充说明（富文本）
gameplay_function       玩法功能（富文本）
```

Mermaid 默认：prop 用 `stateDiagram-v2`，gameplay 用 `flowchart TD`。

---

## 附录 C — 已知陷阱

### C.1 字符串否定前缀

```javascript
'不可破坏'.includes('可破坏')  // true
```

填 radio 时必须**先检否定形式**：「不可破坏」→「可破坏」→「未提及」。

### C.2 HTML 实体反转义

提取 group_doc HTML 时，mermaid 箭头 `-->` 被编码为 `--&gt;`。
所有提取结果必须反转义 `&amp; &lt; &gt; &quot; &#39;` 才能放回 mermaid 容器，否则渲染失败。

### C.3 v1.5 模板的 hydrate 机制

`data-snapshot` 属性只在用户**手动**点「导入纯净 HTML」时被读取，**页面加载时不会自动 hydrate**。所以填充必须**直接修改 HTML 字符串**，不能寄希望于 snapshot 注入。

### C.4 动态生成的 radio name

v1.5 模板的交互属性 section（交互方式 1/2/3）的 radio name 格式为 `interact-type-{序号}`，由 JS 在 DOM ready 时动态创建。**这些状态无法通过静态 HTML 设置**，必须由用户在预览栏内手动点选。

