# lib/protocol/ — LDD 协议层

> spec.json 真源生态的"动作语言" + 校验 + 派生工具集中区。
> 协议跟 CLI / 渲染 / UI / 编辑器解耦——只这一份代码是同事仓库 / 第三方 agent 消费 LDD 的接口面。

## 一句话作用

**别处（tools/ webapp/ editor/ cc-skills/）想对 spec.json 做"读 / 校 / 派生"任何操作，都来这里**。这里没有的就是没有，不在别处复刻。

---

## 为什么这个目录存在（Why this package exists）

参照同事 projectx-leveldesign 的 `packages/docs-shared/` 范式：把**协议**单独立成一等公民，跟使用者解耦。

**之前的问题**（M5.3 之前）：
- `tools/mechanical_check.py` 既是 CLI 又含 Validator 类，cc-skills 直接调 CLI
- `tools/cross_check.py` 同上 + 自己持有 `_ZONE_REF_RULES` 列表
- `tools/template_diff.py` 既是 CLI 又含 `build_diff_payload` lib API
- `tools/spec_skeleton.py` 一开始就直接写在 tools/
- `tools/_cross_check_helpers.py` 用下划线标"私有"但被 webapp/backend 越界 import
- **没有"统一协议边界"**，每个工具自己是"半 CLI 半 lib"
- 测试加在 `tools/tests/`，但被测对象散在 tools/ 各处——测试位置和协议位置错位

**M5.3 的修复**：把这 5 个文件都搬到 `lib/protocol/`，tools/ 里只留薄 CLI wrapper（如果需要的话），lib/protocol/ 里是 pure logic + 测试。

**为什么不留在 tools/**：tools/ 的语义是"可执行命令行工具"，protocol 的语义是"对 spec 进行操作的库代码"，两者性质不同。同事 docs-shared/ 也是用 `packages/` 而非 `tools/` 的语义放协议。

`[来源: 同事 docs-shared/README.md "Why this package exists"范式 + 第一原理推导]`

---

## 这里放什么

| 文件 | 作用 |
|---|---|
| `mechanical_check.py` | spec vs schema 单文件校验：Validator + SEMANTIC_CHECKS 注册表（bubble_diagram / spatial_layout）|
| `cross_check.py` | spec 间跨 module ref 校验：CrossValidator + CROSS_CHECKS 注册表（9 条规则）|
| `_cross_check_helpers.py` | cross_check 通用工具（get_spatial_labels / check_zone_field / make_zone_ref_check 工厂）|
| `template_diff.py` | spec vs work_docs / template_fields diff：build_diff_payload + SKIP_PREFIXES + SPEC_TO_WORKDOC_LIGHTING |
| `spec_skeleton.py` | spec → 统一待填清单派生：build_skeleton + collect_cross_refs + 注入 fields |

## 这里**不**放什么

- ❌ CLI argparse 主入口（留 `tools/<name>.py` 当 wrapper，import lib/protocol/ 的纯函数）
- ❌ HTML 渲染（留 `tools/render.py` `tools/render_level.py` `tools/render_deck.py`）
- ❌ 编辑器 / 前端代码（留 `editor/` `webapp/frontend/`）
- ❌ cc skill 定义（留 `cc-skills/`）
- ❌ 状态机 / 文档对话流程（违反 LDD CLAUDE.md 反污染清单）

---

## 约束（继承 LDD CLAUDE.md 第 3 节，无放宽）

- **单文件 < 300 行**
- **stdlib only**（避免公司防火墙下 pip install 麻烦）
- **fail loud**：解析/校验失败明确报错
- 不写注释，除非有非显然的"为什么"

测试在 `tools/tests/`（M5.2 已立，stdlib unittest，63 tests）。

---

## webapp/backend 怎么 import

```python
# M5.3 之前
from tools.mechanical_check import Validator
from tools.cross_check import CROSS_CHECKS, CrossValidator
from tools._cross_check_helpers import get_spatial_labels
from tools.template_diff import build_diff_payload, SKIP_PREFIXES

# M5.3 之后
from lib.protocol.mechanical_check import Validator
from lib.protocol.cross_check import CROSS_CHECKS, CrossValidator
from lib.protocol._cross_check_helpers import get_spatial_labels
from lib.protocol.template_diff import build_diff_payload, SKIP_PREFIXES
```

`apps/webapp/backend/config.py` 已经把 PROJECT_ROOT 加进 sys.path，所以 `from lib.protocol.X` 能正常工作。

---

## 跟同事 projectx-leveldesign 的关系

| 维度 | LDD `lib/protocol/` | projectx `packages/docs-shared/` |
|---|---|---|
| 语言 | Python（stdlib only）| TypeScript |
| 协议形态 | spec.json + JSON Schema 校验 + dot path | Document + JSON Schema + PathSegment + ProposalOp v2 |
| 寻址 | dot path（支持 by-id：`nodes[entry].label`）| PathSegment array（id segment `{id: 'uuid'}`）|
| 派生视图 | `spec_skeleton.py` → 多 module 统一待填清单 + cross_ref 注入 | `skeleton/compute.ts` → 单 doc skeleton + hidden_by/controls |
| 测试位置 | `tools/tests/`（unittest）| `packages/docs-shared/test/`（vitest）|

**两套独立但接口可桥接**——具体怎么桥见 `INTEGRATION_CONTRACT.md`（M5.6 产物）。

---

## 版本

- v0.1.0（2026-05-29 M5.3）：从 tools/ 搬迁 4+1 文件，README + INTEGRATION_CONTRACT.md 一起立柱
