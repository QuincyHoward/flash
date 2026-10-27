"""
run_ml_suite — 一键顺序执行 tracer/ 全部 ml 系列场景
═══════════════════════════════════════════════════════════════════

场景矩阵 (9 个, 顺序即执行顺序):
  OneCH_ml / VCH_ml           纯 CH / V 屏蔽层基线 (辐射开)
  CHTi1 / CHTi2 / CHTi3       Ti 示踪层 @1/2/3um, shld=CH (辐射开)
  VCH_ml_F                    V 屏蔽层, 辐射关
  CHTi1_F / CHTi2_F / CHTi3_F Ti @1/2/3um, 辐射关

时间控制:
  --tmax X  统一覆盖所有场景的仿真结束时间 (传给各脚本 --tmax 参数)。
            默认 1.0e-11 (极短验证)。正式物理运行: --tmax 1.6e-9。
  各场景脚本单独执行时: CHTi 家族默认 tmax=1.0e-11 (config_constants),
  OneCH_ml/VCH_ml 默认规范值 1.6e-9, 均可用 --tmax 覆盖 (par 中 tmax 不符
  时自动重新生成输入文件, 不会静默沿用旧值)。

夜间执行示例 (Windows, 项目 venv):
  E:\\PhySimX\\PhySimX\\simulation\\flash_test\\layer3\\flash\\.venv\\Scripts\\python.exe ^
      E:\\PhySimX\\PhySimX\\simulation\\flash_test\\layer3\\flash\\flash\\scenarios\\private\\tracer\\run_ml_suite.py
  # 全部 9 场景 @1e-11 约 15-20 min; 只跑新场景:
  #   ... run_ml_suite.py --only CHTi1,CHTi2,CHTi3,VCH_ml_F,CHTi1_F,CHTi2_F,CHTi3_F

行为:
  1. 顺序运行 (子进程, 实时透传输出);
  2. 单场景失败不中断下一场景 (便于一次性暴露全部问题);
  3. 结束打印用时/退出码汇总表, 全部成功返回 0, 任一失败返回 1。
"""

import argparse
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# 统一 stdout/stderr 为 UTF-8，避免 GBK 控制台报错
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent

# (显示名, 主脚本路径) — 顺序即执行顺序
SCENARIOS = [
    ("VCH_ml_F", HERE / "VCH_ml_F" / "VCH_ml_F.py"),
    ("CHTi1", HERE / "CHTi" / "CHTi1.py"),
    ("CHTi1_F", HERE / "CHTi_F" / "CHTi1_F.py"),
    ("CHTi2", HERE / "CHTi" / "CHTi2.py"),
    ("CHTi2_F", HERE / "CHTi_F" / "CHTi2_F.py"),
    ("CHTi3", HERE / "CHTi" / "CHTi3.py"),
    ("CHTi3_F", HERE / "CHTi_F" / "CHTi3_F.py"),
    # ("OneCH_ml", HERE / "OneCH_ml" / "OneCH_ml.py"),
    # ("VCH_ml", HERE / "VCH_ml" / "VCH_ml.py"),
]


def main() -> int:
    ap = argparse.ArgumentParser(description="ml 系列场景一键批量运行")
    ap.add_argument("--tmax", type=float, default=1.6e-9,
                    help="统一覆盖各场景仿真结束时间 (s), 默认 1.0e-11 极短验证")
    ap.add_argument("--only", type=str, default=None,
                    help="逗号分隔的场景名筛选 (如 CHTi1,CHTi2); 默认全部")
    args = ap.parse_args()

    selected = SCENARIOS
    if args.only:
        want = {s.strip() for s in args.only.split(",") if s.strip()}
        selected = [(n, p) for n, p in SCENARIOS if n in want]
        unknown = want - {n for n, _ in SCENARIOS}
        if unknown:
            print(f"[!] 未知场景名 (忽略): {sorted(unknown)}")
    if not selected:
        print("[X] 无可运行场景")
        return 1

    print("\n" + "=" * 65)
    print(f" FLASH ml-suite batch runner: {len(selected)} scenario(s)")
    print(f" tmax = {args.tmax:.3e} s (统一覆盖)")
    print(f" {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 65)

    results = []
    for name, script in selected:
        if not script.is_file():
            print(f"\n[X] 主脚本缺失: {script}")
            results.append((name, -1, 0.0))
            continue
        print(f"\n{'─' * 65}")
        print(f"[>>] 开始场景: {name}")
        print(f"     脚本: {script}")
        print(f"{'─' * 65}\n", flush=True)

        t0 = time.time()
        proc = subprocess.run(
            [sys.executable, str(script), "--tmax", repr(args.tmax)])
        dt = time.time() - t0
        results.append((name, proc.returncode, dt))
        status = "OK" if proc.returncode == 0 else f"FAIL (exit={proc.returncode})"
        print(f"\n[<<] {name} 完成: {status}, 用时 {dt / 60:.1f} min\n", flush=True)

    # 汇总
    print("\n" + "=" * 65)
    print(" 批量运行汇总")
    print("=" * 65)
    all_ok = True
    for name, code, dt in results:
        ok = code == 0
        all_ok &= ok
        print(f"  {name:<12} {'✓ PASS' if ok else '✗ FAIL':<10} "
              f"exit={code:<4} 用时 {dt / 60:6.1f} min")
    print("=" * 65)
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
