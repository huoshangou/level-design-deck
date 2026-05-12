# Level Design Deck — spec 真源工作台
<!-- version: 0.1.0 -->

> **Quick Start:** `/design-deck <action> [args]` · actions: `new` / `add` / `check` / `render` / `open` / `help`

把"AI 产 spec、Python 标问题、人定向改字段"做成一键流程。
spec.json 是真源（git 管控的纯文本），HTML 是派生（render.py 出的）。

## 输入

$ARGUMENTS

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

### `new <level_id> <意图>`

创建新关卡，从 level_overview 起步。

**步骤**：
1. 检查 `$DECK_HOME/specs/level_overview_<level_id>.spec.json` 不存在（否则提示已存在，建议 `add`）
2. 跑 `cd $DECK_HOME && python3 tools/generate_spec.py --module level_overview --intent "<意图>"`
3. 看 stdout 输出的 self-contained prompt → **按 prompt 内化执行** → 产 level_overview spec JSON
4. 用 Write 工具写到 `$DECK_HOME/specs/level_overview_<level_id>.spec.json`
5. 跑 `python3 tools/mechanical_check.py specs/<...> schema/level_overview.schema.json --quiet`
6. 0 ERROR → 提示用户：
   ```
   ✓ level_overview 已生成。下一步：
     /design-deck add <level_id> spatial_layout      # 用 LevelCraft 编辑布局后导入
     /design-deck add <level_id> bubble_diagram <意图> # 流程图
     /design-deck add <level_id> lighting_req <意图>   # 灯光
     /design-deck add <level_id> atmosphere_ref <意图> # 氛围
     /design-deck add <level_id> vfx_req <意图>        # 视觉特效
     /design-deck add <level_id> audio_req <意图>      # 音频
     /design-deck add <level_id> asset_list <意图>     # 资产
     /design-deck open <level_id>                     # 浏览器看
     /design-deck render <level_id>                   # 出完整文档
   ```

### `add <level_id> <module> [意图]`

给现有关卡加一个 module 的 spec。

**已支持 module**：`level_overview / lighting_req / bubble_diagram / atmosphere_ref / vfx_req / audio_req / asset_list`

**特例**：`spatial_layout` 不能 LLM 生成（数据来自 LevelCraft 2D 工具）。提示用户：
1. 浏览器打开 `http://127.0.0.1:8766/tools/levelcraft/editor.html` 编辑布局
2. 编辑完导出 JSON
3. 手动包装成 spec（meta + context + layout）写到 `specs/spatial_layout_<level_id>.spec.json`
4. 或者通过 `/design-deck open <level_id>` 后在 editor 用 [📥 Import JSON] 按钮闭环

**步骤**：
1. 检查目标 spec 不存在（如已存在，建议用 editor 改字段或调 `regenerate_field.py`）
2. 跑 `cd $DECK_HOME && python3 tools/generate_spec.py --module <module> --intent "<意图>"`
3. 内化执行 prompt → 产 spec → Write → mechanical_check
4. **如果该 module 有 zone ref**（lighting_req / atmosphere_ref / vfx_req / audio_req / asset_list）：
   - 跑 `python3 tools/cross_check.py --level-id <level_id>` 看 cross_ref_integrity
   - 如果 ERROR：提示用户改 zone_id 字段命中真实 spatial label

### `check <level_id>`

跑全套校验。

**步骤**：
1. ls `$DECK_HOME/specs/` 找该 level_id 所有 spec
2. 对每个 spec 跑 mechanical_check
3. 跑 cross_check --level-id <level_id>
4. 汇总：errors / reviews 数 + 详细列表

### `render <level_id>`

渲染完整关卡文档。

**步骤**：
1. 跑 `cd $DECK_HOME && python3 tools/render_level.py --level-id <level_id> --render-missing`
2. 给用户 URL：`http://127.0.0.1:8766/outputs/level_<level_id>__full.html`

### `open <level_id> [module]`

浏览器打开 editor。

**步骤**：
1. 不传 module：默认开 `level_overview_<level_id>`（如不存在则任选一个 spec）
2. 用 `open` 命令打开 `http://127.0.0.1:8766/editor/editor.html?spec=<spec_id>`

### `help`

列出 deck 当前所有 module + 已存在 spec 的概览。

```bash
python3 $DECK_HOME/tools/generate_spec.py --list-modules
ls $DECK_HOME/specs/
```

---

## 反污染（来自 deck CLAUDE.md）

执行任何 action 时**禁止**：
- 引用 pipeline 路径 / 旧 module 名（vfx_req 字段名按 deck schema，不抄 pipeline）
- 套用 manifest / scorer / HITL 三段术语
- 凭空臆造 schema 没声明的字段
- 给对方资产编伪接口名（asset_id 一律 `[待对接]`）

字段决策来源标签：
`[来源: schema]` / `[来源: work_docs]` / `[来源: Steve 直接指示（YYYY-MM-DD）]` / `[来源: 第一原理推导]`

---

## 安装

复制此文件到 cc 用户级 commands 目录：

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
> /design-deck new gangster_mansion 黑帮大宅潜入POI，主角夜间营救记者，避免正面交战

  ✓ level_overview_gangster_mansion 已生成 (0 ERROR)

> /design-deck add gangster_mansion bubble_diagram 主动线5节点，潜入→对峙→营救→撤退

  ✓ bubble_diagram_gangster_mansion 已生成 (0 ERROR)
    cross_check 跳过（无 spatial_layout 引用）

> /design-deck add gangster_mansion spatial_layout

  ⚠️ spatial_layout 不支持 LLM 生成。请：
     1. 浏览器开 http://127.0.0.1:8766/tools/levelcraft/editor.html 编辑布局
     2. /design-deck open gangster_mansion 后用 [📥 Import JSON] 按钮闭环

> /design-deck add gangster_mansion lighting_req 夜间冷月光为主...

  ✓ lighting_req_gangster_mansion 已生成
    ⚠️ cross_check ERROR: ambience_refs[2].region_id "鬼屋" 不在 spatial labels 里
    建议：改成 "玄关" / "礼佛堂" / etc，或在 editor 中编辑

> /design-deck open gangster_mansion lighting_req
  → 浏览器开 editor，改 region_id

> /design-deck check gangster_mansion
  ✓ 8 specs · 0 ERROR · 3 REVIEW (label_missing 预期)

> /design-deck render gangster_mansion
  ✓ 完整文档：http://127.0.0.1:8766/outputs/level_gangster_mansion__full.html
```
