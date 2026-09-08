#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SNB 场景一键执行脚本 (t001)。

流程: [补丁同步] -> [setup] -> [make] -> [mpiexec 运行] -> [输出收集] -> [报告]

运行环境: Windows 宿主 -> WSL (Ubuntu-22.04) 内的 SNB 专用 FLASH (FLASHSNB)。

用法:
  python run_snb.py                 # 完整流程 (补丁+setup+make+run+collect)
  python run_snb.py --skip-setup    # 复用现有 objdir (不重新 setup)
  python run_snb.py --skip-make     # 复用现有 flash4 二进制
  python run_snb.py --no-patch      # 不执行补丁同步
  python run_snb.py --tmax 1.0e-11  # 覆写 flash.par 的 tmax
  python run_snb.py --nproc 4       # MPI 进程数 (默认 4, 须与 par iProcs 一致)
  python run_snb.py --distro Ubuntu-22.04   # WSL 发行版 (默认 Ubuntu-22.04)
  python run_snb.py --user <name>   # 显式指定 WSL 用户名 (不指定时自动获取)

身份获取优先级: flash._core.credentials.get_user_name() -> 环境变量
FLASH_SIM_USER_DIR -> --user 参数 -> 退出并提示 (绝不硬编码)。
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

# ── 目录布局 (相对本脚本) ──────────────────────────────────────────
T001 = Path(__file__).resolve().parent
PATCHES = T001 / "source_patches"
FLASH_INPUT = T001 / "flash_input"
FLASH_OUTPUT = T001 / "flash_output"

# SNB 专用 FLASH 的 objdir 名 (setup 参数 -objdir= 必须一致)
OBJDIR = "SNB_1D_laser_obj"
# 场景名 (setup 第一个参数)
SCENARIO = "SNB_1D_laser"

SETUP_CMD = (
    "./setup -auto SNB_1D_laser -1d +cartesian +ug -nxb=8 +hdf5typeio "
    "species=cham,tar1,tar2,tar3 +mtmmmt +laser +uhd3t +mgd mgd_meshgroups=10 "
    "-objdir=SNB_1D_laser_obj"
)

# 输出文件 glob (FLASH hdf5typeio 无 .h5 后缀)
OUTPUT_GLOBS = ("NonLTConduct*",)


def log(msg: str, level: str = "INFO") -> None:
    tag = {"INFO": "  ", "STEP": ">> ", "OK": "✓ ", "WARN": "! ", "ERROR": "✗ "}.get(level, "  ")
    print(f"{time.strftime('%H:%M:%S')} {tag}{msg}")


def get_sim_user() -> str | None:
    """获取 WSL 用户名: 专用凭据函数 -> 项目根 flash 包 -> 环境变量 -> None。

    绝不硬编码用户名: 优先 flash._core.credentials.get_user_name()。
    """
    for root in (None, T001.parents[5] if len(T001.parents) > 5 else None):
        if root is not None:
            sys.path.insert(0, str(root))
        try:
            from flash._core.credentials import get_user_name  # type: ignore
            u = get_user_name()
            if u:
                return u
        except Exception:  # noqa: BLE001
            pass
    return os.environ.get("FLASH_SIM_USER_DIR") or None


def wsl_path(win_path: Path, distro: str) -> str:
    """Windows 绝对路径 -> WSL /mnt/... 路径。"""
    drive = win_path.drive.lower().rstrip(":")
    rest = win_path.as_posix().split(":", 1)[1] if ":" in win_path.as_posix() else win_path.as_posix()
    rest = rest.lstrip("/")
    return f"/mnt/{drive}/{rest}"


def find_snb_home(distro: str) -> str | None:
    """在 WSL $HOME 下探测 SNB 专用 FLASH 根目录 (FLASHSNB/FLASH4.8)。

    不依赖用户名拼路径、不硬编码任何目录名: find -name FLASHSNB 自动定位。
    """
    code, out = run_wsl(
        'find "$HOME" -maxdepth 3 -type d -name FLASHSNB 2>/dev/null | head -1', distro, timeout=60
    )
    p = out.strip()
    if not p:
        return None
    code2, out2 = run_wsl(f'ls -d "{p}/FLASH4.8" >/dev/null 2>&1 && echo F4_OK', distro, timeout=60)
    if "F4_OK" in out2:
        return f"{p}/FLASH4.8"
    return None


def run_wsl(cmd: str, distro: str, timeout: int = 7200) -> tuple[int, str]:
    """在 WSL 中执行命令, 返回 (exit_code, 输出)。"""
    log(f"执行: {cmd[:160]}{'...' if len(cmd) > 160 else ''}")
    try:
        p = subprocess.run(
            ["wsl", "-d", distro, "bash", "-lc", cmd],
            capture_output=True, text=True, timeout=timeout,
        )
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return 124, f"[timeout after {timeout}s]"


def shlex_quote(s: str) -> str:
    return "'" + s.replace("'", "'\\''") + "'"


def sync_patches(snb_home: str, distro: str) -> bool:
    """把 source_patches/ 同步到 FLASHSNB source 对应路径 (防 source 被还原)。"""
    if not PATCHES.exists():
        log("source_patches 不存在, 跳过补丁同步", "WARN")
        return True
    snb_src = f"{snb_home}/source"
    wsl_patches = wsl_path(PATCHES, distro)
    # 用 tar 保持目录结构复制 (rsync 可能未安装)
    cmd = (
        f"cd {wsl_patches} && tar cf - . | (cd {snb_src} && tar xf -) && "
        f"echo PATCH_OK"
    )
    code, out = run_wsl(cmd, distro, timeout=300)
    if code == 0 and "PATCH_OK" in out:
        log("补丁已同步到 FLASHSNB source/", "OK")
        return True
    log(f"补丁同步失败: {out[-300:]}", "ERROR")
    return False


def do_setup(snb_home: str, distro: str) -> bool:
    obj = f"{snb_home}/{OBJDIR}"
    run_wsl(
        f"cd {snb_home} && rm -rf {obj} && {SETUP_CMD} 2>&1 | tail -20", distro, timeout=600
    )
    # setup 成功标志: objdir 存在
    code2, out2 = run_wsl(f"ls -d {obj} && echo OBJ_OK", distro, timeout=60)
    if "OBJ_OK" in out2:
        log("setup 完成 (objdir 已生成)", "OK")
        # objdir 内建立 mgd_qesh 符号链接 (若 setup 未包含该场景文件)
        run_wsl(
            f"cd {obj} && ln -sf ../source/Simulation/SimulationMain/SNB_1D_laser/mgd_qesh.F90 mgd_qesh.F90 2>/dev/null; true",
            distro, timeout=60,
        )
        return True
    log(f"setup 失败: {out[-400:]}", "ERROR")
    return False


def do_make(snb_home: str, distro: str) -> bool:
    obj = f"{snb_home}/{OBJDIR}"
    # 并行编译竞态处理: 先单独编关键模块 (若 .o 缺失)
    code, out = run_wsl(
        f"cd {obj} && make hy_slopeLimiters.o Conductivity_interface.o Conductivity_fullState.o 2>&1 | tail -5",
        distro, timeout=600,
    )
    code, out = run_wsl(
        f"cd {obj} && make -j4 2>&1 | grep -iE 'error|Error|flash4' | tail -30; "
        f"echo MAKE_DONE; ls -la flash4 2>/dev/null || echo NO_FLASH4",
        distro, timeout=3600,
    )
    has_flash4 = "NO_FLASH4" not in out
    has_error = bool(re.search(r"(?i)error", out))
    if has_flash4 and not has_error:
        log("编译完成 (flash4 已生成)", "OK")
        return True
    log(f"编译异常: {out[-500:]}", "ERROR")
    return False


def apply_tmax(objdir_par: str, tmax: str, distro: str) -> None:
    """覆写 objdir 内 flash.par 的 tmax (若指定)。"""
    if not tmax:
        return
    cmd = f"cd {objdir_par} && sed -i 's/^tmax.*/tmax           = {tmax}/' flash.par && grep -n '^tmax' flash.par"
    run_wsl(cmd, distro, timeout=60)


def do_run(snb_home: str, nproc: int, distro: str, wsl_out_dir: str) -> bool:
    obj = f"{snb_home}/{OBJDIR}"
    log(f"运行 FLASH: mpiexec -n {nproc} ./flash4 (tmax 见 par)", "STEP")
    code, out = run_wsl(
        f"cd {obj} && rm -f NonLTConduct* wsl_run_snb.log .success && "
        f"mpiexec -n {nproc} ./flash4 > wsl_run_snb.log 2>&1; echo RUN_EXIT=$? >> wsl_run_snb.log",
        distro, timeout=7200,
    )
    # 收集
    log("收集输出到 flash_output/ ...", "STEP")
    wsl_obj = f"{obj}"
    # 检查运行结果
    code2, out2 = run_wsl(
        f"cd {obj} && tail -5 wsl_run_snb.log; echo; ls NonLTConduct* 2>/dev/null | wc -l",
        distro, timeout=120,
    )
    print(out2)
    # 复制输出
    wsl_obj_dir = obj
    cop = (
        f"mkdir -p {wsl_out_dir} && "
        f"cp -f {wsl_obj_dir}/NonLTConduct* {wsl_out_dir}/ 2>/dev/null; "
        f"cp -f {wsl_obj_dir}/wsl_run_snb.log {wsl_out_dir}/ 2>/dev/null; "
        f"echo COLLECT_DONE"
    )
    code3, out3 = run_wsl(cop, distro, timeout=300)
    if "COLLECT_DONE" not in out3:
        log(f"输出收集失败: {out3[-200:]}", "ERROR")
        return False
    # 清理 WSL 侧输出 (已收集, 不占 WSL 空间)
    run_wsl(f"cd {wsl_obj_dir} && rm -f NonLTConduct* .success", distro, timeout=120)
    ok = "RUN_EXIT=0" in out2 or "reached max SimTime" in out2
    log(f"运行 {'成功' if ok else '异常'} (详看 flash_output/wsl_run_snb.log)", "OK" if ok else "ERROR")
    return ok


def main() -> int:
    ap = argparse.ArgumentParser(description="SNB 场景一键执行 (FLASHSNB)")
    ap.add_argument("--skip-setup", action="store_true", help="跳过 setup (复用现有 objdir)")
    ap.add_argument("--skip-make", action="store_true", help="跳过 make (复用现有 flash4)")
    ap.add_argument("--no-patch", action="store_true", help="不执行补丁同步")
    ap.add_argument("--tmax", default="", help="覆写 tmax, 如 1.0e-11")
    ap.add_argument("--nproc", type=int, default=4, help="MPI 进程数 (默认 4)")
    ap.add_argument("--distro", default="Ubuntu-22.04", help="WSL 发行版 (默认 Ubuntu-22.04)")
    ap.add_argument("--user", default=None, help="WSL 用户名 (默认自动获取)")
    args = ap.parse_args()

    user = args.user or get_sim_user()
    # 优先探测 WSL $HOME 下的 FLASHSNB/FLASH4.8 (不依赖用户名拼路径、不硬编码目录名)
    snb_home = find_snb_home(args.distro)
    if not snb_home:
        if not user:
            log("无法定位 FLASHSNB: 请设置环境变量 FLASH_SIM_USER_DIR 或用 --user", "ERROR")
            return 1
        snb_home = f"~/{user}/FLASH/FLASHSNB/FLASH4.8"
    log(f"SNB 专用 FLASH 根目录: {snb_home}", "STEP")

    # 0. 环境检查
    code, out = run_wsl(f"ls -d {snb_home} && which mpiexec && echo ENV_OK", args.distro, timeout=60)
    if "ENV_OK" not in out:
        log(f"WSL/FLASHSNB 环境检查失败: {out[-300:]}", "ERROR")
        return 1
    log("WSL + FLASHSNB 环境就绪", "OK")

    # 1. 补丁同步 (可选)
    if not args.no_patch and PATCHES.exists():
        if not sync_patches(snb_home, args.distro):
            return 1

    # 2. setup (可选)
    if not args.skip_setup:
        if not do_setup(snb_home, args.distro):
            return 1
    # 确保 objdir 存在
    code, out = run_wsl(f"ls -d {snb_home}/{OBJDIR} && echo OBJ_OK", args.distro, timeout=60)
    if "OBJ_OK" not in out:
        log(f"objdir 不存在, 请先 setup (或去掉 --skip-setup): {snb_home}/{OBJDIR}", "ERROR")
        return 1

    # 3. 输入: 同步 par (含 iProcs=4, 可覆写 tmax)
    wsl_input = wsl_path(FLASH_INPUT, args.distro)
    run_wsl(
        f"cp -f {wsl_input}/flash.par {snb_home}/{OBJDIR}/flash.par", args.distro, timeout=60
    )
    apply_tmax(f"{snb_home}/{OBJDIR}", args.tmax, args.distro)

    # 4. 编译 (可选)
    if not args.skip_make:
        if not do_make(snb_home, args.distro):
            return 1

    # 5. 运行 + 收集
    wsl_out_dir = wsl_path(FLASH_OUTPUT, args.distro)
    ok = do_run(snb_home, args.nproc, args.distro, wsl_out_dir)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
