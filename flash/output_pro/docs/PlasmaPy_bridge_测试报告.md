# PlasmaPy Bridge（方案 A）测试报告

- 日期: 2026-10-30
- 模块: `flash/output_pro/plasmapy_bridge.py`（方案 A 适配层，零侵入）
- 测试: `flash/output_pro/test/test_plasmapy_bridge.py`（12 项）
- 结论: **✅ 全部通过 — 全套件 52 passed（40 原有 + 12 新增），16.61 s**

## 1. 环境信息

| 项 | 值 |
|---|---|
| PlasmaPy | **2026.2.0**（editable，source of truth = `flash/output_pro/PlasmaPy/src/PlasmaPy`，git tag v2026.2.0 @ fca3bc8） |
| 安装器 | `flash/output_pro/PlasmaPy/install_editable.py`（版本闸门 py≥3.12 + 子进程冒烟验证） |
| 解释器 ① | managed Python **3.14.6**（`C:/Users/Administrator/AppData/Local/Python/bin/python.exe`）— 安装 + 冒烟 ✅ |
| 解释器 ② | 项目 **`.venv-win` Python 3.13.9** — 安装 + 冒烟 ✅ |
| 关键依赖 | astropy 8.0.2 / pyerfa 2.0.1.5 / xarray 2026.9.0（pip 联网自动拉取） |
| 冒烟断言 | `plasmapy.__file__` 落在 output_pro 克隆内；`thermal_speed(1 keV,"e-") = 1.8755e7 m/s`（理论 ≈1.876e7） |
| HPC NC-E | ❌ 不安装（py3.10.8 < 3.12 闸门 + 离线）；bridge 降级路径有测试覆盖 |
| WSL | 条件支持（venv 需 py≥3.12；命令模板见使用指南 §1） |

## 2. 新变量用例结果（12/12 PASSED）

| # | 用例 | 验证内容 | 结果 |
|---|---|---|---|
| 1 | `test_to_quantity_units_real_file` | CGS→SI：tele K 直通；dens 2.7 g/cm³→2700 kg/m³；nele 8.1299e23 cm⁻³→8.1299e29 m⁻³ | ✅ |
| 2 | `test_to_quantity_unknown_unit_raises` | 未注册单位抛 `ValueError`（含注册提示） | ✅ |
| 3 | `test_coulomb_log_physical_range` | 物理工况 lnΛ∈(1,30)；密度↑100× → lnΛ↓ | ✅ |
| 4 | `test_debye_length_vs_analytic` | λ_D vs 解析式 √(ε₀k_BT_e/n_e e²)，rtol<1e-4 | ✅（实测 6.9009e-9 m @ 1e7 K/1e21 cm⁻³） |
| 5 | `test_critical_density_benchmark` | n_c(0.351 μm) vs 项目基准 9.05×10²¹ cm⁻³，容差 0.1% | ✅（**9.0491e21 cm⁻³**，偏差 0.01%） |
| 6 | `test_quantum_theta_vs_handwritten` | PlasmaPy `quantum_theta` vs 手写 `electron_degeneracy_parameter`（Θ_e），rtol<1e-6 | ✅ |
| 7 | `test_coupling_parameter_vs_handwritten` | PlasmaPy `coupling_parameter` vs 手写 `ion_coupling_parameter`（Γ_i），rtol<1e-3 | ✅ |
| 8 | `test_mean_free_path_and_knudsen` | λ_mfp>0 有限；K_n=λ_mfp/L_Te 与手算一致 rtol<1e-10 | ✅ |
| 9 | `test_spitzer_kappa_t25_scaling` | κ_e^SH ∝ T^{5/2}/lnΛ：同密度双温态比值 vs 期望（含 GMS-6 lnΛ 修正），容差 2% | ✅（**226.62 vs 226.61**，偏差 <0.01%） |
| 10 | `test_saha_zbar_finite_physical_state` | Z̄_Saha 在电离区（1e5 K/1e20 cm⁻³）有限且 >0.1 | ✅ |
| 11 | `test_critical_surface_locates_interface` | 线性密度剖面 1e22→1e18 cm⁻³ 中 x_c 定位误差 <1 网格距 | ✅ |
| 12 | `test_graceful_degradation` | `HAS_PLASMAPY=False` 时物理量函数抛 `RuntimeError`（含 install_editable 安装指引） | ✅ |

κ_e^SH 参考值（Braginskii 平行, Z̄=3, lnΛ=GMS-6 显式传入）:
- 1e6 K / 1e20 cm⁻³ → **5.5611e4 W/(m·K)**
- 1e7 K / 1e20 cm⁻³ → **1.2603e7 W/(m·K)**（比值 226.6 = T^2.5×lnΛ 修正，理论自洽）

## 3. 实测发现的 PlasmaPy 2026.2.0 陷阱（已写入 bridge 文档字符串）

| # | 陷阱 | 处置 |
|---|---|---|
| 1 | 离子记法 `Ti+3` 无效 → `InvalidParticleError` | PlasmaPy 记法为 `"Ti 3+"`；bridge `DEFAULT_ION` 已更正 |
| 2 | `ClassicalTransport` 不接受数组（内部 lnΛ 标量校验） | bridge 逐点循环实现；网格 >1e4 建议取代表点 |
| 3 | `model="Spitzer"` 仅允许 Z∈{1,2,4,16,∞}（SH'53 表 III），Z̄=3 抛 PhysicsError | bridge 默认 `model="Braginskii"`（支持任意 Z̄）；非物理工况捕获后置 NaN |
| 4 | 多电荷离子（"Ti 3+"）传给 `ClassicalTransport` 触发内部 Z 推断缺陷（"3.0 is not an allowed Z value"，连不传 Z 也复现） | bridge 约定输运函数 `ion="p+"` + 显式 `Z=z_mean` |
| 5 | `coulomb_log_method="GMS-6"` 与 Particle 型 z_mean 在 `impact_parameter` 内 `np.isnan` 崩溃 | bridge 先以 GMS-6 自算 lnΛ，再经 `coulomb_log_ei` 显式传入 — 数值与 `coulomb_log_profile` 严格一致 |
| 6 | 合成测试数据（Te=100–500 K, ne=8.13e23 cm⁻³）处强耦合非物理区 → κ_e/Z̄_Saha 全 NaN 属预期 | 物理量交叉验证改用受控物理工况的 duck-type 容器 |

## 4. 运行方式与备注

```bash
cd flash/flash/output_pro
python -m pytest test/ -v -s     # 全套件 52 项; -s 规避沙箱 WinError 6 (conftest 子进程句柄)
python -m pytest test/test_plasmapy_bridge.py -v -s   # 仅 bridge 12 项
```

- 测试数据由 conftest 收集期自动生成、全通过后自动清理（7 个 HDF5）。
- `RelativityWarning`（v≈5.8% c）为 GMS-6 内部热速度提示，1e7 K 工况正常现象。
- 存量问题（与本改造无关）：`deploy/wheel_leak_audit.py` 对 SandwichTxN `.cn4` 大文件（3×568 KB）仍 FAIL，属历史债。

## 5. 打包护栏验证

| 检查 | 结果 |
|---|---|
| wheel 体积 | 9.3 MB → **5.1 MB**（排除新旧两处 PlasmaPy 克隆） |
| wheel/sdist PlasmaPy 泄漏 | **0 文件**（改造前旧目录泄漏 509/254 文件） |
| `.gitignore` | `flash/flash/output_pro/PlasmaPy/` 已加（末尾锚定），`git check-ignore -v` 实测生效 |
