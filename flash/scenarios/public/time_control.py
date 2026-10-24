"""短跑（极短 tmax）的时间控制收缩 —— public 场景共用

为什么需要它
------------
FLASH 的时间控制参数不是独立的：

    dtmin ≤ dtinit ≤ dtmax，且 dtmax 超过 tmax 时步长会被无谓地放大，
    dtinit 大于 tmax 时第一步就跨过终止时间（"瞬间结束"）。

本项目的三个公开场景各自写死了 dtinit/dtmin/dtmax（分别 1e-15/1e-16/1e-12
与 1e-16/1e-15/1e-9），一旦把 tmax 覆盖到 **1e-13 s**（极短验证），
就会出现 `dtmax(1e-12) > tmax(1e-13)` ⇒ 物理上没意义、且部分场景
因 dtinit > tmax 直接白跑。

本模块提供唯一一份收缩规则，各场景的 par 构建器统一调用它：

    dtinit, dtmin, dtmax = fit_time_controls(tmax, dtinit, dtmin, dtmax)

★ 只在**极短验证**（tmax ≪ 场景默认值）时才会真正改变数值；
  正式仿真的 dt 组合原样保留（tmax 远大于 dtmax 时全部不变）。
"""
from __future__ import annotations

__all__ = ["fit_time_controls", "is_short_tmax"]


def is_short_tmax(tmax: float, reference: float) -> bool:
    """tmax 是否比该场景的参考时长短 3 个数量级以上（= 极短验证）。"""
    try:
        tmax = float(tmax)
        reference = float(reference)
    except (TypeError, ValueError):
        return False
    if reference <= 0:
        return False
    return tmax < reference * 1e-3


def fit_time_controls(
    tmax: float,
    dtinit: float,
    dtmin: float,
    dtmax: float,
) -> tuple[float, float, float]:
    """把 (dtinit, dtmin, dtmax) 收缩到与 tmax 相容。

    规则（保持物理设置不变，只动**数值步长控制**）：

    1. `dtmax ≤ tmax × 1.05` —— 否则 FLASH 会浪费步长去跨越 tmax；
    2. `dtinit ≤ tmax × 0.1` —— 保证第一步远小于终止时间（否则瞬间跑完）；
    3. `dtmin ≤ dtinit` —— FLASH 要求 dtmin 不大于 dtinit；
    4. `dtinit ≤ dtmax` —— 同上。

    Returns:
        (dtinit, dtmin, dtmax)
    """
    tmax = float(tmax)
    dtinit = float(dtinit)
    dtmin = float(dtmin)
    dtmax = float(dtmax)

    if tmax <= 0:
        return dtinit, dtmin, dtmax

    dtmax = min(dtmax, tmax * 1.05)
    dtinit = min(dtinit, tmax * 0.1)
    dtmin = min(dtmin, dtinit)
    # 顺序兜底：dtmin ≤ dtinit ≤ dtmax
    dtmax = max(dtmax, dtinit)
    dtinit = max(dtinit, dtmin)
    return dtinit, dtmin, dtmax
