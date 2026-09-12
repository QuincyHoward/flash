"""t005 —— 2×2 辐射开关对比（FL-SH / SNB × 辐射开/关）
═══════════════════════════════════════════════════════════════════════════════

**本场景是「薄驱动」**：不自己实现算法，全部调用 SNB/SNB 核心模块的脚本。
这同时是对核心模块的一次端到端验证。

调用链
------
    t005/run_t005.py
      ├─ generate : SNB/SNB/scripts/generate/gen_scene.py   (F90 复制 + par 生成)
      ├─ run      : SNB/SNB/scripts/run/run_scene.py         (部署→setup→make→run→收集)
      └─ plot     : SNB/SNB/scripts/analysis/compare_4way.py (2×2 图 + 定量)

四腿设计（受控）
----------------
| 腿 | 树 | 热传导源 | 辐射三开关 |
|---|---|---|---|
| FL-SH radON  | 标准 FLASH | 树原生 | .true. ×3 |
| FL-SH radOFF | 标准 FLASH | 树原生 | .false. ×3 |
| SNB radON    | FLASHSNB   | 作者 SNB 版 | .true. ×3 |
| SNB radOFF   | FLASHSNB   | 作者 SNB 版 | .false. ×3 |

★ SNB 侧两腿必须用 `radON` 驱动变体（恢复被注释的辐射推进调用），
  否则 radON 腿的辐射**开不起来**（par 三开关形同虚设，两腿将无区别）。

★★ 本场景是一次**失败案例**（2026-09-11）：曾把 `dtmax` 误设为 `2e-12`，
   导致 SNB 两腿非物理崩塌（ρmax 12.11 → 0.26、质量守恒破裂）。
   根因与完整复盘见 `SNB/docs/08_故障案例_SNB崩塌.md`。
   **判据铁律**：`dtmax` 是否生效**看 chk 的 `dt` 实测值，不看 par 文本**。
   正确配置 = `dtmax 2e-14` + `driver-variant radon`，两者并列缺一不可。
   等价的成功版本见 `Test/t004`（早期脚本）与 `Test/t006`（薄驱动范式）。

用法
----
    python flash/scenarios/private/SNB/SNBtest/Test/t005/run_t005.py            # 全流程
    ... run_t005.py --stage generate        # 只生成场景
    ... run_t005.py --stage run             # 只跑仿真
    ... run_t005.py --stage plot            # 只出图
    ... run_t005.py --tmax 1.0e-11          # 短时验证
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path
from typing import List

_T005 = Path(__file__).resolve().parent


def _find_snb_core() -> Path:
    """定位 SNB/SNB 核心模块。

    目录布局: .../private/SNB/{SNB/**, SNBtest/Test/t005/本文件}
    从本文件向上逐级查找「名为 SNB 且含 scripts/ 的兄弟目录」, 不写死层数。
    """
    for anc in [_T005] + list(_T005.parents):
        cand = anc / "SNB"
        if (cand / "scripts").is_dir() and (cand / "source").is_dir():
            return cand
        sib = anc.parent / "SNB"          # 兄弟目录情形 (t005 位于 SNBtest 下)
        if (sib / "scripts").is_dir() and (sib / "source").is_dir():
            return sib
    raise SystemExit(f"[X] 未找到 SNB 核心模块 (从 {_T005} 向上搜索)")


SNB = _find_snb_core()
GEN = SNB / "scripts" / "generate" / "gen_scene.py"
RUN = SNB / "scripts" / "run" / "run_scene.py"
PLOT = SNB / "scripts" / "analysis" / "compare_4way.py"
CHK = SNB / "scripts" / "check_share_safety.py"

PY = sys.executable
SCENE = _T005 / "scene"          # 生成的场景 (F90/par)
IMAGES = _T005 / "images"        # 对比图 (分门别类)
RESULTS = _T005 / "results"      # 定量表
LOGS = _T005 / "logs"

LEGS = ("flsh", "snb")
RADS = ("radon", "radoff")


def sh(cmd: List[str], tag: str = "") -> int:
    print(f"\n{'='*78}\n $ {' '.join(str(c) for c in cmd)}\n{'='*78}", flush=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    if tag:
        with (LOGS / f"{tag}.log").open("a", encoding="utf-8", newline="\n") as fh:
            fh.write(f"\n### {' '.join(str(c) for c in cmd)}\n")
    p = subprocess.run([str(c) for c in cmd])
    return p.returncode


def preflight() -> bool:
    print("\n" + "=" * 78)
    print(" t005 —— 2×2 辐射开关对比 (薄驱动: 调用 SNB/SNB 核心模块)")
    print(f" 核心模块: {SNB}")
    print(f" 场景输出: {SCENE}")
    print(f" 图像输出: {IMAGES}")
    print("=" * 78)
    ok = True
    for p in (GEN, RUN, PLOT):
        if not p.exists():
            print(f"  [X] 核心模块脚本缺失: {p}")
            ok = False
    if not (SNB / "source" / "snb_package").is_dir():
        print(f"  [X] 核心模块 source/ 缺失 —— 先跑 import_sources.py")
        ok = False
    for v in (SNB / "variants").glob("*.F90"):
        pass
    if not (SNB / "variants" / "Driver_evolveFlash_radON.F90").exists():
        print(f"  [X] 缺 radON 驱动变体 —— 先跑 tools_local/make_variants.py")
        ok = False
    if ok:
        print("  [OK] 前置检查通过")
    return ok


def main() -> int:
    ap = argparse.ArgumentParser(description="t005: 2×2 辐射开关对比 (薄驱动)")
    ap.add_argument("--stage", choices=["all", "generate", "run", "plot"],
                    default="all")
    ap.add_argument("--tmax", type=float, default=0.8e-9)
    ap.add_argument("--dtmax", type=float, default=2.0e-14,
                    help="★★ 必须 2e-14。判据来自 chk 内 real scalars 的 dt 实测值:"
                         "成功腿 dt 全程钉死 2.000e-14; 若用 2e-12 则 dt 增长到 "
                         "4.6e-14 → SNB 腿非物理崩塌 (本场景实测 ρmax→0.26)。"
                         "详见 SNB/docs/08_故障案例_SNB崩塌.md")
    ap.add_argument("--nxb", type=int, default=128)
    ap.add_argument("--iprocs", type=int, default=8)
    ap.add_argument("--driver-variant", choices=["none", "radon"], default="radon",
                    help="★ SNB 腿驱动源, 必须 radon: 作者原版把 call RadTrans 注释了 "
                         "→ 辐射永不推进、par 三开关失效 (trad 差 1700×), 2×2 失去意义。"
                         "radon 变体恢复该调用后开关才生效。"
                         "(此前 help 曾误称 radon 导致崩塌 —— 该结论已推翻, "
                         "t004 成功跑的就是 radon 驱动)")
    ap.add_argument("--tag", default="full", help="输出命名标记")
    ap.add_argument("--skip-setup", action="store_true")
    ap.add_argument("--skip-make", action="store_true")
    args = ap.parse_args()

    if not preflight():
        return 2

    t0 = time.time()
    rc = 0

    # ── ① 生成场景 (F90 复制 + 2×2 par + 受控性自检) ──────────
    if args.stage in ("all", "generate"):
        rc |= sh([PY, GEN, "--out", SCENE, "--legs", "snb,flsh",
                  "--radiation", "both",
                  "--driver-variant", args.driver_variant,
                  "--nxb", args.nxb, "--iprocs", args.iprocs,
                  "--tmax", args.tmax, "--dtmax", args.dtmax,
                  "--chk-dt", 5.0e-11, "--plt-dt", 4.0e-10,
                  "--verify-keys-against",
                  str(SNB / "source" / "example" / "flash.par")], "generate")
        if rc:
            print("\n[X] 场景生成失败, 中止"); return rc

    # ── ② 跑四条腿 (★ 每侧仅 setup/make 一次: 辐射是纯 par 开关) ──
    if args.stage in ("all", "run"):
        for leg in LEGS:
            first_of_leg = True          # ← 按「侧」而非全局: 两侧树/objdir 不同
            for rad in RADS:
                cmd = [PY, RUN, "--scene", SCENE, "--side", leg,
                       "--par", f"{leg}_{rad}.par", "--tag", rad,
                       "--nxb", args.nxb, "--iprocs", args.iprocs,
                       "--out-root", SCENE / "flash_output"]
                if first_of_leg:
                    # 首条腿: 部署 + setup + make (除非用户显式跳过)
                    if args.skip_setup:
                        cmd.append("--skip-setup")
                    if args.skip_make:
                        cmd.append("--skip-make")
                else:
                    # 同侧后续腿: 复用已编译二进制, 只换 par
                    cmd += ["--skip-deploy", "--skip-setup", "--skip-make"]
                rc |= sh(cmd, f"run_{leg}_{rad}")
                first_of_leg = False
                if rc:
                    print(f"\n[!] {leg}/{rad} 失败, 继续尝试其余腿")

    # ── ③ 出图 + 定量 ────────────────────────────────────────
    if args.stage in ("all", "plot"):
        rc |= sh([PY, PLOT, "--scene", SCENE, "--out", IMAGES,
                  "--tag", args.tag], "plot")
        # 定量表另存一份到 results/
        RESULTS.mkdir(parents=True, exist_ok=True)
        for f in (IMAGES / "ablation").glob("*.csv"):
            (RESULTS / f.name).write_bytes(f.read_bytes())
        for f in (IMAGES / "compare").glob("*.md"):
            (RESULTS / f.name).write_bytes(f.read_bytes())

    print("\n" + "=" * 78)
    print(f" t005 完成 — 耗时 {time.time()-t0:.1f} s, rc={rc}")
    print(f" 图:  {IMAGES}")
    print(f" 表:  {RESULTS}")
    print("=" * 78)
    return rc


if __name__ == "__main__":
    sys.exit(main())
