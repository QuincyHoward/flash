"""``cn4`` 目标写出器 —— 把一张 :class:`ParsedTable` 写成 FLASH IONMIX ``.cn4``。

这是"其他文件类型 -> cn4"接入**通用转换注册表**的桥梁：

* 单表接口：表内没有的 12 个二维场 / 3 块不透明度一律 **NaN 占位**
  （12 列对齐，读回由 ``is_nan_placeholder`` 还原），绝不写 0 ——
  0 是合法物理值，会被误读为真实数据。这与
  :func:`eosop_pro.cn4.parsed_tables_to_cn4` 的跨族路径语义一致。
* 组成信息（``izgas``/``fracsp``/``atomwt``）是 cn4 头部必需，**不猜**：
  ``izgas`` 必须显式给出；``fracsp`` 仅在单元素时默认纯丰度 ``[1.0]``
  （数学必然，不是猜测），多元素必须显式给。
* 单温总 EOS（只有 ``P``/``E`` 总量的族）由组装层做 1:1 均分投影，
  保证 ``p_ion + p_ele == P`` 守恒。
* ⚠️ **单位不换算**：源族单位体系如实搬运并在 notes 记录（cn4 格式无注释
  字段，notes 只在转换当次可见），换算责任在调用方。

多表材料（如 LEDCOP 的独立不透明度表）请用文件级入口
:func:`eosop_pro.cn4.convert_foreign_to_cn4`（它聚合全部子表）；
本 writer 是"一张表进、一份 cn4 出"的注册表语义。
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from ..parsers.base import ParsedTable

__all__ = ["write_cn4_single"]


def write_cn4_single(table: ParsedTable, out_path: Path, *,
                     izgas: Sequence[int] | None = None,
                     fracsp: Sequence[float] | None = None,
                     atomwt: Sequence[float] | None = None,
                     **opts) -> Path:
    """把一张表写成 ``.cn4``（注册表 ``cn4`` 目标的 writer）。

    Args:
        table: 源表（须 ``kind`` 为 ``EOS_TOTAL`` 或 ``cn4_eos`` ——
            由 ``ConvertTarget.requires`` 门控）
        out_path: 目标路径（``.cn4`` 后缀自动补全）
        izgas: 原子序数列表（**cn4 头部必需，不猜**）
        fracsp: 丰度列表；单元素源可省（默认 ``[1.0]``）
        atomwt: 原子量列表（可选，缺省走 ``guess_atomwt``）
        **opts: 透传 :func:`eosop_pro.cn4.write_cn4`
            （``mantissa_style`` / ``write_opacities``）

    Raises:
        CN4ParseError: 缺 ``izgas`` / 多元素缺 ``fracsp`` / 无 EOS 总表
        ValueError: 传入 ``invert=True``（cn4 无需 (rho,de)->(rho,Te) 反演）
    """
    from ..parsers.cn4_io import CN4ParseError, parsed_tables_to_cn4, write_cn4

    if opts.pop("invert", None):
        raise ValueError(
            "cn4 目标不支持 invert（cn4 自变量本就是 (Te, nion)；"
            "invert 仅用于 multi_inverted_eos 的 (rho, de) 布局）")
    if opts.pop("skip_axes_check", None) is not None:
        # convert() 的具名参数不会走到这里；防御性吞掉显式误传
        raise ValueError("skip_axes_check 由 convert() 自身处理，勿传给 writer")

    if izgas is None:
        raise CN4ParseError(
            "cn4 目标需要显式 izgas（原子序数列表，cn4 头部必需，不猜）："
            "convert(table, out, target='cn4', izgas=[13]) 或 "
            "convert(table, out, izgas=[1, 6], fracsp=[0.5, 0.5])")
    if fracsp is None:
        if len(list(izgas)) == 1:
            fracsp = [1.0]                    # 单元素纯丰度：数学必然
        else:
            raise CN4ParseError(
                f"多元素源（izgas={list(izgas)}）需要显式 fracsp "
                "（归一化丰度列表，cn4 头部必需）")

    tbl = parsed_tables_to_cn4([table], atomwt=atomwt, izgas=list(izgas),
                               fracsp=list(fracsp), allow_foreign=True)
    return write_cn4(tbl, Path(out_path), **opts)
