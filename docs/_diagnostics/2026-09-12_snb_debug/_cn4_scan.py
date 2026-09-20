# -*- coding: utf-8 -*-
"""按 FLASH 权威读法解析 cn4: 行0=(nTemp,nDens); 轴1=温度(eV), 轴2=密度(g/cm3)。
扫描全部候选表, 报告 (Tmin_K, Tmax_K, rho_min, rho_max) 与元素组成,
并判断本仿真域 rho∈[1e-6,1] g/cm3 / T=290K 是否落在表内。
"""
import io, os, glob, re

WS = r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash"
OUT = WS + r"\_cn4_scan.txt"
K = 11604.5221

# 候选表: 重点看这些
CANDS = [
    r"flash\scenarios\private\tracer\SNB\SNBOneCH_ml\flash_input\CH-BADGER-TOPS-Final.cn4",
    r"flash\scenarios\private\tracer\SNB\SNBOneCH_ml\flash_input\He-BADGER-TOPS-Final.cn4",
    r"flash\scenarios\private\tracer\SNB\SNBOneCH_ml\flash_input\CH-QC-1-001.cn4",
    r"flash\input_gen\gen_eos_op\eos_op_data\Others_data\CH-BADGER-TOPS-Final.cn4",
    r"flash\input_gen\gen_eos_op\eos_op_data\Others_data\He-BADGER-TOPS-Final.cn4",
    r"flash\input_gen\gen_eos_op\eos_op_data\Others_data\Ti-BADGER-TOPS.cn4",
    r"flash\input_gen\gen_eos_op\eos_op_data\Others_data\V-BADGER-TOPS.cn4",
    r"flash\input_gen\gen_eos_op\ionmix\ionmix\src\Ionmix\CH-QC-1-001.cn4",
    r"flash\input_gen\gen_eos_op\ionmix\ionmix\src\Ionmix\he-imx-005.cn4",
    r"flash\input_gen\gen_eos_op\ionmix\ionmix\src\Ionmix\polystyrene-imx-008.cn4",
]

def read_axes(p):
    """返回 (nTemp, nDens, Zlist, fracs, temps_eV, dens) 或 None。"""
    raw = io.open(p, "r", encoding="utf-8", errors="replace").read().splitlines()
    if len(raw) < 8:
        return None
    m = re.match(r"\s*(\d+)\s+(\d+)\s*$", raw[0])
    if not m:
        return None
    nT, nD = int(m.group(1)), int(m.group(2))
    z = [int(x) for x in re.findall(r"\d+", raw[1])]
    fr = [float(x) for x in re.findall(r"\d+\.\d+E[+-]\d+", raw[2])]
    # 数字块从行 4 开始 (行3 = ngroups)
    def nums_from(start, count):
        vals, i = [], start
        while len(vals) < count and i < len(raw):
            s = raw[i].strip()
            # 每 12 字符一列
            for j in range(0, len(s), 12):
                tok = s[j:j+12].strip()
                if not tok:
                    continue
                try:
                    vals.append(float(tok))
                except Exception:
                    pass
            i += 1
        return vals[:count], i
    temps, nxt = nums_from(4, nT)
    dens, _ = nums_from(nxt, nD)
    return nT, nD, z, fr, temps, dens

L = [f"{'table':<34} {'nT':>3} {'nD':>3}  {'Z':<12} {'T_min(eV)':>10} {'T_max(eV)':>10} "
     f"{'rho_min':>10} {'rho_max':>10}  IN?"]
L.append("-" * 130)

for rel in CANDS:
    p = os.path.join(WS, rel)
    name = os.path.basename(rel)
    if not os.path.exists(p):
        L.append(f"{name:<34} NOT FOUND")
        continue
    r = read_axes(p)
    if not r:
        L.append(f"{name:<34} PARSE FAIL")
        continue
    nT, nD, z, fr, temps, dens = r
    if not temps or not dens:
        L.append(f"{name:<34} nT={nT} nD={nD} AXIS FAIL temps={len(temps)} dens={len(dens)}")
        continue
    tmin, tmax = temps[0], temps[-1]
    dmin, dmax = dens[0], dens[-1]
    # 判断覆盖性
    inrho = (1e-6 >= dmin) and (1.0 <= dmax)
    inT = (290.0 / K >= tmin) and (290.0 / K <= tmax)
    ok = "YES" if (inrho and inT) else ("rho-OUT" if not inrho else "T-OUT")
    zs = ",".join(str(x) for x in z)
    L.append(f"{name:<34} {nT:>3} {nD:>3}  {zs:<12} {tmin:>10.3e} {tmax:>10.3e} "
             f"{dmin:>10.3e} {dmax:>10.3e}  {ok}")

L.append("")
L.append("本仿真需求: rho in [1e-6, 1.0] g/cm3 ; T0 = 290.11 K = 2.5e-2 eV")
L.append("判定规则: 需 dmin <= 1e-6 且 dmax >= 1.0 ; 且 tmin <= 2.5e-2 eV <= tmax")

io.open(OUT, "w", encoding="utf-8").write("\n".join(L))
print("\n".join(L))
