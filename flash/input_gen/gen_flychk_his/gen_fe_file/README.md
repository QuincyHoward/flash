# gen_fe_file — FLYCHK 非麦克斯韦电子分布 `fe` 文件生成器

> 最后核对：2026-11-18
> **版本**: 0.1.0 · **依赖**: 仅标准库（自包含，与 `zip_writer.py` 同纪律）

生成 FLYCHK 关键字 `fe file <filename>` 所需的**非麦克斯韦电子能量分布函数**（EEDF/beam）数据文件，与背景热电子（Maxwellian，由主输入 te/ne 给出）叠加计算能级布居与电离速率。

## 目录

- [快速开始](#快速开始)
- [两种输入模式](#两种输入模式)
- [fe 文件格式契约（勿改）](#fe-文件格式契约勿改)
- [zip 集成](#zip-集成)
- [解析模型与归一化](#解析模型与归一化)
- [校验清单](#校验清单)
- [测试](#测试)
- [FAQ](#faq)

## 快速开始

```python
from flash.input_gen.gen_flychk_his.gen_fe_file import (
    FeModel, build_fe_file, write_history_zip_with_fe)

# 模式一：解析模型（麦克斯韦束 Te=1keV，两个时间步）
fe = build_fe_file(
    FeModel(te_beam=1000.0, beam_density=1e11, times=[0.0, 1e-9]),
    energies=[500.0, 1000.0, 2000.0, 5000.0],   # eV, 升序, <=500 点
    comment="maxwellian beam Te=1keV",
)
print(fe.to_text())          # fe 数据文件文本
fe.report.summary()          # 校验结论 ("OK" / "N error(s)，M warning(s)")

# 并入 FLYCHK history 模式 zip（runfile 增加 `fe file <名>` 行, zip 第三成员）
write_history_zip_with_fe(table, fe, "out/history_Ti_Z22_fe.zip")
```

```python
# 模式二：显式数组（用户自己提供分布数据）
from flash.input_gen.gen_flychk_his.gen_fe_file import FeExplicitSeries, build_fe_file

fe = build_fe_file(FeExplicitSeries(
    energies=[4490.0, 4500.0, 4510.0],                       # eV
    records=[                                                # (time[s], 束密度[#/cm^3], fe(E))
        (0.0,   1e11, [1e-20, 1.49071e-03, 1e-20]),
        (1e-9,  1e11, [1e-20, 1.49071e-03, 1e-20]),
    ],
))
```

命令行（自检）：

```bash
python flash/input_gen/gen_flychk_his/gen_fe_file/test/run_test.py   # 端到端 S1~S6
python -m pytest flash/input_gen/gen_flychk_his/gen_fe_file/test -q  # 全量测试
```

## 两种输入模式

| 模式 | 输入对象 | 适用场景 |
|---|---|---|
| 解析模型 | `FeModel(te_beam, beam_density, times, densities, model, ...)` | 麦克斯韦束 / 漂移麦克斯韦 / 单能束，自动生成 fe 值 |
| 显式数组 | `FeExplicitSeries(energies, records)` | 用户直接提供 (time, density, fe(E)) 数据 |

`FeModel` 字段：

| 字段 | 单位 | 说明 |
|---|---|---|
| `te_beam` | eV | 束电子温度，>0 必填 |
| `beam_density` | #/cm³ | 常数束密度（`densities=None` 时用） |
| `times` | s | 时间步序列；空 → 单时间点 t=0 |
| `densities` | #/cm³ | 逐时间点束密度；None → 常数；长度须等于 times |
| `model` | - | `maxwell`（默认）/ `drift_maxwell` / `mono` |
| `drift_energy` / `mono_energy` / `mono_width` | eV | 可选模型参数 |
| `normalize_to_density` | - | True：按梯形积分重标定到 n_beam（网格积分精确相等） |

## fe 文件格式契约（勿改）

依据 NIST FLYCHK fe help 官方文档：

```
c 注释行（以 c 或 # 开头被 FLYCHK 忽略）
2 3                          <- 第1行: 时间步数 能量网格数
4.49E+03 4.50E+03 4.51E+03   <- 第2行: 能量网格[eV], 只写一次
0.0E+00 1.0E+11              <- time[s] 与 束电子密度[#/cm^3] 同一行！
1.0E-20 1.49071E-03 1.0E-20  <- 该时间步 fe(E), 折行<=120字符
1.0E-09 1.0E+11              <- 第2个时间步（时间与密度同行）
1.0E-20 1.49071E-03 1.0E-20
```

| 约束 | 值 | 说明 |
|---|---|---|
| 能量网格点上限 | 500 | 超出为硬错误 |
| 每行字符上限 | 120 | 渲染时自动折行（自由格式按空白分词，折行安全） |
| 分布定义 | n(E)dE = sqrt(E)·fe(E)·dE | fe(E) 官方标注 `#/cm³/eV^0.5`；量纲推导为 `#/cm³/eV^1.5`（文件只含数值，不受标注影响） |
| 麦克斯韦束 | fe(E) = 2/sqrt(π)·exp(-E/Te)/Te^1.5 | 解析归一：∫√E·fe dE = n_beam |
| 首时间点 | 允许 t=0 | 与 history 数据文件的时间约束不同（官方示例 0.0E+00） |
| 数值格式 | `%.6e` | 与 history 数据文件一致 |

## zip 集成

含 fe 的 zip 成员顺序固定（FLYCHK 按成员名取文件，物理顺序不影响解析，固定仅为可测性）：

```
runfile.txt
history_{element}_Z{z}_input.txt
fe_{element}_Z{z}_input.txt          <- 第三成员
```

runfile 变化（`render_runfile(..., fe_filename=...)`）：

```
z 22
initial ss
evolve ss
history
[opacity file]      <- 仅当 size 列
[ti file]           <- 仅当 ti 列
[tr file]           <- 仅当 tr 列
[fhot file]         <- 仅当 fhot/thot 列
fe file fe_Ti_Z22_input.txt     <- 新增行：文件类关键字之后、history 数据行之前
history history_Ti_Z22_input.txt rho
end
```

- `HistoryZipWriter.write/generate_history_zip/verify_zip` 均追加可选参数 `fe_text`/`fe_filename`（必须成对给出）；`fe=None` 路径与旧版逐字节相同（向后兼容）。
- 基础契约 `FORMAT_CONTRACT_ID = "flychk-history-v1"` 不变；含 fe 时 `verify_zip` 追加 `fe_contract = "flychk-history-fe-v1"` 与 fe 成员存在性/内容/runfile 行三项检查。
- `zip_writer` 只接收原始字符串，`FeFile → 文本` 转换由本子包桥接函数 `write_history_zip_with_fe` 完成（禁止反向依赖）。

## 解析模型与归一化

| 模型 | fe(E) | 归一方式 |
|---|---|---|
| `maxwell` | 2/sqrt(π)·exp(-E/Te)/Te^1.5 | 解析（∫√E·fe dE = 1） |
| `drift_maxwell` | E≤E0 为 0；E>E0 为 exp(-(E-E0)/Te) | 数值（网格积分标定到 1） |
| `mono` | 以 E0 为中心、width 为 σ 的高斯 | 数值（网格积分标定到 1） |

归一偏差检查：对最终记录做梯形积分 ∫√E·fe dE，与束密度比较；偏差 >5% 记 warning（能量网格过粗或覆盖不足，建议覆盖 0~10·Te 并在 E~Te 处加密）。`normalize_to_density=True` 时按梯形估计等比重标定，使网格积分精确等于 n_beam（写入 `meta["normalize_to_density"]`）。

## 校验清单

**error**（`build_fe_file` 抛 `ConfigError`）：

- 能量点数 > 500 / 网格非严格升序 / 含 ≤0 或 NaN
- fe 值 < 0 或 NaN / fe 数组长度 ≠ 能量点数
- 时间步重复（须严格递增）/ records 为空
- `te_beam` ≤ 0 / 未知 model（模型模式下负束密度会产生负 fe，同样为 error）

**warning**（不阻断）：

- 束密度 = 0（束关闭可能是合法物理）
- 归一偏差 > 5%

校验容器复用父包 `config.ValidationReport`；`fe.report.ok` 判断、`fe.report.warnings` 读取。

## 测试

```bash
python -m pytest flash/input_gen/gen_flychk_his/gen_fe_file/test -q
python flash/input_gen/gen_flychk_his/gen_fe_file/test/run_test.py          # S1~S6 + out/REPORT.md
python flash/input_gen/gen_flychk_his/test/verify_decoupled.py              # 解耦证明
```

用例矩阵见 `test/README.md`。

## FAQ

**Q1: 为什么不做 grid 模式（`history grid ne` / EBIT 风格）？**
flash-sim 包内只使用 history 数据文件模式（FLASH 1D 剖面时间序列）。不写 grid 代码避免误用；如需 EBIT 风格主输入请手工构造 runfile 并复用本子包生成 fe 数据文件。

**Q2: 时间和束密度到底同一行还是分行？**
官方示例明确**同一行**（`0.0E+00 1.0E+11`），fe(E) 值单独一行。注意与部分二手资料（称须分三行）区分。

**Q3: fe(E) 单位是 eV^-0.5 还是 eV^-1.5？**
官方表头写 `#/cm³/eV^0.5`；按 n(E)dE = sqrt(E)·fe(E)·dE 推导量纲为 `#/cm³/eV^1.5`。文件只含数值，本模块文档按官方标注并保留推导说明。

**Q4: 归一偏差告警一定代表错吗？**
不一定。粗网格（尤其 500 点极限下宽能量域）必然有梯形离散误差；确认网格覆盖 0~10·Te 且 E~Te 处足够密即可，或用 `normalize_to_density=True` 强制精确归一。

**Q5: 如何只生成 fe 文本文件、不碰 zip？**
`build_fe_file(...)` 后直接 `fe.to_text()` 并自行写盘（`encoding="utf-8", newline="\n"`）。
