#!/usr/bin/env python3
"""
publish_pypi.py — flash-sim PyPI 发布脚本
===========================================

从 flash 凭据体系 (flash._core.credentials.pypi) 读取 PyPI / TestPyPI token,
上传 dist/ 产物, 并验证安装。

用法:
    python scripts/03_git_publish/publish_pypi.py --build        # 构建 sdist + wheel (默认含)
    python scripts/03_git_publish/publish_pypi.py --test         # 试发到 TestPyPI (不覆盖正式)
    python scripts/03_git_publish/publish_pypi.py --test --no-verify   # 试发但不验证安装
    python scripts/03_git_publish/publish_pypi.py                # 正式发布到 pypi.org
    python scripts/03_git_publish/publish_pypi.py --check        # 仅 twine check + 产物审计

前置:
    - dist/ 已构建 (或 --build 自动构建)
    - token 已配置: python -m flash._core.credentials.pypi setup
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
for _ in range(12):
    if (_ROOT / "pyproject.toml").exists():
        break
    _ROOT = _ROOT.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

PYTHON = sys.executable


def run(cmd: list, **kw) -> int:
    print(f"\n  $ {' '.join(map(str, cmd))}")
    return subprocess.run(cmd, **kw).returncode


def build() -> bool:
    print("\n  ── 1/4 构建 sdist + wheel ──")
    return run([PYTHON, "-m", "build"]) == 0


def audit() -> bool:
    print("\n  ── 2/4 产物审计 (twine check) ──")
    ok = run([PYTHON, "-m", "twine", "check", "dist/*"]) == 0
    if not ok:
        print("  ❌ twine check 失败, 中止发布。")
    return ok


def upload(index: str) -> bool:
    from flash._core.credentials.pypi import get_pypi_config

    cfg = get_pypi_config(index)
    if not cfg:
        print(f"  ❌ 未配置 {index} token, 请先运行:")
        print(f"     python -m flash._core.credentials.pypi setup {index}")
        return False

    env = dict(os.environ)
    env["TWINE_USERNAME"] = cfg["username"]
    env["TWINE_PASSWORD"] = cfg["password"]
    if index == "testpypi":
        cmd = [PYTHON, "-m", "twine", "upload", "--repository", "testpypi", "dist/*"]
    else:
        cmd = [PYTHON, "-m", "twine", "upload", "dist/*"]
    print(f"\n  ── 3/4 上传到 {index} ──")
    return run(cmd, env=env) == 0


def verify(index: str) -> bool:
    print(f"\n  ── 4/4 验证安装 ({index}) ──")
    venv = Path.home() / ".physimx" / "tmp" / f"venv_verify_{index}"
    if venv.exists():
        import shutil

        shutil.rmtree(venv, ignore_errors=True)
    if run([PYTHON, "-m", "venv", str(venv)]) != 0:
        return False
    py = venv / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    if index == "testpypi":
        pip = [
            str(py),
            "-m",
            "pip",
            "install",
            "-q",
            "--index-url",
            "https://test.pypi.org/simple/",
            "--extra-index-url",
            "https://pypi.org/simple/",
            "flash-sim",
        ]
    else:
        pip = [str(py), "-m", "pip", "install", "-q", "flash-sim"]
    if run(pip) != 0:
        return False
    code = "import flash; print('version:', flash.__version__); from flash import FlashSimulator; print('FlashSimulator OK:', FlashSimulator(mock=True) is not None)"
    return run([str(py), "-c", code]) == 0


def main() -> None:
    ap = argparse.ArgumentParser(description="flash-sim PyPI 发布脚本")
    ap.add_argument("--build", action="store_true", help="先构建产物")
    ap.add_argument("--test", action="store_true", help="发布到 TestPyPI")
    ap.add_argument("--check", action="store_true", help="仅检查产物, 不发布")
    ap.add_argument("--no-verify", action="store_true", help="跳过安装验证")
    args = ap.parse_args()

    if args.build:
        if not build():
            sys.exit(1)
    elif not list(Path("dist").glob("*.whl")):
        print("  dist/ 为空, 自动构建...")
        if not build():
            sys.exit(1)

    if not audit():
        sys.exit(1)

    if args.check:
        print("\n  ✅ 产物检查通过, 未发布。")
        return

    index = "testpypi" if args.test else "pypi"
    if not upload(index):
        sys.exit(1)
    if not args.no_verify and not verify(index):
        print(f"  ⚠️  上传成功但安装验证失败, 请手动检查 {index}")
        sys.exit(1)
    try:
        from importlib.metadata import version
        ver = version("flash-sim")
    except Exception:
        ver = "?"
    print(f"\n  🎉 发布完成: {index} (flash-sim {ver})")


if __name__ == "__main__":
    main()
