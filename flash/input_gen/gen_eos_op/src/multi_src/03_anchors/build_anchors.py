# -*- coding: utf-8 -*-
"""Build the empirical anchor library: read head of representative files
across every format family, dump raw first lines for citation in the doc."""
import io
import os
import sys

ROOT = 'src/Multi1D++Portable20241128'

SECTIONS = [
    ('SESAME / MULTI (4x15, 4x16)', [
        'matter++/mat_Al-1.0/AL_SIMPLE_PLANCK',
        'matter++/mat_Ti/SNOP_LTE.PLANCK',
        'matter++/mat_Al-1.0/AL_eos',
        'matter++/mat_Au-1.0/AU_eosd',
        'matter++/mat_Vacuum/Vacuum_Opacity.dat',
    ]),
    ('Hyades', [
        'matter++/hyades/sesame/eos_2051.dat',
        'matter++/hyades/sesame/eos_32.hug',
        'matter++/hyades/Opacity/opc_1022.dat',
        'matter++/hyades/qeos/qeos_115.dat',
        'matter++/hyades/tmp.dat',
    ]),
    ('FEOS / MPQeos - modern (.feos/.301/.mexport/.cst/.data.txt)',
     ['matter++/mat_Al-1.0/Al.feos',
      'matter++/mat_Al-1.0/FEOS/Al.feos.301',
      'matter++/mat_Al-1.0/FEOS/Al.feos.304',
      'matter++/mat_Al-1.0/FEOS/Al.feos.305',
      'matter++/mat_B/FEOS/B.feos.301',
      'matter++/mat_B/B.mexport',
      'matter++/mat_O/O.cst',
      'matter++/mat_B/B.data.txt',
      'matter++/Ta2O5/Ta2O5.data.txt',
      'matter++/Ta2O5/Ta2O5.cst',
      ]),
    ('FEOS - non-standard SHOWEOS suffixes', [
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
        'matter++/mat_B/B.isobaric.dat',
        'matter++/mat_B/B.critical.dat',
        'matter++/mat_Ce/Cerium.critical.dat',
    ]),
    ('FEOS aux / misc (.par/.cst/.info/.inhalt/.user/.inv/.in/.sesame)', [
        'matter++/mat_Al-1.0/Al.feos.par',
        'matter++/mat_B/B.PAR',
        'matter++/hyades/qeos/qeos_392.dat.par',
        'matter++/mat_Be-1.0/BE_eos.info',
        'matter++/mat_C-1.0/Carbon.info',
        'matter++/mat_Others/Mix20keV.info',
        'matter++/mat_Others/CH10Water.info',
        'matter++/SNOP/opbe.inhalt',
        'matter++/CH/material.user',
        'matter++/Ta2O5/material.user',
        'matter++/mat_CPC/AU.INV',
        'matter++/CH/CHSi10_eos.IN',
        'matter++/Ta2O5/PowerLawTa2O5_EOS.SESAME',
        'matter++/mat_Au/Au_2003POPHammerRosen_EOS.SESAME',
        'matter++/SiO2/eos_21.sesame',
        'matter++/mat_C-1.0/CSi2.5_mopp95',
        'matter++/mat_C-1.0/CSi2.5_mopr95',
    ]),
    ('LEDCOP / ATOMIC', [
        'matter++/ATOMIC/Al.NoFree',
        'matter++/ATOMIC/Al.AvSqFree',
        'matter++/ATOMIC/Al.GrayOpacity_PLANCK',
        'matter++/ATOMIC/Al.MultiGroupOpacity_PLANCK',
    ]),
    ('Thermos', [
        'matter++/Thermos/Readme.txt',
        'matter++/Thermos/mat_Al/Al.ini',
        'matter++/Thermos/mat_Al/Al_Zeff.dat',
        'matter++/Thermos/mat_Al/Al_Z.dat',
        'matter++/Thermos/mat_Al/Al_Planck.dat',
        'matter++/Thermos/mat_Al/Al_Rosseland.dat',
    ]),
    ('IONMIX (.cn4/.cnr)', [
        'matter++/Ionmix/al-imx-002.cn4',
        'matter++/Ionmix/al-imx-001.cnr',
        'matter++/Ionmix/polystyrene-imx-002.cn4',
        'matter++/Ionmix/h-100grp-lte.cnr',
    ]),
    ('Dispatch / Readme / 说明文本', [
        'matter++/Readme.txt',
        'matter++/PROPACEOS/Readme.txt',
        'matter++/hyades/README',
        'matter++/mat_Al-1.0/README',
        'doc/Structure_of_ASCII_data_files.txt',
        'doc/SNOP.MANUAL',
    ]),
    ('ColdOpacity / Hugoniot 附属', [
        'matter++/ColdOpacity/Al.coldopacity',
        'matter++/mat_Al-1.0/AL_eos.hug',
    ]),
]


def head(path, n=14, maxw=170):
    p = os.path.join(ROOT, path)
    if not os.path.exists(p):
        return None, 'MISSING'
    size = os.path.getsize(p)
    try:
        with open(p, 'rb') as fh:
            raw = fh.read(20000)
        txt = raw.decode('utf-8', 'replace')
        if txt.count('\ufffd') > 5:
            txt = raw.decode('latin-1')
    except Exception as e:
        return None, 'ERR %s' % e
    lines = txt.split('\n')
    out = []
    for i, ln in enumerate(lines[:n], 1):
        out.append('%4d|%s' % (i, ln.rstrip()[:maxw]))
    return (size, out), None


def main():
    outp = sys.argv[1] if len(sys.argv) > 1 else '.workbuddy/tmp/anchors.md'
    buf = ['# 实测锚点库', '', '> 全部为 `src/Multi1D++Portable20241128/` 下的真实文件头部原文。',
           '> 路径均为相对该根的路径。', '']
    for sec, paths in SECTIONS:
        buf.append('## %s' % sec)
        buf.append('')
        for path in paths:
            res, err = head(path)
            if err:
                buf.append('### `%s`' % path)
                buf.append('')
                buf.append('**%s**' % err)
                buf.append('')
                continue
            size, lines = res
            buf.append('### `%s`  (%d B)' % (path, size))
            buf.append('')
            buf.append('```')
            buf.extend(lines)
            buf.append('```')
            buf.append('')
    txt = '\n'.join(buf)
    os.makedirs(os.path.dirname(outp), exist_ok=True)
    with io.open(outp, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(txt)
    print('wrote %s  %d chars' % (outp, len(txt)))


if __name__ == '__main__':
    main()
