#!/usr/bin/env python3
"""_probe_mpihello.py — oneAPI MPI 自洽性决定性实验（最小 Fortran MPI 程序）。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from flash._core.paths import hpc_home_required as _hpc_home_req
_RH = _hpc_home_req()  # 超算家目录：运行期解析，绝不硬编码

from flash.scenarios.flash_demo.demo_hpc.remote_ssh_helper import RemoteSession

MPI = "/public1/soft/oneAPI/2022.1/mpi/latest"
SRC = ("program h\n"
       "  use mpi\n"
       "  integer :: ierr, rank\n"
       "  call MPI_Init(ierr)\n"
       "  call MPI_Comm_rank(MPI_COMM_WORLD, rank, ierr)\n"
       "  if (rank == 0) print *, 'MPI_HELLO_OK'\n"
       "  call MPI_Finalize(ierr)\n"
       "end program h\n")

with RemoteSession("flash_ssh") as s:
    s.run("mkdir -p /tmp/mpihello", timeout=30)
    s.run(f"cat > /tmp/mpihello/h.f90 << 'EOF'\n{SRC}EOF", timeout=30)
    tests = [
        ("compile", f"cd /tmp/mpihello && {MPI}/bin/mpiifort h.f90 -o h 2>&1 | tail -2; echo RC=$?"),
        ("run_login_2p", f"cd /tmp/mpihello && {MPI}/bin/mpiexec -n 2 ./h 2>&1 | tail -3; echo RC=$?"),
        ("run_sbatch_2p",
         f"cd /tmp/mpihello && printf '#!/bin/bash\\n#SBATCH -p v5_192\\n#SBATCH -N 1\\n"
         f"#SBATCH --ntasks=2\\n#SBATCH -o mpihello.out\\n"
         f"cd /tmp/mpihello && {MPI}/bin/mpiexec -n 2 ./h\\n' > job.sh && "
         f"sbatch job.sh 2>&1 | tail -1"),
    ]
    for name, cmd in tests:
        out, err, rc = s.run(cmd, timeout=300)
        print(f"== {name} == {(out or '').strip()[-200:]}")
    import time
    time.sleep(45)
    out, _, _ = s.run("cat /tmp/mpihello/mpihello.out 2>/dev/null | tail -5; sacct -j $(ls /tmp/mpihello 2>/dev/null) 2>/dev/null | head -1", timeout=60)
    print("== job out ==")
    print((out or "").strip()[:400])
    s.run("rm -rf /tmp/mpihello", timeout=30)
