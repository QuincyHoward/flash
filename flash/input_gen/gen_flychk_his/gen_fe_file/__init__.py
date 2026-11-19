"""gen_fe_file — FLYCHK 非麦克斯韦电子分布 (EEDF/beam) ``fe`` 文件生成器。

两种输入模式:
1. 解析模型 (FeModel): 麦克斯韦束 / 漂移麦克斯韦 / 单能束, 给 Te/密度/时间自动生成;
2. 显式数组 (FeExplicitSeries): 直接提供 (能量网格, [(time, density, fe(E))])。

产物可独立写文本 (``fe file`` 数据文件), 也可经 ``write_history_zip_with_fe``
并入 FLYCHK history 模式 zip (runfile 增加 ``fe file <名>`` 行, zip 第三成员)。

快速上手::

    from flash.input_gen.gen_flychk_his.gen_fe_file import (
        FeModel, build_fe_file, write_history_zip_with_fe)

    fe = build_fe_file(
        FeModel(te_beam=1000.0, beam_density=1e11,
                times=[0.0, 1e-9]),
        energies=[500.0, 1000.0, 2000.0, 5000.0],
        comment="maxwellian beam Te=1keV",
    )
    write_history_zip_with_fe(table, fe, "out/history_Ti_Z22_fe.zip")

格式契约与约束详见模块 README 与 fe_file.py docstring。
"""

from __future__ import annotations

from .fe_file import (
    FeFile,
    FeFileError,
    FeExplicitSeries,
    FeModel,
    MAX_ENERGY_POINTS,
    MAX_LINE_CHARS,
    MODELS,
    NORM_WARN_REL,
    build_fe_file,
    drift_maxwell_shape,
    fe_filename_for,
    maxwell_fe,
    mono_shape,
    render_fe_text,
    validate_fe_file,
    write_history_zip_with_fe,
)

__all__ = [
    # 输入规格 / 结果容器
    "FeModel",
    "FeExplicitSeries",
    "FeFile",
    "FeFileError",
    # 解析模型
    "maxwell_fe",
    "drift_maxwell_shape",
    "mono_shape",
    # 构建 / 校验 / 渲染 / 集成
    "build_fe_file",
    "validate_fe_file",
    "render_fe_text",
    "fe_filename_for",
    "write_history_zip_with_fe",
    # 格式常量
    "MAX_ENERGY_POINTS",
    "MAX_LINE_CHARS",
    "NORM_WARN_REL",
    "MODELS",
]
