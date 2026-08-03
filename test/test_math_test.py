"""
test_math_test.py — 测试 flash.math_test 模块

测试目标：
  - LaserSlabCa1D 快速测试类
  - FlashMathTest 通用测试框架
  - HDF5保存功能
  - 确定性验证

测试数据位置：
  - 输入：flash/inputfiles/
  - 输出：flash/outputfiles/
"""

import pytest
import numpy as np
from pathlib import Path
import os


class TestLaserSlabCa1D:
    """测试 LaserSlabCa1D 类。"""

    def test_import(self):
        """测试模块导入。"""
        try:
            from flash.test.math_test import LaserSlabCa1D

            assert LaserSlabCa1D is not None
        except ImportError as e:
            pytest.fail(f"Failed to import LaserSlabCa1D: {e}")

    def test_init(self):
        """测试初始化（n_time_steps → n_time）。"""
        from flash.test.math_test import LaserSlabCa1D

        tester = LaserSlabCa1D(nx=50, n_time_steps=20)
        assert tester is not None
        assert tester.nx == 50
        assert tester.n_time == 20

    def test_run(self):
        """测试运行仿真。"""
        from flash.test.math_test import LaserSlabCa1D

        tester = LaserSlabCa1D(nx=50, n_time_steps=20)
        results = tester.run()

        assert results is not None
        assert isinstance(results, dict)
        assert "dens" in results
        assert "tele" in results
        assert "tion" in results
        assert "trad" in results
        assert "zbar" in results
        assert "nele" in results
        assert "shock_front" in results

    def test_output_shape(self):
        """测试输出数据形状。"""
        from flash.test.math_test import LaserSlabCa1D

        tester = LaserSlabCa1D(nx=50, n_time_steps=20)
        results = tester.run()

        # 验证形状：(n_time_steps, nx)
        assert results["dens"].shape == (20, 50)
        assert results["tele"].shape == (20, 50)

    def test_output_values(self):
        """测试输出数值合理性。"""
        from flash.test.math_test import LaserSlabCa1D

        tester = LaserSlabCa1D(nx=50, n_time_steps=20)
        results = tester.run()

        # 密度应该为正
        assert np.all(results["dens"] > 0)
        # 温度应该合理（几百到几万K）
        assert np.all(results["tele"] > 0)
        assert np.all(results["tele"] < 1e6)

    def test_save_hdf5(self, output_dir):
        """测试HDF5保存。"""
        from flash.test.math_test import LaserSlabCa1D

        tester = LaserSlabCa1D(nx=20, n_time_steps=10, output_path=str(output_dir / "test_laser_slab.h5"))
        tester.run()
        path = tester.save_hdf5()

        assert os.path.exists(path), f"HDF5 not saved: {path}"
        print(f"\n  [OK] HDF5 saved to: {path}")

        # 清理 (清理失败不影响测试结果, 如沙箱环境限制删除)
        try:
            os.remove(path)
        except OSError:
            pass

    def test_determinism(self):
        """测试确定性（相同参数 → 相同结果）。"""
        from flash.test.math_test import LaserSlabCa1D

        tester1 = LaserSlabCa1D(nx=50, n_time_steps=20)
        results1 = tester1.run()

        tester2 = LaserSlabCa1D(nx=50, n_time_steps=20)
        results2 = tester2.run()

        # 验证结果相同（确定性）
        np.testing.assert_allclose(results1["dens"], results2["dens"])
        np.testing.assert_allclose(results1["tele"], results2["tele"])


class TestFlashMathTest:
    """测试 FlashMathTest 通用框架。"""

    def test_import(self):
        """测试模块导入。"""
        try:
            from flash.test.math_test import FlashMathTest, MultimodalInput, SimDimension

            assert FlashMathTest is not None
        except ImportError as e:
            pytest.fail(f"Failed to import FlashMathTest: {e}")

    def test_1d_simulation(self):
        """测试1D仿真。"""
        from flash.test.math_test import FlashMathTest, MultimodalInput, SimDimension

        cfg = MultimodalInput(
            dimension=SimDimension.D1,
            nx=30,
            n_time_steps=10,
            domain_x_cm=0.05,
            t_max_s=5e-11,
        )
        tester = FlashMathTest(cfg)
        results = tester.run()

        assert "dens" in results
        assert results["dens"].shape == (10, 30)

    def test_2d_simulation(self):
        """测试2D仿真（空壳测试）。"""
        from flash.test.math_test import FlashMathTest, MultimodalInput, SimDimension

        cfg = MultimodalInput(
            dimension=SimDimension.D2,
            nx=10,
            ny=10,
            n_time_steps=5,
        )
        tester = FlashMathTest(cfg)
        results = tester.run()

        assert "dens" in results

    def test_invalid_dimension(self):
        """测试非法维度。"""
        from flash.test.math_test import FlashMathTest, MultimodalInput
        from enum import Enum

        # 创建一个非法的维度配置
        cfg = MultimodalInput(
            dimension=None,  # 非法
            nx=10,
            n_time_steps=5,
        )
        with pytest.raises(Exception):
            tester = FlashMathTest(cfg)
            tester.run()


class TestQuickTest:
    """测试便捷函数。"""

    def test_quick_test_1d(self, output_dir):
        """测试 quick_test_1d 便捷函数。"""
        from flash.test.math_test import quick_test_1d

        output_path = output_dir / "quick_test_1d.h5"
        summary = quick_test_1d(output_path=str(output_path))

        assert summary is not None
        assert isinstance(summary, dict)
        assert "peak_tele_eV" in summary
        assert "max_zbar" in summary
        assert summary["peak_tele_eV"] > 0

        # 验证HDF5文件已保存
        assert output_path.exists()
        print(f"\n  [OK] Quick test HDF5 saved to: {output_path}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
