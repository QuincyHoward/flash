# -*- coding: utf-8 -*-
"""全量普查：matter++ 下所有属于"MULTI 多群/单群表"格式族的文件。
   判据（实现级）：
     逐行 60 字符、切成 4×15；第 2 段可 float => ZEFF 式（1+D 行/表）；
     第 2 段是文本 => PLANCK/ROSSELAND/EPS 式（K×(2+D) 行）。
   同时统计命名类别与占比。
"""
import os, glob, collections, json

ROOT = r'E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\input_gen\gen_eos_op'
M = os.path.join(ROOT, 'src', 'Multi1D++Portable20241128', 'matter++')
OUT = os.path.join(ROOT, '.workbuddy', 'tmp', 'census_mg.tsv')

KINDS = ('PLANCK', 'ROSSELAND', 'EPS', 'ZEFF')


def isnum(s):
    try:
        float(s)
        return True
    except ValueError:
        return False


rows = []
allfiles = []
for dp, dn, fn in os.walk(M):
    for f in fn:
        allfiles.append(os.path.join(dp, f))
print('matter++ 文件总数 =', len(allfiles))

n_probe = 0
for p in allfiles:
    rel = os.path.relpath(p, M)
    try:
        raw = open(p, 'rb').read(120000)
    except OSError:
        continue
    if b'\r\n' in raw:
        raw = raw.replace(b'\r\n', b'\n')
    L = [x.decode('latin-1') for x in raw.split(b'\n') if x.strip()]
    if not L:
        continue
    l0 = L[0]
    if len(l0) != 60:
        continue
    f = [l0[j:j + 15].strip() for j in range(0, 60, 15)]
    if not (isnum(f[2]) and isnum(f[3])):
        continue
    NR, NT = int(float(f[2])), int(float(f[3]))
    if not (2 <= NR <= 500 and 2 <= NT <= 500):
        continue
    # 判定样式
    f2num = isnum(f[1])
    # 计数 30 字符行（只读前 120KB，若不足则全读）
    if len(raw) >= 120000:
        raw = open(p, 'rb').read().replace(b'\r\n', b'\n')
        L = [x.decode('latin-1') for x in raw.split(b'\n') if x.strip()]
    n30 = sum(1 for l in L if len(l) == 30)
    D = -(-(NR + NT + NR * NT) // 4)
    style = 'ZEFF' if f2num else 'PLANCK/ROSS/EPS'
    pred1 = 1 + D
    predK = n30 * (2 + D)
    if f2num:
        ok = (len(L) == pred1)
        note = 'OK(单表 1+D)' if ok else 'DIFF(1+D=%d)' % pred1
    else:
        ok = (n30 > 0 and len(L) == predK)
        note = 'OK(K=%d)' % n30 if ok else 'DIFF(K×(2+D)=%d)' % predK
    rows.append((rel, f[0], 'Z' if f2num else 'P', NR, NT, n30, D, len(L), pred1, predK, note))

print('判定为 MULTI 表族的文件数 =', len(rows))
okc = sum(1 for r in rows if r[10].startswith('OK'))
print('闭合 OK = %d ; 异常 = %d' % (okc, len(rows) - okc))
print()

# 命名分类
def nclass(rel):
    base = os.path.basename(rel)
    ext = os.path.splitext(base)[1]
    if ext == '':
        return '(无扩展名)'
    return ext


cls = collections.Counter(nclass(r[0]) for r in rows)
print('按后缀分布:')
for k, v in cls.most_common():
    print('   %-14s %3d' % (k, v))
print()

# 目录分布
dr = collections.Counter(r[0].split(os.sep)[0] for r in rows)
print('按一级目录分布 (Top 20):')
for k, v in dr.most_common(20):
    print('   %-22s %3d' % (k, v))
print()

print('样式分布:', dict(collections.Counter(r[2] for r in rows)))
print()
print('=== 异常文件 ===')
for r in rows:
    if not r[10].startswith('OK'):
        print('   %-44s id=%-16s NR=%d NT=%d K=%d lines=%d pred1=%d predK=%d %s'
              % (r[0], r[1], r[3], r[4], r[5], r[7], r[8], r[9], r[10]))
print()
print('=== ID 字段分布 (Top 25) ===')
for k, v in collections.Counter(r[1] for r in rows).most_common(25):
    print('   %-18s %3d' % (k, v))

hdr = ['rel', 'id', 'style', 'NR', 'NT', 'K(n30)', 'D', 'lines', 'pred1', 'predK', 'note']
with open(OUT, 'w', encoding='utf-8', newline='\n') as fh:
    fh.write('\t'.join(hdr) + '\n')
    for r in sorted(rows, key=lambda x: x[0]):
        fh.write('\t'.join(str(x) for x in r) + '\n')
print()
print('written', OUT)
