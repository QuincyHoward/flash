# -*- coding: utf-8 -*-
"""精确解析 IONMIX4 cn4: 密度轴 / 温度轴 / 原子序数 / 分组数。
格式 (FLASH eos_tabBrowseIonmix4Tables):
  行0: nDens nTemp
  行1: atomic #s of gases: Z1 Z2 ...
  行2: relative fractions: f1 f2 ...
  行3: nGroups
  之后: 密度轴 (首个数字块, 固定宽度 13 字符, 可有多个/行)
  再后: 温度轴
FLASH 的 IONMIX4 温度轴单位是 **eV**。
"""
import io, os

WS = r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash"
OUT = WS + r"\_cn4_axes.txt"

TABLES = [
    r"flash\scenarios\private\tracer\SNB\SNBOneCH_ml\flash_input\CH-BADGER-TOPS-Final.cn4",
    r"flash\scenarios\private\tracer\SNB\SNBOneCH_ml\flash_input\He-BADGER-TOPS-Final.cn4",
    r"flash\scenarios\private\tracer\SNB\SNBOneCH_ml\flash_input\CH-QC-1-001.cn4",
    r"flash\input_gen\gen_eos_op\ionmix\ionmix\src\Ionmix\CH-QC-1-001.cn4",
]

def parse_fixed(txt):
    """IONMIX 数字按 13 字符定宽。"""
    vals = []
    for i in range(0, len(txt), 13):
        s = txt[i:i+13].strip()
        if not s:
            continue
        try:
            vals.append(float(s))
        except Exception:
            pass
    return vals

L = []
for rel in TABLES:
    p = os.path.join(WS, rel)
    L.append(f"######## {os.path.basename(rel)}")
    if not os.path.exists(p):
        L.append(f"   NOT FOUND: {p}\n")
        continue
    raw = io.open(p, "r", encoding="utf-8", errors="replace").read().splitlines()
    hdr = raw[:4]
    L.append(f"   [{0}] {hdr[0]!r}")
    L.append(f"   [{1}] {hdr[1]!r}")
    L.append(f"   [{2}] {hdr[2]!r}")
    L.append(f"   [{3}] {hdr[3]!r}")
    nD, nT = [int(x) for x in hdr[0].split()]
    # 密度轴从行 4 开始, 共 nD 个数 (13 字符宽, 4/行)
    dens_txt = "".join(raw[4:4 + (nD * 13 + 79) // 80 + 2])
    dens = parse_fixed(dens_txt)[:nD]
    # 温度轴紧随其后
    start = 4 + (nD * 13 + 79) // 80 + 2
    temp_txt = "".join(raw[start:start + (nT * 13 + 79) // 80 + 2])
    temp = parse_fixed(temp_txt)[:nT]
    L.append(f"   nDens={nD} nTemp={nT}")
    if dens:
        L.append(f"   DENSITY: min={dens[0]:.4e} max={dens[-1]:.4e}  ({len(dens)} pts)")
        L.append(f"            first5={['%.3e'%v for v in dens[:5]]}")
        L.append(f"            last5 ={['%.3e'%v for v in dens[-5:]]}")
    else:
        L.append("   DENSITY: parse failed")
    if temp:
        L.append(f"   TEMP   : min={temp[0]:.4e} max={temp[-1]:.4e}  ({len(temp)} pts)")
        L.append(f"            first5={['%.3e'%v for v in temp[:5]]}")
        L.append(f"            last5 ={['%.3e'%v for v in temp[-5:]]}")
    else:
        L.append("   TEMP   : parse failed")
    L.append("")

io.open(OUT, "w", encoding="utf-8").write("\n".join(L))
print("WROTE", OUT)
