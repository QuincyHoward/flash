# -*- coding: utf-8 -*-
"""
feos_src_q1b.py -- Q1 补充：15-char 固定栅格溢出的鲁棒重解析。

背景：FE-01_TABTOOLS.C 用 "%15.8le" 写头部。宽度 15 只是"最小宽度"：
  形如 -X.XXXXXXXXe-XXX （负尾数 + 3 位指数）实测 16 字符，会越出 15 栅格，
  使整行错位（Ba / Ne 的 L1 len=151）。本脚本用正则按 token 重解析，
  得到与"逐字段物理量"一致的真值，用于判定 SiO2 等"异常值"是否为错位假象。

用法：python feos_src_q1b.py > feos_src_q1b.out.txt
"""
import glob
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
BASE = os.path.join(REPO, 'src', 'Multi1D++Portable20241128', 'matter++') + os.sep

ROW0 = ['FileVersion', 'NR+1', 'NT+1', 'Nelements+1',
        'Tcalclimit', 'Rhocalclimit', 'RhoRef', 'TRef', 'BulkModulusRef',
        'SESAMEnumber']
ROW1 = ['ElectronOffset', 'IonOffset', 'Ecoh', 'softsphere_n', 'softsphere_m',
        'softsphere_A', 'softsphere_B', 'Atot', 'Ztot', 'Xtot']

# %15.8le 写出的 token 形状：X.XXXXXXXXe±XX(|X)
TOKEN = re.compile(rb'[-+]?\d\.\d{8}e[-+]\d{2,3}')

# 参考值（分子量 / 原子序数 / 每化学式原子数），用于判定 Atot/Ztot/Xtot 语义
REF = {
    'Ta2O5.feos': (441.8929, 186.0, 7.0),
    'Al.feos': (26.9815, 13.0, 1.0),
    'B.feos': (10.811, 5.0, 1.0),
    'Ba.feos': (137.327, 56.0, 1.0),
    'Bi.feos': (208.980, 83.0, 1.0),
    'Cerium.feos': (140.116, 58.0, 1.0),
    'Cl.feos': (35.453, 17.0, 1.0),
    'Co.feos': (58.9332, 27.0, 1.0),
    'Cr.feos': (51.9961, 24.0, 1.0),
    'Dy.feos': (162.50, 66.0, 1.0),
    'F.feos': (18.9984, 9.0, 1.0),
    'K.feos': (39.0983, 19.0, 1.0),
    'N.feos': (14.0067, 7.0, 1.0),
    'Na.feos': (22.9898, 11.0, 1.0),
    'Ne.feos': (20.1797, 10.0, 1.0),
    'O.feos': (15.9994, 8.0, 1.0),
    'SiO2.feos': (60.0843, 30.0, 3.0),
    'P-red.feos': (30.9738, 15.0, 1.0),
    'Pd.feos': (106.42, 46.0, 1.0),
    'S-alpha.feos': (32.065, 16.0, 1.0),
    'S-beta.feos': (32.065, 16.0, 1.0),
    'S-gamma.feos': (32.065, 16.0, 1.0),
    'Sc.feos': (44.9559, 21.0, 1.0),
    'Sc2.feos': (44.9559, 21.0, 1.0),
    'Sm.feos': (150.36, 62.0, 1.0),
}


def read_lines(p):
    with open(p, 'rb') as f:
        raw = f.read()
    parts = raw.split(b'\r\n')
    if len(parts) == 1:
        parts = raw.split(b'\n')
    return [x for x in parts if x]


def tok_floats(L):
    return [float(m.group(0)) for m in TOKEN.finditer(L)]


def main():
    files = sorted(glob.glob(BASE + '**/*.feos', recursive=True))
    print('# feos_src_q1b -- %15.8le 栅格溢出鲁棒重解析')
    print('# token 正则: [-+]?\\d\\.\\d{8}e[-+]\\d{2,3}\n')

    print('## A) 逐文件：token 数 / 槽数与真实值（L0 行）')
    bad = []
    for f in files:
        lines = read_lines(f)
        L0 = lines[0]
        t0 = tok_floats(L0)
        nslot = len(L0) // 15
        flag = ''
        if len(t0) != 10:
            flag = '  <== token=%d (!=10)' % len(t0)
            bad.append(os.path.relpath(f, BASE))
        print('  %-46s L0len=%-4d slots=%-3d tokens=%d%s'
              % (os.path.relpath(f, BASE), len(L0), nslot, len(t0), flag))

    print('\n## B) 栅格溢出样本（L1 len != 150）逐 token 定位')
    for f in files:
        lines = read_lines(f)
        if len(lines) < 2:
            continue
        L0, L1 = lines[0], lines[1]
        if len(L1) == 150:
            continue
        toks = tok_floats(L1)
        print('-' * 76)
        print('%s   L1len=%d tokens=%d' % (os.path.relpath(f, BASE), len(L1), len(toks)))
        print('  raw L1 = %r' % L1.decode('ascii', 'replace'))
        for i, t in enumerate(toks):
            nm = ROW1[i] if i < len(ROW1) else '?'
            print('    [%2d] %-16s %.10g' % (i + 1, nm, t))

    print('\n' + '#' * 76)
    print('# C) 鲁棒重解析后的 Atot/Ztot/Xtot 语义核对（对比元素/分子参考值）')
    print('#' * 76)
    print('  %-24s %-11s %-9s %-7s | %-11s %-9s %-7s | %s'
          % ('file', 'Atot', 'Ztot', 'Xtot', 'A_ref', 'Z_ref', 'X_ref', 'verdict'))
    for f in files:
        lines = read_lines(f)
        if len(lines) < 2:
            continue
        t1 = tok_floats(lines[1])
        if len(t1) != 10:
            print('  %-24s <token=%d，跳过>' % (os.path.basename(f), len(t1)))
            continue
        atot, ztot, xtot = t1[7], t1[8], t1[9]
        base = os.path.basename(f)
        ref = REF.get(base)
        if not ref:
            ref = REF.get(base.replace('_20230426', ''))
        if ref:
            ra, rz, rx = ref
            ok = (abs(atot - ra) < 0.01 * ra + 0.02 and abs(ztot - rz) < 0.02
                  and abs(xtot - rx) < 1e-6)
            verdict = 'MATCH 分子总量' if ok else 'MISMATCH'
            print('  %-24s %-11.6g %-9.6g %-7.6g | %-11.6g %-9.6g %-7.6g | %s'
                  % (base, atot, ztot, xtot, ra, rz, rx, verdict))
        else:
            print('  %-24s %-11.6g %-9.6g %-7.6g | %s'
                  % (base, atot, ztot, xtot, '(无参考)'))

    print('\n## D) 结论性计数')
    print('  文件总数             = %d' % len(files))
    n150 = sum(1 for f in files if len(read_lines(f)[0]) == 150)
    print('  L0 len==150 的文件   = %d' % n150)
    print('  L0 token!=10 的文件  = %s' % (bad if bad else '无'))
    print('  L1 len!=150 的文件   = %s'
          % [os.path.relpath(f, BASE) for f in files
             if len(read_lines(f)) > 1 and len(read_lines(f)[1]) != 150])


main()
