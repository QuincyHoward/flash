#!/usr/bin/env python
"""汇总 27 个场景的极短验证矩阵 -> final_validation_matrix.csv

判据（三选三才算 PASS）:
  1. 有 chk_0000（说明 setup/编译/运行都走完）
  2. chk 的 real runtime parameters 里 ms_<sp>A/Z、sim_rho<sp> 与生成的 .par 一致
  3. 记录执行位置（local WSL / hpc）
全部数值从 chk 现读，不依赖任何手工记录 —— 这是 FLASH **实际加载**的值。
"""
from __future__ import annotations
import csv
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[5]))
import h5py  # noqa: E402
from flash.input_gen.gen_checker.relations._parsers import (  # noqa: E402
    strip_par_comment, unquote,
)

ROOT = Path(__file__).resolve().parents[1]

SCENES = [
    "TiTi/TiTi1.py", "TiTi/TiTi2.py", "TiTi/TiTi3.py",
    "VTi/VTi1.py", "VTi/VTi2.py", "VTi/VTi3.py",
    "CHTi/CHTi1.py", "CHTi/CHTi2.py", "CHTi/CHTi3.py",
    "CHTi_F/CHTi1_F.py", "CHTi_F/CHTi2_F.py", "CHTi_F/CHTi3_F.py",
    "VCH_ml/VCH_ml.py", "VCH_ml_F/VCH_ml_F.py",
    "OneCH_ml/OneCH_ml.py", "OneC_ml/OneC_ml.py", "OneC_ml_F/OneC_ml_F.py",
    "OneSi_ml/OneSi_ml.py", "OneSi_ml_F/OneSi_ml_F.py",
    "Au/VAuTi/VAuTi.py",
    "SNB/SNBOneCH_m/SNBOneCH_m.py", "SNB/SNBOneCH_ml/SNBOneCH_ml.py",
    "SNB/SNBVTi1um/SNBVTi1um.py", "SNB/SNBVTi2/SNBVTi2.py",
    "SNB/SNBVTi2_ml/SNBVTi2_ml.py", "SNB/SNBVTi2um/SNBVTi2um.py",
    "SNB/SNBVTi3um/SNBVTi3um.py",
]

PATTERNS = (
    "flash_output/hpc_*/*chk_0000",           # 超算收集
    "flash_output/outputfiles/run_*/*chk_0000",  # WSL runner 统一布局
    "flash_output/outputfiles/*chk_0000",
    "flash_output/*chk_0000",                 # SNB 家族自定义布局
)


def newest_chk(scene: Path) -> Path | None:
    best = None
    for pat in PATTERNS:
        for p in scene.glob(pat):
            if best is None or p.stat().st_mtime > best.stat().st_mtime:
                best = p
    return best


def newest_par(scene: Path) -> Path | None:
    cands = list(scene.glob("flash_input/run_*/*.par")) + list(scene.glob("flash_input/*.par"))
    return max(cands, key=lambda p: p.stat().st_mtime) if cands else None


def load_par(p: Path) -> dict:
    d = {}
    for ln in p.read_text(encoding="utf-8", errors="replace").splitlines():
        s = strip_par_comment(ln).strip()
        if not s or s.startswith("#"):
            continue
        m = re.match(r"^([A-Za-z_]\w*)\s*=\s*(.*)$", s)
        if m:
            d[m.group(1)] = unquote(m.group(2)).strip()
    return d


def main() -> int:
    rows = []
    for rel in SCENES:
        scene = ROOT / rel
        stem = scene.stem
        row = dict(scene=rel, where="", species="", shld=f"", rho_shld="",
                   ti_layer="", status="", note="")
        chk = newest_chk(scene.parent)
        par = newest_par(scene.parent)
        if chk is None:
            row["status"] = "NO_CHK"
            rows.append(row)
            continue
        row["where"] = "hpc" if "hpc_" in str(chk) else "local"
        with h5py.File(chk, "r") as f:
            rp = f["real runtime parameters"][:]
        rt = {n.decode().strip().lower(): float(v) for n, v in zip(rp["name"], rp["value"])}
        parv = load_par(par) if par else {}

        species = sorted({m.group(1) for m in re.finditer(r"^ms_(\w+?)A$", "\n".join(parv), re.M)})
        row["species"] = len(species)
        bad = []
        for sp in species:
            for key in (f"ms_{sp}A", f"ms_{sp}Z", f"sim_rho{sp.capitalize()}"):
                if key not in parv:
                    continue
                try:
                    want = float(parv[key])
                except ValueError:
                    continue
                got = rt.get(key.lower())
                if got is None or abs(want - got) > 1e-9 * max(1.0, abs(want)):
                    bad.append(key)
        row["shld"] = f'{rt.get("ms_shlda", float("nan")):g}/{rt.get("ms_shldz", float("nan")):g}'
        row["rho_shld"] = f'{rt.get("sim_rhoshld", float("nan")):g}'
        ti = [k for k in sorted(rt) if k.startswith("ms_tar") and k.endswith("a")
              and abs(rt[k] - 47.867) < 1e-6]
        row["ti_layer"] = ",".join(k[3:-1] for k in ti) or "-"
        row["status"] = "PASS" if not bad else "FAIL"
        row["note"] = ",".join(bad[:4])
        rows.append(row)

    out = Path(__file__).with_name("final_validation_matrix.csv")
    with out.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    ok = [r for r in rows if r["status"] == "PASS"]
    print(f"{'scene':34s} {'位置':5s} {'物种':4s} {'shld A/Z':14s} {'rho':6s} {'Ti层':6s} 状态")
    for r in rows:
        print(f"{r['scene']:34s} {r['where']:5s} {str(r['species']):4s} "
              f"{r['shld']:14s} {r['rho_shld']:6s} {r['ti_layer']:6s} {r['status']} {r['note']}")
    print(f"\nPASS {len(ok)} / {len(rows)}   ->  {out}")
    return 0 if len(ok) == len(rows) else 1


if __name__ == "__main__":
    sys.exit(main())
