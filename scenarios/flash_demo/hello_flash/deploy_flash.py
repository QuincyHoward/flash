#!/usr/bin/env python3
"""
FLASH 4.8 One-Click Deploy Script
===================================
Interactive CLI to install FLASH on local WSL or remote supercomputers (SSH).

Usage:
    python deploy_flash.py

Features:
    - Select target machine: local WSL / SSH1 (NC-E) / SSH2 (BSCC-T6)
    - Install FLASH to ~/<用户名>/FLASH/ on the selected machine
      (用户名通过 flash._core.credentials 设置, 读取不到时默认 hello;
       默认密码 123, 见 flash._core.credentials 的 SSH 凭据模板)
    - Upload FLASH source tarball to remote machines
    - Compile and run LaserSlab 1D simulation
    - Download HDF5 results to local outputfiles/ directory
    - Generate density analysis plots

Environment:
    - FLASH_SOURCE_SUFFIX env var controls output subdirectory suffix
    - 用户名须通过 flash._core.credentials 设置 (请勿硬编码):
        python -m flash._core.credentials user <用户名>
    - Temp files transferred via ~/<用户名>/AI/AItemp/ on remote machines
"""

import os
import sys
import time
import shutil
import subprocess
import textwrap
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

# ── Path Setup ──────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
# 向上三级: hello_flash → flash_demo → scenarios → flash/ (项目根目录)
FLASH_SRC_DIR = SCRIPT_DIR.parent.parent.parent / "flash_src"
OUTPUT_BASE = SCRIPT_DIR / "outputfiles"

# Required tarballs
REQUIRED_TARBALLS = ["FLASH4.8.tar.gz", "mpich-3.2.tar.gz", "hdf5-1.8.12.tar.gz", "hypre-2.9.0b.tar.gz"]


def get_flash_user_name() -> str:
    """获取 FLASH 专属用户名。

    优先级: flash._core.credentials 中设置的用户名 → 默认 "hello"。
    用户名必须通过 flash._core.credentials 设置, 请勿硬编码:
        python -m flash._core.credentials user <用户名>
    """
    try:
        # flash 包入口: hello_flash → flash_demo → scenarios → flash → sim
        _sim_root = str(SCRIPT_DIR.parents[3])  # parents[3] = .../sim (import flash 需要)
        if _sim_root not in sys.path:
            sys.path.insert(0, _sim_root)
        from flash._core.credentials import get_user_name

        name = get_user_name()
        return name if name else "hello"
    except Exception:
        return "hello"  # 读取不到 → 默认用户名

# ── Color helpers ───────────────────────────────────────────
class C:
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    CYAN = "\033[0;36m"
    BOLD = "\033[1m"
    RESET = "\033[0m"

def info(msg):    print(f"{C.CYAN}[INFO]{C.RESET} {msg}")
def ok(msg):      print(f"{C.GREEN}[ OK ]{C.RESET} {msg}")
def warn(msg):    print(f"{C.YELLOW}[WARN]{C.RESET} {msg}")
def err(msg):     print(f"{C.RED}[ERR ]{C.RESET} {msg}", file=sys.stderr)
def step(msg):    print(f"\n{C.BOLD}{C.CYAN}{'='*50}{C.RESET}\n  {C.BOLD}{msg}{C.RESET}\n{C.BOLD}{C.CYAN}{'='*50}{C.RESET}")


# ══════════════════════════════════════════════════════════════
# Machine Configurations
# ══════════════════════════════════════════════════════════════

MACHINES = {
    "1": {
        "name": "local_wsl",
        "label": "Local WSL (Ubuntu-22.04)",
        "description": "Install FLASH on local WSL, compile from source",
        "ssh_credential": None,
        "install_dir": "~/FLASH",
        "temp_dir": "/tmp/flash_build",
        "output_suffix": "",          # outputfiles/hdf5files/laserslab1d/
        "mpi_path": "/usr/local/mpich",
        "hdf5_path": "/usr/local/hdf5",
        "hypre_path": "/usr/local/hypre",
        "has_sudo": True,
        "module_load": "",
        "flash_setup_args": "-1d +cartesian -nxb=16 +hdf5typeio species=cham,targ +mtmmmt +laser +uhd3t +mgd mgd_meshgroups=10",
        "nproc_run": 1,
    },
    "2": {
        "name": "ssh1",
        "label": "SSH1 - ParaCloud NC-E (scfa2696@NC-E)",
        "description": "Install FLASH on ParaCloud NC-E supercomputer",
        "ssh_credential": "flash_ssh",
        "install_dir": "~/FLASH",
        "temp_dir": "~/flash_temp",
        "output_suffix": "from_ssh1", # outputfiles/hdf5filesfrom_ssh1/laserslab1d/
        "mpi_path": "",  # from module load
        "hdf5_path": "", # from module load
        "hypre_path": "~/FLASH/local/hypre",
        "has_sudo": False,
        "module_load": "source /public1/soft/modules/module.sh && module load hdf5/1.8.18 && module load mpich/3.2-gcc9.3",
        "flash_setup_args": "-1d +cartesian -nxb=16 +hdf5typeio species=cham,targ +mtmmmt +laser +uhd3t +mgd mgd_meshgroups=10",
        "nproc_run": 4,
    },
    "3": {
        "name": "ssh3",
        "label": "SSH3 - ParaCloud BSCC-T6 (sch0348@BSCC-T6)",
        "description": "Install FLASH on ParaCloud BSCC-T6 supercomputer (ssh.paracloud.com:2222)",
        "ssh_credential": "flash_ssh_3",
        "install_dir": "~/FLASH",
        "temp_dir": "~/flash_temp",
        "output_suffix": "from_ssh2", # outputfiles/hdf5filesfrom_ssh2/laserslab1d/
        "mpi_path": "",  # from module load
        "hdf5_path": "", # from module load
        "hypre_path": "~/FLASH/local/hypre",
        "has_sudo": False,
        "module_load": "source /public1/soft/modules/module.sh && module load hdf5/1.8.18 && module load mpich/3.2-gcc9.3",
        "flash_setup_args": "-1d +cartesian -nxb=16 +hdf5typeio species=cham,targ +mtmmmt +laser +uhd3t +mgd mgd_meshgroups=10",
        "nproc_run": 4,
    },
}


# ══════════════════════════════════════════════════════════════
# Local WSL Executor
# ══════════════════════════════════════════════════════════════

def run_wsl_command(cmd: str, timeout: int = 600, wsl_distro: str = "Ubuntu-22.04") -> Tuple[str, str, int]:
    """Execute a command in WSL via PowerShell."""
    # Write command to a temp script file to avoid PowerShell variable escaping issues
    script_path = SCRIPT_DIR / "_wsl_temp_cmd.sh"
    script_path.write_text(cmd, encoding="utf-8")
    wsl_script = f"/mnt/{str(SCRIPT_DIR).replace(':', '').replace(chr(92), '/')}/_wsl_temp_cmd.sh"
    
    ps_cmd = f'& "C:\\Windows\\System32\\wsl.exe" -d {wsl_distro} -e bash "{wsl_script}"'
    
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            capture_output=True, text=True, timeout=timeout,
        )
        return result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        return "", "TIMEOUT", -1
    finally:
        script_path.unlink(missing_ok=True)


# ══════════════════════════════════════════════════════════════
# SSH Remote Executor
# ══════════════════════════════════════════════════════════════

def get_ssh_client(credential_name: str):
    """Create an SSH client from stored credentials."""
    from flash._core.credentials import get_credential_manager
    import paramiko

    cm = get_credential_manager()
    cred = cm.get(credential_name)
    if not cred:
        raise RuntimeError(f"Credential '{credential_name}' not found. Run: python -m flash._core.credentials.manage")

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        hostname=cred["host"],
        port=int(cred.get("port", 22)),
        username=cred["username"],
        password=cred["password"],
        timeout=30,
        allow_agent=False,
        look_for_keys=False,
        banner_timeout=15,
    )
    return client, cred


def run_ssh_command(client, cmd: str, timeout: int = 600) -> Tuple[str, str, int]:
    """Execute a command on remote machine via SSH."""
    import paramiko
    try:
        stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode(errors="replace").strip()
        err = stderr.read().decode(errors="replace").strip()
        exit_code = stdout.channel.recv_exit_status()
        return out, err, exit_code
    except Exception as e:
        return "", str(e), -1


def ssh_upload_file(client, local_path: str, remote_path: str, sftp=None):
    """Upload a file via SFTP."""
    if sftp is None:
        sftp = client.open_sftp()
    sftp.put(local_path, remote_path)
    return sftp


def ssh_download_dir(client, remote_dir: str, local_dir: str, pattern: str = "*hdf5_chk_*") -> List[str]:
    """Download files matching pattern from remote directory."""
    sftp = client.open_sftp()
    downloaded = []
    
    try:
        remote_files = sftp.listdir(remote_dir)
        import fnmatch
        matching = [f for f in remote_files if fnmatch.fnmatch(f, pattern)]
        
        os.makedirs(local_dir, exist_ok=True)
        for fname in matching:
            remote_path = f"{remote_dir}/{fname}"
            local_path = os.path.join(local_dir, fname)
            try:
                sftp.get(remote_path, local_path)
                downloaded.append(local_path)
                ok(f"  Downloaded: {fname}")
            except Exception as e:
                warn(f"  Failed to download {fname}: {e}")
    finally:
        sftp.close()
    
    return downloaded


# ══════════════════════════════════════════════════════════════
# FLASH Installation Scripts (Shell)
# ══════════════════════════════════════════════════════════════

def generate_wsl_install_script(machine: Dict) -> str:
    """Generate the complete WSL installation shell script."""
    user = get_flash_user_name()  # 用户名: flash._core.credentials → 默认 hello
    return textwrap.dedent(f"""\
    #!/bin/bash
    set -eo pipefail
    
    # 用户名: FLASH_SIM_USER_DIR 环境变量 → flash._core.credentials → 默认 hello
    # 用户名须通过 flash._core.credentials 设置 (勿硬编码)
    FLASH_SIM_USER_DIR="${{FLASH_SIM_USER_DIR:-{user}}}"
    FLASH_USER_HOME="${{FLASH_USER_HOME:-$HOME/$FLASH_SIM_USER_DIR}}"
    FLASH_PARENT="$FLASH_USER_HOME/FLASH"
    FLASH_HOME="$FLASH_PARENT/FLASH4.8"
    BUILD_DIR="/tmp/flash_build"
    
    MPI_PATH="{machine['mpi_path']}"
    HDF5_PATH="{machine['hdf5_path']}"
    HYPRE_PATH="{machine['hypre_path']}"
    NPROC="$(nproc)"
    
    FLASH_TAR="FLASH4.8.tar.gz"
    MPICH_TAR="mpich-3.2.tar.gz"
    HDF5_TAR="hdf5-1.8.12.tar.gz"
    HYPRE_TAR="hypre-2.9.0b.tar.gz"
    
    # Source tarball directory - check multiple locations
    PKG_DIR=""
    # 优先搜索脚本所在目录及 flash_src/ 目录
    for d in "$PWD" "$(dirname $0)/../../../flash_src" "$(dirname $0)/../../flash_src"; do
        if [ -f "$d/$FLASH_TAR" ]; then
            PKG_DIR="$d"
            break
        fi
    done
    
    if [ -z "$PKG_DIR" ]; then
        echo "[ERROR] Cannot find FLASH4.8.tar.gz"
        exit 1
    fi
    
    echo "[INFO] Source packages: $PKG_DIR"
    
    # ── Step 0: System dependencies ──
    echo "[0/6] Installing system dependencies..."
    sudo apt-get update -y -qq 2>&1 | tail -1
    sudo apt-get install -y -qq gcc g++ gfortran gcc-9 g++-9 gfortran-9 make \\
        python3 python3-pip python-is-python3 zlib1g-dev \\
        libopenblas-dev liblapack-dev liblapacke-dev wget 2>&1 | tail -5
    sudo update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-9 50 2>/dev/null || true
    sudo update-alternatives --install /usr/bin/g++ g++ /usr/bin/g++-9 50 2>/dev/null || true
    sudo update-alternatives --install /usr/bin/gfortran gfortran /usr/bin/gfortran-9 50 2>/dev/null || true
    if ! command -v python &>/dev/null; then
        sudo ln -sf "$(command -v python3)" /usr/local/bin/python 2>/dev/null || true
    fi
    
    # ── Step 1: Prepare source packages ──
    echo "[1/6] Preparing source packages..."
    mkdir -p "$BUILD_DIR"
    for pkg in "$MPICH_TAR" "$HDF5_TAR" "$HYPRE_TAR" "$FLASH_TAR"; do
        cp -n "$PKG_DIR/$pkg" "$BUILD_DIR/" 2>/dev/null || true
    done
    
    # ── Step 2: MPICH ──
    if [ -x "$MPI_PATH/bin/mpicc" ]; then
        echo "[2/6] SKIP: MPICH already installed"
    else
        echo "[2/6] Building MPICH 3.2..."
        cd "$BUILD_DIR" && rm -rf mpich-3.2 && tar -xzf "$MPICH_TAR" && cd mpich-3.2
        ./configure --prefix="$MPI_PATH" CC=gcc-9 CXX=g++-9 FC=gfortran-9 F77=gfortran-9 2>&1 | tail -3
        make -j"$NPROC" 2>&1 | tail -3 && sudo make install 2>&1 | tail -3
    fi
    export PATH="$MPI_PATH/bin:$PATH"
    export LD_LIBRARY_PATH="$MPI_PATH/lib:${{LD_LIBRARY_PATH:-}}"
    
    # ── Step 3: HDF5 ──
    if [ -f "$HDF5_PATH/lib/libhdf5.a" ] || [ -f "$HDF5_PATH/lib/libhdf5.so" ]; then
        echo "[3/6] SKIP: HDF5 already installed"
    else
        echo "[3/6] Building HDF5 1.8.12..."
        cd "$BUILD_DIR" && rm -rf hdf5-1.8.12 && tar -xzf "$HDF5_TAR" && cd hdf5-1.8.12
        MPI_INC="-I$MPI_PATH/include" MPI_LIB="-L$MPI_PATH/lib"
        ./configure --prefix="$HDF5_PATH" --enable-parallel --enable-fortran \\
            CC=mpicc FC=gfortran F77=gfortran \\
            FCFLAGS="$MPI_INC" FFLAGS="$MPI_INC" LIBS="$MPI_LIB -lmpi -lmpifort" 2>&1 | tail -3
        make -j"$NPROC" 2>&1 | tail -3 && sudo make install 2>&1 | tail -3
    fi
    export PATH="$HDF5_PATH/bin:$PATH"
    export LD_LIBRARY_PATH="$HDF5_PATH/lib:$LD_LIBRARY_PATH"
    
    # ── Step 4: HYPRE ──
    if ls "$HYPRE_PATH/lib/libHYPRE"* &>/dev/null 2>&1; then
        echo "[4/6] SKIP: HYPRE already installed"
    else
        echo "[4/6] Building HYPRE 2.9.0b..."
        cd "$BUILD_DIR" && rm -rf hypre-2.9.0b && tar -xzf "$HYPRE_TAR" && cd hypre-2.9.0b/src
        ./configure --prefix="$HYPRE_PATH" CC=mpicc CXX=mpicxx FC=gfortran-9 F77=gfortran-9 2>&1 | tail -3
        make -j"$NPROC" 2>&1 | tail -3 && sudo make install 2>&1 | tail -3
    fi
    export HYPRE_HOME="$HYPRE_PATH"
    export LD_LIBRARY_PATH="$HYPRE_PATH/lib:$LD_LIBRARY_PATH"
    
    # ── Step 5: FLASH extract + Makefile.h ──
    if [ -f "$FLASH_HOME/Makefile.h" ]; then
        echo "[5/6] SKIP: FLASH already extracted"
    else
        echo "[5/6] Extracting FLASH 4.8..."
        mkdir -p "$FLASH_PARENT" && cd "$FLASH_PARENT" && rm -rf FLASH4.8
        tar -xzf "$BUILD_DIR/$FLASH_TAR"
        
        # Configure Makefile.h
        TEMPLATE="$FLASH_HOME/sites/Prototypes/Linux/Makefile.h"
        cp "$TEMPLATE" "$FLASH_HOME/Makefile.h"
        sed -i "s|^MPI_PATH\\s*=.*|MPI_PATH = $MPI_PATH|"     "$FLASH_HOME/Makefile.h"
        sed -i "s|^HDF5_PATH\\s*=.*|HDF5_PATH = $HDF5_PATH|"   "$FLASH_HOME/Makefile.h"
        sed -i "s|^HYPRE_PATH\\s*=.*|HYPRE_PATH = $HYPRE_PATH|" "$FLASH_HOME/Makefile.h"
        grep -q "^LIB_LAPACK" "$FLASH_HOME/Makefile.h" || \\
            sed -i "/^HYPRE_PATH/a LIB_LAPACK = -llapack -lblas -lgfortran" "$FLASH_HOME/Makefile.h"
        
        # Comment out FLASHBINARY ifeq block
        _sl=$(grep -n "FLASHBINARY" "$FLASH_HOME/Makefile.h" 2>/dev/null | head -1 | cut -d: -f1) || true
        if [ -n "$_sl" ]; then
            _el=$(tail -n +"$_sl" "$FLASH_HOME/Makefile.h" | grep -n "^endif" 2>/dev/null | head -1 | cut -d: -f1) || true
            [ -n "$_el" ] && _el=$((_sl + _el - 1)) && sed -i "$_sl,$_el s/^/#/" "$FLASH_HOME/Makefile.h" || true
        fi
    fi
    
    # ── Step 6: FLASH compile ──
    if [ -f "$FLASH_HOME/object/flash4" ]; then
        echo "[6/6] SKIP: FLASH already compiled"
    else
        echo "[6/6] Compiling FLASH LaserSlab 1D..."
        cd "$FLASH_HOME" && rm -rf object/
        ./setup -auto LaserSlab {machine['flash_setup_args']} -objdir=object -parfile=example1d.par 2>&1 | tail -10
        cd object/ && make -j"$NPROC" 2>&1 | tail -5
        [ -f flash4 ] && echo "[OK] FLASH compiled successfully!" || echo "[ERROR] FLASH compilation failed!"
    fi
    
    echo ""
    echo "=== Installation Complete ==="
    echo "  FLASH: $FLASH_HOME"
    echo "  Exe:   $FLASH_HOME/object/flash4"
    """)


def generate_hpc_install_script(machine: Dict) -> str:
    """Generate the HPC remote installation shell script."""
    module_load = machine["module_load"]
    hypre_path = machine["hypre_path"]
    setup_args = machine["flash_setup_args"]
    user = get_flash_user_name()  # 用户名: flash._core.credentials → 默认 hello

    return textwrap.dedent(f"""\
    #!/bin/bash
    set -eo pipefail
    
    # 用户名: FLASH_SIM_USER_DIR 环境变量 → flash._core.credentials → 默认 hello
    # 用户名须通过 flash._core.credentials 设置 (勿硬编码)
    FLASH_SIM_USER_DIR="${{FLASH_SIM_USER_DIR:-{user}}}"
    FLASH_USER_HOME="$HOME/$FLASH_SIM_USER_DIR"
    FLASH_PARENT="$FLASH_USER_HOME/FLASH"
    FLASH_HOME="$FLASH_PARENT/FLASH4.8"
    AITEMP="$FLASH_USER_HOME/AI/AItemp"
    LOCAL_BUILD="$FLASH_USER_HOME/FLASH/local"
    # Resolve HYPRE_PATH to real path (avoid symlink issues on HPC filesystems)
    HYPRE_PATH="$(readlink -f {hypre_path} 2>/dev/null || echo {hypre_path})"
    
    FLASH_TAR="FLASH4.8.tar.gz"
    HYPRE_TAR="hypre-2.9.0b.tar.gz"
    
    # ── Load modules ──
    echo "[0/5] Loading modules..."
    {module_load}
    
    # Detect MPI/HDF5 paths from module
    MPI_PATH="$(dirname $(dirname $(which mpicc 2>/dev/null || echo '/usr/bin/mpicc')) 2>/dev/null || echo '/usr/local/mpich')"
    HDF5_PATH="$(dirname $(dirname $(which h5pcc 2>/dev/null || echo '/usr/bin/h5pcc')) 2>/dev/null || echo '/usr/local/hdf5')"
    echo "  MPI_PATH:  $MPI_PATH"
    echo "  HDF5_PATH: $HDF5_PATH"
    
    # ── Step 1: HYPRE (no sudo, user space) ──
    if ls "$HYPRE_PATH/lib/libHYPRE"* &>/dev/null 2>&1; then
        echo "[1/5] SKIP: HYPRE already installed"
    else
        echo "[1/5] Building HYPRE 2.9.0b..."
        mkdir -p "$LOCAL_BUILD"
        cd "$AITEMP" && rm -rf hypre-2.9.0b && tar -xzf "$HYPRE_TAR" && cd hypre-2.9.0b/src
        mkdir -p "$HYPRE_PATH"
        ./configure --prefix="$HYPRE_PATH" CC=mpicc CXX=mpicxx FC=gfortran F77=gfortran 2>&1 | tail -3
        make -j"$(nproc)" 2>&1 | tail -3 && make install 2>&1 | tail -3
        echo "[OK] HYPRE installed to $HYPRE_PATH"
    fi
    
    # ── Step 2: Extract FLASH ──
    if [ -f "$FLASH_HOME/Makefile.h" ]; then
        echo "[2/5] SKIP: FLASH already extracted"
    else
        echo "[2/5] Extracting FLASH 4.8..."
        mkdir -p "$FLASH_PARENT" && cd "$FLASH_PARENT" && rm -rf FLASH4.8
        tar -xzf "$AITEMP/$FLASH_TAR"
        echo "[OK] FLASH extracted to $FLASH_HOME"
    fi
    
    # ── Step 3: Configure Makefile.h ──
    if grep -q "^MPI_PATH.*$MPI_PATH" "$FLASH_HOME/Makefile.h" 2>/dev/null; then
        echo "[3/5] SKIP: Makefile.h already configured"
    else
        echo "[3/5] Configuring Makefile.h..."
        TEMPLATE="$FLASH_HOME/sites/Prototypes/Linux/Makefile.h"
        [ ! -f "$FLASH_HOME/Makefile.h" ] && cp "$TEMPLATE" "$FLASH_HOME/Makefile.h"
        sed -i "s|^MPI_PATH\\s*=.*|MPI_PATH = $MPI_PATH|"     "$FLASH_HOME/Makefile.h"
        sed -i "s|^HDF5_PATH\\s*=.*|HDF5_PATH = $HDF5_PATH|"   "$FLASH_HOME/Makefile.h"
        sed -i "s|^HYPRE_PATH\\s*=.*|HYPRE_PATH = $HYPRE_PATH|" "$FLASH_HOME/Makefile.h"
        grep -q "^LIB_LAPACK" "$FLASH_HOME/Makefile.h" || \\
            sed -i "/^HYPRE_PATH/a LIB_LAPACK = -llapack -lblas -lgfortran" "$FLASH_HOME/Makefile.h"
        _sl=$(grep -n "FLASHBINARY" "$FLASH_HOME/Makefile.h" 2>/dev/null | head -1 | cut -d: -f1) || true
        if [ -n "$_sl" ]; then
            _el=$(tail -n +"$_sl" "$FLASH_HOME/Makefile.h" | grep -n "^endif" 2>/dev/null | head -1 | cut -d: -f1) || true
            [ -n "$_el" ] && _el=$((_sl + _el - 1)) && sed -i "$_sl,$_el s/^/#/" "$FLASH_HOME/Makefile.h" || true
        fi
        echo "[OK] Makefile.h configured"
    fi
    
    # ── Step 4: Compile FLASH ──
    if [ -f "$FLASH_HOME/object/flash4" ]; then
        echo "[4/5] SKIP: FLASH already compiled"
    else
        echo "[4/5] Compiling FLASH LaserSlab 1D..."
        export HYPRE_HOME="$HYPRE_PATH"
        export LD_LIBRARY_PATH="$MPI_PATH/lib:$HDF5_PATH/lib:$HYPRE_PATH/lib:${{LD_LIBRARY_PATH:-}}"
        export PATH="$MPI_PATH/bin:$HDF5_PATH/bin:$PATH"
        cd "$FLASH_HOME" && rm -rf object/
        ./setup -auto LaserSlab {setup_args} -objdir=object -parfile=example1d.par 2>&1 | tail -10
        cd object/ && make -j"$(nproc)" 2>&1 | tail -5
        if [ -f flash4 ]; then
            echo "[OK] FLASH compiled successfully!"
        else
            echo "[ERROR] FLASH compilation failed!"
            exit 1
        fi
    fi
    
    # ── Step 5: Run simulation ──
    RUN_DIR="$FLASH_HOME/run_laserslab"
    if ls "$RUN_DIR/"*hdf5_chk_* &>/dev/null 2>&1; then
        _cnt=$(ls "$RUN_DIR/"*hdf5_chk_* 2>/dev/null | wc -l)
        echo "[5/5] SKIP: Simulation already has $_cnt checkpoint files"
    else
        echo "[5/5] Running LaserSlab 1D simulation..."
        rm -rf "$RUN_DIR" && mkdir -p "$RUN_DIR" && cd "$RUN_DIR"
        
        # Copy EOS tables and par file
        SIM_SRC="$FLASH_HOME/source/Simulation/SimulationMain/LaserSlab"
        cp "$SIM_SRC/al-imx-003.cn4" . 2>/dev/null || true
        cp "$SIM_SRC/he-imx-005.cn4" . 2>/dev/null || true
        cp "$SIM_SRC/example1d.par" flash.par
        
        # Run with mpirun
        {module_load}
        export HYPRE_HOME="$HYPRE_PATH"
        export LD_LIBRARY_PATH="$MPI_PATH/lib:$HDF5_PATH/lib:$HYPRE_PATH/lib:${{LD_LIBRARY_PATH:-}}"
        mpirun -np {machine['nproc_run']} "$FLASH_HOME/object/flash4" 2>&1 | tail -20
        
        _cnt=$(ls *hdf5_chk_* 2>/dev/null | wc -l || echo 0)
        if [ "$_cnt" -gt 0 ]; then
            echo "[OK] Simulation complete: $_cnt checkpoint files"
        else
            echo "[ERROR] Simulation failed - no checkpoint files"
        fi
    fi
    
    echo ""
    echo "=== Installation & Simulation Complete ==="
    echo "  FLASH: $FLASH_HOME"
    echo "  Exe:   $FLASH_HOME/object/flash4"
    echo "  Data:  $RUN_DIR"
    """)


# ══════════════════════════════════════════════════════════════
# Deploy Actions
# ══════════════════════════════════════════════════════════════

def deploy_local_wsl(machine: Dict) -> bool:
    """Deploy FLASH on local WSL."""
    step("Deploying FLASH on Local WSL")
    
    # Check tarballs exist
    missing = [t for t in REQUIRED_TARBALLS if not (FLASH_SRC_DIR / t).exists()]
    if missing:
        err(f"Missing tarballs in {FLASH_SRC_DIR}: {', '.join(missing)}")
        err("Please download them first (see README section 'Preparations' b):")
        err("  Download links: see README section 'Preparations' b")
        err("  Recommended: let an Agent AI assistant handle download & adaptation")
        return False
    
    # Generate install script
    script = generate_wsl_install_script(machine)
    script_path = SCRIPT_DIR / "_wsl_install_flash.sh"
    script_path.write_text(script, encoding="utf-8")
    
    info("Running WSL installation script (this may take 30-60 minutes)...")
    stdout, stderr, exit_code = run_wsl_command(f"bash /mnt/{str(script_path).replace(':', '').replace(chr(92), '/')}", timeout=7200)
    
    # Clean up temp script
    script_path.unlink(missing_ok=True)
    
    print(stdout[-2000:] if len(stdout) > 2000 else stdout)
    if stderr and "TIMEOUT" not in stderr:
        print(f"STDERR: {stderr[-500:]}" if len(stderr) > 500 else f"STDERR: {stderr}")
    
    if exit_code != 0:
        err(f"WSL installation failed with exit code {exit_code}")
        return False
    
    # Collect HDF5 results
    step("Collecting HDF5 results from WSL")
    suffix = machine["output_suffix"]
    hdf5_dir_name = f"hdf5files{suffix}"
    local_hdf5_dir = OUTPUT_BASE / hdf5_dir_name / "laserslab1d"
    local_hdf5_dir.mkdir(parents=True, exist_ok=True)
    
    collect_script = f"""
    # 用户名: flash._core.credentials → 默认 hello (勿硬编码)
    FLASH_SIM_USER_DIR="${{FLASH_SIM_USER_DIR:-{get_flash_user_name()}}}"
    FLASH_USER_HOME="${{FLASH_USER_HOME:-$HOME/$FLASH_SIM_USER_DIR}}"
    FLASH_HOME="$FLASH_USER_HOME/FLASH/FLASH4.8"
    RUN_DIR="$FLASH_HOME/run_laserslab"
    OUT_DIR="/mnt/{str(local_hdf5_dir).replace(':', '').replace(chr(92), '/')}"
    
    mkdir -p "$OUT_DIR"
    if ls "$RUN_DIR/"*hdf5_chk_* &>/dev/null 2>&1; then
        cp "$RUN_DIR/"*hdf5_chk_* "$OUT_DIR/"
        cp "$RUN_DIR/"*hdf5_plt_* "$OUT_DIR/" 2>/dev/null || true
        echo "COPIED: $(ls "$OUT_DIR/" | wc -l) files"
    else
        echo "NO_CHK_FILES"
    fi
    """
    stdout, stderr, _ = run_wsl_command(collect_script, timeout=120)
    print(stdout)
    
    return True


def deploy_ssh(machine: Dict) -> bool:
    """Deploy FLASH on remote supercomputer via SSH."""
    cred_name = machine["ssh_credential"]
    step(f"Deploying FLASH on {machine['label']} (credential: {cred_name})")
    
    try:
        client, cred = get_ssh_client(cred_name)
    except Exception as e:
        err(f"SSH connection failed: {e}")
        return False
    
    ok(f"Connected to {cred['username']}@{cred['host']}")
    
    try:
        # Create temp directory
        temp_dir = machine["temp_dir"]
        install_dir = machine["install_dir"]
        
        info("Creating remote directories...")
        run_ssh_command(client, f"mkdir -p {temp_dir} {install_dir}")
        
        # Check if FLASH already exists
        out, _, _ = run_ssh_command(client, f"test -d {install_dir}/FLASH4.8 && echo EXISTS || echo NOT_FOUND")
        if "EXISTS" in out:
            info(f"FLASH directory already exists at {install_dir}/FLASH4.8")
            # Check if flash4 is compiled
            out2, _, _ = run_ssh_command(client, f"test -f {install_dir}/FLASH4.8/object/flash4 && echo COMPILED || echo NOT_COMPILED")
            if "COMPILED" in out2:
                ok("FLASH already compiled on remote machine")
            else:
                info("FLASH extracted but not compiled - will continue setup")
        
        # Upload tarballs
        step("Uploading source tarballs")
        sftp = None
        for tarball in REQUIRED_TARBALLS:
            local_path = FLASH_SRC_DIR / tarball
            if not local_path.exists():
                err(f"Missing tarball: {local_path}")
                return False
            
            remote_path = f"{temp_dir}/{tarball}"
            # Check if already uploaded
            check_out, _, _ = run_ssh_command(client, f"test -f {remote_path} && echo EXISTS || echo NOT_FOUND")
            if "EXISTS" in check_out:
                info(f"  {tarball} already uploaded, skipping")
                continue
            
            info(f"  Uploading {tarball} ({local_path.stat().st_size / 1024 / 1024:.1f} MB)...")
            try:
                if sftp is None:
                    sftp = client.open_sftp()
                sftp.put(str(local_path), remote_path)
                ok(f"  Uploaded: {tarball}")
            except Exception as e:
                err(f"  Upload failed: {e}")
                return False
        
        if sftp:
            sftp.close()
        
        # Generate and upload install script
        step("Running remote installation script")
        install_script = generate_hpc_install_script(machine)
        script_remote_path = f"{temp_dir}/install_flash_hpc.sh"
        
        # Write script via SSH
        escaped = install_script.replace("'", "'\\''")
        run_ssh_command(client, f"cat > {script_remote_path} << 'INSTALLEOF'\n{install_script}\nINSTALLEOF")
        run_ssh_command(client, f"chmod +x {script_remote_path}")
        
        info("Executing installation on remote machine (may take 30-60 minutes)...")
        out, err_out, exit_code = run_ssh_command(client, f"bash {script_remote_path}", timeout=7200)
        
        # Print output (last 2000 chars)
        print(out[-2000:] if len(out) > 2000 else out)
        if err_out:
            print(f"STDERR: {err_out[-500:]}" if len(err_out) > 500 else f"STDERR: {err_out}")
        
        if exit_code != 0:
            warn(f"Remote installation exited with code {exit_code} (may be partial success)")
        
        # Collect HDF5 results
        step("Downloading HDF5 results")
        suffix = machine["output_suffix"]
        hdf5_dir_name = f"hdf5files{suffix}"
        local_hdf5_dir = OUTPUT_BASE / hdf5_dir_name / "laserslab1d"
        
        # Find remote data directory
        remote_data_dir = f"{install_dir}/FLASH4.8/run_laserslab"
        check_out, _, _ = run_ssh_command(client, f"test -d {remote_data_dir} && echo EXISTS || echo NOT_FOUND")
        
        if "EXISTS" in check_out:
            downloaded = ssh_download_dir(client, remote_data_dir, str(local_hdf5_dir), "*hdf5_chk_*")
            # Also download plt files
            ssh_download_dir(client, remote_data_dir, str(local_hdf5_dir), "*hdf5_plt_*")
            ok(f"Downloaded {len(downloaded)} checkpoint files to {local_hdf5_dir}")
        else:
            warn(f"No simulation data found at {remote_data_dir}")
        
        return True
        
    except Exception as e:
        err(f"Remote deployment failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        client.close()


def run_analysis(suffix: str) -> bool:
    """Run density analysis on the collected HDF5 data."""
    step("Running density analysis")
    
    env = os.environ.copy()
    env["FLASH_SOURCE_SUFFIX"] = suffix
    
    analyze_script = SCRIPT_DIR / "analyze_density.py"
    if not analyze_script.exists():
        err(f"Analysis script not found: {analyze_script}")
        return False
    
    try:
        result = subprocess.run(
            [sys.executable, str(analyze_script)],
            env=env, capture_output=True, text=True, timeout=300,
        )
        print(result.stdout[-1000:] if len(result.stdout) > 1000 else result.stdout)
        if result.stderr:
            print(result.stderr[-500:] if len(result.stderr) > 500 else result.stderr)
        return result.returncode == 0
    except Exception as e:
        err(f"Analysis failed: {e}")
        return False


# ══════════════════════════════════════════════════════════════
# Interactive Menu
# ══════════════════════════════════════════════════════════════

def show_banner():
    print(f"\n{C.BOLD}{C.CYAN}")
    print("  ╔══════════════════════════════════════════════════╗")
    print("  ║     FLASH 4.8 One-Click Deploy                  ║")
    print("  ║     LaserSlab 1D Simulation                     ║")
    print(f"  ║     {time.strftime('%Y-%m-%d %H:%M:%S')}                            ║")
    print("  ╚══════════════════════════════════════════════════╝")
    print(f"{C.RESET}")


def show_menu() -> str:
    """Display interactive menu and return selected machine key."""
    print(f"\n{C.BOLD}Select target machine:{C.RESET}\n")
    for key, m in MACHINES.items():
        print(f"  {C.BOLD}[{key}]{C.RESET} {m['label']}")
        print(f"       {m['description']}")
        print(f"       Install: {m['install_dir']}")
        print()
    print(f"  {C.BOLD}[0]{C.RESET} Exit")
    print()
    
    choice = input(f"  {C.BOLD}Your choice [0-3]: {C.RESET}").strip()
    return choice


def confirm_action(machine: Dict) -> bool:
    """Ask for confirmation before proceeding."""
    label = machine["label"]
    print(f"\n  {C.YELLOW}About to deploy FLASH on: {C.BOLD}{label}{C.RESET}")
    print(f"  Install directory: {machine['install_dir']}")
    print(f"  Output suffix: {machine['output_suffix'] or '(none)'}")
    print()
    confirm = input(f"  {C.BOLD}Proceed? [y/N]: {C.RESET}").strip().lower()
    return confirm in ("y", "yes")


def main():
    show_banner()
    
    # Check source tarballs
    info(f"Source tarball directory: {FLASH_SRC_DIR}")
    for t in REQUIRED_TARBALLS:
        path = FLASH_SRC_DIR / t
        if path.exists():
            size_mb = path.stat().st_size / 1024 / 1024
            ok(f"  {t} ({size_mb:.1f} MB)")
        else:
            warn(f"  {t} -- NOT FOUND")
    
    while True:
        choice = show_menu()
        
        if choice == "0" or choice.lower() in ("q", "quit", "exit"):
            print("\n  Bye!")
            return
        
        machine = MACHINES.get(choice)
        if not machine:
            err(f"Invalid choice: {choice}")
            continue
        
        if not confirm_action(machine):
            info("Cancelled.")
            continue
        
        # Execute deployment
        t0 = time.time()
        
        if machine["name"] == "local_wsl":
            success = deploy_local_wsl(machine)
        else:
            success = deploy_ssh(machine)
        
        elapsed = time.time() - t0
        
        if success:
            # Run analysis
            suffix = machine["output_suffix"]
            run_analysis(suffix)
            
            h = int(elapsed // 3600)
            m = int((elapsed % 3600) // 60)
            s = int(elapsed % 60)
            
            print(f"\n{C.BOLD}{C.GREEN}")
            print(f"  ╔══════════════════════════════════════════╗")
            print(f"  ║   Deployment Complete!                   ║")
            print(f"  ║   Elapsed: {h}h {m:02d}m {s:02d}s                   ║")
            print(f"  ╚══════════════════════════════════════════╝")
            print(f"{C.RESET}")
            
            suffix_dir = f"hdf5files{suffix}" if suffix else "hdf5files"
            print(f"  HDF5 files:  {OUTPUT_BASE / suffix_dir / 'laserslab1d'}/")
            print(f"  Plots:       {OUTPUT_BASE / f'plots{suffix}'}/")
        else:
            err(f"Deployment failed after {elapsed:.0f}s")
        
        print()


if __name__ == "__main__":
    main()
