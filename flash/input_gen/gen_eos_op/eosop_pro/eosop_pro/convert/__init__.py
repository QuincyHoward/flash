"""跨格式转换包 —— ``read(A) -> ParsedTable -> write(B)`` 的统一入口。

导入本包即完成全部写出器的注册；之后用 :func:`convert` / :func:`convert_tables`。

已注册目标
----------
* ``cn4``                 **默认目标** —— FLASH IONMIX cn4（18 块，双温 EOS +
  3 群不透明度；缺数据 NaN 占位；``izgas`` 必需、单元素 ``fracsp`` 可省）
* ``multi_opacity``       逆变换 F2（灰度 / 多群子表串联）
* ``hyades_eos``          逆变换 F3（``L=2+nr+nt+2·nr·nt``，T 以 keV 写出）
* ``multi_inverted_eos``  逆变换 F1（``with_e0`` / ``no_e0``）
* ``h5``                  单表 HDF5（双轨）

用法（"默认转 cn4，其他类型也可设置"）
--------------------------------------
::

    convert(table, "out.cn4")                      # 默认目标 = cn4
    convert(table, "out.dat", target="hyades_eos") # 指定其他目标
    convert(tables, outdir)                        # 批量，同样默认 cn4

新增一个目标格式 = 写一个 ``write_x(table, path, **opts)`` 并 ``register(...)``，
**不需要**为每对 (源, 目标) 写转换器。默认目标可 ``set_default_target`` 全局改。
"""

from __future__ import annotations

from pathlib import Path

from ..parsers.base import ParsedTable
from .base import (DEFAULT_TARGET, ConvertTarget, REGISTRY, convert,
                   convert_tables, get_default_target, get_target,
                   list_targets, register, set_default_target)
from .writers_cn4 import write_cn4_single
from .writers_multi import (write_hyades_eos, write_multi_inverted_eos,
                            write_multi_opacity)

__all__ = [
    "ConvertTarget", "REGISTRY", "register", "get_target", "list_targets",
    "convert", "convert_tables", "write_h5_single", "write_cn4_single",
    "DEFAULT_TARGET", "get_default_target", "set_default_target",
]


# ── 单表 HDF5 目标 ─────────────────────────────────────────────
def write_h5_single(table: ParsedTable, out_path: Path, *,
                    unified: bool = True, native: bool = True, **opts) -> Path:
    """把一张表写成 HDF5（与材料级 h5 同一模式，只是单表）。

    ``unified`` / ``native`` 分别控制两条轨道；两条都关会被拒绝。
    """
    from ..grid.unified_grid import build_all_grids
    from ..writer.h5_writer import write_material_h5

    out = Path(out_path)
    if out.suffix.lower() not in (".h5", ".hdf5"):
        out = out.with_suffix(".h5")
    grids = build_all_grids([table], A=opts.get("A")) if unified else None
    return write_material_h5(
        out,
        material={
            "material_name": table.table_key,
            "family": table.family,
            "table_id": table.table_id,
            "source_relpath": table.source_relpath,
        },
        tables=[table],
        grids=grids,
        A=opts.get("A"),
        native_track=native,
        extra_root_attrs={"single_table": True},
    )


# ── 注册 ───────────────────────────────────────────────────────
# cn4 是**默认目标**（DEFAULT_TARGET="cn4"）：FLASH IONMIX 主格式，
# "跨族转 cn4" 是用户工作流的枢纽路径。
register(ConvertTarget(
    name="cn4",
    description=("FLASH IONMIX cn4（18 块定宽 4e12.6：双温 EOS 12 场 + "
                 "3 群不透明度；缺数据 NaN 占位、12 列对齐）"),
    writer=write_cn4_single,
    requires=("EOS_TOTAL", "cn4_eos"),
    notes=("izgas 必需（头部组成信息不猜）；单元素 fracsp 默认 [1.0]。"
           "单温总 EOS 按 1:1 均分到 ion/ele 槽（守恒）。单位不换算。"
           "多表材料（独立不透明度子表）请用 cn4.convert_foreign_to_cn4"),
    examples=["*.301 (mpqeos)", "qeos_* (hyades_eos)", "*.cn4 (ionmix)"],
))

register(ConvertTarget(
    name="multi_opacity",
    description="MULTI 不透明度 / Zeff / EPS（F2，4×15 定宽；多群为子表串联）",
    writer=write_multi_opacity,
    requires=("PLANCK", "ROSSELAND", "MUGROUP", "ZEFF", "ZEFF2", "EMISSIVITY",
              "NONLTE", "OPACITY"),
    notes="权威参考 matlab/outputMULTIOpacity.m（%15.7e×4，全 log10，keV→eV×1000）",
    examples=["1041_ROSS", "AL_SIMPLE_ROSSELAND"],
))

register(ConvertTarget(
    name="hyades_eos",
    description="Hyades / SESAME ASCII（F3，5×15 定宽，L=2+nr+nt+2·nr·nt）",
    writer=write_hyades_eos,
    # ROSSELAND/PLANCK 也在其中：``hyades/Opacity/opc_*.dat`` 就是 Hyades 布局的不透明度表
    requires=("EOS_TOTAL", "EOS_ELECTRON", "EOS_ION", "OPACITY",
              "ROSSELAND", "PLANCK"),
    requires_fields=("P", "E"),
    requires_axes=("rho", "Te"),
    notes="权威参考 matlab/outputHyadesEOS.m；T 必须换算成 keV 写出",
    examples=["eos_41.dat", "opc_1031.dat"],
))

register(ConvertTarget(
    name="multi_inverted_eos",
    description="MULTI 反演 EOS（F1，4×15 定宽；自变量为 (rho, de)）",
    writer=write_multi_inverted_eos,
    requires=("EOS_TOTAL", "EOS_ELECTRON", "EOS_ION"),
    requires_fields=("P", "T"),
    notes="有 e0_cold 时写 with_e0 布局，否则写 no_e0",
    examples=["AL_eos"],
))

register(ConvertTarget(
    name="h5",
    description="HDF5 单表（双轨：native 逐字 + unified 两套统一网格）",
    writer=write_h5_single,
    requires=("*",),
    notes="材料级 h5 请用 writer.h5_writer.write_material_h5",
))
