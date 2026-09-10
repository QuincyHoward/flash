#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cross_check_external.py — 【可选】与外部 FLYCHK 官方小包做格式对拍
=================================================================

**本脚本不属于发布包的运行时依赖**：`gen_flychk_his` 只用自包含写出器
（`zip_writer.HistoryZipWriter`）。若你本地另有 FLYCHK 官方 Python 小包
（提供 `flychk.input_gen.FlychkInputGenerator`），可用本脚本验证两者对同一张
表写出的 zip **逐字节一致**，作为格式契约 `flychk-history-v1` 的外部证据。

用法::

    # 显式给出小包仓库根目录 (含 flychk/input_gen/__init__.py)
    python flash/input_gen/gen_flychk_his/test/cross_check_external.py \
        --flychk-root /path/to/flychk-sim/flychk

    # 或用环境变量
    set FLYCHK_SIM_ROOT=...      (Windows)
    export FLYCHK_SIM_ROOT=...   (bash)
    python .../cross_check_external.py

    # 若同时安装了 flychk 包, 也可省略 --flychk-root (走普通 import)
退出码: 0 = 全部一致; 1 = 存在差异或小包不可用。
"""

from __future__ import annotations

import argparse
import contextlib
import importlib
import importlib.util
import io
import os
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

_ROOT = Path(__file__).resolve().parents[4]      # 仓库根 (含 pyproject.toml)
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from flash.input_gen.gen_flychk_his.builder import HistoryTable   # noqa: E402
from flash.input_gen.gen_flychk_his.zip_writer import HistoryZipWriter  # noqa: E402

# 对拍用例: (columns, n_steps)
CASES: List[Tuple[List[str], int]] = [
    (["time", "size", "te", "ti", "tr", "rho"], 5),
    (["time", "size", "te", "ti", "tr", "ne"], 3),
    (["time", "te", "ni"], 2),
    (["time", "te", "rho"], 1),
    (["time", "size", "te", "ne"], 4),
]


def find_external_class(root: Optional[str]) -> Tuple[Optional[type], str]:
    """定位外部小包的 FlychkInputGenerator 类。"""
    # 1) 显式路径 / 环境变量 -> sys.path
    cand = root or os.environ.get("FLYCHK_SIM_ROOT") or os.environ.get("FLYCHK_ROOT")
    if cand:
        cand = str(Path(cand).expanduser())
        if str(cand) not in sys.path:
            sys.path.insert(0, cand)
    # 2) 普通 import
    try:
        mod = importlib.import_module("flychk.input_gen")
        cls = getattr(mod, "FlychkInputGenerator", None)
        if cls is not None:
            return cls, f"import flychk.input_gen ({Path(mod.__file__)})"
    except Exception as exc:                       # noqa: BLE001
        pass
    # 3) 按文件路径加载 (绕过顶层 __init__ 副作用)
    if cand:
        init_py = Path(cand) / "flychk" / "input_gen" / "__init__.py"
        if init_py.is_file():
            spec = importlib.util.spec_from_file_location(
                "_external_flychk_input_gen", str(init_py))
            mod = importlib.util.module_from_spec(spec)
            assert spec and spec.loader
            spec.loader.exec_module(mod)
            cls = getattr(mod, "FlychkInputGenerator", None)
            if cls is not None:
                return cls, f"importlib 加载 {init_py}"
    return None, "未找到外部 FLYCHK 小包"


def make_table(columns: List[str], n: int, element: str = "Ti", z: int = 22
               ) -> HistoryTable:
    rows = []
    for i in range(n):
        row = []
        for c in columns:
            row.append({
                "time": 1.0e-12 * (i + 1),
                "size": 2.0e-4,
                "te": 700.0 + 37.0 * i,
                "ti": 550.0 + 31.0 * i,
                "tr": 430.0 + 23.0 * i,
                "rho": 0.25,
                "ne": 7.5e22,
                "ni": 1.3e22,
            }[c])
        rows.append(row)
    return HistoryTable(columns=list(columns), rows=rows,
                        meta={"element": element, "z": z})


def write_with(cls, table: HistoryTable, path: Path) -> Dict[str, str]:
    with tempfile.TemporaryDirectory(prefix="xcheck_") as tmp, \
            contextlib.redirect_stdout(io.StringIO()):
        try:
            gen = cls(template_dir=Path(tmp) / "templates",
                      work_dir=Path(tmp) / "work")
        except TypeError:            # 兼容签名不同的实现
            gen = cls()
        gen.generate_history_zip(element=table.element, z=table.z,
                                 columns=list(table.columns),
                                 data_rows=[list(r) for r in table.rows],
                                 output_path=str(path))
    with zipfile.ZipFile(str(path)) as zf:
        return {n: zf.read(n).decode("utf-8") for n in zf.namelist()}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="与外部 FLYCHK 小包做格式对拍 (可选)")
    p.add_argument("--flychk-root", default=None,
                   help="FLYCHK 小包仓库根目录 (含 flychk/input_gen)")
    p.add_argument("--out", default=None, help="对拍产物目录 (默认系统临时目录)")
    args = p.parse_args(argv)

    cls, how = find_external_class(args.flychk_root)
    print(f"[外部小包] {how}")
    if cls is None:
        print("[跳过] 未提供 --flychk-root / FLYCHK_SIM_ROOT，且环境内无 flychk 包。")
        print("       本包不依赖该小包；此脚本仅供可选的格式对拍。")
        return 1

    out_dir = Path(args.out) if args.out else Path(tempfile.mkdtemp(prefix="xcheck_out_"))
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"[输出] {out_dir}")
    print(f"{'列组合':<40s} {'步数':>4s}  结果")
    print("-" * 66)

    n_ok, n_bad = 0, 0
    for i, (cols, n) in enumerate(CASES):
        tb = make_table(cols, n)
        a = HistoryZipWriter().write(tb, str(out_dir / f"case{i}_selfcontained.zip"))
        with zipfile.ZipFile(str(a)) as zf:
            mine_members = {m: zf.read(m).decode("utf-8") for m in zf.namelist()}
        theirs = write_with(cls, tb, out_dir / f"case{i}_external.zip")
        same = (list(mine_members) == list(theirs)) and \
            all(mine_members[m] == theirs.get(m) for m in mine_members)
        tag = "identical" if same else "DIFF"
        print(f"{','.join(cols):<40s} {n:>4d}  {tag}")
        if same:
            n_ok += 1
        else:
            n_bad += 1
            for m in set(mine_members) | set(theirs):
                if mine_members.get(m) != theirs.get(m):
                    print(f"    ! 成员 {m} 不一致")
                    print(f"      自包含: {mine_members.get(m)!r}")
                    print(f"      外部  : {theirs.get(m)!r}")

    print("-" * 66)
    print(f"[汇总] 一致 {n_ok} / 差异 {n_bad} (共 {len(CASES)} 用例)")
    return 0 if n_bad == 0 else 1


if __name__ == "__main__":       # pragma: no cover
    sys.exit(main())
