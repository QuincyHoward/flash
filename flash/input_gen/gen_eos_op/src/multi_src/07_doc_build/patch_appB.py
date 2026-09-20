# -*- coding: utf-8 -*-
"""附录 B 速查卡更新：B.1(.sesame 记录序) / B.3(.feos 10x15) / B.4(.301 双实物)
   并把第 15 章加入前置-2.2 导航图。锚点均为精确唯一子串。"""
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

# ---------- 前置-2.2 导航图：加第 15 章 ----------
rep(
u'\u2502     \u7b2c14\u7ae0  \u8f85\u52a9\u4e0e\u8fb9\u7f18\u683c\u5f0f\n\u2502\n\u2514\u2500\u2500 \u9644\u5f55      \u5355\u4f4d\u6362\u7b97\u603b\u8868 \u00b7 \u683c\u5f0f\u901f\u67e5\u5361 \u00b7 \u5b9e\u6d4b\u6837\u672c\u7d22\u5f15 \u00b7 \u7f3a\u53e3\u6e05\u5355 \u00b7 \u4e66\u76ee',
u'\u2502     \u7b2c14\u7ae0  \u8f85\u52a9\u4e0e\u8fb9\u7f18\u683c\u5f0f\n'
u'\u2502     \u7b2c15\u7ae0  \u4ecd\u672a\u5b8c\u5168\u89e3\u6790\u7684\u683c\u5f0f\uff1a\u9010\u9879\u5904\u7f6e\u4e0e\u89e3\u8bfb\u8fb9\u754c\n'
u'\u2502\n\u2514\u2500\u2500 \u9644\u5f55      \u5355\u4f4d\u6362\u7b97\u603b\u8868 \u00b7 \u683c\u5f0f\u901f\u67e5\u5361 \u00b7 \u5b9e\u6d4b\u6837\u672c\u7d22\u5f15 \u00b7 \u7f3a\u53e3\u6e05\u5355 \u00b7 \u4e66\u76ee',
'nav15')

# ---------- B.1 ----------
rep(
u'| \u8868\u5934 | \u884c 1\uff1a`table_id rho0 nr ne`\uff084 \u5b57\u6bb5\uff0c\u6bcf\u5b57\u6bb5 15 \u5b57\u7b26\uff09 |\n| \u5b57\u6bb5 | rho(nr)\u3001de(ne)\u3001e0(nr)\u3001P(nr\u00b7ne)\u3001T(nr\u00b7ne) |\n| \u5355\u4f4d | rho g/cm3\u3001de/e0/P Mbar \u7cfb\u3001T K\uff08\u8f6c eV\uff09 |\n| \u8ba1\u6570 | `4 + 2nr + ne + 2nr\u00b7ne`\uff08with_e0\uff09/ `4+nr+ne+2nr\u00b7ne`\uff08no_e0\uff09 |\n| \u6837\u672c | `matter++/mat_Al-1.0/AL_SIMPLE_PLANCK`\uff08183 B\uff09\u3001`AL_eos`\uff08152,165 B\uff09 |\n| \u9677\u9631 | EOS \u7ebf\u6027\u5750\u6807\u800c OPAC \u5bf9\u6570\u5750\u6807\uff1b\u4e24\u79cd payload \u5e03\u5c40\u987b\u9760\u8ba1\u6570\u53cd\u89e3 |',
u'| \u8868\u5934 | \u884c 1\uff1a`table_id mode nr ne`\uff084 \u5b57\u6bb5\uff0c\u6bcf\u5b57\u6bb5 15 \u5b57\u7b26\uff09 |\n'
u'| **\u8bb0\u5f55\u5e8f** | **`\u8868\u5934(4) | r[nr] | de[ne] | e0[nr] | P[ne\u00b7nr] | T[ne\u00b7nr]`** |\n'
u'| \u5b57\u6bb5 | `r[nr]` \u5bc6\u5ea6\u7f51\u683c g/cc\uff1b`de[ne]` \u80fd\u91cf**\u589e\u91cf**\u7f51\u683c Mbar\u00b7cm3/g\uff1b`e0[nr]` **\u51b7\u80fd\u91cf** Mbar\u00b7cm3/g\uff1b`P`/`T` \u5747 [ne][nr] |\n'
u'| \u5355\u4f4d | rho g/cm3\u3001de/e0/P Mbar \u7cfb\u3001**T \u5f00\u5c14\u6587**\uff08\u8f6c eV \u9664 11604.519\uff09 |\n'
u'| \u8ba1\u6570 | **`4 + 2\u00b7nr + ne + 2\u00b7nr\u00b7ne`**\uff08\u672c\u7248\u5df2\u7edf\u4e00\u53e3\u5f84\uff0c**7/7 \u6837\u672c\u95ed\u5408**\uff09 |\n'
u'| \u6392\u5217 | **\u5916\u5c42 ne\u3001\u5185\u5c42 nr\uff08\u5bc6\u5ea6\u53d8\u5316\u6700\u5feb\uff09** |\n'
u'| \u6837\u672c | `matter++/Ta2O5/PowerLawTa2O5_EOS.SESAME`\uff08143\uff09\u3001`matter++/SiO2/eos_21.sesame`\uff08153,645\uff09 |\n'
u'| \u9677\u9631 | EOS \u7ebf\u6027\u5750\u6807\u800c OPAC \u5bf9\u6570\u5750\u6807\uff1b**\u4e0d\u5f97\u7528\u5f62\u6001\u5b66\u53cd\u63a8\u8bb0\u5f55\u5e8f**\uff08\u89c4\u7ea6 R15\uff09 |',
'B.1')

# ---------- B.3 ----------
rep(
u'| \u8868\u5934 | \u884c 0 \u5341\u5b57\u6bb5 `[Z,NR,NT,c1,c2,c3,rho0,T_ref_eV,B0,SESAME#]` |\n'
u'| \u5b57\u6bb5 | rho \u7f51\u683c\u3001T \u7f51\u683c\u3001payload\uff08**\u5217\u5e8f\u672a\u5b9a**\uff09 |\n'
u'| \u5355\u4f4d | rho g/cm3\u3001T_ref eV\u3001\u672a\u77e5 payload \u5355\u4f4d |\n'
u'| \u8ba1\u6570 | \u884c 0 \u56fa\u5b9a 10 \u6570\uff1b\u7f51\u683c\u7528\u5355\u8c03\u6027\u88c1\u526a\uff08NR \u5b9e\u6d4b\u591a 1 \u4e2a 0.0 \u54e8\u5175\uff09 |\n'
u'| \u6837\u672c | `matter++/mat_Al-1.0/Al.feos`\uff083,628,968 B\uff09 |\n'
u'| \u9677\u9631 | payload \u5217\u5e8f**\u65e0\u6cd5\u4ece PDF \u8fd8\u539f** `[S-UNK]`\uff1b\u540d\u5b9e\u4e0d\u7b26\uff08`AL_eos.feos` \u5b9e\u4e3a SESAME\uff09 |',
u'| \u884c\u5bbd | **10 \u5b57\u6bb5 \u00d7 15 \u5b57\u7b26 = 150 \u5b57\u7b26/\u884c**\uff08`SF_TRENN=""` \u2192 \u65e0\u5206\u9694\u7b26\uff09 |\n'
u'| \u8868\u5934 | \u884c 0\uff08\u53c2\u6570\uff09`[FileVersion, NRho, NTemp, Nelem+1, TcalcLim, RhocalcLim, RhoRef, TRef, B0_cgs, SESAME#]` |\n'
u'| \u884c 1\uff08\u53c2\u6570\uff09 | `[ElectronOffset, IonOffset, Ecoh, ssm_n, ssm_m, ssm_A, ssm_B, Atot, Ztot, Xtot]` |\n'
u'| \u5b57\u6bb5 | payload \u5217\u5e8f **j\uff08\u6e29\u5ea6\uff09\u5916\u5c42\u3001i\uff08\u5bc6\u5ea6\uff09\u5185\u5c42**\uff08\u6e90\u7801\u7ea7\u786e\u5b9a\uff09 |\n'
u'| \u5355\u4f4d | rho g/cm3\u3001T eV\u3001B0 **cgs**\uff08dyne/cm2\uff09 |\n'
u'| \u8ba1\u6570 | 20 + 3(Nel+1) + (NRho) + (NTemp) + (18+Nel)\u00b7NRho\u00b7NTemp\uff1b**Al \u4e0a\u7cbe\u786e\u95ed\u5408** |\n'
u'| \u6837\u672c | `matter++/mat_Al-1.0/Al.feos`\uff083,628,968 B / 23,874 \u884c\u5168 150 \u5b57\u7b26\uff09 |\n'
u'| \u9677\u9631 | **`Readme.txt` \u7684"4\u00d715"\u662f\u9519\u7684**\uff1b\u540d\u5b9e\u4e0d\u7b26\uff08`AL_eos.feos` \u5b9e\u4e3a SESAME\uff0c`hyades/*.dat.feos` \u5b9e\u4e3a Hyades\uff0c\u884c\u5bbd 75=5\u00d715\uff09 |',
'B.3')

# ---------- B.4 ----------
rep(
u'| \u8868\u5934 | \u884c 1 `Id Density NR NT`\uff08**\u6bcf\u884c 4\u00d716 \u5b57\u7b26**\uff1bID \u5bbd 16/17 \u4e0d\u5b9a\uff0c\u987b\u7528\u7a7a\u683c\u6b63\u5219\uff09 |\n'
u'| \u5b57\u6bb5 | `[R(nr)][T(nt)][P][E][Z]` |\n'
u'| \u5355\u4f4d | R g/cm3\u3001T K\u3001P GPa\u3001E MJ/kg\u3001Z \u65e0\u91cf\u7eb2 |\n'
u'| \u8ba1\u6570 | `4 + nr + nt + 3\u00b7nr\u00b7nt` |\n'
u'| \u6837\u672c | `matter++/mat_Al-1.0/FEOS/Al.feos.301`\uff08620,139 B\uff09 |\n'
u'| \u9677\u9631 | 4\u00d716 \u800c\u975e 4\u00d715\uff1bZ \u6bb5\u5b9e\u6d4b\u542b\u8d1f\u503c\uff08\u8bed\u4e49\u5f85\u6838\uff09\uff1bT Kelvin \u987b\u8f6c eV |',
u'| \u884c\u5bbd | **4 \u5b57\u6bb5/\u884c**\uff0c\u4f46**\u5bbd\u5ea6\u6709\u4e24\u79cd\u5b9e\u7269**\uff1a4\u00d715=60\uff08FEOS 16.7 \u539f\u751f\uff0c`%15.8le` 2 \u4f4d\u6307\u6570\uff09/ 4\u00d716=64\uff08\u65e7 MPQeos v2.0\uff0c3 \u4f4d\u6307\u6570\uff09 |\n'
u'| \u8868\u5934 | \u884c 1 `Id Density NR NT`\uff08ID \u5bbd 16/17 \u4e0d\u5b9a\uff0c\u987b\u7528\u7a7a\u683c\u6b63\u5219\uff09 |\n'
u'| \u5b57\u6bb5 | `[R(nr)][T(nt)][P][E][Z]`\uff1b304=\u7535\u5b50\u3001**305=\u79bb\u5b50**\uff08\u6e90\u7801\u7ea7\u786e\u5b9a\uff09 |\n'
u'| \u5355\u4f4d | R g/cm3\u3001T K\u3001P **GPa**\u3001E MJ/kg\u3001Z \u65e0\u91cf\u7eb2 |\n'
u'| \u8ba1\u6570 | `4 + nr + nt + 3\u00b7nr\u00b7nt` |\n'
u'| \u6837\u672c | `mat_Al-1.0/FEOS/Al.feos.301`\uff08620,139 B / 60 \u5b57\u7b26\uff09\u3001`mat_Au-1.0/Au.301`\uff08618,700 B / 64 \u5b57\u7b26\uff09 |\n'
u'| \u9677\u9631 | **\u4e0d\u80fd\u5047\u8bbe\u56fa\u5b9a\u5bbd\u5ea6**\uff08\u5148\u6309 15 \u5207 4 \u6bb5\uff0c\u6ea2\u51fa\u5e76\u56de\u672b\u6bb5\uff09\uff1bZ \u6bb5\u5b9e\u6d4b\u542b\u8d1f\u503c\uff1bT Kelvin \u987b\u8f6c eV |',
'B.4')

d = d.replace('\r\n', '\n')
io.open(P, 'w', encoding='utf-8', newline='\n').write(d)
print('\n'.join(log))
print('chars %d -> %d (+%d)' % (n0, len(d), len(d) - n0))
print('bytes %d' % len(d.encode('utf-8')))
