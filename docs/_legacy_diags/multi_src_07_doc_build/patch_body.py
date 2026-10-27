# -*- coding: utf-8 -*-
"""正文一致性修正：把仍称 .feos 为 4x15 的地方改为 10x15，并交叉引用 10.6。
   只改"断言性"句子，不动纯叙述 SESAME 4x15 的行。"""
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

# --- 第1章 规则二 ---
rep(u'**\u89c4\u5219\u4e8c\uff1a\u6587\u4ef6\u540d\u542b `.feos` \u2192 FEOS \u65cf\uff0c\u6309 4\u00d715 \u8bfb\u3002**',
    u'**\u89c4\u5219\u4e8c\uff1a\u6587\u4ef6\u540d\u542b `.feos` \u2192 FEOS \u65cf\uff0c\u6309 10\u00d715\uff08=150 \u5b57\u7b26/\u884c\uff09\u8bfb\u3002**\n\n'
    u'> **\u26a0 \u672c\u7248\u66f4\u6b63**\uff1a\u65e7\u7248\u4e0e `matter++/Readme.txt` \u5199\u4f5c"4\u00d715"\uff0c\u5b9e\u4e3a**\u9519\u8bef**\u3002FEOS 16.7 \u5b98\u65b9\u6e90\u7801 `FE-00_DEFINITS.H:28` \u7684 `SF_TRENN=""`\uff08\u5206\u9694\u7b26\u5b9a\u4e49\u4e3a\u7a7a\u4e32\uff09\u5bfc\u81f4 10 \u4e2a 15 \u5b57\u7b26 token \u9996\u5c3e\u76f8\u8fde\uff0c\u5b9e\u6d4b `Al.feos` \u5168 23,874 \u884c\u5747\u4e3a 150 \u5b57\u7b26\u3002\u8be6\u89c1 **10.6.2**\u3002',
    'ch1-rule2')

# --- 第1章 规则三 ---
rep(u'**\u89c4\u5219\u4e09\uff1a\u6587\u4ef6\u540d\u542b `.301`/`.304`/`.305` \u2192 MPQeos \u65cf\uff0c\u6309 4\u00d716 \u8bfb\u3002**',
    u'**\u89c4\u5219\u4e09\uff1a\u6587\u4ef6\u540d\u542b `.301`/`.304`/`.305` \u2192 MPQeos \u65cf\uff0c\u6309 4 \u5b57\u6bb5/\u884c\u8bfb\uff08\u5bbd\u5ea6\u6709 60/64 \u4e24\u79cd\u5b9e\u7269\uff09\u3002**\n\n'
    u'> **\u26a0 \u672c\u7248\u66f4\u6b63**\uff1a\u5b57\u6bb5\u6570\u6052\u4e3a 4\uff0c\u4f46**\u884c\u5bbd\u6709\u4e24\u79cd**\uff1a`%15.8le`\uff082 \u4f4d\u6307\u6570\uff09\u2192 60 \u5b57\u7b26\uff1b3 \u4f4d\u6307\u6570\uff08\u5982 `e+001`\uff09\u2192 16 \u5b57\u7b26/field \u2192 64 \u5b57\u7b26\u3002\u5b9e\u6d4b `Al.feos.301` \u4e3a 60\u3001`Au.301` \u4e3a 64\u3002**\u4e0d\u5f97\u5047\u8bbe\u56fa\u5b9a\u5bbd\u5ea6**\u3002\u8be6\u89c1 **10.6.3**\u3002',
    'ch1-rule3')

# --- 第1章 陷阱表 "同名不同宽" ---
rep(u'| **\u540c\u540d\u4e0d\u540c\u5bbd**\uff1a\u540c\u4e00\u6750\u6599\u7684\u540c\u4e00\u4efd\u6570\u636e\u53ef\u4ee5\u5bfc\u51fa\u4e3a\u4e0d\u540c\u884c\u5bbd\uff0c\u4ec5\u9760\u5185\u5bb9\u65e0\u6cd5\u5728\u8bfb\u53d6\u524d\u5b9a\u5bbd | `Al.feos`\uff084\u00d715\uff0c3,628,968 B\uff09\u4e0e `Al.feos.301`\uff084\u00d716\uff0c620,139 B\uff09\u5185\u5bb9\u8fd1\u4f3c\u4f46\u884c\u5bbd\u4e0d\u540c | `[S-L2] \u4e24\u6587\u4ef6\u7b2c 2\u20134 \u884c\u5bf9\u7167` |',
    u'| **\u540c\u540d\u4e0d\u540c\u5bbd**\uff1a\u540c\u4e00\u6750\u6599\u7684\u540c\u4e00\u4efd\u6570\u636e\u53ef\u4ee5\u5bfc\u51fa\u4e3a\u4e0d\u540c\u884c\u5bbd\uff0c\u4ec5\u9760\u5185\u5bb9\u65e0\u6cd5\u5728\u8bfb\u53d6\u524d\u5b9a\u5bbd | `Al.feos`\uff08**10\u00d715 = 150**\uff0c3,628,968 B\uff09\u4e0e `Al.feos.301`\uff08**4\u00d715 = 60**\uff0c620,139 B\uff09\u5185\u5bb9\u8fd1\u4f3c\u4f46\u884c\u5bbd\u5dee 2.5 \u500d | `[S-SRC] FE-00_DEFINITS.H:28`\uff1b\u4e24\u6587\u4ef6\u884c\u5bbd\u76f4\u65b9\u56fe |',
    'ch1-trap-narrow')

# --- 2.1 表 T4 第 1 行 ---
rep(u'| 1 | 4\u00d715 | 15 | 4 | 60 | `\\s*[+-]?[\\d.]+(?:[EeDd][+-]?\\d+)?` \u914d\u5408\u5217\u5207\u7247 | F1\u3001F3 | `matter++/mat_Al-1.0/AL_eos` \u7b2c 2 \u884c | `[S-L3] matter++/Readme.txt \u7b2c 12\u30011',
    u'| 1 | 4\u00d715 | 15 | 4 | 60 | `\\s*[+-]?[\\d.]+(?:[EeDd][+-]?\\d+)?` \u914d\u5408\u5217\u5207\u7247 | F1\u3001F3 | `matter++/mat_Al-1.0/AL_eos` \u7b2c 2 \u884c | `[S-L3] matter++/Readme.txt \u7b2c 12\u30011',
    'noop1') if False else None

# --- 2.1 表 T4 第 2 行（4x16 那行） ---
rep(u'| 2 | 4\u00d716 | 16 | 4 | 64 | \u540c\u4e0a\uff0c\u5217\u5bbd 16 | F4 | `matter++/mat_Al-1.0/FEOS/Al.feos.301` \u7b2c 2 \u884c | `[S-L3] matter++/Readme.txt \u7b2c 13 \u884c` |',
    u'| 2 | 4\u00d715 / 4\u00d716 | 15 / 16 | 4 | 60 / 64 | \u6309 15 \u5217\u5207\u7247\uff0c\u82e5\u672b\u6bb5\u6ea2\u51fa\u5219\u5e76\u56de | F4 | `Al.feos.301`\uff0860\uff09\u3001`Au.301`\uff0864\uff09 | `[S-SRC] FE-01_TABTOOLS.C:594` |',
    'ch2-T4row2')

# --- 2.1 表 T4 第 8 行（4x15 前导零式）保持，但补第 9 行列说明不需要 ---

# --- 2.2 / 2.3 附近："Al.feos 走 4x15" ---
rep(u'**\u7b2c\u4e8c\uff0cF3 \u4e0e F4 \u5e38\u88ab\u6df7\u4e3a\u4e00\u8c08\u4f46\u5b57\u8282\u5e03\u5c40\u4e0d\u540c\u3002** `Al.feos` \u8d70 4\u00d715\uff0c`Al.feos.301` \u8d70 4\u00d716\u3002\u4e24\u8005\u5185\u5bb9\u8fd1\u4f3c\uff08\u540e\u8005\u662f\u524d\u8005\u7684 `.301` \u5bfc\u51fa\uff09\uff0c\u4f46**\u884c\u5bbd\u4e0d\u540c**\uff0c\u7528\u540c\u4e00\u4e2a\u5207\u5206\u5668\u4f1a\u5931\u8d25\u3002',
    u'**\u7b2c\u4e8c\uff0cF3 \u4e0e F4 \u5e38\u88ab\u6df7\u4e3a\u4e00\u8c08\u4f46\u5b57\u8282\u5e03\u5c40\u4e0d\u540c\u3002** `Al.feos` \u8d70 **10\u00d715 = 150**\uff0c`Al.feos.301` \u8d70 **4\u00d715 = 60**\u3002\u4e24\u8005\u5185\u5bb9\u8fd1\u4f3c\uff08\u540e\u8005\u662f\u524d\u8005\u7684 `.301` \u5bfc\u51fa\uff09\uff0c\u4f46**\u884c\u5bbd\u5dee 2.5 \u500d**\uff0c\u7528\u540c\u4e00\u4e2a\u5207\u5206\u5668\u4f1a\u5931\u8d25\u3002\uff08\u89c1 10.6.2\u201310.6.3\uff09',
    'ch2-F3F4')

# --- 6.x 陷阱："Al.feos（4x15）与 Al.feos.301（4x16）" ---
rep(u'**`Al.feos`\uff084\u00d715\uff09\u4e0e `Al.feos.301`\uff084\u00d716\uff09\u662f\u540c\u6750\u6599\u540c\u65cf\u7684\u4e24\u4efd\u6587\u4ef6\uff0c\u5b57\u6bb5\u5bbd\u4e0d\u540c\u3002** \u82e5\u89e3\u6790\u5668\u628a `W=15` \u4ece\u4e00\u4efd\u6587\u4ef6\u5ef6\u7eed\u5230\u53e6\u4e00\u4efd\uff0c`.301` \u7684\u6bcf\u884c\u4f1a\u591a\u51fa 4 \u4e2a\u5b57\u7b26\u65e0\u5904\u5b89\u7f6e\uff0c\u5bfc\u81f4\u6700\u540e\u4e00\u5217\u88ab\u4e22\u5f03\u6216\u9519\u4f4d\u3002',
    u'**`Al.feos`\uff0810\u00d715\uff09\u4e0e `Al.feos.301`\uff084\u00d715\uff09\u662f\u540c\u6750\u6599\u540c\u65cf\u7684\u4e24\u4efd\u6587\u4ef6\uff0c\u5b57\u6bb5\u6570\u4e0d\u540c\u3002** \u82e5\u89e3\u6790\u5668\u628a `W=15`\uff084 \u6bb5\uff09\u4ece\u4e00\u4efd\u6587\u4ef6\u5ef6\u7eed\u5230\u53e6\u4e00\u4efd\uff0c`Al.feos` \u7684\u6bcf\u884c\u4f1a\u88ab\u622a\u65ad\u4e3a 4 \u6bb5\u800c\u4e22\u5f03\u540e 6 \u4e2a\u5b57\u6bb5\u3002',
    'ch6-trap')

# --- 10 章导语 ---
rep(u'\u672c\u7ae0\u6db5\u76d6 Multi1D++ \u4e2d**\u552f\u4e00\u4e00\u5957\u540c\u65f6\u4ee5"\u539f\u751f\u683c\u5f0f + SESAME \u517c\u5bb9\u683c\u5f0f"\u53cc\u8f68\u5b58\u5728**\u7684 EOS \u6570\u636e\u65cf\uff1aFEOS \u539f\u751f `.feos`\uff084\u00d715 \u5b9a\u5bbd\uff09\u4e0e MPQeos \u517c\u5bb9 `.301`/`.304`/`.305`\uff084\u00d716 \u5b9a\u5bbd\uff09\u3002',
    u'\u672c\u7ae0\u6db5\u76d6 Multi1D++ \u4e2d**\u552f\u4e00\u4e00\u5957\u540c\u65f6\u4ee5"\u539f\u751f\u683c\u5f0f + SESAME \u517c\u5bb9\u683c\u5f0f"\u53cc\u8f68\u5b58\u5728**\u7684 EOS \u6570\u636e\u65cf\uff1aFEOS \u539f\u751f `.feos`\uff08**10\u00d715 = 150 \u5b9a\u5bbd**\uff09\u4e0e MPQeos \u517c\u5bb9 `.301`/`.304`/`.305`\uff084 \u5b57\u6bb5/\u884c\uff0c**60 \u6216 64 \u4e24\u79cd\u5b9e\u7269**\uff09\u3002',
    'ch10-intro')

# --- 10 章 10.2 标题 + 10.2.1 ---
rep(u'### 10.2 `.301` / `.304` / `.305`\uff1aMPQeos 4\u00d716 \u683c\u5f0f',
    u'### 10.2 `.301` / `.304` / `.305`\uff1aMPQeos 4 \u5b57\u6bb5\u5b9a\u5bbd\uff08\u5bbd\u5ea6 60/64 \u53cc\u5b9e\u7269\uff09\n\n'
    u'> **\u26a0 \u672c\u8282\u7ed3\u8bba\u5df2\u88ab 10.6.3 \u66f4\u6b63**\uff1a\u539f\u6587\u79f0"4\u00d716"**\u53ea\u5bf9\u65e7 MPQeos v2.0 \u4ea7\u7269\u6210\u7acb**\uff1bFEOS 16.7 \u539f\u751f\u8f93\u51fa\u4e3a **4\u00d715 = 60**\u3002\u4e24\u79cd\u5b9e\u7269\u90fd\u5728\u91ce\u5916\u5b58\u5728\uff0c**\u4e0d\u5f97\u5047\u8bbe\u56fa\u5b9a\u5bbd\u5ea6**\u3002',
    'ch10-10.2title')

rep(u'#### 10.2.1 4\u00d716 \u5b9a\u5bbd\u4e0e\u5934\u90e8\u9010\u5b57\u8282',
    u'#### 10.2.1 4 \u5b57\u6bb5\u5b9a\u5bbd\u4e0e\u5934\u90e8\u9010\u5b57\u8282\uff08\u5bbd\u5ea6 60/64 \u5e76\u5b58\uff09',
    'ch10-10.2.1title')

rep(u'**"\u6bcf\u884c 4\u00d716 \u4e2a\u5b57\u7b26"**\uff1a\u6bcf\u884c 4 \u4e2a\u5b57\u6bb5\u3001\u6bcf\u5b57\u6bb5 16 \u5b57\u7b26\uff0c\u603b\u884c\u5bbd 64 \u5b57\u7b26\u3002\u8fd9\u662f\u4e0e SESAME 4\u00d715\u3001FEOS 4\u00d715 **\u90fd\u4e0d\u540c**\u7684\u7b2c\u4e09\u79cd\u5b9a\u5bbd\u3002',
    u'**"\u6bcf\u884c 4 \u4e2a\u5b57\u6bb5"**\uff1a\u6bcf\u884c 4 \u4e2a\u5b57\u6bb5\uff0c\u4f46**\u5b57\u6bb5\u5bbd\u5ea6\u53d6\u51b3\u4e8e\u6307\u6570\u4f4d\u6570**\u2014\u2014`%15.8le`\uff082 \u4f4d\u6307\u6570\uff09\u65f6\u4e3a 15 \u5b57\u7b26\uff08\u603b 60\uff09\uff0c3 \u4f4d\u6307\u6570\uff08\u5982 `e+001`\uff09\u65f6\u4e3a 16 \u5b57\u7b26\uff08\u603b 64\uff09\u3002\u8be6\u89c1 **10.6.3**\u3002',
    'ch10-10.2.1body')

# --- 10.3 标题 ---
rep(u'### 10.3 `.feos` \u539f\u751f 4\u00d715 \u683c\u5f0f',
    u'### 10.3 `.feos` \u539f\u751f 10\u00d715 \u683c\u5f0f\uff08= 150 \u5b57\u7b26/\u884c\uff09\n\n'
    u'> **\u26a0 \u672c\u8282\u7ed3\u8bba\u5df2\u88ab 10.6.2 \u66f4\u6b63**\uff1a\u539f\u6587\u79f0"\u4e00\u884c 4 \u4e2a 15 \u5b57\u7b26"\u662f**\u9519\u8bef**\u7684\u3002\u6b63\u786e\u503c\u662f **10 \u4e2a 15 \u5b57\u7b26 = 150 \u5b57\u7b26/\u884c**\uff0c\u6839\u56e0\u662f `FE-00_DEFINITS.H:28` \u7684 `SF_TRENN=""`\u3002',
    'ch10-10.3title')

rep(u'**"\u4e00\u884c 4 \u4e2a 15 \u5b57\u7b26"**\uff1a4\u00d715 \u5b9a\u5bbd\uff0c\u4e0e SESAME \u540c\u5bbd\u4f46**\u5b57\u6bb5\u5e8f\u5b8c\u5168\u4e0d\u540c**\u3002\u636e FEOS \u8bf4\u660e \u00a73.6.8\uff08`write_FEOS_format()`\uff09`[S-L1]`\uff1a',
    u'**"\u4e00\u884c 10 \u4e2a 15 \u5b57\u7b26 = 150"**\uff1a\u6bcf\u5b57\u6bb5 15 \u5b57\u7b26\u4f46**\u6bcf\u884c 10 \u4e2a\u5b57\u6bb5**\u3002\u5b57\u6bb5\u5bbd\u4e0e SESAME \u76f8\u540c\u4f46**\u5b57\u6bb5\u5e8f\u4e0e\u884c\u5bbd\u5747\u4e0d\u540c**\u3002\u6e90\u7801\u4f9d\u636e `FE-00_DEFINITS.H:28` + `FE-01_TABTOOLS.C` \u5199\u51fa\u5faa\u73af `[S-SRC]`\uff1a',
    'ch10-10.3body')

rep(u'\u5b57\u7b26\u603b\u6570 = 15 \u00d7 \u5b57\u6bb5\u603b\u6570                              (4\u00d715 \u5b9a\u5bbd)',
    u'\u5b57\u7b26\u603b\u6570 = 15 \u00d7 \u5b57\u6bb5\u603b\u6570                              (10\u00d715 \u5b9a\u5bbd\uff0c150/\u884c)',
    'ch10-10.3count')

# --- 10.4 表：Al.feos / .301 ---
rep(u'| `Al.feos` | 3,628,968 | **FEOS \u539f\u751f 4\u00d715** | \u884c 0/\u884c 1 \u5341\u5b57\u6bb5\uff0c\u89c1 10.3.1 |\n'
    u'| `FEOS/Al.feos.301` | 620,139 | MPQeos 4\u00d716\uff0c\u603b\u91cf EOS | `Id = 37170301` |\n'
    u'| `FEOS/Al.feos.304` | 620,139 | MPQeos 4\u00d716\uff0c\u7535\u5b50 EOS | `Id = 37170304`\uff08\u4ee3\u7801\u6e05\u5355\u6807 `Pe/Ee/Fe`\uff09 |\n'
    u'| `FEOS/Al.feos.305` | 620,139 | MPQeos 4\u00d716\uff0c\u79bb\u5b50 EOS | `Id = 37170305`\uff08\u4ee3\u7801\u6e05\u5355\u6807 `Pi/Ei/Fi`\uff09 |',
    u'| `Al.feos` | 3,628,968 | **FEOS \u539f\u751f 10\u00d715 = 150** | \u884c 0/\u884c 1 \u5404 10 \u53c2\u6570\uff0c\u89c1 10.3.1 / 10.6.10 |\n'
    u'| `FEOS/Al.feos.301` | 620,139 | MPQeos **4\u00d715 = 60**\uff0c\u603b\u91cf EOS | `Id = 37170301` |\n'
    u'| `FEOS/Al.feos.304` | 620,139 | MPQeos 4\u00d715 = 60\uff0c**\u7535\u5b50** EOS | `Id = 37170304`\uff08\u6e90\u7801\u5b9a\u540d `write_304_format`\uff09 |\n'
    u'| `FEOS/Al.feos.305` | 620,139 | MPQeos 4\u00d715 = 60\uff0c**\u79bb\u5b50** EOS | `Id = 37170305`\uff08\u6e90\u7801\u5b9a\u540d `write_305_format`\uff09 |',
    'ch10-10.4table')

# --- 10.3.3 结论段（Al.feos 与 .301 无法区分）---
rep(u'**\u8fd9\u662f\u672c\u65cf\u6700\u5371\u9669\u7684\u9677\u9631**\uff1a`matter++/Readme.txt` \u7684\u5206\u6d3e\u89c4\u5219\u8bf4"\u6587\u4ef6\u540d\u542b `.feos` \u2192 \u6309 4\u00d715 \u8bfb\u5165"\uff0c\u800c **4\u00d715 \u6070\u597d\u540c\u65f6\u662f SESAME \u4e0e FEOS \u539f\u751f\u7684\u884c\u5bbd**\uff0c\u6545**\u6309\u884c\u5bbd\u65e0\u6cd5\u533a\u5206**\u3002',
    u'**\u8fd9\u662f\u672c\u65cf\u6700\u5371\u9669\u7684\u9677\u9631**\uff1a`matter++/Readme.txt` \u7684\u5206\u6d3e\u89c4\u5219\u8bf4"\u6587\u4ef6\u540d\u542b `.feos` \u2192 \u6309 4\u00d715 \u8bfb\u5165"\uff0c\u800c **`AL_eos.feos` \u5185\u5bb9\u5b9e\u4e3a SESAME 4\u00d715 = 60**\uff0c\u4e0e FEOS \u539f\u751f\u7684 **10\u00d715 = 150** \u884c\u5bbd\u4e0d\u540c\uff0c\u6545**\u53ef\u6309\u884c\u5bbd\u533a\u5206**\uff08\u4f46\u4ecd\u9700\u5185\u5bb9\u590d\u6838\uff0c\u89c1 10.6.11\uff09\u3002',
    'ch10-10.3.3')

# --- 第9章 hyades 表里 qeos_392 那行 ---
rep(u'| `qeos/qeos_392.dat.feos` | 142,553 | `1.20600000E+01 \u2026` | **FEOS 4\u00d715 \u683c\u5f0f** |',
    u'| `qeos/qeos_392.dat.feos` | 142,553 | `Silicon     LLNL QEOS DATED: 062695` | **\u540d\u4e0d\u526f\u5b9e\uff1a\u5b9e\u4e3a Hyades\uff085\u00d715 = 75\uff09** \u2014\u2014\u89c1 10.6.11 |',
    'ch9-qeos392')

# --- 7.x 表里 qeos_392 若另有 4x15 说法（L6125 已处理）---
d = d.replace('\r\n', '\n')
io.open(P, 'w', encoding='utf-8', newline='\n').write(d)
print('\n'.join(log))
print('chars %d -> %d (%+d)' % (n0, len(d), len(d) - n0))
print('bytes %d' % len(d.encode('utf-8')))
