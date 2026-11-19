"""conftest.py — gen_fe_file 测试配置。

- 仓库根目录加入 sys.path (flash 独立包模式, 未安装亦可运行)
- 输出统一管理: ``test/out/<测试名>/``
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

import pytest

_TEST_DIR = Path(__file__).resolve().parent
# flash/ 包父目录 = 仓库根 (含 pyproject.toml); 比 gen_flychk_his/test 多一层
_ROOT = _TEST_DIR.parents[4]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

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


@pytest.fixture()
def history_table():
    """最小合法 HistoryTable (Ti, time/te/rho 列)。"""
    from flash.input_gen.gen_flychk_his.builder import HistoryTable
    return HistoryTable(
        columns=["time", "te", "rho"],
        rows=[[1e-12, 500.0, 1e-3], [2e-12, 800.0, 8e-4]],
        meta={"element": "Ti", "z": 22},
    )
