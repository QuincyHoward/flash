"""EOS 反演转换 —— 把 F1 的 ``(rho, de)`` 表转成 ``(rho, Te)`` 表。

为什么需要
----------
F1（"Inverted EOS"）存的是 **P(rho, de) / T(rho, de)**（自变量是密度与比能）。
要做 ``(rho, Te)`` 统一网格，必须**再反演一次**：对每个 ``(rho, Te)`` 求出对应的
``de``，再在该 ``de`` 上取值。这正是 ``doc/MULTI使用的SESAME数据文件格式.docx``
里描述的 ``P(R,T), E(R,T) ← P(R,E), T(R,E)`` 转换。

算法
----
对每个密度列 ``j``（共 ``nr`` 列）：
1. 取该列的温度序列 ``T[:, j]``（随 ``de`` 单调升）；
2. 在 ``(log10 T, log10 de)`` 空间对目标 ``Te`` 做一维线性插值 → ``de*(Te)``；
3. 在该 ``de*`` 上对 ``P[:, j]`` / ``E[:, j]`` 插值。
超出该列温度范围的目标点 → ``NaN``（不静默外插）。
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .. import config

__all__ = ["InversionResult", "to_Te_grid", "is_de_based"]


@dataclass
class InversionResult:
    """反演结果：``(rho, Te)`` 网格上的场。"""

    Te: list[float]
    rho: list[float]
    fields: dict[str, np.ndarray]      # name -> (n_Te, n_rho)
    out_of_range: int = 0
    notes: list[str] = None

    @property
    def coverage(self) -> float:
        tot = sum(v.size for v in self.fields.values()) or 1
        return 1.0 - self.out_of_range / tot


def is_de_based(table) -> bool:
    """该表是否以 ``de``（比能）为自变量（F1 家族特征）。"""
    return "de" in getattr(table, "axes", {}) and "Te" not in getattr(table, "axes", {})


def _as2d(flat, shape):
    a = np.asarray(flat, dtype=float)
    return a.reshape(shape)


def _log10_or_nan(a: np.ndarray) -> np.ndarray:
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(a > 0, np.log10(np.where(a > 0, a, 1.0)), np.nan)


def to_Te_grid(table, Te_targets, *, fields=("P", "E", "T"),
               log_value: tuple[str, ...] = ("P",)) -> InversionResult:
    """把 ``de`` 基的表反演到 ``(rho, Te_targets)``。

    :param log_value: 哪些场在插值时取 log10（压力通常取，能量可能有负值故不取）
    :returns: :class:`InversionResult`
    """
    if not is_de_based(table):
        raise ValueError(f"table {table.table_key!r} is not de-based")
    rho = np.asarray(table.axes["rho"], dtype=float)
    de = np.asarray(table.axes["de"], dtype=float)
    ne, nr = table.field_shape.get("P", (len(de), len(rho)))
    if (ne, nr) != (len(de), len(rho)):
        raise ValueError(f"shape mismatch: field {(ne, nr)} vs axes {(len(de), len(rho))}")

    T = _as2d(table.fields["T"], (ne, nr))         # eV
    mats: dict[str, np.ndarray] = {}
    for nm in fields:
        if nm in table.fields:
            mats[nm] = _as2d(table.fields[nm], (ne, nr))

    Te_q = np.asarray(Te_targets, dtype=float)
    logTe_q = _log10_or_nan(Te_q)
    log_de = _log10_or_nan(de)

    out = {nm: np.full((Te_q.size, nr), np.nan) for nm in mats}
    n_oor = 0
    notes: list[str] = [
        f"反演 {table.table_key}: {ne}×{nr} (de,rho) -> {Te_q.size}×{nr} (Te,rho)",
    ]
    for j in range(nr):
        logT_col = _log10_or_nan(T[:, j])
        ok = np.isfinite(logT_col) & np.isfinite(log_de)
        if ok.sum() < 2:
            continue
        xs = logT_col[ok]
        ys = log_de[ok]
        o = np.argsort(xs)
        xs, ys = xs[o], ys[o]
        # 该列温度范围外的目标点 → NaN
        inside = (logTe_q >= xs[0]) & (logTe_q <= xs[-1])
        n_oor += int((~inside).sum())
        log_de_star = np.interp(logTe_q, xs, ys, left=np.nan, right=np.nan)
        for nm, M in mats.items():
            col = M[:, j][ok][o]
            if nm in log_value:
                yv = _log10_or_nan(col)
                val = np.interp(log_de_star, ys, np.nan_to_num(yv, nan=0.0),
                                left=np.nan, right=np.nan)
                with np.errstate(over="ignore"):
                    val = np.power(10.0, val)
            else:
                val = np.interp(log_de_star, ys, col, left=np.nan, right=np.nan)
            out[nm][:, j] = np.where(inside, val, np.nan)

    for nm, arr in out.items():
        n_oor_bad = int(np.isnan(arr).sum())
        notes.append(f"  场 {nm}: NaN（越界）{n_oor_bad}/{arr.size}")
    notes.append(f"  温度范围外目标点合计 {n_oor}")
    return InversionResult(Te=list(Te_q), rho=list(rho), fields=out,
                           out_of_range=sum(int(np.isnan(a).sum()) for a in out.values()),
                           notes=notes)
