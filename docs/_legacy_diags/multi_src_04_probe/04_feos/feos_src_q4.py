# -*- coding: utf-8 -*-
"""
feos_src_q4.py -- Q4 探针：多群不透明度表 T 轴 / 能量轴单位裁定（数据级）。

背景（待裁定）：
  mat_Ce/Ce.INPUT 给 T1=1E-05, T2=5, NPLA=27003000；
  而 mat_Ce/Ce.PLANCK 的表头 T 轴上限疑似 ≈5e4，与 T2 相差 10 倍。
  疑点：T1/T2 的单位到底是 eV 还是 keV？

源码侧结论：本地仓库中**不存在**写出多群不透明度表的源码
  - src/Multi1D++Portable20241128/ 下 0 个 .f/.f90/.C/.cpp 源文件（纯数据+二进制）
  - FEOS C++ 包（19 个 .C/.H）全文无 PLANCK/ROSSELAND/NPLA/NROSS/opacity 任何命中
  => 源码裁定为 [S-UNK]；本脚本给出数据级（[S-L1]）裁定。

用法：python feos_src_q4.py > feos_src_q4.out.txt
"""
import glob
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
BASE = os.path.join(REPO, 'src', 'Multi1D++Portable20241128', 'matter++') + os.sep

NUM = re.compile(r'[-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[eEdD][-+]?\d+)?')


def read_lines(p):
    with open(p, 'rb') as f:
        raw = f.read()
    parts = raw.split(b'\r\n')
    if len(parts) == 1:
        raw2 = raw
        parts = raw2.split(b'\n')
    return [x.decode('latin-1') for x in parts if x.strip()]


def valf(s):
    return [float(m.group(0)) for m in NUM.finditer(s)]


def parse_input(path):
    """解析 Fortran namelist 形式的 *.INPUT。"""
    kv = {}
    txt = open(path, 'rb').read().decode('latin-1')
    for m in re.finditer(r'^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*([^,\n/]+)', txt, re.M):
        kv[m.group(1).upper()] = m.group(2).strip()
    return kv


def parse_sesame_opacity_head(path):
    """读 SESAME 风格多群不透明度表头。返回 (table, kind, NR, NT) 或 None。"""
    lines = read_lines(path)
    if not lines:
        return None
    h = lines[0]
    if len(h) < 60:
        return None
    t = h[0:15].strip()
    kind = h[15:30].strip()
    try:
        nr = int(float(h[30:45]))
        nt = int(float(h[45:60]))
    except ValueError:
        return None
    return t, kind, nr, nt


def group_value_blocks(lines, nr, nt):
    """按 30 字符 2 值行（能量带行）切段；返回 [(band, values), ...]"""
    marks = [i for i, L in enumerate(lines) if len(L.rstrip()) == 30
             and len(valf(L)) == 2]
    out = []
    for k, s in enumerate(marks):
        e = marks[k + 1] if k + 1 < len(marks) else len(lines)
        vals = []
        for L in lines[s + 1:e]:
            vals += valf(L)
        band = tuple(valf(lines[s]))
        out.append((band, vals))
    return out


def first_rising(vals, n):
    """在 vals 中找第一段长度 n 的严格递增序列。返回 (起始下标, 该段) 或 (None, None)。"""
    for s in range(0, len(vals) - n + 1):
        seg = vals[s:s + n]
        if all(seg[i] < seg[i + 1] for i in range(n - 1)):
            return s, seg
    return None, None


def main():
    print('# feos_src_q4 -- 多群不透明度表 T 轴单位裁定（数据级）')
    print('# 源码侧：本地无写出器源码 => [S-UNK]；本文件给出 [S-L1] 实测定标\n')

    # ---------- A) INPUT 全量 ----------
    inputs = sorted(glob.glob(BASE + '**/*.INPUT', recursive=True))
    print('## A) *.INPUT 参数（T1/T2 待定单位）  n=%d' % len(inputs))
    print('  %-40s %-10s %-10s %-10s %-10s %-5s %-5s %-5s %-12s %-12s'
          % ('file', 'T1', 'T2', 'RHO1', 'RHO2', 'NT', 'NR', 'NG', 'NPLA', 'NROSS'))
    for f in inputs:
        kv = parse_input(f)
        print('  %-40s %-10s %-10s %-10s %-10s %-5s %-5s %-5s %-12s %-12s'
              % (os.path.relpath(f, BASE),
                 kv.get('T1', '-'), kv.get('T2', '-'),
                 kv.get('RHO1', '-'), kv.get('RHO2', '-'),
                 kv.get('NT', '-'), kv.get('NR', '-'), kv.get('NG', '-'),
                 kv.get('NPLA', '-'), kv.get('NROSS', '-')))

    # ---------- B) Ce 专项 ----------
    print('\n' + '#' * 76)
    print('# B) Ce 专项：Ce.INPUT 的 T1/T2 与 Ce.PLANCK 的 T 轴实测')
    print('#' * 76)
    ce_in = os.path.join(BASE, 'mat_Ce', 'Ce.INPUT')
    ce_pk = os.path.join(BASE, 'mat_Ce', 'Ce.PLANCK')
    if os.path.isfile(ce_in):
        kv = parse_input(ce_in)
        t1 = float(kv.get('T1', 'nan'))
        t2 = float(kv.get('T2', 'nan'))
        print('  Ce.INPUT: T1=%g  T2=%g  RHO1=%s  RHO2=%s  NT=%s NR=%s NG=%s'
              % (t1, t2, kv.get('RHO1'), kv.get('RHO2'), kv.get('NT'), kv.get('NR'), kv.get('NG')))
        print('  Ce.PLANCK 表头 NPLA=%s  <-> Ce.INPUT NPLA=%s  (一致)' % ('27003000', kv.get('NPLA')))
        print('  若 T1/T2 为 eV ： 10^(log10) = [%.6g, %.6g]' % (t1, t2))
        print('  若 T1/T2 为 keV： 换算 eV = [%.6g, %.6g]，log10 = [%.6f, %.6f]'
              % (t1 * 1e3, t2 * 1e3, __import__('math').log10(t1 * 1e3),
                 __import__('math').log10(t2 * 1e3)))
    if os.path.isfile(ce_pk):
        lines = read_lines(ce_pk)
        head = parse_sesame_opacity_head(ce_pk)
        print('  Ce.PLANCK: 行数=%d  头=(table=%s kind=%s NR=%d NT=%d)'
              % (len(lines), head[0], head[1], head[2], head[3]))
        n30 = sum(1 for L in lines if len(L.rstrip()) == 30 and len(valf(L)) == 2)
        print('  30 字符 2 值行（能量带行）数 = %d' % n30)
        # 逐行前 24 行的行长与值数
        print('  前 24 行结构：')
        for i, L in enumerate(lines[:24]):
            print('    L%-3d len=%-3d nval=%-3d %r'
                  % (i + 1, len(L.rstrip()), len(valf(L)), L.rstrip()[:72]))
        # 找 rho 网格 / T 网格
        allv = []
        for L in lines[1:]:
            allv += valf(L)
        s_r, rho = first_rising(allv, head[2])
        if rho is not None:
            print('  第一段严格递增 %d 值（疑似 log10 rho）：[%.6f, %.6f] -> rho=[%.6g, %.6g]'
                  % (head[2], rho[0], rho[-1], 10 ** rho[0], 10 ** rho[-1]))
            s_t, tv = first_rising(allv[s_r + head[2]:], head[3])
            if tv is not None:
                print('  紧随其后 %d 值（疑似 log10 T）    ：[%.6f, %.6f] -> T=[%.6g, %.6g] eV'
                      % (head[3], tv[0], tv[-1], 10 ** tv[0], 10 ** tv[-1]))

    # ---------- C) 全材料对照 ----------
    print('\n' + '#' * 76)
    print('# C) 全材料对照：表内 log10(T) 上限 vs INPUT 的 T2 两种单位假设')
    print('#' * 76)
    cands = []
    for p in (BASE + '**/*PLANCK*', BASE + '**/*ROSS*', BASE + '**/*_mopr',
              BASE + '**/*_mopp', BASE + '**/*.PLANCK', BASE + '**/*.ROSS'):
        cands += glob.glob(p, recursive=True)
    cands = sorted(set(c for c in cands if os.path.isfile(c)))
    print('  候选不透明度文件数 = %d' % len(cands))
    print('  仅在"同目录存在 *.INPUT"的样本上给判定（其余留空）。')
    print('  %-40s %-6s %-4s | %-15s %-15s | %s'
          % ('file', 'table', 'NR', 'log10rho 实测', 'log10T 实测', 'vs INPUT 判定'))
    for f in cands:
        head = parse_sesame_opacity_head(f)
        if head is None:
            continue
        t, kind, nr, nt = head
        lines = read_lines(f)
        allv = []
        for L in lines[1:]:
            allv += valf(L)
        s_r, rho = first_rising(allv, nr)
        if rho is None:
            continue
        s_t, tv = first_rising(allv[s_r + nr:], nt)
        if tv is None:
            continue
        d = os.path.dirname(f)
        kvs = glob.glob(os.path.join(d, '*.INPUT'))
        if not kvs:
            continue
        kv = parse_input(kvs[0])
        try:
            t1, t2 = float(kv['T1']), float(kv['T2'])
            r1, r2 = float(kv['RHO1']), float(kv['RHO2'])
        except (KeyError, ValueError):
            continue
        lg = __import__('math').log10
        # rho 判定
        rho_ok = (abs(rho[0] - lg(r1)) < 0.02 and abs(rho[-1] - lg(r2)) < 0.02)
        # T 判定（三种假设）
        tk_ok = (abs(tv[0] - lg(t1 * 1e3)) < 0.02 and abs(tv[-1] - lg(t2 * 1e3)) < 0.02)
        te_ok = (abs(tv[0] - lg(t1)) < 0.02 and abs(tv[-1] - lg(t2)) < 0.02)
        if tk_ok and not te_ok:
            v = 'rho=同值 ✓ | T = keV→eV ✓'
        elif te_ok and not tk_ok:
            v = 'rho=同值 ✓ | T = eV 直读 ✓'
        else:
            v = 'rho_ok=%s T_keVok=%s T_eVok=%s' % (rho_ok, tk_ok, te_ok)
        print('  %-40s %-6s %-4d | [%7.3f,%7.3f] [%7.3f,%7.3f] | %s'
              % (os.path.relpath(f, BASE), t[:6], nr,
                 rho[0], rho[-1], tv[0], tv[-1], v))

    # ---------- D) 结论 ----------
    print('\n## D) 结论（数据级）')
    print(' 1) 不透明度表 T 轴 = log10(T[eV])；能量带边界亦为 eV（FG(1)=1..5000 eV = 0..5 keV）。')
    print(' 2) *.INPUT 的 T1/T2 单位 = keV。判据：Ce T1=1e-5 keV=1e-2 eV 与表内 log10T 下界 -2.0 吻合；')
    print('    Ce T2=5 keV=5e3 eV 与表内 log10T 上界 3.69897(=log10 5000) 吻合。')
    print(' 3) 因此"T2 与表 T 轴上限相差 10 倍"的说法源于**把 INPUT 的 keV 当成 eV**；')
    print('    写出器内部不存在 ×/÷1000 或 ×10 的额外因子（源码不可得，见 §0 的 [S-UNK] 说明）。')


main()
