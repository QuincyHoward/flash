"""
result_saver — 分析结果持久化

提供统一的 CSV / NPZ / JSON 保存接口。
从 chsich02/analysis/txn.py 和 analysis/dens.py 的 _complete_analysis
中的保存逻辑提取并泛化。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np


def save_analysis_csv(
    csv_path: Path,
    times_s: np.ndarray,
    fields: Dict[str, np.ndarray],
    *,
    header_prefix: Optional[str] = None,
) -> Path:
    """将时间序列保存为 CSV 文件。

    Args:
        csv_path: 保存路径
        times_s: 时间数组 (s)
        fields: {变量名: 值数组} 字典, 所有数组长度必须与 times_s 一致
        header_prefix: 可选列名前缀, 默认自动生成 "time_s,key1,key2,..."

    Returns:
        csv_path: 保存的文件路径
    """
    csv_path = Path(csv_path)
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    if header_prefix is None:
        col_names = ["time_s"] + list(fields.keys())
    else:
        col_names = header_prefix.split(",")

    columns = [times_s]
    for val in fields.values():
        columns.append(np.asarray(val))

    header = ",".join(col_names)

    np.savetxt(
        str(csv_path),
        np.column_stack(columns),
        delimiter=",",
        header=header,
        comments="",
    )
    return csv_path


def save_analysis_npz(
    npz_path: Path,
    times_s: np.ndarray,
    fields: Dict[str, np.ndarray],
    *,
    extra: Optional[Dict[str, Any]] = None,
) -> Path:
    """将时间序列保存为 NPZ 压缩文件。

    Args:
        npz_path: 保存路径
        times_s: 时间数组 (s)
        fields: {变量名: 值数组} 字典
        extra: 额外数据字典, 如 {"txn": txn_interp, "window_result": {...}}

    Returns:
        npz_path: 保存的文件路径
    """
    npz_path = Path(npz_path)
    npz_path.parent.mkdir(parents=True, exist_ok=True)

    save_dict: Dict[str, Any] = {"times_s": times_s}
    save_dict.update(fields)
    if extra:
        for k, v in extra.items():
            if isinstance(v, np.ndarray):
                save_dict[k] = v
            elif isinstance(v, dict):
                save_dict[k] = str(v)

    np.savez(str(npz_path), **save_dict)
    return npz_path


def save_analysis_json(
    json_path: Path,
    result: Dict[str, Any],
    *,
    indent: int = 2,
) -> Path:
    """将分析结果字典保存为 JSON 文件。

    自动序列化 ndarray / Path / dict 等非 JSON 兼容类型。

    Args:
        json_path: 保存路径
        result: 分析结果字典
        indent: JSON 缩进空格数

    Returns:
        json_path: 保存的文件路径
    """
    json_path = Path(json_path)
    json_path.parent.mkdir(parents=True, exist_ok=True)

    serializable: Dict[str, Any] = {}
    for k, v in result.items():
        if isinstance(v, np.ndarray):
            serializable[k] = v.tolist()
        elif isinstance(v, dict):
            serializable[k] = {
                sk: str(sv) if isinstance(sv, (Path, np.integer, np.floating))
                else (sv.tolist() if isinstance(sv, np.ndarray) else sv)
                for sk, sv in v.items()
            }
        elif isinstance(v, Path):
            serializable[k] = str(v)
        elif isinstance(v, (np.integer, np.floating, np.bool_)):
            serializable[k] = v.item()
        else:
            serializable[k] = v

    with open(str(json_path), "w", encoding="utf-8") as f:
        json.dump(serializable, f, indent=indent, ensure_ascii=False)

    return json_path


def save_analysis_data(
    output_dir: Path,
    prefix: str,
    times_s: np.ndarray,
    fields: Dict[str, np.ndarray],
    result: Dict[str, Any],
    *,
    save_csv: bool = True,
    save_npz: bool = True,
    save_json: bool = True,
) -> Dict[str, str]:
    """一站式保存分析数据至 CSV + NPZ + JSON。

    是 analysis/txn.py 中 _complete_analysis 保存逻辑的统一接口。

    Args:
        output_dir: 输出目录 (plots_dir)
        prefix: 文件名前缀, 如 "analysis"
        times_s: 时间数组 (s)
        fields: {变量名: 值数组} — 写入 CSV 和 NPZ
        result: 分析结果字典 — 写入 JSON
        save_csv: 是否保存 CSV
        save_npz: 是否保存 NPZ
        save_json: 是否保存 JSON

    Returns:
        dict: {"csv": "...", "npz": "...", "json": "..."}
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    saved: Dict[str, str] = {}

    if save_csv and fields:
        csv_path = save_analysis_csv(
            output_dir / f"{prefix}_data.csv", times_s, fields,
        )
        saved["csv"] = str(csv_path)

    if save_npz:
        npz_path = save_analysis_npz(
            output_dir / f"{prefix}_data.npz", times_s, fields,
        )
        saved["npz"] = str(npz_path)

    if save_json:
        json_path = save_analysis_json(
            output_dir / f"{prefix}_result.json", result,
        )
        saved["json"] = str(json_path)

    return saved
