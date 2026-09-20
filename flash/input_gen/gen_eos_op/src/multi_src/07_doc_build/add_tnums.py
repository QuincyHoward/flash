# -*- coding: utf-8 -*-
"""Insert T-numbers before appendix tables, starting at T37."""
import re, io

P = r'E:/PhySimX/PhySimX/simulation/flash_test/layer3/flash/flash/input_gen/gen_eos_op/src/multi_docs/MultiEOSOP格式说明.md'
text = open(P, encoding='utf-8', newline='').read()
lines = text.split('\n')

# Appendix table definitions: (line_no_1based_of_header_row, caption)
# Captions chosen from the immediately preceding section heading.
tables = [
    # Appendix A
    (8309, '表 T37　长度与时间换算（A.1）'),
    (8320, '表 T38　压力/压强换算（A.2）'),
    (8333, '表 T39　比能/能量密度换算（A.3）'),
    (8345, '表 T40　温度与能量换算 eV↔K↔keV（A.4）'),
    (8355, '表 T41　不透明度/吸收系数换算（A.5）'),
    (8363, '表 T42　密度与数密度换算（A.6）'),
    (8372, '表 T43　单位换算速查总表（A.7）'),
    (8395, '表 T44　跨族单位体系对照表（A.8）'),
    # Appendix B
    (8415, '表 T45　SESAME 4×15 定宽速查卡（B.1）'),
    (8427, '表 T46　Hyades ASCII EOS 速查卡（B.2）'),
    (8439, '表 T47　FEOS 原生 `.feos` 速查卡（B.3）'),
    (8451, '表 T48　MPQeos `.301`/`.304`/`.305` 速查卡（B.4）'),
    (8463, '表 T49　多群不透明度速查卡（B.5）'),
    (8475, '表 T50　IONMIX `.cn4` 速查卡（B.6）'),
    (8487, '表 T51　IONMIX `.cnr`（legacy）速查卡（B.7）'),
    (8499, '表 T52　ATOMIC/LEDCOP 主表速查卡（B.8）'),
    (8511, '表 T53　LEDCOP 拆分件速查卡（B.9）'),
    (8523, '表 T54　冷不透明度速查卡（B.10）'),
    (8535, '表 T55　Hugoniot `.hug` 速查卡（B.11）'),
    (8547, '表 T56　SNOP namelist 速查卡（B.12）'),
    (8559, '表 T57　Thermos 速查卡（B.13）'),
    (8571, '表 T58　材料级幂律速查卡（B.14）'),
    (8583, '表 T59　曲线/常数 `.dat` 速查卡（B.15）'),
    # Appendix C
    (8599, '表 T60　实测样本索引（相对路径 / 字节数 / 关键表头行）'),
    # Appendix D
    (8745, '表 T61　各族头部结构行数对照（剥离用）'),
    # Appendix E
    (8809, '表 T62　全局已知缺口汇总（按严重程度）'),
    # Appendix F
    (8832, '表 T63　一手材料源清单（字节数 / 覆盖 / 溯源级别）'),
    (8868, '表 T64　待核验项清单'),
    # NOTE: F.3 at L8890 already carries 表 T36 in its heading — must NOT renumber.
]

# verify each target line is a table header (starts with |) and previous non-empty
# line is NOT already a table number line
out = []
inserts = {ln: cap for ln, cap in tables}
report = []
for i, ln in enumerate(lines, 1):
    if i in inserts:
        prev = lines[i-2].strip() if i >= 2 else ''
        if not ln.strip().startswith('|'):
            report.append('SKIP L%d: not a table header: %r' % (i, ln[:60]))
            out.append(ln)
            continue
        if prev.startswith('**表 T'):
            report.append('SKIP L%d: already has T-number line: %r' % (i, prev[:60]))
            out.append(ln)
            continue
        out.append('**%s**' % inserts[i])
        out.append('')
        report.append('OK   L%d <- %s' % (i, inserts[i]))
    out.append(ln)

if report:
    print('\n'.join(report))
bad = [r for r in report if r.startswith('SKIP')]
if bad:
    print('\n!! ABORT: %d problems, not writing' % len(bad))
else:
    open(P, 'w', encoding='utf-8', newline='\n').write('\n'.join(out))
    print('\nWRITTEN, %d tables numbered' % len(tables))
