# eosop_pro

> 最后核对：2026-11-14 · commit ba2981e（其后含深度功能树重组，以代码为准） · 维护规则：改动 eosop_pro/ 代码后同步本文模块要点


> `Multi1D++Portable20241128/matter++` 的物质数据（EOS / 不透明度 / Z̄ / NLTE /
> 冷不透明度 / 雨贡纽）→ **统一解析 → 统一网格 → 双轨 HDF5**。
>
> 每一条结论都可回溯到具体文件与字段；每一个未定项都**显式记账**而非静默降级。

---

## 实测状态

| 项 | 值 |
|---|---|
| 源数据 | `matter++`：**1214 文件 / 695.9 MiB** |
| 解析覆盖率 | **992 / 1214 = 81.7%**（其余 222 为登记跳过） |
| **问题文件** | **0** |
| 闸口 | `已解析 + 已跳过 == 文件总数` ✅ |
| 交叉验证 | `identify` 比对 → `conflict` **0** |
| 测试 | **54 文件 / 691 测试全绿**（零依赖运行器 `test/run_all.py`） |
| 格式族 | 6 大族 / 16 个解析器 |

---

## 快速开始

```bat
:: 1) 建 venv 并安装依赖（双击）
scripts\env_setup.bat

:: 2) 全流程：抽取文档 → 清单 → 审计 → Z̄ → 比对 → h5 → 出图 → 反演 → 测试
scripts\run_all.bat
```

单步启动器（双击即可）：`scripts\01_extract_docs.bat` … `scripts\09_infer_unknown.bat`。

命令行等价（**唯一 CLI 入口**：`python -m eosop_pro.pipeline.cli`）：

```bash
<venv>/Scripts/python.exe -m eosop_pro.pipeline.cli extract-docs
<venv>/Scripts/python.exe -m eosop_pro.pipeline.cli inventory
<venv>/Scripts/python.exe -m eosop_pro.pipeline.cli audit
<venv>/Scripts/python.exe -m eosop_pro.pipeline.cli zeff
<venv>/Scripts/python.exe -m eosop_pro.pipeline.cli identify
<venv>/Scripts/python.exe -m eosop_pro.pipeline.cli convert-all --limit 20
<venv>/Scripts/python.exe -m eosop_pro.pipeline.cli plot-all --limit 12
<venv>/Scripts/python.exe -m eosop_pro.pipeline.cli infer-unknown
<venv>/Scripts/python.exe -m eosop_pro.pipeline.cli prune-reports  # 报告只留最新一批
<venv>/Scripts/python.exe eosop_pro\test\run_all.py                # 或 cd eosop_pro 后 test/run_all.py
```

单文件排查：

```bash
python -m eosop_pro.pipeline.cli parse  mat_Al-1.0/AL_eos                # 声明式解析摘要
python -m eosop_pro.pipeline.cli infer  mat_Au-1.0/AU_op03r              # 零先验反演报告
python -m eosop_pro.pipeline.cli h5     mat_Al-1.0/AL_eos --out al.h5    # 单表双轨 h5
python -m eosop_pro.pipeline.cli convert mat_Al-1.0/AL_eos \
        --to hyades_eos --out al_from_f1.dat --invert                     # F1 → F3
python -m eosop_pro.pipeline.cli targets                                 # 可转换目标清单
```

---

## 目录（深度功能树，逐层按功能划分）

```
eosop_pro/                 包根 = 项目根（扁平化布局）
├─ __init__.py             包入口（re-export config，保住 from eosop_pro import config）
├─ core/                   基础层（格式无关）
│  ├─ config.py            ★ 唯一常量来源（路径/阈值/网格/压缩/绘图），禁止别处硬编码
│  ├─ docsrc.py            说明文档抽取（doc/docx/pptx/xlsx/xmind/pdf/txt）
│  ├─ text/                文本字节级读取：textio / byteclass / hashing / errors / snapshot
│  ├─ numbers/             Fortran 数值解析：fortran_numbers / fixedwidth
│  ├─ profile/             行剖面 / 列剖面：lineprofile / columnprofile
│  └─ infer/               盲读推断（阶段 B）：inference / envelope / anchors / annotations / guess
├─ parsers/                 16 个格式族解析器 + base（ParsedTable 公共容器）
│  ├─ formats/              每解析器一份格式说明（<解析器名>.md，含 uk/uv 标记）
│  └─ test/                 产物核查套件（解析统计 + 代表性图像，人工核查用）
├─ registry/                注册表层
│  ├─ identify/             identify（两阶段比对）/ dispatch（声明分发）
│  ├─ material/             material / material_base / eos_list（材料注册表三源）
│  ├─ schema/               declared_types / annotation_store / database_index
│  ├─ zeff/                 zeff_registry / zeff_inventory / units_registry
│  └─ field_checks.py       字段控制字典（与 docs/eosop变量控制字典.md 逐字同步）
├─ convert/                 跨格式转换（read A → ParsedTable → write B）
├─ grid/                    统一网格与插值
├─ writer/                  HDF5 双轨写出
├─ plotting/                PPT 级 QA 出图（全英文）
│  ├─ cn4/                  cn4 专系：paths / plots / timeseries / fit / thermo
│  ├─ qa/                   qa_plots / gridmap（任意族共用热图原语）
│  └─ style/                labels / units / style
├─ pipeline/                编排层：batch.py（批处理）+ cli.py（唯一 CLI 入口）
├─ ops/                     运行维护：reporting（报告写出）/ prune（保留策略）
├─ scripts/                 10 个薄包装 py + 12 个双击 bat
├─ test/                    54 个测试文件（零依赖运行器 run_all.py）
├─ docs/                    文档索引 README + 13 篇正式文档 + archive/
└─ outputs/                 h5 / plots / reports / logs（gitignore）
```

---

## 两层结构（为什么要这样分）

### 层 1：声明通道（阶段 A）

按**扩展名 / 路径 / 文件名 / 注释 / 注册表**判定家族，逐文件解析。
预期计数由格式公式给出，**必须严格相等**，否则报 `count_mismatch`。

声明给的是**候选列表**而非单值 —— 候选回退机制让"声明错了"退化为
"多试一次"，而不是致命错误。实测：

```
hyades/sesame/eos_41.dat.feos  →  hyades_eos（按上游 Readme 的 hyades 优先规则）
mat_Al-1.0/AL_eos.feos         →  文件名说 .feos，内容却是 F1 反演 EOS
                                  → 候选第 2 位命中，正确解析
```

### 层 2：内容通道（阶段 B）

**只有字节流**，不读任何声明。把表头整数当未知量，
用「计数守恒 × 网格单调 × 物理包络」求解布局：

```bash
$ python -m eosop_pro.pipeline.cli infer mat_Al-1.0/AL_eos
状态: ok
自洽候选 (1):
  - f1_with_e0(d1=66,d2=74,ng=1) payload=9974 mono=True env=True score=2.00
      · 前导表头行数 k=1
```

结论三态：`ok`（唯一解）/ `ambiguous`（**全部列出**）/ `unrecognized`（如实报告）。
**绝不静默挑一个。**

两阶段交叉验证由 `identify` 完成，分类为
`agree` / `order_mismatch` / `conflict` / `declared_only` / `inferred_only`。

---

## 支持的格式族

| 族 | 解析器 | 文件数 | 独立变量 | T 单位 |
|---|---|---|---|---|
| F1 MULTI 反演 EOS | `multi_inverted_eos` | 53 | `(rho, de)` | **Kelvin**（→eV） |
| F2 MULTI 不透明度/Z̄/NLTE | `multi_opacity` | **391** | `(rho, Te)` log10 | **eV** |
| F3 Hyades / SESAME | `hyades_eos` / `hyades_opacity` | 99 + 36 | `(rho, Te)` | **keV**（→eV） |
| F4 FEOS / MPQeos | `mpqeos` / `feos_native` / `feos_tabdata` / `feos_aux` | 190 | `(rho, Te)` | **Kelvin/keV**（→eV）；`.feos` 原生为 **eV** |
| F5 LEDCOP / ATOMIC | `ledcop_atomic` / `ledcop_zeff` | 31 | `(rho, Te)` log10 | **keV**（→eV） |
| F6 其他 | `coldopacity` / `hugoniot` / `ionmix` / `snop_input` / `generic_curve` | 270 | 混合 | 声明决定 |

★ **同一物理量在不同族里单位不同**（`Kelvin` / `eV` / `keV`），
所以单位走**独立四级仲裁链**（`companion > inline > envelope > config_default`），
每条裁决带 `source` 与 `evidence`，写进 h5 与报告。

★ **cn4 原生直通**（`parsers/cn4_io.py`）：`convert_cn4_to_cn4` 默认
`verbatim=True` —— 数据区逐字节直通（仅头部按表字段复刻），
保证 cn4→cn4 往返 byte-identical。原因：BADGER-TOPS 系列文件**同一文件内
混用两种 e12.6 尾数风格**（`0.ddddddE±dd` 与 `d.ddddddE±dd`）并以
`-Infinity` 字面量表示负无穷，逐值重排无法复刻。显式传 `mantissa_style=`
或 `write_opacities=False` 时退回逐值重排路径。

---

## 输出

### HDF5（双轨）

```
/tables/<KIND>_<id>/
    native/            轨道 1：原生网格**逐字**保留（含 units 与 log10 属性）
    unified/<gid>/     轨道 2：插值到统一网格
        x  Te          轴
        <field>        [n_Te, n_x]（与 ParsedTable 同序）
/meta/sources          逐表溯源（20 列）
/meta/units            (quantity, unit, 来源) 逐条
/meta/warnings         全部告警
/meta/zeff_sources     Z̄ 来源
```

统一网格本轮两套，**共用同一条 Te 轴**：

| `gid` | x 轴 | 换算 |
|---|---|---|
| `rho_Te` | `rho [g/cm³]` | — |
| `nion_Te` | `n_ion [1/cm³]` | `ρ·N_A/Ā` |
| `nele_Te` | `n_ele [1/cm³]` | ⏳ 后补（接口已预留） |

★ NaN **只**表示"落在原生凸包之外"（`nan_semantics="out_of_range"`），
与"值恰为 0"严格区分。

### 报告

`outputs/reports/` 下每类报告都带时间戳，头部固定写明
**数据来源 / 生成时刻(UTC) / 样本总数 / 工具版本**：

`audit_all.*` · `inventory.*` · `convert_all.*` · `plot_all.*` ·
`zeff_inventory.*` · `identify.*` · `infer_unknown.*`

### 图

`outputs/plots/`：全英文、DPI 450、title ≥ 24 pt、label/tick ≥ 20 pt、
legend ≥ 18 pt、linewidth ≥ 2、markersize ≥ 8（由测试断言）。

---

## 配置

**唯一常量来源**是 `eosop_pro/core/config.py`，其他模块不得硬编码
（由 `test/hygiene/test_config_single_source.py` 用 `ast` 扫源码强制；
`from eosop_pro import config` 经包入口 re-export 继续可用）。

任意项可用环境变量覆盖（前缀 `MULTI_EOSOP_`）：

```bash
MULTI_EOSOP_MATTER_DIR=/path/to/matter++ \
MULTI_EOSOP_N_X_UNIFIED=256 \
MULTI_EOSOP_EXTRAPOLATION=clamp \
MULTI_EOSOP_MONOTONIC_POLICY=average \
  python -m eosop_pro.pipeline.cli h5 mat_Al-1.0/AL_eos --out al.h5
```

---

## 已知边界（诚实清单）

1. **`ok_unverified` 159 个** —— 结构自洽但单位用的是族默认值，缺针对性声明。
2. **多群段默认不解析** —— LEDCOP 多群（`ATOMIC/Al.txt` 34.8 万行）需
   `--multigroup` 显式开启。
3. **`generic_curve` 94 个** —— 这是**降级**而非成功：
   收下了列式数值，但轴与场只标 `x`/`colN`，单位 `unknown`。
4. **`feos_native` 已定案（2026-11）** —— 16 块 + Qtot + Q 由
   `FE-01_TABTOOLS.C::write_FEOS_format` 定案解码（R3 废除）；
   详见 `parsers/formats/feos_native.md`。已知边界：matter++
   `mat_Others/SiO2.feos`（3 位指数粘连变体）拒收；简并角落
   （低 T × 低 ρ）压力反演电离度可超 Z（数据性质，notes 告警）。
5. **`ionmix` 列语义待定** —— 本地无 IONMIX 格式文档。
6. **PDF 文本层** —— CID 字体抽不出（如部分中文文献），如实记 warning，
   不转述未读内容。
7. **`.xls`（BIFF8）** —— 用 UTF-16LE 游程扫描，保留文本但**丢失表格结构**。
8. **`nele_Te` 网格** —— Z̄(ρ,T) 只覆盖 130/251 材料，
   其余 121 个只能 `Z̄ = const` 近似。

---

## 文档

完整技术文档在 [`docs/`](docs/README.md)（13 篇，位于 `docs/` 根）。
建议先读：

| 想做什么 | 读 |
|---|---|
| 搞清楚方法论 | [docs/02 两段式执行](docs/02_两段式执行.md) |
| 查某个后缀是什么 | [docs/20 格式规格手册](docs/20_格式规格与物理量单位手册.md)（04~09 旧规格已归档至 [docs/archive/](docs/archive/)） |
| **给任意格式我怎么识别** | [docs/11 通用识别协议](docs/11_通用识别协议.md) |
| 用 h5 数据 | [docs/12 HDF5 模式](docs/12_HDF5模式.md) |
| 核对单位 | [docs/15 单位换算](docs/15_单位换算.md) |

---

## 依赖

第三方依赖：`numpy` / `h5py` / `scipy` /
`matplotlib` / `cryptography`。
核心解析层（`core/` / `parsers/` / `registry/`）**零第三方依赖** ——
只用标准库 `re` / `zipfile` / `zlib` / `hashlib`。
`numpy`/`h5py` 只在 `grid/` / `writer/` 需要；
`matplotlib` 只在 `plotting/` 需要；
`cryptography` 只在 `scripts/07_gitee_publish.py` 需要。
