# -*- coding: utf-8 -*-
"""time_control 纯函数行为测试（common/time_control，自 scripts 迁入）。
"""
from __future__ import annotations

from flash.scenarios.common.time_control import fit_time_controls, is_short_tmax


class TestFitTimeControls:
    def test_normal_tmax_untouched(self):
        """正式仿真（tmax 远大于 dtmax）→ 全部原样。"""
        assert fit_time_controls(1.6e-9, 1e-15, 1e-16, 1e-12) == (1e-15, 1e-16, 1e-12)

    def test_short_tmax_shrinks(self):
        """极短验证 1e-13：dtmax/dtinit 收缩到与 tmax 相容。"""
        dtinit, dtmin, dtmax = fit_time_controls(1e-13, 1e-15, 1e-16, 1e-12)
        assert dtmax <= 1e-13 * 1.05
        assert dtinit <= 1e-13 * 0.1
        assert dtmin <= dtinit <= dtmax

    def test_ordering_invariant(self):
        """任意输入下保持 dtmin ≤ dtinit ≤ dtmax。"""
        for tmax in (1e-13, 1e-11, 2e-10):
            dtinit, dtmin, dtmax = fit_time_controls(tmax, 5e-12, 1e-16, 1e-9)
            assert dtmin <= dtinit <= dtmax

    def test_nonpositive_tmax_passthrough(self):
        assert fit_time_controls(0.0, 1e-15, 1e-16, 1e-12) == (1e-15, 1e-16, 1e-12)
        assert fit_time_controls(-1.0, 1e-15, 1e-16, 1e-12) == (1e-15, 1e-16, 1e-12)


class TestIsShortTmax:
    def test_true_for_3_orders_below(self):
        assert is_short_tmax(1e-13, 2e-10) is True

    def test_false_for_normal(self):
        assert is_short_tmax(1.6e-9, 2e-10) is False

    def test_false_for_bad_input(self):
        assert is_short_tmax(None, 2e-10) is False
        assert is_short_tmax(1e-13, 0) is False
