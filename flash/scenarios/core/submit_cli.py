# -*- coding: utf-8 -*-
"""submit_cli.py — 场景层「提交超算作业」命令（**场景声明 → 通用提交服务**）
════════════════════════════════════════════════════════════════════════════

★ 定位

    场景层：知道**场景**（输入在哪、FLASH 单元叫什么、要传哪些 setup 参数）
    执行层：知道**怎么提交**（渲染/落盘/sbatch）
    ⇒ 本模块是两者之间的**薄胶水**，不含任何提交实现细节。

★ 两种驱动形态

    hpc-insitu  驱动脚本**已在超算登录节点** → 用 LocalExecutor（绝不 SSH 自连）
    hpc-remote  本机驱动 → 用 SSHExecutor（凭据名 flash_ssh）

    判据：`sbatch` 在本机可用 ⇒ 就地；否则 ⇒ 走 SSH。

★ 用法

    python -m flash.scenarios.core.cli submit grad_dens_sandwich --run-id 000002
    python -m flash.scenarios.core.cli submit thin_layer_sandwich_si --ntasks 16
    python -m flash.scenarios.core.cli submit grad_dens_sandwich --dry-run
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Optional

from flash.flash_run.env.devices import credential_name
from flash.scenarios.core.hpc_job import get_scene_hpc_job


# ── 路径解析 ────────────────────────────────────────────────────────

def repo_root() -> Path:
    """仓库根（含 pyproject.toml + start_flash.py）。"""
    here = Path(__file__).resolve()
    for cand in [here, *here.parents]:
        if (cand / "pyproject.toml").is_file() and (cand / "start_flash.py").is_file():
            return cand
    raise RuntimeError("无法定位仓库根（需含 pyproject.toml 与 start_flash.py）")


# ── 远端根（部署树）────────────────────────────────────────────────

#: 超算上的部署树根（相对 $HOME）。
#:
#: ★ 这是**部署拓扑**（代码落在超算哪里），属执行/部署层常量，
#:   不是场景信息 ⇒ 放这里；可用环境变量 `FLASH_HPC_ROOT` 覆盖。
DEFAULT_REMOTE_ROOT = "PhySimX/PhySimX/simulation/flash/flash_sim"


def remote_root() -> str:
    """超算部署树根（绝对路径形式，用 $HOME 表达）。"""
    override = os.environ.get("FLASH_HPC_ROOT", "").strip()
    if override:
        return override
    return f"$HOME/{DEFAULT_REMOTE_ROOT}"


# ── 提交 ───────────────────────────────────────────────────────────

# ── 运行期环境块（装置事实只从 devices 取）─────────────────────────

def build_env_block(profile: str, flash_home: str) -> str:
    """按场景声明的环境档渲染运行前导出块。

    Profiles:
      ``nce_qc_flash_sim``  公开场景（flash_sim QC 树, srun + Intel 2018 MPI）。
      ``flash_home_hdf5``   FLASHSNB 档：禁 module purge/load（t001 实测铁律
                            —— 任何 module 都会污染 MPI/HDF5 隐式路径），
                            只补 FLASH 树 Makefile.h 指定的 HDF5 运行库。
    """
    if profile == "nce_qc_flash_sim":
        # ★ 装置事实只从 devices 取（函数内延迟 import，R-LAYER-02a）
        from flash.flash_run.env.devices import INTEL2018_MPI_BIN, runtime_lib_dirs
        return "\n".join([
            "# 运行期环境（禁 mpich 模块：它带 Intel 2018 MPI，会与 oneAPI",
            "# 2022.1 编译产物版本不匹配 ⇒ MPI_Init SIGSEGV）",
            "module purge >/dev/null 2>&1",
            "module load hdf5/1.8.18 >/dev/null 2>&1",
            f'export LD_LIBRARY_PATH="{":".join(runtime_lib_dirs())}"',
            f'export PATH="{INTEL2018_MPI_BIN}:$PATH"',
        ])
    if profile == "flash_home_hdf5":
        return "\n".join([
            "# 运行期环境（flash_home_hdf5 档）：禁 module purge/load ——",
            "# t001 实测铁律：任何 module 都会污染 MPI/HDF5 隐式库路径；",
            "# 只补 FLASH 树 Makefile.h 指定的 HDF5 运行库",
            f'export FLASH_HOME="{flash_home}"',
            'H5LIB=$(grep -E "^HDF5_PATH[[:space:]]*=" "$FLASH_HOME/Makefile.h" '
            '2>/dev/null | head -1 | sed "s/^HDF5_PATH[[:space:]]*=[[:space:]]*//")',
            '[ -n "$H5LIB" ] && export LD_LIBRARY_PATH="$H5LIB/lib:${LD_LIBRARY_PATH:-}"',
        ])
    raise ValueError(f"未知 env_profile: {profile!r}")


def build_request(scene: str, run_id: str, ntasks: int, nodes: int,
                  cpus_per_task: int, time_limit: str, mem_per_node: str,
                  account: str, partition: str, flash_home: str,
                  shared_root: str, scratch_root: str, scratch_prefix: str,
                  launcher: str = "srun"):
    """组装 `JobRequest`（场景声明 → 通用请求）。"""
    from flash.flash_run.remote.job_layout import JobLayout, ResourceSpec
    from flash.flash_run.remote.job_submit import JobRequest
    from flash.flash_run.env.devices import INTEL2018_MPI_BIN, device_default, partition as default_partition, runtime_lib_dirs

    decl = get_scene_hpc_job(scene)

    layout = JobLayout(
        scratch_root=scratch_root or "/tmp",
        shared_root=shared_root,
        scratch_prefix=scratch_prefix or "flash_${SLURM_JOB_ID:-$$}",
        build_dir=f"flash_build_{scene}_{run_id}",
        run_dir=f"flash_run_{scene}_{run_id}",
        output_dir=f"flash_output/{scene}/{run_id}",
        log_dir=f"flash_logs/{scene}/{run_id}",
    )
    resource = ResourceSpec(
        nodes=nodes,
        ntasks=ntasks,
        cpus_per_task=cpus_per_task,
        time_limit=time_limit,
        mem_per_node=mem_per_node,
        account=account or device_default("account"),
        partition=partition or default_partition(),
    )
    env_block = build_env_block(decl.env_profile, flash_home)
    return JobRequest(
        name=f"flash_{scene}",
        flash_home=flash_home,
        unit=decl.unit_for(run_id),
        setup_args=decl.setup_args(),
        par_file=decl.par_file,
        source_dir=f"{shared_root}/{decl.input_rel_dir}",
        layout=layout,
        resource=resource,
        ntasks=ntasks,
        env_block=env_block,
        launcher=launcher,
        archive_patterns=tuple(decl.archive_patterns),
        pre_build_targets=tuple(decl.pre_build_targets),
        make_jobs_max=decl.make_jobs_max,
    )


def _executor():
    """按本机是否具备 sbatch 选执行器（就地 vs SSH）。

    ★ hpc-insitu 铁律：**绝不 SSH 自连** —— 已在超算上时直接 subprocess。
    """
    from flash.flash_run.env.devices import credential_name
    from flash.flash_run.remote.executors import LocalExecutor, SSHExecutor

    if shutil.which("sbatch"):
        return LocalExecutor(), "local(insitu)"
    return SSHExecutor(credential=credential_name()), "ssh(remote)"

def _remote_capture(cmd: str, timeout: int = 60) -> str:
    """在超算上执行命令并**取回 stdout**（就地优先，否则 SSH）。"""
    import subprocess

    if shutil.which("sbatch"):
        r = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=timeout)
        return (r.stdout or "").strip()

    from flash.flash_run.remote.session import RemoteSession
    with RemoteSession(credential_name()) as s:
        out, _err, _rc = s.run(cmd, timeout=timeout)
    return (out or "").strip()


def _run_remote_cmd(cmd: str, timeout: int = 1800) -> int:
    """在超算上执行一条命令（就地优先，否则 SSH）。

    返回 rc；输出直接打印。
    """
    import subprocess

    if shutil.which("sbatch"):
        r = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=timeout)
        print((r.stdout or "").strip()[-2000:], flush=True)
        if r.stderr:
            print((r.stderr or "").strip()[-1000:], file=sys.stderr, flush=True)
        return r.returncode

    from flash.flash_run.remote.session import RemoteSession
    with RemoteSession(credential_name()) as s:
        out, err, rc = s.run(cmd, timeout=timeout)
    print((out or "").strip()[-2000:], flush=True)
    if err:
        print((err or "").strip()[-1000:], file=sys.stderr, flush=True)
    return rc


def _generate_inputs_local(decl, repo: Path) -> Path:
    """本地跑输入生成脚本（local_upload 档）。

    返回本地输入目录。生成脚本自带静态核验（材料绑定 / radON 驱动断言 /
    精确网格三重断言），任一失败即非零退出。
    """
    from flash.flash_run.modes.runner import resolve_venv_python

    script = repo / decl.gen_script
    if not script.is_file():
        raise FileNotFoundError(f"生成脚本不存在: {script}")
    venv_py = resolve_venv_python()
    cmd = [str(venv_py or Path(sys.executable)), str(script), *decl.gen_args]
    print(f"[submit] 本地生成: {' '.join(cmd[1:])}", flush=True)
    r = subprocess.run(cmd, cwd=str(repo))
    if r.returncode != 0:
        raise RuntimeError(f"本地输入生成失败 rc={r.returncode}")
    input_dir = repo / decl.input_rel_dir
    if not (input_dir / decl.par_file).is_file():
        raise RuntimeError(f"生成产物缺 par: {input_dir / decl.par_file}")
    return input_dir


def _upload_inputs(decl, input_dir: Path, source_dir: str) -> int:
    """SFTP 上传输入目录全部文件到共享盘 source_dir（返回上传数）。

    ★ paramiko SFTP 不展开 ``~`` ⇒ source_dir 必须已是绝对路径
      （main 已把 $HOME 解析为远端绝对路径）。
    """
    from flash.flash_run.env.devices import credential_name
    from flash.flash_run.remote.session import RemoteSession

    files = sorted(p for p in input_dir.iterdir() if p.is_file())
    if not files:
        raise RuntimeError(f"输入目录为空: {input_dir}")
    with RemoteSession(credential_name(), verbose=True) as s:
        s.run(f"mkdir -p {source_dir}", timeout=60)
        n = 0
        for f in files:
            if s.upload(str(f), f"{source_dir}/{f.name}"):
                n += 1
            else:
                raise RuntimeError(f"上传失败: {f.name}")
        out, _err, _rc = s.run(f"ls -1 {source_dir} | wc -l", timeout=60)
    print(f"[submit] 输入已上传 {n}/{len(files)} 个文件 → {source_dir} "
          f"(远端现存 {out.strip()})", flush=True)
    return n


def main(argv: Optional[list] = None) -> int:
    ap = argparse.ArgumentParser(
        prog="python -m flash.scenarios.core.cli submit",
        description="提交场景到超算（作业内完成 stage→编译→运行→归档）")
    ap.add_argument("scene")
    ap.add_argument("--run-id", default="000001")
    ap.add_argument("--ntasks", type=int, default=None,
                    help="MPI rank 数（默认取场景声明；必须 ≤ nblockx）")
    ap.add_argument("--nodes", type=int, default=None,
                    help="节点数（默认取场景声明）")
    ap.add_argument("--launcher", default=None,
                    help="运行期启动器（默认取场景声明: srun/mpiexec）")
    ap.add_argument("--cpus-per-task", type=int, default=1)
    ap.add_argument("--time-limit", default=None)
    ap.add_argument("--mem-per-node", default="")
    ap.add_argument("--account", default="")
    ap.add_argument("--partition", default="")
    ap.add_argument("--flash-home", default="",
                    help="FLASH 根目录（默认 $HOME/<user>/FLASH/FLASH4.8）")
    ap.add_argument("--scratch-root", default="",
                    help="节点本地 scratch 根（默认作业内自动探测 tmpfs）")
    ap.add_argument("--scratch-prefix", default="",
                    help="scratch 下的作业专属子目录名（默认含 ${SLURM_JOB_ID}）")
    ap.add_argument("--tmax", default=None,
                    help="仿真结束时间 [s]（仅 local_upload 档生效：附加给"
                         "生成脚本 --tmax，如 2.4e-9；缺省用场景内置值）")
    ap.add_argument("--shared-root", default="",
                    help="共享并行盘根（默认超算部署树）")
    ap.add_argument("--dry-run", action="store_true",
                    help="只渲染作业脚本，不落盘不提交")
    args = ap.parse_args(argv)

    decl = get_scene_hpc_job(args.scene)
    ntasks = args.ntasks or decl.ntasks
    nodes = args.nodes or decl.nodes
    launcher = args.launcher or decl.launcher
    time_limit = args.time_limit or decl.time_limit

    # ① 共享根 + FLASH 根（默认含 $HOME ⇒ 必须先解析成绝对路径：
    #    远端 SFTP 不展开 `~`/`$HOME`，作业脚本里也只有展开后才可用）
    shared_root = args.shared_root or remote_root()
    flash_home = args.flash_home or decl.flash_home_default

    if "$HOME" in shared_root or "$HOME" in flash_home:
        home = _remote_capture("printf '%s' \"$HOME\"", timeout=60)
        if not home.startswith("/"):
            print(f"[FATAL] 无法解析远端 $HOME（得到 {home!r}）", file=sys.stderr)
            return 1
        shared_root = shared_root.replace("$HOME", home)
        flash_home = flash_home.replace("$HOME", home)

    # ② 生成输入（gen_mode 声明决定：远端生成 vs 本地生成+上传）
    if not args.dry_run:
        print(f"[submit] 场景={args.scene} run_id={args.run_id} "
              f"ntasks={ntasks} nodes={nodes} launcher={launcher}", flush=True)
        if decl.gen_mode == "local_upload":
            # SNB 族：覆盖 F90 不入库 ⇒ 远端树缺 snb_package 镜像，
            # 只有本地（含 radON 断言 + 静态核验）能完整生成 → 上传。
            gen_args = list(decl.gen_args)
            if args.tmax:
                gen_args += ["--tmax", args.tmax]
            decl = replace(decl, gen_args=tuple(gen_args))  # dataclass 副本
            source_dir_abs = f"{shared_root}/{decl.input_rel_dir}"
            input_dir = _generate_inputs_local(decl, repo_root())
            _upload_inputs(decl, input_dir, source_dir_abs)
        else:
            gen = ("cd {t} && module load python/3.10.8 >/dev/null 2>&1; "
                   "export FLASH_VENV_DIR={t}/.venv-hpc-nce; export PYTHONUNBUFFERED=1; "
                   ".venv-hpc-nce/bin/python {g} --force 2>&1 | tail -2").format(
                t=shared_root, g=decl.gen_script)
            rc = _run_remote_cmd(gen, timeout=1800)
            if rc != 0:
                print(f"[FATAL] 生成输入失败 rc={rc}", file=sys.stderr)
                return 1

    # ③ 组装请求 + 提交
    req = build_request(
        scene=args.scene, run_id=args.run_id, ntasks=ntasks,
        nodes=nodes, cpus_per_task=args.cpus_per_task,
        time_limit=time_limit, mem_per_node=args.mem_per_node,
        account=args.account, partition=args.partition,
        flash_home=flash_home, shared_root=shared_root,
        scratch_root=args.scratch_root, scratch_prefix=args.scratch_prefix,
        launcher=launcher)

    from flash.flash_run.remote.job_submit import render_job, submit_job

    if args.dry_run:
        rendered = render_job(req)
        print(rendered.script_text)
        print(f"[dry-run] 脚本路径: {rendered.script_path}")
        print(f"[dry-run] 产物目录: {rendered.output_dir}")
        return 0

    exe, mode = _executor()
    res = submit_job(req, executor=exe)
    if not res["ok"]:
        print(f"[FATAL] 提交失败: {res['reason']}", file=sys.stderr)
        return 1
    print(f"[submit] 驱动方式: {mode}")
    print(f"[submit] 作业号: {res['job_id']}")
    print(f"[submit] 日志: {res['log_dir']}/{res['job_name']}_{res['job_id']}.out")
    print(f"[submit] 产物: {res['output_dir']}")
    print(f"[submit] 轮询: sacct -j {res['job_id']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
