# -*- coding: utf-8 -*-
"""探针：读取 §1.2.2 末尾、§15.8、§14 前言，确定补丁锚点。"""
import os
ROOT = r'E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\input_gen\gen_eos_op'
p = os.path.join(ROOT, 'src', 'multi_docs', 'MultiEOSOP格式说明.md')
L = open(p, encoding='utf-8').read().split('\n')
print('total lines', len(L))

def show(a, b, tag):
    print('=' * 20, tag, f'L{a}-{b}')
    for i in range(a - 1, min(b, len(L))):
        print(i + 1, L[i])

# 找 §1.2.2 四域分类法 的收尾
for i, l in enumerate(L):
    if '1.2.3 文件名内嵌点号陷阱' in l:
        show(max(1, i - 22), i + 2, 'sec1.2.2 tail')
        break
print()
for i, l in enumerate(L):
    if '15.8 族覆盖补全' in l:
        show(i + 1, i + 8, 'sec15.8 head')
        break
print()
for i, l in enumerate(L):
    if l.startswith('## 第14章 辅助与边缘格式'):
        show(i + 1, i + 6, 'ch14 head')
        break
print()
for i, l in enumerate(L):
    if '## 0.3 格式全景' in l:
        show(i + 1, i + 3, '0.3')
        break
print()
for i, l in enumerate(L):
    if '0.3.1 八大族一览表' in l:
        show(i + 1, i + 28, '0.3.1')
        break
