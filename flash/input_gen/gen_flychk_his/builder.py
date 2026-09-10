"""
gen_flychk_his.builder — FLYCHK history 数据表构建与校验
========================================================

把 `extract.RegionSeries` (内部规范单位) 转换为**可直接写入 FLYCHK 输入 zip**
的二维表:

    列名行:  time size te ti tr rho
    数据行:  1.000000e-12 1.000000e-04 1.000000e+03 ...   (%.6e, 空格分隔)

处理链 (顺序固定, 全部记录在 `HistoryTable.meta`):

1. **NaN 修补** — 内部线性插值，端点取最近有效值
2. **物理钳位** — te/ti/tr ∈ [te_floor, te_ceil]，rho ∈ [dens_floor, dens_ceil]
3. **时间单位换算** — 秒 → `config.time_unit`（默认 s）
4. **非正时间剔除** — `drop_nonpositive_time` (FLYCHK history 需要 t > 0)
5. **时间窗裁剪** — `tmin` / `tmax`（单位同 `time_unit`）
6. **抽稀** — 先 `time_stride`，再 `n_time_max` 均匀取点（保留首末）
7. **去重** — 强制时间严格递增

文本格式严格遵循 FLYCHK history 模式官方输入契约
（``zip_writer.FORMAT_CONTRACT_ID = "flychk-history-v1"``）。
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from . import units
from .config import (DENSITY_COLUMNS, FlychkHisConfig, REQUIRED_COLUMNS,
                     ValidationReport)
from .extract import RegionSeries


class BuilderError(ValueError):
    """表格构建失败。"""


# FLYCHK 各列的合法下限 (物理>0)
_POSITIVE_COLUMNS = ("te", "ti", "tr", "rho", "ne", "ni", "size")


# ══════════════════════════════════════════════════════════
# 数据结构
# ══════════════════════════════════════════════════════════
@dataclass
class HistoryTable:
    """FLYCHK history 数据表。"""

    columns: List[str]
    rows: List[List[float]]
    meta: Dict[str, Any] = field(default_factory=dict)

    @property
    def n_steps(self) -> int:
        return len(self.rows)

    @property
    def element(self) -> str:
        return self.meta.get("element", "")

    @property
    def z(self) -> int:
        return int(self.meta.get("z", 0))

    def column(self, name: str) -> np.ndarray:
        if name not in self.columns:
            raise KeyError(f"表中无列 '{name}'；现有 {self.columns}")
        idx = self.columns.index(name)
        return np.asarray([r[idx] for r in self.rows], dtype=np.float64)

    def as_dict(self) -> Dict[str, np.ndarray]:
        return {c: self.column(c) for c in self.columns}

    # ── 文本序列化 (FLYCHK history 格式契约) ─────────────────
    def to_text(self) -> str:
        """FLYCHK 数据文件内容 (首行列名, 数据 %.6e 空格分隔)。"""
        lines = [" ".join(self.columns)]
        for row in self.rows:
            lines.append(" ".join(f"{v:.6e}" for v in row))
        return "\n".join(lines) + "\n"

    def to_csv(self, delimiter: str = ",") -> str:
        lines = [delimiter.join(self.columns)]
        for row in self.rows:
            lines.append(delimiter.join(f"{v:.6e}" for v in row))
        return "\n".join(lines) + "\n"

    def preview(self, n: int = 5) -> str:
        """前 n 行 + 列头 (供日志/终端确认)。"""
        head = " ".join(f"{c:>12s}" for c in self.columns)
        lines = [head]
        for row in self.rows[:n]:
            lines.append(" ".join(f"{v:12.4e}" for v in row))
        if self.n_steps > n:
            lines.append(f"... ({self.n_steps} 行, 省略 {self.n_steps - n} 行)")
        return "\n".join(lines)

    def summary(self) -> str:
        if not self.rows:
            return "HistoryTable(空)"
        d = self.as_dict()
        t = d.get("time")
        span = f"{t[0]:.3e}~{t[-1]:.3e}" if t is not None else "-"
        return (f"HistoryTable({self.n_steps} 步, {len(self.columns)} 列 "
                f"{self.columns}, time={span} [{self.meta.get('time_unit', 's')}]"
                f", element={self.element} Z={self.z})")


# ══════════════════════════════════════════════════════════
# 数值修补
# ══════════════════════════════════════════════════════════
def _fill_nan(arr: np.ndarray) -> Tuple[np.ndarray, int]:
    """线性插值修补 NaN；端点用最近有效值。返回 (修补后数组, 修补数量)。"""
    a = np.asarray(arr, dtype=np.float64).copy()
    bad = ~np.isfinite(a)
    n_bad = int(bad.sum())
    if n_bad == 0:
        return a, 0
    if n_bad == a.size:
        raise BuilderError("整列均为 NaN/Inf，无法修补")
    idx = np.arange(a.size)
    a[bad] = np.interp(idx[bad], idx[~bad], a[~bad])
    return a, n_bad


def _clamp(arr: np.ndarray, lo: float, hi: float) -> Tuple[np.ndarray, int]:
    a = np.asarray(arr, dtype=np.float64).copy()
    n = int(np.sum((a < lo) | (a > hi)))
    return np.clip(a, lo, hi), n


# ══════════════════════════════════════════════════════════
# 构建
# ══════════════════════════════════════════════════════════
def build_table(rs: RegionSeries, cfg: FlychkHisConfig) -> HistoryTable:
    """由区域序列构建 FLYCHK history 表。"""
    report = cfg.validate()
    report.raise_if_bad()

    columns = [str(c).strip().lower() for c in cfg.columns]
    missing_cols = [c for c in columns if c not in rs.values]
    if missing_cols:
        raise BuilderError(
            f"区域 '{rs.spec.name}' 缺少列 {missing_cols}；该区域可用列 "
            f"{sorted(rs.values)}（可用 config.evolve(columns=...) 调整列组合，"
            "或换用包含该变量的数据源/区域）"
        )
    meta: Dict[str, Any] = {
        "region": rs.spec.name,
        "region_spec": rs.spec.to_dict(),
        "element": cfg.element,
        "z": cfg.resolved_z,
        "atomic_weight": cfg.resolved_a if _a_ok(cfg) else None,
        "zeff": cfg.resolved_zeff,
        "columns": columns,
        "column_units": {c: cfg.column_unit(c) for c in columns},
        "agg": rs.notes.get("agg"),
        "dens_cut": rs.notes.get("dens_cut"),
        "size_mode": rs.notes.get("size_mode"),
        "size_notes": rs.notes.get("size_notes"),
        "size_scale": rs.notes.get("size_scale"),
        "input_time_unit": "s",
        "time_unit": cfg.time_unit,
        "clamped": {},
        "nan_filled": {},
        "dropped": {},
    }
    if "column_fallback" in rs.notes:
        meta["column_fallback"] = rs.notes["column_fallback"]
    if "all_nonfinite_cells" in rs.notes:
        meta["all_nonfinite_cells"] = rs.notes["all_nonfinite_cells"]
    if rs.cells is not None and rs.cells.size:
        meta["cells"] = {"min": int(rs.cells.min()), "max": int(rs.cells.max()),
                         "median": int(np.median(rs.cells))}

    if len(rs) == 0:
        raise BuilderError(f"区域 '{rs.spec.name}' 无可用时间点")

    # ── 1. 逐列修补 + 钳位 ──
    cleaned: Dict[str, np.ndarray] = {}
    for col in columns:
        if col == "time":
            cleaned[col] = np.asarray(rs.times, dtype=np.float64).copy()
            continue
        arr = np.asarray(rs.column(col), dtype=np.float64).copy()
        arr, n_nan = _fill_nan(arr)
        if n_nan:
            meta["nan_filled"][col] = n_nan
        if col in ("te", "ti", "tr"):
            arr, n_cl = _clamp(arr, cfg.te_floor, cfg.te_ceil)
        elif col == "rho":
            arr, n_cl = _clamp(arr, cfg.dens_floor, cfg.dens_ceil)
        elif col in ("ne", "ni"):
            # 数密度只做正性保护 (与 te_floor 对应量级无关)
            arr, n_cl = _clamp(arr, 1.0, np.inf)
        elif col == "size":
            arr, n_cl = _clamp(arr, cfg.size_floor, np.inf)
        else:
            n_cl = 0
        if n_cl:
            meta["clamped"][col] = int(n_cl)
        cleaned[col] = arr

    # ── 2. 时间: 单位换算 → 剔除非正 → 裁剪 → 抽稀 ──
    t_sec = cleaned["time"]
    factor = 1.0 / float(units.to_s(1.0, cfg.time_unit))   # s -> 目标单位
    t_out = t_sec * factor

    n0 = t_out.size
    if cfg.drop_nonpositive_time:
        keep = t_out > 0
        if not np.all(keep):
            meta["dropped"]["nonpositive_time"] = int((~keep).sum())
        t_out = t_out[keep]
        for col in columns:
            cleaned[col] = cleaned[col][keep]
    if cfg.tmin is not None or cfg.tmax is not None:
        lo = cfg.tmin if cfg.tmin is not None else -np.inf
        hi = cfg.tmax if cfg.tmax is not None else np.inf
        keep = (t_out >= lo) & (t_out <= hi)
        meta["dropped"]["time_window"] = int((~keep).sum())
        t_out = t_out[keep]
        for col in columns:
            cleaned[col] = cleaned[col][keep]
    if cfg.time_stride > 1:
        sel = np.arange(0, t_out.size, cfg.time_stride)
        meta["dropped"]["time_stride"] = int(t_out.size - sel.size)
        t_out = t_out[sel]
        for col in columns:
            cleaned[col] = cleaned[col][sel]
    if cfg.n_time_max and t_out.size > cfg.n_time_max:
        sel = np.unique(np.linspace(0, t_out.size - 1, cfg.n_time_max).round().astype(int))
        meta["dropped"]["subsample"] = int(t_out.size - sel.size)
        t_out = t_out[sel]
        for col in columns:
            cleaned[col] = cleaned[col][sel]
    cleaned["time"] = t_out
    meta["n_time_raw"] = int(n0)
    meta["n_time_used"] = int(t_out.size)

    if t_out.size == 0:
        raise BuilderError(
            f"时间筛选后无剩余时间点 (原始 {n0} 点，"
            f"drop_nonpositive_time={cfg.drop_nonpositive_time}, "
            f"tmin={cfg.tmin}, tmax={cfg.tmax}, stride={cfg.time_stride}, "
            f"n_time_max={cfg.n_time_max})"
        )

    # ── 3. 时间严格递增去重 (保留后者) ──
    order = np.argsort(t_out, kind="stable")
    t_sorted = t_out[order]
    keep_mask = np.ones(t_sorted.size, dtype=bool)
    if t_sorted.size > 1:
        keep_mask[:-1] = np.diff(t_sorted) > 0
    if not np.all(keep_mask):
        meta["dropped"]["duplicate_time"] = int((~keep_mask).sum())
    for col in columns:
        cleaned[col] = cleaned[col][order][keep_mask]

    # ── 4. 组行 ──
    rows: List[List[float]] = []
    n = cleaned["time"].size
    for i in range(n):
        rows.append([float(cleaned[c][i]) for c in columns])

    meta["time_span"] = [float(cleaned["time"][0]), float(cleaned["time"][-1])]
    meta["time_span_seconds"] = [float(cleaned["time"][0] / factor),
                                 float(cleaned["time"][-1] / factor)]
    return HistoryTable(columns=columns, rows=rows, meta=meta)


def _a_ok(cfg: FlychkHisConfig) -> bool:
    try:
        cfg.resolved_a
        return True
    except ValueError:
        return False


# ══════════════════════════════════════════════════════════
# 校验
# ══════════════════════════════════════════════════════════
def validate_table(table: HistoryTable, cfg: Optional[FlychkHisConfig] = None,
                   max_steps_warn: int = 50) -> ValidationReport:
    """校核表是否满足 FLYCHK history 输入约束。"""
    errors: List[str] = []
    warnings: List[str] = []

    cols = table.columns
    if not cols:
        errors.append("表无列")
        return ValidationReport(errors=errors, warnings=warnings)
    for req in REQUIRED_COLUMNS:
        if req not in cols:
            errors.append(f"表缺少必需列 '{req}'")
    dens_cols = [c for c in cols if c in DENSITY_COLUMNS]
    if len(dens_cols) > 1:
        errors.append(f"表含多个密度列 {dens_cols}，FLYCHK 只接受一个")

    if table.n_steps == 0:
        errors.append("表无数据行")
        return ValidationReport(errors=errors, warnings=warnings)

    widths = {len(r) for r in table.rows}
    if widths != {len(cols)}:
        errors.append(f"行列长度不一致: 列数 {len(cols)}，行长集合 {sorted(widths)}")
        return ValidationReport(errors=errors, warnings=warnings,
                                info={"n_steps": table.n_steps, "columns": cols})

    data = table.as_dict()
    for c, arr in data.items():
        if not np.all(np.isfinite(arr)):
            errors.append(f"列 '{c}' 含 NaN/Inf")
    if "time" in data:
        t = data["time"]
        if np.any(t <= 0):
            errors.append(f"列 'time' 存在非正值 (min={t.min():.3e})，"
                          "FLYCHK history 需要 t > 0")
        if t.size > 1 and np.any(np.diff(t) <= 0):
            errors.append("列 'time' 非严格递增")
    for c in _POSITIVE_COLUMNS:
        if c in data and np.any(data[c] <= 0):
            errors.append(f"列 '{c}' 存在非正值 (min={data[c].min():.3e})")

    if table.n_steps > max_steps_warn:
        warnings.append(
            f"时间步数 {table.n_steps} > {max_steps_warn}：FLYCHK 网站对 history "
            "提交的时间步数有限制，建议用 n_time_max 抽稀"
        )
    if "size" not in cols:
        warnings.append("无 'size' 列 → runfile 不含 'opacity file'，不输出 tau")
    if not dens_cols:
        errors.append(
            "表无密度列 (rho/ne/ni) → runfile 不会写出 'history <data> <mode>' 行，"
            "FLYCHK 不会读取数据文件"
        )

    if cfg is not None and cfg.strict:
        errors.extend(warnings)
        warnings = []

    info = {
        "n_steps": table.n_steps,
        "columns": cols,
        "element": table.element,
        "z": table.z,
        "time_span": table.meta.get("time_span"),
        "time_unit": table.meta.get("time_unit"),
    }
    return ValidationReport(errors=errors, warnings=warnings, info=info)


__all__ = ["HistoryTable", "BuilderError", "build_table", "validate_table"]
