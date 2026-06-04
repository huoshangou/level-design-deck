# Level Design Deck — spec 真源工作台
<!-- version: 0.4.0 -->

> **Quick Start:** `/design-deck [action] [args]`
> 无参数 → 向导对话；actions: `new` / `add` / `check` / `render` / `deck` / `open` / `draft`

把"AI 产 spec、Python 标问题、人定向改字段"做成一键流程。
spec.json 是真源（git 管控的纯文本），HTML 是派生（render.py 出的）。

## 输入

$ARGUMENTS

## Windows 用户

双击 `start.bat` 启动服务器（不是 start.command）。
cc skill 用 `python3` 调用工具，请确认 Python 已加入系统 PATH。

## DECK_HOME 解析

按优先级：
1. 环境变量 `LEVEL_DESIGN_DECK_HOME`
2. 默认 `~/Desktop/level-design-deck`

校验：该目录必须存在 `tools/generate_spec.py`。不存在 → 报错让用户检查 deck 是否装好。

## Server 检测

deck server 默认在 `http://127.0.0.1:8766`。每次 action 开始时 curl 检测：
- 通：继续
- 不通：提示用户先**双击 `$DECK_HOME/start.command`**（macOS）或跑 `python3 tools/serve_editor.py`，然后重试

---

## Actions

### 无参数 → 向导对话（改动 3）
[来源: Steve 直接指示（2026-05-12）+ 第一原理推导]

**不带参数时执行向导，不输出 help 文字。**

**步骤**：
1. `ls $DECK_HOME/specs/*.spec.json 2>/dev/null` 扫现有 spec 文件
2. **分支 A · 有 spec 存在**：
   - 从文件名提取所有 level_id（规则：去掉 `<module>_` 前缀，取剩余部分；如 `level_overview_abandoned_factory.spec.json` → `abandoned_factory`）
   - 去重后列出：
     ```
     已有关卡：
       1. abandoned_factory  (3 个 module)
       2. demo_warehouse     (1 个 module)
     
     继续哪个？（输入编号或 level_id）
     还是新建？（描述新关卡）
     ```
   - 用户选已有关卡 → 直接走 `add <level_id>` 向导（改动 4）
   - 用户描述新关卡 → 走分支 B 的命名确认流程
3. **分支 B · 没有 spec**：
   - 直接问："想新建什么关卡？请用一段话描述（POI 或玩法、主题、大致流程长度）"
   - 用户描述后：
     - 从描述提取关键词转 snake_case（如"废弃工厂" → `abandoned_factory`）
     - **不自动猜**，向用户确认：「命名 `abandoned_factory` 是否合适？确认后开始生成」
     - 用户确认 → 自动调用 `new <level_id> "<意图>"` 并继续

---

### `new <level_id> <意图>`

创建新关卡，从 level_overview 起步。

**步骤**：
1. 检查 `$DECK_HOME/specs/level_overview_<level_id>.spec.json` 不存在（否则提示已存在，建议 `add`）
2. 跑 `cd $DECK_HOME && python3 tools/generate_spec.py --module level_overview --intent "<意图>"`
3. 看 stdout 输出的 self-contained prompt → **按 prompt 内化执行** → 产 level_overview spec JSON
4. 用 Write 工具写到 `$DECK_HOME/specs/level_overview_<level_id>.spec.json`
5. 跑 `python3 lib/protocol/mechanical_check.py specs/level_overview_<level_id>.spec.json schema/level_overview.schema.json --quiet`
6. 0 ERROR → **自动打开 editor**（改动 1）：
   `python3 -c "import webbrowser; webbrowser.open('http://127.0.0.1:8766/editor/editor.html?spec=level_overview_<level_id>')"`
7. 打开后 print：
   ```
   ✓ level_overview_<level_id> 已生成，editor 已打开。
   
   下一步建议：/design-deck add <level_id>（自动推荐下一个 module）
   或指定：
     /design-deck add <level_id> spatial_layout      # 用 LevelCraft 编辑布局后导入
     /design-deck add <level_id> bubble_diagram <意图>
     /design-deck add <level_id> lighting_req <意图>
     /design-deck add <level_id> atmosphere_ref <意图>
     /design-deck add <level_id> vfx_req <意图>
     /design-deck add <level_id> audio_req <意图>
     /design-deck add <level_id> asset_list <意图>
     /design-deck add <level_id> storyboard <意图>      # M4.1：img2img 分镜 prompt 生产
   ```
[来源: Steve 直接指示（2026-05-12）]

---

### `add <level_id> [module] [意图]`

给现有关卡加一个 module 的 spec。

**已支持 module**：`level_overview / spatial_layout / bubble_diagram / storyboard / atmosphere_ref / lighting_req / vfx_req / audio_req / asset_list`

**module 推荐顺序（改动 4）**：
[来源: 第一原理推导]
```
level_overview → spatial_layout → bubble_diagram → storyboard → atmosphere_ref
              → lighting_req → vfx_req → audio_req → asset_list
```
理由：spatial_layout 最先因为后续 module（lighting_req / atmosphere_ref / vfx_req / audio_req / asset_list / storyboard）的 cross_check 都依赖它的 zone label；bubble_diagram 表达流程主线必须早于 storyboard（storyboard.panels[].beat_id 引用它）；storyboard 是流程的画面化投影，自然紧随 bubble_diagram。

**不传 module 时 → 自动推下一个（改动 4）**：
1. `ls $DECK_HOME/specs/<module>_<level_id>.spec.json` 检查每个 module 是否已做
2. 按顺序找第一个未做的 module
3. 给用户 1-2 句解释为什么推荐这个 module：
   ```
   推荐下一个：spatial_layout
   理由：后续 5 个 module 的 cross_check 都要对照它的 zone label，优先建立空间骨架。
   
   [继续这个] [跳过，下一个] [指定其他 module]
   ```
4. 用户选 [继续这个] 或直接回车 → 走对应 module 流程
5. 用户选 [跳过] → 推第二个未做的 module
6. 用户选 [指定其他 module] → 提示输入 module 名

**特例**：`spatial_layout` 不能 LLM 生成（数据来自 LevelCraft 2D 工具）。提示用户：
1. 浏览器打开 `http://127.0.0.1:8766/tools/levelcraft/editor.html` 编辑布局
2. 编辑完导出 JSON
3. 通过 `/design-deck open <level_id>` 后在 editor 用 [📥 Import JSON] 按钮闭环

**生成步骤（非 spatial_layout）**：
0. **先读 spec_skeleton 了解关卡现状（M5.1 新加）**：
   `python3 lib/protocol/spec_skeleton.py --level-id <level_id> --markdown 2>/dev/null || echo "首个 module，无现存 spec"`
   - 目的：cc 看清已有哪些 module / 哪些 zone label 可被引用 / 哪些 cross_ref 已建立。**不看就动手 = 漏字段 / 编错 zone_id 的常见原因**
   - 注意：spec_skeleton 输出 ≠ doc_skeleton（doc_skeleton 看 HTML 文档；spec_skeleton 看 spec.json + 跨 module 状态）
1. 检查目标 spec 不存在（如已存在，建议用 editor 改字段或调 `regenerate_field.py`）
2. 跑 `cd $DECK_HOME && python3 tools/generate_spec.py --module <module> --intent "<意图>"`
3. 内化执行 prompt → 产 spec → Write 到 `$DECK_HOME/specs/<module>_<level_id>.spec.json`
4. 跑 `python3 lib/protocol/mechanical_check.py specs/<module>_<level_id>.spec.json schema/<module>.schema.json --quiet`
5. **如果该 module 有 zone ref**（lighting_req / atmosphere_ref / vfx_req / audio_req / asset_list）：
   - 跑 `python3 lib/protocol/cross_check.py --level-id <level_id>`
   - **有 ERROR**（改动 2）：
     - Print 错误信息
     - **自动打开 editor 跳到出错 spec**：
       `python3 -c "import webbrowser; webbrowser.open('http://127.0.0.1:8766/editor/editor.html?spec=<module>_<level_id>')"`
     - Print：「⚠️ cross_check ERROR：<错误信息>。editor 已打开，请在 zone_id 字段改成 spatial label 里有的值。」
   - **0 ERROR**：按下方正常完成流程走（改动 1 + 2）：
     `python3 -c "import webbrowser; webbrowser.open('http://127.0.0.1:8766/editor/editor.html?spec=<module>_<level_id>')"`
6. Print 完成引导（改动 5）：按 module 查 lookup 表（见下方）
[来源: Steve 直接指示（2026-05-12）]

**完成引导 lookup 表（改动 5）**：
[来源: 第一原理推导]

| module | 完成后 print |
|---|---|
| `level_overview` | 看 `intent` 是否一句话说清主题 / 看 `level_type` 是否准确选了 POI 或玩法 |
| `spatial_layout` | 看 layer/shape 数是否合理 / 看 label coverage 是否覆盖关键区域（editor 左栏告警会标 label_missing） |
| `bubble_diagram` | 看 Mermaid 节点连线是否合理 / Phase 分组是否到位 / 入口出口是否各一 |
| `atmosphere_ref` | 看 `image_url` 是否填了真图（PoC 期可暂留 [待对接]）/ 看 zones 是否覆盖关键区域 |
| `lighting_req` | 看 `ambience_refs` 的 `region_id` 是否对应 spatial label / 看 `description` 语气是否到位（不是列参数，是设计意图） |
| `vfx_req` | 看效果描述是否专业到能给制作组用 / 看 `zone_id` 是否命中 spatial label |
| `audio_req` | 看效果描述是否专业到能给制作组用 / 看 `zone_id` 是否命中 spatial label |
| `asset_list` | asset_id 是否都是 `[待对接]`——绝对禁止编伪接口名（如 model_xxx_001） |

---

### `check <level_id>`

跑全套校验。

**步骤**：
1. `ls $DECK_HOME/specs/` 找该 level_id 所有 spec（匹配 `*_<level_id>.spec.json`）
2. 对每个 spec 跑 `python3 lib/protocol/mechanical_check.py specs/<...> schema/<module>.schema.json`
3. 跑 `python3 lib/protocol/cross_check.py --level-id <level_id>`
4. 跑 `python3 lib/protocol/spec_skeleton.py --level-id <level_id> --markdown`（M5.1 新加：跨 module 填空进度 + cross_ref 健康度一次看全）
5. 汇总：errors / reviews 数 + 详细列表 + skeleton 摘要（modules_present / fields_pending / cross_refs_broken）

---

### `render <level_id>`

渲染完整关卡文档（可滚动长文档版）。

**步骤**：
1. 跑 `cd $DECK_HOME && python3 tools/render_level.py --level-id <level_id> --render-missing`
2. 自动打开：`python3 -c "import webbrowser; webbrowser.open('http://127.0.0.1:8766/outputs/level_<level_id>__full.html')"`
3. Print URL 方便用户复制
4. Print 快捷提示：
   ```
   ✓ 完整文档已打开。
   快捷操作：/design-deck deck <level_id>  # 生成汇报用横向翻页 Slide Deck
   ```

---

### `draft <level_id> [设计文字]`

从设计对话产出完整关卡 spec 雏形。支持两种模式自动切换。
[来源: Steve 直接指示（2026-05-13）]

**模式检测**：
- 只传 `level_id` → **引导式（B 模式）**：逐步提问 7 个关卡设计核心维度
- 同时传入大段文字（> 200 字）→ **倾倒式（A 模式）**：从文字中提取设计信息

**随时可以倾倒信息（B 模式中也适用）**：
在引导式问答的任意环节，用户都可以贴入大段文字（白盒草稿、cc 对话摘要、设计意图段落等）。
检测到 > 200 字的输入时：
1. spawn 一个 subagent（Sonnet 或 Haiku）专门处理这段文字，提取 7 个维度的设计信息
2. 将提取结果合并进已有回答
3. 对尚未覆盖的维度补问（不重复已答维度）
4. 继续走生成流程

**前置检查**：
- 若 `specs/level_overview_<level_id>.spec.json` 已存在 → 提示已有关卡，确认是否覆盖
- Server 检测（同其他 action）

---

#### B 模式 · 引导式（7 步对话）

**每次只问一个问题，等用户回答后再问下一个。不要一次性抛出所有问题。**

| # | 问题 | 映射目标 |
|---|---|---|
| 1 | 「这个关卡给玩家的**核心体验**是什么？一句话（玩家要做什么、感受什么）」 | level_overview · intent |
| 2 | 「关卡的**主要矛盾或挑战**是什么？玩家需要克服的核心障碍？」 | level_overview · main_gameplay |
| 3 | 「有哪几个**关键区域**？空间关系是线性 / HUB / 开放？（列区域名，不用精确）」 | atmosphere_ref.zones · lighting_req 区域骨架 |
| 4 | 「大致分**几个阶段**？关键转折点是什么？（如：侦查→接触→Boss→撤退）」 | bubble_diagram 节点骨架 |
| 5 | 「**时间段 / 天气 / 氛围关键词**？（3-5 个，如：夜间、冷月光、压抑、高反差剪影）」 | atmosphere_ref · lighting_req |
| 6 | 「有哪些**关键 NPC 或道具机制**？」 | level_overview · key_npcs / key_items |
| 7 | 「有什么**设计约束或重点资产**需要注意？」 | level_overview · asset_list 雏形 |

全部回答后，打印摘要请用户确认，再生成。

---

#### A 模式 · 倾倒式（文字提取）

用户提供的文字可能是：与 cc 的对话摘要、白盒设计草稿、设计意图段落等。

1. 从文字中提取上表 7 个维度信息（信息不足时用 `[待补充]` 占位）
2. 列出提取结果，让用户确认或修正
3. 用户确认后走「生成 spec 雏形」步骤

---

#### 生成 spec 雏形（B / A 共用出口）

读 `$DECK_HOME/schema/` 各模块的 schema.json，按收集到的设计信息生成：

| Spec | 完整度 | 生成策略 |
|---|---|---|
| `level_overview` | 🟢 较完整 | 从问题 1/2/5/6/7 填充全部字段 |
| `bubble_diagram` | 🟡 骨架 | 从问题 4 提取 phase + 主要节点，边用 sequential |
| `atmosphere_ref` | 🟡 骨架 | overall 从问题 5 填，zones 从问题 3 生成空壳 |
| `lighting_req` | 🔴 stub | meta + context，ambience_refs 按区域列表建空壳 |
| `vfx_req` | 🔴 stub | meta + context |
| `audio_req` | 🔴 stub | meta + context |
| `asset_list` | 🔴 stub | meta + context，从问题 6/7 提取关键资产（asset_id 全部 `[待对接]`） |

`spatial_layout` 跳过（必须用 LevelCraft 工具导入）。

**生成后**：
1. Write 工具写入 `$DECK_HOME/specs/`
2. 对每个 spec 跑 `mechanical_check.py`
3. 打印汇总：
   ```
   ✓ 已生成 7 个 spec 雏形（spatial_layout 待手动导入）

     level_overview  🟢  0 ERROR · 0 REVIEW
     bubble_diagram  🟡  0 ERROR · N REVIEW（预期）
     atmosphere_ref  🟡  0 ERROR · N REVIEW
     lighting_req    🔴  待填（stub）
     vfx_req         🔴  待填（stub）
     audio_req       🔴  待填（stub）
     asset_list      🔴  待填（stub）

   下一步：
     /design-deck open <level_id>              # editor 里补字段
     /design-deck add <level_id> spatial_layout # LevelCraft 建空间骨架
     /design-deck check <level_id>              # 全量校验
     /design-deck deck <level_id>               # 汇报 Slide Deck
   ```
[来源: Steve 直接指示（2026-05-13）+ work_docs_extract.json + 第一原理推导]

---

### `deck <level_id>`

生成汇报用横向翻页 Slide Deck 并打开。
[来源: Steve 直接指示（2026-05-12）]

**结构**：Cover（关卡名 + 意图摘要）→ 8 个 module slide（iframe 隔离，浅色沙丘主题）→ Coda。
**视觉**：WebGL 双背景（深色页全息色散 / 浅色页银色珍珠）+ Playfair Display + Noto Serif SC。

**步骤**：
1. Server 检测（同其他 action）
2. 跑 `cd $DECK_HOME && python3 tools/render_deck.py --level-id <level_id>`
3. 自动打开：`python3 -c "import webbrowser; webbrowser.open('http://127.0.0.1:8766/outputs/level_<level_id>__deck.html')"`
4. Print：
   ```
   ✓ Slide Deck 已打开（<N> 张 slide）
   
   快捷键：← → 翻页  ·  ESC 预览所有 slide  ·  F 全屏
   点击右半屏 → 下一页，左半屏 → 上一页
   ```

**输出 spec 不全时**：缺少某些 module 的 HTML 会跳过对应 slide，不报错。
Print 警告：「⚠️ 以下 module 暂无渲染产物，slide 中已跳过：<module 列表>。可先跑 /design-deck render <level_id> 补齐。」

---

### `open <level_id> [module]`

浏览器打开 editor。

**步骤**：
1. 不传 module：默认开 `level_overview_<level_id>`（如不存在则 ls 任选一个该 level 的 spec）
2. 传 module：拼出 `<module>_<level_id>`
3. `python3 -c "import webbrowser; webbrowser.open('http://127.0.0.1:8766/editor/editor.html?spec=<spec_id>')"`

---

## 反污染（来自 deck CLAUDE.md）

执行任何 action 时**禁止**：
- 引用 pipeline 路径 / 旧 module 名（字段按 deck schema，不抄 pipeline）
- 套用 manifest / scorer / HITL 三段术语
- 凭空臆造 schema 没声明的字段
- 给对方资产编伪接口名（asset_id 一律 `[待对接]`）

字段决策来源标签：
`[来源: schema]` / `[来源: work_docs]` / `[来源: Steve 直接指示（YYYY-MM-DD）]` / `[来源: 第一原理推导]`

## 职责边界（2026-06-03 新增）

**你的职责是 spec 内容层**。你是关卡 spec 的生成者和编辑者，不是工具链的维护者。

**发现 prompt 有问题（重复/结构不对/生图效果差）时**：
- ✅ 修改 spec 字段内容（改 panel.scene 去掉重复描述、改 world_anchor 字段措辞、改 style_anchor 参数）
- ✅ 报告问题给 LD："这个 prompt 有重复，建议修改 panel.scene 去掉 world_anchor 已覆盖的内容"
- ❌ 不要诊断 `tools/*.py` 代码逻辑
- ❌ 不要建议修改 PromptComposer / prompt_sanitizer / render.py 的代码
- ❌ 不要建议修改 schema.json 的字段定义
- ❌ 不要提出代码层面的 bug 修复方案

**生成 storyboard panel.scene 时**：
- panel.scene 只写本帧增量——world_anchor 的 venue_type / material / atmosphere 会被 PromptComposer 自动注入，panel.scene 不要重复这些内容
- panel.shot_size / composition / camera_technique 是独立字段，不要塞到 scene 里

代码问题由 Steve 通过 CC CLI 处理，不是你的职责。

---

## 安装

```bash
mkdir -p ~/.claude/commands
cp ~/Desktop/level-design-deck/cc-skills/design-deck.md ~/.claude/commands/
```

如果 deck 不在默认路径：

```bash
export LEVEL_DESIGN_DECK_HOME=/path/to/your/level-design-deck
```

放进 `~/.zshrc` 或 `~/.bashrc` 持久化。

---

## 流程示例（同事完整使用）

```
> /design-deck
  没有已有关卡。
  想新建什么关卡？请用一段话描述（POI 或玩法、主题、大致流程长度）

> 山中废弃工厂潜入 POI，主角夜间寻找线索，避免正面交战
  命名 `abandoned_factory` 是否合适？

> 是
  → 自动执行 new abandoned_factory "山中废弃工厂潜入..."
  ✓ level_overview_abandoned_factory 已生成，editor 已打开。

> /design-deck add abandoned_factory
  推荐下一个：spatial_layout
  理由：后续 5 个 module 的 cross_check 都依赖它的 zone label，优先建立空间骨架。
  [继续这个] [跳过，下一个] [指定其他 module]

> 继续这个
  ⚠️ spatial_layout 不支持 LLM 生成。请用 LevelCraft 编辑布局后导入。

> /design-deck add abandoned_factory bubble_diagram 主动线5节点，潜入→对峙→取证→撤退
  ✓ bubble_diagram_abandoned_factory 已生成 (0 ERROR)，editor 已打开。
  → 看 Mermaid 节点连线是否合理 / Phase 分组是否到位

> /design-deck add abandoned_factory lighting_req 夜间冷白光为主...
  ⚠️ cross_check ERROR: ambience_refs[2].region_id "控制室" 不在 spatial labels 里
  editor 已打开，请在 region_id 字段改成正确的 spatial label。

> /design-deck check abandoned_factory
  ✓ 8 specs · 0 ERROR · 3 REVIEW (label_missing 预期)

> /design-deck render abandoned_factory
  ✓ 完整文档已打开：http://127.0.0.1:8766/outputs/level_abandoned_factory__full.html
  快捷操作：/design-deck deck abandoned_factory  # 生成汇报用横向翻页 Slide Deck

> /design-deck deck abandoned_factory
  ✓ Slide Deck 已打开（10 张 slide）
  快捷键：← → 翻页 · ESC 预览所有 slide · F 全屏
```
