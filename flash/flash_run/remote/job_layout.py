# -*- coding: utf-8 -*-
"""job_layout.py — 超算作业**目录拓扑**与**资源规格**的唯一实现点
════════════════════════════════════════════════════════════════════════════

★ 为什么需要这个模块（2026-10-26 用户质疑后重做）

  上一轮我曾把两条观测当成"铁律"写进文档与记忆：

    ① "setup 与 make 必须在登录节点"
    ② "产物必须落并行盘"

  **用户指出这不是铁律。** 复核后的计算节点实测（NC-E，作业 4924747/4924748/
  4924752/4924760）证明那两条都是**误判**：

  | 观测项                        | 实测结果                    | 旧结论错在哪        |
  |-------------------------------|-----------------------------|---------------------|
  | GPFS 上 os.walk 2811 个文件   | **0.2 s**                   | 元数据不慢          |
  | GPFS 上建 500 个符号链接      | **1.08 s**                  | 不慢                |
  | setup_depends.py              | **21.7 s**                  | 不是"11 分钟不出 .o"|
  | 计算节点上 `setup`            | **SUCCESS，2 s**            | 不是"永久挂起"      |
  | 计算节点 scratch 上 setup+make| **2 s + 31 s**（1550 个 .o） | 完全可行           |

  ⇒ 真正的规律是：**编译/运行的**中间产物**放在哪，决定了快慢**。
    同一套 FLASH、同一台机器、同一份输入：

      · objdir 在**共享并行盘**（GPFS）→ make 阶段漫长且难以归因
      · objdir 在**节点本地 scratch**（tmpfs）→ setup 2 s + make 31 s

    这不是"必须在登录节点"，而是"**别把编译中间产物写在慢速共享盘上**"。

★ 本模块给出的正是这个"目录拓扑"抽象
  一次超算作业的目录分三类，各有职责：

    scratch（节点本地 tmpfs）── 编译 objdir、运行工作目录
        · 快（内存盘），**用完即弃**，随节点生命周期消失
        · ⇒ 编译/运行都在这里做 ⇒ 真正用满计算节点的 CPU 与内存
    shared（共享并行盘）────── 输入源、最终产物、作业日志
        · 慢，但**跨节点可见、持久**
        · ⇒ 只有需要留存的东西才写这里
    archive（可选）─────────── 产物从 scratch 归档回 shared 的落点

  典型作业流程（全部在**计算节点**内完成，登录节点只做提交/轮询）：

      sbatch job.sh
        ├─ stage   : shared/sim_input  →  scratch/  （拷输入，几十 KB）
        ├─ build   : cd scratch/obj && make -j$SLURM_CPUS_PER_TASK
        ├─ run     : cd scratch/run  && srun -n $SLURM_NTASKS ./flash4
        └─ archive : scratch/run/*.chk → shared/output/  （回传产物）

  与"登录节点预编译 + 作业只运行"相比：编译也吃到了计算节点的核，
  一个作业内串起全流程，无需登录节点长时间占用（登录节点是交互资源）。

★ 约定
  · 本模块**不含**任何装置路径（分区/模块/站点根）—— 那些归
    `flash.flash_run.env.devices`（架构护栏 R-SCENE-05）。
  · 本模块是**纯数据 + 纯渲染**：无网络、无 subprocess，可离线单测。
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Dict, List, Optional, Sequence, Tuple

# ── 目录类别 ────────────────────────────────────────────────────────

#: 节点本地 scratch（快）：编译中间产物、运行工作目录
SCRATCH = "scratch"
#: 共享并行盘（慢但持久且跨节点可见）：输入源、最终产物、日志
SHARED = "shared"


@dataclass(frozen=True)
class JobLayout:
    """一次超算作业的目录拓扑。

    Attributes:
        scratch_root: 节点本地快盘的**探测起点**（作业内按文件系统类型
            复核；可能是 ``$SLURM_TMPDIR`` 之类）。
        scratch_prefix: 在探测到的快盘下为本作业建的**专属子目录**
            （默认含 ``${SLURM_JOB_ID}`` ⇒ 并发作业互不干扰）。
        shared_root: 共享并行盘根（输入/产物/日志）。
        build_dir: 编译目录名 —— 相对 ``FL_SCRATCH_ROOT``。
        run_dir: 运行工作目录名 —— 相对 ``FL_SCRATCH_ROOT``。
        output_dir: 产物落点 —— 相对 ``FL_SHARED_ROOT``。
        log_dir: 作业日志目录 —— 相对 ``FL_SHARED_ROOT``。
    """

    scratch_root: str = "/tmp"
    shared_root: str = "$HOME"
    scratch_prefix: str = "flash_${SLURM_JOB_ID:-$$}"
    build_dir: str = "obj"
    run_dir: str = "run"
    output_dir: str = "output"
    log_dir: str = "logs"

    # ── 绝对路径（作业内 shell 展开） ────────────────────────────

    @property
    def scratch_build(self) -> str:
        """编译目录（scratch 内，相对 FL_SCRATCH_ROOT）。"""
        return f"${{FL_SCRATCH_ROOT}}/{self.build_dir}"

    @property
    def scratch_run(self) -> str:
        """运行目录（scratch 内，相对 FL_SCRATCH_ROOT）。"""
        return f"${{FL_SCRATCH_ROOT}}/{self.run_dir}"

    @property
    def shared_output(self) -> str:
        """产物目录绝对路径（shared 内）。"""
        return self._join(self.shared_root, self.output_dir)

    @property
    def shared_log(self) -> str:
        """日志目录绝对路径（shared 内）。"""
        return self._join(self.shared_root, self.log_dir)

    @staticmethod
    def _join(root: str, rel: str) -> str:
        """拼路径（root 可能是含 $VAR 的 shell 片段，不做规范化）。"""
        if not rel:
            return root
        return f"{root.rstrip('/')}/{rel.lstrip('/')}"

    # ── 渲染 ────────────────────────────────────────────────────

    def shell_vars(self, prefix: str = "FL") -> str:
        """渲染**探测前**的变量导出块。

        只含不依赖 scratch 探测结果的部分：shared 侧的路径 + 探测起点 +
        作业专属前缀。★ scratch 侧的 BUILD/RUN 目录必须等探测完成后
        才能确定 ⇒ 见 `scratch_paths()`。
        """
        return "\n".join([
            f'export {prefix}_SHARED_ROOT="{self.shared_root}"',
            f'export {prefix}_SCRATCH_BASE="{self.scratch_root}"',
            f'export {prefix}_SCRATCH_PREFIX="{self.scratch_prefix}"',
            f'export {prefix}_OUTPUT_DIR="{self.shared_output}"',
            f'export {prefix}_LOG_DIR="{self.shared_log}"',
        ])

    def scratch_paths(self, prefix: str = "FL") -> str:
        """渲染**探测后**的 scratch 路径变量（BUILD/RUN 目录）。

        ★ 必须在 `scratch_probe_script()` **之后**调用 ——
          FL_SCRATCH_ROOT 此时才是真正的节点本地快盘路径。
        """
        return "\n".join([
            f'export {prefix}_SCRATCH_ROOT="${{{prefix}_SCRATCH_BASE}}/'
            f'${{{prefix}_SCRATCH_PREFIX}}"',
            f'export {prefix}_BUILD_DIR="{self.scratch_build}"',
            f'export {prefix}_RUN_DIR="{self.scratch_run}"',
        ])

    def prepare_dirs(self, prefix: str = "FL") -> str:
        """渲染"建目录"片段（scratch + shared 两边都建）。"""
        return "\n".join([
            f'mkdir -p "${{{prefix}_BUILD_DIR}}" "${{{prefix}_RUN_DIR}}"',
            f'mkdir -p "${{{prefix}_OUTPUT_DIR}}" "${{{prefix}_LOG_DIR}}"',
        ])

    def archive_outputs(self, patterns: Sequence[str] = ("*chk*",),
                        prefix: str = "FL") -> str:
        """渲染"把产物从 scratch 归档回 shared"的片段。

        Args:
            patterns: 要归档的文件名 glob（相对运行目录）。
            prefix: 变量名前缀（与 shell_vars 一致）。

        Returns:
            shell 片段；无匹配文件时不报错（保持作业可继续）。

        ★★ glob **不能加引号**：`for f in "*chk*"` 里引号会阻止 shell
          展开 ⇒ 循环体拿到字面量 `*chk*` ⇒ 一个文件都拷不出
          （实测作业 4924826：仿真正常完成但归档目录为空）。
          ⇒ 用 `for f in <glob>`（不加引号）+ nullglob 防空匹配。
        """
        pats = " ".join(patterns)
        return "\n".join([
            "# ── 归档：scratch → shared（只有需要留存的产物才写共享盘）──",
            f'shopt -s nullglob',
            f'cd "${{{prefix}_RUN_DIR}}"',
            f'for f in {pats}; do',
            f'  [ -f "$f" ] || continue',
            f'  cp -f "$f" "${{{prefix}_OUTPUT_DIR}}/" 2>/dev/null || true',
            f'done',
            f'shopt -u nullglob',
            f'echo "[layout] 归档 $(ls -1 "${{{prefix}_OUTPUT_DIR}}" 2>/dev/null | wc -l) '
            f'个文件 → ${{{prefix}_OUTPUT_DIR}}"',
        ])

    def to_dict(self) -> Dict[str, str]:
        return {
            "scratch_root": self.scratch_root,
            "shared_root": self.shared_root,
            "scratch_prefix": self.scratch_prefix,
            "build_dir": self.build_dir,
            "run_dir": self.run_dir,
            "output_dir": self.output_dir,
            "log_dir": self.log_dir,
        }


# ── 资源规格 ────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ResourceSpec:
    """作业资源规格（对应 sbatch 的资源指令）。

    ★ 与目录无关，但同属"提交时该指定什么"这件事，故并列在此。

    Attributes:
        nodes: 节点数。
        ntasks: 总进程数（= MPI rank 数）。
        cpus_per_task: 每 rank 的核数（线程级 MPI 时 >1）。
        time_limit: 墙钟上限（如 ``02:00:00``）。
        mem_per_node: 每节点内存（如 ``16G``）。
        account: 计费账户。
        partition: 分区。
        qos: QoS。
        constraint: 节点特性约束。
    """

    nodes: int = 1
    ntasks: int = 1
    cpus_per_task: int = 1
    time_limit: str = ""
    mem_per_node: str = ""
    account: str = ""
    partition: str = ""
    qos: str = ""
    constraint: str = ""

    def sbatch_directives(self) -> List[str]:
        """渲染为 ``#SBATCH`` 指令行（不含 #SBATCH 前缀）。"""
        out = [f"--nodes={self.nodes}", f"--ntasks={self.ntasks}"]
        if self.cpus_per_task > 1:
            out.append(f"--cpus-per-task={self.cpus_per_task}")
        if self.time_limit:
            out.append(f"--time={self.time_limit}")
        if self.mem_per_node:
            out.append(f"--mem-per-node={self.mem_per_node}")
        if self.account:
            out.append(f"--account={self.account}")
        if self.partition:
            out.append(f"--partition={self.partition}")
        if self.qos:
            out.append(f"--qos={self.qos}")
        if self.constraint:
            out.append(f"--constraint={self.constraint}")
        return out

    def to_dict(self) -> Dict[str, object]:
        return {
            "nodes": self.nodes, "ntasks": self.ntasks,
            "cpus_per_task": self.cpus_per_task,
            "time_limit": self.time_limit, "mem_per_node": self.mem_per_node,
            "account": self.account, "partition": self.partition,
            "qos": self.qos, "constraint": self.constraint,
        }


# ── scratch 根探测 ──────────────────────────────────────────────────

#: 节点本地快盘的候选（按优先级）。★ 刻意不含站点绝对路径 ——
#: 装置参数归 flash.flash_run.env.devices（护栏 R-SCENE-05）。
SCRATCH_CANDIDATES: Tuple[str, ...] = (
    "${SLURM_TMPDIR:-}",
    "/tmp",
    "/var/tmp",
    "/dev/shm",
)

#: 判定"是节点本地快盘"的文件系统类型（tmpfs / ramfs）
LOCAL_FS_TYPES: Tuple[str, ...] = ("tmpfs", "ramfs")


def scratch_probe_script(prefix: str = "FL") -> str:
    """渲染"探测可用的节点本地快盘"的 shell 片段。

    在作业内执行；把选中的根写入 ``FL_SCRATCH_BASE``。
    ★ 判据是**文件系统类型**（tmpfs/ramfs）而非路径 —— 路径可能因
      集群而异（有的集群 /tmp 就在共享盘上）。

    产物：

    - ``FL_SCRATCH_BASE``  —— 探测到的快盘根（**不含**作业专属前缀）
    - ``FL_SCRATCH_LOCAL`` —— ``1``（是节点本地快盘）/ ``0``（回退共享盘）

    ★ 探测**只决定根**，作业专属子目录由 `JobLayout.scratch_paths()`
      追加 ⇒ 并发作业互不干扰（否则共用 /tmp/obj ⇒ 互相覆盖）。
    """
    cands = " ".join(f'"{c}"' for c in SCRATCH_CANDIDATES)
    return "\n".join([
        "# ── 探测节点本地快盘（scratch）──",
        "#   判据 = 文件系统类型 tmpfs/ramfs；找不到则回退共享盘（慢但正确）",
        f'{prefix}_SCRATCH_LOCAL=0',
        f'for cand in {cands}; do',
        '  [ -n "$cand" ] || continue',
        '  [ -d "$cand" ] && [ -w "$cand" ] || continue',
        '  _fstype=$(df -T "$cand" 2>/dev/null | tail -1 | awk "{print \\$2}")',
        '  case "$_fstype" in',
        f'    tmpfs|ramfs) {prefix}_SCRATCH_BASE="$cand"; '
        f'{prefix}_SCRATCH_LOCAL=1; break;;',
        '  esac',
        'done',
        f'[ -n "${prefix}_SCRATCH_BASE" ] || '
        f'{prefix}_SCRATCH_BASE="${{{prefix}_SHARED_ROOT:-/tmp}}"',
        f'export {prefix}_SCRATCH_BASE {prefix}_SCRATCH_LOCAL',
        f'echo "[layout] scratch base=${prefix}_SCRATCH_BASE '
        f'local=${prefix}_SCRATCH_LOCAL fstype=$_fstype"',
    ])


# ── 解析 ────────────────────────────────────────────────────────────

def resolve_layout(
    shared_root: Optional[str] = None,
    scratch_root: Optional[str] = None,
    *,
    build_dir: str = "obj",
    run_dir: str = "run",
    output_dir: str = "output",
    log_dir: str = "logs",
    scratch_prefix: str = "flash_${SLURM_JOB_ID:-$$}",
) -> JobLayout:
    """解析作业目录拓扑。

    优先级（**环境变量 > 显式参数 > 默认**）：

    - ``FLASH_SCRATCH_ROOT`` → scratch 探测起点
    - ``FLASH_SHARED_ROOT`` → shared 根
    - 默认 scratch = ``/tmp``（作业内再按文件系统类型复核）

    ★ scratch_root 允许写成含 ``$VAR`` 的 shell 片段（如
      ``/tmp/flash_${SLURM_JOB_ID}``），保持到作业内才展开。
    """
    scratch = (scratch_root
               or os.environ.get("FLASH_SCRATCH_ROOT")
               or "/tmp")
    shared = (shared_root
              or os.environ.get("FLASH_SHARED_ROOT")
              or os.environ.get("HOME")
              or "$HOME")
    return JobLayout(
        scratch_root=scratch,
        shared_root=shared,
        scratch_prefix=scratch_prefix,
        build_dir=build_dir,
        run_dir=run_dir,
        output_dir=output_dir,
        log_dir=log_dir,
    )


def stage_inputs_script(src_dir: str, prefix: str = "FL",
                        patterns: Sequence[str] = ("*",),
                        dest_var: str = "FL_BUILD_DIR") -> str:
    """渲染"把输入从 shared 拷到 scratch"的片段。

    Args:
        src_dir: 输入源目录（shared 上）。
        patterns: 要拷的文件名 glob（相对 src_dir）。默认全拷。
        prefix: 变量名前缀。
        dest_var: 目标目录变量名（默认 FL_BUILD_DIR）。

    ★ 用 ``find -exec``（**不是** ``for f in *.x``）：后者的 glob 在
      for 列表里**只展开一次且用当前 cwd**，实测会静默拷不到任何文件
      （超算作业 4924540 挂起 7 分钟的根因之一）。
    ★ 单个 pattern 时不能带 `\\(` `\\)`（find 会报语法错）。
    """
    if len(patterns) == 1:
        expr = f'-name "{patterns[0]}"'
    else:
        # ★ 多个 pattern 必须用 **-o** 连接：
        #   \( -name a -o -name b \)
        # 写成 \( -name a \( -name b \) 是**错的**（find 会当成嵌套组，
        # 结果匹配不到任何文件 ⇒ 静默拷 0 个 ⇒ 实测作业 4924811
        # "staged 0 files" ⇒ FLASH 报 "IONMIX4 file not found"）。
        expr = " \\( " + " -o ".join(
            f'-name "{p}"' for p in patterns) + " \\) "
    return "\n".join([
        f'# ── stage：shared → scratch ──',
        f'mkdir -p "${{{dest_var}}}"',
        f'find "{src_dir}" -maxdepth 1 -type f {expr} '
        f'-exec cp -f {{}} "${{{dest_var}}}/" \\;',
        f'echo "[layout] staged '
        f'$(find "${{{dest_var}}}" -maxdepth 1 -type f | wc -l) files → ${dest_var}"',
    ])


def compile_parallel_jobs(nodes_hint: int = 1) -> str:
    """渲染 make 的并行度：按**作业实际申请的总核数**。

    ★ ``nproc`` 在 SLURM 作业内返回**节点全部**核数（实测 48），
      远超作业申请量 ⇒ 编译线程数失控 ⇒ 内存耗尽 / make 卡死。

    ★ 并行度 = ``SLURM_NTASKS × SLURM_CPUS_PER_TASK``：
      只看 ``SLURM_CPUS_PER_TASK`` 会漏掉多 rank 的情况
      （实测 ``--ntasks=4 --cpus-per-task=1`` 时算出 -j1 ⇒ 编译串行，
      白白浪费计算资源）。
    """
    return (
        'FL_MAKE_JOBS="${SLURM_CPUS_PER_TASK:-1}"\n'
        '[ -n "${SLURM_NTASKS:-}" ] && '
        'FL_MAKE_JOBS=$((FL_MAKE_JOBS * ${SLURM_NTASKS}))\n'
        '[ "${SLURM_JOB_NUM_NODES:-1}" -gt 1 ] && '
        'FL_MAKE_JOBS=$((FL_MAKE_JOBS * ${SLURM_JOB_NUM_NODES}))\n'
        'echo "[layout] make -j$FL_MAKE_JOBS"'
    )
