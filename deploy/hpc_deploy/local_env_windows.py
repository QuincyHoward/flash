#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""local_env_windows.py — Step 01a: 本地 Windows 环境建造 + 自检（在线模式）。

职责：
  1. 调用仓库根 start_flash.py（在线模式）→ 建/复用 .venv-win（或兼容旧 .venv）
  2. 流式输出到 logs/01a_windows_<ts>.log
  3. 完成后独立验证: venv python -c "import flash, yt, numpy, h5py, pytest"

报错处理：不在此脚本内恢复 —— 按「逐项恢复策略」人工/编排层定位后重跑本脚本
（start_flash.py 自带健康检查自愈；本脚本只做外层验证）。
"""
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent          # .../deploy/hpc_deploy
ARTIFACTS = HERE.parents[1] / "artifacts"      # 根目录统一产物区
TEST_DIR = ARTIFACTS / "logs" / "hpc_deploy"    # 兼容旧名: logs/packages/results 统一落 artifacts
REPO_ROOT = HERE.parents[1]
LOG_DIR = TEST_DIR / "logs"


def _managed_python() -> Path:
    """WorkBuddy 托管 Python（用户名无关，统一入口 flash/_core/paths.py）。"""
    import sys as _sys
    sys.path.insert(0, str(REPO_ROOT))
    from flash._core.paths import managed_python
    return managed_python()


def pick_base_python() -> str:
    py = _managed_python()
    if py.is_file():
        return str(py)
    return sys.executable


def find_venv_python() -> Path:
    for cand in (REPO_ROOT / ".venv-win" / "Scripts" / "python.exe",
                 REPO_ROOT / ".venv" / "Scripts" / "python.exe"):
        if cand.is_file():
            return cand
    raise SystemExit("[FATAL] 未找到 Windows venv 解释器（.venv-win/.venv）")


def main() -> int:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = LOG_DIR / f"01a_windows_{ts}.log"

    base_py = pick_base_python()
    start_flash = REPO_ROOT / "start_flash.py"
    env = os.environ.copy()
    # 在线模式：确保离线开关关闭
    env.pop("FLASH_OFFLINE", None)
    env["FLASH_FORCE_ONLINE"] = "1"       # 防 wheelhouse 残留误判（本仓库根无 wheelhouse/，双保险）
    env["PYTHONUNBUFFERED"] = "1"
    env["FLASH_VENV_DIR"] = str(REPO_ROOT / ".venv-win")   # ★ 命名环境，不碰旧 .venv

    print(f"[01a] repo root : {REPO_ROOT}")
    print(f"[01a] base py   : {base_py}")
    print(f"[01a] venv      : {env['FLASH_VENV_DIR']}（命名环境）")
    print(f"[01a] log       : {log_path}")

    cmd = [base_py, str(start_flash)]
    with open(log_path, "w", encoding="utf-8", errors="replace") as lf:
        proc = subprocess.Popen(cmd, cwd=str(REPO_ROOT), env=env,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, encoding="utf-8", errors="replace",
                                bufsize=1)
        assert proc.stdout is not None
        for line in proc.stdout:
            lf.write(line)
            print("  | " + line.rstrip())
        proc.wait()
    rc = proc.returncode
    print(f"[01a] start_flash.py 退出码: {rc}")

    # ---- 独立验证 ----
    venv_py = find_venv_python()
    r = subprocess.run(
        [str(venv_py), "-c",
         "import flash, numpy, h5py, pytest, yt\n"
         "import flash as f; print('flash file:', f.__file__)"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    verify_ok = r.returncode == 0
    print(f"[01a] 独立验证 import flash/yt: {'OK' if verify_ok else 'FAIL'}")
    if not verify_ok:
        print((r.stdout or "")[-500:]); print((r.stderr or "")[-800:])

    report = REPO_ROOT / "test" / "reports" / "INSTALL_TEST_REPORT.txt"
    print(f"[01a] 报告: {report}（存在={report.is_file()}）")
    print(f"[01a] 结论: {'PASS' if rc == 0 and verify_ok else 'FAIL'}")
    return 0 if (rc == 0 and verify_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
