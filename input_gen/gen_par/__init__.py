"""
gen_par — .par 参数文件生成器 (自包含)

无外部依赖，所有默认值硬编码在 defaults.py 中。
"""

from .generator import ParGeneratorExtended, BeamConfig
from .materials import Material, MATERIALS, CHAMBER_GASES, get_material, list_materials

__all__ = [
    "ParGeneratorExtended",
    "BeamConfig",
    "Material",
    "MATERIALS",
    "CHAMBER_GASES",
    "get_material",
    "list_materials",
]
