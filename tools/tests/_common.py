"""tools/tests 通用 setup —— 把 PROJECT_ROOT 加到 sys.path，让测试能 `from lib.protocol.* import`。

每个 test_*.py 顶部 `from tools.tests._common import *` 即可触发。
M5.3 后协议层搬到 lib/protocol/，被测对象都从那里 import；tests 留 tools/tests/ 不动。
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

SCHEMA_DIR = PROJECT_ROOT / "schema"
SPECS_DIR = PROJECT_ROOT / "specs"
