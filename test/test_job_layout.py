# -*- coding: utf-8 -*-
"""job_layout / job_scripts 的离线单测。

★ 全部离线：无网络、无 subprocess、无超算依赖。
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from flash.flash_run.remote.job_layout import (
    JobLayout,
    ResourceSpec,
    compile_parallel_jobs,
    resolve_layout,
    scratch_probe_script,
    stage_inputs_script,
)
from flash.flash_run.remote.job_scripts import (
    BuildSpec,
    RunSpec,
    render_job_body,
    render_resource_directives,
)
from flash.flash_run.remote.slurm_control import SlurmJobSpec, render_sbatch


# ── JobLayout ─────────────────────────────────────────────────

def test_layout_paths_split_scratch_and_shared():
    lay = JobLayout(scratch_root="/tmp/scr", shared_root="/shared",
                    build_dir="obj", run_dir="run",
                    output_dir="out", log_dir="logs")
    # ★ scratch 侧路径是**相对 FL_SCRATCH_ROOT**（探测后才确定）
    assert lay.scratch_build == "${FL_SCRATCH_ROOT}/obj"
    assert lay.scratch_run == "${FL_SCRATCH_ROOT}/run"
    assert lay.shared_output == "/shared/out"
    assert lay.shared_log == "/shared/logs"
    # ★ 关键不变式：编译/运行在 scratch，产物/日志在 shared
    assert "SCRATCH_ROOT" in lay.scratch_build
    assert lay.shared_output.startswith("/shared")


def test_layout_keeps_shell_variables_literal():
    """★ 路径里的 $VAR 必须保留字面量，由作业内 shell 展开。"""
    lay = JobLayout(scratch_root="/tmp/flash_${SLURM_JOB_ID}")
    assert "SLURM_JOB_ID" in lay.scratch_prefix
    assert "${FL_SCRATCH_ROOT}" in lay.scratch_build


def test_layout_shell_vars_split_before_and_after_probe():
    """★ BUILD/RUN 路径必须在 scratch 探测**之后**才导出。"""
    lay = JobLayout(scratch_root="/tmp/s", shared_root="/sh")
    before = lay.shell_vars()
    for k in ("FL_SCRATCH_BASE", "FL_SCRATCH_PREFIX",
              "FL_OUTPUT_DIR", "FL_LOG_DIR"):
        assert k in before
    # 探测前不得出现 BUILD/RUN（此时还不知道 scratch 根）
    assert "FL_BUILD_DIR" not in before
    assert "FL_RUN_DIR" not in before
    after = lay.scratch_paths()
    assert "FL_SCRATCH_ROOT" in after
    assert "FL_BUILD_DIR" in after and "FL_RUN_DIR" in after
    prep = lay.prepare_dirs()
    assert "mkdir -p" in prep
    assert "${FL_BUILD_DIR}" in prep and "${FL_OUTPUT_DIR}" in prep


def test_layout_scratch_prefix_isolates_concurrent_jobs():
    """★ 并发作业必须各有各的 scratch 子目录（否则互相覆盖）。"""
    lay = JobLayout()
    assert "SLURM_JOB_ID" in lay.scratch_prefix


def test_layout_archive_copies_from_run_to_output():
    lay = JobLayout(scratch_root="/tmp/s", shared_root="/sh")
    arch = lay.archive_outputs(["*chk*"])
    assert "cd \"${FL_RUN_DIR}\"" in arch
    assert "cp -f" in arch and "${FL_OUTPUT_DIR}" in arch
    # ★ 必须用 nullglob，否则无匹配时字面量 '*chk*' 会被 cp 报错
    assert "nullglob" in arch


def test_layout_archive_glob_not_quoted():
    """★ glob 不能加引号 —— 引号会阻止 shell 展开 ⇒ 一个文件都拷不出。

    实测作业 4924826：仿真正常完成（chk_0622）但归档目录为空。
    """
    lay = JobLayout(scratch_root="/tmp/s", shared_root="/sh")
    arch = lay.archive_outputs(["*chk*"])
    line = [ln for ln in arch.splitlines() if ln.startswith("for f in")][0]
    assert line == "for f in *chk*; do", f"glob 被引号包住了: {line!r}"
    assert "\"*chk*\"" not in arch
    # ★ 只拷普通文件（目录要跳过）
    assert '[ -f "$f" ] || continue' in arch


def test_resolve_layout_env_override(monkeypatch):
    monkeypatch.setenv("FLASH_SCRATCH_ROOT", "/env/scr")
    monkeypatch.setenv("FLASH_SHARED_ROOT", "/env/shared")
    lay = resolve_layout()
    assert lay.scratch_root == "/env/scr"
    assert lay.shared_root == "/env/shared"


def test_resolve_layout_explicit_beats_env(monkeypatch):
    monkeypatch.setenv("FLASH_SCRATCH_ROOT", "/env/scr")
    lay = resolve_layout(scratch_root="/explicit")
    assert lay.scratch_root == "/explicit"


# ── ResourceSpec ──────────────────────────────────────────────

def test_resource_spec_directives():
    res = ResourceSpec(nodes=2, ntasks=16, cpus_per_task=4,
                       time_limit="02:00:00", mem_per_node="32G",
                       account="flash_ssh", partition="v5_192")
    d = res.sbatch_directives()
    assert "--nodes=2" in d
    assert "--ntasks=16" in d
    assert "--cpus-per-task=4" in d
    assert "--time=02:00:00" in d
    assert "--mem-per-node=32G" in d
    assert "--account=flash_ssh" in d
    assert "--partition=v5_192" in d


def test_resource_spec_omits_unset():
    res = ResourceSpec()
    d = res.sbatch_directives()
    assert "--cpus-per-task" not in d
    assert "--time" not in d
    assert "--mem-per-node" not in d


# ── scratch 探测 ──────────────────────────────────────────────

def test_scratch_probe_uses_fstype_not_path():
    """★ 判据必须是文件系统类型（tmpfs/ramfs），不能是路径。"""
    txt = scratch_probe_script()
    assert "tmpfs|ramfs" in txt
    assert "df -T" in txt
    assert "FL_SCRATCH_LOCAL" in txt
    # 候选里不得有站点绝对路径（装置参数归 devices.py）
    assert "/public1/soft" not in txt


def test_compile_parallel_jobs_uses_slurm_cpus_not_nproc():
    """★ 不得用 nproc（返回节点全部核数）⇒ 编译线程数失控。"""
    txt = compile_parallel_jobs()
    assert "SLURM_CPUS_PER_TASK" in txt
    assert "nproc" not in txt


# ── stage ─────────────────────────────────────────────────────

def test_stage_multi_pattern_uses_or():
    """★ 多个 pattern 必须用 **-o** 连接。

    写成 ( -name a ( -name b ) 是错的 ⇒ find 匹配不到 ⇒ 静默拷 0 个
    ⇒ 实测作业 4924811 "staged 0 files" ⇒ FLASH 报 IONMIX4 file not found。
    """
    txt = stage_inputs_script("/src", patterns=("*.cn4", "*.par"))
    assert "-name \"*.cn4\" -o -name \"*.par\"" in txt
    assert "\\( -name" in txt


def test_stage_single_pattern_no_paren_group():
    """★ 单 pattern 不带分组括号（否则 find 报语法错）。"""
    txt = stage_inputs_script("/src", patterns=("*.cn4",))
    assert "-name \"*.cn4\"" in txt
    assert "\\(" not in txt


def test_compile_parallel_jobs_counts_ntasks():
    """★ 并行度要含 SLURM_NTASKS（否则多 rank 时算出 -j1 串行）。"""
    txt = compile_parallel_jobs()
    assert "SLURM_NTASKS" in txt
    assert "nproc" not in txt


def test_stage_uses_find_not_for_glob():
    """★ for 列表里的 glob 只展开一次且用当前 cwd ⇒ 静默拷不到文件。"""
    txt = stage_inputs_script("/shared/input")
    assert "find " in txt and "-exec cp" in txt
    assert "for f in" not in txt


# ── render_job_body ───────────────────────────────────────────

def _body(**kw):
    lay = JobLayout(scratch_root="/tmp/scr_${SLURM_JOB_ID}",
                    shared_root="/shared/proj")
    build = BuildSpec(flash_home="/home/u/QC/FLASH/FLASH4.8",
                      unit="QC/grad_dens_sandwich_000001",
                      setup_args=["-1d", "+cartesian", "-nxb=16"],
                      par_file="grid_rede.par",
                      source_dir="/shared/proj/sim_input")
    run = RunSpec(ntasks=4, binary="flash4", launcher="srun")
    params = dict(layout=lay, build=build, run=run,
                  input_dir="/shared/proj/sim_input")
    params.update(kw)
    return render_job_body(**params)


def test_job_body_stage_build_run_archive_order():
    txt = _body()
    i_stage = txt.find("# ── stage")
    i_build = txt.find("# ── build")
    i_run = txt.find("# ── run")
    i_arch = txt.find("# ── 归档")
    assert -1 < i_stage < i_build < i_run < i_arch, "阶段顺序错"


def test_job_body_compiles_in_scratch_not_shared():
    txt = _body()
    assert 'cd "${FL_BUILD_DIR}"' in txt
    assert 'make -j"$FL_MAKE_JOBS"' in txt
    # ★ setup 的 objdir 必须是 scratch 变量，不是 shared 路径
    assert '-objdir="${FL_BUILD_DIR}"' in txt


def test_job_body_copies_eos_and_par_to_run_dir():
    txt = _body()
    assert "*.cn4" in txt and "${FL_RUN_DIR}" in txt
    assert "flash.par" in txt


def test_job_body_stage_only_moves_runtime_data():
    """★ stage 只能搬运行期数据（.cn4/.par），**不能搬 .F90**。

    理由：.F90 若进 objdir，setup 会 input() 提问 ⇒ 批处理里 EOFError
    （实测作业 4924789）。
    """
    txt = _body()
    stage = txt[txt.find("# ── stage"):txt.find("# ── build")]
    assert "*.cn4" in stage
    assert "*.F90" not in stage
    # ★ stage 落 run 目录（不是 objdir）
    assert "FL_RUN_DIR" in stage
    assert "FL_BUILD_DIR" not in stage


def test_job_body_setup_is_non_interactive():
    """★ setup 必须非交互（喂 Y），否则批处理里 EOFError。"""
    txt = _body()
    i_setup = txt.find("./setup -auto")
    line_start = txt.rfind("\n", 0, i_setup) + 1
    line = txt[line_start:txt.find("\n", i_setup)]
    assert "printf" in line and "| ./setup" in line
    # ★ 也要带 -parfile（setup 自己生成 flash.par）
    assert "-parfile=grid_rede.par" in txt


def test_job_body_prepares_simulation_main_before_setup():
    """★ setup 读 SimulationMain ⇒ 源文件拷贝必须排在 setup 之前。"""
    txt = _body()
    i_copy = txt.find("SimulationMain")
    i_setup = txt.find("./setup -auto")
    assert -1 < i_copy < i_setup


def test_job_body_runs_srun_with_ntasks():
    txt = _body()
    assert "srun -n 4 ./flash4" in txt


def test_job_body_archives_at_end():
    txt = _body()
    assert "shopt -u nullglob" in txt
    # ★ 归档段必须在最后（仿真跑完才归档）
    assert txt.find("# ── 归档") > txt.find("srun -n 4")
    # ★ 归档后要有计数回显（便于判成败）
    assert "归档" in txt[txt.find("# ── 归档"):]


def test_job_body_is_valid_bash(tmp_path):
    """★ 生成的作业体必须是合法 bash（语法错 ⇒ 作业秒退）。"""
    txt = _body()
    p = tmp_path / "job.sh"
    p.write_text(txt, encoding="utf-8", newline="\n")
    # ★ 从 stdin 喂给 bash -n（避免 Windows 路径转换问题）
    # ★ 用 bytes 输入（避免 Windows 文本模式把 \n 转成 \r\n）
    r = subprocess.run(["bash", "-n"], input=txt.encode("utf-8"),
                       capture_output=True)
    assert r.returncode == 0, f"bash -n 失败: {r.stderr.decode()}"


def test_full_sbatch_script_is_valid_bash(tmp_path):
    """★ 头 + 体合起来也必须合法。"""
    txt = _body()
    spec = SlurmJobSpec(name="flash_grad", script=txt,
                         partition="v5_192", nodes=1, ntasks=4,
                         time_limit="02:00:00", out_dir="/shared/logs")
    full = render_sbatch(spec, workdir="/shared/proj")
    p = tmp_path / "full.sh"
    p.write_text(full, encoding="utf-8", newline="\n")
    # ★ 从 stdin 喂给 bash -n（避免 Windows 路径转换问题）
    # ★ 用 bytes 输入（避免 Windows 文本模式把 \n 转成 \r\n）
    r = subprocess.run(["bash", "-n"], input=txt.encode("utf-8"),
                       capture_output=True)
    assert r.returncode == 0, f"bash -n 失败: {r.stderr.decode()}"
    assert "#SBATCH -o /shared/logs/flash_grad_%j.out" in full
    assert "#SBATCH --time=02:00:00" in full


# ── SlurmJobSpec 新字段 ───────────────────────────────────────

def test_slurm_spec_renders_new_directives():
    spec = SlurmJobSpec(name="j", script="true", partition="v5_192",
                         nodes=2, ntasks=16, cpus_per_task=4,
                         time_limit="01:30:00", mem_per_node="16G",
                         account="flash_ssh", qos="normal",
                         constraint="cpu", chdir="/tmp/work")
    txt = render_sbatch(spec, "/wk")
    assert "#SBATCH --cpus-per-task=4" in txt
    assert "#SBATCH --time=01:30:00" in txt
    assert "#SBATCH --mem-per-node=16G" in txt
    assert "#SBATCH --account=flash_ssh" in txt
    assert "#SBATCH --qos=normal" in txt
    assert "#SBATCH --constraint=cpu" in txt
    assert "#SBATCH --chdir=/tmp/work" in txt
    assert "\r" not in txt


def test_slurm_spec_out_dir_overrides_log_location():
    spec = SlurmJobSpec(name="j", script="true", out_dir="/logs")
    txt = render_sbatch(spec, "/wk")
    assert "#SBATCH -o /logs/j_%j.out" in txt
    assert "#SBATCH -o /wk/j_%j.out" not in txt


def test_render_resource_directives_helper():
    d = render_resource_directives(nodes=1, ntasks=4, partition="v5_192")
    assert "#SBATCH --nodes=1" in d
    assert "#SBATCH --partition=v5_192" in d
    assert all(x.startswith("#SBATCH ") for x in d)
