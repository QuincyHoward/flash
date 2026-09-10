"""SNBOneCH_ml NC-E 1.6ns 全流程一键编排 (用户指令: 编写 py 直接执行 1.6ns 仿真全流程)。

流程 (每阶段独立验证, 失败即停):
  [0] 预备: 旧收集目录归档改名 (hpc_flash_ssh → hpc_flash_ssh_prev_<ts>)
  [1] 冒烟: tmax=1e-11 全流程验证 (生成→上传→提交→轮询→收集), ~5 min
  [2] 正式: tmax=1.6e-9 (CH 示踪规范), --poll-timeout 43200 (12h 轮询上限;
      NC-E 131 核 @ dx=0.0298µm 实测 2e-10 用 58.4min → 1.6e-9 预计 ~8h)
  [3] 分析: plot_snb_profile.py 密度/温度剖面 + dt 演化 → analysis/*.png

用法:
  python run_full_nce_16ns.py                 # 冒烟 → 正式 → 分析
  python run_full_nce_16ns.py --skip-smoke    # 跳过冒烟直接 1.6ns
  python run_full_nce_16ns.py --smoke-only    # 只跑冒烟验证全流程

依赖: SNBOneCH_ml.py (--poll-timeout 已支持), 凭据 flash_ssh (NC-E)。
"""
import argparse
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "..", "..", ".."))
PY = sys.executable

ACCOUNT = "flash_ssh"        # NC-E scfa2696
NPROC = 131                  # +ug: nproc = iProcs = 块数 → dx=0.0298 µm
TMAX_SMOKE = "1.0e-11"       # 全流程冒烟
TMAX_FINAL = "1.6e-9"        # CH 示踪规范结束时间
POLL_SMOKE = 7200            # 冒烟轮询上限 2h (含排队)
POLL_FINAL = 43200           # 正式轮询上限 12h

COLLECT = os.path.join(SCRIPT_DIR, "flash_output", "hpc_flash_ssh")


def _sh_step(msg: str) -> None:
    print(f"\n{'=' * 66}\n [{msg}]\n{'=' * 66}", flush=True)


def _run_snb(tmax: str, poll_timeout: int) -> int:
    """调 SNBOneCH_ml.py 单轮 HPC 全流程 (生成/上传/提交/轮询/收集)。"""
    cmd = [
        PY, os.path.join(SCRIPT_DIR, "SNBOneCH_ml.py"),
        "--mode", "hpc", "--account", ACCOUNT,
        "--nproc", str(NPROC), "--tmax", tmax,
        "--skip-build", "--poll-timeout", str(poll_timeout),
    ]
    print("  CMD:", " ".join(cmd), flush=True)
    return subprocess.call(cmd, cwd=ROOT)


def _archive(name_src: str, name_dst: str) -> None:
    src = os.path.join(SCRIPT_DIR, "flash_output", name_src)
    dst = os.path.join(SCRIPT_DIR, "flash_output", name_dst)
    if os.path.isdir(src):
        if os.path.isdir(dst):
            shutil.rmtree(dst)
        os.rename(src, dst)
        print(f"  [archive] {name_src} → {name_dst}", flush=True)


def main() -> int:
    ap = argparse.ArgumentParser(description="NC-E 1.6ns 全流程编排")
    ap.add_argument("--skip-smoke", action="store_true", help="跳过冒烟直接 1.6ns")
    ap.add_argument("--smoke-only", action="store_true", help="只跑冒烟验证")
    ap.add_argument("--tmax-final", default=TMAX_FINAL, help="正式跑结束时间")
    args = ap.parse_args()

    t0 = time.time()
    print("#" * 66)
    print(f"# SNBOneCH_ml NC-E 全流程编排  start={datetime.now():%F %T}")
    print(f"# 冒烟 tmax={TMAX_SMOKE}  正式 tmax={args.tmax_final}  nproc={NPROC}")
    print("#" * 66, flush=True)

    # [0] 旧结果归档
    _sh_step("STEP 0: 归档旧收集目录")
    ts = datetime.now().strftime("%H%M%S")
    _archive("hpc_flash_ssh", f"hpc_flash_ssh_prev_{ts}")

    # [1] 冒烟
    if not args.skip_smoke:
        _sh_step(f"STEP 1: 冒烟全流程 tmax={TMAX_SMOKE}")
        rc = _run_snb(TMAX_SMOKE, POLL_SMOKE)
        if rc != 0:
            print(f"\n✗ 冒烟失败 (rc={rc}) — 中止, 不进入 1.6ns 正式跑", flush=True)
            return 1
        _archive("hpc_flash_ssh", "hpc_flash_ssh_smoke_1e-11")
        print("  ✓ 冒烟全流程通过, 收集目录已归档为 hpc_flash_ssh_smoke_1e-11/",
              flush=True)
        if args.smoke_only:
            print("\n[smoke-only] 到此为止", flush=True)
            return 0
    elif args.smoke_only:
        print("--smoke-only 与 --skip-smoke 冲突")
        return 2

    # [2] 正式 1.6ns
    _sh_step(f"STEP 2: 正式仿真 tmax={args.tmax_final} (预计 ~8h + 排队)")
    rc = _run_snb(args.tmax_final, POLL_FINAL)
    if rc != 0:
        print(f"\n✗ 正式跑失败 (rc={rc}) — 检查 run 日志与远端 run_*_out.txt",
              flush=True)
        return 1

    # [3] 绘图分析
    _sh_step("STEP 3: 绘图分析 (profile + dt evolution)")
    rc = subprocess.call([PY, os.path.join(SCRIPT_DIR, "scripts", "analysis", "plot_snb_profile.py"),
                          "--dir", COLLECT], cwd=ROOT)
    if rc != 0:
        print(f"⚠ 绘图分析未完全成功 (rc={rc}), 但仿真结果已收集", flush=True)

    dt_total = time.time() - t0
    print("#" * 66)
    print(f"# 全流程完成  总耗时 {dt_total/3600:.2f} h  "
          f"end={datetime.now():%F %T}")
    print(f"# 结果: {COLLECT}")
    print("#" * 66, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
