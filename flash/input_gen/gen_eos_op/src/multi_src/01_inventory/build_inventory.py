# -*- coding: utf-8 -*-
"""Build a full inventory of `src/Multi1D++Portable20241128/` for appendix C
(sample file index): relative path, byte size, and first non-empty line.

Usage:
    python build_inventory.py [out.md]
"""
import io
import os
import sys

ROOT = 'src/Multi1D++Portable20241128'

# One representative sample per format family / notable artifact.
SAMPLES = [
    # --- dispatch / readme / doc ---
    'matter++/Readme.txt',
    'matter++/PROPACEOS/Readme.txt',
    'matter++/Thermos/Readme.txt',
    'doc/Structure_of_ASCII_data_files.txt',
    'doc/SNOP.MANUAL',
    # --- SESAME / MULTI 4x15 ---
    'matter++/mat_Al-1.0/AL_SIMPLE_PLANCK',
    'matter++/mat_Ti/SNOP_LTE.PLANCK',
    'matter++/mat_Al-1.0/AL_eos',
    'matter++/mat_Au-1.0/AU_eosd',
    'matter++/mat_Vacuum/Vacuum_Opacity.dat',
    'matter++/mat_C-1.0/CSi2.5_mopp95',
    'matter++/mat_C-1.0/CSi2.5_mopr95',
    'matter++/mat_C-1.0/CSi2.5_from_lililing',
    'matter++/SiO2/eos_21.sesame',
    'matter++/mat_Au/Au_2003POPHammerRosen_EOS.SESAME',
    'matter++/Ta2O5/PowerLawTa2O5_EOS.SESAME',
    # --- MPQeos .301/.304/.305 ---
    'matter++/mat_Al-1.0/FEOS/Al.feos.301',
    'matter++/mat_Al-1.0/FEOS/Al.feos.304',
    'matter++/mat_Al-1.0/FEOS/Al.feos.305',
    'matter++/mat_B/B.301',
    'matter++/mat_Au-1.0/Au.301',
    # --- FEOS native + siblings ---
    'matter++/mat_Al-1.0/Al.feos',
    'matter++/mat_Al-1.0/Al.feos.par',
    'matter++/mat_B/B.PAR',
    'matter++/mat_B/B.mexport',
    'matter++/mat_B/B.data.txt',
    'matter++/mat_B/B.critical.dat',
    'matter++/mat_B/B.isobaric.dat',
    'matter++/mat_Ce/Cerium.critical.dat',
    'matter++/mat_O/O.cst',
    'matter++/Ta2O5/Ta2O5.cst',
    'matter++/Ta2O5/Ta2O5.data.txt',
    # --- FEOS SHOWEOS outputs ---
    'matter++/Ta2O5/Ta2O5.Rho-P.ist',
    'matter++/Ta2O5/Ta2O5.Rho-T.ist',
    'matter++/Ta2O5/Ta2O5.Rho-E.ist',
    'matter++/Ta2O5/Ta2O5.Rho-PTF.ist',
    'matter++/Ta2O5/Ta2O5.Rho-P.isc',
    'matter++/Ta2O5/Ta2O5.Rho-T.isc',
    'matter++/Ta2O5/Ta2O5.Rho-PTF.isc',
    'matter++/Ta2O5/Ta2O5.Rho-P.ise',
    'matter++/Ta2O5/Ta2O5.Rho-T-P.mnt',
    'matter++/mat_Al-1.0/Al.feos.Rho-P.ist',
    'matter++/mat_Al-1.0/Al.feos.Rho-P.ist4gnuplot',
    'matter++/Ta2O5/Ta2O5.Rho-P.ist4gnuplot',
    'matter++/Ta2O5/Ta2O5.Rho-T-P.mnt4gnuplot',
    'matter++/Ta2O5/Ta2O5.Rho-P.ise4gnuplot',
    'matter++/Ta2O5/Ta2O5.Rho-P.isc4gnuplot',
    'matter++/mat_Al-1.0/Al.feos.hug',
    'matter++/mat_Al-1.0/AL_eos.hug',
    'matter++/mat_Au-1.0/AU_eos.hug',
    # --- FEOS aux ---
    'matter++/mat_Be-1.0/BE_eos.info',
    'matter++/mat_C-1.0/Carbon.info',
    'matter++/mat_Others/Mix20keV.info',
    'matter++/mat_Others/CH10Water.info',
    'matter++/SNOP/opbe.inhalt',
    'matter++/CH/material.user',
    'matter++/Ta2O5/material.user',
    'matter++/mat_CPC/AU.INV',
    'matter++/CH/CHSi10_eos.IN',
    'matter++/hyades/qeos/qeos_392.dat.par',
    # --- Hyades ---
    'matter++/hyades/sesame/eos_2051.dat',
    'matter++/hyades/sesame/eos_32.hug',
    'matter++/hyades/Opacity/opc_1022.dat',
    'matter++/hyades/qeos/qeos_115.dat',
    'matter++/hyades/tmp.dat',
    # --- ATOMIC / LEDCOP ---
    'matter++/ATOMIC/Al.NoFree',
    'matter++/ATOMIC/Al.AvSqFree',
    'matter++/ATOMIC/Al.GrayOpacity_PLANCK',
    'matter++/ATOMIC/Al.MultiGroupOpacity_PLANCK',
    # --- IONMIX ---
    'matter++/Ionmix/al-imx-002.cn4',
    'matter++/Ionmix/al-imx-001.cnr',
    'matter++/Ionmix/polystyrene-imx-002.cn4',
    'matter++/Ionmix/h-100grp-lte.cnr',
    # --- Thermos ---
    'matter++/Thermos/mat_Al/Al.ini',
    'matter++/Thermos/mat_Al/Al_Zeff.dat',
    'matter++/Thermos/mat_Al/Al_Z.dat',
    'matter++/Thermos/mat_Al/Al_Planck.dat',
    'matter++/Thermos/mat_Al/Al_Rosseland.dat',
    # --- cold opacity ---
    'matter++/ColdOpacity/Al.coldopacity',
    # --- constants / curves ---
    'matter++/Albedo.xml',
    'matter++/ScalingLaws.dat',
    'matter++/density.dat',
    'matter++/AtomicWeightTable.txt',
    'matter++/DatabaseIndex.xml',
]


def first_line(path):
    try:
        with open(path, 'rb') as fh:
            raw = fh.read(4096)
    except Exception as e:
        return '<ERR %s>' % e
    txt = raw.decode('utf-8', 'replace')
    if txt.count('\ufffd') > 3:
        txt = raw.decode('latin-1')
    for ln in txt.split('\n'):
        ln = ln.rstrip('\r').strip()
        if ln:
            return ln[:130]
    return '<empty>'


def main():
    outp = sys.argv[1] if len(sys.argv) > 1 else '.workbuddy/tmp/sample_index.md'
    buf = ['# 实测样本索引（附录 C 素材）', '',
           '> 路径相对 `src/Multi1D++Portable20241128/`。字节数与首行均为实测。', '',
           '| # | 相对路径 | 字节 | 首行（截断） |', '|---|---|---:|---|']
    miss = []
    for i, rel in enumerate(SAMPLES, 1):
        p = os.path.join(ROOT, rel)
        if not os.path.exists(p):
            miss.append(rel)
            buf.append('| %d | `%s` | **MISSING** | — |' % (i, rel))
            continue
        size = os.path.getsize(p)
        fl = first_line(p).replace('|', '\\|')
        buf.append('| %d | `%s` | %d | `%s` |' % (i, rel, size, fl))
    txt = '\n'.join(buf) + '\n'
    os.makedirs(os.path.dirname(outp), exist_ok=True)
    with io.open(outp, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(txt)
    print('wrote %s  (%d samples, %d missing)' % (outp, len(SAMPLES), len(miss)))
    for m in miss:
        print('  MISSING %s' % m)


if __name__ == '__main__':
    main()
