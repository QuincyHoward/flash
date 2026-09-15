"""汇总运行 ``test/`` 下全部 ``test_*.py``（**递归**，含功能子包）。

用法::

    <venv>/Scripts/python.exe test/run_all.py

退出码 = 失败测试总数（0 表示全绿）。

布局
----
``test/`` 已被按功能分类为子包::

    test/
      _runner.py          # 共享运行器（含 sys.path bootstrap）
      run_all.py          # 本汇总器
      core/               # 文本 / 数值内核
      registry/           # 类型声明 / 识别 / 注册表
      parsers/            # 各格式族解析器
      plotting/           # 绘图 / PPT 规范
      io/                 # 网格 / HDF5 / prune
      pipeline/           # batch / CLI / 发布
      hygiene/            # 项目级规约守护
      eosopdata/          # 材料数据模块（cn4 / 其他类型 / transcn4）
        cn4/
        <type>/
        transcn4/

本汇总器递归发现所有层级的 ``test_*.py``，因此**新增子包无需改这里**。
"""

from __future__ import annotations

import importlib.util
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import _runner  # noqa: E402  —— 顺带把项目根加入 sys.path


def _discover() -> list[str]:
    """递归收集 ``test/`` 下所有 ``test_*.py`` 的相对路径（POSIX 风格）。"""
    found: list[str] = []
    for dirpath, dirnames, filenames in os.walk(_HERE):
        # 跳过缓存目录
        dirnames[:] = sorted(d for d in dirnames if d != "__pycache__")
        for fn in sorted(filenames):
            if fn.startswith("test_") and fn.endswith(".py"):
                rel = os.path.relpath(os.path.join(dirpath, fn), _HERE)
                found.append(rel.replace(os.sep, "/"))
    return sorted(found)


def _load(rel: str):
    path = os.path.join(_HERE, *rel.split("/"))
    modname = "wb_" + rel[:-3].replace("/", "_")
    spec = importlib.util.spec_from_file_location(modname, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    # 让测试文件能 ``import _runner``：其所在目录已在共享 __init__ 里补过，
    # 但 FileLoader 不走包导入，故这里显式补一次。
    sub = os.path.dirname(path)
    if sub not in sys.path:
        sys.path.insert(0, sub)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    names = _discover()
    if not names:
        print("no test files found")
        return 1

    total_fail = 0
    total_files = 0
    failed_files: list[str] = []
    n_groups = 0
    last_group = None
    for rel in names:
        group = rel.rsplit("/", 1)[0] if "/" in rel else "."
        if group != last_group:
            n_groups += 1
            last_group = group
            print(f"\n{'#' * 60}\n# group: {group}\n{'#' * 60}")
        try:
            mod = _load(rel)
        except Exception as exc:  # noqa: BLE001
            print(f"\n=== {rel} : IMPORT FAILED ===")
            print(f"  {type(exc).__name__}: {exc}")
            total_fail += 1
            failed_files.append(rel)
            continue
        n = _runner.run_all(vars(mod))
        if n:
            failed_files.append(rel)
        total_fail += n
        total_files += 1

    print("=" * 60)
    if total_fail:
        print(f"TOTAL: {total_fail} test(s) FAILED in {len(failed_files)} file(s): "
              f"{', '.join(failed_files)}")
    else:
        print(f"TOTAL: all tests passed across {total_files} file(s) "
              f"in {n_groups} group(s)")
    print("=" * 60)
    return total_fail


if __name__ == "__main__":
    raise SystemExit(main())
