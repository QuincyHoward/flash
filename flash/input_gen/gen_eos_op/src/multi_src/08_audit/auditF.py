# -*- coding: utf-8 -*-
import re, os, collections
BASE = r"E:/PhySimX/PhySimX/simulation/flash_test/layer3/flash/flash/input_gen/gen_eos_op"
DOC = BASE + "/src/multi_docs/MultiEOSOP格式说明.md"
OUT = BASE + "/.workbuddy/tmp/auditF.txt"
LINES = open(DOC, encoding='utf-8').read().split('\n')
lo=[]
def P(*a): lo.append(' '.join(str(x) for x in a))

P("="*30,"AUDIT F: per-chapter 本章实测锚点 / 本章缺口","="*30)
# find chapter starts
chaps=[]
for i,ln in enumerate(LINES,1):
    m=re.match(r'^#{1,3}\s*第(\d+)章', ln)
    if m: chaps.append((int(m.group(1)), i))
chaps.sort(key=lambda x:x[1])
P("chapters: %s" % [c[0] for c in chaps])
P("")
anchors=[]; gaps=[]
for k,(cn, start) in enumerate(chaps):
    end = chaps[k+1][1]-1 if k+1<len(chaps) else len(LINES)
    body = LINES[start-1:end]
    a_idx = [start+j for j,l in enumerate(body) if re.match(r'^#{2,5}\s*本章实测锚点', l)]
    g_idx = [start+j for j,l in enumerate(body) if re.match(r'^#{2,5}\s*本章缺口', l)]
    anchors.append((cn, a_idx)); gaps.append((cn, g_idx))
P("-- 本章实测锚点 --")
for cn, idx in anchors:
    P("  ch%-3d %s %s" % (cn, "PRESENT" if idx else "*** MISSING ***", idx))
P("\n-- 本章缺口 --")
for cn, idx in gaps:
    P("  ch%-3d %s %s" % (cn, "PRESENT" if idx else "*** MISSING ***", idx))

# count gap ENTRIES inside each 本章缺口 section
P("\n-- gap entry counts (numbered/bulleted lines) --")
P("  ch | entries | theme summary")
tot=0
rowout=[]
for k,(cn, start) in enumerate(chaps):
    end = chaps[k+1][1]-1 if k+1<len(chaps) else len(LINES)
    gi = [x for c,ii in gaps for x in ii if c==cn]
    if not gi: continue
    gs = gi[0]
    # section ends at next heading of same-or-higher level
    ge = end
    for j in range(gs, end):
        if j>gs and re.match(r'^#{1,5}\s', LINES[j-1]) and not re.match(r'^#{4,5}', LINES[j-1]):
            ge = j-1; break
        if j>gs and re.match(r'^#{2,3}\s', LINES[j-1]):
            ge = j-1; break
    sec = LINES[gs-1:ge]
    # count entries: lines starting with "N." or "- " or "| N |"
    ents = [l for l in sec if re.match(r'^\s*(\d+\.|[-*]\s|\|\s*\d+\s*\|)', l)]
    # if a markdown table, count its rows minus header/sep
    tbl = [l for l in sec if re.match(r'^\s*\|.*\|\s*$', l)]
    n = len(ents)
    if len(tbl)>2 and n==0:
        n = len(tbl)-2
    theme = ''
    for l in sec[1:6]:
        s=l.strip()
        if s and not s.startswith('|') and '---' not in s:
            theme = s[:70]; break
    tot += n
    rowout.append((cn, n, theme))
    P("  %-3d| %5d  | %s" % (cn, n, theme))
P("\n  *** TOTAL GAP ENTRIES across all chapters: %d ***" % tot)

# also the global appendix gap list
P("\n-- appendix E / 附录E: 缺口清单 rows --")
for i,ln in enumerate(LINES,1):
    if re.match(r'^#{1,4}\s*附录\s*E', ln): P("  L%d %s" % (i, ln.strip()))
for i,ln in enumerate(LINES,1):
    if re.search(r'附录\s*E', ln) and i>8700: P("  L%-6d %s" % (i, ln.strip()[:150]))
open(OUT,'w',encoding='utf-8',newline='\n').write('\n'.join(lo))
print('\n'.join(lo))
