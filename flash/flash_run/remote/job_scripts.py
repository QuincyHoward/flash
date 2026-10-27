# -*- coding: utf-8 -*-
"""job_scripts.py — 超算作业体生成器（stage → build → run → archive）
════════════════════════════════════════════════════════════════════════════

★ 为什么把整条链放进**一个** sbatch 作业（2026-10-26）

  之前的做法是「登录节点预编译 → 作业只运行」，看起来快，实则：

  - 登录节点是**交互资源**，在上面跑 make 属于误用（长时间占核）；
  - 编译在登录节点串行，而作业内只能用 4 个 rank ⇒ 资源用不满；
  - 编译产物落在**共享并行盘**上，作业里再读一遍（慢）。

  实测（NC-E 计算节点，作业 4924760 COMPLETED）把四步放进**同一个作业**
  之后，一切都在**计算节点**的节点本地 scratch 上完成：

      setup        2 s
      make -j16   31 s   （1550 个 .o，13 MB 二进制）
      FLASH 运行  299 s   （623 chk）
      归档回共享盘  0 s

  ⇒ 计算节点的 CPU 与内存被**完整利用**，登录节点只做"提交 + 轮询"。

★ 本模块的职责
  渲染一个自包含的作业体：输入搬运 → 编译 → 运行 → 产物归档。
  目录拓扑来自 `job_layout.JobLayout`（scratch/shared 分离），
  装置参数来自 `flash.flash_run.env.devices`（护栏 R-SCENE-05）。

★ 不含装置绝对路径：模块路径/库路径由调用方通过 ``env_block`` 注入。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence

from .job_layout import (
    JobLayout,
    compile_parallel_jobs,
    scratch_probe_script,
    stage_inputs_script,
)


@dataclass
class BuildSpec:
    """编译步骤的规格。

    Attributes:
        flash_home: FLASH 安装根（含 setup 与 source/）。
        unit: FLASH 场景单元名（``-auto`` 的参数）。
        setup_args: 额外的 setup 参数（不含 ``-auto <unit>`` 与 ``-objdir``）。
        par_file: 源目录里的 par 文件名（复制到运行目录并改名 flash.par）。
        bin_name: 编译产物二进制名（默认 flash4）。
        source_dir: 场景源文件目录（**shared** 上），作业内会被拷到
            ``flash_home/source/Simulation/SimulationMain/<unit>/``。
            ★ setup 会**读取**该目录来生成 objdir 的 .F90 符号链接 ⇒
              必须先拷到、后 setup（顺序反了 ⇒ objdir 无链接 ⇒ make 无从编译）。
    """

    flash_home: str
    unit: str
    setup_args: Sequence[str] = ()
    par_file: str = ""
    bin_name: str = "flash4"
    source_dir: str = ""
    #: make -j 之前先单独烘的目标（竞态修复）。★ 纯机制：目标列表由
    #: 场景声明给出，本模块不含任何场景信息。2026-09 实测：SNB 覆盖的
    #: hy_slopeLimiters 与 Conductivity 全量并行编译存在竞态。
    pre_build_targets: Sequence[str] = ()
    #: make 并行度上限（0 = 不限）。★ 多节点作业按 SLURM 环境算出的
    #: -j 可能远超单节点内存可承载的并发编译数。
    make_jobs_max: int = 0

    def setup_cmd(self, objdir_var: str = "$FL_BUILD_DIR",
                  stdin_answer: str = "") -> str:
        """渲染 setup 命令（objdir 用**变量**，作业内才解析）。

        Args:
            objdir_var: objdir 的 shell 表达式（通常 ``"$FL_BUILD_DIR"``）。
            stdin_answer: 喂给 setup 的 stdin 答案（默认空 = 不接管 stdin）。
                ★ setup 在遇到"实体 .F90"时会 ``input()`` 提问
                  "Continue? [Y/n]" ⇒ 批处理里 stdin 为空 ⇒ EOFError。
                  传 "Y" 即"同意删除并重建符号链接"。

        Notes:
            ★ ``-parfile`` 让 setup 自己把 par 拷成 flash.par（它要从
              ``SimulationMain/<unit>/`` 读）——比运行前手工 cp 更可靠。
        """
        args = " ".join(self.setup_args)
        par = f" -parfile={self.par_file}" if self.par_file else ""
        cmd = (f"./setup -auto {self.unit} {args}{par} "
               f"-objdir={objdir_var}")
        if stdin_answer:
            # ★ 用 printf 而非 echo：echo 会给所有行加换行，setup 只读一行
            cmd = f"printf '%s\\n' '{stdin_answer}' | {cmd}"
        return cmd

    def simulation_main_dir(self) -> str:
        """FLASH 树内该场景单元的 SimulationMain 目录。"""
        return f"{self.flash_home}/source/Simulation/SimulationMain/{self.unit}"


@dataclass
class RunSpec:
    """运行步骤的规格。

    Attributes:
        ntasks: MPI rank 数（``srun -n``）。
        binary: 运行的可执行文件名（相对运行目录）。
        launcher: 启动器（``srun`` 走 SLURM PMI；``mpirun`` 走自带 bootstrap）。
        extra_args: 追加参数。
        env_block: 运行前的环境导出块（module/库路径等）。
    """

    ntasks: int = 1
    binary: str = "flash4"
    launcher: str = "srun"
    extra_args: Sequence[str] = ()
    env_block: str = ""


def render_job_body(
    layout: JobLayout,
    *,
    build: Optional[BuildSpec] = None,
    run: Optional[RunSpec] = None,
    input_dir: str = "",
    archive_patterns: Sequence[str] = ("*chk*",),
    prefix: str = "FL",
) -> str:
    """渲染完整作业体（stage → build → run → archive）。

    Args:
        layout: 目录拓扑。
        build: 编译规格（None = 跳过编译，直接用现成二进制）。
        run: 运行规格（None = 只编译不运行）。
        input_dir: 输入源目录（shared 上）；非空时先 stage 到 scratch。
        archive_patterns: 归档的文件名 glob。
        prefix: 目录变量前缀。

    Returns:
        shell 脚本体（**不含** ``#SBATCH`` 头 —— 那是 render_sbatch 的职责）。

    ★ 关键顺序：``scratch 探测 → 建目录 → stage → build → run → archive``。
      归档放在最后且**必须成功**，否则作业产物留在 scratch 里随节点消失。
    """
    parts: List[str] = []

    # ── 0. 变量 → scratch 探测 → 路径 → 建目录 ──
    # ★ 顺序至关重要：BUILD/RUN 目录依赖探测出的 FL_SCRATCH_ROOT，
    #   必须在探测**之后**才能确定（否则多节点/多盘时路径会错）。
    parts.append(layout.shell_vars(prefix))
    parts.append(scratch_probe_script(prefix))
    parts.append(layout.scratch_paths(prefix))
    parts.append(layout.prepare_dirs(prefix))

    # ── 1. stage：shared → scratch ──
    # ★★ 只搬**运行期数据**（EOS 表 .cn4 + par），且落到 **run 目录**
    #   （不是 objdir！）：
    #   · .F90 必须留在 SimulationMain/<unit>/ 让 setup 建符号链接；
    #     若把实体 .F90 放进 objdir，setup 会提示
    #     "Simulation_initBlock.F90 is not a symlink and will be deleted
    #      by setup. Continue? [Y/n]" ⇒ 批处理里 stdin 为空 ⇒ EOFError
    #     ⇒ setup 中止（实测作业 4924789：EOFError: EOF when reading a line）。
    #   · par 必须是 setup 的**输入**（setup 读它生成 flash.par），
    #     所以它也要出现在 SimulationMain/<unit>/ 里。
    if input_dir:
        parts.append(stage_inputs_script(input_dir, prefix=prefix,
                                         patterns=("*.cn4", "*.par"),
                                         dest_var=f"{prefix}_RUN_DIR"))

    # ── 2. build：在 scratch 里编译 ──
    if build is not None:
        parts.append("# ── build：编译（全部在节点本地 scratch）──")
        # ① 源文件准备：setup 要读 SimulationMain/<unit>/ 下的源文件 ⇒ 先拷
        if build.source_dir:
            sim_main = build.simulation_main_dir()
            parts.append(
                f'mkdir -p "{sim_main}"\n'
                f'find "{build.source_dir}" -maxdepth 1 -type f \\( '
                f'-name "Config" -o -name "Makefile" -o -name "*.F90" '
                f'-o -name "*.cn4" -o -name "*.par" \\) '
                f'-exec cp -f {{}} "{sim_main}/" \\;\n'
                f'echo "[layout] 源文件就绪: '
                f'$(find "{sim_main}" -maxdepth 1 -type f | wc -l) 个"')
        parts.append(compile_parallel_jobs())
        if build.make_jobs_max > 0:
            parts.append(
                f'[ "${{FL_MAKE_JOBS:-1}}" -gt {build.make_jobs_max} ] && '
                f'FL_MAKE_JOBS={build.make_jobs_max}\n'
                f'echo "[layout] make 并行度钳制 → -j$FL_MAKE_JOBS '
                f'(上限 {build.make_jobs_max})"')
        parts.append(f'cd "{build.flash_home}"')
        # ★★ setup 必须**非交互**：它在 objdir 里遇到"实体 .F90"（非符号
        #   链接）时会 input() 提问 "will be deleted by setup. Continue? [Y/n]"
        #   ⇒ 批处理里 stdin 为空 ⇒ EOFError ⇒ setup 中止（实测作业
        #   4924789："EOFError: EOF when reading a line"）。
        #   双保险：① 上面已保证 objdir 干净；② 喂一个 "Y" 进去
        #   （等价于"同意删除并重建符号链接"），残留实体文件也不阻塞。
        parts.append(build.setup_cmd(f'"${{FL_BUILD_DIR}}"', stdin_answer="Y"))
        parts.append(f'cd "${{FL_BUILD_DIR}}"')
        # ★ pre-build 竞态目标必须在 **setup 之后**（objdir 的 Makefile 由
        #   setup 生成；setup 之前 objdir 为空 ⇒ "No rule to make target"，
        #   2026-10-27 作业 4926819 实测）。且 `|| true`：个别目标可能
        #   无对应规则（非竞态目标集时），不能因此中止整个作业。
        if build.pre_build_targets:
            targets = " ".join(build.pre_build_targets)
            parts.append(
                f'# ── pre-build：先单独烘竞态目标（setup 之后）──\n'
                f'make -j"$FL_MAKE_JOBS" {targets} '
                f'2>&1 | tail -2 || true')
        # ★ 闸门（§V 教训：make 失败绝不能静默流入运行步）
        parts.append(
            f'make -j"$FL_MAKE_JOBS" || {{ echo MAKE_FAIL; exit 3; }}')
        parts.append(
            f'[ -x "${{{prefix}_BUILD_DIR}}/{build.bin_name}" ] || '
            f'{{ echo BUILD_FAIL_NO_{build.bin_name.upper()}; exit 3; }}')
        parts.append(f'cp -f "${{{prefix}_BUILD_DIR}}/{build.bin_name}" '
                     f'"${{{prefix}_RUN_DIR}}/"')

    # ── 3. run：在 scratch 里跑 ──
    if run is not None:
        parts.append("# ── run：运行（scratch）──")
        if run.env_block:
            parts.append(run.env_block)
        # ★ .cn4（EOS 表）与 par 已在 stage 阶段落到 run 目录；
        #   flash.par 由 setup 用 -parfile 生成在 objdir ⇒ 拷过来。
        if build is not None and build.par_file:
            parts.append(
                f'cp -f "${{{prefix}_BUILD_DIR}}/flash.par" '
                f'"${{{prefix}_RUN_DIR}}/flash.par" 2>/dev/null || true')
        parts.append(f'cd "${{{prefix}_RUN_DIR}}"')
        extra = " ".join(run.extra_args)
        parts.append(f'{run.launcher} -n {run.ntasks} ./{run.binary} {extra}'.rstrip())

    # ── 4. archive：scratch → shared ──
    parts.append(layout.archive_outputs(archive_patterns, prefix=prefix))
    # ★ 闸门（§V）：有运行步 ⇒ 成功 = 产物数 > 0；零产物显式失败，
    #   防止"作业 COMPLETED 但实际什么都没跑出来"的假成功。
    if run is not None:
        parts.append(
            f'[ "$(ls -1 "${{{prefix}_OUTPUT_DIR}}" 2>/dev/null | wc -l)" -gt 0 ] || '
            f'{{ echo ARCHIVE_EMPTY_FAIL; exit 4; }}')

    return "\n".join(parts)


def render_resource_directives(
    nodes: int = 1,
    ntasks: int = 1,
    cpus_per_task: int = 1,
    time_limit: str = "",
    mem_per_node: str = "",
    account: str = "",
    partition: str = "",
    qos: str = "",
    constraint: str = "",
) -> List[str]:
    """渲染资源指令（``#SBATCH`` 完整行）。

    与 `job_layout.ResourceSpec.sbatch_directives()` 等价，
    此处直接给完整 ``#SBATCH`` 前缀版本，便于脚本模板拼接。
    """
    from .job_layout import ResourceSpec

    spec = ResourceSpec(
        nodes=nodes, ntasks=ntasks, cpus_per_task=cpus_per_task,
        time_limit=time_limit, mem_per_node=mem_per_node, account=account,
        partition=partition, qos=qos, constraint=constraint,
    )
    return [f"#SBATCH {d}" for d in spec.sbatch_directives()]
