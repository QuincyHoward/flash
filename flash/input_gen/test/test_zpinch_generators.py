"""测试 ZPinch 隔离生成器族（gen_config/gen_sim_data/gen_sim_init/
gen_sim_initblock/gen_sim_adjustevo 的 zpinch_* 模块）+ 防污染断言。

隔离铁律：ZPinch 生成器与激光系 gen_par 主文件零 import、零共享状态；
激光默认参数（ed_*/rt_mgd* 10 群）绝不进入 ZPinch 参数集。
"""

import sys

import pytest

ZPINCH_MARKERS = {
    "Config": "REQUIRES physics/sourceTerms/Circuit/CircuitMain/FileInput",
    "Simulation_data.F90": "module Simulation_data",
    "Simulation_init.F90": "subroutine Simulation_init",
    "Simulation_initBlock.F90": "subroutine Simulation_initBlock",
    "Simulation_adjustEvolution.F90": "Simulation_adjustEvolution",
}


def _generators():
    """返回 {文件名: 生成器类}。"""
    from flash.input_gen.gen_config.zpinch_config import ZPinchConfigGenerator
    from flash.input_gen.gen_sim_adjustevo import SimAdjustEvoGenerator
    from flash.input_gen.gen_sim_data.zpinch_data import ZPinchSimDataGenerator
    from flash.input_gen.gen_sim_init.zpinch_init import ZPinchSimInitGenerator
    from flash.input_gen.gen_sim_initblock.zpinch_initblock import (
        ZPinchBlockGenerator,
    )
    return {
        "Config": ZPinchConfigGenerator,
        "Simulation_data.F90": ZPinchSimDataGenerator,
        "Simulation_init.F90": ZPinchSimInitGenerator,
        "Simulation_initBlock.F90": ZPinchBlockGenerator,
        "Simulation_adjustEvolution.F90": SimAdjustEvoGenerator,
    }


class TestZpinchGenerators:
    @pytest.mark.parametrize("name", list(ZPINCH_MARKERS))
    def test_import(self, name):
        cls = _generators()[name]
        assert cls is not None

    @pytest.mark.parametrize("name", list(ZPINCH_MARKERS))
    def test_generate_contains_marker(self, name):
        cls = _generators()[name]
        content = cls().generate()
        assert isinstance(content, str)
        assert ZPINCH_MARKERS[name] in content

    @pytest.mark.parametrize("name", list(ZPINCH_MARKERS))
    def test_save(self, name, tmp_output_dir):
        cls = _generators()[name]
        path = cls().save(str(tmp_output_dir / name))
        assert path.exists()

    def test_zpinch_param_markers(self):
        from flash.input_gen.gen_par.zpinch_par import ZPINCH_BASELINE
        # ZPinch 特有键存在
        for k in ("sim_rhoType", "sim_innerRadius", "circ_currFile",
                  "sim_trajOutputInterval", "sim_rNearStag", "res_vacSpec"):
            assert k in ZPINCH_BASELINE
        # 激光专属键不存在
        for k in ("ed_numberOfBeams", "ed_wavelength_1", "ed_lensX_1",
                  "ed_maxPulseSections"):
            assert k not in ZPINCH_BASELINE


class TestIsolationFromLaserGenPar:
    """防污染断言：激光参数绝不加载进 zpinch 参数集。"""

    def test_zpinch_par_not_exported_by_gen_par_init(self):
        import flash.input_gen.gen_par as gp
        exported = getattr(gp, "__all__", [])
        assert not any("zpinch" in name.lower() for name in exported)

    def test_laser_defaults_not_imported_by_zpinch_module(self):
        # AST 级检查: zpinch_par 的 import 只允许标准库,
        # 不得 import gen_par 激光实现 (defaults/generator/materials/par_comments)
        import ast
        import flash.input_gen.gen_par.zpinch_par as zp
        tree = ast.parse(open(zp.__file__, encoding="utf-8").read())
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    imported.add(a.name)
            elif isinstance(node, ast.ImportFrom):
                imported.add(node.module or "")
        allowed = {"", "pathlib", "copy", "typing", "__future__"}
        bad = [m for m in imported if m not in allowed
               and not m.startswith(allowed)]
        assert not bad, f"zpinch_par 引入了非标准库 import: {bad}"

    def test_laser_generator_output_has_no_zpinch_species(self):
        # 正向隔离：激光默认输出不含 ZPinch 物种族键
        from flash.input_gen.gen_par import ParGeneratorExtended
        gen = ParGeneratorExtended(simulation_name="LaserSlab", dimension=1)
        content = gen.generate()
        for k in ("sim_fill_dens", "sim_line_dens", "circ_currFile",
                  "sim_rNearStag"):
            assert k not in content

    def test_gen_par_module_graph_clean(self):
        # import zpinch_par 会机制性执行包 gen_par/__init__.py（Python 包行为）,
        # 因此检查对象是 zpinch_par 模块命名空间: 不得含任何激光符号。
        import flash.input_gen.gen_par.zpinch_par as zp
        for sym in ("ParGeneratorExtended", "Material", "MATERIALS",
                    "CHAMBER_GASES", "get_material", "list_materials",
                    "BeamConfig", "PARAM_COMMENTS", "LAYER_TRACER_BASELINE"):
            assert not hasattr(zp, sym), f"zpinch_par 命名空间含激光符号: {sym}"
