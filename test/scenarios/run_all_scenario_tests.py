"""
run_all_scenario_tests.py — 运行所有 scenarios 接口测试并保存结果

用法:
    python run_all_scenario_tests.py              # 运行并保存到 outputfiles/
    python run_all_scenario_tests.py --print       # 仅打印到终端
    python run_all_scenario_tests.py --output xxx  # 指定输出目录
"""

import sys, os, time, subprocess
from pathlib import Path

_TEST_DIR = Path(__file__).parent.resolve()
_OUTPUT_DIR = _TEST_DIR.parent / "outputfiles" / "scenario_tests"

# 测试脚本列表 (按依赖顺序)
TEST_SCRIPTS = [
    ("test_scenarios_imports.py",       "场景导入与注册"),
    ("test_scenario_par_build.py",      ".par 文件生成"),
    ("test_engine_dryrun.py",           "引擎 dry-run"),
    # 真实 FLASH 仿真测试: 需要 5-10 分钟
    # 取消注释以运行 (scenarios/test_real_flash_run.py)
    # ("test_real_flash_run_si.py", "Si FLASH 仿真 (1ns)"),
    # ("test_real_flash_run_ch.py", "CH FLASH 仿真 (1ns)"),
]

# 验证已有真实仿真输出
REAL_RUN_DIRS = {
    "thin_layer_sandwich_si":
        _TEST_DIR / "runs" / "000001",
    "ch_center":
        _TEST_DIR / "runs_ch_center" / "000001",
}


def run_tests(output_dir: str = None):
    """运行所有测试, 保存结果"""
    if output_dir is None:
        output_dir = str(_OUTPUT_DIR)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    results = {}
    all_passed = True
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

    print("=" * 60)
    print(f"  scenarios 接口全面测试 — {timestamp}")
    print(f"  输出目录: {out_dir}")
    print("=" * 60)

    for script, description in TEST_SCRIPTS:
        script_path = _TEST_DIR / script
        print(f"\n{'─' * 50}")
        print(f"  [{description}] {script}")
        print(f"{'─' * 50}")

        start = time.time()
        result_file = out_dir / f"{script.replace('.py', '.txt')}"

        # 执行 (UTF-8 环境, 兼容 Anaconda GBK)
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        r = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True, text=True,
            cwd=str(_TEST_DIR),
            timeout=60,
            env=env,
        )

        elapsed = time.time() - start
        passed = r.returncode == 0
        combined = r.stdout or ""
        if r.stderr:
            combined += "\n--- STDERR ---\n" + (r.stderr or "")

        # 保存结果
        with open(result_file, "w", encoding="utf-8") as f:
            f.write(f"Test: {script} ({description})\n")
            f.write(f"Status: {'PASS' if passed else 'FAIL'}\n")
            f.write(f"Time: {elapsed:.2f}s\n")
            f.write(f"Exit Code: {r.returncode}\n")
            f.write("=" * 50 + "\n")
            f.write(combined)

        results[script] = {
            "passed": passed,
            "elapsed": elapsed,
            "stdout": combined,
        }
        if not passed:
            all_passed = False

        # 打印摘要
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status} ({elapsed:.2f}s)")
        print(f"  结果: {result_file}")
        # 打印最后几行
        last_lines = [l for l in combined.strip().split("\n") if l.strip()][-3:]
        for line in last_lines:
            print(f"    {line}")

    # 汇总
    print(f"\n{'=' * 60}")
    print(f"  测试汇总")
    print(f"{'=' * 60}")
    n_pass = sum(1 for r in results.values() if r["passed"])
    n_total = len(results)
    print(f"  通过: {n_pass}/{n_total}")
    print(f"  时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  结果目录: {out_dir}")

    # 汇总文件
    summary_file = out_dir / "SUMMARY.txt"
    with open(summary_file, "w", encoding="utf-8") as f:
        f.write(f"scenarios 接口测试汇总\n")
        f.write(f"{'=' * 50}\n")
        f.write(f"时间: {timestamp}\n")
        f.write(f"通过: {n_pass}/{n_total}\n\n")
        for script, r in results.items():
            f.write(f"  {'✅' if r['passed'] else '❌'} {script} ({r['elapsed']:.2f}s)\n")
    print(f"  汇总: {summary_file}")

    return all_passed


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="scenarios 接口测试")
    p.add_argument("--output", type=str, default=None,
                   help="输出目录 (默认 test/outputfiles/scenario_tests/)")
    p.add_argument("--print", action="store_true", dest="print_only",
                   help="仅打印, 不保存文件")
    args = p.parse_args()

    if args.print_only:
        # 直接执行每个测试脚本, 不保存
        test_dir = _TEST_DIR
        for script, desc in TEST_SCRIPTS:
            print(f"\n>>> {desc}")
            r = subprocess.run(
                [sys.executable, str(test_dir / script)],
                cwd=str(test_dir), timeout=60,
            )
            if r.returncode != 0:
                print(r.stderr)
    else:
        ok = run_tests(args.output)
        sys.exit(0 if ok else 1)
