#!/usr/bin/env python3
"""
测试运行器 — 双击可执行
=======================

双击执行: 运行全部模块的 pytest 测试 (全局测试), 汇总结果。

功能模式:
  (默认) 全局测试  =  Flash 框架 + InputGen + OutputProcessors
  --framework      仅 Flash 框架测试
  --input          仅 InputGen 测试
  --output         仅 OutputProcessors 测试
  --module PATH    运行指定测试文件/目录

用法:
  python run_global_tests.py                        # 双击/默认: 全局测试
  python run_global_tests.py --framework            # 仅框架测试
  python run_global_tests.py -v                     # 详细输出
  python run_global_tests.py --framework --list     # 列出框架测试用例
  python run_global_tests.py --module test/test_gitee.py   # 单个文件
"""

import os
import subprocess
import sys
import time
from pathlib import Path

# ============================================================================
#  Bootstrap: find flash project root (独立包模式, 可任意搬迁)
#  兼容目录名非 flash 的情况 (如备份目录 flash_backup_gitee_xxx)
# ============================================================================
_ROOT = Path(__file__).resolve().parent
for _ in range(12):
    if (_ROOT / "pyproject.toml").exists():
        break
    _ROOT = _ROOT.parent
else:
    raise RuntimeError("Cannot locate flash package root")
_PARENT = _ROOT
if str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))


# ============================================================================
#  Bootstrap: 直接运行时自动转为模块方式 (scripts 包, 标准布局)
#  重组后: flash 包 = 项目根/flash/, scripts 包 = 项目根/scripts/
#  旧"包名映射 flash 别名 + 目录 junction"兼容逻辑已废弃
# ============================================================================
if __name__ == "__main__" and __package__ is None:
    import runpy

    runpy.run_module("scripts.run_global_tests", run_name="__main__")
    sys.exit(0)

# ============================================================================
#  预定义测试套件
# ============================================================================

SUITES = {
    "framework": ("Flash 框架测试",   "test/",                   True),
    "input":     ("InputGen 测试",    "flash/input_gen/test/",   True),
    "output":    ("OutputProcessors 测试", "flash/output_processors/test/", False),
}

SUITE_ORDER = ["framework", "input", "output"]

# 颜色
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def eprint(*args, **kwargs):
    print(*args, **kwargs, file=sys.stderr)


def ok(msg: str):
    eprint(f"  {GREEN}✅{RESET} {msg}")


def info(msg: str):
    eprint(f"  {CYAN}ℹ️{RESET} {msg}")


def warn(msg: str):
    eprint(f"  {YELLOW}⚠️{RESET} {msg}")


def fail(msg: str):
    eprint(f"  {RED}❌{RESET} {msg}")


# ============================================================================
#  核心
# ============================================================================

def find_project_root() -> Path:
    """向上查找包含 .git 的目录作为项目根。"""
    current = Path(__file__).resolve().parent
    for _ in range(10):
        if (current / ".git").exists():
            return current
        if current == current.parent:
            break
        current = current.parent
    return Path(__file__).resolve().parent.parent


def build_test_env(project_root: Path) -> dict:
    """构建环境变量: 设置 PYTHONPATH 让 import flash 可用。"""
    test_env = os.environ.copy()
    parent_path = str(project_root.parent)
    existing = test_env.get("PYTHONPATH", "")
    paths = [p for p in existing.split(";") if p] if existing else []
    if parent_path not in paths:
        paths.insert(0, parent_path)
    test_env["PYTHONPATH"] = ";".join(paths)
    return test_env


def run_one_suite(
    label: str,
    rel_dir: str,
    project_root: Path,
    test_env: dict,
    verbose: bool = False,
    critical: bool = True,
    collect_only: bool = False,
) -> tuple[bool, float]:
    """运行一个测试套件, 返回 (通过?, 耗时秒)。"""
    test_path = project_root / rel_dir
    if not test_path.exists():
        warn(f"测试目录不存在: {test_path}")
        return (True, 0.0)

    info(f"  - {label}: {rel_dir}")
    t0 = time.time()

    cmd = [sys.executable, "-m", "pytest", str(test_path)]
    # 设置 pytest 根目录为 flash/，阻止 pytest 向上查找加载父包 __init__.py
    if project_root:
        cmd.extend(["--rootdir", str(project_root)])
    if verbose:
        cmd.extend(["-v", "--tb=long"])
    else:
        cmd.extend(["-q", "--tb=line"])
    if collect_only:
        cmd.append("--collect-only")

    r = subprocess.run(
        cmd, cwd=project_root, capture_output=False,
        encoding="utf-8", errors="replace", env=test_env,
    )
    elapsed = time.time() - t0

    passed = (r.returncode == 0)
    if not passed and not critical:
        warn(f"{label} 测试失败 (非关键, 继续执行)")
        passed = True
    return (passed, elapsed)


def print_header(title: str, project_root: Path):
    eprint()
    eprint(f"  {BOLD}{'='*56}{RESET}")
    eprint(f"  {BOLD}  {title}{RESET}")
    eprint(f"  {BOLD}{'='*56}{RESET}")
    info(f"项目根: {project_root}")
    info(f"Python: {sys.executable}")
    eprint()


def print_footer(results: list, total_elapsed: float, all_passed: bool):
    eprint()
    eprint(f"  {BOLD}{'='*56}{RESET}")
    eprint(f"  {BOLD}  测试总结{RESET}")
    eprint(f"  {BOLD}{'='*56}{RESET}")
    for label, passed in results:
        s = f"{GREEN}✅ 通过{RESET}" if passed else f"{RED}❌ 失败{RESET}"
        eprint(f"  {s}  {label}")
    eprint()
    if all_passed:
        ok(f"全部通过! (耗时 {total_elapsed:.1f}s)")
    else:
        fail(f"存在失败测试 (耗时 {total_elapsed:.1f}s)")


# ============================================================================
#  模式: 运行预定义套件
# ============================================================================

def run_suites(suite_keys: list[str], verbose: bool, collect_only: bool) -> int:
    """运行指定套件列表, 返回退出码。"""
    project_root = find_project_root()
    test_env = build_test_env(project_root)

    mode_name = "+".join(suite_keys)
    print_header(f"测试套件 [{mode_name}]", project_root)

    all_passed = True
    total_elapsed = 0.0
    results = []

    for key in suite_keys:
        if key not in SUITES:
            warn(f"未知套件: {key}")
            continue
        label, rel_dir, critical = SUITES[key]
        passed, elapsed = run_one_suite(
            label, rel_dir, project_root, test_env,
            verbose=verbose, critical=critical, collect_only=collect_only,
        )
        results.append((label, passed))
        total_elapsed += elapsed
        if not passed:
            all_passed = False
            if critical:
                fail("关键测试未通过, 中止")
                return 1

    print_footer(results, total_elapsed, all_passed)
    return 0 if all_passed else 1


# ============================================================================
#  模式: 运行指定模块
# ============================================================================

def run_module(
    module_path: str,
    verbose: bool,
    collect_only: bool,
) -> int:
    """运行指定的测试模块/目录, 返回退出码。"""
    project_root = find_project_root()
    test_env = build_test_env(project_root)
    target = project_root / module_path

    if not target.exists():
        fail(f"测试路径不存在: {target}")
        return 1

    print_header(f"模块测试 [{module_path}]", project_root)

    t0 = time.time()
    cmd = [sys.executable, "-m", "pytest", str(target)]
    if verbose:
        cmd.extend(["-v", "--tb=long"])
    else:
        cmd.extend(["-q", "--tb=line"])
    if collect_only:
        cmd.append("--collect-only")

    r = subprocess.run(
        cmd, cwd=project_root, capture_output=False,
        encoding="utf-8", errors="replace", env=test_env,
    )
    elapsed = time.time() - t0
    passed = (r.returncode == 0)

    print_footer([(module_path, passed)], elapsed, passed)
    return 0 if passed else 1


# ============================================================================
#  CLI 入口
# ============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="测试运行器 — 双击运行全局测试, 也支持按模块单独运行",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
模式 (互斥, 默认全局):
  (无参数)         全局测试 (framework + input + output)
  --framework      仅 Flash 框架测试 (test/)
  --input          仅 InputGen 测试 (input_gen/test/)
  --output         仅 OutputProcessors 测试 (output_processors/test/)
  --module PATH    运行指定测试文件或目录

示例:
  python run_global_tests.py                          # 全局测试
  python run_global_tests.py --framework              # 仅框架测试
  python run_global_tests.py --framework -v           # 框架测试详细输出
  python run_global_tests.py --input --list           # 列出 input_gen 用例
  python run_global_tests.py --module test/test_gitee.py   # 单个文件
  python run_global_tests.py --module input_gen/test       # 单个模块
        """,
    )

    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--framework", action="store_true", help="仅运行 Flash 框架测试")
    mode.add_argument("--input", action="store_true", help="仅运行 InputGen 测试")
    mode.add_argument("--output", action="store_true", help="仅运行 OutputProcessors 测试")
    mode.add_argument("--module", metavar="PATH", help="运行指定测试文件或目录 (相对项目根)")

    parser.add_argument("-v", "--verbose", action="store_true", help="详细 pytest 输出")
    parser.add_argument("--list", action="store_true", help="仅列出测试用例, 不执行")

    args = parser.parse_args()

    if args.module:
        sys.exit(run_module(args.module, args.verbose, args.list))

    # 确定套件列表
    if args.framework:
        keys = ["framework"]
    elif args.input:
        keys = ["input"]
    elif args.output:
        keys = ["output"]
    else:
        keys = SUITE_ORDER  # 全局

    sys.exit(run_suites(keys, args.verbose, args.list))


if __name__ == "__main__":
    main()
