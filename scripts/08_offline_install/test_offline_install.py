#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
test_offline_install.py — 离线安装链路的回归自检
============================================================================

为什么需要它：离线安装的正确性**无法在联网机上"跑一遍看看"** 才发现问题
（离线机才会缺包）。因此所有"判断逻辑"（档位解析 / 文件名归一化 /
MANIFEST 校验 / 覆盖度预检 / 开关判定）都必须用**已知答案**离线自检。

★ 特别针对两个已发生的真实缺陷:
  1. 依赖解析器按字符切片 → base/full/dev 全空 → 预检**假通过**
     （捕获手段: 对照 pyproject 实际声明的包名做断言, 而非只看"没报错"）
  2. 自动探测用"脚本目录存在"当离线判据 → 所有在线用户被误切离线
     （捕获手段: 6 用例开关矩阵）

用法:
    python scripts/08_offline_install/test_offline_install.py
    或纳入 pytest（test/ 或 scripts 下的test_*.py 会被收集）
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import _wh_common as wh  # noqa: E402

try:
    import start_flash  # noqa: E402
except Exception:
    start_flash = None  # 允许只测_common 部分


# ---------------------------------------------------------------------------
# 迷你测试框架
# ---------------------------------------------------------------------------

_RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    _RESULTS.append((name, bool(cond), detail))
    mark = "PASS" if cond else "FAIL"
    print(f"  [{mark}] {name}" + (f"— {detail}" if detail and not cond else ""))


def section(title: str) -> None:
    print(f"\n{title}")


# ---------------------------------------------------------------------------
# 1. 文件名归一化（PEP 427/ 625）
# ---------------------------------------------------------------------------

def test_wheel_name() -> None:
    section("[1] wheel/sdist 文件名归一化")
    cases = [
        ("flash_sim-0.1.7-py3-none-any.whl", "flash-sim"),
        ("numpy-2.5.2-cp313-cp313-win_amd64.whl", "numpy"),
        ("pytest_cov-7.1.0-py3-none-any.whl", "pytest-cov"),
        ("python_dateutil-2.9.0.post0-py3-none-any.whl", "python-dateutil"),
        ("zope.interface-5.0.tar.gz", "zope-interface"),
        ("ruamel.yaml.clib-0.2.8-cp313-cp313-win_amd64.whl", "ruamel-yaml-clib"),
    ]
    for fn, expect in cases:
        got = wh.wheel_dist_name(fn)
        check(f"{fn} → {expect}", got == expect, f"got={got!r}")

    # 必须是**从右往左**剥段：name 段本身可含 '-'
    check("含 '-' 的包名不被截断",
          wh.wheel_dist_name("my-pkg-name-1.0-py3-none-any.whl") == "my-pkg-name")


# ---------------------------------------------------------------------------
# 2. requirement 名提取
# ---------------------------------------------------------------------------

def test_requirement_name() -> None:
    section("[2] requirement 串 → 包名")
    cases = [
        ("yt>=4.1", "yt"),
        ("pytest-cov>=4.0", "pytest-cov"),
        ("pandas[excel]>=2.0", "pandas"),
        ('foo; python_version<"3.11"', "foo"),
        ("flash_sim[full,dev]", "flash-sim"),
        ("git+https://gitee.com/x/y.git@v1#egg=myproj", "myproj"),
    ]
    for req, expect in cases:
        got = wh.requirement_name(req)
        check(f"{req!r} → {expect}", got == expect, f"got={got!r}")


# ---------------------------------------------------------------------------
# 3. ★ pyproject 依赖解析（防"假通过"）
# ---------------------------------------------------------------------------

def test_pyproject_parsing(root: Path) -> None:
    section("[3] ★ pyproject 依赖解析（必须对照已知答案，防假通过）")
    pp = root / "pyproject.toml"
    reqs = wh.parse_pyproject_requirements(pp)

    # base: pyproject 里实际声明的 2 个
    check("base 非空（曾因按字符切片而全空）", len(reqs["base"]) > 0,
          f"base={reqs['base']}")
    check("base 含 cryptography", any("cryptography" in r for r in reqs["base"]),
          f"base={reqs['base']}")
    check("base 含 numpy", any("numpy" in r for r in reqs["base"]))

    # full: h5py/matplotlib/yt/pandas
    for pkg in ("h5py", "matplotlib", "yt", "pandas"):
        check(f"full 含 {pkg}", any(r.startswith(pkg) for r in reqs["full"]),
              f"full={reqs['full']}")

    # dev: pytest/black/ruff
    for pkg in ("pytest", "black", "ruff"):
        check(f"dev 含 {pkg}", any(r.startswith(pkg) for r in reqs["dev"]),
              f"dev={reqs['dev']}")

    # 不得有幽灵包名（"]" 曾被当成 requirement 收进来）
    allreq = reqs["base"] + reqs["full"] + reqs["dev"]
    ghost = [r for r in allreq if not r.strip() or "]" in r or "[" == r.strip()]
    check("无幽灵包名（']'/空串）", not ghost, f"ghost={ghost}")

    # 各档位包数应递减
    nf, _ = wh.required_packages(pp, "full")
    nr, _ = wh.required_packages(pp, "runtime")
    nl, _ = wh.required_packages(pp, "lite")
    check(f"full({len(nf)}) > runtime({len(nr)}) > lite({len(nl)})",
          len(nf) > len(nr) > len(nl))
    check("lite 不含 yt", "yt" not in nl)
    check("lite 不含 matplotlib", "matplotlib" not in nl)
    check("runtime 不含 pytest", "pytest" not in nr)
    check("runtime 仍含 yt（要出图）", "yt" in nr)
    check("三档都含 flash-sim 本体",
          all(wh.canonical_name(wh.PROJECT_DIST) in s for s in (nf, nr, nl)))


# ---------------------------------------------------------------------------
# 4. ★ 开关判定矩阵（防"误伤在线用户"）
# ---------------------------------------------------------------------------

def test_switch_matrix() -> None:
    section("[4] ★ 在线/离线开关判定矩阵（防所有在线用户被误切离线）")
    if start_flash is None:
        check("可导入 start_flash", False, "start_flash 导入失败，跳过")
        return

    A = argparse.Namespace(offline=False, wheelhouse=None, profile=None)
    B = argparse.Namespace(offline=True, wheelhouse=None, profile=None)
    orig_dir = start_flash.PROJECT_DIR
    env_backup = {k: os.environ.get(k) for k in
                  ("FLASH_OFFLINE", "FLASH_FORCE_ONLINE", "FLASH_WHEELHOUSE")}

    def restore():
        start_flash.PROJECT_DIR = orig_dir
        for k, v in env_backup.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    try:
        for k in env_backup:
            os.environ.pop(k, None)
        tmp = Path(tempfile.mkdtemp())

        # 关键回归：仓库里存在 scripts/08_offline_install/（随仓库分发），
        # 但 wheelhouse/MANIFEST.json 不存在 → **必须**判在线
        start_flash.PROJECT_DIR = tmp
        check("无 wheelhouse → 在线", start_flash.resolve_offline_mode(A) is False)

        os.makedirs(tmp / "wheelhouse")
        check("wheelhouse 目录存在但无 MANIFEST → 在线",
              start_flash.resolve_offline_mode(A) is False,
              "★ 判据必须是 MANIFEST.json 本身，不是目录存在")

        (tmp / "wheelhouse" / "MANIFEST.json").write_text("{}", encoding="utf-8")
        check("有 MANIFEST.json → 自动转离线",
              start_flash.resolve_offline_mode(A) is True)

        os.environ["FLASH_FORCE_ONLINE"] = "1"
        check("FLASH_FORCE_ONLINE=1 强制在线",
              start_flash.resolve_offline_mode(A) is False)
        os.environ.pop("FLASH_FORCE_ONLINE")

        os.environ["FLASH_OFFLINE"] = "1"
        check("FLASH_OFFLINE=1 → 离线", start_flash.resolve_offline_mode(A) is True)
        os.environ.pop("FLASH_OFFLINE")

        check("--offline → 离线", start_flash.resolve_offline_mode(B) is True)

        shutil.rmtree(tmp, ignore_errors=True)
    finally:
        restore()


# ---------------------------------------------------------------------------
# 5. ★ 覆盖度预检 + MANIFEST 校验（含负例）
# ---------------------------------------------------------------------------

def test_gates(root: Path) -> None:
    section("[5] ★ 三道闸门（含损坏/ 缺失 / 档位不匹配负例）")
    pp = root / "pyproject.toml"
    tmp = Path(tempfile.mkdtemp())
    whd = tmp / "wheelhouse"
    whd.mkdir()
    house = wh.WheelHouse(whd)

    try:
        # G1 目录内有归档
        check("G1: 空目录无归档", not house.archives())

        # 造 full 档的假包
        names, _ = wh.required_packages(pp, "full")
        for n in names:
            (whd / f"{n}-1.0.0-py3-none-any.whl").write_bytes(b"PK\x03\x04fake")
        check("G1: full 档 18 包已就位", len(house.archives()) == len(names))

        # G3 覆盖度预检
        miss, pres = house.preflight(pp, "full")
        check("G3: full 档无缺失", not miss, f"missing={miss}")
        check("G3: full 档 present 数正确", len(pres) == len(names))

        # G2 MANIFEST 缺失 → 报错
        probs, _ = house.verify_manifest(deep=False)
        check("G2: 无 MANIFEST 时报错", len(probs) == 1 and "MANIFEST" in probs[0])

        # 写 MANIFEST → 通过
        house.write_manifest({"test": 1})
        probs, notes = house.verify_manifest(deep=True)
        check("G2: 写 MANIFEST 后通过", not probs, f"problems={probs}")

        # MANIFEST 内容可被 json 解析且含 sha256
        man = house.read_manifest()
        check("MANIFEST 结构正确",
              bool(man) and all("sha256" in e and "size" in e
                                for e in man.get("entries", [])))

        # 负例：损坏一个 wheel
        victim = whd / f"{names[0]}-1.0.0-py3-none-any.whl"
        victim.write_bytes(b"CORRUPTED-BIGGER")
        probs, _ = house.verify_manifest(deep=True)
        check("负例: 损坏文件被拦截", bool(probs), f"problems={probs}")

        # 负例：删除一个 wheel
        victim2 = whd / f"{names[1]}-1.0.0-py3-none-any.whl"
        victim2.unlink()
        probs, _ = house.verify_manifest(deep=True)
        check("负例: 缺失文件被拦截",
              any("[缺失]" in p for p in probs), f"problems={probs}")

        # 负例：档位不匹配（lite 的包跑 full 预检）
        for f in whd.glob("*.whl"):
            f.unlink()
        lite, _ = wh.required_packages(pp, "lite")
        for n in lite:
            (whd / f"{n}-1.0.0-py3-none-any.whl").write_bytes(b"PK\x03\x04fake")
        miss, _ = house.preflight(pp, "full")
        check("负例: 档位不匹配报出缺失清单", len(miss) > 0, f"missing={miss}")
        for pkg in ("yt", "matplotlib", "pytest"):
            check(f"负例: 缺失清单含 {pkg}", pkg in miss)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# 6. .bat ASCII/CRLF 约定
# ---------------------------------------------------------------------------

def test_bat_convention() -> None:
    section("[6] .bat 纯 ASCII（Windows cmd GBK 约定；行尾由 .gitattributes 统一为 LF）")
    for name in ("build_wheelhouse.bat", "install_offline.bat"):
        p = HERE / name
        if not p.is_file():
            check(f"{name} 存在", False)
            continue
        ok, note = wh.ensure_ascii_bat_ok(p)
        check(f"{name} 纯 ASCII 无 BOM", ok, note)
        # 行尾只提示不拦截：仓库 .gitattributes 规定 *.bat text eol=lf
        d = p.read_bytes()
        print(f"         行尾: {'CRLF' if b'\\r\\n' in d else 'LF'}（.gitattributes 统一 LF）")


# ---------------------------------------------------------------------------
# 7. 根目录零新增（收纳约定）
# ---------------------------------------------------------------------------

def test_no_root_pollution(root: Path) -> None:
    section("[7] 脚本收纳：根目录零新增")
    online_scripts = {
        "build_wheelhouse.py", "install_offline.py", "_wh_common.py",
    }
    stray = [n for n in online_scripts if (root / n).exists()]
    check("离线脚本不在根目录", not stray, f"stray={stray}")
    for n in sorted(online_scripts):
        check(f"{n} 在 scripts/08_offline_install/",
              (HERE / n).is_file())


# ---------------------------------------------------------------------------
# 8. ★ 实测踩坑固化：pip download 参数 / Path 类型 / 自动定位
# ---------------------------------------------------------------------------

def test_pip_download_flags() -> None:
    section("[8] ★ pip download 参数合法性（实测 --upgrade 会 rc=2）")
    # `pip download` 不支持 --upgrade（那是 install 专有）——
    # 传入直接报 "no such option: --upgrade" 并终止整个造包。
    import subprocess
    r = subprocess.run(
        [sys.executable, "-m", "pip", "download", "--upgrade", "--dest",
         os.path.join(tempfile.gettempdir(), "_pipflagtest"), "six"],
        capture_output=True, text=True, errors="replace")
    check("pip download 拒绝 --upgrade（故脚本中不得使用）",
          r.returncode != 0 and "no such option" in (r.stderr or ""),
          f"rc={r.returncode}")

    # 反之：--find-links / --only-binary / --disable-pip-version-check 必须被接受
    r2 = subprocess.run([sys.executable, "-m", "pip", "download", "--help"],
                        capture_output=True, text=True, errors="replace")
    h = r2.stdout or ""
    for flag in ("--find-links", "--only-binary", "--disable-pip-version-check"):
        check(f"pip download 支持 {flag}", flag in h)


def test_preflight_accepts_path_only() -> None:
    section("[9] ★ preflight 必须收Path（曾因传 str 抛 AttributeError）")
    root = wh.find_project_root()
    tmp = Path(tempfile.mkdtemp())
    whd = tmp / "wheelhouse"
    whd.mkdir()
    try:
        house = wh.WheelHouse(whd)
        names, _ = wh.required_packages(root / "pyproject.toml", "full")
        for n in names:
            (whd / f"{n}-1.0.0-py3-none-any.whl").write_bytes(b"PK\x03\x04fake")

        # 传 Path（start_flash.py 的实际用法）
        miss_ok, _ = house.preflight(root / "pyproject.toml", "full")
        check("传 Path 正常工作", not miss_ok, f"missing={miss_ok}")

        # 传 str 必须给出清晰错误或至少不静默通过
        try:
            house.preflight(str(root / "pyproject.toml"), "full")
            check("传 str 会被拒（防误用）", False, "静默接受了 str，未报错")
        except AttributeError:
            check("传 str 明确报错 AttributeError（调用方须传 Path）", True)
        except Exception as e:
            check("传 str 报错（可接受）", True, f"{type(e).__name__}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_autolocate_paths() -> None:
    section("[10] ★ wheelhouse 自动定位（须含 offline_pkg/ 默认输出目录）")
    root = wh.find_project_root()
    tmp = Path(tempfile.mkdtemp())
    try:
        # 只放 offline_pkg/wheelhouse（build 的默认输出位置）
        whd = tmp / "offline_pkg" / "wheelhouse"
        whd.mkdir(parents=True)
        (whd / "dummy-1.0-py3-none-any.whl").write_bytes(b"PK\x03\x04fake")
        (whd / wh.MANIFEST_NAME).write_text("{}", encoding="utf-8")
        h = wh.resolve_wheelhouse(None, start=tmp)
        check("能从 offline_pkg/wheelhouse 自动定位",
              h.root == whd.resolve(), f"got={h.root}")

        # 贴项目根的 wheelhouse/ 应优先
        whd2 = tmp / "wheelhouse"
        whd2.mkdir()
        (whd2 / "dummy2-1.0-py3-none-any.whl").write_bytes(b"PK\x03\x04fake")
        (whd2 / wh.MANIFEST_NAME).write_text("{}", encoding="utf-8")
        h2 = wh.resolve_wheelhouse(None, start=tmp)
        check("项目根 wheelhouse/ 优先于 offline_pkg/",
              h2.root == whd2.resolve(), f"got={h2.root}")

        # 无 MANIFEST 的目录不算数（防止误命中半拷贝的目录）
        (whd2 / wh.MANIFEST_NAME).unlink()
        h3 = wh.resolve_wheelhouse(None, start=tmp)
        check("无 MANIFEST 的目录不被采纳",
              h3.root == whd.resolve(), f"got={h3.root}")
    except SystemExit:
        check("自动定位流程未抛异常", False, "resolve_wheelhouse 抛 SystemExit")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description="离线安装链路回归自检")
    ap.parse_args()

    root = wh.find_project_root()
    print("=" * 72)
    print("  离线安装链路回归自检 (test_offline_install.py)")
    print("=" * 72)
    print(f"项目根: {root}")

    test_wheel_name()
    test_requirement_name()
    test_pyproject_parsing(root)
    test_switch_matrix()
    test_gates(root)
    test_bat_convention()
    test_no_root_pollution(root)
    test_pip_download_flags()
    test_preflight_accepts_path_only()
    test_autolocate_paths()

    passed = sum(1 for _, ok, _ in _RESULTS if ok)
    total = len(_RESULTS)
    print()
    print("=" * 72)
    print(f"  结果: {passed}/{total} 通过")
    if passed != total:
        print("  失败项:")
        for n, ok, d in _RESULTS:
            if not ok:
                print(f"    - {n}" + (f"  ({d})" if d else ""))
    print("=" * 72)
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())