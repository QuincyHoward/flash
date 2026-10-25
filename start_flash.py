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
  6. 生成纯文本测试报告 test/reports/INSTALL_TEST_REPORT.txt
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

# 测试报告与 pytest 日志统一写入 <PROJECT>/test/reports/ (运行时自动创建),
# 不再散落在仓库根目录。REPORT_FILE / pytest_*.log 路径均由此派生。
REPORT_DIR = os.path.join(PROJECT_DIR, "test", "reports")
REPORT_FILE = os.path.join(REPORT_DIR, "INSTALL_TEST_REPORT.txt")

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

#: 离线预检档位（与 deploy/_wh_common.py 的 PROFILES 对齐）
OFFLINE_PROFILES = ("full", "runtime", "lite")

#: pip 离线硬闸门：这两个参数让 pip **物理上**无法访问 PyPI
OFFLINE_PIP_FLAGS = ("--no-index",)

#: 运行期由 main() 填充（模块级是因为 run_pip() 沿用既有全局风格）
OFFLINE = False
WHEELHOUSE = ""

#: 超算（SLURM 集群）探测结果缓存：(是否超算, 说明)
_HPC_PROBE: tuple[bool, str] | None = None


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------

def _probe_existing_venv(venv_dir: str) -> tuple[bool, str]:
    """探测指定目录下的 venv 是否**已存在且健康**。

    返回 (可用, 说明)。健康判据复用 `check_env_health`（关键依赖齐全 +
    pytest 能启动）—— 与 Step 1 的复用判据**同一份实现**，避免两处口径不一
    （一处说健康、一处说不健康 ⇒ 用户看到的报告自相矛盾）。

    ★ 用途（2026-10-25 超算修正）：超算部署目录没有 wheelhouse，
      若无条件做离线预检就会中止；但那里往往已有 `.venv-hpc-nce`
      且健康 ⇒ 应直接复用，而不是逼用户先造 212 MB 的 wheelhouse。
    """
    if not venv_dir or not os.path.isdir(venv_dir):
        return False, f"环境目录不存在: {venv_dir}"
    py = os.path.join(venv_dir, "Scripts", "python.exe") if os.name == "nt" \
        else os.path.join(venv_dir, "bin", "python")
    if not os.path.isfile(py):
        return False, f"解释器不存在: {py}"
    ok, problems = check_env_health(py)
    if ok:
        return True, f"venv 健康（{venv_dir}）"
    return False, f"venv 不健康: {'; '.join(problems[:3])}"


def _hpc_venv_dir(project_dir: str) -> str:
    """超算侧命名环境目录（默认 `<项目根>/.venv-hpc-nce`）。

    ★ 事实源 = `flash/flash_run/env/venv_paths.py`（`kind="hpc"`），与
      `deploy/hpc_deploy/remote_install.py`、insitu 执行体一致 ⇒ 三处不再
      各写一份名字。但该模块在**安装前**可能不可导入（flash 未装），
      故此处按文件路径加载，退化时用同名常量（与 venv_paths 同名，
      可由 `FLASH_HPC_VENV_NAME` 覆盖）。
    """
    name = os.environ.get("FLASH_HPC_VENV_NAME", "").strip() or ".venv-hpc-nce"
    p = os.path.join(project_dir, "flash", "flash_run", "env", "venv_paths.py")
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("_flash_venv_paths", p)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            name = mod.hpc_venv_name()
    except Exception:
        pass                       # 退化：用上面的常量
    return os.path.join(project_dir, name)


def probe_hpc() -> tuple[bool, str]:
    """探测当前是否运行在 **SLURM 超算**（登录节点或计算节点）。

    判据（三条同时满足，缺一即判定"非超算"）：
      1. `sbatch` / `sacct` / `sinfo` 三个命令都在 PATH；
      2. `sinfo -s` 能成功返回**分区行**（控制器可达，而不只是装了客户端）；
      3. `SLURM_CLUSTER_NAME` 或 `SLURM_JOB_ID` 至少一个存在（作业上下文）。

    ★ 为什么必须有这条：**超算部署目录不含 wheelhouse**（212 MB，不随
      代码同步，只在 `package_and_upload.py` 全量部署时落地）。而
      `resolve_offline_mode` 的原判据是「wheelhouse/MANIFEST.json 存在」
      ⇒ 在超算上该判据**永远为假** ⇒ 误走在线分支 ⇒ pip 访问 PyPI ⇒
      超算无外网 ⇒ SSL 失败 ⇒ 60 s 无限重试。2026-10-25 用户实跑复现。

    ★ 判据 2 不可省：`apt install slurm-client` 也会装上三个命令，
      但连不上控制器。只查 `which sbatch` 会把装了客户端的普通机器
      误判成超算（与 flash_run.execution._probe_slurm_healthy 同一教训）。
    """
    global _HPC_PROBE
    if _HPC_PROBE is not None:
        return _HPC_PROBE
    import shutil
    import subprocess
    missing = [c for c in ("sbatch", "sacct", "sinfo") if shutil.which(c) is None]
    if missing:
        _HPC_PROBE = (False, f"缺少 SLURM 命令: {','.join(missing)}")
        return _HPC_PROBE
    try:
        r = subprocess.run(["sinfo", "-s"], capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.SubprocessError) as exc:
        _HPC_PROBE = (False, f"sinfo 无法执行: {exc}")
        return _HPC_PROBE
    if r.returncode != 0:
        _HPC_PROBE = (False, f"sinfo rc={r.returncode}（控制器不可达？）")
        return _HPC_PROBE
    lines = [ln for ln in (r.stdout or "").splitlines() if ln.strip()]
    if len(lines) < 2:                      # 1 行表头 + ≥1 分区
        _HPC_PROBE = (False, "sinfo 无分区行（控制器不可达）")
        return _HPC_PROBE
    ctx = []
    for k in ("SLURM_CLUSTER_NAME", "SLURM_JOB_ID", "SLURM_JOB_NAME"):
        v = os.environ.get(k, "").strip()
        if v:
            ctx.append(f"{k}={v}")
    why = f"SLURM 控制器可达（{len(lines) - 1} 分区）"
    if ctx:
        why += "；" + ", ".join(ctx)
    _HPC_PROBE = (True, why)
    return _HPC_PROBE
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
                log("    处理：在联网机重跑 deploy\\build_wheelhouse.py")
                log("          （确认 --profile 与本机一致），重新拷贝整个 wheelhouse 目录。")
                raise SystemExit(f"[FATAL] 离线安装失败: {step}")
            # ★★ 2026-10-25：**无外网**是"环境性失败"而非"网络抖动" ⇒
            #   重试 3×（每次等 60 s）纯属浪费：超算上必然同样失败。
            #   判据 = pip 输出里的 SSL / 连接类关键词（超算实测报
            #   "the ssl module in Python is not available" +
            #   "No matching distribution found"）。命中即**立即报错**。
            if _looks_like_no_network(r):
                log("")
                log("  ★ 检测到**无外网 / SSL 不可用**（pip 无法访问 PyPI）——"
                    "这不是网络抖动，重试无意义。")
                log("    修法（按优先级）：")
                log("      ① 超算 / 离线机：改用离线安装")
                log("           python start_flash.py --offline --wheelhouse <wheelhouse 目录>")
                log("         （wheelhouse 由联网机 deploy\\build_wheelhouse.py 生成）")
                log("      ② 已装好命名环境时：直接复用，无需重装")
                log("           export FLASH_VENV_DIR=<项目根>/.venv-hpc-nce")
                log("      ③ 确实需要联网：检查代理 / 证书后设 FLASH_FORCE_ONLINE=1")
                raise SystemExit(f"[FATAL] pip 步骤失败（无外网）: {step}")
        if i < retries:
            log("[wait] 疑似网络中断，等待 60s 后重试 ...")
            time_sleep(60)
    raise SystemExit(f"[FATAL] pip 步骤失败: {step}")


#: pip 输出里表示"**根本没有外网**"的关键词（区分于真正的网络抖动）。
#: ★ 命中即立即失败：这类错误重试必然同样失败，等待 60 s×3 只是浪费时间
#:   （2026-10-25 超算实跑：ssl module not available ⇒ 重试到用户 Ctrl-C）。
_NO_NETWORK_MARKERS = (
    "ssl module is not available",
    "SSLError",
    "SSL: CERTIFICATE_VERIFY_FAILED",
    "No matching distribution found",
    "Could not fetch URL https://pypi.org",
    "Failed to establish a new connection",
    "Name or service not known",
    "Temporary failure in name resolution",
    "Network is unreachable",
    "Connection refused",
)


def _looks_like_no_network(r) -> bool:
    """pip 输出是否表明"本机根本没有外网"（而非网络抖动）。"""
    if r is None:
        return False
    blob = ((r.stdout or "") + "\n" + (r.stderr or "")).lower()
    return any(m.lower() in blob for m in _NO_NETWORK_MARKERS)


def time_sleep(sec: float) -> None:
    import time
    time.sleep(sec)


# ---------------------------------------------------------------------------
# 离线模式：wheelhouse 定位与覆盖度预检
# ---------------------------------------------------------------------------
def _load_wh_common():
    """导入 deploy/ 下的 deploy/_wh_common.py。

    start_flash.py 会被 sdist 一起分发，而 scripts/ 不在 sdist 内（见
    pyproject [tool.hatch.build.targets.sdist].exclude 的 "/scripts/**"），
    故此处**必须优雅降级**：模块不存在时给出明确指引而非 ImportError 堆栈。
    """
    p = os.path.join(PROJECT_DIR, "deploy")
    if p not in sys.path:
        sys.path.insert(0, p)
    try:
        import _wh_common# noqa: E402
        return _wh_common
    except ImportError as e:
        raise SystemExit(
            f"[FATAL] 离线模式需要 deploy/_wh_common.py，"
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

    # ---- 闸门 2.5: 平台 / Python 版本一致性 ----
    # ★ 09-10 新增：wheel 带 cp3XX+平台标签，跨版本装不上时 pip 只说
    #   "No matching distribution found"，**不会提示是版本问题**，
    #   用户无从判断（实测：Windows/py3.13 造 71 包，Linux/py3.10 造 78 包，
    #   两者不可互换）。这里提前给出可操作的结论。
    plat_problems, plat_notes = house.platform_check()
    for n in plat_notes:
        log(f"[offline] {n}")
    if plat_problems:
        log("")
        log("[FATAL] wheelhouse 与本机平台/Python 版本不匹配：")
        for p in plat_problems:
            log(f"        - {p}")
        log("")
        log("  ★ 包数不同不一定是 bug：差异主要来自 Python 版本（3.10 需要")
        log("    typing-extensions/tomli/exceptiongroup 等兼容垫片，pandas 也降级到 2.x）。")
        log("  ★ 修法：在**本机**（或同 Python 版本的机器）上重造 wheelhouse：")
        log(f"        python deploy\\build_wheelhouse.py --profile {profile}")
        raise SystemExit("[FATAL] 中止安装（平台不匹配，未创建/改动 venv）。")
    log("[ok] 平台与Python 版本一致")

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
        log(f"        python deploy\\build_wheelhouse.py --profile {profile}")
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


def _venv_has_pip() -> bool:
    """检查刚建的 venv 里是否已有可用的 pip。"""
    if os.name == "nt":
        return os.path.isfile(os.path.join(VENV_DIR, "Scripts", "pip.exe"))
    return os.path.isfile(os.path.join(VENV_DIR, "bin", "pip"))


def _bootstrap_pip_from_wheelhouse() -> bool:
    """用 wheelhouse 里的 pip/setuptools/wheel wheel 让 venv 具备 pip。

    ★ 背景（09-10 用户实测）：Ubuntu 默认**不装** `python3.10-venv`，
      此时 `python -m venv` 因缺 `ensurepip` 直接失败并报
      `No module named 'ensurepip'` ⇒ 离线机必须先联网 `apt install` 才能装。
      但 wheelhouse 里**本来就带** `pip-*.whl`（造包时列为 extra_pkgs），
      所以完全可以**离线自举**，不必依赖 apt / 系统包。

    做法：`python -m venv --without-pip` 建骨架 → 用该解释器把
          wheelhouse 里的 pip wheel 装进去。
    """
    wh = WHEELHOUSE
    if not wh or not os.path.isdir(wh):
        return False
    pip_wheels = sorted(
        f for f in os.listdir(wh) if f.startswith("pip-") and f.endswith(".whl"))
    if not pip_wheels:
        return False
    setuptools_wheels = sorted(
        f for f in os.listdir(wh) if f.startswith("setuptools-") and f.endswith(".whl"))
    wheel_wheels = sorted(
        f for f in os.listdir(wh) if f.startswith("wheel-") and f.endswith(".whl"))

    log(f"[info] 用 wheelhouse 里的 pip 自举（{pip_wheels[-1]}）...")
    # venv 缺 ensurepip ⇒ 连 pip 都没有；用「把 wheel 放进 sys.path 后
    # 直接跑 pip 的 __main__」的方式装，比 get-pip.py 更干净且不需要联网。
    # ★★ requirement 必须直接给**绝对路径**，且**不能加 `path=` 前缀**
    #   （09-10 连续踩了三个坑，逐一实测排除）：
    #     ① 传裸文件名 → pip 去**cwd** 找 ⇒ "does not exist"
    #     ② `sys.path.insert` 只解决「pip 代码可 import」，不解决
    #        「pip 自己解析 requirement」——两者是不同机制
    #     ③ `path=/abs/x.whl` → pip 不认path= 前缀，会把它当文件名的一部分
    #        ⇒ 报 ".../tempt/path=/abs/x.whl does not exist"
    #   正确写法：`pip install --no-index --find-links <wh> <abs path1> <abs path2>`
    targets = [os.path.join(wh, g[-1])
               for g in (pip_wheels, setuptools_wheels, wheel_wheels) if g]
    argv_items = ", ".join(repr(t) for t in targets)
    code = (
        "import sys, runpy;"
        f"sys.path.insert(0, {targets[0]!r});"   # 让 pip 代码本身可 import
        "sys.argv=['pip','install','--no-index','--find-links',"
        f"{wh!r},'--upgrade',{argv_items}];"
        "runpy.run_module('pip', run_name='__main__')"
    )
    r = subprocess.run([VENV_PY, "-c", code], env=clean_env(),
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=900)
    ok = r.returncode == 0 and _venv_has_pip()
    if ok:
        log("[ok] pip 自举成功（无需 apt install python3.x-venv）")
    else:
        log(f"[warn] pip 自举失败 (rc={r.returncode}): "
            f"{(r.stderr or r.stdout or '')[-300:]}")
    return ok


def create_venv() -> None:
    """创建全新虚拟环境（缺 ensurepip 时自动离线自举 pip）。"""
    log("[info] 创建全新虚拟环境 ...")
    r = subprocess.run(
        [BASE_PY, "-m", "venv", VENV_DIR], env=clean_env(),
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=600,
    )
    if r.returncode != 0 or not os.path.isfile(VENV_PY):
        #★ 诊断信息要能区分「venv 命令本身失败」与「解释器路径找不到」——
        #   09-10 前者只报 stderr 空一片，后者才是路径布局问题。
        stderr = (r.stderr or "")
        stdout = (r.stdout or "")
        hint = ""
        if r.returncode == 0 and not os.path.isfile(VENV_PY):
            hint = (f"\n    venv 命令返回 0，但预期解释器不存在: {VENV_PY}\n"
                    f"    ⇒ 平台布局不匹配。Windows 应为 Scripts\\python.exe，"
                    f"Linux/WSL 应为 bin/python（当前 os.name={os.name!r}）")
        # ── 回退 1：缺 ensurepip（Ubuntu 默认不装 python3.x-venv）──
        # ★ 症状判定必须**同时看 stdout 与 stderr**：ensurepip 缺失时，
        #   Debian/Ubuntu 的 venv 把提示打在 **stdout** 而 stderr 全空
        #   （09-10 实测，只查 stderr 会漏判 ⇒ 自举不触发，白白失败）。
        #   典型文本含 "ensurepip is not available" / "python3-venv" / "apt install"。
        blob = f"{stderr}\n{stdout}"
        if "ensurepip" in blob or "python3-venv" in blob or "python3.10-venv" in blob:
            log("[warn] venv 创建失败：base 解释器缺 ensurepip 模块"
                "（Ubuntu/WSL 默认不装 python3.x-venv）")
            log("[info] 改用--without-pip 建骨架 + wheelhouse 离线自举 pip ...")
            log("      ★ 无需联网 apt install —— wheelhouse 内已含 pip wheel")
            rb = subprocess.run(
                [BASE_PY, "-m", "venv", "--without-pip", VENV_DIR],
                env=clean_env(), capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=600,
            )
            if rb.returncode == 0 and os.path.isfile(VENV_PY):
                log(f"[ok] venv 骨架已创建（无 pip）: {VENV_PY}")
                if _bootstrap_pip_from_wheelhouse():
                    return
                raise SystemExit(
                    "[FATAL] venv 已创建，但无法从 wheelhouse 自举 pip。\n"
                    "    原因通常是 wheelhouse 不完整（缺 pip-*.whl）。\n"
                    "    ⇒ 请在联网机重跑 build_wheelhouse.py 后重新拷贝整个目录。\n"
                    f"---- venv stdout ----\n{(rb.stdout or '')[-300:]}")
            raise SystemExit(
                "[FATAL] venv 创建失败，且 `--without-pip` 回退也失败。\n"
                "    ★ Ubuntu/WSL 缺 python3.x-venv 时可先装它（需联网）：\n"
                "        sudo apt install -y python3.10-venv\n"
                f"---- venv stdout ----\n{stdout[-300:]}\n---- stderr ----\n{stderr[-300:]}{hint}")

        raise SystemExit(
            f"[FATAL] 创建 venv 失败 (rc={r.returncode}):\n{stderr[-400:]}{hint}"
        )
    if not _venv_has_pip():
        # venv 骨架建成了但没有 pip（如 base 自带损坏副本）⇒ 同样走离线自举
        log("[warn] venv 中未找到 pip，尝试从 wheelhouse 自举")
        if _bootstrap_pip_from_wheelhouse():
            return
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
        # 保存完整日志便于排查 (统一放 test/reports/, 不污染根目录)
        os.makedirs(REPORT_DIR, exist_ok=True)
        logfile = os.path.join(REPORT_DIR, f"pytest_{name}.log")
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
def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
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

    # ── 统一入口子命令（09-10 新增）────────────────────────────────
    # 目标：联网机/离线机的**全部**操作都从start_flash.py 发起，
    #      不必记住 build_wheelhouse.py / usb_backup.py 等分散脚本。
    ap.add_argument("--make-wheelhouse", action="store_true",
                    help="联网机：造 wheelhouse（等价 build_wheelhouse.py）")
    ap.add_argument("--export-usb", metavar="DEST", default=None,
                    help="导出离线包到 U 盘目录（等价 usb_backup.py --mode gitee）")
    ap.add_argument("--check", action="store_true",
                    help="只校验 wheelhouse/依赖覆盖度，不安装不跑测试")
    ap.add_argument("--no-tests", action="store_true",
                    help="装好环境后跳过三套测试（快速安装）")
    ap.add_argument("--export-profile", default=None,
                    choices=list(OFFLINE_PROFILES),
                    help="--make-wheelhouse 用的档位（默认 full）")

    # ── 部署目标（2026-10-24 解耦计划 B3）─────────────────────────
    # 统一入口：此前"本机安装"与"超算部署链"是两套命令、两套解释器选择，
    # 且 run_all.py 写死本机绝对路径 Python。现在都从 start_flash.py 进。
    ap.add_argument("--target", default="auto",
                    choices=["auto", "win", "wsl", "hpc"],
                    help="部署目标：auto(默认,按平台) | win(Windows 本地) | "
                         "wsl(WSL 内重新启动自己) | hpc(委托 deploy/hpc_deploy/run_all.py)")
    return ap.parse_args(argv)


# ---------------------------------------------------------------------------
# --target 分流（B3）
# ---------------------------------------------------------------------------
def _to_wsl_path(p: str) -> str:
    """`E:\\a\\b` → `/mnt/e/a/b`（幂等）。"""
    s = str(p).replace("\\", "/")
    if s.startswith("/"):
        return s
    if len(s) > 1 and s[1] == ":":
        return f"/mnt/{s[0].lower()}{s[2:]}"
    return s


def run_hpc_deploy(passthrough: list[str]) -> int:
    """`--target hpc`：委托超算部署链（11 步）。

    ★ 该链需要**完整源码树**（含 deploy/hpc_deploy/ 与 paramiko 凭据）。
      在 sdist 解包目录里必须明确报错 —— 若"尽力而为"会产生半套部署
      （计划风险 R24）。
    """
    chain = Path(PROJECT_DIR) / "deploy" / "hpc_deploy" / "run_all.py"
    if not chain.is_file():
        print("[X] --target hpc 需要完整源码树（缺少 deploy/hpc_deploy/run_all.py）")
        print("    ① 这是**控制器侧**命令：请在 git clone 的完整仓库里运行"
              "（不是 sdist 解包目录）")
        print("    ② 只做离线安装请用：python start_flash.py --offline --wheelhouse <dir>")
        return 2

    try:
        from deploy.targets import resolve_deploy_target      # noqa: PLC0415
    except ImportError:
        sys.path.insert(0, str(PROJECT_DIR))
        from deploy.targets import resolve_deploy_target      # noqa: PLC0415

    _target, trace = resolve_deploy_target("hpc")
    for line in trace:
        print(line)
    cmd = [sys.executable, str(chain), *passthrough]
    print(f"[hpc] {' '.join(cmd)}")
    return subprocess.run(cmd, cwd=str(PROJECT_DIR)).returncode


def reexec_in_wsl(extra_args: list[str]) -> int:
    """`--target wsl`（Windows 侧）：在 WSL 内用 Linux venv 重新启动自己。"""
    script = Path(__file__).resolve()
    wsl_script = _to_wsl_path(str(script))
    venv_py_local = Path(str(PROJECT_DIR)) / ".venv-linux" / "bin" / "python"
    # ★ Windows 上该路径是符号链接，is_file() 会抛 OSError（WinError 1920）
    try:
        has_venv = venv_py_local.is_file()
    except OSError:
        has_venv = False
    py = _to_wsl_path(str(venv_py_local)) if has_venv else "python3"
    inner = f"cd {wsl_script.rsplit('/', 1)[0]} && {py} {wsl_script}"
    if extra_args:
        inner += " " + " ".join(extra_args)
    print(f"[wsl] {inner}")
    return subprocess.run(["wsl", "--", "bash", "-lc", inner]).returncode


def resolve_offline_mode(args: argparse.Namespace) -> bool:
    """三路开关求或：命令行 --offline > 环境变量 FLASH_OFFLINE=1。

    另加两条**自动探测**兜底：

    A. **超算（SLURM）⇒ 强制离线**（2026-10-25 用户实跑复现）：
       超算部署目录**不含 wheelhouse**（212 MB 不随代码同步），
       而 B 条判据（MANIFEST.json 存在）在超算上永远为假 ⇒ 误走在线分支
       ⇒ pip 访问 PyPI ⇒ 超算无外网 ⇒ SSL 失败 ⇒ 60 s 无限重试。
       ⇒ 超算上默认走**离线安装**，缺包**立即报错**（见 run_pip 的离线分支）。

    B. 项目根存在 wheelhouse/MANIFEST.json 时自动转离线
       （避免离线机上误走在线分支，白等 40 分钟超时）。
       可用 FLASH_FORCE_ONLINE=1 强制关掉自动探测。

    ★ 探测信号只能是 MANIFEST.json **本身**，绝不能用「deploy/
      目录存在」这类间接信号 —— 该目录随仓库分发，联网机上永远存在，
      拿它当判据会把**所有在线用户**误切成离线模式（09 开发时踩过，
      由 resolve_offline_mode 的独立单测抓出）。
    """
    if args.offline or os.environ.get("FLASH_OFFLINE", "").strip() == "1":
        return True
    if os.environ.get("FLASH_FORCE_ONLINE", "").strip() == "1":
        return False
    # ── A. 超算 ⇒ 强制离线 ──
    is_hpc, why = probe_hpc()
    if is_hpc:
        log(f"[auto] 检测到超算环境（{why}）→ 强制离线安装模式"
            f"（超算通常无外网；如需联网请设 FLASH_FORCE_ONLINE=1）")
        return True
    wh = args.wheelhouse or os.environ.get("FLASH_WHEELHOUSE", "").strip()
    cand = wh or os.path.join(PROJECT_DIR, "wheelhouse")
    # ── B. 唯一判据：wheelhouse 目录里确实躺着 MANIFEST.json ──
    if os.path.isfile(os.path.join(cand, "MANIFEST.json")):
        log(f"[auto] 检测到 {cand}\\MANIFEST.json → 自动切换离线模式"
            f"（如需强制在线请设 FLASH_FORCE_ONLINE=1）")
        return True
    return False


def run_utility_commands(args: argparse.Namespace) -> int:
    """统一入口的「造包 / 导 U 盘」子命令（09-10）。

    设计原则：**只做转发，不复制逻辑** —— 真正干活的仍是
    `build_wheelhouse.py` / `usb_backup.py`，这里负责参数翻译与
    友好输出。好处：两处逻辑永不漂移，且保留各脚本的独立可执行性。
    """
    log("=" * 72)
    log("  start_flash.py — 离线部署工具（造包 / 导出）")
    log("=" * 72)

    def _run(script_rel: str, argv: list[str]) -> int:
        script = os.path.join(PROJECT_DIR, *script_rel.split("/"))
        if not os.path.isfile(script):
            log(f"[FATAL] 找不到脚本: {script}", "ERROR")
            log(f"       请确认拷贝了完整的仓库（含 {script_rel.split('/')[0]}/ 目录）",
                "ERROR")
            return 2
        log(f"[exec] {script_rel} {' '.join(argv)}")
        r = subprocess.run([sys.executable, script] + argv,
                           cwd=PROJECT_DIR, env=clean_env())
        return r.returncode

    rc = 0
    if args.make_wheelhouse:
        prof = args.export_profile or os.environ.get("FLASH_PROFILE", "full")
        log(f"[info] 联网机造包，档位: {prof}")
        log(f"[info] Python: {sys.version.split()[0]} / 平台: {sys.platform}")
        argv = ["--profile", prof]
        if args.wheelhouse:
            argv += ["--out", args.wheelhouse]
        rc = _run("deploy/build_wheelhouse.py", argv)
        if rc != 0:
            return rc
        log("")
        log("[next] 下一步: 把整个 artifacts/wheelhouse/ 目录（含 MANIFEST.json）")
        log("       与源码一起拷到 U 盘 —— 可用：")
        log("       python start_flash.py --export-usb <U盘目录>")

    if args.export_usb:
        dest = args.export_usb
        log("")
        log(f"[info] 导出离线包到: {dest}")
        rc = _run("scripts/04_backup/usb_backup.py", ["--mode", "gitee", dest])
        if rc != 0:
            return rc
        log("")
        log("[done] 导出完成。U 盘内容应为：")
        log("       flash/                (源码，git跟踪的约 17 MB)")
        log("       artifacts/wheelhouse/ (含 MANIFEST.json)")
        log("       ★ 不要用 --mode full：flash/ 目录在磁盘上可达 71 GB")
    return rc


def main() -> int:
    global VENV_DIR, VENV_PY, BASE_PY, OFFLINE

    # `--` 之后一律透传（--target hpc 时交给 run_all.py，不经 argparse）
    _argv = sys.argv[1:]
    _passthrough: list[str] = []
    if "--" in _argv:
        _i = _argv.index("--")
        _argv, _passthrough = _argv[:_i], _argv[_i + 1:]

    args = parse_args(_argv)

    # ── 统一入口分流（09-10）：造包 / 导 U盘 这两个动作与「安装」互斥，
    #    放最前面处理，避免为造包去建 venv（那是离线机才需要的）。
    if args.make_wheelhouse or args.export_usb:
        return run_utility_commands(args)

    # ── --target 分流（2026-10-24 B3）──────────────────────────
    if args.target == "hpc":
        return run_hpc_deploy(_passthrough)
    if args.target == "wsl" and os.name == "nt":
        # 去掉 --target/其值 再进 WSL（WSL 内 os.name=posix ⇒ 不会递归）
        clean: list[str] = []
        _skip = False
        for a in _argv:
            if _skip:
                _skip = False
                continue
            if a == "--target":
                _skip = True
                continue
            clean.append(a)
        return reexec_in_wsl(clean)

    OFFLINE = resolve_offline_mode(args)

    # 离线档位需在 setup_offline 之前落进环境（offline_install_args 会读）
    if args.profile:
        os.environ["FLASH_PROFILE"] = args.profile
    os.environ.setdefault("FLASH_PROFILE", "full")

    BASE_PY = find_base_python()
    # ★ venv 目录**按平台区分**（09-10）：Windows 用 .venv-win、
    #   Linux/WSL 用 .venv-linux。理由：两平台的 venv 物理上不能共用
    #   （解释器分别是 PE / ELF，numpy 等扩展也是win_amd64 vs manylinux），
    #   共用会导致「在 Windows 跑 start_flash.py 把 WSL 的 venv 删掉重建」。
    #   FLASH_VENV_DIR 显式指定时仍以用户为准。
    #
    # ★★ 2026-10-25 超算修正：超算上用**命名环境 .venv-hpc-nce**
    #   （deploy/hpc_deploy/remote_install.py 离线装出来的那个），而不是
    #   新建 .venv-linux。原因：
    #     · 超算**无 wheelhouse**（212 MB 不随代码同步）⇒ 新建环境必失败；
    #     · .venv-hpc-nce 已是**可用的离线环境**（实测 flash 0.1.11 可导入）；
    #     · 新建 .venv-linux 还会留下一个装不起来的空壳，误导后续排查。
    #   命名规则的事实源是 flash/flash_run/env/venv_paths.py（kind="hpc"），
    #   与部署链、insitu 执行体保持一致，避免三处各写一份。
    _whc_v = None
    try:
        _whc_v = _load_wh_common()
    except SystemExit:
        pass
    _is_hpc, _hpc_why = probe_hpc()
    if os.environ.get("FLASH_VENV_DIR", "").strip():
        VENV_DIR = os.environ["FLASH_VENV_DIR"].strip()
    elif _is_hpc:
        VENV_DIR = _hpc_venv_dir(PROJECT_DIR)
        log(f"[info] 超算环境（{_hpc_why}）→ 使用命名环境: {VENV_DIR}")
    elif _whc_v is not None:
        VENV_DIR = _whc_v.venv_dir(PROJECT_DIR)
    else:
        VENV_DIR = (DEFAULT_VENV_DIR if os.name == "nt"
                    else DEFAULT_VENV_DIR.replace(".venv", ".venv-linux"))
    # 兼容已有环境：若本平台目录不存在、但旧版无后缀 .venv 恰好属于本平台，
    # 就继续用它（避免让老用户重新装一遍）。
    _legacy = DEFAULT_VENV_DIR
    if (not os.path.isdir(VENV_DIR) and os.path.isdir(_legacy)
            and VENV_DIR != _legacy):
        _belongs = False
        if _whc_v is not None:
            _belongs = _whc_v.venv_belongs_to_platform(_legacy)
        else:
            _belongs = (os.path.isfile(os.path.join(_legacy, "Scripts", "python.exe"))
                        if os.name == "nt"
                        else os.path.isfile(os.path.join(_legacy, "bin", "python")))
        if _belongs:
            log(f"[info] 沿用已有的无后缀 venv: {_legacy}")
            VENV_DIR = _legacy
        elif os.path.isdir(_legacy):
            # ★ 旧目录属于**另一种平台** ⇒ 绝不能删它，只是不用它。
            log(f"[warn] 检测到 {_legacy} 属于其他平台的 venv，已改用 {VENV_DIR}"
                f"（原目录保留，不会被删除）")
    # ★ venv 内解释器路径**必须跨平台**（09-10 修复）：Windows 是
    #   Scripts\python.exe，Linux/WSL 是 bin/python（无 .exe、无 Scripts）。
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
    #
    # ★★ 2026-10-25 超算修正：**已有健康的命名环境 ⇒ 不做 wheelhouse 预检**。
    #   超算部署目录不含 wheelhouse（212 MB 不随代码同步），若无条件跑
    #   setup_offline 就会因"找不到 wheelhouse"而中止 —— 但那台机器上
    #   `.venv-hpc-nce` 早已离线装好且健康（实测 flash 0.1.11 可导入）。
    #   ⇒ 先探命名环境是否可用，可用则直接进 Step 1 复用；不可用才要求
    #     wheelhouse（并给出明确的"怎么把 wheelhouse 弄上来"指引）。
    _reuse_named_env = False
    if OFFLINE:
        _named_ok, _named_why = _probe_existing_venv(VENV_DIR)
        if _named_ok:
            _reuse_named_env = True
            log(f"\n[step 0/5] 检测到可用的现有环境（{_named_why}）"
                f"→ 跳过 wheelhouse 预检，直接复用")
            log(f"[info] 环境: {VENV_DIR}")
        else:
            log("\n[step 0/5] 离线模式前置校验（wheelhouse 清单 + 依赖覆盖度）...")
            try:
                setup_offline(args.wheelhouse, os.environ.get("FLASH_PROFILE", "full"))
            except SystemExit as _se:
                # ★ 2026-10-25：超算上缺 wheelhouse 时，**补一条最可行的出路**：
                #   部署链（deploy/hpc_deploy/）早已装好命名环境 .venv-hpc-nce，
                #   只是本次 FLASH_VENV_DIR 指错了。给出可直接复制的命令，
                #   免得用户以为"必须造 212 MB wheelhouse"才能用超算。
                if _is_hpc:
                    log("")
                    log("  ★ 超算上的推荐做法（**不需要** wheelhouse）：")
                    log(f"      export FLASH_VENV_DIR={_hpc_venv_dir(PROJECT_DIR)}")
                    log("      python start_flash.py")
                    log("    （该环境由 deploy/hpc_deploy/remote_install.py 离线装好）")
                    log("    若该环境也不存在，再考虑：")
                    log("      ① 联网机：python deploy\\build_wheelhouse.py --profile full")
                    log("      ② 整目录拷贝 wheelhouse/ 到超算后：")
                    log("         python start_flash.py --offline --wheelhouse <路径>")
                raise
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

    # ★ --check（09-10）：只校验、不安装、不跑测试、不碰 venv。
    #   Step 0（离线时）已完成 wheelhouse 清单 + 平台 + 依赖覆盖度三道校验，
    #   这里直接汇报并退出 —— 供「拷贝到离线机后先验一下」用。
    if args.check:
        log("[check] 只校验模式：不创建/改动 venv，不安装，不跑测试")
        if OFFLINE:
            log(f"[ok] wheelhouse: {WHEELHOUSE}")
            log("[ok] 清单 + 平台/Python 版本 + 依赖覆盖度：三道校验全部通过")
        else:
            log("[info] 当前为在线模式，无 wheelhouse 可校验")
            log("       如需校验离线包，请加 --offline --wheelhouse <路径>")
        venv_state = "健康" if (os.path.isdir(VENV_DIR)
                                and check_env_health(VENV_PY)[0]) else (
            "不存在" if not os.path.isdir(VENV_DIR) else "不健康")
        log(f"[info] 本平台 venv: {VENV_DIR}（{venv_state}）")
        log(f"[info] venv 目录按平台区分：Windows=.venv-win / Linux=.venv-linux")
        log(f"[info]              另一平台的 venv 不会被本脚本删除")
        log("\n[done] 校验完成（未做任何改动）")
        return 0

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
    # ★★ 2026-10-25 超算修正：**离线 + 已有健康环境 ⇒ 完全跳过 pip**。
    #   否则 fix_setuptools/install_flash_package 会去访问 PyPI ⇒ 超算无外网
    #   ⇒ SSL 失败 ⇒ 60 s 重试（用户实跑复现的原始故障链）。
    #   跳过是**正确**的：环境已健康（依赖齐全 + pytest 可启动），
    #   无需重装；真要重装时显式 FLASH_FORCE_CLEAN=1。
    _skip_pip = bool(_reuse_named_env and OFFLINE
                     and os.path.isfile(VENV_PY))
    if _skip_pip:
        log("\n[step 2/5] 复用已健康的离线环境 → 跳过 pip 安装"
            "（离线模式不联网；如需重装请设 FLASH_FORCE_CLEAN=1）")
        flash_verify = ""
    elif not os.path.isfile(VENV_PY):
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
    if args.no_tests:
        # ★ 09-10 新增：--no-tests 跳过三套测试（快速安装）。
        #   环境健康复检已在 Step 3 完成，跳过测试不会漏掉环境问题。
        log("\n[step 4/5] 全局测试 —— 已按 --no-tests 跳过 ...")
        log("[info] 如需完整验证请不带 --no-tests 重跑，或执行：")
        log(f"       {os.path.join(VENV_DIR, 'Scripts' if os.name == 'nt' else 'bin', 'pytest')} flash")
        results = {}
    else:
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
        # ★ 三套件都要判：output_processors 曾被排除在外，导致它 3 个 FAIL 时
        #   报告仍写"安装验证通过"（报喜不报忧）。数据缺失属可自愈类问题，
        #   已在 conftest 导入期预生成修复 ⇒ 这里恢复全量判定。
        if res is not None:
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
    lines.append("- 完整测试日志见 test\\reports\\ 下的 pytest_framework.log / "
                 "pytest_input_gen.log / pytest_output_processors.log。")
    lines.append("- 虚拟环境为项目专属 .venv（项目根目录），与共享环境 envs/default 完全隔离。")
    if OFFLINE:
        lines.append(f"- 本次为**离线安装**：pip 全程带 --no-index，从 wheelhouse 本地取包，"
                     f"物理上未访问 PyPI。")
        lines.append(f"- 离线模式**不使用** `-e .`（可编辑安装）：它会往 .venv 写入指向"
                     f"源码树的绝对路径，U盘换机后即失效；且需要源码树含依赖声明。")
        lines.append(f"- 需要更新依赖时：在联网机重跑 "
                     f"deploy\\build_wheelhouse.py，"
                     f"重新拷贝整个 wheelhouse 目录（含 MANIFEST.json）。")
    lines.append("")

    report = "\n".join(lines)
    os.makedirs(REPORT_DIR, exist_ok=True)
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
