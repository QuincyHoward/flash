# -*- coding: utf-8 -*-
"""分类 .workbuddy/tmp 中与 MultiEOSOP格式说明.md 相关的文件。
   输出 TSV 报告供人工复核。"""
import os, re, json

ROOT = r'E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\input_gen\gen_eos_op'
TMP = os.path.join(ROOT, '.workbuddy', 'tmp')
DOCNAME = 'MultiEOSOP格式说明'

# ── 判定关键词 ───────────────────────────────────────────────
DOC_HINTS = [
    'MultiEOSOP', 'multi_docs', 'multi_doc_parts', 'Multi1D++Portable',
    'matter++', 'Readme.txt', '格式说明', 'anchors.md', 'plan_multi_doc',
    'candidate', 'CANDIDATE', '§', '附录',
]
PKG_HINTS = [
    'eosop_pro', 'field_checks', 'run_all', 'plotting', 'parsers',
    'cn4_paths', 'sound_velocity', 'cn4_thermo', 'registry',
    '_out/', 'test/', 'steps', 'step01', 'step02', 'step03',
    'PLOT_LEGEND_FONTSIZE', 'DPI', 'gridmap', 'labels.py',
    'run_sv', 'regress', 'patch_test_plots', 'guess_uk',
]
# 明确属于包开发的轮次（r11–r16）文件名特征
ROUND_RE = re.compile(r'r1[1-6]|_r1[1-6]|round10|regress')

EXT_TEXT = {'.py', '.md', '.txt', '.json', '.log', '.out', '.tsv', '.csv', '.bat', '.sh'}


def read_head(p, nbytes=6000):
    try:
        with open(p, 'rb') as f:
            b = f.read(nbytes)
        return b.decode('utf-8', 'replace')
    except OSError:
        return ''


rows = []
for name in sorted(os.listdir(TMP)):
    p = os.path.join(TMP, name)
    if os.path.isdir(p):
        # 目录：抽查目录内所有文本文件
        txt = ''
        cnt = 0
        for dp, _, fn in os.walk(p):
            for f in fn:
                if os.path.splitext(f)[1].lower() in EXT_TEXT:
                    txt += read_head(os.path.join(dp, f), 2500)
                    cnt += 1
                    if len(txt) > 120000:
                        break
            if len(txt) > 120000:
                break
        size = sum(os.path.getsize(os.path.join(dp, f))
                   for dp, _, fn in os.walk(p) for f in fn)
        kind = 'DIR'
    else:
        txt = read_head(p)
        size = os.path.getsize(p)
        kind = 'FILE'

    ds = sum(txt.count(h) for h in DOC_HINTS)
    ps = sum(txt.count(h) for h in PKG_HINTS)
    is_round = bool(ROUND_RE.search(name))
    rows.append((name, kind, size, ds, ps, is_round))

# 写 TSV
lines = ['name\tkind\tbytes\tdoc_hits\tpkg_hits\tround_flag\tsuggestion']
for name, kind, size, ds, ps, is_round in rows:
    if is_round and ds <= ps:
        sug = 'EXCLUDE(pkg-round)'
    elif ds > ps and ds > 0:
        sug = 'INCLUDE'
    elif ds == 0 and ps > 0:
        sug = 'EXCLUDE(pkg)'
    elif ds == 0 and ps == 0:
        sug = 'REVIEW(no-hint)'
    else:
        sug = 'REVIEW(tie)'
    lines.append('%s\t%s\t%d\t%d\t%d\t%s\t%s'
                 % (name, kind, size, ds, ps, is_round, sug))

out = os.path.join(TMP, 'z_classify.tsv')
open(out, 'w', encoding='utf-8', newline='\n').write('\n'.join(lines))

# 汇总
from collections import Counter
c = Counter(l.split('\t')[6] for l in lines[1:])
print('wrote', out)
for k, v in c.most_common():
    print('  %-22s %d' % (k, v))
