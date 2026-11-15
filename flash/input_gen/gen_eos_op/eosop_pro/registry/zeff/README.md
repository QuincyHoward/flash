> 最后核对：2026-11-14 · commit ba2981e（其后含功能树重组，代码为准）

# registry/zeff/ —— Z̄（平均电离度）数据源注册、覆盖度盘点与单位裁决

回答「某个材料能不能算出 Z̄(ρ,T)、它的 T 轴单位是什么单位依据是什么」。
`zeff_registry.py` 文件级扫描全树并登记全部 Z̄ 数据源；`zeff_inventory.py` 合成
**材料级**覆盖度；`units_registry.py` 把 T 轴单位从猜测变成**有来源的裁决**。
上层 `pipeline/cli.py` 的 `zeff` 子命令（scripts/04_zeff.bat）驱动盘点并写报告；
`convert/` 写 h5 时消费 `UnitsRegistry` 的单位决定。向下依赖 `material/`
（材料归属）、`schema/annotation_store`（单位声明）、`ops/reporting`（报告）。

实测底盘：178 个 Z̄ 相关文件 / 79 个目录，九类布局（Z1~Z9）；三条硬结论——
① F2 表的槽位是**类型码**而非 Zbar；② 单位**必须靠声明**（`Al_Zeff.dat` keV 与
`Al_Z.dat` eV 表头行数完全相同，Δlog10 恰 3.000，纯数字无法区分）；
③ Z̄(ρ,T) 覆盖 **130/251** 材料，另 121 个只有常量 Z。

## 模块

### zeff_registry.py
文件级 Z̄ 数据源注册表。`scan()` 遍历全树，按文件名模式分类为 Z1~Z9 九类
（`Thermos/*_Zeff.dat` keV、`*_Z.dat` eV 已作废、`*.ZEFF`、`*_op03z`、
`ATOMIC/*.NoFree|*.AvSqFree`、`.301/.304/.305` 第 5 段内嵌 Z 数组…），
随后用 `UnitsRegistry` 逐文件裁决 T 单位。

关键 API：
- `ZeffRegistry(matter_dir=None, *, units=None, material=None, with_sha=False)`
- `scan() -> list[ZeffSource]` —— 全树扫描分类；`with_sha=True` 时附 sha256
- `by_family() -> dict[str, list[ZeffSource]]` /
  `by_material() -> dict[str, list[ZeffSource]]` —— 分组视图
- `unit_suspects() -> list[ZeffSource]` —— 单位存疑清单（envelope 兜底裁决的）
- `summary() -> dict[str, int]`
- `ZeffSource` —— 单个数据源条目（relpath/kind/family/units_T/unit_source/
  unit_evidence/sha256）；常量 `KIND_Z`（Z̄ 表）/ `KIND_Z2`（Z² 表）/ `KIND_CONST`

### zeff_inventory.py
材料级 Z̄ 覆盖度盘点——回答「某材料能不能算出 Z̄(ρ,T)」。覆盖度四级：
`table`（material.base 显式声明 ZEFF 行，权威）/ `table_by_name`（仅按文件名
归属）/ `nominal_only`（只有常量名义 Z）/ `none`。实测 material.base 的 251 个
MATERIAL 块中 130 个声明了 ZEFF。`write_reports()` 落盘 CSV + Markdown（固定名
`zeff_inventory.*`，每次覆盖）。

关键 API：
- `ZeffInventory(zeff=None, material=None)` —— 构造即备好文件级扫描
- `build() -> list[MaterialZeff]` —— 文件 → 材料归属 + 覆盖度定级
- `summary() -> dict[str, int]` —— 各覆盖度计数
- `write_reports(outdir=None) -> tuple[Path, Path]` —— 写 CSV 与 Markdown 报告
- `MaterialZeff` —— 单材料结论（material/mid/formula/nominal_Z/coverage/
  declared_zeff/tables/notes）

### units_registry.py
单位注记表——把「T 轴单位」从猜测变成**有来源的裁决**。裁决优先级（高→低）：
① `companion` 伴随文件名模式声明（`Thermos/Readme.txt`）；② `inline` 文件内嵌
声明（`T in keV`、两行表头）；③ `envelope` 兜底启发式（logT 上限 ≥4.5 → eV、
≤2.5 → keV，换算后用物理包络 `T ∈ [1e-2, 1e6] eV` 复核）；④ `config_default`
格式默认（F2 默认 eV）。每条裁决带 `source` 与 `evidence`，写进 h5 的
`/meta/units`，使「为什么取这个单位」可追溯。

关键 API：
- `UnitsRegistry(store=None)` —— 可选挂 `AnnotationStore`
- `declared_T(relpath) -> UnitDecision | None` —— 只取声明类裁决（companion/
  inline，不猜）
- `decide_T(relpath, *, logT=None, ...) -> UnitDecision` —— 完整四级裁决链
- `for_file(relpath, *, logT=None, ...) -> dict[str, UnitDecision]` ——
  T 及其他量的单位一并裁决
- `declared_other(relpath) -> dict[str, UnitDecision]` / `summary()`
- `infer_T_from_logT_range(logT) -> UnitDecision | None` —— envelope 启发式
- `UnitDecision` —— 裁决结果（quantity/unit/source/evidence）

用法示例：
```python
from eosop_pro.registry.zeff.zeff_registry import ZeffRegistry
from eosop_pro.registry.zeff.zeff_inventory import ZeffInventory
from eosop_pro.registry.zeff.units_registry import UnitsRegistry

reg = ZeffRegistry(units=UnitsRegistry())
reg.scan()
print(reg.unit_suspects())                    # 单位存疑的文件

inv = ZeffInventory(zeff=reg)
inv.build()
print(inv.summary())                          # {'table': ..., 'nominal_only': ...}
inv.write_reports()                           # outputs/reports/zeff_inventory.*
```
```bash
python -m eosop_pro.pipeline.cli zeff         # 一键盘点并写报告
```
