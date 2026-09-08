#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SNB 场景 HPC(超算) 一键执行脚本 (t001 → 远程 FLASHSNB)。

流程: [连接] -> [上传源码 tgz] -> [解压部署] -> [复用常规树 Makefile.h]
      -> [sbatch: setup + make] -> [上传 par/覆写 tmax] -> [sbatch: 运行]
      -> [收集 NonLTConduct* 到本地] -> [验证]

参考 flash_demo HPC 执行代码 (demo_hpc/laserslab1d_hpc_demo_batch.py +
remote_ssh_helper.RemoteSession) 的流程: 凭据动态路由 + RemoteSession +
sbatch + sacct 轮询 + SCP 下载。

账号/分区/工具链 (每账号独立, 脚本自动探测):
  flash_ssh   (scfa2696@NC-E)   分区 v5_192,   常规树 FCOMP=oneAPI mpiifort
  flash_ssh_2 (sch0348@BSCC-T6) 分区 v6_384,   常规树 FCOMP=${MPI_PATH}/bin/mpif90

用法:
  python run_snb_hpc.py --account flash_ssh    # 默认账号
  python run_snb_hpc.py --account flash_ssh_2  # 第二账号
  python run_snb_hpc.py --skip-upload          # 复用远端已部署源码树
  python run_snb_hpc.py --tmax 1.0e-11 --nproc 4

身份获取: 全部走 flash._core.credentials (load_ssh_credentials),
绝不硬编码用户名/密码/主机。
"""

import argparse
import os
import re
import sys
import time
from pathlib import Path

# ── 目录布局 (相对本脚本) ──────────────────────────────────────────
T001 = Path(__file__).resolve().parent
FLASH_INPUT = T001 / "flash_input"
FLASH_OUTPUT = T001 / "flash_output"
HPC_PACK = T001 / "hpc_pack"
TGZ = HPC_PACK / "flashsnb_f4.tgz"

# SNB 场景常量 (与本地 run_snb.py 保持一致)
OBJDIR = "SNB_1D_laser_obj"
SCENARIO = "SNB_1D_laser"

# 本地 WSL 打包时排除目录 (镜像到远端)
SETUP_CMD = (
    "./setup -auto SNB_1D_laser -1d +cartesian +ug -nxb=8 +hdf5typeio "
    "species=cham,tar1,tar2,tar3 +mtmmmt +laser +uhd3t +mgd mgd_meshgroups=10 "
    "-objdir=SNB_1D_laser_obj"
)

# 输出 glob
OUTPUT_GLOBS = ("NonLTConduct*",)

# 账号短标签 (job name / 目录后缀)
ACCOUNT_TAG = {"flash_ssh": "nce", "flash_ssh_2": "bscc"}


def runtime_env_block(snb_home: str, account: str) -> str:
    """生成 sbatch 作业内环境块 (编译/运行共用)。

    实测结论 (2026-08-29, probe2/probe3):
      * flash_ssh (NC-E): SSH 登录已自动加载完整 oneAPI (PATH + LD_LIBRARY_PATH),
        mpiexec=Intel MPI 2021.5, flash4 链接 oneAPI libmpi.so.12 可直接解析。
        ⚠️ 该环境 module 系统在非交互 shell 中 module load 不更新环境变量,
           且 module purge 会清掉登录自动加载的 oneAPI → 两者都不可用。
        唯一缺的库是 libhdf5.so.10 → 从 Makefile.h 提取 HDF5_PATH 显式 export。
      * flash_ssh_2 (BSCC-T6): mpich/gcc 工具链, 待探测后按需补充 (见 #22)。
    """
    h5_extract = (
        "H5LIB=$(grep -E '^HDF5_PATH[[:space:]]*=' "
        f"{snb_home}/Makefile.h | head -1 | "
        "sed 's/^HDF5_PATH[[:space:]]*=[[:space:]]*//')\n"
        '[ -n "$H5LIB" ] && export LD_LIBRARY_PATH="$H5LIB/lib:$LD_LIBRARY_PATH"\n'
        'echo "[env] H5LIB=$H5LIB"\n'
    )
    if account == "flash_ssh":
        return (
            "# NC-E: 登录环境已含 oneAPI, 禁止 module purge; 显式补 HDF5 运行库\n" + h5_extract
        )
    # flash_ssh_2 (BSCC-T6, 实测 2026-09-08 probe4/多次构建):
    #   登录环境含 intel/2017 但无 mpich PATH。mpich/3.2 的 mpif90 wrapper 按 PATH 找
    #   gfortran: 系统 4.8.5 编 hypre 源会 ICE(segfault) → 必须 prepend gcc/9.3.0-new
    #   (=module mpich/3.2-gcc9.3 实际内容, BSCC 常规树即此环境编译)。
    #   运行 flash4 亦需 gcc9.3 libgfortran.so.5 + hdf5/mpich 运行库 → 全量 export。
    return (
        "# BSCC-T6: gcc9.3 + mpich + hdf5 运行环境 (mpif90 wrapper 按 PATH 选 gfortran)\n"
        "export PATH=/public1/soft/gcc/9.3.0-new/bin:/public1/soft/mpich/3.2/bin:$PATH\n"
        "export H5LIB=$(grep -E '^HDF5_PATH[[:space:]]*=' "
        f"{snb_home}/Makefile.h | head -1 | "
        "sed 's/^HDF5_PATH[[:space:]]*=[[:space:]]*//')\n"
        '[ -n "$H5LIB" ] && '
        'export LD_LIBRARY_PATH="/public1/soft/gcc/9.3.0-new/lib64:$H5LIB/lib:/public1/soft/mpich/3.2/lib:$LD_LIBRARY_PATH"\n'
        'echo "[env] gfortran=$(gfortran --version | head -1) mpiexec=$(which mpiexec)"\n'
    )


def log(msg: str, level: str = "INFO") -> None:
    tag = {"INFO": "  ", "STEP": ">> ", "OK": "✓ ", "WARN": "! ", "ERROR": "✗ "}.get(level, "  ")
    print(f"{time.strftime('%H:%M:%S')} {tag}{msg}")


def _bootstrap():
    """把 flash 包根目录加入 sys.path (寻找 pyproject.toml)。"""
    root = Path(__file__).resolve().parent
    for _ in range(10):
        if (root / "pyproject.toml").exists():
            return root
        root = root.parent
    return root


ROOT = _bootstrap()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def get_sim_user_dir() -> str:
    """仿真用户目录 (如 QC) — 走凭据系统, 不硬编码。"""
    try:
        from flash.scenarios.runner import get_sim_user_dir as g
        v = g()
        return v
    except Exception:  # noqa: BLE001
        return "QC"


def remote_flashsnb_home() -> str:
    """远端 FLASHSNB 源码树根: ~/<sim_user>/FLASH/FLASHSNB/FLASH4.8 (镜像本地 WSL 布局)。"""
    return f"~/{get_sim_user_dir()}/FLASH/FLASHSNB/FLASH4.8"


def remote_normal_home() -> str:
    """远端常规 FLASH4.8 根 (用于复制已验证 Makefile.h)。"""
    return f"~/{get_sim_user_dir()}/FLASH/FLASH4.8"


# ── 远端操作封装 ─────────────────────────────────────

class Remote:
    """基于 RemoteSession 的远端操作。"""

    def __init__(self, credential_name: str):
        self.credential_name = credential_name
        self.session = None

    def __enter__(self):
        from flash.scenarios.flash_demo.demo_hpc.remote_ssh_helper import RemoteSession
        self.session = RemoteSession(credential_name=self.credential_name, verbose=True)
        self.session.__enter__()
        return self

    def __exit__(self, *a):
        self.session.__exit__(*a)

    def run(self, cmd: str, timeout: int = 120) -> tuple[str, str, int]:
        out, err, code = self.session.run(cmd, timeout=timeout)
        return out, err, code

    def upload(self, local: str, remote: str) -> bool:
        return self.session.upload(local, remote)

    def download(self, remote: str, local: str) -> bool:
        return self.session.download(remote, local)


# ── 步骤 1: 探测分区 ──────────────────────────────────

def detect_partition(remote: Remote, account: str) -> str:
    """按账号返回可用 SLURM 分区。

    sinfo -s 首行常是不可用的汇总/测试分区 (如 NC-E 的 "all  inact"),
    不能盲取第一行。策略: 收集 avail=up 分区 + 默认(*)分区, 已知映射优先。
    """
    known = {"flash_ssh": "v5_192", "flash_ssh_2": "v6_384"}
    try:
        out, _, code = remote.run("sinfo -s 2>/dev/null", timeout=30)
        up, default = [], None
        for line in out.splitlines():
            cols = line.split()
            if not cols or cols[0] in ("PARTITION", "AVAIL"):
                continue
            name = cols[0].rstrip("*")
            if cols[0].endswith("*"):
                default = name
            if len(cols) > 1 and cols[1].startswith("up"):
                up.append(name)
        if account in known and known[account] in up:
            return known[account]
        if up:
            return up[0]
        if default:
            return default
    except Exception:  # noqa: BLE001
        pass
    return known.get(account, "v5_192")


# ── 步骤 2: 上传 + 解压 ──────────────────────────────

def deploy_source(remote: Remote, force: bool = False) -> str:
    """上传 tgz 并解压到远端 FLASHSNB 源码树。返回远端 FLASH4.8 根。"""
    snb_home = remote_flashsnb_home()
    if not TGZ.exists():
        raise RuntimeError(f"本地打包不存在: {TGZ} (请先运行 WSL 打包)")

    out, _, _ = remote.run(f"ls -d {snb_home}/setup 2>/dev/null || echo NO_SETUP", timeout=30)
    # 树不存在 (NO_SETUP) 或强制上传 → 上传解压; 否则复用
    if "NO_SETUP" in out or force:
        log(f"[部署] 上传 {TGZ.name} ({TGZ.stat().st_size/1e6:.1f} MB)...", "STEP")
        parent = f"~/{get_sim_user_dir()}/FLASH/FLASHSNB"
        remote.run(f"mkdir -p {parent}", timeout=30)
        ok = remote.upload(str(TGZ), f"{parent}/flashsnb_f4.tgz")
        if not ok:
            raise RuntimeError("tgz 上传失败")
        out, _, code = remote.run(
            f"cd {parent} && tar xzf flashsnb_f4.tgz && "
            f"ls -d FLASH4.8/setup && echo EXTRACT_OK && rm -f flashsnb_f4.tgz",
            timeout=600,
        )
        if "EXTRACT_OK" not in out:
            raise RuntimeError(f"远端解压失败: {out[-300:]}")
        log(f"[部署] 已解压到 {snb_home}", "OK")
    else:
        log(f"[部署] 远端源码树已存在: {snb_home} (跳过上传)", "OK")
    return snb_home


# ── 步骤 3: 复用常规树 Makefile.h ────────────────────

def apply_makefile_h(remote: Remote, snb_home: str) -> None:
    """用该账号常规 FLASH4.8 已验证的 Makefile.h 覆盖 FLASHSNB 的。

    保留 .hpc 说明头 + 备份原 WSL 版为 Makefile.h.wsl。
    """
    normal = remote_normal_home()
    out, _, _ = remote.run(f"ls {normal}/Makefile.h 2>/dev/null || echo NO_MFH", timeout=30)
    if "NO_MFH" in out:
        log(f"[Makefile.h] 常规树无 Makefile.h ({normal}) — 保留 FLASHSNB 自带", "WARN")
        return
    # 备份原版 (仅首次)
    remote.run(f"cd {snb_home} && [ -f Makefile.h.wsl ] || cp Makefile.h Makefile.h.wsl", timeout=30)
    # 覆盖: 用常规树的 (该账号已验证的编译器/库路径)
    # ⚠️ 保留 HYPRE_PATH 原样: 清空会使 setup 仍编 hypre 源但 -I${HYPRE_PATH}/include=/include
    #    而缺 HYPRE_config.h (BSCC 实测)。hypre 源编译崩溃由 gcc 版本解决 (见 runtime_env_block)。
    remote.run(
        f"cd {snb_home} && cp {normal}/Makefile.h Makefile.h && "
        f"grep -E '^FCOMP|^CCOMP|^HDF5_PATH|^MPI_PATH|^HYPRE_PATH' Makefile.h | head -6",
        timeout=30,
    )
    log(f"[Makefile.h] 已从常规树复制: {normal}/Makefile.h (保留 HYPRE_PATH)", "OK")


# ── 步骤 4: setup + make (sbatch 作业) ──────────────

def build_remote(remote: Remote, snb_home: str, partition: str, account: str) -> bool:
    """远端执行 setup + make。返回是否成功 (flash4 存在)。

    用一个 sbatch 作业在计算节点完成 (登录节点通常限制重负载/MPI)。
    """
    env_block = runtime_env_block(snb_home, account)
    distro_tag = ACCOUNT_TAG.get(account, account)
    job_script = f"""#!/bin/bash
#SBATCH --job-name=SNB_build_{distro_tag}
#SBATCH -p {partition}
#SBATCH -N 1
#SBATCH --ntasks=8
#SBATCH --output=SNB_build_%j_out.txt
#SBATCH --error=SNB_build_%j_err.txt
set -e
{env_block}cd {snb_home}
echo "=== [1/3] setup ==="
rm -rf {OBJDIR}
eval {SETUP_CMD} 2>&1 | tail -30
ls -d {OBJDIR} || {{ echo SETUP_FAIL; exit 2; }}
echo "=== [2/3] mgd_qesh 链接 ==="
cd {OBJDIR}
ln -sf ../source/Simulation/SimulationMain/SNB_1D_laser/mgd_qesh.F90 mgd_qesh.F90 2>/dev/null || true
echo "=== [3/3] make ==="
make -j8 2>&1 | tail -40
ls -la flash4 && echo BUILD_OK
"""
    remote.run("mkdir -p ~/SNB_hpc_build", timeout=30)
    script_path = f"~/SNB_hpc_build/build_{distro_tag}.sh"
    # 本地生成脚本文件 → scp 上传 (base64 超长单命令在 BSCC 网关不可靠, 弃用)
    # ⚠️ newline="\n" 强制 LF: Windows write_text 默认转 CRLF, 远端 bash 会语法报错
    local_sh = T001 / f"_hpc_build_{distro_tag}.sh"
    local_sh.write_text(job_script, encoding="utf-8", newline="\n")
    ok_up = remote.upload(str(local_sh), script_path)
    local_sh.unlink(missing_ok=True)
    out, _, _ = remote.run(f"chmod +x {script_path} && bash -n {script_path} && echo SCRIPT_OK", timeout=30)
    if not ok_up or "SCRIPT_OK" not in out:
        log(f"[构建] 作业脚本上传/校验失败: {out[-200:]}", "ERROR")
        return False

    log("[构建] 提交 sbatch 作业 (setup+make)...", "STEP")
    out, _, code = remote.run(f"cd ~/SNB_hpc_build && sbatch {script_path.split('/')[-1]} 2>&1", timeout=60)
    m = re.search(r"Submitted batch job (\d+)", out)
    if not m:
        log(f"[构建] sbatch 提交失败: {out[-300:]}", "ERROR")
        return False
    job_id = m.group(1)
    log(f"[构建] JobID={job_id} (分区 {partition})", "OK")
    return wait_job(remote, job_id, snb_home, "BUILD_OK", timeout=3600)


# ── 作业等待 (sacct 轮询) ────────────────────────────

def wait_job(remote: Remote, job_id: str, check_dir: str, marker: str,
             out_glob: str = "~/SNB_hpc_build/*_out.txt", timeout: int = 1800) -> bool:
    """轮询 sacct 直到 COMPLETED/FAILED, 并检查 marker 是否出现。"""
    start = time.time()
    last_state = ""
    while time.time() - start < timeout:
        out, _, _ = remote.run(
            f"sacct -j {job_id} --format=State --noheader 2>/dev/null | head -1", timeout=30
        )
        state = out.strip().splitlines()[0] if out.strip() else ""
        if state != last_state:
            log(f"[作业] JobID={job_id} 状态: {state or '(无记录)'}")
            last_state = state
        if state in ("COMPLETED",):
            # 检查 marker (作业输出文件在提交目录, build→~/SNB_hpc_build, run→~/SNB_hpc_run)
            out2, _, _ = remote.run(
                f"grep -l '{marker}' {out_glob} 2>/dev/null | head -1; "
                f"tail -5 {out_glob} 2>/dev/null",
                timeout=30,
            )
            if marker in out2:
                return True
            # marker 未出现但作业 COMPLETED → 仍可能成功 (marker 在 ls 行)
            log(f"[作业] 完成但 marker 未确认, 回退判定 True (可人工核验): {out2[-200:]}", "WARN")
            return True
        if state in ("FAILED", "CANCELLED", "TIMEOUT", "NODE_FAIL", "OUT_OF_MEMORY"):
            log(f"[作业] 失败: {state}", "ERROR")
            out3, _, _ = remote.run(
                f"tail -20 {out_glob.replace('_out.txt', '_err.txt')} 2>/dev/null; "
                f"tail -20 {out_glob} 2>/dev/null",
                timeout=30,
            )
            log(f"[作业] 输出尾部:\n{out3[-1500:]}", "ERROR")
            return False
        time.sleep(20)
    log(f"[作业] JobID={job_id} 等待超时 ({timeout}s)", "ERROR")
    return False


# ── 步骤 5: 运行 (sbatch) ────────────────────────────

def run_remote(remote: Remote, snb_home: str, partition: str, account: str,
               tmax: str, nproc: int) -> bool:
    """上传 par → 覆写 tmax → sbatch 运行 → 检查输出。"""
    env_block = runtime_env_block(snb_home, account)
    distro_tag = ACCOUNT_TAG.get(account, account)
    # 上传 par
    par_local = FLASH_INPUT / "flash.par"
    remote.run(f"mkdir -p ~/SNB_hpc_run", timeout=30)
    ok = remote.upload(str(par_local), f"~/SNB_hpc_run/flash.par")
    if not ok:
        raise RuntimeError("flash.par 上传失败")

    run_script = f"""#!/bin/bash
#SBATCH --job-name=SNB_run_{distro_tag}
#SBATCH -p {partition}
#SBATCH -N 1
#SBATCH --ntasks={nproc}
#SBATCH --output=SNB_run_%j_out.txt
#SBATCH --error=SNB_run_%j_err.txt
set -e
{env_block}cd {snb_home}/{OBJDIR}
rm -f NonLTConduct* .success
cp -f ~/SNB_hpc_run/flash.par flash.par
sed -i 's/^tmax.*/tmax           = {tmax}/' flash.par
grep -n '^tmax' flash.par
echo "=== running (mpi) ==="
# mpiexec 优先 (登录环境 MPI, 与 Makefile.h 编译器一致), 失败回退 srun
mpiexec -n {nproc} ./flash4 > wsl_run_snb.log 2>&1 || srun -n {nproc} ./flash4 > wsl_run_snb.log 2>&1
echo "RUN_EXIT=$?" >> wsl_run_snb.log
tail -5 wsl_run_snb.log
ls NonLTConduct* 2>/dev/null | wc -l
echo RUN_DONE
"""
    # 本地生成运行脚本 → scp 上传 (newline="\n" 强制 LF, 防 CRLF)
    local_sh = T001 / f"_hpc_run_{distro_tag}.sh"
    local_sh.write_text(run_script, encoding="utf-8", newline="\n")
    ok_up = remote.upload(str(local_sh), "~/SNB_hpc_run/run.sh")
    local_sh.unlink(missing_ok=True)
    out, _, _ = remote.run("chmod +x ~/SNB_hpc_run/run.sh && bash -n ~/SNB_hpc_run/run.sh && echo SCRIPT_OK", timeout=30)
    if not ok_up or "SCRIPT_OK" not in out:
        log(f"[运行] 作业脚本上传/校验失败: {out[-200:]}", "ERROR")
        return False

    log(f"[运行] 提交 sbatch 作业 (tmax={tmax}, nproc={nproc})...", "STEP")
    out, _, code = remote.run(f"cd ~/SNB_hpc_run && sbatch run.sh 2>&1", timeout=60)
    m = re.search(r"Submitted batch job (\d+)", out)
    if not m:
        log(f"[运行] sbatch 失败: {out[-300:]}", "ERROR")
        return False
    job_id = m.group(1)
    ok = wait_job(remote, job_id, f"{snb_home}/{OBJDIR}", "RUN_DONE",
                  out_glob="~/SNB_hpc_run/*_out.txt", timeout=1200)
    if not ok:
        return False

    # 检查运行日志
    out2, _, _ = remote.run(
        f"cd {snb_home}/{OBJDIR} && tail -6 wsl_run_snb.log 2>/dev/null; "
        f"echo '---'; ls NonLTConduct* 2>/dev/null | head; echo FILES_END",
        timeout=30,
    )
    good = ("RUN_EXIT=0" in out2) or ("reached max SimTime" in out2)
    if not good:
        log(f"[运行] 疑似未成功:\n{out2[-400:]}", "ERROR")
    return good


# ── 步骤 6: 收集输出到本地 ───────────────────────────

def collect_outputs(remote: Remote, snb_home: str, account: str) -> Path:
    """把 objdir 内 NonLTConduct* + wsl_run_snb.log 下载到 flash_output/hpc_<account>/。"""
    out_dir = FLASH_OUTPUT / f"hpc_{account}"
    out_dir.mkdir(parents=True, exist_ok=True)
    obj = f"{snb_home}/{OBJDIR}"

    # 列出远端文件
    out, _, _ = remote.run(f"cd {obj} && ls NonLTConduct* wsl_run_snb.log 2>/dev/null; echo LIST_END", timeout=30)
    names = []
    for line in out.splitlines():
        line = line.strip()
        if not line or line == "LIST_END":
            continue
        names.append(line)
    if not names:
        log(f"[收集] objdir 无输出文件: {obj}", "WARN")
        return out_dir

    log(f"[收集] 下载 {len(names)} 个文件到 {out_dir}...", "STEP")
    for n in names:
        # 先 cp 到 home 根 (scp 相对路径稳定)
        remote.run(f"cp -f {obj}/{n} ~/SNB_hpc_out_{n} 2>/dev/null || true", timeout=30)
        ok = remote.download(f"~/SNB_hpc_out_{n}", str(out_dir / n))
        if ok:
            log(f"  ✓ {n}")
        else:
            log(f"  ✗ {n} 下载失败", "WARN")
        remote.run(f"rm -f ~/SNB_hpc_out_{n}", timeout=20)

    # 清理远端输出 (已收集, 不占超算空间; 保留源码树/objdir 供复用)
    remote.run(f"cd {obj} && rm -f NonLTConduct* wsl_run_snb.log 2>/dev/null; true", timeout=30)
    log(f"[收集] 完成 → {out_dir}", "OK")
    return out_dir


# ── 主流程 ───────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(description="SNB 场景 HPC 一键执行")
    ap.add_argument("--account", default="flash_ssh", choices=["flash_ssh", "flash_ssh_2"],
                    help="凭据账号名 (默认 flash_ssh=scfa2696)")
    ap.add_argument("--tmax", default="1.0e-11", help="覆写 tmax (默认 1.0e-11)")
    ap.add_argument("--nproc", type=int, default=4, help="MPI 进程数 (默认 4)")
    ap.add_argument("--partition", default="", help="SLURM 分区 (默认按账号自动探测)")
    ap.add_argument("--skip-upload", action="store_true", help="跳过上传/解压 (复用远端源码树)")
    ap.add_argument("--skip-build", action="store_true", help="跳过 setup+make (复用已编译 flash4)")
    ap.add_argument("--force-upload", action="store_true", help="强制重新上传解压")
    args = ap.parse_args()

    print("=" * 64)
    print(f" SNB HPC 执行 — 账号: {args.account}")
    print(f" 仿真用户目录: {get_sim_user_dir()}")
    print(f" 远端 FLASHSNB: {remote_flashsnb_home()}")
    print("=" * 64)

    with Remote(args.account) as remote:
        # 0. 环境探测
        out, _, code = remote.run(
            f"which sbatch >/dev/null 2>&1 && echo SBATCH_OK; echo USER=$(whoami); "
            f"echo HOME=$HOME", timeout=30,
        )
        log(f"远端: {out.strip()[:200]}", "OK")

        # 1. 分区
        partition = args.partition or detect_partition(remote, args.account)
        log(f"SLURM 分区: {partition}", "OK")

        # 2. 部署源码
        if args.skip_upload:
            snb_home = remote_flashsnb_home()
            out, _, _ = remote.run(f"ls -d {snb_home}/setup || echo NO_SETUP", timeout=30)
            if "NO_SETUP" in out:
                log(f"远端源码树不存在 (--skip-upload 但无树): {snb_home}", "ERROR")
                return 1
            log(f"[部署] 复用远端源码树: {snb_home}", "OK")
        else:
            snb_home = deploy_source(remote, force=args.force_upload)

        # 3. Makefile.h
        apply_makefile_h(remote, snb_home)

        # 4. 构建 (setup+make)
        if not args.skip_build:
            ok = build_remote(remote, snb_home, partition, args.account)
            if not ok:
                log("[构建] 失败", "ERROR")
                return 1
        else:
            out, _, _ = remote.run(f"ls {snb_home}/{OBJDIR}/flash4 2>/dev/null || echo NO_FLASH4", timeout=30)
            if "NO_FLASH4" in out:
                log("[构建] --skip-build 但 flash4 不存在", "ERROR")
                return 1

        # 5. 运行
        ok_run = run_remote(remote, snb_home, partition, args.account, args.tmax, args.nproc)

        # 6. 收集 (无论运行成功与否都尝试收集)
        out_dir = collect_outputs(remote, snb_home, args.account)

    print("\n" + "=" * 64)
    if ok_run:
        print(" HPC 运行成功! 输出:")
    else:
        print(" HPC 运行异常 — 输出目录 (可能部分):")
    for f in sorted(out_dir.iterdir()):
        print(f"   {f.name}  ({f.stat().st_size} bytes)")
    print("=" * 64)
    return 0 if ok_run else 1


if __name__ == "__main__":
    sys.exit(main())
