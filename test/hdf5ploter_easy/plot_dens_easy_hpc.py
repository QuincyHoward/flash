#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FLASH HDF5 → CSV + 密度绘图 (纯 h5py, 无 yt 依赖)
═════════════════════════════════════════════════════

本地和超算双模式，确保两组 CSV 数据完全一致。

模式:
  --mode local        : 读取本地 HDF5 → dens_local.csv + dens_plot_local.png
  --mode hpc          : 读取超算 HDF5 → dens_hpc.csv + dens_plot_hpc.png
                        (需在超算上运行, 无需 yt/matplotlib)
  --mode orchestrate  : (默认) 编排全流程:
                        本地处理 → 上传 HDF5+脚本 → SSH 远程执行 →
                        下载结果 → 验证 CSV 一致性 → 展示所有产出

用法 (本地):
  python plot_dens_easy_hpc.py --mode local --hdf5 <path> --output <dir>

用法 (超算):
  python plot_dens_easy_hpc.py --mode hpc --hdf5 <path> --output <dir>

用法 (编排 - 从本地一键完成):
  python plot_dens_easy_hpc.py --mode orchestrate --hdf5 <path> --output <dir>
"""

import argparse
import csv
import hashlib
import os
import platform
import sys
from pathlib import Path

# 确保项目根目录在 sys.path 中 (兼容从子目录直接运行)

# Bootstrap: find flash project root by searching upward for marker
_ROOT = Path(__file__).resolve().parent
for _ in range(12):
    if (_ROOT / "pyproject.toml").exists():
        break
    _ROOT = _ROOT.parent
else:
    raise RuntimeError("Cannot locate flash package root")
_PARENT = _ROOT
if str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))


def hdf5_to_csv(hdf5_path: str, csv_path: str) -> dict:
    """读取 FLASH 1D HDF5 plot/checkpoint 文件, 提取 (x, dens) 写入 CSV。

    支持 FLASH 4.8 AMR 格式，自动处理多块拼接和 x 坐标重建。

    Args:
        hdf5_path: FLASH HDF5 文件路径
        csv_path:   输出的 CSV 路径

    Returns:
        {"x": [...], "dens": [...], "npoints": int, "nblocks": int,
         "dens_min": float, "dens_max": float, "x_min": float, "x_max": float}
    """
    import h5py
    import numpy as np
    import warnings
    # 兼容 HDF5 1.8 的 H5T_NATIVE_DOUBLE 等精度警告
    try:
        warnings.filterwarnings("ignore", category=h5py.h5w.DeprecationWarning)
    except AttributeError:
        pass  # 新版 h5py 无 h5w 模块, 无需兼容

    with h5py.File(hdf5_path, "r") as f:
        # --- 读取密度 ---
        raw = f["dens"][:]                     # (nblocks, Nz, Ny, Nx)
        # squeeze 去除长度为 1 的维度 (1D: Ny=Nz=1)
        dense = np.squeeze(raw)                # → (nblocks, Nx) 或 (Nx,) 或 (nblocks,)
        if dense.ndim == 1:
            # 单块: 重新 reshape
            dense = dense.reshape(1, -1)
        elif dense.ndim == 0:
            # 极端情况: 单块单格点
            dense = dense.reshape(1, 1)

        nblocks, nx = dense.shape

        # --- 读取边界框 ---
        bbox = f["bounding box"][:nblocks]      # (nblocks, 3, 2)
        # 对 1D: 即使模拟是 1D, FLASH 也返回 3D 边界框
        # x 方向: bbox[b, 0, 0] (min), bbox[b, 0, 1] (max)

        # --- 重建 x 坐标 ---
        x_list = []
        d_list = []
        for b in range(nblocks):
            x_min = float(bbox[b, 0, 0])
            x_max = float(bbox[b, 0, 1])
            xs = np.linspace(x_min, x_max, nx)
            x_list.append(xs)
            d_list.append(dense[b, :])

        x_all = np.concatenate(x_list)
        d_all = np.concatenate(d_list)

    # 按 x 排序（使用稳定的 mergesort 保证跨平台确定性）
    idx = np.argsort(x_all, kind="mergesort")
    x_sorted = x_all[idx]
    d_sorted = d_all[idx]

    # 合并重复 x 坐标处的密度值（取平均）
    # AMR 块边界处共享相同 x 值，不同块的密度可能有微小差异
    unique_x, inverse = np.unique(x_sorted, return_inverse=True)
    if len(unique_x) < len(x_sorted):
        d_unique = np.zeros_like(unique_x)
        np.add.at(d_unique, inverse, d_sorted)
        counts = np.bincount(inverse)
        d_unique /= counts
        x_out = unique_x.tolist()
        d_out = d_unique.tolist()
    else:
        x_out = x_sorted.tolist()
        d_out = d_sorted.tolist()

    # --- 写入 CSV ---
    os.makedirs(os.path.dirname(csv_path) or ".", exist_ok=True)
    with open(csv_path, "w", newline="") as fcsv:
        writer = csv.writer(fcsv)
        writer.writerow(["x_cm", "dens_g_per_cm3"])
        writer.writerows(zip(x_out, d_out))

    summary = {
        "x": x_out,
        "dens": d_out,
        "npoints": len(x_out),
        "nblocks": nblocks,
        "dens_min": float(min(d_out)),
        "dens_max": float(max(d_out)),
        "x_min": float(min(x_out)),
        "x_max": float(max(x_out)),
    }
    return summary


# ═══════════════════════════════════════════════════
# 核心函数: CSV → 密度图
# ═══════════════════════════════════════════════════

def csv_to_plot(csv_path: str, plot_path: str, title: str = None) -> str:
    """从 CSV 读取 (x, dens) 并生成密度分布图。

    使用纯 matplotlib，无 yt 依赖。

    Args:
        csv_path:  输入的 CSV 路径
        plot_path: 输出的图像路径
        title:     图的标题 (None 则自动生成)

    Returns:
        plot_path (便于链式调用)
    """
    import numpy as np

    # 读取 CSV
    x, d = [], []
    with open(csv_path, "r") as fcsv:
        reader = csv.reader(fcsv)
        header = next(reader)  # 跳过表头
        for row in reader:
            x.append(float(row[0]))
            d.append(float(row[1]))
    x = np.array(x)
    d = np.array(d)

    # --- 使用 Agg 后端 (兼容无显示器环境) ---
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    # ── PPT-friendly plot style (fonts >= 18, English only) ──
    try:
        from output_processors.plotter.plot_style import apply_plot_style
        apply_plot_style()
    except ImportError:
        pass

    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.plot(x, d, "b-", linewidth=1.5)
    ax.set_xlabel("x (cm)")
    ax.set_ylabel(r"density (g/cm$^3$)")
    ax.set_title(title or f"Density Profile (n={len(x)} points)")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    os.makedirs(os.path.dirname(plot_path) or ".", exist_ok=True)
    fig.savefig(plot_path, dpi=200)
    plt.close(fig)
    return plot_path


# ═══════════════════════════════════════════════════
# 辅助: CSV 文件校验
# ═══════════════════════════════════════════════════

def sha256_of_csv(csv_path: str) -> str:
    """计算 CSV 文件的 SHA256 (含表头, 确保完全一致)。"""
    sha = hashlib.sha256()
    with open(csv_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha.update(chunk)
    return sha.hexdigest()


def csvs_are_identical(path_a: str, path_b: str, rtol: float = 1e-12,
                       atol: float = 1e-15) -> tuple:
    """对比两个 CSV 的数值数据, 确认科学与一致性。

    由于 Windows/Linux 浮点数格式化存在微小差异 (~1e-13),
    使用 np.allclose 进行数值比较而非 SHA256。

    Args:
        path_a: CSV 文件 A
        path_b: CSV 文件 B
        rtol:   相对容差
        atol:   绝对容差

    Returns:
        (is_ok: bool, detail: str)
    """
    import numpy as np

    if not os.path.exists(path_a) or not os.path.exists(path_b):
        return False, "文件不存在"

    def load_csv(path):
        x, d = [], []
        with open(path, "r") as f:
            reader = csv.reader(f)
            next(reader)  # 跳过表头
            for row in reader:
                x.append(float(row[0]))
                d.append(float(row[1]))
        return np.array(x), np.array(d)

    xa, da = load_csv(path_a)
    xb, db = load_csv(path_b)

    if len(xa) != len(xb):
        return False, f"行数不一致: {len(xa)} vs {len(xb)}"

    # 检查 x 坐标
    if not np.allclose(xa, xb, rtol=rtol, atol=atol):
        max_xdiff = np.max(np.abs(xa - xb))
        return False, f"x 坐标差异过大, max|diff|={max_xdiff:.2e}"

    # 检查密度值
    if not np.allclose(da, db, rtol=rtol, atol=atol):
        max_ddiff = np.max(np.abs(da - db))
        max_drel = np.max(np.abs(da - db) / np.maximum(np.abs(da), 1e-30))
        return False, (f"密度数值差异, max|diff|={max_ddiff:.2e}, "
                       f"max|rel|={max_drel:.2e}")

    max_abs_diff = float(np.max(np.abs(da - db)))
    max_rel_diff = float(np.max(np.abs(da - db) / np.maximum(np.abs(da), 1e-30)))
    return True, (f"数值一致 ✓ (max|diff|={max_abs_diff:.2e}, "
                  f"max|rel|={max_rel_diff:.2e})")


# ═══════════════════════════════════════════════════
# HPC 远程操作
# ═══════════════════════════════════════════════════

def orchestrate(hdf5_path: str, output_dir: str,
                remote_hdf5_dir: str = None,
                credential_name: str = None):
    """编排全流程: 本地→上传→远程执行→下载→验证。

    Args:
        hdf5_path:       本地 HDF5 文件路径 (同时也是需要上传到超算的文件)
        output_dir:      本地输出目录 (所有产出汇集处)
        remote_hdf5_dir: 超算目标目录 (HDF5 文件存放位置)
        credential_name:  超算凭据名 (默认 None = flash_ssh)
    """
    from flash.scenarios.flash_demo.demo_hpc.remote_ssh_helper import RemoteSession

    output_dir = os.path.abspath(output_dir)
    os.makedirs(output_dir, exist_ok=True)

    hdf5_abs = os.path.abspath(hdf5_path)
    hdf5_name = os.path.basename(hdf5_abs)

    # 1 ── 本地处理 ────────────────────────────────
    print("=" * 58)
    print("  [Phase 1/5] 本地处理: HDF5 → CSV + 绘图")
    print("=" * 58)

    csv_local = os.path.join(output_dir, "dens_local.csv")
    plot_local = os.path.join(output_dir, "dens_plot_local.png")

    s_local = hdf5_to_csv(hdf5_abs, csv_local)
    print(f"  ✓ dens_local.csv  →  {csv_local}")
    print(f"    nblocks={s_local['nblocks']}, npoints={s_local['npoints']}")
    print(f"    dens range: {s_local['dens_min']:.4e} ~ {s_local['dens_max']:.4e} g/cm³")
    print(f"    x   range: {s_local['x_min']:.4e} ~ {s_local['x_max']:.4e} cm")

    csv_to_plot(csv_local, plot_local,
                title="Density Profile (Local) — lasslab_hdf5_plt_cnt_0066")
    print(f"  ✓ dens_plot_local.png  →  {plot_local}")

    # 2 ── 上传到超算 ──────────────────────────────
    print("\n" + "=" * 58)
    print("  [Phase 2/5] SCP 上传到超算")
    print("=" * 58)

    if remote_hdf5_dir is None:
        remote_hdf5_dir = f"~/AI/AItemp/hdf5ploter_easy/"
    remote_hdf5_path = posix_path_join(remote_hdf5_dir, hdf5_name)
    remote_script_path = posix_path_join(remote_hdf5_dir, "plot_dens_easy_hpc.py")

    with RemoteSession(credential_name=credential_name) as sess:
        # 创建远程目录
        sess.run(f"mkdir -p {remote_hdf5_dir}", timeout=15)

        # 上传 HDF5 文件
        print(f"  Uploading {hdf5_name} ({os.path.getsize(hdf5_abs)} bytes)...")
        ok = sess.upload(hdf5_abs, remote_hdf5_path)
        if not ok:
            raise RuntimeError(f"上传 {hdf5_name} 失败!")
        print(f"  ✓  {hdf5_name} → {remote_hdf5_path}")

        # 上传脚本本身 (self-upload)
        this_script = os.path.abspath(__file__)
        print(f"  Uploading script ({os.path.getsize(this_script)} bytes)...")
        ok = sess.upload(this_script, remote_script_path)
        if not ok:
            raise RuntimeError("上传脚本失败!")
        print(f"  ✓  plot_dens_easy_hpc.py → {remote_script_path}")

    # 3 ── 远程执行 ────────────────────────────────
    print("\n" + "=" * 58)
    print("  [Phase 3/5] SSH 远程执行 (超算端转换+绘图)")
    print("=" * 58)

    remote_output_dir = posix_path_join(remote_hdf5_dir, "output")
    remote_csv = posix_path_join(remote_output_dir, "dens_hpc.csv")
    remote_plot = posix_path_join(remote_output_dir, "dens_plot_hpc.png")

    # 远程命令: 先 module load python → 运行脚本
    cmd = (
        f"cd {remote_hdf5_dir} && "
        f"module load python/3.9.6 && "
        f"python plot_dens_easy_hpc.py --mode hpc "
        f"--hdf5 {remote_hdf5_path} "
        f"--output {remote_output_dir}"
    )

    with RemoteSession(credential_name=credential_name) as sess:
        print(f"  Running remote command (may take a while)...")
        out, err, code = sess.run(cmd, timeout=180)

        # 打印输出 (截取有用部分)
        for line in out.splitlines():
            print(f"  [STDOUT] {line}")
        if err:
            for line in err.splitlines()[:10]:
                print(f"  [STDERR] {line}")
        if code != 0:
            # 远程执行失败也可能是 matplotlib 缺失
            print(f"\n  ⚠ 远程执行返回码 {code}, 尝试备用方案 (pip install matplotlib)...")
            retry_cmd = (
                f"cd {remote_hdf5_dir} && "
                f"module load python/3.9.6 && "
                f"pip install matplotlib --quiet --user && "
                f"python plot_dens_easy_hpc.py --mode hpc "
                f"--hdf5 {remote_hdf5_path} "
                f"--output {remote_output_dir}"
            )
            out2, err2, code2 = sess.run(retry_cmd, timeout=300)
            for line in out2.splitlines():
                print(f"  [STDOUT] {line}")
            if err2:
                for line in err2.splitlines()[:10]:
                    print(f"  [STDERR] {line}")
            if code2 != 0:
                raise RuntimeError(
                    f"远程执行失败! 返回码={code2}\n"
                    f"请手动登录超算检查:\n"
                    f"  cd {remote_hdf5_dir} && module load python/3.9.6 && "
                    f"python plot_dens_easy_hpc.py --mode hpc "
                    f"--hdf5 {remote_hdf5_path} --output {remote_output_dir}"
                )

        print(f"  ✓ 超算端处理完成")

    # 4 ── 下载结果 ────────────────────────────────
    print("\n" + "=" * 58)
    print("  [Phase 4/5] SCP 下载结果")
    print("=" * 58)

    csv_hpc_local = os.path.join(output_dir, "dens_hpc.csv")
    plot_hpc_local = os.path.join(output_dir, "dens_plot_hpc.png")

    with RemoteSession(credential_name=credential_name) as sess:
        for rpath, lpath in [(remote_csv, csv_hpc_local),
                              (remote_plot, plot_hpc_local)]:
            ok = sess.download(rpath, lpath)
            if ok:
                print(f"  ✓  {os.path.basename(rpath)} → {lpath}")
            else:
                print(f"  ⚠  {rpath} 下载失败 (可能是超算端绘图未生成)")

    # 5 ── 验证 ────────────────────────────────────
    print("\n" + "=" * 58)
    print("  [Phase 5/5] 验证 CSV 一致性")
    print("=" * 58)

    if os.path.exists(csv_hpc_local):
        is_ok, detail = csvs_are_identical(csv_local, csv_hpc_local)
        if is_ok:
            print(f"  ✓  {detail}")
        else:
            print(f"  ⚠  数据不一致: {detail}")
            print(f"    dens_local.csv (SHA256) : {sha256_of_csv(csv_local)}")
            print(f"    dens_hpc.csv   (SHA256) : {sha256_of_csv(csv_hpc_local)}")
    else:
        print(f"  ⚠ dens_hpc.csv 未下载, 跳过校验")

    # 展示产出
    print("\n" + "=" * 58)
    print("  ✅ 全流程完成! 产出文件:")
    print("=" * 58)
    files = [csv_local, plot_local]
    if os.path.exists(csv_hpc_local):
        files.append(csv_hpc_local)
    if os.path.exists(plot_hpc_local):
        files.append(plot_hpc_local)
    for f in files:
        size = os.path.getsize(f)
        print(f"    {f}  ({size:,} bytes)")
    print()

    return files


def posix_path_join(a: str, b: str) -> str:
    """用 / 拼接远程路径 (Linux 超算)。"""
    a = a.rstrip("/")
    return f"{a}/{b}"


# ═══════════════════════════════════════════════════
# 超算端入口 (--mode hpc)
# ═══════════════════════════════════════════════════

def run_on_hpc(hdf5_path: str, output_dir: str):
    """在超算上运行: HDF5 → CSV + 密度图。

    超算环境通常无 yt, 但可能有 h5py + numpy + matplotlib (需 Agg 后端)。
    如果 matplotlib 不可用, 至少生成 CSV 供本地绘图。
    """
    print(f"[HPC] 超算端处理开始")
    print(f"  HDF5:  {hdf5_path}")
    print(f"  Output: {output_dir}")
    os.makedirs(output_dir, exist_ok=True)

    # 1. HDF5 → CSV
    csv_path = os.path.join(output_dir, "dens_hpc.csv")
    try:
        summary = hdf5_to_csv(hdf5_path, csv_path)
        print(f"[HPC] ✓ dens_hpc.csv 生成: {csv_path}")
        print(f"  nblocks={summary['nblocks']}, npoints={summary['npoints']}")
        print(f"  dens range: {summary['dens_min']:.4e} ~ {summary['dens_max']:.4e} g/cm³")
    except Exception as e:
        print(f"[HPC] ✗ CSV 生成失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 2. CSV → 密度图
    plot_path = os.path.join(output_dir, "dens_plot_hpc.png")
    try:
        csv_to_plot(csv_path, plot_path,
                    title="Density Profile (HPC)")
        print(f"[HPC] ✓ dens_plot_hpc.png 生成: {plot_path}")
    except ImportError as e:
        print(f"[HPC] ⚠ matplotlib 不可用, 跳过绘图 ({e})")
        print("[HPC] CSV 已生成, 可在本地 python csv_to_plot(...)")
    except Exception as e:
        print(f"[HPC] ✗ 绘图失败: {e}")
        import traceback
        traceback.print_exc()
        # 绘图失败不阻断, CSV 已经生成
        print("[HPC] CSV 已生成, 绘图失败不影响 CSV")

    return True


# ═══════════════════════════════════════════════════
# 本地入口 (--mode local)
# ═══════════════════════════════════════════════════

def run_local(hdf5_path: str, output_dir: str):
    """本地运行: HDF5 → CSV + 密度图。"""
    print(f"[LOCAL] 本地处理开始")
    print(f"  HDF5:  {hdf5_path}")
    print(f"  Output: {output_dir}")
    os.makedirs(output_dir, exist_ok=True)

    # HDF5 → CSV
    csv_path = os.path.join(output_dir, "dens_local.csv")
    summary = hdf5_to_csv(hdf5_path, csv_path)
    print(f"[LOCAL] ✓ dens_local.csv 生成: {csv_path}")
    print(f"  nblocks={summary['nblocks']}, npoints={summary['npoints']}")
    print(f"  dens range: {summary['dens_min']:.4e} ~ {summary['dens_max']:.4e} g/cm³")

    # CSV → 密度图
    plot_path = os.path.join(output_dir, "dens_plot_local.png")
    csv_to_plot(csv_path, plot_path,
                title="Density Profile (Local) — DEHPC")
    print(f"[LOCAL] ✓ dens_plot_local.png 生成: {plot_path}")

    return [csv_path, plot_path]


# ═══════════════════════════════════════════════════
# 主入口
# ═══════════════════════════════════════════════════

def main():
    # 高精度解析, 兼容 argparse
    raw_args = sys.argv[1:]

    parser = argparse.ArgumentParser(
        description="FLASH HDF5 → CSV + 密度绘图 (纯 h5py, 无 yt 依赖)",
    )
    parser.add_argument("--mode", default="orchestrate",
                        choices=["local", "hpc", "orchestrate"],
                        help="运行模式 (默认: orchestrate)")
    parser.add_argument("--hdf5", type=str, default=None,
                        help="FLASH HDF5 文件路径")
    parser.add_argument("--output", type=str, default=None,
                        help="输出目录")
    parser.add_argument("--remote-dir", type=str, default=None,
                        help="超算目标目录 (仅 orchestrate 模式)")
    parser.add_argument("--credential", type=str, default=None,
                        help="超算凭据名 (默认 flash_ssh)")

    args = parser.parse_args(raw_args)

    mode = args.mode

    # ── 默认路径 ──
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if args.hdf5 is None:
        args.hdf5 = os.path.join(script_dir, "lasslab_hdf5_plt_cnt_0066")
    if args.output is None:
        args.output = os.path.join(script_dir, "output", "hpc_comparison")

    hdf5_path = os.path.abspath(args.hdf5)
    output_dir = os.path.abspath(args.output)

    # 检查 HDF5 文件存在
    if not os.path.exists(hdf5_path):
        print(f"[ERROR] HDF5 文件不存在: {hdf5_path}")
        sys.exit(1)

    # 检查 h5py 依赖
    try:
        import h5py
    except ImportError:
        print("[ERROR] 需要 h5py 库: pip install h5py")
        sys.exit(1)

    # ── 路由模式 ──
    if mode == "local":
        run_local(hdf5_path, output_dir)
    elif mode == "hpc":
        run_on_hpc(hdf5_path, output_dir)
    elif mode == "orchestrate":
        orchestrate(
            hdf5_path=hdf5_path,
            output_dir=output_dir,
            remote_hdf5_dir=args.remote_dir,
            credential_name=args.credential,
        )


if __name__ == "__main__":
    main()
