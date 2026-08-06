"""
gen_eos_op — EOS/opacity 表文件管理

管理 .cn4 格式的 EOS/opacity 表文件。
支持文件查找、复制、验证和 ionmix 生成（占位）。
"""

from .generator import EOSOpacityGenerator, EOSMaterial, DEFAULT_GRUPBD, DEFAULT_SPEC

__all__ = ["EOSOpacityGenerator", "EOSMaterial", "DEFAULT_GRUPBD", "DEFAULT_SPEC"]
