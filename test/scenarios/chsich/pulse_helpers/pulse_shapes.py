"""
pulse_shapes.py — FLASH 激光脉冲形状发生器

脉冲数据格式: List[Tuple[time_s, power_Wcm2]]
对应 FLASH .par 中的 ed_time_1_N / ed_power_1_N 参数。

===== ⭐ 快速修改区: 直接在这里改 ed_time/ed_power 数值 =====
  把下面 _QUICK_EDIT_ED_DATA 的值改成你想要的 (time, power) 对。
  数据为 None → 自动回落为梯形方波。
  数据非空 → 直接使用你设的值。
===========================================================
"""

from __future__ import annotations

from typing import List, Optional, Tuple

import numpy as np

# ── 类型别名 ─────────────────────────────────────────────
PulseData = List[Tuple[float, float]]


# ╔══════════════════════════════════════════════════════════════╗
# ║  ★ 快速修改区 ★                                            ║
# ║                                                              ║
# ║  您可以直接修改下面 _QUICK_EDIT_ED_DATA 的值，之后运行       ║
# ║  run_si.py 时就会自动使用您设定的 ed_time/ed_power 数据。     ║
# ║                                                              ║
# ║  ⚡ 数据为 None → 自动回落为梯形方波                         ║
# ║  ⚡ 数据非空   → 直接使用您设的值                             ║
# ║                                                              ║
# ║  下面有几个现成的示例，把注释去掉就能用。                     ║
# ╚══════════════════════════════════════════════════════════════╝

# _QUICK_EDIT_ED_DATA: PulseData | None = None
#     ↑ 把上面这句的 None 改成 [(time, power), ...] 即可


# ── 示例 1: 简单三段脉冲 (200ps 上升到 3e14, 1ns 结束) ──
# _QUICK_EDIT_ED_DATA = [
#     (0.0, 0.0),         # ed_time=0       ed_power=0
#     (0.2e-9, 3e14),     # ed_time=0.2ns   ed_power=3e14
#     (1.0e-9, 0.0),      # ed_time=1.0ns   ed_power=0
# ]


# ── 示例 2: 四段梯形 (200ps 上升 → 1ns 平顶 → 80ps 下降) ──
# _QUICK_EDIT_ED_DATA = [
#     (0.0, 0.0),         # 时间=0        功率=0
#     (0.2e-9, 5e14),     # 时间=0.2ns    功率=5e14   ← 上升结束
#     (1.2e-9, 5e14),     # 时间=1.2ns    功率=5e14   ← 平顶结束
#     (1.28e-9, 0.0),     # 时间=1.28ns   功率=0      ← 下降结束
# ]


# ── 示例 3: 低脚脉冲 (先 预热, 后 主脉冲) ──
_QUICK_EDIT_ED_DATA = [
    (0.0, 0.0),
    (0.1e-9, 0.9e14),
    (0.8e-9, 0.9e14),
    (0.9e-9, 1.5e14),
    (1.0e-9, 4e14),
    (1.5e-9, 5e14),
    (1.55e-9, 0.0),
]


# ── 示例 4: 长脉冲 (300ps 上升到 2e14, 2ns 平顶, 200ps 下降) ──
# _QUICK_EDIT_ED_DATA = [
#     (0.0, 0.0),
#     (0.3e-9, 2e14),
#     (2.3e-9, 2e14),
#     (2.5e-9, 0.0),
# ]


# ╔══════════════════════════════════════════════════════════════╗
# ║  上面是快速修改区，下面的代码不用动。                         ║
# ╚══════════════════════════════════════════════════════════════╝


# ============================================================
#  脉冲生成函数
# ============================================================

def make_trapezoid(
    peak_power: float = 5e14,
    rise_time: float = 0.1e-9,
    flat_time: float = 1.4e-9,
    fall_time: float = 0.08e-9,
) -> PulseData:
    """梯形方波脉冲 — 4 段: 上升 → 平顶 → 下降 → 关断"""
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
    center_time: float = 0.8e-9,
    fwhm: float = 0.5e-9,
    order: int = 4,
    n_points: int = 100,
    time_start: float = 0.0,
    time_end: float = 1.6e-9,
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
    if result and result[0][1] > 0.0:
        result.insert(0, (max(0.0, result[0][0] - 1e-12), 0.0))
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
#  统一入口 — 同时支持快速修改区、函数参数、CLI 参数
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
    """解析脉冲数据 — 优先级: 快速修改区 > 函数参数 > 自动回落

    1. _QUICK_EDIT_ED_DATA 非空 → 直接使用
    2. ed_times/ed_powers 非空 → 使用 custom
    3. 都为空 → 按 pulse_type 回落生成

    Returns:
        [(t1, p1), (t2, p2), ...]
    """
    # ★ 优先级 1: 文件顶部快速修改区
    if _QUICK_EDIT_ED_DATA is not None and len(_QUICK_EDIT_ED_DATA) > 0:
        print(f"  [pulse_shapes] ✅ 使用快速修改区数据 ({len(_QUICK_EDIT_ED_DATA)} 段)")
        return _QUICK_EDIT_ED_DATA

    # ★ 优先级 2: 函数参数
    if ed_times is not None and ed_powers is not None and len(ed_times) > 0:
        print(f"  [pulse_shapes] ✅ 使用函数参数自定义 ({len(ed_times)} 段)")
        return make_custom(ed_times, ed_powers)

    # ★ 优先级 3: 自动回落
    print(f"  [pulse_shapes] ⏩ 数据为空, 回落为 {pulse_type}")
    return gen_pulse(pulse_type, **pulse_kwargs)
