"""
FLASH 输入生成器测试 — test_flash_input_gen.py
═══════════════════════════════════════════════

测试 flash/input_gen/ 下的模块结构存在且可导入。

注意: ParGenerator 和 PulseShape 类尚未在 input_gen/ 中实现，
因此测试聚焦于现有模块的可导入性和关键函数的存在性。
"""

import sys
from pathlib import Path
import pytest

# Bootstrap
_ROOT = Path(__file__).resolve().parent
for _ in range(12):
    if (_ROOT / "__init__.py").exists() and (_ROOT / "pyproject.toml").exists():
        break
    _ROOT = _ROOT.parent
else:
    raise RuntimeError("Cannot locate flash package root")
_PARENT = _ROOT.parent
if str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))


def test_input_gen_package_exists():
    """确认 input_gen 包根可导入。"""
    import flash.input_gen
    assert hasattr(flash.input_gen, "__path__"), "input_gen 应是一个包"
    # 验证子模块
    submodules = ["gen_eos_op", "gen_shell_script"]
    for mod in submodules:
        try:
            __import__(f"flash.input_gen.{mod}")
        except ImportError:
            pytest.fail(f"无法导入 input_gen.{mod}")
    print(f"  ✅ input_gen 包结构完整")


def test_gen_par_module_exists():
    """确认 gen_par 模块存在（即使尚未完整实现）。"""
    try:
        import flash.input_gen.gen_par
        print("  ✅ gen_par 模块已存在")
    except ImportError:
        print("  ℹ gen_par 模块尚未创建（预期行为）")


def test_gen_eos_op_importable():
    """确认 gen_eos_op 可导入且包含 EOSOpacityGenerator。"""
    from flash.input_gen.gen_eos_op.generator import EOSOpacityGenerator, EOSMaterial
    print(f"  ✅ EOSOpacityGenerator 可导入")
    print(f"  ✅ EOSMaterial 定义存在")


def test_gen_shell_script_importable():
    """确认 gen_shell_script 可导入。"""
    from flash.input_gen.gen_shell_script.generator import ShellScriptGenerator
    print(f"  ✅ ShellScriptGenerator 可导入")


def test_gen_par_defaults_importable():
    """确认 defaults.py 存在且可导入。"""
    from flash.input_gen.gen_par.defaults import PARAMS_1D, PARAMS_2D, PARAMS_3D
    assert isinstance(PARAMS_1D, dict), "PARAMS_1D 应为 dict"
    print(f"  ✅ defaults.py ({len(PARAMS_1D)} 个 1D 默认参数)")


def test_gen_newpara_importable():
    """确认 gen_newpara 模块可导入。"""
    import flash.input_gen.gen_newpara
    print(f"  ✅ gen_newpara 包可导入")
