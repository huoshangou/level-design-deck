# tools/tests — 协议层测试

> stdlib `unittest`，零依赖；遵守 LDD CLAUDE.md "优先标准库"约束。
> pytest **仅** webapp/ 用，tools/ 不引。

## 跑测试

```bash
cd ~/Desktop/level-design-deck

# 跑全部
python3 -m unittest discover -s tools/tests -p 'test_*.py' -v

# 跑单个文件
python3 -m unittest tools.tests.test_mechanical_check -v

# 跑单个方法
python3 -m unittest tools.tests.test_mechanical_check.TestRequired.test_required_missing -v
```

## 覆盖范围（M5.2）

| 文件 | 覆盖 |
|---|---|
| `test_mechanical_check.py` | required / type / enum / pattern / minLength / additionalProperties / placeholder / caveat / SEMANTIC bubble + spatial |
| `test_cross_check.py` | 7 条规则 cross_ref_integrity / phase_summary 等 |
| `test_template_diff.py` | mapped / missing / extra / SKIP_PREFIXES |
| `test_spec_skeleton.py` | iter_fields / classify / cross_ref 注入 / 真实 abandoned_temple 端到端 |

## 写新测试约定

- 文件命名 `test_<被测模块>.py`
- 顶部 `from tools.tests._common import *`（自动 setup sys.path）
- 被测对象从 `lib.protocol.*` import（M5.3 后协议层搬到那里；tests 留 tools/tests/ 不动）
- 用 `unittest.TestCase` 子类，方法名 `test_*`
- 用 inline dict / JSON 构造测试 fixture，**不**依赖 specs/ 真实文件（端到端测试除外）
- assertion 用 `self.assertEqual / assertTrue / assertIn` 风格

## 为什么不用 pytest

LDD CLAUDE.md 第 3 节 "Python 工具优先标准库"硬约束 + 红线 5 "webapp/ 外不引入新依赖"。pytest 已在 `webapp/wheels/` 但仅 webapp/ 例外可用；tools/ 严守 stdlib。

unittest 写起来比 pytest 啰嗦，但零依赖、零环境配置、跨 Python 版本稳。`[来源: CLAUDE.md 第 3 节 + 红线 5]`
