"""测试 gen_sim_initblock/ 子包。"""


class TestGenSimInitBlock:
    def test_import(self):
        from flash.input_gen.gen_sim_initblock import (
            BlockGenerator, GridBuilder, Region, GridSpec, BlockVisualizer,
        )
        assert BlockGenerator is not None
        assert GridBuilder is not None
        assert Region is not None
        assert GridSpec is not None
        assert BlockVisualizer is not None
