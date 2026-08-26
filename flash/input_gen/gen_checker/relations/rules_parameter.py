"""
relations.rules_parameter — 规则 B：参数级一致性关联
═════════════════════════════════════════════════════

对应 GEN_CHECKER_GUIDE「B. 参数级一致性关联」：
  4. .par 中的 sim_* 运行时参数应在 Config 有对应 PARAMETER 定义
  5. Simulation_data.F90 声明的模块变量应与 Simulation_init.F90 的读取一一对应
  6. .par 的 sim_* 键应与 Simulation_init.F90 读取的键一致
"""

from __future__ import annotations

from typing import List

from ._core import RelationContext, RelationResult, relation_rule
from ._parsers import f90_save_vars, init_get_keys


@relation_rule("par_sim_in_config", ".par 的 sim_* 参数需在 Config 有 PARAMETER 定义")
def rule_par_sim_in_config(ctx: RelationContext) -> RelationResult:
    """规则 4：.par 中出现的 sim_* 键应在 Config 有对应 PARAMETER 声明。

    反向放宽：Config 中允许有 .par 未设置的参数（使用默认值）；只报告
    .par 有而 Config 无的白名单外键。
    """
    params = ctx.par_params()
    sim_keys = [k for k in params if k.startswith("sim_")]
    if not sim_keys:
        return RelationResult(
            rule_id="par_sim_in_config",
            name=".par 的 sim_* 参数需在 Config 有 PARAMETER 定义",
            status=None, message=".par 中无 sim_* 键，跳过",
        )
    cfg_params = set(ctx.config_parameters())
    undefined = [k for k in sim_keys if k not in cfg_params]
    if undefined:
        return RelationResult(
            rule_id="par_sim_in_config",
            name=".par 的 sim_* 参数需在 Config 有 PARAMETER 定义",
            status=False,
            message=(f".par 中 {len(undefined)} 个 sim_* 键未在 Config 声明 "
                     f"(可能触发 Unknown runtime parameter 告警): {undefined}"),
            details={"undefined": undefined},
        )
    return RelationResult(
        rule_id="par_sim_in_config",
        name=".par 的 sim_* 参数需在 Config 有 PARAMETER 定义",
        status=True,
        message=f"所有 {len(sim_keys)} 个 sim_* 键均在 Config 有 PARAMETER 定义",
        details={"sim_keys": sim_keys},
    )


@relation_rule("simdata_init_consistency", "Simulation_data.F90 变量与 Simulation_init.F90 读取对应")
def rule_simdata_init_consistency(ctx: RelationContext) -> RelationResult:
    """规则 5：Simulation_init.F90 中 RuntimeParameters_get 写入的 sim_* 变量，
    必须在 Simulation_data.F90 中声明为 save 变量。
    """
    f90 = ctx.simulation_f90()
    data_f90 = f90.get("Simulation_data.F90", "")
    init_f90 = f90.get("Simulation_init.F90", "")
    if not data_f90 or not init_f90:
        return RelationResult(
            rule_id="simdata_init_consistency",
            name="Simulation_data.F90 变量与 Simulation_init.F90 读取对应",
            status=None,
            message="缺少 Simulation_data.F90 或 Simulation_init.F90，无法交叉检查",
        )
    declared = set(f90_save_vars(data_f90))
    # 读取键的左侧目标变量（RuntimeParameters_get('key', var)）—— 默认与键同名
    get_keys = init_get_keys(init_f90)
    # 提取 get 的第二个实参（目标变量名），可能不同于键
    import re
    targets = re.findall(
        r"RuntimeParameters_get\(\s*['\"][^'\"]+['\"]\s*,\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)",
        init_f90,
    )
    missing = [t for t in targets if t not in declared]
    if missing:
        return RelationResult(
            rule_id="simdata_init_consistency",
            name="Simulation_data.F90 变量与 Simulation_init.F90 读取对应",
            status=False,
            message=(f"Simulation_init.F90 写入但 Simulation_data.F90 未声明的变量: "
                     f"{missing}"),
            details={"missing": missing, "declared": sorted(declared)},
        )
    return RelationResult(
        rule_id="simdata_init_consistency",
        name="Simulation_data.F90 变量与 Simulation_init.F90 读取对应",
        status=True,
        message=f"Simulation_init.F90 读取的 {len(targets)} 个变量均在 Simulation_data.F90 声明",
        details={"targets": targets},
    )


@relation_rule("par_init_key_match", ".par 的 sim_* 键与 Simulation_init.F90 读取键一致")
def rule_par_init_key_match(ctx: RelationContext) -> RelationResult:
    """规则 6：.par 中出现的 sim_* 键应与 Simulation_init.F90 读取的键一致。

    判定：只对"**.par 设置了但 init 未读取**"的键告警（参数设了却不生效，是真隐患）。
    反向"init 读取但 .par 未设置"（走 Config 默认）是正常行为，仅作提示不告警。
    """
    params = ctx.par_params()
    init_f90 = ctx.simulation_f90().get("Simulation_init.F90", "")
    if not params or not init_f90:
        return RelationResult(
            rule_id="par_init_key_match",
            name=".par 的 sim_* 键与 Simulation_init.F90 读取键一致",
            status=None, message="缺 .par 或 Simulation_init.F90，跳过",
        )
    par_sim = set(k for k in params if k.startswith("sim_"))
    init_keys = set(init_get_keys(init_f90))
    # .par 设置了但 init 从未读取（含条件编译下未读到的）：参数未生效
    unread = sorted(par_sim - init_keys)
    # init 读取但 .par 未设置（走 Config 默认）——仅提示
    unset = sorted(init_keys - par_sim)

    if unread:
        return RelationResult(
            rule_id="par_init_key_match",
            name=".par 的 sim_* 键与 Simulation_init.F90 读取键一致",
            status=False,
            message=(f".par 设置了 {len(unread)} 个 Simulation_init.F90 未读取的 "
                     f"sim_* 键（参数不会生效）: {unread}"),
            details={"unread": unread, "unset": unset},
        )
    msg = f".par 与 Simulation_init.F90 的 sim_* 键一致（{len(par_sim)} 项）"
    if unset:
        msg += f"；另有 {len(unset)} 个 init 读取的键走 Config 默认: {unset}"
    return RelationResult(
        rule_id="par_init_key_match",
        name=".par 的 sim_* 键与 Simulation_init.F90 读取键一致",
        status=True, message=msg,
        details={"unread": unread, "unset": unset},
    )
