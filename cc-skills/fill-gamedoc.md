# /fill-gamedoc — 从结构化数据填充 prop / gameplay 设计文档

将已有的结构化设计数据（group_doc HTML、IR JSON、字段表等）批量填入 v1.5 物件/玩法需求文档模板中，输出可在 webapp 预览栏直接查看的填充版 HTML。

> **deck 适配版**（原版来自同事 fenlier，已修改路径和环境配置）

---

## 环境路径

```
模板目录:     ~/Desktop/level-design-deck/templates/html/
prop 模板:    templates/html/prop_template_v1.5.html
gameplay 模板: templates/html/gameplay_template_v1.5.html
mermaid.js:  ~/Desktop/level-design-deck/lib/mermaid.min.js
输出目录:     ~/Desktop/level-design-deck/docs/
```

---

## 输入

$ARGUMENTS

支持形式：
- `/fill-gamedoc <源文件路径> [--kind=prop|gameplay]` — 从单个源文件生成
- `/fill-gamedoc <源文件路径> --output=<文件名>` — 指定输出文件名

---

## Phase 0 — 前置检查

### 0.1 验证路径

启动时验证以下路径存在，任一缺失则报错并停止：

```
~/Desktop/level-design-deck/templates/html/prop_template_v1.5.html
~/Desktop/level-design-deck/templates/html/gameplay_template_v1.5.html
~/Desktop/level-design-deck/lib/mermaid.min.js
~/Desktop/level-design-deck/docs/   ← 自动创建，不报错
```

### 0.2 源文件格式识别

| 格式 | 处理方式 |
|---|---|
| `.html`（group_doc 等） | 正则解析 tab-content |
| `.json`（IR / manifest） | JSON.parse 读字段 |
| `.pdf` / `.pptx` / `.xlsx` / `.docx` | `python3 ~/scripts/*2text.py` 提取文本 → 进 Phase 1 |
| 图片 | 视觉读取后进文本流程 |
| 纯文本 / 对话 | 直接进 Phase 1 |

### 0.3 文档类型确认

未通过 `--kind` 声明时：
- 源文件含「物件分类」/「可交互」/「碰撞处理」等字段 → **prop**
- 源文件含「玩法流程」/「核心循环」/「设计目标」等字段 → **gameplay**
- 不确定 → 询问用户

### 0.4 输出文件名

- prop：`{物件名}-设计文档-{设计师英文缩写}.html`
- gameplay：`【玩法】{玩法名}-设计文档-{设计师英文缩写}.html`
- 设计师英文缩写从用户确认获取，不要假设

---

## Phase 1 — 数据提取

### 1.1 从 group_doc HTML 提取

每个 entity 数据在 `<div id="tab-{key}" class="tab-content">` 块内：

```javascript
function extractTabContent(html, key) {
  const re = new RegExp(`id="tab-${key}"[^>]*>([\\s\\S]*?)(?=<div\\s+id="tab-\\w+"|$)`, 'i');
  const m = html.match(re);
  return m ? m[1] : '';
}
```

### 1.2 字段提取函数

| 函数 | 用途 |
|---|---|
| `extractPreField(tab, label)` | 从 `<pre>` 标签提取多行文本 |
| `extractField(tab, label)` | 从 `<span class="value">` 提取单行文本 |
| `extractSelectedOptions(tab, label)` | 提取所有 `class="opt on"` 的选中项 |
| `extractMermaid(tab)` | 提取 `<pre class="mermaid">` 中的 mermaid 源码 |
| `extractImages(tab)` | 提取所有 base64 图片（按 section 分类） |
| `extractSoundRows(tab)` | 提取音效需求表格行 |
| `extractConfigRows(tab)` | 提取配置参数表格行 |

**关键**：所有提取结果必须调用 `unescapeHtml()` 反转义：

```javascript
function unescapeHtml(str) {
  return str.replace(/&amp;/g, '&').replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&#39;/g, "'");
}
```

---

## Phase 2 — 模板填充

### 2.0 核心原则

**直接修改 HTML 字符串**，不走 snapshot 注入。

原因（来自附录 C.3）：v1.5 模板的 `data-snapshot` 属性只在手动导入（importCleanHTML）和版本对比（onDiffFileSelected）时被读取。页面加载时**不会自动 hydrate**。

### 2.1 注入顺序

按以下顺序操作，避免正则重叠被前面的替换破坏：

1. **标题区**：`<title>`, `nav-title`, `header-title`, `prop_name_en` / `gameplay_name_en`
2. **Header meta**：version, date, status, designer
3. **版本记录表**（version-table-body）
4. **基本信息表**：info_version, info_setting, info_region, info_level, info_name_cn, info_name_en
5. **设计概述**（rich editor 字段）
6. **白盒视角**：whitebox_p4_path
7. **Radio / Checkbox 选中状态**
8. **功能描述**（prop_function_desc / gameplay_function）
9. **Mermaid 流程图**
10. **系统需求各子字段**
11. **其他 rich editor 字段**（mission, anim, light, placement 等）
12. **图片嵌入**（参考图区域）
13. **Init script 注入**（动态模块数据：音效/配置/资产）

### 2.2 注入函数

#### 文本字段

```javascript
// data-field 容器替换（单行文本）
function replaceContentEditable(html, dataField, newContent) {
  const re = new RegExp(`(data-field="${dataField}"[^>]*>)[\\s\\S]*?(</)`, 'i');
  return html.replace(re, `$1${escapeHtml(newContent)}$2`);
}

// 可富文本 rich editor（多段落，用 <p> 包裹）
function replaceRichEditor(html, dataField, newContent) {
  const re = new RegExp(
    `(data-field="${dataField}"[^>]*>)[\\s\\S]*?(<\\/div>\\s*<\\/div>\\s*(?:<\\/div>|<h[34]))`, 'i'
  );
  const paragraphs = newContent.split('\n').filter(l => l.trim())
    .map(l => `<p>${escapeHtml(l)}</p>`).join('\n          ');
  return html.replace(re, `$1\n          ${paragraphs}\n        $2`);
}
```

#### Radio / Checkbox

```javascript
function setRadio(html, radioName, value) {
  // 先清除所有该 name 的 checked
  html = html.replace(
    new RegExp(`(name="${radioName}"\\s+value="[^"]*")(\\s+checked)?`, 'gi'),
    (m, prefix) => prefix
  );
  // 再设置目标值
  return html.replace(
    new RegExp(`(name="${radioName}"\\s+value="${escapeRegex(value)}")`),
    `$1 checked`
  );
}

function setCheckbox(html, checkboxId, checked) {
  const re = new RegExp(`(id="${checkboxId}")(\\s+checked)?`, 'i');
  return html.replace(re, checked ? `$1 checked` : `$1`);
}
```

**警告**：字符串匹配的否定前缀先检查（见附录 C.1）：
```javascript
// 正确：先检查否定形式
if (has(opts, '不可破坏')) return '不可破坏';
if (has(opts, '可破坏')) return '可破坏';
```

#### Mermaid 流程图

```javascript
// prop 模板默认是 stateDiagram-v2，gameplay 默认是 flowchart TD
// 两种都兼容替换
doc = doc.replace(
  /data-field="mermaid_flowchart">\s*(stateDiagram-v2|flowchart TD|flowchart LR)[\s\S]*?<\/div>\s*<\/div>\s*<\/div>/,
  `data-field="mermaid_flowchart">\n${mermaidCode}\n          </div>\n        </div>\n      </div>`
);
```

#### 动态模块（Init Script 注入）

配置参数、音效表、资产列表等由模板 JS 动态建，不能静态替换。在 `</body>` 前注入 `<script>`：

```javascript
const initScript = `<script>
document.addEventListener('DOMContentLoaded', function() {
  // 音效行
  var soundRows = ${JSON.stringify(soundData)};
  soundRows.forEach(function(row) { addTableRow('sfx-table-body', 9); /* 填行数据 */ });
  // 配置参数组
  // ... 调用模板的 addParamGroup() 等函数
});
</script>`;
doc = doc.replace('</body>', initScript + '\n</body>');
```

### 2.3 版本记录

每次生成必须填写：

```html
<tr>
  <td><input type="date" value="YYYY-MM-DD" ...></td>
  <td contenteditable="true">从 [源文件名] 自动生成</td>
  <td contenteditable="true">[设计师英文缩写]</td>
  <td></td>
</tr>
```

**设计师英文缩写从用户确认获取，不要假设。**

---

## Phase 3 — 验证

### 3.1 必填字段检查

生成完成后，扫描 HTML 检查以下字段是否仍为默认空值：

| 字段 | 默认空值标志 |
|---|---|
| `prop_name_cn` / `gameplay_name_cn` | `XXX物件` / `XXX玩法` |
| `prop_name_en` / `gameplay_name_en` | `Prop Name — 一句话描述` / `Gameplay Name — 一句话描述` |
| `designer` | `—` |
| `header-date` | 无 `value` 属性 |
| `prop_description` / `design_goal` | 含 `fill-placeholder` class |
| `mermaid_flowchart` | 仍为默认模板内容 |

### 3.2 缺失报告

生成后向用户汇报：
1. 哪些字段成功填充
2. 哪些字段无法从源数据推断（标注 `[待确认]`）
3. 哪些动态模块需要在浏览器中手动补填

---

## Phase 4 — 写入与展示

### 4.1 写入 docs/

```
输出路径：~/Desktop/level-design-deck/docs/{文件名}.html
```

写入后 webapp 会自动检测并在预览栏展示。

### 4.2 完成后告知用户

```
✅ 文档已生成：docs/{文件名}.html
📄 webapp 预览栏应自动打开，如未打开可点 Topbar「📄 文档模板」手动选择

⚠️ 以下字段需手动补填（在预览栏内直接点击编辑）：
- [字段列表]

💾 编辑完成后在模板内按 Ctrl+S 保存为本地工作文件
```

---

## 附录 A — Prop 模板字段 Schema

### 静态字段（直接 HTML 替换）

```
field:prop_name_cn          物件中文名
field:prop_name_en          英文名 — 一句话描述
field:version_num           v1.0
field:status                设计中
field:designer              设计师英文缩写
field:info_version          1.0版本
field:info_setting          设定描述
field:info_region           Los Angeles
field:info_level            T0 | T1 | T2 | T3
field:info_name_cn          物件中文名
field:info_name_en          物件英文名
field:whitebox_p4_path      P4路径
field:prop_description      物件描述（富文本）
field:gameplay_description  玩法描述（富文本）
field:prop_function_desc    功能描述（富文本）
field:mermaid_flowchart     Mermaid 源码
field:reward_yn             不奖励 | 奖励
field:reward_timing         奖励节点
field:map_display           — | 大地图 | 小地图 | 都显示 | 不上地图
field:map_fog               迷雾解除后显示 | 迷雾解除前显示
field:map_destroy           随物件销毁而销毁 | [自定义]
field:map_dynamic           是 | 否
field:map_priority          高 | 中 | 低
field:mission_requirement   任务需求（富文本）
field:anim_requirement      动画需求（富文本）
field:light_requirement     灯光需求（富文本）
field:placement_rules       布设规范（富文本）
```

### Radio 枚举（严格匹配）

```
radio:collision             有碰撞体 | 无碰撞体
radio:art-precision         细精度 | 一般精度
radio:interactable          可交互 | 不可交互
radio:scan-highlight        全部高亮 | 局部高亮 | 不用高亮
radio:destructible          可破坏 | 不可破坏        ← 先检否定形式
radio:movable               可移动 | 不可移动        ← 先检否定形式
radio:impulse-response      单次冲击 | 累计冲击
radio:mp-host               yes | no
radio:mp-guest              yes | no
```

### Checkbox（ID）

```
checkbox:col-no-stand       不可站立
checkbox:col-no-climb       不可攀爬
checkbox:col-see-through    视线可穿透
checkbox:col-shoot-through  可射穿（精确匹配，不能匹配到 shoot-vfx）
checkbox:col-shoot-vfx      可射穿-特效
checkbox:col-no-cover       不可作为掩体
checkbox:chk-sfx            音效需求
checkbox:chk-mission        任务需求
checkbox:chk-map            地图系统
checkbox:chk-system         系统需求
checkbox:chk-physics-destructive  可破坏物
checkbox:chk-ux             UIUX（默认勾选）
checkbox:chk-concept        概念（默认勾选）
checkbox:chk-model          模型（默认勾选）
```

### 动态模块（init script 注入，不能静态替换）

```
interact-method-body        交互方式表格行
config-form-groups          模板参数分组
config-scene-groups         动态实例参数分组
art-items-container         概念/模型需求条目
sfx-table-body              音效需求表格行
stim-items-container        刺激源列表
```

---

## 附录 B — Gameplay 模板差异

与 Prop 共用大部分字段，差异：

```
field:gameplay_name_cn      玩法中文名（代替 prop_name_cn）
field:gameplay_name_en      英文名 — 一句话描述
field:design_goal           设计目标与体验（富文本）
field:gameplay_description  玩法描述（富文本）
field:validation_items      校验项（富文本）← 填审核维度，不是真实测试点
field:flowchart_description 流程图补充说明（富文本）
field:gameplay_function     玩法功能（富文本）
```

Mermaid 默认内容不同：prop 用 `stateDiagram-v2`，gameplay 用 `flowchart TD`。替换正则兼容两种。

---

## 附录 C — 已知陷阱

### C.1 字符串匹配陷阱

`'不可破坏'.includes('可破坏')` 为 `true`。映射函数必须**先检测否定形式**：

```javascript
if (has(opts, '不可破坏')) return '不可破坏';
if (has(opts, '可破坏'))   return '可破坏';
```

同理：不可移动/可移动，不可交互/可交互。

### C.2 HTML 实体反转义

group_doc 源文件中 mermaid 箭头 `-->` 会被编码为 `--&gt;`。所有提取结果必须调用 `unescapeHtml()`，否则 mermaid 渲染失败。

### C.3 Snapshot 注入无效

v1.5 模板的 `data-snapshot` 属性只在手动导入（importCleanHTML）时被读取，页面加载时**不会自动 hydrate**。必须用直接 HTML 修改方式填充。

### C.4 动态模块的 radio name 是运行时生成的

v1.5 模板的交互属性 section（交互方式/交互朝向/重复交互等）的 radio name 格式为 `interact-type-{序号}`，由 JS 动态创建。无法通过静态 HTML 设置这些 radio 状态——需要通过 init script 在 DOM ready 后操作。
