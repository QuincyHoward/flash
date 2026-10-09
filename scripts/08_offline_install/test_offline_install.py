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
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
# ★ start_flash.py 在**项目根**，不在本脚本所在目录 ⇒ 只把 HERE 加进
#   sys.path 会ImportError，导致 test_switch_matrix整节被静默跳过
#   （09-10 实测 58/59，误报"start_flash 导入失败"，而实际手动导入完全正常）。
PROJECT_ROOT = HERE.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import _wh_common as wh  # noqa: E402

try:
    import start_flash  # noqa: E402
except Exception as _exc:  # pragma: no cover
    start_flash = None  # 允许只测 _common 部分
    START_FLASH_IMPORT_ERR = f"{type(_exc).__name__}: {_exc}"
else:
    START_FLASH_IMPORT_ERR = None


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
        check("可导入 start_flash", False,
              f"导入失败({START_FLASH_IMPORT_ERR}) —— 开关矩阵整节无法验证")
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

def test_no_stale_wheel() -> None:
    """[11] ★ 造包不得静默使用陈旧 wheel（09-10 事故）。

    背景：build 失败时旧实现会从 dist/ 拷一个历史 wheel 当成功，09-10 实测
    拷进 wheelhouse 的是 9-08 的旧包 —— 少 2650 个文件（含
    flash/_core/credentials/hpc_config.py），体积 1.5MB vs 正常 4.8MB。
    """
    section("[11] ★ 陈旧 wheel 防护（造包不得静默用旧包）")
    sys.path.insert(0, str(HERE))
    import build_wheelhouse as bwh

    tmp = Path(tempfile.mkdtemp())
    try:
        # 造一个"上一轮遗留"的 wheel
        old = tmp / "flash_sim-0.1.7-py3-none-any.whl"
        old.write_bytes(b"PK\x03\x04STALE")

        bwh._quarantine_previous_wheels(tmp)
        check("隔离: 旧 wheel 被挪走", not old.exists())
        check("隔离: 落到 .stale/ 下",
              any((tmp / ".stale").glob("flash_sim-*.whl")))
        check("隔离: out_dir 不再残留 wheel",
              not list(tmp.glob("flash_sim-*.whl")))

        # 空目录不应报错
        empty = Path(tempfile.mkdtemp())
        bwh._quarantine_previous_wheels(empty)
        check("隔离: 空目录无异常", True)

        #体积哨兵：过大/过小都要告警（用返回值不便断言，查日志字符串）
        src = (HERE / "build_wheelhouse.py").read_text(encoding="utf-8")
        check("哨兵: 存在体积区间常量", "WHEEL_SIZE_OK" in src)
        check("哨兵: 偏大时告警", "偏大" in src)
        check("哨兵: 偏小时告警", "偏小" in src)
        check("哨兵: 比 pyproject 旧时告警", "还旧" in src)

        # 退回 dist/ 必须显式开关
        check("旧包退路需显式 --allow-legacy-dist",
              "--allow-legacy-dist" in src)
        check("默认不再静默 copy dist/",
              src.count("shutil.copy2(legacy") == 1)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_wheel_size_sanity(root: Path) -> None:
    """[12] ★ wheel 体积哨兵：产物必须是 MB 级（.gitignore 管不到 wheel 构建）。"""
    section("[12] ★ wheel 体积与 exclude 卫生")
    pp = root / "pyproject.toml"
    if not pp.is_file():
        check("存在 pyproject.toml", False)
        return
    text = pp.read_text(encoding="utf-8")

    # 关键：根 .gitignore 有裸 `*` ⇒ hatchling 的 VCS 排除会整体失效
    gi = root / ".gitignore"
    has_bare_star = False
    if gi.is_file():
        has_bare_star = any(l.strip() == "*"
                            for l in gi.read_text(encoding="utf-8").splitlines())
    check("根 .gitignore 含裸 `*`（故 pyproject 必须自带 exclude）", has_bare_star)

    # 这些大目录必须被 pyproject 显式排除
    must_exclude = [
        ("flash_input/flash_output", "flash/scenarios/**/flash_input/**"),
        ("测试产物 _out/", "**/_out/**"),
        ("Multi1D++ 便携包", "**/Multi1D*/**"),
        ("FLASH 引擎源码 SNBtest", "**/SNBtest/src/**"),
        ("helm_table.dat", "helm_table.dat"),
        ("BADGER 分发表 Others_data", "Others_data/**"),
    ]
    for label, pat in must_exclude:
        check(f"exclude 含 {label}", pat in text)

    # wheel 与 sdist 必须成对（只写一侧是历史 bug 来源）
    w_start = text.find("[tool.hatch.build.targets.wheel]")
    s_start = text.find("[tool.hatch.build.targets.sdist]")
    wheel_blk = text[w_start:s_start] if 0 < w_start < s_start else ""
    sdist_blk = text[s_start:]
    for label, pat in [("_out", "**/_out/**"),
                       ("SNBtest/src", "**/SNBtest/src/**"),
                       ("Others_data", "Others_data/**")]:
        check(f"成对维护: {label} 同时在 wheel 与 sdist",
              pat in wheel_blk and pat in sdist_blk)

    # ★★ 禁止**整目录**排除 private/：09-10 第三轮实测，写
    #   `flash/scenarios/private/tracer/**` 虽挡下 62GB 产物，却误伤
    #   116 个 git 已跟踪源码（151 .py / 33 .md / 9 .sh），含 SNBOneCH_ml.py、
    #   run_cores_parallel.py 等**自研 SNB 场景主线**⇒ 离线机装完跑不了场景。
    #   体积问题只能用**精确子目录/文件**规则解决，不能整目录砍。
    blanket = [x for x in ("flash/scenarios/private/tracer/**",
                           "flash/scenarios/private/**")
               if f'"{x}"' in text]
    check("未整目录排除 private/（会误伤已跟踪源码）", not blanket,
          f"存在 {blanket}" if blanket else "")
    # 精确化后的替代规则必须在位
    for label, pat in [("docs_diag", "private/tracer/**/docs_diag/**"),
                       ("plots", "private/tracer/**/plots/**"),
                       ("temp_delete", "private/tracer/temp_delete/**")]:
        check(f"private/tracer 精确排除含 {label}",
              pat in wheel_blk and pat in sdist_blk)


def test_pypi_overwrite_guard() -> None:
    """[13] ★★ 本体 wheel 不得被 PyPI 同名包覆盖（09-10 严重事故）。

    背景：flash-sim 0.1.7 已发布在 PyPI（1.53MB）。造包时
    `pip download flash_sim[full,dev] --find-links <本地目录>` 中，
    --find-links **不保证本地优先**，pip 会以"bad hash. Re-downloading."
    为由下载公开旧包覆盖本地构建产物（实测 4.76MB/902条目 → 1.53MB/224条目）。
    后果：离线机安静地装上过期公开代码；日志仍打印 [ok]，肉眼极难发现。
    """
    section("[13] ★★ PyPI 同名包覆盖防护")
    sys.path.insert(0, str(HERE))
    import build_wheelhouse as bwh
    import _wh_common as whc

    tmp = Path(tempfile.mkdtemp())
    try:
        w = tmp / "flash_sim-0.1.7-py3-none-any.whl"
        w.write_bytes(b"PK\x03\x04" + b"LOCAL" * 100)

        # ① 正常路径：指纹一致 → 不报错
        bwh._LOCAL_WHEEL_FINGERPRINT.clear()
        bwh._LOCAL_WHEEL_FINGERPRINT.update(
            sha256=whc.sha256_file(w), size=w.stat().st_size,
            entries=bwh._wheel_entry_count(w))
        try:
            bwh._ensure_local_wheel_intact(w)
            check("指纹一致时不误报", True)
        except SystemExit:
            check("指纹一致时不误报", False, "一致却被判为覆盖")

        # ② 被覆盖 → 必须中止
        w.write_bytes(b"PK\x03\x04" + b"PYPI-OLD-PKG" * 100)
        try:
            bwh._ensure_local_wheel_intact(w)
            check("被覆盖时中止", False, "★护栏漏检★")
        except SystemExit as e:
            check("被覆盖时中止", True)
            check("报错信息点明 PyPI 同名包",
                  "PyPI" in str(e) and "flash-sim" in str(e))

        # ③ 条目数过少（残包）→ 中止。用**真zip** 造一个条目数少的包，
        #    否则非 zip 文件读不出条目数（-1），测的就不是同一件事了。
        import zipfile as _zf
        real = tmp / "flash_sim-0.1.7-py3-none-any.whl"
        with _zf.ZipFile(real, "w") as zf:
            zf.writestr("flash/__init__.py", "# tiny\n")
        bwh._LOCAL_WHEEL_FINGERPRINT.clear()
        bwh._LOCAL_WHEEL_FINGERPRINT.update(
            sha256=whc.sha256_file(real), size=10 * 1024 * 1024, entries=902)
        try:
            bwh._ensure_local_wheel_intact(real)
            check("残包(条目过少)时中止", False, "未拦截")
        except SystemExit:
            check("残包(条目过少)时中止", True)

        # ④ 无指纹时不误伤（首次运行/单测场景）
        bwh._LOCAL_WHEEL_FINGERPRINT.clear()
        try:
            bwh._ensure_local_wheel_intact(w)
            check("无指纹时静默跳过", True)
        except SystemExit:
            check("无指纹时静默跳过", False)

        # ⑤ 源码里必须真的接上了这个校验
        src = (HERE / "build_wheelhouse.py").read_text(encoding="utf-8")
        check("Step2 已接入 _ensure_local_wheel_intact",
              "local_wheel=local_wheel" in src)
        check("Step1 记录 sha256 指纹", "_LOCAL_WHEEL_FINGERPRINT" in src)

        # ⑥★ 根因修复：pip download 目标列表**不得含项目本体**，
        #    否则 pip 会从 PyPI 下载同名包覆盖本地 wheel（见上）。
        #    本体 wheel 由 Step 1 直接放入 wheelhouse，根本不经pip。
        root = wh.find_project_root()
        for prof in ("full", "runtime", "lite"):
            pkgs = bwh.build_pip_freeze_list(root, Path("."), prof)
            names = {wh.canonical_name(wh.requirement_name(p)) for p in pkgs}
            check(f"{prof} 档: download 列表不含本体",
                  wh.canonical_name(wh.PROJECT_DIST) not in names,
                  f"含本体 -> 会拉 PyPI 包")
            check(f"{prof} 档: 列表非空且含关键包",
                  len(pkgs) > 0
                  and "numpy" in {wh.canonical_name(wh.requirement_name(p))
                                  for p in pkgs})
        # 关键依赖必须齐（09-09 整批缺包的教训）
        full_names = {wh.canonical_name(wh.requirement_name(p))
                      for p in bwh.build_pip_freeze_list(root, Path("."), "full")}
        for need in ("h5py", "matplotlib", "yt", "pandas", "pytest",
                     "scipy", "paramiko"):
            check(f"full 档含 {need}", need in full_names)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        bwh._LOCAL_WHEEL_FINGERPRINT.clear()


def test_leak_audit_guard(root: Path) -> None:
    """[14] ★★ 泄漏审计护栏自身必须可信（09-10 教训：护栏自己骗了我）。

    本脚本首版用 `subprocess.run(text=True)` 喂 `git check-ignore`，Windows 走
    ANSI 代码页（GBK/cp1252）把 CJK 路径弄坏 ⇒ 同一输入报 1733 条 vs 正确
    1855 条，**漏报 94.5%**，差点让100.5MB 的 wheel 通过审计。
    ⇒ 这里断言：① 用bytes 而非 text；② §3 判据按**路径分量**而非子串；
    ③ dist-info/ 被剔除；④ 负向样本必须真的 FAIL（rc=1）。
    """
    section("[14] ★★ 泄漏审计护栏自检")
    sys.path.insert(0, str(HERE))
    try:
        import wheel_leak_audit as wla
    except Exception as exc:
        check("可导入 wheel_leak_audit", False, f"{type(exc).__name__}: {exc}")
        return

    src = (HERE / "wheel_leak_audit.py").read_text(encoding="utf-8")

    # ① 必须喂 bytes（text=True 是 94.5% 漏报的根因）
    #    ★★ 断言**运行时行为**而非源码文本：函数 docstring 里就写着
    #    "text=True 会漏报" 的告警，grep 源码必然误报（09-10 已踩过一次）。
    #    这里真的调一次 git_ignored，用 CJK + 空格路径验证它能识别忽略项。
    check("git_ignored 用 bytes 而非 text=True",
          'input=b"\\0".join' in src)
    # 真调一次：构造一个 git 确实忽略的 CJK 路径，看能否识别出来
    cjk = "flash/input_gen/gen_eos_op/中文 目录/临时产物.log"
    try:
        got = wla.git_ignored([cjk, "flash/__init__.py"])
        check("git_ignored 能识别 CJK+空格路径", cjk in got,
              f"返回 {sorted(got)[:3]}")
    except Exception as exc:
        check("git_ignored 可调用", False, f"{type(exc).__name__}: {exc}")
    check("自行 UTF-8 解码", 'decode("utf-8", "replace")' in src)
    check("用 -z 分隔（路径含空格/CJK 安全）", '"-z"' in src)

    # ② §3 判据按路径分量，不按子串（否则 MultiEOSOP格式说明.md 误报）
    check("§3 用路径分量集合而非子串",
          isinstance(getattr(wla, "FLASH_STRONG_PARTS", None), frozenset))
    check("§3 目录前缀单独处理",
          isinstance(getattr(wla, "FLASH_STRONG_DIRS", None), tuple))
    check("MultiEOSOP格式说明.md 不再误报",
          not wla.is_flash_material(
              "flash/input_gen/gen_eos_op/src/multi_docs/MultiEOSOP格式说明.md"))
    check("真§3 材料仍能命中（flash_src/EosMain.F90）",
          wla.is_flash_material("flash/flash_src/EosMain.F90"))
    check("真 §3 材料仍能命中（Multi1D++Portable 目录）",
          wla.is_flash_material("flash/x/Multi1D++Portable3.0/y.txt"))
    check("helm_table.dat 仍命中",
          wla.is_flash_material("a/b/helm_table.dat"))

    # ③ dist-info 剔除（否则每次审计 2 条假阳性）
    check("dist-info 已被剔除",
          getattr(wla, "DIST_INFO", "") and
          wla.DIST_INFO in src)

    # ④ 容差按体积而非文件数（残余 50 个 results/*.json 共 384KB 可接受）
    check("泄漏容差按体积设定", 0 < wla.LEAK_BYTES_OK <= 8 * 1024 * 1024)
    check("单文件上限已设定", 0 < wla.LEAK_FILE_BYTES_OK < wla.LEAK_BYTES_OK)
    check("体积区间含实测 5.5MB", wla.WHEEL_BYTES_OK[0] <= int(5.5 * 1048576)
          <= wla.WHEEL_BYTES_OK[1])

    # ⑤ 负向样本必须真的 FAIL —— 未证明会失败的护栏不算护栏
    tmp = Path(tempfile.mkdtemp())
    try:
        neg = tmp / "neg.whl"
        with zipfile.ZipFile(neg, "w") as z:
            z.writestr("flash/__init__.py", "x" * 10)
            z.writestr("flash/flash_src/EosMain.F90", "y" * 10)
            z.writestr("flash/a/big.log", "z" * (wla.LEAK_FILE_BYTES_OK + 1024))
        argv = sys.argv
        sys.argv = ["wheel_leak_audit", str(neg)]
        try:
            import io
            import contextlib
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = wla.main()
        finally:
            sys.argv = argv
        check("负向样本 rc=1（护栏真的会失败）", rc == 1, f"实际 rc={rc}")
        check("负向报告点名 flash_src",
              "flash_src" in buf.getvalue())
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


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
    test_no_stale_wheel()
    test_wheel_size_sanity(root)
    test_pypi_overwrite_guard()
    test_leak_audit_guard(root)

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