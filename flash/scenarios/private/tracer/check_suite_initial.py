"""初始帧 (chk_0000) 设计正确性快检 — tracer 全家族 12 场景。

判据 (t=0 初始帧, 每个场景):
  1. shld 层 [0, 0.1um] 密度: CH 系≈1.0 (OneCH/CHTi*), V 系≈6.11
     (VCH/VCH_ml_F), Ti 系≈4.54 (TiTi*)
  2. Ti 示踪层: TI_SP 指定标记层内 dens≈4.54 g/cm^3 (其余 tar* 层≈1.0)
  3. samp 基体抽查 [0.2, 0.9um] dens≈1.0
  4. 8 物种 0/1 阶跃: 每个标记层内均值≈1、层外最大≈0
退出码: 0=PASS, 2=FAIL
用法: python check_suite_initial.py [场景名 ...]   # 不带参数 = 全部场景
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
RHO_TI = 4.54

# 场景 → (输出目录, shld 设计密度, Ti 层物种或 None)
# 注: CHTi1/2/3 共享 CHTi/ 目录, CHTi*_F 共享 CHTi_F/ 目录, TiTi1/2/3 共享
#     TiTi/ 目录 — run 归属不可凭目录名/编号推断, 需按剖面自证: 从最新 run
#     向旧扫描, 取 Ti 判据全满足的第一个 run (同时校验其余 tar 层 dens≈1.0,
#     杜绝串味误配)。
SCENARIOS = {
    "OneCH_ml":  ("OneCH_ml",  1.0,  None),
    "VCH_ml":    ("VCH_ml",    6.11, None),
    "CHTi1":     ("CHTi",      1.0,  "tar1"),
    "CHTi2":     ("CHTi",      1.0,  "tar2"),
    "CHTi3":     ("CHTi",      1.0,  "tar3"),
    "VCH_ml_F":  ("VCH_ml_F",  6.11, None),
    "CHTi1_F":   ("CHTi_F",    1.0,  "tar1"),
    "CHTi2_F":   ("CHTi_F",    1.0,  "tar2"),
    "CHTi3_F":   ("CHTi_F",    1.0,  "tar3"),
    "TiTi1":     ("TiTi",      4.54, "tar1"),
    "TiTi2":     ("TiTi",      4.54, "tar2"),
    "TiTi3":     ("TiTi",      4.54, "tar3"),
}
ALL_TAR = ["tar1", "tar2", "tar3"]

# 可选过滤: 命令行位置参数 = 只检查这些场景 (如 TiTi1 TiTi2 TiTi3)
_ONLY = {a for a in sys.argv[1:] if not a.startswith("-")} or None

ok_all = True
n_checked = 0
for name, (dirname, rho_shld, ti_sp) in SCENARIOS.items():
    if _ONLY and name not in _ONLY:
        continue
    n_checked += 1
    runs_root = TRACER / dirname / "flash_output" / "outputfiles"
    run_dirs = sorted(runs_root.glob("run_*"), reverse=True)
    matched = None
    for rd in run_dirs:
        chk = sorted(rd.glob("*hdf5_chk_0000"))
        if not chk:
            continue
        c = FlashDataLoader(chk[0]).load(compute_derived=False,
                                         extraction_mode="yt")
        x = np.asarray(c.x) * 1e4  # cm -> um
        dens = np.asarray(c.data["dens"])
        # Ti 归属自证: 目标层≈4.54 且其余 tar 层≈1.0
        if ti_sp is not None:
            def rho_at(sp):
                lo, hi = EXPECT[sp]
                m = (x >= lo) & (x <= hi)
                return float(np.mean(dens[m]))
            ok_self = (abs(rho_at(ti_sp) - RHO_TI) / RHO_TI < 1e-3 and all(
                abs(rho_at(o) - 1.0) < 1e-3
                for o in ALL_TAR if o != ti_sp))
            if not ok_self:
                continue
        matched = (rd.name, c, x, dens)
        break
    if matched is None:
        print(f"\n===== {name}: 无匹配 run — FAIL")
        ok_all = False
        continue
    run_id, c, x, dens = matched
    print(f"\n===== {name} ({run_id}, 剖面自证匹配) =====")

    # 1) shld 层密度
    m = (x >= EXPECT["shld"][0]) & (x <= EXPECT["shld"][1])
    rho_in = float(np.mean(dens[m]))
    ok_rho = abs(rho_in - rho_shld) / rho_shld < 1e-3
    ok_all &= ok_rho
    print(f"  shld 密度: {rho_in:.4f} (设计 {rho_shld})  {'PASS' if ok_rho else 'FAIL'}")

    # samp 基体密度抽查 [0.2, 0.9um]
    m_s = (x >= 0.2) & (x <= 0.9)
    rho_s = float(np.mean(dens[m_s]))
    ok_s = abs(rho_s - 1.0) < 1e-3
    ok_all &= ok_s
    print(f"  samp 密度: {rho_s:.4f} (设计 1.0)  {'PASS' if ok_s else 'FAIL'}")

    # 2) Ti 示踪层密度
    if ti_sp is not None:
        lo, hi = EXPECT[ti_sp]
        m_ti = (x >= lo) & (x <= hi)
        rho_ti = float(np.mean(dens[m_ti]))
        ok_ti = abs(rho_ti - RHO_TI) / RHO_TI < 1e-3
        ok_all &= ok_ti
        print(f"  Ti({ti_sp}) 密度: {rho_ti:.4f} (设计 {RHO_TI})  "
              f"{'PASS' if ok_ti else 'FAIL'}")

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

n = n_checked
print(f"\n===== 总判定: {'PASS' if ok_all else 'FAIL'} ({n} 场景) =====")
sys.exit(0 if ok_all else 2)
