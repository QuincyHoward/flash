"""零依赖测试运行器（**不需要 pytest**）。

用法
----
在本目录下 ``python test_xxx.py``，或 ``python run_all.py`` 汇总。

每个测试文件头两行固定为::

    import _runner                      # noqa: F401  —— 顺带修正 sys.path
    from _runner import expect, expect_eq, main

原因：``python test/test_x.py`` 会把 ``test/`` 放进 ``sys.path[0]``，
所以 ``import _runner`` 一定成功；而 ``_runner`` 在被导入时把**项目根**
插入 ``sys.path``，于是之后 ``from eosop_pro import ...`` 也能成功。

子目录布局
----------
``test/`` 下的测试已按功能分入子包（``core/`` ``registry/`` ``parsers/``
``plotting/`` ``io/`` ``pipeline/`` ``hygiene/`` ``eosopdata/`` ...）。
每个子包有 ``__init__.py``，其中把 ``test/`` 补进 ``sys.path``，
因此**子目录内的测试文件仍然只写 ``import _runner`` 即可**，无需相对导入。
"""

from __future__ import annotations

import os
import sys
import traceback
from typing import Any, Callable

# ── 项目根 bootstrap（本文件位于 <ROOT>/test/_runner.py） ────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
# 让 ``import eosop_pro`` 与顶层 ``import config`` 都能工作
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
# 便于 ``python test/<sub>/test_x.py`` 直接运行时仍能定位 ``_runner``
for _sub in ("core", "registry", "parsers", "plotting", "io",
             "pipeline", "hygiene", "eosopdata"):
    _p = os.path.join(_HERE, _sub)
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

__all__ = [
    "expect", "expect_eq", "expect_almost", "expect_in",
    "expect_lt", "expect_gt", "main", "run_all",
]

_GREEN = "\033[92m"
_RED = "\033[91m"
_DIM = "\033[2m"
_RESET = "\033[0m"


def _ok_color(s: str) -> str:
    return s if os.environ.get("NO_COLOR") else _GREEN + s + _RESET


def _fail_color(s: str) -> str:
    return s if os.environ.get("NO_COLOR") else _RED + s + _RESET


def _dim(s: str) -> str:
    return s if os.environ.get("NO_COLOR") else _DIM + s + _RESET


# ── 断言辅助（带明确失败信息，输出数值证据） ─────────────────────────
def expect(cond: bool, msg: str = "") -> None:
    if not cond:
        raise AssertionError(msg or "condition is falsy")


def expect_lt(actual: Any, bound: Any, msg: str = "") -> None:
    if not actual < bound:
        raise AssertionError(f"{msg or 'not less than'}: actual={actual!r} bound={bound!r}")


def expect_gt(actual: Any, bound: Any, msg: str = "") -> None:
    if not actual > bound:
        raise AssertionError(f"{msg or 'not greater than'}: actual={actual!r} bound={bound!r}")


def expect_eq(actual: Any, expected: Any, msg: str = "") -> None:
    if actual != expected:
        raise AssertionError(
            f"{msg or 'value mismatch'}: actual={actual!r} expected={expected!r}"
        )


def expect_almost(actual: float, expected: float, tol: float = 1e-9, msg: str = "") -> None:
    if abs(actual - expected) > tol:
        raise AssertionError(
            f"{msg or 'value mismatch'}: actual={actual!r} expected={expected!r} "
            f"delta={actual - expected!r} tol={tol}"
        )


def expect_in(needle: Any, haystack: Any, msg: str = "") -> None:
    if needle not in haystack:
        raise AssertionError(f"{msg or 'membership failed'}: {needle!r} not in {haystack!r}")


# ── 运行器 ────────────────────────────────────────────────────────
def _collect(ns: dict[str, Any]) -> list[tuple[str, Callable[[], Any]]]:
    items = []
    for name, obj in ns.items():
        if name.startswith("test_") and callable(obj):
            items.append((name, obj))
    items.sort(key=lambda kv: kv[0])
    return items


def run_all(ns: dict[str, Any], *, verbose: bool = True) -> int:
    """执行 ``ns`` 中全部 ``test_*`` 可调用对象，返回失败数。"""
    tests = _collect(ns)
    label = os.path.basename(ns.get("__file__", "tests"))
    if not tests:
        print(_dim(f"[{label}] no tests found"))
        return 0

    failures: list[tuple[str, str]] = []
    print(f"\n=== {label} : {len(tests)} tests ===")
    for name, fn in tests:
        try:
            fn()
        except Exception as exc:  # noqa: BLE001 - 测试运行器必须抓住一切
            failures.append((name, f"{type(exc).__name__}: {exc}"))
            print(f"  {_fail_color('FAIL')} {name}")
            if verbose:
                tb = traceback.format_exc().rstrip().splitlines()
                for line in tb[-6:]:
                    print(_dim(f"        {line}"))
        else:
            print(f"  {_ok_color('PASS')} {name}")

    n_ok = len(tests) - len(failures)
    if failures:
        print(f"  --> {_fail_color(f'{len(failures)} FAILED')} / {n_ok} passed\n")
    else:
        print(f"  --> {_ok_color('all passed')} ({n_ok})\n")
    return len(failures)


def main(ns: dict[str, Any]) -> int:
    """测试文件入口：``sys.exit(main(globals()))``。"""
    return 0 if run_all(ns) == 0 else 1
