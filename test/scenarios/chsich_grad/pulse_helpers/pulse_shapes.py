"""
pulse_shapes.py — FLASH 激光脉冲形状发生器

脉冲数据格式: List[Tuple[time_s, power_Wcm2]]
对应 FLASH .par 中的 ed_time_1_N / ed_power_1_N 参数。
"""

from __future__ import annotations

from typing import List, Optional, Tuple

import numpy as np

# ── 类型别名 ─────────────────────────────────────────────
PulseData = List[Tuple[float, float]]


# ╔══════════════════════════════════════════════════════════════╗
# ║  ★ 快速修改区 ★                                            ║
# ╚══════════════════════════════════════════════════════════════╝

# 默认: 超高斯脉冲 (order=4, 1ns FWHM, 5e14 W/cm²)
# 把下面改成 None 可回落为梯形方波
_QUICK_EDIT_ED_DATA: PulseData | None = None


# ============================================================
#  脉冲生成函数
# ============================================================

def make_trapezoid(
    peak_power: float = 5e14,
    rise_time: float = 0.1e-9,
    flat_time: float = 0.9e-9,
    fall_time: float = 0.08e-9,
) -> PulseData:
    """梯形方波脉冲 — 4 段"""
    t_on = rise_time
    t_off = rise_time + flat_time
    return [
        (0.0, 0.0),
        (t_on, peak_power),
        (t_off, peak_power),
        (t_off + fall_time, 0.0),
    ]


def make_super_gaussian(
    peak_power: float = 5e14,
    center_time: float = 0.6e-9,
    fwhm: float = 1.0e-9,
    order: int = 4,
    n_points: int = 120,
    time_start: float = 0.0,
    time_end: float = 1.2e-9,
    threshold_ratio: float = 1e-6,
) -> PulseData:
    """超高斯脉冲 P(t)=P0*exp(-ln2*[2(t-t0)/FWHM]^(2*order))"""
    times = np.linspace(time_start, time_end, n_points)
    exponent = (2.0 * (times - center_time) / fwhm) ** (2 * order) * np.log(2.0)
    powers = peak_power * np.exp(-exponent)
    powers = np.clip(powers, 0.0, None)
    threshold = peak_power * threshold_ratio
    valid = powers > threshold
    result = list(zip(times[valid].tolist(), powers[valid].tolist()))
    # Ensure first point is at t=0.0 with power=0.0 (FLASH requires strictly increasing times)
    if result:
        t0, p0 = result[0]
        if t0 > 0.0 and p0 > 0.0:
            result.insert(0, (0.0, 0.0))
        elif t0 == 0.0 and p0 > 0.0:
            result[0] = (0.0, 0.0)
    return result


def make_custom(
    ed_times: List[float],
    ed_powers: List[float],
) -> PulseData:
    """自定义脉冲: 直接使用传入的 ed_time/ed_power 列表。"""
    if len(ed_times) != len(ed_powers):
        raise ValueError(
            f"ed_times ({len(ed_times)}) 和 ed_powers ({len(ed_powers)}) 长度不一致"
        )
    return list(zip(ed_times, ed_powers))


# ============================================================
#  统一入口
# ============================================================

_PULSE_REGISTRY = {
    "trapezoid": make_trapezoid,
    "trapezoidal": make_trapezoid,
    "super-gaussian": make_super_gaussian,
    "super_gaussian": make_super_gaussian,
    "supergaussian": make_super_gaussian,
    "custom": make_custom,
}


def gen_pulse(pulse_type: str = "trapezoid", /, **kwargs) -> PulseData:
    """统一脉冲生成入口。"""
    maker = _PULSE_REGISTRY.get(pulse_type.lower())
    if maker is None:
        raise ValueError(
            f"未知脉冲类型: '{pulse_type}'. 可选: {list(_PULSE_REGISTRY.keys())}"
        )
    return maker(**kwargs)


def resolve_pulse_data(
    ed_times: Optional[List[float]] = None,
    ed_powers: Optional[List[float]] = None,
    pulse_type: str = "trapezoid",
    **pulse_kwargs,
) -> PulseData:
    """解析脉冲数据 — 优先级: 快速修改区 > 函数参数 > 自动回落"""
    if _QUICK_EDIT_ED_DATA is not None and len(_QUICK_EDIT_ED_DATA) > 0:
        print(f"  [pulse_shapes] ✅ 使用快速修改区数据 ({len(_QUICK_EDIT_ED_DATA)} 段)")
        return _QUICK_EDIT_ED_DATA
    if ed_times is not None and ed_powers is not None and len(ed_times) > 0:
        print(f"  [pulse_shapes] ✅ 使用函数参数自定义 ({len(ed_times)} 段)")
        return make_custom(ed_times, ed_powers)
    print(f"  [pulse_shapes] ⏩ 数据为空, 回落为 {pulse_type}")
    return gen_pulse(pulse_type, **pulse_kwargs)
