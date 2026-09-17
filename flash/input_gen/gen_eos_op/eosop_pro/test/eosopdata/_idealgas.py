#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""合成单原子理想气体 cn4 表 —— 测试共享 stub（zbar 恒定、代数自洽）。

从 ``test_cn4_paths.py`` 的 ``_IdealGasStub`` 升格为 step 级共享
helper（r16 固化）：``test_cn4_paths``（声速 ln10 守卫）与
``test_cn4_thermo``（γ / 两项分解 / 占比 / γ_sound 锚）共用。

设计
----
- **代数自洽**：``P ∝ n·T``、``cv = 1.5·P/(ρT)``（即
  ``e = cv·T = 1.5·P/ρ``，单原子理想气体）、``e_ion = e_ele = e/2``、
  ``p_ion = p_ele = P/2``。
- **差分零截断误差**：lnP 对 lnn 线性、P 对 T 线性 ->
  ``np.gradient`` 中心/单边差分对线性函数精确 -> 所有解析锚
  （γ_sound = 5/3、热熵占比 = 0.4、γ = 5/3）到机器精度成立。
- **幅度不影响锚**：P 的绝对幅度在 γ_sound = c_s²ρ/P×1e-7 等
  无量纲比值中约掉，故无需真实物理常数。
- 仅实现各计算函数的依赖面（``field`` / ``density`` /
  ``temperature`` / ``avgatw`` / ``ndens`` / ``ntemp``），鸭子类型。
"""

from __future__ import annotations

import numpy as np

from eosop_pro.plotting.units import NA


class IdealGasStub:
    """合成单原子理想气体表（默认 <A>=12.011、9×5 网格）。

    Attributes:
        density / temperature: 1D 轴（list，与 CN4Table 一致）。
        avgatw: 平均原子量。
        ndens / ntemp: 网格尺寸。
        P / rho / cv / e: 内部 2D 场（(ndens, ntemp)）。
    """

    def __init__(self, ndens: int = 9, ntemp: int = 5,
                 avgatw: float = 12.011):
        self.density = np.logspace(20.0, 24.0, ndens).tolist()
        self.temperature = np.linspace(100.0, 1000.0, ntemp).tolist()
        self.avgatw = avgatw
        self.ndens, self.ntemp = ndens, ntemp
        n = np.asarray(self.density, dtype=float)[:, None]
        T = np.asarray(self.temperature, dtype=float)[None, :]
        self.rho = n * avgatw / NA                         # g/cm^3
        self.P = n * T                                     # ∝ n·T（幅度任意）
        self.cv = 1.5 * self.P / (self.rho * T)            # e = cv·T = 1.5 P/ρ
        self.e = self.cv * T                               # = 1.5 P/ρ

    # field 的 flat 约定与 CN4Table 一致：ravel 后 reshape(ndens, ntemp)
    _HALF_FIELDS = {
        "p_ion": ("P", 0.5), "p_ele": ("P", 0.5),
        "cv_ion": ("cv", 0.5), "cv_ele": ("cv", 0.5),
        "e_ion": ("e", 0.5), "e_ele": ("e", 0.5),
    }

    def field(self, name: str):
        if name not in self._HALF_FIELDS:
            raise KeyError(f"IdealGasStub 未实现场 {name!r}")
        attr, half = self._HALF_FIELDS[name]
        return (half * getattr(self, attr)).ravel().tolist()
