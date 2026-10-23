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


class TestFlashHomePropagation:
    """回归护栏: FLASH_HOME 必须能透传到生成的脚本 (2026-10-23)。

    ★ 起因 (真实故障): demo 传的是 ``~/QC/FLASH/FLASH4.8`` (带用户名),
      而 ``ShellScriptGenerator`` 的默认是 ``$HOME/FLASH/FLASH4.8`` (不带用户名)。
      ``create_input_files`` 当时**没有 flash_home 形参** ⇒ 脚本拿到错误路径
      ⇒ run_flash.sh 的 ``[1/5] 环境检查`` 直接 ``exit 1``; 而调用方
      ``bash run_flash.sh | tail -100`` 取的是 tail 的返回码 ⇒ 报"仿真完成"、
      退出码 0, 实则零输出。

    护栏要点: 显式传入的 flash_home 必须**原样**出现在三份脚本里, 且
      **不得**回落到不带用户名的默认值。
    """

    FLASH_HOME = "~/QC/FLASH/FLASH4.8"

    def _read(self, result, key):
        import os
        assert key in result, f"{key} 未生成"
        with open(result[key], encoding="utf-8", errors="replace") as fh:
            return fh.read()

    def test_flash_home_written_into_scripts(self, tmp_output_dir):
        from flash.input_gen import create_input_files
        result = create_input_files(
            output_dir=str(tmp_output_dir / "fh"),
            dimension=1,
            generate_scripts=True,
            copy_eos_files=False,
            flash_home=self.FLASH_HOME,
        )
        for key in ("script_wsl", "script_windows", "script_slurm"):
            text = self._read(result, key)
            assert self.FLASH_HOME in text, (
                f"{key} 未包含传入的 FLASH_HOME={self.FLASH_HOME} — "
                f"脚本会指向错误目录导致 [1/5] exit 1"
            )

    def test_flash_home_not_defaulted_away(self, tmp_output_dir):
        """反向断言: 默认路径 ($HOME/FLASH/FLASH4.8) 不得混入自定义 flash_home 的脚本。"""
        from flash.input_gen import create_input_files
        result = create_input_files(
            output_dir=str(tmp_output_dir / "fh2"),
            dimension=1,
            generate_scripts=True,
            copy_eos_files=False,
            flash_home=self.FLASH_HOME,
        )
        text = self._read(result, "script_wsl")
        # 生成器写的是 FLASH_HOME="..." 赋值行; 若默认值混入会出现两次赋值
        assert text.count("FLASH_HOME=") == 1, (
            "run_flash.sh 中 FLASH_HOME 出现多次赋值 — "
            "自定义值被默认值覆盖, 后者生效"
        )

    def test_omitting_flash_home_keeps_legacy_default(self, tmp_output_dir):
        """不传 flash_home 时保持向后兼容 (仍用生成器默认值), 不报错。"""
        from flash.input_gen import create_input_files
        result = create_input_files(
            output_dir=str(tmp_output_dir / "fh3"),
            dimension=1,
            generate_scripts=True,
            copy_eos_files=False,
        )
        text = self._read(result, "script_wsl")
        assert "$HOME/FLASH/FLASH4.8" in text
