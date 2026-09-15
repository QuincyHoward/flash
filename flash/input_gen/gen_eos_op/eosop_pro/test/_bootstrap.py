"""``test/`` 引导模块 —— 让**任意深度**子目录里的测试文件都能直接运行。

问题
----
``python test/<sub>/test_x.py`` 时 ``sys.path[0]`` 是 ``<sub>/``，
而 ``_runner.py`` 位于**上一级** ``test/``，于是 ``import _runner`` 失败::

    ModuleNotFoundError: No module named '_runner'

子包 ``<sub>/__init__.py`` 里的 ``sys.path`` 修补**帮不上忙**：
直接执行脚本时 Python 不会导入 ``<sub>`` 这个包（它只把 ``<sub>/``
放进 ``sys.path[0]``），所以那段修补是**死代码**。实测确认：
``PathFinder.find_spec('core', ['.../test/core'])`` -> ``None``，
``PathFinder.find_spec('core', ['.../test'])`` -> 正常 spec。

采用的方案
----------
删掉所有 ``<sub>/__init__.py`` 里失效的 ``sys.path`` 修补，改为
**测试文件自身在导入 ``_runner`` 之前先调用 :func:`ensure_paths`**。

每个测试文件头部因此变成::

    import _runner                                  # noqa: F401

### 为什么这样仍然可行

``run_all.py`` 用 ``_load()`` 时已显式 ``sys.path.insert(0, sub)``
且插入过 ``test/``，所以**汇总运行**本来就通。
只有"单文件裸跑"这一种用法失败，而它才是开发者最常用的调试方式。

为了不把样板散进 32 个文件，用法统一为**一次内联上溯**（3 行）::

    import os, sys
    _d = os.path.dirname(os.path.abspath(__file__))
    while _d != os.path.dirname(_d) and not os.path.isfile(
            os.path.join(_d, "_runner.py")):
        _d = os.path.dirname(_d)
    sys.path.insert(0, _d)

    import _runner                                  # noqa: F401

:func:`ensure_paths` 是等价的函数形式，供需要它的脚本调用；
``_pathfix.py``（同目录）是这 3 行的可导入封装，测试文件写成::

    import _pathfix  # noqa: F401  —— 已修正 sys.path
    import _runner

即可，但 ``_pathfix`` 本身也要能被找到……故 **最终** 采用内联 3 行。
本模块保留 :func:`ensure_paths` 供 ``run_all.py`` / 一次性脚本复用。
"""

from __future__ import annotations

import os
import sys


def test_dir(start: str | os.PathLike[str] | None = None) -> str:
    """从 ``start``（默认本文件）向上找到含 ``_runner.py`` 的目录。"""
    if start is None:
        start = os.path.abspath(__file__)
    d = os.path.dirname(os.path.abspath(start))
    for _ in range(8):
        if os.path.isfile(os.path.join(d, "_runner.py")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    return os.path.dirname(os.path.abspath(__file__))


def ensure_paths(start: str | os.PathLike[str] | None = None) -> list[str]:
    """把 ``test/`` 与仓库根插入 ``sys.path``；返回实际新增的目录。

    幂等：重复调用不产生重复项。
    """
    added: list[str] = []
    root = test_dir(start)
    repo = os.path.dirname(root)
    here = os.path.dirname(os.path.abspath(start)) if start else root
    for p in (here, root, repo):
        if p and p not in sys.path:
            sys.path.insert(0, p)
            added.append(p)
    return added


if __name__ == "__main__":                      # 自检
    print("test_dir()   ->", test_dir())
    print("ensure_paths ->", ensure_paths(__file__))
