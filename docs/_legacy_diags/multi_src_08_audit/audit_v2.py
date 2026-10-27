# -*- coding: utf-8 -*-
"""综合核查 v2：汉字门禁 / 围栏 / 表号 / 章节顺序 / 内部引用（区分外部文档§）/
   表格列数 / 单行长度 / 残留标记。"""
import os, re, collections

ROOT = r'E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\input_gen\gen_eos_op'
DOC = os.path.join(ROOT, 'src', 'multi_docs', 'MultiEOSOP格式说明.md')
txt = open(DOC, encoding='utf-8').read()
L = txt.split('\n')
out = []


def P(*a):
    s = ' '.join(str(x) for x in a)
    out.append(s)
    print(s)


P('=' * 76)
P('MultiEOSOP格式说明.md 综合核查 v2')
P('=' * 76)
P('字节数 :', os.path.getsize(DOC))
P('字符数 :', len(txt))
P('总行数 :', len(L))
cn = len(re.findall(r'[\u4e00-\u9fff]', txt))
P('汉字数 :', cn, '(门禁 80,000)', 'PASS' if cn >= 80000 else 'FAIL')
P()

# ── 1 围栏 ───────────────────────────────────────────────────
P('-' * 76); P('[1] 代码围栏配对'); P('-' * 76)
fen = [i for i, l in enumerate(L) if l.strip().startswith('```')]
P('围栏总数:', len(fen), 'PASS' if len(fen) % 2 == 0 else 'FAIL')
langs = collections.Counter()
for k in range(0, len(fen) - 1, 2):
    langs[L[fen[k]].strip()[3:].strip() or '(none)'] += 1
P('代码块数:', sum(langs.values()), dict(langs))
P()

# ── 2 表号 ───────────────────────────────────────────────────
P('-' * 76); P('[2] 表号 T1–T99'); P('-' * 76)
tabs = [int(m) for m in re.findall(r'表\s*T(\d+)\b', txt)]
cnt = collections.Counter(tabs)
P('不同表号:', len(cnt), '范围:', (min(tabs), max(tabs)))
# 只把 "**表 Tnn 标题**" 形态视为定义；其余为引用
defs = collections.Counter()
for l in L:
    m = re.match(r'^\*\*表\s*T(\d+)\s+[^*]+\*\*', l.strip())
    if m:
        defs[int(m.group(1))] += 1
dupd = {k: v for k, v in defs.items() if v > 1}
P('出现重复"定义"的表号:', dupd if dupd else '无  PASS')
miss = [i for i in range(1, max(cnt) + 1) if i not in cnt]
P('编号缺口 (%d): %s' % (len(miss), miss))
undef = sorted(set(cnt) - set(defs))
P('被引用但无"**表 Tnn ...**"定义 (%d): %s' % (len(undef), undef))
P()

# ── 3 章节顺序 ───────────────────────────────────────────────
P('-' * 76); P('[3] 章节编号顺序'); P('-' * 76)
ch = [(i + 1, int(m.group(1))) for i, l in enumerate(L)
      for m in [re.match(r'^## 第(\d+)章', l)] if m]
nums = [n for _, n in ch]
P('第N章:', nums, 'PASS' if nums == sorted(nums) else 'FAIL')
apps = [m.group(1) for l in L for m in [re.match(r'^## 附录 ([A-F])', l)] if m]
P('附录  :', apps, 'PASS' if apps == sorted(apps) else 'FAIL')

bad = []
for lvl_pat, label in [(r'^### (\d+)\.(\d+)\b', '三级'), (r'^#### (\d+)\.(\d+)\.(\d+)\b', '四级')]:
    grp = collections.defaultdict(list)
    for i, l in enumerate(L):
        m = re.match(lvl_pat, l)
        if m:
            g = m.groups()
            key = (int(g[0]), int(g[1])) if len(g) == 2 else (int(g[0]), int(g[1]))
            val = int(g[1]) if len(g) == 2 else int(g[2])
            grp[key].append((i + 1, val))
    for k, lst in sorted(grp.items()):
        vs = [v for _, v in lst]
        if vs != sorted(vs):
            bad.append((label, k, vs))
if bad:
    P('  非单调:')
    for label, k, vs in bad:
        P('    [%s] %s -> %s' % (label, k, vs))
else:
    P('  二/三/四级节全部单调  PASS')
# 附录 B 子节
b = [(i + 1, int(m.group(1))) for i, l in enumerate(L)
     for m in [re.match(r'^### B\.(\d+)\b', l)] if m]
P('  附录 B 子节:', [v for _, v in b], 'PASS' if [v for _, v in b] == sorted(v for _, v in b) else 'FAIL')
P()

# ── 4 内部引用 ───────────────────────────────────────────────
P('-' * 76); P('[4] 交叉引用有效性'); P('-' * 76)
defined = set()
for l in L:
    for pat in [r'^#{2,4}\s+(\d+\.\d+(?:\.\d+)?)\b',
                r'^#{2,4}\s+(前置-\d+\.\d+)\b',
                r'^#{2,4}\s+([A-F]\.\d+(?:\.\d+)?)\b']:
        m = re.match(pat, l)
        if m:
            defined.add(m.group(1))

EXT = ('FEOS 说明', 'FEOS API', 'FEOS §', '手册', 'IONMIX', 'FLASH', '指南',
       'Package Documentation', 'User\'s Guide', '文档 §', 'doc/', 'UG §',
       'Hrutkai', 'MULTI2002', 'MULTI 手册', 'CPC', '论文')
refs = []
for i, l in enumerate(L):
    for m in re.finditer(r'§\s*((?:\d+\.\d+(?:\.\d+)?)|(?:前置-\d+\.\d+)|(?:[A-F]\.\d+(?:\.\d+)?))', l):
        ctx = l[max(0, m.start() - 40):m.start()]
        ext = any(e in ctx for e in EXT)
        refs.append((i + 1, m.group(1), ext, ctx.replace('\n', ' ')[-38:]))
intr = [r for r in refs if not r[2]]
extr = [r for r in refs if r[2]]
P('引用总数:', len(refs), ' 内部:', len(intr), ' 外文档:', len(extr))
dang = [r for r in intr if r[1] not in defined]
if dang:
    P('  !! 内部悬空引用 (%d):' % len(dang))
    for ln, k, _, ctx in dang:
        P('     L%-6d §%-10s  ← %s' % (ln, k, ctx))
else:
    P('  内部引用全部有效  PASS')
P()

# ── 5 表格列数 ───────────────────────────────────────────────
P('-' * 76); P('[5] 表格列数一致性'); P('-' * 76)
def cells(l):
    s = l.strip()
    if s.startswith('|'): s = s[1:]
    if s.endswith('|'): s = s[:-1]
    o, b, i, code = [], '', 0, False
    while i < len(s):
        c = s[i]
        if c == '\\' and i + 1 < len(s):
            b += s[i:i+2]; i += 2; continue
        if c == '`':
            code = not code; b += c; i += 1; continue
        if c == '|' and not code:
            o.append(b); b = ''; i += 1; continue
        b += c; i += 1
    o.append(b)
    return [x.strip() for x in o]

bad_t, ntab, i = [], 0, 0
while i < len(L):
    if L[i].strip().startswith('|') and i + 1 < len(L) and re.match(r'^\s*\|[\s:|-]+\|\s*$', L[i+1]):
        ntab += 1
        n = len(cells(L[i]))
        j, rows = i + 2, []
        while j < len(L) and L[j].strip().startswith('|'):
            if len(cells(L[j])) != n:
                rows.append((j + 1, len(cells(L[j]))))
            j += 1
        if len(cells(L[i+1])) != n:
            rows.append((i + 2, len(cells(L[i+1]))))
        if rows:
            bad_t.append((i + 1, n, rows[:6], len(rows)))
        i = j
    else:
        i += 1
P('表格总数:', ntab)
P('  列数不一致:', len(bad_t), 'PASS' if not bad_t else 'FAIL')
for ln, n, rows, tot in bad_t:
    P('    L%d 表头%d列 异常%d行: %s' % (ln, n, tot, rows))
P()

# ── 6 残留标记 ───────────────────────────────────────────────
P('-' * 76); P('[6] 残留标记'); P('-' * 76)
for pat, lab in [(r'TODO|FIXME|待补充|待写|\bXXX\b', 'TODO/待补'),
                 (r'\{\{|\}\}', '模板占位'),
                 (r'\]\(\s*\)', '空链接'),
                 (r'[。，]\s*[。，]', '重复标点'),
                 (r'\bNone\b', '裸 None'),
                 (r'<<<|>>>|<<<<<<<|>>>>>>>', '冲突标记')]:
    hits = [(i + 1, l.strip()[:70]) for i, l in enumerate(L) if re.search(pat, l)]
    P('%-12s %d' % (lab, len(hits)))
    for ln, s in hits[:5]:
        P('     L%d: %s' % (ln, s))
P()
P('=' * 76)
P('核查结束')
P('=' * 76)

open(os.path.join(ROOT, '.workbuddy', 'tmp', 'audit_v2.txt'), 'w',
     encoding='utf-8', newline='\n').write('\n'.join(out))
print('\n[written] .workbuddy/tmp/audit_v2.txt')
