# Real FLASH Scenario Tests

Three standalone test scripts for running and validating real FLASH simulations:

| Script | Scenario | EOS | 初温 | Laser | sim_name | Timeout |
|--------|----------|-----|------|-------|----------|---------|
| `test_ch_center_run.py` | ch_center | he-imx-005 + polystyrene-imx-008 (old), eos_tab | **290.11375 K** | 5e14 W/cm² | LaserSlab1D_new | 300s |
| `test_al_run.py` | thin_layer_sandwich_al | al-imx-003 + he-imx-005 + polystyrene-imx-008 (old), eos_gam | **290.11375 K** | 5e11 W/cm² | grid_rede | 300s |
| `test_si_05ns_run.py` | thin_layer_sandwich_si | Z02 + Z14 + Z06 (new), eos_gam | **3500.00 K** | 5e14 W/cm², 0.5ns pulse | grid_rede_si | 600s |

> **Si 场景 3500K 说明**: 新 EOS opacity 表在 290K 低温时，扩散求解器在 He/CH 界面计算负时间步。提温至 3500K 可避免此问题。新 EOS 表起始温 0.01 eV（116 K），3500 K（0.30 eV）在有效范围内。

## Usage

```bash
# Run a single test (compiles FLASH + runs simulation + validates output)
python test_ch_center_run.py
python test_al_run.py
python test_si_05ns_run.py
```

### Dependencies
- Python 3.10+ with `h5py`, `numpy`
- FLASH 4.8 installed in WSL at `~/hello/FLASH/FLASH4.8/`
- `flash` package on `sys.path`

## What Each Test Validates

### 1. Simulation Status
- Engine returns `success=True`
- `result.h5` exists at `database/flash_out/result.h5`
- At least some chk files generated

### 2. Directory Structure
- `sim_input/` — contains FLASH source files and .par
- `sim_output/` — contains chk HDF5 files
- `database/flash_in/` — contains input_params.json + run.log
- `database/flash_out/` — contains result.h5

### 3. EOS File References
- ch_center: `he-imx-005.cn4` + `polystyrene-imx-008.cn4` (eos_tab)
- Al: `al-imx-003.cn4` + `he-imx-005.cn4` + `polystyrene-imx-008.cn4` (eos_gam)
- Si: `Z02_1.00` + `Z14_1.00` + `Z06_0.50` (eos_gam)

### 4. Output Data Shape
- Time grid: uniform step interpolation
- Spatial grid: uniform mesh interpolation
- All field arrays: `(Nt, Nx)` shape

### 5. Laser Parameters (Si 0.5ns)
- `ed_time_1_2 = 1e-10` (100ps rise)
- `ed_time_1_3 = 5e-10` (500ns peak)
- `ed_time_1_4 = 6e-10` (600ns off)
- `tmax = 7e-10` (700ns total)

## Architecture Notes

- Object directory: `{flash_home}/{user_name}/object_{sim_name}_{run_id:06d}`
  - user_name from `flash._core.credentials.get_user_name()`
  - run_id auto-increments
- Sim source directory: `{flash_home}/source/Simulation/SimulationMain/{user_name}/{sim_name}`
- Each run has unique object directory (never conflicts)
- dtmax defaults to `tmax * 1.05` (calculated from laser pulse times)

## EOS 表温度单位

所有 `.cn4` 温度网格单位为 **eV**（电子伏特），FLASH 运行时自动将 `sim_tele*`（K 值）转换为 eV 查表。

| EOS 表 | 起始温度 | ≈ K | 说明 |
|--------|---------|-----|------|
| 旧表 (he-imx-*, al-imx-*, polystyrene-imx-*) | 2.0 eV | 23209 K | 室温 0.025 eV 低于下界，FLASH 外推处理 |
| 新表 (Z02_*, Z06_*, Z14_*) | 0.01 eV | 116 K | 室温 0.025 eV 在有效范围内 |

## 并行后处理

`interpolate_flash_to_grid` 默认启用 `use_parallel=True`，自动使用并行处理：
- 文件读取：`ThreadPoolExecutor` (上限 12 workers)
- 时空插值：`ProcessPoolExecutor` (上限 7 workers)
- 自动降级：小数据 (<4 文件或 <16 时间步) 自动串行

详见 `flash/output_processors/parallel.py`。

## Latest Test Results

| Scenario | t range | Fields | Chk files | Initial Temp | Status |
|----------|---------|--------|-----------|-------------|--------|
| ch_center | 0~1.00ns (300s timeout) | 7 | 608 | 290.11375 K | ✅ |
| Al | 0~3.00ns (reached max SimTime) | 13 | 15 | 290.11375 K | ✅ |
| Si (0.5ns) | 0~0.70ns (reached max SimTime) | 13 | 48 | 3500.00 K | ✅ |
