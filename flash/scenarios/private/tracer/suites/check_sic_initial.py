"""初始帧 (chk_0000) 设计正确性快检 — OneSi_ml / OneC_ml 家族 4 场景。

单一纯材料烧蚀场景: shld/tar1/2/3/4/6/samp 全部为同一种材料
(Si 2.329 或 C 金刚石 3.515 g/cm^3 常温固体密度), 无 Ti 示踪层, cham 为 He 填充 (Z02 6 群表)。

判据 (t=0 初始帧, 每个场景):
  1. 各标记层 (shld/tar*) 内 dens ≈ 1.00 g/cm^3
  2. samp 基体抽查 [0.2, 0.9 um] dens ≈ 1.00
  3. 6 个标记物种 0/1 阶跃: 层内均值≈1、层外最大≈0
每个场景独占输出目录, 直接取最新 run。
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
# 常温固体密度 (g/cm^3): Si=2.329, C=金刚石 3.515
RHO_SOLID = {
    "OneSi_ml": 2.329, "OneSi_ml_F": 2.329,
    "OneC_ml": 3.515, "OneC_ml_F": 3.515,
}

# 每场景独占目录, 取最新 run
SCENARIOS = ["OneSi_ml", "OneSi_ml_F", "OneC_ml", "OneC_ml_F"]

ok_all = True
for name in SCENARIOS:
    rho_solid = RHO_SOLID[name]
    runs_root = TRACER / name / "flash_output" / "outputfiles"
    run_dirs = sorted(runs_root.glob("run_*"), reverse=True)
    chk = None
    for rd in run_dirs:
        c0 = sorted(rd.glob("*hdf5_chk_0000"))
        if c0:
            chk = (rd.name, c0[0])
            break
    if chk is None:
        print(f"\n===== {name}: 无 chk_0000 — FAIL")
        ok_all = False
        continue
    run_id, chk_path = chk
    print(f"\n===== {name} ({run_id}) =====")
    c = FlashDataLoader(chk_path).load(compute_derived=False,
                                       extraction_mode="yt")
    x = np.asarray(c.x) * 1e4  # cm -> um
    dens = np.asarray(c.data["dens"])

    # 1) 各标记层密度
    for sp, (lo, hi) in EXPECT.items():
        m = (x >= lo) & (x <= hi)
        rho_in = float(np.mean(dens[m]))
        ok = abs(rho_in - rho_solid) / rho_solid < 1e-3
        ok_all &= ok
        print(f"  {sp:<6} dens={rho_in:.4f} (设计 {rho_solid})  "
              f"{'PASS' if ok else 'FAIL'}")

    # 2) samp 基体抽查
    m_s = (x >= 0.2) & (x <= 0.9)
    rho_s = float(np.mean(dens[m_s]))
    ok_s = abs(rho_s - rho_solid) / rho_solid < 1e-3
    ok_all &= ok_s
    print(f"  samp   dens={rho_s:.4f} (设计 {rho_solid})  "
          f"{'PASS' if ok_s else 'FAIL'}")

    # 3) 物种 0/1 阶跃
    for sp, (lo, hi) in EXPECT.items():
        y = np.asarray(c.data[sp])
        mi = (x >= lo) & (x <= hi)
        mo = ~mi
        v_in, v_out = float(np.mean(y[mi])), float(np.max(y[mo]))
        ok = abs(v_in - 1.0) < 1e-3 and v_out < 1e-3
        ok_all &= ok
        print(f"  {sp:<6} in-mean={v_in:.6f}  out-max={v_out:.2e}  "
              f"{'PASS' if ok else 'FAIL'}")

n = len(SCENARIOS)
print(f"\n===== 总判定: {'PASS' if ok_all else 'FAIL'} ({n} 场景) =====")
sys.exit(0 if ok_all else 2)
