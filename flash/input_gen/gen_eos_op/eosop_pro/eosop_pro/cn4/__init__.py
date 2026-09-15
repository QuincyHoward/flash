"""IONMIX ``.cn4`` 数据表支持 —— 解析 / 单位 / EOS 路径 / 绘图。

本子包把 ``input_gen/gen_eos_op/ionmix`` 参考实现中的 cn4 处理能力
**整体并入** ``eosop_pro``，此后 cn4 相关能力只在本包维护。

模块地图
--------
``cn4_io.py``       cn4 文件读写内核: 18 个数据块的布局、定宽解析、``CN4Table``
``cnr_io.py``       cnr (late-1986 CONRAD) 只读内核: 7 个数据块、``CNRTable``
``units.py``        cn4 原始单位 → 显示单位换算（含每个因子的推导链）
``cn4_paths.py``    EOS 路径研究: 等温/等压/等熵/雨贡纽、声速、P-V 图
``cn4_plots.py``    PPT 演讲级绘图（全英文、字号 ≥18pt、DPI ≥450）

两种 CONRAD 家族格式
--------------------
``abjt_03.f`` 的 ``OWTF`` 有**两个互斥输出分支**，产出两种扩展名::

    isw(21) != 0   → unit 123 → ``.cn4``（"new"，18 块，含完整 EOS）
    isw(8) = 1/12/13 → unit 8 → ``.cnr``（"original late 1986"，7 块，无 EOS 场）

二者头部第 4 行**格式不同**（``.cn4`` 为 ``982 (i12)`` 独占行；
``.cnr`` 为 ``981 (4e12.6,i12)`` 与 4 个网格参数同行），故**必须按扩展名分派**。
只有 ``.cn4`` 能参与 EOS 路径分析与 ``→ .cn4`` 转换。

权威格式来源
------------
``cn4_io`` 模块 docstring 记录了 cn4 的完整块布局，其依据是
``src/Ionmix/abjt_03.f`` 中的 ``SUBROUTINE OWTF``（``isw(21) != 0`` 分支）
逐条 ``write(123, ...)`` 语句 —— 这是**唯一的一手格式规格**，
且本地存有该源码，可逐行核对。

用法
----
::

    from eosop_pro.cn4 import load_cn4, CN4Table
    from eosop_pro.cn4 import trace_isotherm, trace_hugoniot

    d = load_cn4("Ti-BADGER-TOPS.cn4")
    print(d.species_label, d.ntemp, d.ndens, d.ngrups)
    trace_isotherm(d, T_idx=10, outfile="isotherm.png")

或者直接走统一入口（推荐）::

    from eosop_pro.cn4 import convert_cn4_to_cn4, cn4_to_parsed_tables
"""

from __future__ import annotations

from .cn4_io import (
    CN4Table,
    CN4ParseError,
    load_cn4,
    load_cn4_dir,
    parse_cn4,
    write_cn4,
    cn4_to_parsed_tables,
    parsed_tables_to_cn4,
    convert_cn4_to_cn4,
    convert_foreign_to_cn4,
    NAN_PLACEHOLDER_FIELD,
    NAN_PLACEHOLDER_CUTOFF,
    is_nan_placeholder,
    N_BLOCKS,
    BLOCK_SPEC,
    OPACITY_SPEC,
    FIXED_WIDTH,
    FIXED_HEADER_WIDTH,
    expected_number_count,
    ELEMENT_ATOMWT,
)
from .units import (
    P_JCM3_TO_MBAR,
    E_JG_TO_ERG_G,
    CV_TO_ERG_G_EV,
    V_CMS_TO_UM_NS,
    pressure_mbar,
    energy_ergg,
    heat_cgs,
    velocity_umns,
    time_ns,
    length_um,
    density_gcc_from_nion,
    nion_from_rhogcc,
    DISPLAY_UNITS,
)
from .cn4_paths import (
    nion_from_rho,
    rho_from_nion,
    interpolate_quantity,
    trace_isotherm,
    trace_isobar,
    compute_entropy,
    trace_isentrope,
    trace_hugoniot,
    plot_usup_vs_pressure,
    plot_interpolated_probe,
    sound_speed,
    plot_pv_diagram,
)
from .cnr_io import (
    CNRTable,
    CNRParseError,
    parse_cnr,
    load_cnr,
    load_cnr_dir,
    parse_cnr_header,
    solve_ntrad,
    CNR_BLOCK_SPEC,
    CNR_N_BLOCKS,
)
from .cn4_plots import (
    AXES,
    SUPPORTED_QUANTITIES,
    axis_label,
    display_scale,
    plot_quantity_heatmap,
    plot_group_opacity_heatmap,
    plot_opacity_group_figure,
    plot_all_opacity_figures,
    plot_vs_temperature,
    plot_vs_density,
    plot_cn4_directory,
)
from .cn4_timeseries import (
    plot_time_series,
    plot_center_series,
    flash_extract,
    read_flash_h5,
)
from .cn4_fit import (
    compute_r2,
    fit_power_law,
    fit_exponential,
    fit_ideal_gas,
    fit_generic,
)

__all__ = [
    # io (cn4)
    "CN4Table", "CN4ParseError", "load_cn4", "load_cn4_dir", "parse_cn4",
    "write_cn4", "cn4_to_parsed_tables", "parsed_tables_to_cn4",
    "convert_cn4_to_cn4", "convert_foreign_to_cn4",
    "NAN_PLACEHOLDER_FIELD", "NAN_PLACEHOLDER_CUTOFF", "is_nan_placeholder",
    "N_BLOCKS", "BLOCK_SPEC", "OPACITY_SPEC", "FIXED_WIDTH",
    "FIXED_HEADER_WIDTH", "expected_number_count",
    "ELEMENT_ATOMWT",
    # io (cnr, legacy)
    "CNRTable", "CNRParseError", "parse_cnr", "load_cnr", "load_cnr_dir",
    "parse_cnr_header", "solve_ntrad", "CNR_BLOCK_SPEC", "CNR_N_BLOCKS",
    # units
    "P_JCM3_TO_MBAR", "E_JG_TO_ERG_G", "CV_TO_ERG_G_EV", "V_CMS_TO_UM_NS",
    "pressure_mbar", "energy_ergg", "heat_cgs", "velocity_umns",
    "time_ns", "length_um", "density_gcc_from_nion", "nion_from_rhogcc",
    "DISPLAY_UNITS",
    # paths
    "nion_from_rho", "rho_from_nion", "interpolate_quantity",
    "trace_isotherm", "trace_isobar", "compute_entropy", "trace_isentrope",
    "trace_hugoniot", "plot_usup_vs_pressure", "plot_interpolated_probe",
    "sound_speed", "plot_pv_diagram",
    # plots (任务 A / A' / B)
    "AXES", "SUPPORTED_QUANTITIES", "axis_label", "display_scale",
    "plot_quantity_heatmap", "plot_group_opacity_heatmap",
    "plot_opacity_group_figure", "plot_all_opacity_figures",
    "plot_vs_temperature", "plot_vs_density", "plot_cn4_directory",
    # time series (任务 C)
    "plot_time_series", "plot_center_series", "flash_extract",
    "read_flash_h5",
    # fitting (任务 D)
    "compute_r2", "fit_power_law", "fit_exponential", "fit_ideal_gas",
    "fit_generic",
]

__version__ = "1.0.0"
