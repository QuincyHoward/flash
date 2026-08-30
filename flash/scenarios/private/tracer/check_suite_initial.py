"""初始帧 (chk_0000) 设计正确性快检 — OneCH_ml vs VCH_ml 对比。

判据 (t=0 初始帧):
  1. shld 层 [0, 0.1um] 密度: OneCH≈1.0 (CH), VCH≈6.11 (V)
  2. 8 物种 0/1 阶跃: 每个标记层内均值≈1、层外最大≈0
退出码: 0=PASS, 2=FAIL
"""
import sys
from pathlib import Path

import numpy as np

REPO = Path(r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash")
sys.path.insert(0, str(REPO))
from flash.output_processors.loader import FlashDataLoader  # noqa: E402

TRACER = REPO / "flash" / "scenarios" / "private" / "tracer"
# 设计标记层位置 (um): (lo, hi)
EXPECT = {
    "shld": (0.0, 0.1), "tar1": (1.0, 1.1), "tar2": (2.0, 2.1),
    "tar3": (3.0, 3.1), "tar4": (4.0, 4.1), "tar6": (6.0, 6.1),
}
# shld 层设计密度 (g/cm3)
RHO_SHLD = {"OneCH_ml": 1.0, "VCH_ml": 6.11}

ok_all = True
for name in ("OneCH_ml", "VCH_ml"):
    chk = sorted((TRACER / name / "flash_output" / "outputfiles" / "run_000001").glob("*hdf5_chk_0000"))
    print(f"\n===== {name}: {chk[0].name} =====")
    c = FlashDataLoader(chk[0]).load(compute_derived=False, extraction_mode="yt")
    x = np.asarray(c.x) * 1e4  # cm -> um
    dens = np.asarray(c.data["dens"])

    # 1) shld 层密度
    m = (x >= EXPECT["shld"][0]) & (x <= EXPECT["shld"][1])
    rho_in = float(np.mean(dens[m]))
    target = RHO_SHLD[name]
    ok_rho = abs(rho_in - target) / target < 1e-3
    ok_all &= ok_rho
    print(f"  shld 密度: {rho_in:.4f} (设计 {target})  {'PASS' if ok_rho else 'FAIL'}")

    # samp 基体密度抽查 [0.2, 0.9um]
    m_s = (x >= 0.2) & (x <= 0.9)
    rho_s = float(np.mean(dens[m_s]))
    ok_s = abs(rho_s - 1.0) < 1e-3
    ok_all &= ok_s
    print(f"  samp 密度: {rho_s:.4f} (设计 1.0)  {'PASS' if ok_s else 'FAIL'}")

    # 2) 物种 0/1 阶跃
    for sp, (lo, hi) in EXPECT.items():
        y = np.asarray(c.data[sp])
        mi = (x >= lo) & (x <= hi)
        mo = ~mi
        v_in, v_out = float(np.mean(y[mi])), float(np.max(y[mo]))
        ok = abs(v_in - 1.0) < 1e-3 and v_out < 1e-3
        ok_all &= ok
        print(f"  {sp:<6} in-mean={v_in:.6f}  out-max={v_out:.2e}  "
              f"{'PASS' if ok else 'FAIL'}")

print(f"\n===== 总判定: {'PASS (6/6 物种 + 密度)' if ok_all else 'FAIL'} =====")
sys.exit(0 if ok_all else 2)
