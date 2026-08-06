"""
test_scenarios_imports.py — 测试 scenarios 包导入与注册

验证:
  - 各层 __init__.py 可正确导入
  - 注册表可列出所有场景
  - 每个场景可加载且元信息完整
  - 场景不依赖 flash_demo/
"""

import sys
from pathlib import Path

# ── 路径设置 ──────────────────────────────────────────

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

    """测试 scenarios 顶级包导入"""
    from flash.scenarios import (
        base, registry,
        plasma_preparation,
        collision_compression,
        center_evolution,
    )
    assert base.SimulationScenario is not None
    assert registry.get_scenario is not None
    print("✔ scenarios 顶级包导入成功")


def test_registry_list():
    """测试场景注册表列出所有场景"""
    import pytest
    from flash.scenarios.registry import list_scenarios

    scenarios = list_scenarios()
    names = [s[0] for s in scenarios]
    print(f"已注册 {len(scenarios)} 个场景: {names}")

    # 公开场景: ch_center 必须存在 (随包分发)
    assert len(scenarios) >= 1, f"至少应注册 1 个公开场景, 实际 {len(scenarios)}"
    assert "ch_center" in names

    # 私有场景 (仅本地): 存在则校验, 缺失 (发布环境) 则跳过
    private_names = ["thin_layer_sandwich_si", "thin_layer_sandwich_al", "grad_dens_sandwich"]
    present_private = [n for n in private_names if n in names]
    missing_private = [n for n in private_names if n not in names]
    if missing_private:
        pytest.skip(f"私有场景未注册 (发布环境): {missing_private}")

    for name, desc in scenarios:
        print(f"  {name}: {desc}")
        assert name, "场景名不能为空"
        assert desc, "场景描述不能为空"


def test_each_scenario_metadata():
    """测试每个场景的元信息完整性"""
    from flash.scenarios.registry import get_scenario, list_scenarios

    for name, _ in list_scenarios():
        sc = get_scenario(name)
        print(f"\n── {name} ──")
        print(f"  描述: {sc.description}")
        print(f"  目录: {sc.scenario_dir}")
        print(f"  sim_name: {sc.sim_name}")
        print(f"  sim_input 存在: {sc.sim_input_dir.exists()}")
        print(f"  flash_setup_args: {sc.flash_setup_args[:60]}...")
        print(f"  默认参数量: {len(sc.default_params)}")
        print(f"  输出字段量: {len(sc.default_output_fields)}")

        # 断言
        assert sc.name == name
        assert sc.sim_input_dir.exists(), f"{name}: sim_input 不存在!"
        assert sc.sim_name, f"{name}: sim_name 为空!"
        assert sc.flash_setup_args, f"{name}: flash_setup_args 为空!"
        assert len(sc.default_params) > 0, f"{name}: 无默认参数"
        assert len(sc.default_output_fields) > 0, f"{name}: 无输出字段"

        # 验证 build_par / build_grid / interpolate 可调用
        assert callable(sc.build_par), f"{name}: build_par 不可调用"
        assert callable(sc.build_grid), f"{name}: build_grid 不可调用"
        assert callable(sc.interpolate), f"{name}: interpolate 不可调用"

        print("  ✔ 通过")


def test_no_flash_demo_dependency():
    """验证注册场景不依赖 scenarios/flash_demo/ 路径（旧 Demo 目录）
    正式场景完全独立，仅引用自己的 sim_input 目录"""
    from flash.scenarios.registry import list_scenarios

    for name, _ in list_scenarios():
        from flash.scenarios.registry import get_scenario
        sc = get_scenario(name)
        sim_input_str = str(sc.sim_input_dir)
        scenario_dir_str = str(sc.scenario_dir)
        assert "scenarios/flash_demo" not in sim_input_str, \
            f"{name}: sim_input 路径包含 scenarios/flash_demo/! {sim_input_str}"
        assert "scenarios/flash_demo" not in scenario_dir_str, \
            f"{name}: scenario_dir 路径包含 scenarios/flash_demo/! {scenario_dir_str}"
    print("✔ 所有场景路径均不含 scenarios/flash_demo/")


if __name__ == "__main__":
    test_scenarios_package_import()
    test_registry_list()
    test_each_scenario_metadata()
    test_no_flash_demo_dependency()
    print("\n✅ 所有导入测试通过")
