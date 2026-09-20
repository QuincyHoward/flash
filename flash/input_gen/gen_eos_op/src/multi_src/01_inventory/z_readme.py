# -*- coding: utf-8 -*-
"""生成 src/multi_src/README.md 与 EXCLUDED.md（文件清单由实际目录扫描得出）。"""
import os

ROOT = r'E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\input_gen\gen_eos_op'
DST = os.path.join(ROOT, 'src', 'multi_src')
TMP = os.path.join(ROOT, '.workbuddy', 'tmp')

# 子目录职责说明（顺序 = 建议阅读顺序）
DESC = [
    ('01_inventory', '盘点与索引', '对 `src/Multi1D++Portable20241128/` 与项目根做**全量清点**：文件树、后缀频次、体积、体积分档、路径 token 索引、材料目录清单。产出 JSON/TXT 索引，供后续所有章节引用同一套"事实底座"。'),
    ('02_doc_extract', '一手文档抽取', '把上游 `.doc/.docx/.pdf/.xlsx` 权威说明**逐份转成纯文本**（对应溯源级 `[S-L1]`）。子目录 `docext/ legacy/ pdfext/` 为抽取产物；根下 TXT 为各级汇总（`doc_misc.txt` 汇总散篇、`dataheaders.txt` 汇总数据文件头、`textdocs.txt` 汇总纯文本说明等）。'),
    ('03_anchors', '实测锚点库', '**全文引用的实证底座**：`anchors.md` 收录各族真实文件的头部原文 + 字节数，写作时所有"实测"结论必须溯源到这里。`sample_index.md` 为样本索引，`build_anchors.py` 为生成器（可重跑以刷新锚点）。'),
    ('04_probe', '格式逆向探针', '按**格式族**分组的探针脚本与原始输出。每个子目录自成闭环：脚本 + 输出 + 结论。'),
    ('04_probe/01_cst_and_noext', '`.cst` 与无扩展名族', '`probe_00`–`probe_14` 系列探针及 `out_01`–`out_14` 原始输出。核心成果：`.cst` 双变体（德文/英文）记录结构、`-1.#INF00e+000` 处理、无扩展名多群不透明度表识别。属代理 `probe-cst-naming` 的完整作业痕迹。'),
    ('04_probe/02_multigroup_planck', '多群不透明度表', '`my_planck_*.py` 系列（本人实测）：逐族验证 `PLANCK`/`ROSSELAND`/`EPS`/`ZEFF` 的记录结构、群数双重编码、能量带语义、闭合算术。'),
    ('04_probe/03_sesame', 'SESAME 族', '`.sesame` / `.sesame_` / `.sesame_PLANCK` 的尺寸公式闭合、首字段哨兵常量、粘连表头修复。`v_sesame_*` 为独立复算脚本（用于仲裁代理结论）。'),
    ('04_probe/04_feos', 'FEOS / MPQeos 族', '`.feos` / `.301`/`.304`/`.305` / `.mexport` / `.cst` 的字节级验证；`al_feos_probe.out` 为本地 FEOS 族文件全量定位输出（192 KB）。'),
    ('04_probe/05_hyades_ionmix', 'Hyades / IONMIX 族', 'Hyades ASCII EOS 与 IONMIX `.cn4`/`.cnr` 的头部解码、`ntrad` 反解、计数闭合。`verify_cnr*` / `verify_cn4` 为逐属性验证脚本。'),
    ('04_probe/06_general', '通用探针', '跨族探针：尾部块剥离、手册记录序比对、路径核实（`path_verify*`）、断言复核（`verify2`–`verify7`）。'),
    ('04_probe/probe_noext_agent', '代理 probe-noext 作业目录', '代理 `probe-noext` 的**完整工作目录**（37 文件）：`groupA*` 系列按族分组探针、`selfcheck.py` 自检、`noext_list.json` / `groupA_grids.json` 中间数据。保留原样以便追溯。'),
    ('05_cross_validation', '交叉验证与仲裁', '**同材料跨格式一致性验证**：`xval_s1`–`xval_s14` 分阶段脚本与输出；`eos_readers.py` 为各族读取器原型；`cross_validation.md` 为汇总报告。`arb*.py` / `arbitration.md` 为**三方结论仲裁**（主理人独立复算，否决代理假阳性）。'),
    ('06_agent_reports', '代理产出报告', '各代理交付的**素材报告**（写作时直接引用的中间成果）：格式调研、源码定义反推、网络核验记录、遗漏目录补查、族报告拆分件（`src_doc_*`）。注意：这些是**素材**，正式结论以 `src/multi_docs/` 为准。'),
    ('07_doc_build', '文档生成与打补丁', '**文档装配线**：`plan_multi_doc.md`（写作计划）、`multi_doc_parts/`（分批撰写稿）、`merge_doc.py`（合并器）、`patch_*.py` / `p*_*.py`（历次结构性补丁）。**每个补丁脚本都是幂等可重跑的**，且带 `count` 断言防误改。'),
    ('08_audit', '审计与核查', '**质量门禁**：`audit_v3.py` 为终版综合核查（汉字门禁 / 围栏配对 / 表号唯一性 / 章节单调性 / 交叉引用有效性 / 表格列数 / 残留标记）；`audit*.txt` / `audit_report*.md` 为历次报告；`chk_*.py` 为专项检查；`diag*.py` 为诊断脚本。'),
    ('09_source_verify', '源码级核验与官方包', '**最硬证据源**：`vendor/` 内为 FEOS 官方发行包（`Code/` 37 个 `.C/.H` 为全部表写出器的格式定义、`Documents/` 官方文档、`EOS-Data/` 参数文件）。`dl_feos.py` / `dl_ionmix.py` 为获取脚本。'),
]

lines = []
A = lines.append

A('# multi_src —— 《MultiEOSOP格式说明.md》配套源码与素材库')
A('')
A('> 本目录存放撰写与维护 `src/multi_docs/MultiEOSOP格式说明.md` 过程中产生的**全部脚本、')
A('> 探针、抽取文本、验证输出与代理报告**，按**功能**分门别类归档，便于后续**抽象固化**')
A('> 为可复用的解析器/工具库。')
A('')
A('## 0. 快速导航')
A('')
A('| 我想…… | 去哪个子目录 |')
A('|---|---|')
A('| 了解包内到底有哪些文件、多大、什么后缀 | `01_inventory/` |')
A('| 找上游官方文档的原文 | `02_doc_extract/` |')
A('| 核对文档里某句"实测"结论的依据 | `03_anchors/` |')
A('| 看某个格式是怎么被逆向出来的 | `04_probe/<族>/` |')
A('| 验证"同一材料不同格式数据一致" | `05_cross_validation/` |')
A('| 看某代理交付的调研素材 | `06_agent_reports/` |')
A('| 重新生成/修改文档 | `07_doc_build/` |')
A('| 重新跑一次质量核查 | `08_audit/audit_v3.py` |')
A('| 找格式的**终极权威**（源码级） | `09_source_verify/vendor/` |')
A('')
A('## 1. 目录结构')
A('')
A('```')
A('src/multi_src/')
A('├── README.md                    本文件（索引与约定）')
A('├── MANIFEST.tsv                 源→目标完整映射（338 条）')
A('├── EXCLUDED.md                  未收录项及理由（110 个，属另一工作流）')
A('│')
A('├── 01_inventory/                盘点与索引')
A('├── 02_doc_extract/              一手文档抽取（.doc/.docx/.pdf/.xlsx → txt）')
A('│   ├── docext/                  散篇说明抽取物')
A('│   ├── legacy/                  旧版说明抽取物')
A('│   └── pdfext/                  PDF 抽取物（FEOS / MPQeos / 论文）')
A('├── 03_anchors/                  实测锚点库（全文引用的实证底座）')
A('├── 04_probe/                    格式逆向探针')
A('│   ├── 01_cst_and_noext/        .cst 双变体 + 无扩展名族')
A('│   ├── 02_multigroup_planck/    多群不透明度表（PLANCK/ROSSELAND/EPS/ZEFF）')
A('│   ├── 03_sesame/               SESAME 族')
A('│   ├── 04_feos/                 FEOS / MPQeos 族')
A('│   ├── 05_hyades_ionmix/        Hyades / IONMIX 族')
A('│   ├── 06_general/              跨族通用探针')
A('│   └── probe_noext_agent/       代理 probe-noext 完整作业目录（37 文件）')
A('├── 05_cross_validation/         交叉验证 + 三方仲裁')
A('├── 06_agent_reports/            代理交付的调研素材报告')
A('├── 07_doc_build/                文档装配线（计划/分稿/合并/补丁）')
A('│   ├── multi_doc_parts/         分批撰写稿（17 文件）')
A('│   └── parts/                   后期替换稿')
A('├── 08_audit/                    审计与核查（质量门禁）')
A('└── 09_source_verify/            源码级核验与官方包')
A('    └── vendor/                  FEOS 官方发行包（37 源码 + 文档 + 参数）')
A('```')
A('')
A('## 2. 各子目录职责')
A('')
for d, title, desc in DESC:
    A('### `%s/` —— %s' % (d, title))
    A('')
    A(desc)
    A('')

A('## 3. 完整文件清单')
A('')
tot_files = 0
tot_bytes = 0
for d, title, _ in DESC:
    base = os.path.join(DST, d.replace('/', os.sep))
    if not os.path.isdir(base):
        continue
    A('### `%s/`（%s）' % (d, title))
    A('')
    A('```')
    for dp, dn, fn in os.walk(base):
        rel = os.path.relpath(dp, base)
        files = sorted(fn)
        if rel != '.':
            A('  %s/' % rel)
        for f in files:
            fp = os.path.join(dp, f)
            A('  %-56s %10d' % (f, os.path.getsize(fp)))
            tot_files += 1
            tot_bytes += os.path.getsize(fp)
    A('```')
    A('')
A('**合计：%d 个文件 / %d 字节。**' % (tot_files, tot_bytes))
A('')

A('## 4. 复现约定')
A('')
A('### 4.1 解释器（必须用托管 venv）')
A('')
A('```')
A('C:/Users/Administrator/.workbuddy/binaries/python/envs/default/Scripts/python.exe')
A('```')
A('')
A('### 4.2 数据根（所有探针的相对基准）')
A('')
A('```')
A('src/Multi1D++Portable20241128/')
A('```')
A('')
A('### 4.3 环境陷阱（本机 bash shim 缺 coreutils）')
A('')
A('shim 缺 `dirname` / `cd` / `head` / `tail` / `ls` / `grep` / `cp` / `rm` / `find`，')
A('且**内联 `python -c` 会被二次解释**（含引号/花括号/中文标点必然出错）。')
A('**结论：一律先写 `.py` 脚本文件，再用解释器执行。**')
A('')
A('另注：环境对 `shutil.rmtree` 有 safe-delete 拦截，脚本**不得删除目录**；')
A('复制时用 `shutil.copytree(..., dirs_exist_ok=True)` 实现幂等。')
A('')
A('### 4.4 重跑文档装配与核查')
A('')
A('```bash')
A('# 1) 结构补丁（幂等，可重复执行；每个脚本内含 count 断言防误改）')
A('python 07_doc_build/p7_fixorder.py        # 编号顺序修正')
A('python 07_doc_build/p9_final_fixes.py     # 表号唯一性等')
A('# 2) 质量核查')
A('python 08_audit/audit_v3.py               # 输出 audit_v3.txt')
A('```')
A('')
A('## 5. 归档约定（后续新文件请遵守）')
A('')
A('1. **探针/诊断脚本** → 归入 `04_probe/<相应族>/`；跨族者入 `04_probe/06_general/`。')
A('2. **文档补丁脚本** → `07_doc_build/`，命名 `p<序号>_<主题>.py`；')
A('   必须**幂等**且用 `count` 断言而非 `replace` 静默替换。')
A('3. **核查脚本** → `08_audit/`，命名 `audit_v<n>.py`，报告落同名 `.txt`。')
A('4. **中间输出/原始 dump** → **与产生它的脚本同目录**，不单独建 dump 目录。')
A('5. **代理交付报告** → `06_agent_reports/`，文件名保持代理原始命名以便追溯。')
A('6. **含凭据、绝对临时路径、一次性调试残留**者**不入库**。')
A('')
A('---')
A('')
A('## 6. 关键结论索引（本库支撑的核心成果）')
A('')
A('| 结论 | 主要支撑文件 |')
A('|---|---|')
A('| 无扩展名多群不透明度表（150 文件）记录结构 7/7 闭合 | `04_probe/02_multigroup_planck/`、文档 §14.5 |')
A('| `.cst` 双变体（德 23 / 英 1）与 `-1.#INF00e+000` 处理 | `04_probe/01_cst_and_noext/`、文档 §15.14.2 |')
A('| `.sesame` 尺寸公式 `4+2nr+ne+2nr·ne` 与首字段哨兵 | `04_probe/03_sesame/`、文档 §15.2.6 |')
A('| 记账文件 `CHECKSUM` = (SysV-16, BSD-16) | 文档 §15.14.3、附录 B.23 |')
A('| `.feos` 四列单位与 `write_Rostock_format` 源码明文 | `09_source_verify/vendor/FEOS_src/FEOS/Code/FE-01_TABTOOLS.C` |')
A('| 同材料跨格式一致性（密度网格逐位一致） | `05_cross_validation/xval_s2_closure.txt` |')
A('| 代理"`.sesame` 公式全错"指控为假阳性 | `05_cross_validation/arbitration.md`、`v_sesame_solve.py` |')
A('')

open(os.path.join(DST, 'README.md'), 'w', encoding='utf-8', newline='\n').write('\n'.join(lines))

# ── EXCLUDED.md ──────────────────────────────────────────────
EXCL = []
import re
EXCLUDE_RE = [
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
]
for name in sorted(os.listdir(TMP)):
    if any(re.search(p, name) for p in EXCLUDE_RE):
        EXCL.append(name)

el = []
B = el.append
B('# EXCLUDED —— 未收录项及理由')
B('')
B('`.workbuddy/tmp/` 中另有 **%d 项不属于本文档工作流**，故未复制到 `multi_src/`。' % len(EXCL))
B('它们属于**同一仓库的另一条工作流 —— `eosop_pro` Python 包的开发轮次 (r11–r16)**，')
B('内容为包自身的回归测试日志、提交信息、绘图重绘输出、字段校验再生成等，')
B('与《MultiEOSOP格式说明.md》的**格式规格**工作无关。')
B('')
B('**处置**：保留在 `.workbuddy/tmp/` 原位，不删除、不搬运（避免污染两条工作流的归档）。')
B('')
B('## 排除清单')
B('')
B('| # | 名称 | 归类 |')
B('|---|---|---|')
CAT = [
    (r'^regress|^regression_|^round10_', '包回归测试日志'),
    (r'^commit_msg|^commit_verify', 'Git 提交信息/校验'),
    (r'^git|^hugo_enc_check|^msg_utf8_check|^linecheck', 'Git 与环境检查'),
    (r'^sv_|^run_sv|^cn4fit_probe|^diag_gsound', '声速/热力学模块调试 (r16)'),
    (r'^fit_check_r15|^fit_probe|^clear_check_r15|^clear_plots|^png_left|^redraw_step0|^affected|^orphan_del', '绘图与拟合检查 (r15)'),
    (r'^shrink_memory|^mem_r13|^append_r1|^demo_sync|^migrate_cn4|^del_family_dirs|^drop_shorttable|^inline_short', '模块重构与记忆精简 (r12–r14)'),
    (r'^patch_docstrings|^patch_tags_scheme|^patch_test_plots|^stats_step02|^step01_regenerated|^step02_rerun|^tree_step02|^tpl_|^run_sweep|^run_guess_uk|^guess_|^ne_smoke|^solid_|^run_affected|^run_capture', '包测试与参数扫描'),
    (r'^mem_len', '记忆长度检查'),
]
for i, n in enumerate(EXCL, 1):
    cat = '其它（包开发）'
    for rx, c in CAT:
        if re.search(rx, n):
            cat = c
            break
    B('| %d | `%s` | %s |' % (i, n, cat))
B('')
B('## 如需追查')
B('')
B('```')
B('.workbuddy/tmp/    ← 全部原始文件仍在原位（未删改）')
B('```')
B('')
B('这两条工作流共用同一个 `tmp/` 是历史原因；如后续要彻底分离，建议把包开发产物迁到')
B('`.workbuddy/tmp_eosop/`，并在本文件同步更新排除规则。')
B('')

open(os.path.join(DST, 'EXCLUDED.md'), 'w', encoding='utf-8', newline='\n').write('\n'.join(el))

print('README.md  written, %d files / %d bytes listed' % (tot_files, tot_bytes))
print('EXCLUDED.md written, %d excluded' % len(EXCL))
