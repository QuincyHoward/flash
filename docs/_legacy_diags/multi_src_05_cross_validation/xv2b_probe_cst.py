# -*- coding: utf-8 -*-
"""
xv2b_probe_cst.py -- 判定 .cst 到底是「单条 T=0 等温线」还是「完整 (rho,T) 网格」
方法: 用行数 vs NRho*NT 的关系 + rho 列的周期检验 + 固定 rho 下 P 随块号单调性
"""
import os, io, re, math
from collections import Counter
HERE = os.path.dirname(os.path.abspath(__file__))
SRC  = os.path.abspath(os.path.join(HERE, '..', '..'))
MATTER = os.path.join(SRC, 'Multi1D++Portable20241128', 'matter++')
OUT = os.path.join(HERE, 'xv2b_probe_cst.txt')
NUMRE = re.compile(r'[-+]?\d*\.?\d+(?:[eEdD][-+]?\d+)?')
NA = 6.02214076e23
MU = 1.66053906660e-24

def whole(p):
    with open(p,'rb') as fh:
        b = fh.read()
    if b.startswith(b'\xef\xbb\xbf'): b = b[3:]
    return b.decode('utf-8','replace')

def lines(t):
    return [l.rstrip('\n') for l in t.replace('\r\n','\n').replace('\r','\n').split('\n')]

def cst_rows(p):
    rows = []
    for l in lines(whole(p)):
        t = l.strip()
        if not t or 'Molek' in t or 'Massendichte' in t or 'Particle density' in t \
           or t.lower().startswith('isotherm'):
            continue
        v = NUMRE.findall(t)
        if len(v) == 4:
            rows.append([float(x.replace('D','E').replace('d','e')) for x in v])
        elif len(v) > 4 and len(v) % 4 == 0:
            for i in range(0, len(v), 4):
                rows.append([float(x.replace('D','E').replace('d','e')) for x in v[i:i+4]])
    return rows

def feos_hdr(p):
    ls = [l for l in lines(whole(p)[:8192]) if l.strip()]
    def f15(s):
        o=[]
        for i in range(0,len(s),15):
            c=s[i:i+15].strip()
            if not c: continue
            try: o.append(float(c.replace('D','E').replace('d','e')))
            except ValueError:
                for t in NUMRE.findall(c): o.append(float(t.replace('D','E').replace('d','e')))
        return o
    h0=f15(ls[0]); h1=f15(ls[1])
    return int(round(h0[1])), int(round(h0[2])), (h1[7] if len(h1)>7 else None)

def data_cols(p):
    ls=[l for l in lines(whole(p)) if l.strip()]
    return [[float(t.replace('D','E').replace('d','e')) for t in NUMRE.findall(l)] for l in ls]

L=[]
def P(s=''): L.append(str(s))

CASES = [
 ('mat_B',  r'mat_B\B.cst',       r'mat_B\B.data.txt'),
 ('mat_Ce', r'mat_Ce\Cerium.cst', r'mat_Ce\Cerium.data.txt'),
 ('mat_He', r'mat_He\Untitled.CST', None),
 ('mat_Al-1.0', None, None),
]

P("判定 .cst 的记录结构")
P("="*96)
for mat, cstrel, datrel in CASES:
    P("")
    P("-"*96)
    if cstrel is None:
        # find a .cst
        d=os.path.join(MATTER,mat)
        cand=[f for f in os.listdir(d) if f.lower().endswith(('.cst',))]
        if not cand: P("MAT %s: 无 .cst"%mat); continue
        cstrel=os.path.join(mat,cand[0])
    p=os.path.join(MATTER,cstrel)
    if not os.path.exists(p):
        P("MISSING %s"%cstrel); continue
    rows=cst_rows(p)
    n=len(rows)
    rhos=[r[1] for r in rows]
    ns=[r[0] for r in rows]
    ur=sorted(set(rhos)); un=sorted(set(ns))
    P("FILE %s   n_rows=%d" % (cstrel, n))
    P("  唯一 rho 值 = %d ; 唯一 数密度 值 = %d" % (len(ur), len(un)))
    if len(ur)>1:
        P("  n_rows / 唯一rho = %.4f" % (n/len(ur)))
    # .feos
    fe=None
    d=os.path.dirname(p)
    for f in sorted(os.listdir(d)):
        if f.lower().endswith('.feos'):
            NR,NT,At=feos_hdr(os.path.join(d,f))
            fe=(f,NR,NT,At); break
    if fe:
        P("  同目录 .feos %s : NRho=%d NT=%d Atot=%s" % fe)
        P("  >>> NRho*NT = %d ; n_rows = %d ; 相等? %s" % (fe[1]*fe[2], n, fe[1]*fe[2]==n))
        if fe[1]>0:
            P("  n_rows / NRho = %.4f  (若为整数且 = NT 则 T 为外层)" % (n/fe[1]))
        if fe[2]>0:
            P("  n_rows / NT   = %.4f  (若为整数且 = NRho 则 rho 为外层)" % (n/fe[2]))
    # period tests
    R=len(ur)
    for lbl, per in (('rho 内层 (T外层), period=NRho', R),
                     ('数密度 内层, period=唯一n', len(un))):
        if per>0 and per<n:
            ok=0; tot=0
            for i in range(0, min(n-per, 4000)):
                tot+=1
                if abs(rhos[i]-rhos[i+per])<=1e-9*max(1,abs(rhos[i])): ok+=1
            P("  周期检验 [%s] period=%d : 匹配 %d/%d = %.1f%%" % (lbl, per, ok, tot, 100.0*ok/max(1,tot)))
    # if T outer: reshape (NT, NR) and test P monotonic in block index at fixed rho
    if fe and fe[1]>0 and n % fe[1]==0:
        NTb=n//fe[1]; NRb=fe[1]
        P("  重塑为 (%d 块 × %d 行) ，每块第 0 个 rho = %.6g / %.6g / %.6g / %.6g"
          % (NTb, NRb, rows[0][1], rows[NRb][1] if NRb<n else -1,
             rows[2*NRb][1] if 2*NRb<n else -1, rows[3*NRb][1] if 3*NRb<n else -1))
        # P at fixed rho index across blocks
        for ridx in (0, 5, 20, 60, 100, 120):
            if ridx>=NRb: continue
            series=[rows[b*NRb+ridx][2] for b in range(NTb)]
            mono=all(series[i]<=series[i+1] for i in range(len(series)-1))
            P("     rho[%3d]=%10.5g  P 首/中/末 = %10.4g / %10.4g / %10.4g  单调增=%s"
              % (ridx, rows[ridx][1], series[0], series[NTb//2], series[-1], mono))
    # data.txt grid overlap with tolerance
    if datrel:
        dc=data_cols(os.path.join(MATTER,datrel))
        P("  对照 %s : %d 行 × %d 列" % (datrel, len(dc), len(dc[0])))
        # candidate rho column = cardinality == .feos NRho
        card=[len(set(round(r[c],12) for r in dc)) for c in range(len(dc[0]))]
        P("    各列基数 = %s" % card)
        tgt = fe[1] if fe else None
        ccol = None
        for c,cd in enumerate(card):
            if tgt and cd==tgt: ccol=c; break
        if ccol is not None:
            cand=sorted(set(r[ccol] for r in dc))
            oneblk=[rows[i][1] for i in range(min(R,len(rows)))]
            one=sorted(set(oneblk))
            # tolerance match
            import bisect
            hit=0
            for x in one:
                j=bisect.bisect_left(cand,x)
                near=False
                for k in (j-1,j,j+1):
                    if 0<=k<len(cand) and abs(cand[k]-x)<=1e-6*max(abs(x),1e-30):
                        near=True;break
                if near: hit+=1
            P("    .cst 单块 rho(%d 个) 与 data.txt col%d(%d 个) 在 rtol=1e-6 下匹配: %d/%d = %.1f%%"
              % (len(one), ccol, len(cand), hit, len(one), 100.0*hit/max(1,len(one))))
            P("    .cst 单块 rho 范围 %.6g .. %.6g" % (min(one),max(one)))
            P("    data col%d 范围    %.6g .. %.6g" % (ccol,min(cand),max(cand)))
            # 逐位(listwise)比对
            if len(one)==len(cand):
                same=sum(1 for a,b in zip(one,cand) if abs(a-b)<=1e-9*max(abs(a),1e-30))
                P("    逐位(index-wise)一致个数 = %d/%d" % (same,len(one)))
    # A_eff
    vals=[r[1]*NA/r[0] for r in rows if r[0]>0 and r[1]>0]
    if vals:
        P("  A_eff = %.6f (mean, n=%d) ; Atot=%s ; 偏差=%.4f%%" %
          (sum(vals)/len(vals), len(vals), fe[3] if fe else None,
           ((sum(vals)/len(vals)-fe[3])/fe[3]*100.0) if (fe and fe[3]) else float('nan')))

with io.open(OUT,'w',encoding='utf-8') as fh:
    fh.write('\n'.join(L)+'\n')
print("WROTE",OUT,os.path.getsize(OUT))
