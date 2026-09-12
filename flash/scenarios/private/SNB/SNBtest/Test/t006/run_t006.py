"""t006 —— 辐射开关 2×2 矩阵（FL-SH / SNB × 辐射开/关）

**本场景与 t004 等价**（同样的几何/激光/材料/网格/时间积分与四腿矩阵），
但**完全通过 `SNB/SNB` 核心模块从零搭建** —— 本文件是唯一的自有脚本（薄驱动）。

设计目标
--------
1. **验证核心模块的自包含性**：若本薄驱动能一次跑通四腿且受控性自检通过，
   说明 `SNB/SNB` 已可独立复用，不再依赖任何历史场景目录。
2. **把 t004 的成功经验固化**、**把 t005 的失败教训前置拦截**（见下）。

调用链
------
    t006/run_t006.py
      ├─ generate : SNB/SNB/scripts/generate/gen_scene.py    (F90 复制 + par 生成 + 受控自检)
      ├─ run      : SNB/SNB/scripts/run/run_scene.py          (部署→setup→make→run→收集)
      ├─ check    : SNB/SNB/scripts/analysis/chk_probe.py     (chk 健康检查: dt 钳位判据)
      └─ plot     : SNB/SNB/scripts/analysis/compare_4way.py  (2×2 图 + 定量表)

★★ 三条并列前提（缺一不可；前两条由本驱动护栏强制，第三条由核心模块强制）
----------------------------------------------------------------------
| # | 前提 | 违反后果 |
|---|---|---|
| 1 | **`gr_hypreUseFloor = .false.`** | ★★★ **真正主因**。FLASH 默认 `.true.` → HYPRE 隐式扩散解失真 → 过度压缩 → ρmax 冲高后崩塌（12.1 → 0.26，质量守恒破裂）。由 `snb_params.py` 写入 + `gen_scene.py` 的 `NUMERIC_CRITICAL_KEYS` 硬校验 |
| 2 | **`dtmax = 2.0e-14`** | `dt` 增长越过稳定阈值（**必要条件，非充分条件**） |
| 3 | **SNB 腿 `driver-variant = radon`** | 作者原版把 `call RadTrans` 注释了 → 辐射永不推进、par 三开关失效 → 2×2 失去意义 |

★ **两条判据铁律**（详见 `SNB/docs/08_故障案例_SNB崩塌.md`）
-----------------------------------------------------------
1. `dtmax` 是否生效**不能看 par 文本**（会被命令行覆写），必须读 chk 里
   `real scalars` 的 `dt` 实测值。
2. **`dt` 钳位正确 ≠ 结果正确** —— 还必须检查 **ρmax 走势**与**总质量守恒**。
   t006 曾出现 `dt` 全程钳位 2.000e-14 却依然崩塌的情形（即前提 1 缺失）。
3. 配置溯源最可靠的手段：与参考日志做**参数回显差分**。

四腿矩阵（受控）
----------------
| 腿 | 树 | 驱动 | 热传导源 | 辐射三开关 |
|---|---|---|---|---|
| FL-SH radON  | 标准 FLASH | 树原生（本就调用 RadTrans） | 树原生 | `.true.` ×3 |
| FL-SH radOFF | 标准 FLASH | 树原生 | 树原生 | `.false.` ×3 |
| SNB radON    | FLASHSNB   | **radON 变体** | 作者 SNB 版 | `.true.` ×3 |
| SNB radOFF   | FLASHSNB   | **radON 变体** | 作者 SNB 版 | `.false.` ×3 |

同侧两腿共用同一份 F90 与 objdir → "辐射"是两腿间的唯一变量。

用法
----
    PY=C:/Users/Administrator/.workbuddy/binaries/python/envs/default/Scripts/python.exe
    cd flash/scenarios/private/SNB/SNBtest/Test/t006

    $PY run_t006.py                      # 全流程 (generate → run → check → plot)
    $PY run_t006.py --stage generate     # 只生成场景
    $PY run_t006.py --stage run          # 只跑仿真 (四腿)
    $PY run_t006.py --stage check        # 只做 chk 健康检查
    $PY run_t006.py --stage plot         # 只出图
    $PY run_t006.py --smoke              # 短时验证 (tmax=1e-11, 约 1 分钟)
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional

_T006 = Path(__file__).resolve().parent

PY = sys.executable

# ── 目录布局 ──────────────────────────────────────────────────
SCENE = _T006 / "scene"           # 生成物 (F90 + par), 可随时删除重建
IMAGES = _T006 / "images"         # 对比图
RESULTS = _T006 / "results"       # 定量表
LOGS = _T006 / "logs"             # 日志
DOCS = _T006 / "docs"

LEGS = ("snb", "flsh")
RADS = ("radon", "radoff")

# ── ★★ 并列前提（硬编码于此，避免任何"从模板继承"的歧义）────────
DTMAX_REQUIRED = 2.0e-14
DTMAX_GUARD = 1.0e-13             # 超过此值直接拒绝运行 (安全护栏)
DRIVER_VARIANT_REQUIRED = "radon"


def _find_snb_core() -> Path:
    """定位 `SNB/SNB` 核心模块。

    目录布局: .../private/SNB/{SNB/**,  SNBtest/Test/t006/本文件}
    从本文件向上逐级查找「名为 SNB 且同时含 scripts/ 与 source/ 的目录」,
    **不写死层数** —— 便于场景目录整体搬迁。
    """
    for anc in [_T006] + list(_T006.parents):
        for cand in (anc / "SNB", anc.parent / "SNB"):
            if (cand / "scripts").is_dir() and (cand / "source").is_dir():
                return cand
    raise SystemExit(f"[X] 未找到 SNB 核心模块 (从 {_T006} 向上搜索)")


SNB = _find_snb_core()
GEN = SNB / "scripts" / "generate" / "gen_scene.py"
RUN = SNB / "scripts" / "run" / "run_scene.py"
PROBE = SNB / "scripts" / "analysis" / "chk_probe.py"
PLOT = SNB / "scripts" / "analysis" / "compare_4way.py"
SAFETY = SNB / "scripts" / "check_share_safety.py"
EXAMPLE_PAR = SNB / "source" / "example" / "flash.par"


def sh(cmd: List[object], tag: str = "") -> int:
    print(f"\n{'='*78}\n $ {' '.join(str(c) for c in cmd)}\n{'='*78}", flush=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    if tag:
        with (LOGS / f"{tag}.log").open("a", encoding="utf-8", newline="\n") as fh:
            fh.write(f"\n### {' '.join(str(c) for c in cmd)}\n")
    return subprocess.run([str(c) for c in cmd]).returncode


def preflight(args) -> bool:
    print("\n" + "=" * 78)
    print(" t006 —— 辐射开关 2×2 矩阵 (薄驱动: 全部调用 SNB/SNB 核心模块)")
    print(f" 核心模块: {SNB}")
    print(f" 场景输出: {SCENE}")
    print(f" 图/表:    {IMAGES} / {RESULTS}")
    print("-" * 78)
    print(f" 数据 tag: {args.tag}    网格: iProcs={args.iprocs} × nxb={args.nxb} "
          f"= {args.iprocs*args.nxb} 格")
    print(f" tmax={args.tmax:.3e}   ★★ dtmax={args.dtmax:.3e}   "
          f"★ driver={DRIVER_VARIANT_REQUIRED}")
    print("=" * 78)

    ok = True
    for p, what in ((GEN, "场景生成器"), (RUN, "运行驱动"),
                    (PROBE, "chk 健康检查"), (PLOT, "四腿对比绘图")):
        if not p.exists():
            print(f"  [X] 核心模块脚本缺失 ({what}): {p}")
            ok = False
    if not (SNB / "source" / "snb_package").is_dir():
        print(f"  [X] 核心模块 source/snb_package 缺失 —— 先跑 import_sources.py")
        ok = False
    if not (SNB / "variants" / "Driver_evolveFlash_radON.F90").exists():
        print(f"  [X] 缺 radON 驱动变体 —— 先跑 tools_local/make_variants.py")
        ok = False

    # ★★ 前提 1: dtmax 护栏
    if args.dtmax > DTMAX_GUARD:
        print(f"  [X] dtmax={args.dtmax:.3e} 超过安全护栏 {DTMAX_GUARD:.1e}。")
        print(f"      ★ 本场景必须 dtmax={DTMAX_REQUIRED:.3e}，否则 SNB 腿会非物理崩塌")
        print(f"        (t005 实测: dt 增长到 4.6e-14 → ρmax 12.11→0.26, 质量守恒破裂)")
        print(f"        详见 SNB/docs/08_故障案例_SNB崩塌.md")
        ok = False
    elif abs(args.dtmax - DTMAX_REQUIRED) > 1e-18:
        print(f"  [!] dtmax={args.dtmax:.3e} 与推荐值 {DTMAX_REQUIRED:.3e} 不同 —— "
              f"请确认是刻意为之")

    # ★★ 前提 2: 驱动变体
    if args.driver_variant != DRIVER_VARIANT_REQUIRED:
        print(f"  [X] driver-variant={args.driver_variant} 不可用于本场景。")
        print(f"      ★ SNB 腿必须用 {DRIVER_VARIANT_REQUIRED}: 作者原版把 call RadTrans")
        print(f"        注释了 → 辐射永不推进、par 三开关失效 → 2×2 矩阵失去意义")
        ok = False

    if ok:
        print("  [OK] 前置检查通过（两条并列前提均满足）")
    return ok


def stage_check(args, tag_prefix: str) -> int:
    """★ chk 健康检查：以 dt 实测值判定 dtmax 是否生效（docs/08 铁律）。"""
    print("\n" + "=" * 78)
    print(" chk 健康检查 —— dtmax 钳位判据")
    print("=" * 78)
    rc = 0
    found = 0
    for leg in LEGS:
        for rad in RADS:
            d = SCENE / "flash_output" / f"sim_{leg}" / f"{tag_prefix}{rad}"
            if not d.is_dir():
                print(f"\n  [!] {leg}/{tag_prefix}{rad}: 目录不存在, 跳过")
                continue
            found += 1
            print(f"\n── {leg}/{tag_prefix}{rad} ──────────────────────────")
            rc |= sh([PY, PROBE, "--dir", d,
                      "--expect-dtmax", f"{args.dtmax:.6e}", "--brief"], "")
    if not found:
        print(f"\n  [X] 未找到任何腿的数据目录 (前缀='{tag_prefix}')")
        return 1
    return rc


def main() -> int:
    ap = argparse.ArgumentParser(
        description="t006: 辐射开关 2×2 矩阵 (薄驱动, 全调用 SNB/SNB 核心模块)")
    ap.add_argument("--stage", choices=["all", "generate", "run", "check", "plot"],
                    default="all")
    # ★★ 时间积分: 硬性 2e-14
    ap.add_argument("--dtmax", type=float, default=DTMAX_REQUIRED,
                    help=f"★★ 必须 {DTMAX_REQUIRED:.1e}（判据见 SNB/docs/08）")
    ap.add_argument("--tmax", type=float, default=0.8e-9)
    # ★★ 驱动变体: 硬性 radon
    ap.add_argument("--driver-variant", choices=["radon", "none"],
                    default=DRIVER_VARIANT_REQUIRED,
                    help=f"★★ SNB 腿必须 {DRIVER_VARIANT_REQUIRED}"
                         f"（作者原版注释了 call RadTrans → 辐射永不推进）")
    ap.add_argument("--nxb", type=int, default=128)
    ap.add_argument("--iprocs", type=int, default=8)
    ap.add_argument("--chk-dt", type=float, default=5.0e-11,
                    help="chk 间隔; 0.8 ns / 5e-11 = 17 帧")
    ap.add_argument("--plt-dt", type=float, default=4.0e-10)
    ap.add_argument("--tag", default="full", help="绘图/输出命名标记")
    ap.add_argument("--smoke", action="store_true",
                    help="短时验证: tmax=1e-11")
    ap.add_argument("--skip-setup", action="store_true")
    ap.add_argument("--skip-make", action="store_true")
    args = ap.parse_args()

    if args.smoke:
        args.tmax = 1.0e-11
        args.tag = "smoke"

    if not preflight(args):
        return 2

    t0 = time.time()
    rc = 0
    tag_prefix = "smoke_" if args.smoke else ""

    # ── ① 生成场景（F90 复制 + 2×2 par + 受控性自检 + 键集差分）──
    if args.stage in ("all", "generate"):
        cmd: List[object] = [
            PY, GEN, "--out", SCENE, "--legs", "snb,flsh",
            "--radiation", "both",
            "--driver-variant", args.driver_variant,
            "--nxb", args.nxb, "--iprocs", args.iprocs,
            "--tmax", args.tmax, "--dtmax", args.dtmax,
            "--chk-dt", args.chk_dt, "--plt-dt", args.plt_dt,
        ]
        if EXAMPLE_PAR.exists():
            cmd += ["--verify-keys-against", EXAMPLE_PAR]
        rc |= sh(cmd, "generate")
        if rc:
            print("\n[X] 场景生成失败, 中止")
            return rc

    # ── ② 跑四条腿（★ 每侧只 setup/make 一次: 辐射是纯 par 开关）──
    if args.stage in ("all", "run"):
        for leg in LEGS:
            first_of_leg = True      # 按「侧」而非全局: 两侧树/objdir 不同
            for rad in RADS:
                cmd = [PY, RUN, "--scene", SCENE, "--side", leg,
                       "--par", f"{leg}_{rad}.par", "--tag", f"{tag_prefix}{rad}",
                       "--nxb", args.nxb, "--iprocs", args.iprocs,
                       "--out-root", SCENE / "flash_output"]
                if first_of_leg:
                    if args.skip_setup:
                        cmd.append("--skip-setup")
                    if args.skip_make:
                        cmd.append("--skip-make")
                else:
                    # 同侧后续腿: 复用已编译二进制, 只换 par
                    cmd += ["--skip-deploy", "--skip-setup", "--skip-make"]
                r = sh(cmd, f"run_{leg}_{rad}")
                if r:
                    print(f"\n[!] {leg}/{rad} 未通过（rc={r}）—— 继续其余腿")
                rc |= r
                first_of_leg = False

    # ── ③ chk 健康检查（dt 钳位判据）────────────────────────────
    if args.stage in ("all", "check"):
        rc |= stage_check(args, tag_prefix)

    # ── ④ 出图 + 定量表 ─────────────────────────────────────────
    if args.stage in ("all", "plot"):
        cmd = [PY, PLOT, "--scene", SCENE, "--out", IMAGES, "--tag", args.tag]
        if tag_prefix:
            # ★ 数据前缀与输出 tag 解耦: 短测读 smoke_* 目录, 图名仍标 smoke
            cmd += ["--data-prefix", tag_prefix]
        rc |= sh(cmd, "plot")
        RESULTS.mkdir(parents=True, exist_ok=True)
        for f in (IMAGES / "ablation").glob("*"):
            (RESULTS / f.name).write_bytes(f.read_bytes())
        for f in (IMAGES / "compare").glob("*"):
            (RESULTS / f.name).write_bytes(f.read_bytes())

    print("\n" + "=" * 78)
    print(f" t006 完成 — 耗时 {time.time()-t0:.1f} s, rc={rc}")
    print(f" 场景: {SCENE}")
    print(f" 图:   {IMAGES}")
    print(f" 表:   {RESULTS}")
    print("=" * 78)
    return rc


if __name__ == "__main__":
    sys.exit(main())
