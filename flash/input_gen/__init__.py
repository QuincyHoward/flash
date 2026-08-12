"""
FLASH 仿真输入文件生成器 v2.0 (自包含)
═══════════════════════════════════════

所有 gen_* 子包完全自包含，不依赖外部模板文件。

子包:
  gen_config/         - Config 文件生成 (ConfigGenerator)
  gen_par/            - .par 参数文件生成 (ParGeneratorExtended)
  gen_makefile/       - Makefile 生成 (MakefileGenerator)
  gen_sim_data/       - Simulation_data.F90 (SimDataGenerator)
  gen_sim_init/       - Simulation_init.F90 (SimInitGenerator)
  gen_sim_initblock/  - Simulation_initBlock.F90 (BlockGenerator)
  gen_eos_op/         - EOS/opacity 表文件 (EOSOpacityGenerator)
  gen_shell_script/   - 平台运行脚本 (ShellScriptGenerator)
  gen_checker/        - 依赖检查 (DependencyChecker)
  gen_checker/ploter/ - 绘图 (PulsePlotter, DensityPlotter, RayPlotter)

统一接口:
  create_input_files(): 一键生成所有 FLASH 输入文件
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# ── 便捷一键生成函数 ─────────────────────────────────


def create_input_files(
    output_dir: Union[str, Path],
    dimension: int = 1,
    simulation_name: str = "LaserSlab",
    target_material: str = "aluminum",
    chamber_gas: str = "helium",
    n_beams: int = 1,
    par_filename: str = "laserslab.par",
    generate_scripts: bool = True,
    copy_eos_files: bool = True,
    setup_cmd: Optional[str] = None,
    sim_user_dir: Optional[str] = None,
    platform: str = "local",
) -> Dict[str, str]:
    """一键生成所有 FLASH 输入文件。

    使用硬编码默认参数生成完整的仿真目录结构。

    Args:
        output_dir: 输出根目录
        dimension: 仿真维度 (1/2/3)
        simulation_name: 仿真名称
        target_material: 靶材名称
        chamber_gas: 腔室气体名称
        n_beams: 光束数量
        par_filename: .par 文件名
        generate_scripts: 是否生成运行脚本
        copy_eos_files: 是否复制 .cn4 文件
        setup_cmd: 完整 setup 命令 (含 -objdir 和 -par_file, 如
                   "./setup -auto <用户名>/LaserSlab_local ... -objdir=<用户名>/LaserSlab_local -par_file=run.par")
                   (注: <用户名> 通过 flash._core.credentials 设置, 勿硬编码)
                   为 None 时使用默认命令 (不含 -objdir, 由脚本自动追加)
        sim_user_dir: 用户目录前缀 (None = 从 flash._core.credentials 读取,
                      读取不到回退默认; 勿硬编码用户名)
        platform: 目标平台标识
                  "local"              — 本地, 取第一个 local 环境 (如 wsl_ubuntu22)
                  "local/wsl_ubuntu22" — 指定本地环境
                  "hpc"                — 超算, 取第一个 hpc 环境 (如 scfa2696)
                  "hpc/scfa2696"       — 指定超算账号环境

    Returns:
        {文件类型: 文件路径} 字典
    """
    # 用户名: flash._core.credentials → 默认 (勿硬编码用户名)
    if sim_user_dir is None:
        try:
            from flash._core.credentials import get_user_name
            sim_user_dir = get_user_name()
        except Exception:
            sim_user_dir = "hello"  # 读取不到 → 默认用户名
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    result: Dict[str, str] = {}

    # 1. 生成 .par 文件
    from flash.input_gen.gen_par import ParGeneratorExtended

    gen = ParGeneratorExtended(
        simulation_name=simulation_name,
        dimension=dimension,
    )
    par_path = gen.save(str(out / par_filename))
    result["par"] = str(par_path)

    # 2. 生成 Config 文件
    from flash.input_gen.gen_config import ConfigGenerator

    config_gen = ConfigGenerator()
    config_path = config_gen.save(str(out / "Config"))
    result["config"] = str(config_path)

    # 3. 生成 Makefile
    from flash.input_gen.gen_makefile import MakefileGenerator

    mf_gen = MakefileGenerator()
    mf_path = mf_gen.save(str(out / "Makefile"))
    result["makefile"] = str(mf_path)

    # 4. 生成 Simulation_data.F90
    from flash.input_gen.gen_sim_data import SimDataGenerator

    sd_gen = SimDataGenerator()
    sd_path = sd_gen.save(str(out / "Simulation_data.F90"))
    result["sim_data"] = str(sd_path)

    # 5. 生成 Simulation_init.F90
    from flash.input_gen.gen_sim_init import SimInitGenerator

    si_gen = SimInitGenerator()
    si_path = si_gen.save(str(out / "Simulation_init.F90"))
    result["sim_init"] = str(si_path)

    # 6. 生成 Simulation_initBlock.F90
    from flash.input_gen.gen_sim_initblock import BlockGenerator, GridBuilder

    if dimension == 1:
        builder = GridBuilder.from_laserslab_1d()
    elif dimension == 2:
        builder = GridBuilder(dim=2, geometry="cylindrical",
                              domain={"x": (0, 40e-4), "y": (0, 80e-4)})
    else:
        builder = GridBuilder(dim=3, geometry="cartesian",
                              domain={"x": (-40e-4, 40e-4), "y": (0, 40e-4), "z": (-40e-4, 40e-4)})

    block_gen = BlockGenerator(simulation_name=simulation_name)
    block_gen.build(builder)
    block_path = block_gen.save(str(out / "Simulation_initBlock.F90"))
    result["sim_initblock"] = str(block_path)

    # 7. 复制 .cn4 EOS 文件
    if copy_eos_files:
        from flash.input_gen.gen_eos_op import EOSOpacityGenerator

        eos_gen = EOSOpacityGenerator()
        for mat_name in [target_material, chamber_gas]:
            copied = eos_gen.copy_eos_file(mat_name, str(out))
            if copied:
                result[f"eos_{mat_name}"] = str(copied)

    # 8. 生成运行脚本
    if generate_scripts:
        from flash.input_gen.gen_shell_script import ShellScriptGenerator

        # 构建脚本配置 (含维度和平台, 使 ShellScriptGenerator 可自动加载 resource_config)
        script_config = {
            "sim_user_dir": sim_user_dir,
            "dimension": dimension,
            "platform": platform,
        }
        if setup_cmd is not None:
            script_config["setup_cmd"] = setup_cmd

        script_gen = ShellScriptGenerator(config=script_config)
        script_gen.save(str(out / "run_flash.bat"), "windows", par_file=par_filename)
        script_gen.save(str(out / "run_flash.sh"), "wsl", par_file=par_filename)
        script_gen.save(str(out / "submit_flash.sh"), "slurm", par_file=par_filename)
        result["script_windows"] = str(out / "run_flash.bat")
        result["script_wsl"] = str(out / "run_flash.sh")
        result["script_slurm"] = str(out / "submit_flash.sh")

    return result
