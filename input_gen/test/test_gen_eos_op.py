"""测试 gen_eos_op/ 子包。"""


class TestGenEosOp:
    def test_import(self):
        from flash.input_gen.gen_eos_op import EOSOpacityGenerator
        assert EOSOpacityGenerator is not None

    def test_material_registry(self):
        """测试材料查找包含已知材料。"""
        from flash.input_gen.gen_eos_op import EOSOpacityGenerator
        gen = EOSOpacityGenerator()
        # 通过别名查找铝
        path_al = gen.get_eos_file("aluminum")
        path_he = gen.get_eos_file("helium")
        # 如果 eos_op_data/ 下有对应文件，路径应存在
        if path_al:
            assert path_al.exists()
        if path_he:
            assert path_he.exists()

    def test_get_eos_file(self):
        from flash.input_gen.gen_eos_op import EOSOpacityGenerator
        gen = EOSOpacityGenerator()
        path = gen.get_eos_file("aluminum")
        # 如果 eos_op_data/ 下有 .cn4 文件，应该能找到
        if path:
            assert path.exists()

    def test_list_materials(self):
        from flash.input_gen.gen_eos_op import EOSOpacityGenerator
        gen = EOSOpacityGenerator()
        materials = gen.list_available_materials()
        assert isinstance(materials, list)

    def test_verify_eos_file(self, tmp_output_dir):
        from flash.input_gen.gen_eos_op import EOSOpacityGenerator
        gen = EOSOpacityGenerator()

        # 创建假的 .cn4 文件
        fake = tmp_output_dir / "fake.cn4"
        fake.write_text("21 25\n atomic #s of gases: 13\n relative fractions: 1.0\n 6\n")
        result = gen.verify_eos_file(str(fake))
        # verify_eos_file 返回 dict，valid=True 表示成功
        assert isinstance(result, dict)
        assert result.get("valid") is True

        # 空文件应该验证失败
        empty = tmp_output_dir / "empty.cn4"
        empty.write_text("")
        result_empty = gen.verify_eos_file(str(empty))
        assert isinstance(result_empty, dict)
        assert result_empty.get("valid") is not True

    def test_copy_eos_file(self, tmp_output_dir):
        from flash.input_gen.gen_eos_op import EOSOpacityGenerator
        gen = EOSOpacityGenerator()

        # 无论是否找到源文件，方法应该正常返回不抛异常
        copied = gen.copy_eos_file("aluminum", str(tmp_output_dir))
        if copied:
            assert copied.exists()

    def test_generate_via_ionmix(self):
        from flash.input_gen.gen_eos_op import EOSOpacityGenerator
        gen = EOSOpacityGenerator()
        import pytest
        with pytest.raises(NotImplementedError):
            gen.generate_via_ionmix("test", "/tmp/test.cn4")
