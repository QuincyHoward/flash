# gen_flychk_his 测试套件

## 一键命令

```bash
cd <repo root>            # 含 pyproject.toml

# 1) 生成测试数据 (幂等, 已存在则跳过; --force 强制重建)
python flash/input_gen/gen_flychk_his/test/make_test_data.py --force

# 2) 端到端测试: 6 数据源 × 6 区域方案 = 36 用例
#    + 每个 zip 回读自检 + out/REPORT.md + out/overview.png
python flash/input_gen/gen_flychk_his/test/run_test.py
python flash/input_gen/gen_flychk_his/test/run_test.py --pytest   # 附带全量 pytest

# 3) 单元测试 (223 例; 无任何外部 FLYCHK 包依赖)
python -m pytest flash/input_gen/gen_flychk_his/test -q

# 4) 解耦验证: 封锁 flychk* 导入后重跑全量测试 + 端到端 (机械化证明)
python flash/input_gen/gen_flychk_his/test/verify_decoupled.py

# 5) 【可选】与外部 FLYCHK 小包格式对拍 (非发布依赖, 需显式路径)
python flash/input_gen/gen_flychk_his/test/cross_check_external.py \
    --flychk-root /path/to/flychk-sim/flychk
```

状态 / 清理：

```bash
python flash/input_gen/gen_flychk_his/test/make_test_data.py --status
python flash/input_gen/gen_flychk_his/test/make_test_data.py --clean
```

## 测试数据（自定义合成，非 FLASH 真实结果）

`make_test_data.ensure_test_data()` 生成到 `test/data/`（已 gitignore）：

| 产物 | 内容 | 单位 |
|------|------|------|
| `flash_hdf5/xchk_hdf5_chk_0001..0008` | 合成 **FLASH 格式** 1D HDF5（变量 `dens/tele/tion/trad/ye/sumy/trac/pres/velx`，`unknown names` 为 `(n,1)`\|S4 布局，与 `flash.output_processors.FlashHDF5File` 读取契约一致） | FLASH 原生 (K, g/cm³) |
| `hist_series.npz` | `time`/`x` + 9 个 `(nt, nx)` 场 | K, g/cm³ |
| `hist_long.csv` | 长表 `time,x,te,ti,tr,rho,trac` | K, g/cm³ |
| `hist_series.json` | `{times, x, fields}` 结构 | K, g/cm³ |
| `hist_snapshots.json` | `{snapshots:[…]}` 结构 | K, g/cm³ |
| `hist_units.json` | 温度 eV / 密度 kg·m⁻³ + `units` **自声明** | eV, kg/m³ |

物理剖面（解析模型，与 `sources.synthetic_ch_ti_slab` 同源）：

- 坐标 `x ∈ [-100, +100] µm`，`nx = 800`（0.25 µm，可分辨 1/2/3 µm 示踪层）
- 初始 CH 平板 `x ∈ [-50, +50] µm`（0.25 g/cm³），外侧本底 1e-6 g/cm³
- 烧蚀面 `x_a(t) = -50µm + 2e5·t`（向 +x 推进），临界面 `x_c = x_a + 10µm`
- `Te(x,t) = Te_cold + (Te_pk(t) - Te_cold)·exp(-|x-x_c|/L_te)`，
  `Te_pk(t) = 1200 eV·(t/tmax)^0.25`，`L_te = 25µm + 1e7·t`，
  `Te_cold = 30 eV`；`Ti = 0.8 Te`，`Tr = 0.6 Te`
- 示踪层（`trac` = 1/2/3）位于 `x_a(t) + 1/2/3 µm`，随波前移动，含 5% 密度增量
- `ye = 3.5/13.011` mol e⁻/g，`sumy = 1/13.011` mol ions/g

> 该模型是**解析构造**（不是 FLASH 运行结果），用于验证单位换算、区域选择、
> 聚合、格式契约与端到端链路；产物全部确定性可复现（无随机数）。

## 用例矩阵

| 数据源 | 区域方案 | 说明 |
|--------|----------|------|
| `flash_hdf5` / `npz` / `csv` / `json_fields` / `json_snapshots` / `json_units_declared` | `whole_target` | 全域 |
| 同上 | `tracer_layers` | `label:trac=1/2/3`（3 zip） |
| 同上 | `spatial_layers` | `layer:1..4/4`（4 zip） |
| 同上 | `front_zone` | `x:-46..-40um`（波前附近） |
| 同上 | `corona_top10` | `top:10%@tele` |
| 同上 | `mass_half` | `mass:0..0.5` |

## 测试文件

| 文件 | 覆盖内容 |
|------|----------|
| `make_test_data.py` | 测试数据生成/状态/清理（含 CLI） |
| `run_test.py` | 端到端 36 用例 + 交叉验证 + 报告 + 概览图 |
| `test_units.py` | 单位换算、元素表、`ne = ρ·Z/A·N_A` |
| `test_sources.py` | 8 类数据源、别名、单位归一化/自声明/告警、派生 `nele/nion` |
| `test_regions.py` | DSL 解析、9 种区域掩码语义、分层精确覆盖、空区域诊断 |
| `test_builder.py` | 表构建、钳位/插值/抽稀/时间窗、`validate_table`、size 策略、聚合 |
| `test_zip_writer.py` | 自包含写出器、格式契约、回读自检、writer/manifest/batch 布局、**无外部引用静态断言** |
| `cross_check_external.py` | 【可选】与外部 FLYCHK 小包逐字节对拍 (显式路径才运行) |
| `verify_decoupled.py` | 解耦机械化验证 (封锁外部导入 → 全量测试 + 端到端) |
| `test_interface.py` | 门面类、一键函数、CLI、端到端物理合理性（示踪层较全域更热等） |

## 产物目录

- `test/data/` — 生成的测试数据（可 `--clean` 删除）
- `test/out/` — 端到端测试产物：`REPORT.md`、`overview.png`、逐用例目录
  （zip / 表文本 / 预诊断图 / `manifest.json`），每次 pytest 会话清空重建
