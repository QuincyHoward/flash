---
name: flash-eos-op
description: FLASH EOS/不透明度数据子体系：gen_eos_op 表文件管理与 eosop_pro 解析/转换/绘图。处理 .cn4/.cnr IONMIX 文件（格式判据、计数式校验、E12.6 指数溢出修复）、grupbd 能群一致性、材料注册、uk/uv 标记、绘图规约、表分发 gitignore 策略时使用。触发词：EOS、不透明度、cn4、cnr、ionmix、eosop_pro、物态方程、grupbd、eosmeta、E12.6、材料表。
---

> 最后核对：2026-11-06 · commit 72f6428

# EOS/不透明度数据子体系（gen_eos_op + eosop_pro）

权威参考：
- `flash/input_gen/gen_eos_op/GEN_EOS_OP_GUIDE.md` — 表文件管理指南（材料注册表）
- `flash/input_gen/gen_eos_op/eosop_pro/README.md` — 解析/网格/双轨 HDF5 子包
- `flash/input_gen/gen_eos_op/ionmix/ionmix/README.md` — IONMIX 输入生成

## 1. 目录结构（数据子体系根 = gen_eos_op）

```
flash/input_gen/gen_eos_op/
├── generator.py + GEN_EOS_OP_GUIDE.md + eos_op_data/   ← 表文件管理（别名感知）
├── eosop_pro/          解析/网格/转换/绘图（~60 模块）
├── ionmix/ionmix/      IONMIX 输入生成 + .cn4 后处理参考实现
└── src/multi_src/      MULTI 格式历史资料（含 04_probe 权威记录）
```

数据流转：`ionmix`（生成 .cn4）→ `eos_op_data/`（注册/复制）→ `eosop_pro`（解析/HDF5）→ 场景 `.par` 装配消费 `.eosmeta.json`。

## 2. .cn4 / .cnr 格式判据（最易错）

| 格式 | 识别特征 | 块数 |
|---|---|---|
| `.cn4` | `isw21 != 0` | 18 块，含 EOS |
| `.cnr` | `isw8 = 1/12/13` | 7 块，无 EOS |

**判据**：头部第 4 行能否 `int()`。计数式校验（cn4）：

```
ntemp + ndens + 12*ntemp*ndens + (ngrups+1) + 3*ngrups*ntemp*ndens
```

**⚠️ Fortran E12.6 指数溢出坑**：三位指数会吞掉 `E`，读数前必须修复：

```python
re.sub(r"(\d\.\d{6})([-+]\d{3})", r"\1E\2", text)
```

**单位陷阱**：ionmix 密度轴 = cm⁻³ 数密度（`<A>` 取同目录 ionmxinp）；LEDCOP 温度 keV；ionmix P/E = J/cm³、J/g；Hyades CGS。`.cnr` 不能转 `.cn4`；`.feos` 的 NR/NT 比真实值多 1。

## 3. 表文件管理 API（EOSOpacityGenerator）

```python
from input_gen.gen_eos_op import EOSOpacityGenerator
g = EOSOpacityGenerator()
g.get_eos_file("silicon")                    # 别名/stem/容错查找 → Path
g.copy_eos_file("ch_mix", target_dir)        # 复制 + 写 <stem>.eosmeta.json
g.validate_grupbd_consistency("a", "b")      # 能群一致校验（不可混用）
g.list_available_materials()                 # 已注册且文件在盘
g.list_discovered_files()                    # 磁盘全部 .cn4（含未注册兜底）
```

护栏：注册表**只引用实际存在的文件**；磁盘文件不移动、不删除、不重命名；未注册文件走 `rglob("*.cn4")` 自动发现兜底。新材料接入推荐在 `generator.py` 的 `EOSMaterial` 列表追加一条（canonical/filename/aliases/description）。命名约定：ionmix 生成表 → `Gen_eos_op_data/Zxx_1.00-YYYYMMDD_HHMM/`，外来格式（BADGER/QC）→ `badger_qc/`。

## 4. 能群（grupbd）一致性

全部材料共用 `DEFAULT_GRUPBD = [1e-1 … 1e5] eV`（7 群）。**同一算例不同能群不可混用**——`validate_grupbd_consistency(*queries)` 强制校验；`copy_eos_file` 写出的 `.eosmeta.json` 内含 grupbd 供 `.par` 装配消费。ionmix 新生成表规格：`ntemp=61, dlgtmp=0.105, tplSMA=1e-2 eV, ndens=71, dlgden=0.14, densnn=1e16 cm⁻³`；`verify_against_spec(query)` 对照文件头实际值（不一致仅提示不阻断，BADGER/QC 外来表分辨率不同属正常）。

## 5. 表分发与 gitignore 策略

| 目录 | 性质 | 分发策略 |
|---|---|---|
| `Gen_eos_op_data/`（含 `Z*.cn4` 自研表） | 自研/ionmix 生成 | **随包分发**，必须包含在发布包 |
| `FLASH_eos_op_data/` | FLASH 版权表 | **默认不分发**（License §3），gitignore 排除；用户自行获取 |
| `badger_qc/` | 外来格式 | 按来源约定 |

依赖 FLASH 分发表的测试需 `pytest.skip`。已跟踪的大文件改 gitignore 无效，需 `git rm --cached`；`!` 例外规则必须写在被覆盖规则之后。

## 6. uk/uv 标记与控制字典（registry/field_checks.py 唯一权威）

- 标记只有 **uk（无来源）/ uv（未核查）**；有源且已核查整体省略；`tags_label` 统一出口，图上标签 = `Name (unit, <tags>)`
- `kind` 六值词表：declaration/document/code/measured/derived/none；source 只引一级出处，**禁引 _P20**（守卫强制）
- 再生成字典 md：`python -m eosop_pro.registry.field_checks`（**须在 eosop_pro/ 包根运行**；实现位于 `eosop_pro/eosop_pro/registry/field_checks.py`）；守护测试 `test_field_checks.py`
- 遗留：ledcop_zeff 字段 Z/Z2 vs 字典 NoFree/AvSqFree（运行时 `*` 兜底）

## 7. 绘图规约

- `plotting/labels.py` = 标签唯一出口；`FAMILY_ALIASES = {"cn4": "ionmix"}`；Te/tele → T；兜底命中（key=None）回退字段名；零缓存
- **散点规约**：tags 非空 → 散点 `lw=0`；路径图保留连线
- **数值格式**：图上数值一律 `:.1e`（含量纲 1 系数）；console/报告/文件名/异常/原子量 A 除外
- `gridmap.plot_table_all_fields` 任意族统一入口；`PLOT_LEGEND_FONTSIZE=20`（严格 >18）；DPI=450 全 ASCII PPT 级

## 8. 护栏

- eosop_pro 测试入口 `eosop_pro/test/run_all.py`（递归发现 test_*.py）；解释器必须用工作区 venv（含 numpy/h5py/matplotlib/scipy）
- 全套测试约 4.5 min，后台跑，日志落临时目录（不落 test/ 内）；figure 显式 close；产物落 `<测试文件夹>/_out/`
- 换行铁律：`*.py`/`*.sh` = LF；科学数据 `-text`；禁用 MSYS `sed -i`；同文件多次 Edit 必须串行

## 关联资源

- `flash/input_gen/gen_eos_op/GEN_EOS_OP_GUIDE.md`（材料注册表与 API 速查）
- `flash/input_gen/gen_eos_op/eosop_pro/README.md`（解析/转换子包）
- `flash/input_gen/gen_eos_op/ionmix/ionmix/README.md`、`flash/input_gen/gen_eos_op/ionmix/ionmix/docs/IONMIX用户指南.md`
- skill `flash-par-gen`（.par 装配消费 .eosmeta.json）
