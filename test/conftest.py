"""conftest.py — flash 模块测试的共享固件（fixtures）

flash 独立包模式：flash/ 是最顶层包目录。
"""

import sys
import pytest
import numpy as np
from pathlib import Path

# ── 路径设置：将 flash/ 的父目录加入 sys.path ─────
# 使包在未安装（源码树直接运行 pytest）时也能以 `flash.` 前缀导入。

# Bootstrap: find flash project root by searching upward for marker
_ROOT = Path(__file__).resolve().parent
for _ in range(12):
    if (_ROOT / "pyproject.toml").exists():
        break
    _ROOT = _ROOT.parent
else:
    raise RuntimeError("Cannot locate flash package root")
_PARENT = _ROOT
if str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))


@pytest.fixture(scope="module")
def require_declared_dir():
    """声明目录存在性检查器：区分「受版本控制的资产」与「私有运行数据」。

    ★ 2026-11-15 三环境一致性：场景声明的 ``input_rel_dir`` / legacy 锚点
      指向的目录有一部分被 ``.gitignore`` 排除（SNB ``variants``、各
      ``flash_input/`` 里的 cn4/chk 等，合计可达数十 GB），只存在于开发机。
      超算等部署端重建仓库后不带这些私有数据是**正常**的，旧断言一律红灯
      导致全局测试无法通过；而把这些资产逐个上传既不可持续也不合规。

      现在：目录存在 → 通过；缺失但 ``git ls-files`` 显示该路径下有受版本
      控制的文件 → 仍红灯（代码树不完整）；缺失且索引为空 → WARN 放行
      （声明路径本身仍由 discovery/相对形式断言保证，护栏不降级）。
    """
    import subprocess
    import warnings

    def _check(root, rel: str, label: str = "") -> None:
        p = Path(root) / rel
        if p.is_dir():
            return
        try:
            r = subprocess.run(["git", "ls-files", "--", rel],
                               cwd=str(root), capture_output=True,
                               text=True, timeout=60)
            tracked = [x for x in (r.stdout or "").splitlines() if x.strip()]
        except (OSError, subprocess.SubprocessError):
            tracked = []  # 无 git 的环境无法判定，按私有资产处理
        if tracked:
            raise AssertionError(
                f"{label} 受版本控制的目录缺失: {rel}"
                f"（索引含 {len(tracked)} 个文件，如 {tracked[0]}）")
        warnings.warn(
            f"{label} 私有资产未随仓库分发（.gitignore 排除），部署端可不提供: {rel}",
            UserWarning, stacklevel=2)

    return _check


@pytest.fixture(scope="module")
def flash_simulator():
    """创建FlashSimulator mock实例。"""
    try:
        from flash import FlashSimulator

        simulator = FlashSimulator(mock=True, verbose=False)
        yield simulator
    except ImportError:
        pytest.skip("FlashSimulator not available")


@pytest.fixture(scope="function")
def sample_request():
    """创建示例SimulationRequest（使用 vendored _core 模式）。"""
    try:
        from flash._core.schema import SimulationRequest, SimulatorType

        request = SimulationRequest(
            simulator_type=SimulatorType.FLASH,
            params={
                "temperature": 5000.0,
                "density": 1e-2,
                "magnetic_field": 1.0,
            },
        )
        return request
    except ImportError as e:
        pytest.skip(f"flash._core.schema not available: {e}")


@pytest.fixture(scope="function")
def temp_par_file(tmp_path):
    """创建临时.par参数文件。"""
    par_content = """
# FLASH parameter file for testing
geometry = 1
ndim = 1
nblockx = 4
nblocky = 1
nblockz = 1
"""
    par_file = tmp_path / "test_flash.par"
    par_file.write_text(par_content)
    return par_file


@pytest.fixture(scope="session")
def test_data_dir():
    """测试数据目录。"""
    data_dir = Path(__file__).parent / "inputfiles"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


@pytest.fixture(scope="session")
def output_dir():
    """测试输出目录。"""
    out_dir = Path(__file__).parent / "outputfiles"
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir
