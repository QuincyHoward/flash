> 最后核对：2026-11-14 · commit ba2981e（其后含功能树重组，代码为准）

# core/numbers/ —— Fortran 数值解析与定宽切分

core 内层数值内核：L2 正则（fortran_numbers，兜底）+ L1 定宽切分（fixedwidth，
权威路径）。上层 profile、infer、各解析器、docsrc 的数值闸门都依赖它。
两条路径在同一文件上必须给出相同结果（见 test_fixedwidth）。
核心难题：字段定宽 15/16 字符，**负号吃掉前导空格**导致字段紧邻无分隔符
（`-0.60000000E+01-0.55789474E+01` 是 4 个数，`str.split()` 只得到 1 个）。

## 模块

### fortran_numbers.py
Fortran 定宽数值解析内核（L2 正则）。覆盖实测全部写法：无前导零
（`.27000000E+01`）、小写 e + 三位指数（`1.1041000e+004`）、紧邻负数、
空小数（`1.`）、D 指数（`1.0D+03`）、MSVC 非有限值（`-1.#INF0000e+000`）。
纪律：`extract_numbers()` 只允许作用于**已剥离表头的 payload 文本**——
对整文件调用会把表头里的 `3711 / 22581 / 11483` 当成数据。

关键 API：
- `extract_numbers(text) -> list[float]` —— 从 payload 文本按出现顺序提取全部数值（含 `1.#INF` → inf/nan，保证计数守恒）
- `count_numbers(text) -> int` —— 只计数不构造列表（大文件省内存）
- `parse_fortran_float(token) -> float` —— 单 token 转 float（兼容 D 指数、`1.#INF`→inf、`1.#IND`/nan→nan）
- `is_payload_line(line, *, coverage_min=0.99) -> bool` —— 头部/payload 分界主判据：删掉数值 token 后无字母残留 **且** 数值覆盖率 ≥ 阈值
- `numeric_coverage(line, *, ignore_space=True) -> float` —— 数值 token 覆盖的非空白字符占比（纯数值行 1.0，自由文本 0.0）
- `non_numeric_residue(line) -> str` / `has_letters(line) -> bool` / `letter_ratio(line) -> float` —— 删数值 token 后的残留 / 是否还有字母 / 非数值文本比例
- `numbers_from_lines(lines) -> list[float]` / `count_nonfinite(values) -> int` —— 多行提取 / 统计 inf·nan 个数
- `FORTRAN_NUM_RE` / `SPECIAL_FLOAT_RE` —— 唯一数值正则 / 非有限值正则

### fixedwidth.py
L1 定宽切分 —— matter++ 的权威解析路径。字段宽实测：MULTI/SESAME/Hyades
为 15，MPQeos `.301/.304/.305` 为 16；每行字段数 MULTI/SESAME=4，Hyades=5。

关键 API：
- `slice_fields(line, width=WIDTH_MULTI, count=None, start=0) -> list[str]` —— 按定宽切出字段原始文本（空字段跳过）
- `slice_values(line, width=WIDTH_MULTI, count=None, start=0) -> list[float]` —— 定宽切分并转 float
- `values_from_lines(lines, width=WIDTH_MULTI, start=0) -> list[float]` —— 多行定宽切分汇总
- `infer_payload_width(lines, n_fields=FIELDS_MULTI, *, default=WIDTH_MULTI) -> int` —— 由 payload 行长反推字段宽（`W = len(line) // n_fields` 取众数，限 `PLAUSIBLE_WIDTHS=(15,16,20)`；表头不可定宽切分，须交 L2）
- `fields_per_line(n_chars, width=WIDTH_MULTI) -> int` —— 满行时的字段数
- 常量 `WIDTH_MULTI=15` / `WIDTH_MPQEOS=16` / `FIELDS_MULTI=4` / `FIELDS_HYADES=5`

用法示例：
```python
from eosop_pro.core.numbers import fortran_numbers as fn
from eosop_pro.core.numbers.fixedwidth import slice_values, infer_payload_width

fn.extract_numbers("-0.60000000E+01-0.55789474E+01")   # [-6.0, -5.5789474]
fn.is_payload_line("-0.60000000E+01-0.55789474E+01")   # True（E 属数值 token）
fn.is_payload_line("ALUMINUM  LANL SESAME #3711")      # False（表头）

slice_values("-0.60000000E+01-0.55789474E+01-0.51578947E+01-0.47368421E+01", width=15)
# [-6.0, -5.5789474, -5.1578947, -4.7368421]
```
