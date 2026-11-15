> 最后核对：2026-11-14 · commit ba2981e（其后含功能树重组，代码为准）

# registry/identify/ —— 声明式分派解析与「声明 vs 内容」交叉验证

两个阶段在此衔接：`dispatch.py` 是**阶段 A 分派器**（按声明候选族依次调解析器，
全程留痕）；`identify.py` 是**阶段 B2 比对器**（把声明类型与内容反演类型比对，
产出冲突清单）。二者向上被 `pipeline/cli.py` 的 `parse` / `identify` 子命令与
`pipeline/batch.py::audit_sweep` 调用；向下依赖 `schema/declared_types`（候选族）、
`parsers/`（实际解析器）、`core/infer`（内容反演）、`ops/reporting`（报告写出）。

## 模块

### dispatch.py
按**声明式**候选族依次尝试解析。候选族来自 `declared_types`（扩展名 / 路径 /
命名 token / 注册表 / 伴随注释），按候选顺序尝试、**成功即停**，并把「第几个
候选成功」记进 `dispatch_rule`。经典案例：`mat_Al-1.0/AL_eos.feos` 声明
`feos_native` 但内容实为 SESAME，第一候选计数守恒失败后回退 `multi_inverted_eos`
——回退**不是猜测**，而是按声明候选顺序尝试且完整记录在案。每个文件产出一条
`ParseSnapshot`；mismatch/异常**不静默**。

关键 API：
- `FAMILY_PARSERS: dict[str, Callable]` —— 声明族 → 各解析器 `parse_all` 的映射
  （F1 multi_inverted_eos / F2 multi_opacity / F3 hyades_eos·hyades_opacity·
  sesame_dat / F4 mpqeos·feos_native·feos_tabdata·feos_aux / coldopacity /
  hugoniot / ionmix / ledcop_atomic / ledcop_zeff / snop_input / generic_curve）
- `parse_declared(relpath, declared, *, registry=None, store=None,
  include_multigroup=False) -> ParseOutcome` —— 按声明候选族依次尝试解析
- `ParseOutcome(tables, snapshot)` —— 一次解析尝试的结果；属性 `ok`
- 内部提示：`_unit_hint_for` / `_ng_hint_for` 从 `AnnotationStore` 取单位/群数声明

### identify.py
把「声明类型」与「内容反演类型」比对，产出**五类**严格区分的结果：
`agree`（一致）/ `agree_structure`（★结构等价——同一条计数公式仅字段语义不同，
**不是缺陷**）/ `order_mismatch`（在候选里但非第一候选）/ `conflict`（不在候选里）/
`declared_only`·`inferred_only`（单侧无结论）。反演「无结论」（ambiguous /
unrecognized）**不算冲突**——多群子表串联等格式本就无法用扁平模板表达，记成
冲突会淹没真正的信号。`STRUCT_EQUIV` 显式声明结构等价组（实测
`hyades_eos` ≡ `hyades_opacity`：`L = 2 + nr + nt + 2*nr*nt`），避免 37 个
`opc_*.dat` 被误报成 mismatch 而淹没真正的 10 条 conflict。

关键 API：
- `identify(relpath, *, declared=None, inference=None, registry=None,
  store=None) -> TypeComparison` —— 比对单个文件
- `sweep(*, registry=None, store=None, relpaths=None, max_bytes=4_000_000)
  -> list[TypeComparison]` —— 全树比对；超 `max_bytes` 的文件跳过内容反演
  （显式取舍，只在清单里记 declared_only 并注明原因）
- `write_report(comparisons, outdir=None) -> tuple[Path, Path]` —— 写
  `type_conflict.csv` 与 `type_conflict.md`（固定名，每次覆盖）
- `TypeComparison` —— 单文件比对结果 dataclass；`describe()` / `to_row()`
- `same_structure(a, b) -> bool` —— 两族是否同属 `STRUCT_EQUIV` 等价组

用法示例：
```python
from eosop_pro.registry.schema.declared_types import declare
from eosop_pro.registry.identify.dispatch import parse_declared
from eosop_pro.registry.identify.identify import identify

d = declare("mat_Al-1.0/AL_eos.feos")          # 声明候选 [feos_native, multi_inverted_eos]
out = parse_declared("mat_Al-1.0/AL_eos.feos", d)
print(out.snapshot.family, out.snapshot.dispatch_rule)   # 实际家族 + 第几候选成功

c = identify("mat_Al-1.0/AL_eos.feos")
print(c.describe())                             # -> agreement: order_mismatch
```
```bash
python -m eosop_pro.pipeline.cli parse  mat_Al-1.0/AL_eos.feos  # 单文件解析摘要
python -m eosop_pro.pipeline.cli identify                        # 全树比对 + 报告
```
