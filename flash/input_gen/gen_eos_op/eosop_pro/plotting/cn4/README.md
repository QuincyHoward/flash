> 最后核对：2026-11-14 · commit ba2981e（其后含功能树重组，代码为准）

# plotting/cn4/ —— IONMIX cn4 表格专题绘图与热力学派生

面向 cn4 静态 `(T, n_ion)` 表格的五个模块：二维彩图与一维曲线（`cn4_plots`）、
热力学路径（`cn4_paths`）、时间演化（`cn4_timeseries`）、关系拟合（`cn4_fit`）、
γ/声速派生量（`cn4_thermo`）。上层 `pipeline/cli.py` 的 `cn4-plot` / `cn4-plot-all`
/ `cn4-paths` / `cn4-fit` 子命令是编排入口；本层依赖 `parsers/cn4_io.load_cn4`
（CN4Table）、`../style/units`（单位换算）、`../style/labels`（字典标签）、
`core/config`（PLOT_* 常量）。物理量组合：`P = p_ion + p_ele`（J/cm³，块 5+6）、
`e = e_ion + e_ele`（J/g，块 9+10）、`rho = n_ion*<A>/N_A`、`T`（eV，块 1）。

**单位纪律**：内部计算一律 cn4 原始单位（J/cm³、J/g、cm⁻³、eV），仅在出图/
返回值处经 `style/units` 换算到显示单位（Mbar、erg/g、um/ns），不新增硬编码常数。

## 模块

### cn4_plots.py
二维彩图与一维变化曲线。轴可取 `T/tele/nion/nele/rho` 任意组合（`nele` 为 2D
派生量，作轴时散点插值 + 凸包）；`plot_opacity_group_figure` 出单能群 2×2 大图
（Rosseland/Planck 吸收/Planck 发射/透射率）；`plot_cn4_directory` 是整目录批量
入口。颜色对数、轴对数自动判定。

关键 API：
- `plot_quantity_heatmap(...)` —— 二维彩图（x/y 轴 + 任意物理量/群不透明度）
- `plot_opacity_group_figure(tbl, ig, ...)` —— 单能群 2×2 大图
- `plot_all_opacity_figures(tbl, ...)` / `plot_all_quantities_dual_axes(tbl, ...)`
  —— 批量：全部群大图 / 双 y 轴量图
- `plot_vs_temperature(tbl, ...)` / `plot_vs_density(tbl, ...)` —— 一维多曲线
- `plot_cn4_directory(cn4_dir, ...)` —— 目录批量入口
- `axis_label(name) -> str` / `display_scale(quantity) -> float` ——
  轴标签与显示缩放
- `AXES` / `DUAL_Y_AXES` / `Y_AXIS_SUFFIX` / `SUPPORTED_QUANTITIES` —— 轴与
  物理量受控表

### cn4_paths.py
从 cn4 表格出发研究四类热力学路径：等温线（T 固定输出 P(n_ion)、e(n_ion)）、
等压线（P=const 曲线提取）、等熵线（第一定律数值积分熵场后提取 s=const）、
冲击雨贡纽（给定参考态求 `(e-e0) = (P+P0)(1/rho0 - 1/rho)/2` 状态点集 + Us-Up
关系）。另含声速唯一实现 `sound_speed`（2026-09-17 已修 ln10 坐标 bug）与
P-V 图。

关键 API：
- `trace_isotherm(tbl, T_idx=10, T=None, ...)` / `trace_isobar(tbl, P, ...)`
- `compute_entropy(tbl, ref_rho_idx=0, ...) -> np.ndarray` / `trace_isentrope(tbl, s, s0_idx=(5,10), ...)`
- `trace_hugoniot(tbl, ref_idx=(0,0), ...)` —— 雨贡纽状态点集
- `plot_usup_vs_pressure(Us, Up, P, ...)` —— Us-Up 图
- `sound_speed(tbl) -> np.ndarray` —— **严格等熵声速唯一实现**
  （`c_s² = (∂P/∂ρ)_T + T/(ρ²c_v)(∂P/∂T)_ρ²`）
- `plot_pv_diagram(tbl, T_ref, s_field, ...)` / `plot_interpolated_probe(...)` /
  `interpolate_quantity(...)` / `nion_from_rho(...)` / `rho_from_nion(...)`

### cn4_timeseries.py
时间演化绘图。cn4 是静态表，随时间变化的数据来自 **FLASH 辐射流体模拟 HDF5
时间序列**（`*hdf5_plt_cnt_*` / `result.h5` 含 `ed_time`）。形式 A：
`(t, x)` 二维彩图看波前传播；形式 B：固定空间位置（如靶中心 x=0）的时间曲线。
本模块不做物理量换算，输入为 cm/s 时调用方先转显示单位（ns/um）。

关键 API：
- `plot_time_series(...)` —— `(t, x)` 二维彩图
- `plot_center_series(...)` —— 特征点时间曲线
- `flash_extract(...)` —— 从 FLASH h5 序列批量抽取为网格数据
- `read_flash_h5(fp, var="tele", ...) -> np.ndarray` —— 读单文件单变量

### cn4_fit.py
四类关系拟合：`fit_power_law`（`y = a·x^b`，log-log 线性回归）、
`fit_exponential`（半对数回归）、`fit_ideal_gas`（检验 `P = (1+<Z>)·n_ion·k_B·T`）、
`fit_generic`（任意 `func`，scipy `curve_fit`）。物理常数取自
`config.EV_PER_K`（CODATA 单一来源规则，`test_config_single_source` 守护）。
每类拟合返回参数 + R² + 残差图 PNG（`compute_r2` 供复用）。

### cn4_thermo.py
cn4 热力学派生量——有效 γ 场 / 声速两项分解 / 等熵指数。固化自
`test/sound_velocity`（r16）：包级唯一实现，测试区改薄调用，消除双实现漂移
（ln10 bug 教训）。物理设计：① γ = 1 + P/(ρe) 单点恒等式（无差分），γ 场是
EOS 非理想性诊断量，**不用于声速**；② 声速只复用 `cn4_paths.sound_speed`，
本模块做 `c_s²` 两项分解（等温压缩项 + 热熵项，理想气体区热熵占比 2/5）；
③ 等熵指数 γ_sound = c_s²ρ/P。

关键 API：
- `gamma_ion(tbl) / gamma_ele(tbl) -> np.ndarray` —— γ_i / γ_e 场
- `gamma_species(tbl, p_name, e_name)` —— 通用单点 γ
- `cs_terms(tbl) -> tuple[np.ndarray, np.ndarray]` —— c_s² 两项分解
- `thermal_fraction(cs2_thermal, cs2_total) -> np.ndarray` —— 热熵占比
- `sound_gamma_eff(tbl) -> np.ndarray` —— 等熵指数场
- `gamma_powerlaw_fit(T_row, gamma_row) -> tuple[float, float, float]`
- `main(argv=None) -> int` —— CLI 入口

用法示例：
```python
from eosop_pro.parsers.cn4_io import load_cn4
from eosop_pro.plotting.cn4.cn4_plots import plot_quantity_heatmap
from eosop_pro.plotting.cn4.cn4_paths import trace_hugoniot, sound_speed

tbl = load_cn4("matter++/Ionmix/AL.cn4")
plot_quantity_heatmap(tbl, quantity="P", x_axis="T", y_axis="nion")
Us, Up, P = trace_hugoniot(tbl)          # 雨贡纽 + Us-Up 图
cs2 = sound_speed(tbl) ** 2
```
```bash
python -m eosop_pro.plotting.cn4.cn4_thermo sample.cn4 --outdir out/   # γ/声速报告
python -m eosop_pro.pipeline.cli cn4-plot sample.cn4 -q P -x T -y nion # 单图
python -m eosop_pro.pipeline.cli cn4-paths sample.cn4 --what hugoniot  # 热力学路径
```
