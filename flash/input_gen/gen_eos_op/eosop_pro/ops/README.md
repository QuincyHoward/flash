> 最后核对：2026-11-14 · commit ba2981e（其后含功能树重组，代码为准）

# ops/ —— 运行维护：审计证据报告写出与产物保留策略

两个无状态工具模块，被全包复用：`reporting.py` 是所有 CSV/JSON/Markdown 报告的
统一写出器（`registry/identify`、`registry/zeff`、`pipeline/batch` 都经它落盘）；
`prune.py` 是报告目录保留策略（`pipeline/cli.py` 的 `prune-reports` 子命令、
`scripts/10_prune_reports.bat`、`run_all.bat` 第 9 步调用）。

## 模块

### reporting.py
报告写出工具（CSV / JSON / Markdown）——审计证据的统一格式。所有报告遵循同一
纪律：**头部写明数据来源、生成时刻、样本总数、sha256 汇总**，让每条结论都可
追溯到具体文件与字段。编码/行尾纪律：CSV 用 UTF-8 with BOM（Excel 直接打开
中文不乱码）且 **CRLF**（RFC 4180）；其余文本产物一律 **LF**。

关键 API：
- `write_csv(path, rows, columns=None) -> Path` —— 写 CSV（UTF-8 BOM + CRLF）
- `write_json(path, obj) -> Path` —— 写 JSON
- `write_md(path, text) -> Path` —— 写 Markdown（统一 LF）
- `md_header(title, source, total, ...) -> str` —— 标准报告头部（来源/时刻/
  样本数）
- `md_table(rows, columns=None, ...) -> str` —— dict 行序列 → Markdown 表格
- `counter_table(counter, key_name="key", ...) -> str` —— Counter → 频次表
- `now_stamp() -> str` —— 本地时间戳 `20260914T152830`（报告批次 id 的来源）
- `utc_now() -> str` / `shorten(s, n=60)` —— UTC 时间戳 / 截断

### prune.py
报告目录保留策略——每类报告只留最新几批。背景：报告文件名带时间戳
（`audit_all.<ts>.md`），每跑一次多一份，一次测试套件就能新增十多个文件；而
**固定名**报告（`zeff_inventory.*` / `type_conflict.*`）每次覆盖、不会堆积。
纪律：① 只删时间戳批次里的旧文件，从不删最新一批、从不删固定名报告；
② 一次运行的 csv/json/md 三份共享同一时间戳，**同进同出**；③ `dry_run=True`
只列不删。不做的事：不碰 `outputs/{h5,plots,logs}`（产物不是报告）、不做按
大小淘汰。

关键 API：
- `prune_reports(*, outdir=None, keep=1, dry_run=False) -> dict` ——
  每类保留最新 `keep` 批（默认 1）
- `list_report_batches(outdir=None) -> dict[str, list[list[Path]]]` ——
  前缀 → 批次列表（供预览）
- `REPORT_PREFIXES` —— 参与保留策略的批次型前缀：`audit_all.` / `inventory.` /
  `convert_all.` / `plot_all.` / `identify.` / `infer_unknown.`

用法示例：
```python
from eosop_pro.ops import reporting, prune

reporting.write_csv("outputs/reports/audit_all.csv", rows)   # UTF-8 BOM + CRLF
md = reporting.md_header("审计", "matter++", 150) + reporting.md_table(rows)
reporting.write_md("outputs/reports/audit_all.md", md)

prune.list_report_batches()                       # 预览各前缀的批次
prune.prune_reports(keep=1, dry_run=True)         # 只列不删
```
```bash
python -m eosop_pro.pipeline.cli prune-reports --keep 1 --dry-run
```
