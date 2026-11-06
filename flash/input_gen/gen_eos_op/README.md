# gen_eos_op — EOS/Opacity 数据生成器与子体系

> 最后核对：2026-11-05 · commit 7e04857 · 维护规则：改动 generator.py 注册表后必须同步 §4 材料表

## 1. 职责定位

管理 FLASH 仿真的 EOS（物态方程）/不透明度数据文件（ionmix4 `.cn4` 格式）：别名感知的表文件查找/复制、辐射能群（grupbd）一致性校验、`.eosmeta.json` 元数据写出。**本目录同时是 EOS/不透明度数据子体系的根**——含 `.cn4` 后处理（eosop_pro）、IONMIX 输入生成（ionmix）、MULTI 格式资料（src），见 §6 导航。

**生成器类型**：数据文件管理器（别名感知，`generator.py` 584 行）
**数据库目录**：`eos_op_data/`（递归扫描，子目录层级无关）

> ⚠️ 设计约束
> - 注册表**只引用实际存在的文件**；磁盘文件不移动、不删除、不重命名；
> - 一个材料可配多个别名，agent 用任意别名精准定位；
> - 未注册文件走**自动发现兜底**（`rglob("*.cn4")`，按 stem 容错命中）。

## 2. 快速上手

```python
from input_gen.gen_eos_op import EOSOpacityGenerator
g = EOSOpacityGenerator()

g.get_eos_file("silicon")                      # 别名/stem/容错形式命中
copied = g.copy_eos_file("ch_mix", "path/to/Simulation")   # 连带写出 .eosmeta.json
g.validate_grupbd_consistency("polystyrene", "silicon")    # 能群一致校验（不可混用）
g.list_available_materials()                   # 已注册且文件在
g.list_discovered_files()                      # 磁盘全部 .cn4（含未注册）
```

## 3. 数据目录现状（2026-11-05 实测）

`eos_op_data/Gen_eos_op_data/` 下 **6 个子目录、10 个 `.cn4`**（原始 FLASH 随包表目录 `FLASH_eos_op_data/` 与 `Others_data/` 已不在本工作区）：

| 子目录 | 内容 |
|---|---|
| `Z02_1.00-20260708_0851/` | 氦（ionmix 生成） |
| `Z06_0.50-Z01_0.50-20260708_0850/` | CH 混合 |
| `Z06_1.00-20260902_2228/` | 碳 |
| `Z14_1.00-20260708_0850/` | 硅 |
| `Z79_1.00-20261009_1256/` | 金（ngrups=10） |
| `badger_qc/` | BADGER-TOPS/QC 五表：He/CH-BADGER-TOPS-Final、CH-QC-1-001、Ti/V-BADGER-TOPS |

## 4. 材料注册表（25 条，2026-11-05 实测可用 9 条）

> 注册表 filename 已于 2026-11-05 与磁盘对齐（badger 系扁平化入 `badger_qc/`、Au 表入时间戳目录）。**注册但文件暂缺**的条目保留在表中（文件就绪即自动恢复可用）。

### 可用（9）

| 规范名 | .cn4 文件（相对 eos_op_data/） | 常用别名 | 说明 |
|---|---|---|---|
| `helium_hires` | `Gen_eos_op_data/Z02_1.00-20260708_0851/…cn4` | z02, helium_gen, 氦高分辨 | 氦，ionmix 生成 |
| `ch_mix` | `Gen_eos_op_data/Z06_0.50-Z01_0.50-20260708_0850/…cn4` | chmix, z06, 碳氢混合物 | C0.5-H0.5 |
| `silicon` | `Gen_eos_op_data/Z14_1.00-20260708_0850/…cn4` | si, z14, 硅 | 硅 Z=14 |
| `au_ionmix10` | `Gen_eos_op_data/Z79_1.00-20261009_1256/…cn4` | z79_1.00, 金高分辨 | 金，ngrups=10 |
| `he_badger` | `Gen_eos_op_data/badger_qc/He-BADGER-TOPS-Final.cn4` | — | He BADGER-TOPS |
| `ch_badger` | `Gen_eos_op_data/badger_qc/CH-BADGER-TOPS-Final.cn4` | — | CH BADGER-TOPS |
| `ch_qc` | `Gen_eos_op_data/badger_qc/CH-QC-1-001.cn4` | — | CH QC |
| `ti_badger` | `Gen_eos_op_data/badger_qc/Ti-BADGER-TOPS.cn4` | — | Ti BADGER-TOPS |
| `v_badger` | `Gen_eos_op_data/badger_qc/V-BADGER-TOPS.cn4` | — | V BADGER-TOPS |

### 注册但文件暂缺（16）

| 规范名 | 期望文件 | 备注 |
|---|---|---|
| `aluminum` / `aluminum_v2` / `helium` / `hydrogen` / `polystyrene` / `beryllium` / `deuterium` / `polystyrene_hi` / `hydrogen_1grp` / `helium_1grp` | `FLASH_eos_op_data/…`（10 条） | FLASH 原始随包表目录已移出本工作区；旧表 ntemp≈16–21 |
| `ch_qc_au` / `ch_qc_t` | `badger_qc/CH-QC-1-001_Au|.cn4`、`…_T.cn4` | 变体表未就绪 |
| `au_ionmix_2026` | `Others_data/Au/Z79_1.00-20261009_1131.cn4` | 1131 时间戳版本不在库 |
| `au_badger` / `au_badger_ch` / `gold_hires` | `Gen_eos_op_data/Au-imx-ForcedRepair[…]/…`、`Au-imx/…` | Au 系其余表未就绪 |

> 未注册但可自动发现：磁盘上全部 10 个 `.cn4`（按 stem/容错形式命中，无语义别名）。

## 5. 辐射能群（grupbd）与规格

全部材料共用：`DEFAULT_GRUPBD = [1e-1 … 1e5] eV`（7 群）。**FLASH 同一算例不同能群不可混用**——`validate_grupbd_consistency(*queries)` 校验；`copy_eos_file` 写出的 `<stem>.eosmeta.json` 内含 grupbd 供 `.par` 装配消费。

当前规格（ionmix 新生成表）：`ntemp=61, dlgtmp=0.105, tplSMA=1e-2 eV, ndens=71, dlgden=0.14, densnn=1e16 cm⁻³`。`verify_against_spec(query)` 对照文件头实际值（不一致仅提示不阻断；BADGER/QC 外来表分辨率不同属正常）。

## 6. 子体系导航（本目录 = 数据子体系根）

```
gen_eos_op/
├── generator.py + gen_eos_op/README.md(本文) + eos_op_data/   ← 表文件管理（本指南）
├── eosop_pro/          matter++ 数据 → 统一解析/网格 → 双轨 HDF5（~60 模块 + 16 篇 docs）
│                       → 详见 eosop_pro/README.md
├── ionmix/ionmix/      IONMIX 输入生成（src/Ionmix_run）+ .cn4 后处理参考实现（eosop_pro/core）
│                       → 详见 ionmix/ionmix/README.md；用户指南 docs/IONMIX用户指南.md(1274 行)
└── src/multi_src/      MULTI 格式历史资料（multi_src/README.md + 03_anchors 锚点库）
```

数据流转：`ionmix`（生成 .cn4）→ `eos_op_data/`（注册/复制）→ `eosop_pro`（解析/网格/HDF5）→ 场景 `.par` 装配消费 `.eosmeta.json`。

## 7. 新材料接入

- **方式 A（零代码）**：`.cn4` 丢进 `eos_op_data/` 任意子目录，立即按 stem 可查（无语义别名）；
- **方式 B（推荐）**：`generator.py` 的 `EOSMaterial` 列表追加一条（canonical/filename/aliases/description），保存即用任意别名精准定位。

命名约定：FLASH 原始表→`FLASH_eos_op_data/`（如恢复）、ionmix 生成表→`Gen_eos_op_data/`（带时间戳 `Zxx_1.00-YYYYMMDD_HHMM`）、外来格式（BADGER/QC）→`badger_qc/`；同元素不同分辨率注册不同规范名（`helium` vs `helium_hires`）。

## 8. API 速查

| 方法 | 作用 |
|---|---|
| `get_eos_file(query)` | 别名/stem/容错查找 → Path |
| `copy_eos_file(query, target_dir, write_meta=True)` | 复制 + 写 `.eosmeta.json` |
| `get_material_config(query)` | 完整配置（别名/文件/grupbd/规格/可用性） |
| `list_available_materials()` / `list_all_materials()` / `list_discovered_files()` | 可用注册 / 全部注册 / 磁盘全量 |
| `verify_against_spec(query)` | 文件头 vs 规格对照 |
| `validate_grupbd_consistency(*queries)` | 能群一致性（不可混用） |

## 9. 导航

上级：[../README.md](../README.md)（input_gen） · 子体系：[eosop_pro/README.md](eosop_pro/README.md)、[ionmix/ionmix/README.md](ionmix/ionmix/README.md)、[src/multi_src/README.md](src/multi_src/README.md)

---
**文档版本**: 3.0（注册表与磁盘对齐实测重写；子体系导航补全）
**最后核对**: 2026-11-05 · **维护**: PhySimX Team
