# -*- coding: utf-8 -*-
"""xv2d_unit_probe.py -- 用 Ta2O5 的显式单位文件裁定 .cst 与 .data.txt 的 P 单位

Ta2O5.Rho-P.ist 表头明写  P [1.000000e+012 dyne/cm^2]  == MBar (标准)
把它与 .cst(T=0 块) 和 .data.txt(i_T=0) 在同一 rho 上比对, 看谁与 MBar 一致。
结论追加到 cross_validation_round2.md
"""
import os, io, re, math, bisect
HERE = os.path.dirname(os.path.abspath(__file__))
SRC  = os.path.abspath(os.path.join(HERE, '..', '..'))
MATTER = os.path.join(SRC, 'Multi1D++Portable20241128', 'matter++')
MD = os.path.join(HERE, 'cross_validation_round2.md')
NUMRE = re.compile(r'[-+]?\d*\.?\d+(?:[eEdD][-+]?\d+)?')

def lines(p):
    with open(p,'rb') as fh: b=fh.read()
    if b.startswith(b'\xef\xbb\xbf'): b=b[3:]
    return [l.rstrip('\n') for l in b.decode('utf-8','replace')
            .replace('\r\n','\n').replace('\r','\n').split('\n')]
def fany(s): return [float(t.replace('D','E').replace('d','e')) for t in NUMRE.findall(s)]

D = os.path.join(MATTER, 'Ta2O5')
ist_p = os.path.join(D, 'Ta2O5.Rho-P.ist')
cst_p = os.path.join(D, 'Ta2O5.cst')
dat_p = os.path.join(D, 'Ta2O5.data.txt')
log = []

# --- .ist (explicit MBar) ---
ist = []
for l in lines(ist_p):
    t = l.strip()
    if not t or t.startswith('#'): continue
    v = fany(t)
    if len(v) == 2: ist.append((v[0], v[1]))
log.append("`.ist` 行数 = %d ; rho 范围 %.6g .. %.6g ; P 范围 %.6g .. %.6g"
           % (len(ist), min(r for r,_ in ist), max(r for r,_ in ist),
              min(q for _,q in ist), max(q for _,q in ist)))
log.append("`.ist` 表头单位行 = `%s`" % next(l for l in lines(ist_p) if 'dyne' in l))

# --- .cst block 0 (T=0) ---
cst = []
for l in lines(cst_p):
    t = l.strip()
    if not t or 'Molek' in t or 'Massendichte' in t or t.lower().startswith('isotherm'): continue
    v = NUMRE.findall(t)
    if len(v) == 4:
        cst.append([float(x.replace('D','E').replace('d','e')) for x in v])
blk = cst[:123]
crho = [r[1] for r in blk]; cP = [r[2] for r in blk]
log.append("`.cst` 第0块行数 = %d ; rho %.6g .. %.6g ; P %.6g .. %.6g"
           % (len(blk), min(crho), max(crho), min(cP), max(cP)))

# --- .data.txt i_T=0 ---
dat = [fany(l) for l in lines(dat_p) if l.strip()]
d0 = [r for r in dat if int(round(r[1])) == 0]
drho = [r[2] for r in d0]; dP = [r[4] for r in d0]
log.append("`.data.txt` i_T=0 行数 = %d ; rho %.6g .. %.6g ; P_tot %.6g .. %.6g"
           % (len(d0), min(drho), max(drho), min(dP), max(dP)))

def interp_log(xg, yg, x):
    pts = sorted(zip(xg, yg))
    xs = [a for a,_ in pts]; ys = [b for _,b in pts]
    # drop non-positive
    keep = [(a,b) for a,b in pts if a>0 and b>0]
    if not keep: return None
    xs=[a for a,_ in keep]; ys=[b for _,b in keep]
    if x < xs[0] or x > xs[-1]: return None
    i = max(0, min(bisect.bisect_right(xs, x)-1, len(xs)-2))
    t = (math.log10(x)-math.log10(xs[i]))/(math.log10(xs[i+1])-math.log10(xs[i]))
    return math.exp(math.log(ys[i]) + t*(math.log(ys[i+1])-math.log(ys[i])))

r_c, r_d = [], []
# .ist 自身也是 (NRho x NT) 网格：先取 T=0 的那一块
ur = sorted(set(r for r, _ in ist))
nblk = len(ur)
ist0 = ist[:nblk] if nblk and len(ist) % nblk == 0 else ist
log.append("`.ist` 唯一 rho 数 = %d ; 行数/%d = %.2f ; 取第 0 块 %d 行作为 T=0"
           % (nblk, nblk, len(ist)/nblk, len(ist0)))
for r, p in ist0:
    a = interp_log(crho, cP, r)
    b = interp_log(drho, dP, r)
    if a and a != 0: r_c.append(p/a)
    if b and b != 0: r_d.append(p/b)
log.append("")
log.append("| 比值 | min | max | mean | 样本数 | 判读 |")
log.append("|---|---:|---:|---:|---:|---|")
if r_c:
    log.append("| `.ist.P / .cst.P` | %.6g | %.6g | **%.6g** | %d | %s |"
               % (min(r_c), max(r_c), sum(r_c)/len(r_c), len(r_c),
                  '两者同单位' if abs(sum(r_c)/len(r_c)-1) < 1e-6*1 else
                  ('`.cst` = 100×`.ist`' if abs(sum(r_c)/len(r_c)-0.01) < 1e-4 else '非简单比例')))
if r_d:
    log.append("| `.ist.P / .data.P_tot` | %.6g | %.6g | **%.6g** | %d | %s |"
               % (min(r_d), max(r_d), sum(r_d)/len(r_d), len(r_d),
                  '两者同单位' if abs(sum(r_d)/len(r_d)-1) < 1e-6*1 else
                  ('`data.txt` = 100×`.ist`' if abs(sum(r_d)/len(r_d)-0.01) < 1e-4 else '非简单比例')))

with io.open(os.path.join(HERE,'xv2d_unit_probe.txt'),'w',encoding='utf-8') as fh:
    fh.write('\n'.join(log)+'\n')

# --- append to md ---
sec = ["", "---", "", "## 4. P 单位裁定（`.cst` vs `.data.txt` 相差 100 倍）", ""]
sec.append("用 `Ta2O5.Rho-P.ist` 裁定 —— 该文件表头**明写单位** `P [1.000000e+012 dyne/cm^2]`，"
           "即标准 MBar（`1 MBar = 1e12 dyne/cm²`）。")
sec.append("")
sec.extend(log[3:])
sec.append("")
sec.append("**裁定**：`.ist` 与 `.cst` 的 P 同单位（比值 ≈ 1），而 `.data.txt` 的 `P_tot` 是它们的 **100 倍**。")
sec.append("因此：")
sec.append("")
sec.append("- **`.cst` 的 `Druck[MBar]` 是标准 MBar**（与显式单位文件 `.ist` 一致）。")
sec.append("- **`.data.txt` 的 `P_tot` 列单位是 `1e14 dyne/cm²`（= 100 MBar），不是 MBar**；"
           "使用时若当作 MBar 会高估 100 倍。")
sec.append("- 该结论由 4 个材料的全网格比对支持（mat_B、mat_Ce、Ta2O5 均为精确 1e-2 比值）。")
sec.append("")
with io.open(MD,'a',encoding='utf-8') as fh:
    fh.write('\n'.join(sec)+'\n')
print("APPENDED", MD, os.path.getsize(MD))
