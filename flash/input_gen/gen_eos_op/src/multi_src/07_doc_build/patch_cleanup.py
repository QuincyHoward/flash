# -*- coding: utf-8 -*-
"""Clean up stale wording after the .sesame layout correction."""
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


# 1. 15.2.1 table header wording (nT -> ne) -------------------------------
rep('| \u6587\u4ef6 | \u6807\u91cf\u603b\u6570 `n` | \u8868\u5934\u7b2c 3 \u5b57\u6bb5 | \u8868\u5934\u7b2c 4 \u5b57\u6bb5 |',
    '| \u6587\u4ef6 | \u6807\u91cf\u603b\u6570 `n` | \u8868\u5934\u7b2c 3 \u5b57\u6bb5\uff08`n\u03c1`\uff09 | \u8868\u5934\u7b2c 4 \u5b57\u6bb5\uff08`ne`\uff09 |',
    '15.2.1 table hdr')

# 2. 15.3.5 : `nρ=3, nT=19` -> `ne` ---------------------------------------
rep('`PowerLawTa2O5_EOS.SESAME`\uff082,217 B\uff09\u4e0e `PowerLawTa2O5_EOS.SESAME_`\uff084,650 B\uff09**\u4e0d\u662f\u91cd\u547d\u540d\uff0c\u800c\u662f\u4e24\u4e2a\u4e0d\u540c\u7f51\u683c\u7248\u672c**\uff1a\u524d\u8005 `n\u03c1=3, nT=19`\uff0c\u540e\u8005 `n\u03c1=5, nT=26`\uff0c\u6807\u91cf\u6570 143 vs 300\u3002\u4e8c\u8005**\u540c\u4e3a `n = 4 + 2\u00b7n\u03c1 + nT + 2\u00b7n\u03c1\u00b7nT`**\uff0c\u5747\u53ef\u6309 15.2',
    '`PowerLawTa2O5_EOS.SESAME`\uff082,217 B\uff09\u4e0e `PowerLawTa2O5_EOS.SESAME_`\uff084,650 B\uff09**\u4e0d\u662f\u91cd\u547d\u540d\uff0c\u800c\u662f\u4e24\u4e2a\u4e0d\u540c\u7f51\u683c\u7248\u672c**\uff1a\u524d\u8005 `n\u03c1=3, ne=19`\uff0c\u540e\u8005 `n\u03c1=5, ne=26`\uff0c\u6807\u91cf\u6570 143 vs 300\u3002\u4e8c\u8005**\u540c\u4e3a `n = 4 + 2\u00b7n\u03c1 + ne + 2\u00b7n\u03c1\u00b7ne`**\uff0c\u5747\u53ef\u6309 15.2',
    '15.3.5 ne')

rep('\u5373 `id = \u5360\u4f4d\u5e38\u91cf`\u3001`mode = 1`\u3001`n\u03c1 = 5`\u3001`nT = 26`\u3002',
    '\u5373 `id = \u5360\u4f4d\u5e38\u91cf`\u3001`mode = 1`\u3001`n\u03c1 = 5`\u3001`ne = 26`\u3002',
    '15.3.5 fields')

# 3. 15.11.2 comparison formula -------------------------------------------
rep('\u4e0e 15.2 \u7684 `.sesame` \u516c\u5f0f\uff08`4 + 2\u00b7n\u03c1 + nT + 2\u00b7n\u03c1\u00b7nT`\uff09**\u4e0d\u540c**',
    '\u4e0e 15.2 \u7684 `.sesame` \u516c\u5f0f\uff08`4 + 2\u00b7n\u03c1 + ne + 2\u00b7n\u03c1\u00b7ne`\uff09**\u4e0d\u540c**',
    '15.11.2 formula')

# 4. 本章缺口 #1 -- tail is now closed ------------------------------------
old_gap1 = ('1. **`.sesame` \u5c3e\u5757\u8bed\u4e49\u672a\u5b9a\u540d**\u2014\u2014\u957f\u5ea6\uff08`n\u03c1`\uff09\u3001'
            '\u4f4d\u7f6e\uff08\u6570\u636e\u533a\u672b\u5c3e\uff09\u3001\u6570\u503c\u5747\u5df2\u63d0\u53d6\uff0c'
            '\u4f46\u65e0\u4efb\u4f55\u672c\u5730\u6587\u4ef6\u7ed9\u51fa\u6587\u5b57\u58f0\u660e\u3002\u5df2\u6392\u9664\u538b\u5f3a\u3001'
            '\u6bd4\u5185\u80fd\u3001`\u03c1^(5/3)` \u5e42\u5f8b\u4e09\u79cd\u53ef\u80fd\uff1b\u5f62\u6001\u4e3a"\u62f1\u5f62"\uff0c'
            '\u7591\u4e3a\u7b49\u6e29\u7ebf\u6216\u76f8\u754c\u53c2\u8003\u91cf\u3002**\u9700\u4e0a\u6e38 FEOS/SESAME '
            '\u751f\u6210\u5668\u7684\u8bf4\u660e\u624d\u80fd\u5173\u95ed\u3002**')
new_gap1 = ('1. ~~**`.sesame` \u5c3e\u5757\u8bed\u4e49\u672a\u5b9a\u540d**~~\uff1a**\u5df2\u5173\u95ed**\u3002'
            '\u5c3e\u5757\u5c31\u662f\u624b\u518c\u660e\u6587\u7684 **`e0[nr]` \u51b7\u80fd\u91cf**\uff08`Mbar\u00b7cm\u00b3/g`\uff09\uff0c'
            '\u89c1 15.2.4\u201315.2.5\u3002\u672c\u6761\u4e4b\u6240\u4ee5\u957f\u671f\u60ac\u7f6e\uff0c\u662f\u56e0\u4e3a\u6b64\u524d'
            '**\u672a\u53bb\u8bfb\u672c\u5730\u624b\u518c\u7684\u8bb0\u5f55\u9aa8\u67b6**\uff0c\u800c\u662f\u7528\u5f62\u6001\u5b66\u53cd\u63a8'
            '\u3002\u7ecf\u9a8c\u5df2\u5199\u5165\u89c4\u7ea6 R15\u3002')
rep(old_gap1, new_gap1, 'gap#1 closed')

# 5. gap #9 -- tail source file -------------------------------------------
old_gap9 = ('9. **`.sesame` \u5c3e\u5757\u7684\u6765\u6e90\u6587\u4ef6\u672a\u77e5**\u2014\u2014\u672a\u627e\u5230\u751f\u6210 '
            '`.sesame` \u7684\u7a0b\u5e8f\uff08FEOS \u5bfc\u51fa\u7684 SESAME \u4e3a `.mexport` / `.data.txt`\uff0c'
            '\u975e `.sesame`\uff09\u3002**\u8be5\u540e\u7f00\u7684\u751f\u6210\u94fe\u672a\u95ed\u5408\u3002**')
new_gap9 = ('9. **`.sesame` \u7684\u751f\u6210\u5668\u672a\u77e5**\uff1a\u672a\u627e\u5230\u76f4\u63a5\u5199\u51fa `.sesame` '
            '\u7684\u7a0b\u5e8f\uff08FEOS \u5bfc\u51fa\u7684 SESAME \u4e3a `.mexport` / `.data.txt`\uff0c'
            '\u975e `.sesame`\uff09\u3002**\u4f46\u683c\u5f0f\u672c\u8eab\u5df2\u5b8c\u5168\u89e3\u5f00**'
            '\uff08\u8bb0\u5f55\u5e8f + \u5c3a\u5bf8\u516c\u5f0f 7/7 \u95ed\u5408\uff0c\u89c1 15.2\uff09\uff0c'
            '\u6b64\u9879\u4ec5\u5f71\u54cd"\u8c01\u5199\u7684"\u800c\u4e0d\u5f71\u54cd"\u600e\u4e48\u8bfb"\u3002')
rep(old_gap9, new_gap9, 'gap#9 reframed')

io.open(P, 'w', encoding='utf-8', newline='').write(t)
print('ops=%d  chars %d -> %d' % (ops, before, len(t)))
