#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
build_wheelhouse.py — 联网机侧：造离线安装包（wheelhouse）
============================================================================

用途：在**有网络**的电脑上把 flash 及其全部依赖下载成一个自包含目录，
拷到 U 盘，带到**无网络**的电脑上用 start_flash.py --offline 安装。

流程:
  1. 构建 flash 本体 wheel（python -m build --wheel）
     ★ 绝不能沿用线上 `-e git+https://gitee.com/...` 的 editable 装法
  2. pip download 全部依赖闭包（与当前平台/ Python 版本严格匹配）
  3. 可选下载 Python 安装程序（离线机没Python 时需要）
  4. 写 MANIFEST.json（每个文件 size + SHA256）
  5. 可选打包成单个 zip 便于 U 盘拷贝

★ 关键设计：
  - 依赖用 `pip download` 而非手写清单 —— 由 pip 自己解算**完整传递闭包**。
    当前 .venv 实际 69 个包，而 pyproject 直接依赖只有 18 个；手写清单必然漏包。
  - 用 `pip download` 的解析结果**交叉校验** _wh_common 的预检清单，
    两边不一致就报错（见verify_against_pip）。
  - 默认 --only-binary=:all:，避免离线机需要编译 C 扩展（无编译器必失败）。
    若某包确实只有 sdist，会明确报出而不是产出坏包。

用法:
  python build_wheelhouse.py                      # full 档 + Python 安装程序
  python build_wheelhouse.py --profile runtime    # 精简（保留 yt 出图）
  python build_wheelhouse.py --profile lite       # 最精简
  python build_wheelhouse.py --out D:\pkg         # 指定输出目录
  python build_wheelhouse.py --no-interpreter     # 不下载 Python 安装程序
  python build_wheelhouse.py --zip                # 额外打成 zip
  python build_wheelhouse.py --dry-run           # 只打印计划，不下载

输出:
  <out>/wheelhouse/            ← 拷这个目录到 U 盘
     flash_sim-0.1.7-py3-none-any.whl
     numpy-*.whl / scipy-*.whl / yt-*.whl / ...
     python-3.13.9-amd64.exe     （可选）
     MANIFEST.json
"""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _wh_common as wh  # noqa: E402


# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

DEFAULT_OUT = "offline_pkg"
WH_DIRNAME = "wheelhouse"

#: Python 安装程序下载源（仅 --with-interpreter 时使用）
PYTHON_URL_TMPL = "https://www.python.org/ftp/python/{ver}/python-{ver}-amd64.exe"


def log(msg: str = "") -> None:
    wh.log(msg)


def die(msg: str) -> "None":
    raise SystemExit(f"[FATAL] {msg}")


def run(cmd: list, cwd=None, timeout=3600, check=True) -> subprocess.CompletedProcess:
    """执行子进程，实时回显（下载过程不能黑屏）。"""
    log(f"  $ {' '.join(str(c) for c in cmd)}")
    try:
        r = subprocess.run(
            cmd, cwd=cwd, env=wh.clean_env(),
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        die(f"命令超时（{timeout}s）: {' '.join(cmd[:3])}")
    if check and r.returncode != 0:
        log("")
        log(f"  [stderr 尾部]")
        for ln in (r.stderr or "").strip().splitlines()[-25:]:
            log("    " + ln)
        die(f"命令失败 rc={r.returncode}: {' '.join(cmd[:3])}")
    return r


# ---------------------------------------------------------------------------
# Step 1: 构建 flash 本体 wheel
# ---------------------------------------------------------------------------

def build_project_wheel(root: Path, out_dir: Path, dry_run: bool) -> Path | None:
    """构建 flash_sim-*.whl。

    ★ 用 `python -m build --wheel --no-isolation`：--no-isolation 复用当前
      解释器已装好的 hatchling，避免 build 过程再去联网拉构建依赖
      （构建机通常有网，但保持"一次成型"更稳，且离线机复现时同理）。
    """
    log("")
    log("[step 1/5] 构建 flash 本体 wheel ...")
    if dry_run:
        log(f"[dry-run]将执行: python -m build --wheel --no-isolation -o <out>/{WH_DIRNAME}")
        return None

    # build 模块可能未安装
    r = subprocess.run([sys.executable, "-c", "import build"],
                       env=wh.clean_env(), capture_output=True)
    if r.returncode != 0:
        log("[info] 未安装 build 模块，先安装 ...")
        run([sys.executable, "-m", "pip", "install", "--upgrade", "build", "wheel"])

    r = subprocess.run(
        [sys.executable, "-c", "import hatchling"],
        env=wh.clean_env(), capture_output=True)
    if r.returncode != 0:
        log("[info] 未安装 hatchling（pyproject 的构建后端），先安装 ...")
        run([sys.executable, "-m", "pip", "install", "hatchling"])

    out_dir.mkdir(parents=True, exist_ok=True)
    log("[info] python -m build --wheel --no-isolation（可能需 1~3 分钟）...")
    r = run([sys.executable, "-m", "build", "--wheel", "--no-isolation",
             "-o", str(out_dir)], cwd=root, timeout=1800, check=False)

    wheels = sorted(out_dir.glob("flash_sim-*.whl"))
    if not wheels:
        # 退路：直接从已构建的 dist/ 拿（若历史遗留）
        legacy = sorted((root / "dist").glob("flash_sim-*.whl"))
        if legacy:
            log(f"[warn] build 未产出 wheel，改用已有 {legacy[-1].name}")
            shutil.copy2(legacy[-1], out_dir / legacy[-1].name)
            return out_dir / legacy[-1].name
        die("未能构建 flash_sim wheel。请检查上方 build 输出。"
            "注意 pyproject 用 hatchling，磁盘需有写权限。")

    w = wheels[-1]
    log(f"[ok] 本体 wheel: {w.name}  ({wh.human_size(w.stat().st_size)})")
    return w


# ---------------------------------------------------------------------------
# Step 2: 下载依赖闭包
# ---------------------------------------------------------------------------

def build_pip_freeze_list(root: Path, wh_dir: Path, profile: str) -> list[str]:
    """返回传给 `pip download` 的 requirement 列表（**含项目本体**）。

    结构: "flash_sim[full,dev]" + pyproject base/extras 全量 + scipy/paramiko 等补装项。

    ★ 项目本体用**本地刚构建的 wheel**参与解析，靠 `--find-links <wh_dir>`
      让 pip 从本地取到它，从而顺带把 base/extras 的传递闭包全部解析下载。
      （若不传 flash_sim，pip 只会下scipy/paramiko 等少数几项，
        h5py/matplotlib/yt/pandas/pytest 会**整批缺失** —— 这是必须显式
        带上本体的根本原因。）

    ★ scipy / paramiko 未写进 pyproject 的 full/dev extras（paramiko 是
      remote_deploy 的 SSH 依赖），但 start_flash.py 会装，必须在此补齐。
    """
    spec = wh.PROFILES[profile]
    _, human = wh.required_packages(root / "pyproject.toml", profile)

    reqs: list[str] = []
    # 第 1 项是 _wh_common 插入的 project 本体（带 extras）
    for r in human:
        name = wh.requirement_name(r)
        if name == wh.canonical_name(wh.PROJECT_DIST):
            reqs.append(r)
            break
    # 其余直接依赖（去重，保持 pyproject 声明顺序）
    seen = {wh.canonical_name(wh.PROJECT_DIST)}
    for r in human:
        n = wh.canonical_name(wh.requirement_name(r))
        if n in seen:
            continue
        seen.add(n)
        reqs.append(r)
    # 补装项（scipy/paramiko/setuptools/wheel/pip）—— 去重后追加
    for p in spec["extra_pkgs"]:
        if wh.canonical_name(p) not in seen:
            seen.add(wh.canonical_name(p))
            reqs.append(p)
    return reqs


def download_deps(out_dir: Path, pkgs: list[str], python_exe: str,
                  dry_run: bool, no_binary: bool = False) -> None:
    """pip download 全部依赖到 out_dir。

    ★ --find-links <out_dir>：让 pip 能从**本地刚构建的 flash_sim wheel**
      解析项目本体，从而顺带解出 base/extras 的全部传递依赖。
      此时不加 --no-index（还需从 PyPI 下载第三方包）。

    ★ --upgrade 不能用：`pip download` **不支持**该选项（只有 install 有），
      传入会直接 rc=2 报 "no such option: --upgrade"。
      无需担心版本陈旧——`pip download` 本来就按索引取**最新**匹配版本，
      不像 `pip install` 那样受本机已装版本约束。

    ★ --only-binary=:all:：默认只要 wheel。离线机通常没有 C 编译器，
      若给到 sdist 会编译失败 → 整批报废。少数纯 sdist 包可用 --allow-sdist 放宽。
    """
    log("")
    log(f"[step 2/5] 下载依赖闭包（{len(pkgs)} 个直接依赖 + 全部传递依赖）...")
    cmd = [python_exe, "-m", "pip", "download",
           "--dest", str(out_dir),
           "--find-links", str(out_dir),
           "--disable-pip-version-check"]
    if not no_binary:
        cmd.append("--only-binary=:all:")
    cmd += pkgs
    if dry_run:
        log(f"[dry-run] 将执行: {' '.join(cmd)}")
        return
    log("[info] 下载中（yt/numba/matplotlib 体积大，约 5~15 分钟）...")
    t0 = time.time()
    run(cmd, timeout=5400)
    log(f"[ok] 下载完成，耗时 {time.time() - t0:.0f}s")


# ---------------------------------------------------------------------------
# Step 3: Python 安装程序（可选）
# ---------------------------------------------------------------------------

def download_python_installer(out_dir: Path, version: str, dry_run: bool) -> None:
    """下载 Windows Python 安装程序到 out_dir（离线机无 Python 时用）。

    ★ 只在 Windows 造包时有意义；且**不会**在离线机自动执行 ——
      装解释器是系统级变更，必须用户亲自双击确认。
    """
    log("")
    log("[step 3/5] 下载 Python 安装程序 ...")
    if sys.platform != "win32":
        log(f"[skip] 当前平台 {sys.platform} 非 Windows，无需 Windows 安装程序")
        return
    url = PYTHON_URL_TMPL.format(ver=version)
    fname = f"python-{version}-amd64.exe"
    dest = out_dir / fname
    if dest.is_file():
        log(f"[ok] 已存在: {fname}")
        return
    if dry_run:
        log(f"[dry-run] 将下载: {url}")
        return
    import urllib.request
    log(f"[info] {url}")
    try:
        with urllib.request.urlopen(url, timeout=120) as r, open(dest, "wb") as f:
            shutil.copyfileobj(r, f, 1 << 20)
    except Exception as e:
        log(f"[warn] 下载失败: {e}")
        log(f"       请手动下载 {url} 并放入: {out_dir}")
        return
    log(f"[ok] Python 安装程序: {fname} ({wh.human_size(dest.stat().st_size)})")


# ---------------------------------------------------------------------------
# Step 4: MANIFEST + 交叉校验
# ---------------------------------------------------------------------------

def git_sha(root: Path) -> str:
    r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root,
                       capture_output=True, text=True)
    return r.stdout.strip()[:12] if r.returncode == 0 else "N/A"


def verify_against_pip(wh_dir: Path, root: Path, profile: str) -> None:
    """用 _wh_common 的预检清单交叉校验 wheelhouse 实际内容。

    这是"预检逻辑"与"造包逻辑"的闭环：若二者对依赖的理解不一致
    （例如某个包名归一化写错），这里立刻暴露，而不是等到离线机上才发现。
    """
    log("")
    log("[step 4/5] 交叉校验预检清单 vs wheelhouse 实际内容 ...")
    house = wh.WheelHouse(wh_dir)
    missing, present = house.preflight(root / "pyproject.toml", profile)
    log(f"[ok] 直接依赖覆盖: {len(present)}/{len(present) + len(missing)} 已就位")
    if missing:
        log("[FATAL] 造包后自检仍缺以下直接依赖（造包逻辑有BUG，请反馈）:")
        for x in missing:
            log(f"        - {x}")
        die("自检未通过 —— 产出的 wheelhouse 不能交付，请勿拷贝到离线机。")


def write_manifest(wh_dir: Path, root: Path, profile: str, interpreter: str) -> Path:
    log("")
    log("[step 5/5] 生成 MANIFEST.json（size + SHA256 全清单）...")
    house = wh.WheelHouse(wh_dir)
    meta = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "profile": profile,
        "profile_desc": wh.PROFILES[profile]["desc"],
        "project_dist": wh.PROJECT_DIST,
        "project_version": _project_version(root),
        "git_sha": git_sha(root),
        "python_version": interpreter,
        "platform": f"{platform.system()}-{platform.machine()}",
        "pip_flags": list(wh.OFFLINE_PIP_FLAGS) if hasattr(wh, "OFFLINE_PIP_FLAGS")
                     else ["--no-index"],
    }
    p = house.write_manifest(meta)
    man = house.read_manifest()
    log(f"[ok] {p.name}: {len(man['entries'])} 个条目")
    return p


def _project_version(root: Path) -> str:
    import re
    txt = (root / "pyproject.toml").read_text(encoding="utf-8")
    m = re.search(r'^version\s*=\s*"([^"]+)"', txt, re.M)
    return m.group(1) if m else "unknown"


# ---------------------------------------------------------------------------
# Step 5: 打包 zip（可选）
# ---------------------------------------------------------------------------

def make_zip(wh_dir: Path, dry_run: bool) -> Path | None:
    log("")
    log("[extra] 打包为 zip（便于 U 盘拷贝）...")
    zip_path = wh_dir.parent / f"{WH_DIRNAME}.zip"
    if dry_run:
        log(f"[dry-run] 将打包: {zip_path}")
        return None
    import zipfile
    files = [p for p in wh_dir.iterdir() if p.is_file()]
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for i, p in enumerate(files, 1):
            z.write(p, arcname=f"{WH_DIRNAME}/{p.name}")
            if i % 20 == 0:
                log(f"  ... {i}/{len(files)}")
    log(f"[ok] {zip_path}  ({wh.human_size(zip_path.stat().st_size)})")
    return zip_path


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        prog="build_wheelhouse.py",
        description="联网机侧造离线安装包（wheelhouse）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例:\n"
            "  python build_wheelhouse.py                    full 档 + Python 安装程序\n"
            "  python build_wheelhouse.py --profile runtime  精简（保留 yt 出图）\n"
            "  python build_wheelhouse.py --no-interpreter   不下载 Python 安装程序\n"
            "  python build_wheelhouse.py --zip              额外打成 zip\n"
            "  python build_wheelhouse.py --dry-run          只打印计划\n"
        ),
    )
    ap.add_argument("--out", default=None,
                    help=f"输出根目录（默认 <项目根>/{DEFAULT_OUT}）")
    ap.add_argument("--profile", default="full", choices=list(wh.PROFILES),
                    help="依赖档位（默认 full）")
    ap.add_argument("--no-interpreter", action="store_true",
                    help="不下载 Python 安装程序（离线机已有 Python 时用）")
    ap.add_argument("--python-version", default=None,
                    help="Python 安装程序版本（默认取当前 sys.version）")
    ap.add_argument("--allow-sdist", action="store_true",
                    help="允许 sdist（默认只要 wheel；离线机通常无 C 编译器）")
    ap.add_argument("--zip", action="store_true", help="打包为 zip")
    ap.add_argument("--dry-run", action="store_true", help="只打印计划，不实际下载")
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    root = wh.find_project_root()
    out_root = Path(args.out) if args.out else (root / DEFAULT_OUT)
    wh_dir = out_root / WH_DIRNAME
    wh_dir.mkdir(parents=True, exist_ok=True)

    log("=" * 72)
    log("  build_wheelhouse.py — 联网机造离线安装包")
    log("=" * 72)
    log(f"[info] 项目根: {root}")
    log(f"[info] 输出  : {wh_dir}")
    log(f"[info] 档位  : {args.profile} — {wh.PROFILES[args.profile]['desc']}")
    log(f"[info] Python : {platform.python_version()} "
        f"({platform.system()}-{platform.machine()})")

    t0 = time.time()

    # ---- 依赖清单 ----
    pkgs = build_pip_freeze_list(root, wh_dir, args.profile)
    log("")
    log(f"[info] 直接依赖: {' '.join(pkgs)}")

    # ---- Step 1 ----
    build_project_wheel(root, wh_dir, args.dry_run)

    # ---- Step 2 ----
    download_deps(wh_dir, pkgs, sys.executable, args.dry_run,
                  no_binary=args.allow_sdist)

    # ---- Step 3 ----
    if not args.no_interpreter:
        pyver = args.python_version or platform.python_version()
        download_python_installer(wh_dir, pyver, args.dry_run)

    # ---- Step 4: 自检 + 清单 ----
    if not args.dry_run:
        verify_against_pip(wh_dir, root, args.profile)
        write_manifest(wh_dir, root, args.profile, platform.python_version())

        # 汇总
        house = wh.WheelHouse(wh_dir)
        total = sum(p.stat().st_size for p in house.archives())
        log("")
        log("=" * 72)
        log(f"  完成: {len(house.archives())} 个包,共 {wh.human_size(total)}")
        log(f"  耗时  : {time.time() - t0:.0f}s")
        log("=" * 72)
        log("")
        log("下一步:")
        log(f"  1) 把整个目录拷到 U 盘: {wh_dir}")
        log("     ★ 必须**整个目录**一起拷（含 MANIFEST.json），不能只拷 .whl")
        log("  2) 连同项目源码一起拷（可另用 scripts\\04_backup\\usb_backup.py）")
        log("  3) 离线机上双击 install_offline.bat，或执行:")
        log(f"       python start_flash.py --offline --wheelhouse <U盘路径>\\{WH_DIRNAME}")

        if args.zip:
            make_zip(wh_dir, args.dry_run)
    else:
        log("")
        log("[dry-run] 以上为计划，未实际下载。去掉 --dry-run 执行真实造包。")

    return 0


if __name__ == "__main__":
    sys.exit(main())