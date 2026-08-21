# -*- coding: utf-8 -*-
"""
IONMIX eos.cn4 / *.cn4 数据文件解析模块
========================================

解析 IONMIX (abjt_03) 输出的 CONRAD 格式数据表 (.cn4)。
格式定义见 src/Ionmix/abjt_03.f 中 SUBROUTINE OWTF (unit=123, isw(21)!=0 分支)。

文件布局 (数据块均以 4e12.6 无分隔符写出):
    line 1 : ntemp, ndens            (2i10)
    line 2 : izgas(...)               (a80, " atomic #s of gases: ...")
    line 3 : fracsp(...)              (a80, " relative fractions: ...")
    line 4 : ngrups                   (i12)
    block 1 : tplsma(1..ntemp)        温度数组 (eV)
    block 2 : densnn(1..ndens)        核子数密度数组 (cm^-3)
    block 3 : zbar = ne/ntot          (ntemp*ndens, 温度内循环、密度外循环)
    block 4 : dzdt                    (ntemp*ndens)
    block 5 : ion pressure            (ntemp*ndens, J/cm^3)
    block 6 : electron pressure       (ntemp*ndens, J/cm^3)
    block 7 : d(pion)/dT              (ntemp*ndens)
    block 8 : d(pele)/dT              (ntemp*ndens)
    block 9 : enrgyion                (ntemp*ndens, J/g)
    block 10: enrgyele                (ntemp*ndens, J/g)
    block 11: heatcpion               (ntemp*ndens, J/g/eV)
    block 12: heatcpele               (ntemp*ndens, J/g/eV)
    block 13: d(eion)/d(nion)         (ntemp*ndens)
    block 14: d(eele)/d(nele)         (ntemp*ndens)
    block 15: engrup(1..ngrups+1)     能群边界 (eV)
    block 16: Rosseland 群不透明度     (ngrups*ntemp*ndens, 群外循环)
    block 17: Planck 吸收群不透明度    (ngrups*ntemp*ndens)
    block 18: Planck 发射群不透明度    (ngrups*ntemp*ndens)

二维场存储顺序: 温度内循环 (it=1..ntemp)、密度外循环 (id=1..ndens)
    -> 可用 .reshape(ndens, ntemp) 得到 (行=密度, 列=温度) 的 2D 数组
三维不透明度场: 群外循环、温度中循环、密度内循环
    -> 可用 .reshape(ngrups, ndens, ntemp) 得到 (群, 密度, 温度)
"""

import os
import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import numpy as np

# 阿伏伽德罗常数 (1/mol)
_NA = 6.02214076e23

# 经典元素原子量表 (amu), 键为原子序数 Z。
# 用于从 izgas 自动派生平均原子量, 避免对特定材料 (如 CH) 硬编码。
# 数据来源: IUPAC 标准原子量 (常用值)。
_ELEMENT_ATOMWT = {
    1: 1.008,       # H
    2: 4.002602,    # He
    3: 6.94,        # Li
    4: 9.0122,      # Be
    5: 10.81,       # B
    6: 12.011,      # C
    7: 14.007,      # N
    8: 15.999,      # O
    9: 18.9984032,  # F
    10: 20.1797,    # Ne
    11: 22.98976928,# Na
    12: 24.305,     # Mg
    13: 26.9815385, # Al
    14: 28.085,     # Si
    15: 30.973761998,# P
    16: 32.06,      # S
    17: 35.45,      # Cl
    18: 39.948,     # Ar
    19: 39.0983,    # K
    20: 40.078,     # Ca
    21: 44.955912,  # Sc
    22: 47.867,     # Ti
    23: 50.9415,    # V
    24: 51.9961,    # Cr
    25: 54.938044,  # Mn
    26: 55.845,     # Fe
    27: 58.933194,  # Co
    28: 58.6934,    # Ni
    29: 63.546,     # Cu
    30: 65.38,      # Zn
    47: 107.8682,   # Ag
    79: 196.966569, # Au
    82: 207.2,      # Pb
}

# 头部行内的科学计数法数字 (相对丰度等, 宽松匹配即可)
_NUM_RE = re.compile(r"[-+]?\d+\.\d+[EeDd][-+]?\d+")

# ionmxinp 中 atomwt 行: "    atomwt(1) = 12.011000, ..."
_ATOMWT_RE = re.compile(
    r"atomwt\s*\(\s*(\d+)\s*\)\s*=\s*([-+]?\d*\.?\d+(?:[EeDd][-+]?\d+)?)"
)

# Fortran 4e12.6 格式: 每个数字固定占 12 列, 数字紧贴无分隔符
_FLOAT_WIDTH = 12


def _parse_fixed_width(line: str) -> List[float]:
    """
    按 Fortran e12.6 固定宽度解析一行数据。
    每 12 字符为一个科学计数法数字 (如 '0.100000E+01')。
    """
    out = []
    s = line.rstrip("\r\n")
    for i in range(0, len(s) - _FLOAT_WIDTH + 1, _FLOAT_WIDTH):
        chunk = s[i:i + _FLOAT_WIDTH].strip()
        if chunk:
            out.append(float(chunk.replace("D", "E")))
    return out


@dataclass
class CN4Data:
    """IONMIX .cn4 文件的结构化数据容器"""

    filepath: str
    ntemp: int
    ndens: int
    ngrups: int
    ngases: int
    izgas: np.ndarray                # (ngases,) 原子序数
    fracsp: np.ndarray               # (ngases,) 原子数丰度
    atomwt: Optional[np.ndarray]     # (ngases,) 原子量 amu; 未知时为 None
    temperature: np.ndarray          # (ntemp,) eV, 升序
    density: np.ndarray              # (ndens,) cm^-3, 升序
    zbar: np.ndarray                 # (ndens, ntemp) 平均电荷态 (电离度)
    dzdt: np.ndarray                 # (ndens, ntemp) d<Z>/dT (1/eV)
    p_ion: np.ndarray                # (ndens, ntemp) 离子压力 J/cm^3
    p_ele: np.ndarray                # (ndens, ntemp) 电子压力 J/cm^3
    dpion_dt: np.ndarray             # (ndens, ntemp) d(离子压力)/dT
    dpele_dt: np.ndarray             # (ndens, ntemp) d(电子压力)/dT
    e_ion: np.ndarray                # (ndens, ntemp) 离子比内能 J/g
    e_ele: np.ndarray                # (ndens, ntemp) 电子比内能 J/g
    cv_ion: np.ndarray               # (ndens, ntemp) 离子比热 J/g/eV
    cv_ele: np.ndarray               # (ndens, ntemp) 电子比热 J/g/eV
    deion_dn: np.ndarray             # (ndens, ntemp) d(e_ion)/d(nion)
    deele_dn: np.ndarray             # (ndens, ntemp) d(e_ele)/d(nele)
    group_bounds: np.ndarray         # (ngrups+1,) 能群边界 eV
    opac_rosseland: np.ndarray       # (ngrups, ndens, ntemp) cm^2/g
    opac_planck_abs: np.ndarray      # (ngrups, ndens, ntemp) cm^2/g
    opac_planck_ems: np.ndarray      # (ngrups, ndens, ntemp) cm^2/g

    @property
    def basename(self) -> str:
        """不带扩展名的文件名"""
        return os.path.splitext(os.path.basename(self.filepath))[0]

    @property
    def avgatw(self) -> Optional[float]:
        """平均原子量 (amu): sum(fracsp * atomwt); 原子量未知时返回 None"""
        if self.atomwt is None:
            return None
        return float(np.sum(self.fracsp * self.atomwt))

    @property
    def nele(self) -> np.ndarray:
        """电子数密度 (ndens, ntemp), cm^-3 = zbar * ntot"""
        return self.zbar * self.density[:, None]

    @property
    def rho(self) -> np.ndarray:
        """物质密度 (ndens, ntemp), g/cm^3 = ntot * avgatw / N_A"""
        aw = self.avgatw
        if aw is None:
            raise ValueError("原子量未知, 无法计算物质密度 rho. "
                             "请提供 atomwt (load_cn4(..., atomwt=[...]))")
        rho_1d = self.density * aw / _NA            # (ndens,)
        return np.broadcast_to(rho_1d[:, None], self.zbar.shape)

    @property
    def species_label(self) -> str:
        """成分标签, 如 'C(50%) + H(50%)'"""
        names = []
        for iz, fr in zip(self.izgas, self.fracsp):
            names.append(f"Z{iz}({fr*100:.0f}%)")
        return " + ".join(names)

    def quantity(self, name: str) -> np.ndarray:
        """按名称获取二维物理量场 (ndens, ntemp), 便于后续扩展"""
        aliases = {
            "zbar": self.zbar, "z": self.zbar, "charge": self.zbar,
            "dzdt": self.dzdt, "dzdT": self.dzdt,
            "p_ion": self.p_ion, "pion": self.p_ion,
            "p_ele": self.p_ele, "pele": self.p_ele,
            "dpion_dt": self.dpion_dt,
            "dpele_dt": self.dpele_dt,
            "e_ion": self.e_ion, "eion": self.e_ion,
            "e_ele": self.e_ele, "eele": self.e_ele,
            "cv_ion": self.cv_ion, "cvion": self.cv_ion,
            "cv_ele": self.cv_ele, "cvele": self.cv_ele,
            "deion_dn": self.deion_dn,
            "deele_dn": self.deele_dn,
            "nele": self.nele, "ne": self.nele, "electron_density": self.nele,
            "rho": self.rho, "rhoe": self.rho, "mass_density": self.rho,
        }
        if name.lower() not in aliases:
            raise KeyError(
                f"未知物理量 '{name}'. 可选: {sorted(set(v for v in aliases))}"
            )
        return aliases[name.lower()]

    def group_opacity(self, name: str, ig: int) -> np.ndarray:
        """按名称+群号获取三维不透明度场 (ndens, ntemp)"""
        opts = {
            "rosseland": self.opac_rosseland,
            "planck_abs": self.opac_planck_abs,
            "planck_ems": self.opac_planck_ems,
        }
        if name.lower() not in opts:
            raise KeyError(f"未知不透明度 '{name}'. 可选: {list(opts)}")
        if not 1 <= ig <= self.ngrups:
            raise ValueError(f"群号 ig 越界: 1..{self.ngrups}")
        return opts[name.lower()][ig - 1]


def _parse_header_lines(lines: List[str]) -> Tuple[int, int, List[int], List[float], int]:
    """解析前 4 行头部, 返回 (ntemp, ndens, izgas, fracsp, ngrups)"""
    # line 1: ntemp, ndens (2i10)
    ntemp, ndens = map(int, lines[0].split()[:2])
    # line 2: " atomic #s of gases:  6  1"
    izgas = [int(x) for x in lines[1].split()[4:]]
    # line 3: " relative fractions:   5.00E-01  5.00E-01"
    fracsp = [float(x) for x in _NUM_RE.findall(lines[2])]
    # line 4: ngrups (i12)
    ngrups = int(lines[3].split()[0])
    ngases = len(izgas)
    if len(fracsp) != ngases:
        raise ValueError(
            f"头部解析不一致: izgas 数量 {ngases} != fracsp 数量 {len(fracsp)}"
        )
    return ntemp, ndens, izgas, fracsp, ngrups


def guess_atomwt(izgas: List[int]) -> Optional[np.ndarray]:
    """
    根据原子序数列表猜测原子量 (amu), 查经典元素表。
    所有 Z 均在表中时返回数组; 否则返回 None (调用方需用户显式传入)。
    """
    vals = []
    for z in izgas:
        if z in _ELEMENT_ATOMWT:
            vals.append(_ELEMENT_ATOMWT[z])
        else:
            return None
    return np.array(vals, dtype=float)


def _parse_atomwt_from_ionmxinp(dirpath: str, ngases: int) -> Optional[np.ndarray]:
    """
    从同目录 ionmxinp 文件中解析 atomwt (amu)。
    找不到或解析不全时返回 None。
    """
    inp = os.path.join(dirpath, "ionmxinp")
    if not os.path.exists(inp):
        return None
    values = {}
    with open(inp, "r") as f:
        for line in f:
            m = _ATOMWT_RE.search(line)
            if m:
                values[int(m.group(1))] = float(m.group(2).replace("D", "E"))
    if len(values) != ngases:
        return None
    return np.array([values[i] for i in range(1, ngases + 1)], dtype=float)


def load_cn4(filepath: str, atomwt: Optional[List[float]] = None) -> CN4Data:
    """
    解析 .cn4 文件为 CN4Data 对象。

    Args:
        filepath: .cn4 文件路径
        atomwt: 各气体原子量 (amu) 列表, 顺序与 izgas 一致。
                缺省时自动尝试从同目录 ionmxinp 读取; 均不可得则为 None
                (此时 nele 仍可用, 但 rho 会抛出 ValueError)。

    Returns:
        CN4Data: 结构化数据
    """
    filepath = os.path.abspath(filepath)
    with open(filepath, "r") as f:
        all_lines = f.readlines()

    ntemp, ndens, izgas, fracsp, ngrups = _parse_header_lines(all_lines[:4])

    # 头部之后的所有数据行: 按固定 12 列宽度解析每个 e12.6 数字
    values = []
    for ln in all_lines[4:]:
        values.extend(_parse_fixed_width(ln))
    values = np.array(values)

    # 各块大小
    n2d = ntemp * ndens          # 二维场元素数
    n3d = ngrups * n2d           # 三维不透明度元素数
    n_2d_fields = 12             # 源码中 12 个二维物理量块 (zbar..deele_dn)
    expected = (
        ntemp + ndens + n_2d_fields * n2d + (ngrups + 1) + 3 * n3d
    )
    if len(values) != expected:
        raise ValueError(
            f"数值个数不匹配: 实际 {len(values)}, 期望 {expected} "
            f"(ntemp={ntemp}, ndens={ndens}, ngrups={ngrups})"
        )

    pos = 0

    def take(n: int) -> np.ndarray:
        nonlocal pos
        block = values[pos:pos + n]
        pos += n
        return block

    temperature = take(ntemp)
    density = take(ndens)

    # 12 个二维场: 温度内循环、密度外循环 -> reshape(ndens, ntemp)
    two_d_fields = [take(n2d).reshape(ndens, ntemp) for _ in range(n_2d_fields)]
    (zbar, dzdt, p_ion, p_ele, dpion_dt, dpele_dt,
     e_ion, e_ele, cv_ion, cv_ele, deion_dn, deele_dn) = two_d_fields

    group_bounds = take(ngrups + 1)

    # 三维不透明度: 群外循环 -> reshape(ngrups, ndens, ntemp)
    opac_rosseland = take(n3d).reshape(ngrups, ndens, ntemp)
    opac_planck_abs = take(n3d).reshape(ngrups, ndens, ntemp)
    opac_planck_ems = take(n3d).reshape(ngrups, ndens, ntemp)

    if pos != len(values):
        raise ValueError(f"解析后仍有 {len(values) - pos} 个数值未消费")

    # 原子量: 优先用户传入, 其次从同目录 ionmxinp, 最后查经典元素表
    atomwt_arr = None
    if atomwt is not None:
        if len(atomwt) != len(izgas):
            raise ValueError(
                f"atomwt 长度 {len(atomwt)} 与气体数 {len(izgas)} 不一致"
            )
        atomwt_arr = np.array(atomwt, dtype=float)
    else:
        atomwt_arr = _parse_atomwt_from_ionmxinp(
            os.path.dirname(filepath), len(izgas)
        )
        if atomwt_arr is None:
            atomwt_arr = guess_atomwt(izgas)

    return CN4Data(
        filepath=filepath,
        ntemp=ntemp,
        ndens=ndens,
        ngrups=ngrups,
        ngases=len(izgas),
        izgas=np.array(izgas),
        fracsp=np.array(fracsp),
        atomwt=atomwt_arr,
        temperature=temperature,
        density=density,
        zbar=zbar,
        dzdt=dzdt,
        p_ion=p_ion,
        p_ele=p_ele,
        dpion_dt=dpion_dt,
        dpele_dt=dpele_dt,
        e_ion=e_ion,
        e_ele=e_ele,
        cv_ion=cv_ion,
        cv_ele=cv_ele,
        deion_dn=deion_dn,
        deele_dn=deele_dn,
        group_bounds=group_bounds,
        opac_rosseland=opac_rosseland,
        opac_planck_abs=opac_planck_abs,
        opac_planck_ems=opac_planck_ems,
    )


def load_cn4_dir(dirpath: str) -> List[CN4Data]:
    """解析目录下所有 .cn4 文件, 返回 CN4Data 列表"""
    results = []
    if os.path.isdir(dirpath):
        for fname in sorted(os.listdir(dirpath)):
            if fname.endswith(".cn4"):
                results.append(load_cn4(os.path.join(dirpath, fname)))
    return results


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("用法: python cn4_parser.py <file.cn4>")
        sys.exit(1)
    data = load_cn4(sys.argv[1])
    print(f"文件      : {data.basename}")
    print(f"网格      : ntemp={data.ntemp}, ndens={data.ndens}, ngrups={data.ngrups}")
    print(f"成分      : {data.species_label}")
    print(f"温度范围  : {data.temperature[0]:.3e} ~ {data.temperature[-1]:.3e} eV")
    print(f"密度范围  : {data.density[0]:.3e} ~ {data.density[-1]:.3e} cm^-3")
    print(f"zbar 范围 : {data.zbar.min():.4f} ~ {data.zbar.max():.4f}")
