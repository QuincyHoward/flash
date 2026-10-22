#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""run_all.py — flash-sim 超算离线部署总编排（串行，失败即停）。

步骤链（每步可独立重跑）:
  01a  local_env_windows.py     本地 Windows 环境建造+自检（在线）
  01b  local_env_wsl.py         本地 WSL 环境建造+自检（★离线=复刻超算路径）
  02   probe_remote_env.py      超算只读探测
  03   build_wheelhouse_linux.py 交叉造 Linux wheelhouse
  04   build_bundle.py          git bundle 制作+校验
  05   package_and_upload.py    打包上传+远端解压 clone
  06   remote_install.py        超算命名环境离线安装+三套测试
  07   run_snb_smoke.py         SNBOneCH_m 极短仿真验证

用法:
  python run_all.py                 # 从 01a 全链路
  python run_all.py --from 03      # 从第 3 步开始（编号见上）
  python run_all.py --only 05      # 只跑某步
  python run_all.py --skip 01a,01b # 跳过已完成的本地预演
"""
import argparse
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEST_DIR = HERE.parent
REPO_ROOT = TEST_DIR.parents[3]
LOG_DIR = TEST_DIR / "logs"
MANAGED_PY = Path(r"C:\Users\Administrator\.workbuddy\binaries\python\versions\3.13.12\python.exe")

STEPS = [
    ("01a", "local_env_windows.py",      "本地 Windows 环境建造+自检"),
    ("01b", "local_env_wsl.py",          "本地 WSL 环境建造+自检（离线预演）"),
    ("02",  "probe_remote_env.py",       "超算只读探测"),
    ("03",  "build_wheelhouse_linux.py", "交叉造 Linux wheelhouse"),
    ("04",  "build_bundle.py",           "git bundle 制作+校验"),
    ("05",  "package_and_upload.py",     "打包上传+远端展开 clone"),
    ("06",  "remote_install.py",         "超算命名环境离线安装+测试"),
    ("07",  "run_snb_smoke.py",          "SNBOneCH_m 极短仿真验证"),
]

#: 各步骤默认参数（02 步远端操作天然串行；01b/03 本地可复跑）
STEP_ARGS: dict = {"01b": ["--offline"]}


def pick_py() -> str:
    return str(MANAGED_PY) if MANAGED_PY.is_file() else sys.executable


def run_step(key: str, script: str, extra: list) -> int:
    py = pick_py()
    cmd = [py, str(HERE / script)] + extra
    print("\n" + "=" * 72)
    print(f"[run_all] Step {key}: {script} {' '.join(extra)}")
    print(f"[run_all] 开始: {datetime.now():%H:%M:%S}")
    print("=" * 72)
    t0 = time.time()
    r = subprocess.run(cmd, cwd=str(REPO_ROOT))
    dt = time.time() - t0
    status = "PASS" if r.returncode == 0 else "FAIL"
    print(f"[run_all] Step {key} {status}（rc={r.returncode}，耗时 {dt:.0f}s）")
    return r.returncode


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="from_step", default=None,
                    help="从某步开始，如 03")
    ap.add_argument("--only", default=None, help="只跑某步")
    ap.add_argument("--skip", default="", help="逗号分隔跳过列表")
    args = ap.parse_args()

    skip = {s.strip() for s in args.skip.split(",") if s.strip()}
    started = False
    results = []
    for key, script, desc in STEPS:
        if args.only:
            if key != args.only:
                continue
        elif args.from_step:
            if key == args.from_step:
                started = True
            if not started:
                continue
        if key in skip:
            print(f"[run_all] 跳过 Step {key}（--skip）")
            continue
        rc = run_step(key, script, STEP_ARGS.get(key, []))
        results.append((key, rc))
        if rc != 0:
            print(f"\n[run_all] Step {key} 失败 —— 按逐项恢复策略定位后，"
                  f"用 --from {key} 重跑本编排。已停在此步。")
            break

    print("\n" + "=" * 72)
    print("[run_all] 汇总:")
    for key, rc in results:
        print(f"  Step {key}: {'PASS' if rc == 0 else 'FAIL'}")
    return 0 if results and all(rc == 0 for _, rc in results) else 1


if __name__ == "__main__":
    sys.exit(main())
