> 最后核对：2026-11-14 · commit ba2981e（其后含功能树重组，代码为准）

# core/text/ —— 文本字节级读取：字节分类、编码链、哈希、异常与审计快照

core 内层文本/字节 I/O 子包。上层 docsrc、profile、infer、各解析器都从这里
取文本与字节画像；它依赖 `core.config`（BOM/NUL 常量、编码链）。实测背景：
matter++ 中 26 个文件带 UTF-8 BOM、12 个非 UTF-8（Readme.txt 是 GB18030）、
3 个混合换行、291 个无结尾换行 —— 所有实现都以这些事实为准。

## 模块

### byteclass.py
字节层分类：决定一个文件能否走文本解析路径、用哪段编码。NUL 字节一票否决
（→ binary），可打印率 ≥0.90 判 text，其余可解码判 mixed。

关键 API：
- `classify_bytes(data, *, size_bytes=None) -> ByteClass` —— 对一段字节（通常为文件头部样本）做分类
- `classify_file(path, *, strict=False) -> ByteClass` —— 只读头部样本（256 KiB）分类；`strict=True` 时非文本抛 `BinarySuspect`
- `encoding_chain(data) -> tuple[str, ...]` —— 按「有无 BOM」选编码链：有 BOM 先试 `utf-8-sig`，无 BOM 先试 `utf-8`
- `read_head(path, n=SAMPLE_BYTES) -> bytes` —— 读文件头部 n 字节
- `ByteClass` —— 字节层画像（kind/encoding/has_bom/has_nul/printable_ratio/newline/reasons；`is_text`、`describe()`）

### textio.py
文本读取：编码链解码、通用换行统一、BOM 剥离、空行统计。注释行与空行永不
进入 payload 数值流（由各解析器保证），原始行文本完整保留供溯源。

关键 API：
- `read_text(path) -> TextDoc` —— 整文件读入并解码（正确性优先，编码链作用于完整字节流）；超大文件请用 `iter_lines`
- `iter_lines(path, *, encoding=None) -> Iterator[str]` —— 流式逐行读取（通用换行），超大文件压内存峰值；`errors="replace"` 避免坏字节中断
- `load_lines(path) -> list[str]` —— 只取行列表的便捷封装
- `strip_bom(s) -> str` / `is_blank(line) -> bool` —— 剥 BOM / 判空行
- `TextDoc` —— 文件画像（text/lines/encoding/byteclass/blank_line_indices/has_trailing_newline；`n_lines`、`head(n)`、`line(i)`）

### hashing.py
文件哈希：流式分块（1 MiB），大文件不整读入内存。

关键 API：
- `sha256_file(path) -> str` —— 分块计算 SHA-256，返回小写十六进制摘要
- `sha256_bytes(data) -> str` —— 内存字节的 SHA-256
- `short8(digest) -> str` —— 取摘要前 8 位（用于报告文件名）

### errors.py
解析异常类型。原则：任何不确定都必须变成带数值证据的诊断，而不是静默兜底。

关键 API：
- `MultiEosOpError` —— 项目所有异常的基类
- `ParseError(message, *, path="", header_raw="")` —— 无法解析（携带路径与原始表头）
- `CountMismatch(actual, expected, *, path="", header_raw="")` —— 实测数值个数与表头推导不一致，不可静默吞掉（带 `actual/expected/delta`）
- `BinarySuspect` / `UnrecognizedFormat` / `AmbiguousFormat(candidates)` / `UnitConflict` —— 二进制嫌疑 / 布局不自洽 / 多布局并列 / 单位冲突

### snapshot.py
解析审计记录：每个文件一条 `ParseSnapshot`，是 `audit_all.<ts>.csv` 的行结构与
h5 `/meta/sources` 的来源。count_mismatch / ambiguous 等状态绝不允许静默丢弃。

关键 API：
- `ParseSnapshot` —— 单文件审计记录（status/header_raw/n_numbers_actual/expected/layout_rule/...；`note()`、`finalize()`、`as_row()`、`should_write_h5`）
- `STATUSES` —— 11 种允许状态（ok / ok_unverified / count_mismatch / ambiguous_layout / unrecognized / type_conflict / unit_suspect / unit_conflict / skipped_non_numeric / binary_suspect / error）
- `SNIP_COLUMNS` —— 审计 CSV 的列（顺序即写盘顺序）
- `TableRecord` —— 已解析表格（写 h5 的单元：axes/fields/units/log10 标记；`nr`、`nt`）
- `Stopwatch` / `utc_mtime(path)` —— 毫秒计时 / UTC mtime 字符串

用法示例：
```python
from eosop_pro.core.text.textio import read_text, iter_lines
from eosop_pro.core.text.byteclass import classify_file
from eosop_pro.core.text.hashing import sha256_file

bc = classify_file("Al.txt")          # ByteClass(kind='text', encoding='utf-8', ...)
doc = read_text("Al.txt")             # TextDoc：行列表 + 编码 + 空行索引
for ln in iter_lines("ATOMIC/Al.txt"):  # 超大文件流式读
    ...
print(sha256_file("Al.txt")[:8])
```
