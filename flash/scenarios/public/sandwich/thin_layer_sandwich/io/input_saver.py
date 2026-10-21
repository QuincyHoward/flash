"""
input_saver — FLASH 输入文件保存

将 FLASH 仿真配置保存为 .par / pulse_data.npz / input_params.json。
对应 chsich02/flash_runner.py 中 save_flash_input 的功能。
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np


def save_input_params(
    save_dir: Path,
    params: Dict[str, Any],
    *,
    ga_params: Optional[Dict[str, float]] = None,
    eval_index: int = 0,
) -> Path:
    """保存输入参数 JSON 快照。

    Args:
        save_dir: 保存目录
        params: FLASH 配置参数字典
        ga_params: 可选 GA 算法原始优化参数
        eval_index: 评估序号

    Returns:
        保存的 JSON 文件路径
    """
    save_dir = Path(save_dir)
    save_dir.mkdir(parents=True, exist_ok=True)

    input_params = {
        "eval_index": eval_index,
        "sim_rhoTarg": float(params.get("sim_rhoTarg", 2.33)),
        "sim_rhoPoly": float(params.get("sim_rhoPoly", 0.08)),
        "sim_polyHeight_um": float(params.get("sim_polyHeight_um", 100.0)),
        "sim_targHeight_um": float(params.get("sim_targHeight_um",
                                             params.get("sim_targetHeight_um", 0.2))),
        "sim_rhoCham": float(params.get("sim_rhoCham", 1e-6)),
        "pulse_peak": float(params.get("pulse_peak", 0.0)),
        "pulse_energy": float(params.get("pulse_energy", 0.0)),
        "n_gaussians": len(params.get("gaussians", [])),
        "L0_um": float(params.get("L0_um", 350.0)),
        "lrefine_max": int(params.get("lrefine_max", 8)),
    }

    # 激光脉冲时序
    time_pts = params.get("pulse_time_points_s", [])
    power_pts = params.get("pulse_power_points", [])
    if time_pts and power_pts:
        input_params["pulse_time_points_s"] = [float(t) for t in time_pts]
        input_params["pulse_power_points"] = [float(p) for p in power_pts]

    if ga_params is not None:
        for key, val in ga_params.items():
            if key not in input_params:
                input_params[f"ga_{key}"] = float(val)
        input_params["ga_param_names"] = sorted(str(k) for k in ga_params.keys())

    json_path = save_dir / "input_params.json"
    with open(str(json_path), "w") as f:
        json.dump(input_params, f, indent=2)

    return json_path


def save_pulse_data(
    save_dir: Path,
    times_ns: np.ndarray,
    powers: np.ndarray,
) -> Path:
    """保存激光脉冲数据到 NPZ 文件。

    Args:
        save_dir: 保存目录
        times_ns: 脉冲时间轴 (ns)
        powers: 脉冲功率 (W/cm²)

    Returns:
        NPZ 文件路径
    """
    save_dir = Path(save_dir)
    save_dir.mkdir(parents=True, exist_ok=True)

    npz_path = save_dir / "pulse_data.npz"
    np.savez(str(npz_path), times_ns=times_ns, powers=powers)
    return npz_path


def save_flash_input(
    save_dir: Path,
    par_content: str,
    *,
    params: Optional[Dict[str, Any]] = None,
    ga_params: Optional[Dict[str, float]] = None,
    eval_index: int = 0,
    pulse_times_ns: Optional[np.ndarray] = None,
    pulse_powers: Optional[np.ndarray] = None,
    copy_pulse_script_source: Optional[Path] = None,
) -> Dict[str, str]:
    """一站式保存 FLASH 输入文件。

    保存内容:
      - simulation.par: FLASH 参数文件 (需事先用 par_builder 生成)
      - pulse_data.npz: 激光脉冲数据
      - input_params.json: 完整参数快照

    Args:
        save_dir: 保存目录 (例如 work_dir/database/flash_in/)
        par_content: .par 文件内容字符串
        params: FLASH 配置参数
        ga_params: GA 优化参数
        eval_index: 评估序号
        pulse_times_ns: 脉冲时间轴
        pulse_powers: 脉冲功率
        copy_pulse_script_source: 要复制的 pulse_shaping.py 源路径

    Returns:
        {文件名: 保存路径} 字典
    """
    save_dir = Path(save_dir)
    save_dir.mkdir(parents=True, exist_ok=True)

    saved: Dict[str, str] = {}

    # 1. 保存 .par 文件
    par_path = save_dir / "simulation.par"
    with open(str(par_path), "w") as f:
        f.write(par_content)
    saved["par"] = str(par_path)

    # 2. 保存脉冲数据
    if pulse_times_ns is not None and pulse_powers is not None:
        npz_path = save_pulse_data(save_dir, pulse_times_ns, pulse_powers)
        saved["pulse_npz"] = str(npz_path)

    # 3. 复制 pulse_shaping.py (独立重建)
    if copy_pulse_script_source and Path(copy_pulse_script_source).exists():
        shutil.copy(str(copy_pulse_script_source),
                    str(save_dir / "pulse_shaping.py"))
        saved["pulse_shaping"] = str(save_dir / "pulse_shaping.py")

    # 4. 保存参数快照
    if params is not None:
        json_path = save_input_params(
            save_dir, params, ga_params=ga_params, eval_index=eval_index,
        )
        saved["params_json"] = str(json_path)

    return saved
