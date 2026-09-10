"""t002 +ug 分辨率/速度矩阵探针 —— 回答" +ug 只能靠核数提分辨率?"

背景 (源码 Grid/GridMain/UG/Grid_init.F90:186-194)
--------------------------------------------------
    #ifdef FIXEDBLOCKSIZE   (setup 给了 -nxb=N)
        gr_gIndexSize(IAXIS) = iProcs * NXB        → 总格数 = iProcs × nxb
    #else                   (不给 -nxb)
        iGridSize (par)                            → 总格数 = iGridSize
        局部块 = iGridSize / iProcs

  因此分辨率 **不是** 只能靠核数提升:
    * 固定块模式: 核数不变, 只把 -nxb 加倍 → 分辨率加倍;
    * 非固定块模式: iGridSize 直接给定总格数 → 分辨率与核数解耦。
  ("+ug 下 nproc 必须等于 iProcs" 是"一块一进程"的约束, 与分辨率是否可自由
   设定是两回事。)

本探针在 FL-SH 腿上实测 ncell 与墙钟, 全部用 tmax=2e-10 (速度优先)。

用法 (在 t002 目录下):
    python scripts/probe/ug_resolution_probe.py                  # 全部 5 个用例
    python scripts/probe/ug_resolution_probe.py --cases A1,A2,A3
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

_T002 = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_T002 / "common"))
sys.path.insert(0, str(_T002 / "scripts" / "generate"))
sys.path.insert(0, str(_T002 / "scripts" / "run"))

import t002_common as C          # noqa: E402
import gen_t002_inputs as GEN    # noqa: E402
import run_t002 as RT            # noqa: E402

TMAX = "2.0e-10"

# 用例矩阵: (id, 说明, nxb, iprocs, iGridSize, fixed_bs)
CASES: List[Dict[str, Any]] = [
    {"id": "A1", "note": "固定块基线 (与生产配置相同)",
     "nxb": 64, "iprocs": 8, "igs": 0, "fixed": True},
    {"id": "A2", "note": "同 8 核, nxb×2 → 分辨率×2 (关键对照)",
     "nxb": 128, "iprocs": 8, "igs": 0, "fixed": True},
    {"id": "A3", "note": "同 nxb, iprocs×2 (复用 A2 二进制)",
     "nxb": 128, "iprocs": 16, "igs": 0, "fixed": True},
    {"id": "A4", "note": "非固定块 (-nofbs) iGridSize=1024, 8 核",
     "nxb": 0, "iprocs": 8, "igs": 1024, "fixed": False},
    {"id": "A5", "note": "非固定块 (-nofbs) iGridSize=1024, 16 核 (复用 A4 二进制)",
     "nxb": 0, "iprocs": 16, "igs": 1024, "fixed": False},
]


def measure_ncell(outdir: Path) -> Optional[int]:
    """从 plt 实测全局格数 (x 坐标长度)。"""
    files = [p for p in sorted(outdir.glob("*plt_cnt*")) if "forced" not in p.name]
    if not files:
        files = sorted(outdir.glob("*plt_cnt*"))
    if not files:
        return None
    try:
        from flash.output_processors.loader import FlashDataLoader
        import numpy as np
        c = FlashDataLoader(str(files[-1])).load(compute_derived=False)
        return int(np.asarray(c.x).ravel().size)
    except Exception as exc:  # noqa: BLE001
        C.log(f"    格数实测失败: {exc}", "WARN")
        return None


def run_case(case: Dict[str, Any], distro: str, rebuild_ok: bool) -> Dict[str, Any]:
    cid = case["id"]
    print("\n" + "─" * 72)
    print(f" 用例 {cid}: {case['note']}")
    mode = (f"固定块 nxb={case['nxb']} × iProcs={case['iprocs']}"
            if case["fixed"] else
            f"非固定块 iGridSize={case['igs']} × iProcs={case['iprocs']}")
    print(f"   {mode}")
    print("─" * 72)

    # 生成该用例的 par (FL-SH 腿)
    if rebuild_ok:
        GEN.generate("flsh", case["nxb"], case["iprocs"], case["igs"], tmax=float(TMAX))

    tmax = None if rebuild_ok else TMAX
    ok = RT.run_leg("flsh", distro, case["nxb"], case["iprocs"], case["igs"],
                    case["fixed"], tmax, tag=f"probe_{cid}",
                    skip_deploy=False, skip_setup=False, skip_make=False)
    outdir = C.leg_output_dir("flsh") / f"probe_{cid}"
    ncell = measure_ncell(outdir)
    exp = (case["iprocs"] * case["nxb"] if case["fixed"] else case["igs"])
    dx_exp = (C.dx_um(case["nxb"], case["iprocs"]) if case["fixed"]
              else C.dx_um_from_igridsize(case["igs"]))
    dx_meas = ((C.PARAMS["xmax"] - C.PARAMS["xmin"]) / ncell * 1e4
               if ncell else float("nan"))
    wall = "N/A"
    wf = outdir / "walltime.txt"
    if wf.exists():
        lines = [l for l in wf.read_text(encoding="utf-8").splitlines() if l.strip()]
        if lines:
            p = lines[-1].split("\t")
            wall = f"{p[3]} s" if len(p) >= 4 else "N/A"

    res = {"id": cid, "note": case["note"], "mode": mode,
           "nxb": case["nxb"], "iprocs": case["iprocs"], "igs": case["igs"],
           "expected_cells": exp, "measured_cells": ncell,
           "dx_expected_um": dx_exp, "dx_measured_um": dx_meas,
           "wall": wall, "ok": ok}
    C.log(f"预期 {exp} 格 / dx≈{dx_exp:.4f} µm | 实测 "
          f"{ncell if ncell else 'N/A'} 格 / dx≈{dx_meas:.4f} µm | 墙钟 {wall}",
          "OK" if (ok and ncell == exp) else "WARN")
    return res


def _merge_previous(rows: List[Dict[str, Any]], csv_path: Path) -> List[Dict[str, Any]]:
    """与已有 matrix.csv 合并 (按 id 覆盖), 这样可以分批跑 --cases 再汇总。"""
    if not csv_path.exists():
        return rows
    try:
        with csv_path.open("r", encoding="utf-8", newline="\n") as fh:
            old = list(csv.DictReader(fh))
    except Exception:  # noqa: BLE001
        return rows
    if not old:
        return rows
    merged: Dict[str, Dict[str, Any]] = {str(o["id"]): o for o in old}
    for r in rows:
        merged[str(r["id"])] = r
    # 数值字段还原为 int/float, 便于后续格式化
    out: List[Dict[str, Any]] = []
    for k in sorted(merged):
        d = dict(merged[k])
        for key, cast in (("nxb", int), ("iprocs", int), ("igs", int),
                          ("expected_cells", int)):
            try:
                d[key] = cast(float(d[key]))
            except (TypeError, ValueError):
                d[key] = 0
        for key in ("dx_expected_um", "dx_measured_um"):
            try:
                d[key] = float(d[key])
            except (TypeError, ValueError):
                d[key] = float("nan")
        mc = d.get("measured_cells")
        try:
            d["measured_cells"] = int(float(mc))
        except (TypeError, ValueError):
            d["measured_cells"] = None
        if isinstance(d.get("ok"), str):
            d["ok"] = d["ok"].strip().lower() in ("true", "1")
        out.append(d)
    return out


def write_report(rows_in: List[Dict[str, Any]]) -> None:
    outdir = C.RESULT_DIR / "ug_resolution"
    outdir.mkdir(parents=True, exist_ok=True)
    csv_path = outdir / "matrix.csv"
    rows = _merge_previous(rows_in, csv_path)

    with csv_path.open("w", encoding="utf-8", newline="\n") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    lines = [
        "# +ug 均匀网格分辨率机制 —— 实测矩阵",
        "",
        f"生成时间: {C.stamp()}    运行环境: WSL Ubuntu-22.04, 24 核 / 11 GB",
        f"场景: t002 FL-SH 腿      tmax = {TMAX} s",
        "",
        "## 源码机制 (Grid/GridMain/UG/Grid_init.F90:186-194)",
        "",
        "```fortran",
        "#ifdef FIXEDBLOCKSIZE        ! setup 给了 -nxb=N",
        "   gr_gIndexSize(IAXIS) = gr_axisNumProcs(IAXIS) * NXB",
        "#else                        ! 不给 -nxb",
        "   RuntimeParameters_get(\"iGridSize\", gr_gIndexSize(IAXIS))",
        "#endif",
        "```",
        "",
        "UG/Config 明文: `D nblockx number of blocks along X - ignored by UG Grid`;",
        "`D iGridSize ... ONLY needed when running in NON_FIXED_BLOCKSIZE mode`。",
        "",
        "### ★ 关键前提: 非固定块模式必须显式 `-nofbs`",
        "",
        "首次尝试只\"去掉 `-nxb`\" 并在 par 里写 `iGridSize=1024`，实测**无效**：",
        "`iProcs=8 → 64 格`、`iProcs=16 → 128 格`（即 `iProcs×8`，NXB 取了默认值 8），",
        "说明 FLASH 默认仍定义 `FIXEDBLOCKSIZE`，`iGridSize` 被完全忽略。",
        "正确开关是 `-nofbs`（`bin/parseCmd.py:282` → `fixedBlockSize=False`；",
        "`bin/Readme.SetupVars:97`；快捷方式 `nofbs:-nofbs:+ug:parallelIO=True:`）。",
        "注意副作用：`not fixedBlockSize` 会让 `IO/IOMain/hdf5/Config` 强制",
        "`DEFAULT parallel`，且 `parallelIO=False` 直接 SETUPERROR —— 即 `-nofbs`",
        "与串行 HDF5 不兼容。",
        "",
        "## 实测结果",
        "",
        "| 用例 | 模式 | nxb | iProcs | iGridSize | 预期格数 | 实测格数 | dx 预期 [µm] | dx 实测 [µm] | 墙钟 |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| {r['id']} | {'固定块' if r['nxb'] else '非固定块'} | "
            f"{r['nxb'] or '-'} | {r['iprocs']} | {r['igs'] or '-'} | "
            f"{r['expected_cells']} | {r['measured_cells'] or 'N/A'} | "
            f"{r['dx_expected_um']:.4f} | {r['dx_measured_um']:.4f} | {r['wall']} |")
    lines += ["", "## 结论", ""]
    for r in rows:
        lines.append(f"- **{r['id']}** ({r['note']}): {r['mode']} → "
                     f"实测 {r['measured_cells']} 格, dx≈{r['dx_measured_um']:.4f} µm, "
                     f"墙钟 {r['wall']}")
    a1 = next((r for r in rows if r["id"] == "A1"), None)
    a2 = next((r for r in rows if r["id"] == "A2"), None)
    a4 = next((r for r in rows if r["id"] == "A4"), None)
    a5 = next((r for r in rows if r["id"] == "A5"), None)
    lines += ["", "### 判读", ""]
    if a1 and a2 and a1["measured_cells"] and a2["measured_cells"]:
        ratio = a2["measured_cells"] / a1["measured_cells"]
        lines.append(
            f"1. **核数不变、只把 `-nxb` 从 {a1['nxb']} 提到 {a2['nxb']}**：格数 "
            f"{a1['measured_cells']} → {a2['measured_cells']} (×{ratio:.2f}), "
            f"dx {a1['dx_measured_um']:.4f} → {a2['dx_measured_um']:.4f} µm "
            f"→ 分辨率**与核数无关**，`-nxb` 是独立旋钮。")
    if a4 and a5:
        same = (a4["measured_cells"] == a5["measured_cells"])
        lines.append(
            f"2. **非固定块模式 `iGridSize={a4['igs']}`**：8 核 → "
            f"{a4['measured_cells']} 格, 16 核 → {a5['measured_cells']} 格 "
            f"({'分辨率不变' if same else '分辨率变化'}) → "
            f"{'总格数由 iGridSize 直接给定，与核数完全解耦' if same else '异常, 需复查'}。")
    lines.append(
        "3. 因此旧结论「SNB 分辨率只能靠 iProcs 提升 / 不存在固定分辨率扫核数」"
        "**只在固定块模式且不动 `-nxb` 时成立**：固定块模式下 `-nxb` 本身就是"
        "独立分辨率旋钮；改用 `-nofbs` 并给 `iGridSize` 后，分辨率与核数完全解耦。")
    lines += ["",
              "> 注意 1: UG 是「一块一进程」，因此 `nproc` 必须严格等于 `iProcs`；"
              "这与「分辨率是否可自由设定」是两个独立约束。",
              "> 注意 2: `-nofbs` 会强制并行 HDF5 IO，与 `+serialIO`/`parallelIO=False` "
              "冲突（setup 直接报错）。",
              ""]
    (outdir / "matrix.md").write_text("\n".join(lines) + "\n",
                                      encoding="utf-8", newline="\n")
    C.log(f"报告: {outdir/'matrix.md'}", "OK")
    C.log(f"CSV : {outdir/'matrix.csv'}", "OK")


def main() -> int:
    ap = argparse.ArgumentParser(description="t002 +ug 分辨率/速度矩阵探针")
    ap.add_argument("--cases", default=None,
                    help="逗号分隔用例 id 子集, 如 A1,A2,A3 (默认全部)")
    ap.add_argument("--distro", default="Ubuntu-22.04")
    args = ap.parse_args()

    want = None
    if args.cases:
        want = {c.strip().upper() for c in args.cases.split(",") if c.strip()}

    print("\n" + "=" * 72)
    print(f" t002 +ug 分辨率/速度矩阵探针   tmax={TMAX} s   {C.stamp()}")
    print("=" * 72)

    rows: List[Dict[str, Any]] = []
    for case in CASES:
        if want and case["id"] not in want:
            continue
        rows.append(run_case(case, args.distro, rebuild_ok=True))

    if rows:
        write_report(rows)
        print("\n  汇总:")
        print("  用例 | 模式        | nxb | iprocs | 预期格数 | 实测格数 | dx[µm]  | 墙钟")
        print("  -----+-------------+-----+--------+----------+----------+---------+-------")
        for r in rows:
            print(f"  {r['id']:<4} | {'固定块' if r['nxb'] else '非固定块':<11} | "
                  f"{str(r['nxb'] or '-'):>3} | {r['iprocs']:>6} | "
                  f"{r['expected_cells']:>8} | {str(r['measured_cells'] or 'N/A'):>8} | "
                  f"{r['dx_measured_um']:>7.4f} | {r['wall']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
