"""FEOS .feos 原生表 -> IONMIX cn4 转换器

数据布局一手依据（终局）：feos/src/FEOS/Code/FE-01_TABTOOLS.C
``write_FEOS_format``（196-355 行）—— eosop_pro 的 ``feos_native`` 解析器
此前"数据块列序未定"（R3），本模块以源码为准完全解码::

    头部行 0（10 数）: [FileVersion, NRho, NT, Nelements, Tcalclimit,
                       Rhocalclimit, RhoRef, TRef, B0, SESAME#]
    头部行 1（10 数）: [ElectronOffset, IonOffset, Ecoh, ss_n, ss_m,
                       ss_A, ss_B, Atot, Ztot, Xtot]
    随后连续流: A[]/Z[]/X[]（各 Nelements 个） -> rho 网格 -> T 网格 ->
    16 个二维块（T 外循环、rho 内循环）: P,E,S,F | Pe,Ee,Se,Fe |
    Pi,Ei,Si,Fi | PTF,ETF,STF,FTF -> Qtot -> Q（k 最内层交错）

FEOS 单位 = cgs + eV；cn4 单位 = J/cm3（压强）/ J/g（比能）。
不透明度: FEOS 不产生 -> cn4 默认 7 群（DEFAULT_GRUPBD）**零填充**，
与项目现役 7 群表格式同构；零占位在 notes/注册描述中标注"禁止消费"。

用法:
    from feos_to_cn4 import feos_to_cn4
    cn4 = feos_to_cn4("Z13_1.00-20260101_1200.feos", "al.cn4")

    python feos_to_cn4.py <in.feos> [out.cn4] [--ngrups 7]
"""

from __future__ import annotations

import os
import sys
from dataclasses import replace
from pathlib import Path
from typing import Dict, List, Optional

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_GEN_EOS_OP = os.path.normpath(os.path.join(_SCRIPT_DIR, "..", ".."))
if _GEN_EOS_OP not in sys.path:
    sys.path.insert(0, _GEN_EOS_OP)

from eosop_pro.parsers.base import ParsedTable                       # noqa: E402
from eosop_pro.convert.cn4_write import (                            # noqa: E402
    parsed_tables_to_cn4, write_cn4)   # 2026-11-15 写侧已迁 convert/cn4_write
from eosop_pro.parsers.cn4_io import CN4ParseError                   # noqa: E402
from eosop_pro.parsers.feos_native import (                          # noqa: E402
    FEOS_BLOCKS, FeosTable, decode, positive_indices)
from eosop_pro.core.config import N_A as NA                          # noqa: E402

__all__ = ["FeosTable", "read_feos", "feos_to_cn4", "FEOS_BLOCKS"]

# FEOS(cgs) -> cn4(SI-ish) 单位换算因子
_DYNE2J_CM3 = 1.0e-7     # dyne/cm^2 = erg/cm^3 -> J/cm^3
_ERG2J_G = 1.0e-4        # erg/g -> J/g


def _default_grupbd() -> List[float]:
    """项目默认 7 群边界（gen_eos_op/generator.py DEFAULT_GRUPBD，懒加载带回退）"""
    try:
        from generator import DEFAULT_GRUPBD  # noqa: PLC0415
        return list(DEFAULT_GRUPBD)
    except Exception:                                        # noqa: BLE001
        return [1.0e-1, 1.0e0, 1.0e1, 1.0e2, 1.0e3, 1.0e4, 1.0e5]


def read_feos(path: str | os.PathLike) -> FeosTable:
    """解码 .feos 表 —— 布局知识单一事实源为
    ``eosop_pro.parsers.feos_native.decode``（write_FEOS_format 定案），
    本函数仅做异常类型适配以保持本模块 API 稳定。"""
    try:
        return decode(path)
    except CN4ParseError:
        raise
    except Exception as e:                                   # noqa: BLE001
        raise CN4ParseError(str(e)) from e


def _trim_grid(tbl: FeosTable) -> FeosTable:
    """修剪 Qstart=0.0 前导哨兵点。

    FEOS 表生成模式把 Qstart=Rhostart=Tstart=0.0 写进网格首点
    （FE-03_MAIN.C:56 + makeRTPointArray array[0]=Qstart）。cn4 的温度/密度
    轴用于对数插值，必须严格为正 -> 修剪 rho<=0 与 T<=0 的点（含整行/整列）。
    """
    t_idx, r_idx = positive_indices(tbl.t, tbl.rho)
    if len(t_idx) == tbl.nt and len(r_idx) == tbl.nrho:
        return tbl

    def trim_flat(flat: List[float]) -> List[float]:
        return [flat[j * tbl.nrho + i] for j in t_idx for i in r_idx]

    return replace(
        tbl,
        nrho=len(r_idx), nt=len(t_idx),
        rho=[tbl.rho[i] for i in r_idx], t=[tbl.t[j] for j in t_idx],
        blocks={k: trim_flat(v) for k, v in tbl.blocks.items()},
        qtot=trim_flat(tbl.qtot),
        q={k: trim_flat(v) for k, v in tbl.q.items()})


def _dzdt_central(qtot: List[float], t_axis: List[float], nrho: int) -> List[float]:
    """d(Qtot)/dT（1/eV）：T 方向中心差分，端点单侧（FLASH USED，必须真值）"""
    nt = len(t_axis)
    out: List[float] = [0.0] * (nt * nrho)
    for j in range(nt):
        for i in range(nrho):
            if j == 0:
                lo, hi, dl, dh = 0, 1, t_axis[1] - t_axis[0], 0.0
            elif j == nt - 1:
                lo, hi, dl, dh = nt - 2, nt - 1, 0.0, t_axis[nt - 1] - t_axis[nt - 2]
            else:
                lo, hi, dl, dh = j - 1, j + 1, t_axis[j] - t_axis[j - 1], t_axis[j + 1] - t_axis[j]
            denom = dl + dh
            out[j * nrho + i] = ((qtot[hi * nrho + i] - qtot[lo * nrho + i]) / denom
                                 if denom > 0 else 0.0)
    return out


def feos_to_cn4(feos_path: str | os.PathLike, out_path: str | os.PathLike, *,
                ngrups: Optional[int] = None,
                grupbd: Optional[List[float]] = None) -> Path:
    """把 .feos 表转换为 IONMIX cn4（默认群零填充，不透明度禁止消费）

    块映射（单位已换算）:
        zbar  <- Qtot / Xtot（LIB-03_TF_MIXTURE.C:123: Qtot = Σ Q_k·X_k，
                 为每**化学式单位**总电离；cn4 zbar 语义 = 每**核**平均，
                 ne=1 时 Xtot=1 无差别，混合物必须除）
        dzdt  <- d(Qtot)/dT / Xtot（FLASH USED）
        p_ion <- Pi  (dyne/cm^2 -> J/cm^3, x1e-7)
        p_ele <- Pe  (同上；FEOS 内 P = Pi + Pe，守恒)
        e_ion <- Ei  (erg/g -> J/g, x1e-4)
        e_ele <- Ee  (同上)
        其余导数/热容槽位 -> NaN 占位（eosop_pro 既有约定，FLASH ignored）

    密度轴: cn4 要求数密度 n_ion = rho * N_A / <A>（<A> = Atot / Xtot），
    经 parsed_tables_to_cn4 的跨族轴归一化完成。
    """
    tbl = read_feos(feos_path)
    raw_dims = (tbl.nt, tbl.nrho)
    tbl = _trim_grid(tbl)
    if (tbl.nt, tbl.nrho) != raw_dims:
        trim_note = (f"网格修剪: FEOS Qstart=0.0 前导哨兵点已移除 "
                     f"({raw_dims[0]}x{raw_dims[1]} -> {tbl.nt}x{tbl.nrho})")
    else:
        trim_note = ""
    nrho, nt, ne = tbl.nrho, tbl.nt, tbl.nelements
    n2d = nrho * nt

    # ── 组成: cn4 头部 izgas/fracsp/atomwt（fracsp 归一化为原子分数，
    #    保证 parsed_tables_to_cn4 的 <A> = sum(fracsp*atomwt) = 每核平均质量）──
    izgas = [int(round(zv)) for zv in tbl.z]
    xtot_x = sum(tbl.x) or 1.0
    fracsp = [xv / xtot_x for xv in tbl.x]
    atomwt = list(tbl.a)

    # ── 组装跨族 ParsedTable（字段直接用 cn4 原生标签 -> 直通映射）──
    #    zbar/dzdt 归一到每核: Qtot = Σ Q_k·X_k 是每化学式总量（FE-03:
    #    "Qtot for molecule"），cn4 zbar = 每核平均 = Qtot / Xtot
    xtot = tbl.xtot or sum(tbl.x) or 1.0
    fields = {
        "zbar": [v / xtot for v in tbl.qtot],
        "dzdt": [v / xtot for v in _dzdt_central(tbl.qtot, tbl.t, nrho)],
        "p_ion": [v * _DYNE2J_CM3 for v in tbl.blocks["Pi"]],
        "p_ele": [v * _DYNE2J_CM3 for v in tbl.blocks["Pe"]],
        "e_ion": [v * _ERG2J_G for v in tbl.blocks["Ei"]],
        "e_ele": [v * _ERG2J_G for v in tbl.blocks["Ee"]],
    }
    field_units = {"zbar": "-", "dzdt": "1/eV",
                   "p_ion": "J/cm3", "p_ele": "J/cm3",
                   "e_ion": "J/g", "e_ele": "J/g"}
    pt = ParsedTable(
        table_key=f"FEOS_{tbl.sesame_no}", kind="EOS_TOTAL", family="feos_native",
        source_relpath=Path(feos_path).name,
        table_id=tbl.sesame_no, header_raw="",
        axes={"Te": list(tbl.t), "rho": list(tbl.rho)},
        axis_units={"Te": "eV", "rho": "g/cm3"},
        axis_log10={"Te": False, "rho": False},
        fields=fields,
        field_shape={k: (nt, nrho) for k in fields},
        field_units=field_units,
        unit_source="format:FEOS (cgs+eV) -> cn4 (J/cm3, J/g)，已换算",
        layout_rule="feos_to_cn4: write_FEOS_format 源码布局（16 块 + Qtot + Q）",
    )
    pt.notes.append(
        f"FEOS 表: SESAME#={tbl.sesame_no}, grid={nt}x{nrho}, "
        f"Atot={tbl.atot:.4g}, Ztot={tbl.ztot:.4g}, Xtot={tbl.xtot:.4g}")
    pt.notes.append("dzdt 由 Qtot 对 T 数值微分（中心差分+端点单侧）后 /Xtot 归一到每核")
    if trim_note:
        pt.notes.append(trim_note)

    cn4 = parsed_tables_to_cn4([pt], izgas=izgas, fracsp=fracsp,
                               atomwt=atomwt, allow_foreign=True)

    # ── 不透明度决策: ngrups 群边界 + 零填充（write_cn4 对缺失块写 0）──
    #    默认 ngrups 由边界长度自动推导（DEFAULT_GRUPBD 7 边界 = 6 群）
    bounds = grupbd if grupbd is not None else _default_grupbd()
    if ngrups is None:
        ngrups = len(bounds) - 1
    if ngrups > 0 and len(bounds) != ngrups + 1:
        raise CN4ParseError(
            f"grupbd 长度 {len(bounds)} != ngrups+1 = {ngrups + 1}")
    cn4.ngrups = ngrups
    cn4.group_bounds = list(bounds) if ngrups > 0 else [0.0]
    cn4.opacities = {}
    cn4.notes.append(
        "⚠️ 不透明度三块为**零占位**（FEOS 不产生不透明度），禁止消费；"
        f"群边界为默认 {ngrups} 群（仅保持与现役 cn4 格式同构）")

    return write_cn4(cn4, out_path)


def _main(argv: List[str]) -> int:
    args = [a for a in argv if not a.startswith("--")]
    opts: Dict[str, object] = {}
    for i, a in enumerate(argv):
        if a == "--ngrups" and i + 1 < len(argv):
            opts["ngrups"] = int(argv[i + 1])
    if not args:
        print(__doc__)
        print("用法: python feos_to_cn4.py <in.feos> [out.cn4] [--ngrups 6]")
        return 1
    src, dst = args[0], (args[1] if len(args) > 1 else
                         os.path.splitext(args[0])[0] + ".cn4")
    cn4 = feos_to_cn4(src, dst, **opts)

    # ── 自验证: 读回 cn4 并打印摘要 ──
    from eosop_pro.parsers.cn4_io import parse_cn4
    back = parse_cn4(cn4)
    print(back.summary())
    print(f"计数: {back.n_numbers_seen} (期望 {back.n_numbers_expected})")
    print(f"已写出: {cn4}  ({os.path.getsize(cn4):,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
