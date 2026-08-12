"""input_gen 模块测试的共享 fixtures。

flash 独立包模式：flash/ 是顶层目录。
"""

import sys
import pytest
from pathlib import Path

# =======================================================================
# 路径设置：flash 独立包模式
# =======================================================================

def _setup_path():
    """设置 sys.path，将 flash/ 的父目录添加到路径。"""
    current_file = Path(__file__).resolve()
    flash_dir = current_file.parent.parent.parent  # flash/
    parent_dir = flash_dir.parent  # flash/ 的父目录
    if str(parent_dir) not in sys.path:
        sys.path.insert(0, str(parent_dir))
    return "standalone"


# 设置路径
_RUN_MODE = _setup_path()


# =======================================================================
# Fixtures
# =======================================================================

@pytest.fixture
def tmp_output_dir(tmp_path):
    """临时输出目录。"""
    d = tmp_path / "flash_input_gen_test"
    d.mkdir()
    return d


@pytest.fixture
def laserslab_template_dir():
    """LaserSlab 模板目录路径。"""
    flash_dir = Path(__file__).resolve().parent.parent.parent
    return flash_dir / "scenarios" / "flash_demo" / "LaserSlab"


@pytest.fixture
def default_par_generator():
    """默认 ParGenerator 实例。"""
    from flash.input_gen.gen_par.generator import ParGeneratorExtended
    return ParGeneratorExtended(dimension=1)


@pytest.fixture
def flash_module():
    """返回 flash 模块。"""
    import flash
    return flash


@pytest.fixture
def run_mode():
    """返回当前运行模式（始终为 standalone）。"""
    return "standalone"
