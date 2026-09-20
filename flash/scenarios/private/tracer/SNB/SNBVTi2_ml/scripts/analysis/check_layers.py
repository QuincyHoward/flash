# -*- coding: utf-8 -*-
"""check_layers.py — 示踪层位核查（可复用，跨场景）。

★★ 为什么要有这个脚本（三次手工重推后的固化, 2026-09-15）
=========================================================
SNBVTi 族场景的层位核查曾三次在会话中手工重推, 且每次都踩同一类坑。
本脚本把**已验证的方法论**固化为一条命令, 方法论要点（缺一即错）:

1. **坐标必须用 `bounding box` + `nxb` 逐块重建**, 严禁用 `coordinates`
   数据集（它是每块上边缘的扁平 131 点, 且块序与物理序不同 →
   会得到数万 µm 的荒谬偏差）:
       x_center(b, j) = bb[b,0,0] + (j+0.5)·(bb[b,0,1]-bb[b,0,0])/nxb
2. **物种"空"值是地板值 1e-99 而非 0** —— 用 `d > 0` 判命中会让全部
   块命中; 必须用质量分数阈值 `d > 0.5`。
3. **层位核验必须用初始帧 chk_0000** —— 示踪层是 Lagrangian 标记,
   流动发展后随稀疏流平流/稀释（实测 t≥1.0 ns 全层跌破 0.5）,
   用末帧核查会误判"层位全缺席"。
4. 物种数据集是 chk 根级**裸名**（shld/tar1/...）, 无前缀后缀。

用法:
  python check_layers.py --dir <flash_output_dir> [--file <某个chk>]
      [--expect-cells 5] [--species shld,tar1,tar2,tar3,tar4,tar6]
      [--baseline-json baseline.json]

判定:
  (a) 每层命中格数 n_cells（--expect-cells 给出时要求精确相等, 否则仅报告）;
  (b) 每层内质量分数纯度（min fraction, 精确划分应 = 1.0）;
  (c) 6 层 ×2 端点的"所需刚性平移量" mean/std —— std ≪ dx 说明各层
      标距逐层一致（层位无相对畸变）; mean 即 +ug 固有域位移, 仅报告。
退出码: 0 = 全部断言通过; 1 = 失败。
"""
from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path

import h5py
import numpy as np

DEFAULT_SPECIES = ("shld", "tar1", "tar2", "tar3", "tar4", "tar6")
# SNBVTi2_ml 短测基线 (µm) —— 仅供平移量参考; 不同场景平移量可不同
DEFAULT_BASELINE = {
    "shld": (1.920, 1.979), "tar1": (2.933, 2.993), "tar2": (3.917, 4.007),
    "tar3": (4.931, 4.991), "tar4": (5.915, 6.005), "tar6": (7.913, 8.003),
}
FRAC_THR = 0.5          # 质量分数命中阈值（铁律 #2, 勿改回 >0）
UM_PER_CM = 1e4


def pick_chk(path: Path) -> Path:
    """选 chk: 显式 --file 优先; 否则 dir 下编号最小的 chk_0000（铁律 #3）。"""
    if path.is_file():
        return path
    if path.is_dir():
        chks = sorted(glob.glob(str(path / "*hdf5_chk_*")))
        if chks:
            return Path(chks[0])
    raise SystemExit(f"[X] 找不到 chk: {path}")


def layer_extent(h: h5py.File, sp: str, nxb: int):
    """返回 (x_lo_um, x_hi_um, n_cells, frac_min, blocks) 或 None（未命中）。"""
    if sp not in h:
        return None
    bb = h["bounding box"][:]
    d = h[sp][:]
    flat = d.reshape(d.shape[0], -1)
    hits = np.where((flat > FRAC_THR).any(axis=1))[0]
    if hits.size == 0:
        return None
    xs, fr = [], []
    for b in hits:
        x0, x1 = bb[b, 0, 0], bb[b, 0, 1]
        xc = x0 + (np.arange(nxb) + 0.5) * (x1 - x0) / nxb
        row = flat[b]
        m = row > FRAC_THR
        xs.append(xc[m])
        fr.append(row[m])
    xs = np.concatenate(xs) * UM_PER_CM
    fr = np.concatenate(fr)
    return float(xs.min()), float(xs.max()), int(xs.size), float(fr.min()), \
        [int(b) for b in hits]


def main() -> int:
    ap = argparse.ArgumentParser(description="示踪层位核查（bounding box 块法）")
    ap.add_argument("--dir", default=None, help="flash_output 目录（自动取 chk_0000）")
    ap.add_argument("--file", default=None, help="直接指定 chk 路径")
    ap.add_argument("--expect-cells", type=int, default=None,
                    help="每层期望精确格数（如 5）; 给出则强校验")
    ap.add_argument("--species", default=",".join(DEFAULT_SPECIES))
    ap.add_argument("--baseline-json", default=None,
                    help="自定义基线 JSON {layer:[lo_um,hi_um], ...}")
    args = ap.parse_args()

    target = Path(args.file) if args.file else Path(args.dir or ".")
    chk = pick_chk(target)
    species = tuple(s.strip() for s in args.species.split(",") if s.strip())
    baseline = DEFAULT_BASELINE
    if args.baseline_json:
        baseline = {k: tuple(v) for k, v in
                    json.loads(Path(args.baseline_json).read_text()).items()}

    ok = True
    shifts = []
    print(f"chk = {chk.name}")
    with h5py.File(chk, "r") as h:
        # nxb 从数据集末维取（物种/dens 数组形状 = (nblocks,1,1,nxb)）最稳
        nxb = h[species[0] if species[0] in h else "dens"].shape[-1]
        bb = h["bounding box"][:]
        dx_um = (bb[0, 0, 1] - bb[0, 0, 0]) * UM_PER_CM / nxb
        rs_n = [x.decode().strip() for x in h["real scalars"]["name"]]
        t_cm = float(h["real scalars"]["value"][rs_n.index("time")])
        print(f"t = {t_cm*1e9:.6g} ns   nxb = {nxb}   leaf dx = {dx_um:.6f} um")
        if abs(dx_um - 0.02) < 1e-9:
            print("  [OK] dx == 0.02 um（精确网格）")
        print(f"{'layer':6s} {'blocks':>10s} {'n_cells':>7s} {'x_lo(um)':>10s} "
              f"{'x_hi(um)':>10s} {'shift_lo':>9s} {'shift_hi':>9s} {'frac_min':>8s}")
        for sp in species:
            ext = layer_extent(h, sp, nxb)
            if ext is None:
                print(f"{sp:6s} {'--absent--':>10s}  ← 层未命中（阈值 {FRAC_THR}）")
                if args.expect_cells is not None:
                    ok = False
                continue
            lo, hi, ncell, fmin, blocks = ext
            blo, bhi = baseline.get(sp, (float("nan"), float("nan")))
            s_lo, s_hi = lo - blo, hi - bhi
            shifts += [s_lo, s_hi]
            print(f"{sp:6s} {str(blocks):>10s} {ncell:7d} {lo:10.4f} {hi:10.4f} "
                  f"{s_lo:9.4f} {s_hi:9.4f} {fmin:8.4f}")
            if args.expect_cells is not None and ncell != args.expect_cells:
                print(f"        [X] 期望 {args.expect_cells} 格, 实际 {ncell} 格")
                ok = False
            if fmin < 0.999:
                print(f"        [!] 层内质量分数最低 {fmin:.4f} < 0.999 "
                      f"（层边界未与网格边对齐?）")
                if args.expect_cells is not None:
                    ok = False
    if shifts:
        s = np.array(shifts)
        print(f"\n刚性平移: mean = {s.mean():+.4f} um   std = {s.std():.4f} um   "
              f"(N={s.size})")
        print("  → std ≪ dx ⇒ 各层标距逐层一致（无相对畸变）; mean 为 +ug 固有域位移")
    print("\n结论:", "✓ 层位核查通过" if ok else "✗ 层位核查失败")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
