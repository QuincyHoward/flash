"""汇总四个二维场景 HPC 短跑结果：depo 空间范围、日志参数回显、健康检查。"""

from __future__ import annotations

import json
import re
from pathlib import Path

import h5py
import numpy as np

REPO = Path(__file__).resolve().parent.parent.parent
ROOT = REPO / "flash" / "scenarios" / "private" / "Sandwich" / "TxN" / "hpc_results"
REPORTS = REPO / "flash" / "scenarios" / "private" / "Sandwich" / "TxN" / "SandwichTxN_reports"
RUNS = {
    "SandwichTxN_cartesian2d": "940005",
    "SandwichTxN_cartesian2d_one": "940002",
    "SandwichTxN_cylindrical2d": "940006",
    "SandwichTxN_cylindrical2d_one": "940004",
}
JOBS = {
    "SandwichTxN_cartesian2d": (4971744, 48, "00:04:06"),
    "SandwichTxN_cartesian2d_one": (4971736, 48, "00:03:02"),
    "SandwichTxN_cylindrical2d": (4971746, 48, "00:03:51"),
    "SandwichTxN_cylindrical2d_one": (4971740, 48, "00:03:26"),
}


def depo_summary(path: Path) -> dict:
    with h5py.File(path, "r") as fh:
        d = np.asarray(fh["depo"][:, 0], dtype=float)
        b = np.asarray(fh["bounding box"][:], dtype=float)
    nb, ny, nx = d.shape
    xs = np.array([b[k, 0, 0] + (np.arange(nx) + 0.5) * (b[k, 0, 1] - b[k, 0, 0]) / nx
                   for k in range(nb)])
    ys = np.array([b[k, 1, 0] + (np.arange(ny) + 0.5) * (b[k, 1, 1] - b[k, 1, 0]) / ny
                   for k in range(nb)])
    X = xs[:, None, :] * np.ones((1, ny, 1))
    Y = ys[:, :, None] * np.ones((1, 1, nx))
    m = d > 0.01 * d.max()
    return {
        "max": float(d.max()),
        "blocks": nb,
        "nonzero_cells": int(np.count_nonzero(d)),
        "strong_cells": int(m.sum()),
        "strong_um": {
            "transverse": [float(X[m].min() * 1e4), float(X[m].max() * 1e4)],
            "axial": [float(Y[m].min() * 1e4), float(Y[m].max() * 1e4)],
        },
    }


def log_summary(path: Path) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace")
    def grab(pat: str, default: str = "?") -> str:
        m = re.search(pat, text, re.M)
        return m.group(1).strip() if m else default
    return {
        "geometry": grab(r"^geometry\s+=\s+(\S+)"),
        "beams": int(grab(r"^ed_numberofbeams\s+=\s+(\d+)", "0")),
        "3din2d": grab(r"^ed_laser3din2d\s+=\s+(\S+)"),
        "peak_ed_power": grab(r"^ed_power_1_2\s+=\s+(\S+)"),
        "complete": "LOGFILE_END: FLASH run complete." in text,
    }


def main() -> None:
    out = []
    for scene, rid in RUNS.items():
        d = ROOT / scene / rid
        chk = d / "lasslab_hdf5_chk_0001"
        log = d / "lasslab.log"
        job_id, ntasks, elapsed = JOBS[scene]
        rec = {
            "scene": scene,
            "run_id": rid,
            "job_id": job_id,
            "ntasks": ntasks,
            "elapsed": elapsed,
            "chk_mb": round(chk.stat().st_size / 1e6, 1),
            **depo_summary(chk),
            **log_summary(log),
        }
        out.append(rec)
        print(json.dumps(rec, ensure_ascii=False))
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "hpc_summary.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
