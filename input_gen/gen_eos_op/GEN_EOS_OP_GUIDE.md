# gen_eos_op — EOS/Opacity 数据生成器说明文档

## 概述

`gen_eos_op` 子包用于管理 FLASH 仿真的 EOS（方程状态）和不透明度数据文件（`.cn4`
格式，ionmix4）。这些文件包含材料的温度-密度相关物理属性。

**生成器类型**: 数据文件管理器（别名感知）
**数据库目录**: `gen_eos_op/eos_op_data/`（递归扫描，子目录亦支持）
**支持格式**: ionmix4 (`.cn4`)

> ⚠️ 设计约束
> - 注册表 **只引用实际存在的文件**；脚本不再包含指向不存在文件的条目。
> - 磁盘文件 **不移动、不删除、不重命名**，后续可直接往 `eos_op_data/` 追加新 `.cn4`（含新子目录）。
> - 一个 eos_op 可配置 **多个别名**，agent 用任意别名即可精准定位文件。
> - 重写后注册表共 13 条材料；另有 `matr_009999(.ses).cn4` 为非标准 ionmix 头，不注册，仅走自动发现。

## 目录结构约定

`eos_op_data/` 当前分两类子目录（仅为组织约定，agent 扫描时 **不区分层级**）：

| 子目录 | 内容 | 来源 |
|--------|------|------|
| `FLASH_eos_op_data/` | `al-imx-003/004`、`he-imx-005`、`he-imx-1grp`、`h-imx-1grp`、`polystyrene-imx-001`(纯氢)/`002`(CH 1:1)/`008`(CH 高分辨)、`Be-006-imx`、`DD-006-imx`、`matr_009999(.ses)` | FLASH 随包原始表（分辨率较低, ntemp≈16–51） |
| `Gen_eos_op_data/` | `Z02_1.00`(氦)、`Z06_0.50-Z01_0.50`(CH混)、`Z14_1.00`(硅) | ionmix 新生成表（ntemp=61，匹配当前规格） |

> 新表可按元素/项目自建子目录（如 `MyElement/`），只要最终落在一个 `.cn4` 文件即可。

## 辐射能群边界 (grupbd)

当前所有材料共用同一组辐射能群边界（单位 eV）：

```python
DEFAULT_GRUPBD = [1.0e-1, 1.0e+0, 1.0e+01, 1.0e+02, 1.0e+03, 1.0e+04, 1.0e+05]
```

**约束**：FLASH 同一算例中 **不同能群不能混用**。引用多个材料时，它们必须共享相同
`grupbd`，可用 `validate_grupbd_consistency(...)` 校验。`copy_eos_file` 写出的
`<stem>.eosmeta.json` 内含 `grupbd`，供 agent 装配 `.par` 时消费。

## 材料规格 (辅助确认文件信息)

每个材料携带一组规格参数，用于对照/确认 `.cn4` 文件信息（非强制匹配，仅作参考）：

| 参数 | 值 | 含义 |
|------|----|------|
| `ntemp` | 61 | 温度点数 |
| `dlgtmp` | 0.105 | 温度对数增量 |
| `tplsma` | {1: 1e-2} | 起始温度 [eV]（索引 1） |
| `ndens` | 71 | 密度点数 |
| `dlgden` | 0.14 | 密度对数增量 |
| `densnn` | 1.0e16 | 起始离子数密度 [cm⁻³] |
| `trad` | 200.0 | 辐射温度 [eV] |

`verify_against_spec(query)` 会将 `.cn4` 文件头的实际 `ntemp/ndens` 与规格对照，
返回是否一致（不一致仅作提示，不阻断复制）。注：FLASH 原始表分辨率（ntemp≈21）低于
当前规格（61），属正常历史数据，`verify_against_spec` 会标注但不报错。

## 材料注册表（含别名）

| 规范名 | .cn4 文件（相对 eos_op_data/） | 别名 | 说明 |
|--------|-------------------------------|------|------|
| `aluminum` | `FLASH_eos_op_data/al-imx-003.cn4` | aluminum, aluminium, al, 铝, al-imx-003 | 铝 Z=13，ntemp=21 |
| `helium` | `FLASH_eos_op_data/he-imx-005.cn4` | helium, he, 氦, he-imx-005 | 氦 Z=2，ntemp=21 |
| `hydrogen` | `FLASH_eos_op_data/polystyrene-imx-001.cn4` | hydrogen, h, 氢, polystyrene-imx-001 | **文件名误导**，内容实为纯氢 Z=1（占比 1.0/0.0），ntemp=21 |
| `polystyrene` | `FLASH_eos_op_data/polystyrene-imx-002.cn4` | polystyrene, ps, 聚苯乙烯, ch, CH靶, polystyrene-imx-002 | 聚苯乙烯/CH 靶 (H0.5-C0.5)，ntemp=21 |
| `beryllium` | `FLASH_eos_op_data/Be-006-imx.cn4` | beryllium, be, 铍, Be-006-imx | 铍 Z=4，ntemp=21（原 phantom，现已真实存在） |
| `deuterium` | `FLASH_eos_op_data/DD-006-imx.cn4` | deuterium, dd, 氘, 重氢, DD-006-imx | 氘氢混合物 (H+D 各50%)，ntemp=21 |
| `helium_hires` | `Gen_eos_op_data/Z02_1.00-20260708_0851/Z02_1.00-20260708_0851.cn4` | z02, z02_1.00, helium_gen, helium_hires, 氦_生成, 氦高分辨 | 氦 Z=2，ionmix 新生成表 ntemp=51（2026-07-08 重新生成，与 `helium` 同元素不同分辨率） |
| `ch_mix` | `Gen_eos_op_data/Z06_0.50-Z01_0.50-20260708_0850/Z06_0.50-Z01_0.50-20260708_0850.cn4` | ch_mix, chmix, 碳氢混合物, 碳氢混合物高分辨, z06 | C0.5-H0.5，新生成表 ntemp=51（2026-07-08 重新生成） |
| `silicon` | `Gen_eos_op_data/Z14_1.00-20260708_0850/Z14_1.00-20260708_0850.cn4` | silicon, si, 硅, z14 | 硅 Z=14，新生成表 ntemp=51（2026-07-08 重新生成） |
| `aluminum_v2` | `FLASH_eos_op_data/al-imx-004.cn4` | al-imx-004, al004, al-v2 | 铝 Z=13 另一版本，ntemp=21 |
| `polystyrene_hi` | `FLASH_eos_op_data/polystyrene-imx-008.cn4` | polystyrene-imx-008, polystyrene-008, ch-hi, ps-hi | CH 早期高分辨表，ntemp=51 |
| `hydrogen_1grp` | `FLASH_eos_op_data/h-imx-1grp.cn4` | h-imx-1grp, h-1grp, 氢单能群 | 氢 Z=1 单能群版，ntemp=17 |
| `helium_1grp` | `FLASH_eos_op_data/he-imx-1grp.cn4` | he-imx-1grp, he-1grp, 氦单能群 | 氦 Z=2 单能群版，ntemp=16 |

> 未注册但可被发现：`matr_009999.cn4` / `matr_009999.ses.cn4`（非标准 ionmix 头，
> 第 1 行非 ntemp/ndens），仅能按文件名自动发现，不纳入语义别名。

> 已移除原 phantom 条目：`gold`(au-imx-003)、`copper`(cu-imx-003)、
> `carbon`(c-imx-003) —— 它们的 `.cn4` 文件并不存在，待对应文件就绪后重新加入即可。
> 注意 `beryllium` 之前也是 phantom，但 `Be-006-imx.cn4` 现已真实存在，已重新注册。

## 如何让 AI agent 知道新文件 / 文件夹

`eos_op_data/` 对 agent 是**透明递归扫描**的：`EOSOpacityGenerator` 在初始化时执行
`eos_op_data.rglob("*.cn4")`，因此新增文件**无需改代码即可被找到**（自动发现兜底）。

接入新材料的两种方式：

### 方式 A：只要求"能找到并复制"（零代码，靠自动发现）

把 `.cn4` 丢进 `eos_op_data/` 的 **任意子目录**（如 `Gen_eos_op_data/`、`MyNew/`），
agent 立即可用其 **文件名或文件名 stem（容错）** 定位：

```python
from input_gen.gen_eos_op import EOSOpacityGenerator
g = EOSOpacityGenerator()

g.get_eos_file("Z02_1.00-20260708_0851")     # 按 stem 命中（去 .cn4）
g.get_eos_file("DD-006-imx")                 # 按 stem 命中
g.get_eos_file("dd006imx")                   # 容错：去 -/_ 后一致也命中
```

此时文件被当作"未注册"材料，自动套用默认 `grupbd` 与 `spec`。若它确按当前规格
（ntemp=61）生成，`verify_against_spec` 会通过。
**缺点**：无语义别名（中文/元素符号），agent 只能靠文件名猜。重要材料建议走方式 B。

### 方式 B：希望有友好别名 + 确认规格（推荐）

在 `generator.py` 的 `EOSMaterial` 列表（`MATERIALS`）追加一条：

```python
EOSMaterial(
    canonical="gold",                                       # 规范名（英文）
    filename="Gen_eos_op_data/au-imx-001.cn4",              # 相对 eos_op_data 的路径（可含子目录）
    aliases=["gold", "au", "金", "au-imx-001", "auimx001"], # 任意别名（含容错形式）
    description="金 (Au, Z=79)",
    # grupbd / spec 省略则继承 DEFAULT_GRUPBD / DEFAULT_SPEC
),
```

保存后 agent 即可用 `gold` / `au` / `金` 等任意别名精准定位；`copy_eos_file` 会连带
写出 `<stem>.eosmeta.json`（含 `grupbd` + `spec`）。

### 验证与排查（让 agent 自检）

```python
g.list_discovered_files()        # 磁盘上所有 .cn4（含未注册），确认新文件被扫到
g.list_available_materials()      # 已注册且文件存在的材料
g.verify_against_spec("<查询>")   # 对照实际文件头与规格
g.validate_grupbd_consistency("helium", "silicon")  # 校验能群一致（不同能群不可混用）
```

### 约定建议（便于 agent 自动发现 + 避免别名冲突）

- FLASH 随包原始表 → `FLASH_eos_op_data/`
- ionmix 新生成表 → `Gen_eos_op_data/`（或按元素/项目自建子目录）
- 文件名以 **元素符号** 或 **Zxx** 开头：`al-`、`he-`、`Be-`、`Z06_...`、`Z14_...`
- 同元素不同分辨率/版本用后缀区分：`-imx-003` / `-imx-004` / `-1grp`
- ionmix 新生成表建议带时间戳：`Z02_1.00-20260708_0851`（避免重名）
- 同一元素不同分辨率 → 注册为不同规范名（如 `helium` vs `helium_hires`），避免别名冲突

## gen_eos_op 生成器 API

### 类: EOSOpacityGenerator

**位置**: `gen_eos_op/generator.py`

### 主要方法

#### get_eos_file(query)

按别名/文件名精准查找材料的 EOS 文件路径。支持规范名、元素符号、中文、文件名
stem 及其容错形式（如 `al` / `Al` / `铝` / `al-imx-003` / `alimx003` 均命中）。

```python
path = generator.get_eos_file("aluminum")      # 或 "al" / "铝" / "al-imx-003"
```

#### copy_eos_file(query, target_dir, write_meta=True)

复制 EOS 文件到目标目录；默认额外写出 `<stem>.eosmeta.json`，内含 `grupbd` 与规格参数，
供仿真装配（.par）与 agent 确认。

```python
copied = generator.copy_eos_file("ch_mix", "path/to/Simulation")
```

#### get_material_config(query)

返回材料完整配置（别名、文件名、grupbd、规格、可用性），用于写入辐射能群等参数。

#### list_available_materials() / list_all_materials() / list_discovered_files()

- `list_available_materials()`: 实际可用的已注册材料规范名。
- `list_all_materials()`: 所有已注册材料（含文件暂缺）。
- `list_discovered_files()`: 磁盘上发现的所有 `.cn4` 相对路径（含未注册文件）。

#### verify_against_spec(query)

将 `.cn4` 头实际 `ntemp/ndens` 与规格对照，返回一致性报告。

#### validate_grupbd_consistency(*queries)

校验多个材料是否共用相同 `grupbd`（FLASH 约束：不同能群不可混用）。

## 使用示例

### 示例 1: 为仿真准备 EOS 文件（agent 复制）

```python
from input_gen.gen_eos_op import EOSOpacityGenerator
from pathlib import Path

generator = EOSOpacityGenerator()
sim_dir = Path("path/to/Simulation")

generator.copy_eos_file("polystyrene", sim_dir)   # 规范名 → polystyrene-imx-002.cn4
generator.copy_eos_file("氦", sim_dir)            # 中文别名
generator.copy_eos_file("ch_mix", sim_dir)        # 碳氢混合物 (高分辨率)
generator.copy_eos_file("z02", sim_dir)           # ionmix 新生成氦高分辨
generator.copy_eos_file("beryllium", sim_dir)     # 铍 (新注册)

print("EOS files copied; grupbd written to .eosmeta.json")
```

### 示例 2: 校验辐射能群一致性

```python
res = generator.validate_grupbd_consistency("polystyrene", "silicon", "helium_hires")
assert res["consistent"], f"能群冲突: {res['conflicting']}"
```

## 参考资料

1. FLASH User Guide - Equation of State
2. IONMIX4 format documentation

---

**文档版本**: 2.2
**最后更新**: 2026-07-07
**维护**: PhySimX Team
