"""
extraction_modes.py — FLASH 数据提取方案模式注册表
========================================================

统一管理 output_processors 的 AMR 数据提取方案，支持一行代码切换
当前使用的提取模式。

模式字典 EXTRACTION_MODES:
  - "h5py": 纯 h5py 实现 (FlashHDF5File.extract_var_yt_style)
            无需安装 yt，超算环境优先（推荐默认）。
  - "yt":   基于 yt 库的实现 (FlashHDF5File.extract_var_with_yt)
            适合本地安装 yt 的对比验证环境。

一行切换（优先级 h5py）:
    from flash.output_processors.extraction_modes import CURRENT_EXTRACTION_MODE
    CURRENT_EXTRACTION_MODE = "yt"   # ← 切换当前提取模式

运行时切换:
    from flash.output_processors.extraction_modes import set_extraction_mode
    set_extraction_mode("yt")

环境变量覆盖 (CI/HPC 免改代码):
    设置 FLASH_EXTRACTION_MODE=yt 即可在不修改代码配置的前提下
    强制使用 yt 模式; 未设置时回落到 CURRENT_EXTRACTION_MODE。
    生效优先级: extract_var(mode=...) > FLASH_EXTRACTION_MODE > CURRENT_EXTRACTION_MODE。

两种模式返回格式一致:
    1D: (x, data)
    2D: (x, y, data)
    3D: (x, y, z, data)
"""

import os

# ═══════════════════════════════════════════════════════════════
#  模式字典 — 数据提取方案注册表
# ═══════════════════════════════════════════════════════════════

EXTRACTION_MODES: dict[str, dict] = {
    "h5py": {
        "description": "纯 h5py 实现 (无 yt 依赖, 超算环境优先, 推荐默认)",
        "implementation": "FlashHDF5File.extract_var_yt_style",
        "requires": ["h5py"],
    },
    "yt": {
        "description": "基于 yt 库的实现 (需安装 yt, 适合本地对比验证)",
        "implementation": "FlashHDF5File.extract_var_with_yt",
        "requires": ["yt"],
    },
}

# ★ 一行代码切换当前数据提取模式 (默认优先 h5py)
CURRENT_EXTRACTION_MODE: str = "h5py"


# ── 模式查询与切换 ────────────────────────────────────────────


def get_extraction_mode() -> str:
    """返回当前数据提取模式名。"""
    return CURRENT_EXTRACTION_MODE


def set_extraction_mode(mode: str) -> None:
    """切换当前数据提取模式。

    参数:
        mode: 模式名, 必须已在 EXTRACTION_MODES 中注册 ('h5py' / 'yt')
    抛出:
        ValueError: 未注册的模式名
    """
    if mode not in EXTRACTION_MODES:
        raise ValueError(
            f"未知提取模式: {mode!r}, 可用模式: {sorted(EXTRACTION_MODES)}"
        )
    global CURRENT_EXTRACTION_MODE
    CURRENT_EXTRACTION_MODE = mode


def resolve_extraction_mode(mode: str | None = None) -> str:
    """解析最终生效的提取模式。

    生效优先级:
      1. 显式传入的 mode 参数
      2. 环境变量 FLASH_EXTRACTION_MODE (CI/HPC 免改代码)
      3. 代码配置 CURRENT_EXTRACTION_MODE (一行切换)

    参数:
        mode: 显式指定的模式 (None = 按上述优先级回落到当前默认模式)
    返回:
        模式名
    """
    if mode is not None:
        return mode
    env = os.environ.get("FLASH_EXTRACTION_MODE")
    if env in EXTRACTION_MODES:
        return env
    return CURRENT_EXTRACTION_MODE


def available_extraction_modes() -> list[str]:
    """返回全部已注册的提取模式名。"""
    return sorted(EXTRACTION_MODES.keys())