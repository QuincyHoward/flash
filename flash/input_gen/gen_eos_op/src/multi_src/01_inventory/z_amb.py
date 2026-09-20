# -*- coding: utf-8 -*-
"""对分类模糊的文件打印前两行，供人工判定。"""
import os

ROOT = r'E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\input_gen\gen_eos_op'
TMP = os.path.join(ROOT, '.workbuddy', 'tmp')

AMB = """DELIVERABLES.txt
check_deliverables.py
count_cjk.py
extract_doc.py
pdf_extract.py
run_capture.py
ch.txt
seg.txt
tbl.txt
_dump_c20g.txt
_sesame_au.txt
sesame_dump.txt
sesame_extract.txt
solid_results.txt
solid_t1.log
solid_t1b_results.txt
auditCDEF.txt
verdictB.txt
doc_misc.txt
fds_gui.txt
docx_extract.txt
textdocs.txt
enum_doc_matter.txt
dataheaders.txt
legacy_doc_be.txt
legacy_doc_full.txt
inv_matter.json
noext_inventory.json
web_verify.md
multigroup_opacity_finding.md
arbitration.md
_candtok.json
_pathtok.json
_miss.json
_idx_repo.json
paths_resolve.json
al_feos_probe.out
hugo_enc_check.txt
msg_utf8_check.txt
out_dummy.txt
out_srcs.txt
out_14_log.txt
empty_s1.py
find2.py
find_real.py
count_patterns.py
formats_from_source.md
explore_python_support.md
probe_al_feos.py
_x.py
_fl.txt
_w7.txt
_wv2_idx.txt
_cases.py
_tft.py
_probe.py
_probe2.py
_mats.py
_mhead.py
_ls.py
_ls2.py
_tree.py
_dump.py
inspect_data.py
dl_feos.py
dl_ionmix.out
out_01.txt
out_11.txt
out_14.txt
xval_s10.txt
xval_s2_closure.txt
z_inv2.py
_filelist_tmp.txt
_out_dummy.txt""".split('\n')

for name in AMB:
    p = os.path.join(TMP, name)
    print('=' * 74)
    if not os.path.exists(p):
        print('!! MISSING', name)
        continue
    print('## %s  (%d B)' % (name, os.path.getsize(p)))
    try:
        raw = open(p, 'rb').read(700)
    except OSError as e:
        print('   ERR', e); continue
    txt = raw.decode('utf-8', 'replace')
    for line in txt.split('\n')[:5]:
        line = line.strip()
        if line:
            print('   |', line[:150])
