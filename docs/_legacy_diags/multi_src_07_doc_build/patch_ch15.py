# -*- coding: utf-8 -*-
"""第15章缺口清单更新：关闭本轮 FEOS 源码级解出的项目；第6章陷阱表同步。"""
import io

P = r'src/multi_docs/MultiEOSOP格式说明.md'
d = io.open(P, encoding='utf-8').read()
n0 = len(d)
log = []

def rep(old, new, name):
    global d
    c = d.count(old)
    assert c == 1, '%s: count=%d' % (name, c)
    d = d.replace(old, new, 1)
    log.append('%s ok (%+d)' % (name, len(new) - len(old)))

# ===== 第15章 本章实测锚点：补 A35-A42 =====
rep(u'| A32 | \u9057\u6f0f\u6750\u6599\u76ee\u5f55\u6570 | **19 \u4e2a**\uff08\u6587\u4ef6\u6570 2\u201322\uff09 | 15.8.1 |',
    u'| A32 | \u9057\u6f0f\u6750\u6599\u76ee\u5f55\u6570 | **19 \u4e2a**\uff08\u6587\u4ef6\u6570 2\u201322\uff09 | 15.8.1 |\n'
    u'| A35 | `.feos` \u771f\u5b9e\u884c\u5bbd | **150 = 10\u00d715**\uff08`Al.feos` 23,874 \u884c\u5168 150\uff09 | 10.6.2 |\n'
    u'| A36 | `.feos` \u65e0\u5206\u9694\u7b26\u7684\u6839\u56e0 | `FE-00_DEFINITS.H:28` **`#define SF_TRENN ""`** | 10.6.2 |\n'
    u'| A37 | `.301` \u53cc\u5b9e\u7269 | `Al.feos.301` **60 \u5b57\u7b26**\uff1b`Au.301` **64 \u5b57\u7b26** | 10.6.3 |\n'
    u'| A38 | `.mexport` \u884c\u5bbd | **\u4e25\u683c 80 \u5b57\u7b26**\uff08`B.mexport` 22,508 \u884c\u65e0\u4f8b\u5916\uff09 | 10.6.4 |\n'
    u'| A39 | `.cst` \u5217\u6570\u4e0e\u5355\u4f4d | 4 \u5217\uff1b**1/cm\u00b3 / g\u00b7cm\u207b\u00b3 / MBar / \u65e0\u91cf\u7eb2** | 10.6.5 |\n'
    u'| A40 | `4gnuplot` \u5f52\u5c5e | FEOS \u5168\u6e90\u7801 + 99,338 B \u6587\u6863\u4e2d **0 \u547d\u4e2d** \u21d2 \u975e\u539f\u751f | 10.6.6 |\n'
    u'| A41 | `.feos` \u53c2\u6570\u884c\u5b57\u6bb5\u6570 | \u884c 0 / \u884c 1 **\u5404 10 \u4e2a**\uff08\u5171 20\uff09 | 10.6.10 |\n'
    u'| A42 | \u65b0\u589e\u540d\u5b9e\u4e0d\u7b26\u6837\u672c | `hyades/qeos/qeos_392.dat.feos`\u3001`hyades/sesame/eos_41.dat.feos`\uff08**\u884c\u5bbd 75**\uff09 | 10.6.11 |',
    'ch15-anchors')

# ===== 第15章 本章缺口：把 FEOS 相关缺口标为已关闭 =====
rep(u'9. **`.sesame` \u7684\u751f\u6210\u5668\u672a\u77e5**\uff1a\u672a\u627e\u5230\u76f4\u63a5\u5199\u51fa `.sesame` \u7684\u7a0b\u5e8f\uff08FEOS \u5bfc\u51fa\u7684 SESAME \u4e3a `.mexport` / `.data.txt`\uff0c\u975e `.sesame`\uff09\u3002**\u4f46\u683c\u5f0f\u672c\u8eab\u5df2\u5b8c\u5168\u89e3\u5f00**\uff08\u8bb0\u5f55\u5e8f + \u5c3a\u5bf8\u516c\u5f0f 7/7 \u95ed\u5408\uff0c\u89c1 15.2\uff09\uff0c\u6b64\u9879\u4ec5\u5f71\u54cd"\u8c01\u5199\u7684"\u800c\u4e0d\u5f71\u54cd"\u600e\u4e48\u8bfb"\u3002',
    u'9. **`.sesame` \u7684\u751f\u6210\u5668\u672a\u77e5**\uff1a\u672a\u627e\u5230\u76f4\u63a5\u5199\u51fa `.sesame` \u7684\u7a0b\u5e8f**\uff08FEOS 16.7 \u6e90\u7801\u5df2\u9010\u8868\u6392\u67e5\uff1a\u5b83\u53ea\u5199 `.mexport` / `.data.txt` / `.301` \u7b49\uff0c**\u65e0 `.sesame` \u5199\u51fa\u5668**\uff09**\u3002**\u4f46\u683c\u5f0f\u672c\u8eab\u5df2\u5b8c\u5168\u89e3\u5f00**\uff08\u8bb0\u5f55\u5e8f + \u5c3a\u5bf8\u516c\u5f0f 7/7 \u95ed\u5408\uff0c\u89c1 15.2\uff09\uff0c\u6b64\u9879\u4ec5\u5f71\u54cd"\u8c01\u5199\u7684"\u800c\u4e0d\u5f71\u54cd"\u600e\u4e48\u8bfb"\u3002**\u672c\u8f6e\u5df2\u7531\u6e90\u7801\u6392\u67e5\u786e\u8ba4**\u3002',
    'ch15-gap9')

rep(u'10. **`mat_CH2` / `mat_CHBr` / `CHBr3at%` \u7684\u914d\u6bd4\u8bed\u4e49\u672a\u5c55\u5f00**\u2014\u2014\u76ee\u5f55\u540d\u542b"at%"\uff08\u539f\u5b50\u767e\u5206\u6bd4\uff09\uff0c\u4f46\u672a\u627e\u5230\u58f0\u660e\u5177\u4f53\u914d\u6bd4\u7684\u6587\u4ef6\u3002',
    u'10. **`mat_CH2` / `mat_CHBr` / `CHBr3at%` \u7684\u914d\u6bd4\u8bed\u4e49\u672a\u5c55\u5f00**\u2014\u2014\u76ee\u5f55\u540d\u542b"at%"\uff08\u539f\u5b50\u767e\u5206\u6bd4\uff09\uff0c\u4f46\u672a\u627e\u5230\u58f0\u660e\u5177\u4f53\u914d\u6bd4\u7684\u6587\u4ef6\u3002\n'
    u'11. ~~**FEOS \u65cf\u7684 5 \u6761\u683c\u5f0f\u7ea7\u7f3a\u53e3**~~\uff1a**\u5168\u90e8\u5df2\u95ed\u5408**\u3002\u672c\u8f6e\u901a\u8fc7\u5b98\u65b9\u6e90\u7801\u5305 `FEOS_package_v16.7` \u5b8c\u6210\u6e90\u7801\u7ea7\u6838\u9a8c\uff0c\u5305\u62ec `.feos` 10\u00d715\u3001`.301/.304/.305` \u53cc\u5b9e\u7269\u3001`.mexport` 80 \u5b57\u7b26\u3001`.cst` 4 \u5217\u3001`.critical.dat` 14 \u6bb5\u3001`BulkModulusRef` \u5355\u4f4d\u4e0d\u77db\u76fe\u3001`.hug` \u547d\u540d\u89c4\u5219\u3001`Path=` \u5c5e\u65e7 MPQEOS v2.0\u3002**\u8be6\u89c1\u7b2c 10.6 \u8282**\uff08\u516b\u95ee\u5168\u90e8\u89e3\u51fa\uff09\u3002\n'
    u'12. **`*4gnuplot` \u7684\u8f6c\u5199\u5de5\u5177\u4e0e\u4f5c\u8005**\uff1a\u5df2\u786e\u8ba4**\u975e FEOS \u539f\u751f**\uff08\u6e90\u7801 0 \u547d\u4e2d\uff09\uff0c\u4f46\u5177\u4f53\u8f6c\u5199\u811a\u672c\u4e0e\u4f5c\u8005\u65e0\u4e00\u624b\u4f9d\u636e\u3002`[S-UNK]`\uff08\u4f4e\u4f18\u5148\u7ea7\uff09\u3002',
    'ch15-gap10')

d = d.replace('\r\n', '\n')
io.open(P, 'w', encoding='utf-8', newline='\n').write(d)
print('\n'.join(log))
print('chars %d -> %d (%+d)' % (n0, len(d), len(d) - n0))
print('bytes %d' % len(d.encode('utf-8')))
