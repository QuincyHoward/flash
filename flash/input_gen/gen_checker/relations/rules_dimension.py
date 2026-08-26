"""
relations.rules_dimension — 规则 C：维度 / 光束 / 脉冲级约束关联
════════════════════════════════════════════════════════════════

对应 GEN_CHECKER_GUIDE「C. 维度 / 光束 / 脉冲级约束关联」：
  7. 维度一致性（.par 网格参数 vs setup 维度 flag / geometry）
  8. 光束数目一致性（ed_numberOfBeams vs ed_lensX_*/ed_targetX_*）
  9. 脉冲-光束绑定（ed_pulseNumber_i 在 ed_numberOfPulses 范围内）
 10. 脉冲组数上限（ed_numberOfSections_* > 20 → setup 需 ed_maxPulseSections）
 11. 靶/透镜位置在仿真域内
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional

from ._core import RelationContext, RelationResult, relation_rule
from ._parsers import setup_cmd_from, unquote


def _int(params: Dict[str, str], key: str) -> Optional[int]:
    v = params.get(key)
    if v is None:
        return None
    try:
        return int(float(unquote(v)))
    except ValueError:
        return None


def _float(params: Dict[str, str], key: str) -> Optional[float]:
    v = params.get(key)
    if v is None:
        return None
    try:
        return float(unquote(v))
    except ValueError:
        return None


@relation_rule("dimension_grid_vs_setup", "维度一致性：.par 网格参数 vs setup flag")
def rule_dimension_grid(ctx: RelationContext) -> RelationResult:
    """规则 7：.par 的维度网格参数（nblocky/nblockz 有无）应与 setup 的 -1d/2d/3d 一致，
    且 geometry 与 +cartesian/cylindrical/spherical 一致。"""
    params = ctx.par_params()
    if not params:
        return RelationResult(rule_id="dimension_grid_vs_setup",
                              name="维度一致性：.par 网格参数 vs setup flag",
                              status=None, message="无 .par，跳过")

    has_y = "nblocky" in params
    has_z = "nblockz" in params
    if has_z:
        par_dim = 3
    elif has_y:
        par_dim = 2
    else:
        par_dim = 1

    # 从运行脚本提取 setup 指令（可能多个脚本；取第一个含 ./setup 的）
    scripts = ctx.run_scripts()
    setups = [setup_cmd_from(t) for t in scripts.values() if "./setup " in t]
    setup_cmd = setups[0] if setups else ""
    issues: List[str] = []

    if setup_cmd:
        dim_flag = re.search(r"-(1d|2d|3d)\b", setup_cmd)
        setup_dim = int(dim_flag.group(1)[0]) if dim_flag else None
        if setup_dim is not None and setup_dim != par_dim:
            issues.append(f".par 暗示 {par_dim}D (nblocky={'有' if has_y else '无'}"
                          f", nblockz={'有' if has_z else '无'})，但 setup 用 -{setup_dim}d")
        # geometry 一致性
        par_geo = unquote(params.get("geometry", "cartesian")).lower()
        geo_flag = re.search(r"\+(cartesian|cylindrical|spherical)\b", setup_cmd)
        if geo_flag and geo_flag.group(1) != par_geo:
            issues.append(f".par 的 geometry={par_geo} 与 setup +{geo_flag.group(1)} 不一致")
    else:
        issues.append("未在运行脚本中找到 ./setup 指令，无法核对维度 flag")

    if issues:
        return RelationResult(rule_id="dimension_grid_vs_setup",
                              name="维度一致性：.par 网格参数 vs setup flag",
                              status=False, message="; ".join(issues),
                              details={"par_dim": par_dim, "issues": issues})
    return RelationResult(rule_id="dimension_grid_vs_setup",
                          name="维度一致性：.par 网格参数 vs setup flag",
                          status=True, message=f".par 为 {par_dim}D，与 setup 维度及 geometry 一致",
                          details={"par_dim": par_dim})


@relation_rule("beam_number_match", "光束数目一致性：ed_numberOfBeams vs ed_lensX_*/ed_targetX_*")
def rule_beam_number(ctx: RelationContext) -> RelationResult:
    """规则 8：ed_numberOfBeams=N 时，应存在 ed_lensX_1..N 与 ed_targetX_1..N。"""
    params = ctx.par_params()
    n = _int(params, "ed_numberOfBeams")
    if n is None:
        return RelationResult(rule_id="beam_number_match",
                              name="光束数目一致性", status=None,
                              message="无 ed_numberOfBeams，跳过")
    have_lens = [i for i in range(1, n + 1) if f"ed_lensX_{i}" in params]
    have_targ = [i for i in range(1, n + 1) if f"ed_targetX_{i}" in params]
    miss_lens = [i for i in range(1, n + 1) if i not in have_lens]
    miss_targ = [i for i in range(1, n + 1) if i not in have_targ]
    if miss_lens or miss_targ:
        return RelationResult(rule_id="beam_number_match",
                              name="光束数目一致性：ed_numberOfBeams vs ed_lensX_*/ed_targetX_*",
                              status=False,
                              message=f"ed_numberOfBeams={n} 但缺 ed_lensX_{miss_lens} "
                                      f"或 ed_targetX_{miss_targ}",
                              details={"n": n, "missing_lens": miss_lens,
                                       "missing_target": miss_targ})
    return RelationResult(rule_id="beam_number_match",
                          name="光束数目一致性：ed_numberOfBeams vs ed_lensX_*/ed_targetX_*",
                          status=True, message=f"{n} 束的 ed_lensX/ed_targetX 齐全",
                          details={"n": n})


@relation_rule("pulse_beam_binding", "脉冲-光束绑定：ed_pulseNumber_i 在 ed_numberOfPulses 内")
def rule_pulse_beam(ctx: RelationContext) -> RelationResult:
    """规则 9：每条光束的 ed_pulseNumber_i 应在 1..ed_numberOfPulses 范围内。"""
    params = ctx.par_params()
    n_pulse = _int(params, "ed_numberOfPulses")
    n_beam = _int(params, "ed_numberOfBeams")
    if n_pulse is None or n_beam is None:
        return RelationResult(rule_id="pulse_beam_binding",
                              name="脉冲-光束绑定", status=None,
                              message="无 ed_numberOfPulses/ed_numberOfBeams，跳过")
    bad: List[int] = []
    for i in range(1, n_beam + 1):
        pn = _int(params, f"ed_pulseNumber_{i}")
        if pn is not None and not (1 <= pn <= n_pulse):
            bad.append(i)
    if bad:
        return RelationResult(rule_id="pulse_beam_binding",
                              name="脉冲-光束绑定：ed_pulseNumber_i 在 ed_numberOfPulses 内",
                              status=False,
                              message=f"光束 {bad} 的 ed_pulseNumber 超出 "
                                      f"ed_numberOfPulses={n_pulse}",
                              details={"bad_beams": bad, "n_pulse": n_pulse})
    return RelationResult(rule_id="pulse_beam_binding",
                          name="脉冲-光束绑定：ed_pulseNumber_i 在 ed_numberOfPulses 内",
                          status=True, message=f"全部 {n_beam} 束的脉冲号合法",
                          details={"n_beam": n_beam, "n_pulse": n_pulse})


@relation_rule("pulse_sections_limit", "脉冲组数上限：ed_numberOfSections_* 超 20 需 setup 设 ed_maxPulseSections")
def rule_pulse_sections(ctx: RelationContext) -> RelationResult:
    """规则 10：任一条光束的 ed_numberOfSections_i > 20 时，setup 指令需带
    ed_maxPulseSections=<足够大>，否则超出段被截断。"""
    params = ctx.par_params()
    n_beam = _int(params, "ed_numberOfBeams")
    if n_beam is None:
        return RelationResult(rule_id="pulse_sections_limit",
                              name="脉冲组数上限", status=None,
                              message="无 ed_numberOfBeams，跳过")
    max_sec = 0
    for i in range(1, n_beam + 1):
        s = _int(params, f"ed_numberOfSections_{i}")
        if s is not None:
            max_sec = max(max_sec, s)
    if max_sec <= 20:
        return RelationResult(rule_id="pulse_sections_limit",
                              name="脉冲组数上限：ed_numberOfSections_* 超 20",
                              status=True,
                              message=f"最大脉冲组数 {max_sec} ≤ 20，无需 ed_maxPulseSections",
                              details={"max_sections": max_sec})
    scripts = ctx.run_scripts()
    has_limit = any("ed_maxPulseSections" in t for t in scripts.values())
    if not has_limit:
        return RelationResult(rule_id="pulse_sections_limit",
                              name="脉冲组数上限：ed_numberOfSections_* 超 20",
                              status=False,
                              message=(f"最大脉冲组数 {max_sec} > 20，但 setup 指令未设置 "
                                       f"ed_maxPulseSections，超出段会被截断"),
                              details={"max_sections": max_sec})
    return RelationResult(rule_id="pulse_sections_limit",
                          name="脉冲组数上限：ed_numberOfSections_* 超 20",
                          status=True,
                          message=f"最大脉冲组数 {max_sec} > 20，且 setup 已含 ed_maxPulseSections",
                          details={"max_sections": max_sec})


@relation_rule("beam_in_domain", "靶/透镜位置在仿真域内")
def rule_beam_in_domain(ctx: RelationContext) -> RelationResult:
    """规则 11：1D 激光下 ed_lensX_i / ed_targetX_i 应在仿真域 [xmin, xmax] 内。"""
    params = ctx.par_params()
    xmin = _float(params, "xmin")
    xmax = _float(params, "xmax")
    n_beam = _int(params, "ed_numberOfBeams")
    if xmin is None or xmax is None or n_beam is None:
        return RelationResult(rule_id="beam_in_domain",
                              name="靶/透镜位置在仿真域内", status=None,
                              message="缺 xmin/xmax/ed_numberOfBeams，跳过")
    out: List[str] = []
    for i in range(1, n_beam + 1):
        lens = _float(params, f"ed_lensX_{i}")
        targ = _float(params, f"ed_targetX_{i}")
        if lens is not None and not (xmin <= lens <= xmax):
            out.append(f"ed_lensX_{i}={lens} 在域 [{xmin},{xmax}] 外")
        if targ is not None and not (xmin <= targ <= xmax):
            out.append(f"ed_targetX_{i}={targ} 在域 [{xmin},{xmax}] 外")
    # 透镜常故意放在域外（光线从远处射入）；仅对 targetX 严格告警，lensX 提示
    strict = [o for o in out if "targetX" in o]
    if strict:
        return RelationResult(rule_id="beam_in_domain",
                              name="靶/透镜位置在仿真域内",
                              status=False,
                              message="; ".join(strict), details={"issues": strict})
    if out:
        return RelationResult(rule_id="beam_in_domain",
                              name="靶/透镜位置在仿真域内",
                              status=True,
                              message="透镜在域外（正常，允许）；目标均在域内。提示: " + "; ".join(out),
                              details={"notes": out})
    return RelationResult(rule_id="beam_in_domain",
                          name="靶/透镜位置在仿真域内",
                          status=True, message=f"全部 {n_beam} 束的目标/透镜位置合理",
                          details={"n_beam": n_beam})
