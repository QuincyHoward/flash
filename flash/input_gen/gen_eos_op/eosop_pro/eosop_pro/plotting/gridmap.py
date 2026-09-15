# -*- coding: utf-8 -*-
"""统一绘图模块 —— 通用二维彩图 / 一维曲线原语 + 任意 ParsedTable 批量出图。

定位（用户 2026-09-15 规约）
----------------------------
cn4 专用绘图（:mod:`..cn4.cn4_plots`）里的**绘图原语**已上提至此，
任何 eosop 文件类型（F1~F6 全部族的 :class:`~..parsers.base.ParsedTable`）
都可以直接调用本模块画出「cn4 同款」图像：

* :func:`plot_heatmap` —— 二维彩图原语（log/linear 轴、log/linear 色标、
  NaN 白色占位、数据边界凸包虚线、PPT 演讲级样式）；
* :func:`plot_multi_curve` —— 一维多曲线原语（vs T / vs rho 等）；
* :func:`plot_table_all_fields` —— **批量入口**：对任意族的一组
  ParsedTable 逐场出图（2D 场画 rho-T 平面彩图 + 可导出时 ne-T 彩图 +
  截断曲线），并写 ``_report.txt``（网格点数 / 单调性 / 物理量意义 /
  单位 / checked 状态，字典来自 :mod:`..registry.field_checks`）。

纪律
----
* 样式常量唯一来源 :mod:`..config`；全 ASCII 文本由
  :func:`.style.assert_ascii` 在落盘前强校验；
* 每张图落盘后立即 ``close``（run_all 同进程执行，figure 不得泄漏）；
* ne-T 等**派生轴**只在物理可导出时绘制（需电离度场 + 显式 ``atomwt``），
  缺依据时**跳过并写明原因**，绝不猜测；
* **认证标记显示规约**（用户 2026-09-15 第二次裁定 + 第十二轮）：标记
  只有 ``uk``（无来源确认）/ ``uv``（未人工核查）两个，有源且已核查
  **整体省略**（当前仅 cn4）—— 例如 ``P (Mbar), uv``。所有轴 /
  colorbar / ylabel 标签一律经 :mod:`.labels`（字典驱动统一出口）实时
  取意义/单位/标记 —— 人工核查翻 ``checked`` 后**下一次出图自动同步**，
  本模块不再硬编码任何物理量标签。报告 ``_report.txt`` 的轴/字段行
  同规约；
* **raw 数值兜底**（用户 2026-09-15）：字段与轴的形状/长度不匹配而无法
  按语义绘图的，**不再静默跳过** —— 改画 ``raw values vs element index``
  序列图（数值本身永远可画），图与报告明确标注 semantics unknown；
  物理量意义与单位未知不妨碍"读出数值、画出数值"。
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Sequence

import numpy as np

from .. import config
from ..registry.field_checks import field_check, tags_label
from .labels import display_unit, field_label, tags_of

__all__ = [
    "plot_heatmap", "plot_multi_curve", "plot_table_all_fields",
    "CHARGE_FIELD_CANDIDATES", "sanitize_name",
]

#: 可作「平均电离度」解释的场名候选（ne-T 派生轴的前提之一）。
#: 仅当族文档明确其为 Zbar 等价量时才成立（如 mpqeos 的 ``Z``、
#: ledcop_zeff 的 ``NoFree``）；其余族不猜。
CHARGE_FIELD_CANDIDATES: tuple[str, ...] = ("Z", "zbar", "Zbar", "Zeff", "NoFree")

#: 温度轴的候选名（按优先级）。
_TE_CANDIDATES: tuple[str, ...] = ("Te", "T", "tele")

#: 批量出图的规模护栏（防单表几十群 / 几百列拖垮测试）。
MAX_MAP_FIELDS_PER_TABLE = 12
MAX_CURVE_FIELDS_PER_TABLE = 6


# ================================================================
# 通用原语
# ================================================================

def _plt():
    """惰性应用全局样式并返回 ``matplotlib.pyplot``。"""
    from .style import apply_style
    return apply_style()


def _save(fig, outfile, *, close: bool = True):
    """ASCII 强校验后落盘；``close=True`` 时立即释放 figure。"""
    from .style import assert_ascii
    outfile = Path(outfile)
    outfile.parent.mkdir(parents=True, exist_ok=True)
    assert_ascii(fig)
    fig.savefig(str(outfile), dpi=config.PLOT_DPI, bbox_inches="tight")
    if close:
        _plt().close(fig)
    return outfile


def _style_axes(ax) -> None:
    ax.tick_params(which="both", direction="in", top=True, right=True,
                   labelsize=config.PLOT_TICK_FONTSIZE, width=1.5, length=6)
    for s in ax.spines.values():
        s.set_linewidth(1.5)


def _colorbar(fig, mappable, ax, label: str):
    cb = fig.colorbar(mappable, ax=ax, fraction=0.046, pad=0.04)
    cb.set_label(label, fontsize=config.PLOT_LABEL_FONTSIZE)
    cb.ax.tick_params(labelsize=config.PLOT_TICK_FONTSIZE, width=1.5, length=6)
    cb.outline.set_linewidth(1.5)
    return cb


def plot_heatmap(
    *, x, y, field,
    xlabel: str, ylabel: str, clabel: str, title: str,
    outfile: str | Path | None = None,
    cmap: str | None = None,
    vmin: float | None = None, vmax: float | None = None,
    xlog: bool = True, ylog: bool = True, zlog: bool = False,
    figsize: tuple[float, float] = (10.0, 7.5),
    hull_xy: np.ndarray | None = None,
    nan_color: str = "white",
    close: bool = True,
    error_cls: type = ValueError,
) -> str | "matplotlib.figure.Figure":  # noqa: F821
    """二维彩图通用原语（cn4 ``_plot_heatmap`` 的上提版）。

    Args:
        x / y: 1D 轴数组（``y`` 亦可为 2D ``(len(y), len(x))`` 网格，
            用于 ``ne-T`` 这类逐点派生轴）。
        field: ``(len(y), len(x))`` 数值场（行 = y，列 = x）。
        clabel: colorbar 标签（含显示单位）。
        outfile: ``None`` 时不出盘、返回 figure（调用方自行 close）。
        zlog: 色标对数；非正值 / NaN 一律白色掩膜。
        hull_xy: 数据边界凸包顶点（可选，画灰色虚线）。
        error_cls: 无有效正值时抛出的异常类型
            （cn4 侧传 ``CN4ParseError`` 以保持既有行为）。

    Returns:
        落盘路径（``outfile`` 给出时）或 figure 对象（``outfile=None`` 时）。
    """
    import matplotlib.colors as mcolors

    plt = _plt()
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    field = np.asarray(field, dtype=float)
    ylen = y.shape[0] if y.ndim == 2 else len(y)
    if field.shape != (ylen, len(x)):
        raise ValueError(
            f"field 形状 {field.shape} != (len(y)={ylen}, len(x)={len(x)})")

    fig, ax = plt.subplots(figsize=figsize)
    X, Y = np.meshgrid(x, y) if y.ndim == 1 else (x[None, :], y)

    fplot = np.ma.masked_invalid(field)
    if zlog:
        fplot = np.ma.masked_where(fplot <= 0, fplot)
    if fplot.count() == 0:
        plt.close(fig)
        raise error_cls(f"'{clabel}' 无有效正值，无法出图")

    if zlog:
        dmin, dmax = float(fplot.min()), float(fplot.max())
        if vmin is None:
            vmin = 10.0 ** np.floor(np.log10(dmin))
        if vmax is None:
            vmax = 10.0 ** np.ceil(np.log10(dmax))
        norm = mcolors.LogNorm(vmin=vmin, vmax=vmax)
    else:
        norm = mcolors.Normalize(
            vmin=fplot.min() if vmin is None else vmin,
            vmax=fplot.max() if vmax is None else vmax)

    cm = plt.get_cmap(cmap or config.PLOT_CMAP).copy()
    cm.set_bad(nan_color)
    mesh = ax.pcolormesh(X, Y, fplot, cmap=cm, norm=norm,
                         shading="auto", rasterized=True)

    if xlog:
        ax.set_xscale("log")
    if ylog:
        ax.set_yscale("log")

    if hull_xy is not None and len(hull_xy) >= 3:
        closed = np.vstack([hull_xy, hull_xy[:1]])
        ax.plot(closed[:, 0], closed[:, 1], "--", lw=1.2,
                color="#444444", alpha=0.9, label="Data boundary")
        ax.legend(fontsize=config.PLOT_LEGEND_FONTSIZE, loc="best")

    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    _style_axes(ax)
    _colorbar(fig, mesh, ax, clabel)
    fig.tight_layout()

    if outfile is None:
        return fig
    return str(_save(fig, outfile, close=close))


def plot_multi_curve(
    curves: Sequence[tuple[str, Sequence[float], Sequence[float]]],
    *, xlabel: str, ylabel: str, title: str,
    outfile: str | Path | None = None,
    xlog: bool = True, ylog: bool | None = None,
    figsize: tuple[float, float] = (10.0, 7.5),
    close: bool = True,
    scatter: bool = False,
):
    """一维多曲线通用原语。

    Args:
        curves: ``(label, x, y)`` 序列；``y`` 含非正值且跨度大时自动对数。
        ylog: ``None`` = 按数据跨度自动（全正且跨 > 4 个量级 -> 对数）。
        scatter: ``True`` = 纯散点（marker-only，无线段）。**uk/uv 数据
            必须散点**（用户 2026-09-15 第十一轮规约：认证标记非空的数据
            画散点图便于查找规律；已核查数据保持线图）。
    """
    plt = _plt()
    fig, ax = plt.subplots(figsize=figsize)
    all_vals = []
    for label, cx, cy in curves:
        cx = np.asarray(cx, dtype=float)
        cy = np.asarray(cy, dtype=float)
        all_vals.append(cy)
        if scatter:
            ax.plot(cx, cy, lw=0, marker="o",
                    ms=config.PLOT_MARKERSIZE - 1, alpha=0.85,
                    label=str(label))
        else:
            ax.plot(cx, cy, lw=config.PLOT_LINEWIDTH, marker="o",
                    ms=config.PLOT_MARKERSIZE - 2, label=str(label))
    if xlog:
        ax.set_xscale("log")
    if ylog is None:
        ylog = _auto_log(np.concatenate(all_vals)) if all_vals else False
    if ylog:
        ax.set_yscale("log")

    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.grid(True, which="both", alpha=0.3)
    _style_axes(ax)
    ax.legend(fontsize=config.PLOT_LEGEND_FONTSIZE)
    fig.tight_layout()

    if outfile is None:
        return fig
    return str(_save(fig, outfile, close=close))


def _auto_log(vals: np.ndarray) -> bool:
    v = np.asarray(vals, dtype=float)
    v = v[np.isfinite(v) & (v > 0)]
    if v.size < 2:
        return False
    return bool(np.log10(v.max()) - np.log10(v.min()) > 4)


# ================================================================
# ParsedTable 批量出图（任意 eosop 族）
# ================================================================

def _unit_disp(family: str, name: str, raw: str) -> str:
    """单位 + 认证标记显示串（**字典驱动**，:func:`.labels.display_unit`）。

    单位：解析器逐文件实测值优先 -> 字典 ``unit`` -> ``unknown``；
    标记只有 ``uk``（无来源确认）/ ``uv``（未人工核查），有源且已核查
    整体省略（当前仅 cn4）—— 报告行与图上（colorbar / 曲线 ylabel）
    同规约，意义/单位/标记实时取自控制字典，人工核查后自动同步。
    """
    unit = display_unit(family, name, raw)
    tags = tags_of(family, name)
    return f"{unit}, {tags}" if tags else unit


def sanitize_name(name: str) -> str:
    """表键 / 字段名 -> 文件名安全 ASCII 串（非 [A-Za-z0-9._-] 替换 '_'）。"""
    out = "".join(c if (c.isascii() and (c.isalnum() or c in "._-"))
                  else "_" for c in str(name))
    return out.strip("_") or "table"


def _axis_report(name: str, vals: Sequence[float], unit: str) -> tuple[str, dict]:
    """轴的核查行 + 元数据（点数 / 单调性 / 对数均匀性）。"""
    v = np.asarray(vals, dtype=float)
    n = int(v.size)
    if n >= 2:
        dif = np.diff(v)
        inc = int((dif > 0).sum())
        dec = int((dif < 0).sum())
        mono = "increasing" if inc == n - 1 else (
            "decreasing" if dec == n - 1 else "NON-MONOTONIC")
        pos = v[(v > 0) & np.isfinite(v)]
        log_uniform = "n/a"
        if pos.size >= 3:
            lr = np.diff(np.log10(pos))
            log_uniform = ("yes" if np.allclose(lr, lr[0], rtol=1e-3)
                           else "no")
    else:
        mono, log_uniform = "n/a", "n/a"
    lo = float(np.nanmin(v)) if n else float("nan")
    hi = float(np.nanmax(v)) if n else float("nan")
    line = (f"axis {name!r}: N={n}, unit={unit or 'unknown'}, "
            f"range=[{lo:.6g}, {hi:.6g}], monotonic={mono}, log-uniform={log_uniform}")
    return line, {"name": name, "n": n, "unit": unit, "mono": mono}


def _resolve_charge(table, charge_name: str) -> np.ndarray | None:
    """取电离度场为 2D (n_te, n_x)；不存在 / 非 2D 返回 None。"""
    if charge_name not in table.fields:
        return None
    flat = table.fields[charge_name]
    shape = table.field_shape.get(charge_name)
    if not shape or len(shape) != 2 or not isinstance(flat, (list, tuple)):
        return None
    return np.asarray(flat, dtype=float).reshape(shape)


def _derive_ne(table, charge: np.ndarray, atomwt: float) -> tuple[np.ndarray, str] | None:
    """由 ``rho`` 轴 + 电离度场派生 n_e (cm^-3) 2D 场。

    n_e = rho [g/cm3] * N_A [1/mol] * Zbar / A [amu]  （rho 与 T 无关的逐列缩放）
    返回 ``(ne_2d, 说明)``；轴不是 rho / 数据含非正 -> None。
    """
    from .. import config as _cfg
    rho_name = "rho" if "rho" in table.axes else None
    if rho_name is None:
        return None
    rho = np.asarray(table.axes[rho_name], dtype=float)
    n_x = charge.shape[1]
    if n_x != rho.size:
        return None
    ne = rho[None, :] * _cfg.N_A * charge / float(atomwt)
    if not np.any(ne > 0):
        return None
    return ne, f"n_e = rho * N_A * Zbar / A (A={atomwt:g} amu, N_A={_cfg.N_A:.1e})"


def plot_table_all_fields(
    tables: Iterable,
    outdir: str | Path,
    *,
    family: str | None = None,
    atomwt: float | None = None,
    max_groups: int = 3,
    max_tables: int = 6,
    cmap: str | None = None,
) -> dict:
    """对任意 eosop 族的一组 ParsedTable 批量出「cn4 同款」图像。

    每张表一个子目录（按 ``table_key`` 消毒命名）；产物：

    * 2D 场 -> 彩图：``<field>_rho-T.png``（原生 (rho, Te) 平面；
      F1 类无 Te 轴的表画在其原生 (de, rho) 平面并注明）；
      可导出 n_e 时另有 ``<field>_ne-T.png``（2D 逐点派生轴，不插值）；
    * 3D 群场 -> 前 ``max_groups`` 群逐群彩图 ``<field>_g<k>_rho-T.png``；
    * 2D 场 -> 截断曲线 ``<field>_vs_T.png`` / ``<field>_vs_rho.png``；
    * 1D 表 -> 每场一条 log-log 曲线；
    * ``_report.txt`` —— 网格点 / 单调性 / 物理量意义 / 单位 / checked
      状态（:mod:`..registry.field_checks`）与出图清单（跳过附原因）。

    Returns:
        ``{"outdir", "family", "n_tables", "n_plots", "plots", "skipped",
        "tables_truncated", "reports"}``
    """
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    tables = list(tables)
    fam = family or (getattr(tables[0], "family", "") if tables else "")

    plots: list[str] = []
    skipped: list[str] = []
    reports: list[str] = []
    truncated = len(tables) > max_tables

    for ti, tbl in enumerate(tables[:max_tables]):
        sub = outdir / sanitize_name(f"{ti:02d}_{tbl.table_key}")
        sub.mkdir(parents=True, exist_ok=True)
        rep_lines: list[str] = [f"=== {tbl.family}/{tbl.kind} table_key={tbl.table_key} ==="]
        rep_lines.append(f"source_relpath: {tbl.source_relpath}")
        if getattr(tbl, "unit_source", ""):
            rep_lines.append(f"unit_source: {tbl.unit_source}")
        if getattr(tbl, "layout_rule", ""):
            rep_lines.append(f"layout_rule: {tbl.layout_rule}")

        # ── 轴与网格核查 ──
        axis_meta: dict[str, dict] = {}
        for name, vals in tbl.axes.items():
            line, meta = _axis_report(name, vals, tbl.axis_units.get(name, ""))
            fc_ax = field_check(fam, name)
            tags_ax = tags_label(fc_ax)
            if tags_ax:
                line += f"  [tags={tags_ax.replace(', ', ',')}]"
            rep_lines.append(line)
            axis_meta[name] = meta

        # ── 坐标轴选择：Te 优先；无 Te 时取非 rho 轴（F1 (rho,de) 基） ──
        te_name = next((k for k in _TE_CANDIDATES if k in tbl.axes), None)
        other_names = [k for k in tbl.axes if k != te_name]
        if te_name is not None and other_names:
            x_name, y_name = te_name, other_names[0]
        elif len(tbl.axes) == 2:
            y_name = "rho" if "rho" in tbl.axes else sorted(tbl.axes)[0]
            x_name = next(k for k in tbl.axes if k != y_name)
            rep_lines.append(
                f"note: no Te axis -> maps drawn on native ({x_name}, {y_name}) plane")
        else:
            x_name = y_name = None

        def _ax_label(name: str) -> str:
            """轴标签（**带认证标记**，字典驱动 :func:`.labels.field_label`）。

            格式 ``Meaning (unit)`` 或 ``Meaning (unit), <tags>`` —— 标记
            只有 ``uk``（无来源）/``uv``（未核查），有源且已核查则整体
            省略（用户 2026-09-15 规约）；意义/单位实时取自控制字典，
            轴与场量同规约，人工核查后自动同步。
            """
            return field_label(fam, name,
                               parser_unit=tbl.axis_units.get(name, ""))

        # 轴数组提前取好（2D/3D 分支共用；1D 表为 None）
        xv = np.asarray(tbl.axes[x_name], float) if x_name else None
        yv = np.asarray(tbl.axes[y_name], float) if y_name else None

        # ── 电离度场与 ne 派生轴（仅当显式给 atomwt） ──
        ne_cache: dict[str, tuple[np.ndarray, str] | None] = {}
        charge_name = next((c for c in CHARGE_FIELD_CANDIDATES if c in tbl.fields), None)
        if charge_name is not None:
            ch = _resolve_charge(tbl, charge_name)
            if ch is not None and atomwt is not None:
                got = _derive_ne(tbl, ch, atomwt)
                ne_cache[charge_name] = got
            else:
                reason = ("charge field present but atomwt (A) not provided "
                          "- n_e not derivable, skipped (no guessing)")
                ne_cache[charge_name] = None
                skipped.append(f"{tbl.table_key}: ne-T {reason}")

        # ── 逐场出图 ──
        made_here = 0
        map_count = 0
        curve_count = 0

        def _raw_fallback(fname, flat, unit, why: str):
            """语义映射失败时的 **raw 数值兜底图**（用户 2026-09-15 规约）。

            返回 ``(plot_path | None, note | None)``：成功 -> ``(路径, None)``；
            失败/超预算 -> ``(None, 跳过原因)``。物理量意义与单位未知
            不妨碍把已读出的数值画出来（semantics unknown 显式标注）。
            """
            if not isinstance(flat, (list, tuple)) or len(flat) < 2:
                return None, (f"{tbl.table_key}.{fname}: {why}; "
                              f"no plottable raw values")
            if curve_count >= MAX_CURVE_FIELDS_PER_TABLE:
                return None, (f"{tbl.table_key}.{fname}: {why}; "
                              f"raw fallback budget exhausted")
            try:
                return _plot_raw_sequence(tbl, fname, flat, sub,
                                          _unit_disp(fam, fname, unit)), None
            except Exception as exc:                          # noqa: BLE001
                return None, (f"{tbl.table_key}.{fname}: {why}; "
                              f"raw fallback failed: {exc}")

        for fname in tbl.fields:
            flat = tbl.fields[fname]
            shape = tbl.field_shape.get(fname, ())
            fc = field_check(fam, fname)
            unit = tbl.field_units.get(fname) or fc.unit or ""
            tags = tags_label(fc)
            rep_lines.append(
                f"field {fname!r}: shape={tuple(shape) or '(1d)'}, "
                f"unit={unit or 'unknown'}, "
                f"meaning='{fc.meaning}', "
                + (f"tags={tags.replace(', ', ',')}, " if tags else "")
                + f"source='{fc.source}'")

            if not isinstance(flat, (list, tuple)) or not flat:
                continue

            # ---- 3D 群场 ----
            if len(shape) == 3:
                ng = getattr(tbl, "n_groups", None)
                if ng is None or shape[0] != ng:
                    why = (f"3D field without confirmed group dim "
                           f"(shape={tuple(shape)}, n_groups={ng})")
                    p, note = _raw_fallback(fname, flat, unit, why)
                    if note:
                        skipped.append(note)
                    if p:
                        plots.append(p)
                        made_here += 1
                        curve_count += 1
                    continue
                arr = np.asarray(flat, dtype=float).reshape(shape)
                for g in range(min(int(ng), max_groups)):
                    if x_name is None:
                        break
                    f2 = arr[g]
                    f2 = f2 if f2.shape == (len(yv), len(xv)) else f2.T
                    if f2.shape != (len(yv), len(xv)):
                        skipped.append(
                            f"{tbl.table_key}.{fname}[g{g + 1}]: shape "
                            f"{tuple(shape[1:])} does not match axes - skipped")
                        continue
                    zl = _auto_zlog(f2)
                    out = sub / f"{sanitize_name(fname)}_g{g + 1}_rho-T.png"
                    try:
                        plots.append(plot_heatmap(
                            x=xv, y=yv, field=f2,
                            xlabel=_ax_label(x_name), ylabel=_ax_label(y_name),
                            clabel=(f"{field_label(fam, fname, parser_unit=unit)}"
                                    f" - group {g + 1}"),
                            title=f"{tbl.table_key}: {fname} group {g + 1}",
                            outfile=out, cmap=cmap, zlog=zl))
                        made_here += 1
                        map_count += 1
                    except Exception as exc:                      # noqa: BLE001
                        skipped.append(f"{tbl.table_key}.{fname}[g{g + 1}]: {exc}")
                continue

            # ---- 2D 场 (n_te, n_x) ----
            if len(shape) == 2 and x_name is not None:
                if map_count >= MAX_MAP_FIELDS_PER_TABLE:
                    skipped.append(
                        f"{tbl.table_key}.{fname}: map budget "
                        f"({MAX_MAP_FIELDS_PER_TABLE}) exhausted - skipped")
                    continue
                arr = np.asarray(flat, dtype=float).reshape(shape)
                f2 = arr if arr.shape == (len(yv), len(xv)) else arr.T
                if f2.shape != (len(yv), len(xv)):
                    why = (f"shape {tuple(shape)} does not match "
                           f"axes ({x_name}, {y_name})")
                    p, note = _raw_fallback(fname, flat, unit, why)
                    if note:
                        skipped.append(note)
                    if p:
                        plots.append(p)
                        made_here += 1
                        curve_count += 1
                    continue
                # 原生平面彩图（rho-T 同款）
                out = sub / f"{sanitize_name(fname)}_{y_name}-{x_name}.png"
                try:
                    plots.append(plot_heatmap(
                        x=xv, y=yv, field=f2,
                        xlabel=_ax_label(x_name), ylabel=_ax_label(y_name),
                        clabel=field_label(fam, fname, parser_unit=unit),
                        title=f"{tbl.table_key}: {fname}",
                        outfile=out, cmap=cmap, zlog=_auto_zlog(f2)))
                    made_here += 1
                    map_count += 1
                except Exception as exc:                          # noqa: BLE001
                    skipped.append(f"{tbl.table_key}.{fname}: {exc}")

                # ne-T 彩图（2D 逐点派生轴；仅当电离度场 + atomwt 齐备）
                if charge_name is not None and ne_cache.get(charge_name):
                    ne2d, how = ne_cache[charge_name]
                    # ne2d 与原始 arr 同序（rows=Te, cols=x）-> 与 f2 归一到
                    # (len(yv), len(xv)) 行=y 列=x 的绘图约定
                    ne_plot = (ne2d if ne2d.shape == (len(yv), len(xv))
                               else ne2d.T)
                    if f2.shape == ne_plot.shape:
                        out = sub / f"{sanitize_name(fname)}_ne-T.png"
                        # 派生轴同样走字典（derived_axes 族登记，实时同步）
                        ylab = field_label("derived_axes", "n_e")
                        try:
                            plots.append(plot_heatmap(
                                x=xv, y=ne_plot, field=f2,
                                xlabel=_ax_label(x_name),
                                ylabel=ylab,
                                clabel=field_label(fam, fname, parser_unit=unit),
                                title=f"{tbl.table_key}: {fname}  [{how}]",
                                outfile=out, cmap=cmap, zlog=_auto_zlog(f2)))
                            made_here += 1
                            map_count += 1
                        except Exception as exc:                  # noqa: BLE001
                            skipped.append(f"{tbl.table_key}.{fname} (ne-T): {exc}")
                elif charge_name is not None and atomwt is None and map_count == 1:
                    skipped.append(
                        f"{tbl.table_key}: ne-T maps skipped - "
                        f"charge field '{charge_name}' found but atomwt (A) not provided")

                # 截断曲线（vs x 轴 / vs y 轴；uk/uv 字段散点规约）
                if curve_count < MAX_CURVE_FIELDS_PER_TABLE:
                    curve_count += 1
                    try:
                        plots.append(_table_curves(
                            tbl, fname, f2,
                            fixed_name=y_name, fixed_vals=yv,
                            var_name=x_name, var_vals=xv, fixed_axis=0,
                            tag="vs_" + sanitize_name(x_name), sub=sub,
                            parser_unit=unit, scatter=bool(tags)))
                        made_here += 1
                    except Exception as exc:                      # noqa: BLE001
                        skipped.append(f"{tbl.table_key}.{fname} (vs x): {exc}")
                    try:
                        plots.append(_table_curves(
                            tbl, fname, f2,
                            fixed_name=x_name, fixed_vals=xv,
                            var_name=y_name, var_vals=yv, fixed_axis=1,
                            tag="vs_" + sanitize_name(y_name), sub=sub,
                            parser_unit=unit, scatter=bool(tags)))
                        made_here += 1
                    except Exception as exc:                      # noqa: BLE001
                        skipped.append(f"{tbl.table_key}.{fname} (vs y): {exc}")
                continue

            # ---- 1D 场 ----
            if len(shape) <= 1 and tbl.axes:
                ax_name = next(iter(tbl.axes))
                xv = np.asarray(tbl.axes[ax_name], float)
                yv = np.asarray(flat, dtype=float)
                if yv.size != xv.size:
                    why = (f"len {yv.size} != axis {ax_name!r} "
                           f"len {xv.size}")
                    p, note = _raw_fallback(fname, flat, unit, why)
                    if note:
                        skipped.append(note)
                    if p:
                        plots.append(p)
                        made_here += 1
                        curve_count += 1
                    continue
                out = sub / f"{sanitize_name(fname)}_curve.png"
                try:
                    plots.append(plot_multi_curve(
                        [(fname, xv, yv)],
                        xlabel=_ax_label(ax_name),
                        ylabel=field_label(fam, fname, parser_unit=unit),
                        title=f"{tbl.table_key}: {fname}", outfile=out,
                        scatter=bool(tags)))
                    made_here += 1
                except Exception as exc:                          # noqa: BLE001
                    skipped.append(f"{tbl.table_key}.{fname} (curve): {exc}")

        rep_lines.append("-- plots --")
        rep_lines += [f"[ok] {Path(p).name}" for p in plots[-made_here:]] if made_here else ["(none)"]
        rep_lines.append(f"made this table: {made_here}")
        rep = "\n".join(rep_lines)
        # newline="\n"：Windows 上 write_text 默认翻译成 CRLF，
        # 会触发 test_python_sources_do_not_contain_crlf（.txt 也在扫描范围）
        (sub / "_report.txt").write_text(rep + "\n", encoding="utf-8",
                                         newline="\n")
        reports.append(str(sub / "_report.txt"))

    return {
        "outdir": str(outdir),
        "family": fam,
        "n_tables": len(tables[:max_tables]),
        "n_plots": len(plots),
        "plots": plots,
        "skipped": skipped,
        "tables_truncated": truncated,
        "reports": reports,
    }


def _table_curves(tbl, fname, f2, *, fixed_name, fixed_vals, var_name,
                  var_vals, fixed_axis, tag, sub, parser_unit,
                  scatter: bool = False):
    """2D 场的截断曲线（cn4 ``plot_vs_temperature`` 的 ParsedTable 泛化版）。

    ``f2`` 已归一为 ``(len(y), len(x))``（行 = y 轴，列 = x 轴）。

    * ``fixed_axis=0`` —— 固定 **y 轴**（行）若干值，画 ``field`` 随 **x 轴** 的变化；
    * ``fixed_axis=1`` —— 固定 **x 轴**（列）若干值，画 ``field`` 随 **y 轴** 的变化；
    * ``parser_unit`` —— 解析器逐文件实测单位（None/空 -> 字典单位）；
    * ``scatter`` —— 字段认证标记非空（uk/uv）时为 ``True``（散点规约）。
    """
    fixed_vals = np.asarray(fixed_vals, dtype=float)
    var_vals = np.asarray(var_vals, dtype=float)
    if fixed_vals.size < 2:
        raise ValueError(f"axis {fixed_name!r} too short ({fixed_vals.size})")
    # 取样索引落在**固定轴**维度上（固定几条曲线），变量轴全量作为 x
    k = min(5, fixed_vals.size)
    idxs = [round(i * (fixed_vals.size - 1) / (k - 1)) for i in range(k)]
    curves = []
    for j in idxs:
        label = f"{fixed_name} = {fixed_vals[j]:.1e}"
        row = f2[j, :] if fixed_axis == 0 else f2[:, j]
        curves.append((label, var_vals, row))
    return plot_multi_curve(
        curves, xlabel=_axis_label_of(tbl, var_name),
        ylabel=field_label(tbl.family, fname, parser_unit=parser_unit),
        title=f"{tbl.table_key}: {fname} {tag.replace('_', ' ')}",
        outfile=sub / f"{sanitize_name(fname)}_{tag}.png", scatter=scatter)


def _axis_label_of(tbl, name: str, *, long: bool = False) -> str:
    """轴标签（**带认证标记**，字典驱动 :func:`.labels.field_label`）。

    格式 ``Label (unit)`` / ``Label (unit), <tags>`` —— 截断曲线的
    x/y 轴同样必须让认证状态可见（用户 2026-09-15 令）；用 ``tbl.family``
    查询控制字典，意义/单位/标记实时同步（★ 模块级导入修复：旧实现把
    ``field_check`` 放在函数内导入，本函数在模块层引用不到 ->
    NameError 被 vs_x/vs_y 的 try/except 静默吞掉，截断曲线从未产出）。
    **长/短双轨**（用户 2026-09-15 晚裁定）：默认短标签（``short``，
    空回退 ``meaning``）；``long=True`` 用长标签（报告/核查场景）。
    """
    return field_label(tbl.family, name, long=long,
                       parser_unit=tbl.axis_units.get(name, ""))


def _auto_zlog(f2: np.ndarray) -> bool:
    v = np.asarray(f2, dtype=float)
    v = v[np.isfinite(v) & (v > 0)]
    if v.size < 2:
        return False
    return bool(np.log10(v.max()) - np.log10(v.min()) > 3)


def _plot_raw_sequence(tbl, fname: str, flat, sub: Path,
                       unit_disp: str) -> str:
    """raw 数值兜底图（用户 2026-09-15 规约）：**值 vs 元素索引** 散点图。

    字段与轴的形状/长度不匹配、语义映射不可行时 —— 数值本身永远可画：
    **纯散点**（marker-only；第十一轮规约：语义未知/未核查的数据画散点
    便于查找规律），x = element index（线性），y = 原始值，跨度 > 4 个
    量级且全正时对数。图上明确标注 ``semantics unknown``，物理量意义与
    单位未知不妨碍"读出数值、画出数值"。
    """
    vals = np.asarray(flat, dtype=float).ravel()
    fin = vals[np.isfinite(vals)]
    if vals.size < 2 or fin.size == 0:
        raise ValueError(f"{fname}: no plottable raw values")
    plt = _plt()
    fig, ax = plt.subplots(figsize=(10.0, 7.5))
    idx = np.arange(vals.size, dtype=float)
    ylog = (fin.min() > 0 and np.log10(fin.max()) - np.log10(fin.min()) > 4)
    ax.plot(idx, vals, lw=0, marker="o",
            ms=max(2.0, config.PLOT_MARKERSIZE - 4),
            color="#1f77b4", alpha=0.8)
    if ylog:
        ax.set_yscale("log")
    ax.set_xlabel("element index")
    ax.set_ylabel(f"{fname} ({unit_disp})")
    ax.set_title(f"{tbl.table_key}: {fname} raw values vs index "
                 f"(semantics unknown)")
    ax.grid(True, which="both", alpha=0.3)
    _style_axes(ax)
    fig.tight_layout()
    return str(_save(fig, sub / f"{sanitize_name(fname)}_raw_vs_index.png"))
