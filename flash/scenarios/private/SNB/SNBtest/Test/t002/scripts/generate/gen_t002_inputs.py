"""t002 输入生成器 —— 由 common/t002_common.py 的唯一参数源生成两个仿真腿的输入
═══════════════════════════════════════════════════════════════════════════════

用法 (在 t002 目录下):
    python scripts/generate/gen_t002_inputs.py --model both           # 默认网格
    python scripts/generate/gen_t002_inputs.py --model snb --nxb 128 --iprocs 8
    python scripts/generate/gen_t002_inputs.py --model flsh --no-nxb --igridsize 1024

产物 (每腿):
    sim_<model>/flash_input/
        <par>  Config  Makefile  Simulation_data.F90  Simulation_init.F90
        Simulation_initBlock.F90  <2 张 cn4>  run_flash.sh
        pre_diag_laser_pulse.png  pre_diag_initial_density.png
        [+ SNB 腿] 9 个 SNB 覆盖 F90

设计: 两腿的 par 除 model 专属键 (basenm/log_file/diff_eleFlMode/plot_var) 外
必须逐字节相同 —— 本脚本在写盘后自动做逐行 diff 自检并打印结果。
"""

from __future__ import annotations

import argparse
import difflib
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# ── sys.path: t002/common 与仓库根 ───────────────────────────
_T002 = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_T002 / "common"))

import t002_common as C  # noqa: E402

_REPO = C._REPO_ROOT
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

# SNB 覆盖 F90 的本地权威归档目录
_SNB_ARCHIVE = (_REPO / "flash" / "scenarios" / "private" / "tracer" / "SNB"
                / "SNBOneCH" / "flash_input")

# par 中需要剔除的模板键 (单层多示踪靶遗留)
_DEL_PREFIXES = (
    "eos_shld", "op_shld", "ms_shld",
    "eos_samp", "op_samp", "ms_samp",
    "sim_rhoShld", "sim_teleShld", "sim_tionShld", "sim_tradShld",
    "sim_rhoSamp", "sim_teleSamp", "sim_tionSamp", "sim_tradSamp",
    "plot_var", "refine_var", "refine_cutoff", "derefine_cutoff",
    "ed_time_1_", "ed_power_1_", "rt_mgdBounds_",
)
_DEL_KEYS = {
    "basenm", "log_file",
    "sim_shldRadius", "sim_sampRadius", "sim_targetRadius",
    "sim_targetHeight", "sim_sampHeight",
    "ed_numberOfSections_1",
}


# ══════════════════════════════════════════════════════════════
# par 构建
# ══════════════════════════════════════════════════════════════
def build_par_text(model: str, nxb: int, iprocs: int,
                   igridsize: int = 0, tmax: Optional[float] = None,
                   plot_interval_time: Optional[float] = None) -> str:
    """由 CH_FLASH_PAR 模板 + t002 覆写构建 .par 文本。

    仅 model 专属键不同 (basenm / log_file / diff_eleFlMode / plot_var 白名单)。
    """
    from flash.input_gen.gen_par import ParGeneratorExtended
    from flash.scenarios.private.tracer._par_layers import CH_FLASH_PAR

    leg = C.LEGS[model]
    P = C.PARAMS

    tmp = dict(CH_FLASH_PAR)
    for k in list(tmp):
        if k.startswith(_DEL_PREFIXES) or k in _DEL_KEYS:
            del tmp[k]

    g = ParGeneratorExtended(simulation_name=leg["sim_name"], dimension=1)
    g._params.clear()
    for k, v in tmp.items():
        g.set(k, v)

    # ── 几何 / 物种 / 材料 ─────────────────────────────────
    g.set("xmin", P["xmin"])
    g.set("xmax", P["xmax"])
    g.set("geometry", "cartesian")
    g.set("sim_rhoCham", P["cham"]["rho"])
    g.set("sim_rhoTarg", P["targ"]["rho"])
    g.set("ms_chamA", P["cham"]["A"])
    g.set("ms_chamZ", P["cham"]["Z"])
    g.set("ms_targA", P["targ"]["A"])
    g.set("ms_targZ", P["targ"]["Z"])
    g.set("ms_targZMin", P["targ"]["ZMin"])
    for z, mat in (("Cham", P["cham"]), ("Targ", P["targ"])):
        g.set(f"eos_{z.lower()}EosType", "eos_tab")
        g.set(f"eos_{z.lower()}SubType", "ionmix4")
        g.set(f"eos_{z.lower()}TableFile", mat["cn4"])
        g.set(f"op_{z.lower()}Absorb", "op_tabpa")
        g.set(f"op_{z.lower()}Emiss", "op_tabpe")
        g.set(f"op_{z.lower()}Trans", "op_tabro")
        g.set(f"op_{z.lower()}FileType", "ionmix4")
        g.set(f"op_{z.lower()}FileName", mat["cn4"])
        g.set(f"sim_tele{z}", P["t_initial"])
        g.set(f"sim_tion{z}", P["t_initial"])
        g.set(f"sim_trad{z}", P["t_initial"])

    # ── 激光: 4 段梯形波 ──────────────────────────────────
    L = P["laser"]
    g.set("useEnergyDeposition", True)
    g.set("ed_maxRayCount", 10000)
    g.set("ed_gradOrder", 2)
    g.set("ed_useLaserIO", False)
    g.set("ed_laserIOMaxNumberOfPositions", 10000)
    g.set("ed_laserIOMaxNumberOfRays", 128)
    g.set("ed_numberOfPulses", 1)
    g.set("ed_numberOfBeams", 1)
    g.set("ed_numberOfSections_1", L["n_sections"])
    for i, (t, pw) in enumerate(zip(L["times"], L["powers"]), start=1):
        g.set(f"ed_time_1_{i}", t)
        g.set(f"ed_power_1_{i}", pw)
    g.set("ed_lensX_1", L["lensX"])
    g.set("ed_targetX_1", L["targetX"])
    g.set("ed_wavelength_1", L["wavelength_um"])
    g.set("ed_crossSectionFunctionType_1", L["cross_section"])
    g.set("ed_numberOfRays_1", L["n_rays"])
    g.set("ed_gridType_1", L["grid_type"])
    g.set("ed_gridnRadialTics_1", L["n_radial_tics"])
    g.set("ed_pulseNumber_1", 1)

    # ── 辐射 MGD (6 群, 与表族一致) ────────────────────────
    R = P["radiation"]
    g.set("rt_useMGD", R["rt_useMGD"])
    g.set("rt_mgdNumGroups", R["rt_mgdNumGroups"])
    for i, b in enumerate(R["rt_mgdBounds"], start=1):
        g.set(f"rt_mgdBounds_{i}", b)
    g.set("rt_mgdFlMode", R["rt_mgdFlMode"])
    g.set("rt_mgdFlCoef", R["rt_mgdFlCoef"])
    g.set("rt_mgdXlBoundaryType", R["boundary"])
    g.set("rt_mgdXrBoundaryType", R["boundary"])
    g.set("rt_dtFactor", 1.0e100)
    g.set("useOpacity", True)

    # ── 电子热传导 (局部步): 仅限流模式为两腿差异 ─────────
    g.set("useDiffuse", True)
    g.set("useDIffuseTherm", True)
    g.set("useConductivity", True)
    g.set("diff_useEleCond", True)
    g.set("diff_eleFlMode", leg["diff_eleFlMode"])       # ★ 两腿唯一物理差异
    g.set("diff_eleFlCoef", leg["diff_eleFlCoef"])
    g.set("diff_thetaImplct", 1.0)
    g.set("diff_anisoCondForEle", False)                 # SNB 块只在 1D 均匀各向同性生效
    g.set("dt_diff_factor", 1.0e100)
    g.set("useHeatexchange", True)
    g.set("hx_dtFactor", 1.0e100)

    # ── 边界条件 ───────────────────────────────────────────
    for k, v in P["bc"].items():
        g.set(k, v)

    # ── 时间积分 ───────────────────────────────────────────
    T = P["time"]
    g.set("tstep_change_factor", T["tstep_change_factor"])
    g.set("cfl", T["cfl"])
    g.set("dtinit", T["dtinit"])
    g.set("dtmin", T["dtmin"])
    g.set("dtmax", T["dtmax"])
    g.set("nend", 100000000)
    g.set("use_3dFullCTU", True)
    g.set("eos_maxNewton", 5000)
    g.set("tmax", P["tmax"] if tmax is None else tmax)

    # ── +ug 均匀网格 ───────────────────────────────────────
    # 固定块模式: nblockx/lrefine 被 UG 无视 (UG/Config 明文 "ignored by UG Grid"),
    # 置 1 以免 lrefine_min_init > lrefine_max; iProcs 必须等于 mpiexec -n
    g.set("iProcs", iprocs)
    g.set("nblockx", 1)
    g.set("lrefine_max", 1)
    g.set("lrefine_min", 1)
    g.set("lrefine_min_init", 1)
    if not nxb and igridsize:
        # 非固定块模式: par 的 iGridSize 直接给定全局格数
        g.set("iGridSize", igridsize)

    # ── 输出 ───────────────────────────────────────────────
    O = P["output"]
    g.set("basenm", leg["basenm"])
    g.set("log_file", leg["log_file"])
    g.set("plotFileIntervalTime",
          O["plotFileIntervalTime"] if plot_interval_time is None else plot_interval_time)
    g.set("checkpointFileIntervalTime", O["checkpointFileIntervalTime"])
    g.set("plotFileNumber", 0)
    g.set("checkpointFileNumber", 0)
    g.set("restart", False)
    _pv = C.PLOT_VARS_SNB if leg["has_snb"] else C.PLOT_VARS_BASE
    for i, v in enumerate(_pv, start=1):
        g.set(f"plot_var_{i}", f"{v:<4s}")

    return _postprocess_par(g.generate())


def _postprocess_par(text: str) -> str:
    """清理 ParGeneratorExtended 头部的固定占位行。

    gen_par/build 头部硬编码了 `log_file = "lasslab.log"` / `basenm = "lasslab_"`
    (generator.py:375-376), 与场景实际值**重复**。SNBOneCH 实测 FLASH 取后者,
    但重复键有歧义风险 → 直接注释掉头部占位行。
    同时把 step 触发式 IO 间隔置为极大值, 使 plt/chk 只由时间触发
    (IO_output.F90:367 为 "time OR step" 双触发)。
    """
    out: List[str] = []
    for line in text.splitlines():
        s = line.lstrip()
        if s.startswith('log_file') and "lasslab.log" in line:
            out.append("# " + line + "   # [t002] 占位行, 实际值见文末")
            continue
        if s.startswith("basenm") and "lasslab_" in line:
            out.append("# " + line + "   # [t002] 占位行, 实际值见文末")
            continue
        if s.startswith("plotFileIntervalStep"):
            out.append("# " + line + "   # [t002] 关闭 step 触发, 只用 plotFileIntervalTime")
            continue
        if s.startswith("checkpointFileIntervalStep"):
            out.append("# " + line + "   # [t002] 关闭 step 触发, 只用 checkpointFileIntervalTime")
            continue
        out.append(line)
    return "\n".join(out) + "\n"


# ══════════════════════════════════════════════════════════════
# 输入文件生成
# ══════════════════════════════════════════════════════════════
def _copy_cn4(filename: str, alias: str, dest: Path) -> bool:
    """按 注册表别名 → eos_op_data 递归 → 旧仓库兜底 的顺序复制 cn4 表。"""
    from flash.input_gen.gen_eos_op import EOSOpacityGenerator
    dst = EOSOpacityGenerator().copy_eos_file(alias, dest)
    if dst is not None and Path(dst).exists():
        return True
    data_root = _REPO / "flash" / "input_gen" / "gen_eos_op" / "eos_op_data"
    for cand in data_root.rglob(filename):
        shutil.copyfile(cand, dest / filename)
        C.log(f"    {filename} ← {cand.relative_to(data_root)}")
        return True
    legacy = _REPO.parent / "flash_c" / "flash" / "input_gen" / "gen_eos_op" / "eos_op_data"
    if legacy.is_dir():
        for cand in legacy.rglob(filename):
            shutil.copyfile(cand, dest / filename)
            C.log(f"    {filename} ← 旧仓库兜底", "WARN")
            return True
    C.log(f"    {filename} 缺失", "ERROR")
    return False


def _write_run_flash_sh(model: str, nxb: int, iprocs: int,
                        igridsize: int = 0) -> None:
    """生成 flash_input/run_flash.sh (WSL 手动一键流水线, 强制 LF)。"""
    leg = C.LEGS[model]
    inp = C.leg_input_dir(model)
    flags = C.setup_flags(nxb if nxb else None)
    setup_cmd = f"./setup -auto {leg['sim_name']} {flags} -objdir={leg['objdir']}"
    out = C.leg_output_dir(model)

    if model == "snb":
        tree_line = ('SNB_HOME="${SNB_HOME:-$(find "$HOME" -maxdepth 4 -type d '
                     '-name FLASHSNB 2>/dev/null | head -1)/FLASH4.8}"')
        tree_var = "SNB_HOME"
    else:
        tree_line = 'FLASH_HOME="${FLASH_HOME:-$(ls -d "$HOME"/*/FLASH/FLASH4.8 2>/dev/null | head -1)}"'
        tree_var = "FLASH_HOME"

    deploy_block = ""
    if model == "snb":
        overrides = " ".join(C.SNB_OVERRIDE_FILES)
        deploy_block = f"""
# 0) 树级 physics 补丁 (t001 六补丁基线中的 #3/#4; 幂等)
T001="$SCRIPT_DIR/../../../Test/t001/source_patches"
for rel in {' '.join(C.TREE_PATCHES)}; do
  if [ ! -f "${tree_var}/source/$rel" ] && [ -f "$T001/$rel" ]; then
    mkdir -p "${tree_var}/source/$(dirname "$rel")"
    cp -f "$T001/$rel" "${tree_var}/source/$rel"
    echo "  patch synced: $rel"
  fi
done

# 1) 部署单元: 生成件 + cn4 + 9 个 SNB 覆盖 F90
mkdir -p "$UNIT"
cp -f "$SCRIPT_DIR"/Config "$SCRIPT_DIR"/Makefile \\
      "$SCRIPT_DIR"/Simulation_data.F90 "$SCRIPT_DIR"/Simulation_init.F90 \\
      "$SCRIPT_DIR"/Simulation_initBlock.F90 "$SCRIPT_DIR"/*.cn4 "$UNIT"/ || exit 1
for f in {overrides}; do cp -f "$SCRIPT_DIR/$f" "$UNIT/$f" || exit 1; done
echo "  unit deployed: $UNIT"
"""
        make_prefix = ("make hy_slopeLimiters.o Conductivity_interface.o "
                       "Conductivity_fullState.o 2>&1 | tail -3; ")
        make_cmd = "make -j4"
    else:
        make_prefix = ""
        make_cmd = "make -j4"

    igs_block = ""
    if not nxb and igridsize:
        igs_block = (f'\n# 非固定块模式: 全局格数由 par 的 iGridSize={igridsize} 给定\n'
                     f'grep -q "^iGridSize" "$OBJ/flash.par" || '
                     f'echo "iGridSize = {igridsize}" >> "$OBJ/flash.par"')

    sh = f"""#!/usr/bin/env bash
# t002 {leg['label']} one-click pipeline (WSL) — generated by gen_t002_inputs.py
# Env switches: SKIP_DEPLOY=1 SKIP_SETUP=1 SKIP_MAKE=1 TMAX=2.0e-10 NPROC={iprocs}
# 网格: +ug {'固定块模式 -nxb=' + str(nxb) if nxb else '非固定块模式 iGridSize=' + str(igridsize)}
set -u
{tree_line}
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OBJ="${tree_var}/{leg['objdir']}"
UNIT="${tree_var}/source/Simulation/SimulationMain/{leg['sim_name']}"
NPROC="${{NPROC:-{iprocs}}}"
echo "== t002 {leg['label']} ({tree_var}=${tree_var}, +ug NPROC=$NPROC) =="
{deploy_block}
# 2) setup (+ug 均匀网格)
if [ -z "${{SKIP_SETUP:-}}" ]; then
  cd "${tree_var}" && rm -rf "$OBJ"
  {setup_cmd} 2>&1 | tail -15 || exit 1
  [ -d "$OBJ" ] || {{ echo "setup failed"; exit 1; }}
  echo "  setup done"
fi
[ -d "$OBJ" ] || {{ echo "objdir missing, run setup first"; exit 1; }}{igs_block}

# 3) make
if [ -z "${{SKIP_MAKE:-}}" ]; then
  cd "$OBJ"
  {make_prefix}if {make_cmd} > make_t002.log 2>&1; then echo "  MAKE_OK"; else echo "  MAKE_FAIL"; tail -20 make_t002.log; exit 1; fi
  [ -x flash4 ] || {{ echo "flash4 not built"; exit 1; }}
  echo "  build done"
fi

# 4) run
cp -f "$SCRIPT_DIR/{leg['par_file']}" "$OBJ/flash.par" || exit 1
if [ -n "${{TMAX:-}}" ]; then
  sed -i "s/^tmax.*/tmax           = $TMAX/" "$OBJ/flash.par"
fi
cd "$OBJ" && rm -f {leg['basenm']}* wsl_run_{leg['model']}.log
if mpiexec -n "$NPROC" ./flash4 > wsl_run_{leg['model']}.log 2>&1; then
  echo "RUN_EXIT=0" >> wsl_run_{leg['model']}.log
else
  echo "RUN_EXIT_NZ" >> wsl_run_{leg['model']}.log
fi
tail -4 wsl_run_{leg['model']}.log

# 5) collect (WSL 侧输出用后即清)
COLLECT="${{FLASH_COLLECT_DIR:-{C.wsl_path(out)}}}"
mkdir -p "$COLLECT"
cp -f "$OBJ"/{leg['basenm']}* "$OBJ"/wsl_run_{leg['model']}.log "$OBJ"/{leg['log_file']} "$COLLECT"/ 2>/dev/null
rm -f "$OBJ"/{leg['basenm']}*
echo "  collected to $COLLECT"
echo "== pipeline done =="
"""
    (inp / "run_flash.sh").write_text(sh, encoding="utf-8", newline="\n")


def generate(model: str, nxb: int, iprocs: int, igridsize: int = 0,
             tmax: Optional[float] = None,
             plot_interval_time: Optional[float] = None) -> Dict[str, str]:
    """生成单腿的全部输入文件到 sim_<model>/flash_input/。"""
    from flash.input_gen.gen_config import ConfigGenerator
    from flash.input_gen.gen_makefile import MakefileGenerator
    from flash.input_gen.gen_sim_data import SimDataGenerator
    from flash.input_gen.gen_sim_init import SimInitGenerator
    from flash.input_gen.gen_sim_initblock import BlockGenerator, GridBuilder

    leg = C.LEGS[model]
    P = C.PARAMS
    inp = C.leg_input_dir(model)
    inp.mkdir(parents=True, exist_ok=True)
    res: Dict[str, str] = {}

    C.log(f"【{leg['label']}】输入生成 → {inp}", "STEP")

    # 1. par
    par_text = build_par_text(model, nxb, iprocs, igridsize, tmax, plot_interval_time)
    par_path = inp / leg["par_file"]
    par_path.write_text(par_text, encoding="utf-8", newline="\n")
    res["par"] = str(par_path)
    n_cells = iprocs * nxb if nxb else igridsize
    dx = C.dx_um(nxb, iprocs) if nxb else C.dx_um_from_igridsize(igridsize)
    C.log(f"    .par → {par_path.name}  ({n_cells} 格, dx≈{dx:.4f} µm, "
          f"iProcs={iprocs}, nxb={nxb or 'N/A'})", "OK")

    # 2. Config
    species_defs = [
        {"name": "cham", "file": P["cham"]["cn4"], "rho": P["cham"]["rho"],
         "A": P["cham"]["A"], "Z": P["cham"]["Z"]},
        {"name": "targ", "file": P["targ"]["cn4"], "rho": P["targ"]["rho"],
         "A": P["targ"]["A"], "Z": P["targ"]["Z"]},
    ]
    cfg_path = ConfigGenerator().save(
        str(inp / "Config"), simulation_path=leg["sim_name"],
        species_defs=species_defs)
    if leg["has_snb"]:
        txt = Path(cfg_path).read_text(encoding="utf-8", newline="\n")
        Path(cfg_path).write_text(txt.rstrip("\n") + "\n" + C.SNB_CONFIG_VARIABLES,
                                  encoding="utf-8", newline="\n")
    res["config"] = str(cfg_path)
    C.log(f"    Config ✓{f' (+{C.SNB_CONFIG_VARIABLES.count(chr(86)+chr(65)+chr(82)+chr(73)+chr(65)+chr(66)+chr(76)+chr(69))} SNB VARIABLE)' if leg['has_snb'] else ''}")

    # 3. Makefile
    if leg["has_snb"]:
        mk = ("# t002 SNB Simulation unit makefile\n"
              "# mgd_qesh.o: SNB 多群 SH 热流权重 (FLASHSNB 专用, 无同名 physics 文件)\n"
              "Simulation += Simulation_data.o mgd_qesh.o\n")
        (inp / "Makefile").write_text(mk, encoding="utf-8", newline="\n")
    else:
        MakefileGenerator().save(str(inp / "Makefile"), sim_path=leg["sim_name"])
    res["makefile"] = str(inp / "Makefile")

    # 4/5. Simulation_data.F90 / Simulation_init.F90
    SimDataGenerator().save(str(inp / "Simulation_data.F90"), species=species_defs)
    SimInitGenerator().save(str(inp / "Simulation_init.F90"),
                            params={"species": species_defs})

    # 6. Simulation_initBlock.F90: 2 物种 2 区 (x<0 cham 兜底 / x>=0 targ)
    builder = GridBuilder(dim=1, geometry="cartesian", domain=(P["xmin"], P["xmax"]))
    for sp in species_defs:
        builder.set_material(sp["name"], rho=sp["rho"], tele=P["t_initial"],
                             tion=P["t_initial"], trad=P["t_initial"])
    builder.add_region("targ_main", species="targ",
                       x_range=(P["interface_x"], P["xmax"]))
    BlockGenerator(simulation_name=leg["sim_name"], sim_path=leg["sim_name"],
                   species=P["species"]).build(builder).save(
        str(inp / "Simulation_initBlock.F90"))
    res["sim_initblock"] = str(inp / "Simulation_initBlock.F90")
    C.log(f"    Simulation_initBlock.F90 ({len(builder.regions)} 区, "
          f"cham 兜底 / targ x≥{P['interface_x']:g}) ✓")

    # 7. cn4 表
    ok = True
    for key in ("cham", "targ"):
        m = P[key]
        if not _copy_cn4(m["cn4"], m["alias"], inp):
            ok = False
    if not ok:
        C.log("EOS/opacity 表不齐, FLASH 将 abort", "ERROR")
        return res

    # 8. SNB 覆盖 F90
    if leg["has_snb"]:
        n_ok = 0
        for f in C.SNB_OVERRIDE_FILES:
            src = _SNB_ARCHIVE / f
            if src.exists():
                shutil.copyfile(src, inp / f)
                n_ok += 1
            else:
                C.log(f"    {f} 归档缺失 (部署时从 WSL 参考单元复制)", "WARN")
        res["overrides"] = str(n_ok)
        C.log(f"    SNB 覆盖 F90 归档 {n_ok}/{len(C.SNB_OVERRIDE_FILES)} ✓")

    # 9. run_flash.sh + 预诊断图
    _write_run_flash_sh(model, nxb, iprocs, igridsize)
    res["script_wsl"] = str(inp / "run_flash.sh")
    try:
        import numpy as np
        from flash.input_gen.gen_checker.ploter import PulsePlotter, DensityPlotter
        L = P["laser"]
        PulsePlotter().plot_pulse(
            np.array(L["times"]) * 1e9, np.array(L["powers"]),
            title=f"Laser Pulse (trapezoid, {L['n_sections']} sections)",
            save_path=inp / "pre_diag_laser_pulse.png",
            beam_label=f"Beam 1 ({L['wavelength_um']*1000:.0f} nm)")
        xs, dens1d, _ = builder.sample_1d(n_points=4000)
        DensityPlotter().plot_1d(
            xs, dens1d, region_boundaries=[("targ (CH)", P["interface_x"])],
            title=f"Initial Density ({leg['label']}: He|CH interface at x=0)",
            save_path=inp / "pre_diag_initial_density.png")
        res["pre_diag"] = str(inp / "pre_diag_initial_density.png")
        C.log("    预诊断图 (laser pulse + initial density) ✓")
    except Exception as exc:  # noqa: BLE001
        C.log(f"预诊断图失败 (不影响仿真): {exc}", "WARN")

    return res


# ══════════════════════════════════════════════════════════════
# 两腿 par 一致性自检
# ══════════════════════════════════════════════════════════════
_ALLOWED_DIFF_KEYS = {"basenm", "log_file", "diff_eleFlMode", "diff_eleFlCoef"}


def _par_kv(path: Path) -> Dict[str, str]:
    kv: Dict[str, str] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        s = line.split("#", 1)[0].strip()
        if not s or "=" not in s:
            continue
        k, v = s.split("=", 1)
        kv[k.strip()] = v.strip()
    return kv


def check_consistency() -> bool:
    """自检: 两腿 par 的差异只允许出现在 model 专属键上。"""
    a = _par_kv(C.leg_input_dir("flsh") / C.LEGS["flsh"]["par_file"])
    b = _par_kv(C.leg_input_dir("snb") / C.LEGS["snb"]["par_file"])
    only_a = {k: v for k, v in a.items() if k not in b}
    only_b = {k: v for k, v in b.items() if k not in a}
    diff = {k: (a[k], b[k]) for k in a if k in b and a[k] != b[k]}
    bad = []
    for k in list(only_a) + list(only_b):
        # plot_var_N 白名单允许 SNB 腿多出 SNB 诊断量; iGridSize 仅非固定块模式存在
        if k.startswith("plot_var"):
            continue
        if k not in _ALLOWED_DIFF_KEYS and k != "iGridSize":
            bad.append(f"仅存在于一腿: {k}")
    for k in diff:
        # plot_var 白名单允许不同 (SNB 腿多 8 个诊断量)
        if k.startswith("plot_var"):
            continue
        if k not in _ALLOWED_DIFF_KEYS:
            bad.append(f"值不同: {k}: {diff[k][0]!r} vs {diff[k][1]!r}")
    print("\n  ── 两腿 par 一致性自检 ─────────────────────────────")
    print(f"    FL-SH 键数 = {len(a)},  SNB 键数 = {len(b)}")
    for k in sorted(diff):
        if k.startswith("plot_var"):
            continue
        flag = "OK  " if k in _ALLOWED_DIFF_KEYS else "!!  "
        print(f"    {flag}{k}: {diff[k][0]!r} → {diff[k][1]!r}")
    for k in sorted(set(only_a) ^ set(only_b)):
        if k.startswith("plot_var"):
            print(f"    OK  plot_var 白名单差异: {k}")
            continue
        print(f"    {'OK  ' if k in _ALLOWED_DIFF_KEYS else '!!  '}仅一腿: {k}")
    if bad:
        for m in bad:
            C.log(f"一致性自检不合格: {m}", "ERROR")
        return False
    C.log("两腿 par 一致 (差异仅限 model 专属键) ✓", "OK")
    return True


# ══════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════
def main() -> int:
    ap = argparse.ArgumentParser(description="t002 输入生成器 (SNB vs FL-SH)")
    ap.add_argument("--model", choices=["flsh", "snb", "both"], default="both")
    ap.add_argument("--nxb", type=int, default=None,
                    help=f"固定块模式每块格数 (默认 {C.GRID['nxb']}); 0 = 非固定块模式")
    ap.add_argument("--iprocs", type=int, default=None,
                    help=f"+ug 块数 = MPI 进程数 (默认 {C.GRID['iprocs']})")
    ap.add_argument("--igridsize", type=int, default=None,
                    help="非固定块模式的全局格数 (仅 nxb=0 时生效)")
    ap.add_argument("--tmax", type=float, default=None,
                    help=f"覆写 tmax (s); 默认 {C.PARAMS['tmax']:.1e}")
    ap.add_argument("--plot-interval-time", type=float, default=None,
                    help="覆写 plotFileIntervalTime (s)")
    args = ap.parse_args()

    nxb = C.GRID["nxb"] if args.nxb is None else int(args.nxb)
    iprocs = C.GRID["iprocs"] if args.iprocs is None else int(args.iprocs)
    igs = C.GRID["iGridSize"] if args.igridsize is None else int(args.igridsize)
    if not nxb and not igs:
        igs = iprocs * C.GRID["nxb"]      # 非固定块模式缺省 = 默认总格数

    print("\n" + "=" * 72)
    print(f" t002 输入生成器  {C.stamp()}")
    print(f" 域 [{C.PARAMS['xmin']}, {C.PARAMS['xmax']}] cm  "
          f"({(C.PARAMS['xmax']-C.PARAMS['xmin'])*1e4:.0f} µm)")
    if nxb:
        print(f" 网格 +ug 固定块: nxb={nxb}, iProcs={iprocs} → "
              f"{iprocs*nxb} 格, dx≈{C.dx_um(nxb, iprocs):.4f} µm")
    else:
        print(f" 网格 +ug 非固定块: iGridSize={igs}, iProcs={iprocs} → "
              f"{igs} 格, dx≈{C.dx_um_from_igridsize(igs):.4f} µm")
    print("=" * 72)

    models = ["flsh", "snb"] if args.model == "both" else [args.model]
    for m in models:
        generate(m, nxb, iprocs, igs, args.tmax, args.plot_interval_time)

    if len(models) == 2:
        return 0 if check_consistency() else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
