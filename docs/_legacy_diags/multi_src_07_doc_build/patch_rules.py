# -*- coding: utf-8 -*-
"""Fix rules R1/R2/R7, add R15, and correct anchors A1-A8 in ch.15."""
import io
import os

P = os.path.join('src', 'multi_docs', 'MultiEOSOP\u683c\u5f0f\u8bf4\u660e.md')
t = io.open(P, encoding='utf-8').read()
before = len(t)
ops = 0


def rep(old, new, label):
    global t, ops
    n = t.count(old)
    if n:
        t = t.replace(old, new)
        ops += 1
    print('%-3d %s' % (n, label))


# --- rules ----------------------------------------------------------------
rep('| R1 | `.sesame` \u5fc5\u7528 `n = 4 + 2\u00b7n\u03c1 + nT + 2\u00b7n\u03c1\u00b7nT` \u505a**\u5f3a\u5236\u4e0d\u53d8\u5f0f\u6821\u9a8c**\uff1b\u4e0d\u95ed\u5408\u5373\u62a5\u9519 | 15.2.3 |',
    '| R1 | `.sesame` \u5fc5\u7528 `n = 4 + 2\u00b7n\u03c1 + ne + 2\u00b7n\u03c1\u00b7ne` \u505a**\u5f3a\u5236\u4e0d\u53d8\u5f0f\u6821\u9a8c**\uff1b\u4e0d\u95ed\u5408\u5373\u62a5\u9519 | 15.2.3 |',
    'R1 formula')

rep('| R2 | `.sesame` \u7684 `n\u03c1`\u3001`nT` **\u4e0d\u5f97**\u4ece\u6570\u636e\u63a8\u65ad\uff0c**\u5fc5\u987b**\u53d6\u8868\u5934\u7b2c 3\u30014 \u5b57\u6bb5 | 15.2.2 |',
    '| R2 | `.sesame` \u7684 `n\u03c1`\u3001`ne` **\u4e0d\u5f97**\u4ece\u6570\u636e\u63a8\u65ad\uff0c**\u5fc5\u987b**\u53d6\u8868\u5934\u7b2c 3\u30014 \u5b57\u6bb5 | 15.2.2 |',
    'R2 names')

rep('| R7 | `.sesame` \u4e24\u5757\u6570\u636e\u5757**\u5747\u4e3a\u5916\u5c42 nT\u3001\u5185\u5c42 n\u03c1**\uff08\u5bc6\u5ea6\u53d8\u5316\u6700\u5feb\uff09 | 15.2.5 |',
    '| R7 | `.sesame` \u4e24\u5757\u6570\u636e\u5757**\u5747\u4e3a\u5916\u5c42 ne\u3001\u5185\u5c42 n\u03c1**\uff08\u5bc6\u5ea6\u53d8\u5316\u6700\u5feb\uff09 | 15.2.4 |',
    'R7 layout')

# insert R15 after R14
r14 = '| R14 | \u9047 `.cn4` \u65f6\u82e5\u5934\u90e8\u7b2c 4 \u884c**\u4e0d\u662f** 5 \u4e2a\u6570\uff0c\u987b\u8f6c `.cnr` \u8def\u5f84 | 15.10.5 |'
r15 = (r14 + '\n'
       '| R15 | **\u672c\u5730\u624b\u518c\u660e\u6587\u5b58\u5728\u65f6\uff0c\u624b\u518c\u7684\u5b57\u6bb5\u8bb0\u5f55\u5e8f\u4f18\u5148\u4e8e\u4efb\u4f55\u5f62\u6001\u5b66\u5224\u636e**\uff1b'
       '\u5f62\u6001\u5b66\uff08`\u221d\u03c1`\u3001`T\u21920 \u5f52\u96f6` \u7b49\uff09**\u53ea\u7528\u4e8e\u4ea4\u53c9\u9a8c\u8bc1\uff0c\u4e0d\u7528\u4e8e\u5b9a\u5e8f** | '
       '15.12.3b\uff08\u6559\u8bad\uff09\u300115.2.4 |')
rep(r14, r15, 'R15 inserted')

# --- anchors --------------------------------------------------------------
rep('| A1 | `.sesame` \u5c3a\u5bf8\u516c\u5f0f | `n = 4 + 2\u00b7n\u03c1 + nT + 2\u00b7n\u03c1\u00b7nT`\uff0c**7/7 \u95ed\u5408** | 15.2.3 |',
    '| A1 | `.sesame` \u5c3a\u5bf8\u516c\u5f0f | `n = 4 + 2\u00b7n\u03c1 + ne + 2\u00b7n\u03c1\u00b7ne`\uff0c**7/7 \u95ed\u5408** | 15.2.3 |',
    'A1 formula')

rep('| A6 | `Au` \u7b2c\u4e8c\u5757\u6570\u636e `B/\u03c1` \u6052\u5b9a | **644.79**\uff086 \u4e2a \u03c1 \u70b9\u5168\u540c\uff09\u2192 B = \u538b\u5f3a | 15.2.4 |',
    '| A6 | `Au` \u7b2c 5 \u6bb5\uff08`P`\uff09`P/\u03c1` \u6052\u5b9a | **644.791**\uff086 \u4e2a \u03c1 \u70b9\u5168\u540c\uff09\u2192 \u786e\u8ba4\u8be5\u6bb5\u4e3a\u538b\u5f3a | 15.2.4 |',
    'A6 P')

rep('| A7 | `Au` \u7b2c\u4e00\u5757\u6570\u636e\u5728 T\u21920 \u65f6 | **\u6052\u4e3a 0.0** \u2192 A = \u6bd4\u5185\u80fd | 15.2.4 |',
    '| A7 | `Au` \u7b2c 4 \u6bb5\uff08`e0`\uff09 | **\u6052\u4e3a 0.0**\uff1b`eos_22` \u5219\u4e3a `0.304843` \u7f13\u964d\u5e73\u53f0 \u2192 \u786e\u8ba4\u4e3a\u51b7\u80fd\u91cf | 15.2.4 |',
    'A7 e0')

# append two new anchors for the corrected layout
a8 = '| A8 | `Ta2O5` \u5217\u540d\u58f0\u660e | `#eV g/cc J/cm3 J/g Mbar*cm3/g erg/g Pressure(dyne/cm2)` | `matter++/Ta2O5/Ta2O5_EOS(T, same rho).dat:2` |'
a8new = (a8 + '\n'
         '| A33 | `.sesame` \u6743\u5a01\u8bb0\u5f55\u5e8f | `\u8868\u5934 / r[nr] / de[ne] / e0[nr] / P[ne\u00b7nr] / T[ne\u00b7nr]` | '
         '`[S-L1] doc/MULTI\u4f7f\u7528\u7684SESAME\u6570\u636e\u6587\u4ef6\u683c\u5f0f.docx`\uff0c\u7ecf 7/7 \u6837\u672c `leftover=0` \u5370\u8bc1 |\n'
         '| A34 | `.sesame` \u7684 `T` \u5355\u4f4d | **\u5f00\u5c14\u6587**\uff1a`Au` \u6700\u5927 `T = 3.66186e7` \u00f7 11604.519 = **3155.6 eV** | 15.2.4 |')
rep(a8, a8new, 'A33/A34 added')

io.open(P, 'w', encoding='utf-8', newline='').write(t)
print('ops=%d  chars %d -> %d' % (ops, before, len(t)))
