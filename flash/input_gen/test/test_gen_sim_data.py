"""测试 gen_sim_data/ 子包。"""


class TestGenSimData:
    def test_import(self):
        from flash.input_gen.gen_sim_data import SimDataGenerator
        assert SimDataGenerator is not None

    def test_generate(self):
        from flash.input_gen.gen_sim_data import SimDataGenerator
        gen = SimDataGenerator()
        content = gen.generate()
        assert isinstance(content, str)
        assert "module Simulation_data" in content

    def test_save(self, tmp_output_dir):
        from flash.input_gen.gen_sim_data import SimDataGenerator
        gen = SimDataGenerator()
        path = gen.save(str(tmp_output_dir / "Simulation_data.F90"))
        assert path.exists()
        assert path.name == "Simulation_data.F90"

    def test_content_has_module(self):
        from flash.input_gen.gen_sim_data import SimDataGenerator
        gen = SimDataGenerator()
        content = gen.generate()
        assert "module Simulation_data" in content
