"""parsers/test 引导 —— 让本目录测试可单文件裸跑。

本目录**不在** ``eosop_pro/test/`` 之下，故主测试体系的 ``import _runner``
机制不可直接用；此处把四层路径注入 ``sys.path``（幂等）：

1. ``parsers/test/`` 本目录（import _bootstrap / _common）
2. ``eosop_pro/test/``（复用零依赖运行器 ``_runner`` 与 ``eosopdata._samples``）
3. ``eosop_pro/``（包根，辅助定位）
4. ``gen_eos_op/``（使 ``import eosop_pro`` 生效）

用法：测试文件头两行固定为::

    import _bootstrap           # noqa: F401
    import _runner              # noqa: F401
    from _runner import expect, expect_eq, main
"""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))          # .../eosop_pro/parsers/test
_PKG = os.path.dirname(os.path.dirname(_HERE))              # .../eosop_pro（包根）
_TEST = os.path.join(_PKG, "test")                          # .../eosop_pro/test（复用 _runner/_samples）
_PARENT = os.path.dirname(_PKG)                             # .../gen_eos_op（使 import eosop_pro 生效）

for _p in (_HERE, _TEST, _PKG, _PARENT):
    if _p not in sys.path:
        sys.path.insert(0, _p)
