> 最后核对：2026-11-14 · commit ba2981e（其后含功能树重组，代码为准）

# grid/ —— 统一网格构造与 (log10 x, log10 Te) 双线性插值

上层依赖：`writer/h5_writer`（unified 轨道落盘）、`convert/`（h5 目标与 F1 反演后的统一网格）与 `plotting/` 消费本层。本层依赖 `config`（网格点数/范围/外推策略常量）。三条纪律：插值在 (log10 x, log10 Te) 空间进行；**越界 → NaN**（只表示"落在原生凸包之外"，与"值恰为 0"严格区分）；坐标轴单调性问题**默认不静默修复**。

## 模块

### interpolate.py —— 二维重采样（log 空间双线性）
源数组形状统一 `(n_Te, n_x)`（与 `ParsedTable.field_shape` 一致）。用 `np.interp` 逐行/逐列一维线性插值（等价双线性），越界由 `left=right=nan` 直接表达，无需额外掩码。被插值的量按族选择：`kappa` 在 log10 空间（本源数据即对数），`P/E/Z` 用线性。实现内部已做保序排序，单调性由调用方（`monotonic.diagnose_axis`）保证。

关键 API：
- `resample_2d(x_src, y_src, v_src, x_dst, y_dst, *, logs=("x","y"), log_value=False, extrapolation=None) -> ResampleResult` —— 双线性重采样，`values` 形状 `(len(y_dst), len(x_dst))`
- `resample_1d(x_src, v_src, x_dst, *, log_x=True, log_value=False, extrapolation=None) -> ResampleResult` —— 一维重采样（如 ColdOpacity 的 mu(photon_eV)）
- `to_array2d(values, shape) -> np.ndarray` —— 展平列表还原成 `(n_Te, n_x)`
- `log10_or_nan(values) -> np.ndarray` —— 非正值返回 NaN（不返回 -inf）
- `ResampleResult` —— `values/out_of_range/method/extrapolation` + `coverage` 属性

### monotonic.py —— 坐标轴单调性与重复点诊断（默认不静默修复）
重复点判定用相对容差（`config.MONOTONIC_ATOL`，默认 1e-12）。非单调点/重复点一律列出索引与数值，写进 `/meta/warnings` 供人工判定；`policy="error"`（默认）直接报错，`"average"`/`"keep_last"` 是显式探索性选项且动作记入 notes。

关键 API：
- `diagnose_axis(x, *, atol=None) -> AxisDiagnosis` —— 单调性/重复点/非有限值/log 等距/span 全量诊断
- `repair_axis(x, *, policy=None, atol=None) -> (新轴, notes)` —— 按显式策略修复（error/average/keep_last）
- `make_log_uniform(lo, hi, n) -> list` —— log10 等距一维网格（含端点）
- `log10_list(values) -> list` / `minmax(values) -> (min, max)`
- `AxisDiagnosis` —— 诊断结果容器，`clean` 属性 + `describe()`

### unified_grid.py —— 统一网格构造（rho_Te / nion_Te 两套共用 Te 轴）
两套网格**共用同一条 Te 轴**，只替换 x 轴变量：`rho_Te`（x = rho g/cm³）与 `nion_Te`（x = n_ion = rho·N_A/Ā，纯换算一一映射）。`(n_ele, Te)` 本轮不实现（后补预留）：接口已按"x 轴变换函数"参数化，新增 `nele_Te` 只需加一对 `x_from_rho`/`rho_from_x`，writer 与 interpolate 无需改动。范围退化的轴（如实测 `Mo_Ideal_Gas` 的 rho 网格 `[0.0, 1.0]` 过滤后仅剩 1 点）**不硬造网格**——`can_build` 返回 False，对应 gid 缺轨并记 warning（"宁可缺，不造假"）。

关键 API：
- `GRID_IDS = ("rho_Te", "nion_Te")` —— 本轮实现的网格 id
- `build_all_grids(tables, *, A=None, n_x=None, n_Te=None) -> dict[str, UnifiedGrid]` —— 构造全部统一网格（退化 gid 自动略过）
- `build_grid_for_tables(tables, *, gid, A=None, ...) -> UnifiedGrid | None` —— 取各表原生范围交集、按物理包络裁剪（`config.RHO_MIN/MAX`、`TE_MIN/MAX`）后构造
- `build_grid(gid, *, rho_range, Te_range, n_x=None, n_Te=None, A=None, origin="") -> UnifiedGrid` —— 显式范围构造
- `x_from_rho(gid, rho, A) / rho_from_x(gid, x, A)` —— x 坐标与 ρ 的双向换算
- `data_ranges(tables) -> dict` —— 一组表在 (rho, Te) 上的交集范围
- `UnifiedGrid` —— 数据类：`gid/x_axis/x/Te/attrs` + `n_x`/`n_Te`/`describe()`

## 用法示例

```python
from eosop_pro.grid.unified_grid import build_all_grids
from eosop_pro.grid.interpolate import resample_2d
from eosop_pro.grid.monotonic import diagnose_axis

grids = build_all_grids(tables, A=26.98)   # {'rho_Te': ..., 'nion_Te': ...}
g = grids["rho_Te"]
res = resample_2d(rho_src, Te_src, P_src, g.x, g.Te, logs=("x", "y"))
print(res.coverage, res.out_of_range)      # 覆盖率 / 越界点数
print(diagnose_axis(g.Te).describe())
```
