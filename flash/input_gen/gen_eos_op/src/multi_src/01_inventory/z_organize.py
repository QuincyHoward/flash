# -*- coding: utf-8 -*-
"""把 .workbuddy/tmp 中与《MultiEOSOP格式说明.md》相关的脚本/素材，按功能复制到
   src/multi_src/ 的功能子目录中。只复制、不移动、不删除。

输出：multi_src/MANIFEST.tsv（源→目标映射）+ multi_src/EXCLUDED.md（排除项说明）
"""
import os, re, shutil, hashlib
from collections import defaultdict

ROOT = r'E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\input_gen\gen_eos_op'
TMP = os.path.join(ROOT, '.workbuddy', 'tmp')
DST = os.path.join(ROOT, 'src', 'multi_src')

# ─────────────────────────────────────────────────────────────
# 排除：eosop_pro 包开发轮次 (r11–r16) 的产物，与本文档无关
# ─────────────────────────────────────────────────────────────
EXCLUDE_RE = [re.compile(p) for p in [
    r'^affected_', r'^append_r1[24]_log', r'^clear_check_r15', r'^clear_plots_r15',
    r'^cn4fit_probe_r15', r'^commit_msg_r1', r'^commit_verify_r1',
    r'^demo_sync_r12', r'^diag_gsound_r16', r'^drop_shorttable_r14',
    r'^fit_check_r15$', r'^fit_probe_', r'^git', r'^inline_short_r14',
    r'^linecheck_r16', r'^log_tail_r16', r'^mem_len', r'^mem_r13',
    r'^migrate_cn4_r13', r'^ne_smoke$', r'^orphan_del_r15',
    r'^patch_docstrings', r'^patch_tags_scheme', r'^patch_test_plots',
    r'^png_left_r15', r'^redraw_step0', r'^regress', r'^regression_',
    r'^round10_fieldchecks_regen', r'^run_affected_r14', r'^run_guess_uk',
    r'^run_sv_r16', r'^run_sweep', r'^shrink_memory_r14', r'^stats_step02',
    r'^step01_regenerated_r15', r'^step02_rerun', r'^sv_', r'^tpl_path',
    r'^tpl_r15', r'^tree_step02', r'^hugo_enc_check', r'^msg_utf8_check',
    r'^guess_smoke', r'^guess_uk_summary', r'^del_family_dirs',
    r'^solid_', r'^run_capture\.py$',
]]

# ─────────────────────────────────────────────────────────────
# 规则：(正则, 目标子目录)  —— 按顺序首个命中生效
# ─────────────────────────────────────────────────────────────
D = {
    'inv':   '01_inventory',
    'doc':   '02_doc_extract',
    'anch':  '03_anchors',
    'p_cst': '04_probe/01_cst_and_noext',
    'p_mg':  '04_probe/02_multigroup_planck',
    'p_ses': '04_probe/03_sesame',
    'p_fe':  '04_probe/04_feos',
    'p_hy':  '04_probe/05_hyades_ionmix',
    'p_gen': '04_probe/06_general',
    'p_nx':  '04_probe/probe_noext_agent',
    'xval':  '05_cross_validation',
    'rep':   '06_agent_reports',
    'build': '07_doc_build',
    'aud':   '08_audit',
    'src':   '09_source_verify',
}

RULES = [
    # ── 先处理特例（避免被后面的宽规则吃掉） ─────────────────
    (r'^probe_00_env\.py$|^probe_09_lsroot\.py$|^probe_lower\.py$', D['inv']),
    (r'^append_mem\.py$', D['build']),
    (r'^diag_issues\.py$|^ls_head\.py$|^ls_state\.py$|^scan\.txt$', D['inv']),
    (r'(?i)^my_planc', D['p_mg']),
    (r'^q_|^census_|^multigroup_opacity', D['p_mg']),
    (r'^new_145', D['build']),
    (r'(?i)^recheck_sesame', D['p_ses']),
    (r'^feos_src', D['p_fe']),
    (r'(?i)^debug', D['aud']),
    (r'^verify_feos', D['p_fe']),

    # ── 目录 ────────────────────────────────────────────────
    (r'^docext$', D['doc']),
    (r'^legacy$', D['doc']),
    (r'^pdfext$', D['doc']),
    (r'^multi_doc_parts$', D['build']),
    (r'^parts$', D['build']),
    (r'^probe_noext$', D['p_nx']),
    (r'^vendor$', D['src']),

    # ── 09 源码级核验 ────────────────────────────────────────
    (r'^_tft\.py$|^_cases\.py$', D['src']),
    (r'^dl_feos\.py$|^dl_ionmix', D['src']),
    (r'^inspect_data\.', D['src']),

    # ── 08 审计与核查 ────────────────────────────────────────
    (r'^audit', D['aud']),
    (r'^chk\d*\.py$|^chk_', D['aud']),
    (r'^diag', D['aud']),
    (r'^count_cjk\.py$', D['aud']),
    (r'^verify_cn\.py$|^verify_cn4\.py$|^verify_cnr\d*\.py$', D['aud']),
    (r'^linecheck|^final\.txt$|^doc_conventions\.md$', D['aud']),

    # ── 07 文档生成/打补丁 ───────────────────────────────────
    (r'^plan_multi_doc\.md$|^merge_doc\.py$', D['build']),
    (r'^patch_', D['build']),
    (r'^p\d+[a-z]?_', D['build']),
    (r'^add_tnums\.py$|^app_tables\.py$|^appF\.txt$|^_appE\.txt$', D['build']),
    (r'^fix_sec_refs\.py$|^fix_paths_scan\.py$|^find_real\.py$|^empty_s1\.py$', D['build']),

    # ── 05 交叉验证 ──────────────────────────────────────────
    (r'^xval_', D['xval']),
    (r'(?i)^xv2', D['xval']),
    (r'^cross_validation\.md$|^eos_readers\.py$|^eos_final\.py$', D['xval']),
    (r'^arb', D['xval']),
    (r'^cst_naming_finding\.md$|^multigroup_opacity_finding\.md$', D['xval']),
    (r'^verdictB', D['xval']),
    (r'^DELIVERABLES\.txt$|^check_deliverables\.py$', D['xval']),

    # ── 04/01 CST + 无扩展名探针（代理 probe-cst-naming） ─────
    (r'^probe_0\d', D['p_cst']),
    (r'^probe_1\d', D['p_cst']),
    (r'^probe_cst_noext\.py$|^noext_cst\.py$', D['p_cst']),
    (r'^out_\d\d', D['p_cst']),
    (r'^out_dummy\.txt$', D['p_cst']),
    (r'^cst_inventory\.json$|^noext_inventory\.json$', D['p_cst']),

    # ── 04/02 多群不透明度（PLANCK/ROSSELAND/EPS/ZEFF） ──────
    (r'^my_planck', D['p_mg']),
    (r'^my_groups_cmp\.py$', D['p_mg']),

    # ── 04/03 SESAME ────────────────────────────────────────
    (r'^probe_sesame', D['p_ses']),
    (r'^v_sesame_', D['p_ses']),
    (r'^verify_sesame_', D['p_ses']),
    (r'^sesame_dump\.txt$|^sesame_extract\.txt$|^_sesame_au\.txt$', D['p_ses']),

    # ── 04/04 FEOS / MPQeos ─────────────────────────────────
    (r'^probe_feos|^probe_al_feos|^al_feos_probe\.out$', D['p_fe']),
    (r'^dbg_feos\.py$|^dbg_sio2\.py$', D['p_fe']),
    (r'^_dump_c20g\.txt$', D['p_fe']),

    # ── 04/05 Hyades / IONMIX ───────────────────────────────
    (r'^probe_hyades\.py$|^verify_hyades\.py$|^list_hyades\.py$', D['p_hy']),
    (r'^dbg_cn4\.py$', D['p_hy']),
    (r'^verify_cn4\.py$|^verify_cnr\d*\.py$', D['p_hy']),
    (r'^hyades_doc\.txt$|^atomic_dump\.txt$|^dataheaders\.txt$', D['p_hy']),

    # ── 04/06 通用探针 ───────────────────────────────────────
    (r'^probe_tail', D['p_gen']),
    (r'^probe_manual_order\.py$|^probe_anchors2\.py$', D['p_gen']),
    (r'^verify[2-7]\.py$', D['p_gen']),
    (r'^path_verify', D['p_gen']),
    (r'^_probe2?\.py$|^_x\.py$|^_dump\.py$', D['p_gen']),

    # ── 06 代理产出报告 ──────────────────────────────────────
    (r'^explore_multi_formats\.md$|^explore_python_support\.md$', D['rep']),
    (r'^formats_from_source\.md$|^formats_resolved\.md$|^feos_formats\.md$', D['rep']),
    (r'^missed_dirs\.md$|^noext_formats\.md$|^naming_cst_formats\.md$', D['rep']),
    (r'^web_verify', D['rep']),
    (r'^src_doc_', D['rep']),
    (r'^src_ionmix_snop\.md$|^src_sesame_ledcop\.md$', D['rep']),
    (r'^_w7\.txt$|^_wv2_idx\.txt$', D['rep']),

    # ── 02 文档抽取 ─────────────────────────────────────────
    (r'^extract_doc\.py$|^extract_legacy\.py$|^pdf_extract\.py$', D['doc']),
    (r'^doc_misc\.txt$|^docx_extract\.txt$|^xlsx_extract\.txt$|^textdocs\.txt$', D['doc']),
    (r'^enum_doc_matter\.txt$', D['doc']),
    (r'^legacy_doc', D['doc']),
    (r'^fds_gui\.txt$|^_feos_pdf_dump\.txt$', D['doc']),
    (r'^toc\.txt$|^_ch8\.txt$|^tbl\.txt$|^ch\.txt$|^seg\.txt$', D['doc']),

    # ── 03 锚点 ────────────────────────────────────────────
    (r'^anchors\.md$|^build_anchors\.py$', D['anch']),
    (r'^sample_index\.md$|^find_anchors\.py$', D['anch']),

    # ── 01 盘点与索引 ────────────────────────────────────────
    (r'^_ls2?\.py$|^_tree\.py$|^_mats\.py$|^_mhead\.py$', D['inv']),
    (r'^_idx_|^_candtok\.json$|^_pathtok\.json$|^_miss\.json$', D['inv']),
    (r'^_fl\.txt$|^paths_resolve\.json$|^_filelist_tmp\.txt$', D['inv']),
    (r'^inv_', D['inv']),
    (r'^build_inventory\.py$', D['inv']),
    (r'^count_patterns\.', D['inv']),
    (r'^uncovered\.py$|^cov_check\.py$', D['inv']),
    (r'^dirlist', D['inv']),
    (r'^find_lower|^find2\.py$', D['inv']),
    (r'^out_lsroot\.txt$|^out_srcs\.txt$|^out_feosls\.txt$', D['inv']),
    (r'^probe_00_env\.py$|^probe_09_lsroot\.py$|^probe_lower\.py$', D['inv']),
    (r'^z_', D['inv']),
    (r'^auditCDEF\.txt$', D['aud']),
]


def sha1(p, n=1 << 20):
    h = hashlib.sha1()
    with open(p, 'rb') as f:
        while True:
            b = f.read(n)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


RULES_C = [(re.compile(p), dest) for p, dest in RULES]


def route(name, isdir):
    for rx in EXCLUDE_RE:
        if rx.search(name):
            return None, 'EXCLUDE'
    for rx, dest in RULES_C:
        if rx.search(name):
            return dest, 'OK'
    return None, 'UNSORTED'


os.makedirs(DST, exist_ok=True)
manifest = []
excluded = []
unsorted = []

entries = sorted(os.listdir(TMP))
for name in entries:
    p = os.path.join(TMP, name)
    isdir = os.path.isdir(p)
    dest, status = route(name, isdir)
    if status == 'EXCLUDE':
        sz = (sum(os.path.getsize(os.path.join(dp, f))
                  for dp, _, fn in os.walk(p) for f in fn) if isdir
              else os.path.getsize(p))
        excluded.append((name, isdir, sz))
        continue
    if status == 'UNSORTED':
        sz = (sum(os.path.getsize(os.path.join(dp, f))
                  for dp, _, fn in os.walk(p) for f in fn) if isdir
              else os.path.getsize(p))
        unsorted.append((name, isdir, sz))
        continue
    target_dir = os.path.join(DST, dest.replace('/', os.sep))
    os.makedirs(target_dir, exist_ok=True)
    tp = os.path.join(target_dir, name)
    if isdir:
        # 幂等：已存在则合并覆盖，不做删除（环境对 rmtree 有 safe-delete 拦截）
        shutil.copytree(p, tp, dirs_exist_ok=True)
        n = sum(len(f) for _, _, f in os.walk(tp))
        sz = sum(os.path.getsize(os.path.join(dp, f))
                 for dp, _, fn in os.walk(tp) for f in fn)
        manifest.append(('%s/' % name, dest, 'DIR', n, sz))
    else:
        shutil.copy2(p, tp)
        manifest.append((name, dest, 'FILE', 1, os.path.getsize(tp)))

# ── 写清单 ──────────────────────────────────────────────────
ml = ['src\t->\tdest\tsubpath\tkind\tn_files\tbytes']
for src, dest, kind, n, sz in sorted(manifest, key=lambda r: (r[1], r[0])):
    ml.append('%s\t%s\t\t%s\t%d\t%d' % (src, dest, kind, n, sz))
open(os.path.join(DST, 'MANIFEST.tsv'), 'w', encoding='utf-8', newline='\n').write('\n'.join(ml))

print('=== COPIED ===')
byd = defaultdict(list)
for src, dest, kind, n, sz in manifest:
    byd[dest].append((src, kind, n, sz))
tot = 0
for dest in sorted(byd):
    items = byd[dest]
    b = sum(s for _, _, _, s in items)
    f = sum(n for _, k, n, _ in items if k == 'FILE') + sum(n for _, k, n, _ in items if k == 'DIR')
    tot += b
    print('%-34s %3d items %10d B' % (dest, len(items), b))
print('TOTAL COPIED BYTES = %d  (items %d)' % (tot, len(manifest)))
print()
print('=== EXCLUDED (pkg-dev r11-r16) : %d ===' % len(excluded))
for n, d, s in excluded:
    print('   %-38s %s %10d' % (n, 'DIR ' if d else 'FILE', s))
print()
print('=== UNSORTED : %d ===' % len(unsorted))
for n, d, s in unsorted:
    print('   %-38s %s %10d' % (n, 'DIR ' if d else 'FILE', s))
