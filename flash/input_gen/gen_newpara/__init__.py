"""
gen_newpara — 新参数多区控制生成器
════════════════════════════════

基于 test/newpara/ 的参考实现，提供 Multi-Zone + Density Profile 的
FLASH 源文件生成能力。

核心类:
  NewParaGenerator — 生成含密度剖面的多区 FLASH 仿真输入文件

依赖:
  gen_config.ConfigGenerator
  gen_sim_data.SimDataGenerator
  gen_sim_init.SimInitGenerator
  gen_sim_initblock.BlockGenerator
"""
from .generator import NewParaGenerator

__all__ = ["NewParaGenerator"]
