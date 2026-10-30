#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
install_editable.py — PlasmaPy 源码 editable 安装器 (output_pro 托管版)

将本目录旁的 PlasmaPy vendor 快照 (src/PlasmaPy) 以 editable 模式安装进
**当前/指定 Python 环境**, 使 flash/output_pro/PlasmaPy/src/PlasmaPy 成为
plasmapy 的唯一 source of truth。

★ 2026-10-30 vendor 快照 (路线 1): 内层 .git 已移除并归档 (artifacts/),
  源码随 flash 仓库分发 (Gitee/HPC bundle); 版本号由
  SETUPTOOLS_SCM_PRETEND_VERSION_FOR_PLASMAPY 提供, 不再依赖 setuptools-scm
  的 git 描述。升级 = 替换本目录 → commit → 重跑本安装器 → 跑桥接测试。

与旧 install_from_source.sh 的区别:
  - 旧脚本把 plasmapy 装进它自己的 .venv (仅服务于旧工作区
    E:/PhySimX/PhySimX/simulation/PlasmaPy/), 不再维护;
  - 本安装器装进 **flash 包所在环境** (分析机 managed Python / .venv-win /
    WSL venv), 由 --python 显式指定目标解释器。

用法 (在仓库根执行):
  python flash/output_pro/PlasmaPy/install_editable.py                 # 装进当前解释器
  python flash/output_pro/PlasmaPy/install_editable.py --python <path> # 装进指定解释器
  python flash/output_pro/PlasmaPy/install_editable.py --check         # 只验证不安装
  python flash/output_pro/PlasmaPy/install_editable.py --uninstall     # 卸载

平台支持 (2026-10-30):
  Windows  ✅ managed Python 3.13/3.14 + .venv-win (需联网)
  WSL      ✅ 条件支持: venv 的 python 必须 >= 3.12 (FLASH_VENV_DIR 注入)
  HPC NC-E ❌ 不支持: python 3.10.8 < 3.12 闸门 + 离线 (pip 构建隔离需联网)
           + glibc 2.17 (astropy 依赖链交叉构建成本高)。
           plasmapy_bridge 会在缺失时优雅降级, HPC 上后处理请在 win/wsl 完成。
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------- 常量
_HERE = Path(__file__).resolve().parent          # .../output_pro/PlasmaPy
DEFAULT_SOURCE = _HERE / "src" / "PlasmaPy"      # 源码克隆 (source of truth)
MIN_PY = (3, 12)                                 # PlasmaPy 2026.2.0 requires-python >=3.12


def _fail(msg: str, hint: str = "") -> int:
    print(f"[install_editable] ❌ {msg}")
    if hint:
        print(hint)
    return 1


def check_source(source: Path) -> int:
    """验证 vendor 源码完整性 (editable 安装的物理前提)。

    2026-10-30 vendor 快照: 内层 .git 已移除 (归档于 artifacts/), 版本号改由
    SETUPTOOLS_SCM_PRETEND_VERSION_FOR_PLASMAPY 环境变量提供 (见 main)。
    """
    for name in ("pyproject.toml", "src/plasmapy"):
        if not (source / name).exists():
            return _fail(
                f"vendor 源码不完整: 缺少 {name}",
                f"提示: 请从 https://github.com/PlasmaPy/PlasmaPy.git "
                f"clone tag v2026.2.0 并按 DEPENDENCIES.md vendor 流程还原到 {source}",
            )
    print(f"[install_editable] ✅ vendor 源码完整: {source}")
    return 0


_SMOKE_CODE = r'''
import sys
from pathlib import Path
import astropy.units as u
import plasmapy
from plasmapy.formulary.speeds import thermal_speed

here = Path(r"__HERE__")
expected = (here / "src" / "plasmapy").resolve()
pkg_file = Path(plasmapy.__file__).resolve()
if expected not in pkg_file.parents:
    print(f"[smoke] FAIL plasmapy.__file__={pkg_file} 不在本克隆 {expected} 内")
    sys.exit(2)
v = thermal_speed(1 * u.keV, "e-")
v_expect = 1.876e7
if abs(v.si.value - v_expect) / v_expect > 0.01:
    print(f"[smoke] FAIL thermal_speed(1keV,'e-')={v} 偏离 {v_expect:.3e} 超 1%")
    sys.exit(3)
print(f"[smoke] OK plasmapy {plasmapy.__version__} @ {pkg_file}")
print(f"[smoke] OK thermal_speed(1 keV, 'e-') = {v:.4e} m/s (理论值 ~ {v_expect:.3e})")
'''.replace("__HERE__", str(_HERE))


def smoke_test(py: str) -> int:
    """安装后冒烟验证 (子进程执行 — .pth 需新解释器启动才生效)。"""
    r = subprocess.run([py, "-c", _SMOKE_CODE], capture_output=True, text=True,
                       encoding="utf-8", timeout=120)
    sys.stdout.write(r.stdout or "")
    if r.returncode != 0:
        return _fail(f"smoke test 失败 (exit={r.returncode})", (r.stderr or "").strip()[-800:])
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="PlasmaPy editable 安装器 (output_pro 托管)")
    ap.add_argument("--python", default=sys.executable, help="目标解释器 (缺省=当前)")
    ap.add_argument("--source", default=str(DEFAULT_SOURCE), help="源码克隆路径")
    ap.add_argument("--check", action="store_true", help="只验证不安装")
    ap.add_argument("--uninstall", action="store_true", help="卸载 plasmapy")
    args = ap.parse_args()

    source = Path(args.source).resolve()
    py = args.python

    # ---- 前置闸门 1: 源码克隆完整
    rc = check_source(source)
    if rc:
        return rc

    # ---- 前置闸门 2: 目标解释器版本 >= 3.12
    try:
        out = subprocess.run(
            [py, "-c", "import sys; print('%d.%d.%d' % sys.version_info[:3])"],
            capture_output=True, text=True, timeout=30,
        )
        ver = tuple(int(x) for x in out.stdout.strip().split("."))
    except Exception as exc:  # noqa: BLE001
        return _fail(f"无法探测目标解释器 {py}: {exc}")
    if ver < MIN_PY:
        return _fail(
            f"目标解释器 Python {ver[0]}.{ver[1]} < {MIN_PY[0]}.{MIN_PY[1]} "
            f"(PlasmaPy 2026.2.0 要求 >=3.12)",
            "平台指引:\n"
            "  Windows: 使用 managed Python 3.13/3.14 或 .venv-win\n"
            "  WSL:     python3.12 -m venv <dir> && export FLASH_VENV_DIR=<dir>\n"
            "  HPC:     不支持 (module python/3.10.8); 请在 win/wsl 完成后处理,\n"
            "           或未来 checkout v2024.10.0 (最后支持 py3.10 的版本) 单独评估",
        )
    print(f"[install_editable] 目标解释器: {py} (Python {ver[0]}.{ver[1]}.{ver[2]})")

    if args.check:
        return smoke_test(py)

    if args.uninstall:
        r = subprocess.run([py, "-m", "pip", "uninstall", "-y", "plasmapy"])
        return r.returncode

    # ---- 执行 editable 安装 (需联网: pip 构建隔离会取 setuptools>=77)
    # vendor 快照无 .git → setuptools-scm 版本号用 pretend 环境变量提供
    # (PEP 517 项目名规范化: PlasmaPy → PLASMAPY)
    print(f"[install_editable] 开始 editable 安装: {source}")
    print("[install_editable] (需联网; HPC 离线环境会被上方版本闸门拦下)")
    env = dict(os.environ)
    env["SETUPTOOLS_SCM_PRETEND_VERSION_FOR_PLASMAPY"] = "2026.2.0"
    env.setdefault("SETUPTOOLS_SCM_PRETEND_VERSION", "2026.2.0")
    r = subprocess.run([py, "-m", "pip", "install", "-e", str(source)], env=env)
    if r.returncode != 0:
        return _fail(
            "pip install -e 失败",
            "排查: ① 网络/代理是否可用 (构建隔离需从 PyPI 取 setuptools);\n"
            "     ② 目标环境 pip 版本 >= 21.3 (PEP 660 editable);\n"
            "     ③ 若 bootstrap 构建报 setuptools 版本, 升级: <python> -m pip install -U pip setuptools",
        )

    return smoke_test(py)


if __name__ == "__main__":
    sys.exit(main())
