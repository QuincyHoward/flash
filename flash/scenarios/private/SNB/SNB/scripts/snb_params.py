#!/usr/bin/env python3
"""SNB 场景参数参考 ── 可直接复制进自己的场景
═══════════════════════════════════════════════════════════════════════════════

本文件只含**参数与配置**（方法层），不含任何 F90 实现。可自由分享/复用。

用法:
    python snb_params.py --show          # 打印全部推荐设置
    python snb_params.py --emit-par      # 输出可粘贴的 par 片段
    python snb_params.py --emit-setup    # 输出 setup 命令模板
    python snb_params.py --check <par>   # 校验一个 par 的关键设置是否符合建议
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

# ══════════════════════════════════════════════════════════════
# 一、几何 / 物种 / 材料
# ══════════════════════════════════════════════════════════════
GEOMETRY: Dict[str, Any] = {
    "xmin": -50.0e-4,          # cm  → -50 µm
    "xmax": 250.0e-4,          # cm  → +250 µm
    "geometry": "cartesian",
}

# 各物种: 名称 → (cn4 表, 密度 g/cm³, A, Z, ZMin)
# 注: tar2/tar3 与 tar1 组分相同, 仅作**示踪层标记**用 (便于诊断追踪)
SPECIES: Dict[str, Dict[str, Any]] = {
    "cham": {"cn4": "He-BADGER-TOPS-Final.cn4", "rho": 1.0e-6,
             "A": 4.002602, "Z": 2.0, "ZMin": None},
    "tar1": {"cn4": "CH-BADGER-TOPS-Final.cn4", "rho": 1.04,
             "A": 6.5, "Z": 3.5, "ZMin": 0.02},
    "tar2": {"cn4": "CH-BADGER-TOPS-Final.cn4", "rho": 1.04,
             "A": 6.5, "Z": 3.5, "ZMin": 0.02},
    "tar3": {"cn4": "CH-BADGER-TOPS-Final.cn4", "rho": 1.04,
             "A": 6.5, "Z": 3.5, "ZMin": 0.02},
}
# ⚠ 同一场景内所有物种的表**群数必须一致**

T_INITIAL = 290.11375          # K (室温)

# ══════════════════════════════════════════════════════════════
# 二、激光（多段梯形）
# ══════════════════════════════════════════════════════════════
LASER: Dict[str, Any] = {
    "n_sections": 4,
    "times": [0.0, 0.2e-9, 0.99e-9, 1.0e-9],     # s
    "powers": [0.0, 1.5e14, 1.5e14, 0.0],        # W/cm²
    "lensX": 500.0e-4,                            # cm; 由 lens 指向 target 决定入射方向
    "targetX": 0.0,
    "wavelength_um": 0.351,
    "cross_section": "uniform",                   # 或 "gaussian1D"
    "n_rays": 1,
    "grid_type": "regular1D",
    "n_radial_tics": 512,
}

# ══════════════════════════════════════════════════════════════
# 三、辐射 MGD（N 群需 N+1 个边界）
# ══════════════════════════════════════════════════════════════
RADIATION: Dict[str, Any] = {
    "rt_useMGD": True,
    "rt_mgdNumGroups": 10,          # ★ 必须 == setup 的 mgd_meshgroups
    "rt_mgdBounds": [1.0e-1, 3.981e-1, 1.585e0, 6.31e0, 2.51e1,
                     1.0e2, 3.981e2, 1.585e3, 6.31e3, 2.51e4, 1.0e5],
    "rt_mgdFlMode": "fl_larsen",
    "rt_mgdFlCoef": 1.0,
    "boundary": "vacuum",           # rt_mgd{Xl,Xr,Yl,Yr,Zl,Zr}BoundaryType
    "useOpacity": True,
    "useRadTrans": True,
    "op_tableEnergyTolerance": 1.0e-2,
}

# 关辐射: 纯运行时三开关 (源码/setup/编译不变)
RADIATION_OFF: Dict[str, Any] = {
    "rt_useMGD": False, "useOpacity": False, "useRadTrans": False,
}

# ══════════════════════════════════════════════════════════════
# 三-b、流体 / EOS（★ 缺失会导致启动即失稳: 负 3T 内能）
# ══════════════════════════════════════════════════════════════
HYDRO_EOS: Dict[str, Any] = {
    "eosModeInit": "dens_temp_gather",
    "smallt": 1.0,                  # ★ EOS 温度下限 (缺省会导致温度被钳到 0)
    "smallx": 1.0e-99,
    "eos_useLogTables": False,
    "eos_maxNewton": 5000,
    "useHydro": True,
    "order": 3,
    "slopeLimiter": "minmod",
    "LimitedSlopeBeta": 1.0,
    "charLimiting": True,
    "use_avisc": True,
    "cvisc": 0.1,
    "use_flattening": False,
    "use_steepening": False,
    "use_upwindTVD": False,
    "use_hybridOrder": True,
    "RiemannSolver": "HLL",
    "entropy": False,
    "shockDetect": True,            # ★ 数值稳定性
    "use_3dFullCTU": True,
    # 边界 (1D 用 x 两侧; 其余维度一并给出以便复用)
    "xl_boundary_type": "outflow", "xr_boundary_type": "outflow",
    "yl_boundary_type": "outflow", "yr_boundary_type": "outflow",
    "zl_boundary_type": "outflow", "zr_boundary_type": "outflow",
}

# ══════════════════════════════════════════════════════════════
# 四、电子热传导（SNB 核心区）
# ══════════════════════════════════════════════════════════════
CONDUCTION: Dict[str, Any] = {
    "useDiffuse": True,
    "useDIffuseTherm": True,
    "useConductivity": True,
    "diff_useEleCond": True,
    # ★★ 2026-09-12 实测更正 —— 本键在 SNB 场景下是 **no-op**:
    #    `source/snb_package/diff_advanceTherm.F90` 各向同性电子分支里,
    #    限流器调用(:839)与 SH 传导解(:847)**都被注释**; 且场景
    #    `diff_anisoCondForEle=.false.` → 不进入各向异性分支(:818) →
    #    **没有任何存活的消费者**。实测(全长 0.8ns × 17 帧 + 短时 × 11 帧):
    #    `fl_none` 与 `fl_harmonic` 六个物理量逐帧最大绝对差**全为 0(逐位相同)**。
    #  ⇒ 按项目约定**默认 `fl_none`**(声明意图)。
    #  ⚠ 请勿再以"fl_harmonic 保护 SNB 守恒"为依据 —— 见 docs/05 坑位清单 P1 更正块。
    #    该键对**离子**腿(用 diff_ionFlMode)与 FLLM_VAR 诊断量仍有作用。
    "diff_eleFlMode": "fl_none",
    "diff_eleFlCoef": 0.06,
    "diff_thetaImplct": 1.0,
    "diff_anisoCondForEle": False,     # SNB 分支在 1D 均匀各向同性下生效
    "dt_diff_factor": 1.0e100,         # ★ 关掉扩散步长限制
    # ★★★ gr_hypreUseFloor = .false. —— 决定性键 (2026-09-12 A/B 实测)
    #   隐式扩散求解器 (HYPRE) 的"取整/floor"开关。**FLASH 默认 = .true.**,
    #   而 SNB 多群非局域热流经该求解器时, 打开 floor 会改变解 →
    #   过度压缩 → ρmax 冲高后崩塌 (质量守恒破裂)。
    #   实测: 同一 par 仅此一键(默认 .true. → .false.)即可把
    #         ρmax@0.05ns 从 2.845451 拉回 1.738337 = 与成功基线**逐位相同**。
    #   ⚠ 该键此前被 gen_scene 的 _KEY_DIFF_IGNORE 排除在键集校验之外,
    #     导致"183 键 0 缺"通过但物理已失真 —— 已同时修正校验清单。
    "gr_hypreUseFloor": False,
    "useHeatexchange": True,
    "hx_dtFactor": 1.0e100,
    "rt_dtFactor": 1.0e100,
}

# ══════════════════════════════════════════════════════════════
# 五、时间积分（★ dtmax 是稳定性的关键）
# ══════════════════════════════════════════════════════════════
TIME: Dict[str, Any] = {
    "tstep_change_factor": 1.10,
    "cfl": 0.2,
    "dtinit": 1.0e-15,
    "dtmin": 1.0e-16,
    # ★★ dtmax = 2e-14（2026-09-11 由 chk 内实测 dt 值反推确认）
    #   判据不是 par 文本, 而是 chk 里 'real scalars' 的 dt:
    #     t004 (成功, ρmax→12.11, 跑满 800 ps): dt 全程钉在 2.000e-14
    #       → 说明 t004 实际是以 `--dtmax 2e-14` 命令行覆写运行的
    #         (作者 objdir 的 flash.par 虽写 dtmax=2e-12, 但被覆写)
    #     t005 (dtmax=2e-12): dt 从 2.9e-14 涨到 4.6e-14 → ρmax 0.26, 崩塌
    #   机理: SNB 电子热扩散步长限制未被 dt_diff_factor=1e100 关掉时,
    #         dt 允许增长就会越过稳定阈值。2e-14 提供固定安全裕度。
    "dtmax": 2.0e-14,
    "tmax": 0.8e-9,
    "nend": 100000000,
}

# ══════════════════════════════════════════════════════════════
# 六、输出（以 chk 为主）
# ══════════════════════════════════════════════════════════════
OUTPUT: Dict[str, Any] = {
    "checkpointFileIntervalTime": 5.0e-11,   # chk: 推荐绘图数据源 (71 键 / float64)
    "plotFileIntervalTime": 4.0e-10,         # plt: 仅健全性检查
    # ★ 不要写 plotFileIntervalStep / checkpointFileIntervalStep
    #   (与 Time 是 OR 双触发)
    # ★ plot_var 白名单 ≤ 12 项且从 1 连续编号 (第 13 项起静默忽略)
}

# ══════════════════════════════════════════════════════════════
# 七、setup 命令模板
# ══════════════════════════════════════════════════════════════
SETUP_TEMPLATE = (
    "./setup -auto {sim_name} -1d +cartesian +ug {nxb_flag} +hdf5typeio "
    "species={species} +mtmmmt +laser +uhd3t +mgd mgd_meshgroups={ng} "
    "-objdir={objdir}"
)

# ══════════════════════════════════════════════════════════════
# 八、网格建议（+ug 均匀网格）
# ══════════════════════════════════════════════════════════════
GRID_NOTES = (
    "+ug 下 par 的 nblockx/lrefine_* 被忽略; 一块一进程 → mpiexec -n 必须 == iProcs。\n"
    "分辨率三条路径: ① 固定块 -nxb=N → 总格数=iProcs*N;\n"
    "                ② 非固定块 显式 -nofbs + par iGridSize=M → 总格数=M (与核数解耦);\n"
    "                ③ iProcs 本身。\n"
    "⚠ 只'不给 -nxb'进不了非固定块模式 (FLASH 默认仍 NXB=8, iGridSize 被静默忽略)。\n"
    "⚠ -nofbs 会强制并行 HDF5 IO, 与 +serialIO / parallelIO=False 冲突。"
)

# 参考量级: 1D / 域 300 µm / dx≈0.29 µm
GRID_REFERENCE = {"nxb": 128, "iprocs": 8, "cells": 128 * 8, "dx_um": 300.0 / (128 * 8)}

# 运行耗时参考 (1024 格, dtmax=2e-14, tmax=0.8 ns)
# ★ 2026-09-11 复现值 (t004 SNB 侧 verify_ 腿, iProcs=8 × nxb=128):
#     SNB / 辐射开 = 1405.9 s,  SNB / 辐射关 = 807.0 s
#   下表为更早一轮的参考, 与网格/负载相关, 仅作量级参考。
PERF_REFERENCE = [
    ("限流 SH / 辐射开", "≈4.0 万", "≈970 s", "≈40 步/s"),
    ("限流 SH / 辐射关", "≈4.0 万", "≈460 s", "≈85 步/s"),
    ("SNB     / 辐射开", "≈4.0 万", "≈1406 s", "≈28 步/s"),
    ("SNB     / 辐射关", "≈4.0 万", "≈807 s", "≈50 步/s"),
]

# 建议值校验表: key → (期望值, 说明)
RECOMMENDED: Dict[str, Tuple[Any, str]] = {
    "diff_eleFlMode": ("fl_none", "SNB 电子路径实测 no-op; 默认 fl_none (2026-09-12)"),
    "diff_eleFlCoef": (0.06, "有限限流系数 (对离子腿/FLLM 诊断量生效)"),
    "diff_thetaImplct": (1.0, "全隐式"),
    "diff_anisoCondForEle": (False, "SNB 1D 各向同性分支"),
    "dt_diff_factor": (1.0e100, "关扩散步长限制"),
    "hx_dtFactor": (1.0e100, "关热交换步长限制"),
    "rt_dtFactor": (1.0e100, "关辐射步长限制"),
    # ★★★ 真正的承重键: FLASH 默认 .true. → SNB 多群解失真 → 崩塌
    "gr_hypreUseFloor": (False, "★★★ SNB 崩塌真正主因; 作者原版 par 亦为此值"),
    "dtmax": (2.0e-14, "★★ 必用值 — 非 2e-12; 判据见时效性说明 (t004 实测跑满 800 ps)"),
    "useHeatexchange": (True, "电子-离子耦合"),
}


def _fmt(v: Any) -> str:
    if isinstance(v, bool):
        return ".true." if v else ".false."
    if isinstance(v, float):
        return f"{v:.6g}"
    if isinstance(v, str):
        return f'"{v}"'
    return str(v)


def show() -> None:
    print("=" * 78)
    print(" SNB 场景参数参考 (可直接复制; 详见 docs/01_设置方法.md)")
    print("=" * 78)
    for title, d in (("几何", GEOMETRY), ("激光", LASER), ("辐射 MGD", RADIATION),
                     ("电子热传导", CONDUCTION), ("时间积分", TIME), ("输出", OUTPUT)):
        print(f"\n── {title} ──")
        for k, v in d.items():
            print(f"  {k:<38} = {_fmt(v)}")
    print("\n── 物种/材料 ──")
    for name, m in SPECIES.items():
        print(f"  {name}: cn4={m['cn4']}, rho={m['rho']}, A={m['A']}, Z={m['Z']}")
    print(f"\n── 关辐射三开关 (纯运行时) ──")
    for k, v in RADIATION_OFF.items():
        print(f"  {k:<38} = {_fmt(v)}")
    print(f"\n── 网格建议 ──\n{GRID_NOTES}")
    print(f"\n  参考量级: nxb={GRID_REFERENCE['nxb']} × iProcs={GRID_REFERENCE['iprocs']}"
          f" = {GRID_REFERENCE['cells']} 格, dx≈{GRID_REFERENCE['dx_um']:.4f} µm")
    print("\n── 耗时参考 (1024 格, dtmax=2e-14) ──")
    for a, b, c, d in PERF_REFERENCE:
        print(f"  {a}: {b} 步, 墙钟 {c}, {d}")


def emit_par() -> None:
    print("# " + "=" * 76)
    print("# SNB 场景 par 片段 (由 snb_params.py 生成; 仅供参考, 请按需调整)")
    print("# " + "=" * 76)
    for d in (GEOMETRY, LASER, RADIATION, CONDUCTION, TIME, OUTPUT):
        for k, v in d.items():
            print(f"{k:<38} = {_fmt(v)}")
    for name, m in SPECIES.items():
        cap = name.capitalize()
        print(f"sim_rho{cap:<32} = {m['rho']:.6g}")
        print(f"sim_tele{cap:<31} = {T_INITIAL}")
        print(f"sim_tion{cap:<31} = {T_INITIAL}")
        print(f"sim_trad{cap:<31} = {T_INITIAL}")
        print(f"ms_{name}A{'':<34} = {m['A']}")
        print(f"ms_{name}Z{'':<34} = {m['Z']}")
        if m.get("ZMin") is not None:
            print(f"ms_{name}ZMin{'':<31} = {m['ZMin']}")
        for kind in ("eos", "op"):
            if kind == "eos":
                print(f"eos_{name}EosType{'':<26} = \"eos_tab\"")
                print(f"eos_{name}SubType{'':<26} = \"ionmix4\"")
                print(f"eos_{name}TableFile{'':<24} = \"{m['cn4']}\"")
            else:
                print(f"op_{name}Absorb{'':<27} = \"op_tabpa\"")
                print(f"op_{name}Emiss{'':<28} = \"op_tabpe\"")
                print(f"op_{name}Trans{'':<28} = \"op_tabro\"")
                print(f"op_{name}FileType{'':<25} = \"ionmix4\"")
                print(f"op_{name}FileName{'':<25} = \"{m['cn4']}\"")


def emit_setup() -> None:
    print(SETUP_TEMPLATE.format(
        sim_name="<SimName>", nxb_flag="-nxb=128",
        species=",".join(SPECIES.keys()),
        ng=RADIATION["rt_mgdNumGroups"], objdir="<SimName>_obj"))


def check_par(path: Path) -> int:
    """校验 par 的关键设置是否符合建议。"""
    if not path.exists():
        print(f"[X] 文件不存在: {path}")
        return 2
    kv: Dict[str, str] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        s = line.split("#", 1)[0].strip()
        if s and "=" in s:
            k, v = s.split("=", 1)
            kv[k.strip()] = v.strip()

    print("=" * 78)
    print(f" par 关键设置校验: {path}")
    print("=" * 78)
    bad = 0
    for k, (want, why) in RECOMMENDED.items():
        raw = kv.get(k)
        if raw is None:
            print(f"  [!] 缺失  {k:<32} 建议 {_fmt(want)}   ({why})")
            continue
        v = raw.lower().replace(".", "")
        if isinstance(want, bool):
            got = v in ("true", "t")
        elif isinstance(want, float):
            try:
                got = float(raw)
            except ValueError:
                got = None
        else:
            got = raw.strip('"')
        ok = (got == want) if not isinstance(want, float) else \
             (got is not None and abs(got - want) <= 1e-12 * abs(want))
        print(f"  {'OK ' if ok else '[X]'} {k:<32} = {raw:<16} 建议 {_fmt(want)}   ({why})")
        bad += 0 if ok else 1

    # 群数一致性
    ng = kv.get("rt_mgdNumGroups")
    if ng:
        n = int(float(ng))
        n_bounds = sum(1 for k in kv if re.match(r"rt_mgdBounds_\d+$", k))
        ok = (n_bounds == n + 1)
        print(f"  {'OK ' if ok else '[X]'} rt_mgdBounds 个数 = {n_bounds} "
              f"(N={n} 群需 {n+1} 个)")
        bad += 0 if ok else 1
    # plot_var 上限
    pv = [k for k in kv if re.match(r"plot_var_\d+$", k)]
    ok = len(pv) <= 12
    print(f"  {'OK ' if ok else '[X]'} plot_var 项数 = {len(pv)} (上限 12)")
    bad += 0 if ok else 1

    print()
    if bad:
        print(f" [X] {bad} 项不符合建议 —— 见 docs/01_设置方法.md / 05_坑位清单.md")
        return 1
    print(" [OK] 关键设置全部符合建议 ✓")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="SNB 场景参数参考")
    ap.add_argument("--show", action="store_true", help="打印全部推荐设置")
    ap.add_argument("--emit-par", action="store_true", help="输出 par 片段")
    ap.add_argument("--emit-setup", action="store_true", help="输出 setup 命令模板")
    ap.add_argument("--check", metavar="PAR", help="校验一个 par 文件")
    args = ap.parse_args()

    if args.emit_par:
        emit_par(); return 0
    if args.emit_setup:
        emit_setup(); return 0
    if args.check:
        return check_par(Path(args.check))
    show()
    return 0


if __name__ == "__main__":
    sys.exit(main())
