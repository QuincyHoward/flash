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

__all__ = ["InversionResult", "DeGridResult", "to_Te_grid", "to_de_grid",
           "is_de_based", "cn4_eos_to_rho_base", "cn4_opac_to_rho_base"]


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


# ── 正演反演：(rho, Te) 基 -> (rho, de) 基（cn4 → F1 的核心步骤） ──

@dataclass
class DeGridResult:
    """正演反演结果：``(rho, de)`` 网格上的场。"""

    de: list[float]
    rho: list[float]
    fields: dict[str, np.ndarray]      # name -> (n_de, n_rho)
    out_of_range: int = 0
    notes: list[str] = None

    @property
    def coverage(self) -> float:
        tot = sum(v.size for v in self.fields.values()) or 1
        return 1.0 - self.out_of_range / tot


def to_de_grid(table, de_targets, *, value_fields=("P",),
               energy_field="E", log_value=("P",),
               extrapolate: str = "edge") -> DeGridResult:
    """把 ``(rho, Te)`` 基的表正演反演到 ``(rho, de_targets)``。

    与 :func:`to_Te_grid` 互为逆操作：源表自变量是 ``(rho, Te)``，
    能量 ``E(rho, T)`` 随 T 单调增；对每个密度列 ``j`` 在
    ``(log10 E, log10 T)`` 空间反解 ``T(E)``，并**用同一插值权重**
    对 ``value_fields``（如 ``P``）插值，保证 P/T 自洽。

    :param energy_field: 用作能量自变量的场名（缺省 ``"E"``；
        若源表能量就是温度轴本身——cn4 情形——由调用方先合成该场，
        或传 ``energy_field=None`` 且源表有 ``axes["Te"]``，
        此时把 Te 轴沿 rho 复制为能量场、把目标 ``de_targets`` 当作能量轴）
    :param extrapolate: ``"edge"``（端点常值延拓，记入 notes）或 ``"nan"``
        （越界置 NaN，与 to_Te_grid 一致）。F1 文件不允许 NaN，
        生成整表时通常取 ``"edge"``。
    """
    rho = np.asarray(table.axes["rho"], dtype=float)
    Te = np.asarray(table.axes["Te"], dtype=float)
    nt, nr = table.field_shape.get("P", (len(Te), len(rho)))
    if (nt, nr) != (len(Te), len(rho)):
        raise ValueError(f"shape mismatch: field {(nt, nr)} vs axes {(len(Te), len(rho))}")

    if energy_field is None:
        E = np.tile(Te[:, None], (1, nr))          # 能量=温度轴（单位 eV）
    else:
        if energy_field not in table.fields:
            raise ValueError(f"missing energy field {energy_field!r}")
        E = _as2d(table.fields[energy_field], (nt, nr))
    T = Te[:, None] * np.ones((1, nr))             # T 场即 Te 轴

    mats: dict[str, np.ndarray] = {}
    for nm in value_fields:
        if nm not in table.fields:
            raise ValueError(f"missing value field {nm!r}")
        mats[nm] = _as2d(table.fields[nm], (nt, nr))

    de_q = np.asarray(de_targets, dtype=float)
    log_de_q = _log10_or_nan(de_q)

    out = {nm: np.full((de_q.size, nr), np.nan) for nm in mats}
    T_out = np.full((de_q.size, nr), np.nan)
    notes: list[str] = [
        f"正演反演 {table.table_key}: {nt}x{nr} (Te,rho) -> "
        f"{de_q.size}x{nr} (de,rho); extrapolate={extrapolate}",
    ]
    for j in range(nr):
        logE_col = _log10_or_nan(E[:, j])
        ok = np.isfinite(logE_col) & np.isfinite(_log10_or_nan(T[:, j]))
        if ok.sum() < 2:
            continue
        xs = logE_col[ok]
        o = np.argsort(xs)
        xs = xs[o]
        logT = _log10_or_nan(T[:, j])[ok][o]
        inside = (log_de_q >= xs[0]) & (log_de_q <= xs[-1])
        n_oor_col = int((~inside).sum())
        logT_star = np.interp(log_de_q, xs, logT,
                              left=logT[0] if extrapolate == "edge" else np.nan,
                              right=logT[-1] if extrapolate == "edge" else np.nan)
        T_out[:, j] = np.power(10.0, logT_star)
        for nm, M in mats.items():
            col = M[:, j][ok][o]
            if nm in log_value:
                yv = _log10_or_nan(col)
                val = np.interp(log_de_q, xs, yv,
                                left=yv[0] if extrapolate == "edge" else np.nan,
                                right=yv[-1] if extrapolate == "edge" else np.nan)
                with np.errstate(over="ignore"):
                    val = np.power(10.0, val)
            else:
                val = np.interp(log_de_q, xs, col,
                                left=col[0] if extrapolate == "edge" else np.nan,
                                right=col[-1] if extrapolate == "edge" else np.nan)
            out[nm][:, j] = val
        if n_oor_col and extrapolate == "edge":
            notes.append(f"  rho 列 {j}: {n_oor_col} 点越界（端点延拓）")

    n_nan = sum(int(np.isnan(a).sum()) for a in list(out.values()) + [T_out])
    if extrapolate == "edge":
        notes.append(f"NaN 合计 {n_nan}（edge 模式应≈0）")
    fields_out = dict(out)
    fields_out["T"] = T_out
    return DeGridResult(de=list(de_q), rho=list(rho), fields=fields_out,
                        out_of_range=n_nan, notes=notes)


# ── cn4 轴适配：nion (cm^-3) -> rho (g/cm3) ──────────────────────

def _cn4_rho_axis(table, avgatw: float) -> list:
    """由离子数密度轴与平均原子量 ``<A>`` 求质量密度轴（g/cm3）。"""
    if avgatw is None or avgatw <= 0:
        raise ValueError("cn4 轴适配需要 avgatw（<A>）；源表无 atomwt 时不可转换")
    return [n * avgatw / config.N_A for n in table.axes["nion"]]


def _check_rho_const(rho2d, nt: int, nr: int) -> list:
    """cn4 的 rho 派生场每列（同一 nion）应常值；取第 0 行作为轴。"""
    m = _as2d(rho2d, (nt, nr))
    ref = m[0, :]
    if not np.allclose(m, ref[None, :], rtol=1e-9, atol=0.0):
        raise ValueError("rho 派生场并非沿 Te 常值，nion->rho 轴替换不成立")
    return [float(x) for x in ref]


def cn4_eos_to_rho_base(table, *, table_id=None):
    """把 cn4 EOS 总表（轴 ``nion``×``Te``）适配为 ``rho``×``Te`` 基表。

    - ``rho`` 轴取自派生场 ``rho`` 的第 0 行（校验沿 Te 常值）；
    - 场 ``P``(J/cm3)/``E``(J/g) 原样保留，单位换算由调用方/writer 负责；
    - 返回新 ``ParsedTable``，``notes`` 记录轴替换动作。
    """
    from ..parsers.base import ParsedTable as _PT

    nt, nr = table.field_shape["P"]
    rho_axis = _check_rho_const(table.fields["rho"], nt, nr)
    new = _PT(
        table_key=f"{table.table_key}_rho_base",
        kind=table.kind, family=table.family,
        source_relpath=table.source_relpath, table_id=table.table_id if table_id is None else table_id,
        header_raw=table.header_raw,
        layout_rule=table.layout_rule + " + axis nion->rho (rho=nion*<A>/N_A)",
        unit_source=table.unit_source,
        notes=list(table.notes) + ["轴 nion(cm^-3) 替换为 rho(g/cm3)，rho 派生场第 0 行"],
    )
    new.axes["rho"] = rho_axis
    new.axis_units["rho"] = "g/cm3"
    new.axis_log10["rho"] = False
    new.axes["Te"] = list(table.axes["Te"])
    new.axis_units["Te"] = "eV"
    new.axis_log10["Te"] = False
    for nm in ("P", "E", "T", "zbar"):
        if nm in table.fields:
            new.fields[nm] = list(table.fields[nm])
            new.field_shape[nm] = table.field_shape[nm]
            new.field_units[nm] = table.field_units.get(nm, "")
            new.field_log10[nm] = table.field_log10.get(nm, False)
    return new


def cn4_opac_to_rho_base(table, avgatw: float):
    """把 cn4 不透明度表（轴 ``nion``×``Te``）适配为 ``rho``×``Te`` 基表。

    场值（cm2/g，线性）原样保留；是否取 log10 由 F2 writer 路径决定。
    """
    from ..parsers.base import ParsedTable as _PT

    new = _PT(
        table_key=f"{table.table_key}_rho_base",
        kind=table.kind, family=table.family,
        source_relpath=table.source_relpath,
        header_raw=table.header_raw,
        layout_rule=table.layout_rule + " + axis nion->rho (rho=nion*<A>/N_A)",
        unit_source=table.unit_source,
        n_groups=table.n_groups, group_bounds=list(table.group_bounds or []),
        notes=list(table.notes) + ["轴 nion(cm^-3) 替换为 rho(g/cm3)（rho=nion*<A>/N_A）"],
    )
    new.axes["rho"] = _cn4_rho_axis(table, avgatw)
    new.axis_units["rho"] = "g/cm3"
    new.axis_log10["rho"] = False
    new.axes["Te"] = list(table.axes["Te"])
    new.axis_units["Te"] = "eV"
    new.axis_log10["Te"] = False
    for nm, shp in table.field_shape.items():
        new.fields[nm] = list(table.fields[nm])
        new.field_shape[nm] = shp
        new.field_units[nm] = table.field_units.get(nm, "")
        new.field_log10[nm] = table.field_log10.get(nm, False)
    return new
