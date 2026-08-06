#!/usr/bin/env python3
r"""
环境自检与依赖安装脚本 — 独立包模式 (备份/U 盘可双击执行)
=================================================================

功能:
  1. 检测 Python 版本与关键依赖 (numpy/h5py/matplotlib/scipy/pytest/paramiko/cryptography)
  2. 缺失的依赖自动 pip 安装 (已有则跳过)
  3. 检测当前目录是否为 flash 包根 (目录名不强制为 flash, 自动兼容)
  4. 输出检测报告, 可引导运行全局测试

用法:
  python check_env.py                 # 检测 + 自动安装缺失依赖
  python check_env.py --check-only    # 仅检测, 不安装
  python check_env.py --test          # 检测/安装后运行全局测试
  python check_env.py --install PKG   # 仅安装指定包 (可多次)
"""

import argparse
import importlib
import subprocess
import sys
from pathlib import Path

# ============================================================================
#  常量
# ============================================================================

# 必需依赖: (模块名, pip 包名)
REQUIRED_DEPS = [
    ("numpy", "numpy>=1.24"),
    ("h5py", "h5py>=3.8"),
    ("matplotlib", "matplotlib>=3.7"),
    ("scipy", "scipy"),
    ("pytest", "pytest>=7.0"),
    ("paramiko", "paramiko"),
    ("cryptography", "cryptography>=41.0"),
]

# 可选依赖 (缺失仅提示, 不安装)
OPTIONAL_DEPS = [
    ("yt", "yt>=4.1"),
    ("pydantic", "pydantic>=2.0"),
    ("physimx_core", "physimx-core"),
]

MIN_PYTHON = (3, 10)

# 颜色
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def ok(msg: str):
    print(f"  {GREEN}✅{RESET} {msg}")


def warn(msg: str):
    print(f"  {YELLOW}⚠️{RESET} {msg}")


def fail(msg: str):
    print(f"  {RED}❌{RESET} {msg}")


def info(msg: str):
    print(f"  {CYAN}ℹ️{RESET} {msg}")


# ============================================================================
#  项目根检测 (标准 flash/ 子包布局, 2026-08-06 起)
# ============================================================================


def find_package_root() -> Path:
    """向上查找含 pyproject.toml 的项目根目录 (flash 包位于其 flash/ 子目录)."""
    root = Path(__file__).resolve().parent
    for _ in range(12):
        if (root / "pyproject.toml").exists():
            return root
        root = root.parent
    raise RuntimeError("Cannot locate flash package root")


def ensure_flash_importable(package_root: Path) -> None:
    """将项目根加入 sys.path, 使 `import flash` 可用 (flash/ 子包, 目录名固定).

    兼容场景:
      - 开发目录: 项目根入 sys.path, flash 包位于 项目根/flash/
      - 备份目录: 目录名为 flash_backup_gitee_xxx → 同上 (子目录名固定为 flash)
    """
    if str(package_root) not in sys.path:
        sys.path.insert(0, str(package_root))

    pkg_name = package_root.name
    if pkg_name != "flash":
        # 备份/独立目录: flash 子包名固定, 无需别名映射 (旧逻辑已废弃)
        try:
            import flash  # noqa: F401
        except Exception as e:  # noqa: BLE001
            warn(f"flash 子包导入失败: {e}")


# ============================================================================
#  依赖检测与安装
# ============================================================================


def check_dep(module_name: str) -> bool:
    """检查模块是否可导入, 返回 (是否已安装)."""
    try:
        mod = importlib.import_module(module_name)
        ver = getattr(mod, "__version__", "?")
        return True, str(ver)
    except ImportError:
        return False, ""


def install_dep(pip_name: str, python: str) -> bool:
    """安装单个依赖, 返回 (是否成功)."""
    cmd = [python, "-m", "pip", "install", pip_name, "--retries", "10", "--timeout", "120"]
    info(f"安装: {pip_name}")
    r = subprocess.run(cmd, capture_output=False)
    return r.returncode == 0


def run_env_check(python: str | None = None, auto_install: bool = True) -> dict:
    """执行环境检测, 可选自动安装缺失依赖.

    Returns:
        {"missing": [pip 包名], "failed": [pip 包名]}
    """
    python = python or sys.executable

    print()
    print(f"  {BOLD}{'='*56}{RESET}")
    print(f"  {BOLD}  环境自检 (flash-sim){RESET}")
    print(f"  {BOLD}{'='*56}{RESET}")
    info(f"Python: {python}")
    info(f"版本:   {sys.version.split()[0]}")

    # Python 版本检查
    if sys.version_info < MIN_PYTHON:
        fail(f"Python 版本过低: {sys.version_info[0]}.{sys.version_info[1]} (需要 >=3.10)")
    else:
        ok(f"Python 版本 {sys.version_info[0]}.{sys.version_info[1]}")

    # 依赖检测
    missing = []
    for module, pip_name in REQUIRED_DEPS:
        installed, ver = check_dep(module)
        if installed:
            ok(f"{module} {ver}")
        else:
            warn(f"缺少: {module}")
            missing.append(pip_name)

    # 可选依赖提示
    for module, pip_name in OPTIONAL_DEPS:
        installed, _ = check_dep(module)
        if not installed:
            warn(f"可选依赖缺失 (不影响核心): {module} ({pip_name})")

    # 自动安装
    failed = []
    if missing and auto_install:
        print()
        info(f"检测到 {len(missing)} 个缺失依赖, 开始自动安装...")
        for pip_name in missing:
            if not install_dep(pip_name, python):
                failed.append(pip_name)
        print()
        # 二次验证
        recheck = [pip_name for m, pip_name in REQUIRED_DEPS if not check_dep(m)[0]]
        if recheck:
            fail(f"仍有缺失: {recheck}")
        else:
            ok("所有依赖已就绪")

    return {"missing": missing, "failed": failed}


# ============================================================================
#  主入口
# ============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="环境自检与依赖安装 (独立包模式)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""示例:
  python check_env.py                 # 检测 + 自动安装缺失依赖
  python check_env.py --check-only    # 仅检测, 不安装
  python check_env.py --test          # 检测/安装后运行全局测试
""",
    )
    parser.add_argument("--check-only", action="store_true", help="仅检测, 不安装")
    parser.add_argument("--test", action="store_true", help="检测/安装后运行全局测试")
    parser.add_argument(
        "--install", action="append", default=[], metavar="PKG", help="仅安装指定包 (可多次, 如 --install pytest)"
    )

    args = parser.parse_args()

    # 包根检测 (即使目录名不是 flash)
    try:
        root = find_package_root()
        ensure_flash_importable(root)
        info(f"包根: {root}")
    except RuntimeError as e:
        fail(str(e))
        sys.exit(1)

    # 仅安装指定包
    if args.install:
        for pkg in args.install:
            installed_ok = install_dep(pkg, sys.executable)
            if not installed_ok:
                fail(f"安装失败: {pkg}")
                sys.exit(1)
        ok(f"已安装: {', '.join(args.install)}")
        return

    # 标准检测
    result = run_env_check(auto_install=not args.check_only)

    if result["failed"]:
        fail(f"安装失败: {result['failed']}")
        sys.exit(1)

    # 运行测试
    if args.test:
        print()
        info("运行全局测试...")
        test_script = root / "scripts" / "run_global_tests.py"
        if test_script.exists():
            r = subprocess.run([sys.executable, str(test_script)], cwd=root)
            sys.exit(r.returncode)
        else:
            fail(f"测试脚本不存在: {test_script}")
            sys.exit(1)

    print()
    ok("环境检查完成")


if __name__ == "__main__":
    main()
