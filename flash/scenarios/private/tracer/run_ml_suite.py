"""
run_ml_suite — 一键顺序执行 OneCH_ml 与 VCH_ml 两个场景
═══════════════════════════════════════════════════════════════════

用途: 批量测试验证 (当前两场景 config_constants 中 tmax=1.0e-11)。
夜间执行示例 (Windows, 项目 venv):

  E:\\PhySimX\\PhySimX\\simulation\\flash_test\\layer3\\flash\\.venv\\Scripts\\python.exe ^
      E:\\PhySimX\\PhySimX\\simulation\\flash_test\\layer3\\flash\\flash\\scenarios\\private\\tracer\\run_ml_suite.py

行为:
  1. 顺序运行 OneCH_ml → VCH_ml (子进程, 实时透传输出);
  2. 单场景失败不中断下一场景 (便于一次性暴露全部问题);
  3. 结束打印用时/退出码汇总表, 全部成功返回 0, 任一失败返回 1。

正式物理运行 (tmax=1.6e-9) 时请先改两场景的 config_constants["tmax"]。
"""

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
    ("OneCH_ml", HERE / "OneCH_ml" / "OneCH_ml.py"),
    ("VCH_ml", HERE / "VCH_ml" / "VCH_ml.py"),
]


def main() -> int:
    print("\n" + "=" * 65)
    print(" FLASH ml-suite batch runner: OneCH_ml -> VCH_ml")
    print(f" {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 65)

    results = []
    for name, script in SCENARIOS:
        if not script.is_file():
            print(f"\n[X] 主脚本缺失: {script}")
            results.append((name, -1, 0.0))
            continue
        print(f"\n{'─' * 65}")
        print(f"[>>] 开始场景: {name}")
        print(f"     脚本: {script}")
        print(f"{'─' * 65}\n", flush=True)

        t0 = time.time()
        proc = subprocess.run([sys.executable, str(script)])
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
