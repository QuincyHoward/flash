> 最后核对：2026-11-14 · commit ba2981e（其后含功能树重组，代码为准）

# core/profile/ —— 行剖面与列剖面：从内容定位头部/payload 分界与字段宽

core 内层结构证据层，是 infer 布局反演的直接输入。依赖 `core.numbers`
（数值覆盖率/字母残留）与 `core.text.textio`（流式读行）。两把尺子：
行剖面用「行长直方图 + 数值覆盖率 + 字母残留率」三证据定头部/payload 分界；
列剖面用「空白列间距 + 行长 // token 数」双路径反推字段宽。

## 模块

### lineprofile.py
行结构剖面（②）：定位「头部文本区 / payload 数值区」分界。实测教训已内建：
注释行也含数字（覆盖率不能单独用）；payload 行含指数 E（「含字母」必须先剔除
数值 token 再判）。`modal_only=True` 时 payload 判定额外要求行宽 == 众数行宽。

关键 API：
- `profile_lines(lines, *, coverage_min=0.99, modal_only=True) -> LineProfile` —— 对行列表做剖面，给出分界 `header_end` 与 payload 计数
- `profile_file(path, *, coverage_min=0.99, modal_only=True, max_lines=None) -> LineProfile` —— 对文件做剖面（流式读，大文件友好）
- `LineProfile` —— 行结构画像（n_lines/n_blank/length_hist/modal_length/payload_flags/payload_flags_raw/header_end/n_payload/n_header/notes）
  - `is_all_numeric` —— 无头部全 payload
  - `is_free_text_heavy` —— 头部占比 >50%（可能是锚点状态机型，如 LEDCOP）
  - ★ `payload_flags_raw` 是**未施加众数过滤**的原始判定，用于发现 payload 区中断（拼接多表/注释穿插），中断信息写入 `notes`

### columnprofile.py
列占用剖面（③）：**不预设** 15/16，由 payload 区列占用直方图反推字段宽。
路径 A：恒为空白的列是天然字段边界 → 间距众数；路径 B：行长 // 每行 token 数。
退化情形（matter++ 常态）：负号吃掉前导空格导致字段紧邻、无空白列 →
依赖长度法。选宽**长度法优先**（右对齐字段的散碎空白列常使空白列法偏小），
两法不一致时把分歧记入 `conflicts`，让人能看出结论怎么来的。

关键 API：
- `profile_columns(payload_lines, *, default=WIDTH_MULTI) -> ColumnProfile` —— 由 payload 行推断字段宽与所用判据
- `ColumnProfile` —— 列占用画像（blank_columns/width_from_gaps/width_from_length/tokens_per_line/width/rule/conflicts；`describe()`）

用法示例：
```python
from eosop_pro.core.profile.lineprofile import profile_file
from eosop_pro.core.profile.columnprofile import profile_columns

prof = profile_file("Al_eos.IN")            # LineProfile(header_end=4, n_payload=128, ...)
lines = open("Al_eos.IN").read().splitlines()[prof.header_end:]
cols = profile_columns(lines)
print(cols.describe())                       # ... W=15 (line-length // tokens-per-line ...)
```
