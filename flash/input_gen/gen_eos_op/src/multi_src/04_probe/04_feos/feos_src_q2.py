# -*- coding: utf-8 -*-
"""
feos_src_q2.py -- Q2 探针：.cst / .CST（Rostock 格式）表头语言与列结构普查。

对应源码：FE-01_TABTOOLS.C:883-907 write_Rostock_format()
  fprintf( h, "Isotherme T = %.0f Kelvin \n", T[j]*eV2Kelvin );                    // :896
  fprintf( h, "Moleküldichte[1/cm^3]  Massendichte[g/cm^3]  Druck[MBar]  Ladungszustand\n" ); // :897
  fprintf( h, "%e          %e          %e    %e\n", ... );                        // :899-901

同时回答"英文表头变体（Particle density / load state / Mass density）是否存在于源码"。
源码侧已用 Grep 全量核查（见 out 文件的 §0）。

用法：python feos_src_q2.py > feos_src_q2.out.txt
"""
import glob
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
BASE = os.path.join(REPO, 'src', 'Multi1D++Portable20241128', 'matter++') + os.sep

DE_HDR = 'Moleküldichte'
EN_HDR = 'Particle density'
EN_LOAD = 'load state'
EN_MASS = 'Mass density'

NUMBER = re.compile(r'[-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[eEdD][-+]?\d+)?')


def valf(s):
    return [float(m.group(0)) for m in NUMBER.finditer(s)]


def read_lines(p):
    with open(p, 'rb') as f:
        raw = f.read()
    parts = raw.split(b'\r\n')
    if len(parts) == 1:
        parts = raw.split(b'\n')
    return [x for x in parts if x.strip()]


def dec(b):
    for enc in ('utf-8', 'latin-1'):
        try:
            return b.decode(enc)
        except UnicodeDecodeError:
            continue
    return b.decode('latin-1', 'replace')


def main():
    pats = [BASE + '**/*.cst', BASE + '**/*.CST']
    files = []
    for p in pats:
        files += glob.glob(p, recursive=True)
    files = sorted(set(files))

    print('# feos_src_q2 -- .cst/.CST 普查')
    print('# 文件总数 = %d' % len(files))

    print('\n## 0) 源码侧英文模板核查结果（由 Grep 得出，此处复述）')
    print('  在 src/multi_src/09_source_verify/vendor/FEOS_src/ 全量 grep：')
    print('    "Particle density" -> 0 命中')
    print('    "load state"       -> 0 命中')
    print('    "Mass density"     -> 0 命中')
    print('    德文模板 "Isotherme"/"Moleküldichte" -> 仅 FE-01_TABTOOLS.C:896-897')
    print('  结论：英文表头模板在 FEOS C++ 源码中不存在。')

    print('\n## 1) 逐文件表头（前 3 行）+ 列数')
    langs = {}
    for f in files:
        lines = read_lines(f)
        rel = os.path.relpath(f, BASE)
        h1 = dec(lines[0]) if len(lines) > 0 else ''
        h2 = dec(lines[1]) if len(lines) > 1 else ''
        d = dec(lines[2]) if len(lines) > 2 else ''
        ncol = len(d.split())
        if DE_HDR in h2:
            lang = 'DE(源码模板)'
        elif EN_HDR in h2 or EN_LOAD in h2 or EN_MASS in h2:
            lang = 'EN(非源码模板)'
        else:
            lang = 'OTHER'
        langs[lang] = langs.get(lang, 0) + 1
        print('-' * 76)
        print('%s   [%s]  data_ncol=%d  lines=%d' % (rel, lang, ncol, len(lines)))
        print('   L1: %r' % h1.strip())
        print('   L2: %r' % h2.strip())
        if d:
            print('   L3: %r  (ncol=%d)' % (d.strip(), ncol))
        # 连续若干等温段头计数
        n_iso = sum(1 for L in lines if 'Kelvin' in dec(L))
        n_hdr = sum(1 for L in lines if DE_HDR in dec(L) or EN_HDR in dec(L))
        print('   Kelvin 段头数 = %d   列头行数 = %d' % (n_iso, n_hdr))

    print('\n## 2) 语言分布统计')
    for k in sorted(langs):
        print('   %-16s %d' % (k, langs[k]))

    print('\n## 3) 列名语义（源码 FE-01_TABTOOLS.C:899-901 逐参对照）')
    print('   col1 = Rho[i]/(Atot*M_proton)   [1/cm^3]  粒子(分子)数密度')
    print('   col2 = Rho[i]                   [g/cm^3]  质量密度')
    print('   col3 = P[i][j]*cgs2MBar         [MBar]    压强 (cgs2MBar=1e-12)')
    print('   col4 = Qtot[i][j]               [e]       平均电离度(无量纲)')

    # ---- 4) 数值反解：col1/col2 是否恒等于 1/(Atot*M_proton) ----
    print('\n## 4) 数值反解：col1/col2 = 1/(Atot*M_proton) ？')
    print('    => 反解 Atot = 1/(col1/col2 * M_proton)，与候选材料比对')
    M_PROTON = 1.6726231e-24          # COMMON-00_DEFINITS.H:57
    probe = [('mat_Ce/Cerium.cst', 'Ce 期望 Atot=140.114', 140.114),
             ('mat_He/Untitled.CST', 'He 期望 Atot=4.0026', 4.0026)]
    for rel, note, cand in probe:
        p = os.path.join(BASE, rel.replace('/', os.sep))
        if not os.path.isfile(p):
            print('  %-28s <缺失>' % rel)
            continue
        lines = read_lines(p)
        rows = []
        for L in lines:
            v = valf(dec(L))
            if len(v) == 4 and v[1] > 0 and v[0] > 0:
                rows.append(v)
        if not rows:
            print('  %-28s <无有效数据行>' % rel)
            continue
        v = rows[len(rows) // 2]
        ratio = v[0] / v[1]
        atot_implied = 1.0 / (ratio * M_PROTON)
        print('  %-28s %s' % (rel, note))
        print('    样本行: col1=%e col2=%e col3=%e col4=%e' % (v[0], v[1], v[2], v[3]))
        print('    col1/col2 = %.6e  =>  反解 Atot = %.6f  (候选 %.6f, 偏差 %+.2e)'
              % (ratio, atot_implied, cand, atot_implied / cand - 1.0))


main()
