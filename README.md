# level-design-deck

**spec 真源 + schema-driven 编辑 + 机械校验**的关卡设计工作台。

![version](https://img.shields.io/badge/version-0.1.0-blue) ![status](https://img.shields.io/badge/status-PoC-orange)

---

## 演示视频

<video src="https://github.com/huoshangou/level-design-deck/raw/main/outputs/tutorial-video.mp4" controls width="100%"></video>

> 无法内嵌播放？[点此直接下载 MP4](https://github.com/huoshangou/level-design-deck/raw/main/outputs/tutorial-video.mp4)（5.5 MB，102 秒）

---

## 是什么 / 不是什么

**是**：

- `spec.json` 是 git 管控的数据真源，HTML 是固定模板派生的渲染产物
- schema-driven 编辑器：表单由 JSON Schema 自动生成，加字段先改 schema
- 机械检测优先：Python 跑强/中/弱三档检查，挑出占位符/类型越界/跨 module 引用断链
- 跨 module 联动校验：同一关卡的多份 spec 之间做 cross_check，word/wiki 做不到这件事
- 轻便、单文件、离线可用，无 build step

**不是**：

- 富文本编辑器（spec 是结构化 JSON，不允许格式自由）
- 文档生成器（HTML 只是渲染产物，不是交付物）
- 重型管线（没有 manifest / 状态机 / 多人协作 / 打分机制）
- 公司 wiki 或知识库（不做搜索/权限/版本管理）

---

## 核心理念

1. **`spec.json` 是真源、HTML 是派生** — 一旦反过来，整个项目失败
2. **schema 改了字段才存在** — AI 不能凭空加字段，想加先改 schema
3. **机械检测 > AI confidence** — Python 报错是硬约束，AI 自评只配做 hint
4. **template 是 checklist，不是模板** — 只用提取出的字段清单做 diff，原文件不读

---

## Quickstart

**系统要求**：Python 3.8+，macOS / Windows / Linux，不需要 npm/pip install

```bash
git clone https://github.com/huoshangou/level-design-deck.git
cd level-design-deck
```

**启动编辑器**：

**macOS**：双击 `start.command`（自动启 server + 打开浏览器）

**Windows**：双击 `start.bat`（同样自动启 server + 打开浏览器）

或手动跑（任意系统）：

```bash
python3 tools/serve_editor.py --port 8766
# 浏览器开 http://127.0.0.1:8766/editor/editor.html
```

**（可选）安装 Claude Code skill**：

```bash
mkdir -p ~/.claude/commands
cp cc-skills/design-deck.md ~/.claude/commands/
```

**（M4 进阶）Web UI + Daemon**：在原 editor 之上新增一层 FastAPI 后端 + React/Vite 前端 + 浏览器内对话生成 spec（可拖文件给 cc 当参考资料）。详见 [webapp/README.md](webapp/README.md)。原 editor 仍可用 — webapp 起来后访问 `http://127.0.0.1:8766/legacy/editor.html`。

---

## 典型工作流

### 从零开始设计一个关卡

```
/design-deck draft my_poi
```

skill 会逐步提问 7 个关卡设计核心维度（核心体验 → 主要矛盾 → 空间区域 → 流程节拍 → 氛围 → 关键角色 → 设计约束），**任意时刻都可以直接贴入大段设计草稿**，skill 自动提取并合并。

回答完成后，一次性产出 7 个 spec 雏形（`level_overview` 较完整，`bubble_diagram` / `atmosphere_ref` 骨架，其余 stub），并跑机械校验标出缺口。

```
/design-deck add my_poi spatial_layout   # 用 LevelCraft 2D 工具建空间骨架
/design-deck open my_poi                 # 在 editor 里补字段、审阅告警
/design-deck check my_poi               # 全量校验（7 条 cross_check 规则）
/design-deck render my_poi              # 生成完整关卡长文档
/design-deck deck my_poi                # 生成汇报用横向翻页 Slide Deck
```

### 已有设计思路，直接倒入

```
/design-deck draft my_poi 这是一个夜间潜入任务，主角需要... (大段文字)
```

skill 检测到长文本，spawn subagent 提取设计维度，跳过对应问题，直接生成。

---

## 8 个 Module

| module | 定位 |
|---|---|
| `level_overview` | 关卡 README，同 level 所有 module 的 hub，level_id 真源 |
| `spatial_layout` | 空间布局，接 LevelCraft 2D 工具导出 JSON，渲染 2D/3D 区域图 |
| `bubble_diagram` | 流程图，节点+边描述关卡动线，支持 HUB 结构、分支、回流 |
| `lighting_req` | 灯光需求，颜色/强度/氛围光分区描述，POI 专用 |
| `atmosphere_ref` | 氛围参考，图片墙+关键词+区域氛围描述 |
| `vfx_req` | 视觉特效需求，环境/互动/叙事类特效分区描述 |
| `audio_req` | 音频需求，环境音/场景音乐/互动音效分区描述 |
| `asset_list` | 资产对接清单，给制作团队的资产类别/区域/状态表 |

---

## 架构

```
设计师 ↔ Claude 对话
        │
        ▼
  generate_spec.py  ──────────→  spec.json (真源，git 管控)
        │                              │
        │                    mechanical_check.py
        │                    cross_check.py
        │                              │
        │                         告警列表
        │                              │
        ▼                              ▼
  editor.html (schema-driven UI)  ←──  serve_editor.py
        │
        ▼
    render.py  ───────────→  outputs/*.html (派生)
        │
        ▼
  render_level.py  ─────→  outputs/level_<id>__full.html
                                    (完整关卡文档)
```

spec 只走一个方向：对话 → JSON → HTML。HTML 永远不反向影响 spec。

---

## 设计哲学

**spec 真源**：设计数据存成机器可读的 JSON，而不是 word 段落。AI 改字段，git 记历史，Python 跑检查，三件事互不干扰。

**schema-driven UI**：编辑器表单由 JSON Schema 自动生成。加一个字段只需改 schema，编辑器自动跟上。不手写 HTML 表单。

**机械检测优先**：LLM 自评校准差。Python 脚本跑占位符检测/引用完整性/类型越界，是可重现、可自动化的约束。AI 自评只是 hint。

**跨 module cross_check（B 阶段亮点）**：同一关卡下，`lighting_req` 里的 region_id 必须命中 `spatial_layout` 里的 shape label。`atmosphere_ref`、`vfx_req`、`audio_req`、`asset_list` 里的 zone_id 同理。这种跨文件一致性校验是 word/wiki 完全做不到的。

---

## 不做什么

- 不做富文本编辑（保 spec 纯净）
- 不做 UI 美化（先验证流程通不通）
- 不做团队权限/多人协作（PoC 期单人）
- 不做版本管理（用 git 就行）
- 不做 manifest/状态机（违背"轻便"原则）
- 不做打分机制（方向是机械检测，不是分数）
- 不做插件系统/主题切换

---

## 致谢 / Attribution

**layoutTools 编辑器**：本仓库 `tools/levelcraft/` 包含 LevelCraft 2D 编辑器 bundle，归原作者所有。已征得使用许可，原工具链接🔗https://www.bilibili.com/video/BV1PrD9BQEo3?buvid=YE42B9E3D53802F14A40AFC21B21359649A4&is_story_h5=false&mid=brROephpd%2B6l7LdnRGTNXQ%3D%3D&p=1&plat_id=168&share_from=ugc&share_medium=iphone&share_plat=ios&share_session_id=5D407EC0-51B9-4407-99C3-349024AAA5F8&share_source=WEIXIN&share_tag=s_i&spmid=main.my-history-search-result.option-more.0&timestamp=1778564824&unique_k=LLuBSPE&up_id=10154071

**Mermaid**：`lib/mermaid.min.js` 使用 [Mermaid](https://github.com/mermaid-js/mermaid)，MIT License。

**Slide Deck 视觉系统**：`tools/render_deck.py` 生成的汇报 Slide Deck，视觉风格参考自 [guizang-ppt-skill](https://github.com/op7418/guizang-ppt-skill)（op7418），包括 WebGL 双背景着色器、沙丘配色方案（`--ink:#1f1a14 / --paper:#f0e6d2`）及 Playfair Display + Noto Serif SC + IBM Plex Mono 字体系统。

---

## 路线图

| 里程碑 | 状态 | 内容 |
|---|---|---|
| M0 | 完成 | 项目骨架、反污染规则、template 字段提取 |
| M1 | 完成 | lighting_req 端到端：schema + editor + 机械检测 + 渲染 |
| M2 | 完成 | AI 生成工具（generate_spec.py / regenerate_field.py，只产 prompt 不调 LLM） |
| M3 | 完成 | 8 个 module 全部落地 + 跨 module cross_check + LevelCraft 集成 + cc skill + Mermaid 本地化 |
| 未来方向 | 待定 | app 壳（Tauri/Electron/内网部署）让不会 cc 的设计师直接用；MCP server 升级 skill 到产品形态 |

