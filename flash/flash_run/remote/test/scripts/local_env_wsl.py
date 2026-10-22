#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""local_env_wsl.py — Step 01b: 本地 WSL 环境建造 + 自检（在线模式，Linux 路径预演）。

职责：
  1. 在 WSL 内调用仓库根 start_flash.py（在线模式）→ 建 .venv-linux
     ★ WSL python3 = 3.10.12，与超算 python/3.10.8 同为 3.10 系列，
       是远端安装路径（bin/python、平台分叉、ensurepip 行为）最忠实的预演。
  2. 流式输出到 logs/01b_wsl_<ts>.log
  3. 完成后独立验证: .venv-linux/bin/python -c "import flash, yt, numpy, h5py, pytest"

报错处理：不在此脚本内恢复 —— 按「逐项恢复策略」定位后重跑本脚本。
"""
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEST_DIR = HERE.parent
REPO_ROOT = TEST_DIR.parents[3]
LOG_DIR = TEST_DIR / "logs"


def wsl_posix(repo_root: Path) -> str:
    """E:\\... -> /mnt/e/..."""
    drive = repo_root.drive.rstrip(":").lower()
    tail = str(repo_root)[len(repo_root.drive):].replace("\\", "/")
    return f"/mnt/{drive}{tail}"


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true",
                    help="离线模式（复刻超算安装路径）: --offline --wheelhouse <wheelhouse-linux>")
    ap.add_argument("--wheelhouse", default=None,
                    help="wheelhouse 目录（默认 test/packages/wheelhouse-linux）")
    args = ap.parse_args()

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = LOG_DIR / f"01b_wsl_{ts}.log"

    posix = wsl_posix(REPO_ROOT)
    venv_dir = f"{posix}/.venv-linux"
    print(f"[01b] repo root (wsl): {posix}")
    print(f"[01b] venv           : {venv_dir}（命名环境）")
    print(f"[01b] log            : {log_path}")

    # 先探测 WSL python3 版本
    p = subprocess.run(["wsl", "bash", "-c", "python3 --version"],
                       capture_output=True, text=True, timeout=60)
    print(f"[01b] WSL python3    : {(p.stdout or p.stderr).strip()}")

    if args.offline:
        wh_posix = args.wheelhouse or f"{wsl_posix(TEST_DIR)}/packages/wheelhouse-linux"
        start_flags = f"--offline --wheelhouse '{wh_posix}'"
        env_line = f"PYTHONUNBUFFERED=1 FLASH_VENV_DIR='{venv_dir}'"
        print(f"[01b] 模式           : 离线（★ 复刻超算安装路径）wheelhouse={wh_posix}")
    else:
        start_flags = ""
        env_line = f"PYTHONUNBUFFERED=1 FLASH_FORCE_ONLINE=1 FLASH_VENV_DIR='{venv_dir}'"
        print("[01b] 模式           : 在线")

    inner = (
        f"cd '{posix}' && "
        f"{env_line} python3 start_flash.py {start_flags}"
    )
    log_f = open(log_path, "w", encoding="utf-8", errors="replace")
    proc = subprocess.Popen(["wsl", "bash", "-c", inner],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, encoding="utf-8", errors="replace", bufsize=1)
    assert proc.stdout is not None
    for line in proc.stdout:
        log_f.write(line)
        print("  | " + line.rstrip())
    proc.wait()
    log_f.close()
    rc = proc.returncode
    print(f"[01b] start_flash.py (WSL) 退出码: {rc}")

    # ---- 独立验证 ----
    verify = (f"'{venv_dir}/bin/python' -c "
              "\"import flash, numpy, h5py, pytest, yt; "
              "import flash as f; print('flash file:', f.__file__)\"")
    r = subprocess.run(["wsl", "bash", "-c", verify],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=300)
    verify_ok = r.returncode == 0
    print(f"[01b] 独立验证 import flash/yt: {'OK' if verify_ok else 'FAIL'}")
    if not verify_ok:
        print((r.stdout or "")[-500:]); print((r.stderr or "")[-800:])

    report = f"{posix}/test/reports/INSTALL_TEST_REPORT.txt"
    chk = subprocess.run(["wsl", "bash", "-c", f"test -f '{report}' && echo EXISTS || echo MISSING"],
                         capture_output=True, text=True, timeout=60)
    print(f"[01b] 报告: {report}（{chk.stdout.strip()}）")
    print(f"[01b] 结论: {'PASS' if rc == 0 and verify_ok else 'FAIL'}")
    return 0 if (rc == 0 and verify_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
