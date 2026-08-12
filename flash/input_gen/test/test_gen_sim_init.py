"""测试 gen_sim_init/ 子包。"""


class TestGenSimInit:
    def test_import(self):
        from flash.input_gen.gen_sim_init import SimInitGenerator
        assert SimInitGenerator is not None

    def test_generate(self):
        from flash.input_gen.gen_sim_init import SimInitGenerator
        gen = SimInitGenerator()
        content = gen.generate()
        assert isinstance(content, str)
        assert len(content) > 50
        assert "Simulation_init" in content

    def test_save(self, tmp_output_dir):
        from flash.input_gen.gen_sim_init import SimInitGenerator
        gen = SimInitGenerator()
        path = gen.save(str(tmp_output_dir / "Simulation_init.F90"))
        assert path.exists()
        assert path.name == "Simulation_init.F90"
