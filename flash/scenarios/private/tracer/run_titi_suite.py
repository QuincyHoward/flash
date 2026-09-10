"""
run_titi_suite — 一键顺序执行 TiTi 家族三场景 (TiTi1/2/3)
═══════════════════════════════════════════════════════════════════

场景矩阵 (3 个, 顺序即执行顺序):
  TiTi1 / TiTi2 / TiTi3   shld=Ti 屏蔽层 (4.54) + Ti 示踪层 @1/2/3um,
                          其余 samp/tar* 为 CH, MGD 10 群辐射开

时间控制:
  --tmax X  统一覆盖所有场景的仿真结束时间 (s)。默认 1.6e-9 (1.6 ns,
            正式物理运行, 与 CHTi 家族规范值一致); 极短验证用
            --tmax 1.0e-11。
  各场景脚本单独执行时默认 tmax=1.0e-11 (config_constants), 可用
  --tmax 覆盖 (par 中 tmax 不符时自动重新生成输入文件, 不会静默沿用
  旧值)。

夜间执行示例 (Windows, 项目 venv):
  E:\\PhySimX\\PhySimX\\simulation\\flash_test\\layer3\\flash\\.venv\\Scripts\\python.exe ^
      E:\\PhySimX\\PhySimX\\simulation\\flash_test\\layer3\\flash\\flash\\scenarios\\private\\tracer\\run_titi_suite.py
  # 全部 3 场景 @1.6e-9 约 5-7 h (参考 OneCH_ml 正式跑 113 min/场景);
  # 极短验证: ... run_titi_suite.py --tmax 1.0e-11
  # 只跑部分: ... run_titi_suite.py --only TiTi1,TiTi3

行为:
  1. 顺序运行 (子进程, 实时透传输出; TiTi1/2/3 共享 flash_input, 禁止并行);
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
    ("TiTi1", HERE / "TiTi" / "TiTi1.py"),
    ("TiTi2", HERE / "TiTi" / "TiTi2.py"),
    ("TiTi3", HERE / "TiTi" / "TiTi3.py"),
]


def main() -> int:
    ap = argparse.ArgumentParser(description="TiTi 家族一键批量运行")
    ap.add_argument("--tmax", type=float, default=1.6e-9,
                    help="统一覆盖各场景仿真结束时间 (s), 默认 1.6e-9 正式运行")
    ap.add_argument("--only", type=str, default=None,
                    help="逗号分隔的场景名筛选 (如 TiTi1,TiTi3); 默认全部")
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
    print(f" FLASH TiTi-suite batch runner: {len(selected)} scenario(s)")
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
