"""二维重采样 —— 以 ``(log10 x, log10 Te)`` 为插值空间的双线性插值。

约定
----
* 源数组形状统一为 ``(n_Te, n_x)``（与 ``ParsedTable.field_shape`` 一致）。
* 插值空间按量选择：``x`` 用 ``log10``，``Te`` 用 ``log10``；
  被插值的量：``kappa`` 用 ``log10``（本源数据即对数），``P``/``E``/``Z`` 用线性。
* **越界 → NaN**（默认；可配 ``clamp`` / ``linear``）。NaN 只表示"落在原生凸包之外"，
  与"值恰为 0"严格区分。
* 返回 ``out_of_range`` 计数，写入 ``unified/<gid>/attrs``。

实现用 numpy 的 ``np.interp`` 逐行/逐列做一维线性插值（等价于双线性），
越界由 ``left=right=nan`` 直接表达 —— 不需要额外掩码逻辑。
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .. import config

__all__ = ["ResampleResult", "resample_2d", "resample_1d", "to_array2d",
           "log10_or_nan"]


@dataclass
class ResampleResult:
    """一次重采样的结果与质量指标。"""

    values: np.ndarray
    out_of_range: int = 0
    method: str = config.INTERP_METHOD
    extrapolation: str = config.EXTRAPOLATION
    notes: list[str] = field(default_factory=list)

    @property
    def n_total(self) -> int:
        return int(self.values.size)

    @property
    def coverage(self) -> float:
        if self.n_total == 0:
            return 0.0
        return 1.0 - self.out_of_range / self.n_total


def _log10_or_nan(a: np.ndarray) -> np.ndarray:
    with np.errstate(divide="ignore", invalid="ignore"):
        out = np.where(a > 0, np.log10(np.where(a > 0, a, 1.0)), np.nan)
    return out.astype(float)


def log10_or_nan(values) -> np.ndarray:
    """公开别名：对非正值返回 ``NaN``（不返回 ``-inf``，便于与"越界"区分）。"""
    return _log10_or_nan(np.asarray(values, dtype=float))


def _interp_1d(xs: np.ndarray, yv: np.ndarray, xq: np.ndarray,
               extrapolation: str) -> np.ndarray:
    """一维线性插值；越界按 ``extrapolation`` 处理。"""
    if xs.size < 2:
        return np.full(xq.shape, np.nan)
    if extrapolation == "nan":
        return np.interp(xq, xs, yv, left=np.nan, right=np.nan)
    if extrapolation == "clamp":
        return np.interp(xq, xs, yv)
    if extrapolation == "linear":
        out = np.interp(xq, xs, yv)
        lo = xq < xs[0]
        hi = xq > xs[-1]
        if lo.any():
            slope = (yv[1] - yv[0]) / (xs[1] - xs[0])
            out = np.where(lo, yv[0] + slope * (xq - xs[0]), out)
        if hi.any():
            slope = (yv[-1] - yv[-2]) / (xs[-1] - xs[-2])
            out = np.where(hi, yv[-1] + slope * (xq - xs[-1]), out)
        return out
    raise ValueError(f"unknown extrapolation: {extrapolation!r}")


def to_array2d(values, shape: tuple[int, int]) -> np.ndarray:
    """把 ``ParsedTable`` 的展平列表还原成 ``(n_Te, n_x)`` 数组。"""
    arr = np.asarray(values, dtype=float)
    if arr.size != shape[0] * shape[1]:
        raise ValueError(f"size {arr.size} != shape {shape}")
    return arr.reshape(shape)


def resample_2d(x_src, y_src, v_src, x_dst, y_dst, *,
                logs: tuple[str, ...] = ("x", "y"),
                log_value: bool = False,
                extrapolation: str | None = None) -> ResampleResult:
    """把 ``v_src(y_src, x_src)`` 双线性重采样到 ``v(x_dst, y_dst)``。

    :param logs: 哪些轴取 log10（``"x"`` / ``"y"``）
    :param log_value: 值本身是否取 log10（``kappa`` 族为 True）
    :returns: :class:`ResampleResult`，``values`` 形状 ``(len(y_dst), len(x_dst))``
    """
    ext = extrapolation or config.EXTRAPOLATION
    xs = np.asarray(x_src, dtype=float)
    ys = np.asarray(y_src, dtype=float)
    xq = np.asarray(x_dst, dtype=float)
    yq = np.asarray(y_dst, dtype=float)
    v = np.asarray(v_src, dtype=float)
    if v.shape != (ys.size, xs.size):
        raise ValueError(f"v shape {v.shape} != (n_y,n_x)=({ys.size},{xs.size})")

    X = _log10_or_nan(xs) if "x" in logs else xs
    Y = _log10_or_nan(ys) if "y" in logs else ys
    XQ = _log10_or_nan(xq) if "x" in logs else xq
    YQ = _log10_or_nan(yq) if "y" in logs else yq
    V = _log10_or_nan(v) if log_value else v

    # 单调性由调用方（monotonic.diagnose_axis）保证；这里只做保序排序
    xo = np.argsort(X)
    yo = np.argsort(Y)
    X, V = X[xo], V[:, xo]
    Y, V = Y[yo], V[yo, :]

    n_out = 0
    # ① 沿 x 逐行插值 → (n_y, n_xq)
    vx = np.empty((V.shape[0], XQ.size), dtype=float)
    for i in range(V.shape[0]):
        vx[i] = _interp_1d(X, V[i], XQ, ext)
    # ② 沿 y 逐列插值 → (n_yq, n_xq)；越界计数以**最终结果**为准
    out = np.empty((YQ.size, XQ.size), dtype=float)
    for j in range(XQ.size):
        col = _interp_1d(Y, vx[:, j], YQ, ext)
        out[:, j] = col
        n_out += int(np.isnan(col).sum())

    if log_value:
        with np.errstate(over="ignore", invalid="ignore"):
            out = np.power(10.0, out)

    return ResampleResult(values=out, out_of_range=n_out, extrapolation=ext)


def resample_1d(x_src, v_src, x_dst, *, log_x: bool = True,
                log_value: bool = False,
                extrapolation: str | None = None) -> ResampleResult:
    """一维重采样（用于 ColdOpacity 的 ``mu(photon_eV)``）。"""
    ext = extrapolation or config.EXTRAPOLATION
    xs = np.asarray(x_src, dtype=float)
    v = np.asarray(v_src, dtype=float)
    xq = np.asarray(x_dst, dtype=float)
    X = _log10_or_nan(xs) if log_x else xs
    XQ = _log10_or_nan(xq) if log_x else xq
    V = _log10_or_nan(v) if log_value else v
    o = np.argsort(X)
    out = _interp_1d(X[o], V[o], XQ, ext)
    n_out = int(np.isnan(out).sum())
    if log_value:
        with np.errstate(over="ignore", invalid="ignore"):
            out = np.power(10.0, out)
    return ResampleResult(values=out, out_of_range=n_out, extrapolation=ext)
