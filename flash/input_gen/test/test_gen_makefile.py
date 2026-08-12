"""测试 gen_makefile/ 子包。"""


class TestGenMakefile:
    def test_import(self):
        from flash.input_gen.gen_makefile import MakefileGenerator
        assert MakefileGenerator is not None

    def test_generate(self):
        from flash.input_gen.gen_makefile import MakefileGenerator
        gen = MakefileGenerator()
        content = gen.generate()
        assert isinstance(content, str)

    def test_save(self, tmp_output_dir):
        from flash.input_gen.gen_makefile import MakefileGenerator
        gen = MakefileGenerator()
        path = gen.save(str(tmp_output_dir / "Makefile"))
        assert path.exists()
        assert path.name == "Makefile"
