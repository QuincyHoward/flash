#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_wheelhouse_linux.py — Step 03: 在 Windows 联网机上交叉造 Linux wheelhouse。

★ 背景：scripts/08_offline_install/build_wheelhouse.py 只支持"当前平台"造包
  （无 --platform 参数，MANIFEST 平台标记取当前解释器），传到 Linux 超算会被
  _wh_common.platform_check() 拦死。本脚本复用其公共层（_wh_common），
  用 pip download 的 --platform/--python-version/--abi 交叉下载 manylinux wheel。

五步流程（对齐 build_wheelhouse.py，事故教训全部内置）：
  1. 本体 wheel 复用 dist/flash_sim-*.whl（py3-none-any 跨平台），
     记 SHA256/体积/条目数指纹；★ 本体绝不进 pip download 列表
     （09-10 事故：--find-links 不保证本地优先，PyPI 同名旧包会覆盖本地构建）。
  2. pip download 依赖闭包（manylinux2014 + manylinux_2_28 双平台，
     cp310/py3.10），--only-binary=:all:；jeepney/secretstorage 手动补
     （Windows 上 platform_extra_pkgs() 返回空）。
  3. 指纹复核（SHA256 防 PyPI 覆盖）+ 平台断言（无 win_amd64、含垫片包）。
  4. 写 MANIFEST.json，meta 显式 platform_tag="linux" / python_tag="3.10"
     （★ 必须显式，不能取当前平台）。
  5. 交叉校验（preflight 覆盖度）+ wheel_leak_audit.py 泄漏审计（退出码判定）。

判据: MANIFEST 存在、覆盖度 100%、审计 rc=0、本体 wheel 仍为 MB 级。
回退: 删 wheelhouse-linux/ 重跑本脚本。
"""
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEST_DIR = HERE.parent
REPO_ROOT = TEST_DIR.parents[3]
LOG_DIR = TEST_DIR / "logs"
PKG_DIR = TEST_DIR / "packages"
WH_DIR = PKG_DIR / "wheelhouse-linux"

sys.path.insert(0, str(REPO_ROOT / "scripts" / "08_offline_install"))
import _wh_common as wh  # noqa: E402

PLATFORMS = ["manylinux2014_x86_64", "manylinux_2_28_x86_64"]
PY_VERSION = "3.10"
PY_ABIS = ["cp310", "abi3"]

# ★ glibc 上限锁定（2026-10-22 实测：NC-E = CentOS 7 / glibc 2.17 / pip 22.2.2，
#   最高支持 manylinux_2_17）。以下包的最新版只发 >2_17 的 wheel，必须锁定到
#   最后一个带 cp310+manylinux_2_17 的版本（均已核实满足 pyproject 约束）。
#   若未来 pyproject 升级依赖，重造包时 glibc 审计（见下）会自动拦截新违约者。
GLIBC_MAX_TAG = "manylinux_2_17_x86_64"
ALLOWED_LOW_TAGS = {"any", "manylinux1_x86_64", "manylinux2010_x86_64",
                    "manylinux2014_x86_64", "manylinux_2_17_x86_64", "linux_x86_64"}
VERSION_PINS = {
    "pandas": "2.3.2",           # 2.3.3 只发 2_24+
    "h5py": "3.14.0",            # 3.15/3.16 只发 2_28
    "pillow": "12.2.0",          # 12.3 只发 2_27+
    "ewah-bool-utils": "1.2.2",  # 1.3.0 只发 2_24（yt 依赖，兼容 yt 4.4）
    # ★ yt 4.3.1 在 NC-E（CentOS7/glibc2.17，登录+计算节点均复现）import 即
    #   SIGSEGV；4.1.4/4.3.0 为 numpy1 构建与 numpy2 ABI 冲突（干净报错）。
    #   4.4.0（numpy2 构建，requires-python>=3.10.3，cp310+manylinux_2_17）
    #   实测 2026-10-22 超算 import OK + output_processors 45 全过 ⇒ 锁定。
    "yt": "4.4.0",
}
# ★ Linux/py3.10 平台条件依赖（_wh_common.PLATFORM_DIFF_NOTE 记录的全集）：
#   jeepney/secretstorage = paramiko 的 Linux keyring 后端；
#   其余 6 个 = py3.10 兼容垫片。★ pip download 交叉下载时环境标记
#   （如 `typing-extensions; python_version<"3.11"`）按**当前解释器**
#   （Windows 3.13）求值而被跳过 —— 必须显式列出，否则远端 --no-index 下缺包。
#   pexpect/ptyprocess = ipython 的 sys_platform!="win32" 条件依赖
#   （01b WSL 离线预演实测抓出，Linux 侧必装）。
MANUAL_LINUX_EXTRAS = ["jeepney", "secretstorage",
                       "typing-extensions", "tomli", "exceptiongroup",
                       "importlib-metadata", "zipp", "backports.tarfile",
                       "pexpect", "ptyprocess"]
EXPECTED_SHIMS = ["typing_extensions", "tomli", "exceptiongroup", "pytz",
                  "importlib_metadata", "zipp", "backports_tarfile",
                  "jeepney", "secretstorage", "pexpect", "ptyprocess",
                  "pip", "setuptools", "wheel"]


def die(msg: str) -> None:
    print(f"[FATAL] {msg}")
    raise SystemExit(1)


def run(cmd: list, timeout: int = 5400) -> subprocess.CompletedProcess:
    print(f"  $ {' '.join(str(c) for c in cmd)[:200]}")
    return subprocess.run(cmd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=timeout)


def wheel_entry_count(p: Path) -> int:
    try:
        with zipfile.ZipFile(p) as z:
            return len(z.namelist())
    except Exception:  # noqa: BLE001
        return -1


def find_body_wheel() -> Path:
    """dist/ 下最新的 flash_sim-*.whl（py3-none-any 跨平台）。"""
    cands = sorted((REPO_ROOT / "dist").glob("flash_sim-*.whl"),
                   key=lambda p: p.stat().st_mtime, reverse=True)
    if not cands:
        die("dist/ 下没有 flash_sim-*.whl —— 先构建本体 wheel")
    return cands[0]


def reqs_for_download(profile: str = "full") -> list[str]:
    """依赖闭包列表（★ 不含本体）。复用 build_wheelhouse.build_pip_freeze_list 逻辑。"""
    _, human = wh.required_packages(REPO_ROOT / "pyproject.toml", profile)
    proj = wh.canonical_name(wh.PROJECT_DIST)
    reqs, seen = [], set()
    for r in human:
        n = wh.canonical_name(wh.requirement_name(r))
        if n == proj or n in seen:
            continue
        seen.add(n)
        reqs.append(r)
    for p in wh.PROFILES[profile].get("extra_pkgs", []):
        n = wh.canonical_name(p)
        if n not in seen:
            seen.add(n)
            reqs.append(p)
    for p in MANUAL_LINUX_EXTRAS:   # ★ Windows 上 platform_extra_pkgs() 返回空，手动补
        n = wh.canonical_name(p)
        if n not in seen:
            seen.add(n)
            reqs.append(p)
    # ★ glibc 锁定：pin 作为**附加约束**追加（pillow/ewah 等是 matplotlib/yt 的
    #   传递依赖，不在直接依赖列表里，仅替换不生效——首版实测漏网）。
    #   pip 对同名多约束取交集，`pillow==12.2.0` 会压制传递解析出的 12.3.0。
    for pkg, ver in VERSION_PINS.items():
        reqs.append(f"{pkg}=={ver}")
    return reqs


def main() -> int:
    t0 = time.time()
    print(f"[03] wheelhouse-linux 输出: {WH_DIR}")
    if WH_DIR.exists():
        print(f"[03] 已存在，先清空重造")
        shutil.rmtree(WH_DIR)
    WH_DIR.mkdir(parents=True, exist_ok=True)
    PKG_DIR.mkdir(parents=True, exist_ok=True)

    # ---- Step 1: 本体 wheel + 指纹 ----
    body = find_body_wheel()
    body_dest = WH_DIR / body.name
    shutil.copy2(body, body_dest)
    fp_sha = wh.sha256_file(body_dest)
    fp_size = body_dest.stat().st_size
    fp_entries = wheel_entry_count(body_dest)
    print(f"[03] step1 本体 wheel: {body.name}")
    print(f"[03]   sha256={fp_sha[:16]} size={wh.human_size(fp_size)} entries={fp_entries}")
    if fp_size < 1_000_000:
        die(f"本体 wheel 仅 {wh.human_size(fp_size)} —— 疑似残包/PyPI 旧包，中止")
    if not (1000 <= fp_entries <= 100000):
        die(f"本体 wheel 条目数异常: {fp_entries}")

    # ---- Step 2: pip download 依赖闭包（manylinux 交叉） ----
    reqs = reqs_for_download("full")
    print(f"[03] step2 pip download（{len(reqs)} 个直接依赖，目标 manylinux/cp310）...")
    py = sys.executable
    cmd = [py, "-m", "pip", "download",
           "--dest", str(WH_DIR),
           "--disable-pip-version-check",
           "--only-binary=:all:"]
    for plat in PLATFORMS:
        cmd += ["--platform", plat]
    cmd += ["--python-version", PY_VERSION, "--implementation", "cp"]
    for abi in PY_ABIS:
        cmd += ["--abi", abi]
    cmd += reqs
    r = run(cmd, timeout=7200)
    (LOG_DIR / "03_pip_download_tail.log").write_text(
        (r.stdout or "")[-8000:] + "\n---- stderr ----\n" + (r.stderr or "")[-8000:],
        encoding="utf-8")
    if r.returncode != 0:
        print((r.stdout or "")[-3000:]); print((r.stderr or "")[-3000:])
        die("pip download 失败 —— 见 logs/03_pip_download_tail.log")

    # ---- Step 3: 指纹复核 + 平台断言 ----
    now_sha = wh.sha256_file(body_dest)
    now_entries = wheel_entry_count(body_dest)
    print(f"[03] step3 本体复核: sha256={now_sha[:16]} entries={now_entries}")
    if now_sha != fp_sha or now_entries != fp_entries:
        die("本体 wheel 在下载依赖后被覆盖（PyPI 同名包事故）！删 wheelhouse 重跑。")

    wheels = sorted(WH_DIR.glob("*.whl"))
    # ★ 按**平台标签分量**判定（wheel 文件名末段），绝不能子串匹配——
    #   pywin32_ctypes 的包名含 "win32" 子串，子串匹配会误报（§3 教训翻版）。
    def plat_tag(fname: str) -> str:
        stem = fname[: -len(".whl")]
        parts = stem.split("-")
        return parts[-1] if len(parts) >= 5 else ""
    bad_plat = [p.name for p in wheels
                if (t := plat_tag(p.name)) and
                ("win" in t or "macosx" in t or "cygwin" in t)]
    if bad_plat:
        die(f"混入非 Linux wheel（按平台标签分量）: {bad_plat[:5]}")
    # ★ glibc 门槛审计：目标机 glibc=2.17，任何"全部标签均 > 2_17"的 wheel
    #   远端 pip 必拒（No matching distribution found）。此处前置拦截并点名，
    #   修法：在 VERSION_PINS 里锁定到带 ≤2_17 wheel 的版本。
    offenders = []
    for p in wheels:
        stem = p.name[: -len(".whl")]
        parts = stem.split("-")
        if len(parts) < 5:
            continue
        tags = set(parts[-1].split("."))
        if not (tags & ALLOWED_LOW_TAGS):
            offenders.append(p.name)
    if offenders:
        die("以下 wheel 的 glibc 门槛 > 2.17（远端 CentOS 7 pip 必拒）:\n"
            + "\n".join(f"    - {x}" for x in offenders[:10])
            + "\n    ⇒ 在 VERSION_PINS 中锁定到带 manylinux_2_17 wheel 的版本")
    n_manylinux = sum(1 for p in wheels
                      if "manylinux" in p.name or "none-any" in p.name or "linux" in p.name)
    print(f"[03] 共 {len(wheels)} 个 wheel（manylinux/纯 py: {n_manylinux}）")
    # 垫片/关键包存在性（py3.10 造包特征 + extra_pkgs）
    names = {wh.wheel_dist_name(p.name) for p in wheels}
    missing_shims = [s for s in EXPECTED_SHIMS if wh.canonical_name(s) not in names]
    if missing_shims:
        print(f"[warn] 预期垫片缺失: {missing_shims}（py3.10 特征包，缺则远端 pip 可能补不上）")
        die("垫片缺失，中止（检查 pip download 的 --python-version 是否为 3.10）")

    # ---- Step 4: MANIFEST（显式 linux/3.10 平台标记） ----
    house = wh.WheelHouse(WH_DIR)
    import platform as _plat
    meta = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "profile": "full",
        "profile_desc": wh.PROFILES["full"]["desc"],
        "project_dist": wh.PROJECT_DIST,
        "git_sha": "N/A",
        "python_version": f"cross-build target {PY_VERSION}",
        "platform": f"cross:{_plat.system()}-{_plat.machine()} -> linux x86_64",
        # ★ 显式写目标平台：platform_check() 在超算(linux/3.10)上据此放行
        "platform_tag": "linux",
        "python_tag": "3.10",
        "platform_extra_pkgs": MANUAL_LINUX_EXTRAS,
        "platform_diff_note": ("交叉造包: Windows 联网机 pip download "
                               "--platform manylinux2014_x86_64 --python-version 3.10 "
                               "（目标: NC-E python/3.10.8）"),
        "pip_flags": ["--no-index"],
        "target": "NC-E scfa2696 python/3.10.8",
    }
    mp = house.write_manifest(meta)
    man = house.read_manifest()
    print(f"[03] step4 MANIFEST: {len(man['entries'])} 条目 -> {mp.name}")

    # ---- Step 5: 交叉校验 + 泄漏审计 ----
    missing, present = house.preflight(REPO_ROOT / "pyproject.toml", "full")
    print(f"[03] step5 覆盖度: {len(present)}/{len(present) + len(missing)}")
    if missing:
        die(f"预检缺直接依赖: {missing}")
    audit = REPO_ROOT / "scripts" / "08_offline_install" / "wheel_leak_audit.py"
    r = run([py, str(audit), str(WH_DIR)], timeout=900)
    print((r.stdout or "")[-1500:])
    if r.returncode != 0:
        die(f"泄漏审计未通过 rc={r.returncode}")

    total = sum(p.stat().st_size for p in WH_DIR.iterdir() if p.is_file())
    print(f"[03] 完成: {len(wheels)} wheel, 总体积 {wh.human_size(total)}, "
          f"耗时 {time.time() - t0:.0f}s")
    print("[03] 结论: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
