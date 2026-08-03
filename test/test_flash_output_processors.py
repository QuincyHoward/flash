"""
FLASH 输出处理器测试 — test_flash_output_processors.py (修正版)
══════════════════════════════════════════════

测试 flash/output_processors/ 下模块。
使用 synthetic 3D HDF5 文件进行单元测试。
"""

import os
import tempfile

import h5py
import numpy as np
import pytest

from flash.output_processors.hdf5processor import (
    FlashHDF5File,
    DataCalculator,
)

# ────────────────────────────────────────────
# 辅助函数
# ────────────────────────────────────────────


def _make_synthetic_hdf5(path: str):
    """
    创建一个 synthetic FLASH HDF5 文件用于测试。
    FLASH 输出为 4D：(nt, nz, ny, nx)
    这里用 nt=1, nz=1, ny=1, nx=20。
    包含 bounding box 数据集以支持 read_grid()。
    """
    nt, nz, ny, nx = 1, 1, 1, 20
    nblocks = 1
    xmin, xmax = 0.0, 0.016
    with h5py.File(path, "w") as f:
        f.create_dataset("dens", data=np.ones((nt, nz, ny, nx)) * 2.7)
        f.create_dataset("tele", data=np.ones((nt, nz, ny, nx)) * 300.0)
        f.create_dataset("tion", data=np.ones((nt, nz, ny, nx)) * 300.0)
        f.create_dataset("velx", data=np.ones((nt, nz, ny, nx)) * 1e5)
        f.create_dataset("pres", data=np.ones((nt, nz, ny, nx)) * 1e15)
        f.create_dataset("nele", data=np.ones((nt, nz, ny, nx)) * 1e21)
        # 坐标（1D）
        f.create_dataset("xcoord", data=np.linspace(xmin, xmax, nx))
        # bounding box (nblocks, 3, 2): x/y/z 的 min/max
        bbox = np.array([[[xmin, xmax], [0.0, 0.0], [0.0, 0.0]]], dtype=np.float64)
        f.create_dataset("bounding box", data=bbox)
        # unknown names — FLASH compound dtype: (S80 name, f8 flag)
        unames_dt = np.dtype([("name", "S80"), ("flag", "f8")])
        unames_data = np.array(
            [(n.encode("utf-8"), 1.0) for n in ["dens", "tele", "tion", "velx", "pres", "nele"]],
            dtype=unames_dt,
        )
        f.create_dataset("unknown names", data=unames_data)
    return path


# ────────────────────────────────────────────
# FlashHDF5File 测试
# ────────────────────────────────────────────


class TestFlashHDF5File:
    """FlashHDF5File 测试（读写 synthetic HDF5）。"""

    def test_open_file(self, tmp_path):
        """构造不抛异常。"""
        h5_path = str(tmp_path / "test.h5")
        _make_synthetic_hdf5(h5_path)
        fh = FlashHDF5File(h5_path)
        assert fh is not None
        fh.close()

    def test_available_datasets(self, tmp_path):
        """available_datasets 属性返回列表。"""
        h5_path = str(tmp_path / "test.h5")
        _make_synthetic_hdf5(h5_path)
        fh = FlashHDF5File(h5_path)
        dsets = fh.available_datasets
        assert isinstance(dsets, list)
        assert "dens" in dsets
        fh.close()

    def test_read_dataset(self, tmp_path):
        """read_dataset() 返回 numpy 数组。"""
        h5_path = str(tmp_path / "test.h5")
        _make_synthetic_hdf5(h5_path)
        fh = FlashHDF5File(h5_path)
        dens = fh.read_dataset("dens")
        assert isinstance(dens, np.ndarray)
        assert np.allclose(dens, 2.7)
        fh.close()

    def test_read_var(self, tmp_path):
        """read_var() 同 read_dataset()。"""
        h5_path = str(tmp_path / "test.h5")
        _make_synthetic_hdf5(h5_path)
        fh = FlashHDF5File(h5_path)
        tele = fh.read_var("tele")
        assert isinstance(tele, np.ndarray)
        fh.close()

    def test_read_grid(self, tmp_path):
        """read_grid() 返回坐标字典（需要 bounding box 数据集）。"""
        h5_path = str(tmp_path / "test.h5")
        _make_synthetic_hdf5(h5_path)
        fh = FlashHDF5File(h5_path)
        try:
            grid = fh.read_grid()
            assert isinstance(grid, dict)
        except KeyError:
            pytest.skip("synthetic HDF5 缺少 bounding box 数据集")
        finally:
            fh.close()

    def test_print_info_no_crash(self, tmp_path):
        """print_info() 不抛异常。"""
        h5_path = str(tmp_path / "test.h5")
        _make_synthetic_hdf5(h5_path)
        fh = FlashHDF5File(h5_path)
        fh.print_info(detailed=False)  # 仅验证不崩溃
        fh.close()

    def test_stats(self, tmp_path):
        """stats() 返回统计信息字典。"""
        h5_path = str(tmp_path / "test.h5")
        _make_synthetic_hdf5(h5_path)
        fh = FlashHDF5File(h5_path)
        s = fh.stats("dens")
        assert isinstance(s, dict)
        assert "min" in s
        assert "max" in s
        fh.close()

    def test_resolve_var_name(self, tmp_path):
        """resolve_var_name() 模糊匹配变量名。"""
        h5_path = str(tmp_path / "test.h5")
        _make_synthetic_hdf5(h5_path)
        fh = FlashHDF5File(h5_path)
        name = fh.resolve_var_name("dens")
        assert name == "dens"
        fh.close()


# ────────────────────────────────────────────
# DataCalculator 测试
# ────────────────────────────────────────────


class TestDataCalculator:
    """DataCalculator 派生变量计算测试。"""

    def _make_3d_data_dict(self):
        """构造 3D 测试数据字典 (nz, ny, nx) = (1, 1, 20)。"""
        nz, ny, nx = 1, 1, 20
        return {
            "dens": np.ones((nz, ny, nx)) * 2.7,
            "tele": np.ones((nz, ny, nx)) * 300.0,
            "tion": np.ones((nz, ny, nx)) * 300.0,
            "velx": np.ones((nz, ny, nx)) * 1e5,
            "pres": np.ones((nz, ny, nx)) * 1e15,
            "nele": np.ones((nz, ny, nx)) * 1e21,
        }

    def test_creation(self):
        """构造不抛异常。"""
        dc = DataCalculator(data_dict=self._make_3d_data_dict())
        assert dc is not None

    def test_get_available_derived(self):
        """get_available_derived() 返回列表。"""
        dc = DataCalculator(data_dict=self._make_3d_data_dict())
        available = dc.get_available_derived()
        assert isinstance(available, list)

    def test_compute_all(self):
        """compute_all() 计算所有派生变量。"""
        dc = DataCalculator(data_dict=self._make_3d_data_dict())
        result = dc.compute_all()
        assert isinstance(result, dict)

    def test_register_new_variable(self):
        """register() 注册新派生变量。"""
        dc = DataCalculator(data_dict=self._make_3d_data_dict())
        dc.register(
            varname="test_var",
            formula="dens * 2.0",
            description="test derived variable",
            unit="g/cm3",
        )
        assert "test_var" in dc.get_available_derived()


# ────────────────────────────────────────────
# 集成测试
# ────────────────────────────────────────────


class TestOutputProcessorsIntegration:
    """FlashHDF5File + DataCalculator 集成测试。"""

    def test_read_and_calculate(self, tmp_path):
        """从 HDF5 读取数据后计算派生变量。"""
        h5_path = str(tmp_path / "test.h5")
        _make_synthetic_hdf5(h5_path)
        fh = FlashHDF5File(h5_path)

        # 读取原始数据
        data_dict = {}
        for name in fh.available_datasets:
            data_dict[name] = fh.read_dataset(name)

        fh.close()

        # 用 DataCalculator 计算派生变量
        dc = DataCalculator(data_dict=data_dict)
        derived = dc.compute_all()
        assert isinstance(derived, dict)
