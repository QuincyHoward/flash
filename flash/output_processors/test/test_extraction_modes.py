#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模式字典与双提取方案测试 — test_extraction_modes.py
========================================================

验证 output_processors 的 AMR 数据提取模式机制:
  - 模式字典 EXTRACTION_MODES 注册了 h5py / yt 两种方案
  - 默认模式为 h5py (超算环境优先)
  - 一行代码切换默认模式 (CURRENT_EXTRACTION_MODE / set_extraction_mode)
  - FlashHDF5File.extract_var(mode=...) 按模式调度
  - h5py 与 yt 两种模式提取结果逐点一致 (1D/2D/3D)

运行方式 (在项目根目录):
  pytest flash/output_processors/test/test_extraction_modes.py -v
"""

import os
import sys
from pathlib import Path

import numpy as np
import pytest

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

from flash.output_processors import extraction_modes as em
from flash.output_processors.hdf5processor import FlashHDF5File
from flash.output_processors.extraction_modes import (
    EXTRACTION_MODES,
    CURRENT_EXTRACTION_MODE,
    get_extraction_mode,
    set_extraction_mode,
    resolve_extraction_mode,
    available_extraction_modes,
)

# ── 测试数据路径 ────────────────────────────────────────────────
_INPUT_BASE = Path(__file__).resolve().parent / ".." / "inputfiles"

TEST_FILES = {
    "1d": _INPUT_BASE / "hdf5files_1d" / "lasslab_hdf5_chk_0001",
    "2d": _INPUT_BASE / "hdf5files_2d" / "lasslab_hdf5_plt_cnt_0001",
    "3d": _INPUT_BASE / "hdf5files_3d" / "lasslab_hdf5_plt_cnt_0001",
}


def _sorted(*arrays):
    """按 (c1, c2, c3) 字典序排序 (最后一个是数据, 其余是坐标)。"""
    coords = arrays[:-1]
    idx = np.lexsort(coords[::-1])
    return tuple(np.asarray(a)[idx] for a in arrays)


# ═══════════════════════════════════════════════════════════════
#  模式字典本身
# ═══════════════════════════════════════════════════════════════

class TestExtractionModesRegistry:
    """模式字典与切换 API 测试。"""

    def test_modes_dict_has_both_schemes(self):
        assert "h5py" in EXTRACTION_MODES
        assert "yt" in EXTRACTION_MODES
        assert "h5py" in available_extraction_modes()
        assert "yt" in available_extraction_modes()

    def test_h5py_is_preferred_default(self):
        assert CURRENT_EXTRACTION_MODE == "h5py"
        assert get_extraction_mode() == "h5py"

    def test_resolve_explicit_overrides_default(self):
        assert resolve_extraction_mode("yt") == "yt"
        assert resolve_extraction_mode("h5py") == "h5py"
        # None 应解析为当前生效的默认模式 (env 覆盖优先于代码配置)
        effective = os.environ.get("FLASH_EXTRACTION_MODE") or CURRENT_EXTRACTION_MODE
        assert resolve_extraction_mode(None) == effective

    def test_set_extraction_mode_switches(self):
        prev = get_extraction_mode()
        try:
            set_extraction_mode("yt")
            assert get_extraction_mode() == "yt"
            set_extraction_mode("h5py")
            assert get_extraction_mode() == "h5py"
        finally:
            set_extraction_mode(prev)

    def test_set_unknown_mode_raises(self):
        with pytest.raises(ValueError):
            set_extraction_mode("unknown_mode")

    def test_modes_metadata(self):
        assert EXTRACTION_MODES["h5py"]["requires"] == ["h5py"]
        assert EXTRACTION_MODES["yt"]["requires"] == ["yt"]


# ═══════════════════════════════════════════════════════════════
#  双提取方案一致性
# ═══════════════════════════════════════════════════════════════

class TestDualExtractionModes:
    """h5py 模式与 yt 模式提取结果逐点一致性测试。"""

    @pytest.fixture(autouse=True)
    def _skip_if_no_data(self):
        for path in TEST_FILES.values():
            if not path.exists():
                pytest.skip(f"测试数据缺失: {path} (运行 gen_test_data.py 生成)")

    def _compare(self, key, var="dens"):
        path = TEST_FILES[key]
        ff = FlashHDF5File(str(path))
        try:
            rh = ff.extract_var(var, mode="h5py")
            ry = ff.extract_var(var, mode="yt")
        finally:
            ff.close()

        ndim = len(rh) - 1
        assert len(ry) == len(rh), f"{key}: yt 返回维度不一致"
        assert len(rh[-1]) == len(ry[-1]), f"{key}: 点数不一致 h5py={len(rh[-1])} yt={len(ry[-1])}"

        rh_s = _sorted(*rh)
        ry_s = _sorted(*ry)

        # 坐标逐点一致 (机器精度)
        for ci in range(ndim):
            assert np.allclose(rh_s[ci], ry_s[ci], rtol=1e-8, atol=1e-10), \
                f"{key}: 坐标轴 {ci} 不一致"
        # 数值逐点一致
        assert np.allclose(rh_s[-1], ry_s[-1], rtol=1e-8, atol=1e-14), \
            f"{key}: 物理量数值不一致"

    def test_1d_h5py_matches_yt(self):
        self._compare("1d")

    def test_2d_h5py_matches_yt(self):
        self._compare("2d")

    def test_3d_h5py_matches_yt(self):
        self._compare("3d")

    def test_other_var_1d(self):
        self._compare("1d", var="tele")


# ═══════════════════════════════════════════════════════════════
#  extract_var 调度器
# ═══════════════════════════════════════════════════════════════

class TestExtractVarDispatcher:
    """FlashHDF5File.extract_var() 按模式调度测试。"""

    @pytest.fixture(autouse=True)
    def _skip_if_no_data(self):
        if not TEST_FILES["1d"].exists():
            pytest.skip(f"测试数据缺失: {TEST_FILES['1d']}")

    def _ff(self):
        return FlashHDF5File(str(TEST_FILES["1d"]))

    def test_explicit_h5py_equals_yt_style(self):
        ff = self._ff()
        try:
            r1 = ff.extract_var("dens", mode="h5py")
            r2 = ff.extract_var_yt_style("dens")
            assert np.allclose(_sorted(*r1)[0], _sorted(*r2)[0])
            assert np.allclose(_sorted(*r1)[-1], _sorted(*r2)[-1])
        finally:
            ff.close()

    def test_explicit_yt_uses_yt_scheme(self):
        ff = self._ff()
        try:
            x, d = ff.extract_var("dens", mode="yt")
            assert x.shape == d.shape
            assert len(x) == 32  # 1D nx=32
        finally:
            ff.close()

    def test_default_mode_switch_one_line(self):
        """一行切换: 修改 CURRENT_EXTRACTION_MODE 后 extract_var() 跟随。"""
        prev = get_extraction_mode()
        env_backup = os.environ.pop("FLASH_EXTRACTION_MODE", None)
        try:
            em.CURRENT_EXTRACTION_MODE = "yt"     # ← 一行切换默认模式
            assert get_extraction_mode() == "yt"
            r_yt = self._ff().extract_var("dens")   # mode=None -> 使用 yt
            em.CURRENT_EXTRACTION_MODE = "h5py"
            assert get_extraction_mode() == "h5py"
            r_h5 = self._ff().extract_var("dens")   # mode=None -> 使用 h5py
            assert np.allclose(_sorted(*r_yt)[0], _sorted(*r_h5)[0])
            assert np.allclose(_sorted(*r_yt)[-1], _sorted(*r_h5)[-1])
        finally:
            em.CURRENT_EXTRACTION_MODE = prev
            if env_backup is not None:
                os.environ["FLASH_EXTRACTION_MODE"] = env_backup

    def test_unknown_mode_raises(self):
        ff = self._ff()
        try:
            with pytest.raises(ValueError):
                ff.extract_var("dens", mode="unknown_mode")
        finally:
            ff.close()


# ═══════════════════════════════════════════════════════════════
#  扁平化容器加载 + 绘图 (模式字典接入 loader/plotter)
# ═══════════════════════════════════════════════════════════════

class TestFlatLoaderAndPlotter:
    """FlashDataLoader.load(extraction_mode=...) 扁平化容器 + plotter 直接绘图。"""

    @pytest.fixture(autouse=True)
    def _skip_if_no_data(self):
        if not TEST_FILES["1d"].exists():
            pytest.skip(f"测试数据缺失: {TEST_FILES['1d']}")

    def test_load_extracted_yields_flat_container(self):
        from flash.output_processors.loader import FlashDataLoader
        c = FlashDataLoader(str(TEST_FILES["1d"])).load(extraction_mode="yt")
        assert c.flat is True
        assert c.ndim == 1
        assert c.x is not None
        assert "dens" in c.data
        assert c.data["dens"].ndim == 1
        assert len(c.data["dens"]) == len(c.x)

    def test_load_extracted_matches_extract_var(self):
        from flash.output_processors.loader import FlashDataLoader
        c = FlashDataLoader(str(TEST_FILES["1d"])).load(extraction_mode="h5py")
        ff = FlashHDF5File(str(TEST_FILES["1d"]))
        try:
            x, d = ff.extract_var("dens", mode="h5py")
        finally:
            ff.close()
        assert np.allclose(np.sort(c.x), np.sort(x))
        assert np.allclose(c.data["dens"], d)

    def test_flat_plotter_1d_renders(self, tmp_path):
        from flash.output_processors.loader import FlashDataLoader
        from flash.output_processors.plotter import FlashPlotter
        c = FlashDataLoader(str(TEST_FILES["1d"])).load(extraction_mode="yt")
        out = str(tmp_path / "flat_dens.png")
        FlashPlotter(c).plot("dens", save_path=out)
        assert Path(out).exists()
        assert Path(out).stat().st_size > 0

    def test_flat_plotter_2d_renders(self, tmp_path):
        if not TEST_FILES["2d"].exists():
            pytest.skip(f"测试数据缺失: {TEST_FILES['2d']}")
        from flash.output_processors.loader import FlashDataLoader
        from flash.output_processors.plotter import FlashPlotter
        c = FlashDataLoader(str(TEST_FILES["2d"])).load(extraction_mode="yt")
        out = str(tmp_path / "flat_2d.png")
        FlashPlotter(c).plot("dens", save_path=out)
        assert Path(out).exists()
        assert Path(out).stat().st_size > 0

    def test_default_load_unchanged(self):
        """未传 extraction_mode 时保持原 block-wise 行为 (向后兼容)。"""
        from flash.output_processors.loader import FlashDataLoader
        c = FlashDataLoader(str(TEST_FILES["1d"])).load()
        assert c.flat is False
        assert "dens" in c.data
        assert c.data["dens"].ndim == 2  # (nblocks, nx)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))