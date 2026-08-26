"""
relations.rules_reference — 规则 A：文件级引用关联
═══════════════════════════════════════════════════

对应 GEN_CHECKER_GUIDE「A. 文件级引用关联」：
  1. .par 引用的 EOS/Opacity 表必须在磁盘存在
  2. .par 引用的 .cn4 必须在 Config 的 DATAFILES 声明
  3. Config 的 PARAMETER 需定义 .par 用到的表绑定
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from ._core import RelationContext, RelationResult, relation_rule
from ._parsers import par_refs_of_prefix, unquote


# 所有引用 .cn4 表的 .par 参数前缀
_EOS_PAR_PREFIXES = ("eos_", "op_")


def _disk_cn4_names(ctx: RelationContext) -> List[str]:
    """仿真目录磁盘上所有 .cn4 文件名（小写集合）。"""
    return [p.name for p in ctx.sim_dir.glob("*.cn4")]


@relation_rule("par_cn4_on_disk", ".par 引用的 .cn4 必须存在于磁盘")
def rule_par_cn4_on_disk(ctx: RelationContext) -> RelationResult:
    """规则 1：.par 中 eos_*/op_* 引用的 .cn4 必须在仿真目录真实存在。"""
    params = ctx.par_params()
    refs = par_refs_of_prefix(params, *_EOS_PAR_PREFIXES)
    if not params:
        return RelationResult(
            rule_id="par_cn4_on_disk", name=".par 引用的 .cn4 必须存在于磁盘",
            status=None, message="无 .par 文件或无可检查的 eos_*/op_* 参数，跳过",
        )
    disk = {f.lower() for f in _disk_cn4_names(ctx)}
    missing = [r for r in refs if r.lower() not in disk and not r.lower().endswith(".ses")]
    if missing:
        return RelationResult(
            rule_id="par_cn4_on_disk", name=".par 引用的 .cn4 必须存在于磁盘",
            status=False,
            message=f"缺失 {len(missing)} 个被 .par 引用的表文件: {missing}",
            details={"missing": missing, "disk": sorted(disk)},
        )
    return RelationResult(
        rule_id="par_cn4_on_disk", name=".par 引用的 .cn4 必须存在于磁盘",
        status=True, message=f"所有 {len(refs)} 个被引用的表文件均存在于磁盘",
        details={"referenced": refs},
    )


@relation_rule("par_cn4_in_config_datafiles", ".par 引用的 .cn4 必须在 Config 的 DATAFILES 声明")
def rule_par_cn4_in_config(ctx: RelationContext) -> RelationResult:
    """规则 2：.par 引用的每个 .cn4 都应在 Config 有 DATAFILES 声明。

    注意：DATAFILES 可多不可少；只有 .par 引用但未声明才是错误。
    """
    params = ctx.par_params()
    refs = par_refs_of_prefix(params, *_EOS_PAR_PREFIXES)
    if not refs:
        return RelationResult(
            rule_id="par_cn4_in_config_datafiles",
            name=".par 引用的 .cn4 必须在 Config 的 DATAFILES 声明",
            status=None, message="无 eos_*/op_* 引用，跳过",
        )
    declared = {unquote(f).lower() for f in ctx.config_datafiles()}
    missing = [r for r in refs if r.lower() not in declared and not r.lower().endswith(".ses")]
    if missing:
        return RelationResult(
            rule_id="par_cn4_in_config_datafiles",
            name=".par 引用的 .cn4 必须在 Config 的 DATAFILES 声明",
            status=False,
            message=("以下被 .par 引用的表文件未在 Config 的 DATAFILES 声明，"
                     f"setup 时不会被复制，可能报 eos files not found: {missing}"),
            details={"missing": missing, "declared": sorted(declared)},
        )
    return RelationResult(
        rule_id="par_cn4_in_config_datafiles",
        name=".par 引用的 .cn4 必须在 Config 的 DATAFILES 声明",
        status=True,
        message=f"所有 {len(refs)} 个被引用的表文件均已声明于 DATAFILES",
        details={"referenced": refs, "declared": sorted(declared)},
    )


@relation_rule("config_table_parameter", "Config 需定义 .par 用到的表绑定 PARAMETER")
def rule_config_table_parameter(ctx: RelationContext) -> RelationResult:
    """规则 3：检查 .par 中"表文件绑定键"（*TableFile/*FileName）是否规范。

    注意：`eos_*TableFile` / `op_*FileName` 等是 **FLASH 内建 Eos/Opacity 模块**
    的运行时参数，由 FLASH 源中的 Eos/Opacity Config 声明，**不要求在 Simulation
    Config 里重复定义 PARAMETER**。因此本规则不再校验 Simulation Config 白名单，
    而是校验：凡是以 TableFile/FileName 结尾的键，其取值应是指向 `.cn4` 文件的
    引用（排除误把模式名/类型名填进文件键的写法）。
    """
    params = ctx.par_params()
    table_keys = [k for k in params if k.endswith("TableFile") or k.endswith("FileName")]
    if not table_keys:
        return RelationResult(
            rule_id="config_table_parameter",
            name="Config 需定义 .par 用到的表绑定 PARAMETER",
            status=None, message=".par 中无 *TableFile/*FileName 键，跳过",
        )
    bad: List[str] = []
    for k in table_keys:
        v = unquote(params[k])
        # 表文件键的取值应为 .cn4（或 .ses）文件名；空值或非文件名视为可疑
        if not v.lower().endswith((".cn4", ".ses")):
            bad.append(f"{k}={v}")
    if bad:
        return RelationResult(
            rule_id="config_table_parameter",
            name="Config 需定义 .par 用到的表绑定 PARAMETER",
            status=False,
            message=(f"以下 *TableFile/*FileName 键的取值不是 .cn4/.ses 文件名，"
                     f"疑似误填模式名/类型名: {bad}"),
            details={"bad": bad, "table_keys": table_keys},
        )
    return RelationResult(
        rule_id="config_table_parameter",
        name="Config 需定义 .par 用到的表绑定 PARAMETER",
        status=True,
        message=f"全部 {len(table_keys)} 个表绑定键取值均为 .cn4/.ses 文件引用",
        details={"table_keys": table_keys},
    )
