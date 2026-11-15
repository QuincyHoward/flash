> 最后核对：2026-11-15 · commit ba2981e（其后含功能树重组，代码为准）

# convert/ —— 跨格式转换层：read(A) -> ParsedTable -> write(B) 的统一入口

> **转换公式与算法口径的逐条详解**（轴适配/单位链/正演反演/反演/越界策略/数值验证）：
> 见 [转换公式详解.md](转换公式详解.md)。本文只讲 API 与注册表。

上层依赖：`pipeline/cli`（`targets` 子命令）与用户脚本经 `eosop_pro.convert` 导入本层。本层依赖 `parsers/base`（ParsedTable）、`parsers/cn4_io`（cn4 组装与写出）、`grid/unified_grid`、`writer/h5_writer`（h5 目标）。设计核心：解析器统一读成 ParsedTable、写出器统一实现 `write(table, out_path, **opts) -> Path`，任意两族互转**不需要 N×N 个转换器**。导入本包（`__init__.py`）即完成全部目标写出器注册。

## 模块

### __init__.py —— 导出面 + 目标注册
导入即注册 5 个目标：`cn4`（**默认目标** DEFAULT_TARGET）、`multi_opacity`、`hyades_eos`、`multi_inverted_eos`、`h5`。每个目标带 `requires`（KIND 门控）/ `requires_fields` / `requires_axes`，缺场或缺轴时跳过并给说明，不写坏文件。

关键 API（`__all__` 导出面）：
- `convert(table, out_path, target=None, **opts) -> Path` —— 单表转换；`target=None` 走默认 cn4
- `convert_tables(tables, outdir, target=None, *, on_skip="collect") -> (paths, skipped)` —— 批量
- `get_target(name) -> ConvertTarget` —— 查注册表（未知名抛 KeyError）
- `list_targets() -> list[ConvertTarget]` —— 列出全部已注册目标
- `REGISTRY: dict[str, ConvertTarget]` —— 注册表本体；`register(target)` 注册新目标
- `get_default_target() / set_default_target(name) -> str` —— 查看/全局改默认目标
- `write_h5_single(table, out_path, *, unified=True, native=True)` —— 单表 h5（双轨）

### base.py —— 注册表与转换接口
`ConvertTarget` 数据类（name/description/writer/requires/requires_fields/requires_axes/notes/examples）与 `can_write(table) -> (bool, why)` 门控；`convert()` 在写出前校验 KIND/场/轴，`skip_axes_check=True` 配合写出器的 `invert=True`（F1 源表无 Te 轴属正常）。已注册目标的权威参考：F2 ← `matlab/outputMULTIOpacity.m`（`%15.7e`×4、log10、keV→eV×1000）、F3 ← `matlab/outputHyadesEOS.m`（`%15.8e`×5、T keV）、F1 ← 解析器 + `doc/MULTI使用的SESAME数据文件格式.docx`。

### invert_eos.py —— F1 的 (rho, de) → (rho, Te) 反演
F1 存的是 P(rho, de)/T(rho, de)，要做 (rho, Te) 统一网格必须对每个密度列在 (log10 T, log10 de) 空间一维插值求 `de*(Te)`，再取 P/E。超出该列温度范围的目标点 → NaN（不静默外插）。

关键 API：
- `is_de_based(table) -> bool` —— 判断表是否以 `de` 为自变量（F1 特征）
- `to_Te_grid(table, Te_targets, *, fields=("P","E","T"), log_value=("P",)) -> InversionResult`
- `InversionResult` —— `Te/rho/fields`（name -> (n_Te, n_rho) ndarray）+ `coverage` 属性、notes

### writers_cn4.py —— cn4 目标写出器（注册表桥梁）
单表进、一份 cn4 出：内部走 `parsers.cn4_io.parsed_tables_to_cn4(..., allow_foreign=True)` + `write_cn4`。表内没有的二维场/不透明度块一律 **NaN 占位**（不写 0——0 是合法物理值）；组成信息**不猜**：`izgas` 必须显式给出，`fracsp` 仅单元素时默认 `[1.0]`；单温总 EOS 由组装层 1:1 均分到 ion/ele 槽保证守恒；**单位不换算**，换算责任在调用方。多表材料（如 LEDCOP 独立不透明度表）请用 `parsers.cn4_io.convert_foreign_to_cn4`。

关键 API：
- `write_cn4_single(table, out_path, *, izgas=None, fracsp=None, atomwt=None, **opts) -> Path`

### writers_multi.py —— MULTI/Hyades 逆变换写出器
每条逆变换对照权威参考实现严格复刻列宽/单位/展平顺序。F2 的 kappa 在表里本身已是 log10 值（`field_log10=True`），写出**不再取一次 log10**；F3 的 T 以 keV 写出；F1 有 `e0_cold` 写 `with_e0` 布局否则 `no_e0`。换行按目标族给默认（MULTI 族 LF、hyades MATLAB 风格 CRLF），可覆盖。

关键 API：
- `write_multi_opacity(table, out_path, *, field=None, newline="\n") -> Path` —— 灰度与多群子表串联
- `write_hyades_eos(table, out_path, *, zbar=1.0, abar=1.0, rho0=1.0, comment=None, newline="\r\n", invert=False) -> Path` —— 源表是 (rho,de) 基时须 `invert=True`（自动反演，Te 轴取源 T 场范围、log10 等距、点数同 ne）
- `write_multi_inverted_eos(table, out_path, *, newline="\n") -> Path`
- `fmt15(v) / fmt16(v)` —— Fortran/C 风格 15/16 字符科学计数（含 `1.#INF` 处理）
- `dump_values(path, values, *, per_line=4, fmt=fmt15, newline="\n")` —— 定宽多列写数值

## 用法示例

```python
from eosop_pro.convert import convert, convert_tables, list_targets, get_target

for t in list_targets():            # cn4 / h5 / hyades_eos / multi_* ...
    print(t.name, t.description)

convert(table, "out.cn4", izgas=[13])          # 默认目标 = cn4（izgas 必需）
convert(table, "out.dat", target="hyades_eos") # 指定其他目标
written, skipped = convert_tables(tables, "outdir/")  # 批量，默认 cn4
```

新增一个目标格式 = 写一个 `write_x(table, path, **opts)` 并 `register(ConvertTarget(...))`，无需为每对 (源, 目标) 写转换器。格式族背景见 [`../docs/20_格式规格与物理量单位手册.md`](../docs/20_格式规格与物理量单位手册.md)。
