# Multi1D++Portable20241128 补充说明与参考文献 —— 提取素材

## 提取方法与局限

- 纯文本文件：逐字节读入，按 `utf-8-sig → utf-8 → cp936 → latin-1` 顺序尝试解码，
  取第一个成功者；原文**全文照录**（未截断、未改述）。每个文件节内注明所用编码。
- README 类文件全量扫描（36 个命中），**逐个全文照录**，是各族数据的溯源依据。
- 参考文献 PDF：用 `pdfminer.six` 提取，**仅摘录**与「输入文件格式 / 数据表读取 / 单位 /
  频群结构 / EOS 与 opacity 接口」强相关的段落，附原书页码；未全文翻译。
- 本机 bash shim 缺 coreutils，全部用 Python 完成。输出 UTF-8 / LF。

---

# 第二批：补充说明与工具文档

## doc/FEOS/Info.txt (2475 B)

<!-- 编码: utf-8-sig -->

> ##################################################################
> ## FEOS_16.7
> ## SHOWEOS_16.7 
> ## Copyright (C) 2017  Dr. Steffen Faik
> ##################################################################
> 
> 
> ##################################################################
> ## LICENSING PROVISIONS
> ##################################################################
> 
> This program is free software: you can redistribute it and/or modify
> it under the terms of the GNU General Public License as published by
> the Free Software Foundation, either version 3 of the License, or
> (at your option) any later version.
> 
> This program is distributed in the hope that it will be useful,
> but WITHOUT ANY WARRANTY; without even the implied warranty of
> MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
> GNU General Public License for more details.
> 
> You should have received a copy of the GNU General Public License
> along with this program. If not, see http://www.gnu.org/licenses/.
> 
> 
> ##################################################################
> ## INFO
> ##################################################################
> 
> author of MPQEOS:      Andreas Kemp (modified by Annika Krenz, Rafael Ramis 
>                                      and Tommaso Vinci)
> author of FEOS:        Dr. Steffen Faik
> version:               16.7
> description:           equation-of-state table generation
>                        equation-of-state table visualization
> date of latest change: july 29 11:00:00 CEST 2016
> documentation:         Documents/FEOS-Package-Documentation.pdf
> 
> 
> ##################################################################
> ## CHANGELIST
> ##################################################################
> 
> MPQEOS -> FEOS: - calculation of homogeneous mixtures of elements added
>                 - TF cold curve can now be replaced with soft sphere function
>                 - new numerics for calculation of Maxwell construction added
>                 - EOS is now calculated within a library which provides
>                   a C/C++ and Fortran interface
> 
> 
> ##################################################################
> ## FILELIST
> ##################################################################
> 
> Code/*.C
> Code/*.H
> Code/libfeos.h
> Code/Makefile
> Documents/*.pdf
> Documents/Info.txt
> Documents/License.txt
> EOS-Data/*.par
> EOS-Data/*.dat
> 
> 
> ##################################################################
> ## eof.

## doc/FEOS/License.txt (28360 B)

<!-- 编码: latin-1 -->

> *[许可证全文 115 行，此处录前 20 行与后 10 行；全文与数据格式无关，略]*

> TERMS AND CONDITIONS
> 
> 0. Definitions. 
> This License refers to version 3 of the GNU General Public License.
> Copyright also means copyright-like laws that apply to other kinds of works, such as semiconductor masks.
> The Program refers to any copyrightable work licensed under this License. Each licensee is addressed as you. Licensees and recipients may be individuals or organizations.
> To modify a work means to copy from or adapt all or part of the work in a fashion requiring copyright permission, other than the making of an exact copy. The resulting work is called a modified version of the earlier work or a work based on the earlier work.
> A covered work means either the unmodified Program or a work based on the Program.
> To propagate a work means to do anything with it that, without permission, would make you directly or secondarily liable for infringement under applicable copyright law, except executing it on a computer or modifying a private copy. Propagation includes copying, distribution (with or without modification), making available to the public, and in some countries other activities as well.
> To convey a work means any kind of propagation that enables other parties to make or receive copies. Mere interaction with a user through a computer network, with no transfer of a copy, is not conveying.
> An interactive user interface displays Appropriate Legal Notices to the extent that it includes a convenient and prominently visible feature that (1) displays an appropriate copyright notice, and (2) tells the user that there is no warranty for the work (except to the extent that warranties are provided), that licensees may convey the work under this License, and how to view a copy of this License. If the interface presents a list of user commands or options, such as a menu, a prominent item in the list meets this criterion.
> 
> 1. Source Code. 
> The source code for a work means the preferred form of the work for making modifications to it. Object code means any non-source form of a work.
> A Standard Interface means an interface that either is an official standard defined by a recognized standards body, or, in the case of interfaces specified for a particular programming language, one that is widely used among developers working in that language.
> The System Libraries of an executable work include anything, other than the work as a whole, that (a) is included in the normal form of packaging a Major Component, but which is not part of that Major Component, and (b) serves only to enable use of the work with that Major Component, or to implement a Standard Interface for which an implementation is available to the public in source code form. A Major Component, in this context, means a major essential component (kernel, window system, and so on) of the specific operating system (if any) on which the executable work runs, or a compiler used to produce the work, or an object code interpreter used to run it.
> The Corresponding Source for a work in object code form means all the source code needed to generate, install, and (for an executable work) run the object code and to modify the work, including scripts to control those activities. However, it does not include the work's System Libraries, or general-purpose tools or generally available free programs which are used unmodified in performing those activities but which are not part of the work. For example, Corresponding Source includes interface definition files associated with source files for the work, and the source code for shared libraries and dynamically linked subprograms that the work is specifically designed to require, such as by intimate data communication or control flow between those subprograms and other parts of the work.
> The Corresponding Source need not include anything that users can regenerate automatically from other parts of the Corresponding Source.
> The Corresponding Source for a work in source code form is that same work.
> 
> ...
> 15. Disclaimer of Warranty. 
> THERE IS NO WARRANTY FOR THE PROGRAM, TO THE EXTENT PERMITTED BY APPLICABLE LAW. EXCEPT WHEN OTHERWISE STATED IN WRITING THE COPYRIGHT HOLDERS AND/OR OTHER PARTIES PROVIDE THE PROGRAM AS IS WITHOUT WARRANTY OF ANY KIND, EITHER EXPRESSED OR IMPLIED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE. THE ENTIRE RISK AS TO THE QUALITY AND PERFORMANCE OF THE PROGRAM IS WITH YOU. SHOULD THE PROGRAM PROVE DEFECTIVE, YOU ASSUME THE COST OF ALL NECESSARY SERVICING, REPAIR OR CORRECTION.
> 
> 16. Limitation of Liability. 
> IN NO EVENT UNLESS REQUIRED BY APPLICABLE LAW OR AGREED TO IN WRITING WILL ANY COPYRIGHT HOLDER, OR ANY OTHER PARTY WHO MODIFIES AND/OR CONVEYS THE PROGRAM AS PERMITTED ABOVE, BE LIABLE TO YOU FOR DAMAGES, INCLUDING ANY GENERAL, SPECIAL, INCIDENTAL OR CONSEQUENTIAL DAMAGES ARISING OUT OF THE USE OR INABILITY TO USE THE PROGRAM (INCLUDING BUT NOT LIMITED TO LOSS OF DATA OR DATA BEING RENDERED INACCURATE OR LOSSES SUSTAINED BY YOU OR THIRD PARTIES OR A FAILURE OF THE PROGRAM TO OPERATE WITH ANY OTHER PROGRAMS), EVEN IF SUCH HOLDER OR OTHER PARTY HAS BEEN ADVISED OF THE POSSIBILITY OF SUCH DAMAGES.
> 
> 17. Interpretation of Sections 15 and 16. 
> If the disclaimer of warranty and limitation of liability provided above cannot be given local legal effect according to their terms, reviewing courts shall apply local law that most closely approximates an absolute waiver of all civil liability in connection with the Program, unless a warranty or assumption of liability accompanies a copy of the Program in return for a fee.
> 
> END OF TERMS AND CONDITIONS

*说明：GNU GPL v3 完整许可证文本，与 EOS/opacity 数据格式无关，故仅节录。*

## doc/SNOP.MANUAL (6604 B)

<!-- 编码: utf-8-sig -->

> 1. GENERAL
> The physics that goes into the code is described in the paper by K.Eidmann,
> Laser and Particle Beams, vol. 12, no. 2, pp. 223-244 (1994). In case you use results of the SNOP code, please quote the reference given above.
> 
> The SNOP source code is in  the directory Snop/source. In order to install it
> on a IBM workstation, make this directory the working directory and use the 
> command 'make risc'. After a successful preprocessing and compilation of the 
> source code you will find an executable file called snoprisc in the directory
> Snop/Risc. The program reads the input (using fortan namelist input: daten) 
> from a file called SNOP.INPUT and produces two output files:
> SNOP.INHALT: Gives a list of all the input parameters and option that 
>               were chosen for the special run.
> SNOP.TAB:    Contains the tables in MULTI-format.
> 
> 2. INPUT DATA AND OPTIONS
> For each of the input parameters described here, an example of the namelist
> input command is given in paranthesis.
> 
>       NT      Number of temperatures 
>               (NT = 20)
>       NR      Number of densities
>               (NR = 20)
>       NG      Number of groups
>               (NG = 20)
>       NP      Number of photon energies
>               (NP = 3000)
>       The maximum numbers for NT,NR,NG and NP (NTM,NRM,NGM,NPM) are 
>       specified in the file v.risc that contains the parameter 
>       declaration. If higher values are needed, change the corresponding 
>       value in this file and recompile the code.
> 
>       Z       Nuclear charge of the element
>               (Z = 26.0)
>       RHO1    Lowest density (in g/cm**3) 
>               (RHO1 = 1.0E-6)
>       RHO2    Highest density (in g/cm**3)
>               (RHO2 = 100.0)
>       T1      Lowest temperature (in keV)
>               (T1 = 1.0E-3)
>       T2      Highest temperature (in keV)
>               (T2 = 100.0)
>       X1      Lowest photon energy (in keV)
>               (X1 = 1.0E-3)
>       X2      Highest photon energy (in keV)
>               (X2 = 10.0)
>       IGROUP  Index for definition of photon energy groups
>               (see subroutine gdef.fpre)
>               =0: user supplies group boundaries
>               =1: linear division using F1 and F0
>               =2: quadratic division using F1 and F0
>               =3: logarithmic division using F1 and F0
>               =4: standard division with 20 groups (1eV --> 5keV)
>               =5: grey approximation with 2 groups
>               (IGROUP = 0)
>       F0      Lowest photon energy for automatic division (in eV).
>               Only needed if IGROUP = [1-3]!
>               (F0 = 1.0)
>       F1      Highest photon energy for automatic division (in eV).
>               Only needed if IGROUP = [1-3]!
>               (F1 = 5000.0) 
>       FG(1)-       
>       FG(NG+1)Group boundaries (in eV) given by user if IGROUP = 0.
>               (FG(1)  = 1.0,10.0,50.0,100.0,150.0,
>                FG(6)  = 250.0,400.0,550.0,700.0,900.0,
>                FG(11) = 1200.0,1600.0,2000.0,2200.0,2400.0,
>                FG(16) = 2600.0,2800.0,3100.0,3500.0,4000.0,
>                FG(21) = 5000.0)
>       EQ      Specifies LTE or Non-LTE
>               =0.0: LTE
>               =1.0: Non-LTE
>               (EQ = 0.0)
>       IDEG    Switch for Thomas-Fermi ionization degree at high density
>               =0: use result of rate equations 
>               =1: use ionization degree according to Thomas-Fermi (Standard)
>               (IDEG = 1)
>       LINEPRO Specifies the line profile used in subroutine lw.f
>               =0: Lorentz profile (Standard)        
>               =1: Gauss profile
>               (LINEPRO = 0)
>       NBFSMEAR
>               =0: (Standard)
>               (NBFSMEAR =0)
>       DREK    Takes into account dielectronic recombination
>               =1.0  for Z < 10
>               =3.0  for 10 < Z < 40
>               =10.0 for 40 < Z
>               (DREK = 3.0)
>       XGRIEM 
>               =1: (Standard)
>               (XGRIEM = 1.0)
>       AV
>               =-3.0: (Standard)
>               (AV = -3.0)
>       FACT    Takes into account line smearing: 
>               line width =  FACT * (calculated line width)
>               =1.0      for Z < 10
>               =100.0  - 1000.0  for 10 < Z < 40
>               =1000.0 - 3000.0  for 40 < Z
>               Standard: 1000.0 for Z=79
>               (FACT = 300.0)
>       NSIGMA  Specifies the screenig constants that are used in the screened
>               hydrogenic model for energy levels
>               =0: Mayer's constants (Standard for Z<10)
>               =1: More's constants (Standard for Z>10) 
>               (NSIGMA = 1)
>       NPLA    Number of table for Planck group mean opacity table according
>               to SESAME 
>               (xxxx3nnn, xxxx: material-ID, nnn: specifies number of table)
>               Material     xxxx
>               Deuterium    5263
>               Beryllium    2020
>               Bor          7081
>               Carbon       7560
>               Aluminium    3712
>               Iron         2140
>               Gold         2700
>               (NPLA = 21403000)    
>       NROSS   Number of table for Rosseland group mean opacity table according
>               to SESAME
>               (xxx4nnn, xxxx: material-ID as for NPLA, nnn: specifies number 
>                of table)
>               (NROSS = 21404000)
>       NEPS    Number of table for group mean emissivity table according
>               to SESAME
>               (xxx5nnn, xxxx: material-ID as for NPLA, nnn: specifies number 
>                of table)
>               If LTE is chosen, this table is not necessary.
>               (NEPS = 21405000)
>       NZ      Number of table for mean ionization degree
>               (xxx2nnn, xxxx: material-ID as for NPLA, nnn: specifies number 
>                of table)
>               (NZ = 21402000)
> 
> 3. EXAMPLE
> 
>    &daten
>          NT = 20,
>          NR = 20,
>          NG = 20,
>          NP = 3000,
>          Z = 26.0,
>          RHO1 = 1.0E-6,
>          RHO2 = 100.0,
>          T1 = 1.0E-3,
>          T2 = 100.0,
>          X1 = 1.0E-3,
>          X2 = 10.0,
>          IGROUP = 0,
>          FG(1) = 1.0,10.0,50.0,100.0,150.0,
>          FG(6) = 250.0, 400.0,550.0,700.0,900.0,
>          FG(11) = 1200.0,1600.0,2000.0,2200.0,2400.0,
>          FG(16) = 2600.0,2800.0,3100.0,3500.0,4000.0,
>          FG(21) = 5000.0,
>          EQ = 0.0,
>          IDEG = 1,
>          LINEPRO = 0,
>          NBFSMEAR = 0,
>          DREK = -1.0,
>          XGRIEM = 1.0,
>          AV = -3.0,
>          FACT = 300.0,
>          NSIGMA = 1,
>          NPLA  = 21403000,
>          NROSS = 21404000,
>          NEPS  = 21405000,
>          NZ    = 21402000
>     /
>                                                                 
> 
> 
> 
> 
> 

## doc/Structure_of_ASCII_data_files.txt (82 B)

<!-- 编码: utf-8-sig -->

> 1	0	2	1	12
> 2	0	1
> 3	0	4
> 
> 1	1	3	2	2
> 2	1	2
> 3	1	5
> 
> 1	2	1	4	22
> 2	2	2
> 3	2	10

## matter++/Readme.txt (530 B)

<!-- 编码: cp936 -->

> material.base的修改规则
> 为同一material.base的修改，简单指定规则如下：
> Ramis等公布的材料，MID编号在100之前，之后用户添加的材料在10000之后。
> 
> 
> [Thermos]中没有EOS的
> Br
> 
> 添加参数时请注意：
> 文件名命名需要有如下的规则(不同格式有不同的单位转换)：
> 如果文件名和路径中有“hyades”，程序识别为hyades程序的文件
> 如果文件名和路径中有“.feos”，程序识别为FEOS程序文件，按照一行4个15字符的数字读入
> 如果文件名和路径中有“.301”或“.304”或“.305”，程序识别为MPQeos生成的每行4x16个字符
> 其他按照默认的SESAME数据库格式，每行4x15个字符。

## matter++/AtomicWeightTable.txt (21590 B)

<!-- 编码: utf-8-sig -->

> Isotope data from http://physics.nist.gov/cgi-bin/Compositions/stand_alone.pl
> Material     Z     Atomic weight         File handle
> h             1      1.00794             z01
> h1            1      1.00782503207       z01
> d             1      2.0141017778        z01
> t             1      3.0160492777        z01
> he            2      4.002602            z02
> he3           2      3.0160293191        z02
> he4           2      4.00260325415       z02
> li            3      6.941               z03
> li6           3      6.015122795         z03
> li7           3      7.01600455          z03
> be            4      9.012182            z04
> be9           4      9.0121822           z04
> b             5     10.811               z05
> b10           5     10.0129370           z05
> b11           5     11.0093054           z05
> c             6     12.0107              z06
> c12           6     12.0                 z06
> c13           6     13.0033548378        z06
> c14           6     14.003241989         z06
> n             7     14.0067              z07
> n14           7     14.0030740048        z07
> n15           7     15.0001088982        z07
> o             8     15.9994              z08
> o16           8     15.99491461956       z08
> o17           8     16.99913170          z08
> o18           8     17.9991610           z08
> f             9     18.9984032           z09
> f19           9     18.99840322          z09
> ne           10     20.1797              z10
> ne20         10     19.9924401754        z10
> ne21         10     20.99384668          z10
> ne22         10     21.991385114         z10
> na           11     22.98976928          z11
> na23         11     22.9897692809        z11
> mg           12     24.3050              z12
> mg24         12     23.985041700         z12
> mg25         12     24.98583692          z12
> mg26         12     25.982592929         z12
> al           13     26.9815386           z13
> al27         13     26.98153863          z13
> si           14     28.0855              z14
> si28         14     27.9769265325        z14
> si29         14     28.976494700         z14
> si30         14     29.97377017          z14
> p            15     30.973762            z15
> p31          15     30.97376163          z15
> s            16     32.065               z16
> s32          16     31.97207100          z16
> s33          16     32.97145876          z16
> s34          16     33.96786690          z16
> s36          16     35.96708076          z16
> cl           17     35.453               z17
> cl35         17     34.96885268          z17
> cl37         17     36.96590259          z17
> ar           18     39.948               z18
> ar36         18     35.967545106         z18
> ar38         18     37.9627324           z18
> ar40         18     39.9623831225        z18
> k            19     39.0983              z19
> k39          19     38.96370668          z19
> k40          19     39.96399848          z19
> k41          19     40.96182576          z19
> ca           20     40.078               z20
> ca40         20     39.96259098          z20
> ca42         20     41.95861801          z20
> ca43         20     42.9587666           z20
> ca44         20     43.9554818           z20
> ca46         20     45.9536926           z20
> ca48         20     47.952534            z20
> sc           21     44.955912            z21
> sc45         21     44.9559119           z21
> ti           22     47.867               z22
> ti46         22     45.9526316           z22
> ti47         22     46.9517631           z22
> ti48         22     47.9479463           z22
> ti49         22     48.9478700           z22
> ti50         22     49.9447912           z22
> v            23     50.9415              z23
> v50          23     49.9471585           z23
> v51          23     50.9439595           z23
> cr           24     51.9961              z24
> cr50         24     49.9460442           z24
> cr52         24     51.9405075           z24
> cr53         24     52.9406494           z24
> cr54         24     53.9388804           z24
> mn           25     54.938045            z25
> mn55         25     54.9380451           z25
> fe           26     55.845               z26
> fe54         26     53.9396105           z26
> fe56         26     55.9349375           z26
> fe57         26     56.9353940           z26
> fe58         26     57.9332756           z26
> co           27     58.933195            z27
> co59         27     58.9331950           z27
> ni           28     58.6934              z28
> ni58         28     57.9353429           z28
> ni60         28     59.9307864           z28
> ni61         28     60.9310560           z28
> ni62         28     61.9283451           z28
> ni64         28     63.9279660           z28
> cu           29     63.546               z29
> cu63         29     62.9295975           z29
> cu65         29     64.9277895           z29
> zn           30     65.38                z30
> zn64         30     63.9291422           z30
> zn66         30     65.9260334           z30
> zn67         30     66.9271273           z30
> zn68         30     67.9248442           z30
> zn70         30     69.9253193           z30
> ga           31     69.723               z31
> ga69         31     68.9255736           z31
> ga71         31     70.9247013           z31
> ge           32     72.64                z32
> ge70         32     69.9242474           z32
> ge72         32     71.9220758           z32
> ge73         32     72.9234589           z32
> ge74         32     73.9211778           z32
> ge76         32     75.9214026           z32
> as           33     74.92160             z33
> as75         33     74.9215965           z33
> se           34     78.96                z34
> se74         34     73.9224764           z34
> se76         34     75.9192136           z34
> se77         34     76.9199140           z34
> se78         34     77.9173091           z34
> se80         34     79.9165213           z34
> se82         34     81.9166994           z34
> br           35     79.904               z35
> br79         35     78.9183371           z35
> br81         35     80.9162906           z35
> kr           36     83.798               z36
> kr78         36     77.9203648           z36
> kr80         36     79.9163790           z36
> kr82         36     81.9134836           z36
> kr83         36     82.914136            z36
> kr84         36     83.911507            z36
> kr86         36     85.91061073          z36
> rb           37     85.4678              z37
> rb85         37     84.911789738         z37
> rb87         37     86.909180527         z37
> sr           38     87.62                z38
> sr84         38     83.913425            z38
> sr86         38     85.9092602           z38
> sr87         38     86.9088771           z38
> sr88         38     87.9056121           z38
> y            39     88.90585             z39
> y89          39     88.9058483           z39
> zr           40     91.224               z40
> zr90         40     89.9047044           z40
> zr91         40     90.9056458           z40
> zr92         40     91.9050408           z40
> zr94         40     93.9063152           z40
> zr96         40     95.9082734           z40
> nb           41     92.90638             z41
> nb93         41     92.9063781           z41
> mo           42     95.96                z42
> mo92         42     91.906811            z42
> mo94         42     93.9050883           z42
> mo95         42     94.9058421           z42
> mo96         42     95.9046795           z42
> mo97         42     96.9060215           z42
> mo98         42     97.9054082           z42
> mo100        42     99.907477            z42
> tc           43     98.0                 z43
> tc97         43     96.906365            z43
> tc98         43     97.907216            z43
> tc99         43     98.9062547           z43
> ru           44    101.07                z44
> ru96         44     95.907598            z44
> ru98         44     97.905287            z44
> ru99         44     98.9059393           z44
> ru100        44     99.9042195           z44
> ru101        44    100.9055821           z44
> ru102        44    101.9043493           z44
> ru104        44    103.905433            z44
> rh           45    102.90550             z45
> rh103        45    102.905504            z45
> pd           46    106.42                z46
> pd102        46    101.905609            z46
> pd104        46    103.904036            z46
> pd105        46    104.905085            z46
> pd106        46    105.903486            z46
> pd108        46    107.903892            z46
> pd110        46    109.905153            z46
> ag           47    107.8682              z47
> ag107        47    106.905097            z47
> ag109        47    108.904752            z47
> cd           48    112.411               z48
> cd106        48    105.906459            z48
> cd108        48    107.904184            z48
> cd110        48    109.9030021           z48
> cd111        48    110.9041781           z48
> cd112        48    111.9027578           z48
> cd113        48    112.9044017           z48
> cd114        48    113.9033585           z48
> cd116        48    115.904756            z48
> in           49    114.818               z49
> in113        49    112.904058            z49
> in115        49    114.903878            z49
> sn           50    118.710               z50
> sn112        50    111.904818            z50
> sn114        50    113.902779            z50
> sn115        50    114.903342            z50
> sn116        50    115.901741            z50
> sn117        50    116.902952            z50
> sn118        50    117.901603            z50
> sn119        50    118.903308            z50
> sn120        50    119.9021947           z50
> sn122        50    121.9034390           z50
> sn124        50    123.9052739           z50
> sb           51    121.760               z51
> sb121        51    120.9038157           z51
> sb123        51    122.9042140           z51
> te           52    127.60                z52
> te120        52    119.904020            z52
> te122        52    121.9030439           z52
> te123        52    122.9042700           z52
> te124        52    123.9028179           z52
> te125        52    124.9044307           z52
> te126        52    125.9033117           z52
> te128        52    127.9044631           z52
> te130        52    129.9062244           z52
> i            53    126.90447             z53
> i127         53    126.904473            z53
> xe           54    131.293               z54
> xe124        54    123.9058930           z54
> xe126        54    125.904274            z54
> xe128        54    127.9035313           z54
> xe129        54    128.9047794           z54
> xe130        54    129.9035080           z54
> xe131        54    130.9050824           z54
> xe132        54    131.9041535           z54
> xe134        54    133.9053945           z54
> xe136        54    135.907219            z54
> cs           55    132.9054519           z55
> cs133        55    132.905451933         z55
> ba           56    137.327               z56
> ba130        56    129.9063208           z56
> ba132        56    131.9050613           z56
> ba134        56    133.9045084           z56
> ba135        56    134.9056886           z56
> ba136        56    135.9045759           z56
> ba137        56    136.9058274           z56
> ba138        56    137.9052472           z56
> la           57    138.90547             z57
> la138        57    137.907112            z57
> la139        57    138.9063533           z57
> ce           58    140.116               z58
> ce136        58    135.907172            z58
> ce138        58    137.905991            z58
> ce140        58    139.9054387           z58
> ce142        58    141.909244            z58
> pr           59    140.90765             z59
> pr141        59    140.9076528           z59
> nd           60    144.242               z60
> nd142        60    141.9077233           z60
> nd143        60    142.9098143           z60
> nd144        60    143.9100873           z60
> nd145        60    144.9125736           z60
> nd146        60    145.9131169           z60
> nd148        60    147.916893            z60
> nd150        60    149.920891            z60
> pm           61    145.0                 z61
> pm145        61    144.912749            z61
> pm147        61    146.9151385           z61
> sm           62    150.36                z62
> sm144        62    143.911999            z62
> sm147        62    146.9148979           z62
> sm148        62    147.9148227           z62
> sm149        62    148.9171847           z62
> sm150        62    149.9172755           z62
> sm152        62    151.9197324           z62
> sm154        62    153.9222093           z62
> eu           63    151.964               z63
> eu151        63    150.9198502           z63
> eu153        63    152.9212303           z63
> gd           64    157.25                z64
> gd152        64    151.9197910           z64
> gd154        64    153.9208656           z64
> gd155        64    154.9226220           z64
> gd156        64    155.9221227           z64
> gd157        64    156.9239601           z64
> gd158        64    157.9241039           z64
> gd160        64    159.9270541           z64
> tb           65    158.92535             z65
> tb159        65    158.9253468           z65
> dy           66    162.500               z66
> dy156        66    155.924283            z66
> dy158        66    157.924409            z66
> dy160        66    159.9251975           z66
> dy161        66    160.9269334           z66
> dy162        66    161.9267984           z66
> dy163        66    162.9287312           z66
> dy164        66    163.9291748           z66
> ho           67    164.93032             z67
> ho165        67    164.9303221           z67
> er           68    167.259               z68
> er162        68    161.928778            z68
> er164        68    163.929200            z68
> er166        68    165.9302931           z68
> er167        68    166.9320482           z68
> er168        68    167.9323702           z68
> er170        68    169.9354643           z68
> tm           69    168.93421             z69
> tm169        69    168.9342133           z69
> yb           70    173.054               z70
> yb168        70    167.933897            z70
> yb170        70    169.9347618           z70
> yb171        70    170.9363258           z70
> yb172        70    171.9363815           z70
> yb173        70    172.9382108           z70
> yb174        70    173.9388621           z70
> yb176        70    175.9425717           z70
> lu           71    174.9668              z71
> lu175        71    174.9407718           z71
> lu176        71    175.9426863           z71
> hf           72    178.49                z72
> hf174        72    173.940046            z72
> hf176        72    175.9414086           z72
> hf177        72    176.9432207           z72
> hf178        72    177.9436988           z72
> hf179        72    178.9458161           z72
> hf180        72    179.9465500           z72
> ta           73    180.94788             z73
> ta180        73    179.9474648           z73
> ta181        73    180.9479958           z73
> w            74    183.84                z74
> w180         74    179.946704            z74
> w182         74    181.9482042           z74
> w183         74    182.9502230           z74
> w184         74    183.9509312           z74
> w186         74    185.9543641           z74
> re           75    186.207               z75
> re185        75    184.9529550           z75
> re187        75    186.9557531           z75
> os           76    190.23                z76
> os184        76    183.9524891           z76
> os186        76    185.9538382           z76
> os187        76    186.9557505           z76
> os188        76    187.9558382           z76
> os189        76    188.9581475           z76
> os190        76    189.9584470           z76
> os192        76    191.9614807           z76
> ir           77    192.217               z77
> ir191        77    190.9605940           z77
> ir193        77    192.9629264           z77
> pt           78    195.084               z78
> pt190        78    189.959932            z78
> pt192        78    191.9610380           z78
> pt194        78    193.9626803           z78
> pt195        78    194.9647911           z78
> pt196        78    195.9649515           z78
> pt198        78    197.967893            z78
> au           79    196.966569            z79
> au197        79    196.9665687           z79
> hg           80    200.59                z80
> hg196        80    195.965833            z80
> hg198        80    197.9667690           z80
> hg199        80    198.9682799           z80
> hg200        80    199.9683260           z80
> hg201        80    200.9703023           z80
> hg202        80    201.9706430           z80
> hg204        80    203.9734939           z80
> tl           81    204.3833              z81
> tl203        81    202.9723442           z81
> tl205        81    204.9744275           z81
> pb           82    207.2                 z82
> pb204        82    203.9730436           z82
> pb206        82    205.9744653           z82
> pb207        82    206.9758969           z82
> pb208        82    207.9766521           z82
> bi           83    208.98040             z83
> bi209        83    208.9803987           z83
> po           84    209.0                 z84
> po209        84    208.9824304           z84
> po210        84    209.9828737           z84
> at           85    210.0                 z85
> at210        85    209.987148            z85
> at211        85    210.9874963           z85
> rn           86    222.0                 z86
> rn211        86    210.990601            z86
> rn220        86    220.0113940           z86
> rn222        86    222.0175777           z86
> fr           87    223.0                 z87
> fr223        87    223.0197359           z87
> ra           88    226.0                 z88
> ra223        88    223.0185022           z88
> ra224        88    224.0202118           z88
> ra226        88    226.0254098           z88
> ra228        88    228.0310703           z88
> ac           89    227.0                 z89
> ac227        89    227.0277521           z89
> th           90    232.03806             z90
> th230        90    230.0331338           z90
> th232        90    232.0380553           z90
> pa           91    231.03588             z91
> pa231        91    231.0358840           z91
> u            92    238.02891             z92
> u233         92    233.0396352           z92
> u234         92    234.0409521           z92
> u235         92    235.0439299           z92
> u236         92    236.0455680           z92
> u238         92    238.0507882           z92
> np           93    237.0                 z93
> np236        93    236.046570            z93
> np237        93    237.0481734           z93
> pu           94    244.0                 z94
> pu238        94    238.0495599           z94
> pu239        94    239.0521634           z94
> pu240        94    240.0538135           z94
> pu241        94    241.0568515           z94
> pu242        94    242.0587426           z94
> pu244        94    244.064204            z94
> am           95    243.0                 z95
> am241        95    241.0568291           z95
> am243        95    243.0613811           z95
> cm           96    247.0                 z96
> cm243        96    243.0613891           z96
> cm244        96    244.0627526           z96
> cm245        96    245.0654912           z96
> cm246        96    246.0672237           z96
> cm247        96    247.070354            z96
> cm248        96    248.072349            z96
> bk           97    247.0                 z97
> bk247        97    247.070307            z97
> bk249        97    249.0749867           z97
> cf           98    251.0                 z98
> cf249        98    249.0748535           z98
> cf250        98    250.0764061           z98
> cf251        98    251.079587            z98
> cf252        98    252.081626            z98
> es           99    252.0                 z99
> es252        99    252.082980            z99
> fm          100    257.0                 z100
> fm257       100    257.095105            z100
> md          101    258.0                 z101
> md258       101    258.098431            z101
> md260       101    260.10365             z101
> no          102    259.0                 z102
> no259       102    259.10103             z102
> lr          103    262.0                 z103
> lr262       103    262.10963             z103
> rf          104    265.0                 z104
> rf265       104    265.11670             z104
> db          105    268.0                 z105
> db268       105    268.12545             z105
> sg          106    271.0                 z106
> sg271       106    271.13347             z106
> bh          107    272.0                 z107
> bh272       107    272.13803             z107
> hs          108    270.0                 z108
> hs270       108    270.13465             z108
> mt          109    276.0                 z109
> mt276       109    276.15116             z109
> ds          110    281.0                 z110
> ds281       110    281.16206             z110
> rg          111    280.0                 z111
> rg280       111    280.16447             z111
> cn          112    285.0                 z112
> cn285       112    285.17411             z112
> uut         113    284.0                 z113
> uut284      113    284.17808             z113
> uuq         114    289.0                 z114
> uuq289      114    289.18728             z114
> uup         115    288.0                 z115
> uup288      115    288.19249             z115
> uuh         116    293.0                 z116
> uuh293      116    293.0                 z116
> uus         117    292.0                 z117
> uus292      117    292.20755             z117
> uuo         116    294.0                 z118
> uuo294      116    294.0                 z118
> h2o          10     18.01528             h2o
> water        10     18.01528             h2o
> d2o          10     20.0276035556        d2o
> heavy_water  10     20.0276035556        d2o

## doc/muParser.txt (4073 B)

<!-- 编码: utf-8-sig -->

> muParser - fast math parser for C++
> -------------------------------------------------------------------------------------
> Features
> The following is a list of the features currently supported by the parser library. The primary objective is to keep it as extensible as possible whilst ensuring a maximum parsing speed. Extending the parser is mostly based on allowing a user to add custom callbacks, which require only an absolute minimum of code. For instance, you need exactly two lines of code to add a new function. But extending the parser may not be necessary at all since it comes with a powerful default implementation. Here is the (incomplete) list of features:
> 
> ----------------------------------------------------------------------------------------
> Overview
> Easy to use
> you need only a few lines of code to evaluate en expression.
> Extremely fast
> faster than similar commercial parsers
> User-defined operators
> binary operators
> postfix operators
> infix operators
> User-defined functions
> with a fixed number of up to five arguments
> with variable number of arguments
> with a single string argument (for database queries)
> User-defined constants.
> numeric constants
> string constants
> User-defined variables.
> unlimited in number
> definable at parser runtime by the parser
> assigning variables in terms of other variables is possible
> Custom value recognition callbacks
> support for binary and hex values.
> can be used to implement database queries
> Default implementation with many features
> 26 predefined functions.
> 15 predefined operators.
> Supports numerical differentiation with respect to a given variable.
> Assignment operator is supported
> Portability
> GNU Makefile included
> BCB Project files included
> MSVC 7.1 Project files for managed and unmanaged code
> ISO 14882 compliant code
> DLL version usable from every language able to use function exported in C-style
> Unit support
> Use postfix operators as unit multipliers (3m -> 0.003).
> 
> ----------------------------------------------------------------------------------------
> The default implementation
> This section gives an overview on the default features supported by the parser. The default implementation is defined in the class mu::Parser located in the file muParser.cpp. The DLL-version uses this class internally.
> 
> ----------------------------------------------------------------------------------------
> Built-in functions
> The following table gives an overview of the functions supported by the default implementation. It lists the function names, the number of arguments and a brief description.
> 
> Name	Argc.	Explanation
> sin	1	sine function
> cos	1	cosine function
> tan	1	tangens function
> asin	1	arcus sine function
> acos	1	arcus cosine function
> atan	1	arcus tangens function
> sinh	1	hyperbolic sine function
> cosh	1	hyperbolic cosine
> tanh	1	hyperbolic tangens function
> asinh	1	hyperbolic arcus sine function
> acosh	1	hyperbolic arcus tangens function
> atanh	1	hyperbolic arcus tangens function
> log2	1	logarithm to the base 2
> log10	1	logarithm to the base 10
> log	1	logarithm to the base 10
> ln	1	logarithm to base e (2.71828...)
> exp	1	e raised to the power of x
> sqrt	1	square root of a value
> sign	1	sign function, -1 if x<0; 1 if x>0
> rint	1	round to nearest integer
> abs	1	absolute value
> if	3	if ... then ... else ...
> min	var.	min of all arguments
> max	var.	max of all arguments
> sum	var.	sum of all arguments
> avg	var.	mean value of all arguments
> 
> ----------------------------------------------------------------------------------------
> Built-in binary operators
> The following table lists the default binary operators supported by the parser:
> 
> Operator	Meaning	Priority
> =	assignment*	-1
> and	logical AND	1
> or	logical OR	1
> xor	logical XOR	1
> <=	less or equal	2
> >=	greater or equal	2
> !=	not equal	2
> ==	equal	2
> >	greater than	2
> <	less than	2
> +	addition	3
> -	subtraction	3
> *	multiplication	4
> /	division	4
> ^	raise x to the power of y	5
> *The assignment operator is special since it changes one of its arguments and can only by applied to variables.

## doc/solution of unsymmetry/关于不对称.txt (1631 B)

<!-- 编码: cp936 -->

> 针对CH-Al-CH不对称的问题：
> 不对称问题主要为如下的几个变量：
> XC, X, V, TR
> 
> 其他变量对称条件下基本重合。
> 数据在solveImplicitly中得到的dvec中速度的变量不对称，密度温度能量的变量误差在1e-12可以忽略。
> 
> 速度的误差在 1e-7左右。其中靠近边缘的网格的误差最大，靠近中间的逐渐缩小到1e-20。
> 
> 主要集中在前5个网格其中
> 		state->v[0]+state->v[99] = 8.4239582065492868e-007
> 		state->v[5]+state->v[94] = -3.4582059438292845e-013
> 密度的误差较小
> 		rho_final[0]-rho_final[98]	6.0396132539608516e-013	double
> 		rho_final[1]-rho_final[97]	7.2386541205560206e-014	double
> 		rho_final[48]-rho_final[50]	1.7763568394002505e-015	double
> 		rho_final[49]			2.7000097312953821	double
> 
> 继续查找原因：
> 在solveImplicitly中，矩阵对角个数为5与向量vec的存储4倍不符(不是这里的问题！)
> 
> 问题出现在计算 state->x的时候使用了从i=0开始的递推。
> i=0  dx=(v_new+v_old)/2*dt
> 其他时刻使用 dx = m/rho
> 
> 如果统一使用 dx=(v_new+v_old)/2*dt，则结果完全对称。但是否会有其他不守恒的问题？(质量守恒？)
> 
> 但是这样会引入一定的误差。结果略有差异（请查看before/after.log）。还没有对算法进行详细的推导和分析。
> 
> 解决方法：先查找是否有静止不动的界面，如果有则从这个界面开始向两侧计算。对于Simple19.case计算通过，但是其他算例涉及到其他的不对称来源，结果仍然不对称。
> 
> 其他的不对称性来源为：
> 
>        double dvelocity[NMAX+1];        /* time derivative of velocity */  
>        {
>            dvelocity[0]=-area_per_mass[0]*pressure_total[0];
>            for(i=1;i<n;++i){
>               dvelocity[i]=area_per_mass[i]*(pressure_total[i-1]-pressure_total[i]);
>            }
>            dvelocity[n]=area_per_mass[n]*pressure_total[n-1];   // Unsymmetry
>        }
> 
> 
> 
> 

## doc/multi1d7.6/README (5619 B)

<!-- 编码: utf-8-sig -->

>                        
> 
>                           Code multi1d Version 7.6
>                           ========================
> 
> 
> 
>                                   MULTI       
> 
>      This is a developing version of the code MULTI. The code was originally
> writen in october-december of 1985 by R.Ramis at the Max-Planck-Institut fuer
> Quantenoptik at Garching (Germany). The code was published as "MULTI - A
> computer code for one-dimensional multigroup radiation hydrodynamics", by
> R.Ramis, R.Schmalz and J. Meyer-ter-Vehn, Comput. Phys. Commun. 49 (1988)
> 475-505, and is obtainable from: CPC Program Library, Queen's University of
> Belfast, N. Ireland. That version included the following physics:
>      - 1D planar lagrangian hydrodynamics (solved implicitelly) 
>      - one temperature tabulated equations of state (tables ussually generated
>        from SESAME library)
>      - heat flux transport, with a flux limiter
>      - multigroup transport with angular resolution, using tabulated opacities
>        and emissivities. (ussually taken from SNOP code, G.D.Tsakiris and 
>        K.Eidmann, J. Quant. Spectrosc. Radiat. Transfer 38, 353 (1987))
>      - Laser deposition by bremsstrahlung (+ a fraction of the laser power
>        arriving to the critical density)
>      - Time splitting was used to solve the system; the different proccesses
>        were applied succesivelly during a time step
> The code was run on a CRAY-XMP with COS operating system, a separated program
> P3D was used to produce 3D figures (variables plotted as a functions of time
> and lagrangian coordinate). The complete job (source files for multi and P3D,
> tables, and input files) have to be submited from a Siemens front end computer.
> The user received the output listing in its e-mail, and had to pick up the 
> plots in a Din A4 laser printer.  
> 
> 
> 
> 
>                                  MULTI6      
> 
> From 1985 to 1991 the program was improved in several aspects: new physics
> were included:
>      - Cylindrical and spherical 1-D geometries (at this point the angular
>        resolution was eliminated, instead, the forward-reverse aproximation 
>        was used)
>      - Two temperatures (ion and electron) equations of state (the ion
>        contribution was assumed to be an ideal gas, the electron contribution
>        was obtained substracting an ion contribution to the tabulated values)
>      - The mean ion number used for ions EOS, heat transport, and laser depo-
>        sition coefficients was also read (optionally) from tables.
>      - Fusion reactions (DT only), together with a model for alpha-particle
>        transport.
>      - Improved boundary condition for radiation: a source term formed by
>        a planckian thermal bath plus a user suplied data file (generated in
>        a previous job), can be coupled to the boundaries.
>      - Possibility to model 3D geometries (hohlraums with holes, and radiation
>        sources), by specifiing a radiation source/sink in an arbitrary
>        interface.
> Also improvement in the user interface were done:
>      - A code PXD able to produce either 3D surface plots, and 2D (a variable
>        versus time for a fixed lagrangian coordinate, or versus coordinate
>        for a fixed time, etc...), and combine several plots in a sheet.
>      - A code SUS, running in the front end computer, facilitates job submision 
>        by mean of a macro lenguage. Computations and graphics generation jobs
>        can be submitted independently.
>      - Plot metafiles can be previewed in a graphical terminal.
>      - The code runs on a CRAY-YMP with UNICOS (Unix) operating system. 
>      - Some documentation files were writen.
> The complete package was named MULTI6. At that moment the code was used by 
> several people, some of them created its own improved versions, in particular
> S. Hueller (now at LULI,France) created a version for femptosecond laser matter
> interaction including wave equation for the laser deposition, and appropriate
> transport coefficients. Other people (N. Murakami, T.Aoki) create/improved the
> post proccessors. From 1991 a code multi2d is being writen to solve radiation
> transportin two dimensions, its develoment is independent of the here described
> code that has been renamed multi1d.
> 
> 
> 
>                                multi1d-7.3
> 
>       During 1995 the code was adapted to run in Unix workstations giving
> place to the Version multi1d-7.3. In addition, some interactive graphic
> pre/postproccessors using a X-windows and OpenGL enviroment were developed,
> but they are not considered part of this package. They are about 1 order of
> magnitude more complex that multi1d ((in number of lines, and executable size).
> 
> 
> 
> 
>                                multi1d-7.4
> 
>       During 1996 The code was translated from fortran77 to C, the resulting
> version was called multi1d-7.4. It has essentially the same features as 
> multi1d-7.4. The main changes are:
>      - Thermal bath with variable temperature as boundary condition
>      - Table management through a index file: material.base
>      - Improved ion energy equation
> 
> 
> 
> 
>                                multi1d-7.6
> 
>       During 1997, a mayor change takes place the splitting of the code in
> two parts: the hydrodynamic code itself (multi1d-7.6), and a module 
> (matter-1.0) that manages all material properties (equation of state, transport
> coefficients, etc...). That module can be also used by other programs, and will
> be discused separatelly. The improvements introduced in 7.6 are 
>      - Posibility to start from tabulated initial conditions     
>      - Simple model for heavy-ion beam deposition
>      - Posibility of tabulated intensity for laser pulse
>    

## doc/multi1d7.6/examples (11588 B)

<!-- 编码: utf-8-sig -->

> 
> 
> 
>                        Examples for multi1d-7.6 code
>                        =============================
> 
> 
> All use one-group radiation transport, opacities are given from simple power
> laws. The cpu time is on a Silicon Graphics INDY R4600 PC at 133 MHz.
> 
> 
> 
> 
>                               simple1.case
>                               ============
> 
>       One sided expansion of a 10 microns aluminium slab. Initial density of
> 2.7 gr/cm3, 1eV electron temperature and 0.1eV ion temperature. Ideal gas 
> equation of state used. 
>       The electron pressure is about 1.16 MBars after ion-electron thermal
> equilibrium, the velocity is about 6.0e+5 cm/s (at x=10 microns, the initial
> matter boundary)
>       56 time steps and 0.57 seconds
> 
> 
> 
>                               simple2.case
>                               ============
> 
>       Shock tube with one open side. Composed by 1) rigid wall, 2) 10 microns
> Al at 2.7 g/cm3 and 1 eV (1.25 MBars), 3) 40 microns Al at 2.7 g/cm3 and 0.1 eV
> (0.125 MBars), 4) a free boundary. Ideal gas EOS is used.
>       The maximum density is about 6.8 g/cm3, the shock wave coming from the
> interface between materials collides with the rarefaction wave coming from the
> free boundary in 4ns.
>       40 time steps and 1.23 seconds
> 
> 
> 
>                               simple3.case
>                               ============
> 
>       Gold foil (10 microns at 19.2 g/cm3) irradiated by a 100 ev themal bath.
> Using ideal gas EOS.
>       After 1 ns 0.677 microns have been ablated, the shock wave has run 5.92
> microns, and the pressure reaches 4 Mbars.
>       246 time steps and 7.24 seconds.
> 
> 
> 
>                               simple4.case
>                               ============
> 
>       Spherical radiation driven ICF pellet composed of: 3.5 mm DT at 0.001
> g/cm3, 0.25mm DT at 0.225 g/cm3, 0.37mm C at 2.14 g/cm3. Irradiated by a 300 eV
> thermal bath. Ideal gas EOS used for both materials. Fusion reactions switched
> off.
>       The implosion takes 20 ns, absorbing 10.81 MJ. The typical implosion
> velocity is 3.2e+7 cm/s.
>       413 time steps and 12.49 seconds.
> 
> 
> 
>                               simple5.case
>                               ============
> 
>       C foil (0.05 mm, 1g/cm3), irradiated by a laser pulse (10e+14 W/cm2,
> 1 micron wavelenght, 500 ps rise time). Ideal gas EOS and a flux limiter of
> 0.03 have been used.
>       The shock wave reaches the inner side in 1.3 ns, after 20 ns the corona
> temperature is at 5250 eV, 68% of the mass has been ablated and the dense
> material has been accelerated to 4.78e+7 cm/s. The pressure changes from
> 13.4 to 4.28 Mbars.
>       466 time steps and 14.07 seconds.
> 
> 
> 
>                               simple6.case
>                               ============
> 
>       
>       Spherical radiation driven ICF pellet composed of: 2 mm DT at 0.0003
> g/cm3, 0.0864 mm DT at 0.22053 g/cm3, and 0.45 mm of C at 1.265 g/cm3. Sesame
> EOS, and fusion reaction allowed. The pelles is driven by a 350 eV thermal
> bath.
>       The maximum compression is reached after 8.6 ns. The yield is 26.03 MJ,
> absorbing 3.51 MJ.
>       563 time step and 18.04 seconds.
> 
> 
> 
>                               simple7.case
>                               ============
> 
>       
>       Gold foil 0.2 microns thick irradiated by a 100 ev thermal bath.
> Ideal EOS with 0.5 eV starting temperature, Multigroup opacity, with the same
> values for 24 groups.
>       Shock travelling time is 40 ps, burnthrough at 500 ps. The foil moves
> a distance of 0.0025 cm before burnthought. At 1 ns:
>                Incident flux   ~ 1.023e+13 W/cm2
>                Reflected flux  ~ 0.738e+13 W/cm2
>                Transmited flux ~ 0.235e+13 W/cm2
>                Absorbed energy ~ 2.666e+03 J/cm2
>                Kinetic energy  ~ 1.134e+03 J/cm2
>                Electrons Ei    ~ 1.475e+03 J/cm2
>                Ions Ei         ~ 0.022e+03 J/cm2
>       271 time steps and 42.74 seconds
> 
> 
> 
> 
>                               simple8.case
>                               ============
> 
> 
>       The same parameters as in simple7.case but ussing one group opacities
> Similar results (0.1% of difference)
>       716 time steps and 20.38 seconds
> 
> 
> 
> 
>                               simple9.case
>                               ============
> 
> 
>       The same parameters as in simple7.case and simple8.case. Now tabulates
> properties are used (SESAME+SNOP).
>       Shock run time      ~ 16 ps
>       Burn-through        ~ 40 ps
>       Space moved         ~ 0.00288 cm
>       Energy in ions      ~ 2.917e+08
>       Energy in electrons ~ 2.027e+10
>       Kinetic energy      ~ 1.181e+10
>       Radiated energy     ~ -3.278e+11
>       Incident flux       ~ 1.027e+20
>       Transmited flux     ~ 0.333e+20
>       Reflected flux      ~ 0.578e+20
>       232/243 time steps and 42.76 seconds 
> 
> 
> 
> 
>                              simple10.case
>                              =============
> 
> 
>       Hohlraum simulation. Internal wall: 0.5mm, 5 microns gold. External wall:
> 1mm, 2 microns gold. Filling: DT at 0.001 g/cm3. RInternal sphere irradiated
> with 1e15 W/cm2. 10% of radiation losses at R=0.8 mm. Simple models for
> materials.
>       664/672 time steps and 35.52 seconds
> 
> 
> 
> 
>                              simple11.case
>                              =============
> 
> 
>       C-Foil: 0.02 mm, 1g/cm3. Laser 1e14 W/cm2 (500ps risetime), 1 micron,
>       delta=0.5, 20 ns.
>       Shock run time       ~ 0.6 ns
>       Burn-through         ~ 9 ns
>       Transparent to laser ~ 13 ns
>       Tmax                 ~ 5653.02 eV
>       Pmax                 ~ 16 MBars
>       439/450 time steps and 8.39 seconds
> 
> 
> 
> 
>                              simple12.case
>                              =============
> 
> 
>       ICF implosion (DT+C) 50 Cells. D=0.14+0.01636+0.011823
>       Pulse: 90,120,160,220,250 eV in 17ns
>       Tign=18.88 ns
>       Input   3.01e12 (0.301 MJ)
>       Output  6.14e13 (6.140 MJ)
>       Gain    20.4
>       690/730 time steps and 21.68 seconds
> 
> 
> 
> 
>                              simple13.case
>                              =============
> 
> 
>       ICF implosion (DT+C) 50 Cells. D=0.14+0.01636+0.018187
>       Pulse: 90,120,160,220,280,287 eV in 20ns
>       Tign=21.47 ns
>       Input   5.1686e12
>       Output  1.13927e15 
>       Gain    220.4
>       880/918 time steps and 27.22 seconds
> 
> 
> 
> 
>                              simple14.case
>                              =============
> 
> 
>       ICF implosion (DT+C) 70 Cells. D=0.16+0.02412+0.031174
>       Pulse: 90,120,150,180,210,250,320 eV in 31.2ns
>       Tign=34 ns
>       Input   1.22084e13
>       Output  3.11585e15
>       Gain    255.2
>       1064/1097 time steps and 45.02 seconds
> 
> 
> 
> 
>                              simple15.case
>                              =============
> 
>       ICF implosion (DT+C) 70 Cells. D=0.16+0.02412+0.031174
>       Pulse: 90->320 eV (smooth) in 31ns
>       Tign=34.28 ns
>       Input   1.40886e13
>       Output  3.33668e15
>       Gain    236.84
>       1058/1087 time steps and 44.70 seconds
> 
> 
> 
> 
>                              simple16.case
>                              =============
> 
>       Experiment: 10 microns mylar + 0.8 microns Al
>       7.215e15 W/cm2, 480 ps FWHM, 438 nm
>       Shock time 296 ps
>       Burn time 455 ps
>       Max T= 2163.04 (ele.), 1244.76 (ions), 201.168 (rad.)
>       Max P= 63.756 MBar
>       672/677 time steps and 25.53 seconds
> 
> 
> 
> 
>                              simple17.case
>                              =============
> 
>       Gold wall 10 microns thick submitted to the NIF radiation pulse
>       WorkOp-II:94 based opacity, 80 cells
>       Shock time 3.7 ns
>       Burn time 17.5 ns
>       Max P= 41.4722 MBar
>       1093/1108 time steps and 50.33 seconds
> 
> 
> 
> 
> 
>                              simple18.case
>                              =============
> 
> 
>       C-wall 50 microns, irradiated by 1e14 W/cm2, 20 ns, Nd laser
>       Shock time 1.22 ns
>       34 microns ablated 
>       P=18.5947 Mbars
>       Te=5178.48 eV
>       Ti=2701.52 eV
>       Tr=71.1551 eV
>       466/476 time steps and 14.11 seconds
> 
> 
> 
> 
>                              simple19.case
>                              =============
> 
>       Non uniform initial conditions (read from file simple19.data)
>       Planar DT semi-layer: d=0.2 cm, Te=Ti=5000eV 
>       Rho varies from 0 (center) to 2 g/cm3 (surface)
>       Te reaches 7760.01 eV
>       Fusion=297.44 MJ
>       55/55 timesteps and 0.77 seconds
> 
> 
> 
> 
>                             simple20.case
>                             =============  
> 
> 
>       Gold converter study for NIF like targets
>       AU semi-layer d/2=32.5 microns
>       Irradiated by NIF Tr nominal pulse (300eV)
>       Ion-Beam deposition with range 0.125 (whole thickness)
>       10.3132 MJ/cm2 with time law ~ Tr**4
>       For the semi-layer at end of pulse:
>           5.1561 MJ/cm2 of ion energy input
>           2.73   MJ/cm2 of radiation input
>           4.74   MJ/cm2 of radiation output
>           2.64   MJ/cm2 of electron internal energy
>           0.021  MJ/cm2 of ion internal energy
>           0.4    MJ/cm2 of kinetic energy
>       249/250 timesteps and 7.71 seconds
> 
> 
> 
> 
>                             simple21.case
>                             =============  
> 
> 
>       Aluminium converter study for NIF like targets
>       Al semi-layer d/2=231.5 microns
>       Irradiated by NIF Tr nominal pulse (300eV)
>       Ion-Beam deposition with range 0.125 (whole thickness)
>       10.0855 MJ/cm2 with time law ~ Tr**4
>       For the semi-layer at end of pulse:
>           5.0432 MJ/cm2 of ion energy input
>           2.7628 MJ/cm2 of radiation input
>           4.52   MJ/cm2 of radiation output
>           2.2856 MJ/cm2 of electron internal energy
>           0.125  MJ/cm2 of ion internal energy
>           0.76   MJ/cm2 of kinetic energy
>       248/255 timesteps and 7.90 seconds
> 
> 
> 
> 
>                             simple22.case
>                             =============  
> 
> 
>       Carbon converter study for NIF like targets
>       Al semi-layer d/2=0.0625 cm
>       Irradiated by NIF Tr nominal pulse (300eV)
>       Ion-Beam deposition with range 0.125 (whole thickness)
>       10.3460 MJ/cm2 with time law ~ Tr**4
>       For the semi-layer at end of pulse:
>           5.173  MJ/cm2 of ion energy input
>           2.751  MJ/cm2 of radiation input
>           4.35   MJ/cm2 of radiation output
>           2.4898 MJ/cm2 of electron internal energy
>           0.28   MJ/cm2 of ion internal energy
>           0.702  MJ/cm2 of kinetic energy
>       236/240 timesteps and 7.37 seconds
> 
> 
> 
> 
>                             simple23.case
>                             =============  
> 
> 
>       Be converter study for NIF like targets
>       Be-foam  semi-layer d/2=0.168 cm / rho=0.375
>       Irradiated by NIF Tr nominal pulse (300eV)
>       Ion-Beam deposition with range 0.125 (whole thickness)
>       10.3502 MJ/cm2 with time law ~ Tr**4
>       For the semi-layer at end of pulse:
>           5.175  MJ/cm2 of ion energy input
>           2.751  MJ/cm2 of radiation input
>           5.30   MJ/cm2 of radiation output
>           1.89   MJ/cm2 of electron internal energy
>           0.395  MJ/cm2 of ion internal energy
>           0.275  MJ/cm2 of kinetic energy
>       238/243 timesteps and 7.60 seconds
> 
> 
> 
> 
>                             simple24.case
>                             =============
> 
> 
>       Simulation of NIF CH-capsule driven by 300 eV radiation
>            Vimp=387 km/s
>            Absorbed energy=141.419 KJ
>            Fusion energy=14.9848 MJ
>       1199/1214 timesteps and 64.39 seconds
> 
> 
> 
> 
>                             simple25.case
>                             =============
> 
> 
>       Simulation of NIF Be-capsule driven by 250 eV radiation
>            Vimp=324 km/s
>            Absorbed energy=153.726 KJ
>            Fusion energy=16.1121 MJ
>       980/1012 timesteps and 41.50 seconds

## doc/multi1d7.6/history (3874 B)

<!-- 编码: utf-8-sig -->

> Thu Feb  2 14:59:42 MET 1995
> 
> Development of a unix version of multi 1D
> 
>    - segregated main program
>    - segregated routine schritt
>    - segregated routine group
>    - segregated routine radia
> 
> Fri Feb  3 10:14:49 MET 1995
> 
>    - segregated routines quelle
>    - segregated routines hydro
>    - eliminated the use of namelist input
>    - program running in single precission only
> 
> Mon Feb  6 12:33:59 MET 1995
> 
>    - program running in double preccission
> 
> Tue Feb  7 18:57:53 MET 1995
> 
>    - segregated routines soutin and sogen
> 
> Wed Feb  8 19:28:25 MET 1995
> 
>    - all input is through unit 12
>    - comments are allowed, scattered in the input data
>    - blancks are ignored
>    - all alphanumeric output on standard output
> 
> Tue Feb 21 18:33:00 MET 1995
> 
>    - implemented some test cases
>    - simple tables for Al,Au,C, and DT
> 
> Wed Feb 22 17:37:18 MET 1995
> 
>    - first post-proccessor for X-windows
> 
> Tue Jan  9 16:52:27 MET 1996
> 
>    - more sophisticated pre/post-proccessor for X-windows/OpenGL
>    - release version 7.3
> 
> Thu Jan 11 16:46:38 MET 1996
> 
>    - created version 7.4
>    - 3423 fortran lines
>    - first statements coded in C
> 
> 
> Wed Jan 31 13:36:26 MET 1996
> 
>    - The structure of pre/postprocessing has been simplified
>          i) m1dpre (m1d_env-1.1) is an editor of input data
>         ii) m1dpp2 (m1d_env-1.1) allows for all sort of plots:
>             - 2d plot with time or cell/interface number as parameters
>             - 3d plots of variables as function of time, and celli, lagrangian
>               co-ordiante or frequency.
>             - minimum and maximum value of any variable
>        iii) codes Plot2D (X11) and gl9 (OpenGL) are called by ii) to display
>             the figures.
> 
> Thu Jan 11 16:46:38 MET 1996 - 3423 fortran lines /    0 C lines
> Fri Jan 12 10:58:10 MET 1996 - 3222 fortran lines /  210 C lines
> Wed Jan 31 17:47:31 MET 1996 - 2994 fortran lines /  296 C lines
> Thu Feb  1 16:20:41 MET 1996 - 2708 fortran lines /  499 C lines
> Fri Feb  2 18:43:01 MET 1996 - 2717 fortran lines /  966 C lines
> Tue Feb 20 11:58:59 MET 1996 - 2717 fortran lines / 1220 C lines
> Tue Feb 20 17:20:08 MET 1996 - 2348 fortran lines / 1285 C lines
> Thu Feb 22 18:49:40 MET 1996 - 1934 fortran lines / 1913 C lines
> Fri Feb 23 17:30:00 MET 1996 - 1808 fortran lines / 1968 C lines
> Mon Mar 11 17:46:03 MET 1996 - 1497 fortran lines / 2129 C lines
> Tue Mar 12 13:18:24 MET 1996 - 1429 fortran lines / 2272 C lines
> Tue Mar 12 17:43:29 MET 1996 - 1380 fortran lines / 2381 C lines
> Thu Mar 14 13:25:07 MET 1996 - 1269 fortran lines / 2630 C lines
> Fri Mar 15 14:03:27 MET 1996 - 1189 fortran lines / 2791 C lines
> Fri Mar 15 17:23:37 MET 1996 - 1105 fortran lines / 2989 C lines
> Mon Apr  1 13:19:18 MDT 1996 -  985 fortran lines / 3187 C lines
> Mon Apr  1 19:03:42 MDT 1996 -  889 fortran lines / 3436 C lines
> Tue Apr  2 14:14:10 MDT 1996 -  773 fortran lines / 3635 C lines
> Tue Apr  2 18:39:24 MDT 1996 -  674 fortran lines / 3804 C lines
> Tue Apr 23 13:12:44 MDT 1996 -  516 fortran lines / 4091 C lines
> Wed Apr 24 11:24:48 MDT 1996 -  518 fortran lines / 4145 C lines
> Mon Nov 18 16:57:35 MET 1996 -  477 fortran lines / 4298 C lines
> Tue Nov 19 18:36:26 MET 1996 -  277 fortran lines / 4590 C lines
> Wed Nov 20 17:46:59 MET 1996 -  219 fortran lines / 4830 C lines
> Thu Nov 21 18:53:30 MET 1996 -    0 fortran lines / 5207 C lines
> 
> Fri Nov 22 18:14:25 MET 1996
> 
>    Released version 7.4
> 
> Thu Apr 10 16:47:34 MDT 1997
> 
>    Splitting: multi1d-7.4 ---> multi1d-7.6 + matter-1.0
> 
> Mon May 12 16:43:05 MDT 1997
> 
>    - Heavy-ion beam deposition routine
>    - Tabulated laser/ion beam time laws
>    - Possibility of arbitary profiles as initial condition
>    - 4386 C lines
> 
> Wed Oct 15 13:07:24 MET 1997
> 
>    - 4262 C lines
> 
> Fri Oct 17 12:43:26 MET 1997
> 
>    - 4090 C lines
> 
> Wed Oct 22 17:03:58 MET 1997
> 
>    - 4130 C lines
>    - Released matter-1.0
> 
> Thu Oct 23 15:36:34 MET 1997
> 
>    - Releaded multi1d-7.6

## doc/multi1d7.6/manual (13797 B)

<!-- 编码: utf-8-sig -->

>                               multi1d-7.6
>                               ===========
> 
> 
> 
> 
>                                 Modules
> 
> 
>    The present package ("multi1d-7.6") is just a piece of the complete multi
> system. The whole  thingh has been  divided in unities  called "modules" (or
> "r94-modules").  A module is  an archive  file  whose contents will never be
> changed. Typically are  copied from  a remote  ftp-server  into  the   local
> directory $HOME/archive.  To upgrade the system, only new modules have to be
> transfered  and installed. The modules have to be installed. This is done by
> unconpressing  the  archive,  extracting  all  files  in  a  new  directory, 
> executing the  makefile, and updating the file $HOME/.s96_base that contains
> a table of installed modules-names and  associated directories. This task is
> done usually by the procedures in module "start-2.1". This is done typically
> by the command:  "s96 -i <module_name>".  To get  information  about a given
> module, install the module and look for README or INFO files.
> 
> 
> 
> 
> 
>                                 Overview
> 
> 
>    The code solves the 1-D dimensional gas-dynamics of a plasma, coupled
> with radiation transport, heat diffusion, nuclear reactions (fusion), and
> laser or ion beam heating. It uses the fractional step method: during a time
> step, the above physical proccesses are applied in sequence. This method
> maximizes the flexibility and modularization of the code, and allows the
> discusion of each module separatelly.
>    The computational field is divided in N subregions called "cells", the
> border of cells are called "interfaces". There are N-1 internal interfaces
> shared by two cells, and 2 boundary interfaces, in total N+1 interfaces.
> Some of the variables (typically fluxes and vectorial quantities) are defined
> at interfaces, while others (typically specific quantities and scalars) are
> defined at cells.
>    At each time the simulation status is specified in data in a structure
> of type "hydro_state" (structure definition are given in file "multi.h"). This 
> information includes the type of geometry (planar, cylindrical or spherical),
> the number of cells, the current value of time, number of DT cells, and the
> state variables:
>    ts  -  an integer specifiing the thermodynamic state (see module
>           "matter-1.0" for details), that is density, and specific electron
>           and ion energies. Other quantiies, i.e. electron temperature are
>           evaluated in function of these. All these quantities are defined
>           at cells.
>    dm  -  mass of cells
>    x,v -  coordinates and velocities at interfaces
>    f   -  molar fraction of tritium (<0.5) at cells (0 for no DT cells)
>    ea  -  density of energy in flying alpha particles at cells
> By other hand, a structure of type "control", contains numerical parameters:
> number of frequency intervals for radiation transport, type of boundary
> condition, flux limit factor for electrons, maximum number of time steps, ...
>    The code starts reading control data from file "FT12" ("read_control()"),
> initializing the hydro state from a layered structure ("hydro_layers()") or
> user specified profile ("hydro_profile()"), and initializing auxiliary
> structures used to store energy balances ("ene_test") and radiation quantities
> ("radiation_field").  Then the main loop is entered until either the final
> time or the maximum number of step is reached. Periodically binary data
> is written into file "fort.10". 
>    The routine "schritt()" performs the time step. Each step is divided
> in a certain number of substeps (subcycling), in each of them the following
> main actions are carried:
>    i) obtain deposition of energy by laser ("quelle()") or ion beams
>       ("ionbeam()").
>   ii) Advance nuclear reactions ("fusion_()"), that is, solve rate equation
>       to determine new fuel fraction, solve transport equation for alpha
>       particles, upgrading its energy density, and finally compute energy
>       deposition on electron and ions.
>  iii) The energy deposition comming from i) and ii) is divided in fractions
>       ("wa[i]") to be coupled to the different proceses that follow.
>   iv) Advance simultaneously hydrodynamics, heat transport, and ion-electron
>       energy interchange ("hydro()"). The equations are solved implicitly.
>       Routine "leicht()" computes numerically the system jacobian by calling
>       several times "abltng()" with slightly different values, and solves it
>       by calling LINPACK based routines "sgbfa()" and "sgbsl()".
>   iv) Compute radiation transport for a subset of groups. For each group 
>       the routine "group()" is called to advances electron temperatures.
> These routines need some additional data (radiation boundary conditions, 
> laser power as a function of time, ion beam range, ....) that are also
> read from file "FT12", the first time they are called. In addition to the 
> mechanism described, some auxiliar routines are called to conditionate
> radiation output data ("rflux_()"), keep track of energy conservation 
> ("enetest2()"), compute new energy fractions from temperature changes in the
> last timestep ("wctrl_()"), and other secondary things.
> 
> 
> 
> 
>                                Input data
> 
> The run specification is read from file FT12, this is a ASCII file composed
> of sections. Each section is composed by a head line containing a keyword and
> specification lines. Each specification has the form <name> "=" <value>,
> optionally followed by a comment ("#" + text)
> 
> Section &CONTROL
> 
>    FLAG      -  If 0 default values are used
>    NSPLIT    -  Number of hydro substeps (must be a divisor of the number
>                 of radiation groups)
>    TEXIT     -  Time to be run
>    NEXIT     -  Maximum number of time steps
>    DTN       -  Initial time step, maximum time step
>    DTO       -  Binary output time step
>    VARNOM    -  Alloved relative variation in each time step (0.2 recomended)
>    WALLLEFT  -  If 1, rigid left boundary
>    WALLRIGHT -  If 1, rigid right boundary (inactive in multi1d-7.6)
>    FLF       -  Flux limit factor (0.03 recomended)
> 
> Section &LAYERS is optional
> 
>    FLAG       -  If 1 this section is active 
>    IGEO       -  Geometry: 1-Planar, 2-Cylindrical, 3-Spherical
>    XMIN       -  Initial minimum value of X  
>    NFUEL      -  Number of cells with active DT fuel
>    NC(1)      -  Number of cells of layer 1
>    MID(1)     -  Material code of layer 1 (see module "matter-1.0")
>    THICK(1)   -  Thickness in cm of layer 1
>    RHO(1)     -  Initial density (gr/cm3) of layer 1
>    TE(1)      -  Initial electron temperature (eV) of layer 1
>    TI(1)      -  Initial electron temperature (eV) of layer 1
>    ZONPAR(1)  -  Relation between consecutive cell thicknesses of layer 1
>    NC(2)      -  \
>    MID(2)     -  |
>    THICK(2)   -  |
>    RHO(2)     -  |
>    TE(2)      -  |
>    TI(2)      -  |-- Parameters for additional layers
>    ZONPAR(2)  -  |
>    NC(3)      -  |
>    MID(3)     -  |
>    THICK(3)   -  |
>    .......    .  .
> 
> Section &PROFILE is optional
> 
>    FLAG       -  enable initial profile from data file
>    IGEO       -  geometry type (1-planar,2-cylindrical,3-spherical)
>    NFUEL      -  number of cells with active dt fuel
>    FILE       -  ASCII file with tabulated data:
>                  line 1   : "MSanchez"  (magic number)
>                  line 2   : x(1) v(1) mid(1) rho(1) te(1) ti(1)
>                  line 3   : x(2) v(2) mid(2) rho(2) te(2) ti(2)
>                             ............
>                  line N+1 : x(N) v(N) mid(N) rho(N) te(N) ti(N)
>                  line N+2 : x(N+1) v(N+1)
> 
> 
> Section &RBOUND
> 
>    ALPHAL     -   Fraction of radiation reflected at left boundary
>    ALPHAR     -   Fraction of radiation reflected at right boundary
>    BETAL      -   Fraction of 'FLUX' coupled to the left boundary
>    BETAR      -   Fraction of 'FLUX' coupled to the right boundary
>    GAB        -   Fraction of S+ that goes throught ltre
>    GBA        -   Fraction of S- that goes throught ltre
>    GOA        -   Fraction of 'FLUX' coupled to S- in ltre
>    GOB        -   Fraction of 'FLUX' coupled to S+ in ltre
>    LTR        -   If not zero, ltre=LTR
>    XTR        -   If LTR=0, ltre is such than x(ltre)-XTR is minimum
> 
> Section &RSOURCE is optional, if no present  FLUX=0 all the times
> 
>    TIME(0)    -   Time value
>    T(0)       -   Radiation temperature that define FLUX at TIME(0)
>    TIME(1)    -   Time value (if less than TIME(0) end of this table)
>    T(1)       -   Radiation temperature that define FLUX at TIME(0)
>    ....
>    TIME(19)   -   Time value
>    T(19)      -   Radiation temperature
>  
> Section &PULSE is optional, if not present no laser deposition takes place
> 
>    FLAG       -   Enable/disable laser deposition
>    INTER      -   The laser enters the layer from this interface number (if
>                   positive from right hand side, if negative from left hand
>                   side)
>    PIMAX      -   Maximum power (in erg/s.cm2, erg/s.cm, or erg/s)
>    PITIME     -   Pulse time (sec)
>    WL         -   Laser wavelenght (cm)
>    DELTA      -   Fraction of laser flux dumped at the critical density
>    ITYPE      -   1:sin**2 pulse, 2: use a tabulated pulse
>    TIME(0)    -   | if ITYPE==2, use linear interpolation in a table defined
>    I(0)       -   | by TIME(i)*PITIME and I(i)*PIMAX values
>    ....       . 
>  
> Section &IONBEAM is optional, if not present no ion-beam deposition takes place
> 
>    FLAG       -   Enable/disable ionbeam deposition
>    PIMAX      -   Maximum power (in erg/s.cm2, erg/s.cm, or erg/s)
>    PITIME     -   Pulse time (sec)
>    RANGE      -   Ion range in gr/cm2
>    EXPO       -   The ion power is PIMAX*I(time/PITIME)**EXPO
>    TIME(0)    -   This table define the pulse form by linear interpolation
>    I(0)       -   I(t), the number of points is arbitrary
>    ....       . 
> 
> 
> 
>                                Output data
> 
> The code writes data into binary file "fort.10". The format of file is divided
> in "records", each record is formed by several bytes ("data"), preceded and
> followed by an integer indicating its number.  The structure is:
> 
> record    data
> 
> 1         integer(4 bytes) indicating the number of words in records 2 and 3
> 2         each word is a 8 character string with the name of one variable,
>           for arrays the name appears several times
> 3         each word is a double precission number with the value of the 
>           variable named above (static values)
> 4         integer(4 bytes) indicating the number of words in next records
> 5         each word is a 8 character string with the name of one variable,
>           for arrays the name appears several times
> 6         each word is a double precission number with the value of the 
>           variable named above (at some time)
> more      like 6 but for a different value of time
> 
> The actual stored values are (N=number of cells):
> 
> In record 3 :
> 
> CMC     N        Mass coordinate at center of cells (*)
> NC      N        Cell number
> CMI     N+1      Mass coordiante at interfaces (*)
> NI      N+1      Interface number
> FREC    NG       Central frequency of groups (ev)
> FREI    NG+1     Boundary frequencies (ev)
> 
> In records 6,7,8,...:
> 
> TIME    1        Time (sec)
> ISTEP   1        Number of time step
> ENLAS   1        Incident laser energy (**)
> ENQUE   1        Absorbed laser energy (**)
> ENIE    1        Electron internal energy (**)
> ENII    1        Ion internal energy (**)
> ENKI    1        Kinetic energy (**)
> ENRAD   1        =ENRL1+ENRL2+ENRL3+ENRL4-ENRG1-ENRG1-ENRG2-ENRG3-ENRG4
> ENRL1   1        Radiated energy (left boundary) (**)
> ENRL2   1        Radiated energy (internal boundary left side) (**)
> ENRL3   1        Radiated energy (internal boundary right side) (**)
> ENRL4   1        Radiated energy (right boundary) (**)
> ENRG1   1        Absorbed energy (left boundary) (**)
> ENRG2   1        Absorbed energy (internal boundary left side) (**)
> ENRG3   1        Absorbed energy (internal boundary right side) (**)
> ENRG4   1        Absorbed energy (right boundary) (**)
> EALFA   1        Energy in alpha particles (**)
> ENAL    1        Energy lost by alpha particles flux on right side (**)
> ENGA    1        Fusion energy dumped in alpha particles (**) (1/5 total)
> EYIELD  1        Number of neutrons
> R       N        Density (gr/cm3)
> T       N        Electron temperature (ev)
> P       N        Electron pressure (dynes/cm2)
> ZI      N        Effective ion number
> XC      N        Position of center of cells (cm)
> D       N        Laser deposition (per mass unit) (erg/s.gr)
> DENE    N        Electron number density (1/cm3)
> EA      N        Alfa energy (dynes/cm2)
> F       N        Fraction of deuterium (or tritium)
> TI      N        Ion temperature (ev)
> PT      N        Total pressure (dynes/cm2) (electrons+ion+alfas)
> X       N+1      Position of interfaces (cm)
> V       N+1      Velocity of interfaces (cm/sec)
> S+      N+1      Radiation flux in positive direction
> S-      N+1      Radiation flux in negative direction
> S       N+1      Total radiation flux (S+ - S-)
> TR      N+1      Radiation temperature
> I-Left  NG       Spectrum (Erg/sec/eV) on left boundary
> I-Right NG       Spectrum (Erg/sec/eV) on right boundary
> 
> (*) (gr/cm2, gr/cm, or gr)
> (**) (erg/cm2, erg/cm, or erg)
> 
> 
> 
>                          Running the program
> 
> To run the code one needs:
>    - install the module "start-2.1" (reffer to this module README)
>    - install the code (type: s96 -i multi1d-7.6) the code is automatically
>      build
>    - select an example file (see file "examples")
>    - copy file into FT12 (type for example: cp simple1.case FT12)
>    - execute the code (type: multi)
>    - binary data is now in FT12
>    - to dysplay graphically the date reffer to module "m1d_env-1.2"
> 
> 
> 
>                               Checking 
> 
> The procedure check (type for example: check 1) runs the code with data
> simple1.case, and compares part of the results with data in file check.1.

---

# 第二批附：全部 README / Readme / .readme 文件（逐个全文照录）

*这些文件是各族数据的溯源说明，逐字照录。*

## doc/FEOS/Info.txt (2475 B)

<!-- 编码: utf-8-sig -->

> ##################################################################
> ## FEOS_16.7
> ## SHOWEOS_16.7 
> ## Copyright (C) 2017  Dr. Steffen Faik
> ##################################################################
> 
> 
> ##################################################################
> ## LICENSING PROVISIONS
> ##################################################################
> 
> This program is free software: you can redistribute it and/or modify
> it under the terms of the GNU General Public License as published by
> the Free Software Foundation, either version 3 of the License, or
> (at your option) any later version.
> 
> This program is distributed in the hope that it will be useful,
> but WITHOUT ANY WARRANTY; without even the implied warranty of
> MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
> GNU General Public License for more details.
> 
> You should have received a copy of the GNU General Public License
> along with this program. If not, see http://www.gnu.org/licenses/.
> 
> 
> ##################################################################
> ## INFO
> ##################################################################
> 
> author of MPQEOS:      Andreas Kemp (modified by Annika Krenz, Rafael Ramis 
>                                      and Tommaso Vinci)
> author of FEOS:        Dr. Steffen Faik
> version:               16.7
> description:           equation-of-state table generation
>                        equation-of-state table visualization
> date of latest change: july 29 11:00:00 CEST 2016
> documentation:         Documents/FEOS-Package-Documentation.pdf
> 
> 
> ##################################################################
> ## CHANGELIST
> ##################################################################
> 
> MPQEOS -> FEOS: - calculation of homogeneous mixtures of elements added
>                 - TF cold curve can now be replaced with soft sphere function
>                 - new numerics for calculation of Maxwell construction added
>                 - EOS is now calculated within a library which provides
>                   a C/C++ and Fortran interface
> 
> 
> ##################################################################
> ## FILELIST
> ##################################################################
> 
> Code/*.C
> Code/*.H
> Code/libfeos.h
> Code/Makefile
> Documents/*.pdf
> Documents/Info.txt
> Documents/License.txt
> EOS-Data/*.par
> EOS-Data/*.dat
> 
> 
> ##################################################################
> ## eof.

## doc/multi1d7.6/README (5619 B)

<!-- 编码: utf-8-sig -->

>                        
> 
>                           Code multi1d Version 7.6
>                           ========================
> 
> 
> 
>                                   MULTI       
> 
>      This is a developing version of the code MULTI. The code was originally
> writen in october-december of 1985 by R.Ramis at the Max-Planck-Institut fuer
> Quantenoptik at Garching (Germany). The code was published as "MULTI - A
> computer code for one-dimensional multigroup radiation hydrodynamics", by
> R.Ramis, R.Schmalz and J. Meyer-ter-Vehn, Comput. Phys. Commun. 49 (1988)
> 475-505, and is obtainable from: CPC Program Library, Queen's University of
> Belfast, N. Ireland. That version included the following physics:
>      - 1D planar lagrangian hydrodynamics (solved implicitelly) 
>      - one temperature tabulated equations of state (tables ussually generated
>        from SESAME library)
>      - heat flux transport, with a flux limiter
>      - multigroup transport with angular resolution, using tabulated opacities
>        and emissivities. (ussually taken from SNOP code, G.D.Tsakiris and 
>        K.Eidmann, J. Quant. Spectrosc. Radiat. Transfer 38, 353 (1987))
>      - Laser deposition by bremsstrahlung (+ a fraction of the laser power
>        arriving to the critical density)
>      - Time splitting was used to solve the system; the different proccesses
>        were applied succesivelly during a time step
> The code was run on a CRAY-XMP with COS operating system, a separated program
> P3D was used to produce 3D figures (variables plotted as a functions of time
> and lagrangian coordinate). The complete job (source files for multi and P3D,
> tables, and input files) have to be submited from a Siemens front end computer.
> The user received the output listing in its e-mail, and had to pick up the 
> plots in a Din A4 laser printer.  
> 
> 
> 
> 
>                                  MULTI6      
> 
> From 1985 to 1991 the program was improved in several aspects: new physics
> were included:
>      - Cylindrical and spherical 1-D geometries (at this point the angular
>        resolution was eliminated, instead, the forward-reverse aproximation 
>        was used)
>      - Two temperatures (ion and electron) equations of state (the ion
>        contribution was assumed to be an ideal gas, the electron contribution
>        was obtained substracting an ion contribution to the tabulated values)
>      - The mean ion number used for ions EOS, heat transport, and laser depo-
>        sition coefficients was also read (optionally) from tables.
>      - Fusion reactions (DT only), together with a model for alpha-particle
>        transport.
>      - Improved boundary condition for radiation: a source term formed by
>        a planckian thermal bath plus a user suplied data file (generated in
>        a previous job), can be coupled to the boundaries.
>      - Possibility to model 3D geometries (hohlraums with holes, and radiation
>        sources), by specifiing a radiation source/sink in an arbitrary
>        interface.
> Also improvement in the user interface were done:
>      - A code PXD able to produce either 3D surface plots, and 2D (a variable
>        versus time for a fixed lagrangian coordinate, or versus coordinate
>        for a fixed time, etc...), and combine several plots in a sheet.
>      - A code SUS, running in the front end computer, facilitates job submision 
>        by mean of a macro lenguage. Computations and graphics generation jobs
>        can be submitted independently.
>      - Plot metafiles can be previewed in a graphical terminal.
>      - The code runs on a CRAY-YMP with UNICOS (Unix) operating system. 
>      - Some documentation files were writen.
> The complete package was named MULTI6. At that moment the code was used by 
> several people, some of them created its own improved versions, in particular
> S. Hueller (now at LULI,France) created a version for femptosecond laser matter
> interaction including wave equation for the laser deposition, and appropriate
> transport coefficients. Other people (N. Murakami, T.Aoki) create/improved the
> post proccessors. From 1991 a code multi2d is being writen to solve radiation
> transportin two dimensions, its develoment is independent of the here described
> code that has been renamed multi1d.
> 
> 
> 
>                                multi1d-7.3
> 
>       During 1995 the code was adapted to run in Unix workstations giving
> place to the Version multi1d-7.3. In addition, some interactive graphic
> pre/postproccessors using a X-windows and OpenGL enviroment were developed,
> but they are not considered part of this package. They are about 1 order of
> magnitude more complex that multi1d ((in number of lines, and executable size).
> 
> 
> 
> 
>                                multi1d-7.4
> 
>       During 1996 The code was translated from fortran77 to C, the resulting
> version was called multi1d-7.4. It has essentially the same features as 
> multi1d-7.4. The main changes are:
>      - Thermal bath with variable temperature as boundary condition
>      - Table management through a index file: material.base
>      - Improved ion energy equation
> 
> 
> 
> 
>                                multi1d-7.6
> 
>       During 1997, a mayor change takes place the splitting of the code in
> two parts: the hydrodynamic code itself (multi1d-7.6), and a module 
> (matter-1.0) that manages all material properties (equation of state, transport
> coefficients, etc...). That module can be also used by other programs, and will
> be discused separatelly. The improvements introduced in 7.6 are 
>      - Posibility to start from tabulated initial conditions     
>      - Simple model for heavy-ion beam deposition
>      - Posibility of tabulated intensity for laser pulse
>    

## matlab/Backlighter/Readme.txt (34 B)

<!-- 编码: utf-8-sig -->

> ImageProcessing\ImplosionAsymmetry

## matlab/PostProcess/CrystalSpectrometer/Readme.txt (39 B)

<!-- 编码: utf-8-sig -->

> E:\Programming\#Codes\Opacity9\Cl_lines

## matter++/HeatCapacity/Readme.txt (91 B)

<!-- 编码: utf-8-sig -->

> Electron-Phonon Coupling and Electron Heat Capacity in Metals at High Electron Temperatures

## matter++/mat_Al-1.0/README (617 B)

<!-- 编码: utf-8-sig -->

> Tables for Aluminium 
> ====================
> 
> AL_IDEAL_GAS
>     Eos as an ideal gas with Z=12, A=27 and GAMMA=5/3
> 
> AL_SIMPLE_PLANCK
>     Rosseland opacity (cm): 8.7e-09 * T^2.5 / rho^1.5
>     (Taken from M.Murakami, J.Meyer-ter-Vehn, and R.Ramis. Journal of
>     X-Ray science and technology 2,127-148 (1990))
> 
> AL_SIMPLE_ROSSELAND
>     Planck    opacity (cm): 1.8e-09 * T^2.4 / rho^1.5
>     (Taken from M.Murakami, J.Meyer-ter-Vehn, and R.Ramis. Journal of
>     X-Ray science and technology 2,127-148 (1990))
> 
> AL_eos
>     Probably a SESAME table
> AL_LV.INV.data
>    copied from doc-multi3d_2009
>    
> Al.feos
> 	Calculate from FEOS
> 

## matter++/mat_Au-1.0/README (1221 B)

<!-- 编码: utf-8-sig -->

> Gold properties
> ===============
> 
> 
> AU_IDEAL_GAS
>    EOS as ideal gas with Z=19.998,A=197 and GAMMA=1.2168
> 
> AU_eos
>    EOS from SESAME library (probably)
> 
> AU_eosd
>    EOS from SESAME library (probably)
> 
> AU_SIMPLE_PLANCK
>    Planck    opacity (cm): 3.0e-07 * T^1.2 / rho^1.2
>    (Taken from M.Murakami, J.Meyer-ter-Vehn, and R.Ramis. Journal of
>    X-Ray science and technology 2,127-148 (1990))
> 
> AU_SIMPLE_PLANCK_MG
>    Like AU_SIMPLE_PLANCK but with 24 groups in frequency with the same
>    opacity
> 
> AU_SIMPLE_ROSSELAND
>    Planck opacity (cm): 3.0e-07 * T^1.2 / rho^1.2
>    (Taken from M.Murakami, J.Meyer-ter-Vehn, and R.Ramis. Journal of
>    X-Ray science and technology 2,127-148 (1990))
> 
> AU_WorkOp_Ross
>    WorkOp-III:94 Opacities.  Third International Opacity Workshop & Code
>    Comparison Study MPI fuer Quantenoptik, Garching, March 7-11, 1994,
>    Final Report
> 
> AU_info
>    Information about the parameters used by SNOP See G.D.Tsakiris
>    and K.Eidmann, J.Quant.Spectosc.Radiat.Transfer 38,353(1987)).
> 
> AU_op03e
>    Multigroup NON-LTE factor computed by SNOP
> 
> AU_op03p
>    Multigroup Planck opacity computed by SNOP
> 
> AU_op03r
>    Multigroup Rosseland  opacity computed by SNOP
> 
> AU_op03z
>    Z-effective table (unknown procedence)

## matter++/mat_Au/Au_Rosseland_2003POPHammerRosen.readme (90 B)

<!-- 编码: utf-8-sig -->

> Opacity generated by power law l = c * T^a*rho^b, with
> c: 1.38889e-007
> a: 1.5
> b: -1.2

## matter++/mat_Ba/Ba_Planck_1987JQSRT.readme (94 B)

<!-- 编码: utf-8-sig -->

> Opacity generated by power law l = c * T^a*rho^b, with
> c: 3.60912e-008
> a: 1.644
> b: -1.244

## matter++/mat_Ba/Ba_Rosseland_1987JQSRT.readme (94 B)

<!-- 编码: utf-8-sig -->

> Opacity generated by power law l = c * T^a*rho^b, with
> c: 1.70882e-007
> a: 1.619
> b: -1.142

## matter++/mat_Ba/Readme.txt (403 B)

<!-- 编码: utf-8-sig -->

> Ba_1987JQSRT_Planck/Rosseland
> REM Opacity parameters from MPQ174 _Ramisrecor, 1987JQSRT38(Tsakiris&Eidmann)
> REM Obtained by fitting power laws to SNOP computations(Tsakiris).
> REM k = a*T^s*rho^r (k in cm2/g, T in keV, rho in g/cm3)
> REM k = a*1000^-s*T^s*rho^r (k in cm2/g, T in eV, rho in g/cm3)
> REM expression valid for temperatures between 30eV to 1KeV and 
> REM density between 0.1g/cc to 10g/cc

## matter++/mat_Be-1.0/README (510 B)

<!-- 编码: utf-8-sig -->

> Tables for berilium
> ===================
> 
> BE_eos
>    Probably taken from SESAME library
> 
> BE_SIMPLE_PLANCK
>    Computed from Ya.B.Zel'dovich and Yu.P.Raizer. Physics of Shock Waves and Hight-
>    Temperature Hydrodynamic Phenomena. Academic Press,New York and London
>    (1966). Page 260, formulas 5.23 and 5.24.
> 
> BE_PLANCKx03
>    Same as BE_SIMPLE_PLANCK, but multiplied by a 0.3
> 
> opbe
>    Generated by SNOP in 1997. Must be divided in Planck, Rosseland, ... before used
> 
> oobe.inhalt
>    Some documentation about opbe

## matter++/mat_C-1.0/README (654 B)

<!-- 编码: utf-8-sig -->

> Tables for carbon
> =================
> 
> C_IDEAL_GAS
>    Ideal EOS using Z=6, A=12, and GAMMA=5/3
> 
> C_EOS
>    Probably taken from SESAME library
> 
> C_SIMPLE_PLANCK
>    Planck    opacity (cm): 1.0e-12 * T^4.0 / rho^2.0
>    (Taken from M.Murakami, J.Meyer-ter-Vehn, and R.Ramis. Journal of
>    X-Ray science and technology 2,127-148 (1990))
> 
> C_SIMPLE_ROSSELAND
>    Rosseland opacity (cm): 1.0e-12 * T^4.0 / rho^2.0
>    (Taken from M.Murakami, J.Meyer-ter-Vehn, and R.Ramis. Journal of
>    X-Ray science and technology 2,127-148 (1990))
> CH_ieos
> C_1G.PLANCK
> C.ZEFF
>    copied from doc-multi3d_2009
>    
> C_Planck.dat
> C_Rosseland.dat
> C_Z.dat
>    Li Liling generated from Thermos

## matter++/mat_CELIA/C.ZEFF.readme (223 B)

<!-- 编码: utf-8-sig -->

> 20170425:
> Orginal C.ZEFF with Te in eV. Changed to keV. C.ZEFF, Carbon.zeff, C_20GSNOP.ZEFF are idential. Preserved for compatibility with older database version. 
> All C.ZEFF are replaced with Carbon.zeff in material.base

## matter++/mat_CELIA/Readme.txt (92 B)

<!-- 编码: utf-8-sig -->

> C.ZEFF_old, Te in eV, replace by Carbon.Zeff
> D.ZEFF_old, Te in eV, replace by Deutrium.Zeff

## matter++/mat_DT-1.0/README (715 B)

<!-- 编码: utf-8-sig -->

> Tables for deuterium-tritium mixture
> ====================================
> 
> DT_IDEAL_GAS
>    Ideal gas EOS using Z=1,A=1.5, and GAMMA=5/3
> 
> DT_EOS
>    Probably taken from SESAME library
> 
> DT_SIMPLE_PLANCK
>    Planck    opacity (cm): 4.5e-10 * T^3.5 / rho^2.0
>    From Ya.B.Zel'dovich and Yu.P.Raizer. Physics of Shock Waves and Hight-
>    Temperature Hydrodynamic Phenomena. Academic Press,New York and London
>    (1966). Page 260, formulas 5.23 and 5.24.
> 
> DT_SIMPLE_ROSSELAND
>    Rosseland opacity (cm): 1.4e-08 * T^3.5 / rho^2.0
>    From Ya.B.Zel'dovich and Yu.P.Raizer. Physics of Shock Waves and Hight-
>    Temperature Hydrodynamic Phenomena. Academic Press,New York and London
>    (1966). Page 260, formulas 5.23 and 5.24.

## matter++/mat_Eu/Eu_Planck_1987JQSRT.readme (94 B)

<!-- 编码: utf-8-sig -->

> Opacity generated by power law l = c * T^a*rho^b, with
> c: 5.95806e-008
> a: 1.536
> b: -1.238

## matter++/mat_Eu/Eu_Rosseland_1987JQSRT.readme (93 B)

<!-- 编码: utf-8-sig -->

> Opacity generated by power law l = c * T^a*rho^b, with
> c: 3.45463e-007
> a: 1.45
> b: -1.094

## matter++/mat_Ge/Ge_Planck_1999Minguez.readme (94 B)

<!-- 编码: utf-8-sig -->

> Opacity generated by power law l = c * T^a*rho^b, with
> c: 8.09516e-009
> a: 2.025
> b: -1.413

## matter++/mat_Ge/Ge_Rosseland_1999Minguez.readme (93 B)

<!-- 编码: utf-8-sig -->

> Opacity generated by power law l = c * T^a*rho^b, with
> c: 1.55467e-009
> a: 2.598
> b: -1.58

## matter++/mat_Ge/Readme.txt (939 B)

<!-- 编码: utf-8-sig -->

> Ge_2002FED_Planck & Ge_2002FED_Rosseland
> REM from Analytical opacity formulas for ICF elements,Fusion Engineering and Design 60(2002) 17-25
> REM equation k=e^a*T^b*rho^c
> REM where e=2.71828, T in eV, rho in g/cc, k in cm2/g
> REM Constants a, b, and c are fitted by means of the following  procedure:  
> REM First, opacity data (Rosseland or Planck) are determined by JIMENA or ANALOP codes 
> REM  at several plasma conditions (temperature and density), corresponding to the ranges aforementioned.
> REM Then, these values are used in a standard statistical program, that finally provides a, b and c, 
> REM  giving also the standard error of estimate (S_R) and the adjusted squared multiple (R^2).
> REM The average of adjusted square multiple for all cases (R^2) is 0.979 and the standard error of estimate (S R ) is 0.645.
> REM Valid range: temperatures from 50  to  10^4 eV  and  
> REM              densities from  10^-3 to  10^3 g/cm3 .

## matter++/mat_Sn/Sn_Planck_1987JQSRT.readme (94 B)

<!-- 编码: utf-8-sig -->

> Opacity generated by power law l = c * T^a*rho^b, with
> c: 5.24082e-008
> a: 1.588
> b: -1.228

## matter++/mat_Sn/Sn_Rosseland_1987JQSRT.readme (92 B)

<!-- 编码: utf-8-sig -->

> Opacity generated by power law l = c * T^a*rho^b, with
> c: 2.6824e-007
> a: 1.571
> b: -1.16

## matter++/mat_Ti/readme.txt (133 B)

<!-- 编码: utf-8-sig -->

> [SNOP from Zhang Jiyan]
> Ti_eos
> Ti_EPS
> Ti_Ross
> Ti_Plank
> [SNOP run by Song Tianming Ti_LTE/_NLTE.INPUT]
> SNOP_LTE.*
> SNOP_NLTE.*

## matter++/PROPACEOS/Readme.txt (120 B)

<!-- 编码: cp936 -->

> 此文件格式为版权保护，没有找到相关格式说明文件。
> FLASH圈的格式转化软件opacplot2有相关代码，但是由于许可证问题没有公开。

## matter++/RadiativeCoolingRates/readme.txt (429 B)

<!-- 编码: utf-8-sig -->

> Ref: 1977ADNDT20.397(Post)_Steady-state radiative cooling rates for low-density, high-temperature plasmas
> Check this paper for more information
> 
> Original data file: Post_dat.txt
> User can add new/Replace fit data into RadiativeCoolingRates.dat, the code will load first item that matches.
> 
> Other Radiative cooling function fits:
> for H,D,He,Li
> Ref: 2011MNRAS415(Coppola)_Radiative cooling functions for primordial molecules

## matter++/Readme.txt (530 B)

<!-- 编码: cp936 -->

> material.base的修改规则
> 为同一material.base的修改，简单指定规则如下：
> Ramis等公布的材料，MID编号在100之前，之后用户添加的材料在10000之后。
> 
> 
> [Thermos]中没有EOS的
> Br
> 
> 添加参数时请注意：
> 文件名命名需要有如下的规则(不同格式有不同的单位转换)：
> 如果文件名和路径中有“hyades”，程序识别为hyades程序的文件
> 如果文件名和路径中有“.feos”，程序识别为FEOS程序文件，按照一行4个15字符的数字读入
> 如果文件名和路径中有“.301”或“.304”或“.305”，程序识别为MPQeos生成的每行4x16个字符
> 其他按照默认的SESAME数据库格式，每行4x15个字符。

## matter++/Ta2O5/Ta2O5_mop.readme (343 B)

<!-- 编码: utf-8-sig -->

> MATERIAL MID110873
> REM generated by Li Liling @20220422
> REM 96G opacity, Planck opacity use Rosseland opacity
> REM EOS, specific energy e~T^1.3285
> 
>    A 63.13
>    Z 26.57
>    Formula Ta2O5
>    Name Ta2O5
>    RHO 1
>    T 0.0253
> REM   EOS        Ta2O5   Ta2O5_EOS.hyades
>    PLANCK     Ta2O5   Ta2O5_mopp
>    ROSSELAND  Ta2O5   Ta2O5_mopr

## matter++/Thermos/Readme.txt (576 B)

<!-- 编码: cp936 -->

> Opacity data generated using opadata.exe which based on Thermos
> Multigroup opacity calculated OpaDataRunner coded by Song Tianming
> 
> ___________________________________________________________________________
> Following elements No EOS, use ideal gas by default
> Br
> Dy
> Gd
> Sm
> B
> Co
> F
> H
> K
> Mn 数据错误无法计算Opacity
> N
> Na
> P
> Pd
> S
> Sc
> ___________________________________________________________________________
> * 离化度文件的说明
> *_Z.dat 文件温度单位为eV
> *_Zeff.dat 文件温度单位为keV
> 程序中使用的单位为keV，新版程序修改后，使用*_Zeff.dat文件。 *_Z.dat文件作废。

## tabelle/readme.txt (357 B)

<!-- 编码: utf-8-sig -->

>   for( i = 1; i<=NR; i++ ) {
>     fprintf( h, "%.15e\n", (*table).rho[i] );
>     for( j = 1; j<=NT; j++ ) 
>       fprintf(h,"%.15e  %.15e  %.15e  %.15e  %.15e  %.15e\n",
> 	      (*table).Te[j],
> 	      (*table).Pe[i][j] ,
> 	      (*table).Ee[i][j], 
> 	      (*table).Fe[i][j],
> 	      (*table).Q[i][j],
> 	      (*table).dPdT[i][j] );
> 	      }
> 
> rho
> Te	Pe	Ee	Fe	Q	dPdT

## templates/color/readme.txt (305 B)

<!-- 编码: utf-8-sig -->

> To add a new user defined color-tables, use the following format
> #first line MUST be commented with #, only digits are allowed.
> #R	G	B 
> 0	0	0
> ...
> 255	255	255
> 
> 
> * save to file with extension *.dat
> * current data from
>    ct**.dat from IDL
>    other from https://github.com/NeutrinoToolkit/Neutrino

## templates/data/readme.txt (180 B)

<!-- 编码: cp936 -->

> Templates for output data files
> Name and Explanation separated with Tab。
> Stored in fusion.template are those fusion related variables that will be hidden if fusion is disabled. 

## tools/npp/plugins/doc/NppFTP/Readme.txt (5231 B)

<!-- 编码: utf-8-sig -->

> NppFTP Readme:
> 
> To start using the plugin, use the "Show NppFTp Window" option from the plugins menu, or use the Notepad++ toolbar button.
> To find some information about the plugin, use the "About NppFTP" option from the menu. There is a button there for a link to the NppFTP site.
> 
> 
> Configuring:
> ------------
> There are two configuration dialogs for NppFTP. These can be accessed by clicking on the settings button in the NppFTP toolbar (cog icon).
> 
> -General configuration
> In the general configuration dialog, the default cache location can be entered. See 'Cache paths' for more details. It will map to the root directory on the server ('/')
> and if no other cache locations are provided by a profile, this will always be the target.
> 
> -Profile configuration:
> In the profiles configuration dialog, profiles can be created, modified and deleted. Initially, no profiles exists and no connection can be made.
> To create a new profile, click the Add profile button and enter the name of the new profile. Please provide an unique name for your own ease of use.
> Renaming and delting a profile is done with the corresponding buttons.
> In the connections tab, settings for each connection be be entered. At minimum provide a hostname (address) and port.
> In the transfers tab, settings for FTP transfers can be edited.
> In the cache tab, specific cache mappings can be added for the selected profile. See 'Cache paths' for more details.
> 
> Cache paths:
> ------------
> When downloading files form a server, they are by default stored in the cache. When a file in the cache is saved, it will automatically be uploaded. To allow more fine grained control over what files go to where, a cache mapping can be created. A cache map consists of a local directory and an external path. The local directory provides the location on the local computer to look for files to upload and to download to. For example, if "C:\ftpfiles\myserver\home" were entered, files in that directory and subdirectory would be transferred to the correspodning path on the external server. The external path provides the location to download files from and upload to. For example, "/home/myuser/public_html/" would map files on that path and its subpaths to the corresponding directory.
> Determining a cache map for a filetransfer is done on a first match basis (rather than 'best fit'). For example, consider the following scenario:
> Profile cache maps:
> Local                        External
> C:\webfiles                  /home/user/public_html
> C:\webfiles                  /home/user2/public_html
> C:\rootfiles                 /root
> D:\serverfilesystem          /
> 
> General cache map:
> C:\myuser@server.com\        / (fixed)
> 
> Downloads:
> The external file "/home/user/public_html/index.html" would be transferred to "C:\webfiles\index.html"
> The external file "/home/user/.bash_rc" would be transferred to "D:\serverfilesystem\home\user\.bash_rc"
> The external file "/root/apache.conf" would be transferred to "C:\rootfiles\apache.conf"
> The external file "/vmlinuz.img" would be transferred to "D:\serverfilesystem\vmlinuz.img"
> No download would be directed to "C:\myuser@server.com\"
> 
> Uploads:
> The local file "C:\webfiles\home\user\.bash_rc" would be transferred to "/home/user/public_html/home/user/.bash_rc" (user2 will NOT be considered)
> The local file "D:\serverfilesystem\boot\grub\menu.lst" would be transferred to "/boot/grub/menu.lst"
> The local file "C:\myuser@server.com\home\user\public_html\index.html" would be transferred to "/home/user/public_html/index.html"
> 
> Ordering is important. The general cache map will always be considered last, the profile maps will be considered from top to bottom. So if
> D:\serverfilesystem          /
> were to be at the top, ALL files would be downloaded to "D:\serverfilesystem"
> 
> Toolbar:
> --------
> The toolbar provides the following buttons:
> Connected/Disconnect: Either connect to a server from a profile form a dropdown menu, or disconnect from the current server.
> Download file: If a file is selected in the treeview, download it to the cache.
> Upload file: If a directory is selected in the treeview, upload the current file to that directory.
> Refresh: If a directory is selected in the treeview, refresh its contents.
> Abort: If a transfer is active, abort it.
> Quote: send a direct command to the server (Currently not implemented)
> Settings: Access settings dialogs.
> Show messages: Hide or Show the messages window.
> 
> Treeview:
> ---------
> If an ftp session is active, the treview will show the files on the server. Some actions of the toolbar depend on the selected object in the treeview (see toolbar).
> Doubleclicking on a directory will show its contents. Doubleclicking on a file will download it to the cache and open it.
> 
> Queue:
> ------
> The queue window shows the currently active and queued filetransfers, along with their progress and filepath. Rightclicking on an item
> allows to abort or cancel it, depending whether the transfer is active or queued.
> 
> Message window:
> ---------------
> The messagewindow shows some output of various operations. If something goes wrong, look for errors here.
> Notifications are blue, server messages are green, errors are red.

## tools/npp/plugins/doc/SelectNLaunch/readme.txt (524 B)

<!-- 编码: utf-8-sig -->

> Select 'N' Launch is a plugin of Notepad++.
> 
> Its basic feature is get your selected text, save it as file with the extension you customized in the system temporary directory, then call system to open it with the extension associated program.
> In my personal usage, I defined crt and pdf as extension, then I can launch pdf or show a certificate on the fly, by selecting a Base64 text and executing the defined commands.
> 
> Upto 20 commands (20 extensions) are customizable in this plugin.
> 
> Enjoy
> 
> Don Ho
> don.h@free.fr

## tools/npp/plugins/doc/ZenCodingPython/readme.txt (2798 B)

<!-- 编码: utf-8-sig -->

> Zen Coding for Notepad++ - Python Version
> 
> 
> 
> This plugin is powered by the Python Script plugin for Notepad++ - install that with Plugin Manager, 
> or download from http://npppythonscript.sourceforge.net or http://www.brotherstone.co.uk/npp/ps
> 
> You need the Visual C++ Runtime 2008 for the Python Plugin 
> (this is a Python requirement - hopefully this will change in the future)
> If you've not got it, you'll get a LoadLibrary failure (chances are you have, lots and lots of software 
> comes with it).  Download it free from Microsoft:
> 
> http://www.microsoft.com/downloads/details.aspx?FamilyID=9b2da534-3e03-4391-8a4d-074b9f2bc1bf&displaylang=en
> 
> 
> Zen Coding is Copyright and developed by Sergey Chikuyonok
> 
> 
> 
> This plugin is Copyright (C) 2010 Dave Brotherstone
> 
> License: GPL2
> 
> Source available on github.com/davegb3
> 
> 
> 
> Installation
> ============
> 
> Just copy the ZenCoding-Python.dll to your Plugins directory (normally c:\Program Files\Notepad++\plugins), and the ZenCodingPython
> directory to your plugin config directory - normally %APPDATA%\Notepad++\plugins\config\ZenCodingPython, but can also be
> under plugins\config from your Notepad++ directory (if you have a doLocalConf.xml file next to notepad++.exe)
> 
> 	
> Usage
> =====
> Set the shortcuts under the shortcut mapper (Settings menu)
> If you set the shortcut for Expand Abbreviation to just "Tab", you need to remove the Tab shortcut from the Scintilla commands (for SCI_TAB).
> Notepad++ won't let you do this, so you have to change the shortcut to something obscure (Ctrl-Alt-Shift-9 or something)
> 
> If you set Tab as the shortcut, it will intellegently expand an abbreviation if one is there, or if not, send the Tab command directly to Scintilla
> (so won't interfere with normal Tab operation, eg. indenting and so on)
> 
> Profiles are automatically selected when the Auto Select Profile is on.  This switches between xhtml (default), xml when the language is set to XML,
> and Plain, when the language is Normal Text.  
> 
> Edit Shortcuts - this allows you to easily edit your own shortcuts - this file is not replaced by Plugin Manager (when Zen Coding for Python is available 
> in Plugin Manager), so you can add your own abbreviations to this, and they won't be overwritten.
> 
> 
> 
> Contact 
> =======
> 
> Comments, bug reports, requests etc as always, welcome - davegb@pobox.com
> 
> 
> 
> 
> 
> Version history
> Version: 
> 		0.1 
> 			- Initial relese
> 			
>         0.1.1
> 		    - ZenCodingPython files updated with correct structure
> 			
> 		0.2
> 			- Profiles available, with auto select
> 			- Edit settings option, with automatic refresh (when saved from Notepad++)
> 			- my_zen_settings.py now auto-generates, to allow non-installation by Plugin Manager.
> 			- Tab key support
> 			- XSD mode and filter added
> 			

## tools/npp/readme.txt (1543 B)

<!-- 编码: utf-8-sig -->

> What is Notepad++?
> ******************
> 
> Notepad++ is a free (as in "free speech" and also as in "free beer") source code editor and Notepad replacement that supports several programming languages and natural languages. Running in the MS Windows environment, its use is governed by GPL License.
> 
> 
> Why another source code editor?
> *******************************
> 
> The company where I worked used JEXT (another open source code editor in Java) as the production tool. Due to its poor performance, I began an investigation to find another solution (in C++ instead of in Java) in September 2003. I found Scintilla and built a prototype. Unfortunately this solution was not accepted. I removed the specific part and continued to develop it in my leisure time. On the 25th November 2003 it was made available on Sourceforge, and that was the birth of Notepad++.
> 
> 
> How to install:
> ***************
> 
> From the installer : 
> 	Just follow the install wizard.
> From the zip :
> 	just unzip all the files into a directory you want then launch it.
> 
> 	
> Web sites:
> ***********
> 
> Notepad++ official site:
> 	http://notepad-plus-plus.org/
> 
> Notepad++ online document site:
> 	http://npp-community.tuxfamily.org/
> 
> Notepad++ project site:
> 	http://sourceforge.net/projects/notepad-plus/
> 
> Notepad++ wiki:
> 	http://sourceforge.net/apps/mediawiki/notepad-plus/index.php?title=Main_Page
> 
> Notepad++ support:
> 	http://sourceforge.net/projects/notepad-plus/forums
> 
> 
> Author:
> *******
> 
> Don Ho <don.h@free.fr>
> 	http://notepad-plus-plus.org/author

---

# 第三批：参考文献 PDF —— 与数据格式强相关段落摘录

*方法：pdfminer.six 全文提取后，用关键词窗口法定位相关段落。关键词：*
`input file`、`input data`、`table`、`tabulated`、`opacity`、`EOS`、`equation of state`、
`units`、`cgs`、`group`、`frequency`、`photon energy`、`SESAME`、`SNOP`、`format`、`read`。

## doc/References/1988CPC49(R.Ramis)_MULTI - A computer code for one-dimensional multigroup radiation hydrodynamics.pdf (2757057 B)

<!-- 共 32 页 -->

### 第 1 页

> Received 31 July 1987
>
> The basic physical equations as well as a computer code for the simulation of one-dimensional radiation hydrodynamics are
> described. The hydrodynamic equations are combined with a multigroup method for the radiation transport. The code, written
> in standard FORTRAN-77, is characterized by one-dimensional planar geometry with multilayer structure. A time-splitting
> schema has been adopted with implicit finite-differencing formulation (including the hydrodynamics), and Lagrangian
> coordinates. Tabulated equations of state and opacities are used.
>
> PROGRAM SUMMARY

> field strongly interacts with the hydrodynaniic motion through
> frequency-dependent emission and absorption processes.
>
> Method of solution
> The equations of radiation transfer coupled with Lagrangian
> hydrodynamics are solved using a fully implicit numerical
> scheme. Frequency and angle dependence is included via a
> multigroup treatment. A time-splitting algorithm is adopted
> which feeds in all the groups successively during one hydrody-
> namic time step. Tabulated equation of state data, Planck and
> Rosseland opacities, and non-LTE properties of the matter are
> used winch have to be generated externally.
>
> Restrictions on the complexity of the problem
> The MULTI code assumes one-dimensional plane symmetry.
> The target may consist of upto ten layers with up to three
> different materials. Laser energy deposition is modeled by
> inverse bremsstrahlung absorption and a dump at the critical
> density. Electronic heat conduction is flux limited in the usual
> way. Radiation transport is treated stationary assuming that

> Restrictions on the complexity of the problem
> The MULTI code assumes one-dimensional plane symmetry.
> The target may consist of upto ten layers with up to three
> different materials. Laser energy deposition is modeled by
> inverse bremsstrahlung absorption and a dump at the critical
> density. Electronic heat conduction is flux limited in the usual
> way. Radiation transport is treated stationary assuming that
>
> the matter velocity is much less than the speed of light.
> Scattering is neglected. There is a single matter temperature
> and opacities are assumed to depend only on tins temperature,
> the density and frequency.
>
> Typical running time
> On the CRAY-XMP the computing time is below i0-~s/(zone
> timestep group) if the number of groups is not too small.

### 第 2 页

> The present version of the code includes laser
> absorption by inverse bremsstrahlung 9. Anoma-
> bus absorption mechanism are mocked up by a
> dump at
> the critical density. Other forms of en-
> ergy deposition can be easily implemented by
> changing the appropriate routines.
>
> The properties of the matter are given through
> tabulated equations of state (usually taken from
> the SESAME library 10) and tabulated opacities.
> The non-LTE option requires the knowledge of
> the emission properties of the matter depending
> only on temperature, density and frequency. These
> are generated off-line using a stationary model
> 14 and fed into the code in tabular form.
>
> A time-splitting scheme is used;

### 第 3 页

> (2.1)
>
> I(r, n, v, t) is the specific intensity of radiation of
> frequency v at a position r travelling in direction
> n at time t, i~is the total emissivity and x is the
> total opacity. The term on the right hand side is
> the effective rate of energy emission (emission
> minus absorption) by the matter per unit of
> volume, frequency and solid angle. The relation-
> ship between the photon momentum p and its
> energy e is given by: p = (e/c)n. Consequently
> the specific rate of momentum emission is ~ —
> XI)/c)n. The total emission rates per unit volume
> of energy Q and momentum R are obtained by
> integrating over all frequencies and directions
>
> thermodynamic properties of the matter: tempera-
> ture T and density p. This is obviously correct for
> thermodynamic equilibrium and is the simpler
> choice for more complicated situations:

> I~(T,v)=~_(ekT_l)_1.
>
> (2.5)
> Deviations of I~from I~,may become im-
> portant in laser plasma problems, in particular in
> the thin plasma corona. MULTI allows for non-
> LTE physics, details are described further below.
> The velocity of the matter is assumed to be
> small in comparison with the light velocity. Conse-
> quently the opacity and the source function can be
> considered as isotropic (this is equivalent to ne-
> glecting the Doppler effect). In addition they are
> assumed to depend only on the frequency and the
>
> XJ

### 第 4 页

> consistent with the terms which are also dropped
> in the radiation transfer equation. The equations
>
> The main variables matter density p(r, t), velocity
> v(r,
> t), specific internal energy e(r, t) and pres-
> sure P(r, t) are considered here to be functions of
> coordinate and time. .D~is the time derivative in a
> 8~+ v
> frame moving with the fluid velocity: (D1
> v). R and Q are the radiated momentum and
> energy per unit volume,
> respectively, q is the
> thermal flux and S includes other energy sources
> like laser or
> ion beam energy deposition. The
> Eulerian fluid equations for the one-dimensional
> planar case can be obtained easily from the system
> (11)—(13), but instead it proves convenient to use
> the Lagrangian formulation. The Lagrangian coor-
> dinate is defined here by
> m(x, t) = fX p(x’, t) dx’,
>
> (2.14)

> —~
>
> m is in fact the total mass per unit area at the left
> the considered point. The system (11)—(13)
> of
> becomes in planar geometry
>
> used in the code are, in fact, the first order equa-
> tions in a hierarchy of equations obtained by
> developing in powers of
> the small factor va/c,
> where v~is the characteristic velocity (m l~/t~).

### 第 5 页

> sides, whose position change with time. However,
>
> their Lagrangian mass coordinates, denoted by mL
> and mR, respectively, are constant. (m L = 0 be-
> cause there is no mass to the left of
> the left
> boundary, and mR, the total mass per unit area, is
> constant if the mass is conserved).
> First the specific radiation intensity I(m, p, v,
> t) will be considered. For positive p this function
> represents the intensity of radiation travelling from
> left to right. Consequently the natural boundary
>
> conditions must be, in this case, imposed on the
> left boundary mL. Once these are known, (7) can
> be integrated and the values at the right boundary
> determined. Conversely, the boundary conditions
> for I with negative p must be imposed at mR.
> Some of
> the left
> the possible combinations at
> hand side are (for p

### 第 6 页

> Although
>
> the program manages composed
> layers there are no explicit boundary conditions at
> the interfaces. Instead a matter composition func-
> tion N( m) (usually taking integer values) is given,
> which enters as a parameter in the opacity and
> equation of state.
>
> 3. Muttigroup radiation model

> (3.1)
>
> pend on the Lagrangian coordinate. The quantity
> ic (m x/~)is the opacity expressed in units of
> surface per mass. The above equation is obviously
> very complicated;
> the specific intensity depends
> on four variables. Careless discretization can easily
> lead to an enormous amount of computational
> work or a substantial loss of accuracy. The ap-
> proach adopted here carries out the discretization
> in two steps. First eq. (1) is replaced by its in-
> tegrals over the variables v and p in a finite
> number of domains called ‘groups’. This proce-
> dure leads to a finite number of differential equa-
> tions involving a finite number of variables de-
> pending only on m and t.
> In the second step,
> discussed in the next sections, this set of equations
> together with the fluid,
> thermal flux and laser
> equations is discretized in a computational mesh
> in the m,
> t space, generating finite difference
> equations.
>
> 3.2. Group definition

### 第 8 页

> C
>
> The material coefficients ic~and 4 are usually
> named Planck and Rosseland mean opacities and
> are defined by
>
> = j bKI~dv/f~Ip dv,

### 第 9 页

> (3.35)
>
> On the other hand, the boundary conditions are
> the same, provided that g~is used instead of g,,~.
> These equations can be compared with the system
> (19), (20). There are two differences, namely: the
> appearance of the Planck opacity instead of the
> Rosseland opacity and the different expression for
> the factor g,~in (34). Nevertheless, both descrip-
> tions are equivalent. In fact, they coincide when
> the size of the groups is made arbitrarily small.
> That is: 4—3.4 and g,~~—3.g~when v~’—~v~and
> 14 — p’~,.The advantage of the previous model had
> been already pointed out. On the other hand, the
> alternative model has an interesting property: eqs.
> (33), (34) can be linearly combined giving
>
> ~m (Sk + g,~cUk) = C4 Usk — ~ (Sk + gkCUk)

### 第 12 页

> 4.6. Matter equations
>
> The above equations must be completed by the
> equation of state, opacities and other matter prop-
> erties
>
> Peq,iFeq(Pi, e~,N;),

> N, k=1,...,NG).
>
> (4.25)
> is constant in time. These
> The composition N;
> relations are implemented in the standard version
> of the code interpolating between tabulated val-
> ues. Nevertheless it is possible, by changing the
> appropriate routines, to use analytic expressions.
>
> 5. Temporal discretization

> supplies the required solution, provided that z~tis
> small enough. In general, this explicit scheme needs
>
> a prohibitively small value for the time step I~tin
> order to be numerically stable. This makes it
> useless in practice. The numerically stable implicit
>
> scheme
> _________ = (1— 9)f(x~)+ Of(X~~),
> x”-’-

### 第 13 页

> (5.7)
>
> stands for terms that verify
> The notation ~2(~t)
> I e’(~t)I constant X .~t for i~t ~
> This ex-
> pression implies the so-called ‘consistency’ of the
> method. If, in addition, the method is stable, this
> leads to the appropriate solutions. If both (5), (6)
> are stable it is reasonable to think that the two
> substeps method is also stable;
> this occurs in
> practice. The global method has only a first order
> accuracy (the error is of order ~!2(’~t)), but this is
> scarcely a trouble;
> the main (and unavoidable)
> sources of error had been made in modelling the
> physics. The extension to more than two terms on
> the right of (4) is straightforward.
>
> Now coming back to the physical equations, it
> is clear that the different terms can be grouped in
> the following way

### 第 15 页

> are selected, the temperature increments in all the
> transport processes are the same, supplying the
>
> same name and arguments, but with completely
> different physics, without the need of additional
> changes in other program units. The modules are
> the following:
>
> QUELIN-QUELLE-LASER3
> HYDRO-LEICHT-ABLTNG

> EOSM-EOSIN1-EOSIN2-EOSBIN-EOSLIN
> WFIN-WFLUSS-LEICHT-WFDER
> OPA-OPAIN-OPABIN
>
> The program input is done through FOR-
> TRAN units 12 to 19. Every unit has assigned a
> conceptually different sort of data (i.e. on 16 are
> given the laser characteristics). In some units the
> read process is carried out until the ‘end-of-file’ is
> reached.
>
> Matrices are used at different places of the

> Matrices are used at different places of the
>
> program. In general they have a banded structure
> and thus can be stored in condensed format. Ev-
> ery diagonal of the ‘mathematical’ matrix is stored
> in one row of the ‘FORTRAN’ matrix. This for-
> mat is required by the library routines that per-
>
> desired smoothing through the step.

> The program initializes first the values of the
>
> The program uses the c.g.s. system of units,
>
> factors to

> The program is written (as much as possible) in
> a modular way; only four routines have more than
>
> with the exception of the temperature which is
> given in electron volts. However, for compatibility
> with other programs, the equation of state tables
> must be supplied in SESAME 10 units.
>
> 6.2. Main body

> In this section the main program (MULTI) and
> some auxiliary routines for input and initialization
> (INITYR, GDTGEN, WCTRL, ZONING) will
> be described. The different tasks carried out are
> the following
>
> i) The program reads from the FORTRAN unit
> 12 a series of parameters that control the subse-
> quent operations. These parameters must be given
> in a NAMELIST block with the name INPUT as
> in table 1.

### 第 16 页

> Then the program prints out its version number
> (the actual is 2.0) followed by and echo of all the
> above parameters.
>
> ii) The routine INITVR reads its input data
> initializates zXm~ and
> from FORTRAN unit 14,
> the main variables p,, v, and e, and stores in the
> common block COMLDT (Layer Definition Ta-
> ble) the composition of the foil N;.
>
> The program manages multilayer foils; for ev-
> ery individual layer an input line with the follow-
> ing format is read.

> is greater/bess than one, a finer zoning occurs at
> In addition, negative values give
> the left/right.
> finer zoning at both sides (I ZONPAR I
> 1) or in
> the center (I ZONPAR I 1). Finally, the echo of
> the read data and the initial values are printed
> out.
>
> iii) The initialization routines for the equation
> of state (EOSIN1, EOSIN2), opacity (OPAIN),
> energy deposition (QUELIN) and thermal flux
> (WFIN) are called. They are appropriately de-
> scribed in the corresponding subsections of this
> section.
>
> A printout is generated with information about

> A printout is generated with information about
>
> the tables actually read by these routines.
>
> iv) The routine GDTGEN loads the common
> block COMGDT (Group Definition Table) from
> the contents of the commons COMLDT (Layer
> Definition Table) and COMODT (Opacities Defi-
> nition Table). During this process a checkout of
> consistency is done. Some conditions can produce
> a program stop (i.e. an opacity table for a given

### 第 17 页

> 491
>
> frequency interval and material loaded more than
> once), or a warning message (i.e. loading a table
> for a not used material).
>
> Finally, the values of ,.t’~,,i4 and g,~are set to
> 0, 1 and 1/ v~,respectively (no angular resolution
> in the standard version of the code).

> Finally, the values of ,.t’~,,i4 and g,~are set to
> 0, 1 and 1/ v~,respectively (no angular resolution
> in the standard version of the code).
>
> v) The routine SOUTIN reads from FOR-
> TRAN unit 18 information about what variables
> must be dumped on disk for later post-processing.
> A detailed description of the output format will be
> given in the following section.
>
> vi) In the following,

### 第 18 页

> The subroutine SOUTIN reads from FOR-
> the
>
> TRAN unit 18 a line for every selection,
> format is
>
> Format

> the
> If the first field is not a blank character,
> line is interpreted as a comment. The auxiliary
> arrays CMI and CMC contain the mass coordi-
> nates at the interfaces and in the center of the
> cells,
> the
> respectively, while FREC contains
> medium frequencies of the groups. In addition the
> arrays SOCFRE and SOFCMI contain the Ire-
> quencies and mass coordinates corresponding to
> the values stored in SOC and SOF, respectively
> (there is a one to one correspondence between
> these arrays).
>
> The structure of the output file had been desig-
> ned in order to make easy a posterior search of the
> required data. Therefore, besides the numerical
> data, suitable information over the contents are
> stored (directory). The file is composed of ‘sec-
> tions’, and these are composed of binary records
> (not formatted). The contents of a section is:
>
> 1st record:

> 3rd record: a list of integer values that specifies
> whether the associated variables are scalars (value
> the corresponding
> zero) or an array (index of
> elements). Nevertheless these values are scarcely
> used by the post-processor programs and thus can
>
> be taken to store other information.
>
> 4th record: a list with the data (real values).
> Successive records: equal

### 第 19 页

> The subroutine contains two DO loops. The
> external one (DO 23) goes over NS times (one for
> every hydrodynamic substep). The internal one
> (DO ii) goes over NG/NS times for every time in
> the external loop; hence a total of NG times (once
> for each group). The tasks carried out in the
> external loop are:
>
> i) The equation of state, in the form (5.13),
> (5.14), is computed through a call to the routine
> EOS.
>
> ii) The hydrodynamic substep is carried out by

> The temperature increments is in this cell through
> the heat flux substep, and the group substeps are
> stored in WBW(scalar) and WB(array), respec-
> tively, for posterior use in the control of
> the
> partition of the power deposition (see section 5.5).
> The other quantities related to this related to this
> process a,
> ilo and ilk are passed through the
> variables WC, WAW and WA, respectively.
>
> The validity of the intermediate results is often
> checked;. if a negative temperature or density is
> found the complexion variable ICOMP takes a
> negative value and a return occurs. The error
> origin is coded in ICOMP in the format: — ggssee,
> where ee is the error type, ss the number of the
> subcycle where occurred and gg the group (if any)
> concerned.
>
> There are many points where the variables and
> intermediate results are printed. The flags IPRT1
> and IPRT2 enable this printout in the ranges of
> the external loop and internal loop, respectively.
> In addition the flags IPRT3 and IPRT4 are passed
> to the equation of state and opacity routines,
> respectively, enabling the printout of their results
> (for test purposes). Most of this output is gener-
> ated by the auxiliary routine DUMPE.
> The routine GROUP delivers

> There are many points where the variables and
> intermediate results are printed. The flags IPRT1
> and IPRT2 enable this printout in the ranges of
> the external loop and internal loop, respectively.
> In addition the flags IPRT3 and IPRT4 are passed
> to the equation of state and opacity routines,
> respectively, enabling the printout of their results
> (for test purposes). Most of this output is gener-
> ated by the auxiliary routine DUMPE.
> The routine GROUP delivers
>
> the radiation
> variables in the array SPECTR, and from there
> they are selected and put into the arrays SOC and
> SOF as described in the previous section. This
> process take place in the inner loop. The requested
> options are described in the tables KSOC and
> KSOF.
>
> iii) The power deposition profile is computed

### 第 20 页

> initial time derivatives. By other hand the Jacobian
> is computed using the approximate formula
>
> and Rosseland (OR) opacities, and the non-LTE
> coefficients Ek (EPS) from the values of density
>
> 0FH

> (6.2)
>
> some small quantity, X°) the initial
> Being (cid:128)
> value of (X, and LJ~. a unit vector. The evalua-
> tion of this expression requires as many additional
> calls to ABLTNG as non-null diagonals in the
> Jacobian (seven). Finally, system (5.16) is solved
> by standard library (LINPACK) routines: SGBFA
> (factorization of a general banded matrix) and
> SGBSL (solve a general banded linear system).
>
> this process, carried out by the routine
> All
> the
> is independent of
> LEICHT,
> equations,
> this routine is in fact written as a
> general purpose subprogram. The routine HY-
> DRO serves merely as interface between the main
> program and this subprogram.

> 6.6. Heat flux
>
> The routine WFIN, called by the main pro-
> gram, reads its input from FORTRAN unit 19,
> from a NAMELIST block with name THERM,
> and computes the conduction coefficient. The
> variables read are the atomic mass A, the effective
> ion charge number Z, and the flux limit factor
> FFACTOR. The value of Coulomb’s logarithm is
> taken equal to 10. Finally, the values of z, FFAC-
> TOR and the conductivity coefficient are printed
> out.
>
> The heat flux substep is carried out in a similar
> way as the hydrodynamic substep. The routine
> LEICHT is also used, while the time derivatives
> are
> routine
> supplied by WFDER,
> WFLUSS serves as interface,

> The group substep is controlled by the routine
> GROUP that performs some trivial computations
> and calls the auxiliary routines OPACIT, RFE,
> REE, MEE, SOLVE3, MAT1 and PLANCK. In
> addition, the last one calls the routine PDSTRB.
> First the routine OPACIT supplies Planck (OP),
>
> The non-squared matrix AS is stored in usual
> format (the diagonals stored in rows), while the
> the first and last elements of BS are BS1 and BS2,
> respectively (all the others are zero). These values
> are evaluated through a call to the routine RFE.
>
> As follows, the routine PLANCK delivers the
> source energy density as well as their temporal
> derivative, computed at some temperature T1 ~,
> in
> the arrays UP and UPD, respectively. For a differ-
> the energy density is approxi-
> ent temperature,
> mated by
> 1U 1—1UP~+1UPD’1T T*
> ~ Sk I — 1
> .1 1
> The temperature T, * (m TTRY) is initially set to
> the temperature T,°.

### 第 21 页

> dx
>
> which is supphed by the routme PDSTRB by
> interpolation in a table. This table is computed by
> the same routine when it is called the first time.
>
> 6.8. Laser deposition

> Material identification
>
> Normal density (unused)
> Number of tabulated den-
> sities
> Number of
>
> tabulated en-

> The main program calls
>
> routine
> QUELIN which reads from FORTRAN unit 16
> the laser characteristics. These data must be given
> in a NAMELIST block with the name PULSE, of
> the following contents
> _____________________________________________
> Parameter
>
> Description

> 6.9. Equation of state
>
> The routine EOSIN1 is called from the main
> program. It reads, from FORTRAN unit 13, a
> series of equation of state tables. The format of
> one of these tables consists of a string of real
> numbers, four numbers packed in one line in
> fields of 15 characters (format 4E15.0). In case
>
> R(I),

> 3 g —1)
>
> ergies
> Tabulated densities
> cm )
> Tabulated energies (dif-
> ference to the cold energy
> values) (Mbar. cm
> Values of the cold energy
> corresponding to the tabu-
> bated densities (Mbar’ cm3
> g 1)
> Pressure at density R(I)
> and at specific internal en-
> ergy DE(J) + E0(I) (Mbar)
>
> at

> If more than one material is required, the corre-
>
> sponding tables are loaded successively up to a
> maximum of
> four. The materials will be refer-
> enced everywhere by their order in this loading.
> The routine prints out the identification and num-
> ber of memory words needed for every material
> and the total number of materials loaded.
>
> Afterwards, the routine EOSIN2, called by the
> main program, converts these tables to the system
> of units of the program. In addition, the negative
> pressures are set to zero.

### 第 22 页

> R. Ramis et at / One-dimensional multigroup radiation hydrodynamics
>
> DTDE. The values in all computational cells are
> requested at the same time. This routine uses the
> information stored in the ‘Layer Description Ta-
> ble’ (COMLDT) in order to generate a call to the
> routine EOSM for every layer present. This routine
> performs really the interpolation using the aux-
> iliary routines EOSLIN and EOSBIN for linear
> interpolation in a 1-dimensional array and for
> bilinear interpolation in a 2-dimensional array,
> respectively,
>
> Setting the flag IPRT to one, the routine EOS
> generates a listing with all the interpolated values.
> This is intended to be a diagnostic test of the
> integrity of the tables.

> 6.10. Opacities
>
> The routine OPAIN is called from the main
> program. It reads, from the FORTRAN unit 15, a
> series of opacity tables. The format of one of these
> tables is shown in table 2.
>
> The above data are packed at

> the rate of four
> values per line. In the case that the total number is
> not an even multiple of four,
> the last line is left
> partially empty.
>
> This tables are loaded successively up to a
> maximum of 100. They will be referenced inter-
> nally by their order in this loading. The routine
> prints out the identification and number of mem-
> ory words needed for every table and the total
> number of tables loaded.
>
> The routine OPACIT, called by the routine
> GROUP, supplies the values of OP, OR and EPS.
> The values in all the computational cells are re-
> quested at the same time. This routine uses the
> information stored in the ‘Layer Description Ta-
> ble’ (COMLDT) and in the ‘Groups Description
> Table’ (COMGDT) in order to generate three calls
> to the routine OPA for every layer present. This
> routine performs the interpolation in a 2-dimen-
> sional array. In the case that one of
> the two
> opacities is missing the other is used. On the other
> hand if the non-LTE coefficients are missing the
> program assumes ~k = 1.

> The routine OPACIT, called by the routine
> GROUP, supplies the values of OP, OR and EPS.
> The values in all the computational cells are re-
> quested at the same time. This routine uses the
> information stored in the ‘Layer Description Ta-
> ble’ (COMLDT) and in the ‘Groups Description
> Table’ (COMGDT) in order to generate three calls
> to the routine OPA for every layer present. This
> routine performs the interpolation in a 2-dimen-
> sional array. In the case that one of
> the two
> opacities is missing the other is used. On the other
> hand if the non-LTE coefficients are missing the
> program assumes ~k = 1.
>
> the routine
> Setting the flag IPRT to one,
> the inter-
> OPACIT generates a listing with all
> polated values. This is intended to be a diagnostic
> test of the integrity of the tables.
>
> Table 2

> Description
>
> Material identification
> Type of the table. One of the following:
> ‘PLANCK 1’
> ‘PLANCK M’
> ‘ROSSELAND 1’
> ‘ROSSELAND M’
> ‘EPS1’ )
> ‘EPS M’
> Number of tabulated densities
> Number of tabulated temperatures
>
> Opacities

> This line must be given only for types ‘PLANCK M’, ‘ROSSELAND M’ and ‘EPS M’. If either, the type ends with ‘1’, or both
>
> FRECA and FRECB are zero, the program assumes that this table applies to all groups.
>
> Subsequent lines
> E15.8
> E15.8
> E15.8

> LR(I), I = 1, NR
> LT(J), J
> 1, NT
> (LO(I, J), I = 1, NR), J = 1, NT
>
> 3)
> Decimal logarithm of the tabulated densities (g cm
> Decimal logarithm of the tabulated temperatures (eV)
> Decimal logarithm of the opacity corresponding to LR(I) and LT(J) (cm2 g~1)

### 第 24 页

> A composed target is considered: an aluminum
> layer of 2 jim thickness is covered by 0.2 jim of
> 2 intensity,
> gold. A laser pulse of 3 x 10i4 W/cm
> 300 ps (fwhm) duration, and 0.44 jim wavelength
> is incident from the right (on the gold side).
>
> For the gold, Rosseland and Planck opacities
> and the non-LTE source function are taken from
> ref. 14. Twenty groups are formed. For the
> aluminum, LTE is assumed and grey (one group)
>
> opacities found in the SESAME library are ap-
> plied. For both materials, SESAME equations of
> state are used. Electronic heat flux is not limited.
> The print output is shown below in slightly
> compressed form. In addition graphical output is
> generated using 3-D routines developed at
> IPP/Garching. Included in figs. 1—5, respectively,
> are: T(m, t), p(rn, t), p(m, t) and It)
> at the
> at the left boundary as a function
> right and I~)
> of time and frequency. Because the plot software
> is non-standard, we omit the corresponding part
> of the output.

### 第 27 页

> (IF ISOLATED —I
> (IF ISOLATED —l
>
> EOSIN1—I READ EOS TABLES FR~ UNIT 13
> EOSIN1—2 MATERIAL 2700 NEEDS 4871 STORAGE UNITS
> EOSINI—2 MATERIAL 3712 NEEDS 9125 STORAGE UNITS
> EOSINI—3 2 MATERIALS LOADED
>
> INITVR—I INPUT DATA

### 第 29 页

> HEEDS 442 WORDS
> NEEDS 442 WORDS
> NEEDS 442 WORDS
> HEEDS 442 WORDS
> NEEDS 442 WORDS
> NEEDS 442 WORDS
> NEEDS 442 WORDS
> NEEDS 442 WORDS
> NEEDS 442 WORDS
> NEEDS 442 WORDS
> NEEDS 442 WORDS
> NEEDS 442 WORDS
> NEEDS 442 WORDS
> NEEDS 442 WORDS
> NEEDS 442 WORDS
> NEEDS 442 WORDS
> NEEDS 442 WORDS
> NEEDS 442 WORDS
> NEEDS 442 WORDS
> NEEDS 442 WORDS
>
> OPAIN—i READ OPACITY DATA FROM UNIT 15
> OPAIN-’2 TABLE 2700 TYPE PLANGK 14
> OPAIN-2 TABLE 2700 TYPE PLANGK U
> OPAIN—2 TABLE 2700 TYPE PLANGK 14
> OPAIN—2 TABLE 2700 TYPE PLANGK U
> OPAIN—2 TABLE 2700 TYPE PLANCK U
> 14
> OPAIN—2 TABLE 2700 TYPE PLANCI
> OPAIN-2 TABLE 2700 TYPE P1*1.30K U
> O4’AIN-2 TABLE 2700 TYPE PLANCK 14
> OPAIN—2 TABLE 2700 TYPE PLAP30K 14
> OPAIN—2 TABLE 2700 TYPE PLANCI U
> OPAIN—2 TABLE 2700 TYPE PLANCI( U
> OPAIN—2 TABLE 2700 TYPE PLAICK 14
> OPAIN—2 TABLE 2700 TYPE P1*130K 14
> OPAIN—2 TABLE 2700 TYPE PLAICK 14
> OPAIN—2 TABLE 2700 TYPE PLANCK 14
> OPAIN—2 TABLE 2700 TYPE PLANCK 14
> OPAIN—2 TABLE 2700 TYPE PLANCK U
> OPAIN—2 TABLE 2700 TYPE PLANCK 14
> OPAIN—2 TABLE 2700 TYPE PLANCK 14
> OPAIN—2 TABLE 2700 TYPE P1*1.30K 14
> OPAIN—2 TABLE 3712 TYPE
> OPAIN—2 TABLE 2700 TYPE ROSSELAND U
> OPAIN—2 TABLE 2700 TYPE ROSSELAND 14
> OPAIN—2 TABLE 2700 TYPE ROSSELAND 14
> OPAIN—2 TABLE 2700 TYPE ROSSELAND U
> OPAIN—2 TABLE 2700 TYPE ROSSELAND U
> OPAIN—2 TABLE 2700 TYPE ROSSELAND U
> OPAIN—2 TABLE 2700 TYPE ROSSELANO U
> OPAIN—2 TABLE 2700 TYPE ROSSELANO U
> OPAIN—2 TABLE 2700 TYPE ROSSELAND U
> OPAIN—2 TABLE 2700 TYPE ROSSELAN0 U
> OPAIN—2 TABLE 2700 TYPE ROSSELAND U
> OPAIN—2 TABLE 2700 TYPE ROSSELAN0 U
> OPAIN—2 TABLE 2700 TYPE ROSSELANI) U
> OPAIN—2 TABLE 2700 TYPE ROSSELAND U
> OPAIN—2 TABLE 2700 TYPE ROSSELANO U
> OPAIN-2 TABLE 2700 TYPE ROSSELAND U
> OPAIN—2 TABLE 2700 TYPE ROSSELAND U
> OPAIN—2 TABLE 2700 TYPE ROSSELAND U
> OPAIN—2 TABLE 2700 TYPE ROSSELAND U
> OPAIN—2 TABLE 2700 TYPE ROSSELAND U
> OPAIN—2 TABLE 3712 TYPE 0.70000000E+Oi NEEDS 1505 WORDS
> OPAIN—2 TABLE 2700 TYPE EPS U
> OPAIN—2 TABLE 2700 TYPE EPS U
> OPAIN—2 TABLE 2700 TYPE EPS U
> OPAIN—2 TABLE 2700 TYPE EPS U
> OPA1N—2 TABLE 2700 TYPE EPS U
> OPAIN—2 TABLE 2700 TYPE EPS U
> OPAIN—2 TABLE 2700 TYPE EPS U
> OPAIN—2 TABLE 2700 TYPE EPS U
> OPAIN—2 TABLE 2700 TYPE EPS U
> OPAIN—2 TABLE 2700 TYPE EPS U
> OPAIN—2 TABLE 2700 TYPE EPS U
> OPAIN—2 TABLE 2700 TYPE EPS U
> OPAIN—2 TABLE 2700 TYPE EPS U
> OPAIN—2 TABLE 2700 TYPE EPS U
> OPAIN—2 TABLE 2700 TYPE EPS U
> OPA1N—2 TABLE 2700 TYPE EPS U
> OPAIN—2 TABLE 2700 TYPE EPS U
> OPAIN—2 TABLE 2700 TYPE EPS U
> OPAIN—2 TABLE 2700 TYPE EPS U
> OPAIN—2 TABLE 2700 TYPE EPS 14
> OPAIN—3 62 TABLES LOADED
>
> NEEDS 442 WORDS
> NEEDS 442 WORDS
> HEEDS 442 WORDS
> NEEDS 442 WORDS
> NEEDS 442 WORDS
> NEEDS 442 WORDS
> NEEDS 442 WORDS
> NEEDS 442 WORDS
> NEEDS 442 WORDS
> NEEDS 442 WORDS
> NEEDS 442 WORDS
> NEEDS 442 WORDS
> NEEDS 442 WORDS
> NEEDS 442 WORDS
> NEEDS 442 WORDS
> NEEDS 442 WORDs
> NEEDS 442 WORDS
> NEEDS 442 WORDS
> NEEDS 442 WORDS
> NEEDS 442 WORDS

> 1
> 2
> 3
> 4
> 5
> 6
> 7
> 8
> 9
> 10
> 11
> 12
> 13
> 14
> 15
> 16
> 17
> 38
> 39
> 20
>
> 0.00
> 0.00
> 0.00
> 0.00
> 0.00
> 0.00
> 0.00
> 0.00
> 0.00
> 0.00
> 0.00
> 0.00
> 0.00
> 0.00
> 0.00
> 0.00
> 0.00
> 0.00
> 0.00
> 0.00
> GDTGEN — WARNINGS THE TABLES ARE NOT CCWLETE III
>
> 1.0000
> 10.000
> 50.000
> 100.00
> 150.00
> 250.00
> 400.00
> 550.00
> 700.00
> 900.00
> 1200.0
> 1600.0
> 2000.0
> 2200.0
> 2400.0
> 2600.0
> 2800.0
> 3100.0
> 3500.0
> 4000.0

*本节命中相关段落 55 处。*

## doc/References/2009CPC180.977(Ramis)_MULTI2D – a computer code for two-dimensional radiation hydrodynamics.pdf (1201526 B)

<!-- 共 19 页 -->

### 第 1 页

> Program summary
>
> Program title: MULTI2D
> Catalogue identiﬁer: AECV_v1_0
> Program summary URL: http://cpc.cs.qub.ac.uk/summaries/AECV_v1_0.html
> Program obtainable from: CPC Program Library, Queen’s University, Belfast, N. Ireland
> Licensing provisions: Standard CPC licence, http://cpc.cs.qub.ac.uk/licence/licence.html
> No. of lines in distributed program, including test data, etc.: 151 098
> No. of bytes in distributed program, including test data, etc.: 889 622
> Distribution format: tar.gz
> Programming language: C
> Computer: PC (32 bits architecture)
> Operating system: Linux/Unix
> RAM: 2 Mbytes
> Word size: 32 bits
> Classiﬁcation: 19.7
> External routines: X-window standard library (libX11.so) and corresponding heading ﬁles (X11/*.h) are
> required.
> Nature of problem: In inertial conﬁnement fusion and related experiments with lasers and particle beams,
> energy transport by thermal radiation becomes important. Under these conditions, the radiation ﬁeld
> strongly interacts with the hydrodynamic motion through emission and absorption processes.
> Solution method: The equations of radiation transfer coupled with Lagrangian hydrodynamics, heat
> diffusion and beam tracing (laser or ions) are solved, in two-dimensional axial-symmetric geometry (R– Z
> coordinates) using a fractional step scheme. Radiation transfer is solved with angular resolution. Matter
> properties are either interpolated from tables (equations-of-state and opacities) or computed by user
> routines (conductivities and beam attenuation).
> Restrictions: The code has been designed for typical conditions prevailing in inertial conﬁnement fusion
> (ns time scale, matter states close to local thermodynamical equilibrium, negligible radiation pressure,
>
> ✩

### 第 2 页

> The central point of this paper is to give a correct description of
> directional radiative energy transfer with high angular resolution.
> This requires to go beyond the usual diffusive approximation, fre-
> quently used in 1D and 2D codes [7,13–16]. However, more sophis-
> ticated and accurate methods to solve the transport equation [17]
> demand extensive computer resources. Dealing with problems like
> ICF, in which drastically different optical thicknesses and thermo-
> dynamic properties occur simultaneously, robust, fast, and eﬃcient
> algorithms are needed.
>
> In the ICF context, matter velocity is typically smaller than
> the speed of light, so that the radiation ﬁeld can be regarded as
> quasi-static at any instant of time. The spectral radiation intensity
> Iν ((cid:3)r, (cid:3)n) (energy ﬂux per unit of solid angle and frequency) depends
> on position (cid:3)r, propagation direction (cid:3)n, and frequency ν. For condi-
> tions not too far away from local thermodynamical equilibrium, Iν
> is determined (neglecting scattering and refraction) by the radia-
> tive transport equation [18,19]:
>
> (cid:3)n · ∇ Iν = I P

> (1)
>
> where λ(cid:5)
> ν is the mean free path for radiation (taking into account
> stimulated emission), qν the power deposited in matter (per unit
> of volume, solid angle, and frequency), and I P
> ν is Planck’s distribu-
> tion function given by
>
> =

### 第 3 页

> (6)
>
> where Q is the power deposited into matter per unit of volume. If
> mean free path and temperature are known functions of position,
> Eq. (4) can be integrated over straight lines ((cid:3)r = (cid:3)r0 + l(cid:3)n, l being the
> length from point (cid:3)r0):
>
> I((cid:3)r0 + l(cid:3)n, (cid:3)n) = I((cid:3)r0, (cid:3)n)e

> integrating the tensor (cid:3)n(cid:3)n over all space directions gives
>
> Here,
> (4π /3) ¯¯u, ¯¯u being the unit tensor.
>
> Although the formal solution of the transfer Eq. (4) is given
> by Eq. (7), this procedure (called the long characteristics method
> [17,18]) cannot be implemented directly into an ICF code because
> it would require, in order to avoid numerical noise, a separation
> between characteristics lines smaller than the minimum size of the
> mesh; typical Lagrangian grids are very distorted, with some of
> the cells having an extremely small thickness, resulting in a pro-
> hibitive number of lines. In order to clarify the algorithm used by
> MULTI2D, we will discuss below situations of increasing complex-
> ity before considering the 2D axial-symmetric geometry used by
> the code.

### 第 4 页

> (cid:6)
>
> The absorbed power for the cell (per unit of transversal area) is
>
> + =

> 2 (I P
>
> Q
> (cid:9)x
> where ¯I P ≡ 1
> + I P
> b ), (cid:9)x is the cell thickness, and λc is the
> (cid:7)
> a λ−1(x) dx). Because we
> averaged opacity in the cell (λc = (cid:9)x/
> consider temperature deﬁned at interfaces, it is natural to deﬁne
> also the deposition of energy at interfaces. For optically thin cells
> ((cid:9)τ < 1), deposition is a smooth function, so that Q
> can be di-
> vided into two equal parts. For (cid:9)τ > 1, deposition is not smooth
> any more. Eq. (15) shows that, for large (cid:9)τ , deposition takes place
> in a region of thickness of order unity, close to cell entrance (the
> second term in this equation ( dI
> dτ /λ) will cancel exactly with a sim-
> ilar one originating by the transport in opposite direction −(cid:3)n). We
> observe that we can write the deposition of energy in a cell also
> as
>
> +

> 2.2. Two-dimensional planar transport
>
> The method outlined above can be extended to ideal planar ra-
> diation transport, where only propagation in directions parallel to
> a plane is allowed. In this situation, integrals in Eq. (3) should
> be extended over ordinary angles rather than solid angles, while
> Eq. (11) now becomes (cid:3)S (cid:8) −π λ∇ I P . We consider a 2D planar
> grid composed of triangular cells with temperatures deﬁned at the
> nodes (see Fig. 2), and radiative mean free path λ constant in each
> cell. The direction space is dicretized by subdividing the unit circle
> by an even number Nn of equal parts of size (cid:9)(cid:3)n = 2π /Nn. Transfer
> Eq. (4) for each direction is independent of the others, and can be
> solved separately. In principle, one could apply the 1D procedure of
> Section 2.1 for each direction by cutting the computational domain
> in parallel bands (shaded area in Fig. 2). The value of I P could
> be deﬁned, in each interface, as the average of values at its ends,
> while the deposition of radiation, computed at interfaces, would
> be distributed between the nodes at their ends. This approach is
> not convenient in distorted non-structured grids, because it will
> require as many bands as nodes. The computational effort, scal-
> ing with the number of triangles raised to the power 3/2, would
> be prohibitive. Instead, we take radiation intensity deﬁned at cell
> interfaces. For a given propagation direction (cid:3)n, we have two cell
> types: a, cells with radiation entering through one of the sides,
> and exiting through the other two (Fig. 3), b, cells with radiation
> entering through two sides, and exiting by the third (Fig. 4). We
> parallel to (cid:3)n, and ap-
> divide each cell into two parts by line A A
> ply the concepts outlined above for each part. For cells of type a,
> the exit intensities are obtained by applying Eq. (14)
>
> (cid:5)

### 第 6 页

> (45)
>
> To obtain Eqs. (42)–(43) from Eq. (40), one has to integrate the
> term ∂ I i/∂ϕ, singular at interval boundary ϕi j because Ii has been
> assumed discontinuous there. Although the integral of such term
> is I i j − I i, j−1, is not clear how to distribute this value between
> intervals j and j − 1. To solve this ambiguity, we use the follow-
> ing physical argument: this term takes into account that, for a
> photon moving along a straight line, ϕ is increasing (for ϕ < 0),
> until the boundary value ϕi j
> is reached and the photon passes
> j − 1 to interval
> from interval
> j. It is reasonable to assume that
> j − 1
> equation for interval
> (from where photons are coming) but not the intensity of inter-
> j + 1 (to where photons are going). This assumption, together
> val
> with the condition that I = I P = constant must be a valid solu-
> tion, determines completely Eqs. (42)–(43). Current implementa-
> tion in the code3 uses a uniform subdivision of θ and ϕ ranges,
> and requires M and Ni to be even and to verify the condition
> Ni = N M−i+1. In order to get an equation in conservative form,
> suitable to be discretized in R–Z space, a new variable is deﬁned:
>
> j will contain the intensity of interval

### 第 7 页

> (cid:3)ur + Ci j
> E i j
>
> plays the role of the unit vector in the propagation direction of
> radiation component Γi j . The two terms containing r can be in-
> terpreted as an attenuation term and a source term, originating
> geometrically from exit or entrance of photons in the direction
> domain. For r → ∞, both terms vanish, and the planar 2D trans-
> port is recovered. This similarity can be emphasized by writing the
> transfer equations as
>
> (cid:5)

> i j and Γ E
>
> where λE
> i j are effective mean-free-path and source term.
> This set of equations can be solved by the method described in
> Section 2.2. A grid of triangular cells in the plane R– Z is consid-
> ered, with temperatures deﬁned at nodes and opacities assumed
> uniform inside cells. For each value of i, we have a coupled set of
> equations from j = 1 to j = Ni , that has to be solved in this order.
> For each direction (cid:3)ni j , the cells must be sorted before computing
> exit values of Γi j from entry values in each cell. λE
> i j and the cor-
> responding optical depths (cid:9)τ E
> i j at cells are computed assuming an
> average value of radius in Eq. (49)
>
> ¯r = r A + r B + rC

### 第 9 页

> i E i +
>
> Obviously the conservation of energy is then satisﬁed in the sense
> i (cid:17)i is conserved. The method is consistent because,
> that
> for small values of (cid:9)t, one has |(cid:17)i| → 0. If, in addition, the method
> is stable, the numerical solution approaches to the true solution.
> In the context of complex and strongly nonlinear systems, these
> issues have to be assessed by numerical experiments. Neverthe-
> less, the numerical analysis of simpliﬁed cases will allow to clarify
> the limitations of the method. As such an example, we consider
> the discretization of the equation of one-dimensional diffusion,
> ∂ T /∂t = ∂ 2 T /∂ x2, taking, for simplicity, a unlimited and uniform
> grid with (cid:9)x = 1:
>
> dT i
> dt

> (74)
>
> It can be proven that, for 0 < β < 1 and α > 1 − β/2, the SSI
> method is unconditionally stable. Notice that, different from a
> straightforward explicit method (Eq. (67)), (cid:9)t values larger than
> one can be used (we assume (cid:9)t (cid:13) 1 in the following), and that,
> due to the introduction of the additional variable (cid:17)i , Eq. (74) pro-
> vides two roots for each wavenumber k. For a given value of k,
> both roots are real for small enough (cid:9)t and can be developed in
> terms of the quantity ζ ≡ γ∗(k)((cid:9)t)2, that we assume to be small.
> The slower root (positive sign in Eq. (74)) is given by
>
> γ1(k) = γ∗(k)

> After a short transient time (cid:8) |1/γ2| (cid:16) |1/γ∗|, in which value of ˜(cid:17)
> goes from 0 (if initially the “ghost” energy was set to be zero) to
>
> −2αζ ˜T /β (cid:16) ˜T (“ghost” energy is smaller than physical energy),
> the numerical solution approaches asymptotically the exact one
> (γ1 (cid:8) γ∗). Long wavelength components extending over N inter-
> −2 (cid:8) N 2 are
> vals and having an attenuation time ta (cid:8) |1/γ∗| (cid:8) k
> correctly reproduced when ζ (cid:8) k2((cid:9)t)2 (cid:8) ((cid:9)t/N)2 (cid:16) 1. This con-
> dition means that the number of time steps during the character-
> istic attenuation time ta must be larger than N, so that numerical
> propagation of information (one interval per step) along distance
> N can take place. Shorter wavelength modes, although poorly re-
> produced, are strongly damped, as it is the case for the physical
> ones. MULTI2D uses the SSI method with α = 1 and β = 1/2,
> a combination that has been found satisfactory for all the sit-
> uations treated up to now. The accuracy limitations mentioned
> above are not restrictive in the context of strongly nonlinear prob-
> lems, where anyway very small time steps are needed to obtain
> the correct evolution of nonlinear thermal waves; as in the SSI
> method, more than N time steps are required to solve structures
> extending over N cells. To apply Eq. (69), in addition to the ra-
> diation deposition Q i (returned by routine radia), its temperature
> derivative (∂ Q i/∂ T i ) and the value of the thermal capacity associ-
> ated with nodes (∂ E i/∂ T i ) are needed. Different from the implicit
> method (Eq. (67)) and due to energy conservation inherent to the
> SSI method, it is not critical that these quantities are extremely
> accurate. (∂ Q i/∂ T i ) values are evaluated by routine radiader in an
> approximate way. For a node surrounded by optically thin cells,
> one has from Eq. (6)
>
> ∂ Q i
> ∂ T i

> (77)
>
> where the sum extends over cells that have i as a vertex. For opti-
> cally thick situations, ∂ Q i/∂ T i is extracted from Eq. (122), derived
> in Section 6 for diffusive transport, using κ = 16λσ T 3/3π as ther-
> mal conductivity. For intermediate cases, smooth interpolation is
> used. Also provision is taken for the case where one side A B (of
> length l) of an optically thick cell belongs to the free boundary (or
> is in front of an optically thin cell). It will radiate a power given by
> (cid:8) σ πl(r A T 4
> i contribution is added
> A
> to the value of ∂ Q i/∂ T i at its vertices. Finally, the evaluation of
> ∂ E i/∂ T i , for mixtures of materials with tabulated thermodynamic
> properties will be described in detail in Section 6.4.
>
> B ), so that a −4πσ lri T 3

### 第 10 页

> To illustrate the algorithm in an optically thick situation, we
> consider the problem of the radiative heat wave emerging from an
> instantaneous point source. The corresponding analytical solution
> is given in [20] (Ch. X, Sec. 6). A ﬁxed amount of energy is instan-
> taneously released in a point (in the simulation, the initial energy
> of the node at the origin) and launches a spherical self-similar
> thermal wave. The spherical front advances with time, while tem-
> perature decreases. For simulating this problem, we use a 50×50
> rectangular grid, where each quadrangle is divided diagonally into
> two triangles. As in the previous case, only the half space z (cid:3) 0
> has to be simulated. A constant and uniform heat capacity is as-
> sumed, and the radiative mean free path is set to one tenth of the
> grid size, such that cells are optically thick. We use dimensionless
> variables, so that temperature and time are expressed in arbitrary
>
> Fig. 9. Instantaneous point source problem. Radiation temperature plots at different
> times (both in arbitrary units).
>
> units. Fig. 9 shows the radiation temperature distribution (almost
> identical to the matter temperature) at different times. In Fig. 10,
> radial temperature proﬁles obtained by the code (cuts at z = 0) are
> compared with the analytical solution. There is a good agreement:
> the position of the thermal front is correctly determined, and the
> proﬁles are similar. Nevertheless, small differences are visible in
> the region close to the axis of symmetry, where the used dis-
> cretization does not describe diffusive transport accurately, because
> cell size is not small compared with distance to the axis. Also the
> shape of the numerical thermal wave front deviates slightly (about
> 8%) from a sphere.

### 第 13 页

> (105)
>
> 8 The central planar tensor of inertia for a set of unit mass particles located at
>
> the vertices of the cell.

### 第 14 页

> enced.
>
> This information can be used to check data consistency and, if
> necessary, perform data conversion. In addition to numeric arrays,
> other types of data have been deﬁned: null (no data at all), func-
> tion (in this case, address is a pointer to a C-function, and size is
> the number of arguments), and list (the data is an array of pointers
> to “D-structures”). The “D-list” type allows to implement multi-
> level lists of arbitrary depth. Because data is managed by reference,

### 第 15 页

> In addition to the radiation-hydrodynamics algorithms, a num-
> ber of miscellaneous utility routines has been developed to per-
> form creation, manipulation, and deletion of “D-structures”, basic
> arithmetic between numeric data, ﬁle access, operating system in-
> terface, grid generation, . . . . Top level components of MULTI2D and
> other related codes are basically composed of a large amount of
> calls to the appropriate routines. To facilitate their development, a
> special computer language (called r94), human readable and with
> a simple syntax, has been created. Files with r94-code are prepro-
> cessed to generate C code.
>
> All this software has been organized in a modular way: all re-
> lated source ﬁles are stored together in the same “tar” archive,9
> identiﬁed by a unique name, typically a keyword followed by the
> version number. For example, m2d-5.1 corresponds to the algo-
> rithms described in this paper. Each of these “modules” is docu-
> mented and maintained individually, and it must be installed in its
> own subdirectory by converting source ﬁles to C, compiling the C
> code, and creating an object-library. Modules can also be used as
> containers of other types of data, like tables or documents.
>
> The software package supplied through the CPC Program Li-

> (i) r94_2005.tar.gz - installation and control scripts, modules im-
> plementing general purpose libraries, the r94 to C translator,
> a development toolkit (including a graphical user interface),
> and miscellaneous documentation. This subpackage has to be
> installed ﬁrst.
>
> (ii) multi_2008.tar.gz - modules corresponding to the radiation-
> hydrodynamics (m2d-5.1), ﬁle access (multi_data-2.0), ta-
> ble interpolation (matter-2.1), grid generation (malla-5.0), a
> graphical user interface to control job submission, miscella-
> neous graphic post-processors, equation-of-state tables, opac-
> ity tables, and the example described in Section 7.
>
> (iii) README – note with detailed instructions for installation.

> Fig. 12. Graphic user interface.
>
> the results. For each “case”, a user deﬁned code (ﬁle User.r) is used
> to initialize the problem (with the help of several special libraries)
> and pass control to the main integration routine. The shell proce-
> dure RUN translates this r94 code to C, compiles the C code, links
> the object code with the libraries speciﬁed in ﬁle DEPENDENCES to
> generate an executable code, and launches it as a background job.
> User.r contains in fact a main program responsible to carry out the
> following tasks:
>
> (i) Deﬁne the geometry of the grid: initial node positions (ar-
> rays x0 and y0), and, for each triangular cell, the indices of its
> nodes (array tb) and a ﬂag (array ct) indicating if this trian-
> gle is either an independent cell (value 0), or the ﬁrst/second
> half of a quadrangular cell (values 1/2). This task is usually
> accomplished with the help of the grid generation package
> malla-5.0. The utility routine NewTopo uses this basic data
> to generate additional tables needed in different places of
> the code: edge numbering; edge–triangle, edge–node, edge–
> triangle, triangle–edge, and triangle–triangle connectivities; as
> well as a list of edges belonging to the boundary.

> (i) Deﬁne the geometry of the grid: initial node positions (ar-
> rays x0 and y0), and, for each triangular cell, the indices of its
> nodes (array tb) and a ﬂag (array ct) indicating if this trian-
> gle is either an independent cell (value 0), or the ﬁrst/second
> half of a quadrangular cell (values 1/2). This task is usually
> accomplished with the help of the grid generation package
> malla-5.0. The utility routine NewTopo uses this basic data
> to generate additional tables needed in different places of
> the code: edge numbering; edge–triangle, edge–node, edge–
> triangle, triangle–edge, and triangle–triangle connectivities; as
> well as a list of edges belonging to the boundary.
>
> (ii) Set the dynamical state variables: initial velocity (cid:3)v i , internal
> energy E i , and “ghost” energy (cid:17)i at each node i, and masses
> mlk of material number l in cell k. This data (together with
> topological information of (i)) is grouped in a structure called
> hydro, created by routine HydroNew. This task is performed
> usually by the routine AddToHydro that allows to add a mate-
> rial with speciﬁed density and temperature to each cell.
> (iii) The structure hydro and all program parameters are stored
> in a structure called multi created by routine MultiNew. This
> structure stores also user’s functions to deﬁne boundary con-
> ditions (external pressure, kinematic restrictions, incoming ra-
> . . .), matter properties (opacities,
> diation,
> thermal conductivities, beam attenuation, . . .), timing control,
> and output control.
>
> incoming beams,

### 第 16 页

> R. Ramis et al. / Computer Physics Communications 180 (2009) 977–994
>
> are computed by routine HydroEOS. For cells with only one
> material, these values are interpolated directly from tabu-
> lated values T (ρ, e) and P (ρ, e) generated externally, either
> from SESAME library [25] or by MPQEOS code [26]. For cells
> containing L different materials, we treat the materials as not
> mixed, assuming that mechanical and thermal equilibrium
> has been reached with uniform pressure and temperature in-
> side the cell. We have to solve the system:
>
> (cid:17)

### 第 17 页

> in Figs. 16 and 17.
>
> Figs. 16 and 17 show snapshots of matter and radiation temper-
> ature at 10 ns. Matter temperature reaches a maximum value of
> 810 eV in the ﬁlling gas close to the Z -axis, where laser beams
> cross each other. Heating of the ﬁlling gas is due to light ab-
> sorption, modelled here as inverse bremsstrahlung. In contrast, the
> temperature of the ablated beryllium and the gold walls is consid-
> erably lower. Although laser energy impinges directly on the gold
> wall, the gold temperature is limited due to its high opacity. It rep-
> resents a balance between laser heating and cooling by radiation
> emission towards the optically thin cavity and radiation diffusion
> into the optically thick wall. These processes are described by the
> present code with accurate angular resolution. The resultant dis-
> tribution of radiation inside the cavity appears to be quite uni-
> form with temperatures ranging from 100 to 110 eV in this early
> phase of hohlraum heating. The radiation transport algorithm, de-
> spite the discrete number of directions used in the simulations
> (cid:13)
> i=1 Ni = 32) does not produce non-physical concentration of
> (
> rays near the axis of the target (the structure visible at z = 0.2 cm
> is due to the collision between ablated material and hohlraum ﬁll-
> ing).
>
> M

### 第 18 页

> (2003) 095003.
>
> [25] SESAME, Report on the Los Alamos Equation-of-State Library, T-4 group, Report
>
> LALP-83-4, Los Alamos National Laboratory, Los Alamos, NM, 1983.

*本节命中相关段落 25 处。*

## doc/References/2012CPC183.637(Ramis)_MULTI-fs – A computer code for laser–plasma interaction in the fs regime.pdf (1031401 B)

<!-- 共 20 页 -->

### 第 1 页

> Program summary
>
> Program title: MULTI-fs
> Catalogue identiﬁer: AEKT_v1_0
> Program summary URL: http://cpc.cs.qub.ac.uk/summaries/AEKT_v1_0.html
> Program obtainable from: CPC Program Library, Queen’s University, Belfast, N. Ireland
> Licensing provisions: Standard CPC licence, http://cpc.cs.qub.ac.uk/licence/licence.html
> No. of lines in distributed program, including test data, etc.: 49 598
> No. of bytes in distributed program, including test data, etc.: 443 771
> Distribution format: tar.gz
> Programming language: FORTRAN
> Computer: PC (32 bits and 64 bits architecture)
> Operating system: Linux/Unix
> RAM: 1.6 MiB
> Classiﬁcation: 19.13, 21.2
> Subprograms used: Cat Id: AECV_v1_0; Title: MULTI2D; Reference: CPC 180 (2009) 977
> Nature of problem: One-dimensional interaction of intense ultrashort (sub-picosecond) and ultraintense
> (up to 1017 W cm
> Solution method:
> transport
> mechanisms is solved in one-dimensional geometry using a fractional step scheme. Fluid motion together
> with heat diffusion is solved by using an implicit Lagrangian method. Transport by thermal conduction
> and radiation as well as electron–ion energy transfer are treated in a two-temperature (electron and
> ion) model covering the wide range from solid state to high temperature plasma. Laser propagation
> is calculated from the one-dimensional Maxwell equations. Radiation transfer is solved by using the
> forward-reverse method for a discrete number of frequency groups. Matter properties are interpolated
> from tables (equations-of-state, ionization, opacities, and emissivities) generated by external codes. An
> alternative WKB laser deposition package is available to be used for long pulse lasers.
>
> The hydrodynamic motion coupled to laser propagation and several

### 第 2 页

> Recent developments in laser technology have opened new
> laser matter interaction with sub-picosecond laser
> regimes of
> pulses at powers of 1012–1015 W [1]. Focused to intensities beyond
> −2, the interaction leads to relativistic plasma dynam-
> 1018 W cm
> ics that requires kinetic treatment, e.g. by means of particle-in-cell
> (PIC) codes [2]. At lower intensities, however, the hydrodynamic
> approximation is still useful and is actually widely used to describe
> expansion and heating of targets irradiated by femtosecond laser
> pulses [3].
>
> Some signiﬁcant differences exist due to the ultra-short interac-
> tion times. In particular for solid targets, target expansion has less
> time to develop, and therefore laser interaction occurs at much
> steeper fronts (expansion layers on the scale of the laser wave-
> length) than in traditional laser plasma cases, where nanosecond
> laser pulses form ablation layers much thicker than the laser wave-
> length. It also implies energy deposition in denser target material
> (close to solid densities) and typically lower target temperatures.
> This is the regime of warm dense matter that requires special care
> concerning equation-of-state (EOS) and transport properties [4].
>
> The code MULTI-fs described in the present paper responds to
> this new situation. It extends the one-dimensional radiation hy-
> drodynamics code MULTI [5] that is widely used to simulate laser
> plasma interaction on the nanosecond time scale. Most features
> of MULTI are preserved, in particular heat conduction, multi-group
> radiation transport, and external tables for EOS and transport co-
> eﬃcients. Important new features are the two-temperature hydro-
> dynamics and the explicit solution of Maxwell’s equations to deal
> with light matter interaction in steep density gradients. It is impor-
> tant to note that by solving the wave equation also resonance ab-
> sorption is described implicitly. This is impressively demonstrated
> in Ref. [6], reproducing the angular dependence for oblique inci-
> dence and the difference between s and p polarization charac-
> teristic for resonance absorption. The code includes two different
> models describing electron collisions in warm dense matter, in
> particular the transition from plasma to solid behavior. The ﬁrst
> model is based on electron–phonon interaction and was described
> in detail in [3]. The second model involves a frequency-dependent
> collision frequency that allows to describe light absorption also as
> a function of its frequency. This is important to treat interaction
> with high-power short-wavelength radiation which presently be-
> comes available from high harmonics laser and XFEL sources.

> Another important application is the characterization of the ra-
> diative properties of fs-laser plasmas. In such studies the density
> and temperature proﬁles calculated by MULTI-fs are used as input
> for an atomic kinetics code. In this way spectra and pulse duration
> of the emitted X-rays have been calculated [10,11]. Audebert et al.
> [12] have studied, by X-ray absorption spectroscopy, the ionization
> and recombination in plasma generated by ultra short laser pulses.
> −2 μm2 used in these ex-
> At intensities Iλ2 larger than 1016 W cm
> periments, the hydrodynamic model approaches its limits, because
> the electron mean free path starts to exceed the scale length of
> the expanding low density plasma in the region of the critical
> layer, and density proﬁle modiﬁcations due to the light pressure,
> not considered in the code, may modify the plasma proﬁles. Nev-
> ertheless, the agreement with experimental results was found to
> be satisfactory.
>
> The present paper describes the physical model and the nu-
> merical methods used in MULTI-fs and gives a detailed descrip-
> tion of the internal structure of the code. Section 2 is devoted to
> clarify and explain the limits of applicability of the code. In Sec-
> tions 3 to 6, the equations describing hydrodynamics, thermal ﬂux,
> electron–ion relaxation, laser coupling, and electron collision time
> are discussed as well as how they are solved on a spatial grid.
> The problem reduces to a set of ordinary differential equations for
> the values of the physical variables taken at cell centers or inter-
> faces. In Section 7 the discretization in time is discussed and the
> fractional time step for an eﬃcient solution of this system. Sec-
> tion 8 is devoted to the details of the implementation, to available
> options and control parameters. In Section 9, a representative ex-
> ample is presented. Appendix A explains the ﬁle formats used in
> the input tables for equations of state, opacities, and ionization,
> as well as the structure of the output ﬁles. Appendix B presents
> the derivation of the wave equations used to solve laser propaga-
> tion. Thermal radiation transport is typically not relevant for short
> pulse interaction, but clearly plays an important role for long pulse
> interaction with high-Z materials. The corresponding physics and
> an algorithm used to solve the radiation transport are discussed
> in [5]. Because the MULTI-fs, as an extension of the original MULTI
> code, is also able to work in the long pulse regime, we include, for
> completeness, Appendix C describing an upgraded version of the
> radiation package.1
>
> 2. Limits of applicability

### 第 3 页

> P (ρ, e) + P v
>
> (cid:3) ¯¯U .
> ¯¯U is the unit second rank tensor and
> (cid:4)
>
> 2ρ L2(∇ · v)2,
> 0,

> where L is a characteristic length, taken equal to the cell thickness.
> Using this approach, shock waves appear as quasi-discontinuities
> with a thickness of a few numerical cells [24], and at the same
> time, due to its quadratic dependence on velocity gradient, viscous
> effects become negligible everywhere else.
>
> The set of relations { P = P (ρ, e), T = T (ρ, e)} constitute the
> equation-of-state (EOS). As part of MULTI-fs, we consider here the
> QEOS model [4,25], in which the free energy is modeled as the
> sum of electron and ion contributions (plus a binding correction)
> in the form
>
> F (V , T ) = F i(V , T ) + F e(V , T ) + Fb(V ),
> where T denotes temperature and V = 1/ρ the speciﬁc volume. In
> the plasmas considered here, both electrons and ions are assumed

### 第 4 页

> Here δ takes the values 1, 2, and 3, for planar, cylindrical, and
> spherical geometry, respectively.
>
> to be in a state close to a thermal distribution, each species hav-
> ing its own temperature. This accounts approximately for systems
> having components of vastly different masses in which species
> thermalize much faster by themselves than among each other. Un-
> der these circumstances, the additive splitting in Eq. (6) into an
> electron and an ion EOS is valid, and then pressures, entropies,
> and speciﬁc internal energies are given by
>
> (cid:5)
> (cid:5)
> P = P i(V , T i) + P e(V , T e) = − ∂ F i
> (cid:5)
> (cid:5)
> ∂ V
> (cid:5)
> (cid:5)
> S = S i(V , T i) + Se(V , T e) = − ∂ F i
> (cid:5)
> (cid:5)
> ∂ T

### 第 5 页

> 641
>
> Table 1
> Some values of the coeﬃcient α(Z ) compared with Eq. (28).
>
> Z

> (27)
>
> where ne = Zρ/( Ammp) is the electron number density, Z and Am
> the averaged ion charge and mass number, k Boltzmann’s constant,
> T e electron temperature, me and mp mass of electron and proton,
> and νe is the electron collision frequency. The numerical coeﬃcient
> α(Z ) depends on the ion number Z , and a few values are listed in
> Table 1. The expression implemented in the code
>
> α(cid:8)

> 4 The set of quantities deﬁning the state of the simulation at a given time.
>
> instead of K . For small temperature gradients, Fick’s law (Eq. (26))
> is recovered. We emphasize that the f -factor is an adjustable pa-
> rameter that affects the global hydrodynamic proﬁles signiﬁcantly;
> typically, it has been set to f = 0.6 in MULTI-fs simulations [3].
>
> As stated above, the energy ﬂuxes are centered at interfaces.
> The temperature gradient at interfaces 1 < j < N + 1 is computed
> from cell temperatures by

> (33)
>
> are computed at interfaces, and ﬁnally Sth, j
> is obtained at in-
> terfaces by means of Eqs. (30), (31), and (26). For interfaces 1
> and N + 1, the thermal ﬂux is assumed to be zero. Finally, the
> power per unit of volume transferred from electrons to ions is ob-
> tained by directly evaluating
>
> Q ei = 3νemenek

### 第 6 页

> 5 I L is the laser intensity in the direction of beam propagation. For oblique inci-
>
> dence, the laser power incident per unit of target area is I L cos θ .
>
> 6 Although it can be changed by input options, in this section we have in mind
> laser irradiation incident from r = +∞, as it is the case of cylindrical or spherical
> targets.

### 第 7 页

> 6. Electron collision frequency
>
> The collision frequency between electrons and ions, νe , is a
> most important physical quantity in the context of the present
> paper. It governs e.g. laser absorption, electron–ion energy trans-
> fer, electronic heat conduction, electrical conductivity, energy loss
> of ion beams, and other processes relevant to MULTI-fs users. For
> high temperature, weakly coupled, fully ionized plasmas, a well
> established classical theory exists [13,23]. The parametric depen-
> dence of νe on temperature and other parameters, however, com-
> pletely changes for warm dense matter (WDM) and metal-like
> solids, when electrons become degenerate and other quantum be-
> havior sets in, involving bound electrons and strong ion–ion corre-
> lations. The transition from classical plasma to metal-like behavior
> in not well understood, and typically ad hoc interpolation between
> the two regimes is used. In MULTI-fs, two such models are imple-
> mented in addition to the classical description and can be used
> alternatively. They both give qualitatively reasonable descriptions
> when compared with experimental results, be it at the price of
> some arbitrariness in the choice of adjustable parameters.
>
> 6.1. Classical plasma

### 第 8 页

> R. Ramis et al. / Computer Physics Communications 183 (2012) 637–655
>
> Table 2
> Comparison of collision frequencies measured at room temperature (293 K) with
> model values given by Eq. (62) with Kds = 1.
>
> ν (1013 s

> For T e → ∞, expression (62) becomes parametrically identical to
> the collision frequency Eq. (52) of a classical plasma; on the other
> hand, for T e → 0, the warm dense matter result Eq. (59) is re-
> covered, multiplied by a free parameter Kds. This parameter may
> account for solid state effects such as an effective electron mass.
> In the code, the default value is set to Kds = 1, but Kds can also be
> used to adjust the model to measured values.
>
> The full dependence of the effective collision frequency νe(T e,
> ω) on electron temperature T e and frequency ω is shown in Fig. 2,
> for the case of aluminum at solid density. It is seen that νe(T e, ω)
> −1 at temperatures in
> reaches maximum values of almost 1016 s
> the region of 10–100 eV and also as a function of photon en-
> ergy at values of ¯hω ≈ 50 eV. Below these values of T e and ¯hω,
> the collision frequency decreases almost linearly by three orders
> of magnitude. This is due to Pauli blocking (the factor F (T e, ¯hω))
> that reduces the number of electrons available for scattering in a
> degenerate plasma. In Table 2 a few values measured at different
> frequencies for solid aluminum at room temperature are compared
> with Eq. (62). Apparently, the model describes also the increase of
> νe(T e, ω) with frequency in a semi-quantitative way. There is no
> need to use different ﬁt factors Kds for the collision frequency in
> slow (ω = 0) processes like electron–ion energy transfer and heat
> conduction and fast processes like laser absorption, as this was the
> case in model 2 described in Section 6.2. Also the linear rise of
> νe(T e, ω) as a function of temperature at ﬁxed ω for T e < T F is
> obtained correctly. The plots of the test case in Section 9 look al-
> most identical when obtained with either model 1 (Section 6.2)
> containing 3 ﬁtted values or model 2 (this section) with Kds = 1.
>
> The hydrodynamic equations (16)–(18), (22), and (25), derived
> in Section 2, determine the evolution of the set of the state vec-
> tor variables: densities (ρ j ) as well as speciﬁc internal energies of
> electrons (ee, j ) and ions (ei, j ) at cell centers, the velocities (v j ) of
> interfaces, and the position (r1) of the ﬁrst interface. Mass (m j )
> and composition of cells are constant in a Lagrangian scheme. As
> indicated at the end of Section 2, interface positions (except r1) are
> considered as subsidiary quantities. Pressures and temperatures of
> species ( P e, j , P i, j , T e, j , and T i, j ) are computed as functions of den-
> sities and speciﬁc energies. Energy deposition and transfer terms
> ( Q ei, j , De, j and S j ) in Eqs. (17)–(18) are determined from state
> variables by the methods described in Sections 4 to 6, and in
> Appendix C. One can state that the problem has been formally re-
> duced to a set of 4 × N + 2 ordinary differential equations (ODE)
> that determine the evolution of a set X of 4 × N + 2 time depen-
> dent variables7:

> (60)
>
> Fig. 2. Effective collision frequency νe(T e, ω) given by Eq. (62) is plotted versus
> electron temperature T e and photon energy ¯hω for aluminum at solid density ρ0 =
> 2.7 g/cm3 and Kds = 1. The ion charge Z (ρ0, T e) is taken from the ionization table,
> starting with Z = 2.23 at low temperature.
>
> νe(T e, ω) needed for laser collisional absorption, both in its depen-
> dence on electron temperature T e and light frequency ω.

### 第 9 页

> (cid:13)
> R (˜xNG ) + w NG Q L(˜xNG , ˜tNG )
> Q NG
>
> xNG
> Xn+1 = xNG .
> (67)
> Here xi are intermediate values of X , and ˜xi and ˜ti are the values
> used to evaluate the derivatives. For explicit evaluation, one takes
> ˜xi = xi−1 and ˜ti = tn, and for fully implicit evaluation, ˜xi = xi and
> ˜ti = tn+1. One can show that the truncation error of this procedure
> is proportional to ((cid:14)t)2, so that the method has only ﬁrst order ac-
> curacy in time. In the implementation in MULTI-fs, the laser depo-
> sition is evaluated explicitly from the values of X already available,
> while hydrodynamic and radiative terms are computed implicitly.
> This makes the full algorithm unconditionally stable. Restrictions
> on time step size (cid:14)t are imposed by accuracy considerations. Ba-
> sically, the user must specify the maximum relative variation of
> density, electron temperature, and ion temperature in the substeps
> of Eq. (67).
>
> In applications, the number of radiation groups can be large and
> consume most of the CPU time, while the time step is restricted by
> the hydrodynamic substep. This situation is alleviated if the ﬁrst
> term in Eq. (66) is divided into N S components (N S must be a
> divisor of NG ) that are distributed among the radiative terms. To
> improve the accuracy, the radiative groups are redistributed so that
> between two hydrodynamic substeps there are radiation groups of
> assorted frequencies. In this way, each time step is divided into N S
> subcycles. The complete time step is performed as follows:

> In applications, the number of radiation groups can be large and
> consume most of the CPU time, while the time step is restricted by
> the hydrodynamic substep. This situation is alleviated if the ﬁrst
> term in Eq. (66) is divided into N S components (N S must be a
> divisor of NG ) that are distributed among the radiative terms. To
> improve the accuracy, the radiative groups are redistributed so that
> between two hydrodynamic substeps there are radiation groups of
> assorted frequencies. In this way, each time step is divided into N S
> subcycles. The complete time step is performed as follows:
>
> (ii) Begin a new subcycle. From x, interpolate in equation-of-state
> (EOS) tables to obtain ionization ( Z ), temperatures (T e , T i ),
> pressures ( P e , P i ), and their derivatives with respect to den-
> sity and energies. This linearized EOS is assumed to be valid
> during the current subcycle.
>
> (iii) Obtain speciﬁc laser deposition Q L at time t + 1

> 8. Code description
>
> The model described in previous sections has been imple-
> mented as a FORTRAN program. Control parameters are read as
> namelist blocks from I/O unit 12 (normally ﬁle fort.12). These
> blocks can be placed in arbitrary order (except LAYER blocks).
> Some of them are mandatory, while others are optional. In the
> latter case, if they are missing, either default values are assumed
> for the parameters or some part of the model is switched off (for
> example laser absorption). Maximum array sizes are deﬁned in pa-
> rameters statements. For example, to allow a larger number of cells,
> NMAX must be changed at all places it appears. The program units
> have been grouped in several sections that are described below.
>
> 8.1. Initialization

### 第 10 页

> R. Ramis et al. / Computer Physics Communications 183 (2012) 637–655
>
> Table 3
> Parameters in mandatory namelist block GEOMETRY.
>
> IGEO
> XMIN
> IRIG

> 1 for planar, 2 for cylindrical, and 3 for spherical geometry.
> minimum value of r coordinate at initial time.
> if this value is 0, the ﬁrst interface can expand freely, if it is 1,
> a rigid wall is assumed at r = XMIN.
> cells from 1 to NFUEL can contain deuterium–tritium thermonu-
> clear fuel mixture (put NFUEL = 0 to inhibit thermonuclear pro-
> cesses).
>
> Table 4
> Parameters in namelist blocks LAYER (one for each material layer).
>
> NC
> THICK
> ZONPAR
> R0
> TE0
> TI0
> ZMOL
> ZION
> IME
> IMI
> IZ
> IP
> IR
> IE

> −3).
>
> number of cells in this layer.
> layer thickness (in cm).
> zoning parameter (see text).
> initial mass density (in g cm
> initial electron temperature (in eV).
> initial ion temperature (in eV).
> material atomic mass number.
> material atomic number.
> ID code of electron EOS tables: P e(ρ, ee), T e(ρ, ee).
> ID code of ion EOS tables: P i (ρ, ei ), T i (ρ, ei ).
> ID code of ionization table: Z (ρ, T e).
> ID code of Planck opacity table: χ P
> ID code of Rosseland opacity table: χ R
> k (ρ, T e).
> ID code of NON-LTE emissivity table: (cid:19)k(ρ, T e).
>
> k (ρ, T e).

> if the value is unity, the mesh is uniform, and,
>
> Thus,
> if it is
> the left/right
> greater/less than one, a ﬁner zoning occurs at
> side of the layer. Negative values of this parameter generate
> ﬁner zoning at both sides (|ZONPAR| > 1) or in the center
> (|ZONPAR| < 1). Matter properties are interpolated in tables read
> from ﬁle fort.13. These tables are formatted as described in
> Appendix A, and each has a unique identiﬁer (referenced as an in-
> teger in the LAYER blocks). If IZ is set to zero for some material,
> the material is assumed to be completely ionized with Z = ZION,
> and, if IE is set to zero, the normalized emissivity9 (cid:19)k is assumed
> to be equal to one. The number of groups NG and the frequency
> interval of each group are computed from the loaded opacity and
> emissivity tables. If the group distribution of different tables over-
> lap, a common group distribution is generated as schematized in
> Fig. 3.
>
> Finally, before starting integration, the namelist block PLASMA
> described in Table 5 is read to deﬁne the model used for plasma
> collisions and transport.

> 9 See Appendix C.
>
> Fig. 3. Frequency groups generated from two overlapping tables. Each frequency in-
> terval corresponds to different tables; e.g. for group 3, tables b and e are used.
>
> Table 5
> Parameters in mandatory namelist block PLASMA.

> 0 – use the classical model of Section 6.1.
> 1 – use the electron–phonon model of Section 6.2.
> 2 – use the Drude–Sommerfeld model of Section 6.3.
> minimum value of ionization Z , used to avoid numeric singular-
> ities (e.g. if ne = 0, as occurs when starting simulations of no-
> metals at room temperature).
> ﬂux limit factor f for electron heat transport in Eq. (29).
> factor Kwdm in Eq. (56) used to compute heat transport conductiv-
> ity (only if MODEL=1).
> factor Kwdm in Eq. (56) used to compute electron–ion transfer
> (only if MODEL=1).
> factor Kwdm in Eq. (56) used to compute laser absorption (only if
> MODEL=1).
>
> Table 6
> Parameters in mandatory namelist block TIMING.
>
> NSPLIT

> rejected, and a new time step is tried with (cid:14)t ← (cid:14)t/2. The pro-
> cess is repeated until success is attained. Afterwards, a new value
> of (cid:14)t is estimated with the goal to get the maximum relative vari-
> ations of density and temperature close to the prescribed value
> VARNON. Finally, the weights wk (see Section 7) are computed by
> routine WCTRL.
>
> During the numerical integration, output is written, either in
> raw ﬁle fort.10 or in alphanumeric format in the standard out-
> put stream, at speciﬁed step numbers or time values. All this is
> controlled by the parameters in the namelist block TIMING de-
> scribed in Table 6. For situations in which a more detailed output
> is needed during some special time interval, the optional namelist
> block DETAIL described in Table 7 is available. The integration
> routine returns, in array STRAHL, a very detailed description of

### 第 11 页

> 647
>
> Table 7
> Parameters in optional namelist block DETAIL.
>
> Table 8
> Parameters in optional namelist block OPTIONS.

> (71)
>
> Table 9
> Parameters in optional namelist block PULSE_MAXWELL.
>
> νk+1(cid:26)

> νk
>
> This information is usually too detailed. Normally only some values
> at speciﬁc locations (i.e. S+ at the right boundary) or integrated
> k Sk, j ) are really needed to be stored in fort.10.
> quantities (i.e.
> The selection of these radiation quantities is speciﬁed by putting
> lines in ﬁle fort.19 formatted either as:
>
> (cid:29)

> name <= code( j).
>
> The ﬁrst format is used to add quantities from groups k1 to k2. The
> user deﬁned mnemonic symbol name can have up to 8 characters,
> and code is one of:
>
> – S, S+ or S-, the total radiation ﬂux or its forward/backwards

> terface area (1, 2π r, or 4π r2).
> – U, the density of radiation energy.
> – TR, the radiation temperature, deﬁned by Eq. (133).
>
> The second format is used to select spectral quantities at interface
> j. In that case code is one of:
>
> – I+ or I-, the radiation intensity (power per unit of area, solid

> PITIME
> WL
> ITYPE
> TMAX
> IDEP
> ANGLE
> POL
>
> 1, laser incides from the right.
> −1, laser incides from the left.
> (P max) maximum laser intensity (power per unit of area in the
> direction of propagation, expressed in cgs units).
> (τ ) pulse duration FWHM (s).
> laser wavelength (cm).
> pulse type (from 1 to 3).
> (tmax) auxiliary time used in some pulse types (s).
> each cell will be divided in IDEP subintervals.
> incidence angle (in degrees).
> polarization, either ‘P’ or ‘S’.
>
> block OPTIONS described in Table 8 allows to control special as-
> pects of the simulation. Radiative transport and hydrodynamics
> can be artiﬁcially inhibited. Such non-physical settings are useful
> to assess the relative importance of these phenomena in a given
> problem. Also when opacity tables are not available and it is well
> known that radiative transfer does not play any role in the prob-
> lem, one can load arbitrary tables and set IRADIA=0.

> 8.3. Time step
>
> The subroutine SCHRITT tries to advance all variables from
> values at time t to values at time t + (cid:14)t, using the fractional
> step method described in Section 7. The interpolation subrou-
> tine EOS is called twice in each subcycle to compute pressures
> and temperatures of electrons and ions as well as their ther-
> modynamical derivatives with respect to energy and mass den-
> sities. The subroutine ZBR is called to obtain average ionization
> by table interpolation (if no table is given, full ionization is as-
> sumed). Laser deposition is obtained by adding the values returned
> by LASER_MAXWELL and LASER_WKB. The code also contains a
> package to manage thermonuclear fusion reactions. When this part
> is active, the fuel depletion is advanced here and the heating of
> electron and ion species by non-local non-instantaneous α-particle
> deposition is computed. Because this physics is not relevant to
> short pulse irradiated foils, this package is not described in this pa-
> per. To inhibit fusion reactions just set NFUEL=0 in namelist block
> GEOMETRY. The hydrodynamics is now advanced by calling rou-
> tine HYDRO described in Section 8.5. Afterwards the subroutine
> GROUP, described in Section 8.6, is called to solve the radiation
> transport for the NG /N S frequency groups assigned to the cur-
> rent subcycle. After each call to HYDRO and GROUP, the maximum
> relative variation of density and temperature is computed by sub-
> routines VARIA2 and VARIA3. In case a negative temperature is
> detected, the time step is aborted immediately.
>
> 8.4. Laser deposition

> 10 Radiation magnitudes are deﬁned in Appendix C.
> 11 First the values of U k, j are interpolated at internal interfaces and extrapolated
> at boundaries. The resulting values are combined with Sk, j to obtain S+,k, j and
> S−,k, j from Eqs. (104)–(105).
>
> The two available algorithms to compute laser deposition, as
> described in Sections 5.1 and 5.2, are implemented in the sub-
> routines LASER_MAXWELL and LASER_WKB, respectively. These
> subroutines are activated by the presence of namelist blocks
> PULSE_MAXWELL and PULSE_WKB, described in Tables 9 and 10,

### 第 12 页

> R. Ramis et al. / Computer Physics Communications 183 (2012) 637–655
>
> Table 10
> Parameters in optional namelist block PULSE_WKB.
>
> INTER

> TMAX
>
> 1, laser incides from the right.
> −1, laser incides from the left.
> (P max) maximum laser power in cgs units (if IGEO=1 or if
> IGEO=2, power per unit of area, or unit of length, respectively).
> (τ ) pulse duration FWHM (s).
> laser wavelength (cm).
> pulse type (from 1 to 3).
> fraction of power at the critical surface that is absorbed by reso-
> nance (parameter (cid:14) in Section 5.2).
> (tmax) auxiliary time used in some pulse types (s).
>
> in the input ﬁle. The two subroutines can be selected indepen-
> dently, although in normal operation only one is used. As input
> they receive the plasma conﬁguration (densities, temperatures,
> ionization, atomic number, and mass of the cells) and as output
> they return the power deposition per mass unit in each cell. In
> the case of the Maxwell solver, each hydrodynamic cell is sub-
> divided in IDEP equal subcells to improve accuracy. The value
> of IDEP must therefore be chosen large enough in order not to
> miss the necessary resolution required for the absorption process.
> The values of the thermodynamic variables, all of them deﬁned
> at cell centers, are ﬁrst obtained at interfaces and then interpo-
> lated for subcell centers. From these values the collision frequency,
> the electron number density (relative to the critical density), and
> the subcell thickness (expressed in terms of vacuum wavelength)
> are computed and passed on to subroutine DEPOS, where the al-
> gorithm described in Section 5.1 is applied to compute subcell
> deposition. After return, the total deposition into each cell is ob-
> tained by adding the contributions of their subcells. On the other
> hand, for the WKB solver, the cell values are passed directly to
> routine ATENUA. In both routines, in order to account for laser
> light coming from either the right-hand side (INTER=1) or from
> the left-hand side (INTER=-1), the data arrays are reversed as
> needed. Both routines compute ﬁrst the deposition normalized to
> incident power, and then multiply it by the power corresponding
> to the pulse shape selected by parameter ITYPE. The currently
> implemented values are:

> where ε is a suﬃciently small quantity and δ j is an array of zeros,
> except j-th element that takes the value 1. Because the implicit
> treatment of the equations is required only to ensure stability,
> some simpliﬁcations can speed up the code without spoiling the
> accuracy (of ﬁrst order in time).
>
> In addition to use a linearized EOS, the values of interface
> (cid:8)
> area A j , ionization Z j , effective heat conductivity K
> j , and ion–
> electron relaxation coeﬃcient (Q ei, j/(T i, j − T e, j)) are computed
> from x0 (and r1) and are assumed constant from t to t + (cid:14)(cid:8)
> t. The
> evaluation of the Jacobian by Eq. (76) would require in principle
> 4N + 2 evaluations of f . Nevertheless, due to the fact that the in-
> ﬂuence of the j-th element of x extends only from f j−4 to f j+4,
> the number of evaluations can be reduced to 10. The subroutine
> ABLTNG actually evaluates f (x). The resulting nine-banded sys-
> tem of linear equations for x1 is solved by direct inversion. Finally
> the subroutine HYDRO advances the position of the ﬁrst interface
> r1 by:
> (cid:2)
> t + (cid:14)
>
> = r1(t) + v 1(t + (cid:14)(cid:8)

> (79)
>
> This equation, together with the radiation equations (126)–(128),
> (130), (131) for group k, allows to obtain the radiation ﬁeld (Uk, j at
> cell centers and Sk, j at interfaces) as well as the increment of cell
> temperatures (cid:14)T e, j . The parameters for the boundary conditions
> in Eqs. (130), (131) are obtained from the namelist block RBOUND,
> described in Table 11. As it was done with hydrodynamics, laser
> deposition, interface areas, thermodynamic derivatives, opacities,
> and emissivities are computed using the values at the beginning of
> the subcycle. The only non-linearity remaining in the system, the
> Planckian radiative intensity, is linearized as:
>
> 12 The value of r1 is treated separately.

### 第 13 页

> 649
>
> Table 11
> Parameters in mandatory namelist block RBOUND.
>
> TBATH
> ALPHAL
> ALPHAR
> BETAL
> BETAR

> 9. Example
>
> As an illustration of code performance, we present the simula-
> tion of an aluminum foil 150 nm thick, irradiated by a laser pulse
> −2
> of 150 fs (FWHM) duration, 400 nm wavelength, 1015 W cm
> peak intensity, and normal incidence. The pulse shape is given by
> −2.
> Eq. (72) with a total duration of 300 fs and a ﬂuency of 150 J cm
> This case is representative of the parametric study on laser–matter
> interaction reported in [3]. Equation of state tables generated by
> MPQeos code [25], and opacities and ionization tables generated by
> the SNOP code [39,40] (in the LTE approximation and using 20 fre-
> quency groups) were used in these calculations. No strong inhibi-
> tion of thermal ﬂux is assumed ( f = 0.6) and the electron–phonon
> plasma model of Section 6.2 is used with empirical coeﬃcients
> Kwdm in Eq. (56) taken equal to 8, 2, and 25, for heat transport,
> ion–electron interchange, and laser absorption, respectively. The
> time evolution of this target can be followed in Figs. 4–7 that dis-
> play electron temperature, density, ion temperature, and radiation
> temperature, as functions of mass coordinate13 m and time t. Fig. 8
> shows the motion of the Lagrangian interfaces. The mesh has suc-
> cessively ﬁner zoning toward the irradiated side, where most of
> the interaction takes place.
>
> The front layers expand rapidly, having velocities up to a few
> −1. As a consequence, the laser energy is no longer de-

> 107 cm s
>
> 13 The mass coordinate is deﬁned as the mass per unit of area to the left of a given
> position. It remains constant for a ﬂuid particle.
>
> Fig. 6. Same as Fig. 4, but for ion temperature T i (m, t). Ions are heated by elec-
> trons due to energy exchange and cooled by hydrodynamical expansion close to the
> irradiated surface.

### 第 14 页

> pulse is switched off, the heat wave propagates further into the
> solid. However, its propagation velocity slows down, because there
> is no more heating by the laser and the temperature consequently
> decreases.
>
> The same physical conﬁguration has be calculated using the
> Drude–Sommerfeld model described in Section 6.3. Results, shown
> in Fig. 10, agree qualitatively with the ones obtained by the model
> of Section 6.2 (Fig. 9). Although at ﬁrst glance both ﬁgures are
> quite similar, some differences in the main parameters exist. This
> discrepancy is due to the fact that both models include several
> ad hod interpolation procedures and cut-offs. These differences are
> summarized in Table 12, where also have been included the results
> obtained when radiative transport is switched out.
>
> Fig. 10. Same as Fig. 9, but using the model of Section 6.3 for the collision frequency.

> Fig. 10. Same as Fig. 9, but using the model of Section 6.3 for the collision frequency.
>
> Table 12
> Main results obtained for reference case, using the two collisionality models de-
> scribed in Sections 6.2 and 6.3, also the values obtained using the model of Sec-
> tion 6.2 but without radiation transport.
>
> Model

### 第 15 页

> Appendix A. File formats
>
> Tables for equations of state, ionization, opacity and emissivity
> data are stored as plain text ASCII ﬁles composed of lines with a
> maximum length of 60 characters. Each line contains up to 4 ﬁelds
> of 15 characters (either a text string or a ﬂoating point number)
> and ends with the LF character (ASCII code 10).14 MULTI-fs reads
> matter properties from ﬁle fort.13, containing consecutive ta-
> bles, each formed by a block of lines. The head line of each table
> deﬁnes type and structure of the table. For most of the tables, data
> is given for the nodes of a regular grid of size NR × NT with den-
> sity and temperature as independent variables. Data is sorted by
> increasing values of density and temperature; the ﬁrst NR items
> correspond to the ﬁrst value of temperature, the items from NR + 1
> to 2 × NR correspond to the second value of temperature, etc. In
> the case of equation of state tables, pressure and temperature are
> given as functions of density and (cid:14)e = e − e0; the speciﬁc inter-
> nal energy above the cold energy e0(ρ) ≡ e(ρ, T ref ), where T ref
> is a suﬃciently small reference temperature. The one-dimensional
> function e0(ρ) is included as part of the table. The ﬁrst ﬁeld of
> the head line is a table identiﬁer ID matching the values given in
> the LAYER namelist blocks in input ﬁle. The structure of the rest
> of the table depends on table type.
>
> ’PLANCK M’ – Multi-group Planck opacity.
> ’ROSSELAND M’ – Multi-group Rosseland opacity.
> ’EPS M’ – Multi-group emissivity.
> ’ 0.70000000E+01’ the same as ’PLANCK 1’.
> ’ 0.40000000E+01’ the same as ’ROSSELAND 1’.

> ’PLANCK M’ – Multi-group Planck opacity.
> ’ROSSELAND M’ – Multi-group Rosseland opacity.
> ’EPS M’ – Multi-group emissivity.
> ’ 0.70000000E+01’ the same as ’PLANCK 1’.
> ’ 0.40000000E+01’ the same as ’ROSSELAND 1’.
>
> • Field 3 – NR: the number of tabulated densities.
> • Field 4 – NT: the number of tabulated temperatures.
>
> – Second line (only for multi-group tables):

> −3).
>
> • NR values of the decimal logarithm of ρ (g cm
> • NT values of the decimal logarithm of T e (eV).
> • NR × NT values of the decimal logarithm of the quantity.
> The tabulated opacities are the values deﬁned by Eqs. (113)
> and (118) divided by the mass density, χ P
> k /ρ,
> −1. The normalized emissivity given by
> expressed in cm2 g
> Eq. (114) is non-dimensional.
>
> k /ρ and χ R

> k /ρ and χ R
>
> For multi-group opacity data, several tables with the same ID and
> different frequency ranges are needed for each type of opacity. For
> one-group tables, the frequency range is assumed to cover the full
> spectra (ν1 = 0, ν2 = ∞).
>
> A.1. Inverted equation of state

> conditions is usually stored here).
>
> • Field 3 – NR: the number of tabulated densities.
> • Field 4 – NE: the number of tabulated energies.
>
> – Subsequent lines15:

> – Head line:
>
> • Field 1 – Identiﬁer.
> • Field 2 – Table type: ’ 0.60000000E+01’.
> • Field 3 – NR: the number of tabulated densities.
> • Field 4 – NT: the number of tabulated temperatures.
>
> – Subsequent lines:

> – Head line:
>
> • Field 1 – Identiﬁer.
> • Field 2 – Table type:
>
> ’PLANCK 1’ – One group Planck opacity.
> ’ROSSELAND 1’ – One group Rosseland opacity.
> ’EPS 1’ – One group emissivity.

> ’PLANCK 1’ – One group Planck opacity.
> ’ROSSELAND 1’ – One group Rosseland opacity.
> ’EPS 1’ – One group emissivity.
>
> 14 CR characters (ASCII code 13) after LF are ignored.
> 15 Four values in each line, except in the last one.
> 16 The conversion to the internal units of the code is done by routine EOSCU
> −2).
> (1 eV = 11605 K, 1 Mbar = 1012 g cm
> 17 Notice that temperature is expressed in eV in the opacity tables but in KeV in
> the ionization tables!
>
> −1 s

> −1 s
>
> Under control of the parameters in namelist blocks TIMING
> and DETAIL, unformatted output is generated in ﬁle fort.10,
> appropriately structured to be easily readable by graphic post-
> processors. This ﬁle is composed of two sections: the ﬁrst giving
> static data (for example, cell masses), the second with dynamic
> data (changing with time). Each section is composed of several
> records containing several words. In the current implementation18
> each word is an ASCII formatted line of text. The structure of one
> section is:
>
> – First record: an integer number indicating the number of items

> Appendix B. Laser wave propagation
>
> Maxwell’s equations in Gaussian units have the form
>
> ∇ × E + 1
> c
> ∇ × B − 1
> c

> (81)
>
> 18 A more eﬃcient (but non-portable) implementation would be obtained by sim-
> ply storing each word in 8 consecutive bytes.

### 第 17 页

> Fig. 12. Deﬁnition of symbols and photon trajectory for spherical geometry.
>
> Fig. 11. Deﬁnition of coordinates and unit vectors for cylindrical geometry.
>
> new feature, not yet described in [5], is one-dimensional radiation
> transport in spherical and also cylindrical geometry.

> new feature, not yet described in [5], is one-dimensional radiation
> transport in spherical and also cylindrical geometry.
>
> The basic quantity describing radiative transfer is the spectral
> intensity I(r, n, ν) (photon energy ﬂux per units of solid angle and
> frequency at position r in propagation direction n at frequency ν).
> It is determined by the transfer equation [13,41]:
>
> n · ∇ I = η − χ I,

> (99)
>
> where η(r, ν) is the spectral emissivity and χ (r, ν) the spec-
> tral absorption coeﬃcient, assumed here to be independent on n
> (isotropic media). For one-dimensional planar media, I = I(r, μ, ν),
> with r = r · ur being the longitudinal coordinate and μ = n · ur the
> cosine of the angle between propagation direction and ur , the unit
> vector normal to the target, Eq. (99) can be written as
>
> μ

> (cid:26)
>
> and the energy density (per unit of frequency)
> U ≡ 1
> c
>
> I dn = 2π (I+ + I−)

> (cid:3)
>
> expressing the energy conservation. Here δ takes values 1, 2, and
> 3 for planar, cylindrical, and spherical geometry, respectively, and
> 4πη and χ cU are the emitted and the absorbed power (per unit of
> volume and frequency). An additional equation is needed to close
> the problem and to determine the radiation ﬁeld completely. It is
> derived by integrating Eqs. (100)–(102) over the direction domain
> deﬁned by n · ur + (cid:19) < 0, where (cid:19) is a suﬃciently small positive
> value, to obtain
>
> −π

> (108)
>
> Finally, for cylindrical geometry, one has I = I(r, θ, ϕ, ν), with r be-
> ing the distance to the axis of symmetry and n = sin θ(cos ϕur +
> sin ϕuψ ) + cos θ uz, where {ur, uz, uψ } are the unit vectors asso-
> ciated to cylindrical coordinate system, as shown in Fig. 11. Now
> Eq. (99) takes the form [41,42]
>
> (cid:10)

> (103)
>
> The energy ﬂux (per unit of frequency) then takes the form
>
> (cid:26)

### 第 18 页

> present work (see e.g. [42]). All the arguments given above can be
> also applied to the case of cylindrical geometry.
>
> The values of χ and η, that appear in Eqs. (107) and (108), can
> be obtained from atomic physics models. In the example of Sec-
> tion 9, these quantities have been computed by the code SNOP [39,
> 40] as a function of frequency, matter density, and matter temper-
> ature. The range of variation of ν is divided into a certain number
> NG of intervals, denominated “groups”. For group k, deﬁned by the
> frequency range νk−1 < ν < νk (with ν1 = 0 and νNG +1 = ∞), the
> spectrally integrated energy density (Uk(r, t) =
> U (ν, r, t) dν)
> (cid:27)
> νk
> and ﬂux (Sk(r, t) =
> S(ν, r, t) dν) are modeled by equations
> νk−1
> similar to Eqs. (106) and (108), but with appropriately averaged
> values of emissivities and opacities. To derive these equations, one
> considers ﬁrst an optically thin, freely radiating cloud from which
> all emitted photons can escape. In that case, the radiated power
> per unit of volume is
>
> νk
> νk−1

> where χ R
>
> k is the so-called “Rosseland opacity” for group k
>
> νk(cid:26)

> χ P
>
> k is the so-called “Planck opacity”,
>
> νk(cid:26)

> k, j , (cid:19)k, j , and U P
>
> where χ P
> k, j are computed from thermodynamic
> quantities (ρ j and T e, j ) at cell
> j. On the other hand, the term in
> parenthesis in Eq. (120) plays the role of an effective opacity χ eff :
> the Rosseland opacity χ R plus the “geometric” opacity (δ − 1)/2r.
> Its value at internal interfaces 1 < j < N + 1 is obtained from opac-
> ity values at cell centers and from coordinates by

*本节命中相关段落 64 处。*

## doc/References/2016CPC(Ramis)_MULTI-IFE=A 1D computer code for IFE target simulations.pdf (1749702 B)

<!-- 共 13 页 -->

### 第 1 页

> No. of bytes in distributed program, including test data, etc.: 3798542
>
> Distribution format: tar.gz
>
> Programming language: Fortran 95.

### 第 2 页

> 227
>
> temperature (for electrons and ions) model. Laser propagation is treated by 3D tracing of the laser rays in
> the geometrical optics approximation. Radiation transfer is solved by using the forward–reverse method
> for a discrete number of frequency groups. Matter properties are interpolated from tables (equations-of-
> state, ionization, and opacities) generated by external codes.
>
> Restrictions: The code has been designed for typical conditions prevailing in inertial confinement fusion
> (ps–ns time scale, matter states close to local thermodynamic equilibrium, and negligible radiation
> pressure). A wider range of situations can be treated, as long as the above conditions are fulfilled. This
> includes, in particular, laser plasma experiments at moderate intensities (≤1016 W cm−2).
> Unusual features: An optional graphical post-processing package is included in the distribution. This option
> requires a Linux/Unix operating system with the essential developing tools (C compiler; X11 libraries and
> include files; and the xterm command). Most of the figures in this paper have been created using this
> software.

> Inertial Fusion Energy (IFE) [1–4] represents one of the two
> main approaches to the civilian exploitation of nuclear fusion
> energy. IFE production is based on the implosion and ignition
> of spherical microcapsules containing few milligrams of deu-
> terium–tritium mixture. Implosion can be driven by either direct
> irradiation of the capsules by laser beams (direct drive) or by ex-
> posing the capsules to a high temperature thermal radiation (in-
> direct drive). Because of the huge size and costs of experimen-
> tal facilities and the complexity and difficulty of diagnostics, a
> substantial part of the research in this field relies on numerical
> simulations. The code MULTI-IFE described in the present paper
> implements a one-dimensional spherical model that includes the
> basic physical phenomena required to simulate and study IFE
> targets: two-temperature hydrodynamics, laser light absorption,
> heat conduction, multi-group radiation transport, thermonuclear
> burn, and α-particle transport. The study of the important multi-
> dimensional effects such as hydrodynamic instabilities and mix-
> ing processes remain outside the scope of this code. Even though
> these multi-dimensional effects have turned out to be a key issue
> in the recent NIC experiments [5], codes like MULTI-IFE are use-
> ful for quick orientation when changing designs and drive param-
> eters. One of the two designs discussed in this paper is also used in
> the book [3] as a representative example for IFE targets. The code
> MULTI-IFE allows for detailed studies of such designs.
>
> A substantial part of the physics included in the code was
> already present in the widely used codes MULTI [6] and MULTI-fs
> [7,8], devoted to the analysis of experiments of laser irradiated
> targets. In order to keep these capabilities, the treatment of laser
> light by explicit solution of Maxwell’s equations (in planar targets)
> and the computation of low temperature transport coefficients,
> though not so important in IFE applications, are still present in
> MULTI-IFE and can be switched on to use the code in a wider
> range of applications. Some of these applications require specific
> settings that are not available in the standard version of the code
> (additional energy deposition mechanisms, customized output,
> special boundary conditions, etc.). To facilitate the user to modify
> the code to fit to his needs, the structure of the Fortran source
> has been kept simple (one file), compact (4356 lines), and clear
> (data organized in hierarchical structures). A technical manual,
> supplied with the source code, explains in detail data structures,
> flowchart, file formats, input parameters, installation procedure,
> and several examples. In this paper we describe the physical model
>
> and the numerical methods used by the code. For consistency
> and completeness, the components relating to the MULTI-fs code,
> are also briefly described, but we refer the reader to [8] for
> details. In Sections 2–5, the equations describing hydrodynamics,
> thermal flux, electron–ion relaxation, radiation transport, and their
> discretization are discussed. The specific IFE features, namely, a 3D
> laser ray tracing package and a thermonuclear burn package, are
> discussed in detail in Sections 6 and 7, respectively. The structure of
> the code is briefly discussed in Section 8. In Sections 9 and 10, two
> representative IFE examples are presented, a direct drive target and
> an indirect drive target, respectively.

### 第 3 页

> (6)
>
> where the superscript k indicates the species (k = e, i, or α).
> j and P i
> For electrons and ions, P e
> j are interpolated in tables as
> functions of mass density ρj and specific internal energies ee
> j and
> α
> j. For α-particles, an ideal gas equation of state is assumed: P
> =
> ei
> j
> 2
> is needed to
> 3 e
> treat numerically the dynamics of shock waves. Since in a plasma,
> viscosity effects are mainly due to the ions, this term is added to P i
> j .
> Using
>
> ρj. In addition, an artificial viscosity term P

### 第 5 页

> (26)
>
> where c is the light velocity, θ is the angle between the direction
> of photon propagation and the radial direction, and I(r, θ, ν, t) is
> the spectral intensity, i.e. the energy flux per unit of solid angle
> and frequency. U k and Sk are discretized at cell centers and at
> interfaces, respectively. The subprocess for group k is specified by
>
> = AjSk
> j

> (31)
>
> The apparent opacity (combining optical and geometrical effects)
> is
>
> ˆχ k
> j

> (32)
>
> where d is 0, 1, and 2, for planar, cylindrical, and spherical
> geometries. χ R,k, χ P,k, and εk are the so called Rosseland average
> opacity, Planck average opacity, and normalized emissivity, that
> are defined as
>  νk+1
>
>  νk+1

> (35)
>
> where χ(ν, ρ, T ) and η(ν, ρ, T ) are the spectrally resolved
> opacity and emissivity. Notice that εk reduces to unity in case
> of thermodynamic equilibrium because, by the Kirchhoff’s law,
> η = χ I P . The values of χ and η have to be obtained from
> atomic physics models. In the examples of Sections 9 and 10,
> these quantities have been computed by the code SNOP [20,21] as
> functions of frequency, matter density, and matter temperature,
> by assuming either thermodynamic equilibrium (for high density)
> or coronal equilibrium (for low density). Because most of the
> radiative phenomena are due to electrons, electron temperature
> is used to evaluate opacity and emissivity. Eq. (29) is not defined
> for j = 1 and j = N + 1, so that boundary conditions
> should be used to determine the radiative flux there. According to
> the forward–reverse approximation [22,8], the value of Sk at the
> external boundary can be evaluated as
>
> Sk
> ext

> (37)
>
> For planar geometry, a similar expression is derived for Sk
> 1. In
> = 0. To perform a time
> cylindrical and spherical geometries, Sk
> 1
> step integration of Eqs. (27)–(29) and (37), opacity and emissivity
> are computed from initial values of temperature and density, but
> to achieve appropriate numerical stability the final temperature
> should be used to evaluate U P,k. This quantity is linearized as
> U P,k(T e,n+1
>
> ) ≃ U P,k(T e,n

### 第 6 页

> 231
>
> propagation and the gradient of n. Let us introduce a mechanical
> analogy. The above expression is identical to the transverse
> momentum conservation of a fictitious ‘‘particle’’ of unit mass,
> moving in the direction of light propagation with ‘‘velocity’’ n, and
> submitted to a force in the direction of density gradient. Because,
> the modulus of the ‘‘velocity’’ depends only on n, one can state that
> the ‘‘force’’ acting on the particle derives from the ‘‘potential energy’’
> −n2/2. The ‘‘equation of motion’’ of such ‘‘particle’’ then takes the
> form
>
> 2

### 第 7 页

> = −nD∇ · ⃗v − ⟨σ v⟩ n2
>
> is taken into account, and an equimolar mixture of deuterium and
> tritium is assumed. The number density of both components (nT =
> nD) is governed by the rate equation
> ∂nD
> ∂t
> where ⃗v is the fluid velocity, ⟨σ v⟩ n2
> D is the number of reactions
> per unit of time and volume, and ∂/∂t denotes derivation with
> respect to individual fluid elements; i.e. at constant value of mass
> coordinate µ. The reactivity is approximated by [26]
>
> (54)

> C1 = 643.41 × 10
> C3 = 75.189 × 10
> C5 = 13.500 × 10
> C7 = 0.01366 × 10
>
> where the coefficients are
> C0 = 6.6610 keV1/3,
> C2 = 15.136 × 10
> C4 = 4.6064 × 10
> C6 = −0.10675 × 10
> In each reaction event, a neutron and an α-particle are produced.
> The neutron, carrying 80% of the reaction energy, is assumed
> to escape from the plasma without further interaction. The
> α-particles, with initial energy and velocity, ϵ0 = 3.5 MeV and
> v0 = 1.297 × 109 cm s−1, are treated as a supra-thermal species
> α
> (related to the specific energy
> with energy per unit of volume E
> by E
>
> −16 cm3 s,
> −1,
> −3 keV
> −2,
> −3 keV
> −3.
> −3 keV

### 第 8 页

> 8.3. Linearization of the equation-of-state
>
> Ion and electron pressures and temperatures are obtained
> by interpolation in external tables as functions of the density
> and the specific electron and ion internal energies. That involves
> a time consuming fetch and evaluation procedure. To reduce
> the computational burden, these magnitudes are interpolated at
> the beginning of each subcycle and assumed to vary linearly
> throughout the subcycle. Likewise, ionization is interpolated and
> assumed to be constant throughout the subcycle.
>
> 8.4. Flow diagram

### 第 9 页

> Fig. 4. Laser driven capsule. (a) Time dependence of the power of the laser pulse.
> (b) Implosion diagram.
>
> Fig. 5. Laser driven capsule at t = 22.7 ns. (a) Some of the ray trajectories used to
> discretize one of the laser beams. Each trajectory has a different value of the impact
> parameter p (see Fig. 2). Deflection angle decreases with p, from 180°, for p = 0,
> to zero, when p → ∞. (b) Density and laser power per unit of volume, the latter
> obtained by adding the contributions of a large number (100) of rays and averaging
> over the 4π solid angle.
>
> 8.5. Program output

> Laser cross section is taken as a super-Gaussian profile
>
> In addition to deliver the main variables as functions of position
> and time, the code supplies the evolution of a set of magnitudes
> relevant for IFE studies: the average implosion velocity of the fuel,
> the confinement parameter ⟨ρR⟩ =  rfuel
> ρdr, the in-flight-aspect-
> ratio (IFAR; average shell radius divided by shell thickness), and the
> isentrope parameter α (the average ratio of actual fuel pressure and
> the corresponding pressure of totally degenerated fuel at the same
> density). Comprehensive descriptions of all numerical options,
> input and output file formats, implementation, and other technical
> details are given in document 2015-MULTI-IFE.pdf, supplied
> together with the source code.
>
> 0

> (73)
>
> with diameter D = 3.5 mm (FWHM). Rays with normal incidence
> reach the critical density and are reflected back. For grazing
> incidence, rays deviate before reaching the critical density, and
> deposit their energy in low density regions. The 4π -solid angle
> averaged power deposition per unit of volume is displayed in
> Fig. 5(b). When the pulse is switched off, the capsule has absorbed
> about 1.35 MJ of laser energy, and almost 90% of the plastic layer
> has been ablated. The shell has now imploded to half the initial
> radius and is coasting inwards at a velocity of 3.8 × 107 cm s−1.
> The shocks launched during implosion, after passing the shell, run
> into the gas. They generate considerably more entropy in the gas
> than in the shell, because the density of the gas is much smaller.
> At stagnation time t = 24.30 ns, when the imploding material
> piles up in the center and comes to rest, the high entropy gas
> reaches a temperature (T e ≃ T i ≃ 10 keV) much higher than
> the surrounding low-entropy fuel and forms the central part of the
> hot spot, which serves as a spark plug for ignition. The colder fuel
> surrounding the hot spot has been compressed to ρ ≃ 500 g cm−3.
> At this moment of stagnation, when values close to maximum fuel
> ⟨ρR⟩ are achieved, ignition occurs in the central hot spot. A burn
> wave is then running outwards and ignites the whole fuel, which
> expands rapidly. This process is summarized in Fig. 6, showing the
> flow diagram (a), the evolution of the central ion temperature (b),
> the fuel and hot spot confinement parameters (c), and the released
> fusion power (d). A total of 140 MJ of fusion energy is released.
> When Figs. 4 and 6 are compared with Figs. 3.4 and 3.13 of Ref. [3],
> where results computed by code IMPLO-upgraded [25] have been
> plotted, it is difficult to see any difference. Nevertheless, there are
> some small differences: burning maximum takes place at 24.39 ns
> in our results instead of 24.55 ns in [3], peak ⟨ρR⟩ is 1.59 g cm−2
> instead 1.7 g cm−2, and peak ion temperature is 135 keV instead of
> 120 keV. Such discrepancies may be attributed to small differences
> in the two codes with respect to composition of plastic ablator,

### 第 11 页

> R. Ramis, J. Meyer-ter-Vehn / Computer Physics Communications 203 (2016) 226–237
>
> how much driver energy is actually required for stable ignition
> and gain is still a matter of world-wide research, the present code
> may help to explore new target designs and to make such studies
> accessible to a broad international community. For example, laser
> direct drive may be reconsidered as a promising option, possibly
> making use of shock ignition [29,30], and the MULTI-IFE option for
> ray tracing should be helpful in this respect. Multi-group radiation
> transport is another strong feature of this code. In addition, all
> the physical processes available in [8] have been included, so
> that MULTI-IFE can be used in a wide range of applications, for
> example, laser–matter interaction at moderate intensity. The code
> allows to obtain quick answers: the simulations presented in
> Sections 9 and 10 require CPU times of 13 and 18 s on an ordinary
> laptop, respectively. Another major advantage of the code lies in
> its versatility that makes it easy to modify and adjust it to user’s
> needs.
>
> Acknowledgments

> b
>
> For a ̸= 0, the transformation u = (2ax+b)/
> xmin into u = 1, leads to
> Θ ′(a, u)
> 
> 
> 
>
> du
> u2 − 1
> du
> 1 − u2

> Fig. 10.
> Indirectly driven capsule. Temperature and density profiles during the
> thermonuclear burning propagation. Time labels (in ps) are relative to stagnation
> time t = 17.325 ns.
>
> and temperature have been plotted as functions of radius. The
> convergence ratio (initial radius divided by hot spot radius) is 30,
> and the thermonuclear yields is 13.4 MJ. The 24 µm thick internal
> part of the beryllium ablator has been doped with 2.10% of bromine
> and 4.86% of sodium (in % of atoms). The higher opacity of this
> mixture suppresses preheating of the fuel and the residual ablator
> layer. Using only pure beryllium in the ablator, although implosion
> velocity would be higher (3.00 × 107 cm s−1), ignition would not
> occur, and only 130 kJ of fusion energy would be produced.
>
> 11. Conclusions

*本节命中相关段落 19 处。*

## doc/References/2017JCP330.173(Ramis)_1D Lagrangian implicit hydrodynamic algorithm for ICF applications.pdf (1332448 B)

<!-- 共 20 页 -->

### 第 2 页

> R. Ramis / Journal of Computational Physics 330 (2017) 173–191
>
> from  those  of  ideal  gases.  High  temperature  plasmas  should  be  described  with  separate  temperatures  for  electrons  and
> ions,  whereas  that  in  warm  dense  matter,  phase  transitions  can  occur.  These  peculiarities  make  diﬃcult  the  use  of  stan-
> dard gasdynamics methods, for example, schemes based on the resolution of the Riemann’s problem [9]. Therefore, speciﬁc
> hydrodynamic algorithms are proﬁtable in this ﬁeld.
>
> In  one-dimensional  problems,  the  disparity  of  length  scales  can  be  treated  satisfactorily  by  using  Lagrangian  methods,
> where the numerical grid is moving with the matter. The classical algorithm of von Neumann, Richtmyer and Morton [10,11]
> can be considered as the root of this class of methods. It uses a staggered discretization with density and internal energy
> deﬁned  at  cell  centers  and  velocity  deﬁned  at  cell  boundaries.  An  artiﬁcial  viscosity  term  provides  dissipation  of  kinetic
> energy  into  internal  energy  to  ensure  stable  propagation  of  shock  waves.  The  original  algorithm  has  been  extended  to
> multidimensional ﬂows [12–15]. Modiﬁcations of the artiﬁcial viscosity terms have been proposed for one-dimensional [16]
> and  multi-dimensional [17–19] ﬂows.  In  ICF  problems,  grid  distribution  should  be  chosen  so  that  all  regions  of  interest
> are  covered  with  enough  resolution  during  all  the  time.  Because  ﬂuid  evolution  is  not  known  a  priori,  some  iteration  is
> needed  to  specify  the  grid.  For  example,  in  a  laser-irradiated  target,  an  initially  thin  grid  should  be  used  to  describe  the
> external part of the shell that later will expand to form a low density plasma corona. In explicit formulations, due to the
> Courant–Friedrichs–Lewy  (CFL)  condition [20],  the  time  step  interval  is  constrained  by  the  thinnest  cell.  Sometimes  this
> occurs in smooth regions where thin griding is not really required by accuracy reasons, leading to a useless reduction of the
> time step. The implicit formulation adopted in the early versions of code MULTI [21] allows to overcome the CFL limit and
> adjust the time step exclusively by accuracy criteria. This procedure has demonstrated to be robust and eﬃcient. However
> that  scheme,  as  the  original  versions  of [10,11],  is  not  fully  conservative.  Conservative  schemes  are  nowadays  preferred
> because  they  guarantee  the  satisfactory  treatment  of  problems  with  strong  gradients.  For  example,  although  numerical
> shocks extend over a few numerical intervals, shock velocity is correctly determined.

> In  one-dimensional  problems,  the  disparity  of  length  scales  can  be  treated  satisfactorily  by  using  Lagrangian  methods,
> where the numerical grid is moving with the matter. The classical algorithm of von Neumann, Richtmyer and Morton [10,11]
> can be considered as the root of this class of methods. It uses a staggered discretization with density and internal energy
> deﬁned  at  cell  centers  and  velocity  deﬁned  at  cell  boundaries.  An  artiﬁcial  viscosity  term  provides  dissipation  of  kinetic
> energy  into  internal  energy  to  ensure  stable  propagation  of  shock  waves.  The  original  algorithm  has  been  extended  to
> multidimensional ﬂows [12–15]. Modiﬁcations of the artiﬁcial viscosity terms have been proposed for one-dimensional [16]
> and  multi-dimensional [17–19] ﬂows.  In  ICF  problems,  grid  distribution  should  be  chosen  so  that  all  regions  of  interest
> are  covered  with  enough  resolution  during  all  the  time.  Because  ﬂuid  evolution  is  not  known  a  priori,  some  iteration  is
> needed  to  specify  the  grid.  For  example,  in  a  laser-irradiated  target,  an  initially  thin  grid  should  be  used  to  describe  the
> external part of the shell that later will expand to form a low density plasma corona. In explicit formulations, due to the
> Courant–Friedrichs–Lewy  (CFL)  condition [20],  the  time  step  interval  is  constrained  by  the  thinnest  cell.  Sometimes  this
> occurs in smooth regions where thin griding is not really required by accuracy reasons, leading to a useless reduction of the
> time step. The implicit formulation adopted in the early versions of code MULTI [21] allows to overcome the CFL limit and
> adjust the time step exclusively by accuracy criteria. This procedure has demonstrated to be robust and eﬃcient. However
> that  scheme,  as  the  original  versions  of [10,11],  is  not  fully  conservative.  Conservative  schemes  are  nowadays  preferred
> because  they  guarantee  the  satisfactory  treatment  of  problems  with  strong  gradients.  For  example,  although  numerical
> shocks extend over a few numerical intervals, shock velocity is correctly determined.
>
> In order to overcome the diﬃculties associated with the above points, a new implicit, ﬂexible, accurate, and fully con-
> servative  Lagrangian  scheme  has  been  developed.  Several  adjustable  parameters  can  take  different  values  in  each  cell.  In
> regions  with  low  CFL  numbers  (distance  traveled by  a  sound  wave  in  one  time  step  divided  by  cell  size),  these  parame-
> ters allow to optimize accuracy. The linear analysis (i.e., assuming negligible density variations in comparison with average
> value) predicts up to fourth order accuracy in space and in time. Although in the non-linear problems of sections 4 and 5,
> the  accuracy  reduces  to  second  order,  the  truncation  error  is  2  to  10  times  smaller  than  that  in  a  conventional  explicit
> method. Conversely, in regions with large CFL numbers, the parameters can be set to guarantee numerical stability, but at
> the cost of a larger truncation error (second order in time is predicted by the linear analysis). This dynamic adjustment is
> particularly advantageous in problems where regions without signiﬁcant ﬂow structures but with high CFL numbers would
> restrict the integration time step of the entire calculation.
>
> The  method  allows  for  separate  and  arbitrary  equations  of  state  for  electrons  and  ions.  Thermonuclear ignition  mod-
> els [22–24],  where  α-particles  are  treated  as  an  additional  species  can  be  easily  accommodated.  Van  der  Waals  like
> equations  of  state  supplied  by  QEOS  models [25,26] can  be  used  directly,  without  computing  explicitly  the  liquid–vapor
> equilibrium curve. When mechanically unstable domains, where (∂ P /∂ρ)T < 0, are entered, the code reacts giving place to
> either  a  clean  liquid–vapor  interface,  or  a  multiphase  region  with  alternating  liquid  and  vapor  cells.  A wide  range  of  ICF
> problems can be treated satisfactorily with the new method: from low intensity laser–matter interaction to thermonuclear
> ignition.

### 第 5 页

> In typical applications, Eqs. (4), (16), and (17) are coupled, through terms  S e
>
> i , to equations that describe external
> energy  deposition  (e.g.,  laser,  ion  beams)  and  transport  (e.g.,  heat  conduction,  radiative  transfer,  ion–electron  exchange).
> A convenient and widely employed way to treat such complex problems is by using splitting schemes. During a discrete time
> step (cid:11)t, the different physical processes are advanced one by one by separate integration methods. The details of how this is
> done are out of the scope of this paper. The reader is referred to [21,24,29,30] where such methods are discussed in the ICF
> context. Basically, it is required that the algorithms used to solve individual processes are stable, consistent, and accurate.
> Here, only the hydrodynamic component is being considered: the evaluation of interface positions, interface velocities, and
> cell  energies  at  time  tn+1 = tn + (cid:11)t from  their  values  at  time  tn,  assuming  S e
> = 0.  In  the  present  algorithm,  the
> i
> continuous,  time-dependent  cell  pressures  ( P i(t) for  tn ≤ t ≤ tn+1)  are  replaced  by  impulsive  pressures  P
> ∗)
> ,  are
> acting  at  time  t
> constant between tn and t
> , and remain constant until
> tn+1. Notice, that conservation laws derived in section 2.2 are valid for any temporal shape of  P i(t), including also impulsive
> pressures. Eqs. (4), (16) and (17) take now the form
>
> i and  speciﬁc  internal  energies,  ee,n
> , and ei,n+1

> − λ)(mi−1 + mi)(vn+1
> + D
> +
>
> i−1) + ( 1
> 2
> −
> ) = −(D
> i
> −
> i ) = −(D
> i
> 2 vn+1
> i (cid:11)t,
> ∗
> ∗
> − A
> i vn
> i+1 vn
> i+1
> i vn+1
> i+1 vn+1
> ∗
> ∗
> − A
> i+1
> i
> 2, for planar, cylindrical, and spherical geometries) and V i ≡ ( Ai+1xi+1 − Ai xi)/κ
> Ai are the interface areas (1, 2π xi , and 4π xi
> are the cell volumes (κ = 1, 2, and 3, for planar, cylindrical, and spherical geometries). In the planar case, the approximations
> in  Eqs. (23) and  (24) are  indentities.  To  close  this  system,  thermodynamic  and  viscous  pressures  at  time  t
> have  to  be
> speciﬁed. The initial pressures  P s,n
> (where s is either e or i) can be computed (usually by table interpolation) from initial
> speciﬁc internal energies es,n
> i . Pressures at nearby times can be estimated by linear extrapolation
> i
> (cid:6)
> (cid:5)
>
> − V n
> i ,
> )(cid:11)t (cid:9) V n+1
> − V

### 第 6 页

> )2 + (ci,n
>
> where cn
> i )2 is the isentropic sound velocity at time tn, H(u) is the unit step function (0 and 1 for u < 0 and
> i
> u ≥ 0, respectively). The coeﬃcient ν establishes the time-centering of the velocity gradient: ν = 0, for explicit evaluation
> at  time  tn,  and  ν = 1,  for  implicit  evaluation  at  time  tn+1.  The  appropriate  values  for  Fa,  Fb,  and  ν are  discussed  in
> section 5.  The  system  of  Eqs. (18)–(24) and  (29)–(32) should  be  solved  to  obtain  the  values  of  velocities,  positions,  and
> internal  energies  at  tn+1 from  known  values  at  tn.  The  velocities  at  time  tn+1 appear  linearly,  through  D
> ,  in
> the expressions of thermodynamical and viscous pressures. The set of equations can be reduced to a tridiagonal system of
> linear equations for vn+1
> , so that the method can be classiﬁed as implicit. Only if αi = λ = ν = 0, the system of equations is
> diagonal and the method becomes explicit. In that case, the method agrees basically with the classical scheme [10,11]. An
> essential difference is that, in the classical method, energies are advanced using the increment of volume computed from
> initial and ﬁnal interface positions, so that energy is strictly preserved only in planar geometry.
>
> +
> i and  ζ

> (33)
>
> where j is the imaginary unit and (cid:11)x is the initial cell size. For small perturbations ( ˜Xl (cid:13) ¯X ), the discrete equations can be
> linearized and reduced to a numerical dispersion relation between a generic wavenumber and its angular frequency. In this
> limit, the accuracy and stability of the method can be analyzed by comparing this relation with the true dispersion relation
> for sound waves (ω2 = c2k2) [31]. From the equations of previous sections one gets:
>
> ( A − 1)2 + (α A2 + (1 − β − α) A + β)D = 0,

### 第 7 页

> 179
>
> Fig. 1. A(D) for α = 1/4 and β = 0. As D increases, the two roots are ﬁrst imaginary (0 < D < 64/9) and later real (D ≥ 64/9). For D > 8 one of the roots
> has module larger than 1, entering the unstable region.
>
> The  detailed  derivation  is  given  in  the  Appendix.  For  λ < 1/4,  D increases  monotonically  with  k,  from  0  to  a  maximum
> value2

> (37)
>
> remains below or equal to unity for all D in the range from 0 to Dmax. A typical  A(D) relation (α = 1/4 and β = 0) has been
> drawn  in  Fig. 1.  For  D = 0,  one  has  A = 1.  For  small  enough  values  of  D,  the  discriminant  is  negative  and  A is  complex
> with  module  | A|2 = (1 + β D)/(1 + α D).  To  satisfy  the  condition  | A| ≤ 1,  it  is  required  that  β ≤ α.  From  here  on,  it  will
> be  assumed  β ≤ α.  If  α + β > 1
> 2 (1 + (α − β)2),  A is  complex  for  all  values  of  D,  and  | A| ≤ 1.  Otherwise,  A is  real  for
> D ≥ D1 ≡ 4/(1 + (α − β)2 − 2(α + β)). For  D = D1,  A1 ≡ A(D1) = −(1 − α + β)/(1 + α − β) ∈ [−1, 1]. For real  A, it can be
> proved that d A/dD is positive between  A1 and 1, and negative elsewhere. As consequence, for D > D1, one of the real roots
> increases with D, but remains in the interval from  A1 to 1, while the second root decreases and can eventually become less
> than −1. For α + β < 1/2, this happens for  D > 4/(1 − 2(α + β)). For α + β ≥ 1/2, this never occurs and the method is
> unconditionally stable. The stability conditions can be summarized (for λ < 1/4) as
>
> β ≤ α,
> (cid:9)

> ≥ 1
> 2 ,
> < 1
> 2 ,
>
> stable for all (cid:11)t,
> stable for (cid:11)t < (cid:11)x
> c
>
> (cid:14)

> (39)
>
> For long wavelengths (i.e., k(cid:11)x → 0 and ω(cid:11)t → 0), the true dispersion relation (ω2 = c2k2) is recovered. The terms inside
> the  brackets  represent  the  numerical  errors  associated  to  space  discretization  (right  hand  side  series)  and  temporal  dis-
> cretization (left hand side series). The order of accuracy of the method, either in time or in space, is deﬁned by the lowest
> powers of (cid:11)t or (cid:11)x in these series. In general, the method is of ﬁrst order in time and of second order in space. But, if
> λ = 1
> 12 , the second term on the right hand side disappears and the method is of fourth order in space. Choosing α = β, the
> second term (and all even terms) inside the left hand side brackets vanishes and the method becomes of second order in
> time. For α = β = 1
> 12 , the third term also vanishes and the method becomes of fourth order in time. With these optimum
> settings  the  method  is  stable  only  for  (cid:11)t < (cid:11)x/c.  Conversely,  to  get  unconditional  stability,  the  requirement  α + β ≥ 1
> 2
> implies that the scheme is at most of second order in time.
>
> 2 A similar analysis can also be carried out for λ ≥ 1/4, but because the poor accuracy in that case, it has been not included in this paper.

### 第 8 页

> −2
> x
>
> where v is the numerical solution at time  1
> 2 L/c and vr is a reference “exact” solution (a high resolution numerical solution
> with  Nx = 4096,  Nt = 65536, and the best numerical parameters α = β = λ = 1/12). As indicated in the previous section,
> the numerical error can be decomposed in spatial and temporal components. For extremely small time steps (Nt = 65536),
> the  equations  are  solved  very  accurately  in  time  and  the  numerical  error  can  be  attributed  almost  entirely  to  the  space
> discretization.  Fig. 3 shows  the  dependence  of  spatial  component  of  the  error  with  λ and  Nx.  For  a  ﬁxed  value  of  λ,  the
> error  decreases  with  cell  size  as  (cid:17)2 ∝ (cid:11)2x ∝ N
> ,  corresponding  to  a  second  order  accuracy  in  space.  The  fourth  order
> accuracy predicted by the linear analysis for λ = 1/12 has been destroyed by the nonlinearity of the problem. Nevertheless,
> a  clear  optimum  occurs  for  λ = 1/12.  In  this  speciﬁc  problem,  this  accounts  for  one  order  of  magnitude  improvement
> with  respect  to  an  explicit  classical  (λ = 0)  scheme.  To  analyze  the  inﬂuence  of  parameters  α and  β,  the  values  of  Nx
> and  λ have  been  ﬁxed  to  256  and  1/12,  respectively.  The  numerical  error  associated  to  time  discretization  is  deﬁned  by
> taking as reference in Eq. (40) the numerical solution obtained with identical space discretization but with very high time
> resolution (65536 time steps). In Fig. 4, the relative error has been plotted as a function of the number of time steps  Nt
> for several combinations of α and β. The basic predictions of the linear theory are recovered. For α > β (dashed lines), the
> method is only of ﬁrst order in time ((cid:17)2 ∝ (cid:11)t ∝ N
> ). For α = β (continuous lines) the method is of second order in time
> ). For α + β ≥ 1/2, the method is unconditionally stable. Otherwise, a maximum time step exists. Above this
> ((cid:17)2 ∝ (cid:11)2t ∝ N
> threshold, the method becomes unstable (vertical lines in Fig. 4). As occurred with λ, the fourth order accuracy predicted
> for α = β = 1/12 has been destroyed by the nonlinearity of the problem. This fact is depicted in Fig. 5, where the numerical
> error for λ = 1/12 and Nx = Nt = 256 has been plotted as function of α and β. The curve corresponding to α = β presents
> a strong optimum for α = β = 1/12, an order of magnitude lower than the value corresponding to α = β = 0 (i.e., with the
> conventional choice  P s,∗
> ∗
> i ) in Eq. (29)). For α > β, the accuracy degrades. Summarizing, in non-linear problems, the
>
> = ˆP s

### 第 9 页

> Fig. 3. Nonlinear smooth problem with  Nt = 65536. Variation of the spatial discretization error with the number of cells (in half wavelength) and the
> numerical parameter λ.
>
> Fig. 4. Nonlinear smooth problem. Temporal discretization error versus number of time steps Nt . Continuous curves correspond to α = β (value in the
> label). For α + β < 1/2, the method becomes unstable below some value of Nt .
>
> Fig. 5. Nonlinear smooth problem. Dependence of time discretization error on numerical parameters α and β, for Nx = Nt = 256 and λ = 1/12.

### 第 12 页

> R. Ramis / Journal of Computational Physics 330 (2017) 173–191
>
> Table 1
> Error scaling in the “smooth case” for the implicit optimum settings and for the ex-
> plicit settings. The order of convergence k has been computed from two successive
> values of (cid:17)2.
>
> Nt

> 1.998
> 1.998
> 1.997
> 1.989
> –
>
> generates shock waves with width (cid:9) 3(cid:11)x. Numerical shocks are non-linear structures that cannot advance a distance larger
> than their own thickness in a single time step. This requirement gives place to a constrain for the time step, v shock (cid:11)t (cid:2) 3(cid:11)x.
> This limitation can be overcome by taking α > β, so that the diffusive (imaginary) terms in Eq. (39) are not zero. This extra
> diffusion  widens  shock  structures,  allowing  for  integration  with  larger  (cid:11)t.  This  is  apparent  in  the  curves  with  β = 0 in
> Fig. 9 (continuous  thin  lines).  For α ≥ 3/4 and  β = 0,  all  values  of  Nt are  stable.  To  optimize  the  accuracy,  the  values  of
> α and β have to be chosen as functions of  Nt . In the present problem, it is clear that α = β = 1/12 is the best choice for
> Nt ≥ 136. For lower values (Nt = 8, 16, 32, 64, and 128), systematic parametric studies have been carried out to minimize
> the numerical error. The results have been plotted in Fig. 9 as black squares. In the optimum settings,  0.1 < β < 0.2 and
> α < 0.6.  To  extend  this  beneﬁt  to  any  problem,  an  adaptive  algorithm  is  proposed.  As  indicated  in  section 2.5,  different
> values of α and β can be used in different cells. The idea is to use a uniform β ((cid:9) 1/12) and adjust locally the value of α
> to guarantee stability. This can be implemented by the expressions
>
> βi = β

> (44)
>
> is  a  reference  solution  obtained  with  a  very  thin  grid  (Nx = 6400 and  Nt =
> where  X is  the  initial  coordinate  and  vr
> 12800).  Because  no  shock  waves  occur  during  the  time  interval  t ∈ [0, 0.1],  viscosity  can  be  switched  off  (Fa = Fb = 0).
> The  truncation  error  as  a  function  of  grid  resolution  is  shown  in  Table 1 for  both,  the  optimum  (α = β = λ = 1/12)  and
> , with k (cid:9) 2), but
> the explicit (α = β = λ = 0) settings. In both cases, the method proves to be of second order ((cid:17)2 ∝ N
> the  truncation  error  is  smaller  (one  half)  in  the  implicit  method.  The  numerical  stability  has  been  evaluated  for  several
> sets  of  parameters.  The  number  of  cells  is  ﬁxed  to  Nx = 3200 and  λ is  set  to  1/12.  Results  are  shown  in  Table 2.  For
> large  Nt ,  the  error  is  only  due  to  the  space  discretization,  for  small  Nt ,  the  main  contribution  to  the  error  is  due  to  the
> time  discretization.  For  the  optimum  settings  (α = β = 1/12)  the  method  is  unstable  if  Nt (cid:2) 1600.  For  α = β = 1/4,  as
> predicted by the linear analysis, the method is unconditionally stable (even for absurdly small  Nt ). The standard adaptive
>
> −k
> t

### 第 13 页

> 185
>
> Table 2
> Truncation error (cid:17)2 for the “smooth case” with several settings.  Nx = 3200 and
> λ = 1/12 in all the cases.
> α = β = 1
> 12
>
> 3 , β∗ = 1

> 0.00000006
> 0.00000006
> 0.00000580
> 0.00020727
> 0.00062918
> 0.00138173
> 0.00282801
> 0.00569793
> 0.01145205
> 0.02891439
> 0.07379802
> 0.15150341
> 0.29699422
>
> method is also unconditionally stable but with larger truncation errors. This fact suggests that better adaptive algorithms
> (e.g., using lim(cid:11)t→∞ αi = lim(cid:11)t→∞ βi (cid:9) 1/4 in smooth regions, and lim(cid:11)t→∞ αi > lim(cid:11)t→∞ βi in shock regions) can exist.
> For the moment, the adaptive settings α∗ = 2/3, β∗ = 1/12, ξ = 3/2,  Fa = 1,  Fb = 0.7 and ν = 1 will be used throughout
> the rest of examples of this section.
>
> 6.2.  Structure of a shock wave in a plasma

### 第 15 页

> Fig. 12. Radial proﬁles of density and partial pressures corresponding to the simulation of the ICF target of Fig. 11 at the moment of maximum thermonu-
> clear power (t = 17.413 ns).
>
> calculations  require  the  modeling of  warm  dense  matter  (WDM),  i.e.,  extreme  conditions  in  comparison  with  condensed
> matter,  but  also  far  away  from  a  classical  plasma.  Phase  transitions  should  be  considered  in  this  context.  In  the  QEOS
> equation of state model [25], the possibility of phase transitions is implemented by adding binding energy corrections to the
> Thomas–Fermi gas model for electrons. The code MPQEOS [26], used in this work, includes a rather rough model with only
> −3
> two free parameters that are adjusted to reproduce the density and the bulk modulus of the condensed phase (2.7 g cm
> and 140 GPa for diamond-like-carbon (DLC)). See [37] for a more sophisticated model of carbon in WDM conditions. Fig. 13
> displays the pressure estimated by MPQEOS for DLC as a function of density and temperature. One can observe regions of
> negative pressure and unstable regions with negative compressibility ((∂ P /∂ρ)T < 0). When such unstable domains occur,
> hydrodynamic  codes  react  generating  alternating  regions  with  high  density  cells  (liquid)  and  low  density  cells  (vapor).
> These  structures  emulate  a  two-phase  ﬂow  (bubbles  inside  a  liquid  or  droplets  inside  a  gas).  See [38,39] for  multiphase
> simulations  of  laser  irradiated  targets  using  this  approximation.  Here,  we  consider  the  conﬁguration  of  the  experiment
> in  reference [40]:  a  80 nm  thin  DLC  foil  irradiated  by  a  1.05 μm,  50 ps  FWHM  prepulse.  Fig. 14 shows  the  evolution  of
> −2 (40 times  higher  than  the  value  expected  in  the
> the  density  proﬁles  for  a  prepulse  peak  intensity  of  1.5 × 1012 W cm
> experiment).  Initially,  the  laser  heats  the  target  volumetrically,  more  intensely  in  the  irradiated  side.  After  a  while,  a  low
> density and high temperature corona is emitted towards the laser, while the rest of the target is pressed and accelerated in
> opposite direction. This colder and denser part remains initially near liquid density. At around t = 24 ps, negative pressures
> begin to occur. At t = 38.8 ps, a substantial part of the target is inside the instability domain shown in Fig. 13. Numerically,
> one  can  observe  small  ripples  in  the  density  proﬁle  that  grow  and  give  place  to  a  layered  density  proﬁle.  Adjacent  cells
> have similar pressure and temperature but very different densities (see 41.2, 50.0, 53.4, and 56.6 ps frames in Fig. 14). At
> later  times,  a  shock  wave,  formed  in  the  corona  region,  moves  towards  the  dense  region.  At  time  t = 56.6 ps,  the  shock
> is entering the liquid–vapor region. Behind the shock, supercritical conditions establish again a monophasic ﬂow. Pressure
> and density values at cells at t = 50.0 ps have been plotted on Fig. 13 (black circles). One can observe a continuous curve

### 第 16 页

> R. Ramis / Journal of Computational Physics 330 (2017) 173–191
>
> Fig. 13. Equation  of  state  used  in  the  hydrodynamic  simulations.  The  region  below  the  dashed  line  corresponds  to  mechanically  unstable  conditions
> ((∂ P /∂ρ)T < 0). The black circles are the cell values at t = 50 ps. In the liquid–vapor regions, adjacent cells have similar pressures but different values of
> density.
>
> Fig. 14. Evolution of a planar target irradiated by a 50 ns FWHM, 1.5 × 1012 W cm
> during the process.

### 第 17 页

> 189
>
> starting  from  the  rear  side  conditions,  where  pressure  is  zero  and  density  is  ﬁnite,  evolving  towards  the  “liquid”  region.
> There,  the  proﬁle  jumps  many  times  between  “liquid”  and  “gas”  regions,  located  at  both  sides  of  the  unstable  domain.
> The number of jumps depends of the numerical resolution (46 jumps using 1000 cells). This structure corresponds to the
> region  marked  “L–V”  in  Fig. 14.  Afterwards,  the  curve  becomes  again  continuous  from  the  “gas”  region  towards  the  high
> pressures and low densities of the plasma corona (outside the range of values represented in the ﬁgure) and ﬁnishes in the
> front plasma–vacuum interface, where pressure and density go to zero. The present simulation takes only into account the
> mechanical instability of the ﬂuid, but does not include the destruction of the metastable regions (e.g., negative pressures)
> by nucleation processes [38,39]. The method proves to be very convenient for this sort of problems because the time step
> is not restricted by the CFL limit. Otherwise, the CFL condition in one of the liquid cells (very thin and with a very high
> sound  velocity)  would  needlessly  slow  down  the  whole  simulation.  The  state  of  the  target  at  the  end  of  the  prepulse
> allows to assess the level of prepulse tolerable in a given experiment. In the problem presented here, one ﬁnds that below
> −2, the full target remains in condensed state, with sharp front and back boundaries. Between 4 × 1010 and
> 4 × 1010 W cm
> −2,  the  liquid–vapor  region  is  not  present,  but  a  sharp  liquid–vapor  interface  separates  the  dense  region
> 5 × 1011 W cm
> −2, the full target is
> from the corona. From 5 × 1011 to 5 × 1012 W cm
> vaporized.
>
> −2, a two-phase region occurs. Above 5 × 1012 W cm

### 第 19 页

> New York, 1994.
>
> [22] S. Atzeni, A. Caruso, A diffusive model for alpha-particle energy transport in a laser plasma, Nuovo Cimento 64 (1981) 383–395.
> [23] S. Atzeni, 2-D Lagrangian studies of symmetry and stability of laser fusion targets, Comput. Phys. Commun. 43 (1986) 107–125.
> [24] S. Atzeni, The physical basis for numerical ﬂuid simulations in laser fusion, Plasma Phys. Control. Fusion 29 (1987) 1535–1604.
> [25] R.M.  More,  K.H.  Warren,  D.A.  Young,  G.B.  Zimmerman,  A  new  quotidian  equation  of  state  (QEOS)  for  hot  dense  matter,  Phys.  Fluids  31  (1988)
>
> 3059–3078.

> 3059–3078.
>
> [26] A. Kemp, J. Meyer-ter-Vehn, An equation of state code for hot dense matter, based on the QEOS description, Nucl. Instrum. Methods A 415 (1998) 674.
> [27] S.I. Braginskii, Transport processes in a plasma, in: M.A. Leontovich (Ed.), Reviews of Plasma Physics, vol. I, Consultants Bureau, New York, 1995,
>
> pp. 205–311.

> pp. 205–311.
>
> [28] T4-Group, SESAME Report on the Los Alamos Equation-of-State Library, Tech. Rep. LALP-83-4, Los Alamos National Laboratory, 1983.
> [29] R. Ramis, J. Meyer-ter-Vehn, J. Ramírez, MULTI2D a computer code for two-dimensional radiation hydrodynamics, Comput. Phys. Commun. 180 (2009)
>
> [30] R. Ramis, J. Meyer-ter-Vehn, MULTI-IFE a one-dimensional computer code for inertial fusion energy (IFE) target simulations, Comput. Phys. Commun.

*本节命中相关段落 23 处。*

## doc/References/2013物理学报(宋天明)_三维柱腔内辐射输运的一维模拟.pdf (624902 B)

<!-- 共 5 页 -->

### 第 1 页

> 2 辐射输运计算的修正
>
> MULTI[7] 是 一 维 拉 格 朗 日 辐 射 流 体 力 学 模
> 拟, 程序能够进行多群辐射输运的计算. 程序使用
> 的不透明度数据用 SNOP 计算, 状态方程则使用
> MPQeos 程序的 QEOS 模型 [12] 计算, 数据存储在
> SESAME 格式的数据表格中, 计算时可实时调用.
>
> 在一维辐射输运的数值模拟中, 一个网格单元

### 第 3 页

> 图 5 MULTI 修正前后的模拟结果
>
> 从图 5 中还可以看到, 模拟结果和实验测量结
> 果仍有一些差异. 除了程序数值模拟受网格划分、
> 不透明度等参数误差的影响之外, 二者的误差还包
> 括: 上述模型中只考虑了辐射的漏失和损失, 没有
> 考虑流体运动受管壁的影响所产生的二维效应 (本
> 算例中管子的长径比较小, 这一项影响较小); 另外
> 实验测量中金等离子膨胀时存在密度变化, 实验数
> 据处理时界面的提取也存在误差, 等等.
>
> 4 结 论

*本节命中相关段落 2 处。*
