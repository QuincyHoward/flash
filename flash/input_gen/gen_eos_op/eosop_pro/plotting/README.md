> 最后核对：2026-11-14 · commit ba2981e（其后含功能树重组，代码为准）

# plotting/ —— PPT 演讲级 QA 绘图层（全英文、大字号、高 DPI）

把 `parsers/` 解析出的 `ParsedTable` 与 cn4 表格画成可进 PPT 的图：二维彩图、
一维曲线、群不透明度大图、热力学路径、时间演化、拟合。上层 `pipeline/`
（`plot` / `plot-all` / `cn4-*` 子命令）是唯一编排入口；本层向下依赖
`registry/field_checks`（标签字典）、`registry/schema`（ParsedTable 元数据）、
`core/config`（样式常量）。

**绘图样式常量唯一来源**是 `eosop_pro.core.config` 的 `PLOT_*` 值（任何绘图
代码不得自写数字，`test_config_single_source` 守护）：
`PLOT_DPI = 450`、`PLOT_TITLE_FONTSIZE = 26`、`PLOT_LABEL_FONTSIZE = 22`、
`PLOT_TICK_FONTSIZE = 20`、`PLOT_LEGEND_FONTSIZE = 20`、`PLOT_LINEWIDTH = 2.4`、
`PLOT_MARKERSIZE = 8`、`PLOT_FIGSIZE = (8.0, 6.0)`、`PLOT_CMAP = "viridis"`。
文本一律 ASCII（英文），由 `style.assert_ascii` 在落盘前强校验。

## 三子层导航

| 子层 | 定位 | 核心模块 |
| --- | --- | --- |
| `cn4/` | IONMIX cn4 表格专题：热力图、曲线、时间演化、拟合、热力学路径、γ/声速派生 | `cn4_plots.py`、`cn4_paths.py`、`cn4_timeseries.py`、`cn4_fit.py`、`cn4_thermo.py` |
| `qa/` | 通用 ParsedTable QA 出图：等压线/热图/Zeff 图 + 全族通用绘图原语 | `qa_plots.py`、`gridmap.py` |
| `style/` | 样式底座：rcParams 应用、ASCII 强校验、字典驱动标签、单位换算 | `style.py`、`labels.py`、`units.py` |

两条贯穿纪律：
1. **标签字典驱动**——一切物理量标签经 `style/labels.field_label` 从控制字典
   实时取意义/单位/认证标记，绘图代码零硬编码；人工核查翻 `checked` 后下一张
   图自动同步。
2. **标记只有 uk/uv**——`uk`（无来源确认）/ `uv`（未人工核查），有源且已核查
   整体省略（当前仅 cn4/ionmix 全 18 块）。
