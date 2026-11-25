"""下载四个 1.6ns 作业的 sbatch 脚本与 .out 日志到报告目录。"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO))
from flash.flash_run.remote.session import RemoteSession

BASE = ("/publicfs01/fs1-e/home/scfa2696/PhySimX/PhySimX/simulation/flash/"
        "flash_sim/flash_logs")
REPORTS = (REPO / "flash" / "scenarios" / "private" / "Sandwich" / "TxN" /
           "SandwichTxN_reports")
JOBS = {
    "SandwichTxN_cartesian2d": ("950001", 4971782),
    "SandwichTxN_cartesian2d_one": ("950002", 4971784),
    "SandwichTxN_cylindrical2d": ("950003", 4971785),
    "SandwichTxN_cylindrical2d_one": ("950004", 4971787),
}


def main() -> None:
    with RemoteSession(verbose=False) as s:
        for scene, (rid, jid) in JOBS.items():
            remote_dir = f"{BASE}/{scene}/{rid}"
            local_dir = REPORTS / scene / rid
            local_dir.mkdir(parents=True, exist_ok=True)
            out, _, _ = s.run(f"ls -1 {remote_dir}", timeout=60)
            names = [n.strip() for n in (out or "").splitlines()
                     if n.strip().endswith(".sh") or n.strip().endswith(f"_{jid}.out")]
            for name in names:
                local = local_dir / name
                if local.is_file():
                    continue
                ok = s.download(f"{remote_dir}/{name}", str(local))
                print(f"[{scene}] {name}: {'OK' if ok else 'FAIL'}")


if __name__ == "__main__":
    main()
