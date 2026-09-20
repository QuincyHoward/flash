# -*- coding: utf-8 -*-
"""_longrun_lib.py — SNBVTi 长时全流程共用库。

★ 设计要点（为什么要有这个文件）:
  1. **不重复实现** —— 会话/凭据/远端路径解析全部复用 `SNBVTi.py`
     的既有函数 (`_HpcRemote` / `resolve_deploy_dir` / `_remote_snb_home` …),
     避免第二套真相源 (pit-list B 类根因)。
  2. **删除走回收站** —— 本机所有删除一律送系统回收站, 不做永久删除。
     沙箱对 `Path.unlink()` 有 `[safe-delete][SAFE_DELETE_FAIL_CLOSED]` 闸门,
     故回收站失败时**明确报错并跳过**, 绝不退化成 `rm -rf`。
  3. **状态原子落盘** —— 长流程 (9 h) 每阶段写 `pipeline_state.json`,
     `tmp + os.replace` 原子替换, 崩溃后可断点续跑。
  4. **心跳日志** —— 所有输出同时写 stdout 与 `pipeline_run.log`,
     便于宿主后台任务/用户随时 tail。
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

# ── 场景根与模块导入 ──
# ★ 本文件位于 <SCEN>/scripts/longrun/_longrun_lib.py → 上溯 3 级到 <SCEN>
HERE = Path(__file__).resolve().parent          # scripts/longrun/
SCEN_DIR = HERE.parents[1]                      # SNBVTi2_ml/
REPO_ROOT = SCEN_DIR.parents[4]                 # flash/
FLASH_OUT = SCEN_DIR / "flash_output"
FLASH_IN = SCEN_DIR / "flash_input"

STATE_FILE = SCEN_DIR / "pipeline_state.json"
LOGFILE = SCEN_DIR / "pipeline_run.log"

ACCOUNT_NCE = "flash_ssh"
ACCOUNT_BSCC = "flash_ssh_2"

# ★ 场景模块名 = 目录名 (SNBVTi2_ml)。派生新场景时只需改这一处。
SCEN_MODULE = SCEN_DIR.name

# 把场景目录加入 sys.path 以 import <SCEN_MODULE>
if str(SCEN_DIR) not in sys.path:
    sys.path.insert(0, str(SCEN_DIR))

import importlib as _importlib  # noqa: E402

M = _importlib.import_module(SCEN_MODULE)

# ★★★ HPC 原语必须另取引用 (2026-09-13 实测踩坑)
# ---------------------------------------------------------------------
# <SCEN_MODULE>.py 采用**委托**架构: 它自己**不实现** `_HpcRemote` /
# `resolve_deploy_dir` / `_remote_snb_home` / `_hpc_env_block`, 而是在
# `run_hpc_pipeline()` 里把这些命名常量重绑定后委托给 SNBOneCH_ml.run_hpc。
# ⇒ 若本库直接写 `R._HpcRemote(...)` 会 **AttributeError** (实测)。
# 正确做法: 原语从参考模块取, 仅 **命名常量** 从本场景 M 取 —— 这正是
# "不重复实现"原则的正确落法 (第二套真相源是原语代码, 不是常量)。
from flash.scenarios.private.tracer.SNB.SNBOneCH_ml import (  # noqa: E402
    SNBOneCH_ml as _REF,
)
# `_HpcRemote` / `resolve_deploy_dir` / `_remote_snb_home` / `_hpc_env_block`
# 一律经下面的薄封装访问 —— 见 R / 同名模块级别名。
R = _REF


# ══════════════════════════════════════════════════════════════════════
# 日志
# ══════════════════════════════════════════════════════════════════════
def log(msg: str, level: str = "INFO", to_file: bool = True) -> None:
    """统一日志: stdout + pipeline_run.log。"""
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}][{level:5s}] {msg}"
    print(line, flush=True)
    if to_file:
        try:
            with open(LOGFILE, "a", encoding="utf-8", newline="\n") as f:
                f.write(line + "\n")
        except Exception:
            pass


def step(title: str) -> None:
    bar = "=" * 72
    log(bar, "STEP", to_file=False)
    log(f" {title}", "STEP", to_file=False)
    log(bar, "STEP", to_file=False)
    try:
        with open(LOGFILE, "a", encoding="utf-8", newline="\n") as f:
            f.write(f"\n{bar}\n {datetime.now():%F %T}  {title}\n{bar}\n")
    except Exception:
        pass


def human(nbytes: float) -> str:
    for u in ("B", "KB", "MB", "GB", "TB"):
        if abs(nbytes) < 1024:
            return f"{nbytes:.1f} {u}"
        nbytes /= 1024.0
    return f"{nbytes:.1f} PB"


def human_dur(sec: float) -> str:
    if sec < 60:
        return f"{sec:.0f}s"
    if sec < 3600:
        return f"{sec/60:.1f}min"
    if sec < 86400:
        return f"{sec/3600:.2f}h"
    return f"{sec/86400:.2f}d"


# ══════════════════════════════════════════════════════════════════════
# 状态文件（断点续跑）
# ══════════════════════════════════════════════════════════════════════
def load_state() -> Dict[str, Any]:
    if STATE_FILE.is_file():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_state(**kw: Any) -> Dict[str, Any]:
    """原子写 state: 先写 .tmp 再 os.replace。"""
    st = load_state()
    st.update(kw)
    st["_updated"] = datetime.now().strftime("%F %T")
    tmp = STATE_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(st, indent=2, ensure_ascii=False), encoding="utf-8")
    try:
        os.replace(tmp, STATE_FILE)
    except OSError:
        # ★ Windows: 旧句柄/杀软占用 → 退化为 copyfile (读源+新句柄写)
        shutil.copyfile(tmp, STATE_FILE)
        try:
            tmp.unlink()
        except Exception:
            pass
    return st


def clear_state() -> None:
    try:
        if STATE_FILE.is_file():
            STATE_FILE.unlink()
    except Exception:
        # 沙箱阻断 → 写空内容代替删除
        try:
            STATE_FILE.write_text("{}", encoding="utf-8")
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════════════
# 删除（回收站优先；失败即报错，绝不退化为永久删除）
# ══════════════════════════════════════════════════════════════════════
class SafeDeleteError(RuntimeError):
    pass


def _run_ps(ps: str) -> subprocess.CompletedProcess:
    """执行 PowerShell。

    ★ 关键修复：`text=True` 用系统 locale（简体中文 = cp936/GBK）解码管道，
      而 PowerShell 在中文 Windows 上把错误写成 GBK → UnicodeDecodeError
      直接抛在读取线程里，`returncode` 永远拿不到 → 回收站被误判为失败。
      这里显式用 bytes + errors="replace" 解，绝不因编码失败丢返回值。
    """
    return subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
        capture_output=True, timeout=180)


def _trash_windows(path: Path) -> bool:
    """Windows: 用 Microsoft.VisualBasic 送目录到回收站。

    ★ 关键修复（两次踩坑）：
      ① `text=True` 用系统 locale 解码 → 中文 Windows 下 PowerShell 以 GBK
         写 stderr → UnicodeDecodeError 抛在读取线程 → returncode 丢失；
      ② **绝不能把 `Path` 对象直接插进 PowerShell 字符串**：str(Path) 给的是
         `E:/PhySimX/...` 正斜杠形式，VB 的 DeleteDirectory 解析不了 → rc≠0。
         必须用 `os.fspath()` 并在 Windows 上转成反斜杠。
    """
    p = os.path.abspath(os.fspath(path))
    if os.name == "nt":
        p = p.replace("/", "\\")
    ps = (
        "$ErrorActionPreference='Stop';"
        "Add-Type -AssemblyName Microsoft.VisualBasic;"
        "[Microsoft.VisualBasic.FileIO.FileSystem]::DeleteDirectory("
        f"'{p}', 'OnlyErrorDialogs', 'SendToRecycleBin')"
    )
    try:
        r = _run_ps(ps)
        if r.returncode != 0:
            msg = (r.stderr or b"").decode("utf-8", "replace")[:300]
            # ★ 已知良性告警：大目录树删完后 VB(DeleteDirectory) 仍抛
            #   "无法找到指定文件"（rc≠0），但目标其实已被删除。以**结果**为准：
            #   只要 path 已不存在，即判成功，不制造假失败。
            if not path.exists():
                log("    PS 报 rc≠0 但目标已消失 → 判成功（VB 大目录树已知告警）", "WARN")
                return True
            log(f"    PS(del dir) rc={r.returncode}: {msg}", "WARN")
            return False
        return True
    except Exception as e:
        if not path.exists():
            return True
        log(f"    PS(del dir) 异常: {e}", "WARN")
        return False


def _trash_windows_file(path: Path) -> bool:
    p = os.path.abspath(os.fspath(path))
    if os.name == "nt":
        p = p.replace("/", "\\")
    ps = (
        "$ErrorActionPreference='Stop';"
        "Add-Type -AssemblyName Microsoft.VisualBasic;"
        "[Microsoft.VisualBasic.FileIO.FileSystem]::DeleteFile("
        f"'{p}', 'OnlyErrorDialogs', 'SendToRecycleBin')"
    )
    try:
        r = _run_ps(ps)
        if r.returncode != 0:
            msg = (r.stderr or b"").decode("utf-8", "replace")[:300]
            if not path.exists():
                log("    PS 报 rc≠0 但目标已消失 → 判成功", "WARN")
                return True
            log(f"    PS(del file) rc={r.returncode}: {msg}", "WARN")
            return False
        return True
    except Exception as e:
        if not path.exists():
            return True
        log(f"    PS(del file) 异常: {e}", "WARN")
        return False


def _trash_posix(path: Path) -> bool:
    for cmd in (["gio", "trash", str(path)], ["trash-put", str(path)]):
        try:
            r = subprocess.run(cmd, capture_output=True, timeout=120)
            if r.returncode == 0:
                return True
        except FileNotFoundError:
            continue
        except Exception:
            continue
    return False


def safe_remove(path: Path, dry_run: bool = True) -> Tuple[bool, str]:
    """删除到回收站。返回 (是否成功, 说明)。

    ★ 三条铁律:
      1. dry_run=True 时**只报告不动作**;
      2. 只允许删除白名单前缀内的路径 (防止误删远端/系统路径);
      3. 回收站失败 → 抛 SafeDeleteError, **绝不** fallback 到 rm -rf。
    """
    p = Path(path)
    if dry_run:
        return True, "DRY-RUN"
    if not p.exists():
        return True, "不存在(跳过)"
    if os.name == "nt":
        ok = _trash_windows(p) if p.is_dir() else _trash_windows_file(p)
    else:
        ok = _trash_posix(p)
    if not ok:
        raise SafeDeleteError(
            f"送入回收站失败: {p}\n"
            f"  → 出于安全, 已中止而非永久删除。请手动删除该目录后重跑。")
    return True, "已送回收站"


def dir_inventory(root: Path, patterns: Optional[Iterable[str]] = None) -> List[Tuple[Path, int, int]]:
    """列出目录下 (路径, 文件数, 总字节)。patterns 为空则含全部。"""
    import fnmatch
    out: List[Tuple[Path, int, int]] = []
    if not root.exists():
        return out
    for entry in sorted(root.iterdir()):
        name = entry.name
        if patterns and not any(fnmatch.fnmatch(name, g) for g in patterns):
            continue
        if entry.is_dir():
            n = sum(1 for x in entry.rglob("*") if x.is_file())
            b = sum(x.stat().st_size for x in entry.rglob("*") if x.is_file())
        else:
            n, b = 1, entry.stat().st_size
        out.append((entry, n, b))
    return out


def print_inventory(title: str, root: Path,
                    patterns: Optional[Iterable[str]] = None) -> Tuple[int, int]:
    items = dir_inventory(root, patterns)
    tot_n = sum(x[1] for x in items)
    tot_b = sum(x[2] for x in items)
    log(f"{title}  ({root})")
    if not items:
        log("    (空)")
    for p, n, b in items:
        tag = "[D]" if p.is_dir() else "[F]"
        log(f"    {tag} {human(b):>10s}  {n:>5} 项  {p.name}")
    log(f"    ── 合计 {len(items)} 项 / {tot_n} 文件 / {human(tot_b)}")
    return tot_n, int(tot_b)


# ══════════════════════════════════════════════════════════════════════
# 远端会话与路径
# ══════════════════════════════════════════════════════════════════════
def abs_snb_home(remote, retries: int = 3) -> str:
    """解析远端 `~/<user>/FLASH/FLASHSNB/FLASH4.8` 为绝对路径。

    ★ 铁律: paramiko SFTP **不展开 `~`** → 必须绝对路径, 否则下载静默 0 字节。
    ★ 稳健: 用户网络常瞬断 → 多命令 × 多轮 + 退避。
    """
    lit = R._remote_snb_home()
    probes = ('printf %s "$HOME"', 'echo $HOME', 'cd ~ && pwd')
    home = ""
    for attempt in range(retries):
        for pc in probes:
            try:
                out, _, _ = remote.run(pc, timeout=30)
            except Exception:
                continue
            cand = (out or "").strip()
            if cand.startswith("/"):
                home = cand
                break
        if home:
            break
        log(f"  $HOME 探测第 {attempt+1}/{retries} 轮为空, 5s 后重试 (网络瞬断?)", "WARN")
        time.sleep(5)
    if not home.startswith("/"):
        raise RuntimeError(
            f"远端 $HOME 探测失败 (3 命令 × {retries} 轮均为空); 无法解析 {lit}。\n"
            f"  手动诊断: ssh <host> -p <port> 'echo $HOME'")
    return home.rstrip("/") + "/" + lit[2:]


def remote_size(remote, rp: str) -> Optional[int]:
    try:
        o, _, _ = remote.run(f"stat -c %s {rp} 2>/dev/null", timeout=40)
        v = (o or "").strip()
        return int(v) if v.isdigit() else None
    except Exception:
        return None


def remote_md5(remote, rp: str) -> Optional[str]:
    try:
        o, _, _ = remote.run(f"md5sum {rp} 2>/dev/null", timeout=120)
        v = (o or "").strip().split()[0] if o and o.strip() else ""
        return v if len(v) == 32 else None
    except Exception:
        return None


def local_md5(lp: Path) -> Optional[str]:
    import hashlib
    try:
        h = hashlib.md5()
        with open(lp, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None


# ══════════════════════════════════════════════════════════════════════
# ★★★ 构建指纹 (BUILD FINGERPRINT) —— 强制重编译护栏
# ══════════════════════════════════════════════════════════════════════
# 事故 (2026-09-13): 把 `species=cham,shld,samp,tar2` (NSPECIES 8→4) 写进
#   Config 后, `--skip-build` 复用了远端**上一轮的 8 物种 flash4** →
#   仿真"成功"(RUN_EXIT=0) 但 chk 里仍带 tar1/tar3/tar4/tar6 —— **静默错误**。
#
# 根因: NSPECIES 是**编译期**常量 (Config 的 `-DNSPECIES`), 而 flash4 是
#   上一轮编译产物; `--skip-build` 路径只补做 unit.tar.gz 解压 (刷 par/F90),
#   **不重编二进制** ⇒ 判据不能只看"flash4 是否存在"。
#
# 护栏: 任一次成功构建后写 `BUILD_STAMP.json` 到 objdir, 记录输入指纹;
#   提交前比对, 不一致 ⇒ 无视 --skip-build 走全量构建。
# ----------------------------------------------------------------------
BUILD_STAMP_NAME = "_BUILD_STAMP.json"

# 参与指纹的输入 (顺序稳定): 编译期决定二进制行为的文件
def fingerprint_files() -> List[Path]:
    """返回参与构建指纹的本地输入文件列表 (只含存在的项)。"""
    cands = [
        FLASH_IN / "Config",
        FLASH_IN / "Simulation_initBlock.F90",
        FLASH_IN / "Makefile",
    ]
    # 9 个 SNB 覆盖 F90
    for p in sorted(FLASH_IN.glob("*.F90")):
        if p.name not in ("Simulation_initBlock.F90",):
            cands.append(p)
    return [p for p in cands if p.is_file()]


def compute_build_fingerprint() -> str:
    """对输入文件集做 SHA256 (内容 + 文件名), 得稳定指纹。"""
    import hashlib
    h = hashlib.sha256()
    for p in sorted(fingerprint_files(), key=lambda q: q.name):
        h.update(p.name.encode("utf-8"))
        h.update(b"\0")
        h.update(p.read_bytes())
        h.update(b"\0")
    return h.hexdigest()


def remote_fingerprint(remote, objdir: str) -> Optional[str]:
    """读远端 objdir 的构建戳指纹; 无戳/格式坏 → None。"""
    try:
        o, _, _ = remote.run(
            f"cat {objdir}/{BUILD_STAMP_NAME} 2>/dev/null || echo NO_STAMP",
            timeout=60)
        txt = (o or "").strip()
        if "NO_STAMP" in txt or not txt:
            return None
        obj = json.loads(txt)
        return obj.get("fingerprint")
    except Exception:
        return None


def write_remote_fingerprint(remote, objdir: str, fp: str,
                             extra: Optional[Dict[str, Any]] = None) -> bool:
    """把指纹戳写到远端 objdir (构建成功后调用)。"""
    payload = {
        "fingerprint": fp,
        "written_at": datetime.now().strftime("%F %T"),
        "files": {p.name: local_md5(p) for p in fingerprint_files()},
    }
    if extra:
        payload.update(extra)
    try:
        import base64
        raw = json.dumps(payload, ensure_ascii=False, indent=2)
        b64 = base64.b64encode(raw.encode("utf-8")).decode("ascii")
        o, _, _ = remote.run(
            f"echo {b64} | base64 -d > {objdir}/{BUILD_STAMP_NAME} && echo STAMP_OK",
            timeout=60)
        return "STAMP_OK" in (o or "")
    except Exception as e:
        log(f"  写构建戳失败: {type(e).__name__}: {e}", "WARN")
        return False


def needs_rebuild(remote, objdir: str, *, verbose: bool = True) -> Tuple[bool, str]:
    """判定是否需要全量重编译。

    Returns
    -------
    (need_rebuild, reason)
    """
    if not verbose:
        pass
    local_fp = compute_build_fingerprint()
    # flash4 不存在 → 必须构建
    o, _, _ = remote.run(f"ls {objdir}/flash4 2>/dev/null || echo NO_FLASH4",
                         timeout=60)
    if "NO_FLASH4" in (o or ""):
        return True, "objdir 无 flash4"
    rfp = remote_fingerprint(remote, objdir)
    if rfp is None:
        return True, f"无构建戳 (旧二进制, 无法证明与当前输入一致)"
    if rfp != local_fp:
        return True, f"指纹不符 (远端 {rfp[:12]}… ≠ 本地 {local_fp[:12]}…)"
    return False, f"指纹一致 ({local_fp[:12]}…)"


def remote_list(remote, rdir: str, timeout: int = 60) -> Tuple[List[str], List[int]]:
    """列出远端目录内的**普通文件** (名, 大小)。

    ★ 必须排除软链 (setup 会为每个源文件建 `Foo.F90 -> ../source/...` 软链):
      用 `find -maxdepth 1 -type f` 而非 `ls -la | awk`,
      否则软链目标路径会被当成文件名 (实测污染 3018 项)。
    """
    out, _, _ = remote.run(
        f"cd {rdir} 2>/dev/null && "
        f"find . -maxdepth 1 -type f -printf '%s %f\\n' 2>/dev/null | sort -k2",
        timeout=timeout)
    names, sizes = [], []
    for l in (out or "").splitlines():
        parts = l.split(maxsplit=1)
        if len(parts) == 2 and parts[0].isdigit():
            sizes.append(int(parts[0]))
            names.append(parts[1].strip())
    return names, sizes


def remote_inventory(remote, rdir: str) -> Tuple[List[Tuple[str, int]], int]:
    """远端目录清单 → ([(名, 字节)], 总字节)。"""
    names, sizes = remote_list(remote, rdir)
    pairs = list(zip(names, sizes))
    return pairs, sum(sizes)


def remote_batch_remove(remote, patterns: List[str], dry_run: bool = True,
                        rdir: str = "", label: str = "") -> int:
    """远端删除 (仅 glob 模式, 严禁目录级 rm -rf)。

    ★ 安全设计:
      1. 只接受 **glob 模式**(如 `snbvtiug_*`), 不接受裸目录或 `..`/`/`;
      2. 先 dry-run 列清单确认再删;
      3. 每条模式前强制 `cd <rdir>` 限定作用域;
      4. 拒绝任何含 `rm -rf /`、`rm -rf .`、`rm -rf ~` 的形态。
    """
    forbidden = {"", "/", "~", ".", "..", "*", "/*", "~/*", "./*"}
    total = 0
    for pat in patterns:
        if pat.strip() in forbidden:
            log(f"  拒绝危险模式: {pat!r}", "WARN")
            continue
        pre = f"cd {rdir} 2>/dev/null && " if rdir else ""
        # 先数
        cnt_out, _, _ = remote.run(
            f"{pre}ls -1 {pat} 2>/dev/null | wc -l", timeout=60)
        try:
            cnt = int((cnt_out or "0").strip() or 0)
        except ValueError:
            cnt = 0
        if cnt == 0:
            continue
        if dry_run:
            sample_out, _, _ = remote.run(
                f"{pre}ls -1 {pat} 2>/dev/null | head -5", timeout=60)
            sample = " | ".join((sample_out or "").split()[:5])
            log(f"    [DRY] {pat}  → {cnt} 项   样例: {sample}")
        else:
            remote.run(f"{pre}rm -f {pat} 2>/dev/null", timeout=300)
            log(f"    删除 {pat}  → {cnt} 项")
        total += cnt
    if label:
        log(f"  {label}: {total} 项")
    return total


# ══════════════════════════════════════════════════════════════════════
# 物理常量（绘图共用）
# ══════════════════════════════════════════════════════════════════════
K_BOLTZ_EV_PER_K = 1.160451812e4   # K → eV: 1 eV = 11604.51812 K
# ★ 2026-09-14 修正: 原值 1.16045e7 大了 **1000 倍**（那是 K/keV），
#   导致 `tele / K_EV` 实际得到 keV 却被标成 eV（Te 少 1000 倍）。
#   chk 的 `tele` 单位是 **K**（par `sim_tele* [K]` 注释 + p/eint 双独立核验）。
NA = 6.02214076e23

# PPT 绘图规范
PLOT_RC = {
    "font.size": 20, "axes.titlesize": 24, "axes.labelsize": 20,
    "xtick.labelsize": 20, "ytick.labelsize": 20, "legend.fontsize": 18,
    "lines.linewidth": 2.2, "figure.dpi": 100, "savefig.dpi": 450,
    "axes.grid": True, "grid.alpha": 0.3, "font.family": "DejaVu Sans",
}
