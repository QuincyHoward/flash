"""VTi_oldstyle —— 按 VTi_old（ReDo042sp_CH042sp{1,2,3}um8.00e-02）原样重建 VTi 系列。

设计原则
--------
以旧算例的 `flash.par` + 三个 `Simulation_*.F90` 为**唯一真源**（存于 `ref/`），
只把 `sim_sampRadius`（前置 CH 层厚度，即"1/2/3 µm"所指）改成对应值，
其余键（几何、AMR、输出节奏、激光脉冲表、材料表）逐字节保持旧算例取值。
→ 目的是让新 VTi 与 VTi_old 成为**同一算例**，只差层厚。

旧算例层结构（1D slab，激光自 -x 入射）
--------------------------------------
    x < 0                 : cham (He, 1e-6 g/cm^3)
    0      .. 0.1 um      : shld (V,  6.11)          sim_shldRadius = 1e-5 cm
    0.1    .. 0.1+S um     : samp (CH, 1.0)           sim_sampRadius = S（1/2/3 µm）
    0.1+S  .. 0.1+S+0.1   : targ (Ti, 4.54)          sim_targetRadius = 1e-5 cm
    0.1+S+0.1 .. +50 um   : samp (CH, 1.0)           sim_sampHeight = 5e-3 cm

用法
----
    python build_vti_oldstyle.py --gen-only              # 只生成三套输入
    python build_vti_oldstyle.py --depth 2 --submit      # 上传并提交 2 µm
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent            # VTi_oldstyle
REF = HERE / "ref"
TRACER = HERE.parent
ROOT = HERE
while ROOT != ROOT.parent and not (ROOT / "pyproject.toml").exists():
    ROOT = ROOT.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEPTHS = {1: 1.0e-4, 2: 2.0e-4, 3: 3.0e-4}        # sim_sampRadius [cm] = 1/2/3 µm
SIM_USER_DIR = "QC"

# 旧算例 tmax = 1.6 ns。本轮按用户要求延到 2.5 ns（激光脉冲本身到 2.209 ns，
# 故 2.5 ns 仍包含完整驱动 + 约 0.3 ns 的后续演化）。
# 只改终止时刻与计算域，不动任何物理/输出节奏参数 ⇒ 与旧算例在其未被边界污染
# 的时段内仍逐时刻可比。
TMAX_S = 2.5e-9

# ── 计算域（本轮唯一额外偏离旧 par 的部分）────────────────────────────
# 用户要求：负半轴推到约 −500 µm；分辨率必须与旧算例**完全相同**。
#
# 旧算例：xmin=-2.5e-2 cm(-250µm)  xmax=7.5e-3 cm(+75µm)  W=325µm  nblockx=8
#         dx_base = 325/(8*16)  = 2.5390625 µm
#         dx_min  = dx_base/2^7 = 0.019836 µm   (lrefine_max=8)
#
# AMR 的 dx 只由 W/(nblockx*nxb) 与 lrefine 决定，所以"扩域 + 保持 dx"必须同时改
# nblockx。取 W_new = 650 µm = 2×325 ⇒ nblockx 8→16，dx 比值恒等于 1.000000。
#   xmin = -500 µm（按用户要求）
#   xmax = +150 µm —— 右侧也必须扩：旧算例 CH/激波前沿在 1.495 ns 已到 74.96 µm
#          （即贴着 +75 µm 墙），若仍用 75，2.5 ns 的结果会被出流边界污染。
#          +150 µm 是同一 dx 下能取的整数块解，且在激波到达前与原解逐位相同。
XMIN_CM = -5.0e-2
XMAX_CM = 1.5e-2
NBLOCKX = 16
NXB = 16
LREFINE_MAX = 8

# 场景名后缀：新系列与旧的 1.6 ns / −250 µm 算例必须分开目录，避免混帧。
TAG = "L500"

# 块数上限：旧算例峰值 228 块（t≤1.6 ns）；域加倍 + 跑 2.5 ns 后波面覆盖更广，
# 留 2000 作为容量余量。★ maxblocks 只是数组容量，不参与任何物理/网格判据，
# 改动它不改变结果（旧 1000 亦足够，此处仅防 2.5 ns 触发 "maxblocks exceeded"）。
MAXBLOCKS = 2000
FLASH_SUBDIR = "FLASH/FLASH4.8"
CN4_NAMES = ["CH-QC-1-001.cn4", "He-BADGER-TOPS-Final.cn4",
             "Ti-BADGER-TOPS.cn4", "V-BADGER-TOPS.cn4"]
# cn4 正本分散在两个目录（CH 只在 ionmix 源码树里, He/Ti/V 在 eos_op_data）,
# 故按候选目录顺序查找, 全部按字节复制, 不做任何重命名。
CN4_DIRS = [
    TRACER.parents[2] / "input_gen" / "gen_eos_op" / "eos_op_data" / "Others_data",
    TRACER.parents[2] / "input_gen" / "gen_eos_op" / "ionmix" / "ionmix" / "src" / "Ionmix",
]
F90_NAMES = ["Simulation_data.F90", "Simulation_init.F90", "Simulation_initBlock.F90",
             "Grid_markRefineDerefine.F90", "Grid_markRefineSpecialized.F90"]

# ★ 必需: 旧 runfiles 未保存 Config, 而 setup 的 "变量表/单元集" 由它决定。
#   缺 Config 时: (a) Diffuse/Conductivity 不被 REQUESTS 引入 → Flash.h 无 COND_VAR
#   → RadTrans 编译报 "COND_VAR does not have a type"; (b) SimulationMain 的
#   sim_*/ms_*/eos_*/op_* 参数不被声明 → 运行期 "cannot locate real runtime
#   parameter sim_foamRadius"。两个坑 2026-10-20 均实测踩到。
#   下面 REQUESTS 段与当前 VTi 管线同源; PARAMETER 段从旧 build 的 setup_params
#   (setup 自己导出的权威参数表) 机械重建, 只保留 SimulationMain 私有前缀,
#   以免与 Eos/Opacity 单元自身声明冲突。
REQUESTS_BLOCK = """REQUIRES Driver
REQUIRES physics/Hydro

USESETUPVARS ThreeT

IF ThreeT
   REQUESTS physics/Diffuse/DiffuseMain/Unsplit

   REQUESTS physics/sourceTerms/Heatexchange/HeatexchangeMain/Spitzer
   REQUESTS physics/materialProperties/Conductivity/ConductivityMain/SpitzerHighZ
ENDIF

DATAFILES He-BADGER-TOPS-Final.cn4
DATAFILES V-BADGER-TOPS.cn4
DATAFILES CH-QC-1-001.cn4
DATAFILES Ti-BADGER-TOPS.cn4
"""

SPECIES = ("cham", "samp", "shld", "targ")
_PARAM_RE = re.compile(r"^\s{4}([A-Za-z_]\w*)\s+\[(REAL|STRING|BOOLEAN|INTEGER)\]\s+\[(.*?)\]\s*$")


def _is_sim_param(name: str) -> bool:
    if name.startswith("sim_"):
        return True
    return any(name.startswith(f"{p}_{sp}") for p in ("ms", "eos", "op") for sp in SPECIES)


def config_text() -> str:
    """由 ref/setup_params 重建 SimulationMain Config。"""
    lines = [REQUESTS_BLOCK.rstrip(), "", "#", "# SimulationMain 私有运行参数 (源自旧 build 的 setup_params)",
             "#"]
    n = 0
    for raw in (REF / "setup_params").read_text(encoding="utf-8", errors="replace").splitlines():
        m = _PARAM_RE.match(raw)
        if not m or not _is_sim_param(m.group(1)):
            continue
        name, typ, default = m.group(1), m.group(2), m.group(3).strip()
        lines.append(f"PARAMETER {name} {typ} {default}")
        n += 1
    if n < 150:
        raise RuntimeError(f"Config 参数重建过少 ({n} 个), setup_params 解析异常")
    return "\n".join(lines) + "\n"


def scene(depth: int) -> str:
    return f"VTi{depth}{TAG}"


def dx_table() -> dict[str, float]:
    """当前计算域的分辨率表（用于自检与文档）。"""
    w = XMAX_CM - XMIN_CM
    dxb = w / (NBLOCKX * NXB)
    return {"W_um": w * 1e4, "dx_base_um": dxb * 1e4,
            "dx_min_um": dxb * 1e4 / 2 ** (LREFINE_MAX - 1)}


def input_dir(depth: int) -> Path:
    return HERE / "flash_input" / scene(depth)


def output_dir() -> Path:
    return HERE / "flash_output"


# ── par 生成 ────────────────────────────────────────────

def make_par(depth: int) -> str:
    """旧 flash.par 逐字节继承，只替换 sim_sampRadius / run_comment / tmax / 计算域。

    计算域三项（xmin, xmax, nblockx）必须**成组**修改，否则 dx 会变；见模块顶部
    的推导。这里同时做一次 dx 断言，防止日后改一漏一。
    """
    txt = (REF / "flash.par").read_text(encoding="utf-8", errors="replace")
    samp = DEPTHS[depth]
    new, n = re.subn(r"^sim_sampRadius\s*=\s*\S+",
                     f"sim_sampRadius = {samp:.9e}", txt, count=1, flags=re.M)
    if n != 1:
        raise RuntimeError("sim_sampRadius 未找到，模板异常")

    for key, val in (("xmin", XMIN_CM), ("xmax", XMAX_CM)):
        new, n = re.subn(rf"^({key}\s*=\s*)\S+",
                         lambda m, v=val: f"{m.group(1)}{v:.9e}",
                         new, count=1, flags=re.M)
        if n != 1:
            raise RuntimeError(f"{key} 未找到，模板异常")
    new, n = re.subn(r"^(nblockx\s*=\s*)\S+",
                     lambda m: f"{m.group(1)}{NBLOCKX}", new, count=1, flags=re.M)
    if n != 1:
        raise RuntimeError("nblockx 未找到，模板异常")

    new = re.sub(r"^run_comment\s*=\s*\".*?\"",
                 f'run_comment = "VTi_oldstyle {depth}um (clone of ReDo042sp_CH042sp{depth}um8.00e-02, '
                 f'xmin={XMIN_CM*1e4:g}um xmax={XMAX_CM*1e4:g}um, tmax={TMAX_S*1e9:g}ns)"',
                 new, count=1, flags=re.M)
    new, n = re.subn(r"^tmax\s*=\s*\S+", f"tmax = {TMAX_S:.9e}", new, count=1, flags=re.M)
    if n != 1:
        raise RuntimeError("tmax 未找到，模板异常")

    # ★ 分辨率自检：与旧算例（W=325 µm, nblockx=8, nxb=16, lrefine=8）逐位一致
    ref_dxb = 3.25e-2 / (8 * NXB)
    got_dxb = (XMAX_CM - XMIN_CM) / (NBLOCKX * NXB)
    if abs(got_dxb / ref_dxb - 1.0) > 1e-12:
        raise RuntimeError(
            f"分辨率不匹配: dx_base {got_dxb*1e4:.9f} um vs 旧算例 {ref_dxb*1e4:.9f} um "
            f"(比值 {got_dxb/ref_dxb:.12f})；xmin/xmax/nblockx 必须成组调整")
    return new


def layer_table(depth: int) -> list[tuple[str, float, float, float]]:
    """(名称, x_lo[um], x_hi[um], rho)  —— 与旧 initBlock 的 bound1..bound5 一致。"""
    b1 = 0.0
    b2 = b1 + 0.1                       # sim_shldRadius = 1e-5 cm = 0.1 um
    b3 = b2 + DEPTHS[depth] * 1e4       # sampRadius
    b4 = b3 + 0.1                       # targetRadius = 0.1 um
    b5 = b4 + 5.0e-3 * 1e4              # sampHeight = 50 um
    return [("He (cham)", XMIN_CM * 1e4, b1, 1e-6),
            ("V (shld)", b1, b2, 6.11),
            ("CH (samp)", b2, b3, 1.0),
            ("Ti (targ)", b3, b4, 4.54),
            ("CH (samp)", b4, b5, 1.0),
            ("He (cham)", b5, XMAX_CM * 1e4, 1e-6)]


def parse_pulse(par: str) -> tuple[list[float], list[float]]:
    t = {int(m.group(1)): float(m.group(2)) for m in
         re.finditer(r"^ed_time_1_(\d+)\s*=\s*([-+0-9.eE]+)", par, re.M)}
    p = {int(m.group(1)): float(m.group(2)) for m in
         re.finditer(r"^ed_power_1_(\d+)\s*=\s*([-+0-9.eE]+)", par, re.M)}
    idx = sorted(t)
    return [t[i] for i in idx], [p.get(i, 0.0) for i in idx]


# ── 预诊断图 ────────────────────────────────────────────

def plot_diag(depth: int, par: str, out_png: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    plt.rcParams.update({"font.family": "Times New Roman", "font.size": 20,
                         "axes.labelsize": 22, "axes.titlesize": 22,
                         "xtick.labelsize": 18, "ytick.labelsize": 18,
                         "legend.fontsize": 17})
    layers = layer_table(depth)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 7.5), layout="constrained")

    xs, ys = [], []
    for name, lo, hi, rho in layers:
        if hi <= lo:
            continue
        xs += [lo, hi]
        ys += [rho, rho]
    ax1.semilogy(xs, ys, lw=2.6, color="#1f4e79")
    ax1.set_xlim(-3, 5)
    ax1.set_ylim(1e-7, 20)
    ax1.set_xlabel("x ($\\mu$m)")
    ax1.set_ylabel("Density (g/cm$^3$)")
    ax1.set_title(f"Initial density — VTi_oldstyle {depth} $\\mu$m")
    ax1.grid(alpha=0.35, which="both")
    for name, lo, hi, rho in layers:
        if hi > lo and rho > 1e-3:
            ax1.text((lo + hi) / 2, rho * 1.6, name, ha="center", va="bottom", fontsize=16)

    tt, pp = parse_pulse(par)
    ax2.plot([t * 1e9 for t in tt], pp, lw=2.6, color="#c00000")
    ax2.set_xlabel("Time (ns)")
    ax2.set_ylabel("Laser power (W/cm$^2$)")
    ax2.set_title("Laser pulse (82 sections)")
    ax2.grid(alpha=0.35)
    ax2.set_ylim(0, max(pp) * 1.15)

    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=130)
    plt.close(fig)


# ── 提交脚本 ────────────────────────────────────────────

def make_submit_sh(depth: int) -> str:
    name = scene(depth)
    objdir = f"{SIM_USER_DIR}/LaserSlab_{name}"
    setup = (f"./setup -auto {objdir} -1d +cartesian -nxb={NXB} +hdf5typeio "
             f"species=cham,targ,shld,samp +mtmmmt +laser +uhd3t +mgd "
             f"mgd_meshgroups=10 ed_maxPulseSections=300 "
             f"-maxblocks={MAXBLOCKS} -objdir={objdir} -parfile=flash.par")
    return f"""#!/bin/bash
#SBATCH --job-name={name}
#SBATCH -p v5_192
#SBATCH -N 1
#SBATCH --ntasks=7
#SBATCH --output={name}_out.txt
#SBATCH --error={name}_err.txt

set -e

echo "[1/6] Loading environment modules..."
module purge
module load mpich/3.2-gcc9.3
module load hdf5/1.8.18
source /public1/soft/oneAPI/2022.1/setvars.sh >/dev/null 2>&1 || true

FLASH_HOME="$HOME/{SIM_USER_DIR}/{FLASH_SUBDIR}"
PAR_FILE="flash.par"
OBJ_DIR="{objdir}"
FLASH_BIN="$FLASH_HOME/$OBJ_DIR/flash4"
SETUP_CMD="{setup}"
BUILD_CORES=32
SIM_PATH="{objdir}"

SCRIPT_DIR="${{SLURM_SUBMIT_DIR:-$PWD}}"

echo ""
echo "[2/6] Copying source files to SimulationMain..."
SIM_SRC_DIR="$FLASH_HOME/source/Simulation/SimulationMain/$SIM_PATH"
mkdir -p "$SIM_SRC_DIR"
cp "$SCRIPT_DIR"/Config "$SIM_SRC_DIR"/ 2>/dev/null || true
cp "$SCRIPT_DIR"/Makefile "$SIM_SRC_DIR"/ 2>/dev/null || true
cp "$SCRIPT_DIR"/Simulation_*.F90 "$SIM_SRC_DIR"/ 2>/dev/null || true
cp "$SCRIPT_DIR"/Grid_*.F90 "$SIM_SRC_DIR"/ 2>/dev/null || true
cp "$SCRIPT_DIR"/*.cn4 "$SIM_SRC_DIR"/ 2>/dev/null || true
cp "$SCRIPT_DIR/$PAR_FILE" "$SIM_SRC_DIR"/ 2>/dev/null || true
echo "  Source files ready in SimulationMain."

echo ""
echo "[3/6] Checking and compiling FLASH..."
cd "$FLASH_HOME"
if [ -d "$OBJ_DIR" ] && [ -f "$FLASH_BIN" ]; then
    echo "  Binary exists, skipping setup+make."
else
    echo "  No usable binary — wiping stale objdir before setup..."
    rm -rf "$OBJ_DIR"
    echo "  Running setup..."
    eval $SETUP_CMD
    echo "  Setup done. Compiling..."
    cd $OBJ_DIR
    make -j$BUILD_CORES
    echo "  Compilation done."
fi

echo ""
echo "[4/6] Copying input files..."
cd "$FLASH_HOME/$OBJ_DIR"
cp "$SCRIPT_DIR/$PAR_FILE" ./ 2>/dev/null || true
cp "$SCRIPT_DIR"/*.cn4 ./ 2>/dev/null || true
echo "  Input files ready."

echo ""
echo "[5/7] Cleaning stale frames/logs left by any previous run in objdir..."
# ★ 必须清理: 上一轮(含被 scancel 的)会留下 lasslab.log 与半截 chk/plt,
#   末尾的 mv 会把它们和新产物混到一个 outputfiles_* 里, 且轮询步数会读到旧 log。
rm -f lasslab_hdf5_chk_* lasslab_hdf5_plt_cnt_* lasslab_forced_hdf5_plt_cnt_* \\
      lasslab*.log lasslab*.h5 flash_run.log 2>/dev/null || true
echo "  objdir cleaned: $(ls lasslab* 2>/dev/null | wc -l) leftover lasslab* files"

echo ""
echo "[6/7] Running FLASH simulation (mpiexec)..."
TOTAL_TASKS=${{SLURM_NTASKS:-4}}
mpiexec -n $TOTAL_TASKS $FLASH_BIN -par_file $PAR_FILE 2>&1 | tee flash_run.log
FLASH_EXIT=${{PIPESTATUS[0]}}
echo "  FLASH exit code: $FLASH_EXIT"

echo ""
echo "[7/7] Collecting output files..."
OUTPUT_DIR="$SCRIPT_DIR/outputfiles_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$OUTPUT_DIR"
mv *.h5 *chk* *plt* flash_run.log "$OUTPUT_DIR"/ 2>/dev/null || true

echo ""
echo "=== Summary ==="
echo "  Output dir: $OUTPUT_DIR"
echo "  HDF5 files: $(ls "$OUTPUT_DIR"/*.h5 2>/dev/null | wc -l)"
echo "  FLASH exit:  $FLASH_EXIT"
echo "=== Done ==="

exit $FLASH_EXIT
"""


def make_run_sh(depth: int) -> str:
    name = scene(depth)
    objdir = f"{SIM_USER_DIR}/LaserSlab_{name}"
    return f"""#!/bin/bash
# 本地 WSL 快速运行 (setup + make + mpirun)
set -e
FLASH_HOME="$HOME/{SIM_USER_DIR}/{FLASH_SUBDIR}"
OBJ_DIR="{objdir}"
cd "$FLASH_HOME"
SIM_SRC_DIR="$FLASH_HOME/source/Simulation/SimulationMain/$OBJ_DIR"
mkdir -p "$SIM_SRC_DIR"
cp Simulation_*.F90 Grid_*.F90 *.cn4 flash.par Makefile "$SIM_SRC_DIR"/ 2>/dev/null || true
[ -d "$OBJ_DIR" ] || ./setup -auto {objdir} -1d +cartesian -nxb={NXB} +hdf5typeio \\
  species=cham,targ,shld,samp +mtmmmt +laser +uhd3t +mgd mgd_meshgroups=10 \\
  ed_maxPulseSections=300 -maxblocks={MAXBLOCKS} -objdir={objdir} -parfile=flash.par
cd "$OBJ_DIR"
[ -x flash4 ] || make -j8
mpirun -n 1 ./flash4 -par_file flash.par
"""


# ── 生成一套输入 ────────────────────────────────────────

def gen_case(depth: int) -> Path:
    out = input_dir(depth)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    par = make_par(depth)
    (out / "flash.par").write_text(par, encoding="utf-8", newline="\n")

    for f in F90_NAMES:
        shutil.copy2(REF / f, out / f)
    (out / "Config").write_text(config_text(), encoding="utf-8", newline="\n")
    # SimulationMain 的 Makefile 片段（只声明额外模块）
    (out / "Makefile").write_text("Simulation += Simulation_data.o\n",
                                  encoding="utf-8", newline="\n")
    for c in CN4_NAMES:
        src = next((d / c for d in CN4_DIRS if (d / c).exists()), None)
        if src is None:
            raise FileNotFoundError(
                f"{c} 在候选目录中均未找到: " + ", ".join(str(d) for d in CN4_DIRS))
        shutil.copy2(src, out / c)

    (out / "submit_flash.sh").write_text(make_submit_sh(depth), encoding="utf-8", newline="\n")
    (out / "run_flash.sh").write_text(make_run_sh(depth), encoding="utf-8", newline="\n")

    plot_diag(depth, par, out / "pre_diag_initial.png")

    lines = [f"# {scene(depth)} 层结构 (1D slab, 激光自 -x 入射)", ""]
    for name, lo, hi, rho in layer_table(depth):
        lines.append(f"  {name:<12} x = {lo:8.3f} .. {hi:8.3f} um   rho = {rho:.4g} g/cm^3")
    lines.append("")
    lines.append(f"  sim_sampRadius = {DEPTHS[depth]:.9e} cm  (= {depth} um, 前置 CH 层)")
    d = dx_table()
    lines += ["",
              "  ── 计算域 / 分辨率（与旧算例 dx 完全相同）──",
              f"  xmin = {XMIN_CM*1e4:8.2f} um   xmax = {XMAX_CM*1e4:8.2f} um   "
              f"W = {d['W_um']:6.1f} um",
              f"  nblockx = {NBLOCKX}  nxb = {NXB}  lrefine_max = {LREFINE_MAX}",
              f"  dx_base = {d['dx_base_um']:.7f} um   dx_min = {d['dx_min_um']:.6f} um",
              f"  tmax = {TMAX_S*1e9:g} ns  （旧算例 1.6 ns；激光脉冲到 2.209 ns）",
              "  旧算例: xmin=-250 um / xmax=+75 um / nblockx=8 / dx_base=2.5390625 um"]
    (out / "LAYERS.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[gen] {out}  ({len(list(out.iterdir()))} 个文件)")
    return out


# ── 上传 + 提交 ─────────────────────────────────────────

def hpc_spec(depth: int):
    from flash.scenarios.core.runner import HpcSpec, user_flash_home
    name = scene(depth)
    home = user_flash_home()
    return HpcSpec(
        name=name,
        input_dir=input_dir(depth),
        output_dir=output_dir(),
        plots_dir=HERE / "plots",
        objdir=f"{SIM_USER_DIR}/LaserSlab_{name}",
        flash_home=home,
        work_base=f"{home}/AI/Aitemp",
        remote_analysis_script=f"{name}_remote_analysis.py",
        remote_analysis_cmd=lambda d: f"ls {d}",
        state_file=f"hpc_task_{name}.json",
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gen-only", action="store_true")
    ap.add_argument("--depth", type=int, choices=[1, 2, 3], default=2)
    ap.add_argument("--upload", action="store_true")
    ap.add_argument("--submit", action="store_true")
    args = ap.parse_args()

    for d in (args.gen_only and [1, 2, 3]) or [args.depth]:
        gen_case(d)

    if args.gen_only:
        return 0

    from flash.scenarios.core.runner import HpcRunner
    runner = HpcRunner(hpc_spec(args.depth))
    if args.upload:
        runner.upload()
    if args.submit:
        runner.submit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
