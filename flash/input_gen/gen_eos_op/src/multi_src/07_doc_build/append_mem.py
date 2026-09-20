import os

P = '.workbuddy/memory/2026-09-18.md'

ADD = """
## MultiEOSOP格式说明.md 第三轮：未解格式收口 + FEOS 源码级核验 + 整体核查（r18）

**用户指令**：找出仍不能解析其存储格式/读取方法的 eosop 数据 → 再次全量搜索 `Multi1D++Portable20241128/` 思考语义（可联网辅助）→ 未解项写入文档 → 改完整体核查有无遗漏或错误。

**文档终态**：543,824 字符 / 806,357 字节 / 10,698 行 / **107,255 汉字**（GATE PASS）。较 r17 的 93,129 汉字增 14,126。

### 一、`.sesame` 权威记录序（决定性突破）
- **权威来源 = 本地手册 `doc/MULTI使用的SESAME数据文件格式.docx`（183,025 B，zipfile 读 word/document.xml 提取）**，手册明文给出记录骨架。
- 记录序 = 表头(4) | r[nr] | de[ne] | e0[nr] | P[ne*nr] | T[ne*nr]；尺寸 n = 4 + 2*nr + ne + 2*nr*ne。
- 排列方向：P[(0~nr-1)+nr*i] ⇒ **外层能量、内层密度，密度变化最快**。
- 字段：r=密度 g/cc；de=**能量增量网格**（非温度网格！）；e0=**冷能量**（尾块就是它，非"语义未定"）；P=Mbar；T=**Kelvin**。
- **7/7 样本 leftover=0 精确闭合**：Ta2O5(143)/Ta2O5_(300)/Au_2003POPHammerRosen(419)/eos_21(153,645, nr43 ne1765)/eos_22(130,892, 36/1792)/eos_23(407,099, 75/2695)/eos_24(363,828, 73/2474)。
- 三重数值印证：T 确为开尔文（Au max 3.66186e7 K = 3155.6 eV）；Au 的 P/rho 在固定能量下标严格恒定（i=0/15/30 得 7.84173e-06 / 5.36314e-03 / 644.791，6 个 rho 点全同）；e0 形态符合冷能量。

### 二、重大自我更正（第二版引入的错误）
- 第二版初稿把 `.sesame` 记录序错读为「表头, rho, T, A, B, tail」、两块数据定名 (E, P)、de 误称"温度网格"、尾块标"语义未定"。
- **根因：用形态学判据反推绝对顺序，且取错行**。**教训（规约 R15）：本地手册明文存在时，手册记录序优先于任何形态学判据**。
- 已在 §15.2.2–15.2.5 重写 + §15.12.3b 如实登记勘误。

### 三、FEOS 16.7 官方源码级核验（八问全解，[S-SRC] 新增溯源级）
源码包 `FEOS_package_v16.7` 解压至 `.workbuddy/tmp/vendor/FEOS_src/FEOS/`：Code/ 18 个 .C + 18 个 .H、Documents/FEOS-Package-Documentation.txt 99,338 B、EOS-Data/。
- **`.feos` 真实行宽 = 10x15 = 150**（非 Readme.txt 说的 4x15）。根因 FE-00_DEFINITS.H:28 的 `#define SF_TRENN ""`（德文 Trennungszeichen 分隔符被赋空串）⇒ 无分隔符定宽 token 流。参数行与数据行**同为 10 字段/行**，无差异；Al.feos 23,874 行全 150。
- **`.301/.304/.305` 双实物**：FEOS 16.7 原生 %15.8le = **4x15 = 60**；旧 MPQeos v2.0 = **4x16 = 64**（3 位指数 e+001）。实测 Al.feos.301 行宽直方图 {60:10002, 15:1}；Au.301 {64:9374, 16:1} ⇒ 解析器不得假设固定宽度，须"先按 15 切 4 段、溢出并回末段"。
- **`.mexport`**：write_mexport_format(FE-01_TABTOOLS.C:370)，SESAME mexport ASCII 单材料，**每行严格 80 = 5x15 数值 + 5 字符控制位**（解析必切 line[75:80]）。B.mexport 22,508 行全 80。
- **`.cst`（Rostock）**：write_Rostock_format(:883)，4 列空格分隔 —— Molekueldichte[1/cm3]=rho/(A_tot*mp) / Massendichte[g/cm3] / Druck[MBar]=P*1e-12 / Ladungszustand=Qtot；UTF-8 仅因表头德文 u 变音。
- **SHOWEOS 6 后缀**：SE-00_DEFINITS.H:29-33 → .ist(Isotherms)/.isc(Isochores)/.ise(Isentropes)/.mnt(Mountain)/.hug(Hugoniot)；单点（选项6）只到 stdout 不落盘(SE-04_MAIN.C:98-106)。**`*4gnuplot` 在源码+96KB文档 0 命中 ⇒ 非原生（外部后处理）**。.hug 6 列 = Rho/T/P/E/Us/Up。
- **`.par` 与 `Path=`**：COMMON-02_READFILE.C:129-169 自定义分区+key=value；**Path= 在 FEOS 16.7 源码 0 命中**（仅编译期硬编码 TF_TABLE_PATH/MATERIAL_DATABASE_PATH）⇒ 本机唯一 mat_He/Untitled.PAR 属**旧 MPQEOS v2.0 参数模式**。⇒ **目录里混着两代工具链**（与 .301 双实物同源）。
- **`.critical.dat`**：write_criticaldata(FE-01_TABTOOLS.C:58) **14 个分段**；`.isobaric.dat`(FE-02_CALCULATIONS.C:181) 首段 6 列 T[K]/rho/P[bar]/alpha/H/Cp。
- **单位常量**（COMMON-00_DEFINITS.H:56,62-67）：t_kelvin=8.617383848e-5 eV/K；cgs2ses_t=11604.5；cgs2ses_p=1e-10；cgs2ses_e=1e-10；cgs2ses_rho=1.0 ⇒ SESAME 301 单位 = **GPa / MJ*kg^-1 / Mg*m^-3 / K**。
- **`.feos` 20 字段逐字段对齐**：行0 = FileVersion, NRH, NT, Nelements+1, Tcalclimit, Rhocalclimit, RhoRef, TRef, BulkModulusRef, SESAMEnumber；行1 = ElectronOffset, IonOffset, Ecoh, softsphere_n, m, A, B, Atot, Ztot, Xtot。修正：NR=(*table).NRho-1 是"末下标"，写出的是**数组元素个数**（下标 vs 计数换算，非"强制补点"）。
- **TF 基座表**：FEOS_TF-Table_1197.dat = 93x44，单字段行=rho，6 字段行=T,Pe,Ee,Fe,Q,dPdT（cgs+T[eV]），Se 现场算不入文件。tabelle/tabelle1197.TFT **sha256 与其完全相同**（3d0c638c…）⇒ QEOS/QIP 的 Thomas-Fermi 基座。

### 四、新发现的活体陷阱
- hyades/qeos/qeos_392.dat.feos（142,553 B，行宽 75）+ hyades/sesame/eos_41.dat.feos（30,993 B，行宽 75）：**后缀误标 .feos，内容实为 Hyades 5x15**。名不副实样本 3→5 个。新增**内容侧复核伪码 C7**（§10.6.11）。
- **工程结论（附录 B 尾）**：扩展名给出"候选族"，内容给出"最终裁决"；二者冲突**内容优先 + 显式告警**。

### 五、本轮落盘编辑（8 批补丁）
1. patch_1006.py：新增 §10.6（13 子节，+17,232 字符），**8 条缺口全关闭**。
2. patch_appB.py：速查卡 B.1/B.3/B.4 更新 + 导航图加第15章。
3. patch_appB2.py：新增 B.16 .mexport / B.17 .cst / B.18 .critical.dat / B.19 ShowEOS 衍生与 4gnuplot / B.20 .sesame 变体 / B.21 名实不符清单（+4,144）。
4. patch_appF.py：F.1 加 FEOS 源码包清单；F.2 整节重写为"网络核验源与官方源码包"（T71 已核验 6 条 DOI + T72 待核验 15 条 + 两处关键裁决）；F.3 溯源表补 [S-SRC]/[S-IMG]（+2,886）。
5. patch_body.py：正文 16 处一致性修正（.feos 4x15→10x15、.301 4x16→双实物）。
6. patch_ch15.py：锚点表补 A35–A42；缺口 #11（FEOS 5 条全闭合）/ #12（4gnuplot 作者）。
7. patch_final.py：4 处收尾（血缘图 L514、分派顺序表 L1020、推荐路径 L6198、L9950 竖线转义）。
8. patch_reindex.py：表号归位 T59b–g→T65–T70、T64a/b→T71/T72，前置-2.4 编号说明更新。

### 六、整体核查结论（全部通过）
- 汉字 107,255 GATE PASS；代码围栏 **514 全配对**；表号声明 **44 个无重号**（缺口 32-36/64 均为声明过的未分配号位）；内部章节引用 28 个全部有对应标题；表格列数 **0 处真实不一致**（转义感知计数）；**第 0–15 章 + 附录 A–F 全部在位且顺序单调**；§10.5→§10.6→第11章 衔接正确。

### 七、工具链与坑
- .workbuddy/tmp/：patch_*.py（8 个补丁）、audit.py（转义感知审计）、final.txt / toc.txt / ch.txt / tbl.txt / seg.txt / appF.txt。
- **bash shim 无 coreutils**（dirname/cd/head/grep 全 exit 127）；且 **Bash 内联 python -c 含反引号/特殊字符会被 shim 二次解释**（本轮踩坑：整段记忆文本被当命令执行）⇒ **一律先 Write 脚本到 .workbuddy/tmp/ 再 python 执行**。
- 补丁脚本**断言失败即中止不写盘**，可安全重跑。
- old_string 锚点去重用**逐行定位 + 用该行自身前导空白重建**（避免缩进猜错）；表格列数审计须**先剥除转义竖线**再计数。
- **502 网络故障**（copilot.tencent.com ENOTFOUND）击落 rev-goldmine(4m39s) 与 rev-feos-src(3m10s)；FEOS 源码包已提前下载解压，改派 **rev-feos-src2（纯本地，禁联网）成功**（6m57s / 72,531 B → .workbuddy/tmp/feos_formats.md）。rev-goldmine 任务由主理人亲自完成。
- 备份：.bak(692,574 B) / .bak2(693,386 B) / .bak3(699,907 B)。
"""

with open(P, 'a', encoding='utf-8', newline='\n') as f:
    f.write(ADD)

print('APPENDED bytes =', len(ADD.encode('utf-8')), 'newsize =', os.path.getsize(P))
