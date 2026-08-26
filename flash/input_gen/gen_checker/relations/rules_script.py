"""
relations.rules_script — 规则 D：脚本级装配关联
════════════════════════════════════════════════

对应 GEN_CHECKER_GUIDE「D. 脚本级装配关联」：
 12. .par 文件名与 run_flash.sh 的 PAR_FILE 一致
 13. setup 的 species= 与 Config 的 SPECIES 一致
 14. Makefile 引用的 .o 与存在的 Simulation_*.F90 对应
"""

from __future__ import annotations

import re
from typing import List

from ._core import RelationContext, RelationResult, relation_rule
from ._parsers import unquote


@relation_rule("par_file_in_script", "run_flash.sh 的 PAR_FILE 与磁盘 .par 文件名一致")
def rule_par_file_in_script(ctx: RelationContext) -> RelationResult:
    """规则 12：运行脚本里的 PAR_FILE / -par_file 应指向磁盘上真实存在的 .par 名。"""
    par = ctx.par_path()
    if par is None:
        return RelationResult(rule_id="par_file_in_script",
                              name="run_flash.sh 的 PAR_FILE 与磁盘 .par 文件名一致",
                              status=None, message="磁盘无 .par 文件，跳过")
    disk_name = par.name
    scripts = ctx.run_scripts()
    if not scripts:
        return RelationResult(rule_id="par_file_in_script",
                              name="run_flash.sh 的 PAR_FILE 与磁盘 .par 文件名一致",
                              status=None, message="无运行脚本，跳过")
    for fname, text in scripts.items():
        # 匹配 PAR_FILE="xxx.par" 或 -par_file xxx.par
        refs = re.findall(r'PAR_FILE\s*=\s*["\']?([^"\'\s]+\.par)["\']?', text)
        refs += re.findall(r'-par_file\s+([^\s"\'&;]+\.par)', text)
        for ref in refs:
            if ref != disk_name:
                return RelationResult(rule_id="par_file_in_script",
                                      name="run_flash.sh 的 PAR_FILE 与磁盘 .par 文件名一致",
                                      status=False,
                                      message=f"{fname} 引用 par 文件 {ref!r}，但磁盘实际是 {disk_name!r}",
                                      details={"script": fname, "ref": ref, "disk": disk_name})
    return RelationResult(rule_id="par_file_in_script",
                          name="run_flash.sh 的 PAR_FILE 与磁盘 .par 文件名一致",
                          status=True,
                          message=f"运行脚本引用的 par 文件 {disk_name} 与磁盘一致",
                          details={"par": disk_name})


@relation_rule("species_setup_match", "setup 的 species= 与 Config 的 SPECIES 一致")
def rule_species_match(ctx: RelationContext) -> RelationResult:
    """规则 13：运行脚本 setup 指令里的 species=a,b,c 应都出现在 Config 的 SPECIES 中。"""
    cfg_species = ctx.config_species()
    if not cfg_species:
        return RelationResult(rule_id="species_setup_match",
                              name="setup 的 species= 与 Config 的 SPECIES 一致",
                              status=None, message="Config 无 SPECIES 声明，跳过")
    scripts = ctx.run_scripts()
    setup_species: List[str] = []
    for text in scripts.values():
        m = re.search(r"species=([A-Za-z0-9_,]+)", text)
        if m:
            setup_species += [s.strip() for s in m.group(1).split(",") if s.strip()]
    if not setup_species:
        return RelationResult(rule_id="species_setup_match",
                              name="setup 的 species= 与 Config 的 SPECIES 一致",
                              status=None, message="setup 指令中未找到 species=，跳过")
    cfg_set = set(cfg_species)
    unknown = [s for s in setup_species if s not in cfg_set]
    if unknown:
        return RelationResult(rule_id="species_setup_match",
                              name="setup 的 species= 与 Config 的 SPECIES 一致",
                              status=False,
                              message=f"setup 使用 species={unknown}，但 Config 未声明对应 SPECIES",
                              details={"unknown": unknown, "config_species": cfg_species})
    return RelationResult(rule_id="species_setup_match",
                          name="setup 的 species= 与 Config 的 SPECIES 一致",
                          status=True,
                          message=f"setup 的 species={setup_species} 均在 Config 中声明",
                          details={"setup_species": setup_species, "config_species": cfg_species})


@relation_rule("makefile_f90_match", "Makefile 引用的 .o 与存在的 Simulation_*.F90 对应")
def rule_makefile_f90(ctx: RelationContext) -> RelationResult:
    """规则 14：Makefile 中 `Simulation += X.o` 应对应磁盘/源目录存在 X.F90。"""
    lines = ctx.makefile_lines()
    if not lines:
        return RelationResult(rule_id="makefile_f90_match",
                              name="Makefile 引用的 .o 与存在的 Simulation_*.F90 对应",
                              status=None, message="无 Makefile，跳过")
    f90_names = {f.name for f in ctx.sim_dir.glob("*.F90")}
    ref_objs: List[str] = []
    for ln in lines:
        m = re.search(r"Simulation\s*\+=?\s*([A-Za-z_][A-Za-z0-9_]*)\.o\b", ln)
        if m:
            ref_objs.append(m.group(1))
    if not ref_objs:
        return RelationResult(rule_id="makefile_f90_match",
                              name="Makefile 引用的 .o 与存在的 Simulation_*.F90 对应",
                              status=None, message="Makefile 未引用任何 Simulation_*.o，跳过")
    missing = [o for o in ref_objs if f"{o}.F90" not in f90_names]
    if missing:
        return RelationResult(rule_id="makefile_f90_match",
                              name="Makefile 引用的 .o 与存在的 Simulation_*.F90 对应",
                              status=False,
                              message=f"Makefile 引用 {missing} 但目录中无对应 .F90",
                              details={"missing": missing, "f90_on_disk": sorted(f90_names)})
    return RelationResult(rule_id="makefile_f90_match",
                          name="Makefile 引用的 .o 与存在的 Simulation_*.F90 对应",
                          status=True,
                          message=f"Makefile 引用的 {len(ref_objs)} 个 .o 均有对应 .F90",
                          details={"objects": ref_objs})
