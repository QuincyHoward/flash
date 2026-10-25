#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""submit_sandwich.py — 超算上提交 sandwich 场景作业（登录节点预置 setup）。

★ 为什么需要这个（2026-10-26 超算实测）：
  FLASH 的 `setup` 在**登录节点**秒完（实测 SUCCESS + SETUP_RC=0），
  但在**计算节点**里执行会**永久挂起**（实测作业 4924531/4924535：
  RUNNING 17 分钟，objdir 一个文件都没生成）⇒ sbatch 脚本内不能跑 setup。

  ⇒ 本脚本在**登录节点**先跑 setup（生成 objdir/Makefile），
    再 sbatch 提交（脚本内只做 make + 运行）。

★ 同时统一两个 sandwich 场景的提交动作，避免各自漂移：
  · grad_dens_sandwich  : objdir = QC/object_grad_dens_sandwich_<RUN_ID>
  · thin_layer_sandwich_si : objdir = QC/object_grid_rede

用法:
  python deploy/hpc_deploy/submit_sandwich.py grad_dens_sandwich --run-id 000002
  python deploy/hpc_deploy/submit_sandwich.py thin_layer_sandwich_si
"""
from __future__ import annotations

import argparse
import os
import shlex
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]

#: 场景 → (sim_input 相对目录, objdir 名, setup 的 -auto 名)
SCENES = {
    "grad_dens_sandwich": (
        "flash/scenarios/public/sandwich/grad_dens_sandwich/sim_input",
        "object_grad_dens_sandwich_{run_id}",
        "QC/grad_dens_sandwich_{run_id}",
    ),
    "thin_layer_sandwich_si": (
        "flash/scenarios/public/sandwich/thin_layer_sandwich/sim_input_si",
        "object_grid_rede",
        "QC/grid_rede",
    ),
}

#: setup 公共参数（与各场景 submit_flash.sh 保持一致）
SETUP_COMMON = [
    "-1d", "+cartesian", "-nxb=16", "-maxblocks=2048",
    "+hdf5typeio", "species=cham,targ,poly",
    "+mtmmmt", "+laser", "+uhd3t", "+mgd", "mgd_meshgroups=10",
]


def sh(cmd: str, timeout: int = 3600) -> tuple[str, str, int]:
    """执行远端命令（单条，避免 shell 拆分坑）。"""
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
    ap.add_argument("--skip-setup", action="store_true")
    args = ap.parse_args()

    rel_sim_input, objdir_tpl, auto_tpl = SCENES[args.scene]
    objdir = objdir_tpl.format(run_id=args.run_id)
    auto = auto_tpl.format(run_id=args.run_id)

    out, err, rc = sh("printf '%s' \"$HOME\"", timeout=30)
    home = (out or "").strip()
    if not home.startswith("/"):
        print("[FATAL] 无法解析远端 $HOME", flush=True)
        return 1
    flash_home = args.flash_home or f"{home}/QC/FLASH/FLASH4.8"
    target_dir = f"{home}/PhySimX/PhySimX/simulation/flash/flash_sim"
    sim_input = f"{target_dir}/{rel_sim_input}"

    # ---- 1. 生成输入（登录节点）----
    print(f"[submit] 场景: {args.scene}  run_id={args.run_id}", flush=True)
    gen = ("cd {t} && module load python/3.10.8 >/dev/null 2>&1; "
           "export FLASH_VENV_DIR={t}/.venv-hpc-nce; export PYTHONUNBUFFERED=1; "
           ".venv-hpc-nce/bin/python {g} --force 2>&1 | tail -2").format(
        t=target_dir,
        g=("flash/scenarios/public/sandwich/grad_dens_sandwich/gen_flash_inputs.py"
           if args.scene == "grad_dens_sandwich"
           else "flash/scenarios/public/sandwich/thin_layer_sandwich/gen_flash_inputs.py"))
    out, err, rc = sh(gen, timeout=1800)
    print((out or "").strip()[-400:], flush=True)
    if rc != 0:
        print(f"[FATAL] 生成输入失败 rc={rc}\n{(err or '')[-600:]}", flush=True)
        return 1

    # ---- 2. setup（登录节点！计算节点会挂起）----
    if not args.skip_setup:
        setup_cmd = (
            "cd {f} && export PATH={imp}:$PATH && "
            "export LIBRARY_PATH={libs} && "
            "./setup -auto {a} {c} -objdir={o} 2>&1 | tail -6"
        ).format(
            f=flash_home,
            imp="/public1/soft/oneAPI/2022.1/mpi/latest/bin",
            libs=("/public1/soft/oneAPI/2022.1/mpi/latest/lib/release:"
                  "/public1/soft/oneAPI/2022.1/mpi/latest/lib"),
            a=shlex.quote(auto),
            c=" ".join(SETUP_COMMON),
            o=shlex.quote(f"QC/{objdir}"),
        )
        print("[submit] setup（登录节点）...", flush=True)
        out, err, rc = sh(setup_cmd, timeout=3600)
        print((out or "").strip()[-600:], flush=True)
        if "SUCCESS" not in (out or ""):
            print(f"[FATAL] setup 未成功（rc={rc}）\n{(err or '')[-600:]}", flush=True)
            return 1

    # ---- 3. sbatch 提交 ----
    sub = "cd {d} && sbatch submit_flash.sh {rid} 2>&1 | tail -2".format(
        d=sim_input, rid=args.run_id)
    print("[submit] sbatch ...", flush=True)
    out, err, rc = sh(sub, timeout=300)
    print((out or "").strip(), flush=True)
    if "Submitted batch job" not in (out or ""):
        print(f"[FATAL] 提交失败 rc={rc}\n{(err or '')[-600:]}", flush=True)
        return 1
    job = (out or "").strip().split()[-1]
    print(f"[submit] 作业号: {job}", flush=True)
    print(f"[submit] 轮询: sacct -j {job}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
