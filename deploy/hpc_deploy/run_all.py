#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""run_all.py — flash-sim 超算离线部署总编排（串行，失败即停）。

步骤链（每步可独立重跑）:
  00   remote_clean.py         ★ 远端安装目录归档清空（★ 必须在 05 之前）
  01a  local_env_windows.py     本地 Windows 环境建造+自检（在线）
  01b  local_env_wsl.py         本地 WSL 环境建造+自检（★离线=复刻超算路径）
  02   probe_remote_env.py      超算只读探测
  03   build_wheelhouse_linux.py 交叉造 Linux wheelhouse
  04   build_bundle.py          git bundle 制作+校验
  05   package_and_upload.py    打包上传+远端解压 clone（★ 含 wheelhouse，212MB）
  05b  sync_incremental.py      ★ 轻量增量同步（只传 42MB bundle，代码改动用这个）
  06   remote_install.py        超算命名环境离线安装+三套测试
  07   run_snb_smoke.py         SNBOneCH_m 极短仿真验证
  08   run_public_tests.py      ★ public 子场景测试（A 全局自检 + B sbatch 真跑）

★ 步骤 00 的位置铁律：
  ``git clone`` 要求**目标目录不存在或为空** ⇒ 00（清空）必须在 05（clone）之前。
  00 默认 dry-run，只加 ``--yes`` 才真正执行（改名归档，不硬删，可回滚）。
  例：``python run_all.py --from 00 --only 00`` → 只做 dry-run 勘察
      ``python run_all.py --only 00 --step-args "--yes"`` → 真正清空

用法:
  python run_all.py                 # 从 01a 全链路
  python run_all.py --from 03      # 从第 3 步开始（编号见上）
  python run_all.py --only 05      # 只跑某步
  python run_all.py --skip 01a,01b # 跳过已完成的本地预演
"""
import argparse
import os
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
#: ★ 2026-10-24：原 MANAGED_PY 写死本机 `C:\Users\Administrator\...python.exe`
#:   （换机即失效，且该解释器无 cryptography/paramiko）。已删除 —— 解释器
#:   选择统一走 `pick_py()` → flash.flash_run.env.venv_paths。

STEPS = [
    ("00",  "remote_clean.py",         "★ 远端安装目录归档清空（dry-run 默认）"),
    ("01a", "local_env_windows.py",      "本地 Windows 环境建造+自检"),
    ("01b", "local_env_wsl.py",          "本地 WSL 环境建造+自检（离线预演）"),
    ("02",  "probe_remote_env.py",       "超算只读探测"),
    ("03",  "build_wheelhouse_linux.py", "交叉造 Linux wheelhouse"),
    ("04",  "build_bundle.py",           "git bundle 制作+校验"),
    ("05",  "package_and_upload.py",     "打包上传+远端展开 clone（含 wheelhouse）"),
    ("05b", "sync_incremental.py",       "★ 轻量增量同步（只传 bundle，代码改动首选）"),
    ("06",  "remote_install.py",         "超算命名环境离线安装+测试"),
    ("07",  "run_snb_smoke.py",          "SNBOneCH_m 极短仿真验证"),
    ("08",  "run_public_tests.py",       "★ public 子场景测试（A 自检 + B sbatch 真跑）"),
]

#: 各步骤默认参数（02 步远端操作天然串行；01b/03 本地可复跑）
#: ★ 00 步默认**不加** --yes ⇒ 编排里跑 00 只是勘察，不会真的清空远端。
#:   真正清空请显式：python run_all.py --only 00 --extra "--yes"
STEP_ARGS: dict = {"01b": ["--offline"]}


def pick_py() -> str:
    """选解释器：**唯一事实源 = flash.flash_run.env.venv_paths**。

    ★ 2026-10-24（解耦计划 B3）修三处历史缺陷：
      1. 旧实现只认无后缀 `.venv/Scripts/python.exe`，而 01a/01b 实际建的是
         `.venv-win`/`.venv-linux` ⇒ 本机两套环境**并行且静默**：
         01a 用新 venv、02/05/06/07 用旧 venv（缺包时症状是"解密失败"，
         完全指不到 venv）。
      2. 旧实现**不读 `FLASH_VENV_DIR`** ⇒ 部署链里注入的 venv 被忽略。
      3. 旧实现兜底到写死的 `C:\\Users\\Administrator\\...python.exe`
         （换机/换用户即失效，且该解释器没有 cryptography/paramiko）。
    """
    env_dir = os.environ.get("FLASH_VENV_DIR", "").strip()
    candidates: list[Path] = [Path(env_dir)] if env_dir else []

    try:                                    # deploy → flash_run 是允许方向
        from flash.flash_run.env.venv_paths import repo_root, venv_python

        py = venv_python(repo_root() or REPO_ROOT, "local")
        if py and py.is_file():
            candidates.append(Path(py))
    except Exception:                       # noqa: BLE001 - 未安装/旧版本时退回本地探测
        pass

    candidates += [REPO_ROOT / ".venv-win", REPO_ROOT / ".venv-linux", REPO_ROOT / ".venv"]
    # 只探本平台的布局：Windows 上 `.venv-linux/bin/python` 是符号链接，
    # `is_file()` 会抛 WinError 1920（不是返回 False），会打断整个探测。
    subs = (("Scripts", "python.exe"),) if os.name == "nt" else (("bin", "python"),)
    for d in candidates:
        for sub in subs:
            p = Path(d).joinpath(*sub)
            try:
                if p.is_file():
                    return str(p)
            except OSError:
                continue
    return sys.executable


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


def _split_extra(extra: str) -> list[str]:
    """把 --extra 字符串切成参数列表（支持引号内含空格）。"""
    import shlex
    return shlex.split(extra) if extra.strip() else []


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="from_step", default=None,
                    help="从某步开始，如 03")
    ap.add_argument("--only", default=None, help="只跑某步")
    ap.add_argument("--skip", default="", help="逗号分隔跳过列表")
    ap.add_argument("--extra", default="",
                    help="追加到**所有**步骤的额外参数（引号内），如 \"--yes\"")
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
        rc = run_step(key, script, STEP_ARGS.get(key, []) + _split_extra(args.extra))
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
