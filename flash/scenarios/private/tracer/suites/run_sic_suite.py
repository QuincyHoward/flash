"""
run_sic_suite — 一键顺序执行单一纯材料 (Si/C) 示踪烧蚀场景家族
═══════════════════════════════════════════════════════════════════

场景矩阵 (4 个, 顺序即执行顺序):
  OneSi_ml      纯 Si  (Z14_1.00-20260708_0850.cn4), 辐射开
  OneSi_ml_F    纯 Si,  辐射关 (F 变体)
  OneC_ml       纯 C   (Z06_1.00-20260902_2228.cn4),  辐射开
  OneC_ml_F     纯 C,   辐射关 (F 变体)

  全部固体层 (shld/samp/tar1/2/3/4/6) 为同一种纯材料 — 单一纯材料烧蚀
  仿真; 腔室 cham 为稀氦 He; 几何与 OneCH_ml 一致 (8 物种 12 区)。

时间控制:
  --tmax X  统一覆盖所有场景的仿真结束时间 (传给各脚本 --tmax 参数)。
            默认 1.0e-11 (极短验证, 与各场景脚本 config_constants 默认一致)。
            正式物理运行: --tmax 1.6e-9。
  各场景脚本单独执行时: 默认 tmax=1.0e-11 (config_constants), 可用 --tmax
  覆盖 (par 中 tmax 不符时自动重新生成输入文件, 不会静默沿用旧值)。

验证测试 (当前阶段, Windows, 项目 venv):
  E:\\PhySimX\\PhySimX\\simulation\\flash_test\\layer3\\flash\\.venv\\Scripts\\python.exe ^
      flash\\scenarios\\private\\tracer\\run_sic_suite.py
  # 4 场景 @1e-11 约 5-6 min

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
    ("OneSi_ml", HERE / "OneSi_ml" / "OneSi_ml.py"),
    ("OneSi_ml_F", HERE / "OneSi_ml_F" / "OneSi_ml_F.py"),
    ("OneC_ml", HERE / "OneC_ml" / "OneC_ml.py"),
    ("OneC_ml_F", HERE / "OneC_ml_F" / "OneC_ml_F.py"),
]


def main() -> int:
    ap = argparse.ArgumentParser(description="Si/C 单一纯材料场景一键批量运行")
    ap.add_argument("--tmax", type=float, default=1.6e-9,
                    help="统一覆盖各场景仿真结束时间 (s), 默认 1.0e-11 极短验证")
    ap.add_argument("--only", type=str, default=None,
                    help="逗号分隔的场景名筛选 (如 OneSi_ml,OneC_ml_F); 默认全部")
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
    print(f" FLASH Si/C-suite batch runner: {len(selected)} scenario(s)")
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
