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

    # ---- 2. 拷源文件到 SimulationMain（登录节点！）----
    # ★ 顺序至关重要（2026-10-26 实测）：
    #   setup 会**读取** SimulationMain/<场景>/ 下的 Config/Makefile/*.F90
    #   来生成 objdir ⇒ 必须**先拷贝、再 setup**。
    #   反了（先 setup 后拷贝）⇒ setup 时源目录是空的 ⇒ objdir 里没有
    #   .F90 符号链接 ⇒ make 无从编译（实测 objdir 98 文件 / 零 .o，
    #   作业挂起 7 分钟零进展）。
    # ★ 拷完再 setup，且**都要在登录节点**做（计算节点会挂起）。
    copy_cmd = (
        'S={s}; mkdir -p "$S" && '
        'find {d} -maxdepth 1 -type f \\( -name "Config" -o -name "Makefile" '
        '-o -name "*.F90" -o -name "*.cn4" -o -name "*.par" \\) '
        '-exec cp -f {{}} "$S/" \\; && '
        'echo "  [copy] $(find "$S" -maxdepth 1 -type f | wc -l) 个文件 → $S"'
    ).format(s=f"{flash_home}/source/Simulation/SimulationMain/QC/{auto.split('/', 1)[-1]}",
             d=sim_input)
    print("[submit] 拷贝源文件到 SimulationMain（登录节点）...", flush=True)
    out, err, rc = sh(copy_cmd, timeout=900)
    print((out or "").strip()[-300:], flush=True)
    if rc != 0:
        print(f"[FATAL] 拷贝失败 rc={rc}\n{(err or '')[-600:]}", flush=True)
        return 1

    # ---- 3. setup + 编译（登录节点！）----
    # ★★ 为什么编译也放登录节点（2026-10-26 实测）：
    #   FLASH 的 `make` 第一步是 setup_depends.py —— 它用 os.walk 扫描
    #   1500+ 源文件生成 Makefile.Depend。实测该步骤在**计算节点**上
    #   **11 分钟不出 .o**（objdir 1748 条目但 .o 恒为 0），
    #   而在**登录节点**上**秒级完成**（Makefile.Depend 352 KB）。
    #   ★ 这与 grad 场景的成功记录一致：其二进制时间戳对应登录节点操作
    #     （01:27 生成，1550 个 .o + 13 MB 二进制）。
    #   ⇒ 登录节点做「拷贝 → setup → make」，sbatch 作业只负责**运行**。
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

        # 编译（登录节点；make -j7 与 grad 一致）
        print("[submit] 编译（登录节点，make -j7）...", flush=True)
        make_cmd = (
            "cd {o} && export PATH={imp}:$PATH && "
            "export LIBRARY_PATH={libs} && "
            "make -j7 2>&1 | tail -6; "
            "test -x {o}/flash4 && echo BUILD_OK || echo BUILD_FAIL"
        ).format(
            o=f"{flash_home}/QC/{objdir}",
            imp="/public1/soft/oneAPI/2022.1/mpi/latest/bin",
            libs=("/public1/soft/oneAPI/2022.1/mpi/latest/lib/release:"
                  "/public1/soft/oneAPI/2022.1/mpi/latest/lib"),
        )
        out, err, rc = sh(make_cmd, timeout=7200)
        print((out or "").strip()[-800:], flush=True)
        if "BUILD_OK" not in (out or ""):
            print(f"[FATAL] 编译失败 rc={rc}\n{(err or '')[-800:]}", flush=True)
            return 1

    # ---- 4. sbatch 提交 ----
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
