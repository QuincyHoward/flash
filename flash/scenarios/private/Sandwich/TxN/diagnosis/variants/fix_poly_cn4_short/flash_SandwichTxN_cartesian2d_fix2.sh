#!/bin/bash
#SBATCH -p v5_192
#SBATCH --ntasks=48
#SBATCH -t 02:30:00
#SBATCH --account=nc-e
#SBATCH -J flash_SandwichTxN_cartesian2d_fix2
#SBATCH -o /publicfs01/fs1-e/home/scfa2696/PhySimX/PhySimX/simulation/flash/flash_sim/flash_logs/SandwichTxN_cartesian2d/950014/flash_SandwichTxN_cartesian2d_%j.out
#SBATCH -e /publicfs01/fs1-e/home/scfa2696/PhySimX/PhySimX/simulation/flash/flash_sim/flash_logs/SandwichTxN_cartesian2d/950014/flash_SandwichTxN_cartesian2d_%j.out

cd /publicfs01/fs1-e/home/scfa2696/PhySimX/PhySimX/simulation/flash/flash_sim
export PYTHONUNBUFFERED=1
export FL_SHARED_ROOT="/publicfs01/fs1-e/home/scfa2696/PhySimX/PhySimX/simulation/flash/flash_sim"
export FL_SCRATCH_BASE="/tmp"
export FL_SCRATCH_PREFIX="flash_${SLURM_JOB_ID:-$$}"
export FL_OUTPUT_DIR="/publicfs01/fs1-e/home/scfa2696/PhySimX/PhySimX/simulation/flash/flash_sim/flash_output/SandwichTxN_cartesian2d/950014"
export FL_LOG_DIR="/publicfs01/fs1-e/home/scfa2696/PhySimX/PhySimX/simulation/flash/flash_sim/flash_logs/SandwichTxN_cartesian2d/950014"
# ── 探测节点本地快盘（scratch）──
#   判据 = 文件系统类型 tmpfs/ramfs；找不到则回退共享盘（慢但正确）
FL_SCRATCH_LOCAL=0
for cand in "${SLURM_TMPDIR:-}" "/tmp" "/var/tmp" "/dev/shm"; do
  [ -n "$cand" ] || continue
  [ -d "$cand" ] && [ -w "$cand" ] || continue
  _fstype=$(df -T "$cand" 2>/dev/null | tail -1 | awk "{print \$2}")
  case "$_fstype" in
    tmpfs|ramfs) FL_SCRATCH_BASE="$cand"; FL_SCRATCH_LOCAL=1; break;;
  esac
done
[ -n "$FL_SCRATCH_BASE" ] || FL_SCRATCH_BASE="${FL_SHARED_ROOT:-/tmp}"
export FL_SCRATCH_BASE FL_SCRATCH_LOCAL
echo "[layout] scratch base=$FL_SCRATCH_BASE local=$FL_SCRATCH_LOCAL fstype=$_fstype"
export FL_SCRATCH_ROOT="${FL_SCRATCH_BASE}/${FL_SCRATCH_PREFIX}"
export FL_BUILD_DIR="${FL_SCRATCH_ROOT}/flash_build_SandwichTxN_cartesian2d_950014"
if [ "${SLURM_JOB_NUM_NODES:-1}" -gt 1 ]; then
  export FL_RUN_DIR="${FL_SHARED_ROOT}/scratch_run_${SLURM_JOB_ID:-$$}"
  echo "[layout] 多节点作业 ⇒ RUN_DIR 落共享盘 (${FL_RUN_DIR})"
else
  export FL_RUN_DIR="${FL_SCRATCH_ROOT}/flash_run_SandwichTxN_cartesian2d_950014"
fi
mkdir -p "${FL_BUILD_DIR}" "${FL_RUN_DIR}"
mkdir -p "${FL_OUTPUT_DIR}" "${FL_LOG_DIR}"
# ── stage：shared → scratch ──
mkdir -p "${FL_RUN_DIR}"
find "/publicfs01/fs1-e/home/scfa2696/PhySimX/PhySimX/simulation/flash/flash_sim/diagnosis_variants/fix_poly_cn4_short/sim_input_si" -maxdepth 1 -type f  \( -name "*.cn4" -o -name "*.par" \)  -exec cp -f {} "${FL_RUN_DIR}/" \;
echo "[layout] staged $(find "${FL_RUN_DIR}" -maxdepth 1 -type f | wc -l) files → $FL_RUN_DIR"
# ── build：编译（全部在节点本地 scratch）──
mkdir -p "/publicfs01/fs1-e/home/scfa2696/QC/FLASH/FLASH4.8/source/Simulation/SimulationMain/QC/grid_rede"
find "/publicfs01/fs1-e/home/scfa2696/PhySimX/PhySimX/simulation/flash/flash_sim/diagnosis_variants/fix_poly_cn4_short/sim_input_si" -maxdepth 1 -type f \( -name "Config" -o -name "Makefile" -o -name "*.F90" -o -name "*.cn4" -o -name "*.par" \) -exec cp -f {} "/publicfs01/fs1-e/home/scfa2696/QC/FLASH/FLASH4.8/source/Simulation/SimulationMain/QC/grid_rede/" \;
echo "[layout] 源文件就绪: $(find "/publicfs01/fs1-e/home/scfa2696/QC/FLASH/FLASH4.8/source/Simulation/SimulationMain/QC/grid_rede" -maxdepth 1 -type f | wc -l) 个"
FL_MAKE_JOBS="${SLURM_CPUS_PER_TASK:-1}"
[ -n "${SLURM_NTASKS:-}" ] && FL_MAKE_JOBS=$((FL_MAKE_JOBS * ${SLURM_NTASKS}))
[ "${SLURM_JOB_NUM_NODES:-1}" -gt 1 ] && FL_MAKE_JOBS=$((FL_MAKE_JOBS * ${SLURM_JOB_NUM_NODES}))
echo "[layout] make -j$FL_MAKE_JOBS"
cd "/publicfs01/fs1-e/home/scfa2696/QC/FLASH/FLASH4.8"
printf '%s\n' 'Y' | ./setup -auto QC/grid_rede -2d +cartesian -nxb=12 -nyb=8 -maxblocks=8192 +hdf5typeio species=cham,targ,poly +mtmmmt +laser +uhd3t +mgd mgd_meshgroups=10 ed_maxBeams=4 ed_maxPulseSections=240 -parfile=sandwich_txn_cartesian2d.par -objdir="${FL_BUILD_DIR}"
cd "${FL_BUILD_DIR}"
make -j"$FL_MAKE_JOBS" || { echo MAKE_FAIL; exit 3; }
[ -x "${FL_BUILD_DIR}/flash4" ] || { echo BUILD_FAIL_NO_FLASH4; exit 3; }
cp -f "${FL_BUILD_DIR}/flash4" "${FL_RUN_DIR}/"
# ── run：运行（scratch）──
# 运行期环境（禁 mpich 模块：它带 Intel 2018 MPI，会与 oneAPI
# 2022.1 编译产物版本不匹配 ⇒ MPI_Init SIGSEGV）
module purge >/dev/null 2>&1
module load hdf5/1.8.18 >/dev/null 2>&1
export LD_LIBRARY_PATH="/public1/soft/intel/2018/compilers_and_libraries_2018.2.199/linux/mpi/intel64/lib:/opt/slurm/slurm/lib:/public1/soft/hdf5/1.8.18/lib:/public1/soft/oneAPI/2022.1/compiler/2022.0.0/linux/compiler/lib/intel64_lin:/public1/soft/gcc/9.3.0-new/lib64"
export PATH="/public1/soft/intel/2018/compilers_and_libraries_2018.2.199/linux/mpi/intel64/bin:$PATH"
cp -f "${FL_BUILD_DIR}/flash.par" "${FL_RUN_DIR}/flash.par" 2>/dev/null || true
cd "${FL_RUN_DIR}"
srun -n 48 ./flash4
# ── 归档：scratch → shared（只有需要留存的产物才写共享盘）──
shopt -s nullglob
cd "${FL_RUN_DIR}"
for f in *chk* *plt* *.out *.log; do
  [ -f "$f" ] || continue
  cp -f "$f" "${FL_OUTPUT_DIR}/" 2>/dev/null || true
done
shopt -u nullglob
echo "[layout] 归档 $(ls -1 "${FL_OUTPUT_DIR}" 2>/dev/null | wc -l) 个文件 → ${FL_OUTPUT_DIR}"
[ "$(ls -1 "${FL_OUTPUT_DIR}" 2>/dev/null | wc -l)" -gt 0 ] || { echo ARCHIVE_EMPTY_FAIL; exit 4; }
echo FLASH_JOB_DONE
