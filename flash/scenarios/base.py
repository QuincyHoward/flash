"""仿真场景配置基类

每个物理场景 (如 thin_layer_sandwich_si, ch_center) 实例化一个
``SimulationScenario`` 对象, 提供引擎所需的一切场景参数。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple


@dataclass
class SimulationScenario:
    """场景定义

    Attributes:
        name:                 场景唯一名称 (如 "thin_layer_sandwich_si")
        description:          人类可读描述 (用于 CLI 帮助)
        scenario_dir:         场景所在目录 (自动填充)
        sim_input_dir:        FLASH 源文件目录 (.F90, Config, Makefile, .cn4)
        sim_name:             FLASH setup 内部名称
        flash_setup_args:     setup 命令行参数 (除 -objdir 外的全部)

        default_params:       默认参数 dict (被 FlashSimulatorEngine.run 的 override 覆盖)
        default_output_fields:默认输出字段列表

        build_par:            函数 (params) → .par 文件内容字符串
        build_grid:           函数 (params) → (t_grid, x_grid) numpy arrays
        interpolate:          函数 (flash_files, t_grid, x_grid, var_names) → {field: array}
    """
    name: str
    description: str
    scenario_dir: Path
    sim_input_dir: Path
    sim_name: str
    flash_setup_args: str
    run_dir_name: str = "runs"  # 运行目录名 (如 "runs", "runs_ch_center")

    default_params: Dict[str, Any] = field(default_factory=dict)
    default_output_fields: List[str] = field(default_factory=lambda: [
        "dens", "poly", "targ", "ye", "sumy",
        "tele", "tion", "trad",
        "pele", "pion", "prad", "pres", "velx",
    ])

    build_par: Callable = lambda params: ""
    build_grid: Callable = lambda params: (None, None)
    interpolate: Callable = lambda flash_files, t_grid, x_grid, var_names: {}

    def ensure_sim_input(self) -> None:
        """确保 FLASH 仿真输入文件 (sim_input_dir) 就绪, 供引擎/测试在运行前调用。

        默认实现: 目录已存在则无操作; 缺失时抛出 FileNotFoundError 并给出生成指引。
        生成目录设计的场景 (如 ch_center, 输入文件由 gen_flash_inputs.py 产生、
        不随仓库分发) 应覆盖本方法, 在缺失时自动调用生成器补齐。
        """
        if self.sim_input_dir.exists():
            return
        raise FileNotFoundError(
            f"场景 {self.name} 的输入目录不存在: {self.sim_input_dir}\n"
            f"  输入文件为生成物, 不随仓库分发; 请先运行生成器: "
            f"python {self.scenario_dir / 'gen_flash_inputs.py'} 后重试。"
        )
