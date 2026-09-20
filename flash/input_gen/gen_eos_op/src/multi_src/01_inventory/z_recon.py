# -*- coding: utf-8 -*-
"""对账：xval 的 31 个"未识别"文件 vs 我的闭合普查结果。"""
import os, re

ROOT = r'E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\input_gen\gen_eos_op'
SRC = os.path.join(ROOT, 'src', 'Multi1D++Portable20241128')
CEN = os.path.join(ROOT, '.workbuddy', 'tmp', 'census_mg2.txt')

cen = open(CEN, encoding='utf-8').read()
# 我的族清单行形如 "rel ... style ... id ..."
in_family = {}
for l in cen.split('\n'):
    m = re.match(r'^(\S.*?)\s{2,}(单群|多群)\s', l)
    if m:
        in_family[m.group(1).strip()] = m.group(2)

print('我的族清单条数 =', len(in_family))
print()

UNID = """Ta2O5/Ta2O5_1G_MULTI
Ta2O5/Ta_1G_MULTI
Thermos/mat_Mo/Mo_Ideal_Gas
Thermos/mat_W/W_Ideal_Gas
XrayMassCoef/XrayMassCoef.tab1
XrayMassCoef/XrayMassCoef.tab2
mat_Al-1.0/1041_PLANCK
mat_Al-1.0/1041_ROSS
mat_Al-1.0/AL_LV.INV.data
mat_Au-1.0/AU_info
mat_Au/Au_Rosseland_2003POPHammerRosen
mat_Ba/Ba_1987JQSRT_Planck
mat_Ba/Ba_1987JQSRT_Rosseland
mat_Ba/Ba_Planck_1987JQSRT
mat_Ba/Ba_Rosseland_1987JQSRT
mat_Be-1.0/BE_PLANCKx03
mat_Be-1.0/BE_SIMPLE_PLANCK
mat_C-1.0/C.ZEFF_old
mat_CELIA/C.ZEFF_old
mat_CELIA/D.ZEFF_old
mat_CPC/BE_PLANCKx03
mat_Eu/Eu_Planck_1987JQSRT
mat_Eu/Eu_Rosseland_1987JQSRT
mat_Ge/Ge_2002FED_Planck
mat_Ge/Ge_2002FED_Rosseland
mat_Ge/Ge_Planck_1999Minguez
mat_Ge/Ge_Rosseland_1999Minguez
mat_Others/CH10Water1/CH2_H2O_1m1Z
mat_Others/CH10Water2/CH2_H2O_2m1Z
mat_Sn/Sn_Planck_1987JQSRT
mat_Sn/Sn_Rosseland_1987JQSRT""".split('\n')

print('%-46s %-8s %-8s %s' % ('文件', '我的族', '字节', '首行'))
recon = 0
for u in UNID:
    u = u.strip().replace('/', os.sep)
    p = os.path.join(SRC, 'matter++', u)
    fam = in_family.get(u) or in_family.get(u.replace(os.sep, '/')) or '-'
    ok = os.path.exists(p)
    first = ''
    if ok:
        raw = open(p, 'rb').read(200).replace(b'\r\n', b'\n')
        first = raw.split(b'\n')[0].decode('latin-1')[:52]
    else:
        print('  [path not found]', u)
    if fam != '-':
        recon += 1
    print('%-46s %-8s %-8s %s' % (u.replace(os.sep, '/'), fam, os.path.getsize(p) if ok else '?', first))

print()
print('其中已由我的闭合普查覆盖 = %d / %d' % (recon, len(UNID)))
