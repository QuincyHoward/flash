"""测试 create_input_files 一键生成函数与 demo 脚本兼容性。"""


class TestCreateInputFiles:
    def test_create_input_files_1d(self, tmp_output_dir):
        from flash.input_gen import create_input_files
        result = create_input_files(
            output_dir=str(tmp_output_dir / "sim1d"),
            dimension=1,
            generate_scripts=True,
            copy_eos_files=True,
        )
        assert "par" in result
        assert "config" in result
        assert "makefile" in result
        assert "sim_init" in result
        assert "sim_initblock" in result
        assert "sim_data" in result

        # 验证文件存在
        for key in ("par", "config", "makefile", "sim_init", "sim_initblock"):
            p = result[key]
            import os
            assert os.path.exists(p), f"{key} file not found: {p}"

    def test_create_input_files_scripts(self, tmp_output_dir):
        from flash.input_gen import create_input_files
        result = create_input_files(
            output_dir=str(tmp_output_dir / "sim_scripts"),
            generate_scripts=True,
            copy_eos_files=False,
        )
        assert "script_windows" in result
        assert "script_wsl" in result
        assert "script_slurm" in result

    def test_create_input_files_2d(self, tmp_output_dir):
        from flash.input_gen import create_input_files
        result = create_input_files(
            output_dir=str(tmp_output_dir / "sim2d"),
            dimension=2,
            generate_scripts=False,
            copy_eos_files=False,
        )
        assert "par" in result

    def test_create_input_files_3d(self, tmp_output_dir):
        from flash.input_gen import create_input_files
        result = create_input_files(
            output_dir=str(tmp_output_dir / "sim3d"),
            dimension=3,
            generate_scripts=False,
            copy_eos_files=False,
        )
        assert "par" in result
