# 全量覆盖矩阵与语意识别汇总

> 数据根：`src/Multi1D++Portable20241128/matter++/`
> 生成脚本：`cov_inventory.py` → `cov_summary.py`
> 逐文件明细见同目录 `coverage_matrix.tsv`（TSV，含表头，共 1213 行数据）

## 0. 规模

| 指标 | 数值 |
|---|---|
| 文件总数 | **1213** |
| 总字节 | **729653444**（695.9 MB） |
| 含文件的目录数 | 113 |
| 识别出的格式族 | **20** |
| 无扩展名文件 | **150** |
| 可解析 | 608 |
| 部分可解析 | 515 |
| 不可解析 | 90 |

## 1. 按格式族计数（20 族）

| 格式族 | 文件数 | 可解析 | 部分 | 不可 |
|---|---:|---:|---:|---:|
| 无扩展名多群不透明度表(PLANCK/ROSSELAND/EPS/ZEFF) | 237 | 237 | 0 | 0 |
| FEOS辅助(.cst等) | 215 | 90 | 125 | 0 |
| F1 MULTI反演EOS/多群不透明度 | 174 | 99 | 75 | 0 |
| 曲线/常数(.dat/.xml/.txt) | 116 | 0 | 116 | 0 |
| F4 MPQeos .301/.304/.305 | 82 | 0 | 82 | 0 |
| .coldopacity | 67 | 0 | 67 | 0 |
| 记账(MODINFO/FILELIST/LOCK/CHECKSUM) | 53 | 53 | 0 | 0 |
| 非数据 | 52 | 0 | 0 | 52 |
| 配置(.ini/.case) | 45 | 45 | 0 | 0 |
| 幂律.readme | 33 | 33 | 0 | 0 |
| 未识别 | 31 | 0 | 0 | 31 |
| F3 FEOS原生.feos | 29 | 26 | 3 | 0 |
| F5 ATOMIC/LEDCOP/TOPS | 19 | 0 | 19 | 0 |
| F6 IONMIX .cn4/.cnr | 17 | 0 | 17 | 0 |
| F7 SNOP | 12 | 12 | 0 | 0 |
| SESAME .sesame* | 9 | 7 | 2 | 0 |
| 空文件 | 7 | 0 | 0 | 7 |
| 索引(material.base/.user/.list) | 6 | 6 | 0 | 0 |
| .hug | 5 | 0 | 5 | 0 |
| F2 Hyades | 4 | 0 | 4 | 0 |

**族归属说明**：`FEOS辅助(.cst等)` 合并了 `.cst/.mexport/.PAR/.data.txt/.Rho-*.ist/.mnt/.hug 之外的 FEOS 导出`；`无扩展名多群不透明度表` 是文件名无后缀但表头带表号的多群 κ 表；`F1 MULTI反演EOS` 含 `.PLANCK/.ROSS/.EPS/.ZEFF` 带点号形式与 `_ieos/_eos/_mop/_op03*` 形式。

## 2. 按后缀计数（top 45）

| 后缀 | 文件数 |
|---|---:|
| `.dat` | 401 |
| `(无扩展名)` | 150 |
| `.coldopacity` | 67 |
| `.txt` | 53 |
| `.ini` | 43 |
| `.gif` | 30 |
| `.feos` | 29 |
| `.301` | 28 |
| `.304` | 27 |
| `.305` | 27 |
| `.log` | 26 |
| `.par` | 25 |
| `.planck` | 24 |
| `.cst` | 24 |
| `.mexport` | 23 |
| `.ross` | 20 |
| `.zeff` | 15 |
| `.snop` | 12 |
| `.readme` | 11 |
| `.multigroupopacity_planck` | 10 |
| `.multigroupopacity_rosseland` | 10 |
| `.js` | 10 |
| `.avsqfree` | 9 |
| `.grayopacity_planck` | 9 |
| `.grayopacity_rosseland` | 9 |
| `.nofree` | 9 |
| `.cn4` | 9 |
| `.cnr` | 8 |
| `.sesame` | 6 |
| `.info` | 6 |
| `.ist` | 5 |
| `.ist4gnuplot` | 5 |
| `.hug` | 5 |
| `.xlsx` | 4 |
| `.eps` | 4 |
| `.input` | 4 |
| `.list` | 3 |
| `.in` | 3 |
| `.isc` | 3 |
| `.isc4gnuplot` | 3 |
| `.zeff_old` | 3 |
| `.out` | 3 |
| `.xml` | 2 |
| `.base` | 2 |
| `.user` | 2 |

其余后缀（各 <5 个）：`.case`(2), `.inhalt`(2), `.hyades`(2), `.xls`(2), `.5_from_lililing`(2), `.rosseland`(2), `.inv`(2), `.docx`(1), `.bak`(1), `.opj`(1), `.html`(1), `.sesame_planck`(1), `.sesame_rosseland`(1), `.sesame_`(1), `.ise`(1), `.ise4gnuplot`(1), `.mnt`(1), `.mnt4gnuplot`(1), `.tab1`(1), `.tab2`(1), `.db`(1), `.doc`(1), `.data`(1), `.5_mopp95`(1), `.5_mopr95`(1)

## 3. 族 × 解析状态

- **无扩展名多群不透明度表(PLANCK/ROSSELAND/EPS/ZEFF)** — 可解析 237
- **FEOS辅助(.cst等)** — 部分 125, 可解析 90
- **F1 MULTI反演EOS/多群不透明度** — 可解析 99, 部分 75
- **曲线/常数(.dat/.xml/.txt)** — 部分 116
- **F4 MPQeos .301/.304/.305** — 部分 82
- **.coldopacity** — 部分 67
- **记账(MODINFO/FILELIST/LOCK/CHECKSUM)** — 可解析 53
- **非数据** — 不可 52
- **配置(.ini/.case)** — 可解析 45
- **幂律.readme** — 可解析 33
- **未识别** — 不可 31
- **F3 FEOS原生.feos** — 可解析 26, 部分 3
- **F5 ATOMIC/LEDCOP/TOPS** — 部分 19
- **F6 IONMIX .cn4/.cnr** — 部分 17
- **F7 SNOP** — 可解析 12
- **SESAME .sesame*** — 可解析 7, 部分 2
- **空文件** — 不可 7
- **索引(material.base/.user/.list)** — 可解析 6
- **.hug** — 部分 5
- **F2 Hyades** — 部分 4

## 4. 未完成语意识别的文件清单

### 4.1 完全未识别（族 = 未识别，31 个）—— 需人工判定

| 相对路径 | 字节 | 后缀 | 首行片段 |
|---|---:|---|---|
| `Ta2O5/Ta2O5_1G_MULTI` | 19391 | `(无扩展名)` | `0.0000000e+00 1.0000000e+00 2.5000000e+01 4.7000000e+01` |
| `Ta2O5/Ta_1G_MULTI` | 19391 | `(无扩展名)` | `0.0000000e+00 1.0000000e+00 2.5000000e+01 4.7000000e+01` |
| `Thermos/mat_Mo/Mo_Ideal_Gas` | 280 | `(无扩展名)` | `0.1234567E+000 10.22 0.2000000E+001 0.2000000E+001` |
| `Thermos/mat_W/W_Ideal_Gas` | 280 | `(无扩展名)` | `0.1234567E+000 19.3 0.2000000E+001 0.2000000E+001` |
| `XrayMassCoef/XrayMassCoef.tab1` | 4123 | `.tab1` | `Z Element Z/A I(eV) Density(g/cm3)` |
| `XrayMassCoef/XrayMassCoef.tab2` | 5825 | `.tab2` | `Material <Z/A> I Density Composition` |
| `mat_Al-1.0/1041_PLANCK` | 23359 | `(无扩展名)` | `1.1041000e+004 0.70000000E+01 3.1000000e+001 4.6000000e+001` |
| `mat_Al-1.0/1041_ROSS` | 23359 | `(无扩展名)` | `1.0410000e+003 0.40000000E+01 3.1000000e+001 4.6000000e+001` |
| `mat_Al-1.0/AL_LV.INV.data` | 380518 | `.data` | `1.00003010e+07 0.00000000e+00 1.23000000e+02 1.00000000e+02` |
| `mat_Au-1.0/AU_info` | 853 | `(无扩展名)` | `*****************************************************` |
| `mat_Au/Au_Rosseland_2003POPHammerRosen` | 186 | `(无扩展名)` | `0.1234567E+000 0.1234567E+000 0.2000000E+001 0.2000000E+001` |
| `mat_Ba/Ba_1987JQSRT_Planck` | 186 | `(无扩展名)` | `0.1234567E+000 0.1234567E+000 0.2000000E+001 0.2000000E+001` |
| `mat_Ba/Ba_1987JQSRT_Rosseland` | 186 | `(无扩展名)` | `0.1234567E+000 0.1234567E+000 0.2000000E+001 0.2000000E+001` |
| `mat_Ba/Ba_Planck_1987JQSRT` | 186 | `(无扩展名)` | `0.1234567E+000 0.1234567E+000 0.2000000E+001 0.2000000E+001` |
| `mat_Ba/Ba_Rosseland_1987JQSRT` | 186 | `(无扩展名)` | `0.1234567E+000 0.1234567E+000 0.2000000E+001 0.2000000E+001` |
| `mat_Be-1.0/BE_PLANCKx03` | 183 | `(无扩展名)` | `0.00000000e+00 7.00000000e+00 2.00000000e+00 2.00000000e+00` |
| `mat_Be-1.0/BE_SIMPLE_PLANCK` | 183 | `(无扩展名)` | `0.00000000e+00 7.00000000e+00 2.00000000e+00 2.00000000e+00` |
| `mat_C-1.0/C.ZEFF_old` | 6771 | `.zeff_old` | `1 0.60000000E+01 0.20000000E+02 0.20000000E+02` |
| `mat_CELIA/C.ZEFF_old` | 6771 | `.zeff_old` | `1 0.60000000E+01 0.20000000E+02 0.20000000E+02` |
| `mat_CELIA/D.ZEFF_old` | 6771 | `.zeff_old` | `1 0.60000000E+01 0.20000000E+02 0.20000000E+02` |
| `mat_CPC/BE_PLANCKx03` | 183 | `(无扩展名)` | `0.00000000e+00 7.00000000e+00 2.00000000e+00 2.00000000e+00` |
| `mat_Eu/Eu_Planck_1987JQSRT` | 186 | `(无扩展名)` | `0.1234567E+000 0.1234567E+000 0.2000000E+001 0.2000000E+001` |
| `mat_Eu/Eu_Rosseland_1987JQSRT` | 186 | `(无扩展名)` | `0.1234567E+000 0.1234567E+000 0.2000000E+001 0.2000000E+001` |
| `mat_Ge/Ge_2002FED_Planck` | 186 | `(无扩展名)` | `0.1234567E+000 0.1234567E+000 0.2000000E+001 0.2000000E+001` |
| `mat_Ge/Ge_2002FED_Rosseland` | 186 | `(无扩展名)` | `0.1234567E+000 0.1234567E+000 0.2000000E+001 0.2000000E+001` |
| `mat_Ge/Ge_Planck_1999Minguez` | 186 | `(无扩展名)` | `0.1234567E+000 0.1234567E+000 0.2000000E+001 0.2000000E+001` |
| `mat_Ge/Ge_Rosseland_1999Minguez` | 186 | `(无扩展名)` | `0.1234567E+000 0.1234567E+000 0.2000000E+001 0.2000000E+001` |
| `mat_Others/CH10Water1/CH2_H2O_1m1Z` | 30087 | `(无扩展名)` | `3.1315100E+007 0.60000000E+01 3.7000000E+001 5.0000000E+001` |
| `mat_Others/CH10Water2/CH2_H2O_2m1Z` | 30087 | `(无扩展名)` | `3.1315200E+007 0.60000000E+01 3.7000000E+001 5.0000000E+001` |
| `mat_Sn/Sn_Planck_1987JQSRT` | 186 | `(无扩展名)` | `0.1234567E+000 0.1234567E+000 0.2000000E+001 0.2000000E+001` |
| `mat_Sn/Sn_Rosseland_1987JQSRT` | 186 | `(无扩展名)` | `0.1234567E+000 0.1234567E+000 0.2000000E+001 0.2000000E+001` |

### 4.2 空文件（7 个）

- `material.list`
- `HeatCapacity/Electron-Phonon Coupling and Electron Heat Capacity in Metals at High Electron Temperatures`
- `SNOP/### Generated by SNOP`
- `Ta2O5/Ta2O5_1G_MULTI from unknown source`
- `Thermos/___No EOS/No EOS data, but Opacity in OpacityThermos.txt`
- `hyades/sesame/CSi2.5_from_lililing`
- `mat_C-1.0/CSi2.5_from_lililing`

### 4.3 已识别族但解析未完成（状态 = 部分，515 个）

按族分布：

| 格式族 | 部分可解析数 | 主要原因 |
|---|---:|---|
| FEOS辅助(.cst等) | 125 | `.mexport` 多记录块、`.data.txt` 列语义、`.PAR` 非数据卡 |
| 曲线/常数(.dat/.xml/.txt) | 116 | 自由格式曲线/常数，无统一记录结构 |
| F4 MPQeos .301/.304/.305 | 82 | 体区三列归属(T/P/E 顺序)未由物理量独立验证 |
| F1 MULTI反演EOS/多群不透明度 | 75 | `_ieos/_eos/_eosd` 多块结构未闭合；`_mop*` 记录数未定 |
| .coldopacity | 67 | 冷不透明度，记录结构未逆向 |
| F5 ATOMIC/LEDCOP/TOPS | 19 | LEDCOP AvSqFree/NoFree 块结构未逆向 |
| F6 IONMIX .cn4/.cnr | 17 | IONMIX 18/7 块结构未逐块闭合 |
| .hug | 5 | Hugoniot 曲线，格式未定 |
| F2 Hyades | 4 | Hyades 记录序未由闭合确认 |
| F3 FEOS原生.feos | 3 | 3 个文件的表头字段数不足 9 |
| SESAME .sesame* | 2 | `.sesame_PLANCK/ROSSELAND` 是不透明度记录，非 EOS-301 公式 |

### 4.4 非数据文件（52 个，不计入语意识别缺口）

按后缀：`.gif`×30, `.js`×10, `.xlsx`×4, `.xls`×2, `.docx`×1, `.bak`×1, `.opj`×1, `.html`×1, `.db`×1, `.doc`×1

## 5. 诚实缺口说明（8 条）

1. **`.coldopacity`（67 个）结构未逆向**：全部标为「部分」，仅确认其为冷（T=0）不透明度，未确定是几维网格、单位与记录顺序。这是最大的一块未闭合数据。
2. **F4 `.301/.304/.305`（82 个）体区列序未由物理量独立验证**：已确定体区为 `3 + 3·ne + 3·nr` 的三列结构，但三列是 `(T,P,E)` 还是别的顺序，未用独立物理量（如冷压单调性）反证。
3. **`.mexport`（23 个）虽识别但记录块边界未逐块闭合**：仅确认 80 字符行宽与 `line[75:80]` 掩码。
4. **F5 ATOMIC/LEDCOP（19 个）**：`.AvSqFree`/`.NoFree` 两种变体的块结构未逆向。
5. **F6 IONMIX（17 个）**：`.cn4` 18 块 / `.cnr` 7 块，仅识别未逐块闭合。
6. **`.dat`（401 个）中相当一部分是自由格式曲线/常数**，无统一记录结构，只能标记为「曲线/常数」，不宣称已识别具体语义。
7. **31 个完全未识别文件**（见 4.1）多为无扩展名或罕见后缀，需人工或上游文档裁定。
8. **本矩阵的「可解析」仅表示表头/尺寸通过闭合校验**，不等于已完成全部字段的语义标注。
