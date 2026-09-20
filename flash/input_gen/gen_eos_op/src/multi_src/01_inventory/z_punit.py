# -*- coding: utf-8 -*-
"""独立裁定 `.cst` / `.data.txt` 的 P 单位：用 *.critical.dat 的临界点做锚。
   Ce: Tc=2006.73 K, Pc=23032.87 bar, Rhoc=?  -> 在 .cst 中找 (Rhoc, Tc) 附近点。
"""
import os, re, math

ROOT = r'E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\input_gen\gen_eos_op'
M = os.path.join(ROOT, 'src', 'Multi1D++Portable20241128', 'matter++')

for mat, cstf, datf, crif in [
        ('mat_Ce', 'mat_Ce/Cerium.cst', 'mat_Ce/Cerium.data.txt', 'mat_Ce/Cerium.critical.dat'),
        ('mat_B',  'mat_B/B.cst',       'mat_B/B.data.txt',       'mat_B/B.critical.dat'),
        ('Ta2O5',  'Ta2O5/Ta2O5.cst',   'Ta2O5/Ta2O5.data.txt',   'Ta2O5/Ta2O5.critical.dat')]:
    print('=' * 76)
    print(mat)
    print('=' * 76)
    # 1) 临界点
    p = os.path.join(M, crif)
    if not os.path.exists(p):
        print('  [missing]', crif); continue
    t = open(p, 'rb').read(4000).decode('latin-1')
    for line in t.split('\n')[:6]:
        if line.startswith('#'):
            print('   CRIT:', line.strip()[:150])
    m = re.search(r'Tc\s*=\s*([\d.eE+-]+)', t); Tc = float(m.group(1)) if m else None
    m = re.search(r'Pc\s*=\s*([\d.eE+-]+)', t); Pc_bar = float(m.group(1)) if m else None
    m = re.search(r'Rhoc\s*=\s*([\d.eE+-]+)', t); Rc = float(m.group(1)) if m else None
    print('   Tc=%.6g K   Pc=%.6g bar   Rhoc=%.6g g/cm3' % (Tc, Pc_bar, Rc))
    print('   Pc 换算 = %.6g MBar   (1 MBar = 1e6 bar)' % (Pc_bar / 1e6))

    # 2) .cst 逐块解析
    raw = open(os.path.join(M, cstf), 'rb').read().decode('latin-1').replace('\r\n', '\n')
    L = [l for l in raw.split('\n') if l.strip()]
    blocks, cur = [], None
    for l in L:
        mt = re.match(r'Isotherme T = ([-\d.eE+]+) Kelvin', l)
        if mt:
            cur = {'T': float(mt.group(1)), 'rows': []}
            blocks.append(cur)
            continue
        if cur is None:
            continue
        tok = l.split()
        if len(tok) == 4:                      # n, rho, P, Q
            try:
                cur['rows'].append((float(tok[1]), float(tok[2])))
            except ValueError:
                pass
    print('   .cst 块数 = %d ; 每块数据行 = %s' %
          (len(blocks), sorted(set(len(b['rows']) for b in blocks))))
    # 找 T 最接近 Tc 的块，再在其中找 rho 最接近 Rc 的行
    bt = min(blocks, key=lambda b: abs(b['T'] - Tc))
    br = min(bt['rows'], key=lambda r: abs(r[0] - Rc))
    print('   最近块 T=%.6g K (Δ=%.3g) ; 该块内最近 rho=%.6g (Δ=%.3g)' %
          (bt['T'], bt['T'] - Tc, br[0], br[0] - Rc))
    P_cst = br[1]
    print('   .cst  P = %.6g   (若单位 MBar -> %.6g bar)' % (P_cst, P_cst * 1e6))
    print('   ⇒ .cst/Pc[bar] = %.6g' % (P_cst * 1e6 / Pc_bar))

    # 3) data.txt 同一 (rho,T) 附近
    if os.path.exists(os.path.join(M, datf)):
        d = []
        with open(os.path.join(M, datf), 'rb') as f:
            for k in range(2000):
                ln = f.readline()
                if not ln:
                    break
                tok = ln.decode('latin-1').split()
                if len(tok) >= 7:
                    try:
                        d.append((float(tok[2]), float(tok[3]), float(tok[4]), float(tok[5]), float(tok[6])))
                    except ValueError:
                        pass
        if d:
            dmin = min(d, key=lambda r: abs(math.log(max(r[0], 1e-30)) - math.log(max(br[0], 1e-30)))
                       + abs(r[1] - bt['T']) / max(Tc, 1))
            print('   data.txt 最近点 rho=%.6g T=%.6g K  P_tot=%.6g  P_e=%.6g  P_i=%.6g'
                  % (dmin[0], dmin[1], dmin[2], dmin[3], dmin[4]))
            print('   ⇒ data.P_tot / Pc[bar] = %.6g' % (dmin[2] / Pc_bar))
            if P_cst:
                print('   ⇒ data.P_tot / .cst.P = %.6g' % (dmin[2] / P_cst))
    print()
