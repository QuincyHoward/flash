# -*- coding: utf-8 -*-
"""xv2e_ist_exact.py -- 直接打印 Ta2O5 三个源在 T=0 的原始行, 用精确网格点比对(不插值)"""
import os, io, re
HERE = os.path.dirname(os.path.abspath(__file__))
SRC  = os.path.abspath(os.path.join(HERE, '..', '..'))
MATTER = os.path.join(SRC, 'Multi1D++Portable20241128', 'matter++')
NUMRE = re.compile(r'[-+]?\d*\.?\d+(?:[eEdD][-+]?\d+)?')
D = os.path.join(MATTER, 'Ta2O5')
L=[]
def P(s=''): L.append(str(s))
def lines(p):
    with open(p,'rb') as fh: b=fh.read()
    if b.startswith(b'\xef\xbb\xbf'): b=b[3:]
    return [l.rstrip('\n') for l in b.decode('utf-8','replace')
            .replace('\r\n','\n').replace('\r','\n').split('\n')]
def fa(s): return [float(t.replace('D','E').replace('d','e')) for t in NUMRE.findall(s)]

P("### A. Ta2O5.Rho-P.ist 原始行（含注释）")
P("")
for i,l in enumerate(lines(os.path.join(D,'Ta2O5.Rho-P.ist'))[:8]):
    P("  L%-3d |%s|" % (i,l))
P("  ...")
for i,l in enumerate(lines(os.path.join(D,'Ta2O5.Rho-P.ist'))[18:26]):
    P("  L%-3d |%s|" % (i+18,l))

P("")
P("### B. Ta2O5.cst 前 8 个数据行（第0块 = 最低温）")
P("")
cnt=0
for l in lines(os.path.join(D,'Ta2O5.cst')):
    t=l.strip()
    if not t or 'Molek' in t or 'Massendichte' in t or t.lower().startswith('isotherm'): continue
    v=NUMRE.findall(t)
    if len(v)==4:
        P("  row%-3d n=%s rho=%s P=%s Q=%s" % (cnt,v[0],v[1],v[2],v[3]))
        cnt+=1
    if cnt>=8: break

P("")
P("### C. Ta2O5.data.txt i_T=0 前 8 行")
P("")
c=0
for l in lines(os.path.join(D,'Ta2O5.data.txt')):
    if not l.strip(): continue
    v=fa(l)
    if len(v)>=7 and int(round(v[1]))==0:
        P("  i_rho=%d rho=%.8g T=%.6g P_tot=%.8g P_e=%.4g P_i=%.4g" % (v[0],v[2],v[3],v[4],v[5],v[6]))
        c+=1
    if c>=8: break

P("")
P("### D. 精确同点比对（rho 完全相同的网格点）")
P("")
ist={}
for l in lines(os.path.join(D,'Ta2O5.Rho-P.ist')):
    t=l.strip()
    if not t or t.startswith('#'): continue
    v=fa(t)
    if len(v)==2: ist.setdefault(v[0], v[1])   # 第一块 = T=0
cst={}
c=0
for l in lines(os.path.join(D,'Ta2O5.cst')):
    t=l.strip()
    if not t or 'Molek' in t or 'Massendichte' in t or t.lower().startswith('isotherm'): continue
    v=NUMRE.findall(t)
    if len(v)==4:
        if c<123:
            rho=float(v[1].replace('D','E')); PP=float(v[2].replace('D','E'))
            cst[rho]=PP
        c+=1
dat={}
for l in lines(os.path.join(D,'Ta2O5.data.txt')):
    if not l.strip(): continue
    v=fa(l)
    if len(v)>=5 and int(round(v[1]))==0:
        dat[v[2]]=v[4]
P("| rho | .ist P (MBar) | .cst P | .data P_tot | ist/cst | ist/data |")
P("|---:|---:|---:|---:|---:|---:|")
hit=0
for r in sorted(ist):
    cand=[k for k in cst if abs(k-r)<=1e-9*max(abs(r),1e-30)]
    candd=[k for k in dat if abs(k-r)<=1e-9*max(abs(r),1e-30)]
    a=cst[cand[0]] if cand else None
    b=dat[candd[0]] if candd else None
    P("| %.6g | %.6g | %s | %s | %s | %s |" % (
        r, ist[r],
        ('%.6g'%a) if a is not None else '—',
        ('%.6g'%b) if b is not None else '—',
        ('%.6f'%(ist[r]/a)) if a else '—',
        ('%.6f'%(ist[r]/b)) if b else '—'))
    if a: hit+=1
P("")
P("精确同 ρ 网格点数 = %d" % hit)

with io.open(os.path.join(HERE,'xv2e_ist_exact.txt'),'w',encoding='utf-8') as fh:
    fh.write('\n'.join(L)+'\n')
print("WROTE", os.path.getsize(os.path.join(HERE,'xv2e_ist_exact.txt')))
