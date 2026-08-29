"""
统一场景运行器
═══════════════════════════════════════════════════════════

所有 FLASH 场景共用的运行机制:

  * 用户名统一: ``get_sim_user_dir()`` 从 credentials (get_user_name) 动态获取,
    回落顺序 credentials → 环境变量 FLASH_SIM_USER_DIR → "hello"，禁止硬编码用户名。
  * 运行方式一键切换: 各场景模块级常量 ``RUN_MODE = "wsl" | "hpc"``，
    ``resolve_run_mode()`` 同时支持环境变量 ``FLASH_RUN_MODE`` 覆盖。
  * 维度感知资源默认值: ``default_nprocs()`` / ShellScriptGenerator 依据
    ``flash.flash_run.env.resource_config``（装置×维度）自动计算核数，
    场景可显式覆盖（config_constants["nprocs"] / spec.config["slurm_ntasks"]）。
  * wsl 模式: 本机 WSL 执行 run_flash.sh + 本地绘图分析。
  * hpc 模式: paramiko 分阶段驱动 (upload→sbatch→monitor→远程分析→download)，
    带 flash_output/hpc_task.json 断点续跑。

用法 (各场景单入口):
    RUN_MODE = "wsl"          # ← 一键切换 wsl/hpc

    spec = WslSpec(...) / HpcSpec(...)
    runner.run_scenario(wsl_spec, hpc_spec, cfg, run_mode=None)
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import json
import os
import re
import shutil
import subprocess
import sys
import time

# ── 运行模式 ─────────────────────────────────────────────

RUN_MODES = ("wsl", "hpc")
RUN_MODE_ALIASES = {"local": "wsl", "remote": "hpc", "slurm": "hpc", "supercomputer": "hpc"}
LOG_TAG = {"INFO": "[i]", "OK": "[OK]", "WARN": "[!]", "ERROR": "[X]", "STEP": "[-]"}


def log(msg: str, level: str = "INFO") -> None:
    print(f"  {LOG_TAG.get(level, '[i]')} {msg}")


def normalize_run_mode(mode: str) -> str:
    """标准化运行模式: local→wsl, remote/hpc→hpc。"""
    m = (mode or "").strip().lower()
    if m in RUN_MODE_ALIASES:
        return RUN_MODE_ALIASES[m]
    if m in RUN_MODES:
        return m
    raise ValueError(f"未知运行模式 {mode!r}，可用: {RUN_MODES} (+{list(RUN_MODE_ALIASES)})")


def resolve_run_mode(default: str = "wsl") -> str:
    """解析生效运行模式: 环境变量 FLASH_RUN_MODE 优先，否则默认值。"""
    env_mode = os.environ.get("FLASH_RUN_MODE", "").strip()
    return normalize_run_mode(env_mode or default)


# ── 用户名 (禁止硬编码) ──────────────────────────────────

def get_sim_user_dir() -> str:
    """获取仿真用户目录名（即 FLASH 安装前缀目录）。

    回落顺序: credentials get_user_name() → 环境变量 FLASH_SIM_USER_DIR → "hello"。
    """
    try:
        from flash._core.credentials import get_user_name
        return get_user_name()
    except Exception:  # noqa: BLE001
        pass
    return os.environ.get("FLASH_SIM_USER_DIR", "hello")


def user_flash_home(user: Optional[str] = None, tilde: bool = True) -> str:
    """构造 FLASH 安装路径 ~/<user>/FLASH/FLASH4.8。"""
    user = user or get_sim_user_dir()
    if tilde:
        return f"~/{user}/FLASH/FLASH4.8"
    return f"$HOME/{user}/FLASH/FLASH4.8"


# ── 维度感知资源默认值 ───────────────────────────────────

def default_nprocs(dimension: int, is_hpc: bool = False,
                   override: Optional[int] = None) -> int:
    """计算默认 MPI 进程数（装置×维度感知），场景可显式覆盖。

    Args:
        dimension: 仿真维度 1/2/3
        is_hpc: True 为超算模式（资源按 hpc 装置计算）
        override: 显式指定时直接返回
    """
    if override:
        return int(override)
    try:
        from flash.flash_run.env.resource_config import get_resource_config
        return get_resource_config().get_effective_nproc(
            dimension=dimension, is_hpc=is_hpc,
        )
    except Exception:  # noqa: BLE001
        return 4 if not is_hpc else 16


# ── WSL 本地运行 ─────────────────────────────────────────

@dataclass
class WslSpec:
    """WSL 本地运行规格。"""
    input_dir: Path
    output_dir: Path
    plots_dir: Path
    objdir: str                          # 如 "<user>/LaserSlab_Ti"
    analyze_local: Callable[[Path, Path], int]   # (outdir, save_path) -> 成功帧数
    run_sh_name: str = "run_flash.sh"
    flash_home: str = ""                 # 如 "~/<user>/FLASH/FLASH4.8"，用于清理旧 objdir
    wsl_timeout: int = 7200              # WSL 运行超时 (秒)
    outputfiles_dir: Optional[Path] = None
    # FLASH 输出收集目录 (plt/chk/h5 落盘位置)。
    # None → 旧行为: <input_dir>/outputfiles;
    # 推荐显式指定 <output_dir>/outputfiles, 并在 run_flash.sh 生成时传
    # config["collect_dir"] (WSL 路径) 保持两端一致。


def _to_wsl_path(win_path: Path) -> str:
    s = str(win_path)
    # 幂等: 已是 POSIX 路径 (WSL 下运行, __file__ 为 /mnt/... 形式) 时原样返回
    if s.startswith("/"):
        return s
    drive, rest = s.split(":", 1)
    return "/mnt/" + drive.lower() + rest.replace("\\", "/")


def _tail_lines(path: Path, n: int = 25, max_len: int = 160) -> str:
    """读取文件末尾 n 行（运行中日志），每行截断到 max_len 字符。"""
    try:
        data = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    lines = data.splitlines()
    return "\n".join(l[:max_len] for l in lines[-n:])


def _run_wsl_with_progress(cmd: str, console_log: Path,
                           interval: float = 120.0,
                           timeout: float = 7200.0) -> Tuple[int, str]:
    """在 WSL 中执行命令，运行期间每隔 interval 秒回显一段实际日志。

    Returns:
        (WSL 返回码, 日志文件当前全部内容)。
    """
    start = time.monotonic()
    proc = subprocess.Popen(
        ["wsl", "bash", "-c", cmd],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    last_report = start
    while proc.poll() is None:
        now = time.monotonic()
        if now - last_report >= interval:
            last_report = now
            elapsed = int(now - start)
            tail = _tail_lines(console_log)
            if tail.strip():
                log(f"[{elapsed}s] FLASH 运行中，最近输出:")
                print(tail)
            else:
                log(f"[{elapsed}s] 尚无输出（可能仍在 setup/编译阶段）...")
        if now - start > timeout:
            proc.kill()
            proc.wait()
            raise subprocess.TimeoutExpired(cmd, timeout)
        time.sleep(5)
    rc = proc.wait()
    console_txt = ""
    if console_log.exists():
        console_txt = console_log.read_text(encoding="utf-8", errors="replace")
    return rc, console_txt


def allocate_run_id(*base_dirs: Optional[Path]) -> int:
    """扫描各目录下 run_NNNNNN* 条目, 返回下一个可用 run_id (从 1 起)。

    run_id 采用 6 位零填充显示 (run_000001), 为大规模仿真预留位数;
    扫描正则不限位数 (兼容历史 4 位目录, 如 run_0001_longrun → id=1)。
    输入快照目录与输出目录一并扫描, 取二者最大 id + 1。
    """
    mx = 0
    for base in base_dirs:
        if not base or not base.exists():
            continue
        for p in base.iterdir():
            m = re.match(r"run_(\d+)", p.name)
            if m:
                mx = max(mx, int(m.group(1)))
    return mx + 1


def run_id_name(run_id: int, label: str = "") -> str:
    """run_id → 目录名 (06d 零填充, 可附标签): run_000003_longrun。"""
    return f"run_{run_id:06d}" + (f"_{label}" if label else "")


def run_wsl(spec: WslSpec, cfg: Dict[str, Any]) -> bool:
    """在 WSL 中执行 run_flash.sh 并做本地分析。

    run_id 规范 (06d): 当 spec.outputfiles_dir 显式指定时, 每次运行自动
    分配下一个 run_id (扫描现有 run_NNNNNN* 取 max+1):
      * 输出收集: <outputfiles_dir>/run_NNNNNN/ — run_flash.sh 经环境变量
        FLASH_COLLECT_DIR 接收 (优先于脚本内置 COLLECT_DIR);
      * 输入快照: <input_dir>/run_NNNNNN/ — 不同 id 的输入文件可能不同;
      * 分析图像: <plots_dir>/run_NNNNNN/。
    未指定 outputfiles_dir 时保持旧行为 (input_dir/outputfiles, 不分 id)。
    """
    input_dir, plots_dir = spec.input_dir, spec.plots_dir
    wsl_dir = _to_wsl_path(input_dir)
    run_sh = input_dir / spec.run_sh_name
    if not run_sh.exists():
        log(f"run_flash.sh 不存在: {run_sh}", "ERROR")
        return False

    print("\n[WSL] 运行 FLASH (setup→编译→运行→收集)")
    print("-" * 50)
    run_log_name = "wsl_console.log"
    console_log = input_dir / run_log_name
    try:
        console_log.unlink()
    except OSError:
        pass

    log("清理旧 objdir 与本地输出...", "STEP")
    # run_id 分配 (06d): 输出基目录显式指定时按 run_NNNNNN 分轮存储
    # (必须先于 cmd 构造 — cmd 中 FLASH_COLLECT_DIR 引用 outdir)
    if spec.outputfiles_dir is not None:
        run_id = allocate_run_id(spec.outputfiles_dir, input_dir)
        outdir = spec.outputfiles_dir / run_id_name(run_id)
        run_plots = plots_dir / run_id_name(run_id)
        # 输入快照: 不同 id 的输入文件可能不同, 归档到 flash_input/run_NNNNNN/
        # (崩溃记录用; 运行成功后再全量收纳根目录文件, 见 run_wsl 末尾)
        in_snap = input_dir / run_id_name(run_id)
        in_snap.mkdir(parents=True, exist_ok=True)
        for f in input_dir.iterdir():
            if f.is_file() and not f.name.startswith(("wsl_", "run_")) \
                    and (f.suffix.lower() in
                         (".par", ".cn4", ".f90", ".sh", ".png", ".json")
                         or f.name in ("Config", "Makefile")):
                shutil.copy2(f, in_snap / f.name)
        log(f"run_id = {run_id:06d} (输入快照: {in_snap.name}/)", "OK")
        outdir.mkdir(parents=True, exist_ok=True)
    else:
        run_id = None
        outdir = input_dir / "outputfiles"
        run_plots = plots_dir
    for p in [outdir, run_plots]:
        if p.exists():
            shutil.rmtree(p, ignore_errors=True)
            p.mkdir(parents=True, exist_ok=True)

    cmd = (
        f"cd {wsl_dir} && "
        f"FLASH_COLLECT_DIR='{_to_wsl_path(outdir)}' "
        f"bash {spec.run_sh_name} > {run_log_name} 2>&1; "
        f"echo \"FLASH_EXIT_CODE=$?\" >> {run_log_name}"
    )
    log(f"执行: wsl bash -c \"{cmd[:100]}...\"")
    log("首次运行需编译 FLASH，可能耗时 10~60 分钟 ...")
    flash_home = spec.flash_home or user_flash_home()
    objdir = spec.objdir
    try:
        subprocess.run(
            ["wsl", "bash", "-c",
             f"cd {wsl_dir} && rm -f wsl_run.log {run_log_name} flash_run.log "
             f"&& rm -rf {flash_home}/{objdir}"],
            capture_output=True, timeout=120,
        )
    except Exception:  # noqa: BLE001
        pass

    max_attempts = 3
    flash_rc: Optional[int] = None
    console_txt = ""
    for attempt in range(1, max_attempts + 1):
        if attempt > 1:
            log(f"WSL 返回无有效输出，重试 ({attempt}/{max_attempts})...", "WARN")
        try:
            flash_rc, console_txt = _run_wsl_with_progress(
                cmd, console_log, interval=120.0, timeout=spec.wsl_timeout,
            )
        except FileNotFoundError:
            log("未找到 wsl 命令。请确认已安装 WSL。", "ERROR")
            return False
        except subprocess.TimeoutExpired:
            log(f"WSL 运行超时 ({spec.wsl_timeout}s)", "ERROR")
            return False
        combined = console_txt.strip()
        if flash_rc == 0 and console_txt.strip():
            break
        if flash_rc != 0 and combined:
            break
        log(f"WSL 无输出 (exit={flash_rc})，5s 后重试...", "WARN")
        time.sleep(5)

    if flash_rc is None:
        log("WSL 启动失败 (多次重试后仍无输出)", "ERROR")
        return False

    flash_exit = 1
    m = re.findall(r"FLASH exit code:\s*(\d+)", console_txt)
    if m:
        flash_exit = int(m[-1])
    if "DRIVER_ABORT:" in console_txt or "Driver_abort called" in console_txt:
        flash_exit = 1

    log(combined[-3000:] if len(combined) > 3000 else combined)
    wsl_log = input_dir / "wsl_run.log"
    wsl_log.write_text(combined, encoding="utf-8", errors="replace")
    if flash_exit != 0:
        log(f"FLASH 运行失败 (exit={flash_exit})，完整日志: {wsl_log}", "ERROR")
        return False
    log(f"FLASH 运行成功 ✓ (完整日志: {wsl_log})")

    outdir = spec.outputfiles_dir / run_id_name(run_id) \
        if (run_id is not None and spec.outputfiles_dir) \
        else (input_dir / "outputfiles")
    h5s = sorted(outdir.glob("*plt_cnt*")) or sorted(outdir.glob("*chk*"))
    if not h5s:
        log(f"未找到 HDF5 输出: {outdir}", "ERROR")
        return False
    log(f"找到 {len(h5s)} 个 HDF5 输出: {outdir}")

    print("\n[分析] 制作密度时空彩图")
    print("-" * 50)
    spec.analyze_local(outdir, run_plots / "dens_timespace.png")

    # 输入全量收纳: 本轮 flash_input 根目录全部文件 (含运行日志) 移入
    # run_{id:06d}/ — 根目录仅保留 run_* 目录, 下一轮运行从零自动生成。
    # (copy2+unlink 而非 shutil.move: 目标同名时覆盖, 避免中途快照已存在)
    if run_id is not None:
        in_snap = input_dir / run_id_name(run_id)
        in_snap.mkdir(parents=True, exist_ok=True)
        n_arch = 0
        for f in sorted(input_dir.iterdir()):
            if f.is_file() and not f.name.startswith("run_"):
                try:
                    shutil.copy2(f, in_snap / f.name)
                    f.unlink()
                    n_arch += 1
                except OSError as exc:  # noqa: PERF203
                    log(f"归档失败 {f.name}: {exc}", "WARN")
        if n_arch:
            log(f"输入收纳: {n_arch} 个文件 → flash_input/{in_snap.name}/", "OK")

    print("\n" + "=" * 65)
    print(" WSL 全流程完成!")
    print(f"  run_id:       {run_id:06d}" if run_id is not None else "")
    print(f"  输入文件目录: {input_dir / run_id_name(run_id)}"
          if run_id is not None else f"  输入文件目录: {input_dir}")
    print(f"  输出结果目录: {outdir}")
    print(f"  分析图像目录: {run_plots}")
    print("=" * 65)
    return True


# ── HPC 远程运行 (paramiko 分阶段) ───────────────────────

class Remote:
    """paramiko 远程连接 (多路由自动尝试)。"""

    def __init__(self, credential: str = "flash_ssh",
                 routes: Optional[List[Tuple[str, int]]] = None):
        self.credential = credential
        self.routes = routes or [
            ("ssh.cn-zhongwei-1.paracloud.com", 22),
            ("ssh.cn-zhongwei-1.paracloud.com", 2222),
            ("ssh.cn-zhongwei-1.paracloud.com", 8443),
        ]
        self.client = None
        self.sftp = None
        self.home = ""

    def connect(self) -> None:
        from flash._core.credentials import load_ssh_credentials
        cred = load_ssh_credentials(self.credential)
        if not cred:
            raise RuntimeError(f"凭据未找到: {self.credential}")
        username = cred.get("ssh_username") or cred.get("username", "")
        password = cred.get("password", "")
        if not username or not password:
            raise RuntimeError(f"凭据 {self.credential} 缺少 ssh_username/password")

        import paramiko
        last_err = ""
        for host, port in self.routes:
            try:
                client = paramiko.SSHClient()
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                client.connect(
                    hostname=host, port=port, username=username, password=password,
                    timeout=25, allow_agent=False, look_for_keys=False,
                    banner_timeout=15, auth_timeout=25,
                )
                self.client = client
                self.sftp = client.open_sftp()
                i, o, e = client.exec_command("echo $HOME", timeout=15)
                self.home = o.read().decode(errors="replace").strip()
                log(f"已连接 {username}@{host}:{port} (HOME={self.home})", "OK")
                return
            except Exception as exc:  # noqa: BLE001
                last_err = f"{host}:{port} -> {type(exc).__name__}: {exc}"
                log(f"路由失败: {last_err}", "WARN")
        raise RuntimeError(f"全部路由连接失败: {last_err}")

    def close(self) -> None:
        for obj in (self.sftp, self.client):
            try:
                obj and obj.close()
            except Exception:  # noqa: BLE001
                pass
        self.sftp = self.client = None

    def __enter__(self) -> "Remote":
        self.connect()
        return self

    def __exit__(self, *a):
        self.close()

    def _res(self, path: str) -> str:
        if path.startswith("~/"):
            return self.home + "/" + path[2:]
        return path

    def run(self, cmd: str, timeout: int = 120) -> Tuple[str, str, int]:
        i, o, e = self.client.exec_command(cmd, timeout=timeout)
        out = o.read().decode(errors="replace")
        err = e.read().decode(errors="replace")
        code = i.channel.recv_exit_status()
        return out, err, code

    def upload(self, local: str, remote: str) -> None:
        self.sftp.put(local, self._res(remote))

    def download(self, remote: str, local: str) -> bool:
        remote = self._res(remote)
        try:
            self.sftp.stat(remote)
        except FileNotFoundError:
            log(f"远程文件不存在: {remote}", "WARN")
            return False
        Path(local).parent.mkdir(parents=True, exist_ok=True)
        self.sftp.get(remote, local)
        return True

    def exists(self, remote: str) -> bool:
        try:
            self.sftp.stat(self._res(remote))
            return True
        except FileNotFoundError:
            return False


@dataclass
class HpcSpec:
    """HPC 远程运行规格 (参数化自 layer_tracer_Ti_hpc 驱动)。"""
    name: str                          # 上传/作业目录名, 如 "layer_tracer_Ti"
    input_dir: Path
    output_dir: Path                   # 本地输出目录 (状态文件 + 下载)
    plots_dir: Path                    # 本地图像目录
    objdir: str                        # 超算编译目录, 如 "<user>/LaserSlab_Ti"
    remote_analysis_script: str        # 场景目录下的远程分析脚本名
    remote_analysis_cmd: Callable[[str], str]   # (远程输出目录) -> 完整命令
    flash_home: str = ""               # 超算 FLASH 路径, 如 "~/<user>/FLASH/FLASH4.8"
    work_base: str = ""                # 上传根目录, 如 "~/<user>/AI/Aitemp"
    credential: str = "flash_ssh"
    routes: Optional[List[Tuple[str, int]]] = None
    state_file: str = "hpc_task.json"
    download_extra: Optional[Callable[[Remote, str], List[Tuple[str, Path]]]] = None
    # 额外下载项: (远程路径, 本地路径) 列表; 由 runner 在下载阶段调用


class HpcRunner:
    """HPC 分阶段驱动: upload→submit→monitor→analyze→download。

    每阶段独立 SSH 连接, 状态写入 flash_output/hpc_task.json 支持断点续跑。
    """

    def __init__(self, spec: HpcSpec):
        self.spec = spec
        self.state_file = spec.output_dir / spec.state_file

    # ── 状态持久化 ──────────────────────────────────

    def _load_state(self) -> Dict[str, Any]:
        if not self.state_file.exists():
            raise RuntimeError(f"无任务状态: {self.state_file} (先执行 upload)")
        return json.loads(self.state_file.read_text(encoding="utf-8"))

    def _save_state(self, st: Dict[str, Any]) -> None:
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(json.dumps(st, indent=2), encoding="utf-8")

    # ── 阶段 1: upload ──────────────────────────────

    def upload(self) -> str:
        spec = self.spec
        work_base = spec.work_base or f"~/{get_sim_user_dir()}/AI/Aitemp"
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        remote_dir = f"{work_base}/{spec.name}_{ts}"
        with Remote(spec.credential, spec.routes) as r:
            r.run(f"mkdir -p {remote_dir}")
            files = [p for p in spec.input_dir.iterdir() if p.is_file()]
            for f in files:
                r.upload(str(f), f"{remote_dir}/{f.name}")
                log(f"上传 {f.name}")
            r.run(f"cd {remote_dir} && sed -i 's/\\r$//' *.sh 2>/dev/null; echo CONVERT_DONE")
        self._save_state({"ts": ts, "remote_dir": remote_dir, "job_id": None})
        log(f"上传完成 → {remote_dir}", "OK")
        return remote_dir

    # ── 阶段 2: submit ──────────────────────────────

    def submit(self) -> str:
        spec = self.spec
        st = self._load_state()
        remote_dir = st["remote_dir"]
        flash_home = spec.flash_home or user_flash_home()
        with Remote(spec.credential, spec.routes) as r:
            if not r.exists(f"{remote_dir}/submit_flash.sh"):
                raise RuntimeError(f"submit_flash.sh 未上传: {remote_dir}")
            # 预清理: 无 flash4 二进制的残留 objdir 会让 ./setup 报 "already exists"
            r.run(
                f'if [ -f {flash_home}/{spec.objdir}/flash4 ]; then echo KEEP_OBJDIR; '
                f'else rm -rf {flash_home}/{spec.objdir}; echo CLEAN_OBJDIR; fi',
                timeout=30,
            )
            out, err, code = r.run(f"cd {remote_dir} && sbatch submit_flash.sh 2>&1", timeout=60)
            log(f"sbatch: {out.strip()}")
            if err.strip():
                log(f"stderr: {err.strip()[:400]}", "WARN")
            m = re.search(r"Submitted batch job (\d+)", out)
            if not m:
                raise RuntimeError(f"sbatch 提交失败: {out} {err}")
            job_id = m.group(1)
        self._save_state({**st, "job_id": job_id})
        log(f"作业已提交 JobID={job_id}", "OK")
        return job_id

    # ── 阶段 3: monitor ─────────────────────────────

    @staticmethod
    def _check_state(job_id: str, r: Remote) -> str:
        out, _, _ = r.run(f"sacct -j {job_id} --format=State --noheader 2>/dev/null | head -1",
                          timeout=30)
        return out.strip()

    @staticmethod
    def _tail(r: Remote, remote_file: str, n: int = 25) -> None:
        out, _, code = r.run(f"tail -n {n} {remote_file} 2>/dev/null || echo NO_LOG", timeout=30)
        if code == 0 and out.strip() and "NO_LOG" not in out:
            lines = out.strip().splitlines()
            log(f"  tail {remote_file.split('/')[-1]}:")
            for ln in lines[-n:]:
                print(f"    {ln}")

    def monitor(self, wait: int = 0, poll: int = 20) -> Optional[str]:
        spec = self.spec
        st = self._load_state()
        job_id = st["job_id"]
        if not job_id:
            raise RuntimeError("无 job_id, 请先 submit")
        remote_dir = st["remote_dir"]
        started = time.time()
        with Remote(spec.credential, spec.routes) as r:
            while True:
                state = self._check_state(job_id, r)
                elapsed = time.time() - started
                log(f"JobID={job_id} 状态: {state or '(排队中)'} ({elapsed:.0f}s)")
                if state in ("COMPLETED", "COMPLETING"):
                    log(f"作业完成 ✓ (耗时 {elapsed:.0f}s)", "OK")
                    self._tail(r, f"{remote_dir}/{spec.name}_out.txt")
                    return "COMPLETED"
                if state in ("FAILED", "CANCELLED", "TIMEOUT", "NODE_FAIL", "OUT_OF_MEMORY"):
                    log(f"作业失败: {state}", "ERROR")
                    self._tail(r, f"{remote_dir}/{spec.name}_out.txt")
                    self._tail(r, f"{remote_dir}/{spec.name}_err.txt")
                    return state
                if state in ("PENDING", "RUNNING"):
                    self._tail(r, f"{remote_dir}/{spec.name}_out.txt")
                if not wait:
                    return state
                time.sleep(poll)
                if time.time() - started > wait:
                    log(f"监控超时 ({wait}s), 作业仍在运行", "WARN")
                    return state

    # ── 阶段 4: analyze (超算端绘图) ─────────────────

    @staticmethod
    def _find_output_dir(r: Remote, remote_dir: str) -> str:
        out, _, _ = r.run(
            f"ls -d {remote_dir}/outputfiles_* 2>/dev/null | head -1; "
            f"[ -d {remote_dir}/outputfiles ] && echo {remote_dir}/outputfiles",
            timeout=30,
        )
        candidates = [ln.strip() for ln in out.splitlines() if ln.strip()]
        return candidates[0] if candidates else f"{remote_dir}/outputfiles"

    def analyze(self) -> Dict[str, str]:
        spec = self.spec
        st = self._load_state()
        remote_dir = st["remote_dir"]
        script_local = spec.input_dir.parent / spec.remote_analysis_script
        if not script_local.exists():
            script_local = Path(__file__).resolve().parent / spec.remote_analysis_script
        with Remote(spec.credential, spec.routes) as r:
            r.run(f"mkdir -p {remote_dir}/analysis")
            r.upload(str(script_local), f"{remote_dir}/analysis/{spec.remote_analysis_script}")
            outdir = self._find_output_dir(r, remote_dir)
            log(f"输出目录: {outdir}")
            cmd = f"cd {remote_dir}/analysis && " + spec.remote_analysis_cmd(outdir)
            out, err, code = r.run(cmd, timeout=1800)
            print(out.strip()[-4000:])
            if err.strip():
                log(f"stderr: {err.strip()[-500:]}", "WARN")
            if code != 0:
                raise RuntimeError(f"远程分析失败 (code={code})")
        log("超算端绘图分析完成", "OK")
        return {"dens_timespace.png": f"{remote_dir}/analysis/dens_timespace.png",
                "summary.json": f"{remote_dir}/analysis/summary.json"}

    # ── 阶段 5: download ─────────────────────────────

    def download(self) -> Dict[str, Path]:
        spec = self.spec
        st = self._load_state()
        remote_dir = st["remote_dir"]
        local_map: Dict[str, Path] = {}
        files: List[Tuple[str, Path]] = [
            (f"{remote_dir}/analysis/dens_timespace.png", spec.plots_dir / "dens_timespace.png"),
            (f"{remote_dir}/analysis/summary.json", spec.output_dir / "summary.json"),
        ]
        with Remote(spec.credential, spec.routes) as r:
            outdir = self._find_output_dir(r, remote_dir)
            files.append((f"{outdir}/flash_run.log", spec.output_dir / "flash_run.log"))
            if spec.download_extra:
                files.extend(spec.download_extra(r, remote_dir) or [])
            for rf, local in files:
                if r.download(rf, str(local)):
                    local_map[Path(rf).name] = local
                    log(f"下载 {Path(rf).name} → {local}", "OK")
        log(f"本地输出: {spec.output_dir}", "OK")
        return local_map

    def all(self, cfg: Dict[str, Any]) -> bool:
        """完整流水线。"""
        self.upload()
        self.submit()
        state = self.monitor(wait=int(os.environ.get("FLASH_HPC_WAIT", "21600")), poll=20)
        if state != "COMPLETED":
            log(f"作业未完成: {state}", "ERROR")
            return False
        self.analyze()
        self.download()
        return True

    def staged(self, action: str, wait_seconds: Optional[int] = None) -> bool:
        """分阶段动作: upload/submit/monitor/analyze/download/status/all。"""
        a = (action or "").strip().lower()
        if a == "all":
            return self.all({})
        if a == "upload":
            self.upload()
            return True
        if a == "submit":
            self.submit()
            return True
        if a == "monitor":
            state = self.monitor(wait=wait_seconds or 0, poll=20)
            log(f"最终状态: {state}")
            return state == "COMPLETED"
        if a == "analyze":
            res = self.analyze()
            log(f"远程分析产物: {list(res)}", "OK")
            return True
        if a == "download":
            self.download()
            return True
        if a == "status":
            self._load_state()
            log(f"任务状态文件: {self.state_file}", "OK")
            return True
        raise ValueError(f"未知动作 {action!r}: all/upload/submit/monitor/analyze/download/status")


# ── 统一入口 ─────────────────────────────────────────────

def run_scenario(wsl_spec: Optional[WslSpec], hpc_spec: Optional[HpcSpec],
                 cfg: Dict[str, Any], run_mode: Optional[str] = None) -> bool:
    """按 RUN_MODE 分发: wsl → run_wsl; hpc → HpcRunner.all()。

    Args:
        wsl_spec: WSL 运行规格 (wsl 模式必需)
        hpc_spec: HPC 运行规格 (hpc 模式必需)
        cfg: 场景参数配置
        run_mode: 显式指定模式; None 时用 resolve_run_mode()
    """
    mode = resolve_run_mode(run_mode or "wsl")
    if mode == "wsl":
        if wsl_spec is None:
            raise RuntimeError("wsl 模式需要提供 WslSpec")
        return run_wsl(wsl_spec, cfg)
    if hpc_spec is None:
        raise RuntimeError("hpc 模式需要提供 HpcSpec")
    return HpcRunner(hpc_spec).all(cfg)