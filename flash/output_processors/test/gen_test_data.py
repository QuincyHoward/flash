#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_test_data.py — 生成 output_processors 测试所需的合成 FLASH HDF5 数据
==========================================================================

背景
----
`flash/output_processors/inputfiles/` 下的 FLASH HDF5 测试数据
（`hdf5files_1d/2d/3d/`）被 `.gitignore` 排除，克隆/发布包中不含，
导致 output_processors 套件 13 个用例因数据缺失而失败。

本脚本生成**合成 FLASH 格式** HDF5 文件（与 FlashHDF5File/FlashDataLoader
读取逻辑完全兼容），保证任何干净环境测试自愈。

用法
----
    python flash/output_processors/test/gen_test_data.py        # 生成全部
    python flash/output_processors/test/gen_test_data.py --force  # 强制重建

说明
----
- 幂等: 目标文件已存在且有效时跳过（避免重复写盘）。
- 数据为合成剖面（非真实物理仿真），仅用于验证加载/解析/单位转换逻辑。
- LF 换行、确定性生成（无随机数），可重复生成完全一致的文件。
"""

import os
import sys
from pathlib import Path

import h5py
import numpy as np

# ── 路径 ──────────────────────────────────────────────────────
_HERE = Path(__file__).resolve().parent                       # .../output_processors/test
_INPUTFILES = (_HERE / ".." / "inputfiles").resolve()         # .../output_processors/inputfiles
# 注: 各测试文件位于 test/<sub>/ 下, 使用 "../../inputfiles" 定位到
# output_processors/inputfiles (test/<sub>/../.. = output_processors)。

# 原始变量集 (FLASH 风格)
RAW_VARS = [
    "dens", "tele", "tion", "pres", "velx", "pele", "pion",
    "ye", "sumy", "targ", "cham", "shok", "eint", "depo", "game", "gamc",
]


def _write_lf(path: Path, content: str):
    path.write_bytes(content.replace("\r\n", "\n").encode("utf-8"))


def _make_1d_vars(nx: int, nblocks: int) -> dict:
    """1D 合成剖面 (nblocks, 1, 1, nx)。tele 线性变化使梯度标长有意义。"""
    x = np.linspace(-1.0, 1.0, nx)
    dens = np.full((nblocks, 1, 1, nx), 2.7, dtype=np.float64)
    tele = np.broadcast_to(300.0 + 200.0 * x, (nblocks, 1, 1, nx)).copy()
    v = {
        "dens": dens,
        "tele": tele,
        "tion": np.full_like(dens, 300.0),
        "pres": np.full_like(dens, 1e15),
        "velx": np.full_like(dens, 1e5),
        "pele": np.full_like(dens, 1e12),
        "pion": np.full_like(dens, 1e11),
        "ye": np.full_like(dens, 0.5),
        "sumy": np.full_like(dens, 1.0),
        "targ": np.full_like(dens, 0.5),
        "cham": np.full_like(dens, 0.5),
        "shok": np.zeros_like(dens),
        "eint": np.full_like(dens, 1e12),
        "depo": np.zeros_like(dens),
        "game": np.full_like(dens, 5.0 / 3.0),
        "gamc": np.full_like(dens, 1.1),
    }
    return v


def _make_2d_vars(nx: int, ny: int, nblocks: int) -> dict:
    """2D 合成剖面 (nblocks, 1, ny, nx)。"""
    base = _make_1d_vars(nx, nblocks)
    out = {}
    for k, a in base.items():
        out[k] = np.broadcast_to(a[:, :, :1, :], (nblocks, 1, ny, nx)).copy()
    return out


def _make_3d_vars(nx: int, ny: int, nz: int, nblocks: int) -> dict:
    """3D 合成剖面 (nblocks, nz, ny, nx)。"""
    base = _make_1d_vars(nx, nblocks)
    out = {}
    for k, a in base.items():
        out[k] = np.broadcast_to(a[:, :1, :1, :], (nblocks, nz, ny, nx)).copy()
    return out


def write_flash_hdf5(path: Path, vars_data: dict, bbox: np.ndarray,
                     time: float, nstep: int, dim: int,
                     geometry: str = "cartesian"):
    """按 FLASH HDF5 约定写入一个合成文件。dim: 1/2/3 空间维度。"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    nblocks = bbox.shape[0]
    first = next(iter(vars_data.values()))
    nz, ny, nx = first.shape[1], first.shape[2], first.shape[3]

    with h5py.File(str(path), "w") as f:
        # ── 物理量 (FLASH 布局: (nblocks, nz, ny, nx)) ──
        for name, arr in vars_data.items():
            f.create_dataset(name, data=arr.astype(np.float64))

        # ── 变量名映射 (简单 S80 数组, yt frontend 兼容) ──
        f.create_dataset("unknown names",
                         data=np.array([n.encode("utf-8") for n in vars_data.keys()],
                                       dtype="S80"))

        # ── 标量 ──
        rs_dt = np.dtype([("name", "S80"), ("value", "f8")])
        xmin, xmax = float(bbox[:, 0, 0].min()), float(bbox[:, 0, 1].max())
        ymin, ymax = float(bbox[:, 1, 0].min()), float(bbox[:, 1, 1].max())
        zmin, zmax = float(bbox[:, 2, 0].min()), float(bbox[:, 2, 1].max())
        rs = np.array([("time", float(time)), ("dt", 1.0e-12),
                       ("dtold", 1.0e-12), ("dtnew", 1.0e-12),
                       ("xmin", xmin), ("xmax", xmax),
                       ("ymin", ymin), ("ymax", ymax),
                       ("zmin", zmin), ("zmax", zmax),
                       ("gamma", 5.0 / 3.0)], dtype=rs_dt)
        f.create_dataset("real scalars", data=rs)

        is_dt = np.dtype([("name", "S80"), ("value", "i4")])
        isc = np.array([("nstep", int(nstep)), ("nxb", nx), ("nyb", ny),
                        ("nzb", nz), ("dimensionality", int(dim)), ("globalnumblocks", nblocks)],
                       dtype=is_dt)
        f.create_dataset("integer scalars", data=isc)

        # yt frontend 从 string scalars 读取 geometry 等字符串参数
        ss_dt = np.dtype([("name", "S80"), ("value", "S80")])
        ss = np.array([("geometry", geometry), ("eos", "multigamma")], dtype=ss_dt)
        f.create_dataset("string scalars", data=ss)

        # ── 仿真信息 (yt frontend 需要 file format version 字段) ──
        sim_dt = np.dtype([("file format version", "i4"),
                           ("flash version", "S80"), ("build date", "S80"),
                           ("setup call", "S80"), ("eos", "S80"),
                           ("geometry", "S80")])
        sim = np.zeros(1, dtype=sim_dt)
        sim["file format version"] = 8
        sim["flash version"] = b"FLASH 4.8 (synthetic)"
        sim["build date"] = b"2026-08-12"
        sim["setup call"] = b"./setup -auto synthetic -1d +cartesian"
        sim["eos"] = b"multigamma"
        sim["geometry"] = geometry.encode("utf-8")
        f.create_dataset("sim info", data=sim)

        # ── 激光参数 (real runtime parameters) ──
        rr_dt = np.dtype([("name", "S80"), ("value", "f8")])
        rr = np.array([("ed_time_1_1", 0.0), ("ed_time_1_2", 0.3e-10),
                       ("ed_power_1_1", 0.0), ("ed_power_1_2", 5.0e14)], dtype=rr_dt)
        f.create_dataset("real runtime parameters", data=rr)

        # ── AMR 元信息 ──
        f.create_dataset("bounding box", data=bbox.astype(np.float64))   # (nblocks, 3, 2)
        f.create_dataset("node type", data=np.ones(nblocks, dtype=np.int32))  # 全叶节点
        f.create_dataset("refine level", data=np.ones(nblocks, dtype=np.int32))
        # gid: 块父子关系 (yt frontend 读取)。全 -1 = 无子块 (单层无 AMR)。
        f.create_dataset("gid", data=np.full((nblocks, 8), -1, dtype=np.int32))
        f.create_dataset("coordinates", data=np.zeros((nblocks, 3), dtype=np.float64))
        f.create_dataset("block size", data=np.full((nblocks, 3), 0.01, dtype=np.float64))


# ── 各维度文件定义 ────────────────────────────────────────────

def gen_1d(dir_path: Path, n_files: int = 5):
    """生成 1D 文件 lasslab_hdf5_chk_0001..000N (时间递增, 验证排序)。"""
    dir_path.mkdir(parents=True, exist_ok=True)
    xmin, xmax = -0.045, 0.045
    nx = 32
    for i in range(1, n_files + 1):
        path = dir_path / f"lasslab_hdf5_chk_{i:04d}"
        if path.exists():
            continue
        t = (i - 1) * 0.5e-10
        vars_data = _make_1d_vars(nx, nblocks=1)
        bbox = np.array([[[xmin, xmax], [0.0, 0.0], [0.0, 0.0]]], dtype=np.float64)
        write_flash_hdf5(path, vars_data, bbox, time=t, nstep=i * 100, dim=1)
        print(f"  [1D] {path.name}  t={t:.2e}s")


def gen_2d(dir_path: Path):
    """生成 2D 文件 (ny>1 使 y 坐标非退化)。

    FLASH 2D 激光模拟通常为柱坐标 R-Z: 数据布局 (nblocks, nz=1, ny, nx),
    theta 轴 (z) 范围 = 2π → coordinate_system 判定为 cylindrical_rz,
    该组合被 FlashHDF5File.extract_var_yt_style 与 yt 原生支持。

    文件名使用 lasslab_hdf5_plt_cnt_ 前缀: amr_visualization/d2 的
    对比测试按该前缀过滤; dimension_test 取目录内任意文件亦可加载。
    """
    dir_path.mkdir(parents=True, exist_ok=True)
    path = dir_path / "lasslab_hdf5_plt_cnt_0001"
    if path.exists():
        return
    nx, ny = 16, 8
    vars_data = _make_2d_vars(nx, ny, nblocks=1)
    # z (theta) 轴范围 2π → cylindrical_rz
    bbox = np.array([[[-0.045, 0.045], [-0.01, 0.01], [0.0, 2 * np.pi]]], dtype=np.float64)
    write_flash_hdf5(path, vars_data, bbox, time=0.5e-10, nstep=100, dim=2,
                     geometry="cylindrical")
    print(f"  [2D] {path.name}  (ny={ny}, nx={nx}, cylindrical R-Z)")


def gen_3d(dir_path: Path):
    """生成 3D 文件 (nz/ny/nx 均 >1)。

    文件名使用 lasslab_hdf5_plt_cnt_ 前缀: amr_visualization/d3 的
    对比测试按该前缀过滤; dimension_test 取目录内任意文件亦可加载。
    """
    dir_path.mkdir(parents=True, exist_ok=True)
    path = dir_path / "lasslab_hdf5_plt_cnt_0001"
    if path.exists():
        return
    nx, ny, nz = 4, 4, 4
    vars_data = _make_3d_vars(nx, ny, nz, nblocks=1)
    bbox = np.array([[[-0.045, 0.045], [-0.01, 0.01], [-0.02, 0.02]]], dtype=np.float64)
    write_flash_hdf5(path, vars_data, bbox, time=1.0e-10, nstep=200, dim=3)
    print(f"  [3D] {path.name}  (nz={nz}, ny={ny}, nx={nx})")


def ensure_test_data(force: bool = False) -> Path:
    """生成全部测试数据 (幂等)。返回 inputfiles 目录。"""
    d1 = _INPUTFILES / "hdf5files_1d"
    d2 = _INPUTFILES / "hdf5files_2d"
    d3 = _INPUTFILES / "hdf5files_3d"

    if force:
        for d in (d1, d2, d3):
            import shutil
            if d.exists():
                shutil.rmtree(d, ignore_errors=True)

    print(f"[gen_test_data] 输入目录: {_INPUTFILES}")
    if not d1.exists() or not any(d1.glob("lasslab_hdf5_chk_*")):
        gen_1d(d1)
    if not d2.exists() or not any(d2.glob("lasslab_hdf5_chk_*")):
        gen_2d(d2)
    if not d3.exists() or not any(d3.glob("lasslab_hdf5_chk_*")):
        gen_3d(d3)

    n1 = len(list(d1.glob("lasslab_hdf5_chk_*"))) if d1.exists() else 0
    n2 = len(list(d2.glob("lasslab_hdf5_chk_*"))) if d2.exists() else 0
    n3 = len(list(d3.glob("lasslab_hdf5_chk_*"))) if d3.exists() else 0
    print(f"[gen_test_data] 就绪: 1D={n1} 2D={n2} 3D={n3} 文件")
    return _INPUTFILES


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="生成 output_processors 合成测试数据")
    parser.add_argument("--force", action="store_true", help="强制重建全部数据")
    args = parser.parse_args()
    ensure_test_data(force=args.force)
    print("[done] 测试数据生成完成")
