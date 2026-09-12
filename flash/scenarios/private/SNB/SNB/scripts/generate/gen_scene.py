#!/usr/bin/env python3
"""SNB 场景生成器 —— 以 SNB/SNB 为核心模块生成完整场景输入
═══════════════════════════════════════════════════════════════════════════════

**本脚本不含任何 F90 源码文本** —— 它只做 **文件复制 + par 生成 + 自检**，
因此属于"可分享的 py 脚本"（分享规则见 docs/06）。

它把三件事收敛到一处（用户需求：生成场景 / F90 代码复制都在 SNB/SNB 下）：

  1. **F90 代码复制**：从 `source/snb_package/`（作者实现包）与
     `source/stock_sh/`（限流 SH 参考版）**复制**到目标场景的 `flash_input/`；
     可选地把 `variants/` 下的诊断变体覆盖到对应文件上。
  2. **表复制**：从 `source/tables/` 复制 EOS/opacity 表。
  3. **par 生成**：以 `scripts/snb_params.py` 的推荐值为基线，
     叠加场景覆写（腿标识 / 网格 / 时间 / 辐射三开关 / plot_var 白名单）。

两条腿的受控性由脚本自动断言（`--check`）：
**同侧两腿只应差 腿标识 + 辐射三开关；跨侧只应差 腿标识。**

用法
----
    # 生成 SNB 场景 (SNB 腿 + 限流 SH 对照腿)
    python scripts/generate/gen_scene.py --out <目标场景目录>

    # 只生成 SNB 腿; 指定网格与时间
    #   ★★ dtmax 必须 2e-14 (2e-12 会非物理崩塌, 见 docs/08)
    python scripts/generate/gen_scene.py --out ../my_scene --legs snb \
        --nxb 128 --iprocs 8 --tmax 0.8e-9 --dtmax 2.0e-14

    # 2×2 辐射矩阵 (每腿生成 开/关 两个 par; F90 共用)
    python scripts/generate/gen_scene.py --out ../my_scene \
        --radiation both --driver-variant radon

    # 受控性自检
    python scripts/generate/gen_scene.py --out ../my_scene --check-only

★ 判据铁律 (docs/08_故障案例_SNB崩塌.md)
--------------------------------------
`dtmax` 是否生效**不能看 par 文本**(会被命令行覆写), 必须读 chk 里
`real scalars` 的 `dt` 实测值:  全程钉死在常数 = 生效; 随步进增长 = 必崩。
"""

from __future__ import annotations

import argparse
import filecmp
import re
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_SNB_DIR = Path(__file__).resolve().parents[2]          # .../SNB/SNB
sys.path.insert(0, str(_SNB_DIR / "scripts"))

import snb_params as P  # noqa: E402

SOURCE = _SNB_DIR / "source"
VARIANTS = _SNB_DIR / "variants"

# 作者的 9 个覆盖 F90
SNB_F90: Tuple[str, ...] = P.__dict__.get("SNB_F90") or (
    "diff_advanceTherm.F90", "Conductivity.F90", "Driver_evolveFlash.F90",
    "Grid_advanceDiffusion.F90", "hy_uhd_DataReconstructNormalDir_PPM.F90",
    "hy_uhd_dataReconstOneStep.F90", "hy_uhd_getRiemannState.F90",
    "hy_uhd_ragelike.F90", "mgd_qesh.F90",
)
# 两腿共享件 (逐字节相同 → 保证受控)
SHARED = ("Config", "Makefile", "Simulation_data.F90", "Simulation_init.F90",
          "Simulation_initBlock.F90", "mgd_qesh.F90")
# 腿差异件: SNB 腿用作者版; 限流 SH 腿按 --flsh-mode 处理
DIFF_THERM = "diff_advanceTherm.F90"

# 诊断变体: 变体文件 → 目标文件名
VARIANT_MAP = {
    "limiter": ("diff_advanceTherm_limiterON.F90", DIFF_THERM),
    "radon": ("Driver_evolveFlash_radON.F90", "Driver_evolveFlash.F90"),
}

LEG_SPECS: Dict[str, Dict[str, Any]] = {
    "snb": {"has_snb": True, "basenm": "snb_", "log_file": "snb.log",
            "par": "snb.par", "sim_name": "SNB_SCENE", "objdir": "SNB_SCENE_obj"},
    "flsh": {"has_snb": False, "basenm": "flsh_", "log_file": "flsh.log",
             "par": "flsh.par", "sim_name": "FLSH_SCENE", "objdir": "FLSH_SCENE_obj"},
}


def log(msg: str, level: str = "INFO") -> None:
    tag = {"INFO": "[i]", "OK": "[OK]", "WARN": "[!]", "ERROR": "[X]",
           "STEP": "[-]"}.get(level, "[i]")
    print(f"  {tag} {msg}", flush=True)


# ══════════════════════════════════════════════════════════════
# par 生成
# ══════════════════════════════════════════════════════════════
def _fmt(v: Any) -> str:
    """把 Python 值格式化为 par 文本。

    ★ 精度要求: 中间量级 (1e-3 .. 1e5) 的浮点**必须保留有效位**。
      早先用 `%g` 只有 6 位有效数字, 会把
      `290.11375 → 290.114`、`4.002602 → 4.0026` —— 虽影响极小,
      但会让从零生成的场景与权威基线**逐位不等**, 妨碍"同配置复现"核对。
      → 改用 `%.10g`: 既保留精度又避免科学计数法噪音。
    """
    if isinstance(v, bool):
        return ".true." if v else ".false."
    if isinstance(v, float):
        return f"{v:.10e}" if (v and abs(v) < 1e-3) or (v and abs(v) > 1e5) else f"{v:.10g}"
    if isinstance(v, str):
        return f'"{v}"'
    return str(v)


def build_par(leg: str, args, radiation_on: bool, species: List[str],
              rad_tag: str = "") -> str:
    """基线 = snb_params 推荐值; 叠加场景覆写。

    Args:
        rad_tag: 辐射状态标记 ("radon"/"radoff")。非空时用于区分
            par 文件名与输出前缀 —— 2×2 矩阵下同一腿要跑辐射开/关两次，
            **两者必须有不同的 basenm/log_file**，否则输出互相覆盖。
    """
    spec = LEG_SPECS[leg]
    basenm = f"{leg}_{rad_tag}_" if rad_tag else spec["basenm"]
    log_file = f"{leg}_{rad_tag}.log" if rad_tag else spec["log_file"]
    p: Dict[str, Any] = {}
    p.update(P.GEOMETRY)
    p.update(P.HYDRO_EOS)          # ★ 必须: 缺小温度/EOS/斜率限制器会启动即失稳
    p.update(P.RADIATION)
    p.update(P.CONDUCTION)
    p.update(P.TIME)
    p.update(P.OUTPUT)

    # ★ rt_mgdBounds 在参数表里是**列表** → 必须展开成 rt_mgdBounds_1..N+1
    #   (直接 _fmt(list) 会写成一行 Python 列表字面量 → FLASH 报
    #    "MGD Error: Bad group boundary")
    bounds = p.pop("rt_mgdBounds", None)
    if bounds:
        n_grp = int(p.get("rt_mgdNumGroups", len(bounds) - 1))
        if len(bounds) != n_grp + 1:
            log(f"rt_mgdBounds 个数 {len(bounds)} != N+1 ({n_grp}+1)", "WARN")
        for i, b in enumerate(bounds, start=1):
            p[f"rt_mgdBounds_{i}"] = float(b)

    # ★★ 边界条件键名必须**展开**, 不能留占位名:
    #   · 参数表里的 "boundary" 不是合法 par 键 → 会被 FLASH 忽略,
    #     辐射边界退回默认, 导致能量收支错误 (实测 SNB 腿 CH 靶被打散、
    #     Te_max 达 3372 eV, 而 FL-SH 仅 1650 eV)。
    mgd_bc = p.pop("boundary", "vacuum")
    for d_ in ("Xl", "Xr", "Yl", "Yr", "Zl", "Zr"):
        p[f"rt_mgd{d_}BoundaryType"] = mgd_bc
    # 电子热传导边界 (示例 par 为全 neumann; 缺失会用默认 → 边界能量流异常)
    for d_ in ("Xl", "Xr", "Yl", "Yr", "Zl", "Zr"):
        p[f"diff_ele{d_}BoundaryType"] = "neumann"

    # 激光
    L = P.LASER
    p["ed_numberOfPulses"] = 1
    p["ed_numberOfBeams"] = 1
    p["ed_numberOfSections_1"] = L["n_sections"]
    for i, (t, w) in enumerate(zip(L["times"], L["powers"]), start=1):
        p[f"ed_time_1_{i}"] = t
        p[f"ed_power_1_{i}"] = w
    p["ed_lensX_1"] = L["lensX"]
    p["ed_targetX_1"] = L["targetX"]
    p["ed_wavelength_1"] = L["wavelength_um"]
    p["ed_crossSectionFunctionType_1"] = L["cross_section"]
    p["ed_numberOfRays_1"] = L["n_rays"]
    p["ed_gridType_1"] = L["grid_type"]
    p["ed_gridnRadialTics_1"] = L["n_radial_tics"]
    # ★ 必须把 beam 1 绑定到 pulse 1, 否则 "ed_setupBeams: invalid pulse number!"
    p["ed_pulseNumber_1"] = 1
    p["useEnergyDeposition"] = True
    p["ed_maxRayCount"] = 10000
    p["ed_gradOrder"] = 2

    # 辐射开关 (关 = 三开关全 false)
    p.update(P.RADIATION_OFF if not radiation_on else {})

    # ★ 场景覆写
    p["xmin"] = args.xmin
    p["xmax"] = args.xmax
    p["tmax"] = args.tmax
    p["dtmax"] = args.dtmax
    p["iProcs"] = args.iprocs
    # ★ 电子限流模式 (默认取 snb_params.CONDUCTION)。
    #   在 SNB 场景下该键实测为 **no-op** —— 见上方 snb_params.CONDUCTION 注释
    #   与 docs/05 坑位清单 P1 更正块; 默认 fl_none 属项目约定。
    flm = getattr(args, "ele_fl_mode", None)
    if flm:
        p["diff_eleFlMode"] = flm
    p["nblockx"] = 1
    p["lrefine_max"] = p["lrefine_min"] = p["lrefine_min_init"] = 1
    p["checkpointFileIntervalTime"] = args.chk_dt
    p["plotFileIntervalTime"] = args.plt_dt
    p["basenm"] = basenm
    p["log_file"] = log_file
    p["restart"] = False
    p["checkpointFileNumber"] = 0
    p["plotFileNumber"] = 0

    # 物种/材料
    for sp in species:
        m = P.SPECIES.get(sp)
        if m is None:
            log(f"物种 {sp} 无材料定义, 跳过材料绑定", "WARN")
            continue
        cap = sp.capitalize()
        p[f"sim_rho{cap}"] = m["rho"]
        p[f"sim_tele{cap}"] = P.T_INITIAL
        p[f"sim_tion{cap}"] = P.T_INITIAL
        p[f"sim_trad{cap}"] = P.T_INITIAL
        p[f"ms_{sp}A"] = m["A"]
        p[f"ms_{sp}Z"] = m["Z"]
        if m.get("ZMin") is not None:
            p[f"ms_{sp}ZMin"] = m["ZMin"]
        p[f"eos_{sp}EosType"] = "eos_tab"
        p[f"eos_{sp}SubType"] = "ionmix4"
        p[f"eos_{sp}TableFile"] = m["cn4"]
        p[f"op_{sp}Absorb"] = "op_tabpa"
        p[f"op_{sp}Emiss"] = "op_tabpe"
        p[f"op_{sp}Trans"] = "op_tabro"
        p[f"op_{sp}FileType"] = "ionmix4"
        p[f"op_{sp}FileName"] = m["cn4"]

    # 输出
    lines: List[str] = [
        "# " + "=" * 76,
        f"# SNB 场景 par —— leg = {leg} (SNB={spec['has_snb']}, "
        f"辐射={'开' if radiation_on else '关'})",
        "# 由 scripts/generate/gen_scene.py 生成; 基线值来自 scripts/snb_params.py",
        "# " + "=" * 76,
    ]
    for k, v in p.items():
        lines.append(f"{k:<40} = {_fmt(v)}")
    lines.append("")
    lines.append("# ── 输出白名单 (≤12 项, 从 1 连续编号; 第 13 项起静默忽略) ──")
    pv = ["dens", "tele", "tion", "trad", "pele", "pres", "depo", "cond",
          "cham", "tar1", "tar2", "tar3"][:12]
    for i, v in enumerate(pv, start=1):
        lines.append(f'plot_var_{i:<2d} = "{v}"')
    lines.append("")
    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════
# 文件复制
# ══════════════════════════════════════════════════════════════
def _need(p: Path) -> bool:
    if not p.exists():
        log(f"缺少源文件: {p}", "ERROR")
        return False
    return True


def deploy_leg(leg: str, out_dir: Path, args, radiation_on: bool,
               species: List[str], rad_tag: str = "") -> Dict[str, Any]:
    """部署一条腿。

    ★ rad_tag 非空时 ("radon"/"radoff"):
      - par 文件名 = `<leg>_<rad_tag>.par`（F90 仍共用同一份 → 受控）
      - basenm/log_file 带 rad_tag → 两次运行的输出不互相覆盖
      - **不重复复制 F90**（同腿两状态共用同一 flash_input）
    """
    spec = LEG_SPECS[leg]
    inp = out_dir / f"sim_{leg}" / "flash_input"
    inp.mkdir(parents=True, exist_ok=True)
    res: Dict[str, Any] = {"dir": str(inp)}

    pkg = SOURCE / "snb_package"
    stock = SOURCE / "stock_sh"
    tables = SOURCE / "tables"
    if not _need(pkg):
        return res

    # ★ F90 覆盖件每次生成都按出处重写 (幂等覆盖), 不做 "已存在就跳过" 短路:
    #   2×2 下同一腿会先写 rad_tag 版本、再写另一状态; 若上一轮残留了诊断变体
    #   (如 radON 版 Driver_evolveFlash.F90), 短路会导致 --driver-variant none
    #   无法把文件回滚为作者原版 → 场景目录被静默污染 (实测 t005 踩坑:
    #   scene 内 18425 B/radON 残留, 而核心模块原版应为 18443 B)。
    #   覆盖件总量 ≤ 十几 KiB, 重写成本可忽略, 换取确定性。
    #   par / 表 (cn4) 各自有独立的存在性判据, 不受此处影响。
    _copy_f90 = True
    if _copy_f90:
        for f in SHARED:
            s = pkg / f
            if _need(s):
                shutil.copyfile(s, inp / f)

        if spec["has_snb"]:
            s = pkg / DIFF_THERM
            if _need(s):
                shutil.copyfile(s, inp / DIFF_THERM)
            for f in SNB_F90:
                if f in SHARED or f == DIFF_THERM:
                    continue
                s = pkg / f
                if _need(s):
                    shutil.copyfile(s, inp / f)
        else:
            if args.flsh_mode == "stock":
                s = stock / DIFF_THERM
                if _need(s):
                    shutil.copyfile(s, inp / DIFF_THERM)
                log("限流 SH 腿: 部署 stock_sh 参考版覆盖件", "OK")
            else:
                p = inp / DIFF_THERM
                if p.exists():
                    p.unlink()
                log("限流 SH 腿: 无覆盖件 (用标准树原生实现)", "OK")

        # 诊断变体覆盖 (仅 SNB 腿)
        applied: List[str] = []
        if spec["has_snb"]:
            for key, attr in (("limiter", "therm_variant"), ("radon", "driver_variant")):
                if getattr(args, attr, "none") != key:
                    continue
                vname, target = VARIANT_MAP[key]
                vp = VARIANTS / vname
                if not vp.exists():
                    log(f"变体缺失: {vp} (先跑 tools_local/make_variants.py)", "ERROR")
                    continue
                shutil.copyfile(vp, inp / target)
                applied.append(f"{key}→{target}")
        if applied:
            log(f"已应用诊断变体: {', '.join(applied)}", "WARN")

        # 表
        for m in P.SPECIES.values():
            t = tables / m["cn4"]
            if _need(t) and not (inp / m["cn4"]).exists():
                shutil.copyfile(t, inp / m["cn4"])

    # par (每次调用都写; 2×2 下两条腿各写 radon/radoff 两个 par)
    par_name = f"{leg}_{rad_tag}.par" if rad_tag else spec["par"]
    par_text = build_par(leg, args, radiation_on, species, rad_tag)
    (inp / par_name).write_text(par_text, encoding="utf-8", newline="\n")

    n = len([f for f in inp.iterdir() if f.is_file()])
    log(f"[{leg}{('/' + rad_tag) if rad_tag else ''}] {par_name} 已写; "
        f"flash_input 共 {n} 文件 (辐射{'开' if radiation_on else '关'}, "
        f"SNB={spec['has_snb']})", "OK")
    res["n_files"] = n
    res["par"] = par_name
    return res


# ══════════════════════════════════════════════════════════════
# 受控性自检
# ══════════════════════════════════════════════════════════════
ALLOWED_PAR_DIFF = {"basenm", "log_file", "rt_useMGD", "useOpacity", "useRadTrans",
                    "plot_var_1", "plot_var_2", "plot_var_3", "plot_var_4",
                    "plot_var_5", "plot_var_6", "plot_var_7", "plot_var_8",
                    "plot_var_9", "plot_var_10", "plot_var_11", "plot_var_12"}


def _kv(p: Path) -> Dict[str, str]:
    d: Dict[str, str] = {}
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        s = line.split("#", 1)[0].strip()
        if s and "=" in s:
            k, v = s.split("=", 1)
            d[k.strip()] = v.strip()
    return d


def _par_kv(p: Path) -> Dict[str, str]:
    d: Dict[str, str] = {}
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        s = line.split("#", 1)[0].strip()
        if s and "=" in s:
            k, v = s.split("=", 1)
            d[k.strip()] = v.strip()
    return d


# 允许"示例有而生成没有"的无关键前缀 (IO/AMR/单位/注释类)
#
# ★★★ 2026-09-12 血泪修正: 本清单**不得**纳入任何可能影响数值解的键。
#   事故: `gr_hypreUseFloor` 曾被列在此处 → 键集校验报"0 缺"通过,
#         但该键(FLASH 默认 .true., 应为 .false.)使 SNB 多群热流
#         经 HYPRE 求解器时解失真 → ρmax 冲高后崩塌 (ρmax 12.1 → 0.25)。
#   判据: 只有**确定不参与物理解算**的键才可忽略 —— 即
#         ① 输出/IO 开关 (ed_useLaserIO, ed_laserIOMax*)
#         ② 单位制脚手架 (UnitSystem, pc_unitsBase) —— 本场景 par 不带单位标注, 实测无影响
#         ③ AMR 细化键 (+ug 下被忽略: refine_var*, lrefine*)
#         ④ 命名/注释 (basenm, log_file, run_comment)
#     `tmax` 亦在此列(由命令行/场景覆写管理), 但**会单独核对**。
#   ⚠ 新增忽略项前必须做 A/B 实测, 证明其对 ρmax/守恒 无影响。
_KEY_DIFF_IGNORE = ("plot_var", "rt_mgdBounds", "ed_time_1_", "ed_power_1_",
                    "basenm", "log_file", "tmax", "UnitSystem", "pc_unitsBase",
                    "run_comment", "refine_var", "lrefine", "ed_useLaserIO",
                    "ed_laserIOMax")

# ★ 数值敏感键白名单: 这些键**必须**出现在生成的 par 中, 否则直接报错
#   (即使它们因某种原因被加进了 _KEY_DIFF_IGNORE 也会被本清单拦下)
NUMERIC_CRITICAL_KEYS = (
    "gr_hypreUseFloor",      # ★ HYPRE 扩散求解器 floor → SNB 热流正确性
    "diff_eleFlMode",
    "diff_eleFlCoef",
    "diff_thetaImplct",
    "dt_diff_factor",
    "dtmax",
    "rt_mgdNumGroups",
)


def verify_keys_against(ref_par: Path, out_dir: Path,
                        entries: List[Tuple[str, str, str]]) -> bool:
    """★ 键集差分校验: 生成 par 若缺"示例 par 中有"的物理相关键 → 报错。

    教训: 从零生成 par 极易漏掉"看似与主题无关、实则决定稳定性/守恒"的键
    (实例: 缺 rt_mgd*/diff_ele* 边界键 → SNB 腿 CH 靶被打散, Te 达 3372 eV)。
    """
    if not ref_par.exists():
        log(f"参考 par 不存在: {ref_par}", "ERROR")
        return False
    ref = _par_kv(ref_par)
    print("\n  ── par 键集差分校验 (对照参考 par) ────────────────")
    print(f"    参考: {ref_par.name} ({len(ref)} 键)")
    ok = True
    for label, leg, par in entries:
        p = out_dir / f"sim_{leg}" / "flash_input" / par
        if not p.exists():
            log(f"par 缺失: {p}", "ERROR"); ok = False; continue
        gen = _par_kv(p)
        missing = [k for k in ref
                   if k not in gen
                   and not any(k.startswith(s) for s in _KEY_DIFF_IGNORE)]
        extra = [k for k in gen if k not in ref
                 and not any(k.startswith(s) for s in _KEY_DIFF_IGNORE)]
        flag = "OK " if not missing else "[X]"
        print(f"    {flag} {label:<18} {len(gen)} 键; 缺(物理相关) {len(missing)}; "
              f"多 {len(extra)}")
        for k in missing:
            print(f"        [X] 缺失: {k} = {ref[k]}")
        if missing:
            ok = False

        # ★★★ 数值敏感键硬校验: 无论是否被 _KEY_DIFF_IGNORE 放行, 都必须存在
        #   (事故: gr_hypreUseFloor 被忽略清单放行 → 静默失真)
        absent = [k for k in NUMERIC_CRITICAL_KEYS if k not in gen]
        if absent:
            log(f"[{label}] ★ 数值敏感键缺失: {absent} —— 会静默改变物理结果!",
                "ERROR")
            ok = False
    if ok:
        log("键集校验通过 ✓ (无物理相关缺键; 数值敏感键齐全)", "OK")
    return ok


def check_controlled(out_dir: Path, entries: List[Tuple[str, str, str]]) -> bool:
    """受控性自检。

    Args:
        entries: [(标签, leg, par 文件名), ...]
            · `--radiation both` → 4 条: (SH/radON, flsh, flsh_radon.par) ...
            · 否则 → 每腿 1 条

    断言:
      ① **同腿两辐射状态**: par 只应差 辐射三开关 + basenm/log_file，且 F90 完全共用
      ② **跨腿同辐射状态**: par 只应差 basenm/log_file
      ③ 无重复键
    """
    print("\n  ── 场景受控性自检 ─────────────────────────────────")
    ok = True
    # 文件清单(按腿)
    leg_files: Dict[str, set] = {}
    for _, leg, _ in entries:
        d = out_dir / f"sim_{leg}" / "flash_input"
        if not d.is_dir():
            log(f"[{leg}] flash_input 不存在: {d}", "ERROR")
            ok = False
            continue
        leg_files[leg] = {p.name for p in d.iterdir() if p.is_file()}
    if not ok:
        return False

    # ① 同腿两状态 (仅当同腿有 2 条记录)
    by_leg: Dict[str, List[Tuple[str, str]]] = {}
    for label, leg, par in entries:
        by_leg.setdefault(leg, []).append((label, par))
    for leg, lst in by_leg.items():
        if len(lst) < 2:
            continue
        d = out_dir / f"sim_{leg}" / "flash_input"
        (la, pa), (lb, pb) = lst[0], lst[1]
        a, b = _kv(d / pa), _kv(d / pb)
        diff = {k: (a[k], b[k]) for k in a if k in b and a[k] != b[k]}
        bad = [k for k in diff if k not in ALLOWED_PAR_DIFF]
        print(f"    [同腿 {leg}] {pa} vs {pb}: 差异键 {sorted(diff) or '无'}")
        for k in bad:
            log(f"[{leg}] 非预期 par 差异: {k}", "ERROR")
        ok &= not bad
        # F90 文件应完全共用 (同腿只有一个 flash_input)
        n_f90 = len([f for f in leg_files[leg] if f.lower().endswith((".f90", ".f"))])
        print(f"    [同腿 {leg}] F90 文件数 = {n_f90} (两状态共用同一份 ✓)")

    # ② 跨腿同状态
    legs = list(by_leg)
    if len(legs) >= 2:
        for i in range(1, len(legs)):
            la, lb = legs[0], legs[i]
            common = sorted(leg_files[la] & leg_files[lb])
            same = [n for n in common
                    if filecmp.cmp(out_dir / f"sim_{la}" / "flash_input" / n,
                                   out_dir / f"sim_{lb}" / "flash_input" / n,
                                   shallow=False)]
            only_a = sorted(leg_files[la] - leg_files[lb])
            only_b = sorted(leg_files[lb] - leg_files[la])
            print(f"    [跨腿 {la} vs {lb}] 逐字节相同 {len(same)} 个; "
                  f"仅前者有 {only_a or '无'}; 仅后者有 {only_b or '无'}")
            # par 对比 (同名 par)
            for n in common:
                if not n.endswith(".par"):
                    continue
                a, b = _kv(out_dir / f"sim_{la}" / "flash_input" / n), \
                       _kv(out_dir / f"sim_{lb}" / "flash_input" / n)
                diff = {k: (a[k], b[k]) for k in a if k in b and a[k] != b[k]}
                bad = [k for k in diff if k not in ALLOWED_PAR_DIFF]
                print(f"      par {n} 差异键: {sorted(diff) or '无'}")
                for k in bad:
                    log(f"跨腿 par 非预期差异 ({n}): {k}", "ERROR")
                ok &= not bad

    # ③ 重复键
    for label, leg, par in entries:
        p = out_dir / f"sim_{leg}" / "flash_input" / par
        if not p.exists():
            log(f"par 缺失: {p}", "ERROR"); ok = False; continue
        seen: List[str] = []
        for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
            s = line.split("#", 1)[0].strip()
            if s and "=" in s:
                seen.append(s.split("=", 1)[0].strip())
        dup = sorted({k for k in seen if seen.count(k) > 1})
        if dup:
            log(f"[{label}] par 存在重复键: {dup}", "WARN")

    if ok:
        log("受控性自检通过 ✓ (同腿两状态只差辐射开关; 跨腿只差腿标识)", "OK")
    return ok


# ══════════════════════════════════════════════════════════════
def main() -> int:
    ap = argparse.ArgumentParser(description="SNB 场景生成器 (以 SNB/SNB 为核心模块)")
    ap.add_argument("--out", required=True, help="目标场景目录")
    ap.add_argument("--legs", default="snb,flsh",
                    help="要生成的腿 (逗号分隔): snb, flsh")
    ap.add_argument("--species", default="cham,tar1,tar2,tar3")
    ap.add_argument("--flsh-mode", choices=["native", "stock"], default="native",
                    help="限流 SH 腿的 diff_advanceTherm 来源: "
                         "native=标准树原生; stock=source/stock_sh 覆盖件")
    ap.add_argument("--therm-variant", choices=["none", "limiter"], default="none")
    ap.add_argument("--driver-variant", choices=["none", "radon"], default="radon",
                    help="★ SNB 腿的驱动源; 默认 radon (推荐)。"
                         "作者原版把两处 call RadTrans 注释了 → 辐射永不推进、"
                         "par 三开关形同虚设; radon 变体恢复该调用后开关才生效。"
                         "none = 作者原版 (仅在明确不做辐射对比时使用)")
    ap.add_argument("--radiation", choices=["on", "off", "both"], default="on",
                    help="辐射开关; both=每腿都生成开/关两个 par (默认 on)")
    ap.add_argument("--ele-fl-mode",
                    choices=["fl_none", "fl_harmonic", "fl_minmax", "fl_larsen",
                             "fl_levermorepomraning1981"],
                    default=P.CONDUCTION["diff_eleFlMode"],
                    help="★ 电子限流模式 (默认 %(default)s)。实测: 在 SNB 场景下"
                         "该键是 **no-op**(SNB 各向同性电子分支的限流器调用被注释,"
                         " 见 docs/05 坑位清单 P1 更正块), 故默认 fl_none。")
    ap.add_argument("--xmin", type=float, default=P.GEOMETRY["xmin"])
    ap.add_argument("--xmax", type=float, default=P.GEOMETRY["xmax"])
    ap.add_argument("--tmax", type=float, default=P.TIME["tmax"])
    ap.add_argument("--dtmax", type=float, default=P.TIME["dtmax"])
    ap.add_argument("--nxb", type=int, default=P.GRID_REFERENCE["nxb"])
    ap.add_argument("--iprocs", type=int, default=P.GRID_REFERENCE["iprocs"])
    ap.add_argument("--chk-dt", type=float, default=P.OUTPUT["checkpointFileIntervalTime"])
    ap.add_argument("--plt-dt", type=float, default=P.OUTPUT["plotFileIntervalTime"])
    ap.add_argument("--check-only", action="store_true")
    ap.add_argument("--verify-keys-against", default=None, metavar="REF_PAR",
                    help="★ 与该参考 par 做键集差分, 缺物理相关键则报错 "
                         "(强烈建议传作者示例 par)")
    args = ap.parse_args()

    out_dir = Path(args.out).resolve()
    legs = [x.strip() for x in args.legs.split(",") if x.strip()]
    bad = [l for l in legs if l not in LEG_SPECS]
    if bad:
        log(f"未知腿: {bad} (可选 {list(LEG_SPECS)})", "ERROR")
        return 2
    species = [x.strip() for x in args.species.split(",") if x.strip()]

    print("\n" + "=" * 78)
    print(" SNB 场景生成器 (核心模块 = SNB/SNB)")
    print(f" 输出: {out_dir}")
    print(f" 腿: {legs}   物种: {species}   flsh-mode: {args.flsh_mode}")
    print(f" 网格: iProcs={args.iprocs} × nxb={args.nxb} = {args.iprocs*args.nxb} 格, "
          f"dx≈{(args.xmax-args.xmin)/(args.iprocs*args.nxb)*1e4:.4f} µm")
    print(f" tmax={args.tmax:.3e}  dtmax={args.dtmax:.3e}")
    print("=" * 78)

    if not SOURCE.is_dir():
        log(f"source/ 不存在: {SOURCE}\n      请先运行 "
            f"scripts/generate/import_sources.py --from <作者包目录>", "ERROR")
        return 2

    entries: List[Tuple[str, str, str]] = []
    if not args.check_only:
        rad_list = [("radon", True), ("radoff", False)] if args.radiation == "both" \
            else [("", args.radiation == "on")]
        for leg in legs:
            for rad_tag, rad_on in rad_list:
                r = deploy_leg(leg, out_dir, args, rad_on, species, rad_tag)
                entries.append((f"{leg}/{rad_tag or 'default'}", leg,
                                r.get("par", LEG_SPECS[leg]["par"])))
    else:
        rad_list = [("radon", True), ("radoff", False)] if args.radiation == "both" \
            else [("", args.radiation == "on")]
        for leg in legs:
            for rad_tag, _ in rad_list:
                par = f"{leg}_{rad_tag}.par" if rad_tag else LEG_SPECS[leg]["par"]
                entries.append((f"{leg}/{rad_tag or 'default'}", leg, par))

    ok = check_controlled(out_dir, entries)
    if args.verify_keys_against:
        ok = verify_keys_against(Path(args.verify_keys_against).resolve(),
                                 out_dir, entries) and ok
    print()
    log(f"场景已生成: {out_dir}", "OK" if ok else "WARN")
    if args.radiation == "both":
        print("  生成的是 2×2 矩阵 (每腿 2 个 par, F90 共用):")
        for leg in legs:
            for rad_tag, _ in rad_list:
                print(f"    sim_{leg}/flash_input/{leg}_{rad_tag}.par")
        print("  运行示例 (同一 objdir 只需 setup/make 一次):")
        for leg in legs:
            for rad_tag, _ in rad_list:
                print(f"    run_scene.py --scene {out_dir} --side {leg} "
                      f"--par {leg}_{rad_tag}.par --tag {rad_tag}"
                      f"{' --skip-setup --skip-make' if (leg, rad_tag) != (legs[0], rad_list[0][0]) else ''}")
    print("  下一步:")
    print(f"    1) 分享前自检: python scripts/check_share_safety.py")
    print(f"    2) 运行:       python scripts/run/run_scene.py --scene {out_dir}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
