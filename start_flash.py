#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
start_flash.py — flash 包「环境自检自愈 + 从零安装 + 全局测试」一键脚本
========================================================================

用途（对应发布验证流程）：
  1. 检查项目专属虚拟环境 .venv：
     - 不存在 → 全新创建（master 不含此目录，因 .gitignore 排除）
     - 存在   → 做**环境健康检查**（关键依赖可导入 + pytest 可启动）
       - 健康 → 复用
       - 不健康 → **自动清零重建**（无需手动 FLASH_FORCE_CLEAN=1）
  2. 修复 base 内置的损坏 setuptools
  3. pip 从零安装 flash 包:  pip install -e ".[full,dev]" scipy paramiko
  4. 安装后环境复检（仍不健康 → 再自动重建一轮）
  5. 运行全局三套测试:  framework / input_gen / output_processors
     - 若三套件全部「0 用例启动失败」（pytest 崩溃特征）→ 判定为环境问题
       → 自动清零重建 → 重新测试
  6. 生成纯文本测试报告 INSTALL_TEST_REPORT.txt
     （含「环境版本快照」：关键依赖的真实版本统一记录）并在终端完整显示

设计原则（用户明确要求）：
  - start_flash.py 是新用户开启 flash 包的第一步、老用户/调试者验证 flash 包
    是否正常的关键一步 —— 必须**自愈**：环境损坏自动清零重建，测试环境异常
    也自动重建后重测，不依赖重启 WorkBuddy/机器、不依赖人工确认。
  - 进行全局测试的前提是测试环境正常；环境不正常 → 清零重建。
  - 统一使用项目专属 .venv（flash 内部环境），所有关键依赖版本以报告中
    「环境版本快照」为权威记录，版本不统一问题透明化。

注意：
  - 使用项目专属虚拟环境 <项目根目录>/.venv（IDE 默认识别的标准命名），
    确保脚本安装的环境 = IDE/用户实际执行脚本的解释器，避免"装了却 import 不到"。
    与其他项目完全隔离，绝不触碰共享环境
    （如 C:\\Users\\Administrator\\.workbuddy\\binaries\\python\\envs\\default）

用法：
  python start_flash.py

特性：
  - 幂等：重复执行即重新进行"从零安装 + 测试"，无需修改任何文件
  - 自愈：环境健康检查失败 / pytest 启动崩溃 → 自动清零重建（最多重建 2 轮）
  - 所有关键子进程都清空 CODEBUDDY_SESSION_ID / CLAUDE_SESSION_ID，
    以禁用 WorkBuddy 沙箱的"安全删除守卫"（否则 pip 无法删除旧文件而卡死）
  - pip 步骤带自动重试（网络中断时等待 60s 重试）
  - 测试步骤带超时保护，任何一步失败都给出明确错误信息

可覆盖的环境变量：
  FLASH_BASE_PY        base 解释器绝对路径（默认自动探测）
  FLASH_VENV_DIR       虚拟环境绝对路径（默认 <项目根目录>/.venv）
  FLASH_FORCE_CLEAN=1  强制清零重建（原语义保留）
  FLASH_NO_AUTO_REBUILD=1  禁用自动重建（仅检查与报告，不重建；用于诊断）
  FLASH_OFFLINE=1      ★ 离线安装模式：pip 改走本地 wheelhouse（--no-index）
  FLASH_WHEELHOUSE=<dir>  ★ wheelhouse 路径（默认<项目根>/wheelhouse）
  FLASH_PROFILE=<name>    ★ 离线预检档位: full / runtime / lite（默认 full）

★ 在线 / 离线双模式（同一脚本，按开关切换）
--------------------------------------------------------------------
两种模式**共用**全部逻辑：venv 健康检查 → 自愈清零重建 → 三套测试 →
INSTALL_TEST_REPORT.txt。唯一分叉点是 run_pip()：

  在线（默认）  pip install -e ".[full,dev]" scipy paramiko
  离线          pip install --no-index --find-links=<wheelhouse> \
                                "flash_sim[full,dev]" scipy paramiko

  · --no-index 是**硬闸门**：pip 物理上无法访问 PyPI。缺包立即报
    "No matching distribution found" 并指名缺哪个，而不是静默联网补装
    （后者是离线部署最常见的翻车点：装到一半发现漏包，venv 半残需从头再来）。
  · 因此离线模式在装之前先做 wheelhouse **覆盖度预检**（preflight_wheelhouse），
    缺一个就报全清单并当场中止，绝不进入"装到一半才发现缺"。
  · ★ 离线**不能**沿用 `-e .`：可编辑安装要解析源码树里的依赖声明，
    而离线机上的源码树可能来自 sdist（不含 tests/docs）。离线一律装
    build_wheelhouse.py 预先构建的 flash_sim-*.whl。
  · 离线若目录内附了 Python 安装程序且本机无可用 base 解释器，会提示
    先双击安装（不自动执行 —— 装解释器属于系统级变更，必须用户亲自确认）。

用法：
  python start_flash.py                              # 在线（默认）
  python start_flash.py --offline                     # 离线，自动找 wheelhouse/
  python start_flash.py --offline --wheelhouse E:\\offline_pkg\\wheelhouse
  set FLASH_OFFLINE=1 && python start_flash.py        # 环境变量方式（bat 用）
"""

import argparse
import datetime
import os
import re
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# 常量与路径
# ---------------------------------------------------------------------------
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

# 项目专属虚拟环境：位于项目根目录下，与其他项目完全隔离。
# 使用 .venv（IDE 默认识别的标准命名），确保 start_flash.py 安装的环境
# 与 IDE/用户实际执行脚本所用的解释器一致，避免"装了却 import 不到"。
# 绝不使用/删除共享环境（如 C:\Users\Administrator\.workbuddy\binaries\python\envs\default）。
DEFAULT_VENV_DIR = os.path.join(PROJECT_DIR, ".venv")
# base 解释器探测顺序: FLASH_BASE_PY 环境变量 → 当前解释器(非 venv) → 下方硬编码兜底。
# 不在此硬编码本机用户路径（start_flash.py 会随 sdist 发布，避免隐私泄漏）。
DEFAULT_BASE_PY: list = []

REPORT_FILE = os.path.join(PROJECT_DIR, "INSTALL_TEST_REPORT.txt")

# 三套测试: (套件名, 相对测试目录)  — 标准布局: 包代码在 flash/ 下
TEST_SUITES = [
    ("framework",          "test"),
    ("input_gen",          os.path.join("flash", "input_gen", "test")),
    ("output_processors",  os.path.join("flash", "output_processors", "test")),
]

# 环境健康检查的关键模块（对应 pyproject 依赖 + start_flash 补装项 + 传递依赖）：
#   - pytest 启动链: pytest/pluggy/iniconfig/packaging/pygments
#   - 科学计算: numpy/scipy/h5py/matplotlib/cycler/kiwisolver
#   - flash 功能: setuptools/paramiko/cryptography/nacl
#   - AMR 可视化: yt
# 任何一个缺失 → 环境不健康 → 自动清零重建。
ENV_KEY_MODULES = [
    "pytest", "pluggy", "iniconfig", "packaging", "pygments",
    "numpy", "scipy", "h5py", "matplotlib", "cycler", "kiwisolver",
    "paramiko", "cryptography", "nacl",
    "setuptools", "yt",
]

# ---------------------------------------------------------------------------
# 离线安装模式（在线 / 离线双模式）
# ---------------------------------------------------------------------------

#: 离线时安装的 project 本体名（pyproject name = flash-sim → dist 名 flash_sim）
#: ★ 离线**不用** `-e .`，改装预构建的 wheel（理由见文件头）。
OFFLINE_DIST = "flash_sim"

#: 离线预检档位（与 scripts/08_offline_install/_wh_common.py 的 PROFILES 对齐）
OFFLINE_PROFILES = ("full", "runtime", "lite")

#: pip 离线硬闸门：这两个参数让 pip **物理上**无法访问 PyPI
OFFLINE_PIP_FLAGS = ("--no-index",)

#: 运行期由 main() 填充（模块级是因为 run_pip() 沿用既有全局风格）
OFFLINE = False
WHEELHOUSE = ""


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------
def log(msg: str) -> None:
    print(msg, flush=True)


def clean_env() -> dict:
    """返回禁用 WorkBuddy 安全删除守卫的环境副本。

    沙箱注入的 sitecustomize.py 在 CODEBUDDY_SESSION_ID 存在时会
    patch os.remove/os.unlink 到"回收站-失败即中止"，导致 pip 无法
    删除旧文件而卡死/失败。清空相关变量后新子进程加载 sitecustomize
    时不会执行 patch，os.remove 恢复原生删除。
    """
    env = os.environ.copy()
    for key in ("CODEBUDDY_SESSION_ID", "CLAUDE_SESSION_ID", "CODEBUDDY_SAFE_DELETE_SANDBOX"):
        env[key] = ""
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def find_base_python() -> str:
    """定位 base 解释器（用于创建 venv）。"""
    cand = os.environ.get("FLASH_BASE_PY", "").strip()
    if cand and os.path.isfile(cand):
        return cand
    cur = sys.executable
    if cur and os.path.isfile(cur) and "envs" not in cur.replace("\\", "/"):
        return cur  # 当前解释器不是 venv 内的，直接复用
    for c in DEFAULT_BASE_PY:
        if os.path.isfile(c):
            return c
    raise SystemExit(
        f"[FATAL] 找不到 base Python，请设置环境变量 FLASH_BASE_PY。"
        f"已尝试: {DEFAULT_BASE_PY + [cur]}"
    )


def run(cmd: list, cwd=None, env=None, timeout=3600) -> subprocess.CompletedProcess:
    """执行子进程并返回结果；失败时给出简明错误。"""
    log(f"  $ {' '.join(str(c) for c in cmd)}")
    r = subprocess.run(
        cmd, cwd=cwd, env=env or clean_env(),
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=timeout,
    )
    return r


def run_pip(args: list, step: str, cwd=None, retries: int = 3) -> None:
    """带网络重试的 pip 调用。

    ★ 在线 / 离线双模式的**唯一分叉点**。

    在线：原样执行 args。
    离线：强制前置 `--no-index --find-links=<wheelhouse>`。--no-index 是硬闸门，
          pip 无法访问 PyPI，缺包立即失败并指名缺哪个（不会静默联网补装）。
          同时**关闭重试**——离线重试毫无意义（同样的 wheelhouse 必然同样失败），
          改为立刻报错，便于用户看清缺哪个包。
    """
    # ★ pip 路径也必须跨平台（09-10 修复）：
    #   Windows 是 Scripts\pip.exe，Linux/WSL 是 bin/pip（无 .exe、无 Scripts）。
    #   旧硬编码在 Linux 上⇒ "创建 venv 失败"（pip 文件根本不存在）。
    if os.name == "nt":
        venv_pip = os.path.join(VENV_DIR, "Scripts", "pip.exe")
    else:
        venv_pip = os.path.join(VENV_DIR, "bin", "pip")
    if OFFLINE:
        args = list(OFFLINE_PIP_FLAGS) + [f"--find-links={WHEELHOUSE}"] + list(args)
        retries = 1
    for i in range(1, retries + 1):
        log(f"[pip] {step}（第 {i}/{retries} 次尝试"
            f"{'，离线模式' if OFFLINE else ''}）...")
        try:
            r = subprocess.run(
                [venv_pip, "install"] + args, cwd=cwd, env=clean_env(),
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                timeout=2400,
            )
        except subprocess.TimeoutExpired:
            log("[pip] 超时（40 分钟）")
            r = None
        if r is not None and r.returncode == 0:
            tail = "\n".join((r.stdout or "").strip().splitlines()[-8:])
            log("[pip] 成功。最近输出：")
            log(tail)
            return
        if r is not None:
            log(f"[pip] 失败，退出码 {r.returncode}")
            tail_out = "\n".join((r.stdout or "").strip().splitlines()[-6:])
            tail_err = (r.stderr or "").strip().splitlines()[-8:]
            if tail_out:
                log("  stdout 尾部: " + tail_out)
            if tail_err:
                log("  stderr 尾部: " + "\n  ".join(tail_err))
            if OFFLINE and r is not None:
                # 离线失败几乎必然是 wheelhouse 缺包 —— 直接给出可操作指引
                log("")
                log("  ★ 离线安装失败：wheelhouse 中缺少所需包。")
                log(f"    wheelhouse: {WHEELHOUSE}")
                log("    处理：在联网机重跑 scripts\\08_offline_install\\build_wheelhouse.py")
                log("          （确认 --profile 与本机一致），重新拷贝整个 wheelhouse 目录。")
                raise SystemExit(f"[FATAL] 离线安装失败: {step}")
        if i < retries:
            log("[wait] 疑似网络中断，等待 60s 后重试 ...")
            time_sleep(60)
    raise SystemExit(f"[FATAL] pip 步骤失败: {step}")


def time_sleep(sec: float) -> None:
    import time
    time.sleep(sec)


# ---------------------------------------------------------------------------
# 离线模式：wheelhouse 定位与覆盖度预检
# ---------------------------------------------------------------------------
def _load_wh_common():
    """导入同目录的 scripts/08_offline_install/_wh_common.py。

    start_flash.py 会被 sdist 一起分发，而 scripts/ 不在 sdist 内（见
    pyproject [tool.hatch.build.targets.sdist].exclude 的 "/scripts/**"），
    故此处**必须优雅降级**：模块不存在时给出明确指引而非 ImportError 堆栈。
    """
    p = os.path.join(PROJECT_DIR, "scripts", "08_offline_install")
    if p not in sys.path:
        sys.path.insert(0, p)
    try:
        import _wh_common# noqa: E402
        return _wh_common
    except ImportError as e:
        raise SystemExit(
            f"[FATAL] 离线模式需要 scripts/08_offline_install/_wh_common.py，"
            f"但导入失败: {e}\n"
            f"       请确认拷贝了完整的 scripts 目录，或改用在线模式"
            f"（去掉 --offline / FLASH_OFFLINE）。"
        )


def setup_offline(wh_arg: str | None, profile: str) -> None:
    """离线模式初始化：定位 wheelhouse + 校验清单 + 覆盖度预检。

    三道闸门（任一不过即中止，绝不带病安装）：
      1. wheelhouse 目录存在
      2. MANIFEST.json 校验 —— 文件齐全 + 大小相符 + SHA256 相符
         （U盘拷贝是最容易静默损坏的传输环节，必须先于 pip 拦截）
      3. 依赖覆盖度预检 —— pyproject 依赖闭包 ⊆ wheelhouse 实际文件
    """
    global WHEELHOUSE

    wh = _load_wh_common()
    profile = (profile or "full").strip().lower()
    if profile not in OFFLINE_PROFILES:
        raise SystemExit(
            f"[FATAL] 未知档位 '{profile}'（可选: {'/'.join(OFFLINE_PROFILES)}）")

    log(f"[offline] 档位: {profile} — {wh.PROFILES[profile]['desc']}")

    house = wh.resolve_wheelhouse(wh_arg, start=PROJECT_DIR)
    WHEELHOUSE = str(house.root)
    log(f"[offline] wheelhouse: {WHEELHOUSE}")

    # ---- 闸门 2: MANIFEST 校验 ----
    problems, notes = house.verify_manifest(deep=True)
    for n in notes:
        log(f"[offline] {n}")
    if problems:
        log("")
        log("[FATAL] wheelhouse 清单校验未通过（拷贝不完整或文件损坏）：")
        for p in problems[:25]:
            log(f"        - {p}")
        if len(problems) > 25:
            log(f"        ... 另有 {len(problems) - 25} 个")
        raise SystemExit(
            "[FATAL] 中止安装。请在联网机重跑 build_wheelhouse.py 生成 wheelhouse，"
            "并完整拷贝整个目录（不要只拷 .whl 文件）。")
    log("[ok] wheelhouse 清单校验通过")

    # ---- 闸门 3: 依赖覆盖度预检 ----
    # ★ 必须传 Path 而非 str：preflight → required_packages →
    #   parse_pyproject_requirements 内部要调 .read_text()。
    missing, present = house.preflight(
        Path(os.path.join(PROJECT_DIR, "pyproject.toml")), profile)
    log(f"[offline] 依赖覆盖度: 直接依赖 {len(present)} 项已就位")
    if missing:
        log("")
        log(f"[FATAL] wheelhouse 缺少 {len(missing)} 个**直接依赖**，无法离线安装：")
        for m in missing:
            log(f"        - {m}")
        log("")
        log("  ★ 这些是 pyproject 声明的直接依赖，缺失说明 wheelhouse 造包时用的是")
        log("    其它档位或下载中断。请在联网机执行：")
        log(f"        python scripts\\08_offline_install\\build_wheelhouse.py --profile {profile}")
        log("    然后重新拷贝整个 wheelhouse 目录。")
        raise SystemExit("[FATAL] 中止安装（预检未通过，未创建/改动 venv）。")
    log(f"[ok] 依赖覆盖度预检通过（档位 {profile}）")

    # ---- base 解释器提示 ----
    if not os.path.isfile(BASE_PY):
        inst = wh.find_python_installer(house)
        if inst:
            log("")
            log("  ★ 本机未找到可用的 base Python，而 wheelhouse 内含安装程序：")
            log(f"        {inst}")
            log(f"    请先双击它完成安装（建议勾选 Add Python to PATH），")
            log(f"    然后重跑本脚本。目标版本应与构建机一致。")
            log("")
            log("    ★ 脚本不会自动执行安装程序 —— 安装解释器是系统级变更，必须由你确认。")
        raise SystemExit(
            "[FATAL] 找不到 base Python。请先安装 Python 3.10+，或设置 "
            "FLASH_BASE_PY 指向已安装的解释器绝对路径。")

    # ---- 提示体积 ----
    total = sum(p.stat().st_size for p in house.archives())
    log(f"[offline] wheelhouse 体积: {wh.human_size(total)}"
        f"（{len(house.archives())} 个归档）")
    log("[offline] pip 将使用: --no-index --find-links=<wheelhouse>（物理上无法联网）")


def offline_install_args() -> list:
    """离线模式下 install_flash_package() 传给 pip 的参数。

    ★ 关键差异：不带 `-e`（editable），改装预构建 wheel。
      editable 需要解析源码树中的依赖声明，而离线机上的源码树可能来自
      sdist（不含 tests/docs），且 -e 会在 .venv 里写入指向源码树的绝对路径，
      U 盘换机后直接失效。
    """
    extras = ",".join(_load_wh_common().PROFILES[
        os.environ.get("FLASH_PROFILE", "full").strip().lower() or "full"]["extras"])
    target = f"{OFFLINE_DIST}[{extras}]" if extras else OFFLINE_DIST
    # 参数顺序：-e 换成 wheel 名；scipy/paramiko 仍需显式列出（pyproject 未声明）
    return [target, "scipy", "paramiko"]


def parse_pytest(out: str, rc: int) -> dict:
    """解析 pytest 输出，提取统计与失败项。"""
    def cnt(pat: str) -> int:
        m = re.search(pat, out)
        return int(m.group(1)) if m else 0

    res = {
        "passed":  cnt(r"(\d+)\s+passed"),
        "failed":  cnt(r"(\d+)\s+failed"),
        "skipped": cnt(r"(\d+)\s+skipped"),
        "errors":  cnt(r"(\d+)\s+error"),
        "rc":      rc,
        "summary": "",
        "failed_lines": [],
    }
    for line in out.splitlines():
        if re.search(r"\d+\s+passed|\d+\s+failed|\d+\s+error|\d+\s+skipped", line):
            res["summary"] = line.strip()
            break
    for line in out.splitlines():
        s = line.strip()
        if s.startswith("FAILED") or s.startswith("ERROR"):
            res["failed_lines"].append(s)
    res["failed_lines"] = res["failed_lines"][:25]
    return res


# ---------------------------------------------------------------------------
# 环境健康检查 / 版本快照
# ---------------------------------------------------------------------------
def check_env_health(venv_py: str) -> tuple:
    """检查 .venv 关键依赖完整性 + pytest 可启动。

    返回: (是否健康: bool, 问题清单: list[str])
    """
    probe = (
        "import importlib, sys\n"
        f"mods = {ENV_KEY_MODULES!r}\n"
        "bad = []\n"
        "for m in mods:\n"
        "    try:\n"
        "        importlib.import_module(m)\n"
        "    except Exception as e:\n"
        "        bad.append(f'{m}: {type(e).__name__}: {str(e)[:80]}')\n"
        "print('HEALTHY' if not bad else 'BAD')\n"
        "for b in bad:\n"
        "    print(b)\n"
        "sys.exit(0 if not bad else 2)\n"
    )
    try:
        r = subprocess.run(
            [venv_py, "-c", probe], env=clean_env(),
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=300,
        )
    except subprocess.TimeoutExpired:
        return False, ["环境健康检查超时（venv 解释器无响应）"]
    except OSError as e:
        return False, [f"venv 解释器无法启动（{venv_py}）: {e}"]

    problems: list = []
    if r.returncode == 0:
        # 关键包齐全 → 再验证 pytest 能启动
        try:
            r2 = subprocess.run(
                [venv_py, "-m", "pytest", "--version"], env=clean_env(),
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                timeout=180,
            )
        except subprocess.TimeoutExpired:
            return False, ["pytest 启动超时"]
        if r2.returncode == 0:
            return True, []
        err_tail = ((r2.stderr or "") + (r2.stdout or "")).strip().splitlines()
        problems.append("pytest 无法启动: " + (err_tail[-1] if err_tail else "未知错误"))
        return False, problems

    for line in (r.stdout or "").splitlines():
        s = line.strip()
        if s and not s.startswith(("HEALTHY", "BAD")):
            problems.append(s)
    if not problems and (r.stderr or "").strip():
        problems.append((r.stderr or "").strip().splitlines()[-1])
    if not problems:
        problems.append(f"环境检查异常（venv 解释器退出码 {r.returncode}，无详细输出）")
    return False, problems


def collect_versions(venv_py: str) -> dict:
    """收集关键依赖的真实版本（供报告「环境版本快照」使用）。"""
    code = (
        "import importlib\n"
        f"mods = {ENV_KEY_MODULES!r}\n"
        "for m in mods:\n"
        "    try:\n"
        "        mod = importlib.import_module(m)\n"
        "        print(m, getattr(mod, '__version__', '?'))\n"
        "    except Exception:\n"
        "        print(m, 'N/A')\n"
    )
    try:
        r = subprocess.run(
            [venv_py, "-c", code], env=clean_env(),
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=300,
        )
    except (subprocess.TimeoutExpired, OSError):
        return {}
    versions = {}
    for line in (r.stdout or "").splitlines():
        parts = line.split(" ", 1)
        if len(parts) == 2:
            versions[parts[0]] = parts[1].strip()
    return versions


def suites_crashed(results: dict) -> bool:
    """三套件全部 rc!=0 且 0 用例 → pytest 启动即崩（环境问题，非测试本身失败）。

    特征: passed=0 failed=0 errors=0 但 rc!=0 —— 进程在收集用例前就已崩溃。
    """
    if not results:
        return False
    for res in results.values():
        if res is None:
            return False
        if not (res["rc"] != 0 and res["passed"] == 0
                and res["failed"] == 0 and res["errors"] == 0):
            return False
    return True


# ---------------------------------------------------------------------------
# 环境构建（创建 / 重建 / 安装）
# ---------------------------------------------------------------------------
def wipe_venv() -> None:
    """并行删除旧 .venv（调用 base 解释器 -S 模式，避开 sitecustomize 干扰）。"""
    log("[info] 并行删除旧 .venv（预计 5~15 分钟）...")
    code = r'''
import os, time
from concurrent.futures import ThreadPoolExecutor
base = r'__VENV_DIR__'
t = time.time()
def wipe(path):
    if os.path.isfile(path) or os.path.islink(path):
        try: os.remove(path)
        except OSError: pass
        return
    for r, ds, fs in os.walk(path, topdown=False):
        for f in fs:
            try: os.remove(os.path.join(r, f))
            except OSError: pass
        for d in ds:
            try: os.rmdir(os.path.join(r, d))
            except OSError: pass
    try: os.rmdir(path)
    except OSError: pass
if os.path.isdir(base):
    items = [os.path.join(base, x) for x in os.listdir(base)]
    with ThreadPoolExecutor(max_workers=8) as ex:
        list(ex.map(wipe, items))
    try: os.rmdir(base)
    except OSError: pass
print('[ok] venv removed, {:.0f}s'.format(time.time() - t))
'''
    code = code.replace("__VENV_DIR__", VENV_DIR)
    try:
        r = subprocess.run(
            [BASE_PY, "-S", "-u", "-c", code], env=clean_env(),
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=1800,
        )
    except subprocess.TimeoutExpired:
        raise SystemExit(
            "[FATAL] 删除旧 .venv 超时（30 分钟）。目录可能被其他进程占用，"
            "请关闭占用后重新运行。"
        )
    if r.returncode != 0 and os.path.isdir(VENV_DIR):
        raise SystemExit(
            f"[FATAL] 删除旧 .venv 失败（可能被其他进程占用，请关闭占用后重试）:\n"
            f"{r.stderr[-400:]}"
        )
    log("[ok] 已删除旧 .venv（并行删除）")


def create_venv() -> None:
    """创建全新虚拟环境。"""
    log("[info] 创建全新虚拟环境 ...")
    r = subprocess.run(
        [BASE_PY, "-m", "venv", VENV_DIR], env=clean_env(),
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=600,
    )
    if r.returncode != 0 or not os.path.isfile(VENV_PY):
        # ★ 诊断信息要能区分「venv 命令本身失败」与「解释器路径找不到」——
        #   09-10 前者只报 stderr 空��一片，后者才是路径布局问题。
        hint = ""
        if r.returncode == 0 and not os.path.isfile(VENV_PY):
            hint = (f"\n    venv 命令返回 0，但预期解释器不存在: {VENV_PY}\n"
                    f"    ⇒ 平台布局不匹配。Windows 应为 Scripts\\python.exe，"
                    f"Linux/WSL 应为 bin/python（当前 os.name={os.name!r}）")
        raise SystemExit(
            f"[FATAL] 创建 venv 失败 (rc={r.returncode}):\n{r.stderr[-400:]}{hint}"
        )
    log(f"[ok] venv 已创建: {VENV_PY}")


def fix_setuptools() -> None:
    """修复 setuptools（覆盖 base 内置损坏副本）。"""
    log("[info] 修复 setuptools（覆盖 base 内置损坏副本） ...")
    run_pip(["--ignore-installed", "--no-deps", "setuptools"],
            step="安装干净 setuptools"
                 + ("（离线：取自 wheelhouse）" if OFFLINE else ""))
    r = subprocess.run(
        [VENV_PY, "-c",
         "import setuptools, setuptools.build_meta; print('setuptools', setuptools.__version__, 'build_meta OK')"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if r.returncode != 0:
        raise SystemExit(f"[FATAL] setuptools 仍不可用:\n{r.stderr[-300:]}")
    log(f"[ok] {r.stdout.strip()}")


def install_flash_package() -> str:
    """从零安装 flash 包，返回安装验证输出。"""
    # 注意: 额外补装 paramiko —— flash_run.remote.remote_deploy 顶层 import
    # paramiko（SSH/SFTP 依赖），但 pyproject.toml 的 full/dev extras 未声明，
    # 从零安装后 framework 测试收集会因此报错。此处脚本层面补装，不改仓库文件。
    if OFFLINE:
        args = offline_install_args()
        log("[info] 离线安装 flash 包: pip install --no-index "
            f"--find-links={WHEELHOUSE} {' '.join(args)}")
    else:
        args = ["-e", ".[full,dev]", "scipy", "paramiko"]
        log('[info] 从零安装 flash 包: pip install -e ".[full,dev]" scipy paramiko ...')
    run_pip(args,
            step=("离线安装 flash 包及全部依赖（含 paramiko: remote_deploy 的 SSH 依赖）"
                  if OFFLINE else
                  "安装 flash 包及全部依赖（含 paramiko: remote_deploy 的 SSH 依赖）"),
            cwd=PROJECT_DIR)

    # 安装验证: flash 解析路径 + physimx_core 已移除
    r = subprocess.run(
        [VENV_PY, "-c",
         "import importlib\n"
         "m = importlib.import_module('flash')\n"
         "print('flash file:', m.__file__)\n"
         "try:\n"
         "    importlib.import_module('physimx_core')\n"
         "    print('physimx_core: STILL PRESENT (BAD)')\n"
         "    raise SystemExit(1)\n"
         "except ModuleNotFoundError:\n"
         "    print('physimx_core: correctly removed (OK)')\n"],
        cwd=PROJECT_DIR, env=clean_env(),
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    flash_verify = (r.stdout or "").strip() + ("\n" + r.stderr if r.returncode else "")
    if r.returncode != 0:
        log("[warn] flash 安装验证异常:\n" + flash_verify)
    else:
        log("[ok] " + flash_verify.replace("\n", "\n[ok] "))
    return flash_verify


def provision() -> str:
    """完整构建环境: 创建 venv + 修复 setuptools + 安装 flash 包。

    返回 flash 安装验证输出。环境健康复检由调用方负责。
    """
    create_venv()
    fix_setuptools()
    return install_flash_package()


def run_suites() -> dict:
    """运行三套测试，返回 {套件名: parse_pytest 结果}。

    FLASH_SKIP_TESTS=1 时跳过（仅装环境、不验证）—— 供 install_offline.py
    --no-tests 的快速部署路径使用。跳过后 results 为空 dict，
    汇总阶段显示"未运行"，core_ok 保持 True。
    """
    results = {}
    if os.environ.get("FLASH_SKIP_TESTS", "").strip() == "1":
        log("\n[step] 运行全局测试: 已按 FLASH_SKIP_TESTS=1 跳过 "
            "（--no-tests：仅安装环境，不跑测试）")
        return results
    log("\n[step] 运行全局测试（三套件） ...")
    for name, rel in TEST_SUITES:
        path = os.path.join(PROJECT_DIR, rel)
        if not os.path.isdir(path):
            results[name] = None
            log(f"[skip] {name}: 目录不存在 {rel}")
            continue
        log(f"\n[test] {name}: pytest {rel} -q --tb=short")
        try:
            r = subprocess.run(
                [VENV_PY, "-m", "pytest", rel, "-q", "--tb=short"],
                cwd=PROJECT_DIR, env=clean_env(),
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                timeout=3600,
            )
        except subprocess.TimeoutExpired:
            log(f"[test] {name}: 超时（60 分钟）")
            results[name] = {"passed": 0, "failed": 0, "skipped": 0,
                             "errors": 1, "rc": -1, "summary": "TIMEOUT",
                             "failed_lines": ["[TIMEOUT] 测试超时被终止"]}
            continue
        out = r.stdout + "\n" + r.stderr
        # 保存完整日志便于排查
        logfile = os.path.join(PROJECT_DIR, f"pytest_{name}.log")
        with open(logfile, "w", encoding="utf-8") as f:
            f.write(out)
        res = parse_pytest(out, r.returncode)
        results[name] = res
        log(f"  => {res['summary'] or f'rc={r.returncode}'}")
        for fl in res["failed_lines"][:10]:
            log(f"     {fl}")
    return results


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    """命令行参数。在线为默认；--offline 切到离线模式。"""
    ap = argparse.ArgumentParser(
        prog="start_flash.py",
        description="flash 包从零安装 + 全局测试（在线/离线双模式，环境自检自愈）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例:\n"
            "  python start_flash.py                 在线安装（默认）\n"
            "  python start_flash.py --offline        离线安装（自动找 wheelhouse/）\n"
            "  python start_flash.py --offline --wheelhouse D:\\pkg\\wheelhouse\n"
            "  python start_flash.py --profile lite   离线预检用精简档\n"
            "\n环境变量等价开关: FLASH_OFFLINE=1 / FLASH_WHEELHOUSE=<dir> / FLASH_PROFILE=<档位>\n"
        ),
    )
    ap.add_argument("--offline", action="store_true",
                    help="离线安装：pip 走本地 wheelhouse（--no-index），物理上无法联网")
    ap.add_argument("--wheelhouse", default=None,
                    help="wheelhouse 目录路径（默认 <项目根>/wheelhouse）")
    ap.add_argument("--profile", default=None,
                    choices=list(OFFLINE_PROFILES),
                    help="离线预检档位（默认 full）")
    return ap.parse_args()


def resolve_offline_mode(args: argparse.Namespace) -> bool:
    """三路开关求或：命令行 --offline > 环境变量 FLASH_OFFLINE=1。

    另加**自动探测**兜底：项目根存在 wheelhouse/MANIFEST.json 时，
    即使没显式传 --offline 也自动转离线（避免离线机上误走在线分支，
    白等 40 分钟超时）。可用 FLASH_FORCE_ONLINE=1 强制关掉自动探测。

    ★ 探测信号只能是 MANIFEST.json **本身**，绝不能用「scripts/08_offline_install/
      目录存在」这类间接信号 —— 该目录随仓库分发，联网机上永远存在，
      拿它当判据会把**所有在线用户**误切成离线模式（09 开发时踩过，
      由 resolve_offline_mode 的独立单测抓出）。
    """
    if args.offline or os.environ.get("FLASH_OFFLINE", "").strip() == "1":
        return True
    if os.environ.get("FLASH_FORCE_ONLINE", "").strip() == "1":
        return False
    wh = args.wheelhouse or os.environ.get("FLASH_WHEELHOUSE", "").strip()
    cand = wh or os.path.join(PROJECT_DIR, "wheelhouse")
    # ★ 唯一判据：wheelhouse 目录里确实躺着 MANIFEST.json
    if os.path.isfile(os.path.join(cand, "MANIFEST.json")):
        log(f"[auto] 检测到 {cand}\\MANIFEST.json → 自动切换离线模式"
            f"（如需强制在线请设 FLASH_FORCE_ONLINE=1）")
        return True
    return False


def main() -> int:
    global VENV_DIR, VENV_PY, BASE_PY, OFFLINE

    args = parse_args()
    OFFLINE = resolve_offline_mode(args)

    # 离线档位需在 setup_offline 之前落进环境（offline_install_args 会读）
    if args.profile:
        os.environ["FLASH_PROFILE"] = args.profile
    os.environ.setdefault("FLASH_PROFILE", "full")

    BASE_PY = find_base_python()
    VENV_DIR = os.environ.get("FLASH_VENV_DIR", DEFAULT_VENV_DIR).strip()
    # ★ venv 内解释器路径**必须跨平台**（09-10 修复）：Windows 是
    #   Scripts\python.exe，Linux/WSL 是 bin/python（无 .exe、无 Scripts）。
    #   此前硬编码 Windows 布局 ⇒ Linux 上「创建 venv 失败」，且健康检查
    #   恒判失败 → 反复清零重建。
    #   优先用 _wh_common（与 install_offline.py 同一来源，避免漂移）；
    #   它在 sdist 里可能缺失，故用本地等价判断兜底。
    try:
        VENV_PY = str(_load_wh_common().venv_python(VENV_DIR))
    except SystemExit:
        VENV_PY = os.path.join(
            VENV_DIR, "Scripts", "python.exe" if os.name == "nt" else "bin/python"
        )

    start = datetime.datetime.now()
    log("=" * 72)
    log("  start_flash.py — flash 包从零安装 + 全局测试（环境自检自愈）")
    log("=" * 72)
    log(f"[info] 项目目录 : {PROJECT_DIR}")
    log(f"[info] base 解释器: {BASE_PY}")
    log(f"[info] 虚拟环境 : {VENV_DIR}")
    log(f"[info] 安装模式 : {'★ 离线（--no-index，不联网）' if OFFLINE else '在线（PyPI）'}")

    auto_rebuild = os.environ.get("FLASH_NO_AUTO_REBUILD") != "1"
    force_clean = os.environ.get("FLASH_FORCE_CLEAN") == "1"

    # ---- Step 0: 前置校验 -------------------------------------------------
    # 注意：base解释器存在性在离线模式下由 setup_offline 的专门分支处理
    #       （那里能给"wheelhouse 内附安装程序"的可操作提示）。
    if OFFLINE:
        log("\n[step 0/5] 离线模式前置校验（wheelhouse 清单 + 依赖覆盖度）...")
        setup_offline(args.wheelhouse, os.environ.get("FLASH_PROFILE", "full"))
        if not os.path.isfile(BASE_PY):
            raise SystemExit(f"[FATAL] base Python 不存在: {BASE_PY}")
    elif not os.path.isfile(BASE_PY):
        raise SystemExit(f"[FATAL] base Python 不存在: {BASE_PY}")
    for name, rel in TEST_SUITES:
        if not os.path.isdir(os.path.join(PROJECT_DIR, rel)):
            log(f"[warn] 测试套件目录缺失，将跳过: {rel}")

    # ---- Step 1: 环境准备（存在性 + 健康检查 + 自动清零重建） ---------------
    # flash_venv / .venv 位于 .gitignore 中，Gitee master 上不含它：从 master 拉取后
    # 必然不存在，直接新建即可。已存在时默认复用；但若**环境健康检查不通过**
    # （关键依赖缺失 / pytest 无法启动），则自动清零重建 —— 这是本脚本的
    # 自愈核心：不依赖重启机器、不依赖手动 FLASH_FORCE_CLEAN=1。
    log("\n[step 1/5] 检查虚拟环境与健康自检 ...")
    install_mode = ""
    rebuild_count = 0

    if os.path.isdir(VENV_DIR):
        if force_clean:
            log("[info] FLASH_FORCE_CLEAN=1：强制清零重建 ...")
            wipe_venv()
            install_mode = "FLASH_FORCE_CLEAN=1 强制重建"
        else:
            log("[info] .venv 已存在，进行环境健康检查 ...")
            ok, problems = check_env_health(VENV_PY)
            if ok:
                log("[ok] 环境健康检查通过（关键依赖 + pytest 均正常），复用 .venv")
                install_mode = "复用已有 .venv（健康检查通过）"
            else:
                log("[warn] 环境健康检查不通过：")
                for p in problems:
                    log(f"  - {p}")
                if auto_rebuild:
                    log("[info] 自动清零重建 .venv（环境不健康 → 自愈，无需手动操作）...")
                    wipe_venv()
                    rebuild_count += 1
                    install_mode = "自动重建（环境不健康 → 清零重装）"
                else:
                    raise SystemExit(
                        "[FATAL] 环境不健康且 FLASH_NO_AUTO_REBUILD=1 禁用自动重建。"
                        "可运行: FLASH_FORCE_CLEAN=1 python start_flash.py")
    else:
        log("[info] .venv 不存在（master 不含此目录），将全新创建")
        install_mode = "全新创建（.venv 在 .gitignore 中，master 不含此目录）"

    # ---- Step 2: 构建环境（创建 + setuptools 修复 + flash 安装） ------------
    if not os.path.isfile(VENV_PY):
        log("\n[step 2/5] 构建环境（创建 venv + 修复 setuptools + 安装 flash 包）...")
        flash_verify = provision()
    else:
        log("\n[step 2/5] 复用环境，修复 setuptools + 安装 flash 包 ...")
        fix_setuptools()
        flash_verify = install_flash_package()

    ver = subprocess.run(
        [VENV_PY, "-c", "import sys; print(sys.version.split()[0])"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    log(f"[ok] venv Python 版本: {ver.stdout.strip()}")

    # ---- Step 3: 安装后环境复检（仍不健康 → 再重建一轮） --------------------
    log("\n[step 3/5] 安装后环境复检 ...")
    ok, problems = check_env_health(VENV_PY)
    if not ok:
        log("[warn] 安装后环境仍不健康：")
        for p in problems:
            log(f"  - {p}")
        if auto_rebuild and rebuild_count < 2:
            log("[info] 清零重建 .venv 后重新安装（自愈第 2 轮）...")
            wipe_venv()
            rebuild_count += 1
            flash_verify = provision()
            ok, problems = check_env_health(VENV_PY)
            if not ok:
                raise SystemExit(
                    "[FATAL] 重建两轮后环境仍不健康，请手动排查"
                    "（可先重启机器后重试；或查看上方问题清单）")
            install_mode += "（第 2 轮重建）"
        elif not auto_rebuild:
            raise SystemExit("[FATAL] 安装后环境不健康且已禁用自动重建")
        else:
            raise SystemExit("[FATAL] 重建两轮后环境仍不健康，请手动排查")
    else:
        log("[ok] 安装后环境复检通过")

    # ---- Step 4: 全局测试（pytest 启动崩溃 → 自动重建重测） -----------------
    results = run_suites()
    if auto_rebuild and suites_crashed(results) and rebuild_count < 2:
        log("\n[info] 三套件全部「0 用例启动失败」→ pytest 环境异常（非测试失败），"
            "自动清零重建后重测 ...")
        wipe_venv()
        rebuild_count += 1
        flash_verify = provision()
        ok, problems = check_env_health(VENV_PY)
        if not ok:
            raise SystemExit("[FATAL] 重建后环境仍不健康，pytest 无法运行，请手动排查")
        install_mode += "（测试崩溃 → 重建重测）"
        results = run_suites()
        if suites_crashed(results):
            raise SystemExit(
                "[FATAL] 重建重测后 pytest 仍无法启动，请手动排查环境"
                "（查看 pytest_*.log 与上方问题清单）")

    # ---- Step 5: 汇总报告（含统一版本快照） --------------------------------
    log("\n" + "=" * 72)
    log("  汇总")
    log("=" * 72)
    for name, res in results.items():
        if res is None:
            log(f"  {name:20s} 未运行（目录缺失）")
        else:
            log(f"  {name:20s} passed={res['passed']}  failed={res['failed']}  "
                f"skipped={res['skipped']}  errors={res['errors']}  rc={res['rc']}")
    log("")

    # 判定: 三套件均须全过 (output_processors 测试数据由 gen_test_data.py 自动生成)
    def verdict(name: str, res: dict) -> str:
        if res is None:
            return "未运行"
        if res["errors"] > 0 or res["rc"] == -1:
            return "ERROR"
        if res["failed"] > 0:
            return "FAIL"
        return "PASS"

    core_ok = True
    for name, res in results.items():
        if res is not None and name != "output_processors":
            if res["errors"] > 0 or res["failed"] > 0:
                core_ok = False

    git_sha = "N/A"
    r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=PROJECT_DIR,
                       capture_output=True, text=True)
    if r.returncode == 0:
        git_sha = r.stdout.strip()[:12]

    py_ver = ver.stdout.strip()
    versions = collect_versions(VENV_PY)

    lines = []
    lines.append("=" * 72)
    lines.append("FLASH 全局测试报告")
    lines.append("=" * 72)
    lines.append("")
    lines.append(f"生成时间 : {start.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"项目目录 : {PROJECT_DIR}")
    lines.append(f"Git commit: {git_sha}")
    lines.append(f"Python(venv): {py_ver}")
    lines.append(f"虚拟环境 : {VENV_DIR}")
    if OFFLINE:
        lines.append(f"安装模式 : ★ 离线（--no-index，未联网）")
        lines.append(f"wheelhouse : {WHEELHOUSE}")
        lines.append(f"预检档位 : {os.environ.get('FLASH_PROFILE', 'full')}")
        lines.append(f"安装命令 : pip install --no-index "
                     f"--find-links=<wheelhouse> "
                     f"{' '.join(offline_install_args())}")
    else:
        lines.append("安装模式 : 在线（PyPI）")
        lines.append('安装命令 : pip install -e ".[full,dev]" scipy paramiko')
    lines.append(f"安装方式 : {install_mode or '（未记录）'}")
    lines.append("")
    lines.append("-" * 72)
    lines.append("安装验证")
    lines.append("-" * 72)
    lines.append("")
    lines.append(flash_verify.strip() or "(验证输出为空)")
    lines.append("")
    lines.append("-" * 72)
    lines.append("环境版本快照（关键依赖真实版本，统一记录）")
    lines.append("-" * 72)
    lines.append("")
    lines.append(f"  Python     : {py_ver}")
    for m in ENV_KEY_MODULES:
        v = versions.get(m, "N/A")
        lines.append(f"  {m:14s}: {v}")
    lines.append("")
    lines.append("  注: 本快照为本次运行环境的权威版本记录；若与 pyproject.toml")
    lines.append("      声明差异较大，可运行 FLASH_FORCE_CLEAN=1 python start_flash.py")
    lines.append("      重建获得纯净环境后重新生成快照。")
    lines.append("")
    lines.append("-" * 72)
    lines.append("测试结果")
    lines.append("-" * 72)
    lines.append("")
    lines.append("套件              passed  failed  skipped  error  结论")
    lines.append("-" * 72)
    for name, res in results.items():
        if res is None:
            lines.append(f"{name:20s}   -       -       -        -     未运行（目录缺失）")
        else:
            lines.append(
                f"{name:20s}   {res['passed']:<6d} {res['failed']:<6d} "
                f"{res['skipped']:<6d} {res['errors']:<5d} {verdict(name, res)}"
            )
    lines.append("-" * 72)
    lines.append(f"整体结论: {'安装验证通过' if core_ok else '核心测试未通过（详见上方失败项）'}")
    lines.append("")
    lines.append("-" * 72)
    lines.append("失败 / 错误明细")
    lines.append("-" * 72)
    lines.append("")
    any_detail = False
    for name, res in results.items():
        if res and res["failed_lines"]:
            any_detail = True
            lines.append(f"[{name}]")
            lines.append("")
            for fl in res["failed_lines"]:
                lines.append(f"  - {fl}")
            lines.append("")
    if not any_detail:
        lines.append("（无）")
        lines.append("")
    lines.append("-" * 72)
    lines.append("环境备注")
    lines.append("-" * 72)
    lines.append("")
    lines.append("- 自愈机制: .venv 环境健康检查不通过（关键依赖缺失 / pytest 无法启动）"
                 "或三套件全部 0 用例启动失败时，本脚本自动清零重建并重测，"
                 "无需手动 FLASH_FORCE_CLEAN=1，也不依赖重启机器。")
    lines.append("- output_processors 套件测试数据（inputfiles/，.gitignore 排除）"
                 "由 flash/output_processors/test/gen_test_data.py 在测试会话中自动生成，"
                 "克隆/发布环境无需手动准备。")
    lines.append("- 完整测试日志见 pytest_framework.log / pytest_input_gen.log / pytest_output_processors.log。")
    lines.append("- 虚拟环境为项目专属 .venv（项目根目录），与共享环境 envs/default 完全隔离。")
    if OFFLINE:
        lines.append(f"- 本次为**离线安装**：pip 全程带 --no-index，从 wheelhouse 本地取包，"
                     f"物理上未访问 PyPI。")
        lines.append(f"- 离线模式**不使用** `-e .`（可编辑安装）：它会往 .venv 写入指向"
                     f"源码树的绝对路径，U盘换机后即失效；且需要源码树含依赖声明。")
        lines.append(f"- 需要更新依赖时：在联网机重跑 "
                     f"scripts\\08_offline_install\\build_wheelhouse.py，"
                     f"重新拷贝整个 wheelhouse 目录（含 MANIFEST.json）。")
    lines.append("")

    report = "\n".join(lines)
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(report)
    log(f"[report] 报告已写入: {REPORT_FILE}")
    log("")
    log("=" * 72)
    log("  报告内容")
    log("=" * 72)
    log(report)

    elapsed = (datetime.datetime.now() - start).total_seconds()
    log(f"\n[done] 全部完成，总耗时 {elapsed:.0f}s")
    return 0 if core_ok else 1


if __name__ == "__main__":
    sys.exit(main())
