# -*- coding: utf-8 -*-
"""附录 F 更新（最终版）：F.1 源码源 / F.2 网络核验 / F.3 [S-SRC] / 图 F10 / 图 F12"""
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

# ===== 1) F.1 本地源清单 =====
rep(
u'| `doc/FEOS/Info.txt` + `doc/FEOS/*.pdf` | 2,475 + 4 PDF | FEOS \u8840\u7edf\uff08\u7b2c10\u7ae0\u6e90\uff09 | [S-L1] |',
u'| `doc/FEOS/Info.txt` + `doc/FEOS/*.pdf` | 2,475 + 4 PDF | FEOS \u8840\u7edf\uff08\u7b2c10\u7ae0\u6e90\uff09 | [S-L1] |\n'
u'| `ionmix/ionmix/src/Ionmix/abjt_03.f` | 381,216 | **IONMIX \u683c\u5f0f\u552f\u4e00\u5b9a\u4e49\u6e90**\uff08\u884c 4598\u20134755\uff09 | [S-SRC] |\n'
u'| **`FEOS_package_v16.7`**\uff08\u5b98\u65b9\u53d1\u884c\u5305\uff0cGPLv3\uff09 | \u2014 | **FEOS 16.7 \u683c\u5f0f\u7ec8\u6781\u6743\u5a01** | [S-SRC] |\n'
u'| \u2514 `Code/` | 18 `.C` + 18 `.H` | \u5168\u90e8\u8868\u5199\u51fa\u5668\u6e90\u7801 | [S-SRC] |\n'
u'| \u2514 `Code/FE-00_DEFINITS.H` | 4,316 | \u540e\u7f00\u540d\u5b8f\uff08`SF_TRENN=""`\uff09 | [S-SRC] |\n'
u'| \u2514 `Code/FE-01_TABTOOLS.C` | 32,756 | `.301/.304/.305/.feos/.mexport/.cst/.critical.dat` \u5199\u51fa\u5668 | [S-SRC] |\n'
u'| \u2514 `Code/FE-02_CALCULATIONS.C` | \u2014 | `.isobaric.dat` \u7b49\u6d3e\u751f\u8868 | [S-SRC] |\n'
u'| \u2514 `Code/COMMON-00_DEFINITS.H` | \u2014 | \u5355\u4f4d\u6362\u7b97\u5e38\u91cf\uff08`cgs2ses_*`\uff09 | [S-SRC] |\n'
u'| \u2514 `Code/COMMON-02_READFILE.C` | \u2014 | `.par` \u5206\u533a\u8bfb\u5165 | [S-SRC] |\n'
u'| \u2514 `Code/SE-00_DEFINITS.H` | \u2014 | ShowEOS \u516d\u540e\u7f00\u5b8f | [S-SRC] |\n'
u'| \u2514 `Code/SE-03_SERVICES.C` | 31,550 | ShowEOS \u516d\u79cd\u51fa\u56fe\u670d\u52a1 | [S-SRC] |\n'
u'| \u2514 `Code/SE-04_MAIN.C` | \u2014 | ShowEOS \u4e3b\u63a7\uff08\u9009\u9879 6 \u4e0d\u843d\u76d8\uff09 | [S-SRC] |\n'
u'| \u2514 `Documents/FEOS-Package-Documentation.txt` | 99,338 | \u5b98\u65b9\u6587\u6863 | [S-L1] |\n'
u'| \u2514 `EOS-Data/FEOS_TF-Table_1197.dat` | 567,342 | Thomas-Fermi \u57fa\u5ea7\u8868\uff0893\u00d744\uff09 | [S-SRC] |\n'
u'| `matter++/tabelle/tabelle1197.TFT` | \u2014 | \u4e0e\u4e0a\u8005 **sha256 \u76f8\u540c**\uff08`3d0c638c\u2026`\uff09 | [S-L2] |\n'
u'| `matter++/tabelle/readme.txt` | \u2014 | **\u5b9e\u4e3a C \u6e90\u7801**\uff0c\u7ed9\u51fa TF \u8868\u5217\u5e8f | [S-L2] |',
'F.1-src')

# ===== 2) F.2 整节重写 =====
OLD_F2 = u'### F.2 \u7f51\u7edc\u6838\u9a8c\u6e90\n\n**\u5f85\u6838\u9a8c\u6e05\u5355\uff08\u672c\u6b21\u5199\u4f5c\u672a\u8054\u7f51\u6838\u9a8c\uff0c\u4e00\u5f8b\u6807 `[S-UNK]`\uff0c\u4e0d\u5217\u5177\u4f53 URL\uff09**\uff1a'
i = d.find(OLD_F2)
assert i > 0, 'F.2 head not found'
j = d.find(u'### F.3 \u6eaf\u6e90\u901f\u67e5\u8868', i)
assert j > i, 'F.3 not found'

NEW_F2 = u'''### F.2 网络核验源与官方源码包

**已核验的网络来源**（附 DOI，均可交叉核查）：

**表 T64a　已核验网络来源**

| # | 文献 / 资源 | 标识 | 用途 | 溯源 |
|---|---|---|---|---|
| 1 | S. Faik, A. Tauschwitz, I. Iosilevskiy, *The equation of state package FEOS for high energy density matter* | **CPC 227 (2018) 117\u2013125**，DOI `10.1016/j.cpc.2018.01.008` | **FEOS 官方论文**（第 10 章血统） | [S-WEB] |
| 2 | A. Kemp, J. Meyer-ter-Vehn, *An equation of state code for hot dense matter, based on the QEOS description* | **NIM A 415 (1998) 674\u2013676**，DOI `10.1016/S0168-9002(98)00446-X` | **MPQeos 原始论文**（第 10 章血统） | [S-WEB] |
| 3 | R. Ramis, R. Schmalz, J. Meyer-ter-Vehn, *MULTI \u2014 A computer code for one-dimensional multigroup radiation hydrodynamics* | **CPC 49 (1988) 475**，DOI `10.1016/0010-4655(88)90008-2` | MULTI 血统（第 8 章） | [S-WEB] |
| 4 | R. M. More, K. H. Warren, D. A. Young, G. B. Zimmerman, *A new quotidian equation of state (QEOS) for hot dense matter* | **Phys. Fluids 31 (1988) 3059**，DOI `10.1063/1.866963` | QEOS 原始论文（第 10、11 章） | [S-WEB] |
| 5 | FLASH 4.8 User's Guide \u00a723.5.6（IONMIX4 格式章） | 官方手册 | **IONMIX 24 段官方 FORMAT 语句号** | [S-WEB] |
| 6 | FEOS 官方源码包 `FEOS_package_v16.7`（GPLv3） | `Code/` 18 `.C` + 18 `.H` | **格式终极权威**（10.6 全节源） | [S-SRC] |

**关键裁决（本轮网络-本地冲突）**：

1. **`.feos` 的字段宽度**：`matter++/Readme.txt:12` 说"一行 4 个 15 字符"，而 **FEOS 16.7 官方源码 `FE-00_DEFINITS.H:28` 的 `SF_TRENN=""` + 实测 23,874 行全 150 字符**证明正确值是 **10\u00d715 = 150**。**裁决：源码 > 本地非权威说明文本**（二者都是本地物，但源码是一手程序定义）。见 10.6.2。

2. **`.301/.304/.305` 的 4\u00d715 vs 4\u00d716**：官方 FEOS 16.7 源码给出 **4\u00d715（`%15.8le`）**，而本地旧产物 `Au.301` 实测 **4\u00d716**。**二者不冲突**\u2014\u2014是两代工具链（FEOS 16.7 vs 旧 MPQeos v2.0）的两个实物。见 10.6.3。

**仍待核验清单**（保持 `[S-UNK]`，不编造 URL）：

**表 T64b　仍待核验项清单**

| # | 待核验项 | 用途 | 状态 |
|---|---|---|---|
| 1 | K. Eidmann, Laser and Particle Beams 12(2), 223\u2013244 (1994) | SNOP 物理出处 | [S-UNK] 未联网核验 |
| 2 | Tsakiris & Eidmann, 1987JQSRT38 | Ba/Sn/Eu 幂律来源 | [S-UNK] 未联网核验 |
| 3 | Hammer & Rosen, 2003POP | Au 幂律来源 | [S-UNK] 未联网核验 |
| 4 | Fusion Engineering and Design 60 (2002) 17\u201325 | 型 B 幂律来源 | [S-UNK] 未联网核验 |
| 5 | M. Murakami, J. Meyer-ter-Vehn, R. Ramis, J. X-Ray Sci. Tech. 2, 127\u2013148 (1990) | Al 幂律来源 | [S-UNK] 未联网核验 |
| 6 | NIST X-Ray Mass Attenuation Coefficients Table 1 | `density.dat` 来源 | [S-UNK] 未联网核验（URL 见文件注释） |
| 7 | Post 1977ADNDT20.397 | 辐射冷却率 | [S-UNK] 未联网核验 |
| 8 | Coppola 2011MNRAS415 | 冷却函数（H/D/He/Li） | [S-UNK] 未联网核验 |
| 9 | 2000PRE62_1_145 | 反射率/碰撞频率 | [S-UNK] 未联网核验 |
| 10 | WorkOp-III:94 | Au 自由程 | [S-UNK] 未联网核验 |
| 11 | Zeldovich & Raizer (1966) p.260 式 5.23/5.24 | H/Be 自由程 | [S-UNK] 未联网核验 |
| 12 | Lindl 1995 eqn 135 | Au 反照率 | [S-UNK] 未联网核验 |
| 13 | G. Mishra, 2018HEDP | Al/W/Au/Pb/U 反照率 | [S-UNK] 未联网核验 |
| 14 | Jiang Shaoen et al., 物理学报 53 (2004) | Au 反照率 | [S-UNK] 未联网核验 |
| 15 | `*4gnuplot` 转写脚本的作者与来源 | 10.6.6 的外部后处理归属 | [S-UNK] 无一手依据 |

**核验纪律（重申）**：网络内容仅用于书目信息与本地缺失的编码约定补白；任何网络结论须独立标注 `[S-WEB]` 并附 URL + 访问日期；**与本地冲突时以本地为准**并显式记录差异。**本轮已对 FEOS / MPQeos / MULTI / QEOS 四条血统完成 DOI 级核验**（表 T64a 第 1\u20134 行）；**仍待核验的 15 项保持 `[S-UNK]`，不编造 URL**。

'''
d = d[:i] + NEW_F2 + d[j:]
log.append('F.2 rewrite (%+d)' % (len(NEW_F2) - (j - i)))

# ===== 3) F.3 溯源表 =====
rep(
u'| `[S-WEB]` | \u7f51\u7edc\u6838\u9a8c\uff08\u987b URL+\u65e5\u671f\uff09 | \uff08\u672c\u6b21\u672a\u4f7f\u7528\uff09 |',
u'| `[S-SRC]` | **\u7a0b\u5e8f\u6e90\u7801\u660e\u6587**\uff08\u4e00\u624b\u7a0b\u5e8f\u5b9a\u4e49\uff09 | `[S-SRC] FE-00_DEFINITS.H:28 SF_TRENN=""` |\n'
u'| `[S-WEB]` | \u7f51\u7edc\u6838\u9a8c\uff08\u987b URL+\u65e5\u671f\uff09 | `[S-WEB] DOI 10.1016/j.cpc.2018.01.008` |\n'
u'| `[S-IMG]` | \u7eaf\u56fe\u7247\u9875\uff08\u65e0\u53ef\u62bd\u53d6\u6587\u672c\uff09 | \u90e8\u5206 PDF \u63d2\u56fe |',
'F.3')

# ===== 4) 图 F10 =====
rep(
u'  .feos         : \u8868\u5934 10 \u6570\uff0cpayload \u5217\u5e8f\u672a\u77e5 [S-UNK]',
u'  .feos         : \u884c\u5bbd 10\u00d715=150\uff1b\u884c 0/1 \u5404 10 \u53c2\u6570\uff1bj(\u6e29\u5ea6)\u5916\u5c42 i(\u5bc6\u5ea6)\u5185\u5c42',
'F10')

# ===== 5) 图 F12（行内精确替换，逐行操作避开对齐空格数陷阱） =====
L12 = d.split('\n')
hit = None
for k, ln in enumerate(L12):
    if ln.strip().startswith(u'\u251c\u2500 \u6587\u4ef6\u540d\u542b ".feos" ?'):
        hit = k; break
assert hit is not None, 'F12 feos line not found'
assert u'payload \u5217\u5e8f [S-UNK]' in L12[hit+1], repr(L12[hit+1])
# 保留原缩进量
pad = L12[hit][:len(L12[hit]) - len(L12[hit].lstrip())]
pad1 = L12[hit+1][:len(L12[hit+1]) - len(L12[hit+1].lstrip())]
L12[hit] = pad + u'\u251c\u2500 \u6587\u4ef6\u540d\u542b ".feos" ? \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u662f\u2500\u2500> FEOS \u539f\u751f 10\u00d715=150 (\u884c0/1 \u5404 10 \u53c2\u6570)'
L12[hit+1] = pad1 + u'\u26a0 \u5148\u5185\u5bb9\u590d\u6838\uff1a\u884c\u5bbd 75 \u6216\u9996\u884c\u975e\u6570\u503c \u2192 \u975e FEOS'
# 301 行
for k2 in range(hit, hit+8):
    if L12[k2].strip().startswith(u'\u251c\u2500 \u6587\u4ef6\u540d\u542b ".301/.304/.305" ?'):
        p2 = L12[k2][:len(L12[k2]) - len(L12[k2].lstrip())]
        L12[k2] = p2 + u'\u251c\u2500 \u6587\u4ef6\u540d\u542b ".301/.304/.305" ? \u2500\u662f\u2500> MPQeos 4\u00d715(60) / 4\u00d716(64)'
        break
else:
    raise AssertionError('301 line not found near F12')
d = '\n'.join(L12)
log.append('F12 ok')

d = d.replace('\r\n', '\n')
io.open(P, 'w', encoding='utf-8', newline='\n').write(d)
print('\n'.join(log))
print('chars %d -> %d (%+d)' % (n0, len(d), len(d) - n0))
print('bytes %d' % len(d.encode('utf-8')))
