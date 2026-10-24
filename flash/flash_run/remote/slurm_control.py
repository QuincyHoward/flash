#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""slurm_control.py — SLURM 作业控制薄层 + executor 抽象（三模式统一，2026-10-22）。
════════════════════════════════════════════════════════════════════════════

把散落在各场景的 sbatch/sacct/哨兵轮询逻辑收编为单一实现，供两种执行形态共用：

  * LocalExecutor  — 纯 subprocess（hpc-insitu：场景驱动已在超算登录节点，
                     绝不 SSH 自连）
  * RemoteExecutor — 包装 RemoteSession 等远端会话（hpc-remote：本机驱动经
                     SSH 远程执行同一批命令）

两类 executor 实现同一个 ``run(cmd, timeout) -> (stdout, stderr, rc)`` 协议，
因此 submit/轮询/哨兵判定只写一遍。

来源（收编）:
  * SNBOneCH_m._hpc_wait_job     → wait_for_job
  * SNBOneCH_m._hpc_detect_partition → detect_partition
  * HpcRunner.monitor (runner.py) → wait_for_job（同一语义）
设计约束（超算实测铁律）:
  * 长作业轮询间隔自动放宽（timeout>7200 → 60s），减少 SSH 连接次数
  * 哨兵 marker = 作业输出文件中的字符串（如 ``echo BUILD_OK``），
    COMPLETED 后仍须 grep marker 确认（防"作业完成但内部失败"假阳性）
  * 失败时自动回显作业输出尾部，省一次人工登录
"""

from __future__ import annotations

import re
import subprocess
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Protocol, Tuple

LOG_TAG = {"INFO": "[i]", "OK": "[OK]", "WARN": "[!]", "ERROR": "[X]", "STEP": "[-]"}


def log(msg: str, level: str = "INFO") -> None:
    print(f"  {LOG_TAG.get(level, '[i]')} {msg}")


# ── executor 协议与两个实现 ──────────────────────────────

class CommandExecutor(Protocol):
    """统一命令执行协议: run(cmd) -> (stdout, stderr, returncode)。"""

    def run(self, cmd: str, timeout: int = 120) -> Tuple[str, str, int]:
        ...


class LocalExecutor:
    """本地 subprocess 执行器（hpc-insitu：登录节点直接编排，无 SSH）。

    ★ 绝不自连: 不经过任何 SSH/RemoteSession。"""
    def run(self, cmd: str, timeout: int = 120) -> Tuple[str, str, int]:
        r = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=timeout)
        return r.stdout or "", r.stderr or "", r.returncode


class RemoteExecutor:
    """远端会话适配器（hpc-remote）：包装 RemoteSession / _HpcRemote 等对象。

    被包装对象须已有 ``run(cmd, timeout=...) -> (out, err, rc)`` 方法
    （``flash.flash_run.remote.session.RemoteSession`` 即是；旧路径
    ``flash.scenarios.flash_demo.demo_hpc.remote_ssh_helper`` 为兼容壳）。"""

    def __init__(self, session: Any) -> None:
        self._session = session

    def run(self, cmd: str, timeout: int = 120) -> Tuple[str, str, int]:
        return self._session.run(cmd, timeout=timeout)


# ── 基础查询 ─────────────────────────────────────────────

def sbatch_available(exe: CommandExecutor) -> bool:
    """远端/本机是否具备 sbatch+sacct。"""
    out, _, _ = exe.run("which sbatch >/dev/null 2>&1 && which sacct >/dev/null 2>&1 "
                        "&& echo SLURM_OK", timeout=30)
    return "SLURM_OK" in (out or "")


def submit(exe: CommandExecutor, script_path: str, workdir: str = "") -> str:
    """sbatch 提交脚本，返回 JobID（解析失败抛 RuntimeError）。"""
    cmd = f"cd {workdir} && sbatch {script_path} 2>&1" if workdir \
        else f"sbatch {script_path} 2>&1"
    out, err, _ = exe.run(cmd, timeout=60)
    blob = (out or "") + (err or "")
    m = re.search(r"Submitted batch job (\d+)", blob)
    if not m:
        raise RuntimeError(f"sbatch 提交失败: {blob.strip()[-300:]}")
    return m.group(1)


def job_state(exe: CommandExecutor, job_id: str) -> str:
    """sacct 查询作业状态（无记录返回空串）。"""
    out, _, _ = exe.run(
        f"sacct -j {job_id} --format=State --noheader 2>/dev/null | head -1",
        timeout=30)
    return (out or "").strip().splitlines()[0] if (out or "").strip() else ""


def latest_job_by_name(exe: CommandExecutor, name: str) -> str:
    """按作业名查最近一个在队列中的作业 ID；没有则返回空串。

    ★ 用途：提交类操作的**超时回查**。`sbatch` 调用可能因
    `module load` 耗时（NC-E 实测 40~60 s）而超时，但作业其实已入队；
    只凭"调用返回与否"判成败会得出与事实相反的结论（实测 G12）。
      判定必须来自状态查询，而不是调用是否返回。
    """
    out, _err, _rc = exe.run(
        "squeue -u $(whoami) -h -o '%i %j' 2>/dev/null "
        f"| awk '$2==\"{name}\"{{print $1}}' | tail -1",
        timeout=30)
    return (out or "").strip().splitlines()[-1].strip() if (out or "").strip() else ""


def tail(exe: CommandExecutor, path_glob: str, n: int = 25) -> str:
    """回显作业输出尾部（诊断用）。"""
    out, _, _ = exe.run(f"tail -{n} {path_glob} 2>/dev/null", timeout=30)
    return out or ""


def detect_partition(exe: CommandExecutor, known: Dict[str, str],
                     account: str) -> str:
    """sinfo 探测可用分区（收编 SNBOneCH_m._hpc_detect_partition L1153）。

    sinfo 首行可能是不可用分区 (NC-E 'all inact') → 只认 avail=up，
    已知映射 (HPC_PARTITION[account]) 优先。"""
    try:
        out, _, _ = exe.run("sinfo -s 2>/dev/null", timeout=30)
        up, default = [], None
        for line in (out or "").splitlines():
            cols = line.split()
            if not cols or cols[0] in ("PARTITION", "AVAIL"):
                continue
            if cols[0].endswith("*"):
                default = cols[0].rstrip("*")
            if len(cols) > 1 and cols[1].startswith("up"):
                up.append(cols[0].rstrip("*"))
        if account in known and known[account] in up:
            return known[account]
        if up:
            return up[0]
        if default:
            return default
    except Exception:  # noqa: BLE001
        pass
    return known.get(account, "v5_192")


def cores_per_node(exe: CommandExecutor, partition: str, default: int = 48) -> int:
    """查询分区每节点核数（-N 计算依据；收编 SNBOneCH_m L1250-1255）。"""
    out, _, _ = exe.run(f'sinfo -h -p {partition} -o "%c" | head -1', timeout=30)
    try:
        return int((out or "").strip().splitlines()[0])
    except (ValueError, IndexError):
        return default


def wait_for_job(exe: CommandExecutor, job_id: str, marker: str = "",
                 out_glob: str = "", timeout: int = 3600, poll: int = 0,
                 log_fn: Callable[[str, str], None] = log) -> bool:
    """sacct 轮询至 COMPLETED/FAILED 并确认 marker（收编 SNBOneCH_m._hpc_wait_job）。

    Args:
        marker: 作业输出中应出现的字符串（如 BUILD_OK）；空串跳过确认。
        out_glob: 作业输出文件 glob（marker grep 与失败回显用）。
        poll: 轮询间隔秒；0 = 自动（timeout>7200 → 60s，否则 20s，
              减少 SSH 连接次数）。

    ★ 语义与 SNB 原版一致: COMPLETED 但 marker 未命中时**告警并返回 True**
      （"人工核验"——作业退出码可能未回显 marker，但不宜盲目判失败）。
    """
    interval = poll if poll > 0 else (20 if timeout <= 7200 else 60)
    start = time.time()
    last = ""
    while time.time() - start < timeout:
        state = job_state(exe, job_id)
        if state != last:
            log_fn(f"[作业] JobID={job_id} 状态: {state or '(无记录)'} "
                   f"(已等待 {int(time.time()-start)}s)",
                   "OK" if state == "RUNNING" else "STEP")
            last = state
        if state == "COMPLETED":
            if marker and out_glob:
                out2, _, _ = exe.run(
                    f"grep -l '{marker}' {out_glob} 2>/dev/null | head -1; "
                    f"tail -6 {out_glob} 2>/dev/null", timeout=30)
                if marker in (out2 or ""):
                    return True
                log_fn(f"[作业] COMPLETED 但 marker 未确认 (人工核验): "
                       f"{(out2 or '')[-200:]}", "WARN")
            return True
        if state in ("FAILED", "CANCELLED", "TIMEOUT", "NODE_FAIL",
                     "OUT_OF_MEMORY"):
            log_fn(f"[作业] 失败: {state}", "ERROR")
            if out_glob:
                log_fn(f"[作业] 输出尾部:\n{tail(exe, out_glob, 25)[-1800:]}",
                       "ERROR")
            return False
        time.sleep(interval)
    log_fn(f"[作业] JobID={job_id} 等待超时 ({timeout}s)", "ERROR")
    return False


# ── 作业规格与批量执行 ───────────────────────────────────

@dataclass
class SlurmJobSpec:
    """单条 sbatch 作业规格（render_sbatch 渲染为脚本）。"""
    name: str                      # 作业名（也是脚本/日志文件名前缀）
    script: str                    # 作业体命令（不含 #SBATCH 头；可多行）
    partition: str = ""            # 空 = 不写 -p（用集群默认）
    nodes: int = 1
    ntasks: int = 1
    env_block: str = ""            # module load / export 块（插在 cd 之后）
    marker: str = ""               # 成功哨兵（作业体末尾 echo）
    out_glob: str = ""             # 日志 glob（哨兵 grep 与失败回显）
    timeout: int = 3600
    depends_on: str = ""           # 前置 JobID（空 = 不依赖）
    poll: float = 0                # 轮询间隔秒；0=自动（timeout>7200→60s 否则 20s）


def render_sbatch(spec: SlurmJobSpec, workdir: str) -> str:
    """SlurmJobSpec → 完整 sbatch 脚本文本（LF 行尾）。"""
    lines = ["#!/bin/bash"]
    if spec.partition:
        lines.append(f"#SBATCH -p {spec.partition}")
    if spec.nodes > 1:
        lines.append(f"#SBATCH -N {spec.nodes}")
    lines.append(f"#SBATCH --ntasks={spec.ntasks}")
    lines.append(f"#SBATCH -J {spec.name}")
    lines.append(f"#SBATCH -o {workdir}/{spec.name}_%j.out")
    lines.append(f"#SBATCH -e {workdir}/{spec.name}_%j.out")
    if spec.depends_on:
        lines.append(f"#SBATCH --dependency=afterok:{spec.depends_on}")
    lines.append("")
    lines.append(f"cd {workdir}")
    lines.append("export PYTHONUNBUFFERED=1")
    if spec.env_block:
        lines.append(spec.env_block)
    lines.append(spec.script)
    if spec.marker:
        lines.append(f'echo {spec.marker}')
    lines.append("")
    return "\n".join(lines)


def run_job_chain(exe: CommandExecutor, jobs: List[SlurmJobSpec], workdir: str,
                  gates: Optional[Dict[str, Callable[[CommandExecutor], bool]]] = None,
                  skip_first_if: Optional[Callable[[CommandExecutor], bool]] = None,
                  log_fn: Callable[[str, str], None] = log) -> bool:
    """顺序提交一批作业并逐个等待（收编 SNB build→run 双作业流程）。

    Args:
        gates: {job_name: gate(exe)->bool} —— 提交前闸门（如 SNB run 作业的
               par 值级检查 gr_hypreUseFloor=.false.）；返回 False 即中止。
        skip_first_if: 首作业跳过判定（复刻 SNB --skip-build：返回 True 时
                       跳过 jobs[0]，由调用方在回调内完成补解压等替代动作）。
    Returns:
        全部作业成功 True；任一失败/闸门拦截 False。
    """
    gates = gates or {}
    for idx, spec in enumerate(jobs):
        if idx == 0 and skip_first_if is not None and skip_first_if(exe):
            log_fn(f"[作业链] 跳过 {spec.name}（skip_first_if 命中）", "WARN")
            continue
        gate = gates.get(spec.name)
        if gate is not None and not gate(exe):
            log_fn(f"[作业链] {spec.name} 提交前闸门未通过，中止", "ERROR")
            return False
        script_path = f"{workdir}/{spec.name}.sh"
        # 落盘（经 exe 执行 heredoc，两种 executor 通用；★ LF 行尾）
        body = render_sbatch(spec, workdir)
        exe.run(f"mkdir -p {workdir}", timeout=30)
        write_cmd = (
            f"cat > {script_path} << 'FLASH_JOB_EOF'\n{body}FLASH_JOB_EOF\n"
            f"sed -i 's/\\r$//' {script_path} 2>/dev/null; chmod +x {script_path}"
        )
        exe.run(write_cmd, timeout=60)
        job_id = submit(exe, script_path, workdir=workdir)
        log_fn(f"[作业链] {spec.name} 已提交 JobID={job_id}", "OK")
        if not wait_for_job(exe, job_id, marker=spec.marker,
                            out_glob=spec.out_glob or f"{workdir}/{spec.name}_*.out",
                            timeout=spec.timeout, poll=spec.poll, log_fn=log_fn):
            return False
    return True
