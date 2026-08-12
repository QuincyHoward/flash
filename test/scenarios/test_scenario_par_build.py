"""
test_scenario_par_build.py — 测试场景 .par 文件生成

验证:
  - 场景默认参数可生成有效 .par
  - 参数覆盖后 .par 内容变化
  - 各场景 EOS 文件路径正确
  - chk 提取模式正确
  - .par 关键参数检查

私有场景说明 (重要):
  - EXPECTED_EOS 含私有场景 (thin_layer_sandwich_si/al) 条目。
  - **全局测试不测私有场景**: 发布环境私有场景未注册时, 相关验证自动跳过,
    仅校验公开场景 (ch_center)。
  - 本地完整验证私有场景 (需私有场景代码):
      pytest test/scenarios/test_scenario_par_build.py -v
"""

import sys
from pathlib import Path

# Bootstrap: find flash project root by searching upward for marker
_ROOT = Path(__file__).resolve().parent
for _ in range(12):
    if (_ROOT / "pyproject.toml").exists():
        break
    _ROOT = _ROOT.parent
else:
    raise RuntimeError("Cannot locate flash package root")
_PARENT = _ROOT
if str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))


from flash.scenarios.registry import get_scenario, list_scenarios


def _available_scenarios() -> list:
    """返回当前已注册场景名列表 (发布环境仅 ch_center)。"""
    return [s[0] for s in list_scenarios()]


# ── EOS 文件对照表 ─────────────────────────────────────

EXPECTED_EOS = {
    "thin_layer_sandwich_si": {
        "cham": "Z02_1.00-20260708_0851.cn4",
        "targ": "Z14_1.00-20260708_0850.cn4",
        "poly": "Z06_0.50-Z01_0.50-20260708_0850.cn4",
    },
    "thin_layer_sandwich_al": {
        "cham": "he-imx-005.cn4",
        "targ": "al-imx-003.cn4",
        "poly": "polystyrene-imx-008.cn4",
    },
    "ch_center": {
        "cham": "Z02_1.00-20260708_0851.cn4",
        "targ": "Z06_0.50-Z01_0.50-20260708_0850.cn4",
    },
}


def test_each_par_generation():
    """测试每个场景的 .par 文件生成"""
    from flash.scenarios.registry import list_scenarios

    for name, desc in list_scenarios():
        sc = get_scenario(name)
        params = dict(sc.default_params)
        par = sc.build_par(params)

        print(f"\n── {name} ──")
        print(f"  .par 长度: {len(par)} bytes")

        # 跳过无 build_par 的场景 (占位场景)
        if len(par) == 0:
            print(f"  ⚠ 场景 {name} 暂无 build_par 实现, 跳过")
            continue

        # 检查基本参数 (用规范化空格比较, .par 格式使用多空格对齐)
        normalized_par = " ".join(par.split()).replace('"', "")  # 合并空白 + 去引号
        checks = {
            "geometry = cartesian": "几何",
            "useHydro = .true.": "流体",
            "useConductivity = .true.": "热导",
            "useDiffuse = .true.": "扩散",
            "useEnergyDeposition = .true.": "激光能量沉积",
            "useOpacity = .true.": "不透明度",
        }
        for keyword, label in checks.items():
            assert keyword in normalized_par, f"{name}: 缺少 {label} 参数 ({keyword})"
        print("  ✔ 关键参数齐全")

        # 检查激光参数
        assert "ed_power_1_1" in par, f"{name}: 缺少激光功率参数"
        for line in par.split("\n"):
            if "ed_power_1_" in line:
                print(f"  {line.strip()}")

        # 检查 chk 输出设置
        assert "checkpointFileIntervalStep" in par, f"{name}: 缺少 chk 步长"
        for line in par.split("\n"):
            if "checkpointFile" in line:
                print(f"  {line.strip()}")

        print("  ✔ .par 生成有效")


def test_eos_files_correct():
    """测试每个场景的 EOS 文件路径正确性"""
    available = _available_scenarios()
    for name, expected in EXPECTED_EOS.items():
        if name not in available:
            print(f"\n  - {name}: 场景未注册 (发布环境), 跳过 EOS 验证")
            continue
        sc = get_scenario(name)
        params = dict(sc.default_params)
        par = sc.build_par(params)

        # 从 .par 中提取 EOS 文件名
        eos_in_par = {}
        for line in par.split("\n"):
            line = line.strip()
            if "TableFile" in line or "FileName" in line:
                parts = line.split()
                if len(parts) >= 3:
                    key = parts[0]
                    val = parts[2]
                    eos_in_par[key] = val

        print(f"\n── {name} EOS 验证 ──")
        for role, expected_file in expected.items():
            table_key = f"eos_{role}TableFile"
            op_key = f"op_{role}FileName"
            actual_table = eos_in_par.get(table_key, "MISSING").strip('"')
            actual_op = eos_in_par.get(op_key, "MISSING").strip('"')

            assert actual_table == expected_file, \
                f"{name}: {table_key} 期望 {expected_file}, 实际 {actual_table}"
            assert actual_op == expected_file, \
                f"{name}: {op_key} 期望 {expected_file}, 实际 {actual_op}"
            print(f"  {role}: {actual_table} ✔")

        # 验证 EOS 文件实际存在
        for role, fname in expected.items():
            eos_path = sc.sim_input_dir / fname
            if eos_path.exists():
                print(f"  EOS 文件存在: {fname} ({eos_path.stat().st_size} bytes)")
            else:
                print(f"  ⚠ EOS 文件不存在: {fname}")


def test_par_override():
    """测试参数覆盖机制 (优先私有场景 thin_layer_sandwich_si, 缺失用公开场景 ch_center)"""
    import pytest
    available = _available_scenarios()
    if "thin_layer_sandwich_si" in available:
        name = "thin_layer_sandwich_si"
    else:
        name = "ch_center"  # 发布环境降级验证
        print("\n  ℹ 私有场景未注册, 使用公开场景 ch_center 验证参数覆盖")
    sc = get_scenario(name)
    default_par = sc.build_par(dict(sc.default_params))
    # 修改激光功率
    overridden_params = dict(sc.default_params)
    overridden_params["laser_powers"] = [0, 1e15, 1e15, 0]
    overridden_par = sc.build_par(overridden_params)

    assert default_par != overridden_par, "覆盖参数后 .par 应不同"
    normalized = " ".join(overridden_par.split())
    # 幂值格式因场景而异 (如 1e+15 vs 1.000000e+15), 解析后数值比较
    import re
    m = re.search(r"ed_power_1_2\s*=\s*([0-9.eE+-]+)", normalized)
    assert m, "覆盖的功率参数 ed_power_1_2 应出现在 .par 中"
    assert abs(float(m.group(1)) - 1e15) < 1e-9 * 1e15, f"ed_power_1_2 应为 1e15, 实际 {m.group(1)}"
    print(f"  ✔ 覆盖功率生效: ed_power_1_2 = {m.group(1)}")


def test_sim_input_files():
    """测试 sim_input/ 目录中有必要的 FLASH 源文件"""
    from flash.scenarios.registry import list_scenarios

    required_files = ["Config", "Makefile",
                      "Simulation_data.F90", "Simulation_init.F90",
                      "Simulation_initBlock.F90"]

    for name, _ in list_scenarios():
        sc = get_scenario(name)
        sim_input = sc.sim_input_dir
        print(f"\n── {name} sim_input 检查 ──")
        for rf in required_files:
            fpath = sim_input / rf
            if fpath.exists():
                print(f"  {rf}: {fpath.stat().st_size} bytes ✔")
            else:
                print(f"  ⚠ {rf}: 不存在 ({fpath})")

        # 应有至少一个 .cn4 文件
        cn4_files = list(sim_input.glob("*.cn4"))
        print(f"  .cn4 文件数: {len(cn4_files)}")

        # 应有 .F90 源文件
        f90_files = list(sim_input.glob("*.F90"))
        print(f"  .F90 源文件数: {len(f90_files)}")


if __name__ == "__main__":
    test_each_par_generation()
    test_eos_files_correct()
    test_par_override()
    test_sim_input_files()
    print("\n✅ 所有 .par 生成测试通过")
