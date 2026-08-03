"""
par_reader.py — 读取 FLASH .par 文件参数
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict

_PARAM_RE = re.compile(r'^\s*(\w+)\s*=\s*(.+?)\s*(?:#.*)?$')


def read_par(par_path: str | Path) -> Dict[str, Any]:
    """读取 .par 文件, 返回 {变量名: 值} 字典。"""
    params: Dict[str, Any] = {}
    par_path = Path(par_path)
    if not par_path.exists():
        raise FileNotFoundError(f".par 文件不存在: {par_path}")

    for line in par_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = _PARAM_RE.match(line)
        if not m:
            continue
        key = m.group(1)
        val_str = m.group(2).strip().strip('"').strip("'")

        # 数值转换
        try:
            val = int(val_str)
        except ValueError:
            try:
                val = float(val_str)
            except ValueError:
                low = val_str.lower()
                val = True if low in (".true.", "true", "t") else (
                    False if low in (".false.", "false", "f") else val_str)

        # 激光脉冲: 收集为列表
        if key.startswith("ed_time_1_"):
            idx = int(key.rsplit("_", 1)[-1])
            lst = params.setdefault("laser_times", [])
            while len(lst) < idx:
                lst.append(None)
            lst[idx - 1] = float(val)
            continue
        if key.startswith("ed_power_1_"):
            idx = int(key.rsplit("_", 1)[-1])
            lst = params.setdefault("laser_powers", [])
            while len(lst) < idx:
                lst.append(None)
            lst[idx - 1] = float(val)
            continue

        params[key] = val

    return params


def find_latest_par(runs_dir: str | Path, run_id: str | None = None) -> Path:
    """查找 .par 文件。

    Args:
        runs_dir: runs_* 目录路径
        run_id: 指定运行 ID (如 "000002"), None=取最新

    Returns:
        .par 文件路径
    """
    runs_dir = Path(runs_dir)
    if run_id is not None:
        # 指定 run_id 的 sim_input 目录
        par_path = runs_dir / run_id / "sim_input"
        if par_path.exists():
            pars = sorted(par_path.glob("*.par"))
            if pars:
                return pars[0]
    # 回退: rglob 查找
    pars = sorted(runs_dir.rglob("*.par"))
    if not pars:
        raise FileNotFoundError(f"在 {runs_dir} 中未找到 .par 文件")
    return pars[-1]


def find_latest_result_h5(runs_dir: str | Path, run_id: str | None = None) -> Path:
    """查找最新的 result.h5。

    Args:
        runs_dir: runs_* 目录路径
        run_id: 指定运行 ID (如 "000002"), None=取最新

    Returns:
        result.h5 路径
    """
    runs_dir = Path(runs_dir)
    if run_id is not None:
        h5_path = runs_dir / run_id / "database" / "flash_out" / "result.h5"
        if h5_path.exists():
            return h5_path
    # 回退: rglob 查找
    h5s = sorted(runs_dir.rglob("result.h5"))
    if not h5s:
        raise FileNotFoundError(f"在 {runs_dir} 中未找到 result.h5")
    return h5s[-1]
