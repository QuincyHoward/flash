# -*- coding: utf-8 -*-
"""精化普查：用"是否闭合"作为归属判据。
   单群表: lines == 1 + D
   多群表: lines == n30 × (2 + D)
   不闭合者 -> 归入其他族（列出供核对）
"""
import os, collections

ROOT = r'E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\input_gen\gen_eos_op'
M = os.path.join(ROOT, 'src', 'Multi1D++Portable20241128', 'matter++')
OUT = os.path.join(ROOT, '.workbuddy', 'tmp', 'census_mg2.txt')


def isnum(s):
    try:
        float(s)
        return True
    except ValueError:
        return False


belong, others = [], []
allf = [os.path.join(dp, f) for dp, _, fn in os.walk(M) for f in fn]
for p in allf:
    rel = os.path.relpath(p, M)
    try:
        raw = open(p, 'rb').read().replace(b'\r\n', b'\n')
    except OSError:
        continue
    L = [x.decode('latin-1') for x in raw.split(b'\n') if x.strip()]
    if not L or len(L[0]) != 60:
        continue
    f = [L[0][j:j + 15].strip() for j in range(0, 60, 15)]
    if not (isnum(f[2]) and isnum(f[3])):
        continue
    try:
        NR, NT = int(float(f[2])), int(float(f[3]))
    except ValueError:
        continue
    if not (2 <= NR <= 500 and 2 <= NT <= 500):
        continue
    D = -(-(NR + NT + NR * NT) // 4)
    n30 = sum(1 for l in L if len(l) == 30)
    odd = sum(1 for l in L if len(l) not in (30, 60))
    n = len(L)
    style = 'Z' if isnum(f[1]) else 'P'
    kd = f[1] if style == 'P' else '(数值)'
    if n30 == 0 and n == 1 + D:
        belong.append((rel, '单群', kd, f[0], NR, NT, 0, D, n, odd))
    elif n30 > 0 and n == n30 * (2 + D):
        belong.append((rel, '多群', kd, f[0], NR, NT, n30, D, n, odd))
    else:
        others.append((rel, kd, f[0], NR, NT, n30, D, n, 1 + D, n30 * (2 + D)))

buf = []
A = buf.append
A('=' * 90)
A('MULTI 单群/多群表族 —— 全量普查（判据 = 公式闭合）')
A('=' * 90)
A('matter++ 文件总数 = %d' % len(allf))
A('归属本族 = %d   不闭合（属其他族或有残差）= %d' % (len(belong), len(others)))
A('')
A('按样式: %s' % dict(collections.Counter(r[1] for r in belong)))
A('按后缀:')
for k, v in collections.Counter(
        os.path.splitext(os.path.basename(r[0]))[1] or '(无扩展名)'
        for r in belong).most_common():
    A('   %-30s %3d' % (k, v))
A('')
A('按一级目录 (Top 25):')
for k, v in collections.Counter(r[0].split(os.sep)[0] for r in belong).most_common(25):
    A('   %-22s %3d' % (k, v))
A('')
A('类别名(kind)分布:')
for k, v in collections.Counter(r[2] for r in belong).most_common():
    A('   %-24s %3d' % (k, v))
A('')
A('ID 字段分布 (Top 30):')
for k, v in collections.Counter(r[3] for r in belong).most_common(30):
    A('   %-18s %3d' % (k, v))
A('')
A('缺陷行(非 30/60)非零的文件: %d'
  % sum(1 for r in belong if r[9]))
for r in belong:
    if r[9]:
        A('   %-46s 缺陷行=%d' % (r[0], r[9]))
A('')
A('=' * 90)
A('不闭合的文件（需归入其他族 / 有残差）—— %d 个' % len(others))
A('=' * 90)
A('%-46s %-12s %-16s %4s %4s %5s %5s %7s %7s' %
  ('rel', 'kind', 'id', 'NR', 'NT', 'n30', 'D', 'lines', 'pred1'))
for r in sorted(others):
    A('%-46s %-12s %-16s %4d %4d %5d %5d %7d %7d'
      % (r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8]))
A('')
A('=' * 90)
A('本族文件全清单（按目录）')
A('=' * 90)
for r in sorted(belong):
    A('%-50s %-4s %-12s %-16s NR=%-4d NT=%-4d K=%-4d D=%-4d lines=%-7d'
      % (r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8]))

open(OUT, 'w', encoding='utf-8', newline='\n').write('\n'.join(buf))
print('written %s  (%d lines)' % (OUT, len(buf)))
print('belong=%d others=%d' % (len(belong), len(others)))
