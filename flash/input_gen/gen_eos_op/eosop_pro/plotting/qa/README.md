> 最后核对：2026-11-14 · commit ba2981e（其后含功能树重组，代码为准）

# plotting/qa/ —— QA 通用绘图：固定三图 + 全族通用绘图原语

两个模块分工：`qa_plots.py` 画 EOS/不透明度/Zeff 三类固定 QA 图；
`gridmap.py` 是**统一绘图模块**——cn4 专用绘图里的绘图原语已上提至此，
任何 eosop 文件类型（F1~F6 全部族的 `ParsedTable`）都能画出「cn4 同款」图像。
上层 `pipeline/cli.py` 的 `plot` / `plot-all` 子命令经这里出图；依赖
`registry/field_checks`（控制字典）、`../style`（样式/标签）、`parsers/base`
（ParsedTable）。

## 模块

### qa_plots.py
质量保证出图——EOS 等压线 / 不透明度热图 / Zeff 图（全英文、PPT 级）。
所有函数返回 `matplotlib.figure.Figure` 并可写 PNG；★标签纪律：所有 x/y 轴与
colorbar 标签一律经 `style/labels.field_label` 从控制字典实时取物理意义/单位/
认证标记——人工核查翻 `checked` 后下一次出图自动同步，本模块不硬编码标签。

关键 API：
- `plot_eos_isobars(table, field="P", ...)` —— 等压线族图
- `plot_opacity_heatmap(table, field="kappa", ...)` —— 不透明度热图
- `plot_zeff(table, field="Z", ...)` —— Z̄ 图
- `plot_loglog_curve(x, y, *, xlabel="x", ylabel="y", title="curve", ...)` ——
  通用 log-log 曲线
- `save_fig(fig, path) -> Path` —— 落盘（内部先 `assert_ascii` 再保存）

### gridmap.py
通用二维彩图 / 一维曲线原语 + 任意 ParsedTable 批量出图。纪律：样式常量唯一
来源 `core/config`；全 ASCII 文本由 `style.assert_ascii` 落盘前强校验；每张图
落盘后立即 `close`（run_all 同进程，figure 不得泄漏）；ne-T 等派生轴只在物理
可导出时绘制（需电离度场 + 显式 atomwt），缺依据时**跳过并写明原因**，绝不猜测；
字段与轴形状不匹配时**不再静默跳过**——改画 raw values vs element index 序列图
（数值本身永远可画），图与报告明确标注 semantics unknown。

关键 API：
- `plot_heatmap(...)` —— 二维彩图原语（log/linear 轴与色标、NaN 白色占位、
  数据边界凸包虚线、PPT 级样式）
- `plot_multi_curve(...)` —— 一维多曲线原语（vs T / vs rho 等）
- `plot_table_all_fields(tables, outdir, ...)` —— **批量入口**：对任意族一组
  ParsedTable 逐场出图（rho-T 平面彩图 + 可导出时 ne-T 彩图 + 截断曲线），并写
  `_report.txt`（网格点数/单调性/物理量意义/单位/checked 状态，字典来自
  `registry.field_checks`）
- `sanitize_name(name) -> str` —— 文件名净化
- `CHARGE_FIELD_CANDIDATES` —— 电荷场候选名（ne 派生用）

用法示例：
```python
from eosop_pro.registry.identify.dispatch import parse_declared
from eosop_pro.registry.schema.declared_types import declare
from eosop_pro.plotting.qa.qa_plots import plot_opacity_heatmap
from eosop_pro.plotting.qa.gridmap import plot_table_all_fields

rel = "hyades/Opacity/opc_1022.dat"
out = parse_declared(rel, declare(rel))
plot_opacity_heatmap(out.tables[0])            # 单文件单图
plot_table_all_fields(out.tables, "outputs/plots")   # 逐场批量 + _report.txt
```
```bash
python -m eosop_pro.pipeline.cli plot  hyades/Opacity/opc_1022.dat --outdir outputs/plots
python -m eosop_pro.pipeline.cli plot-all --limit 40
```
