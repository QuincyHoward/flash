# -*- coding: utf-8 -*-
import re, os, collections
BASE = r"E:/PhySimX/PhySimX/simulation/flash_test/layer3/flash/flash/input_gen/gen_eos_op"
DOC = BASE + "/src/multi_docs/MultiEOSOP格式说明.md"
OUT = BASE + "/.workbuddy/tmp/auditCDEF.txt"
text = open(DOC, encoding='utf-8').read()
LINES = text.split('\n')
lo=[]
def P(*a): lo.append(' '.join(str(x) for x in a))

# ================= AUDIT C: unit conversions =================
P("="*30,"AUDIT C: unit conversion consistency","="*30)
PAIRS = [
 ("1 GPa = 1e-2 Mbar",   [r'1\s*GPa\s*=\s*(?:1e-2|10⁻²|0\.01)\s*Mbar', r'1\s*Mbar\s*=\s*1e11\s*Pa', r'1e-2\s*Mbar']),
 ("1 MJ/kg = 1e-2 Mbar·cm3/g", [r'1\s*MJ/kg\s*=\s*1e-2']),
 ("1 J/cm3 = 1e-5 Mbar", [r'1\s*J/cm[³3]\s*=\s*(?:10⁻⁵|1e-5)']),
 ("1 J/g = 1e7 erg/g",   [r'1\s*J/g\s*=\s*(?:1e7|10⁷)\s*erg/g']),
 ("1 cm/s = 1e-5 µm/ns", [r'1\s*(?:cm/s|um/ns|µm/ns)\s*=\s*(?:1e-5|10⁻⁵)']),
]
for name, pats in PAIRS:
    hits=[]
    for i,ln in enumerate(LINES,1):
        for p in pats:
            if re.search(p, ln): hits.append(i); break
    P("  %-30s %d hits  L%s" % (name, len(hits), ','.join(map(str,hits[:12]))))

P("\n-- raw grep: all lines with GPa / Mbar conversions --")
for i,ln in enumerate(LINES,1):
    if re.search(r'(1\s*GPa|GPa\s*=)', ln) and 'Mbar' in ln:
        P("   L%-6d %s" % (i, ln.strip()[:190]))
P("\n-- raw grep: J/cm3 <-> Mbar --")
for i,ln in enumerate(LINES,1):
    if re.search(r'J/cm', ln) and 'Mbar' in ln:
        P("   L%-6d %s" % (i, ln.strip()[:190]))
P("\n-- raw grep: J/g <-> erg/g --")
for i,ln in enumerate(LINES,1):
    if 'erg/g' in ln and re.search(r'J/g', ln):
        P("   L%-6d %s" % (i, ln.strip()[:190]))

# collect all "X = Y" numeric conversion claims and check arithmetic
P("\n-- numeric identity check on 换算表 (5.2.x / T11 / T37 area) --")
IDENT = re.compile(r'(1e[-+]?\d+)\s*[·*]?\s*(?:×)?\s*(?:=\s*)?(1e[-+]?\d+)')
for i,ln in enumerate(LINES,1):
    if re.search(r'\|\s*(GPa|MJ/kg|J/cm3|J/g|cm/s|dyne/cm2|erg/g|erg/cm3|kJ/g|bar|K)\s*\|', ln):
        if '|' in ln and re.search(r'1e', ln):
            P("   L%-6d %s" % (i, ln.strip()[:200]))

# ================= AUDIT D: tables =================
P("\n"+"="*30,"AUDIT D: table index integrity","="*30)
tnums = collections.OrderedDict()
for i,ln in enumerate(LINES,1):
    for m in re.finditer(r'\bT(\d{1,3})\b', ln):
        n=int(m.group(1))
        if n<=40:
            tnums.setdefault(n,[]).append(i)
present = sorted(tnums)
P("T-numbers seen: %s" % present)
P("count distinct = %d (min %d max %d)" % (len(present), min(present), max(present)))
missing = [n for n in range(min(present), max(present)+1) if n not in tnums]
P("*** MISSING T numbers in range: %s ***" % missing)
P("")
for n in present:
    P("  T%-3d %4d hits" % (n, len(tnums[n])))

# markdown table entities
tbl_start = [i for i,ln in enumerate(LINES,1) if re.match(r'^\s*\|.*\|\s*$', ln)]
P("\nmarkdown table rows total: %d" % len(tbl_start))
# find contiguous blocks
blocks=[]; cur=[]
for i,ln in enumerate(LINES,1):
    if re.match(r'^\s*\|.*\|\s*$', ln): cur.append(i)
    else:
        if cur: blocks.append((cur[0],cur[-1],len(cur))); cur=[]
if cur: blocks.append((cur[0],cur[-1],len(cur)))
P("markdown table blocks: %d" % len(blocks))
P("\n-- table blocks with NO Tnn mention within 5 lines before/after --")
orphan=0
for a,b,n in blocks:
    ctx = '\n'.join(LINES[max(0,a-7):min(len(LINES),b+5)])
    if not re.search(r'\bT\d{1,3}\b', ctx):
        orphan+=1
        P("   L%d-%d (%d rows)  head: %s" % (a,b,n, LINES[a-1].strip()[:110]))
P("  orphan table blocks: %d" % orphan)

# column consistency per block
P("\n-- column-count inconsistency within blocks --")
badcol=0
for a,b,n in blocks:
    if n<2: continue
    cols=set()
    for k in range(a-1,b):
        cells=LINES[k].strip().strip('|').split('|')
        cols.add(len(cells))
    if len(cols)>1:
        badcol+=1
        P("   L%d-%d cols=%s head:%s" % (a,b,sorted(cols),LINES[a-1].strip()[:100]))
P("  blocks with mixed column counts: %d (note: header/separator counted)" % badcol)

# ================= AUDIT E: cross references =================
P("\n"+"="*30,"AUDIT E: cross-reference validity","="*30)
# chapter refs
ch_defined = set()
for i,ln in enumerate(LINES,1):
    m=re.match(r'^#{1,3}\s*第(\d+)章', ln)
    if m: ch_defined.add(int(m.group(1)))
P("chapters defined: %s" % sorted(ch_defined))
ch_ref=collections.Counter()
for i,ln in enumerate(LINES,1):
    for m in re.finditer(r'第(\d+)章', ln): ch_ref[int(m.group(1))]+=1
P("chapter refs: %s" % dict(sorted(ch_ref.items())))
P("*** DANGLING chapter refs: %s ***" % sorted(set(ch_ref)-ch_defined))

# section refs  §N.M  and N.M節
seclevel={}
for i,ln in enumerate(LINES,1):
    m=re.match(r'^#{2,5}\s*(\d+)\.(\d+)', ln)
    if m: seclevel.setdefault(int(m.group(1)),set()).add(int(m.group(2)))
P("\nsection prefixes defined: %s" % {k:sorted(v) for k,v in sorted(seclevel.items())})
sec_ref=collections.Counter()
for i,ln in enumerate(LINES,1):
    for m in re.finditer(r'§\s*(\d+)\.(\d+)', ln): sec_ref[(int(m.group(1)),int(m.group(2)))]+=1
    for m in re.finditer(r'(?<![\d.])(\d+)\.(\d+)\s*节', ln): sec_ref[(int(m.group(1)),int(m.group(2)))]+=1
dang=[]
for (a,b),c in sorted(sec_ref.items()):
    if a not in seclevel or b not in seclevel[a]: dang.append(((a,b),c))
P("*** DANGLING section refs (§N.M / N.M节): %s ***" % [ (str(a)+'.'+str(b),c) for (a,b),c in dang])

# T refs vs defined
P("\nT-refs vs T-numbers: both from same scan, so by construction consistent.")
P("  T defined/mentioned: %d distinct; MISSING: %s" % (len(present), missing))

# F refs
fref=collections.Counter()
for i,ln in enumerate(LINES,1):
    for m in re.finditer(r'图\s*F(\d+)', ln): fref[int(m.group(1))]+=1
P("\n*** ' 图FN ' refs: %s ***" % dict(fref))
for i,ln in enumerate(LINES,1):
    if re.search(r'图\s*F\d+', ln): P("   L%-6d %s" % (i, ln.strip()[:170]))

# appendix refs
app=collections.Counter()
for i,ln in enumerate(LINES,1):
    for m in re.finditer(r'附录\s*([A-ZIVX]+)', ln): app[m.group(1)]+=1
P("\nappendix refs: %s" % dict(sorted(app.items())))
app_def=set()
for i,ln in enumerate(LINES,1):
    m=re.match(r'^#{1,3}\s*附录\s*([A-ZIVX]+)', ln)
    if m: app_def.add(m.group(1))
P("appendix headings defined: %s" % sorted(app_def))
P("*** DANGLING appendix refs: %s ***" % sorted(set(app)-app_def))

open(OUT,'w',encoding='utf-8',newline='\n').write('\n'.join(lo))
print('\n'.join(lo[:60]))
