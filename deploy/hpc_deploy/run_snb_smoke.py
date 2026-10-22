#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""run_snb_smoke.py — Step 07: SNBOneCH_m 极短仿真验证（本地驱动，超算执行）。

★ 标准命令（核实版，SNBOneCH_m 无 all 子命令）:
  python flash/scenarios/private/tracer/SNB/SNBOneCH_m/SNBOneCH_m.py \
      --mode hpc --account flash_ssh --tmax 1.0e-11

驱动端在**本地**（需要本地 ~/.physimx/flash/credentials.enc + RemoteSession）；
超算侧用已部署的 SNB 树 ~/QC/FLASH/FLASHSNB/FLASH4.8。
全程单场景串行；PYTHONUNBUFFERED=1；产物回收到 results/snb_smoke_<ts>/。
"""
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ARTIFACTS = HERE.parents[1] / "artifacts"      # 根目录统一产物区
TEST_DIR = ARTIFACTS / "logs" / "hpc_deploy"    # 兼容旧名: logs/packages/results 统一落 artifacts
REPO_ROOT = HERE.parents[1]
LOG_DIR = TEST_DIR / "logs"
RESULTS_DIR = TEST_DIR / "results"

SCENARIO = REPO_ROOT / "flash" / "scenarios" / "private" / "tracer" / "SNB" / \
    "SNBOneCH_m" / "SNBOneCH_m.py"

VENV_PY = REPO_ROOT / ".venv" / "Scripts" / "python.exe"


def main() -> int:
    if not SCENARIO.is_file():
        print(f"[FATAL] 场景脚本不存在: {SCENARIO}")
        return 1
    py = str(VENV_PY if VENV_PY.is_file() else sys.executable)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = LOG_DIR / f"07_snb_smoke_{ts}.log"
    out_dir = RESULTS_DIR / f"snb_smoke_{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)

    cmd = [py, str(SCENARIO), "--mode", "hpc", "--account", "flash_ssh",
           "--tmax", "1.0e-11"]
    print(f"[07] 标准验证命令（tmax=1e-11，sbatch 提交 + 作业轮询 + chk 回收）:")
    print(f"     {' '.join(cmd)}")
    print(f"[07] 日志: {log_path}")

    t0 = time.time()
    log_f = open(log_path, "w", encoding="utf-8", errors="replace")
    proc = subprocess.Popen(cmd, cwd=str(REPO_ROOT),
                            env={"PYTHONUNBUFFERED": "1", **dict(__import__("os").environ)},
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, encoding="utf-8", errors="replace", bufsize=1)
    assert proc.stdout is not None
    for line in proc.stdout:
        log_f.write(line)
        print("  | " + line.rstrip()[:200])
    proc.wait()
    log_f.close()
    rc = proc.returncode
    print(f"[07] 驱动退出码: {rc}（耗时 {time.time() - t0:.0f}s）")

    # 产物清点
    n_h5 = len(list(out_dir.rglob("*.h5"))) if out_dir.exists() else 0
    n_png = len(list(out_dir.rglob("*.png"))) if out_dir.exists() else 0
    print(f"[07] 回收产物: h5={n_h5} png={n_png} -> {out_dir}")
    print(f"[07] 结论: {'PASS' if rc == 0 else 'FAIL'}")
    return 0 if rc == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
