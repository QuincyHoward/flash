# gen_flychk_his — FLASH 数据 → FLYCHK history 输入压缩包

**版本**: 0.1.0 · **最后更新**: 2026-09-10

把 FLASH（1D）剖面时间序列转成 **NIST FLYCHK 网站可上传的 history 模式输入 zip**
（`runfile.txt` + 历史数据 `*.txt`），支持多空间区域批量生成、全流程可追溯与
写出后回读自检。

> **完全自包含**：写出器仅依赖 Python 标准库，**不导入、不搜索、不依赖任何
> 外部 FLYCHK Python 包**，可随 flash-sim 单独分发；写出格式遵循 FLYCHK
> history 模式官方输入契约（`FORMAT_CONTRACT_ID = "flychk-history-v1"`）。
> 若需与外部小包做格式对拍，见测试目录下的可选脚本
> `test/cross_check_external.py`（默认不参与测试，非发布依赖）。

---

## 目录

1. [快速开始](#快速开始)
2. [数据流与文件结构](#数据流与文件结构)
3. [接口多样性](#接口多样性)
4. [FLYCHK 格式契约](#flychk-格式契约)
5. [单位与物理映射](#单位与物理映射)
6. [区域选择 DSL](#区域选择-dsl)
7. [时间与数值处理链](#时间与数值处理链)
8. [输出与可追溯性](#输出与可追溯性)
9. [命令行](#命令行)
10. [测试](#测试)
11. [常见问题](#常见问题)

---

## 快速开始

### 1. 一键函数

```python
from flash.input_gen.gen_flychk_his import generate_history_zip

zip_path = generate_history_zip(
    source="path/to/flash_output/",      # FLASH 输出目录 / glob / 单文件
    element="Ti",
    region="x:-46..-40um",               # 区域 DSL (见第 6 节)
    output_dir="out/",
    columns=["time", "size", "te", "ti", "tr", "rho"],
    agg="mass",                          # 质量加权平均
    n_time_max=8,                        # 抽稀到 8 个时间步 (FLYCHK 建议 ≤50)
    dens_cut=1e-6,                       # 剔除真空/本底单元
)
```

### 2. 门面类（多区域批量）

```python
from flash.input_gen.gen_flychk_his import FlychkHistoryGenerator

gen = FlychkHistoryGenerator(element="Ti", agg="mass", n_time_max=8,
                             dens_cut=1e-6)
gen.load("path/to/flash_output/")            # 只加载一次, 后续复用
info = gen.inspect(region="label:trac=2")    # 先诊断 (不写盘)

report = gen.generate(
    region=["label:trac=1", "label:trac=2", "label:trac=3"],
    output_dir="out/",
    write_preview=True,                      # 生成预诊断图
    self_check=True,                         # 写出后回读 zip 与表内容核对
)
print(report.summary())
```

### 3. 命令行

```bash
python -m flash.input_gen.gen_flychk_his.cli --demo --out out/        # 合成数据自检
python -m flash.input_gen.gen_flychk_his.cli --interfaces             # 打印接口清单
python -m flash.input_gen.gen_flychk_his.cli --source run_dir/ \
    --element Ti --region "label:trac=2" --agg mass --out out/ --preview
```

---

## 数据流与文件结构

```
FLASH 输出 (chk/plt HDF5) ─┐
npz / csv / json ──────────┤
内存 dict / callable ──────┼─→ sources.load_series ──→ SnapshotSeries
合成解析模型 (None) ───────┘      (归一化为 eV/cm/g·cm⁻³)
                                        │
                                        ▼
                     regions.RegionSpec 逐时间步求掩码 (材料/波前随之移动)
                                        │
                                        ▼
                     extract.extract_region 区域聚合 → RegionSeries
                                        │
                                        ▼
                     builder.build_table 修补/钳位/时间处理 → HistoryTable
                                        │
                                        ▼
        zip_writer.HistoryZipWriter → FLYCHK 输入 zip (+ manifest 清单/表/预览图)
```

| 模块 | 职责 |
|------|------|
| `units.py` | 单位换算（K⇄eV、cm⇄µm、g/cm³⇄kg/m³）、元素表（Z / 原子量 / 谱窗） |
| `config.py` | `FlychkHisConfig`（不可变）+ `ValidationReport` 配置校验 |
| `sources.py` | 全数据源统一加载、单位归一化、派生 `nele`/`nion`、合成解析模型 |
| `regions.py` | 区域选择（对象/工厂/DSL/dict/元组/callable），9 种区域类型 |
| `extract.py` | 聚合函数注册表、`size` 策略、区域序列提取 |
| `builder.py` | FLYCHK 表构建与校验（NaN 修补 → 钳位 → 时间处理 → 组行） |
| `zip_writer.py` | **自包含** FLYCHK history zip 写出器（仅标准库）+ 回读自检 |
| `writer.py` | zip/表文本/manifest 写出，flat/batch 布局，zipfiles 中转 |
| `preview.py` | PPT 演讲级预诊断图（全英文、≥18pt、DPI 450） |
| `cli.py` | 命令行入口（含 `--inspect` / `--list-elements` / `--interfaces`） |

---

## 接口多样性

### 1) 数据源（8 类，自动派发）

| `source` 形态 | 说明 |
|---------------|------|
| 目录 / glob / 单文件 / 路径列表 | FLASH HDF5，经 `FlashDataLoader(extraction_mode="h5py")` 读**叶子块** |
| `*.npz` | `time`/`x` + 多个 `(nt, nx)` 场，可选 `widths` |
| `*.csv` | 长表（`time`, `x`, 物理量列） |
| `*.json` | `{times, x, fields, units}` 或 `{snapshots:[...]}`（**可自声明单位**） |
| `dict` | `{"time":…, "x":…, "tele":…}` 或 `{"snapshots":[…]}` |
| 快照字典列表 | `[{time, x, tele, …}, …]` |
| `callable` | `f(t) -> {"x":…, 物理量…}`，配合 `times=[…]` |
| `None` | 合成解析模型（CH 烧蚀靶 + Ti 示踪层），用于自检/演示 |

变量名支持别名：`te/tele`、`ti/tion`、`tr/trad`、`rho/dens`、`ne/nele`、`ni/nion`。

```python
# 反例: 温度已是 eV 时应显式声明, 否则按 FLASH 原生 K 解释 (差 11604 倍)
generate_history_zip(source="series.npz", element="Ti", region="whole",
                     output_dir="out/", input_units={"tele": "eV"})
```

### 2) 区域（9 种类型 × 6 种书写形式）

类型：`whole` / `x_range` / `dens_range` / `mass_range` / `label` / `layer` /
`top_fraction` / `index_slice` / `custom`。
书写：`RegionSpec` 对象、工厂函数（`x_range()`、`label()`…）、字符串 DSL、
`dict`、`(lo, hi)` 元组、`callable` 掩码。

### 3) 聚合方式

`mean` / `median` / `mass`（默认，权重 `dens·dx`）/ `volume` / `max` / `min` /
`center` / `peak_dens` / `percentile:NN` / 自定义 `f(values, snapshot, mask) -> float`。

### 4) 列组合与密度基准

`rho` / `ne` / `ni` **三选一**（FLYCHK runfile 只接受单一密度基准），
`size` / `ti` / `tr` 可选，列序可自定义。
若数据缺 `tion`/`trad`，自动回退到 `tele` 并在 manifest 的
`column_fallback` 中记录。

### 5) `size` 策略（FLYCHK 中表示等离子体尺度, cm）

| 模式 | 含义 |
|------|------|
| `extent`（默认） | 区域物理厚度（含半边界单元）——不透明度路径长度的物理对应 |
| `scale_length_ne` / `scale_length_te` | 梯度标长 `f/\|df/dx\|` 的域内中位数，以区域厚度为上限 |
| `fixed` | 固定值 `size_value`，可乘 `size_scale` 统一修正 |

### 6) 时间处理

`time_unit`（s/ps/ns/fs）、`time_stride`、`n_time_max`（均匀抽稀，保留首末）、
`tmin`/`tmax`（时间窗）、`drop_nonpositive_time`（FLYCHK 需要 `t > 0`）。

### 7) 输出

`layout=flat|batch`、`manifest.json`、表文本、预诊断图、`zipfiles/` 中转目录、
`self_check` 回读自检、`inspect()` 只诊断不写盘。

### 8) 自检与可选对拍

- **写出后回读自检**（默认开启）：`self_check=True` 会把刚写出的 zip 读回，
  与表内容逐字符核对（成员顺序 / runfile 内容 / 数据文件 == `table.to_text()`），
  结论写入 `manifest.json` 的 `zip_integrity` 与 `zip_integrity_ok`；
- **可选外部对拍**（不属于发布包）：`test/cross_check_external.py`
  可与外部 FLYCHK 小包逐字节比对格式契约。

---

## FLYCHK 格式契约

写出由 **`zip_writer.HistoryZipWriter`（自包含, 仅标准库）** 完成，
格式契约 `FORMAT_CONTRACT_ID = "flychk-history-v1"`：

```
zip 成员顺序: runfile.txt , history_{element}_Z{z}_input.txt

runfile.txt:
    z 22
    initial ss
    evolve ss
    history
    opacity file                     # 仅当含 size 列
    ti file                          # 仅当含 ti 列
    tr file                          # 仅当含 tr 列
    history history_Ti_Z22_input.txt rho    # 密度列名随 rho/ne/ni 变化
    end

数据文件:
    time size te ti tr rho           # 首行列名, 空格分隔
    1.000000e-12 2.000000e-04 ...    # 数据行, %.6e
```

**硬约束**（违反即 `ZipWriterError`）：必须含 `time` 与 `te`；`rho/ne/ni`
最多出现一种；行长必须等于列数。

**写出后自检**（`self_check=True`，默认）：回读 zip 并逐字符核对
成员顺序、runfile 内容、数据文件与 `table.to_text()`；结论写入
`manifest.json` 的 `zip_integrity`。

**可选外部对拍**（不属发布包，默认不运行）：

```bash
python flash/input_gen/gen_flychk_his/test/cross_check_external.py \
    --flychk-root /path/to/flychk-sim/flychk    # 或设 FLYCHK_SIM_ROOT
```

**独立分发验证**（机械化证明外部包不可达时功能完整）：

```bash
python flash/input_gen/gen_flychk_his/test/verify_decoupled.py
# 1) 源码扫描无外部包引用  2) 封锁 flychk* 导入  3) 敌对环境端到端 + 全量测试
```

---

## 单位与物理映射

内部规范单位：**eV / s / cm / g·cm⁻³ / cm⁻³**；FLASH 原生 cgs + K 为默认输入解释。

| FLYCHK 列 | 输入（FLASH 原生） | 输出 | 换算 |
|-----------|-------------------|------|------|
| `te` / `ti` / `tr` | `tele`/`tion`/`trad` [K] | eV | ÷ 11604.5181（`1/k_B`） |
| `rho` | `dens` [g/cm³] | g/cm³ | — |
| `ne` | `nele` [cm⁻³] | cm⁻³ | `ye·dens·N_A`；缺 `ye` 时 `dens·Z_eff/A·N_A` |
| `ni` | `nion` [cm⁻³] | cm⁻³ | `sumy·dens·N_A`；缺 `sumy` 时 `dens/A·N_A` |
| `size` | 区域厚度/标长 | cm | 见 size 策略 |
| `time` | FLASH time [s] | s | 按 `time_unit` 缩放 |

**单位自洽性保护**：若声明单位为 K 但温度最大值 < 5×10⁴ K（≈4.3 eV），或声明
eV 但最大值 > 5×10⁵ eV，会在 `Snapshot.meta["unit_warnings"]` 中给出告警
（并随 `load_series(verbose=True)` 打印），避免 K⇄eV 的 11604 倍静默误读。

元素表（`units.element_table()`）提供 Z、原子量与**谱窗记录**（取自本仓库既有
产物命名，非 FLYCHK 必需）：Ti He `[4655, 4810]`、Ti Ly `[4921, 5032]`、
V He `[5110, 5240]`、Al `[1580, 1740]`、Si `[1840, 2020]`、Mg `[1330, 1485]` eV。

---

## 区域选择 DSL

```text
whole                    全部单元
x:-46..-40um             坐标区间 (支持 cm/mm/um/nm, 默认 cm; 也接受 [-40,0]um)
rho:0.1..10              质量密度区间 (g/cm^3)
mass:0..0.5              归一化质量坐标区间 (由左端累计, 0~1)
label:trac=2             材料标签等值 (可多值: label:trac=1,2)
label:dens>=0.1          质量分数/任意变量阈值
layer:1/4                等厚分层中的第 1 层 (1-based, 共 4 层)
top:10%                  密度最高的 10% 单元 (可 top:10%@tele)
index:0:60[:2]           按 x 升序的索引切片
```

区域掩码**逐时间步重算**，因此材料层与波前会随时间移动（拉格朗日视角），
这正是示踪层分析所需的行为。

---

## 时间与数值处理链

`build_table` 的处理顺序固定，且每步计数写入 `HistoryTable.meta`：

1. **NaN 修补** — 内部线性插值，端点取最近有效值（计数 `nan_filled`）
2. **物理钳位** — `te/ti/tr ∈ [te_floor, te_ceil]`，`rho ∈ [dens_floor, dens_ceil]`，
   `ne/ni/size > 0`（计数 `clamped`）
3. **时间单位换算** — 秒 → `time_unit`（同时保留 `time_span_seconds`）
4. **非正时间剔除** — `drop_nonpositive_time`（FLYCHK 需要 `t > 0`）
5. **时间窗裁剪** — `tmin` / `tmax`
6. **抽稀** — `time_stride`，再 `n_time_max` 均匀取点（保留首末）
7. **去重** — 强制时间严格递增（重复时间保留后者）

`validate_table` 独立复核：必需列、单一密度列、行长一致、有限值、
`time` 严格递增且为正、`size/te/…` 为正；`strict=True` 时告警升级为错误。

---

## 输出与可追溯性

```
output_dir/
├── history_{label}_{element}_Z{z}_in_.zip      # FLYCHK 上传文件 (2 成员)
├── history_{label}_{element}_Z{z}_in_.txt      # 表文本 (便于人工核查/对拍)
├── history_{label}_{element}_Z{z}_in_preview.png  # 预诊断图 (可选)
├── manifest.json                               # 全量可追溯清单
└── zipfiles/                                   # FLYCHK 场景约定的中转目录 (可选)
```

`manifest.json` 记录：生成时间、源文件列表与提取模式、每个区域的
`RegionSpec` 定义、单元数统计、聚合方式、`size` 来源说明、各列钳位/插值计数、
校验结果（errors/warnings/info）、后端解析级别与根目录、交叉验证结论。

---

## 命令行

```bash
# 合成数据自检 (无需 FLASH 输出)
python -m flash.input_gen.gen_flychk_his.cli --demo --out out/ --preview --cross-check

# 真实数据 + 多区域
python -m flash.input_gen.gen_flychk_his.cli \
    --source path/to/flash_output/ --extraction-mode h5py \
    --element Ti --columns time,size,te,ti,tr,rho \
    --region "x:-46..-40um" --region "label:trac=2" \
    --agg mass --n-time-max 8 --dens-cut 1e-6 \
    --out out/ --layout flat --preview --cross-check

# 只诊断 / 自检
python -m flash.input_gen.gen_flychk_his.cli --source out/ --inspect
python -m flash.input_gen.gen_flychk_his.cli --list-elements
python -m flash.input_gen.gen_flychk_his.cli --interfaces
```

---

## 测试

```bash
# 1) 生成测试数据 (幂等; 合成 FLASH HDF5 + npz/csv/json)
python flash/input_gen/gen_flychk_his/test/make_test_data.py --force

# 2) 一键端到端 (6 数据源 × 6 区域方案 = 36 用例 + 交叉验证 + 报告 + 概览图)
python flash/input_gen/gen_flychk_his/test/run_test.py

# 3) 单元测试
python -m pytest flash/input_gen/gen_flychk_his/test -q

# 4) 解耦验证 (封锁外部包导入后重跑全量测试)
python flash/input_gen/gen_flychk_his/test/verify_decoupled.py

# 5) 【可选】与外部 FLYCHK 小包格式对拍 (需显式给出路径)
python flash/input_gen/gen_flychk_his/test/cross_check_external.py --flychk-root <path>
```

详见 [`test/README.md`](test/README.md)。

---

## 常见问题

**Q1. 生成的 `te` 全是 1 eV，密度也不对？**
温度单位被按 K 解释而数据其实是 eV（或反之）。检查
`Snapshot.meta["unit_warnings"]`，用 `input_units={"tele": "eV"}` 显式声明，
或让 JSON 数据携带 `"units"` 键自声明。

**Q2. 报错"区域 … 为空"？**
错误信息会打印该时刻的 `x` 范围、`dens` 范围与可用变量列表。常见原因：
区域坐标单位写错（`x:-46..-40um` 而非 `-46..-40`）、材料标签变量名不符
（FLASH 变量名 ≤4 字符，如 `trac` 而非 `matid`）。

**Q3. 报错"缺少列 ti/tr"？**
数据源无该变量。两种处理：把 `columns` 改为 `["time","size","te","rho"]`，
或让 `ti`/`tr` 走自动回退到 `tele`（manifest 的 `column_fallback` 会记录）。

**Q4. FLYCHK 网站提交失败/超时？**
先用 `n_time_max` 把时间步压到 ≤50（经验值），并确认 `te > 0`、单密度基准；
提交前的 `*_preview.png` 用于核对曲线是否符合物理预期。

**Q5. 为什么必须指定 `dens_cut`？**
FLASH 本底填充气体（如 He，~1e-6 g/cm³）会把区域平均拖到无物理意义的低温低密
状态；按数据本底设置 `dens_cut`（如 `1e-6`）可获得有代表性的区域状态。

**Q6. 可以只写表不写 zip 吗？**
可以：`write_zip=False`，或使用 `build_history_table()` /
`history_table_text()`；`--no-zip` 同理。

**Q7. 窄示踪层的 `size` 在时间步之间跳变？**
`size_mode="extent"` 取的是**离散单元**覆盖宽度；示踪层只有 3~4 个单元时，
其与网格的相对位置每步不同，覆盖宽度会出现一个网格间距的量化跳变（manifest 中
`cells.min/max` 会体现）。物理上更稳的做法：

- 用 `size_mode="fixed"` + `size_value=<层厚>`（例如 1 µm = 1e-4 cm）；
- 或用 `size_mode="scale_length_ne|te"`（以梯度标长为路径长度）；
- 或提高 FLASH 输出分辨率（+ug 均匀网格）让层内单元数 ≥10。

**Q8. 这个子包依赖别的 FLYCHK Python 包吗？能随 flash-sim 单独发布吗？**
不依赖。发布包源码（顶层 `*.py`）**不含任何外部 FLYCHK 包的导入或路径搜索**，
zip 写出完全由 `zip_writer.py`（仅标准库）实现，只以 FLYCHK 官方**输入格式契约**
为对接面。机械化验证：

```bash
python flash/input_gen/gen_flychk_his/test/verify_decoupled.py
```

该脚本会在 `sys.meta_path` 上封锁 `flychk*` 的导入（抛错而非静默回退）后重跑
全量测试与端到端生成。`test/cross_check_external.py` 里的对拍能力是**可选工具**，
只有显式给出路径才会运行，不属于发布依赖。

**Q9. `manifest.json` 里为什么没有 `backend` 字段？**
解耦后统一为 `writer` 段：`{"id": "flash.input_gen.gen_flychk_his",
"format_contract": "flychk-history-v1", "self_contained": true}`，
配合 `zip_integrity` / `zip_integrity_ok` 记录回读自检结论。
