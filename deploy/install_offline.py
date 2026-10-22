#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
install_offline.py — 离线机侧：一键离线安装
============================================================================

用途：在**无网络**的电脑上，把 U 盘里的 wheelhouse 装成本地 .venv。
本脚本是 start_flash.py --offline 的**外壳**：负责定位/校验/选择解释器，
再用环境变量驱动 start_flash.py 走离线路径。

为何需要外壳而不是直接跑 start_flash.py --offline？
  1. 解释器兜底：离线机可能**连Python 都没装**。外壳能在启动前检测到
     wheelhouse 内附的安装程序，并明确提示用户先双击安装
     （脚本**绝不**自动执行安装程序 —— 装解释器是系统级变更）。
  2. 参数友好：用户只需 `python install_offline.py [wheelhouse路径]`，
     不必记住 start_flash.py 的 --offline/--wheelhouse/--profile 组合。
  3. 语义清晰：文件名即意图，与 build_wheelhouse.py 成对。

流程:
  1. 定位 wheelhouse（显式参数 > FLASH_WHEELHOUSE > 常见位置）
  2. 校验 MANIFEST.json（存在性 + 大小 + SHA256）
  3. 选base 解释器（本机 Python → wheelhouse 内附安装程序提示）
  4. 设 FLASH_OFFLINE=1 调用 start_flash.py --offline
     （自愈重建 / 三套测试 / INSTALL_TEST_REPORT.txt 全部沿用）

用法:
  python install_offline.py# 自动找 wheelhouse/
  python install_offline.py D:\pkg\wheelhouse          # 显式指定
  python install_offline.py --profile lite             # 精简档
  python install_offline.py --check-only               # 只校验不安装
  python install_offline.py --no-tests                 # 跳过三套测试（快速装环境）
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _wh_common as wh  # noqa: E402

START_FLASH = "start_flash.py"


def log(msg: str = "") -> None:
    wh.log(msg)


def die(msg: str) -> "None":
    raise SystemExit(f"[FATAL] {msg}")


# ---------------------------------------------------------------------------
# 解释器选择
# ---------------------------------------------------------------------------

def find_base_python(root: Path) -> str | None:
    """定位可用的 base 解释器（当前解释器 → 系统 PATH 里的 python）。

    ★ 排除 venv 内的解释器：用 venv 的 python 建新 venv 会嵌套，
      start_flash.py 的 find_base_python() 也是这个判据（"envs" not in path）。
    """
    cur = sys.executable
    if cur and os.path.isfile(cur):
        norm = cur.replace("\\", "/").lower()
        # 已在 .venv 内 → 不复用（避免嵌套 venv）
        if os.path.join(str(root), ".venv").replace("\\", "/").lower() not in norm:
            return cur
    for name in ("python", "python3", "py"):
        exe = shutil.which(name)
        if exe and os.path.isfile(exe):
            return exe
    return None


def check_python_ok(exe: str) -> tuple[bool, str]:
    """验证解释器可用且版本 >= 3.10（pyproject requires-python）。"""
    r = subprocess.run([exe, "-c",
                        "import sys;print('.'.join(map(str,sys.version_info[:3])))"],
                       capture_output=True, text=True, errors="replace")
    if r.returncode != 0:
        return False, "解释器无法启动"
    ver = (r.stdout or "").strip()
    try:
        parts = tuple(int(x) for x in ver.split("."))
        if parts < (3, 10):
            return False, f"Python {ver} 过低（需 >= 3.10）"
    except ValueError:
        return False, f"无法解析版本号: {ver!r}"
    return True, ver


# ---------------------------------------------------------------------------
# 步骤
# ---------------------------------------------------------------------------

def stage_locate(args) -> wh.WheelHouse:
    log("[step 1/4] 定位 wheelhouse ...")
    if args.wheelhouse:
        p = Path(args.wheelhouse)
        if not p.is_dir():
            die(f"指定的目录不存在: {p}")
        house = wh.WheelHouse(p)
    else:
        house = wh.resolve_wheelhouse(None, start=wh.find_project_root())
    log(f"[ok] {house.root}")
    if not house.archives():
        die(f"目录内没有任何 .whl/.tar.gz：{house.root}\n"
            f"     请确认拷贝了 build_wheelhouse.py 生成的**整个 wheelhouse 目录**。")
    log(f"[ok] 发现 {len(house.archives())} 个包")
    return house


def stage_verify(house: wh.WheelHouse, root: Path, profile: str, quick: bool) -> None:
    log("")
    log("[step 2/4] 校验 wheelhouse 完整性（MANIFEST size + SHA256）...")
    problems, notes = house.verify_manifest(deep=not quick)
    for n in notes:
        log(f"[info] {n}")
    if problems:
        log("")
        log(f"[FATAL] 校验未通过，{len(problems)} 个问题：")
        for p in problems[:25]:
            log(f"        - {p}")
        if len(problems) > 25:
            log(f"        ... 另有 {len(problems) - 25} 个")
        die("U 盘拷贝过程可能损坏了文件。建议重新拷贝整个 wheelhouse 目录。")

    # 依赖覆盖度（用 pyproject 而非 MANIFEST 的 meta，因为档位可能不同）
    missing, present = house.preflight(root / "pyproject.toml", profile)
    log(f"[ok] 直接依赖覆盖: {len(present)} 项已就位")
    if missing:
        log("")
        log(f"[FATAL] 缺少 {len(missing)} 个直接依赖（档位 {profile}）：")
        for m in missing:
            log(f"        - {m}")
        die("wheelhouse 与当前档位不匹配。请在联网机用相同的 --profile 重新造包。")


def stage_interpreter(house: wh.WheelHouse, root: Path) -> str:
    log("")
    log("[step 3/4] 定位 base 解释器 ...")
    exe = find_base_python(root)
    if exe:
        ok, ver = check_python_ok(exe)
        if ok:
            log(f"[ok] {exe}  (Python {ver})")
            return exe
        log(f"[warn] 找到解释器但不可用: {exe} — {ver}")
    else:
        log("[warn] 本机未找到可用的 Python 解释器")

    inst = wh.find_python_installer(house)
    if inst:
        log("")
        log("=" * 66)
        log("  ★ wheelhouse 内含 Python 安装程序，但本机没有可用解释器")
        log("=" * 66)
        log(f"    {inst}")
        log("")
        log("  请先**双击该文件**完成 Python 安装（建议勾选 Add Python to PATH），")
        log("  安装完成后重新运行本脚本。")
        log("")
        log("  ★ 本脚本不会自动运行安装程序 —— 安装解释器属于系统级变更，")
        log("    必须由你本人确认后再执行。")
        die("等待 Python 安装完成。")

    die("找不到可用的 Python 解释器，且 wheelhouse 内未附安装程序。\n"
        "     处理：① 在联网机重跑 build_wheelhouse.py（不要加 --no-interpreter）\n"
        "           或 ② 自行安装 Python 3.10+ 后重试。")


def stage_install(root: Path, house: wh.WheelHouse, profile: str,
                  exe: str, no_tests: bool) -> int:
    log("")
    log("[step 4/4] 调用 start_flash.py 执行离线安装 ...")
    sf = root / START_FLASH
    if not sf.is_file():
        die(f"未找到 {START_FLASH}（应在 {root}）。\n"
            f"     请确认项目源码已一并拷贝到离线机。")

    env = wh.clean_env()
    env["FLASH_OFFLINE"] = "1"
    env["FLASH_WHEELHOUSE"] = str(house.root)
    env["FLASH_PROFILE"] = profile
    env["FLASH_BASE_PY"] = exe
    if no_tests:
        # start_flash.py 无独立的"跳过测试"开关，这里通过
        # 让测试目录不存在来等价跳过 —— 不改动 start_flash.py 的行为契约。
        log("[info] --no-tests：本次仅安装环境，不跑三套测试")
        env["FLASH_SKIP_TESTS"] = "1"

    cmd = [exe, str(sf), "--offline",
           "--wheelhouse", str(house.root), "--profile", profile]
    log(f"  $ {' '.join(cmd)}")
    log(f"  [env] FLASH_OFFLINE=1 FLASH_PROFILE={profile} FLASH_BASE_PY={exe}")
    log("")
    log("-" * 66)
    r = subprocess.run(cmd, cwd=str(root), env=env)
    log("-" * 66)
    return r.returncode


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        prog="install_offline.py",
        description="离线机侧一键离线安装（驱动 start_flash.py --offline）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例:\n"
            "  python install_offline.py                 自动找 wheelhouse/\n"
            "  python install_offline.py D:\\pkg\\wheelhouse   显式指定\n"
            "  python install_offline.py --profile lite     精简档\n"
            "  python install_offline.py --check-only       只校验不安装\n"
        ),
    )
    ap.add_argument("wheelhouse", nargs="?", default=None,
                    help="wheelhouse 目录（默认自动查找）")
    ap.add_argument("--profile", default="full", choices=list(wh.PROFILES),
                    help="依赖档位（须与造包时一致，默认 full）")
    ap.add_argument("--check-only", action="store_true",
                    help="只校验 wheelhouse 完整性，不执行安装")
    ap.add_argument("--quick", action="store_true",
                    help="校验时跳过 SHA256（更快，但无法发现内容损坏）")
    ap.add_argument("--no-tests", action="store_true",
                    help="仅安装环境，跳过三套测试（快速部署）")
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    root = wh.find_project_root()

    log("=" * 72)
    log("  install_offline.py — 离线机一键安装（全程不联网）")
    log("=" * 72)
    log(f"[info] 项目根: {root}")
    log(f"[info] 档位  : {args.profile} — {wh.PROFILES[args.profile]['desc']}")

    house = stage_locate(args)
    stage_verify(house, root, args.profile, args.quick)

    if args.check_only:
        log("")
        log("[ok] --check-only：校验通过，未执行安装。")
        log(f"     共 {len(house.archives())} 个包已就绪，可直接运行 install_offline.py 安装。")
        return 0

    exe = stage_interpreter(house, root)
    rc = stage_install(root, house, args.profile, exe, args.no_tests)

    log("")
    if rc == 0:
        log("[OK] 离线安装完成。")
        rep = root / "INSTALL_TEST_REPORT.txt"
        if rep.is_file():
            log(f"     报告: {rep}")
        log(f"     虚拟环境: {root / '.venv'}")
    else:
        log(f"[FAIL] start_flash.py 返回码 {rc}（详见上方输出）")
    return rc


if __name__ == "__main__":
    sys.exit(main())