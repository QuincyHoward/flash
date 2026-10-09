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

def build_project_wheel(root: Path, out_dir: Path, dry_run: bool,
                        allow_legacy_dist: bool = False) -> Path | None:
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

    # ★ 关键：**构建前**先隔离 out_dir 里的旧 wheel，只认本次构建的产物。
    #   build 可能 rc!=0 而没产出任何东西，此时残留的旧 wheel 会被随后的
    #   glob 命中并当成成功返回（09-10 实测：把 9-08 的旧 wheel 写进了
    #   MANIFEST，该 wheel 少 2650 个文件）。必须挪走而不是删除，
    #   以便用户还能手工比对。
    _quarantine_previous_wheels(out_dir)

    log("[info] python -m build --wheel --no-isolation（可能需 1~3 分钟）...")
    r = run([sys.executable, "-m", "build", "--wheel", "--no-isolation",
             "-o", str(out_dir)], cwd=root, timeout=1800, check=False)

    wheels = sorted(out_dir.glob("flash_sim-*.whl"))

    if not wheels:
        #退路：dist/ 里的历史 wheel。★ 必须显式 --allow-legacy-dist 才准用。
        #   09-10 事故：build 失败后此处静默 copy 了 9-08 的旧 wheel，
        #   该 wheel 少 2650 个文件（含 flash/_core/credentials/hpc_config.py），
        #   且体积 1.5MB vs 正常 4.8MB —— 不查体积根本发现不了。
        legacy = sorted((root / "dist").glob("flash_sim-*.whl"))
        if legacy and allow_legacy_dist:
            log(f"[warn] 使用 dist/ 遗留 wheel: {legacy[-1].name}")
            log("       ⚠ 该wheel 可能是旧代码构建，务必确认与当前源码一致！")
            shutil.copy2(legacy[-1], out_dir / legacy[-1].name)
            return out_dir / legacy[-1].name
        if legacy:
            die("build 未产出 wheel，而 dist/ 里有历史遗留 wheel。\n"
                "    为避免把**旧代码**误当成当前版本发布，已中止。\n"
                "    请先排查上方 build 报错（常见：磁盘满 / pyproject 语法错 /\n"
                "    exclude 规则把包全排除了）。确需使用旧 wheel 时显式加\n"
                "    --allow-legacy-dist。")
        die("未能构建 flash_sim wheel。请检查上方 build 输出。"
            "注意 pyproject 用 hatchling，磁盘需有写权限。")

    w = wheels[-1]
    _warn_if_implausible_size(w, root)
    log(f"[ok] 本体 wheel: {w.name}  ({wh.human_size(w.stat().st_size)})")
    # 记录指纹：Step 2 的 pip download 可能用 PyPI 同名包覆盖它（见下）
    _LOCAL_WHEEL_FINGERPRINT.clear()
    _LOCAL_WHEEL_FINGERPRINT.update(
        sha256=wh.sha256_file(w),
        size=w.stat().st_size,
        entries=_wheel_entry_count(w),
    )
    log(f"[info] 本体 wheel 指纹: sha256={_LOCAL_WHEEL_FINGERPRINT['sha256'][:16]} "
        f"size={wh.human_size(_LOCAL_WHEEL_FINGERPRINT['size'])} "
        f"entries={_LOCAL_WHEEL_FINGERPRINT['entries']}")
    return w


#: Step 1 记录的本地 wheel 指纹（Step 2 后据此校验未被 PyPI 覆盖）
_LOCAL_WHEEL_FINGERPRINT: dict = {}


#: 正常 wheel 体积区间（09-10 实测 4.76MB；>20MB 说明 exclude 又漏了）
WHEEL_SIZE_OK = (1 * 1024 * 1024, 20 * 1024 * 1024)


def _quarantine_previous_wheels(out_dir: Path) -> None:
    """把 out_dir 里**已存在**的 flash_sim wheel 挪进 .stale/。

    ★ 为什么必须隔离而不是直接删：造包中断后重跑时，若build 这轮没产出，
      `sorted(out_dir.glob("flash_sim-*.whl"))` 会命中上一轮的包并当成功返回
      —— 09-10 实测就是这样把 9-08 的旧 wheel（少 2650 个文件）写进了
      MANIFEST。挪走而非删除，是为了让用户还能手工比对。
    """
    olds = sorted(out_dir.glob("flash_sim-*.whl"))
    if not olds:
        return
    q = out_dir / ".stale"
    q.mkdir(parents=True, exist_ok=True)
    for old in olds:
        stamp = time.strftime("%Y%m%d_%H%M%S", time.localtime(old.stat().st_mtime))
        dest = q / f"{old.stem}__{stamp}{old.suffix}"
        shutil.move(str(old), str(dest))
        log(f"  [stale] 已隔离上一轮产物 -> .stale/{dest.name}")


def _warn_if_implausible_size(w: Path, root: Path) -> None:
    """体积哨兵：GB 级 = exclude 漏了大目录；<1MB = 可能是残包/旧包。"""
    sz = w.stat().st_size
    if sz > WHEEL_SIZE_OK[1]:
        log(f"[WARN] wheel 体积 {wh.human_size(sz)} 偏大 —— 检查 pyproject exclude"
            " 是否漏了新场景目录。")
    elif sz < WHEEL_SIZE_OK[0]:
        log(f"[WARN] wheel 体积 {wh.human_size(sz)} 偏小 —— 确认包内容完整。")
    pyproject = root / "pyproject.toml"
    if pyproject.is_file() and w.stat().st_mtime < pyproject.stat().st_mtime:
        log("[WARN] wheel 比 pyproject.toml 还旧 ⇒  exclude 改动可能未生效。")


# ---------------------------------------------------------------------------
# Step 2: 下载依赖闭包
# ---------------------------------------------------------------------------

def build_pip_freeze_list(root: Path, wh_dir: Path, profile: str) -> list[str]:
    """返回传给 `pip download` 的 requirement 列表（**不含项目本体**）。

    ★★ 09-10 事故：本体**不能**进 `pip download` 的目标列表。本项目已发布在
      PyPI（flash-sim 0.1.7），而 `--find-links` **不保证本地优先** ——
      pip 会以"bad hash. Re-downloading."为由下载公开旧包**覆盖**本地构建
      产物（实测 4.76MB/902 条目 → 1.53MB/224 条目，712 个文件消失）。
      ⇒ 正确做法：把 pyproject 的 base + extras **全部展开后逐项列出**，
      让 pip 只解析第三方依赖；本体 wheel 由 Step 1 直接放进 wheelhouse，
      根本不经过 pip。

    ★ 为什么"不传本体"曾经导致整批缺包（09-09）：当时只传了 extra_pkgs
      （scipy/paramiko 等少数项），h5py/matplotlib/yt/pandas/pytest 全缺。
      现在 `required_packages()` 返回的 human 列表**已含 base + extras 全量
      展开**，逐项传给 pip 即可拿全 71 个包的传递闭包，无需借助本体解析。

    ★ scipy / paramiko 未写进 pyproject 的 full/dev extras（paramiko 是
      remote_deploy 的 SSH 依赖），但 start_flash.py 会装，必须在此补齐。
    """
    spec = wh.PROFILES[profile]
    _, human = wh.required_packages(root / "pyproject.toml", profile)

    proj = wh.canonical_name(wh.PROJECT_DIST)
    reqs: list[str] = []
    seen: set[str] = set()
    for r in human:
        n = wh.canonical_name(wh.requirement_name(r))
        if n == proj or n in seen:
            continue          # ★ 跳过本体（见上方事故说明）
        seen.add(n)
        reqs.append(r)

    # 补装项：pyproject 未声明但 start_flash.py 会装的包
    for p in spec.get("extra_pkgs", []):
        n = wh.canonical_name(p)
        if n not in seen:
            seen.add(n)
            reqs.append(p)
    return reqs


def download_deps(out_dir: Path, pkgs: list[str], python_exe: str,
                  dry_run: bool, no_binary: bool = False,
                  local_wheel: Path | None = None) -> None:
    """pip download 全部依赖到 out_dir。

    ★ --find-links <out_dir>：让 pip 能从**本地刚构建的 flash_sim wheel**
      解析项目本体，从而顺带解出 base/extras 的全部传递依赖。
      此时不加 --no-index（还需从 PyPI 下载第三方包）。

    ★★ `--find-links` **不保证本地优先**（09-10 实测踩坑）：
      flash-sim 0.1.7 已发布在 **PyPI**（1.53MB）。pip 解析
      `flash_sim[full,dev]` 时会认为 PyPI 上那个同样满足要求，于是
      **下载并覆盖掉我们刚构建的 wheel** —— 日志仍打印"[ok] 4.8 MB"
      （那是覆盖前的体积），而目录里已是 1.53MB 的公开旧包。
      后果：离线机安静地装上一份**过期的公开代码**，且体积/条目数
      都不对（224 vs 902 条目）。仅看体积或日志都发现不了。
      ⇒ 对策：下载结束后**用 SHA256 校验本地 wheel 仍在**，
      被覆盖就立即报错（见_ensure_local_wheel_intact）。

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
    _ensure_local_wheel_intact(local_wheel)
    log(f"[ok] 下载完成，耗时 {time.time() - t0:.0f}s")


def _ensure_local_wheel_intact(local_wheel: Path | None) -> None:
    """确认本地构建的 flash_sim wheel 没被 PyPI 同名包覆盖（09-10 事故）。

    用 **SHA256 指纹**比对，而非只看体积 —— 同名同版本的覆盖包体积可能
    接近，只有指纹能给出确定结论。
    """
    if local_wheel is None or not local_wheel.is_file():
        return
    fp = _LOCAL_WHEEL_FINGERPRINT
    if not fp:
        return
    now_sha = wh.sha256_file(local_wheel)
    n_entries = _wheel_entry_count(local_wheel)
    log(f"[info] 本体 wheel 校验: sha256={now_sha[:16]} "
        f"size={wh.human_size(local_wheel.stat().st_size)} entries={n_entries}")
    if now_sha != fp["sha256"]:
        die("本体 wheel 在下载依赖后**被覆盖**了！\n"
            f"    构建时 sha256={fp['sha256'][:16]} / {fp['entries']} 条目 / "
            f"{wh.human_size(fp['size'])}\n"
            f"    现在 sha256={now_sha[:16]} / {n_entries} 条目 / "
            f"{wh.human_size(local_wheel.stat().st_size)}\n"
            "    原因：`pip download flash_sim[full,dev]` 只用 --find-links 提供\n"
            "    本地包，但该选项**不保证本地优先**；本项目已发布在 PyPI\n"
            "    （flash-sim 0.1.7），pip 会下载公开旧包覆盖本地构建结果。\n"
            "    ⇒ 离线机将会装上**过期公开代码**。\n"
            "    对策：① 临时提升 pyproject 版本号（如 0.1.8）使 PyPI 版本\n"
            "         不再满足要求；或② 造包后手动把本地 wheel 拷回覆盖。")
    # 条目数哨兵：只在**能读出条目数**时生效（entries=-1 表示非 zip/读失败），
    # 否则会把单测里的小文件误判成残包。
    if 0 <= n_entries < 100:
        die(f"本体 wheel 只有 {n_entries} 个条目，明显是残包/旧包，已中止。")


def _wheel_entry_count(w: Path) -> int:
    try:
        import zipfile
        with zipfile.ZipFile(w) as z:
            return len(z.namelist())
    except Exception:
        return -1


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


def run_leak_audit(wh_dir: Path, root: Path, strict: bool) -> bool:
    """构建后跑泄漏审计（体积/条目/§3/git-ignored 四项）。

    ★ 为什么必须有这一步：根`.gitignore:11` 的裸`*` 会触发 hatchling 的
      VCS 排除安全阀（`if exclude_spec.match_file(self.root): return []`），
      **536 条 .gitignore 规则全部失效** ⇒ git 忽略的测试产物、FLASH 引擎
      源码（License §3）会被打进 wheel。09-10 实测泄漏 336.8MB / 94.5%。
    ★ 为什么审计器本身要能失败：本项目已栽过两次「护栏自己骗我」
      ——审计器用 text=True 漏报 94.5%、§3 用子串匹配误报自研文档。
      故审计器自带负向自测，且此处按其退出码决定是否中止。
    """
    audit_py = Path(__file__).resolve().parent / "wheel_leak_audit.py"
    if not audit_py.is_file():
        log("[warn] 未找到 wheel_leak_audit.py，跳过泄漏审计")
        return True
    log("")
    log("[audit] 泄漏审计（体积 / 条目 / License §3 / git-ignored）...")
    r = run([sys.executable, str(audit_py), str(wh_dir)],
            cwd=root, timeout=600, check=False)
    if r.returncode == 0:
        log("[ok] 泄漏审计通过")
        return True
    msg = (r.stdout or "")[-800:]
    if strict:
        die("泄漏审计未通过 —— wheel 里混入了 git 忽略的文件或 FLASH 版权材料。\n"
            "    详见上方报告；修法：在 pyproject.toml 的 wheel/sdist exclude 中\n"
            "    补规则（★ 必须 wheel 与 sdist **成对**写），或用 --no-audit 临时跳过。\n"
            f"---- 审计输出尾部 ----\n{msg}")
    log("[warn] 泄漏审计未通过，但已指定 --no-audit ⇒ 继续（风险自负）")
    return False


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
    ap.add_argument("--allow-legacy-dist", action="store_true",
                    help="build 失败时允许退回 dist/ 里的旧 wheel（★危险："
                         "旧 wheel 可能缺文件，09-10 事故根因）")
    ap.add_argument("--dry-run", action="store_true", help="只打印计划，不实际下载")
    ap.add_argument("--no-audit", action="store_true",
                    help="跳过构建后的泄漏审计（★不建议：.gitignore 因裸`*` "
                         "安全阀而对 wheel 完全失效，无审计等于裸奔）")
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
    local_wheel = build_project_wheel(root, wh_dir, args.dry_run,
                                      allow_legacy_dist=args.allow_legacy_dist)

    # ---- Step 2 ----
    download_deps(wh_dir, pkgs, sys.executable, args.dry_run,
                  no_binary=args.allow_sdist, local_wheel=local_wheel)

    # ---- Step 3 ----
    if not args.no_interpreter:
        pyver = args.python_version or platform.python_version()
        download_python_installer(wh_dir, pyver, args.dry_run)

    # ---- Step 4: 自检 + 清单 ----
    if not args.dry_run:
        verify_against_pip(wh_dir, root, args.profile)
        write_manifest(wh_dir, root, args.profile, platform.python_version())

        # ★ Step 4.5: 泄漏审计（必须在写完清单后、宣布成功前）
        run_leak_audit(wh_dir, root, strict=not args.no_audit)

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