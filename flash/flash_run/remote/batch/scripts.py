# -*- coding: utf-8 -*-
"""batch.scripts — 批量作业体渲染（场景无关）
════════════════════════════════════════════════════════════════════════════

一个 sbatch 作业 = 编译**一次** + N 个实例（同节点并发或前台串行）+ per-instance
内联归档。泛化自 SandwichTxN/scripts/hpc_pf_batch.py 的 _render_job_body
（2026-11-07/08 五轮超算实测验证：v3 踩核教训→累计绑核、v1 丢档教训→归档内联、
E1/E2 校准数据→方案库取值）。

场景差异经 BatchGroupSpec 注入（touch_files/cn4_patterns/env_block），
本模块不含任何场景字样。
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from typing import Mapping, Optional, Sequence

from flash.flash_run.remote.slurm_control import SlurmJobSpec, render_sbatch


# ────────────────────────────────────────────────────────────────────
# 实例模型
# ────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class BatchInstance:
    """批量单实例。

    tag       run 目录/归档/日志 key（如 "pf1.0" / "r2_nt8"）
    par_name  输入目录中的 par 文件名（适配器决定命名）
    ntasks    该实例 rank 数
    """
    tag: str
    par_name: str
    ntasks: int


@dataclass(frozen=True)
class BatchGroupSpec:
    """一批实例的运行方式。"""
    instances: Sequence[BatchInstance]
    mode: str = "conc"                        # conc=&+wait；seq=前台串行（E1 独占测量）
    pin: str = "cumulative"                   # cumulative=累计偏移（conc 必须）；
                                              # shared=每实例复用 [0, ntasks-1]
                                              # （seq 单任务独占整节点，默认方案）
    launcher: str = "mpirun"                  # 绑核语义 I_MPI_PIN_PROCESSOR_LIST 依赖 mpirun
    touch_files: Sequence[str] = ()           # 每实例 run 目录需 touch 的空文件
    cn4_patterns: Sequence[str] = ("*.cn4",)  # stage 到每实例 run 目录的 glob
    env_block: str = ""                       # 运行期环境（场景层 build_env_block 注入）
    log_name: str = "flash_run.log"
    elapsed_marker: str = "BATCH_ELAPSED"     # 哨兵行前缀（collect 解析）
    steps_marker: str = "BATCH_STEPS"
    extra_stage_globs: Sequence[str] = dataclasses.field(default_factory=tuple)

    def __post_init__(self):
        if self.pin not in ("cumulative", "shared"):
            raise ValueError(f"BatchGroupSpec.pin 必须为 cumulative|shared，"
                             f"得到 {self.pin!r}")
        if self.mode == "conc" and self.pin == "shared":
            raise ValueError("pin='shared' 仅适用于 seq 模式"
                             "（conc 并发实例会踩同一核段）")

    @property
    def total_ranks(self) -> int:
        return sum(i.ntasks for i in self.instances)

    @property
    def alloc_ranks(self) -> int:
        """sbatch --ntasks 申请量：cumulative=Σ；shared=单实例峰值（顺序复用）。"""
        if self.pin == "shared":
            return max(i.ntasks for i in self.instances)
        return self.total_ranks


# ────────────────────────────────────────────────────────────────────
# 作业体渲染
# ────────────────────────────────────────────────────────────────────

def render_batch_job_body(bid: str, group: BatchGroupSpec, *,
                          input_dir: str, output_dir: str, scratch_root: str,
                          unit: str, flash_home: str, setup_args: str = "",
                          build_setup_exe: str = "./setup",
                          build_make: str = "make -j16",
                          build_par_name: Optional[str] = None,
                          make_fail_rc: int = 3) -> str:
    """渲染 batch sbatch 作业体（bash 文本）。

    build_par_name 缺省取第一个实例的 par（编译期 par 仅作 setup 占位）。
    """
    if group.mode not in ("conc", "seq"):
        raise ValueError(f"BatchGroupSpec.mode 必须为 conc|seq，得到 {group.mode!r}")
    tags = [i.tag for i in group.instances]
    nts = [i.ntasks for i in group.instances]
    pars = [i.par_name for i in group.instances]
    setup_par = build_par_name or pars[0]
    amp = "&" if group.mode == "conc" else ""
    wait_line = "wait" if group.mode == "conc" else ""
    env_block = group.env_block
    cn4_cp = " ".join(f"-name {shlex_quote(p)}" for p in group.cn4_patterns) \
        if group.cn4_patterns else ""
    # touch 文件行
    touch_line = ""
    if group.touch_files:
        touch_line = "  touch " + " ".join(shlex_quote(t) for t in group.touch_files)
    extra_stage = ""
    for pat in group.extra_stage_globs:
        extra_stage += f'\n  cp "$FL_IN"/{pat} "$d/" 2>/dev/null || true'

    return f"""# ── [batch {bid}] build once + {len(group.instances)} instances ({group.mode}) ──
echo "[batch] node=$(hostname)  start=$(date +%s)"
FL_IN="{input_dir}"
FL_OUT="{output_dir}"
FL_UNIT="{unit}"
FL_FLASH_HOME="{flash_home}"
FL_SCR="{scratch_root}"
FL_BUILD="$FL_SCR/build"
mkdir -p "$FL_SCR" "$FL_OUT"

# ── build：编译一次 (setup 非交互, objdir 在节点本地 tmpfs) ──
SIMMAIN="$FL_FLASH_HOME/source/Simulation/SimulationMain/$FL_UNIT"
mkdir -p "$SIMMAIN"
find "$FL_IN" -maxdepth 1 -type f \\( -name "Config" -o -name "Makefile" -o -name "*.F90" \\) \\
    -exec cp -f {{}} "$SIMMAIN/" \\;
cd "$FL_FLASH_HOME"
printf '%s\\n' 'Y' | {build_setup_exe} -auto "$FL_UNIT" {setup_args} \\
    -parfile="$FL_IN/{setup_par}" -objdir="$FL_BUILD"
cd "$FL_BUILD"
{build_make} || {{ echo MAKE_FAIL; exit {make_fail_rc}; }}
[ -x "$FL_BUILD/flash4" ] || {{ echo BUILD_FAIL; exit {make_fail_rc}; }}
echo "[batch] build done t=$(($(date +%s)))"

# ── per-run 目录 (数据文件 + 各实例 par → flash.par) ──
TAGS=({' '.join(_bash_word(t) for t in tags)})
NTS=({' '.join(str(n) for n in nts)})
PARS=({' '.join(_bash_word(p) for p in pars)})
for i in "${{!TAGS[@]}}"; do
  tag=${{TAGS[$i]}}
  d="$FL_SCR/run_$tag"; mkdir -p "$d"
  {"cp " + ' '.join('"$FL_IN"/' + p for p in group.cn4_patterns) + ' "$d/" 2>/dev/null || true' if cn4_cp else ':'}
{extra_stage}
  cp "$FL_IN/${{PARS[$i]}}" "$d/flash.par"
{touch_line}
  cp -f "$FL_BUILD/flash4" "$d/"
done

# ── 运行期环境 ──
{env_block}

# ── {len(group.instances)} 实例 ({group.mode}, pin={group.pin}) ──
# ★ 绑核策略:
#   cumulative — 实例 i 独占 [累计前缀, 累计前缀+ntasks_i-1]（conc 并发必须，
#     v3 踩核教训修复、v4 验证 2.5× 提速；异构 ntasks 按累计偏移）。
#   shared — 每实例复用 [0, ntasks_i-1]（seq 顺序执行不重叠，单任务独占整节点；
#     默认方案 p1x32：核数取实测峰值而非节点满核）。
# ★ 归档内联到每实例（v1 教训: 末尾统一归档在墙钟超时时全丢）。
lo=0
for i in "${{!TAGS[@]}}"; do
  tag=${{TAGS[$i]}}; nts=${{NTS[$i]}}
  {f'hi=$((nts - 1))' if group.pin == 'shared' else 'hi=$((lo + nts - 1))'}
  (
    export I_MPI_PIN=1
    export I_MPI_PIN_PROCESSOR_LIST="$lo-$hi"
    d="$FL_SCR/run_$tag"
    cd "$d" || exit 9
    t0=$(date +%s)
    {group.launcher} -np "$nts" ./flash4 > {group.log_name} 2>&1
    rc=$?
    echo "{group.elapsed_marker} $tag $(( $(date +%s) - t0 )) rc=$rc"
    echo "{group.steps_marker} $tag $(awk '$1 ~ /^[0-9][0-9]*$/ && NF > 3 {{s=$1}} END {{print s+0}}' {group.log_name} 2>/dev/null)"
    o="$FL_OUT/$tag"; mkdir -p "$o"
    cp {group.log_name} "$o/" 2>/dev/null
    cp *chk* "$o/" 2>/dev/null
  ){amp}
  {f'lo=$((lo + nts))' if group.pin == 'cumulative' else ':  # shared: lo 恒 0（顺序复用）'}
done
{wait_line}
echo "[batch] all runs done t=$(($(date +%s)))"
echo FLASH_JOB_DONE
"""


def _bash_word(s: str) -> str:
    """bash 数组字面量安全引用。"""
    return "'" + s.replace("'", "'\\''") + "'"


def shlex_quote(s: str) -> str:
    return _bash_word(s)


# ────────────────────────────────────────────────────────────────────
# sbatch 包装（含 nodes=1 钉死）
# ────────────────────────────────────────────────────────────────────

def render_batch_sbatch(bid: str, body: str, group: BatchGroupSpec, *,
                        partition: str, time_limit: str, account: str = "",
                        out_dir: str, workdir: str,
                        marker: str = "FLASH_JOB_DONE") -> str:
    """组装 SlurmJobSpec → render_sbatch → 单节点钉死补丁。"""
    spec = SlurmJobSpec(
        name=f"batch_{bid}",
        script=body,
        partition=partition,
        nodes=1,
        ntasks=max(group.alloc_ranks, 1),
        cpus_per_task=1,
        time_limit=time_limit,
        mem_per_node="",
        account=account,
        marker=marker,
        out_dir=out_dir,
        timeout=7200,
    )
    text = render_sbatch(spec, workdir=workdir)
    # ★ R1: render_sbatch 仅在 nodes>1 时写 -N；批量作业必须整节点
    #   （节点本地 tmpfs scratch + 单份二进制），显式补 --nodes=1
    if "#SBATCH --nodes=1" not in text and "#SBATCH -N 1" not in text:
        text = text.replace("#!/bin/bash\n", "#!/bin/bash\n#SBATCH --nodes=1\n", 1)
    return text
