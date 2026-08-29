# -*- coding: utf-8 -*-
"""快速验证: chk_0000 (t=0) 初始帧物质标记是否严格落在设计位置。

设计正确性的判据是初始帧 (静态 0/1 阶跃), 而非末帧 —
末帧偏差是激光驱动下标记随流输运的物理结果, 不是设计错误。
"""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
for _ in range(14):
    if (_ROOT / "pyproject.toml").exists():
        break
    _ROOT = _ROOT.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import numpy as np
from flash.output_processors.loader import FlashDataLoader

CHK = (r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\scenarios\private"
       r"\tracer\layer_tracer_CH_ml\flash_output\outputfiles\run_000001\lasslab_hdf5_chk_0000")

# 设计位置 (um): (层内区间, 物种)
EXPECT = {
    "shld": (0.0, 0.1),
    "tar1": (1.0, 1.1),
    "tar2": (2.0, 2.1),
    "tar3": (3.0, 3.1),
    "tar4": (4.0, 4.1),
    "tar6": (6.0, 6.1),
}

dl = FlashDataLoader(CHK)
data = dl.load(compute_derived=False, extraction_mode="yt")

x = np.asarray(data.x).ravel() * 1e4  # cm -> um
n_pass = 0
print(f"{'species':<8}{'in-mean':>12}{'out-max':>12}{'result':>10}")
for sp, (lo, hi) in EXPECT.items():
    y = np.asarray(data.data[sp]).ravel()
    m_in = (x >= lo + 0.02) & (x <= hi - 0.02)
    m_out = ~((x >= lo) & (x <= hi))
    # 排除域外其他材料区(如 shld)自身 — 只要求标记互不泄漏:
    # 层内均值≈1, 层外最大值≈0 (对标记物种而言)
    in_mean = float(y[m_in].mean()) if m_in.any() else float("nan")
    out_max = float(y[m_out].max()) if m_out.any() else float("nan")
    ok = in_mean > 0.99 and out_max < 1e-3
    n_pass += ok
    print(f"{sp:<8}{in_mean:>12.6f}{out_max:>12.3e}{'>PASS' if ok else '>FAIL':>10}")

print(f"\n{list(EXPECT)[n_pass] if n_pass < len(EXPECT) else 'ALL'}: {n_pass}/{len(EXPECT)} PASS")
sys.exit(0 if n_pass == len(EXPECT) else 2)
