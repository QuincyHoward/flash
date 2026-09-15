"""Core 测试子包。

包含: test_anchors.py, test_annotations.py, test_byteclass.py, test_fixedwidth.py, test_fortran_numbers.py, test_inference.py, test_textio_encoding.py
"""

# ── 让子目录内的测试文件仍能 ``import _runner`` ──────────────────
# ``_runner.py`` 位于上一级 ``test/``；直接 ``python test/<sub>/test_x.py``
# 时 ``sys.path[0]`` 是子目录本身，找不到 ``_runner``，故在此补上。
import os as _os
import sys as _sys

_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _ROOT not in _sys.path:
    _sys.path.insert(0, _ROOT)
del _os, _sys, _ROOT
