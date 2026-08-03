"""兼容性模块：支持 flash 独立包运行模式。

此模块提供导入功能，确保测试在 flash 独立包模式下正常工作。
flash 是最顶层包目录。
"""

import sys
import importlib
from pathlib import Path


# =======================================================================
# 导入路径设置
# =======================================================================

def setup_import_path():
    """设置导入路径：将 flash/ 的父目录添加到 sys.path。"""
    current_file = Path(__file__).resolve()
    test_dir = current_file.parent  # input_gen/test/
    input_gen_dir = test_dir.parent  # input_gen/
    flash_dir = input_gen_dir.parent  # flash/
    parent_dir = flash_dir.parent  # flash/ 的父目录

    if str(parent_dir) not in sys.path:
        sys.path.insert(0, str(parent_dir))
    return parent_dir


# =======================================================================
# 智能导入函数
# =======================================================================

def import_from_flash(module_path, class_name=None):
    """从 flash 模块导入。

    参数:
        module_path: 模块路径，例如 "input_gen.gen_par.generator"
        class_name: 类名（可选），如果提供，返回类；否则返回模块

    返回:
        类或模块
    """
    setup_import_path()

    # 构建完整的模块路径（flash 独立包）
    full_module_path = f"flash.{module_path}"

    # 导入模块
    module = importlib.import_module(full_module_path)

    # 如果指定了类名，返回类
    if class_name:
        return getattr(module, class_name)
    else:
        return module


def get_flash_module():
    """获取 flash 模块。"""
    setup_import_path()
    import flash
    return flash


# =======================================================================
# 常用导入（预导入，方便使用）
# =======================================================================

# 设置路径
setup_import_path()

# 导出常用类
try:
    ParGeneratorExtended = import_from_flash("input_gen.gen_par.generator", "ParGeneratorExtended")
    BeamConfig = import_from_flash("input_gen.gen_par.generator", "BeamConfig")
except ImportError:
    ParGeneratorExtended = None
    BeamConfig = None

try:
    ShellScriptGenerator = import_from_flash("input_gen.gen_shell_script.generator", "ShellScriptGenerator")
except ImportError:
    ShellScriptGenerator = None

try:
    ConfigGenerator = import_from_flash("input_gen.gen_config.generator", "ConfigGenerator")
except ImportError:
    ConfigGenerator = None

try:
    CheckerGenerator = import_from_flash("input_gen.gen_checker.generator", "CheckerGenerator")
except ImportError:
    CheckerGenerator = None

# 导出路径信息
FLASH_DIR = Path(__file__).resolve().parent.parent.parent
RUN_MODE = "standalone"
