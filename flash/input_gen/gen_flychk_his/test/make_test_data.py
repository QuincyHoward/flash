#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_test_data.py — gen_flychk_his 测试数据生成器
=================================================

**自定义合成数据**（无网络、无 FLASH 运行依赖、确定性可复现），覆盖
`gen_flychk_his` 支持的全部数据源形态:

============================ ============================================
产物                          用途
============================ ============================================
``flash_hdf5/xchk_000N``     合成 **FLASH 格式** 1D HDF5 序列 (chk) —
                             供 `FlashDataLoader(extraction_mode="h5py")` 直读
``hist_series.npz``          多个 (nt, nx) 场 + time/x 坐标
``hist_long.csv``            长表 (time, x, te, ti, tr, rho, trac)
``hist_series.json``         times/x/fields 结构
``hist_snapshots.json``      snapshots 列表结构
``hist_units.json``          温度 eV / 密度 kg·m^-3 + ``units`` 自声明
============================ ============================================

**单位约定**: 除 ``hist_units.json`` 外，全部产物均使用 FLASH 原生单位
(温度 **K**、密度 **g/cm³**、长度 **cm**、时间 **s**)，因此无需任何
`input_units` 覆盖即可直接用；``hist_units.json`` 专门用于验证非 cgs 单位
与 JSON 自声明单位两条路径。

物理剖面 (解析模型, 与 `sources.synthetic_ch_ti_slab` 同源, 单位为
FLASH 原生 cgs/K):

- 坐标 ``x ∈ [-100, +100] µm``, ``nx = 240``
- 初始 CH 平板 ``x ∈ [-50, +50] µm`` (rho = 0.25 g/cm³), 外侧本底 1e-6 g/cm³
- 烧蚀面 ``x_a(t) = -50µm + v_abl·t``, ``v_abl = 2e5 cm/s`` (向 +x 推进)
- 电子温度 (FLASH 单位 **K**)::

      Te_peak(t) = 1200 eV · (t/tmax)^0.25 · K_PER_EV
      x_c(t)     = x_a(t) + 10 µm        (临界面)
      L_te(t)    = 25 µm + 1e7·t
      Te(x,t)    = Te_cold + (Te_peak - Te_cold)·exp(-|x - x_c| / L_te)

- ``Ti = 0.8 Te``, ``Tr = 0.6 Te`` (K)
- ``ye = 3.5/13.011`` mol e⁻/g, ``sumy = 1/13.011`` mol ions/g
- 示踪层: 在 ``x_a(t) + d_k`` (d_k = 1/2/3 µm) 处叠加 5%·rho_ch 高斯增量
- 变量 ``trac`` (FLASH 名 ≤4 字符): 0=无, k=第 k 层 Ti 示踪层

用法::

    python flash/input_gen/gen_flychk_his/test/make_test_data.py            # 生成 (幂等)
    python flash/input_gen/gen_flychk_his/test/make_test_data.py --force    # 强制重建
    python flash/input_gen/gen_flychk_his/test/make_test_data.py --status   # 查看状态
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np

# ── 路径与常量 ─────────────────────────────────────────────
_HERE = Path(__file__).resolve().parent
DATA_DIR = _HERE / "data"

K_PER_EV = 1.0 / 8.617333262e-5      # 11604.518121550082 K/eV
N_A = 6.02214076e23

X_MIN, X_MAX = -100.0e-4, 100.0e-4   # cm
NX = 800                             # 0.25 µm 网格 —— 可分辨 1/2/3 µm 示踪层
CH_LO, CH_HI = -50.0e-4, 50.0e-4     # cm
RHO_CH, RHO_FILL = 0.25, 1.0e-6      # g/cm^3
TE_PEAK_EV, TE_COLD_EV = 1200.0, 30.0
D_CRIT = 10.0e-4                     # cm
L_C = 20.0e-4                        # 烧蚀稀疏标长 (cm)
V_ABL = 2.0e5                        # cm/s
TRACER_DEPTHS = (1.0e-4, 2.0e-4, 3.0e-4)
ZBAR = 3.5
SERIES_TIMES = np.linspace(2.0e-10, 1.6e-9, 8)
TMAX = float(SERIES_TIMES[-1])

# FLASH 4.8 变量名 <= 4 字符
FLASH_VARS = ("dens", "tele", "tion", "trad", "ye", "sumy", "trac", "pres", "velx")


# ══════════════════════════════════════════════════════════
# 物理剖面
# ══════════════════════════════════════════════════════════
def profiles(t: float, nx: int = NX):
    """返回 (x [cm], fields dict)。温度单位为 **K** (FLASH 原生), 密度 g/cm^3。"""
    x = np.linspace(X_MIN, X_MAX, nx)
    x_a = CH_LO + V_ABL * t
    x_c = x_a + D_CRIT
    te_pk_ev = TE_PEAK_EV * (t / TMAX) ** 0.25
    L_te = 25.0e-4 + 1.0e7 * t

    decay = np.exp(-np.clip(x_a - x, 0.0, None) / L_C)
    dens = RHO_FILL + (RHO_CH - RHO_FILL) * decay
    dens = np.where((x < CH_LO) | (x > CH_HI), RHO_FILL, dens)

    te_ev = TE_COLD_EV + (te_pk_ev - TE_COLD_EV) * np.exp(-np.abs(x - x_c) / L_te)
    te_ev = np.maximum(te_ev, 1.0)
    ti_ev = 0.8 * te_ev

    trac = np.zeros_like(x)
    for k, d in enumerate(TRACER_DEPTHS, start=1):
        x_tr = x_a + float(d)
        g = np.exp(-((x - x_tr) / 0.35e-4) ** 2)
        dens = dens + 0.05 * RHO_CH * g
        band = np.abs(x - x_tr) <= 0.45e-4
        if not band.any():                              # 粗网格保护
            band[int(np.argmin(np.abs(x - x_tr)))] = True
        trac[band] = float(k)

    # 压力 (dyne/cm^2) = (ne·Te + ni·Ti) [eV] × 1.602176634e-12 erg/eV
    ne = dens * (ZBAR / 13.011) * N_A
    ni = dens * (1.0 / 13.011) * N_A
    pres = (ne * te_ev + ni * ti_ev) * 1.602176634e-12

    fields = {
        "dens": dens,
        "tele": te_ev * K_PER_EV,        # K
        "tion": ti_ev * K_PER_EV,        # K
        "trad": 0.6 * te_ev * K_PER_EV,  # K
        "ye": np.full_like(x, ZBAR / 13.011),
        "sumy": np.full_like(x, 1.0 / 13.011),
        "trac": trac,
        "pres": pres,
        "velx": np.zeros_like(x),
    }
    return x, fields


# ══════════════════════════════════════════════════════════
# FLASH 格式 HDF5 (与 output_processors.FlashHDF5File 读取逻辑兼容)
# ══════════════════════════════════════════════════════════
def write_flash_hdf5(path: Path, vars_data: dict, x: np.ndarray,
                     time: float, nstep: int) -> None:
    """写入一个合成 1D FLASH HDF5 chk 文件。

    结构对照 `flash/output_processors/test/gen_test_data.py` (同一读取契约):
    变量为 (nblocks=1, 1, 1, nx); `unknown names` 用 (n,1) |S4 固定 4 字节布局。
    """
    import h5py

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    nx = x.size
    dx = float(np.mean(np.diff(x))) if nx > 1 else 1.0

    with h5py.File(str(path), "w") as f:
        for name, arr in vars_data.items():
            f.create_dataset(name, data=np.asarray(arr, dtype=np.float64)
                             .reshape(1, 1, 1, nx))

        f.create_dataset("unknown names",
                         data=np.array([n.encode("utf-8") for n in vars_data],
                                       dtype="S4").reshape(-1, 1))

        rs_dt = np.dtype([("name", "S80"), ("value", "f8")])
        rs = np.array([("time", float(time)), ("dt", 1.0e-14),
                       ("dtold", 1.0e-14), ("dtnew", 1.0e-14),
                       ("xmin", float(x[0] - 0.5 * dx)),
                       ("xmax", float(x[-1] + 0.5 * dx)),
                       ("ymin", 0.0), ("ymax", 0.0),
                       ("zmin", 0.0), ("zmax", 0.0),
                       ("gamma", 5.0 / 3.0)], dtype=rs_dt)
        f.create_dataset("real scalars", data=rs)

        is_dt = np.dtype([("name", "S80"), ("value", "i4")])
        isc = np.array([("nstep", int(nstep)), ("nxb", nx), ("nyb", 1),
                        ("nzb", 1), ("dimensionality", 1),
                        ("globalnumblocks", 1)], dtype=is_dt)
        f.create_dataset("integer scalars", data=isc)

        ss_dt = np.dtype([("name", "S80"), ("value", "S80")])
        f.create_dataset("string scalars",
                         data=np.array([("geometry", "cartesian"),
                                        ("eos", "multigamma")], dtype=ss_dt))

        sim_dt = np.dtype([("file format version", "i4"), ("flash version", "S80"),
                           ("build date", "S80"), ("setup call", "S80"),
                           ("eos", "S80"), ("geometry", "S80")])
        sim = np.zeros(1, dtype=sim_dt)
        sim["file format version"] = 8
        sim["flash version"] = b"FLASH 4.8 (synthetic for gen_flychk_his)"
        sim["build date"] = b"2026-09-10"
        sim["setup call"] = b"./setup -auto gen_flychk_his -1d +cartesian"
        sim["eos"] = b"multigamma"
        sim["geometry"] = b"cartesian"
        f.create_dataset("sim info", data=sim)

        rr_dt = np.dtype([("name", "S80"), ("value", "f8")])
        f.create_dataset("real runtime parameters",
                         data=np.array([("ed_time_1_1", 0.0),
                                        ("ed_time_1_2", 1.6e-9),
                                        ("ed_power_1_1", 0.0),
                                        ("ed_power_1_2", 5.0e14)], dtype=rr_dt))

        bbox = np.array([[[float(x[0] - 0.5 * dx), float(x[-1] + 0.5 * dx)],
                          [0.0, 0.0], [0.0, 0.0]]], dtype=np.float64)
        f.create_dataset("bounding box", data=bbox)
        f.create_dataset("node type", data=np.ones(1, dtype=np.int32))
        f.create_dataset("refine level", data=np.ones(1, dtype=np.int32))
        f.create_dataset("gid", data=np.full((1, 8), -1, dtype=np.int32))
        f.create_dataset("coordinates", data=np.zeros((1, 3), dtype=np.float64))
        f.create_dataset("block size", data=np.full((1, 3), dx, dtype=np.float64))


def gen_flash_hdf5(dir_path: Path, times=SERIES_TIMES, force: bool = False):
    """生成一串合成 FLASH HDF5 chk 文件 (时间递增)。返回路径列表。"""
    dir_path = Path(dir_path)
    dir_path.mkdir(parents=True, exist_ok=True)
    paths = []
    for i, t in enumerate(times, start=1):
        p = dir_path / f"xchk_hdf5_chk_{i:04d}"
        paths.append(p)
        if p.exists() and not force:
            continue
        x, fields = profiles(float(t))
        write_flash_hdf5(p, {k: fields[k] for k in FLASH_VARS}, x,
                         time=float(t), nstep=i * 100)
    return paths


# ══════════════════════════════════════════════════════════
# 其他数据源
# ══════════════════════════════════════════════════════════
def _stack(times=SERIES_TIMES, nx: int = NX, in_ev: bool = False):
    """返回 (x, times, {name: (nt, nx)})。

    ``in_ev=False`` (默认) 时温度为 **K**，与 FLASH 原生单位一致 —— 配合
    默认的 `input_units` (K) 可直接使用；``in_ev=True`` 时温度换算为 eV，
    用于演示/验证 JSON 自声明单位 (`units` 键)。
    """
    xs, stack, records = None, {}, []
    for t in times:
        x, fields = profiles(float(t), nx=nx)
        xs = x
        records.append(fields)
    for n in records[0]:
        stack[n] = np.stack([r[n] for r in records], axis=0)
    if in_ev:
        for n in ("tele", "tion", "trad"):
            stack[n] = stack[n] / K_PER_EV
    return xs, np.asarray(times), stack


def gen_npz(path: Path, force: bool = False):
    """生成 npz 数据源 (温度 **K**, 密度 g/cm^3 —— FLASH 原生单位)。"""
    path = Path(path)
    if path.exists() and not force:
        return path
    x, t, stack = _stack()
    payload = {"time": t, "x": x}
    for n, arr in stack.items():
        payload[n] = arr
    np.savez_compressed(str(path), **payload)
    return path


def gen_csv(path: Path, force: bool = False):
    """生成长表 CSV (列: time, x, te[K], ti[K], tr[K], rho, trac)。"""
    path = Path(path)
    if path.exists() and not force:
        return path
    x, times, stack = _stack()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["time", "x", "te", "ti", "tr", "rho", "trac"])
        for it, t in enumerate(times):
            for ix in range(x.size):
                w.writerow([f"{t:.8e}", f"{x[ix]:.10e}",
                            f"{stack['tele'][it, ix]:.8e}",
                            f"{stack['tion'][it, ix]:.8e}",
                            f"{stack['trad'][it, ix]:.8e}",
                            f"{stack['dens'][it, ix]:.8e}",
                            f"{stack['trac'][it, ix]:.1f}"])
    return path


def gen_json(path: Path, force: bool = False, snapshots_form: bool = False):
    """生成 JSON 数据源 (温度 K, 密度 g/cm^3; 两种结构)。"""
    path = Path(path)
    if path.exists() and not force:
        return path
    x, times, stack = _stack()
    path.parent.mkdir(parents=True, exist_ok=True)
    if snapshots_form:
        doc = {"snapshots": [
            {"time": float(t), "x": x.tolist(),
             **{n: stack[n][i].tolist() for n in stack}}
            for i, t in enumerate(times)
        ]}
    else:
        doc = {"times": times.tolist(), "x": x.tolist(),
               "fields": {n: stack[n].tolist() for n in stack}}
    path.write_text(json.dumps(doc), encoding="utf-8", newline="\n")
    return path


def gen_units_json(path: Path, force: bool = False):
    """温度以 eV、密度以 kg·m^-3 输入, 并通过 ``units`` 键**自声明**单位。

    用于验证 `input_units` (显式覆盖) 与 JSON 自声明单位两条路径。
    """
    path = Path(path)
    if path.exists() and not force:
        return path
    x, times, stack = _stack(in_ev=True)
    doc = {"times": times.tolist(), "x": x.tolist(),
           "units": {"tele": "eV", "tion": "eV", "trad": "eV",
                     "rho": "kg/m^3"},
           "fields": {
               "tele": stack["tele"].tolist(),            # eV
               "tion": stack["tion"].tolist(),            # eV
               "trad": stack["trad"].tolist(),            # eV
               "rho": (stack["dens"] * 1000.0).tolist(),  # kg/m^3
               "trac": stack["trac"].tolist(),
           }}
    path.write_text(json.dumps(doc), encoding="utf-8", newline="\n")
    return path


def gen_memory_dict(nx: int = NX):
    """内存字典数据源 (温度 K, 密度 g/cm^3, 与 FLASH 同单位)。"""
    x, fields = profiles(TMAX, nx=nx)
    times = SERIES_TIMES
    stack = {k: [] for k in ("dens", "tele", "tion", "trad", "trac")}
    for t in times:
        _, f = profiles(float(t), nx=nx)
        for k in stack:
            stack[k].append(f[k])
    doc = {"time": times, "x": x}
    for k, v in stack.items():
        doc[k] = np.stack(v, axis=0)
    return doc


# ══════════════════════════════════════════════════════════
# 统一入口
# ══════════════════════════════════════════════════════════
def ensure_test_data(root=None, force: bool = False, verbose: bool = True):
    """生成全部测试数据 (幂等)。返回 {名称: 路径} 字典。"""
    base = Path(root) if root else DATA_DIR
    base.mkdir(parents=True, exist_ok=True)

    files = {
        "flash_hdf5_dir": base / "flash_hdf5",
        "npz": base / "hist_series.npz",
        "csv": base / "hist_long.csv",
        "json": base / "hist_series.json",
        "json_snapshots": base / "hist_snapshots.json",
        "json_units": base / "hist_units.json",
    }
    h5_paths = gen_flash_hdf5(files["flash_hdf5_dir"], force=force)
    gen_npz(files["npz"], force=force)
    gen_csv(files["csv"], force=force)
    gen_json(files["json"], force=force)
    gen_json(files["json_snapshots"], force=force, snapshots_form=True)
    gen_units_json(files["json_units"], force=force)

    out = dict(files)
    out["flash_files"] = h5_paths
    if verbose:
        print(f"[数据] 根目录: {base}")
        print(f"  [FLASH HDF5] {len(h5_paths)} 文件 → {h5_paths[0].parent}")
        for k in ("npz", "csv", "json", "json_snapshots", "json_units"):
            p = Path(out[k])
            print(f"  [{k:<14s}] {p.name}  ({p.stat().st_size / 1024:.1f} KB)")
    return out


def cleanup_test_data(root=None) -> int:
    """删除生成的测试数据，返回删除的文件数。"""
    import shutil
    base = Path(root) if root else DATA_DIR
    if not base.exists():
        return 0
    n = sum(1 for p in base.rglob("*") if p.is_file())
    shutil.rmtree(base)
    return n


def data_status(root=None) -> str:
    base = Path(root) if root else DATA_DIR
    if not base.exists():
        return f"未生成 ({base})"
    n = sum(1 for p in base.rglob("*") if p.is_file())
    return f"已生成 {n} 个文件, 共 {sum(p.stat().st_size for p in base.rglob('*') if p.is_file()) / 1024:.1f} KB ({base})"


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="gen_flychk_his 测试数据生成器")
    p.add_argument("--force", action="store_true", help="强制重建")
    p.add_argument("--clean", action="store_true", help="删除已生成数据")
    p.add_argument("--status", action="store_true", help="查看状态")
    p.add_argument("--root", default=None, help="数据根目录 (默认 test/data)")
    args = p.parse_args(argv)

    if args.status:
        print(data_status(args.root))
        return 0
    if args.clean:
        print(f"[清理] 删除 {cleanup_test_data(args.root)} 个文件")
        return 0
    ensure_test_data(args.root, force=args.force)
    return 0


if __name__ == "__main__":
    sys.exit(main())
