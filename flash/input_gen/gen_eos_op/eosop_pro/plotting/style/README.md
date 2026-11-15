> 最后核对：2026-11-14 · commit ba2981e（其后含功能树重组，代码为准）

# plotting/style/ —— 绘图样式底座：rcParams、ASCII 校验、字典标签、单位换算

全部绘图模块共用的底座三件套：`style.py` 应用全局 rcParams 并强校验文本 ASCII；
`labels.py` 是字典驱动的标签统一出口（绘图代码零硬编码标签）；`units.py` 做
cn4 原始单位 → 显示单位换算。被 `plotting/cn4/`、`plotting/qa/` 与
`pipeline/` 报告链路引用；向下依赖 `core/config`（PLOT_* 常量）与
`registry/field_checks`（控制字典）。

## 模块

### style.py
PPT / 演讲级绘图样式——全英文、大字号、高 DPI。硬性要求全部可测（`test_plots`
逐条断言，含「文本必须全 ASCII」正则 `^[\x00-\x7F]*$`，因中文在 PPT 里常出现
字体缺失与乱码）：title ≥24pt、轴标签 ≥20pt、刻度 ≥20pt、图例 ≥18pt、
DPI ≥450、linewidth ≥2、markersize ≥8。具体数值取自 `config.PLOT_*`
（唯一来源，见 `plotting/README.md`）。

关键 API：
- `apply_style()` —— 应用全局 rcParams（幂等，Agg 后端，DejaVu Sans 字体族）
- `assert_ascii(text)` —— 非 ASCII 即抛错（落盘前强校验）
- `all_text_ascii(obj) -> bool` —— 递归检查容器内全部文本
- `style_report(...)` —— 当前样式状态摘要
- `ASCII_RE` —— 允许字符集正则

### labels.py
字典驱动标签统一出口（用户 2026-09-15 第十二轮裁定）。一切绘图/报告的物理量
标签（坐标轴/colorbar/曲线 ylabel/报告行）一律经本模块从控制字典
`registry.field_checks` **实时**取意义（meaning）、单位（unit）与认证标记；
用户核查后只改 `field_checks.py`，下一次出图自动同步。守护：
`test/eosopdata/step02_families/test_plot_labels.py` 扫描绘图模块源码不得再
出现硬编码物理量标签。

标签格式与查找顺序：
- 短/长双轨：`field_label("mpqeos", "P")` → `"P (Mbar), uv"`（默认短标签）；
  `long=True` → 完整 meaning；`short` 为空串（动态注册族）回退 meaning
- 未登记名回退用字段名本身（去 `#` 前缀），绝不冒充字典语义
- 查找顺序：精确字段名 → 去 `#` 前缀（`"#Eph"` → `"Eph"`）→ `Te/tele` →
  `T`（ionmix 温度轴登记名）→ `"*"` 兜底 → 未注册族兜底

关键 API：
- `field_label(family, name, *, long=False, parser_unit=None) -> str` ——
  **标签统一出口**
- `display_unit(family, name, parser_unit=None) -> str` —— 解析器实测单位优先，
  其次字典 unit，皆无写 `unknown`（不猜测）
- `tags_of(family, name) -> str` —— uk/uv 标记（= `tags_label(field_check(...))`）
- `widest_tags(family) -> str` —— 族级最宽标记（`"" < uv < uk < uk, uv` 排序）
- `cn4_tags(origin_family, cn4_field) -> str` —— cn4 量名 → 来源族字典标记
- `FAMILY_ALIASES`（`{"cn4": "ionmix"}`）与 `CN4_SOURCE_FIELD` —— 族名/字段名
  别称映射

### units.py
cn4 原始单位 → 显示单位换算，每个因子附完整推导链与文档出处（本模块不引入
任何未在源码或文档中出现过的单位主张）。一手来源 `abjt_03.f`：温度 eV
（line 4683）、密度 cm⁻³（4685）、压力 J/cm³（4693 赋值表达式推定）、比内能
J/g（4705）、比热 J/g/eV（4710）、群边界 eV（4728）、不透明度 cm²/g（4732）。
常量：`DPDT_TO_MBAR_EV = 1.0e-5`、`E_JG_TO_ERG_G = 1.0e7`、`CV_TO_ERG_G_EV =
1.0e7`、`V_CMS_TO_UM_NS = 1.0e-5`、`T_S_TO_NS = 1.0e9`、`X_CM_TO_UM = 1.0e4`。

关键 API：
- `pressure_mbar(p_jcm3)` / `energy_ergg(e_jg)` / `heat_cgs(cv_jgev)` ——
  压力/能量/比热换算
- `velocity_umns(v_cms)` / `time_ns(t_s)` / `length_um(x_cm)` —— 速度/时间/
  长度换算
- `density_gcc_from_nion(n_ion, avg_atomwt)` /
  `nion_from_rhogcc(rho, avg_atomwt)` —— 数密度 ↔ 质量密度（ρ = n·⟨A⟩/N_A）

用法示例：
```python
from eosop_pro.plotting.style.style import apply_style, assert_ascii
from eosop_pro.plotting.style.labels import field_label, tags_of
from eosop_pro.plotting.style.units import pressure_mbar

apply_style()                                  # 幂等应用 PPT 级 rcParams
assert_ascii("P (Mbar), uv")                   # 非 ASCII 文本落盘前拦截
field_label("mpqeos", "P")                     # -> "P (Mbar), uv"
field_label("ionmix", "T")                     # -> "T (eV)"（已核查，标记省略）
pressure_mbar(1.6e12)                          # J/cm^3 -> Mbar
```
