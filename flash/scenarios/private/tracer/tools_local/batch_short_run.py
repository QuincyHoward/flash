#!/usr/bin/env python
"""批量极短重算 (tmax=1e-11) —— 逐个真实跑 FLASH 并核对实际生效物性.

为什么需要它
------------
par 生成正确 ≠ FLASH 接受。只有真跑一次才能暴露：
  * setup/编译失败 (物种数、MGD 群结构、缺表)
  * par 里未注册的参数、类型错误 (整数写成浮点会 abort)
  * 物性是否真的进了 EOS (ms_*A/Z 反算 abar/Ye)

判据 (每个场景三条同时满足才算 PASS)
------------------------------------
  1. 进程 exit 0, 日志无 "aborting"
  2. 产出 chk_0000
  3. chk 的 `real runtime parameters` 里, ms_<sp>A/Z 与生成的 .par 逐项一致
     —— 这是 FLASH **实际加载**的值, 比看 par 文本可信。

用法
----
    python batch_short_run.py                  # 跑默认待验证清单
    python batch_short_run.py --only VTi3      # 只跑名字匹配的场景
    python batch_short_run.py --tmax 1e-11     # 覆盖 tmax
输出: batch_short_run.csv + batch_short_run.log (本目录)
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]          # .../tracer
PROJ = Path(__file__).resolve().parents[5]          # .../layer3/flash (含 .venv)
PY = PROJ / ".venv" / "Scripts" / "python.exe"

# 已在本轮单独验证过的不再重复 (TiTi1/VTi1 已 exit 0 且读数已核对)
DEFAULT_TARGETS = [
    "TiTi/TiTi2.py", "TiTi/TiTi3.py",
    "VTi/VTi2.py", "VTi/VTi3.py",
    "CHTi/CHTi1.py", "CHTi/CHTi2.py", "CHTi/CHTi3.py",
    "CHTi_F/CHTi1_F.py", "CHTi_F/CHTi2_F.py", "CHTi_F/CHTi3_F.py",
    "VCH_ml/VCH_ml.py", "VCH_ml_F/VCH_ml_F.py",
    "OneCH_ml/OneCH_ml.py", "OneC_ml/OneC_ml.py", "OneC_ml_F/OneC_ml_F.py",
    "OneSi_ml/OneSi_ml.py", "OneSi_ml_F/OneSi_ml_F.py",
    "SNB/SNBOneCH_m/SNBOneCH_m.py", "SNB/SNBOneCH_ml/SNBOneCH_ml.py",
    "SNB/SNBVTi1um/SNBVTi1um.py", "SNB/SNBVTi2/SNBVTi2.py",
    "SNB/SNBVTi2_ml/SNBVTi2_ml.py", "SNB/SNBVTi2um/SNBVTi2um.py",
    "SNB/SNBVTi3um/SNBVTi3um.py",
    "Au/VAuTi/VAuTi.py",
]


def load_par(p: Path) -> dict:
    """解析 .par 为 {key: str}（只切引号外的 #）。"""
    sys.path.insert(0, str(PROJ))
    from flash.input_gen.gen_checker.relations._parsers import (
        strip_par_comment, unquote,
    )
    d = {}
    for ln in p.read_text(encoding="utf-8", errors="replace").splitlines():
        s = strip_par_comment(ln).strip()
        if not s or s.startswith("#"):
            continue
        m = re.match(r"^([A-Za-z_]\w*)\s*=\s*(.*)$", s)
        if m:
            d[m.group(1)] = unquote(m.group(2)).strip()
    return d


def read_runtime_params(chk: Path) -> dict:
    """读 chk 的 real runtime parameters -> {小写名: float}。"""
    import h5py
    with h5py.File(chk, "r") as f:
        if "real runtime parameters" not in f:
            return {}
        rp = f["real runtime parameters"][:]
    names = [n.decode().strip() for n in rp["name"]]
    return {n.lower(): float(v) for n, v in zip(names, rp["value"])}


def find_newest_chk(scene_dir: Path, after: float | None = None) -> Path | None:
    """定位**本次运行**产出的 chk_0000。

    ★ 三种布局并存（踩过）：
      (a) flash_output/outputfiles/run_NNNNNN/*chk_0000  —— runner 的统一收集布局
      (b) flash_output/outputfiles/*chk_0000             —— 未分 run 的旧布局
      (c) flash_output/*chk_0000                         —— SNB 家族自定义输出目录
        （run_flash.sh 里 COLLECT 直接指向 flash_output，不经 outputfiles/）

    ★★ 2026-10-21 严重教训（VAuTi 假阳性）：
      不加 `after` 过滤时，场景跑挂（FLASH exit 139 段错误）仍会被判 PASS ——
      因为目录里躺着上次运行留下的 chk_0000，被当成本次产物读走了。
      ⇒ 必须传入"本次启动前的时间戳"，只接受更新的文件。
    """
    for pat in ("flash_output/outputfiles/run_*/*chk_0000",
                "flash_output/outputfiles/*chk_0000",
                "flash_output/*chk_0000"):
        cands = [p for p in scene_dir.glob(pat)
                 if after is None or p.stat().st_mtime >= after]
        if cands:
            return max(cands, key=lambda p: p.stat().st_mtime)
    return None


def find_newest_par(scene_dir: Path) -> Path | None:
    cands = sorted(scene_dir.glob("flash_input/run_*/*.par"),
                   key=lambda p: p.stat().st_mtime, reverse=True)
    if cands:
        return cands[0]
    cands = sorted(scene_dir.glob("flash_input/*.par"),
                   key=lambda p: p.stat().st_mtime, reverse=True)
    return cands[0] if cands else None


def run_one(rel: str, tmax: float, nproc: int | None = None) -> dict:
    script = ROOT / rel
    scene_dir = script.parent
    name = script.stem
    row = {"scene": rel, "rc": "", "chk": "", "n_species": "",
           "material_ok": "", "mismatch": "", "seconds": "", "note": ""}

    env = dict(os.environ)
    env["RUN_MODE"] = "wsl"
    env.setdefault("PYTHONIOENCODING", "utf-8")

    cmd = [str(PY), str(script), "--tmax", f"{tmax:g}"]
    if nproc:
        # ★ SNB 场景的 config_constants 里 nprocs=131（超算配置）。直接跑会
        #   在 24 核机器上 131 进程超订 —— 实测 36 分钟只推进 4 步
        #   （t=4.6e-15，目标 1e-11），几乎等于挂死。
        #   必须用 --nproc 同步改 par 的 iProcs 与 mpiexec -n，两者不等会
        #   Logfile_open io_status=29 + MPI_Abort（+ug 铁律）。
        cmd += ["--nproc", str(nproc)]

    t0 = time.time()
    started = t0 - 1.0          # 略微回退，容忍文件系统时间戳粒度
    proc = subprocess.run(
        cmd, cwd=str(PROJ), env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    row["seconds"] = f"{time.time() - t0:.0f}"
    out = proc.stdout.decode("utf-8", errors="replace")
    row["rc"] = proc.returncode

    chk = find_newest_chk(scene_dir, after=started)
    if chk is None:
        row["material_ok"] = "NO_CHK"
        tail = [l for l in out.splitlines() if "ERROR" in l or "abort" in l.lower()][-3:]
        row["note"] = " | ".join(tail)[:300]
        return row
    row["chk"] = str(chk.relative_to(ROOT)).replace("\\", "/")

    par = find_newest_par(scene_dir)
    if par is None:
        row["material_ok"] = "NO_PAR"
        return row
    parv = load_par(par)
    rtv = read_runtime_params(chk)

    # 逐物种核对 ms_<sp>A / ms_<sp>Z / sim_rho<Cap>
    species = sorted({m.group(1) for m in re.finditer(r"^ms_(\w+?)A$", "\n".join(parv), re.M)})
    row["n_species"] = len(species)
    bad = []
    for sp in species:
        for key in (f"ms_{sp}A", f"ms_{sp}Z"):
            if key not in parv:
                continue
            try:
                want = float(parv[key])
            except ValueError:
                continue
            got = rtv.get(key.lower())
            if got is None:
                bad.append(f"{key}: FLASH 未加载")
            elif abs(want - got) > 1e-9 * max(1.0, abs(want)):
                bad.append(f"{key}: par={want:g} vs FLASH={got:g}")
        cap = f"sim_rho{sp.capitalize()}"
        if cap in parv:
            try:
                want = float(parv[cap])
                got = rtv.get(cap.lower())
                if got is None:
                    bad.append(f"{cap}: FLASH 未加载")
                elif abs(want - got) > 1e-9 * max(1.0, abs(want)):
                    bad.append(f"{cap}: par={want:g} vs FLASH={got:g}")
            except ValueError:
                pass

    row["material_ok"] = "PASS" if not bad else "FAIL"
    row["mismatch"] = "; ".join(bad[:6])[:400]
    return row


def main() -> int:
    ap = argparse.ArgumentParser(description="批量极短重算并核对实际生效物性")
    ap.add_argument("--tmax", type=float, default=1e-11)
    ap.add_argument("--nproc", type=int, default=None,
                    help="SNB 场景的 MPI 进程数（覆盖 par 的 iProcs 与 mpiexec -n）；"
                         "不传则沿用场景自带值（SNB 为 131，仅适合超算）")
    ap.add_argument("--only", default=None, help="只跑名字含该子串的场景")
    ap.add_argument("--list", default=None, help="JSON 清单文件 (默认内置 25 个)")
    ap.add_argument("--out", default=None,
                    help="输出 CSV 路径（默认 batch_short_run.csv；分批跑时用不同文件名避免覆盖）")
    ap.add_argument("--include-snb", action="store_true",
                    help="也跑 SNB 场景（默认跳过：SNB 的 nprocs 是超算配置，"
                         "本地会严重超订；请改用 <场景>.py all --account flash_ssh --tmax 1e-11）")
    args = ap.parse_args()

    targets = DEFAULT_TARGETS
    if args.list:
        targets = json.loads(Path(args.list).read_text(encoding="utf-8"))
    if args.only:
        targets = [t for t in targets if args.only.lower() in t.lower()]

    # ★ 2026-10-21: SNB 场景默认**不在本地跑**（用户定案）。
    #   实测: SNBOneCH_m 的 nprocs=131、SNBVTi*=125 都是超算配置，本机 24 核上
    #   131 进程 36 min 只推进 4 步，而 24 进程 75 步仅 52 s。且 SNBVTi* 的
    #   精确网格 (iProcs×nxb=25000 → dx=0.02um) 不容许随便改核数。
    #   ⇒ SNB 的极短验证走 `python <SNB场景>.py all --account flash_ssh --tmax 1e-11`。
    if not args.include_snb:
        skipped = [t for t in targets if t.startswith("SNB/")]
        targets = [t for t in targets if not t.startswith("SNB/")]
        if skipped:
            print(f"[skip] SNB 场景 {len(skipped)} 个默认走超算（本次不在本地跑）：",
                  flush=True)
            for t in skipped:
                print(f"         {t}", flush=True)

    out_csv = Path(args.out) if args.out else Path(__file__).with_name("batch_short_run.csv")
    rows = []
    print(f"待验证 {len(targets)} 个场景, tmax={args.tmax:g} s", flush=True)
    for i, rel in enumerate(targets, 1):
        print(f"\n[{i}/{len(targets)}] {rel} ...", flush=True)
        try:
            npr = args.nproc if (args.nproc and rel.startswith("SNB/")) else None
            row = run_one(rel, args.tmax, nproc=npr)
        except Exception as e:  # noqa: BLE001
            row = {"scene": rel, "rc": "", "chk": "", "n_species": "",
                   "material_ok": f"ERROR:{type(e).__name__}", "mismatch": str(e)[:200],
                   "seconds": "", "note": ""}
        rows.append(row)
        print(f"    rc={row['rc']} chk={'Y' if row['chk'] else 'N'} "
              f"species={row['n_species']} material={row['material_ok']} "
              f"({row['seconds']}s) {row['mismatch']}", flush=True)
        with out_csv.open("w", encoding="utf-8-sig", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)

    print("\n" + "=" * 70)
    ok = [r for r in rows if r["material_ok"] == "PASS"]
    print(f"PASS {len(ok)} / {len(rows)}")
    for r in rows:
        if r["material_ok"] != "PASS":
            print(f"  !! {r['scene']}: {r['material_ok']} {r['mismatch'] or r['note']}")
    print(f"CSV -> {out_csv}")
    return 0 if len(ok) == len(rows) else 1


if __name__ == "__main__":
    sys.exit(main())
