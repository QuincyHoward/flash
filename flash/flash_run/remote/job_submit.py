# -*- coding: utf-8 -*-
"""job_submit.py — 超算作业提交服务（**通用**，不含任何场景信息）
════════════════════════════════════════════════════════════════════════════

★ 本模块回答的问题：**怎么把一个作业交到超算上去**

    渲染作业脚本 → 落盘 → sbatch → 拿到 JobID

  它**不认识任何场景**：场景名、setup 参数、par 文件名、输入目录
  全部由调用方（场景层）通过 `JobRequest` 传进来。

★ 与既有模块的分工

    job_layout.py   目录拓扑（scratch / shared）+ 资源规格
    job_scripts.py  作业体渲染（stage → build → run → archive）
    slurm_control.py sbatch / sacct 底层操作
    ★ job_submit.py  ← **本模块**：把上面三者串成"一次提交"

★ 铁律：绝不 SSH 自连
    hpc-insitu（已在超算登录节点）⇒ 用 `LocalExecutor`；
    hpc-remote（本机驱动）⇒ 用 `SSHExecutor`。
    判据由**调用方**给出（`local=True/False`），本模块不自行探测。
"""
from __future__ import annotations

import re
import shlex
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from .job_layout import JobLayout, ResourceSpec
from .job_scripts import BuildSpec, RunSpec, render_job_body
from .slurm_control import SlurmJobSpec, render_sbatch

__all__ = ["JobRequest", "RenderedJob", "render_job", "submit_job"]


# ═══════════════════════════════════════════════════════════════════
# 请求规格
# ═══════════════════════════════════════════════════════════════════

@dataclass
class JobRequest:
    """一次超算提交的完整请求（**场景无关**）。

    Attributes:
        name: 作业名（也用于日志/产物目录名）。
        flash_home: FLASH 安装根（含 ``setup`` 与 ``source/``）。
        unit: FLASH 场景单元名（``-auto`` 的参数）。
        setup_args: setup 额外参数（不含 ``-auto <unit>`` / ``-objdir``）。
        par_file: par 文件名（setup 用 ``-parfile=`` 生成 flash.par）。
        source_dir: 场景输入源目录（**共享盘**上）；作业内拷到 scratch。
        layout: 目录拓扑（scratch / shared）。
        resource: 资源规格（核数/墙钟/账户/分区）。
        ntasks: MPI rank 数（运行期 ``srun -n``）。
        env_block: 运行前的环境导出块（module/库路径）。
        launcher: 启动器（``srun`` 走 SLURM PMI）。
        archive_patterns: 归档回共享盘的文件名 glob。
        bin_name: 编译产物二进制名。
        marker: 作业成功哨兵字符串。
        timeout: 作业墙钟上限（秒）。
    """

    name: str
    flash_home: str
    unit: str
    setup_args: Sequence[str] = ()
    par_file: str = ""
    source_dir: str = ""
    layout: JobLayout = field(default_factory=JobLayout)
    resource: ResourceSpec = field(default_factory=ResourceSpec)
    ntasks: int = 1
    env_block: str = ""
    launcher: str = "srun"
    archive_patterns: Sequence[str] = ("*chk*",)
    bin_name: str = "flash4"
    marker: str = "FLASH_JOB_DONE"
    timeout: int = 7200

    def build_spec(self) -> BuildSpec:
        """编译步骤规格（由请求派生）。"""
        return BuildSpec(
            flash_home=self.flash_home,
            unit=self.unit,
            setup_args=tuple(self.setup_args),
            par_file=self.par_file,
            bin_name=self.bin_name,
            source_dir=self.source_dir,
        )

    def run_spec(self) -> RunSpec:
        """运行步骤规格（由请求派生）。"""
        return RunSpec(
            ntasks=self.ntasks,
            binary=self.bin_name,
            launcher=self.launcher,
            env_block=self.env_block,
        )


@dataclass
class RenderedJob:
    """渲染结果：完整 sbatch 脚本文本 + 关键路径。"""

    script_text: str
    script_path: str
    log_dir: str
    output_dir: str
    job_name: str


# ═══════════════════════════════════════════════════════════════════
# 渲染
# ═══════════════════════════════════════════════════════════════════

def render_job(req: JobRequest) -> RenderedJob:
    """把 `JobRequest` 渲染成完整 sbatch 脚本（**不执行**任何东西）。

    Returns:
        `RenderedJob`（脚本文本 + 落盘路径 + 日志/产物目录）。
    """
    layout = req.layout
    body = render_job_body(
        layout,
        build=req.build_spec(),
        run=req.run_spec(),
        input_dir=req.source_dir,
        archive_patterns=tuple(req.archive_patterns),
    )
    res = req.resource
    spec = SlurmJobSpec(
        name=req.name,
        script=body,
        partition=res.partition,
        nodes=res.nodes,
        ntasks=res.ntasks,
        cpus_per_task=res.cpus_per_task,
        time_limit=res.time_limit,
        mem_per_node=res.mem_per_node,
        account=res.account,
        qos=res.qos,
        constraint=res.constraint,
        marker=req.marker,
        out_dir=layout.shared_log,
        timeout=req.timeout,
    )
    script_text = render_sbatch(spec, workdir=layout.shared_root)
    return RenderedJob(
        script_text=script_text,
        script_path=f"{layout.shared_log}/{req.name}.sh",
        log_dir=layout.shared_log,
        output_dir=layout.shared_output,
        job_name=req.name,
    )


# ═══════════════════════════════════════════════════════════════════
# 提交
# ═══════════════════════════════════════════════════════════════════

_JOBID_RE = re.compile(r"Submitted batch job (\d+)")


def submit_job(req: JobRequest, executor=None, dry_run: bool = False) -> Dict[str, str]:
    """渲染 + 落盘 + `sbatch`，返回提交结果。

    Args:
        req: 提交请求（场景无关）。
        executor: 命令执行器（须实现 `run(cmd, timeout)`）。
            · 本机（hpc-insitu）→ `LocalExecutor`
            · 远程（hpc-remote）→ `SSHExecutor`
            省略则用 `LocalExecutor`。
        dry_run: True ⇒ 只渲染并返回，**不落盘、不提交**。

    Returns:
        ``{"ok", "job_id", "job_name", "script_path", "log_dir", "output_dir",
        "reason"}``

    ★ 成功判据 = **rc==0 且解析出 JobID**：
      "命令返回 0" 不等于"作业已入队"（实测 submit 可能超时但已入队）。
    """
    from .executors import LocalExecutor

    rendered = render_job(req)
    base = {
        "ok": False, "job_id": "", "job_name": rendered.job_name,
        "script_path": rendered.script_path, "log_dir": rendered.log_dir,
        "output_dir": rendered.output_dir, "reason": "",
    }
    if dry_run:
        return {**base, "ok": True, "reason": "dry-run"}

    exe = executor or LocalExecutor()

    # ① 落盘（heredoc + LF 行尾归一 + 可执行位）
    write_cmd = (
        f"mkdir -p {shlex.quote(rendered.log_dir)} && "
        f"cat > {shlex.quote(rendered.script_path)} << 'FLASH_JOB_EOF'\n"
        f"{rendered.script_text}FLASH_JOB_EOF\n"
        f"sed -i 's/\\r$//' {shlex.quote(rendered.script_path)} 2>/dev/null; "
        f"chmod +x {shlex.quote(rendered.script_path)}"
    )
    _out, err, rc = exe.run(write_cmd, timeout=120)
    if rc != 0:
        return {**base,
                "reason": f"作业脚本落盘失败 rc={rc}: {(err or '')[-400:]}"}

    # ② 提交
    sub_cmd = (f"cd {shlex.quote(req.layout.shared_root)} && "
               f"sbatch {shlex.quote(rendered.script_path)} 2>&1")
    out, err, rc = exe.run(sub_cmd, timeout=300)
    blob = (out or "") + (err or "")
    m = _JOBID_RE.search(blob)
    if not m:
        return {**base,
                "reason": f"提交失败（未解析出 JobID）: {blob.strip()[-400:]}"}
    return {**base, "ok": True, "job_id": m.group(1)}
