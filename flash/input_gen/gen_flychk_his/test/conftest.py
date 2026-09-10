"""conftest.py — gen_flychk_his 测试配置。

- 仓库根目录加入 sys.path (flash 独立包模式, 未安装亦可运行)
- 会话级测试数据生成 (`make_test_data.ensure_test_data`)
- 输出统一管理: ``test/out/<测试名>/``
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

import pytest

_TEST_DIR = Path(__file__).resolve().parent
# flash/ 包父目录 = 仓库根 (含 pyproject.toml)
_ROOT = _TEST_DIR.parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from flash.input_gen.gen_flychk_his.test import make_test_data  # noqa: E402

OUT_DIR = _TEST_DIR / "out"


def _reset_dir(path: Path) -> Path:
    """清空并重建目录 (对 Windows 文件占用/回收站拦截保持健壮)。"""
    path = Path(path)
    if path.exists():
        try:
            shutil.rmtree(path)
        except OSError:
            for f in sorted(path.rglob("*"), reverse=True):
                try:
                    os.unlink(f) if f.is_file() else os.rmdir(f)
                except OSError:
                    pass
            try:
                os.rmdir(path)
            except OSError:
                pass
    path.mkdir(parents=True, exist_ok=True)
    return path


@pytest.fixture(scope="session", autouse=True)
def _managed_out_dir():
    """每次会话清空 out/ 并重建。"""
    _reset_dir(OUT_DIR)
    yield OUT_DIR


@pytest.fixture()
def out_dir(request):
    d = OUT_DIR / request.node.name
    d.mkdir(parents=True, exist_ok=True)
    return d


@pytest.fixture(scope="session")
def test_data():
    """生成 (幂等) 并返回全部测试数据路径。"""
    return make_test_data.ensure_test_data(verbose=True)


@pytest.fixture()
def h5_series(test_data):
    """由合成 FLASH HDF5 文件加载的序列。"""
    from flash.input_gen.gen_flychk_his import load_series
    from flash.input_gen.gen_flychk_his.config import FlychkHisConfig
    return load_series(str(test_data["flash_hdf5_dir"]),
                       config=FlychkHisConfig(element="Ti"), verbose=False)


@pytest.fixture()
def synth_series():
    """解析模型合成序列 (不落盘)。"""
    from flash.input_gen.gen_flychk_his import synthetic_ch_ti_slab
    return synthetic_ch_ti_slab(n_time=6, nx=160)


@pytest.fixture()
def default_config():
    from flash.input_gen.gen_flychk_his import FlychkHisConfig
    return FlychkHisConfig(element="Ti", agg="mass", n_time_max=6)
