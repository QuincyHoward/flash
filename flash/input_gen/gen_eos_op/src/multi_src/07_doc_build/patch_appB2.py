# -*- coding: utf-8 -*-
"""新增附录 B.16-B.19 卡（FEOS 源码级解出的 4 个格式）；更新附录 F 书目。"""
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
    log.append('%s ok (+%d)' % (name, len(new) - len(old)))

# ---------- 在 B.15 末尾（"---" 之后紧跟 "## 附录 C"）插入 B.16~B.19 ----------
TARGET = u'| \u9677\u9631 | `Albedo.xml` Type=0/1/2 \u4e09\u516c\u5f0f\u4e14 Au \u91cd\u590d 5 \u6761\uff1b`density.dat` Z=85/87 \u5bc6\u5ea6\u4eba\u4e3a\u8bbe 10 |\n\n---\n\n## \u9644\u5f55 C \u5b9e\u6d4b\u6837\u672c\u7d22\u5f15'

NEW = u'''| \u9677\u9631 | `Albedo.xml` Type=0/1/2 \u4e09\u516c\u5f0f\u4e14 Au \u91cd\u590d 5 \u6761\uff1b`density.dat` Z=85/87 \u5bc6\u5ea6\u4eba\u4e3a\u8bbe 10 |

### B.16 FEOS `.mexport`\uff08SESAME mexport ASCII\uff09

**\u8868 T59b\u3000`.mexport` \u901f\u67e5\u5361\uff08B.16\uff09**

| \u9879 | \u5185\u5bb9 |
|---|---|
| \u89e6\u53d1 | \u6269\u5c55\u540d `.mexport` |
| \u884c\u5bbd | **\u4e25\u683c 80 \u5b57\u7b26 = 5 \u6570\u503c\u5b57\u6bb5\u00d715 + 5 \u63a7\u5236\u4f4d** |
| \u8868\u5934 | \u6bb5\u5934 `0  MID  101  160  r  ...` / `1  MID  301 40007  r  ...` |
| \u5b57\u6bb5 | \u8bb0\u5f55 **101 / 102 / 201 / 301 / 304 / 305**\uff08**\u5355\u6750\u6599**\uff09 |
| \u5355\u4f4d | \u8ddf\u968f SESAME\uff08GPa / MJ\u00b7kg\u207b\u00b9 / Mg\u00b7m\u207b\u00b3 / K\uff09 |
| \u8ba1\u6570 | \u6bb5 301 \u884c\u6570 = `2+(NR+1)+(NT+1)+3\u00b7(NR+1)\u00b7(NT+1)` |
| \u6837\u672c | `matter++/mat_B/B.mexport`\uff081,845,656 B / 22,508 \u884c**\u5168 80 \u5b57\u7b26**\uff09 |
| \u9677\u9631 | **\u5fc5\u987b\u5207\u6389 `line[75:80]`**\uff0c\u5426\u5219\u672b\u4f4d\u4e0e\u63a9\u7801\u7c98\u8fde\uff08`0.00000000e+0011100`\uff09\uff1b\u9694\u6bb5 201 \u7684 `Bulkmat/1e10` \u662f **GPa \u91cf\u7eb2** |

### B.17 FEOS `.cst`\uff08Rostock \u683c\u5f0f\uff09

**\u8868 T59c\u3000`.cst` \u901f\u67e5\u5361\uff08B.17\uff09**

| \u9879 | \u5185\u5bb9 |
|---|---|
| \u89e6\u53d1 | \u6269\u5c55\u540d `.cst` |
| \u884c\u5bbd | 4 \u5217**\u7a7a\u683c\u5206\u9694**\uff08\u975e\u5b9a\u5bbd\uff09 |
| \u8868\u5934 | \u7b2c 1 \u884c `Isotherme T = 0 Kelvin`\uff1b\u5217\u540d\u884c\u4e3a**\u5fb7\u8bed** |
| \u5b57\u6bb5 | \u5217 1 `Molek\u00fcldichte[1/cm^3]`\uff1b\u5217 2 `Massendichte[g/cm^3]`\uff1b\u5217 3 `Druck[MBar]`\uff1b\u5217 4 `Ladungszustand` |
| \u5355\u4f4d | **1/cm\u00b3 / g\u00b7cm\u207b\u00b3 / MBar / \u65e0\u91cf\u7eb2** |
| \u8ba1\u6570 | \u5217\u6570\u6052 4 |
| \u6837\u672c | `matter++/mat_O/O.cst`\uff08929,594 B\uff09\uff1b\u5171 24 \u4e2a |
| \u9677\u9631 | **\u5fc5\u987b\u6309 UTF-8 \u89e3\u7801**\uff08\u5fb7\u6587 `\u00fc`\uff09\uff1b24 \u4e2a\u4e2d 23 \u4e2a\u542b >127 \u5b57\u8282\uff1b**\u5168\u5e93\u552f\u4e00\u540c\u65f6\u7ed9\u6570\u5bc6\u5ea6\u4e0e\u8d28\u91cf\u5bc6\u5ea6\u7684\u6587\u4ef6** |

### B.18 FEOS `.critical.dat` / `.isobaric.dat`

**\u8868 T59d\u3000`.critical.dat` / `.isobaric.dat` \u901f\u67e5\u5361\uff08B.18\uff09**

| \u9879 | `.critical.dat` | `.isobaric.dat` |
|---|---|---|
| \u89e6\u53d1 | \u6269\u5c55\u540d `.critical.dat` | \u6269\u5c55\u540d `.isobaric.dat` |
| \u751f\u6210\u5668 | `write_criticaldata`\uff08`FE-01_TABTOOLS.C:58`\uff09 | `write_isobaricdata`\uff08`FE-02_CALCULATIONS.C:181`\uff09 |
| \u7ed3\u6784 | **14 \u4e2a\u5206\u6bb5**\uff08\u4e34\u754c\u70b9/\u6cb8\u70b9/\u53cc\u7ed3\u70b9/\u65cb\u8282\u7ebf/\u76f4\u5f84\u7ebf/\u84b8\u53d1\u7113/Arrhenius/\u538b\u7f29\u56e0\u5b50/\u4e34\u754c\u6307\u6570/\u2026\uff09 | \u9996\u6bb5 6 \u5217\uff1b**\u7f51\u683c\u786c\u7f16\u7801 21 \u70b9\u3001Tmax\u22486000 K** |
| \u5217\u5e8f | \u6bb5\u95f4\u4ee5 `#` \u6ce8\u91ca\u884c\u5206\u9694 | `T[K] / \u03c1[g/cm\u00b3] / P[bar] / \u03b1[1/K] / H[J/g] / Cp[J/(g\u00b7K)]` |
| \u5355\u4f4d | K / bar / kJ\u00b7g\u207b\u00b9\uff08\u89c1\u9996\u884c\u6ce8\u91ca\uff09 | **P \u7528 bar**\uff08\u672c\u65cf\u7b2c\u4e09\u79cd\u538b\u5f3a\u5355\u4f4d\uff01\uff09 |
| \u6837\u672c | `mat_B/B.critical.dat`\uff0854,692 B\uff09 | `mat_B/B.isobaric.dat`\uff082,657 B\uff09 |
| \u9677\u9631 | \u6ce8\u91ca\u884c\u662f\u4e3b\u8981\u8bfb\u53d6\u5165\u53e3\uff1b\u6570\u503c\u6bb5\u6309 14 \u6bb5\u56fa\u5b9a\u987a\u5e8f | **`P` \u7684 bar \u4e0e `.feos` \u7684 Mbar \u76f8\u5dee 1e6 \u500d** |

### B.19 ShowEOS \u884d\u751f\u4e0e `4gnuplot`

**\u8868 T59e\u3000ShowEOS \u884d\u751f\u6587\u4ef6\u901f\u67e5\u5361\uff08B.19\uff09**

| \u540e\u7f00 | \u9009\u9879 | \u751f\u6210\u5668\uff08`SE-03_SERVICES.C`\uff09 | \u8bf4\u660e |
|---|---|---|---|
| `.ist` | 1 | `:306` | \u7b49\u6e29\u7ebf |
| `.isc` | 2 | `:382` | \u7b49\u5bc6\u5ea6\u7ebf\uff08**\u6ce8\u610f\u662f `isc` \u4e0d\u662f `iso`**\uff09 |
| `.ise` | 3 | `:458` | \u7b49\u71b5\u7ebf |
| `.mnt` | 4 | `:564` | Mountain \u56fe |
| `.hug` | 5 | `:649` | \u96e8\u8d21\u7ebd\uff086 \u5217\uff1a`Rho/T/P/E/Us/Up`\uff09 |
| \u2014 | 6 | `SE-04_MAIN.C:98-106` | **\u5355\u70b9\uff1a\u4ec5\u6253\u5370\u5230 stdout\uff0c\u4e0d\u843d\u76d8** |

- **`*4gnuplot`**\uff1a\u5728 FEOS \u5168\u90e8 36 \u4e2a\u6e90\u7801\u6587\u4ef6\u4e0e 99,338 B \u5b98\u65b9\u6587\u6863\u4e2d **0 \u547d\u4e2d** \u21d2 **\u975e FEOS \u539f\u751f\u4ea7\u7269**\uff0c\u5c5e\u7528\u6237\u540e\u5904\u7406\u3002\u5b9e\u6d4b `.ist4gnuplot` = `.ist` \u7684\u8f6c\u7f6e\uff08T \u63d0\u4e3a\u7b2c 1 \u5217\u3001TAB \u5206\u9694\u3001`&`\u2192\u7a7a\u884c\uff09\u3002**\u8bfb\u53d6\u65f6\u5f52\u5165 `.ist` \u65cf**\u3002
- **`.hug` \u547d\u540d\u89c4\u5219 = \u6bcd\u8868\u540d + `.hug`**\uff08\u975e\u7edf\u4e00\u6750\u6599\u540d\uff09\u3002\u6bcd\u8868\u4e3a FEOS \u8868\u5219\u5f97 `Al.feos.hug`\uff0c\u6bcd\u8868\u4e3a SESAME \u8868\u5219\u5f97 `AL_eos.hug`\u3002
- **\u7a7a\u8868\uff08`AU_eos.hug` 81 B\uff09\u7684\u539f\u56e0**\uff1a\u96e8\u8d21\u7ebd\u641c\u7d22\u8303\u56f4\u53d7**\u8868\u9650**\u7ea6\u675f\uff0c\u5f53\u8bf7\u6c42\u7684 `T`/`P` \u8303\u56f4\u5b8c\u5168\u843d\u5728\u8868\u9650\u5916\u65f6**\u65e0\u89e3\u4f46\u6b63\u5e38\u9000\u51fa**\uff0c\u53ea\u5199\u51fa\u6ce8\u91ca\u884c\u3002**\u4e0d\u662f\u5199\u5165\u622a\u65ad**\u3002
- **Us/Up \u516c\u5f0f**\uff1a`Us = (1/R0)\u00b7\u221a((P-P0)/(1/R0-1/R))`\uff1b`Up = |1-R0/R|\u00b7Us`\u3002

### B.20 `.sesame` \u4e0e\u5176\u53d8\u4f53\uff08`.sesame_` / `.sesame_PLANCK` / `.sesame_ROSSELAND`\uff09

**\u8868 T59f\u3000`.sesame` \u53d8\u4f53\u901f\u67e5\u5361\uff08B.20\uff09**

| \u540e\u7f00 | \u5b9e\u8d28 | \u5224\u636e |
|---|---|---|
| `.sesame` / `.SESAME` | \u539f\u751f\uff08\u8bb0\u5f55\u5e8f `\u8868\u5934/r/de/e0/P/T`\uff09 | 6 \u6bb5\u7ed3\u6784\uff0c\u5c3a\u5bf8\u516c\u5f0f\u95ed\u5408 |
| `.sesame_`\uff08\u672b\u5c3e\u4e0b\u5212\u7ebf\uff09 | **\u53e6\u4e00\u4e2a\u7f51\u683c\u7248\u672c**\uff0c\u975e\u91cd\u547d\u540d | `Ta2O5`: 2,217 B\uff08n\u03c1=3/ne=19\uff09vs 4,650 B\uff08n\u03c1=5/ne=26\uff09 |
| `.sesame_PLANCK` | **= `.PLANCK`**\uff0c\u8868\u53f7\u5b57\u6bb5\u88ab\u54e8\u5175\u5360\u636e | \u9996\u884c ` 0.1234567E+000PLANCK 1  ...`\uff08**\u65e0\u7a7a\u683c\u7c98\u8fde**\uff09 |
| `.sesame_ROSSELAND` | **= `.ROSS`** | \u540c\u4e0a\uff08`ROSSELAND` \u66ff\u4ee3\uff09 |

- **\u54e8\u5175\u4fee\u590d\u5fc5\u987b\u5148\u6309\u56fa\u5b9a\u957f\u5ea6\u5265\u9664**\uff0c**\u4e0d\u53ef\u7528 `\\s` \u6b63\u5219**\uff08\u56e0\u4e3a\u54e8\u5175\u4e0e\u7c7b\u522b\u540d\u4e4b\u95f4\u6ca1\u6709\u7a7a\u683c\uff09\uff1a
  ```python
  # C4\uff1a\u4fee\u590d\u88ab\u5360\u4f4d\u7b26\u6c61\u67d3\u7684 SESAME \u98ce\u683c\u8868\u5934
  line = raw_line.decode('ascii')
  assert line.startswith(' 0.1234567E+000')
  sentinel = line[:14]                       # '\u7a7a\u683c + 0.1234567E+000'
  rest     = line[14:]                       # 'PLANCK 1        3.1000000e+001 ...'
  kind, mode = rest[:6].strip(), int(rest[6:8])
  ```
- **\u8ba1\u6570\u95ed\u5408**\uff1a`opc_1022.sesame_PLANCK` = `4 + 3 + 375\u00d74 = 1503` \u2713\u3002
- **\u8ddf `.PLANCK`/`.ROSS` \u5b8c\u5168\u540c\u5c5e\u4e00\u65cf**\uff0c\u53ea\u662f\u5c11\u4e86\u4e00\u4e2a\u7a7a\u683c\u3002

### B.21 \u4e0d\u540c\u540e\u7f00\u540d\u3001\u540c\u4e00\u5185\u5bb9\uff1a\u540d\u5b9e\u4e0d\u7b26\u6e05\u5355

**\u8868 T59g\u3000\u540d\u5b9e\u4e0d\u7b26\u7684 `.feos` \u6e05\u5355\uff08B.21\uff09**

| \u6587\u4ef6 | \u5b9e\u9645\u884c\u5bbd | \u5b9e\u9645\u683c\u5f0f | \u5224\u636e |
|---|---|---|---|
| `mat_Al-1.0/AL_eos.feos`\uff08152,165 B\uff09 | 60 | **SESAME** | \u9996\u884c `     37181000    .27000000E+01  ...` |
| `mat_Al-1.0/FEOS/*.301`\uff08\u65e7\uff09 | 64 | MPQeos v2.0 | 3 \u4f4d\u6307\u6570 |
| `hyades/qeos/qeos_392.dat.feos`\uff08142,553 B\uff09 | **75 = 5\u00d715** | **Hyades** | \u9996\u884c `Silicon     LLNL QEOS DATED: 062695` |
| `hyades/sesame/eos_41.dat.feos`\uff0830,993 B\uff09 | **75 = 5\u00d715** | **Hyades** | \u9996\u884c `ALUMINUM    LANL SESAME #3711 DATED: 22581 11483` |

**\u5de5\u7a0b\u7ed3\u8bba**\uff1a**\u6269\u5c55\u540d\u7ed9\u51fa"\u5019\u9009\u65cf"\uff0c\u5185\u5bb9\u7ed9\u51fa"\u6700\u7ec8\u88c1\u51b3"**\u3002\u5206\u6d3e\u524d\u5fc5\u987b\u505a\u5185\u5bb9\u4fa7\u590d\u6838\uff08\u89c1 10.6.11 \u7684 C7 \u4f2a\u7801\uff09\u3002\u4e8c\u8005\u51b2\u7a81\u65f6**\u5185\u5bb9\u4f18\u5148**\uff0c\u4e14**\u5fc5\u987b\u7ed9\u51fa\u663e\u5f0f\u544a\u8b66**\u3002

---

## \u9644\u5f55 C \u5b9e\u6d4b\u6837\u672c\u7d22\u5f15'''

rep(TARGET, NEW, 'B.16-B.21')

d = d.replace('\r\n', '\n')
io.open(P, 'w', encoding='utf-8', newline='\n').write(d)
print('\n'.join(log))
print('chars %d -> %d (+%d)' % (n0, len(d), len(d) - n0))
print('bytes %d' % len(d.encode('utf-8')))
