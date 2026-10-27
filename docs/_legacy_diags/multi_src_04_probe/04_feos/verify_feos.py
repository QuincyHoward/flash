# -*- coding: utf-8 -*-
import io, os
B = 'src/Multi1D++Portable20241128/matter++/'

def decode_feos(path):
    with io.open(path, 'r', encoding='cp936', errors='replace') as f:
        txt = f.read().replace('\x1a', '')
    lines = txt.splitlines()
    # fixed 15-char parse of first 20 fields
    head = ''.join(lines[0:2])
    fields = [head[i:i+15] for i in range(0, 150, 15)]
    r0 = fields[0:10]; r1 = fields[10:20]
    FileVersion = float(r0[0]); NR = int(round(float(r0[1])))-1; NT = int(round(float(r0[2])))-1
    Nel = int(round(float(r0[3])))-1
    Tcalc = float(r0[4]); Rhocalc = float(r0[5]); RhoRef = float(r0[6]); TRef = float(r0[7]); B0 = float(r0[8]); SN = int(round(float(r0[9])))
    Eoff = float(r1[0]); Ioff = float(r1[1]); Ecoh = float(r1[2])
    n = float(r1[3]); m = float(r1[4]); A = float(r1[5]); Bb = float(r1[6]); Atot = float(r1[7]); Ztot = float(r1[8]); Xtot = float(r1[9])
    print('%-46s FV=%.0f NR=%-4d NT=%-4d Nel=%-3d Tcalc=%g Rhocalc=%g RhoRef=%g TRef=%g B0=%g SN=%d' %
          (os.path.basename(path), FileVersion, NR, NT, Nel, Tcalc, Rhocalc, RhoRef, TRef, B0, SN))
    print('     [r1] Eoff=%g Ioff=%g Ecoh=%g n=%g m=%g A=%g B=%g Atot=%g Ztot=%g Xtot=%g' %
          (Eoff, Ioff, Ecoh, n, m, A, Bb, Atot, Ztot, Xtot))
    return dict(NR=NR, NT=NT, Nel=Nel, Atot=Atot, Ztot=Ztot, Xtot=Xtot)

for p in ['mat_Al-1.0/Al.feos', 'mat_B/B.feos', 'Ta2O5/Ta2O5.feos',
          'mat_Others/SiO2.feos', 'mat_Ba/Ba.feos', 'mat_Ce/Cerium.feos']:
    try:
        decode_feos(B + p)
    except Exception as e:
        print('ERR', p, e)
