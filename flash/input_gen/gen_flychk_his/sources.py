"""
gen_flychk_his.sources — 数据源统一加载层
=========================================

把**任意来源**的 FLASH 物理量剖面归一化为统一的 `SnapshotSeries`
（内部规范单位: eV / s / cm / g·cm^-3 / cm^-3），供上层区域选择与表格构建使用。

支持的数据源 (`load_series` 自动派发):

============== ============================================================
source 形态     说明
============== ============================================================
str (文件)      FLASH HDF5 chk/plt 文件 -> FlashDataLoader
str (目录)      目录内按 `*hdf5_chk_*` / `*hdf5_plt_cnt_*` 批量加载并按时间排序
str (通配)      含 ``*``/``?`` 的 glob 模式
str (npz)       压缩数组: time/x + 多个 (nt, nx) 场
str (csv)       长表: 列含 time, x 与各物理量
str (json)      ``{"times":[...], "x":[...], "fields":{...}, "units":{...}}``
list/tuple      路径列表 或 快照字典列表
dict            ``{"time":..., "x":..., "tele":...}`` 或 ``{"snapshots":[...]}``
ndarray         仅 x → 单时间点占位 (不推荐)
callable        ``f(t) -> dict`` 或 ``f(t, x) -> dict``，配合 `times=` 使用
None            合成数据 (见 `synthetic_ch_ti_slab`)
============== ============================================================

注意: FLASH 数据读取默认 `extraction_mode="h5py"`（只取 node_type==1 叶子块，
无需 yt）。超算环境无 yt 时该模式可用；有 yt 时可显式传 ``extraction_mode="yt"``
做交叉验证。
"""

from __future__ import annotations

import csv
import glob as _glob
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple, Union

import numpy as np

from . import units
from .config import FlychkHisConfig

# ── 变量别名 (输入名 -> 内部规范名) ─────────────────────────
FIELD_ALIASES: Dict[str, str] = {
    # 质量密度
    "rho": "dens", "dens": "dens", "density": "dens",
    # 温度
    "te": "tele", "tele": "tele", "t_e": "tele", "electron_temperature": "tele",
    "ti": "tion", "tion": "tion", "ion_temperature": "tion",
    "tr": "trad", "trad": "trad", "radiation_temperature": "trad",
    # 数密度
    "ne": "nele", "nele": "nele", "electron_density": "nele",
    "ni": "nion", "nion": "nion", "ion_density": "nion",
    # 其他
    "velx": "velx", "vx": "velx", "ye": "ye", "sumy": "sumy",
    "pres": "pres", "pele": "pele", "pion": "pion",
}

TEMP_FIELDS = ("tele", "tion", "trad")
NUMDENS_FIELDS = ("nele", "nion")

# 默认**输入**单位 (FLASH 原生 cgs + K)
DEFAULT_INPUT_UNITS = {
    "tele": "K", "tion": "K", "trad": "K",
    "dens": "g/cm^3",
    "nele": "cm^-3", "nion": "cm^-3",
    "x": "cm", "size": "cm", "time": "s",
}

# 合成解析模型直接产出 eV 温度, 故显式声明输入单位 (防止 11604 倍误换算)
_SYNTH_INPUT_CFG = FlychkHisConfig(
    input_units={"tele": "eV", "tion": "eV", "trad": "eV", "dens": "g/cm^3"})


# ══════════════════════════════════════════════════════════
# 数据结构
# ══════════════════════════════════════════════════════════
@dataclass
class Snapshot:
    """单个时间点的 1D 剖面 (所有场已归一化为内部规范单位)。"""

    time: float
    x: np.ndarray
    fields: Dict[str, np.ndarray]
    widths: Optional[np.ndarray] = None
    step: int = 0
    source: str = ""
    meta: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        self.x = np.asarray(self.x, dtype=np.float64).ravel()
        self.fields = {
            k: np.asarray(v, dtype=np.float64).ravel()
            for k, v in self.fields.items()
        }
        if self.widths is not None:
            self.widths = np.asarray(self.widths, dtype=np.float64).ravel()

    # ── 访问 ────────────────────────────────────────────────
    def has(self, field_name: str) -> bool:
        return _canonical_field(field_name) in self.fields

    def field(self, field_name: str) -> np.ndarray:
        key = _canonical_field(field_name)
        if key not in self.fields:
            raise KeyError(
                f"快照 (t={self.time:.4e}s) 不含变量 '{field_name}'"
                f" (已归一化名 '{key}')；可用: {sorted(self.fields)}"
            )
        return self.fields[key]

    def get(self, field_name: str, default=None):
        key = _canonical_field(field_name)
        return self.fields.get(key, default)

    def cell_widths(self) -> np.ndarray:
        """单元宽度 (cm)。未显式提供时由 x 的半间距估算。"""
        if self.widths is not None and self.widths.size == self.x.size:
            return self.widths
        return widths_from_x(self.x)

    def extent(self) -> float:
        """剖面覆盖的物理范围 x[-1]-x[0] (cm)。"""
        return float(self.x[-1] - self.x[0]) if self.x.size > 1 else 0.0

    def __repr__(self) -> str:
        return (f"Snapshot(t={self.time:.4e}s, n_cell={self.x.size}, "
                f"fields={sorted(self.fields)})")


@dataclass
class SnapshotSeries:
    """时间序列 (按时间升序)。"""

    snapshots: List[Snapshot]
    meta: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        self.snapshots = list(self.snapshots)
        if self.snapshots:
            order = np.argsort([s.time for s in self.snapshots], kind="stable")
            self.snapshots = [self.snapshots[i] for i in order]

    # ── 属性 ────────────────────────────────────────────────
    @property
    def times(self) -> np.ndarray:
        return np.asarray([s.time for s in self.snapshots], dtype=np.float64)

    @property
    def variables(self) -> List[str]:
        names: set = set()
        for s in self.snapshots:
            names.update(s.fields)
        return sorted(names)

    @property
    def n_time(self) -> int:
        return len(self.snapshots)

    # ── 容器协议 ────────────────────────────────────────────
    def __len__(self) -> int:
        return len(self.snapshots)

    def __iter__(self):
        return iter(self.snapshots)

    def __getitem__(self, idx):
        return self.snapshots[idx]

    def __repr__(self) -> str:
        t = self.times
        rng = f"{t[0]:.3e}~{t[-1]:.3e}s" if t.size else "-"
        return (f"SnapshotSeries(n_time={self.n_time}, {rng}, "
                f"vars={self.variables})")

    # ── 派生 ────────────────────────────────────────────────
    def subset(self, indices: Iterable[int]) -> "SnapshotSeries":
        idx = list(indices)
        return SnapshotSeries([self.snapshots[i] for i in idx], dict(self.meta))

    def with_time_range(self, tmin: Optional[float] = None,
                        tmax: Optional[float] = None) -> "SnapshotSeries":
        keep = [s for s in self.snapshots
                if (tmin is None or s.time >= tmin) and (tmax is None or s.time <= tmax)]
        meta = dict(self.meta)
        meta["time_range"] = [tmin, tmax]
        return SnapshotSeries(keep, meta)

    def summary(self) -> str:
        lines = [f"SnapshotSeries: {self.n_time} 时间点, 变量 {self.variables}"]
        for s in self.snapshots:
            lines.append(f"  t={s.time:.6e}s  n_cell={s.x.size}  "
                         f"[{s.x[0]:.4e}, {s.x[-1]:.4e}] cm  src={Path(s.source).name or '-'}")
        return "\n".join(lines)


# ══════════════════════════════════════════════════════════
# 工具
# ══════════════════════════════════════════════════════════
def _canonical_field(name: str) -> str:
    key = str(name).strip()
    if key in FIELD_ALIASES:
        return FIELD_ALIASES[key]
    low = key.lower()
    if low in FIELD_ALIASES:
        return FIELD_ALIASES[low]
    return key            # 保留原名 (如 cham/targ/shld/trl1/matid)


def widths_from_x(x: np.ndarray) -> np.ndarray:
    """由单元中心坐标估算单元宽度 (cm)。假使 x 单调升序。"""
    x = np.asarray(x, dtype=np.float64).ravel()
    n = x.size
    if n == 0:
        return np.zeros(0)
    if n == 1:
        return np.ones(1) * 1.0e-4
    dx = np.diff(x)
    w = np.empty(n, dtype=np.float64)
    w[0] = dx[0]
    w[-1] = dx[-1]
    if n > 2:
        w[1:-1] = 0.5 * (dx[:-1] + dx[1:])
    return w


# 规范名 -> 全部可选写的键 (含别名), 用于 input_units 查找
_ALIAS_KEYS: Dict[str, tuple] = {}
for _k, _v in FIELD_ALIASES.items():
    _ALIAS_KEYS.setdefault(_v, ())
    if _k not in _ALIAS_KEYS[_v]:
        _ALIAS_KEYS[_v] = (*_ALIAS_KEYS[_v], _k)


def resolve_input_unit(cfg: FlychkHisConfig, field_name: str) -> str:
    """解析某物理量在**输入数据**中的单位。

    查找顺序: ``input_units[原始名]`` → ``input_units[规范名]`` →
    ``input_units[该规范名的任一别名]`` (如 dens ← rho) → 默认值。
    """
    name = _canonical_field(field_name)
    for key in (field_name, name, *_ALIAS_KEYS.get(name, ())):
        if key in cfg.input_units:
            return cfg.input_units[key]
    return DEFAULT_INPUT_UNITS.get(name, "")


def normalize_fields(fields: Dict[str, np.ndarray], cfg: FlychkHisConfig,
                     allow_derived: bool = True
                     ) -> Tuple[Dict[str, np.ndarray], Dict[str, Any]]:
    """把原始剖面归一化为内部规范单位，并按需派生 nele / nion。

    Returns:
        (fields, notes) — notes 含 ``derived``（派生来源）、``units``（换算记录）
        与 ``warnings``（单位自洽性告警，例如温度数量级与声明单位不符）。
    """
    out: Dict[str, np.ndarray] = {}
    notes: Dict[str, Any] = {"derived": [], "units": {}, "warnings": []}

    for raw_name, values in fields.items():
        name = _canonical_field(raw_name)
        arr = np.asarray(values, dtype=np.float64).ravel()
        if name in TEMP_FIELDS:
            unit = resolve_input_unit(cfg, name)
            out[name] = units.to_ev(arr, unit)
            notes["units"][name] = f"{unit} -> eV"
            _check_temp_magnitude(name, arr, unit, notes["warnings"])
        elif name in NUMDENS_FIELDS:
            unit = resolve_input_unit(cfg, name)
            out[name] = units.to_numdens_cgs(arr, unit)
            notes["units"][name] = f"{unit} -> cm^-3"
        elif name == "dens":
            unit = resolve_input_unit(cfg, "dens")
            out[name] = units.to_dens_cgs(arr, unit)
            notes["units"][name] = f"{unit} -> g/cm^3"
        else:
            out[name] = arr

    if not allow_derived:
        return out, notes

    dens = out.get("dens")
    # nele: 优先原生数据集 -> ye*dens*NA -> dens*Zeff/A*NA
    if "nele" not in out and dens is not None:
        if "ye" in out:
            out["nele"] = out["ye"] * dens * units.N_A
            notes["derived"].append("nele = ye * dens * N_A  (FLASH ye, mol e-/g)")
        else:
            out["nele"] = units.nele_from_rho(dens, cfg.resolved_zeff, cfg.resolved_a)
            notes["derived"].append(
                f"nele = dens * (Zeff={cfg.resolved_zeff:g}/A={cfg.resolved_a:g}) * N_A"
                "  [估算, 全剥离假设]"
            )
    if "nion" not in out and dens is not None:
        if "sumy" in out:
            out["nion"] = out["sumy"] * dens * units.N_A
            notes["derived"].append("nion = sumy * dens * N_A  (FLASH sumy, mol ions/g)")
        else:
            out["nion"] = units.nion_from_rho(dens, cfg.resolved_a)
            notes["derived"].append("nion = dens / A * N_A  [估算]")

    return out, notes


def _check_temp_magnitude(field_name: str, values: np.ndarray, unit: str,
                          warnings: List[str]) -> None:
    """温度数量级自洽性检查 (防止 K ⇄ eV 的 11604 倍误读)。

    判据 (量级而非精确值):
      - 声明 K 但最大值 < 5e4 K (≈4.3 eV) → 数据可能本身就是 eV
      - 声明 eV 但最大值 > 5e5 eV          → 数据可能是 K
    """
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return
    vmax = float(finite.max())
    u = str(unit).strip().lower()
    if u in ("k", "kelvin") and vmax < 5.0e4:
        warnings.append(
            f"'{field_name}': 声明单位 K 但最大值仅 {vmax:.3g} K (~{vmax / units.K_PER_EV:.3g} eV)，"
            f"若数据本身以 eV 给出请设置 input_units={{'{field_name}': 'eV'}}"
        )
    elif u == "ev" and vmax > 5.0e5:
        warnings.append(
            f"'{field_name}': 声明单位 eV 但最大值达 {vmax:.3g} eV，"
            f"若数据本身是 K 请设置 input_units={{'{field_name}': 'K'}}"
        )


def dedup_and_sort(x: np.ndarray, arrays: Dict[str, np.ndarray]
                   ) -> Tuple[np.ndarray, Dict[str, np.ndarray], int]:
    """按 x 排序并去除重复坐标 (AMR 块边界常见)。返回 (x, arrays, n_removed)。"""
    x = np.asarray(x, dtype=np.float64).ravel()
    order = np.argsort(x, kind="stable")
    x = x[order]
    arrays = {k: np.asarray(v, dtype=np.float64).ravel()[order] for k, v in arrays.items()}
    keep = np.ones(x.size, dtype=bool)
    if x.size > 1:
        keep[1:] = np.diff(x) > 0
    n_removed = int((~keep).sum())
    if n_removed:
        x = x[keep]
        arrays = {k: v[keep] for k, v in arrays.items()}
    return x, arrays, n_removed


# ══════════════════════════════════════════════════════════
# 各类数据源适配
# ══════════════════════════════════════════════════════════
def _snapshot_from_columns(time: float, x: np.ndarray,
                           fields: Dict[str, np.ndarray],
                           cfg: FlychkHisConfig, source: str = "",
                           step: int = 0,
                           extra_meta: Optional[Dict[str, Any]] = None
                           ) -> Snapshot:
    """由原始列数据构造归一化快照。"""
    norm, notes = normalize_fields(fields, cfg)
    x2, norm2, n_dup = dedup_and_sort(x, norm)
    meta = {"derived": notes["derived"], "unit_map": notes["units"],
            "n_duplicate_x_removed": n_dup}
    if notes["warnings"]:
        meta["unit_warnings"] = notes["warnings"]
    if extra_meta:
        meta.update(extra_meta)
    return Snapshot(time=float(time), x=x2, fields=norm2,
                    widths=widths_from_x(x2), step=int(step),
                    source=source, meta=meta)


def _series_from_flash_files(paths: Sequence[Union[str, Path]],
                             cfg: FlychkHisConfig,
                             extraction_mode: str = "h5py",
                             verbose: bool = True) -> SnapshotSeries:
    """从 FLASH HDF5 文件列表构造序列 (叶子块, 扁平坐标)。"""
    from flash.output_processors.loader import FlashDataLoader

    snaps: List[Snapshot] = []
    for p in paths:
        p = Path(p)
        loader = FlashDataLoader(str(p))
        container = loader.load(compute_derived=False, extraction_mode=extraction_mode)
        x = getattr(container, "x", None)
        if x is None:
            raise ValueError(f"{p.name}: 未取得坐标 (extraction_mode={extraction_mode})")
        fields = dict(container.data)
        snap = _snapshot_from_columns(
            time=float(container.simulation_time), x=np.asarray(x),
            fields=fields, cfg=cfg, source=str(p),
            step=int(container.simulation_step),
            extra_meta={"file_type": container.file_type, "ndim": container.ndim,
                        "nblocks": container.nblocks,
                        "extraction_mode": extraction_mode},
        )
        snaps.append(snap)
        if verbose:
            print(f"  [源] {p.name}: t={snap.time:.4e}s, {snap.x.size} 单元, "
                  f"{len(snap.fields)} 变量")
    return SnapshotSeries(snaps, meta={"kind": "flash_hdf5",
                                       "files": [str(p) for p in paths],
                                       "extraction_mode": extraction_mode})


def _expand_flash_source(source: str, pattern: Optional[str] = None
                         ) -> List[Path]:
    """把文件/目录/通配符展开为 FLASH HDF5 文件列表。"""
    p = Path(source)
    if p.is_dir():
        pats = [pattern] if pattern else ["*hdf5_chk_*", "*hdf5_plt_cnt_*",
                                          "*chk*", "*plt*"]
        found: List[Path] = []
        for pat in pats:
            found.extend(sorted(p.glob(pat)))
        # 去重且保留稳定顺序
        seen, out = set(), []
        for f in found:
            if f.is_file() and f not in seen:
                seen.add(f)
                out.append(f)
        if not out:
            raise FileNotFoundError(f"目录 {source} 内未找到 FLASH HDF5 文件")
        return out
    if any(ch in str(source) for ch in "*?["):
        return [Path(f) for f in sorted(_glob.glob(str(source)))]
    if not p.is_file():
        raise FileNotFoundError(f"数据源不存在: {source}")
    return [p]


def _series_from_npz(path: str, cfg: FlychkHisConfig) -> SnapshotSeries:
    """从 .npz 构造序列。

    约定: `time` [nt] (或标量 times), `x` [nx]; 场为 (nt, nx) 的 2D 数组，
    键名可用别名 (te/tele, rho/dens, ...)。可选 `widths` [nx]。
    """
    data = np.load(path, allow_pickle=False)
    keys = set(data.files)
    tkey = "time" if "time" in keys else ("times" if "times" in keys else None)
    if tkey is None:
        raise ValueError(f"{path}: npz 缺少 'time'/'times' 键；含 {sorted(keys)}")
    times = np.atleast_1d(np.asarray(data[tkey], dtype=np.float64))
    if "x" not in keys:
        raise ValueError(f"{path}: npz 缺少 'x' 坐标键")
    x = np.asarray(data["x"], dtype=np.float64).ravel()
    widths = np.asarray(data["widths"], dtype=np.float64).ravel() if "widths" in keys else None

    snaps = []
    for i, t in enumerate(times):
        fields = {}
        for k in data.files:
            if k in (tkey, "x", "widths"):
                continue
            arr = np.asarray(data[k], dtype=np.float64)
            if arr.ndim == 2 and arr.shape[0] == times.size:
                fields[k] = arr[i]
            elif arr.ndim == 1 and arr.size == x.size:
                fields[k] = arr            # 单时间点常量场
        snap = _snapshot_from_columns(t, x, fields, cfg, source=path, step=i)
        if widths is not None and widths.size == x.size:
            snap.widths = widths
        snaps.append(snap)
    return SnapshotSeries(snaps, meta={"kind": "npz", "files": [str(path)]})


def _series_from_csv(path: str, cfg: FlychkHisConfig,
                     time_col: str = "time", x_col: str = "x") -> SnapshotSeries:
    """从长表 CSV 构造序列 (列: time, x, <物理量...>)。"""
    with open(path, "r", newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        raise ValueError(f"{path}: CSV 为空")
    header = list(rows[0].keys())
    if time_col not in header or x_col not in header:
        raise ValueError(f"{path}: CSV 需含 '{time_col}' 与 '{x_col}' 列，实际 {header}")
    field_cols = [c for c in header if c not in (time_col, x_col)]

    buckets: Dict[float, Dict[str, List[float]]] = {}
    for r in rows:
        t = float(r[time_col])
        b = buckets.setdefault(t, {c: [] for c in field_cols} | {"__x__": []})
        b["__x__"].append(float(r[x_col]))
        for c in field_cols:
            b[c].append(float(r[c]))

    snaps = []
    for i, t in enumerate(sorted(buckets)):
        b = buckets[t]
        fields = {c: np.asarray(b[c], dtype=np.float64) for c in field_cols}
        snaps.append(_snapshot_from_columns(
            t, np.asarray(b["__x__"], dtype=np.float64), fields, cfg,
            source=path, step=i))
    return SnapshotSeries(snaps, meta={"kind": "csv", "files": [str(path)],
                                       "columns": header})


def _series_from_json(path: str, cfg: FlychkHisConfig) -> SnapshotSeries:
    """从 JSON 构造序列。

    支持两种结构:
      A) {"times":[..], "x":[..], "fields":{"tele":[[..],..]}, "units":{...}}
      B) {"snapshots":[{"time":.., "x":[..], "fields":{...}}, ...]}
      C) {"snapshots":[{"time":.., "x":[..], "tele":[..]}, ...]}

    可选键 ``units`` 为该文件的**自我声明**单位 (如
    ``{"tele": "eV", "dens": "kg/m^3"}``)，会合并进 `input_units`，
    显式传入的 `config.input_units` 优先级更高。
    """
    with open(path, "r", encoding="utf-8") as fh:
        doc = json.load(fh)

    doc_units = dict(doc.get("units", {}) or {})
    eff_cfg = cfg.evolve(input_units={**doc_units, **cfg.input_units}) \
        if doc_units else cfg

    if "snapshots" in doc:
        snaps = []
        for i, s in enumerate(doc["snapshots"]):
            raw = s.get("fields", {k: v for k, v in s.items()
                                   if k not in ("time", "step", "x", "widths")})
            snaps.append(_snapshot_from_columns(
                float(s["time"]), np.asarray(s["x"], dtype=np.float64),
                {k: np.asarray(v, dtype=np.float64) for k, v in raw.items()},
                eff_cfg, source=path, step=int(s.get("step", i))))
        return SnapshotSeries(snaps, meta={"kind": "json", "files": [str(path)],
                                           "declared_units": doc_units})

    if "times" not in doc or "x" not in doc or "fields" not in doc:
        raise ValueError(f"{path}: JSON 需含 times/x/fields 或 snapshots 键")
    times = np.atleast_1d(np.asarray(doc["times"], dtype=np.float64))
    x = np.asarray(doc["x"], dtype=np.float64)
    snaps = []
    for i, t in enumerate(times):
        fields = {k: np.asarray(v, dtype=np.float64)[i] if np.asarray(v).ndim == 2
                  else np.asarray(v, dtype=np.float64)
                  for k, v in doc["fields"].items()}
        snaps.append(_snapshot_from_columns(t, x, fields, eff_cfg,
                                            source=path, step=i))
    return SnapshotSeries(snaps, meta={"kind": "json", "files": [str(path)],
                                       "declared_units": doc_units})


def _series_from_arrays(doc: Dict[str, Any], cfg: FlychkHisConfig,
                        source: str = "<dict>") -> SnapshotSeries:
    """从内存字典构造序列。

    结构:
      A) {"time": [nt], "x": [nx], "<field>": (nt, nx) 或标量, ...}
      B) {"snapshots": [{"time":.., "x":.., "<field>":..}, ...]}
    """
    if "snapshots" in doc:
        snaps = []
        for i, s in enumerate(doc["snapshots"]):
            raw = {k: v for k, v in s.items()
                   if k not in ("time", "step", "x", "widths")}
            snap = _snapshot_from_columns(
                float(s["time"]), np.asarray(s["x"], dtype=np.float64),
                {k: np.asarray(v, dtype=np.float64) for k, v in raw.items()},
                cfg, source=source, step=int(s.get("step", i)))
            snaps.append(snap)
        return SnapshotSeries(snaps, meta={"kind": "dict_snapshots"})

    if "x" not in doc:
        raise ValueError("字典数据源缺少 'x' 键")
    x = np.asarray(doc["x"], dtype=np.float64).ravel()
    tkey = "time" if "time" in doc else ("times" if "times" in doc else None)
    if tkey is None:
        raise ValueError("字典数据源缺少 'time'/'times' 键")
    times = np.atleast_1d(np.asarray(doc[tkey], dtype=np.float64))
    widths = np.asarray(doc["widths"], dtype=np.float64).ravel() if "widths" in doc else None

    snaps = []
    for i, t in enumerate(times):
        fields = {}
        for k, v in doc.items():
            if k in (tkey, "x", "widths"):
                continue
            arr = np.asarray(v, dtype=np.float64)
            if arr.ndim >= 2 and arr.shape[0] == times.size:
                fields[k] = arr[i]
            elif arr.ndim == 1 and arr.size == x.size:
                fields[k] = arr
            elif arr.ndim == 0:
                fields[k] = np.full(x.size, float(arr))
        snap = _snapshot_from_columns(t, x, fields, cfg, source=source, step=i)
        if widths is not None and widths.size == x.size:
            snap.widths = widths
        snaps.append(snap)
    return SnapshotSeries(snaps, meta={"kind": "dict"})


def _series_from_callable(fn: Callable, cfg: FlychkHisConfig,
                          times: Sequence[float],
                          source: str = "<callable>") -> SnapshotSeries:
    """从回调构造序列: fn(t) -> {field: 值或数组} 或 fn(x, t) -> {field: 数组}。"""
    reps = np.asarray(times, dtype=np.float64)
    if reps.size == 0:
        raise ValueError("callable 数据源必须提供非空 times")
    snaps = []
    for i, t in enumerate(reps):
        try:
            doc = fn(t)
        except TypeError:
            raise ValueError("callable 数据源签名应为 f(t) -> dict")
        if not isinstance(doc, dict) or "x" not in doc:
            raise ValueError("callable 返回的字典必须含 'x' 键")
        fields = {k: v for k, v in doc.items() if k != "x"}
        snaps.append(_snapshot_from_columns(
            float(t), np.asarray(doc["x"], dtype=np.float64), fields, cfg,
            source=source, step=i))
    return SnapshotSeries(snaps, meta={"kind": "callable"})


# ══════════════════════════════════════════════════════════
# 合成数据 (测试/演示; 非真实仿真结果)
# ══════════════════════════════════════════════════════════
def synthetic_ch_ti_slab(
    n_time: int = 8,
    tmax: float = 1.6e-9,
    t0: float = 2.0e-10,
    nx: int = 480,
    x_min: float = -100.0e-4,
    x_max: float = 100.0e-4,
    rho_ch: float = 0.25,
    rho_fill: float = 1.0e-6,
    te_peak: float = 1200.0,
    te_cold: float = 30.0,
    v_abl: float = 2.0e5,
    tracer_depths: Sequence[float] = (1.0e-4, 2.0e-4, 3.0e-4),
    with_labels: bool = True,
) -> SnapshotSeries:
    """生成合成的 CH 烧蚀靶 + Ti 示踪层时间序列 (解析模型, **非** FLASH 结果)。

    几何: 激光自左入射, 初始 CH 平板占 ``x ∈ [-50µm, +50µm]``, 其余为本底填充
    气体; 烧蚀面向 +x 推进 ``x_a(t) = -50µm + v_abl·t``。

    物理量为显式解析式 (cgs / K):

    - 质量密度 (烧蚀稀疏 + 本底)::

          rho(x,t) = rho_fill + (rho_ch - rho_fill)·exp(-max(x_a - x, 0)/L_c)
                     (x ≤ +50µm)               , L_c = 20 µm
          rho(x,t) = rho_fill                 (x > +50µm)

      示踪层: 在 ``x_a(t) + d_k`` 处叠加 ``5%·rho_ch`` 的高斯增量 (σ=0.35 µm),
      即示踪层随烧蚀面一起运动 (拉格朗日视角)。

    - 电子温度 (峰值在临界面 ``x_c = x_a + 10µm`` 附近)::

          Te_peak(t) = te_peak·(t/tmax)^0.25
          L_te(t)    = 25µm + 1e7·t
          Te(x,t)    = te_cold + (Te_peak - te_cold)·exp(-|x - x_c|/L_te)

    - 离子/辐射温度: ``Ti = 0.8 Te``, ``Tr = 0.6 Te``
    - 丰度 (CH 平均电离近似): ``Zbar = 3.5``, ``ye = Zbar/13.011`` mol e⁻/g,
      ``sumy = 1/13.011`` mol ions/g
    - 材料标签 ``matid``: 0=填充气体, 1=CH, 2=Ti 示踪层 (仅 `with_labels=True`)

    返回 `SnapshotSeries.meta["synthetic"] = True`。
    """
    if n_time < 1:
        raise ValueError("n_time 必须 >= 1")
    if tmax <= 0:
        raise ValueError("tmax 必须 > 0")
    times = np.linspace(max(t0, 1e-13), tmax, n_time)
    x = np.linspace(x_min, x_max, nx)

    zbar = 3.5                       # 平均电离度 (示例值)
    ye = zbar / 13.011               # mol e-/g
    sumy = 1.0 / 13.011              # mol ions/g
    x_ch_lo, x_ch_hi = -50.0e-4, 50.0e-4
    L_c = 20.0e-4                    # 烧蚀稀疏标长 (cm)
    d_crit = 10.0e-4                 # 临界面位于烧蚀面内侧 10 µm

    snaps: List[Snapshot] = []
    for i, t in enumerate(times):
        x_a = x_ch_lo + v_abl * t                     # 烧蚀面 (cm)
        x_c = x_a + d_crit                            # 临界面 (cm)
        te_pk = te_peak * (t / tmax) ** 0.25
        L_te = 25.0e-4 + 1.0e7 * t

        # ── 密度 ──
        decay = np.exp(-np.clip(x_a - x, 0.0, None) / L_c)
        dens = rho_fill + (rho_ch - rho_fill) * decay
        dens = np.where(x > x_ch_hi, rho_fill, dens)
        dens = np.where(x < x_ch_lo, rho_fill, dens)

        # ── 温度 ──
        tele = te_cold + (te_pk - te_cold) * np.exp(-np.abs(x - x_c) / L_te)
        tele = np.maximum(tele, 1.0)
        tion = 0.8 * tele
        trad = 0.6 * tele

        tracer_pos = [x_a + float(d) for d in tracer_depths]
        for x_tr in tracer_pos:
            dens = dens + 0.05 * rho_ch * np.exp(-((x - x_tr) / 0.35e-4) ** 2)

        fields = {
            "dens": dens,
            "tele": tele,
            "tion": tion,
            "trad": trad,
            "ye": np.full_like(dens, ye),
            "sumy": np.full_like(dens, sumy),
        }
        if with_labels:
            dx = float(np.mean(np.diff(x))) if x.size > 1 else 1.0e-4
            band_half = max(0.45e-4, 0.75 * dx)     # 保证粗网格下仍能命中示踪层
            matid = np.zeros_like(x, dtype=np.float64)
            matid[(x >= x_ch_lo) & (x <= x_ch_hi)] = 1.0   # CH 物质 (含烧蚀等离子体)
            for x_tr in tracer_pos:                        # Ti 示踪层
                band = np.abs(x - x_tr) <= band_half
                if not band.any():
                    band[int(np.argmin(np.abs(x - x_tr)))] = True
                matid[band] = 2.0
            fields["matid"] = matid
        snaps.append(_snapshot_from_columns(
            float(t), x, fields, _SYNTH_INPUT_CFG,
            source=f"synthetic:ch_ti_slab[{i}]", step=i))

    return SnapshotSeries(snaps, meta={
        "kind": "synthetic", "synthetic": True,
        "model": "analytic CH slab + Ti tracer (NOT a FLASH simulation)",
        "zbar": zbar, "tracer_depths": list(tracer_depths),
        "x_ch_range_cm": [x_ch_lo, x_ch_hi], "v_abl": v_abl,
    })


# ══════════════════════════════════════════════════════════
# 统一入口
# ══════════════════════════════════════════════════════════
def load_series(source: Any = None, config: Optional[FlychkHisConfig] = None,
                extraction_mode: str = "h5py",
                pattern: Optional[str] = None,
                times: Optional[Sequence[float]] = None,
                verbose: bool = True,
                **synthetic_kwargs) -> SnapshotSeries:
    """统一加载入口 — 按 source 类型自动派发。

    Args:
        source: 见模块 docstring 的支持表；None → 合成数据
        config: `FlychkHisConfig`（提供 input_units / 元素信息）
        extraction_mode: FLASH HDF5 提取模式 ('h5py' | 'yt')
        pattern: 目录源的 glob 覆盖
        times: callable 源或自身为 callable 时的时间点
        verbose: 打印加载摘要
        **synthetic_kwargs: source=None 时透传给 `synthetic_ch_ti_slab`

    Returns:
        SnapshotSeries
    """
    cfg = config or FlychkHisConfig()

    # ── 合成数据 ──
    if source is None:
        series = synthetic_ch_ti_slab(**synthetic_kwargs)
        if verbose:
            print(f"  [源] 合成数据: {series.n_time} 时间点 × "
                  f"{series[0].x.size} 单元 (解析模型)")
        return series

    series = _dispatch_series(source, cfg, extraction_mode, pattern, times,
                              verbose, synthetic_kwargs)
    warn = _collect_unit_warnings(series)
    if warn and verbose:
        for w in warn:
            print(f"  [单位告警] {w}")
    return series


def _dispatch_series(source: Any, cfg: FlychkHisConfig, extraction_mode: str,
                     pattern: Optional[str], times: Optional[Sequence[float]],
                     verbose: bool, synthetic_kwargs: Dict[str, Any]
                     ) -> SnapshotSeries:
    """按 source 类型派发到具体适配器 (load_series 的实现体)。"""
    # ── callable ──
    if callable(source):
        if times is None:
            raise ValueError("callable 数据源必须通过 times= 提供时间点序列")
        return _series_from_callable(source, cfg, times)

    # ── 内存字典 ──
    if isinstance(source, dict):
        return _series_from_arrays(source, cfg)

    # ── 路径 / 通配 / 目录 ──
    if isinstance(source, (str, Path)):
        s = str(source)
        low = s.lower()
        if low.endswith(".npz"):
            return _series_from_npz(s, cfg)
        if low.endswith(".csv"):
            return _series_from_csv(s, cfg)
        if low.endswith(".json"):
            return _series_from_json(s, cfg)
        paths = _expand_flash_source(s, pattern=pattern)
        if verbose:
            print(f"  [源] FLASH HDF5 × {len(paths)} 文件 (mode={extraction_mode})")
        return _series_from_flash_files(paths, cfg,
                                        extraction_mode=extraction_mode,
                                        verbose=verbose)

    # ── 快照字典列表 ──
    if isinstance(source, (list, tuple)):
        items = list(source)
        if not items:
            raise ValueError("数据源列表为空")
        if all(isinstance(v, dict) for v in items):
            return _series_from_arrays({"snapshots": items}, cfg)
        if all(isinstance(v, (str, Path)) for v in items):
            if str(items[0]).lower().endswith(".npz"):
                snaps: List[Snapshot] = []
                for p in items:
                    snaps.extend(_series_from_npz(str(p), cfg).snapshots)
                return SnapshotSeries(snaps, meta={"kind": "npz_list",
                                                  "files": [str(p) for p in items]})
            return _series_from_flash_files([Path(v) for v in items], cfg,
                                            extraction_mode=extraction_mode,
                                            verbose=verbose)
        raise ValueError(f"无法识别的列表元素类型: {type(items[0]).__name__}")

    if isinstance(source, np.ndarray):
        if times is None:
            raise ValueError("传入 ndarray 坐标时必须用 times= 提供时间点")
        return _series_from_callable(lambda t: {"x": source}, cfg, times)

    raise TypeError(f"不支持的数据源类型: {type(source).__name__}")


def _collect_unit_warnings(series: SnapshotSeries) -> List[str]:
    """汇总序列中各快照的单位自洽性告警 (去重)。"""
    seen: List[str] = []
    for s in series:
        for w in s.meta.get("unit_warnings", []):
            if w not in seen:
                seen.append(w)
    return seen


__all__ = [
    "Snapshot", "SnapshotSeries", "load_series", "synthetic_ch_ti_slab",
    "normalize_fields", "widths_from_x", "dedup_and_sort",
    "FIELD_ALIASES", "DEFAULT_INPUT_UNITS",
]
