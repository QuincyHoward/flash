"""统一网格构造 —— 两套：``(rho, Te)`` 与 ``(n_ion, Te)``。

设计（本轮范围）
----------------
三套网格**共用同一条 Te 轴**，只替换 x 轴变量：

=========  ==========================  ==============================  ==============
gid        x 轴                        换算                            备注
=========  ==========================  ==============================  ==============
``rho_Te`` ``rho [g/cm³]``              —                              原生即可
``nion_Te`` ``n_ion [1/cm³]``           ``n_ion = rho · N_A / Ā``      纯换算 → 与 ρ 一一映射
=========  ==========================  ==============================  ==============

``(n_ele, Te)`` **本轮不实现**（用户决定"后补"）。接口已按「x 轴变换函数」
参数化：新增 ``nele_Te`` 只需再加一对 ``x_from_rho`` / ``rho_from_x``
（``n_e = rho · Z̄(ρ,T) · N_A / Ā``，需在每个 Te 列上对 ρ 做一维反演），
``writer`` 与 ``interpolate`` 无需改动。
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable, Iterable

from .. import config
from .monotonic import make_log_uniform

__all__ = [
    "GRID_IDS",
    "UnifiedGrid",
    "x_from_rho",
    "rho_from_x",
    "build_grid",
    "build_grid_for_tables",
    "build_all_grids",
    "data_ranges",
]

#: 本轮实现的两套；``nele_Te`` 为后补预留
GRID_IDS = ("rho_Te", "nion_Te")


def x_from_rho(gid: str, rho: float, A: float | None) -> float:
    """把 ρ 换算成该 gid 的 x 坐标。"""
    if gid == "rho_Te":
        return rho
    if gid == "nion_Te":
        a = A if (A and A > 0) else float("nan")
        return rho * config.N_A / a
    raise KeyError(f"unknown grid id: {gid!r} (nele_Te 为后补项，尚未实现)")


def rho_from_x(gid: str, x: float, A: float | None) -> float:
    """把 x 坐标反算回 ρ（``nion_Te`` 下是一一映射，故可精确反算）。"""
    if gid == "rho_Te":
        return x
    if gid == "nion_Te":
        a = A if (A and A > 0) else float("nan")
        return x * a / config.N_A
    raise KeyError(f"unknown grid id: {gid!r}")


@dataclass
class UnifiedGrid:
    """一套统一网格。"""

    gid: str
    x_axis: str
    x: list[float]
    Te: list[float]
    attrs: dict = field(default_factory=dict)

    @property
    def n_x(self) -> int:
        return len(self.x)

    @property
    def n_Te(self) -> int:
        return len(self.Te)

    def describe(self) -> str:
        return (f"{self.gid}: x={self.x_axis}[{self.x[0]:.4g},{self.x[-1]:.4g}]×{self.n_x} "
                f"Te[{self.Te[0]:.4g},{self.Te[-1]:.4g}]×{self.n_Te} eV")


def data_ranges(tables: Iterable) -> dict[str, tuple[float, float]]:
    """求一组表在 (rho, Te) 上的**交集**范围（忽略非有限与非正值）。"""
    lo_r = lo_t = float("inf")
    hi_r = hi_t = 0.0
    found_r = found_t = False
    for t in tables:
        for key, is_rho in (("rho", True), ("Te", False)):
            ax = t.axes.get(key)
            if not ax:
                continue
            fin = [v for v in ax if v == v and v not in (float("inf"), float("-inf")) and v > 0]
            if not fin:
                continue
            if is_rho:
                lo_r, hi_r = min(lo_r, min(fin)), max(hi_r, max(fin))
                found_r = True
            else:
                lo_t, hi_t = min(lo_t, min(fin)), max(hi_t, max(fin))
                found_t = True
    out: dict[str, tuple[float, float]] = {}
    if found_r:
        out["rho"] = (lo_r, hi_r)
    if found_t:
        out["Te"] = (lo_t, hi_t)
    return out


def _clip(lo: float, hi: float, cfg_lo: float, cfg_hi: float) -> tuple[float, float]:
    return (max(lo, cfg_lo), min(hi, cfg_hi))


def build_grid(gid: str, *, rho_range: tuple[float, float],
               Te_range: tuple[float, float],
               n_x: int | None = None, n_Te: int | None = None,
               A: float | None = None, origin: str = "") -> UnifiedGrid:
    """由 ρ/Te 范围构造一套统一网格（log10 等距）。"""
    n_x = n_x or config.N_X_UNIFIED
    n_Te = n_Te or config.N_TE_UNIFIED
    lo_r, hi_r = rho_range
    lo_t, hi_t = Te_range
    if not (lo_r > 0 and hi_r > lo_r):
        raise ValueError(f"invalid rho range: {rho_range}")
    if not (lo_t > 0 and hi_t > lo_t):
        raise ValueError(f"invalid Te range: {Te_range}")

    rho_axis = make_log_uniform(lo_r, hi_r, n_x)
    Te_axis = make_log_uniform(lo_t, hi_t, n_Te)
    x_axis = "rho" if gid == "rho_Te" else ("n_ion" if gid == "nion_Te" else gid)
    x_vals = [x_from_rho(gid, r, A) for r in rho_axis]
    attrs = {
        "x_axis": x_axis,
        "x_min": x_vals[0],
        "x_max": x_vals[-1],
        "n_x": n_x,
        "Te_min_eV": Te_axis[0],
        "Te_max_eV": Te_axis[-1],
        "n_Te": n_Te,
        "spacing": config.UNIFIED_SPACING,
        "nan_semantics": config.NAN_SEMANTICS,
        "origin": origin or "tables-intersection",
        "A_amu": A,
    }
    return UnifiedGrid(gid=gid, x_axis=x_axis, x=x_vals, Te=Te_axis, attrs=attrs)


def can_build(range_: tuple[float, float]) -> bool:
    """一个轴范围是否**可用**（正、有限、严格递增）。

    ★ 实测反例：``Thermos/mat_Mo/Mo_Ideal_Gas`` 的 rho 网格是 ``[0.0, 1.0]``
    —— ``data_ranges`` 过滤掉非正值后只剩 ``1.0``，范围退化成 ``(1.0, 1.0)``。
    这种表**不该硬造一个网格**（造出来的 rho 轴只有一个点，毫无意义），
    应当**缺轨**并记 warning。这是本项目"宁可缺，不造假"纪律在网格层的落点。
    """
    lo, hi = range_
    if not (math.isfinite(lo) and math.isfinite(hi)):
        return False
    return lo > 0 and hi > lo


def build_grid_for_tables(tables, *, gid: str, A: float | None = None,
                          n_x: int | None = None, n_Te: int | None = None,
                          rho_range: tuple[float, float] | None = None,
                          Te_range: tuple[float, float] | None = None,
                          origin: str = "") -> UnifiedGrid | None:
    """由一组表的原生范围（取交集）构造统一网格，并按物理包络裁剪。

    范围退化（只有一个有效点 / 非正 / 非有限）时返回 ``None`` ——
    **不抛异常、也不硬造网格**。调用方（:func:`build_all_grids`）会略过该 gid。
    """
    rng = data_ranges(tables)
    if rho_range is None:
        rho_range = rng.get("rho", (config.RHO_MIN_G_CM3, config.RHO_MAX_G_CM3))
    if Te_range is None:
        Te_range = rng.get("Te", (config.TE_MIN_EV, config.TE_MAX_EV))
    rho_range = _clip(rho_range[0], rho_range[1],
                      config.RHO_MIN_G_CM3, config.RHO_MAX_G_CM3)
    Te_range = _clip(Te_range[0], Te_range[1], config.TE_MIN_EV, config.TE_MAX_EV)
    if not (can_build(rho_range) and can_build(Te_range)):
        return None
    return build_grid(gid, rho_range=rho_range, Te_range=Te_range,
                      n_x=n_x, n_Te=n_Te, A=A, origin=origin or "tables-intersection")


def build_all_grids(tables, *, A: float | None = None,
                    n_x: int | None = None, n_Te: int | None = None
                    ) -> dict[str, UnifiedGrid]:
    """构造本轮全部统一网格（两套）。

    ★ 退化的轴范围会被**略过**（返回的 dict 里就没有那个 gid），
    使 h5 少一条 unified 轨而不是写出一堆无意义的点。
    """
    out: dict[str, UnifiedGrid] = {}
    for gid in GRID_IDS:
        g = build_grid_for_tables(tables, gid=gid, A=A, n_x=n_x, n_Te=n_Te)
        if g is not None:
            out[gid] = g
    return out
