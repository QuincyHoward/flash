# -*- coding: utf-8 -*-
"""盘点 .workbuddy/tmp 全部内容 + 读文档尾部（§15.12–附录）。"""
import os, re, json

ROOT = r'E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\input_gen\gen_eos_op'
TMP = os.path.join(ROOT, '.workbuddy', 'tmp')

print('=' * 78)
print('A. .workbuddy/tmp 顶层内容')
print('=' * 78)
for name in sorted(os.listdir(TMP)):
    p = os.path.join(TMP, name)
    if os.path.isdir(p):
        n = 0; sz = 0
        for dp, dn, fn in os.walk(p):
            for f in fn:
                fp = os.path.join(dp, f)
                try:
                    sz += os.path.getsize(fp); n += 1
                except OSError:
                    pass
        print('DIR  %-34s %5d files  %12d B' % (name, n, sz))
    else:
        print('FILE %-34s %12d B' % (name, os.path.getsize(p)))

print()
print('=' * 78)
print('B. 子目录树（两级）')
print('=' * 78)
for name in sorted(os.listdir(TMP)):
    p = os.path.join(TMP, name)
    if not os.path.isdir(p):
        continue
    print('# ' + name)
    for sub in sorted(os.listdir(p)):
        sp = os.path.join(p, sub)
        if os.path.isdir(sp):
            cnt = sum(len(f) for _, _, f in os.walk(sp))
            print('   DIR  %s/  (%d files)' % (sub, cnt))
        else:
            print('        %-44s %10d' % (sub, os.path.getsize(sp)))
    print()

print()
print('=' * 78)
print('C. 文档尾部 §15.12 起（行号）')
print('=' * 78)
DOC = os.path.join(ROOT, 'src', 'multi_docs', 'MultiEOSOP格式说明.md')
L = open(DOC, encoding='utf-8').read().split('\n')
start = None
for i, l in enumerate(L):
    if re.match(r'^#{3,4}\s+15\.12\b', l):
        start = i
        break
for i in range(start, min(start + 400, len(L))):
    l = L[i]
    if re.match(r'^#{1,4}\s', l):
        print('%6d  %s' % (i + 1, l[:96]))
    elif i < start + 6:
        print('%6d  | %s' % (i + 1, l[:96]))
print()
print('总行数', len(L), ' 字符', len('\n'.join(L)))
