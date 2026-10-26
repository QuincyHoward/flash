#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""submit_sandwich.py — 超算上提交 sandwich 场景作业（作业内全流程）。

★ 2026-10-26 重写（用户质疑"这不是铁律"后复核实测）：
  上一版把「setup 与 make 必须在登录节点」当成铁律，据此把编译放在登录节点。
  **计算节点实测证伪**（作业 4924747/4924748/4924752/4924760）：

    · GPFS 上 os.walk 2811 文件 = 0.2 s、500 符号链接 = 1.08 s ⇒ 元数据不慢
    · setup_depends.py = 21.7 s ⇒ 不是"11 分钟不出 .o"
    · 计算节点上 `setup` = SUCCESS（2 s）⇒ 不是"永久挂起"
    · **计算节点 scratch 上 setup 2 s + make -j16 31 s + 运行 299 s
      + 归档 0 s ⇒ 全流程 COMPLETED（5:33）**

  ⇒ 真正的规律不是"只能在登录节点编译"，而是
    **别把编译中间产物写在慢速共享盘上**。
  ⇒ 本脚本改为：登录节点只做「生成输入 + 渲染作业 + 提交」，
    **编译、运行、归档全部在计算节点的节点本地 scratch 内完成**
    ⇒ 计算节点的 CPU/内存被完整利用，登录节点不再被长时间占用。

★ 目录拓扑（flash.flash_run.remote.job_layout）
    scratch（节点本地 tmpfs）：编译 objdir + 运行工作目录
    shared（共享并行盘）    ：输入源 + 最终产物 + 作业日志

用法:
  python deploy/hpc_deploy/submit_sandwich.py grad_dens_sandwich --run-id 000002
  python deploy/hpc_deploy/submit_sandwich.py thin_layer_sandwich_si
  python deploy/hpc_deploy/submit_sandwich.py grad_dens_sandwich --ntasks 16
"""
from __future__ import annotations

import argparse
import shlex
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

#: 场景 → (sim_input 相对目录, FLASH 场景单元名, par 文件名)
SCENES = {
    "grad_dens_sandwich": (
        "flash/scenarios/public/sandwich/grad_dens_sandwich/sim_input",
        "QC/grad_dens_sandwich_{run_id}",
        "grid_rede.par",
    ),
    "thin_layer_sandwich_si": (
        "flash/scenarios/public/sandwich/thin_layer_sandwich/sim_input_si",
        "QC/grid_rede",
        "grid_rede.par",
    ),
}

#: setup 公共参数（与各场景 submit_flash.sh 保持一致）
SETUP_COMMON = [
    "-1d", "+cartesian", "-nxb=16", "-maxblocks=2048",
    "+hdf5typeio", "species=cham,targ,poly",
    "+mtmmmt", "+laser", "+uhd3t", "+mgd", "mgd_meshgroups=10",
]

#: 追加的 setup 参数（按场景）
SETUP_EXTRA = {
    "grad_dens_sandwich": ["ed_maxPulseSections=240"],
    "thin_layer_sandwich_si": [],
}

#: 生成输入的脚本（相对 flash_sim 根）
GEN_SCRIPT = {
    "grad_dens_sandwich":
        "flash/scenarios/public/sandwich/grad_dens_sandwich/gen_flash_inputs.py",
    "thin_layer_sandwich_si":
        "flash/scenarios/public/sandwich/thin_layer_sandwich/gen_flash_inputs.py",
}


def sh(cmd: str, timeout: int = 3600) -> tuple[str, str, int]:
    """执行命令 —— **就地优先**，不在超算上时回退 SSH。

    ★ 关键（架构一致性）：本脚本既可在**本机**跑（经 SSH 驱动超算），
      也可直接在**超算登录节点**跑。hpc-insitu 的铁律是「绝不 SSH 自连」
      ⇒ 在超算上必须走就地 subprocess，否则会因缺凭据直接失败
      （实测："凭据未找到: flash_ssh"）。

    判据：能否 import 到本机的 flash 包且 `sbatch` 可用 ⇒ 就地执行。
    """
    import shutil
    import subprocess

    if shutil.which("sbatch"):
        # 就地（超算登录节点）：直接 subprocess，不碰 SSH
        r = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=timeout)
        return (r.stdout or ""), (r.stderr or ""), r.returncode

    from flash.flash_run.remote.session import RemoteSession
    with RemoteSession("flash_ssh") as s:
        out, err, rc = s.run(cmd, timeout=timeout)
    return (out or ""), (err or ""), rc


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("scene", choices=list(SCENES))
    ap.add_argument("--run-id", default="000001")
    ap.add_argument("--flash-home", default=None,
                    help="FLASH 根目录（默认 $HOME/QC/FLASH/FLASH4.8）")
    ap.add_argument("--ntasks", type=int, default=4,
                    help="MPI rank 数（必须 ≤ nblockx=16）")
    ap.add_argument("--nodes", type=int, default=1)
    ap.add_argument("--cpus-per-task", type=int, default=1)
    ap.add_argument("--time-limit", default="02:00:00")
    ap.add_argument("--mem-per-node", default="")
    ap.add_argument("--partition", default="")
    ap.add_argument("--account", default="")
    ap.add_argument("--scratch-root", default="",
                    help="节点本地 scratch 根（默认作业内自动探测 tmpfs）")
    ap.add_argument("--scratch-prefix", default="",
                    help="scratch 下的作业专属子目录名"
                         "（默认含 ${SLURM_JOB_ID} ⇒ 并发隔离）")
    ap.add_argument("--shared-root", default="",
                    help="共享并行盘根（默认 flash_sim 根目录）")
    args = ap.parse_args()

    from flash.flash_run.env.devices import (
        INTEL2018_MPI_BIN, partition, runtime_lib_dirs,
    )
    from flash.flash_run.remote.job_layout import JobLayout, ResourceSpec
    from flash.flash_run.remote.job_scripts import BuildSpec, RunSpec, render_job_body
    from flash.flash_run.remote.slurm_control import render_sbatch, SlurmJobSpec

    rel_sim_input, unit_tpl, par_file = SCENES[args.scene]
    unit = unit_tpl.format(run_id=args.run_id)

    out, err, rc = sh("printf '%s' \"$HOME\"", timeout=30)
    home = (out or "").strip()
    if not home.startswith("/"):
        print("[FATAL] 无法解析远端 $HOME", flush=True)
        return 1
    flash_home = args.flash_home or f"{home}/QC/FLASH/FLASH4.8"
    target_dir = f"{home}/PhySimX/PhySimX/simulation/flash/flash_sim"
    sim_input = f"{target_dir}/{rel_sim_input}"
    shared_root = args.shared_root or target_dir

    # ---- 1. 生成输入（登录节点，轻量）----
    print(f"[submit] 场景: {args.scene}  run_id={args.run_id}", flush=True)
    gen = ("cd {t} && module load python/3.10.8 >/dev/null 2>&1; "
           "export FLASH_VENV_DIR={t}/.venv-hpc-nce; export PYTHONUNBUFFERED=1; "
           ".venv-hpc-nce/bin/python {g} --force 2>&1 | tail -2").format(
        t=target_dir, g=GEN_SCRIPT[args.scene])
    out, err, rc = sh(gen, timeout=1800)
    print((out or "").strip()[-400:], flush=True)
    if rc != 0:
        print(f"[FATAL] 生成输入失败 rc={rc}\n{(err or '')[-600:]}", flush=True)
        return 1

    # ---- 2. 构造目录拓扑 ----
    # ★ scratch 用**节点本地 tmpfs**（作业内再按文件系统类型复核），
    #   shared 用**共享并行盘**（输入/产物/日志，跨节点可见）。
    #   scratch_prefix 含 ${SLURM_JOB_ID} ⇒ 并发作业互不干扰。
    layout = JobLayout(
        scratch_root=args.scratch_root or "/tmp",
        shared_root=shared_root,
        scratch_prefix=args.scratch_prefix
        or "flash_${SLURM_JOB_ID:-$$}",
        build_dir=f"flash_build_{args.scene}_{args.run_id}",
        run_dir=f"flash_run_{args.scene}_{args.run_id}",
        output_dir=f"flash_output/{args.scene}/{args.run_id}",
        log_dir=f"flash_logs/{args.scene}/{args.run_id}",
    )

    # ---- 3. 渲染作业体（编译 + 运行 + 归档，全在计算节点）----
    build = BuildSpec(
        flash_home=flash_home,
        unit=unit,
        setup_args=[*SETUP_COMMON, *SETUP_EXTRA[args.scene]],
        par_file=par_file,
        bin_name="flash4",
        source_dir=sim_input,
    )
    run = RunSpec(
        ntasks=args.ntasks,
        binary="flash4",
        launcher="srun",
        env_block="\n".join([
            "# 运行期环境（禁 mpich 模块：它带 Intel 2018 MPI，会与本场景",
            "# 的 2022.1 编译产物版本不匹配 ⇒ MPI_Init SIGSEGV）",
            "module purge >/dev/null 2>&1",
            "module load hdf5/1.8.18 >/dev/null 2>&1",
            f'export LD_LIBRARY_PATH="{":".join(runtime_lib_dirs())}"',
            f'export PATH="{INTEL2018_MPI_BIN}:$PATH"',
        ]),
    )
    body = render_job_body(
        layout,
        build=build,
        run=run,
        input_dir=sim_input,
        archive_patterns=("*chk*",),
    )

    # ---- 4. 渲染 sbatch 头 ----
    res = ResourceSpec(
        nodes=args.nodes,
        ntasks=args.ntasks,
        cpus_per_task=args.cpus_per_task,
        time_limit=args.time_limit,
        mem_per_node=args.mem_per_node,
        account=args.account,
        partition=args.partition or partition(),
    )
    spec = SlurmJobSpec(
        name=f"flash_{args.scene}",
        script=body,
        partition=res.partition,
        nodes=res.nodes,
        ntasks=res.ntasks,
        cpus_per_task=res.cpus_per_task,
        time_limit=res.time_limit,
        mem_per_node=res.mem_per_node,
        account=res.account,
        marker="FLASH_JOB_DONE",
        out_dir=f"{shared_root}/{layout.log_dir}",
        timeout=7200,
    )
    script_text = render_sbatch(spec, workdir=shared_root)

    # ---- 5. 落盘 + 提交（登录节点只做这件事）----
    job_dir = f"{shared_root}/{layout.log_dir}"
    script_path = f"{job_dir}/job_{args.scene}_{args.run_id}.sh"
    write = (
        'mkdir -p {d} && cat > {p} << "FLASH_JOB_EOF"\n{s}FLASH_JOB_EOF\n'
        "sed -i 's/\\r$//' {p}; chmod +x {p}; echo WROTE {p}"
    ).format(d=job_dir, p=script_path, s=script_text)
    out, err, rc = sh(write, timeout=300)
    print((out or "").strip()[-300:], flush=True)
    if "WROTE" not in (out or ""):
        print(f"[FATAL] 作业脚本落盘失败 rc={rc}\n{(err or '')[-600:]}", flush=True)
        return 1

    sub = "cd {d} && sbatch {p} 2>&1 | tail -2".format(d=job_dir, p=script_path)
    print("[submit] sbatch ...", flush=True)
    out, err, rc = sh(sub, timeout=300)
    print((out or "").strip(), flush=True)
    if "Submitted batch job" not in (out or ""):
        print(f"[FATAL] 提交失败 rc={rc}\n{(err or '')[-600:]}", flush=True)
        return 1
    job = (out or "").strip().split()[-1]
    print(f"[submit] 作业号: {job}", flush=True)
    print(f"[submit] 日志: {job_dir}/flash_{args.scene}_{job}.out", flush=True)
    print(f"[submit] 产物: {shared_root}/{layout.output_dir}", flush=True)
    print(f"[submit] 轮询: sacct -j {job}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
