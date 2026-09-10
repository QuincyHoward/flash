"""
gen_flychk_his.extract — 区域时间序列提取
=========================================

对每个区域 (`regions.RegionSpec`) 在**每个时间步**重新求掩码，然后把域内单元
聚合成 FLYCHK history 所需的标量序列。

聚合方式 (`AGG_MODES`, 由 `config.agg` 选择):

============ =============================================================
agg          含义
============ =============================================================
mean         算术平均
median       中位数 (抗离群)
mass         质量加权平均, 权重 = dens·dx   ← 默认 (对应发射功率加权)
volume       体积加权平均, 权重 = dx
max / min    极值
center       区域几何中心最近单元
peak_dens    区域密度最大处单元
============ =============================================================

另支持 ``"percentile:NN"`` 形式 (NN ∈ [0,100])。

`size` 列 (FLYCHK 中表示等离子体尺度, cm) 由 `config.size_mode` 决定:
``extent`` (区域厚度) / ``scale_length_ne`` / ``scale_length_te`` / ``fixed``。
标长策略取域内 ``f/|df/dx|`` 的**中位数**，并以区域厚度为上限
(`config.size_cap_extent`)。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np

from .config import AGG_MODES, DENSITY_COLUMNS, FlychkHisConfig
from .regions import RegionSpec
from .sources import Snapshot, SnapshotSeries

# FLYCHK 列 -> 内部规范变量名
COLUMN_FIELD: Dict[str, str] = {
    "te": "tele",
    "ti": "tion",
    "tr": "trad",
    "rho": "dens",
    "ne": "nele",
    "ni": "nion",
}

# 缺列时的回退链 (记录在 meta, 不静默)
COLUMN_FALLBACK: Dict[str, Tuple[str, ...]] = {
    "ti": ("tion", "tele"),
    "tr": ("trad", "tele"),
    "rho": ("dens",),
    "ne": ("nele",),
    "ni": ("nion",),
    "te": ("tele",),
    "size": (),
}


class ExtractError(ValueError):
    """区域序列提取失败。"""


# ══════════════════════════════════════════════════════════
# 聚合函数
# ══════════════════════════════════════════════════════════
def _weights(snap: Snapshot, mask: np.ndarray, mode: str) -> Optional[np.ndarray]:
    w = snap.cell_widths()[mask]
    if mode == "volume":
        return w
    if mode == "mass":
        dens = snap.get("dens")
        if dens is None:
            raise ExtractError("agg='mass' 需要 'dens' 变量")
        return dens[mask] * w
    return None


def _agg_mean(v, snap, mask):
    return float(np.nanmean(v))


def _agg_median(v, snap, mask):
    return float(np.nanmedian(v))


def _agg_weighted(v, snap, mask, mode):
    w = _weights(snap, mask, mode)
    w = np.where(np.isfinite(w), w, 0.0)
    tot = float(w.sum())
    if tot <= 0:
        return float(np.nanmean(v))
    return float(np.nansum(v * w) / tot)


def _agg_max(v, snap, mask):
    return float(np.nanmax(v))


def _agg_min(v, snap, mask):
    return float(np.nanmin(v))


def _agg_center(v, snap, mask):
    x = snap.x[mask]
    xc = 0.5 * (x.min() + x.max())
    return float(v[int(np.argmin(np.abs(x - xc)))])


def _agg_peak_dens(v, snap, mask):
    dens = snap.get("dens")
    if dens is None:
        raise ExtractError("agg='peak_dens' 需要 'dens' 变量")
    d = dens[mask]
    return float(v[int(np.argmax(d))])


AGG_FUNCS: Dict[str, Callable[[np.ndarray, Snapshot, np.ndarray], float]] = {
    "mean": _agg_mean,
    "median": _agg_median,
    "mass": lambda v, s, m: _agg_weighted(v, s, m, "mass"),
    "volume": lambda v, s, m: _agg_weighted(v, s, m, "volume"),
    "max": _agg_max,
    "min": _agg_min,
    "center": _agg_center,
    "peak_dens": _agg_peak_dens,
}


def resolve_aggregator(agg: Any) -> Callable[[np.ndarray, Snapshot, np.ndarray], float]:
    """把 agg 名称/回调解析为聚合函数 ``f(values, snapshot, mask) -> float``。"""
    if callable(agg):
        return lambda v, s, m: float(agg(v, s, m))
    key = str(agg).strip().lower()
    if key in AGG_FUNCS:
        return AGG_FUNCS[key]
    if key.startswith("percentile:"):
        try:
            q = float(key.split(":", 1)[1])
        except ValueError:
            raise ExtractError(f"无法解析聚合 '{agg}'，应形如 'percentile:50'")
        if not (0.0 <= q <= 100.0):
            raise ExtractError(f"percentile 分位须在 [0,100]，当前 {q}")
        return lambda v, s, m: float(np.nanpercentile(v, q))
    raise ExtractError(f"未知聚合方式 '{agg}'，可选: {list(AGG_MODES)} 或 'percentile:NN'")


# ══════════════════════════════════════════════════════════
# size 策略
# ══════════════════════════════════════════════════════════
def _region_extent(snap: Snapshot, mask: np.ndarray) -> float:
    x = snap.x[mask]
    if x.size < 2:
        return float(np.sum(snap.cell_widths()[mask]))
    return float(x.max() - x.min() + 0.5 * (
        snap.cell_widths()[mask][0] + snap.cell_widths()[mask][-1]))


def _scale_length(values: np.ndarray, x: np.ndarray) -> Optional[float]:
    """梯度标长 ls = f / |df/dx| 在域内的中位数 (仅统计分母有效处)。"""
    if values.size < 3:
        return None
    grad = np.gradient(values, x)
    denom = np.abs(grad)
    ok = denom > 0
    if not np.any(ok):
        return None
    ls = np.abs(values[ok]) / denom[ok]
    ls = ls[np.isfinite(ls) & (ls > 0)]
    if ls.size == 0:
        return None
    return float(np.median(ls))


def compute_size(snap: Snapshot, mask: np.ndarray, cfg: FlychkHisConfig
                 ) -> Tuple[float, str]:
    """返回 (size_cm, 策略说明)。"""
    extent = _region_extent(snap, mask)
    mode = cfg.size_mode
    note = mode

    if mode == "fixed":
        raw = float(cfg.size_value)
    elif mode == "extent":
        raw = extent
    elif mode in ("scale_length_ne", "scale_length_te"):
        field_name = "nele" if mode.endswith("_ne") else "tele"
        arr = snap.get(field_name)
        if arr is None:
            raw = extent
            note = f"{mode}->extent(缺 {field_name})"
        else:
            ls = _scale_length(arr[mask], snap.x[mask])
            if ls is None:
                raw = extent
                note = f"{mode}->extent(标长退化)"
            elif cfg.size_cap_extent and ls > extent:
                raw = extent
                note = f"{mode}(capped by extent)"
            else:
                raw = ls
    else:  # pragma: no cover - config.validate 已拦截
        raw = extent
        note = f"unknown({mode})->extent"

    value = max(float(raw) * float(cfg.size_scale), float(cfg.size_floor))
    return value, note


# ══════════════════════════════════════════════════════════
# 区域序列容器
# ══════════════════════════════════════════════════════════
@dataclass
class RegionSeries:
    """单个区域的聚合时间序列 (内部规范单位: s / eV / g·cm^-3 / cm)。"""

    spec: RegionSpec
    times: np.ndarray                       # [nt] s
    values: Dict[str, np.ndarray]           # FLYCHK 列名 -> [nt]
    masks: List[np.ndarray] = field(default_factory=list)
    notes: Dict[str, Any] = field(default_factory=dict)
    cells: Optional[np.ndarray] = None      # [nt] 每步参与聚合的单元数

    # ── 容器协议 ────────────────────────────────────────────
    def __len__(self) -> int:
        return int(self.times.size)

    def column(self, name: str) -> np.ndarray:
        if name not in self.values:
            raise KeyError(f"区域 '{self.spec.name}' 无列 '{name}'；"
                           f"现有 {sorted(self.values)}")
        return self.values[name]

    def __repr__(self) -> str:
        n = self.cells.size if self.cells is not None else 0
        return (f"RegionSeries({self.spec.name!r}, n_time={len(self)}, "
                f"cols={sorted(self.values)}, cells~{int(np.median(self.cells)) if n else '-'})")

    def diagnostics(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "region": self.spec.describe(),
            "n_time": len(self),
            "columns": sorted(self.values),
            "notes": self.notes,
        }
        if self.cells is not None and self.cells.size:
            d["cells_min"] = int(self.cells.min())
            d["cells_max"] = int(self.cells.max())
        for col, arr in self.values.items():
            finite = np.asarray(arr)[np.isfinite(arr)]
            if finite.size:
                d[f"{col}_range"] = [float(finite.min()), float(finite.max())]
        return d


# ══════════════════════════════════════════════════════════
# 提取
# ══════════════════════════════════════════════════════════
def extract_region(series: SnapshotSeries, spec: RegionSpec,
                   cfg: FlychkHisConfig,
                   keep_masks: bool = True) -> RegionSeries:
    """把一个区域在整条时间序列上聚合成 `RegionSeries`。"""
    agg_fn = resolve_aggregator(cfg.agg)
    columns = [c for c in cfg.columns]
    times: List[float] = []
    values: Dict[str, List[float]] = {c: [] for c in columns}
    masks: List[np.ndarray] = []
    cells: List[int] = []
    size_notes: set = set()
    fallback_used: Dict[str, str] = {}
    n_missing_cells = 0

    for snap in series:
        mask = spec.mask(snap, dens_cut=cfg.dens_cut)
        if not np.any(mask):
            continue
        masks.append(mask)
        cells.append(int(mask.sum()))
        times.append(float(snap.time))

        for col in columns:
            if col == "time":
                values[col].append(float(snap.time))
                continue
            if col == "size":
                size, note = compute_size(snap, mask, cfg)
                size_notes.add(note)
                values[col].append(size)
                continue
            field_name = COLUMN_FIELD[col]
            arr = snap.get(field_name)
            used = field_name
            if arr is None:
                for alt in COLUMN_FALLBACK.get(col, ()):
                    if snap.get(alt) is not None:
                        arr = snap.get(alt)
                        used = alt
                        break
            if arr is None:
                raise ExtractError(
                    f"区域 '{spec.name}' 需要列 '{col}' (变量 '{field_name}')，"
                    f"但 t={snap.time:.4e}s 快照中不存在，且无可用回退"
                    f"（回退链 {COLUMN_FALLBACK.get(col, ())}）；"
                    f"可用变量: {sorted(snap.fields)}"
                )
            if used != field_name:
                fallback_used[col] = used
            vals = arr[mask]
            if not np.any(np.isfinite(vals)):
                n_missing_cells += 1
                values[col].append(np.nan)
                continue
            values[col].append(agg_fn(vals, snap, mask))

    if not times:
        raise ExtractError(
            f"区域 '{spec.name}' 在所有时间点上均为空；"
            f"请检查区域定义与数据范围 (x∈"
            f"[{series[0].x[0]:.4e},{series[0].x[-1]:.4e}]cm, 时间 "
            f"{series.times[0]:.3e}~{series.times[-1]:.3e}s)"
        )

    notes: Dict[str, Any] = {
        "agg": cfg.agg if isinstance(cfg.agg, str) else "<callable>",
        "dens_cut": cfg.dens_cut,
        "size_mode": cfg.size_mode,
        "size_notes": sorted(size_notes),
        "size_scale": cfg.size_scale,
    }
    if fallback_used:
        notes["column_fallback"] = fallback_used
    if n_missing_cells:
        notes["all_nonfinite_cells"] = n_missing_cells

    return RegionSeries(
        spec=spec,
        times=np.asarray(times, dtype=np.float64),
        values={c: np.asarray(v, dtype=np.float64) for c, v in values.items()},
        masks=masks if keep_masks else [],
        notes=notes,
        cells=np.asarray(cells, dtype=np.int64),
    )


def extract_all(series: SnapshotSeries, specs: Sequence[RegionSpec],
                cfg: FlychkHisConfig, keep_masks: bool = True
                ) -> List[RegionSeries]:
    """批量提取多个区域。"""
    return [extract_region(series, s, cfg, keep_masks=keep_masks) for s in specs]


__all__ = [
    "RegionSeries", "ExtractError", "COLUMN_FIELD", "COLUMN_FALLBACK",
    "AGG_FUNCS", "resolve_aggregator", "compute_size",
    "extract_region", "extract_all",
]
