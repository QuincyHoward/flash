# -*- coding: utf-8 -*-
"""p14: 关闭 §10.4 缺口表第 1 行（.feos 4×15 vs 10×15）。"""
import os
ROOT = r'E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\input_gen\gen_eos_op'
DOC = os.path.join(ROOT, 'src', 'multi_docs', 'MultiEOSOP格式说明.md')
t = open(DOC, encoding='utf-8').read()

old = '| 1 | `.feos` 的"4×15"与"10×15"该如何调和 | `[S-L3] matter++/Readme.txt` 说 4 个 15 字符，实测 `Al.feos` 为 10 个 15 字符；可能是该 Readme 描述的是**读入程序实际取用的前 4 字段**，但无源码佐证 | 正文给出 `[S-L4]` 推论，标注"无源码佐证"；不宣称已解决 |'
new = '| 1 | ~~`.feos` 的"4×15"与"10×15"该如何调和~~ | **已解决** `[S-SRC]`：`FE-00_DEFINITS.H:28` `#define SF_TRENN ""` + `FE-01_TABTOOLS.C:233…258` 的 `if(++count%10) … else "\\n"` ⇒ 字段间**无分隔**、每 10 字段换行 ⇒ **每行 10×15 = 150**。`Readme.txt` 的"4 个 15 字符"**是错的** | 见 §15.12.8 #3、§10.6.2 |'

if t.count(old) == 1:
    t = t.replace(old, new, 1)
    open(DOC, 'w', encoding='utf-8', newline='\n').write(t)
    print('PATCH14 done: OK (%d -> %d)' % (len(open(DOC, encoding='utf-8').read()) - len(new) + len(old), len(t)))
else:
    print('PATCH14: anchor count =', t.count(old))
