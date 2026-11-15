"""
pre_diagnose — 预诊断图生成

生成 initial_density.png (初始密度分布) 和 laser_pulse.png (激光脉冲)
两张预诊断图。

与 simulator.py 中 _generate_pre_diagnosis 功能等价,
但 laser_pulse.png 新增了靶结构参数 (CH厚度、CH密度、Si厚度) 标注,
使诊断图更具信息量。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np

# 在模块级别设置 Agg 后端 (必须在任何 pyplot 导入之前)
import matplotlib as _mpl
_mpl.use("Agg")
import matplotlib.pyplot as plt

# ── 初始密度分布图 ────────────────────────────────────────

def generate_initial_density(
    params: Dict[str, Any],
    save_path: Path,
) -> Path:
    """生成初始密度分布图 (initial_density.png)。

    Args:
        params: 仿真参数字典
        save_path: PNG 保存路径

    Returns:
        save_path: 保存的文件路径
    """
    plt.close("all")
    plt.rcParams.update({"font.size": 14, "axes.labelsize": 16,
                         "axes.titlesize": 18, "legend.fontsize": 14,
                         "lines.linewidth": 2.0})

    xmin = float(params.get("xmin_cm", params.get("xmin", -0.045)))
    xmax = float(params.get("xmax_cm", params.get("xmax", 0.045)))
    half = (xmax - xmin) / 2
    rho_c = float(params.get("sim_rhoCham", 1e-6))
    rho_t = float(params.get("sim_rhoTarg", 2.33))
    rho_p_val = params.get("sim_rhoPoly")
    if rho_p_val is not None:
        rho_p_val = float(rho_p_val)

    # 靶和泡沫厚度 (cm, 已是半厚)
    targ_h = float(params.get("sim_targHeight",
                              params.get("sim_targetHeight", 2e-5)))
    poly_h_val_raw = params.get("sim_polyHeight", None)
    if poly_h_val_raw is not None:
        poly_h = float(poly_h_val_raw)
    else:
        poly_h = None

    n = 2000
    x = np.linspace(-half, half, n)
    dens = np.full_like(x, rho_c)

    m_targ = np.abs(x) <= targ_h
    dens[m_targ] = rho_t

    if poly_h is not None and rho_p_val is not None:
        m_poly = (np.abs(x) > targ_h) & (np.abs(x) <= poly_h)
        dens[m_poly] = rho_p_val

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(x * 1e4, dens, "k-", lw=2.5)
    ax.axvspan(-targ_h * 1e4, targ_h * 1e4, alpha=0.15, color="orange",
               label="Target")

    # 标注参数
    ax.text(0, half * 1e4 * 0.5,
            f"CH: {rho_p_val:.3f} g/cm³" if rho_p_val is not None else "",
            fontsize=14, ha="center", va="center",
            bbox=dict(boxstyle="round", facecolor="lightblue", alpha=0.5))

    if poly_h is not None:
        mid_poly = (targ_h + poly_h) / 2
        ax.text(mid_poly * 1e4,
                rho_p_val / 2 if rho_p_val else 0.05,
                f"CH foam\nh={poly_h*2*1e4:.0f} um\n"
                f"ρ={rho_p_val:.3f}" if rho_p_val else "",
                fontsize=12, ha="center", va="center",
                bbox=dict(boxstyle="round", facecolor="lightgreen", alpha=0.5))

    ax.set_xlabel("x (um)")
    ax.set_ylabel("Density (g/cm³)")
    ax.set_title("Initial Density Distribution")
    ax.legend(fontsize=14)
    ax.set_xlim(-half * 1e4, half * 1e4)
    ax.grid(True, alpha=0.3)

    save_path = Path(save_path)
    save_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(str(save_path), dpi=72)
    plt.close(fig)

    return save_path


# ── 靶结构参数提取 ────────────────────────────────────────

def extract_structure_params(params: Dict[str, Any]) -> Dict[str, str]:
    """从参数中提取靶结构信息, 用于激光脉冲图标注。

    Args:
        params: 仿真参数 (含 sim_rhoPoly, sim_polyHeight, sim_rhoTarg,
                sim_targHeight 等)

    Returns:
        {标签: 描述} 字典
    """
    annotation: Dict[str, str] = {}

    # CH 泡沫层
    rho_poly = params.get("sim_rhoPoly", params.get("rhoPoly"))
    if rho_poly is not None:
        rho_poly_val = float(rho_poly)
    else:
        rho_poly_val = 0.08

    # sim_polyHeight 是 cm, polyHeight_um 是 um
    if "sim_polyHeight" in params:
        poly_h_val = float(params["sim_polyHeight"]) * 1e4  # cm → um
    elif "polyHeight_um" in params:
        poly_h_val = float(params["polyHeight_um"])
    else:
        poly_h_val = 100.0  # 默认 100 um

    # Si 靶 (target)
    rho_targ = params.get("sim_rhoTarg", params.get("rhoTarg", 2.33))
    # sim_targHeight 是 cm, targetHeight_um 是 um
    if "sim_targHeight" in params:
        targ_h_val = float(params["sim_targHeight"]) * 1e4  # cm → um
    elif "sim_targetHeight" in params:
        targ_h_val = float(params["sim_targetHeight"]) * 1e4  # cm → um
    elif "targetHeight_um" in params:
        targ_h_val = float(params["targetHeight_um"])
    else:
        targ_h_val = 0.2  # 默认 0.2 um

    annotation["CH foam density"] = f"{rho_poly_val:.3f} g/cm³"
    annotation["CH foam half-thickness"] = f"{poly_h_val:.1f} μm"
    annotation["Target density"] = f"{float(rho_targ):.2f} g/cm³"
    annotation["Target half-thickness"] = f"{targ_h_val:.3f} μm"

    # 初始温度
    tele_cham = params.get("sim_teleCham", None)
    if tele_cham is not None:
        annotation["Initial Te"] = f"{float(tele_cham):.0f} K"

    return annotation


# ── 激光脉冲图 (简单版, 无标注, 保底回退) ──────────────────

def _generate_laser_pulse_simple(
    params: Dict[str, Any],
    save_path: Path,
) -> Path:
    """简单版激光脉冲图 (无结构参数标注)。

    当带标注的版本因 matplotlib 渲染问题失败时回退至此。
    """
    save_path = Path(save_path)
    save_path.parent.mkdir(parents=True, exist_ok=True)

    plt.close("all")
    plt.rcParams.update({"font.size": 14, "axes.labelsize": 16,
                         "axes.titlesize": 18})

    laser_t = params.get("laser_times", params.get("ed_times", [0, 1e-9]))
    laser_p = params.get("laser_powers", params.get("ed_powers", [0, 0]))
    if not laser_t or not laser_p:
        laser_t, laser_p = [0, 1e-9], [0, 0]

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(np.array(laser_t) * 1e9, np.array(laser_p) / 1e14, "r-", lw=2.5)
    ax.set_xlabel("Time (ps)")
    ax.set_ylabel("Power (\u00d710\u00b9\u2074 W/cm\u00b2)")
    ax.set_title("Laser Pulse")
    ax.grid(True, alpha=0.3)
    fig.savefig(str(save_path), dpi=72)
    plt.close(fig)
    return save_path


# ── 激光脉冲图 (带结构参数标注) ────────────────────────────

def generate_laser_pulse_annotated(
    params: Dict[str, Any],
    save_path: Path,
    *,
    laser_times: Optional[list] = None,
    laser_powers: Optional[list] = None,
) -> Path:
    """生成带靶结构参数标注的激光脉冲图 (laser_pulse.png)。

    在原有的 laser_pulse 图上, 额外展示 CH厚度/CH密度/Si厚度等
    initial_density.png 中包含的结构参数。

    Args:
        params: 仿真参数字典 (含靶结构和激光参数)
        save_path: PNG 保存路径
        laser_times: 激光脉冲时间点列表 (s), 默认从 params 读取
        laser_powers: 激光脉冲功率列表 (W/cm²), 默认从 params 读取

    Returns:
        save_path: 保存的文件路径
    """
    if laser_times is None:
        laser_times = params.get("laser_times", params.get("ed_times", None))
    if laser_powers is None:
        laser_powers = params.get("laser_powers", params.get("ed_powers", None))
    if laser_times is None or laser_powers is None or len(laser_times) == 0:
        laser_times, laser_powers = [0, 1e-9], [0, 0]

    save_path = Path(save_path)
    save_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        # 尝试带标注版
        structure_info = extract_structure_params(params)
        from .pulse import plot_pulse_with_profile

        display_params = {
            "CH foam": f"ρ={structure_info['CH foam density'].split(':')[-1].strip() if ':' in structure_info['CH foam density'] else structure_info['CH foam density']}",
            "CH foam thick.": structure_info["CH foam half-thickness"],
            "Target (Si)": f"ρ={structure_info['Target density'].split(':')[-1].strip() if ':' in structure_info['Target density'] else structure_info['Target density']}",
            "Target thick.": structure_info["Target half-thickness"],
        }
        if "Initial Te" in structure_info:
            display_params["Initial Te"] = structure_info["Initial Te"]

        plot_pulse_with_profile(
            np.array(laser_times) * 1e9,
            np.array(laser_powers),
            str(save_path),
            profile_params=display_params,
            title="Laser Pulse & Target Configuration",
        )
    except Exception as exc:
        import warnings
        warnings.warn(f"带标注的 laser_pulse 生成失败 ({exc}), 回退到简单版")
        return _generate_laser_pulse_simple(params, save_path)

    return save_path


# ── 一站式预诊断 ──────────────────────────────────────────

def generate_pre_diagnosis_pair(
    params: Dict[str, Any],
    sim_input_dir: Path,
) -> Dict[str, Path]:
    """一站式生成两张预诊断图 (initial_density.png + laser_pulse.png)。

    替换 simulator.py 中 _generate_pre_diagnosis 的逻辑。
    若带标注版本失败, 自动回退到简单版。

    Args:
        params: 仿真参数
        sim_input_dir: FLASH 仿真输入目录

    Returns:
        {"initial_density": Path, "laser_pulse": Path}
    """
    sim_input_dir = Path(sim_input_dir)
    sim_input_dir.mkdir(parents=True, exist_ok=True)

    init_path = generate_initial_density(params, sim_input_dir / "initial_density.png")

    # 尝试带标注版, 若 matplotlib 渲染失败则回退
    try:
        pulse_path = generate_laser_pulse_annotated(
            params, sim_input_dir / "laser_pulse.png")
    except Exception:
        pulse_path = _generate_laser_pulse_simple(
            params, sim_input_dir / "laser_pulse.png")

    return {"initial_density": init_path, "laser_pulse": pulse_path}
