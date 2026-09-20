# -*- coding: utf-8 -*-
"""最终交付核验：multi_src 树 + 文档指标 + 备份清单。"""
import os, re, hashlib

ROOT = r'E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\input_gen\gen_eos_op'
DST = os.path.join(ROOT, 'src', 'multi_src')
DOCD = os.path.join(ROOT, 'src', 'multi_docs')
DOC = os.path.join(DOCD, 'MultiEOSOP格式说明.md')

print('=' * 78)
print('A. src/multi_src 最终结构')
print('=' * 78)
tf = tb = 0
for dp, dn, fn in os.walk(DST):
    rel = os.path.relpath(dp, DST)
    if rel == '.':
        rel = ''
    depth = 0 if not rel else rel.count(os.sep) + 1
    ind = '  ' * (depth - 1)
    if rel:
        n = len(fn)
        s = sum(os.path.getsize(os.path.join(dp, f)) for f in fn)
        print('%s%s/   (%d files, %d B)' % (ind, os.path.basename(dp), n, s))
        tf += n; tb += s
    else:
        for f in sorted(fn):
            fp = os.path.join(dp, f)
            print('  %-26s %12d' % (f, os.path.getsize(fp)))
            tf += 1; tb += os.path.getsize(fp)
print()
print('TOTAL: %d files, %d bytes (%.2f MB)' % (tf, tb, tb / 1048576))

print()
print('=' * 78)
print('B. 文档最终指标')
print('=' * 78)
txt = open(DOC, encoding='utf-8').read()
cn = len(re.findall(r'[\u4e00-\u9fff]', txt))
print('路径   :', DOC)
print('字节数 :', os.path.getsize(DOC))
print('字符数 :', len(txt))
print('行数   :', len(txt.split('\n')))
print('汉字数 :', cn, '/ 门禁 80000', 'PASS' if cn >= 80000 else 'FAIL')
print('sha1   :', hashlib.sha1(txt.encode('utf-8')).hexdigest()[:16])
print()
print('章节标题数 :', len(re.findall(r'^#{1,4}\s+\S', txt, re.M)))
print('表格行块数 :', len(re.findall(r'^\|.*\|$', txt, re.M)))
print('代码块数   :', len(re.findall(r'^```', txt, re.M)) // 2)

print()
print('=' * 78)
print('C. src/multi_docs 备份清单')
print('=' * 78)
for f in sorted(os.listdir(DOCD)):
    print('  %-34s %10d' % (f, os.path.getsize(os.path.join(DOCD, f))))
