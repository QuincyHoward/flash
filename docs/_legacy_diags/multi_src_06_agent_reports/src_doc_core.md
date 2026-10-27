# Multi1D++Portable20241128 核心格式说明文档 —— 完整提取

## 提取方法与局限

- **docx**：`python-docx` 1.2.0，按文档流顺序遍历段落与表格；标题按 Word 样式还原为粗体；
  正文段落统一以 `> ` 引用块前缀，未改动一个字。表格还原为 Markdown 表。
- **doc（旧二进制 OLE）**：优先用 `win32com`（Word COM）另存为 docx 再走 docx 流程；
  若 COM 不可用，则回退到「原始字节多编码解码 + 可打印序列抽取」（utf-16-le / cp936 / latin-1 取可打印率最高者）。
  回退路径会丢失格式、页码与表格结构，字符间可能粘连，已在每节 `<提取说明>` 注明。
- **pdf**：`pdfminer.six`，按 `\f` 分页。原文英文照录，不翻译。
- 所有输出 UTF-8 / LF。原文引用逐字准确；提取不到处显式标注「未能提取」。

---

## A 组：核心 DOCX 文档

## doc/MULTI使用的SESAME数据文件格式.docx (183025 B)

<!-- 提取说明: 段落 105，表格 1 -->

**数据文件格式**  

> 参考：MULTI2002_MANUAL_V0 Richard Hrutkai, Diploma Thesis, 3.3.4 Material Module
> MULTI的数据库中提供了EOS，不透明度、Non-LTE factors和effective ion number表格数据。
**Multi的物质参数数据库**  

> MULTI中使用的不透明度和状态方程参数在模块[matter-2.1]数据库中，主要包括material.base 材料定义文件和若干个包含有数据表格文件的文件夹。$MULTI/r94/matter-2.1/material.base中包含了相关路径（material.base:matter-1.0与matter-2.1相同）。
> 数据库中的格式有两种：一种为Inverted EOS，采用直角坐标系，一种为不透明度，NLTE因子，Zeff等，采用log坐标系。
> Multi1D程序代码中采用的单位制为cgs+eV，但是其数据库matter-2.1中的EOS数据的单位制却并不是按照此单位制，因此程序在导入后进行了单位转化。
** 材料的定义**  

> 以Au为例：
> 表中标识：
> A				原子质量
> Z				有效离子数
> EOS				状态方程表（实际上是Inverted EOS,P(rho,e)与T(rho,e)）
> PLANCK			表格Planck不透明度
> ROSSELAND		表格Rosseland不透明度
> NONLTE			表格Non-LTE因子
> ZEFF			表格有效离子数
> material.base中各个变量对应mentry中的前半部分内容
> 数据文件都为4列多行，通过相关函数逐行读入然后解析。
** EOS数据**  

> EOS数据采用“三因素模型(Three component model)”,
> 第一项为冷分布，其他两项分别是电子和例子的参数。	
> 如mat_Au-1.0/AU_IDEAL_GA，使用理想气体的状态方程。Multi1D中为方便计算中直接使用，EOS表格数据为Inverted EOS数据，即自变量为和，因变量为和：
> 根据公式 
> 电子和离子对应的公式分别为
> ，
> 表mat_Au-1.0/AU_IDEAL_GA中的相关常数为：Z=19.998, A=197, GAMMA=1.2168。
> 因变量和自变量都没有使用对数坐标系，而是使用线性坐标系
> mat_Au-1.0/AU_IDEAL_GA表格中的数据和对应的意义如下
> 参数单位制分别为(cgs)
> r[nr]	 密度(g/cc)
> de[ne]	 能量(能量列表，与冷能量的差距, 单位Mbar*cm3/g)
> e0[nr]   冷能量(密度对应的冷能量列表，单位Mbar*cm3/g)
> P[ne*nr]  压力 P[(0~nr-1)+nr*i]为密度为r[0~nr-1]，能量de[i]+e0[0~ nr-1]时的压力，单位为Mbar
> T[ne*nr] 密度为r[0~nr-1]，能量de[i]+e0[0~ nr-1]时的温度（Kelvin）
> 即参数个数为4+2*nr+ne+2*nr*ne
> P[0]  to P[nr-1] are the pressures at energy de[0]+e0[0 to nr-1]
> P[nr]  to P[nr*2-1] at de[1]+e0[0 to nr-1], etc
> 补充
> Mass-specific heat capacity
**表格的转化（电子、离子表格）**
> 计算中使用的Electron Table（ieeos）根据总的EOS(ieos)和原子质量A换算出来。详情请参考eoselectron程序代码。
> 没有使用离子表格。
> MPQeos计算结果中包括了总的EOS和电子、离子表格，可以参考。
**Inverted EOS**
> 为了在计算时直接使用EOS数据，省去转化，需要将EOS数据表格中的P(R, T)，E(R, T)转化为P(R,E), T(R,E)
> 对于P(R, E)
> 对某个密度R, 
> 首先根据E(R, T)找到对应的温度T(R, E)，这个过程需要差值
> P(R, E) = P(R, T(R, E))，这里同样需要差值。
**MPQeos计算结果SESAME的数据格式和单位制**
> MPQeos程序的计算结果采用的单位制并不是Multi1D数据库中数据的单位制：
> SESAME数据库的单位：压强（GPa），能量（MJ/kg）,密度（g/cc）,温度(Kelvin)
> MULTI2D程序中使用cgs单位，而其调用的EOS数据中的单位为压强Mbar，能量Mbar*cm3/g，密度和温度单位与SESAME数据库相同。
> 其转化关系如下(最终为一维情况下的值)：
> 压力： 1GPa= 1e9Pa= 1e10 dyne/cm2=1e10erg/cm3=1e12 erg/cm2=1e-2Mbar
> 能量密度：1MJ/kg= 1e3J/g= 1e10 erg/g= 1e12 erg*cm/g=1e-2Mbar*cm3/g
> 同时，SESAME数据库使用301数据格式，四列多行数据。虽然MPQeos采用了四列多行的结构，但是其内容与Multi1D的要求并不一致：
> 即MPQeos的数据为
> 因此MPQeos的计算结果并不能直接用于Multi1D的计算。
> Multi1D++程序将自动识别文件后缀301/304/305并对单位制进行转化。
> 但是，从计算的结果来看，压强、能量甚至Z等有负值，原因正在查找。
**不透明度数据**  

> 不透明度为logloglog全部采用对数存储数据
> Mat_Au-1.0/AU_SIMPLE_PLANCK
> Mat_Au-1.0/AU_SIMPLE_ROSSELAND
> 第一行第二列数据类型为Multifs中读取并判断数据类型用：
> 表 1 数据类型及其意义

*[表格 1]*
| 参数类型 | 意义 |
|---|---|
| 默认为1 0.60000000E+01 PLANCK 1 0.70000000E+01 ROSSELAND 1 0.40000000E+01 EPS 1 PLANCK M ROSSELAND M  EPS M | INVERTED EOS Z-MEAN P.OPAZ. (1G) P.OPAZ. (1G) R.OPAZ. (1G) R.OPAZ. (1G) EPS. (1G) P.OPAZ. (MG) R.OPAZ. (MG) EPS. (MG) |

> 在MULTI7.6+代码中只有多群的需要此标识
> 其中Z的单位为cm2/g，温度T单位为eV，密度单位为g/cc
> 对定标公式L = c * T^a*rho^b
> Z = log(K)=log(1/(L*rho) )= - log(c*T^a*rho^(b+1)) = -log(c) –a*log(T) –(b+1)*log(rho)
> 本算例中Rosseland opacity (cm): 6.0e-06 * T^1.0 / rho^1.0
> Z(log(T)) = 6-log(6)-log(T)
> Z(0)= 6-log(6)= 5.2218;Z(1) = 5-log(6)=4.2218
**多群的情况**
> 其中数据类型包括PLANCE 1, PLANCK M, ROSSELAND 1, ROSSELAND M, EPS 1, EPS M. 等情况，分别表示Planck平均不透明度(cm2/gr)，Rosseland平均不透明度(cm2/gr)，NLTE因子(non-lte factor)
> 如果为PLANCK 1或者频率上下限都为0，则数据应用于所有的群。
> 数据结构为sesame_tab
> 单位为
> 以MID9为例，频率范围为10eV-5000eV
> 1	10	50	100	150	250	400	550	700	900	1200	1600	2000	2200	2400	2600	2800	3100	3500	4000	5000
> 并不是等间距（因此，最好使用Multi1D的程序进行插值，否则自编会带来较大的工作量）：
> 密度和温度为指数坐标，指数等间距：
> 密度：10-6-102g/cc
> -0.60000000E+01-0.55789474E+01-0.51578947E+01-0.47368421E+01
> -0.43157895E+01-0.38947368E+01-0.34736842E+01-0.30526316E+01
> -0.26315789E+01-0.22105263E+01-0.17894737E+01-0.13684211E+01
> -0.94736842E+00-0.52631579E+00-0.10526316E+00 0.31578947E+00
>  0.73684211E+00 0.11578947E+01 0.15789474E+01 0.20000000E+01
> 温度：0-105eV
>  0.00000000E+00 0.26315789E+00 0.52631579E+00 0.78947368E+00
>  0.10526316E+01 0.13157895E+01 0.15789474E+01 0.18421053E+01
>  0.21052632E+01 0.23684211E+01 0.26315789E+01 0.28947368E+01
>  0.31578947E+01 0.34210526E+01 0.36842105E+01 0.39473684E+01
>  0.42105263E+01 0.44736842E+01 0.47368421E+01 0.50000000E+01
> 如要得到某一温度密度下的参数随光子能量（频率）的向量数据，则需要处理。自编程序，提取出响应频率区间的值。
**Zeff**  

> 温度和密度采用对数坐标系，Zeff也采用了对数坐标系。温度单位是keV, 密度单位是g/cm3.(与不透明度不同，不透明度温度单位为eV)
> 注：之前的Multi计算中一直发现电离度偏高，况龙钰(20160109)发现是温度的单位弄错了，SNOP等输出的SESAME数据，温度的单位一直是keV。但是在Multi的输入是按照eV输入的，因此导致电离度明显偏高。
> 因为之前(20160109)的计算中按照eV输入，因此在创建Thermos的数据文件时电离度也是按照eV创建的，不存在偏大的情况。但程序自20160109之后，统一将输入按照keV执行；相应的Thermos文件夹中所有的电离度文件(名字为X_Z.dat)温度按照keV重新生成，以使其格式与SNOP等SESAME格式一致。名字为X_Zeff.dat(温度单位为keV)，以与之前的X_Z.dat(温度单位为eV)相区分。
> Material.base中替换所有X_Z.dat为X_Zeff.dat.
> Thermos的数据生成软件也将输出的温度单位改为keV。
**NLTE**  

> 温度和密度采用对数坐标系，NLTE也采用了对角坐标系。格式可以为多群。

## matter++/ATOMIC/Atomic(LEDCOP)不透明度格式说明.docx (33218 B)

<!-- 提取说明: 段落 134，表格 1 -->

**网站导出的LEDCOP不透明度格式说明**  

**SESAME格式**  

> 与MULTI默认的格式不同，比较难以解析此处略。
**LEDCOP格式**  

> 文件名Al.txt

*[表格 1]*
| Number of T =  69  Number of rho =  50  Number of materials =   2  TOPS results for  LiH             on Sep  6, 2016  Opacities in cm**2/gm, T in keV, density in gm/cc | 维度等 |
|---|---|
| Normalized composition for requested elements No. Fraction Mass Fraction  At. No.  Chem. Sym.  Mat ID.   5.0000E-01   8.7320E-01      3         Li        4922   5.0000E-01   1.2680E-01      1         H         4525 | 成分介绍 |
| Temperature grid used the following  69 points 5.0000E-04  6.0000E-04  8.0000E-04  1.0000E-03  1.2500E-03  1.5000E-03 …….   2.6250E+00  2.7500E+00  3.0000E+00  3.5000E+00  4.0000E+00  5.0000E+00   6.0000E+00  8.0000E+00  1.0000E+01 | 温度网格点 |
| Density grid used the following  50 points   1.0000E-03  1.2068E-03  1.4563E-03  1.7575E-03  2.1210E-03  2.5595E-03 ……   2.6827E+00  3.2375E+00  3.9069E+00  4.7149E+00  5.6899E+00  6.8665E+00   8.2864E+00  1.0000E+01 | 密度网格点 |
| Rosseland and Planck opacities and free electrons  Density     Ross opa    Planck opa  No. Free    Av Sq Free  T=  5.0000E-04   1.0000E-03  8.8707E+04  2.1555E+06  1.2280E-02  1.2280E-02   1.2068E-03  9.1256E+04  2.1200E+06  1.0632E-02  1.0632E-02 ……   8.2864E+00  5.7521E+04  5.7578E+04  1.0000E+00  1.0000E+00   1.0000E+01  4.9028E+04  4.9072E+04  1.0000E+00  1.0000E+00 Rosseland and Planck opacities and free electrons  Density     Ross opa    Planck opa  No. Free    Av Sq Free  T=  6.0000E-04 … | 单群gray opacity |
| Multigroup opacities   Energy      Ross mg     Planck mg    for T, density =   5.0000E-04  1.0000E-03   1.0000E-03  1.9954E+04  1.9957E+04 …   2.6412E+02  7.7877E-02  1.8976E-06   Energy      Ross mg     Planck mg    for T, density =   5.0000E-04  1.2068E-03   1.0000E-03  2.0681E+04  2.0695E+04 …… Energy      Ross mg     Planck mg    for T, density =   1.0000E+01  1.0000E+01   1.0000E-03  1.0000E+10  1.0000E+10 …… | 多群 |

> Multi1D++对Atomic文件的转换
> Opacity界面选择文件，点击Export
> Atomic网站上提供的信息
**Table of available temperatures (in keV) for use in TOPS **  

> ATOMIC-generated data (released in 2015)

>  5.000E-04 6.000E-04 8.000E-04 1.000E-03 1.250E-03 1.500E-03 2.000E-03
>  2.500E-03 3.000E-03 3.500E-03 4.000E-03 5.000E-03 6.000E-03 7.000E-03
>  8.000E-03 9.000E-03 1.000E-02 1.250E-02 1.500E-02 2.000E-02 2.500E-02
>  3.000E-02 4.000E-02 5.000E-02 6.000E-02 7.000E-02 8.000E-02 9.000E-02
>  1.000E-01 1.250E-01 1.500E-01 1.750E-01 2.000E-01 2.250E-01 2.500E-01
>  2.750E-01 3.000E-01 3.500E-01 4.000E-01 4.500E-01 5.000E-01 5.500E-01
>  6.000E-01 6.500E-01 7.000E-01 8.000E-01 9.000E-01 1.000E+00 1.125E+00
>  1.250E+00 1.375E+00 1.500E+00 1.625E+00 1.750E+00 1.875E+00 2.000E+00
>  2.125E+00 2.250E+00 2.375E+00 2.500E+00 2.625E+00 2.750E+00 3.000E+00
>  3.500E+00 4.000E+00 5.000E+00 6.000E+00 8.000E+00 1.000E+01 1.500E+01
>  2.500E+01 4.000E+01 6.000E+01 1.000E+02
> Temperatures added in 2015 are marked bold.
> LEDCOP-generated data (released in 2000)

>  5.000E-04 6.000E-04 8.000E-04 1.000E-03 1.250E-03 1.500E-03 2.000E-03
>  2.500E-03 3.000E-03 3.500E-03 4.000E-03 5.000E-03 6.000E-03 8.000E-03
>  1.000E-02 1.250E-02 1.500E-02 2.000E-02 2.500E-02 3.000E-02 4.000E-02
>  5.000E-02 6.000E-02 8.000E-02 1.000E-01 1.250E-01 1.500E-01 2.000E-01
>  2.500E-01 3.000E-01 4.000E-01 5.000E-01 6.000E-01 8.000E-01 1.000E+00
>  1.250E+00 1.500E+00 2.000E+00 2.500E+00 3.000E+00 4.000E+00 5.000E+00
>  6.000E+00 8.000E+00 1.000E+01 1.500E+01 2.500E+01 4.000E+01 6.000E+01
>  1.000E+02
**Frequency Dependent Opacity Spectrum Limitations **  

> The opacity calculations are intended primarily for users interested in integrated opacities. The "gray" opacities (Rosseland or Planck) are obtained by integrating over all photon energies while the "multigroup" opacities are integrated between the energy boundaries, giving one opacity number for each energy range. This range is assumed to be large compared with individual line profile widths. Under these assumptions, several approximations are made in the calculations that will reduce spectroscopic accuracy. 
> 1.Most of the atomic energy levels used in the opacity code are obtained from single configuration LS Hartree-Fock calculations, with relativistic corrections. These energy levels are then fit with a quantum defect model in order to reduce this massive data base to a managable set. This can result in errors of 1% or more, especially for inner shell transitions. Errors of this magnitude have little effect on the integrated opacity, but are large in terms of spectroscopic accuracy. 
> 2. For the higher Z elements, even the reduced LS coupled data base becomes too large. Switching to jj coupling, which is usually the preferred model for these elements, would require even more data. For this reason, the opacity code uses an Unresolved Transition Array (UTA) model for many bound-bound transitions calculations. This model replaces the actual transition array with a single Gaussian profile to approximate all of the actual lines (which can number in the millions). This overestimates the opacity for low densities, so a Random Line model is used to replace the single Gaussian with a relatively small set of randomly generated, plasma broadened lines that distribute the total oscillator strength over the same energy interval as the original transition array. For obvious reasons, none of these random lines can be matched spectroscopically, but looking at a broad enough energy range, this model will preserve the oscillator strength within the correct photon energy range. 
> 3. The individual element opacities are all calculated at the same u (u = hv/kT) grid for all temperatures and densities. This allows the elements to be mixed together to form opacities for multi-element materials. Since this is a fixed grid, the contributions from the different processes (such as bound-bound transitions) are calculated and summed only at the grid points and no effort is made to preserve the line centers. Therefore, line ratios could be reversed from their normal ratio by the choice of grid points. In addition to this, since the u's are constant, each temperature samples the opacity cross sections at different photon energies. If the lines are broad enough, this makes little difference, but the narrow line distribution could look entirely different at two adjoining temperatures. 
> All attempts are made to insure the most accurate possible opacity calculations, but because of the above inherent limitations, use of the frequency dependent opacities to match spectra is discouraged. 
**Frequently asked questions for the TOPS Web Page **  

> Q1: I noticed that some of the multigroup opacities were all 1010 . Why did this happen? 
> A: The TOPS code calculates the plasma cutoff frequency for each temperature-density point. Any group that lies either partly or fully below that frequency has the opacity set to 1010 to indicate that photons at those frequencies cannot propagate in the plasma. 
> Q2: I want a table of opacities at 21.8 eV. When I enter this number, the Web Page gives me an error message. Why can I not get the 21.8 eV temperature? 
> A: The TOPS code can only use tabulated temperature points for cross section data. It will not interpolate on temperature. If you choose a temperature that is not on the tabulated grid, the Web Page will compare it to the master list and reject it if it does not agree with one of the table values to within 1 percent. The set of tabulated temperatures is listed under tabulated temperatures.
NOTE: The TOPS code will interpolate in density. 
> Q3: I entered a temperature of .0005 keV (which is on the allowed temperature list) for carbon and did not get any results back. Why can't I get any data for this temperature? 
> A: The materials in this data base were calculated over several years and the temperature-density limits were changed during the course of the calculations. Most elements go down to .0005 keV, but the elements from lithium to magnesium only go down to .001 keV. These should be replaced in the next few months and the limitations shown in the tabulated temperatures list will be removed. 
> Q4: I asked for multigroup opacities for a density of /cc for aluminum at a temperature of .001 keV. Every multigroup had the same opacity in it. Why doesn't it vary with photon energy? 
> A: When you ask for a temperature-density point, TOPS attempts to find cross section data for that point. At low temperatures there is no data available for high densities. Thus the TOPS code uses the cross sections for the highest density available, prints a warning message that this has occurred and uses the gray opacity from those cross sections for all the multigroup and frequency dependent opacities. 
> Q5: When I specify multigroup opacity, it returns tables containing Rosseland Mean and Planck Mean opacity. But I want to obtain opacity as function of energy (not the averaged opacity). Is there a way I can do this? 
> A: When you ask for multigroup opacities, you get the Rosseland and Planck mean as well as the multigroup opacities. When you are looking at the the tabular output, the gray opacities appear in the output first. You may need to scroll down in the window to get to the section of the table that contains the multigroup opacities. Of course, you must have checked the button requesting multigroup opacities on the initial input page, as well as set up the group boundary energies. It is also possible to obtain the frequency dependent opacities for a limited number of temperature-density points. The frequency dependent data is tabulated on a grid of either 3000 or 3900 points depending on whether the old or new version of the data is used. The default is to use the new version where available. Because of the large number of points, we limit the requests to only six temperature-density points ie. you could choose two temperature and three density points for a total of six points, or one temperature with six densities etc. In the output file, the frequency dependent data is listed after the gray opacities, or after the multigroup opacities (if requested). 
> Q6: What is meant by "No. Free" in your tables ? 
> A: For a single element, the free electron number is the average number of free electrons per ion. It is obtained by multiplying the relative population of each ion stage by the number of free electrons for that stage, zero for the neutral, one for single ionized etc. For a mixture, it is a weighted average using the number fractions of each constituent of the mixture.
> Q7: What is your meant by "Av Sq Free" in the output? 
> A: This is the average of the square of the number of free electrons over the ion stages of an element. It is obtained by summing the product of the relative abundance of each ion stage times the square of the number of free electrons for that ion stage, zero for neutral etc. For a mixture, it is a weigthed average over all constituents of the mixture. 
> Q8: I can't seem to find opacities for densities lower than 10/cc. 
> A: All of the opacity data is generated assuming Local Thermodynamic Equilibrium (LTE) and this becomes very questionable below 10-6 to 10/cc. At lower densities, one should use a nonLTE coronal model. Since the data on this web site assumes LTE, they do not go to such low densities. 
> Q9: When I display a GIF plot or a data table for the second time, all that I get is the first plot or table over and over again. 
> A: The Web Page displays a file when showing plots or tables and uses the same file name for each new data set. Many browsers store the file name and data in their cache memeory and if you request a second plot or table, the browser retrieves it from the cache memeory instead of displaying the new data. You must change your browser's cache preference settings from "once a session" to "every time" to force the browser to choose the new data file for each new plot or table. Clicking the Reload button on your browser will also give you the latest plot or table, but you will have to do that every time if you do not reset the brower preference. 
> Q10: When I plot the Rosseland gray opacities, all of the high density curves seem to run together into one curve. Why is this? 
> A: The opacity code is unable to calculate the opacities for the low temperature-high density grid points, but needs to have a non-zero value for these grid points. The TOPS code takes the value for the highest calculated density for each temperature and used that value for all of the higher densities. This makes the curves run together. 
> Q11: I calculated a SESAME table for the same material that I had in the SESAME library that I received from you and the numbers are not quite the same. Why is that? 
> A: The normal SESAME library is calculated on the CRAY computers, using a slightly different interpolation scheme than on the Sun that runs this Web Page. This can cause small numerical differences. In addition, the boundary region (between calculated points and extrapolated points) is handled quite differently for the two SESAME files. The normal library file is done iteratively (with some points being removed) while the Web Page has to use an automatic fail proof method. Finally the extrapolated points are completely different (see the SESAME Format writeup), but these points should never be used in calculations. 
> Q12: When I display a postscript plot with Ghostview, I have trouble reading the Legends on the plot or I can not get the landscape mode to display horizontally. What should I do? 
> A: We have tried Ghostview on different platforms and have found that it operates quite differently on the different platforms. The Macintosh version seems the most limited. All that we can suggest is that you play with the settings and/or preferences until you have the best possible display. The other option is to switch to the GIF format. 
> Q13: I plan to use some of your opacities in a publication. What is the best reference to cite? 
> A: You can click on the Opacities methods and references for a list of refernces. The latest reference is 
> N. H. Magee, Jr., J. Abdallah, Jr., R. E. H. Clark, et al., "Atomic Structure Calculations and New Los Alamos Astrophysical Opacities", Astronomical Society of the Pacific Conference Series (Astrophysical Applications of Powerful New Databases, S. J. Adelman and W. L. Wiese eds.) 78, 51 (1995). 
> You may also refer to the web page: 
> http://aphysics2.lanl.gov/cgi-bin/opacrun/tops.pl 
> Please mail questions or comments to:
> LANL T-1 Opacities <opacity@lanl.gov>
**References for the TOPS code **  

> N. H. Magee, Jr., J. Abdallah, Jr., R. E. H. Clark, et al., "Atomic Structure Calculations and New Los Alamos Astrophysical Opacities", Astronomical Society of the Pacific Conference Series (Astrophysical Applications of Powerful New Databases, S. J. Adelman and W. L. Wiese eds.) 78, 51 (1995). 
> TOPS: A Multigroup Opacity Code;  Report LA-10454, by Joseph Abdallah, Jr. and Robert E. H. Clark. 
> Astrophysical Opacity Library; Los Alamos Report LA-6760-M, by W. F. Huebner, A. L. Merts, N. H. Magee, Jr., M. F. Argo 
> The Los Alamos LEDCOP code; Los Alamos Report LA-UR-97-1038, by N.H. Magee, A.L. Merts, J.J. Keady and D.P. Kilcrease 
> Please mail questions or comments to:
> LANL T-1 Opacities <opacity@lanl.gov>
**Photon Energy Grid **  

> u Grid Definition 
> The elemental opacities are calculated on a uniform grid of temperatures, electron degeneracy paramaters and dimensionless photon energies u, where u is defined as:

u = hv / kT 

hv is the photon energy in eV and kT is the temperature in eV. The u grid is selected instead of the photon energy grid because the same u grid can be used for all temperatures and cover the important photon energy ranges needed to integrate the Rosseland and Planck "gray" opacities. These photon energy ranges would be 0. - 20. eV for a temperature of 1. eV and 0. - 2000. eV for a 100. eV temperature. For the u grid, the range would be 0. - 20. for both temperatures. 
> u Grid used on the Web Page 
> The opacities are calculated on a grid of 14,900 u points for each temperature point. This grid is shown below: 
>   u Values      14,900 Point Grid
>  _________  ___________________________
>       0.0
>        |
>        |    9600 points, steps of .00125
>        |
>      12.5
>        |
>        |    1600 points, steps of .005
>        |
>      20.0
>        |
>        |    1000 points, steps of .01
>        |
>      30.0
>        |
>        |     700 points, steps of .1
>        |
>     100.0
>        |
>        |     900 points, steps of 1.0
>        |
>    1000.0
>        |
>        |     900 points, steps of 10.0
>        |
>   10000.0
>        |
>        |     200 points, steps of 100.0
>        |
>   30000.0
>            _____
>            14900 points
**Help file for the TOPS code **  

> Your first choice as a user is the type of data file to use. There are two types of data files: ATOMIC and LEDCOP. The ATOMIC files are the latest data files produced by the LANL opacity team (groups T-1 and XCP-5) and are the preferred files. 
> See file of currently available materials for the current list of available materials. The material ID numbers are prefixed by the letter n. The LEDCOP files are older cross section files and are included for the sake of continuity. 
> The default is to use the most recent available data file for each element. 
> As a user you may choose to mix an arbitrary number of elements. You have the option of specifying the mixture by number fraction or by mass. You may also choose to specify particular isotopic weights in the mixture. 
> The default is to specify mixtures by number fraction and use the naturally occurring isotopic weights. 
> You have several options for temperatures. You may select individual temperature, choose a subset of the tabulated temperatures, or thin the tabulated temperatures. In any case, the selected set of temperatures must be elements of the default temperature grid. 
> The default is to use temperatures in the range of 0.1 to 10 keV. 
> In a similar manner you can select the density grid. In contrast to the temperature grid, there is no default density grid. You are free to select specific densities, or choose a grid with either logarithmic or linear spacing. 
> One should exercise some restraint in choosing the total number of temperature and density points, especially for mixtures containing a large number of elements. The run times can become quite long. The Web Page will give you an time estimate on the Output Selection page after you submit your calculation from the first input page. If the time estimate is too long, the Web Page will refuse the calculation. 
> One point to be noted is that the range of densities for which cross sections are tabulated varies with temperature. At low temperatures there is a relatively low upper bound on density. This causes the TOPS code to attempt to find opacities for which cross section data do not exist. If this happens, the TOPS code prints a warning message on both the columnar table output and on all graphs except the 3-D graphs. It then uses the cross sections for the highest density point for that temperature to calculate the gray opacities. If multigroup opacities are requested, that gray opacity is put into each multigroup spot so that there is no variation of opacity with photon energy. This should point out that the displayed multigroup opacity does not represent a true multigroup calculation for this point. The frequency dependent data is handled the same way as the multigroups. 
> If you wish to have multigroup opacities, you may select photon group boundaries in keV in a manner similar to the selection of the density grid. The default is to use a logarithmic spacing of 33 boundaries (32 groups) with energies between .001 and 300. keV. 
> Just as there is a pratical limit to the product of number of temperatures times number of densities, there is a limit on the product of number of temperatures times number of densities times number of group boundaries. Currently this product is limited to 50000. Thus if you choose the default temperature grid with 50 temperatures and a density grid with 20 densities, you can still have 50 photon groups. 
> If you choose to look at frequency dependent opacities, the TOPS code will automatically output all of the available data for each temperature- density point. At present, this is 3000 or 3900 frequency points for each case. You may restrict the frequency range on the various graphics pages if you do not want to download the entire table. 
> The TOPS code calculates the plasma cutoff frequency, the frequency below which photons may not propagate in a plasma. Any group which lies partly or fully below this frequency has the opacity in that group set to 1010. Normally this cutoff frequency is very low relative to the temperature and should not make any difference in a radiation transport calculation. 
> The default mode when you press the submit button is to calculate gray Rosseland and Planck opacities along with the average number of free electrons. You also have the option of requesting multigroup and/or frequency dependent opacities. If you choose the frequency dependent option, you are limited to 6 temperature-density points per calculation. Resulting tables can be saved to your local machine with the FILE button on your web browser. 
> The normal columnar TOPS tables first list any warning messages. Then the temperature, density and (if requested) multigroup photon energy grids. boundaries. After this, the gray Rosseland and Planck opacities are shown. If you requested multigroup opacities, these are listed next. Finally, the frequency dependent opacities are listed if this calculation was requested. 
> Special note to SESAME users. This Web Page is now setup to output the special SESAME format ASCII files for opacities. Users must have already obtained the SESAME codes from T-1 at LANL before they can use these tables. See the SESAME writeup for more details about the tables produced by this Web Page. 
> Please mail questions or comments to:
> LANL T-1 Opacities <opacity@lanl.gov>

## doc/GUI,IO相关.docx (65744 B)

<!-- 提取说明: 段落 42，表格 6 -->

**GUI，IO相关**  

**GUI图形用户界面**  

> GUI4Multi1D.exe采用WinForm技术，使用VisualStudio C++.NET编写，基于.NET的3.5框架。但微软公司在2010年之后的VS中放弃了C++.NET的技术支持。目前程序界面使用VisualStudio2008编制，没有升级开发平台的可能。目前Windows系统都有对.NET 3.5版本框架的支持，因此图形界面暂无无法运行的风险。（后续不好说）
**初始化文件**  

**default.ini**

*[表格 1]*
|  |  |
|---|---|
| [Config] Functioning=4 MaxNumOfGrids=1000 | 程序设置 程序功能，4表示GUI下拉程序列表中的东西。 |
| [RecentFiles] File[0]=cases_YuBo\DirectDrive_CHPOP2015_300TW.case File[1]=cases_YuBo\DirectDrive_CHFoamAu_Mix31_SamePower_40p120_s.case | 最近的文件。 |

> [Config]
> Functioning=4
> MaxNumOfGrids=1000
> [RecentFiles]
> File[0]=cases_YuBo\DirectDrive_CHPOP2015_300TW.case
> File[1]=cases_YuBo\DirectDrive_CHFoamAu_Mix31_SamePower_40p120_s.case
> File[2]=cases_YuBo\DirectDrive_CHFoamAu_Mix31_SamePower_40p120.case
> 保存临时文件。
**config.ini**
> GUI界面左上角的程序下拉选单设置在[Programs]中，通过Executable定义程序名（必须和根目录下的程序文件一致），通过Type定义程序类型，0为辐射流体力学计算；1为不透明度；2为状态方程。
> [Programs]
> Program[0].Executable=Multi1D++.exe
> Program[0].Type=0
> Program[1].Executable=multi7.6.exe
> Program[1].Type=0
> Program[2].Executable=Snop++.exe
> Program[2].Type=1
> Program[3].Executable=FEOS.exe
> Program[3].Type=2
> Program[4].Executable=Multi1D++20110907.exe
> Program[4].Type=0
> Program[5].Executable=Multi1D++20200819.exe
> Program[5].Type=0
> [Tools]
> GNUPlot=tools/gnuplot/bin/wgnuplot.exe
> Notepad=tools/npp/notepad++.exe
**输出文件**
> 下面给出输出文件各个变量的意义和定义公式。
***.center.dat**
> 此文件记录

*[表格 2]*
| Time        	Time(s) | 时间 |
|---|---|
| CMC         	Mass coordinate at cell center(g) | 网格中心的质量坐标 |
| XC          	Center of cell (cm) | 网格中心的位置坐标 |
| R           	Density (g/cm3) | 密度 |
| Te          	Electron temperature (eV) | 电子温度 |
| Pe          	Electron pressure (dynes/cm2) | 电子压力 |
| Zi          	Effective ion number | 电离度 |
| D           	Specific external deposition(erg/g) | 能量沉积 |
| DENE        	Electron number density (1/cm3) | 电子数密度 |
| Ee          	Electron specific energy (erg/g) | 电子能量 |
| Ei          	Ion specific energy (erg/g) | 离子能量 |
| Ti          	Ion temperature(eV) | 离子温度 |
| Pt          	Total pressure (dynes/cm2) | 总压力 |
| dln(Pt)/dx  	Delta total pressure/dx (dynes/cm3) | dln(Pt)/dx相对压力的空间梯度 |
| Pi          	Ion pressure (dynes/cm2) | 离子压力 |
| Te(Emission)	Emission Temperature (eV) | 用于发射谱计算的电子温度（仅供参考） |
| dln(R)/dx   	Delta density/dx | 相对密度的空间梯度 |
| MID         	Material ID | 物质的ID |
| Ea          	Alpha specific energy (erg) | Alpha能量（erg） |
| fT          	Fraction of Tritium | 网格中T的份额 |
| fD          	Fraction of Deuterium | D的份额 |
| fHe3        	Fraction of He3 | He3的份额 |
| fZ          	Fraction of Non-reactive | 非反应燃料的份额 |
| dndt        	Neutron generation rate(1/cm3/s) | 单位体积的中子产率 |
| dpdt        	Proton generation rate(1/cm3/s) | 单位体积的质子产率 |
| Index       	Index | 索引 |
| TR_cell     	Radiation Temperature at cell(eV) | 网格的平均辐射温度 |
| kei         	Electron-ion coupling coefficient | 电子离子耦合系数 |
| ke          	Electron thermal conductivity | 电子热传导系数 |
| ki          	Ion thermal conductivity | 离子热传导系数 |
| coulog_ei   	Coulomb Logarithm for electron-ion coupling | 电子离子的库伦对数 |
| pviscous    	Viscous pressure (dynes/cm2) | 黏性压力（人工粘性） |
| len_e_stop  	Electron stopping length (cm) | 电子阻止长度 |
|  |  |

***.interface.dat**

*[表格 3]*
| Time       	Time (s) | 时间 |
|---|---|
| CMI         	Mass coordinate at cell interface(g) | 网格界面的质量坐标 |
| X           	Position of interfaces (cm) | 网格界面的位置 |
| V           	Velocity of interfaces (cm/s) | 网格界面的速度 |
| S+          	Rad. flux in positive direction(erg/s/cm2) | 网格界面上正向（向右）的辐射流 |
| S-          	Rad. flux in negative direction(erg/s/cm2) | 网格界面上负向（向左）的辐射流 |
| S           	Total radiation flux (S+ - S-)(erg/s/cm2) | 总的辐射流（界面上S+ - S-） |
| Tr          	Radiation temperature (eV) | 辐射温度 |
| Vsound      	Sound speed (cm/s) | 声速 |
| Albedo(Wall)	Albedo of leaky wall | 输运管壁的反照 |
| Albedo(Part)	Albedo of leaky particle | 掺杂粒子的反照 |
| RelativeFlux	Relative heat flux = flux/flux_free_streaming | 相对热流（电子热流/自由电子热流） |
| FluxLimited 	Flux Limited(erg/s/cm2) | 限流的电子热流 |
| FluxNonlocal	Nonlocal heat flux(erg/s/cm2) | 非局域模型计算的电子热流 |
|  |  |
|  |  |

***.group.dat**

*[表格 4]*
| Time        	Time (s) | 时间 |
|---|---|
| FREI_left   	Photon energy left boundary(eV) | 能群的左边界 |
| FREI_center 	Photon energy at group center | 能群中点 |
| FREI_right  	Photon energy right boundary (eV) | 能群的右边界 |
| I-Left      	Spectrum (erg/sec/eV) on left boundary | 左向的光谱强度 |
| I-Right      Spectrum (erg/sec/eV) on right boundary | 右向的光谱强度 |

***.scalars.dat**

*[表格 5]*
| TIME        	Time (s) | TIME        	Time (s) | 时间 |
|---|---|---|
| ISTEP       	Number of time step | ISTEP       	Number of time step | 时间步数（反映每个时间点的迭代次数） |
| ENLAS       	Incident laser energy(erg) | ENLAS       	Incident laser energy(erg) | 入射激光能量 |
| ENQUE       	Absorbed laser energy(erg) | ENQUE       	Absorbed laser energy(erg) | 吸收的激光能量 |
| ENIE        	Electron internal energy(erg) | ENIE        	Electron internal energy(erg) | 电子内能 |
| ENII        	Ion internal energy(erg) | ENII        	Ion internal energy(erg) | 离子内能 |
| ENKI        	Kinetic energy(erg) | ENKI        	Kinetic energy(erg) | 动能 |
| ENRAD       	ENRL*-ENRG* | ENRAD       	ENRL*-ENRG* | 辐射能量绝对值 |
| ENRL1       	Rad. energy (left b.) | ENRL1       	Rad. energy (left b.) | 不同边界上的辐射能量 |
| ENRL2       	Rad. energy (internal b. left) | ENRL2       	Rad. energy (internal b. left) | 不同边界上的辐射能量 |
| ENRL3       	Rad. energy (internal b. right) | ENRL3       	Rad. energy (internal b. right) | 不同边界上的辐射能量 |
| ENRL4       	Rad. energy (right b.) | ENRL4       	Rad. energy (right b.) | 不同边界上的辐射能量 |
| ENRG1       	Abs. energy (left b.) | ENRG1       	Abs. energy (left b.) | 不同边界上的吸收能量 |
| ENRG2       	Abs. energy (internal b. left) | ENRG2       	Abs. energy (internal b. left) | 不同边界上的吸收能量 |
| ENRG3       	Abs. energy (internal b. right) | ENRG3       	Abs. energy (internal b. right) | 不同边界上的吸收能量 |
| ENRG4       	Abs. energy (right b.) | ENRG4       	Abs. energy (right b.) | 不同边界上的吸收能量 |
| EALFA       	Energy in alpha particles(erg) | EALFA       	Energy in alpha particles(erg) | Alpha粒子的能量 |
| ENAL        	Energy lost in alpha particles(erg) | ENAL        	Energy lost in alpha particles(erg) | Alpha粒子带出系统的能量 |
| ENAG        	Fusion energy / 5(erg) | ENAG        	Fusion energy / 5(erg) | 聚变能的1/5（本来是用于DT反应的alpha粒子的能量） |
| EYIELD      	Number of neutrons | EYIELD      	Number of neutrons | 中子产额 |
| Nproton     	Number of protons | Nproton     	Number of protons | 质子产额 |
| POWRAD(t)   	Radiation power history(erg/s) | POWRAD(t)   	Radiation power history(erg/s) | 辐射功率的演化 |
| MaxDrho@    	Position of max density change (cm) | MaxDrho@    	Position of max density change (cm) | 最大密度的位置 |
| MaxDTr@     	Position of max TR change (cm) | MaxDTr@     	Position of max TR change (cm) | 最大辐射温度梯度的位置 |
| MaxDPressure@	Position of max pressure change (cm) | MaxDPressure@	Position of max pressure change (cm) | 最大压力梯度的位置 |
| MaxRho@     	Position of max density (cm) | MaxRho@     	Position of max density (cm) | 最大质量的位置 |
| MaxTr@      	Position of max TR (cm) | MaxTr@      	Position of max TR (cm) | 最大辐射温度 |
| MaxPressure@	Position of max pressure (cm) | MaxPressure@	Position of max pressure (cm) | 最大压力位置 |
| MaxDeposition@	Position of max deposition (cm) | MaxDeposition@	Position of max deposition (cm) | 最大激光能量沉积的位置 |
| TOTALMASS   	Total mass (g) | TOTALMASS   	Total mass (g) | 系统总的质量（核反应会造成能量减少） |
| TOTALENERGY 	Total energy (g) | TOTALENERGY 	Total energy (g) | 系统总的能量 |
| TR_Left     	Tr out of left boundary (eV) | TR_Left     	Tr out of left boundary (eV) | 左边界的辐射温度 |
| TR_Right    	Tr out of right boundary (eV) | TR_Right    	Tr out of right boundary (eV) | 右边界的辐射温度 |
| rhoR        	Areal density of fuel (g/cm2) | rhoR        	Areal density of fuel (g/cm2) | 燃料面密度（积分计算到nfuel） |
| rhoRHS       Areal density of fuel at hot spot | rhoRHS       Areal density of fuel at hot spot | with Ti > |
| rhoRTotal     Total areal density | rhoRTotal     Total areal density |  |
| rhoRN        Neutron-averaged areal density | rhoRN        Neutron-averaged areal density | The fuel areal density at the time of neutron yield(measured by the knock-on diagnostic technique) |
| rhoRHM      harmonic-mean areal density | rhoRHM      harmonic-mean areal density | the areal density of thinner regions is weighted more than that of thicker regions. |
| rhoRAM      Arithmetic-mean areal density | rhoRAM      Arithmetic-mean areal density | , the ratio of the stagnating mass to the stagnation hot-spot surface area |
| 其他定义： | 其他定义： |  |
|  |  |  |
| Centroid    	Center of fuel mass (cm) | Centroid    	Center of fuel mass (cm) | 燃料质心的位置（积分计算到nfuel） |
| V_imp       	Implosion velocity of fuel (cm/s) | V_imp       	Implosion velocity of fuel (cm/s) | 其他计算方法还有：，或（老版本差sqrt(0.5)） |
| Ti_burn_avg 	DT Burn-averaged ion temperature (eV) | Ti_burn_avg 	DT Burn-averaged ion temperature (eV) |  |
| Ti_mass_avg 	Mass-averaged ion temperature (eV) | Ti_mass_avg 	Mass-averaged ion temperature (eV) |  |
| 不同界面的关系 | 不同界面的关系 | 不同界面的关系 |
| PosInterface	Position of fuel interface(cm) | 燃料和壳层界面 | 燃料和壳层界面 |
| PosFallLine 	Position of fall line(cm) | Fall-line的位置，两种定义：在减速开始时为准；燃料壳层界面最大速度时为准。 | Fall-line的位置，两种定义：在减速开始时为准；燃料壳层界面最大速度时为准。 |
| PosBubble   	Position of bubble(cm) | 泡泡的位置 | 泡泡的位置 |
| PosMix      	Position of mixing(cm) | 混合边界（使用fall-line的interface penetration fraction定义的相对尺度） | 混合边界（使用fall-line的interface penetration fraction定义的相对尺度） |
| AlbedoLeft  	Albedo at left boundary | 左边界反照， | 左边界反照， |
| AlbedoRight 	Albedo at right boundary | 右边界反照， | 右边界反照， |
| Ti(DDburn_avg) 	DD burn-averaged ion temperature(eV) |  |  |
| Ti(DHe3burn_avg) 	DHe3 burn-averaged ion temperature(eV) |  |  |
| AbsoluteError 	Absolute error in energy conservation(erg) | 能量守恒误差 | 能量守恒误差 |
| RelativeError 	Relative error in energy conservation | 能量守恒的相对误差 | 能量守恒的相对误差 |
| FusionDeposEnergy 	Total deposited fusion energy(erg) | 沉积的聚变能量 | 沉积的聚变能量 |
| FusionTotalEnergy 	Total generated fusion energy(erg) | 产生的聚变能量 | 产生的聚变能量 |
| FusionEAGain 	Alpha energy gain(erg) | Alpha能量增益 | Alpha能量增益 |
| FusionEALoss 	Alpha energy loss(erg) | Alpha能量的损失（逃逸出计算边界） | Alpha能量的损失（逃逸出计算边界） |
| Fusion.dndt     neutron generation rate(1/s) | 空间积分的中子产率 | 空间积分的中子产率 |
| Fusion.dpdt     proton generation rate(1/s) | 空间积分的质子产率 | 空间积分的质子产率 |
| Fusion.FuelBound Boundary position of fuel(cm) | 燃料区边界（nfuel定义） | 燃料区边界（nfuel定义） |
| AblatedMass  	Ablated mass(g) | 以速度变方向网格处为边界，积分计算此处到靶丸外表面的质量。 | 以速度变方向网格处为边界，积分计算此处到靶丸外表面的质量。 |
| AblatedPressure	Ablation pressure(dyne/cm2) | 速度变方向网格的压力 | 速度变方向网格的压力 |

***.final.dat**
> 保存最后时刻的等离子体状态。
***.backlighter.dat**
> 背光信息（当设置计算背光时计算。）

*[表格 6]*
| Time        	Time(s) | 时间 |
|---|---|
| CMC         	Mass coordinate at cell center(g) | 网格中心的质量坐标 |
| XC          	Center of cell (cm) | 网格中心的位置坐标 |
| R           	Density (g/cm3) | 密度 |
| Te          	Electron temperature (eV) | 电子温度 |
| MFP_Rosseland	Rosseland Mean Free Path(cm) | Rosseland平均自由程 |
| MFP_Planck   	Planckian Mean Free Path(cm) | Planck平均自由程 |
| Uemission    	Emission | 自发射强度 |


## doc/QuietStart.docx (205813 B)

<!-- 提取说明: 段落 30，表格 0 -->

**流体力学基础**  

**程序计算中的问题**  

**初始压强差导致的网格运动**  

> 不同材料初始时由于状态方程中初始温度、密度下压力的差异，或者材料与针孔界面。导致网格交界面（如网格与真空交界面/不同材料交界面）存在压强差，在没有外界驱动的情况下，网格也会运动。为解决这一问题，Multi1D++中使用了QuietStart方法。
**Quiet Start方法**
> 这也是BUCKY1D和Hyades中使用的方法，通过设置初始开关温度，只有当离子温度超过某一温度值时，网格的动量方程计算中压力差才会改变，否则压力引起的加速度强制设为0.
> 图 3 Hyades(左图)和Multi1D++启用QuietStart功能后（右图）的计算结果，烧蚀层材料的分布仍然有差异，但是飞片速度相当。默认Hyades关闭输运计算（关闭机制与Multi1D++不一致。）显然左图的Hyades烧蚀层计算有误，因为第一层Mylar在撞击到Cu后被反弹，而烧蚀层没有压力将反弹抑制。
> 图 4 左图为打开Hyades辐射输运计算（设置不透明度文件）的结果，则烧蚀部分的分布更为相近，但飞片启动时间（约9ns）和飞片速度比Multi1D的计算结果更快更早撞击Al片（20ns）。而Multi1D++的计算结果这两个时间分别为（11ns和25ns）。
> Hyades中在温度低于Tecold（默认10eV）时，使用冷的不透明度而不是从数据文件中查找。如果设置tecold为0.1eV（即相当于关闭tecold功能），对结果影响不大。
> 具体原因可能是二者算法不同，现在没有查到。
**Multi1D++中的QuietStart的实现**
> 其他文献中还有使用两个温度的算法，即熔点和沸点之间采用线性插值来使用边界压力的方式来计算压力差。
> 在计算动量方程获得加速度的时候，
> 先根据原来的程序计算出速度变化的速率，然后根据加速度方向判断影响。具体代码为：
>         if(dvdt[0] < 0.0) dvdt[0] *= this->fractionc[0];
>         for(int i=1;i<n;++i){
>             if(dvdt[i] > 0.0){
>                 dvdt[i] *= this->fractionc[i-1];
>             }else{
>                 dvdt[i] *= this->fractionc[i];
>             }
>         }
>         if(dvdt[n] > 0.0) dvdt[n] *= this->fractionc[n-1];
> 参考文献： 2016PPCF58(J.Velechovsky)_[PALE]Hydrodynamic modeling of laser interaction with micro-structured targets
**QuietStart的影响**
> QuietStart在不同的算例中可能会对计算过程的稳定性造成影响，请参考Changes.log中记录的建议处理。
> 如QuietStart会导致初始的几步密度没有变化，如果时间步判据中只包括密度变化，那么就会被判定为No Variation，误判为出错，这时可以设置Max Allowed No Variation Steps为一个大的值。
> 此外，纯冲击波的算例显示，有无QuietStart会导致冲击波速度变慢！还需要结合具体算例分析。
**QuietStart负面影响算例1**
> *QuietStart也可能对某些EOS产生不同的效果，如下面算例中钻石层（CwuCC.case）采用1341号材料，有无QuietStart设置的结果。使用QuietStart导致冲击波没有穿透该层材料，将该层的QuietStart设置取消，结果正常。

## doc/多群辐射源(FDS).docx (22847 B)

<!-- 提取说明: 段落 22，表格 2 -->

**多群辐射源（Frequency Dependent Source）**  

> 输入有能谱分布的辐射源。
**输入的方式**  

**默认输入方式**
> 输入的方式有三种。其中的两种使用SpectroSim多道谱仪解谱程序对实测X射线源的解谱结果。其中一种使用能谱和辐射流时间点数据两个定义文件，另一种使用能谱、光子能量和辐射流时间点数据三个定义文件（推荐前者，后者在新版本中废除）。
> 程序根目录下附带了两组多群辐射源的数据，都来自实验中X射线源时变能谱的解谱的结果，供参考：
> M带成分较强的：
> Shot20120821015.Spline3OrderIterative.Flux0.dat
> Shot20120821015.Spline3OrderIterative.Flux3ns.dat（展宽的时间文件）
> Shot20120821015.Spline3OrderIterative.TotalRadiation2DVertical0.dat
> M带较弱的：
> Flux0.dat
> Flux3ns.dat（展宽的时间文件，用于长脉冲的模拟，从Flux0文件将第一列乘以3得到）
> TotalRadiation2D0Vertical.dat
> 另外一种定义方式使用MULTI1D的多群计算结果，即*.group.dat文件，可以选择左右两个边界（对应*.group.dat文件中的I-Left和I-Right数据列）的出射能谱作为辐射源。
**自定义文件**
> 如果想自己编辑文件，如使用Matlab编写脚本生成时变的能谱，建议使用能谱和辐射流时间点数据两个定义文件即上面SpectroSim程序生成的一种数据文件格式。
> 其中辐射流时间点数据只需要数据文件的第一列数据有效，以秒为单位。
> 能谱文件为多行多列。其中第一列为光子能量点（eV），第二列开始的各个列为对应光子能量点的能谱强度（W/m2/sr/eV），能谱列的列数应该与辐射流时间点的数目相同。如时间点数据文件有n行数据，那么，能谱文件就有n+1列数据。
> 文件格式可以参考上一节提到的两组示例数据。下面简略介绍
> 时间点数据文件

*[表格 1]*
| 0 1e-10 2e-10 … 3e-9 |
|---|

> 能谱文件

*[表格 2]*
| 80    1e-10 1e-10 … 1e-10 100    2e-10 2e-10 …2e-10 1200   2e-10 2e-10 …2e-10 … 6000  1e-11 1e-11 …1e-11 |
|---|


## doc/反弹冲击波的撞击壳的时刻.docx (133017 B)

<!-- 提取说明: 段落 18，表格 0 -->

> Multi1D++的应用与提高
**特殊位置的提取**  

**反弹冲击波的撞击壳的时刻**  

> 爆推靶内爆过程中冲击波聚心反弹后会再次撞击玻璃薄壳导致玻璃壳解体，从而终止燃料的约束和聚变反应。如何提取冲击波反弹后与玻璃壳的撞击时刻？
> 下图显示了冲击波反弹时刻附近的压力梯度值
> 下图给出了界面(Scalars.PosInterface)、fall-line(Scalars.PosFallLine)和最大压力（Scalars.MaxPressure@）、压力梯度（Scalars.MaxDPressure@）的轨迹图（红线为中子产额累积值），图中最大压力线（蓝线）能够看到冲击波反弹后与玻璃壳对撞并折返回球心的轨迹。而最大压力梯度（绿线则没有折返而是与界面流线几乎重合）。需要注意的是，上述信息提取如最大压力和压力梯度都是绝对值，导致没有完全跟踪到DT气体中的冲击波位置，这主要是因为DT气体中的冲击波的压力相对壳层的压力以及较小，直到聚心撞击附近才被跟踪到。反弹冲击波撞玻璃壳的时刻约为0.64ns。
> 下面用Matlab程序重新处理冲击波位置，使用相对值。
> [posOfShock, shock_value] = calShockFront(Time1D,XC,PT,true,true);
> 用相对压强提取到的冲击波位置，正确反映了聚心冲击波的位置，但反弹冲击波位置不光滑。且折返冲击波明显不正确。
> 通过上述考察，以MaxPressureAt为基准处理，基本思路为取两次聚心值之间曲线最大值的时刻为冲击波碰撞时刻。
> 代码：
> function treshock = calTimeReshockCollision(Time1D, MaxPressureAt)
>     ishock0 = find(MaxPressureAt <= 0, 1);
>     ishock1 = length(MaxPressureAt) - find(MaxPressureAt(end:-1:1) <= 0, 1);
>     [~, imax] = max(MaxPressureAt(ishock0:ishock1));
>     treshock = Time1D(imax + ishock0);
> end
> 处理得到的时刻为6.34e-10s

## B 组：旧版 DOC 文档（win32com 优先，字节回退）

## doc/Hyades 数据格式说明.doc (57344 B)

<!-- 提取说明: Word97 OLE 分片表解码（CP936/UTF-16LE 逐片）：段落 226，字符 14155 -->

> Hyades 数据格式说明
> 数据库数据列表
> Ionpot.dat 		离化势文件
> Coldopac.dat  	冷不透明度（多群在线计算不透明度时低温数据不可靠，使用设定的室温不透明度）
> Eoslib.lbf			EOS数据库
> Opaclib.lbf		不透明度数据库
> Tfdat.lbf		  	QEOS模型的Thomas-Fermi数据库，根据压缩原子的spherical-cell模型的热稠密等离子体Thomas-Fermi理论计算得到电子EOS属性。
> 数据库中的材料
> Appendix I - HYADES Equation of State Library
> CAS has assembled a library of equation of states from a variety of sources.  In the following lists, more than one entry for a material may be encountered.  In this case, the different tables may have come from different sources, be built for different temperature-density regimes, or be derived from different theoretical models.  The user is referred to the original source of the table which may be found on the first line of the ASCII data file.
> 揝ingle fluid� EOS pressure and energy tables have material numbers 1 < num < 998, while Rosseland mean and Planck mean opacity tables have numbers 1000 < num < 2000. Two-temperature (搕wo-fluid�) EOS pressure and energy tables may be specified in a material region.  Electron tables have numbers 2000 < num < 3000, and ion tables have numbers 3000 < num < 4000.  Both tables must be specified.
> In the following lists：
> “Zbar” is the average atomic weight of the material,
> “Abar” is its average atomic number, and
> “Rho0” is its solid or reference density. (g/cm3)
> Pressure/Energy tables:
> Preferred tables are indicated by an “*”.
> Two-temperature materials available are indicated by an �#�.
> EOS No..        Material           Zbar         Abar        Rho0
>     11        Deuterium+tritium  1.000       2.515       0.2205
>     21        Glass         10.00       20.028     2.65
> 22        Quartz       10.00       20.028     2.204
> 23        Quartz       10.00       20.028     2.204
>     24        Silica         10.00       20.028     2.65
>     31        Polyethylene          2.667       4.676       0.9540
>     32        Polystyrene            3.500       6.510       1.044      #
>     33        Polyurethane         3.763       7.038       1.265
>     34        Lucite        3.600       6.674       1.186
>     35        Parylene     5.500       10.815     1.42
> 36        Mylar        4.545       8.735       1.38
> 37        PolyVinyl Alcohol  3.645       6.782       1.264
>     41        Aluminum    13.00       26.982     2.7568
>     42        Aluminum    13.00       26.982     2.7
>     43        Aluminum    13.00       26.982     2.7          #
>     44        Aluminum    13.00       26.982     2.7      *  #
>     51        Gold          79.00       196.97     19.3        #
>     52        Gold          79.00       196.97     19.3
>     61        Hydrogen    1.000       1.008       0.0884
> 71        Lithium      3.000       6.939       0.5326
> 81        Beryllium    4.000       9.012       1.845
> 91        Argon        18.00       39.948     1.4
> 92        Argon        18.00       39.948     1.4
> 101       Neon         10.00       20.183     1.44
> 111       Copper      29.00       63.540     8.93
> 112       Copper      29.00       63.540     8.93
> 113       Copper      29.00       63.540     8.93
> 114       Copper      29.00       63.540     8.93
> 115       Copper      29.00       63.540     8.938   * #
> 121       Tungsten    74.00       183.85     19.237    #
>    131       Uranium     92.00       238.03     18.983
>    141       Tungsten carbide   38.75       94.191     14.970
>    151       Deuterium    1.000       2.014       0.1766
>    161       Aluminum oxide    10.00       20.392     3.97
>    162       Aluminum oxide    10.00       20.392     3.97
>    171       CD 2               2.667       5.347       1.0475
>    181       Iron           26.00       55.850     7.85
>    191       Helium      2.000       4.003       0.4
>    201       Krypton     36.00       83.800     2.5005
>    211       6 LiD          2.000       4.000       0.802
>    212       6 LiD          2.000       4.0145     0.792
>    213       LiD            2.000       4.4775     0.883
>    221       Oxygen      8.000       16.000     1.2620
>    231       Lead          82.00       207.19     11.34
>    241       LiH            2.000       4.000       0.775
>    251       Nitrogen     7.000       14.007     0.8572
>    261       Platinum    78.00       195.09     21.419
>    271       Tantalum    73.00       180.95     16.654
>    281       Molybdenum         42.00       95.940     10.2
>    291       Nickel       28.00       58.710     8.882
>    301       Dry-air      7.373       14.803     0.00129
>    311       Water        3.333       6.005       0.9982
>    312       Water        3.333       6.005       0.9998
>    313       Water        3.333       6.005       0.9982
>    314       Water        3.333       6.005       0.9982   *
>    321       Teflon       8.000       16.669     2.1520
>    331       High Explosive      5.626       11.04       1.840
>    332       PBX-9502    5.598       10.98       1.894
>    341       Diamond    6.000       12.011     3.51
>    342       Carbon, liquid       6.000       12.011     3.688
>    343       Carbon, Phenolic   4.648       9.010       1.4503
>    344       Carbon      6.000       12.012     2.25
>    362       Stainless Steel       25.80       55.368     7.91
>    371       Xenon       54.00       131.3       3.0551
>    381       Selenium    34.00       78.96       4.8
>    391       Silicon       14.00       28.08       2.42
>    392       Silicon       14.00       28.08       2.42
>    401       Tin             50.00       118.7       7.29        #
>    402       Tin             50.00       118.7       7.29
>    411       Germanium           32.00       72.60       5.36
>    422       Titanium    22.00       47.90       4.54
>    431       C8H7Br     5.625       11.441     1.53
>    441       BeO           6.000       12.505     3.008
>    451       Magnesium            12.00       24.305     1.740
>    461       Europium    63.00       151.96     5.253
>    466       Neodymium           60.00       144.24     6.95
>    471       Gadolinium           64.00       157.25     7.898
>    481       Calcium      20.00       40.000    1.550
>    491       Silver         47.00       107.87     10.50     #
>    501       Epoxy        3.241       5.9134     1.185
>    502       Epoxy        3.2407     5.9134     1.185
>    511       Boron Carbide       5.200       10.416     2.45
>    521       Vanadium    23.00       50.942     6.11
>    531       Zinc           30.00       65.37       7.139
>  #Two-temperature materials available：数据表格数据与单温个数一致。
> Rosseland/Planck mean opacity tables:
> Opacity No..   Material      Zbar         Abar
>       1022   Quartz       10.00       20.028
>       1031   Polyethylene          2.667       4.676
>       1032   Polystyrene            3.500       6.510
>       1033   Polyurethane         3.763       7.038
>       1035   Parylene     5.500       10.815
>       1036   Mylar        4.545       8.735
>       1041   Aluminum    13.00       26.982
>       1051 *  Gold          79.00       196.97
>       1052 *  Gold          79.00       196.97
>       1061   Hydrogen    1.000       1.008
>       1071   Lithium      3.000       6.939
>       1081   Beryllium    4.000       9.012
>       1091   Argon        18.00       39.948
>       1101   Neon         10.00       20.183
>       1111   Copper      29.00       63.540
>       1121 *  Tungsten    74.00       183.85
>       1151   Deuterium    1.000       2.014
>       1161   Alumina     10.00       20.392
>       1181   Iron           26.00       55.850
>       1191   Helium      2.000       4.003
>       1201   Krypton     36.00       83.800
>       1221   Oxygen      8.000       16.000
>       1251   Nitrogen     7.000       14.007
>       1281   Molybdenum         42.00       95.940
>       1291   Nickel       28.00       58.710
>       1301   Dry-air      7.373       14.803
>       1311   Water        3.333       6.005
>       1344   Carbon      6.000       12.000
>       1371   Xenon       54.00       131.30
>       1391   Silicon       14.00       28.090
>       1401   Tin             50.00       118.69
>       1422   Titanium    22.00       47.90
>       1451   Magnesium            12.00       24.32
>       1461   Europium    63.00       151.96
>       1481   Calcium     20.00       40.00
>       1491   Silver         47.00       107.68
> *   Rosseland mean tables only 本来应该存储Planck平均不透明度的位置用0代替。
> EOS ASCII数据格式(Appendix III - Equation of State ASCII Material File Format)
> The binary EOS library file is formed (using the HYADLIBM program) from individual material files.  Each of these material files is in an ASCII format.  The first line of each material file contains a common material name and historical information about where the data came from.  The second line begins the actual data and consists of the HYADES EOS number, the average atomic number (ZBAR), average atomic weight (ABAR), normal density (DEN), and length of the data array, which follows.  The format for this line is:  1x,i5,4x,1p3e15.8,3x,i5.  The third and subsequent lines contain the EOS information:  the number of density points (NR), the number of temperature points (NT), an array of density points (NR long), an array of temperature points (NT long), followed by a matrix of pressures (NR*NT long), followed by a matrix of energies (NR*NT long).  The format for this data is  1p5e15.8.
> NOTE:  This format is quite similar to that of the Los Alamos Sesame library.  Also, the units used here differ from that in the Sesame tables.
> 单位：
> 密度 g/cm3; 温度 keV; 压强 dyne/cm2;比内能 erg/g
> 例：eos_2051.dat
> GOLD        LANL SESAME #2700-304 DATED: 81678 101582
>   2051     7.90000000E+01 1.96967000E+02 1.93000000E+01    4772
>  1.01000000E+02 2.30000000E+01 0.00000000E+00 1.50781250E-01 2.87685800E-01
>  4.24600000E-01 8.15425000E-01 1.20625000E+00 1.99433269E+00 2.78242310E+00
>  3.57050000E+00 5.21100000E+00 6.75500000E+00 8.20250000E+00 9.65000000E+00	材料名和生成的历史信息
> HYADES EOS编号，Zbar, Abar, Rho, 数组长度
> NR, NT, RHO(1~NR), T(1~NT), P(1~NR*NT), E(1~NR*NT)
> 数组长度 = 2 + NR + NT + 2*NR*NT		例：qeos_115.dat
> COPPER      LLNL-QEOS Dated: 082802
>    115     2.90000000E+01 6.35400000E+01 8.93800000E+00   23774
>  1.28000000E+02 9.20000000E+01 1.00000000E-10 1.77827941E-10 3.16227766E-10
>  5.62341325E-10 1.00000000E-09 1.77827941E-09 3.16227766E-09 5.62341325E-09
>  1.00000000E-08 1.77827941E-08 3.16227766E-08 5.62341325E-08 1.00000000E-07
>  1.77827941E-07 3.16227766E-07 5.62341325E-07 1.00000000E-06 1.25892541E-06	材料名和生成的历史信息
> HYADES EOS编号，Zbar, Abar, Rho, 数组长度
> NR, NT, RHO(1~NR), T(1~NT), P(1~NR*NT), E(1~NR*NT)
> 数组长度 = 2 + NR + NT + 2*NR*NT		状态方程材料编号<998;使用双温表格时，电子流编号 2001-2999，离子流编号3001-3999
> 不透明度数据格式
> 不透明度参数使用同样的格式，压强处为平均Rosseland值，比内能处为平均Planck值，单位cm2/g：
> 例：opc_1151.dat
> DEUTERIUM   LANL SESAME #15264 DATED:  21793  21793
>   1151     1.00000000E+00 2.01600000E+00 1.76600000E-01    2931
>  3.10000000E+01 4.60000000E+01 1.00000000E-06 2.15443467E-06 4.64158887E-06
>  1.00000000E-05 2.15443467E-05 4.64158887E-05 1.00000000E-04 2.15443467E-04
>  4.64158887E-04 1.00000000E-03 2.15443467E-03 4.64158887E-03 1.00000000E-02
>  2.15443467E-02 4.64158887E-02 1.00000000E-01 2.15443469E-01 4.64158884E-01
>  1.00000000E+00 2.15443469E+00 4.64158884E+00 1.00000000E+01 2.15443467E+01	材料名和生成的历史信息
> HYADES EOS编号，Zbar, Abar, Rho, 数组长度
> NR, NT, RHO(1~NR), T(1~NT),  [图片] (1~NR*NT),  [图片] (1~NR*NT)
> 数组长度 = 2 + NR + NT + 2*NR*NT		灰度不透明度模型编号1001-1999
> Inverted EOS
> 为了在Multi1D中使用Hyades的EOS数据，需要将Hyades的EOS数据进行Invert，将
> P(R, T)，E(R, T)转化为P(R,E), T(R,E)
> 对于P(R, E)
> 对某个密度R,
> 首先根据E(R, T)找到对应的温度T(R, E)，这个过程需要差值
> P(R, E) = P(R, T(R, E))，这里同样需要差值。
> 外部不透明度数据格式
> Appendix VI - External Opacity Table File Format
> Provision has been made for an externally generated multi-group opacity table to be used in one material region.  The group structure of this table can be constructed in a fairly arbitrary manner, since the code will map the external structure into the internal one.
> The format for the external ASCII table is free format, 80 column width.  Continuation lines are allowed for each block containing arrays:
> Block No. Contents
>       1        character string header
>       2        number of temperatures, number of densities
>       3        array of temperatures (keV) N t  ; maximum number of temperatures is 200
>       4        array of densities (gm/cm 3 )  N r  ; maximum number of densities is 200
>       5        number of photon groups (keV), NGPS 1 , for temperature #1; maximum number of photon groups is 500
>       6        array of group boundaries for temperature #1 - there will be NGPS 1 +1 entries
>       7        array of opacities (cm 2 /gm) for temperature #1, density #1 – NGPS 1 +1 entries
>       8        array of opacities for temperature #1, density #2 - NGPS 1 +1 entries etc. for all densities
>   N r +7      number of photon groups (keV), NGPS 2 , for temperature #2
>   N r +8      array of group boundaries for temperature #2 - there will be NGPS 2 +1 entries
>   N r +9      array of opacities for temperature #2, density #1 - NGPS 2  entries
>   N r +10    array of opacities for temperature #2, density #2 - NGPS 2  entries
>   etc. for all N r  densities
> etc. for all N t  temperatures.
> An example of an external opacity table might be:
> External opacities for aluminum
> 6  15
> 1.00000E-02 3.00000E-02 1.00000E-01 3.00000E-01 1.00000E+00 3.00000E+00
> 2.70000E-06  8.54000E-06  2.70000E-05  8.54000E-05  2.70000E-04
> 8.54000E-04  2.70000E-03  8.54000E-03  2.70000E-02  8.54000E-02
> 2.70000E-01  8.54000E-01  2.70000E+00  8.54000E+00  2.70000E+01
> 85
> 1.00000E-06  2.00000E-03  2.23770E-03  2.50366E-03  2.80123E-03
> 3.13416E-03  3.50666E-03  3.92343E-03  4.38974E-03  4.91147E-03
> 5.49521E-03  6.14833E-03  6.87908E-03  7.69667E-03  8.61144E-03
> Ionpot.dat
> 离化势要用于计算HYADES模拟的产生和再启动phase。文件中有各个电子被剥离的离化势。
> Coldopac.dat
> 离化和原子物理模块在线生成的多群不透明度在低温下可能会产生错误的不透明度，因此提供了室温的分频不透明度数据（能点较少）。
> Two-temperature materials available
> Preferred tables
> Two-temperature materials available
> *   Rosseland mean tables only
> *   Rosseland mean tables only
> *   Rosseland mean tables only

## matter++/hyades/Hyades 数据格式说明.doc (64000 B)

<!-- 提取说明: Word97 OLE 分片表解码（CP936/UTF-16LE 逐片）：段落 238，字符 14995 -->

> Hyades 数据格式说明
> 简介
> Hyades是一款1D辐射流体力学程序，自带了大量的状态方程和不透明度数据。Multi1D++开发了使用这些数据的功能，程序根据数据文件路径和文件名中的hyades关键字来识别并调用相关的函数来读取数据文件。
> 相关数据在matter++/hyades中，并按照原程序的结构保存了目录和目录下的所有数据文件。
> 下面内容部分根据Hyades User’s Manual编写。
> Ref:
> [1] 1994JQSRT51(J.Larsen)_[HYADES]A plasma hydrodynamics code for dense plasma studies
> [2] Hyades User’s Manual, Cascade Applied Sciences, Inc.
> [3] Hyades Physics Manual, Cascade Applied Sciences, Inc.
> 数据库数据列表
> 相关数据在matter++/hyades中，并按照原程序的结构保存了目录和目录下的所有数据文件。
> 文件或文件夹	说明		Ionpot.dat	离化势文件		Coldopac.dat	冷不透明度（多群在线计算不透明度时低温数据不可靠，使用设定的室温不透明度）		Eoslib.lbf		EOS数据库		Opaclib.lbf	不透明度数据库		Tfdat.lbf	QEOS模型的Thomas-Fermi数据库，根据压缩原子的spherical-cell模型的热稠密等离子体Thomas-Fermi理论计算得到电子EOS属性。		Opacity/	不透明度数据库（都是单群）		Qeos/	EOS数据库，QEOS		Sesame/	EOS数据库, SESAME
> 数据库中的材料
> 摘录自HYADES程序说明文档的附录：
> Appendix I - HYADES Equation of State Library
> CAS has assembled a library of equation of states from a variety of sources.  In the following lists, more than one entry for a material may be encountered.  In this case, the different tables may have come from different sources, be built for different temperature-density regimes, or be derived from different theoretical models.  The user is referred to the original source of the table which may be found on the first line of the ASCII data file.
> 揝ingle fluid� EOS pressure and energy tables have material numbers 1 < num < 998, while Rosseland mean and Planck mean opacity tables have numbers 1000 < num < 2000. Two-temperature (搕wo-fluid�) EOS pressure and energy tables may be specified in a material region.  Electron tables have numbers 2000 < num < 3000, and ion tables have numbers 3000 < num < 4000.  Both tables must be specified.
> In the following lists：
> “Zbar” is the average atomic weight of the material,
> “Abar” is its average atomic number, and
> 揜ho0� is its solid or reference density. (g/cm3)
> Pressure/Energy tables
> Preferred tables are indicated by an �*�.
> Two-temperature materials available are indicated by an �#�.
> EOS No..        Material           Zbar         Abar        Rho0
>     11        Deuterium+tritium  1.000       2.515       0.2205
>     21        Glass         10.00       20.028     2.65
> 22        Quartz       10.00       20.028     2.204
> 23        Quartz       10.00       20.028     2.204
>     24        Silica         10.00       20.028     2.65
>     31        Polyethylene          2.667       4.676       0.9540
>     32        Polystyrene            3.500       6.510       1.044      #
>     33        Polyurethane         3.763       7.038       1.265
>     34        Lucite        3.600       6.674       1.186
>     35        Parylene     5.500       10.815     1.42
> 36        Mylar        4.545       8.735       1.38
> 37        PolyVinyl Alcohol  3.645       6.782       1.264
>     41        Aluminum    13.00       26.982     2.7568
>     42        Aluminum    13.00       26.982     2.7
>     43        Aluminum    13.00       26.982     2.7          #
>     44        Aluminum    13.00       26.982     2.7      *  #
>     51        Gold          79.00       196.97     19.3        #
>     52        Gold          79.00       196.97     19.3
>     61        Hydrogen    1.000       1.008       0.0884
> 71        Lithium      3.000       6.939       0.5326
> 81        Beryllium    4.000       9.012       1.845
> 91        Argon        18.00       39.948     1.4
> 92        Argon        18.00       39.948     1.4
> 101       Neon         10.00       20.183     1.44
> 111       Copper      29.00       63.540     8.93
> 112       Copper      29.00       63.540     8.93
> 113       Copper      29.00       63.540     8.93
> 114       Copper      29.00       63.540     8.93
> 115       Copper      29.00       63.540     8.938   * #
> 121       Tungsten    74.00       183.85     19.237    #
> 131       Uranium     92.00       238.03     18.983
>    141       Tungsten carbide   38.75       94.191     14.970
>    151       Deuterium    1.000       2.014       0.1766
>    161       Aluminum oxide    10.00       20.392     3.97
>    162       Aluminum oxide    10.00       20.392     3.97
>    171       CD 2               2.667       5.347       1.0475
>    181       Iron           26.00       55.850     7.85
>    191       Helium      2.000       4.003       0.4
>    201       Krypton     36.00       83.800     2.5005
>    211       6 LiD          2.000       4.000       0.802
>    212       6 LiD          2.000       4.0145     0.792
>    213       LiD            2.000       4.4775     0.883
>    221       Oxygen      8.000       16.000     1.2620
>    231       Lead          82.00       207.19     11.34
>    241       LiH            2.000       4.000       0.775
>    251       Nitrogen     7.000       14.007     0.8572
>    261       Platinum    78.00       195.09     21.419
>    271       Tantalum    73.00       180.95     16.654
>    281       Molybdenum         42.00       95.940     10.2
>    291       Nickel       28.00       58.710     8.882
>    301       Dry-air      7.373       14.803     0.00129
>    311       Water        3.333       6.005       0.9982
>    312       Water        3.333       6.005       0.9998
>    313       Water        3.333       6.005       0.9982
>    314       Water        3.333       6.005       0.9982   *
>    321       Teflon       8.000       16.669     2.1520
>    331       High Explosive      5.626       11.04       1.840
>    332       PBX-9502    5.598       10.98       1.894
>    341       Diamond    6.000       12.011     3.51
>    342       Carbon, liquid       6.000       12.011     3.688
>    343       Carbon, Phenolic   4.648       9.010       1.4503
>    344       Carbon      6.000       12.012     2.25
>    362       Stainless Steel       25.80       55.368     7.91
>    371       Xenon       54.00       131.3       3.0551
>    381       Selenium    34.00       78.96       4.8
>    391       Silicon       14.00       28.08       2.42
>    392       Silicon       14.00       28.08       2.42
>    401       Tin             50.00       118.7       7.29        #
>    402       Tin             50.00       118.7       7.29
>    411       Germanium           32.00       72.60       5.36
>    422       Titanium    22.00       47.90       4.54
>    431       C8H7Br     5.625       11.441     1.53
>    441       BeO           6.000       12.505     3.008
>    451       Magnesium            12.00       24.305     1.740
>    461       Europium    63.00       151.96     5.253
>    466       Neodymium           60.00       144.24     6.95
>    471       Gadolinium           64.00       157.25     7.898
>    481       Calcium      20.00       40.000    1.550
>    491       Silver         47.00       107.87     10.50     #
>    501       Epoxy        3.241       5.9134     1.185
>    502       Epoxy        3.2407     5.9134     1.185
>    511       Boron Carbide       5.200       10.416     2.45
>    521       Vanadium    23.00       50.942     6.11
>    531       Zinc           30.00       65.37       7.139
>  #Two-temperature materials available：数据表格数据与单温个数一致。
> Rosseland/Planck mean opacity tables:
>  Opacity No..   Material      Zbar         Abar
>       1022   Quartz       10.00       20.028
>       1031   Polyethylene          2.667       4.676
>       1032   Polystyrene            3.500       6.510
>       1033   Polyurethane         3.763       7.038
>       1035   Parylene     5.500       10.815
>       1036   Mylar        4.545       8.735
>       1041   Aluminum    13.00       26.982
>       1051 *  Gold          79.00       196.97
>       1052 *  Gold          79.00       196.97
>       1061   Hydrogen    1.000       1.008
>       1071   Lithium      3.000       6.939
>       1081   Beryllium    4.000       9.012
>       1091   Argon        18.00       39.948
>       1101   Neon         10.00       20.183
>       1111   Copper      29.00       63.540
>       1121 *  Tungsten    74.00       183.85
>       1151   Deuterium    1.000       2.014
>       1161   Alumina     10.00       20.392
>       1181   Iron           26.00       55.850
>       1191   Helium      2.000       4.003
>       1201   Krypton     36.00       83.800
>       1221   Oxygen      8.000       16.000
>       1251   Nitrogen     7.000       14.007
>       1281   Molybdenum         42.00       95.940
>       1291   Nickel       28.00       58.710
>       1301   Dry-air      7.373       14.803
>       1311   Water        3.333       6.005
>       1344   Carbon      6.000       12.000
>       1371   Xenon       54.00       131.30
>       1391   Silicon       14.00       28.090
>       1401   Tin             50.00       118.69
>       1422   Titanium    22.00       47.90
>       1451   Magnesium            12.00       24.32
>       1461   Europium    63.00       151.96
>       1481   Calcium     20.00       40.00
>       1491   Silver         47.00       107.68
> *   Rosseland mean tables only 本来应该存储Planck平均不透明度的位置用0代替。
> EOS ASCII数据格式(Appendix III - Equation of State ASCII Material File Format)
> （二进制EOS数据格式见Appendix II - Equation of State Binary Library File Format，因Multi1D++不支持，所以在此没有列出）
>  The binary EOS library file is formed (using the HYADLIBM program) from individual material files.  Each of these material files is in an ASCII format.  The first line of each material file contains a common material name and historical information about where the data came from.  The second line begins the actual data and consists of the HYADES EOS number, the average atomic number (ZBAR), average atomic weight (ABAR), normal density (DEN), and length of the data array, which follows.  The format for this line is:  1x,i5,4x,1p3e15.8,3x,i5.  The third and subsequent lines contain the EOS information:  the number of density points (NR), the number of temperature points (NT), an array of density points (NR long), an array of temperature points (NT long), followed by a matrix of pressures (NR*NT long), followed by a matrix of energies (NR*NT long).  The format for this data is  1p5e15.8.
> NOTE:  This format is quite similar to that of the Los Alamos Sesame library.  Also, the units used here differ from that in the Sesame tables.
> 单位：密度 g/cm3; 温度 keV; 压强 dyne/cm2;比内能 erg/g
> 其中
> 例：eos_2051.dat
> GOLD        LANL SESAME #2700-304 DATED: 81678 101582
>   2051     7.90000000E+01 1.96967000E+02 1.93000000E+01    4772
>  1.01000000E+02 2.30000000E+01 0.00000000E+00 1.50781250E-01 2.87685800E-01
>  4.24600000E-01 8.15425000E-01 1.20625000E+00 1.99433269E+00 2.78242310E+00
>  3.57050000E+00 5.21100000E+00 6.75500000E+00 8.20250000E+00 9.65000000E+00	材料名和生成的历史信息
> HYADES EOS编号，Zbar, Abar, Rho, 数组长度
> NR, NT, RHO(1~NR), T(1~NT), P(1~NR*1, NR+1~NR*2, ...NR*NT), E(1~NR*NT)
> 数组长度 = 2 + NR + NT + 2*NR*NT		例：qeos_115.dat
> COPPER      LLNL-QEOS Dated: 082802
>    115     2.90000000E+01 6.35400000E+01 8.93800000E+00   23774
>  1.28000000E+02 9.20000000E+01 1.00000000E-10 1.77827941E-10 3.16227766E-10
>  5.62341325E-10 1.00000000E-09 1.77827941E-09 3.16227766E-09 5.62341325E-09
>  1.00000000E-08 1.77827941E-08 3.16227766E-08 5.62341325E-08 1.00000000E-07
>  1.77827941E-07 3.16227766E-07 5.62341325E-07 1.00000000E-06 1.25892541E-06	材料名和生成的历史信息
> HYADES EOS编号，Zbar, Abar, Rho, 数组长度
> NR, NT, RHO(1~NR), T(1~NT), P(1~NR*NT), E(1~NR*NT)
> 数组长度 = 2 + NR + NT + 2*NR*NT		状态方程材料编号<998;使用双温表格时，电子流编号 2001-2999，离子流编号3001-3999
> 不透明度数据格式
> 不透明度参数使用同样的格式，压强处为平均Rosseland值，比内能处为平均Planck值，单位cm2/g：
> 例：opc_1151.dat
> DEUTERIUM   LANL SESAME #15264 DATED:  21793  21793
>   1151     1.00000000E+00 2.01600000E+00 1.76600000E-01    2931
>  3.10000000E+01 4.60000000E+01 1.00000000E-06 2.15443467E-06 4.64158887E-06
>  1.00000000E-05 2.15443467E-05 4.64158887E-05 1.00000000E-04 2.15443467E-04
>  4.64158887E-04 1.00000000E-03 2.15443467E-03 4.64158887E-03 1.00000000E-02
>  2.15443467E-02 4.64158887E-02 1.00000000E-01 2.15443469E-01 4.64158884E-01
>  1.00000000E+00 2.15443469E+00 4.64158884E+00 1.00000000E+01 2.15443467E+01	材料名和生成的历史信息
> HYADES EOS编号，Zbar, Abar, Rho, 数组长度
> NR, NT, RHO(1~NR), T(1~NT),  [图片] (1~NR*NT),  [图片] (1~NR*NT)
> 数组长度 = 2 + NR + NT + 2*NR*NT		灰度不透明度模型编号1001-1999
> 外部不透明度数据格式
> 用户可以提供多群不透明度用于HYADES计算，附录VI提供了相关数据表格文件的格式说明：
> Appendix VI - External Opacity Table File Format
> Provision has been made for an externally generated multi-group opacity table to be used in one material region.  The group structure of this table can be constructed in a fairly arbitrary manner, since the code will map the external structure into the internal one.
> The format for the external ASCII table is free format, 80 column width.  Continuation lines are allowed for each block containing arrays:
> Block No. Contents
>       1        character string header
>       2        number of temperatures, number of densities
>       3        array of temperatures (keV) N t  ; maximum number of temperatures is 200
>       4        array of densities (gm/cm 3 )  N r  ; maximum number of densities is 200
>       5        number of photon groups (keV), NGPS 1 , for temperature #1; maximum number of photon groups is 500
>       6        array of group boundaries for temperature #1 - there will be NGPS 1 +1 entries
>       7        array of opacities (cm 2 /gm) for temperature #1, density #1 – NGPS 1 +1 entries
>       8        array of opacities for temperature #1, density #2 - NGPS 1 +1 entries etc. for all densities
>   N r +7      number of photon groups (keV), NGPS 2 , for temperature #2
>   N r +8      array of group boundaries for temperature #2 - there will be NGPS 2 +1 entries
>   N r +9      array of opacities for temperature #2, density #1 - NGPS 2  entries
>   N r +10    array of opacities for temperature #2, density #2 - NGPS 2  entries
>   etc. for all N r  densities
> etc. for all N t  temperatures.
> An example of an external opacity table might be:
> External opacities for aluminum
> 6  15
> 1.00000E-02 3.00000E-02 1.00000E-01 3.00000E-01 1.00000E+00 3.00000E+00
> 2.70000E-06  8.54000E-06  2.70000E-05  8.54000E-05  2.70000E-04
> 8.54000E-04  2.70000E-03  8.54000E-03  2.70000E-02  8.54000E-02
> 2.70000E-01  8.54000E-01  2.70000E+00  8.54000E+00  2.70000E+01
> 85
> 1.00000E-06  2.00000E-03  2.23770E-03  2.50366E-03  2.80123E-03
> 3.13416E-03  3.50666E-03  3.92343E-03  4.38974E-03  4.91147E-03
> 5.49521E-03  6.14833E-03  6.87908E-03  7.69667E-03  8.61144E-03
> 其他数据文件
> Ionpot.dat
> 离化势要用于计算HYADES模拟的产生和再启动phase。文件中有各个电子被剥离的离化势。
> Coldopac.dat
> 离化和原子物理模块在线生成的多群不透明度在低温下可能会产生错误的不透明度，因此提供了室温的分频不透明度数据（能点较少）。
> Multi1D++对Hyades数据的使用
> Inverted EOS
> 为了在Multi1D中使用Hyades的EOS数据，需要将Hyades的EOS数据进行Invert，将
> P(R, T)，E(R, T)转化为P(R,E), T(R,E)
> 对于P(R, E)
> 对某个密度R,
> 首先根据E(R, T)找到对应的温度T(R, E)，这个过程需要差值
> P(R, E) = P(R, T(R, E))，这里同样需要差值。
> EOS/Opacity Viewer中查看数据文件
> 在GUI4Multi1D中可以查看EOS和Opacity数据。可以选择查看InvertedEOS来获得压力和温度与能量、密度的关系；或者直接查看Hyades的数据（正表），获得压力和能量与温度密度的关系。
> Two-temperature materials available
> Preferred tables
> Two-temperature materials available
> *   Rosseland mean tables only
> *   Rosseland mean tables only
> *   Rosseland mean tables only

## doc/Atomic(LEDCOP)说明.doc (59904 B)

<!-- 提取说明: Word97 OLE 分片表解码（CP936/UTF-16LE 逐片）：段落 160，字符 20781 -->

> Table of available temperatures (in keV) for use in TOPS
>  [图片]
> ATOMIC-generated data (released in 2015)
>  5.000E-04 6.000E-04 8.000E-04 1.000E-03 1.250E-03 1.500E-03 2.000E-03
>  2.500E-03 3.000E-03 3.500E-03 4.000E-03 5.000E-03 6.000E-03 7.000E-03
>  8.000E-03 9.000E-03 1.000E-02 1.250E-02 1.500E-02 2.000E-02 2.500E-02
>  3.000E-02 4.000E-02 5.000E-02 6.000E-02 7.000E-02 8.000E-02 9.000E-02
>  1.000E-01 1.250E-01 1.500E-01 1.750E-01 2.000E-01 2.250E-01 2.500E-01
>  2.750E-01 3.000E-01 3.500E-01 4.000E-01 4.500E-01 5.000E-01 5.500E-01
>  6.000E-01 6.500E-01 7.000E-01 8.000E-01 9.000E-01 1.000E+00 1.125E+00
>  1.250E+00 1.375E+00 1.500E+00 1.625E+00 1.750E+00 1.875E+00 2.000E+00
>  2.125E+00 2.250E+00 2.375E+00 2.500E+00 2.625E+00 2.750E+00 3.000E+00
>  3.500E+00 4.000E+00 5.000E+00 6.000E+00 8.000E+00 1.000E+01 1.500E+01
>  2.500E+01 4.000E+01 6.000E+01 1.000E+02
> Temperatures added in 2015 are marked bold.
>  [图片]
> LEDCOP-generated data (released in 2000)
>  5.000E-04 6.000E-04 8.000E-04 1.000E-03 1.250E-03 1.500E-03 2.000E-03
>  2.500E-03 3.000E-03 3.500E-03 4.000E-03 5.000E-03 6.000E-03 8.000E-03
>  1.000E-02 1.250E-02 1.500E-02 2.000E-02 2.500E-02 3.000E-02 4.000E-02
>  5.000E-02 6.000E-02 8.000E-02 1.000E-01 1.250E-01 1.500E-01 2.000E-01
>  2.500E-01 3.000E-01 4.000E-01 5.000E-01 6.000E-01 8.000E-01 1.000E+00
>  1.250E+00 1.500E+00 2.000E+00 2.500E+00 3.000E+00 4.000E+00 5.000E+00
>  6.000E+00 8.000E+00 1.000E+01 1.500E+01 2.500E+01 4.000E+01 6.000E+01
>  1.000E+02
> Frequency Dependent Opacity Spectrum Limitations
>  [图片]
> The opacity calculations are intended primarily for users interested in integrated opacities. The "gray" opacities (Rosseland or Planck) are obtained by integrating over all photon energies while the "multigroup" opacities are integrated between the energy boundaries, giving one opacity number for each energy range. This range is assumed to be large compared with individual line profile widths. Under these assumptions, several approximations are made in the calculations that will reduce spectroscopic accuracy.
> 1.Most of the atomic energy levels used in the opacity code are obtained from single configuration LS Hartree-Fock calculations, with relativistic corrections. These energy levels are then fit with a quantum defect model in order to reduce this massive data base to a managable set. This can result in errors of 1% or more, especially for inner shell transitions. Errors of this magnitude have little effect on the integrated opacity, but are large in terms of spectroscopic accuracy.
> 2. For the higher Z elements, even the reduced LS coupled data base becomes too large. Switching to jj coupling, which is usually the preferred model for these elements, would require even more data. For this reason, the opacity code uses an Unresolved Transition Array (UTA) model for many bound-bound transitions calculations. This model replaces the actual transition array with a single Gaussian profile to approximate all of the actual lines (which can number in the millions). This overestimates the opacity for low densities, so a Random Line model is used to replace the single Gaussian with a relatively small set of randomly generated, plasma broadened lines that distribute the total oscillator strength over the same energy interval as the original transition array. For obvious reasons, none of these random lines can be matched spectroscopically, but looking at a broad enough energy range, this model will preserve the oscillator strength within the correct photon energy range.
> 3. The individual element opacities are all calculated at the same u (u = hv/kT) grid for all temperatures and densities. This allows the elements to be mixed together to form opacities for multi-element materials. Since this is a fixed grid, the contributions from the different processes (such as bound-bound transitions) are calculated and summed only at the grid points and no effort is made to preserve the line centers. Therefore, line ratios could be reversed from their normal ratio by the choice of grid points. In addition to this, since the u's are constant, each temperature samples the opacity cross sections at different photon energies. If the lines are broad enough, this makes little difference, but the narrow line distribution could look entirely different at two adjoining temperatures.
> All attempts are made to insure the most accurate possible opacity calculations, but because of the above inherent limitations, use of the frequency dependent opacities to match spectra is discouraged.
> Frequently asked questions for the TOPS Web Page
>  [图片]
> Q1: I noticed that some of the multigroup opacities were all 1010 . Why did this happen?
> A: The TOPS code calculates the plasma cutoff frequency for each temperature-density point. Any group that lies either partly or fully below that frequency has the opacity set to 1010 to indicate that photons at those frequencies cannot propagate in the plasma.
>  [图片]
> Q2: I want a table of opacities at 21.8 eV. When I enter this number, the Web Page gives me an error message. Why can I not get the 21.8 eV temperature?
> A: The TOPS code can only use tabulated temperature points for cross section data. It will not interpolate on temperature. If you choose a temperature that is not on the tabulated grid, the Web Page will compare it to the master list and reject it if it does not agree with one of the table values to within 1 percent. The set of tabulated temperatures is listed under tabulated temperatures.NOTE: The TOPS code will interpolate in density.
>  [图片]
> Q3: I entered a temperature of .0005 keV (which is on the allowed temperature list) for carbon and did not get any results back. Why can't I get any data for this temperature?
> A: The materials in this data base were calculated over several years and the temperature-density limits were changed during the course of the calculations. Most elements go down to .0005 keV, but the elements from lithium to magnesium only go down to .001 keV. These should be replaced in the next few months and the limitations shown in the tabulated temperatures list will be removed.
>  [图片]
> Q4: I asked for multigroup opacities for a density of 100 gm/cc for aluminum at a temperature of .001 keV. Every multigroup had the same opacity in it. Why doesn't it vary with photon energy?
> A: When you ask for a temperature-density point, TOPS attempts to find cross section data for that point. At low temperatures there is no data available for high densities. Thus the TOPS code uses the cross sections for the highest density available, prints a warning message that this has occurred and uses the gray opacity from those cross sections for all the multigroup and frequency dependent opacities.
>  [图片]
> Q5: When I specify multigroup opacity, it returns tables containing Rosseland Mean and Planck Mean opacity. But I want to obtain opacity as function of energy (not the averaged opacity). Is there a way I can do this?
> A: When you ask for multigroup opacities, you get the Rosseland and Planck mean as well as the multigroup opacities. When you are looking at the the tabular output, the gray opacities appear in the output first. You may need to scroll down in the window to get to the section of the table that contains the multigroup opacities. Of course, you must have checked the button requesting multigroup opacities on the initial input page, as well as set up the group boundary energies. It is also possible to obtain the frequency dependent opacities for a limited number of temperature-density points. The frequency dependent data is tabulated on a grid of either 3000 or 3900 points depending on whether the old or new version of the data is used. The default is to use the new version where available. Because of the large number of points, we limit the requests to only six temperature-density points ie. you could choose two temperature and three density points for a total of six points, or one temperature with six densities etc. In the output file, the frequency dependent data is listed after the gray opacities, or after the multigroup opacities (if requested).
>  [图片]
> Q6: What is meant by "No. Free" in your tables ?
> A: For a single element, the free electron number is the average number of free electrons per ion. It is obtained by multiplying the relative population of each ion stage by the number of free electrons for that stage, zero for the neutral, one for single ionized etc. For a mixture, it is a weighted average using the number fractions of each constituent of the mixture.
>  [图片]
> Q7: What is your meant by "Av Sq Free" in the output?
> A: This is the average of the square of the number of free electrons over the ion stages of an element. It is obtained by summing the product of the relative abundance of each ion stage times the square of the number of free electrons for that ion stage, zero for neutral etc. For a mixture, it is a weigthed average over all constituents of the mixture.
>  [图片]
> Q8: I can't seem to find opacities for densities lower than 10-12 gm/cc.
> A: All of the opacity data is generated assuming Local Thermodynamic Equilibrium (LTE) and this becomes very questionable below 10-6 to 10-7 gm/cc. At lower densities, one should use a nonLTE coronal model. Since the data on this web site assumes LTE, they do not go to such low densities.
>  [图片]
> Q9: When I display a GIF plot or a data table for the second time, all that I get is the first plot or table over and over again.
> A: The Web Page displays a file when showing plots or tables and uses the same file name for each new data set. Many browsers store the file name and data in their cache memeory and if you request a second plot or table, the browser retrieves it from the cache memeory instead of displaying the new data. You must change your browser's cache preference settings from "once a session" to "every time" to force the browser to choose the new data file for each new plot or table. Clicking the Reload button on your browser will also give you the latest plot or table, but you will have to do that every time if you do not reset the brower preference.
>  [图片]
> Q10: When I plot the Rosseland gray opacities, all of the high density curves seem to run together into one curve. Why is this?
> A: The opacity code is unable to calculate the opacities for the low temperature-high density grid points, but needs to have a non-zero value for these grid points. The TOPS code takes the value for the highest calculated density for each temperature and used that value for all of the higher densities. This makes the curves run together.
>  [图片]
> Q11: I calculated a SESAME table for the same material that I had in the SESAME library that I received from you and the numbers are not quite the same. Why is that?
> A: The normal SESAME library is calculated on the CRAY computers, using a slightly different interpolation scheme than on the Sun that runs this Web Page. This can cause small numerical differences. In addition, the boundary region (between calculated points and extrapolated points) is handled quite differently for the two SESAME files. The normal library file is done iteratively (with some points being removed) while the Web Page has to use an automatic fail proof method. Finally the extrapolated points are completely different (see the SESAME Format writeup), but these points should never be used in calculations.
>  [图片]
> Q12: When I display a postscript plot with Ghostview, I have trouble reading the Legends on the plot or I can not get the landscape mode to display horizontally. What should I do?
> A: We have tried Ghostview on different platforms and have found that it operates quite differently on the different platforms. The Macintosh version seems the most limited. All that we can suggest is that you play with the settings and/or preferences until you have the best possible display. The other option is to switch to the GIF format.
>  [图片]
> Q13: I plan to use some of your opacities in a publication. What is the best reference to cite?
> A: You can click on the Opacities methods and references for a list of refernces. The latest reference is
> N. H. Magee, Jr., J. Abdallah, Jr., R. E. H. Clark, et al., "Atomic Structure Calculations and New Los Alamos Astrophysical Opacities", Astronomical Society of the Pacific Conference Series (Astrophysical Applications of Powerful New Databases, S. J. Adelman and W. L. Wiese eds.) 78, 51 (1995).
> You may also refer to the web page:
> http://aphysics2.lanl.gov/cgi-bin/opacrun/tops.pl
>  [图片]
> Please mail questions or comments to:
> LANL T-1 Opacities <opacity@lanl.gov>
> References for the TOPS code
>  [图片]
> N. H. Magee, Jr., J. Abdallah, Jr., R. E. H. Clark, et al., "Atomic Structure Calculations and New Los Alamos Astrophysical Opacities", Astronomical Society of the Pacific Conference Series (Astrophysical Applications of Powerful New Databases, S. J. Adelman and W. L. Wiese eds.) 78, 51 (1995).
>  [图片]
> TOPS: A Multigroup Opacity Code; Los Alamos Report LA-10454, by Joseph Abdallah, Jr. and Robert E. H. Clark.
>  [图片]
> Astrophysical Opacity Library; Los Alamos Report LA-6760-M, by W. F. Huebner, A. L. Merts, N. H. Magee, Jr., M. F. Argo
>  [图片]
> The Los Alamos LEDCOP code; Los Alamos Report LA-UR-97-1038, by N.H. Magee, A.L. Merts, J.J. Keady and D.P. Kilcrease
>  [图片]
> Please mail questions or comments to:
> LANL T-1 Opacities <opacity@lanl.gov>
> Photon Energy Grid
>  [图片]
> u Grid Definition
> The elemental opacities are calculated on a uniform grid of temperatures, electron degeneracy paramaters and dimensionless photon energies u, where u is defined as:u = hv / kT hv is the photon energy in eV and kT is the temperature in eV. The u grid is selected instead of the photon energy grid because the same u grid can be used for all temperatures and cover the important photon energy ranges needed to integrate the Rosseland and Planck "gray" opacities. These photon energy ranges would be 0. - 20. eV for a temperature of 1. eV and 0. - 2000. eV for a 100. eV temperature. For the u grid, the range would be 0. - 20. for both temperatures.
> u Grid used on the Web Page
> The opacities are calculated on a grid of 14,900 u points for each temperature point. This grid is shown below:
>   u Values      14,900 Point Grid
>  _________  ___________________________
>       0.0
>        |
>        |    9600 points, steps of .00125
>        |
>      12.5
>        |
>        |    1600 points, steps of .005
>        |
>      20.0
>        |
>        |    1000 points, steps of .01
>        |
>      30.0
>        |
>        |     700 points, steps of .1
>        |
>     100.0
>        |
>        |     900 points, steps of 1.0
>        |
>    1000.0
>        |
>        |     900 points, steps of 10.0
>        |
>   10000.0
>        |
>        |     200 points, steps of 100.0
>        |
>   30000.0
>            _____
>            14900 points
>  [图片]
> Help file for the TOPS code
>  [图片]
> Your first choice as a user is the type of data file to use. There are two types of data files: ATOMIC and LEDCOP. The ATOMIC files are the latest data files produced by the LANL opacity team (groups T-1 and XCP-5) and are the preferred files.
> See file of currently available materials for the current list of available materials. The material ID numbers are prefixed by the letter n. The LEDCOP files are older cross section files and are included for the sake of continuity.
> The default is to use the most recent available data file for each element.
>  [图片]
> As a user you may choose to mix an arbitrary number of elements. You have the option of specifying the mixture by number fraction or by mass. You may also choose to specify particular isotopic weights in the mixture.
> The default is to specify mixtures by number fraction and use the naturally occurring isotopic weights.
>  [图片]
> You have several options for temperatures. You may select individual temperature, choose a subset of the tabulated temperatures, or thin the tabulated temperatures. In any case, the selected set of temperatures must be elements of the default temperature grid.
> The default is to use temperatures in the range of 0.1 to 10 keV.
>  [图片]
> In a similar manner you can select the density grid. In contrast to the temperature grid, there is no default density grid. You are free to select specific densities, or choose a grid with either logarithmic or linear spacing.
> One should exercise some restraint in choosing the total number of temperature and density points, especially for mixtures containing a large number of elements. The run times can become quite long. The Web Page will give you an time estimate on the Output Selection page after you submit your calculation from the first input page. If the time estimate is too long, the Web Page will refuse the calculation.
> One point to be noted is that the range of densities for which cross sections are tabulated varies with temperature. At low temperatures there is a relatively low upper bound on density. This causes the TOPS code to attempt to find opacities for which cross section data do not exist. If this happens, the TOPS code prints a warning message on both the columnar table output and on all graphs except the 3-D graphs. It then uses the cross sections for the highest density point for that temperature to calculate the gray opacities. If multigroup opacities are requested, that gray opacity is put into each multigroup spot so that there is no variation of opacity with photon energy. This should point out that the displayed multigroup opacity does not represent a true multigroup calculation for this point. The frequency dependent data is handled the same way as the multigroups.
>  [图片]
> If you wish to have multigroup opacities, you may select photon group boundaries in keV in a manner similar to the selection of the density grid. The default is to use a logarithmic spacing of 33 boundaries (32 groups) with energies between .001 and 300. keV.
> Just as there is a pratical limit to the product of number of temperatures times number of densities, there is a limit on the product of number of temperatures times number of densities times number of group boundaries. Currently this product is limited to 50000. Thus if you choose the default temperature grid with 50 temperatures and a density grid with 20 densities, you can still have 50 photon groups.
>  [图片]
> If you choose to look at frequency dependent opacities, the TOPS code will automatically output all of the available data for each temperature- density point. At present, this is 3000 or 3900 frequency points for each case. You may restrict the frequency range on the various graphics pages if you do not want to download the entire table.
>  [图片]
> The TOPS code calculates the plasma cutoff frequency, the frequency below which photons may not propagate in a plasma. Any group which lies partly or fully below this frequency has the opacity in that group set to 1010. Normally this cutoff frequency is very low relative to the temperature and should not make any difference in a radiation transport calculation.
>  [图片]
> The default mode when you press the submit button is to calculate gray Rosseland and Planck opacities along with the average number of free electrons. You also have the option of requesting multigroup and/or frequency dependent opacities. If you choose the frequency dependent option, you are limited to 6 temperature-density points per calculation. Resulting tables can be saved to your local machine with the FILE button on your web browser.
>  [图片]
> The normal columnar TOPS tables first list any warning messages. Then the temperature, density and (if requested) multigroup photon energy grids. boundaries. After this, the gray Rosseland and Planck opacities are shown. If you requested multigroup opacities, these are listed next. Finally, the frequency dependent opacities are listed if this calculation was requested.
> Special note to SESAME users. This Web Page is now setup to output the special SESAME format ASCII files for opacities. Users must have already obtained the SESAME codes from T-1 at LANL before they can use these tables. See the SESAME writeup for more details about the tables produced by this Web Page.
>  [图片]
> Please mail questions or comments to:
> LANL T-1 Opacities <opacity@lanl.gov>

## doc/Restart.doc (61952 B)

<!-- 提取说明: Word97 OLE 分片表解码（CP936/UTF-16LE 逐片）：段落 61，字符 2371 -->

> [Restart]从中断处重新开始计算
> MULTI7.6提供了读取proifle文件的功能，但是初始化文件不包括辐射温度等信息，因此功能有所限制。即使包含了辐射温度，多群辐射的定义也将使得初始化复杂化。
> 另外一维模拟计算耗时不多，从中断处开始计算的必要性值得讨论。
> MULTI7.6的原生功能
> MULTI7.6提供了读取初始位置、速度、密度、材料ID和电子离子温度的初始化方法，根据这几个量，定义本来需要用&LAYERS定义的内容。
> 缺点是这几个量对重新开始中断的计算远远不够。其他量如辐射温度、聚变相关量等都对继续计算有影响。
> Multi1D++可以输出最后时刻位置和温度、密度参数到*.final.dat中，同时记录了结束的时刻。Restart功能基于此文件和若干设置继续计算。
>  [图片]
> 图 3 *.final.dat数据格式，各列与profile的定义对应（即x, v, MID, rho, te, ti, cmc）。
> 各列的意义：网格节点位置x(cm), 网格节点速度v(cm/s), 材料编号MID, 密度rho(g/cc), 电子温度te(eV), 离子温度ti(eV), 网格质量坐标cmc(g)
> Multi1D++的Restart功能
> 命令行操作
> Multi1D++.exe --Input Untitled.case --ASCII --Restart --TimeExit 3E-09 --AppendOutput [--RestartFrom Untitled.final.dat]
> 上面的命令中：
> --Restart激活了重新计算功能；
> --TimeExit设置了退出时刻（TimeExit），确保这个量比Untitled.case中定义的退出时间要更长；
> --AppendOutput用于设置是否在原来的输出文件中续写结果；
> 方括号中的--RestartFrom定义了从哪个文件开始重复计算。如果文件名与case名一致，则可以不写这个选项。
> 图形界面操作
> 在主界面Run按钮上点击右键，弹出菜单中选择Restart.然后在图形界面中设置再计算的终结时间，选择是否在原有的Output上续写计算结果，否则就会替换掉原来的数据结果。
>  [图片]
> Restart功能的使用
> 算例1：与IRAD3D的互动
> 采用Restart功能与IRAD3D进行互动的方案要求Multi1D++启动后读入上次计算的结果（*.final.dat）并继续根据IRAD3D计算出的新的辐射温度开始新的计算。
> 思路如下：
> 1) 根据*.case文件初始化
> 2) 根据*.final.dat文件中的数据设置默认的等离子体状态
> 3) 命令行要传递计算的起始时间记录在*.final.dat的第一行(如：Time=1e-9)
> 4) 通过命令行指定新的计算终止时间 Multi1D++.exe –ASCII –Input Untitled.case --Restart --TimeExit 1e-9
> 5) 程序开始计算直到给定的计算终止时间，然后再输出新的*.final.dat
> 6) 程序关闭
> 本方案需要有初始化的*.case，上一次计算的*.final.dat文件，上一次计算结束的时间作为本次计算的起始时间。
> 算例2：CH膜烧穿信号匹配
> 实验测量充气腔阻气膜后的温度曲线，据此计算膜前烧蚀的辐射温度曲线。
> ！目前无法实现自动化，需要手动修改每次的参数（或者编写脚本来实现）。
> 计算初始算例到第一个时间点t1.case
> 如果改时间点的温度不匹配则手动调整T1.case中的辐射边界条件，然后重新计算。
> 如果匹配（差距满足要求），则另存为t2.case。
> 计算第n个时间点
> tn.case以tn-1.final.dat为初始时刻重新计算到第n时间步，如果温度不匹配则修改tn-1.case重新计算。
> 如此反复。
> 相比之前的计算，只节省了每次重新计算0到n时间步的时间，如果计算耗时不多，此方法优势不大。
> 算例3：混合模型修改温度密度后再计算
> 计算到某一时刻后，由混合模型修改材料温度密度值之后再继续计算，可以判断混合对计算结果的影响。
> 先计算默认算例，如计算到2e-9s：
> Multi1D++.exe –ASCII –Input Untitled.case
> 改写这个算例的*final.dat中的内容，可以用Matlab等脚本快速实现。
> 再继续计算，以得到修改内容后的计算结果，到3e-9s
> Multi1D++.exe --Input Untitled.case --ASCII --Restart --TimeExit 3E-09 --AppendOutput
> 与Matlab结合实现与实验结果的拟合
> 逐个时间点调整可以结合Matlab脚本实现自动化。
> 将Multi1D++的计算封装为一个函数，将匹配误差作为输出，采用Matlab的优化方法如fmincon来最小化匹配误差。
>  更全面的功能
> 下面简单讨论这个功能比较全面的实现方法
> 比较全面的功能是从上次计算的多个数据文件中读取最后一个时刻的所有参数，对材料进行初始化，而不仅仅是原生功能中的位置、速度、密度、材料ID和电子离子温度这几个量。
> [TODO]导入所有计算数据到内存中
> MULTI中有将数据保存到内存buffer中，是否可以将buffer整体输出？
> [TODO]包含Fusion信息的restart
> 当模拟计算包含Fusion信息时，需要额外输入输出核燃料组分等信息。
> 当前Multi1D++支持的组分包括H/D/T/He3/Z
> 每次计算结束将燃料组分保存在*.fusion.final.dat中，供再启动时读取。

## C 组：FEOS 相关 PDF

## doc/FEOS/FEOS-Package-Documentation2012.pdf (978594 B)

<!-- 提取说明: 共 64 页（pdfminer 解析出 65 段） -->

### [FEOS-Package-Documentation2012.pdf] 第 1 页

> FEOS
> 
> A new equation-of-state code for hot dense matter
> 
> Package Documentation
> 
> Version: 12.9-beta (September 2012)
> 
> Steﬀen Faik
> Institute for Theoretical Physics
> Goethe University Frankfurt am Main, Germany
> 
> MPQeos Version 2.0 (09/99):
> 
> A.J. Kemp and J. Meyer-ter-Vehn
> Max-Planck Institute for Quantum Optics
> Garching, Germany

### [FEOS-Package-Documentation2012.pdf] 第 2 页

> Foreword / Contact
> 
> First of all I would like to thank Dr Anna Tauschwitz, Prof Dr Joachim
> Maruhn (both Goethe University Frankfurt am Main & GSI Darmstadt),
> Prof Dr Igor Iosilevskiy (Joint Institute for High Temperatures Moscow &
> GSI Darmstadt), and Prof Dr Mikhail Basko (Institute for Theoretical and
> Experimental Physics Moscow & GSI Darmstadt) for very helpful and con-
> structive discussions. The whole work was supported by the Extreme Mat-
> ter Institute EMMI and the Bundesministerium f¨ur Bildung und Forschung
> BMBF (Project 06FY9085).
> 
> This present new revised version of the original code MPQeos by A. Kemp
> [1] was built within the last four years, partially within the framework of
> my diploma thesis at the university of Frankfurt, Germany. For this reason,
> the new package is called ”Frankfurt equation-of-state (FEOS)”.
> It was
> mainly built for usage at GSI – Helmholtz Center for Heavy Ion Research in
> Darmstadt, but is already used by several institutions and working groups
> around the world.
> 
> At this point I want to emphasize that some parts of this documentation are
> based on the original documentation of MPQeos (version 2.0) by A. Kemp
> and J. Meyer-ter-Vehn. I updated these parts concerning the new features
> of FEOS. So, the reader does not have to read the original documentation of
> MPQeos in order to understand the new manual.
> 
> Address of the author of FEOS
> 
> Steﬀen Faik
> Goethe University Frankfurt am Main
> Institute for Theoretical Physics
> Max von Laue-Str. 1
> 60438 Frankfurt am Main
> 
> Room: 02.227
> Phone: +49 (0)69 798-47846
> Fax: +49 (0)69 798-47879
> faik@th.physik.uni-frankfurt.de
> http://th.physik.uni-frankfurt.de/˜faik/

### [FEOS-Package-Documentation2012.pdf] 第 3 页

> Contents
> 
> The FEOS Package
> 
> 1 Introduction / Overview
> 
> 1.1 Citation Rules . . . . . . . . . . . . . . . . . . . . . . . . . . .
> 
> 2 Package File Structure
> 
> 3 Installation
> 
> 4 Parameter & Database File Structure
> 
> 5 Package Standard Units
> 
> The FEOS Library
> 
> 6 The Physics behind the QEOS Model
> 
> 6
> 
> 6
> 
> 8
> 
> 8
> 
> 9
> 
> 10
> 
> 10
> 
> 11
> 
> 11
> 
> 6.1 General Facts . . . . . . . . . . . . . . . . . . . . . . . . . . . 11
> 
> 6.2 Electronic EOS: TF Model . . . . . . . . . . . . . . . . . . . . 12
> 
> 6.3 Semiempirical Bonding Correction . . . . . . . . . . . . . . . . 15
> 
> 6.4
> 
> Ionic EOS: Cowan Model . . . . . . . . . . . . . . . . . . . . . 16
> 
> 6.5 Homogeneous Mixtures of Elements . . . . . . . . . . . . . . . 19
> 
> 6.6 Liquid-Vapor Phase Coexistence . . . . . . . . . . . . . . . . . 20
> 
> 6.7 Cold Curve Improvement . . . . . . . . . . . . . . . . . . . . . 22
> 
> 7 Technical Design of the Library
> 
> 23
> 
> 7.1 Material Initialization Stage . . . . . . . . . . . . . . . . . . . 23
> 
> 3

### [FEOS-Package-Documentation2012.pdf] 第 4 页

> 8 Information provided by the Library
> 
> 9 Source Code Structure
> 
> 10 Material Parameter Database
> 
> 11 Implementation of the Library
> 
> 12 Interface Routines
> 
> 27
> 
> 27
> 
> 29
> 
> 29
> 
> 30
> 
> 12.1 Obligatory Interface Routines . . . . . . . . . . . . . . . . . . 31
> 
> 12.2 Facultative Interface Routines . . . . . . . . . . . . . . . . . . 34
> 
> The FEOS Table Generation Tool
> 
> 13 Generation of EOS Tables
> 
> 45
> 
> 45
> 
> 13.1 Additional Features . . . . . . . . . . . . . . . . . . . . . . . . 45
> 
> 14 Source Code Structure
> 
> 15 Input Parameters
> 
> 16 EOS Table Structure
> 
> 47
> 
> 47
> 
> 49
> 
> 16.1 Qtable / CriticalDataTable Structures
> 
> . . . . . . . . . . . . . 49
> 
> 16.2 FEOS Format . . . . . . . . . . . . . . . . . . . . . . . . . . . 50
> 
> 16.3 SESAME Formats
> 
> . . . . . . . . . . . . . . . . . . . . . . . . 50
> 
> 16.4 Other Output Formats . . . . . . . . . . . . . . . . . . . . . . 52
> 
> 17 User-Deﬁned Calculations
> 
> 53
> 
> 17.1 Isobaric Expansion Data . . . . . . . . . . . . . . . . . . . . . 53
> 
> 4

### [FEOS-Package-Documentation2012.pdf] 第 5 页

> The SHOWEOS Table Visualization Tool
> 
> 18 Visualization of EOS Tables
> 
> 19 Source Code Structure
> 
> 20 Input Parameters and Procedures
> 
> 55
> 
> 55
> 
> 57
> 
> 57
> 
> 20.1 General Settings . . . . . . . . . . . . . . . . . . . . . . . . . . 57
> 
> 20.2 Isocurves . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 59
> 
> 20.3 Mountain Plots . . . . . . . . . . . . . . . . . . . . . . . . . . 60
> 
> 20.4 Hugoniots . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 61
> 
> 20.5 Single Point Information . . . . . . . . . . . . . . . . . . . . . 62
> 
> References
> 
> 63
> 
> 5

### [FEOS-Package-Documentation2012.pdf] 第 6 页

> The FEOS Package
> 
> 1
> 
> Introduction / Overview
> 
> The FEOS package is a C++ computer code which consists of three parts:
> 
> 1. the FEOS library (ﬁle ”libfeos.a”),
> 
> 2. the FEOS table generation tool (executable ”feos”),
> 
> 3. the SHOWEOS table visualization tool (executable ”showeos”).
> 
> The main part of the new package, the FEOS library, provides all the routines
> which are needed to calculate the equation-of-state (EOS) of an, in principle,
> arbitrary material as a function of density and temperature. The underlying
> physical model is the ”quotidian equation-of-state model (QEOS)”, described
> further in Ref. [2]. The background of the original code MPQeos, together
> with some applications, is described in a correspondig MPQ Report 229 [3].
> Having outsourced the main EOS routines into a static library an implemen-
> tation of the EOS directly into the user’s code was made possible. For this
> purpose the library provides several interfaces, for codes written in C, C++,
> or Fortran. Furthermore, a ﬁle containing a database of material parameters
> which is accessed by the FEOS library is intended to be exchanged between
> a growing community of FEOS users.
> 
> The second part, the FEOS table generation tool makes use of the FEOS
> library and can be used to create EOS table ﬁles as a function of density
> and temperature. Several output formats, like the SESAME format, already
> come with the package, but the user is free to write her/his own output
> routines. Also, the FEOS table generation tool provides the possibility to
> perform ”simple” user-deﬁned calculations which require an EOS.
> 
> The SHOWEOS table visualization tool can be used to visualize the FEOS
> (or SESAME) table ﬁles, i.e. to make plots of isotherms, isochores, isen-
> tropes, Hugoniot curves, or to show three-dimensional phase planes.
> 
> Figure 1 gives an overview of the whole package’s structure. The documen-
> tation explains in detail how to use the three diﬀerent parts of the package
> and gives hints how and where to change the source code in order to cus-
> tomize it for the user’s own needs. The part which deals with the FEOS
> 
> 6

### [FEOS-Package-Documentation2012.pdf] 第 7 页

> Figure 1: Outline of the FEOS package.
> 
> 7

### [FEOS-Package-Documentation2012.pdf] 第 8 页

> library includes also a short description of the physical model and the im-
> provements and changes applied to the original MPQeos code. Furthermore,
> the library interface routines and their implementation into any user’s code
> are explained in detail.
> 
> 1.1 Citation Rules
> 
> Whenever the FEOS package or parts of it are used Reference [4], which
> contains a short section about the package, must be cited. For the future, a
> stand-alone publication about the FEOS package in a computational journal
> is planed and the users will be informed on the web (http://th.physik.uni-
> frankfurt.de/˜faik) when it is available. Also, since the package relies on the
> QEOS model and on the MPQeos code, one should always cite the original
> publications (Ref. [1, 2]).
> 
> 2 Package File Structure
> 
> The FEOS package comes in a packed ﬁle ”FEOS 12.9-beta 20120921.zip”.
> Under Unix this ﬁle can be unzipped with the command ”unzip”. After
> having unzipped the ﬁle, three directories will be present:
> 
> 1. /Code → contains all source ﬁles of the package,
> 
> 2. /Documents → documentation and QEOS/MPQeos pdf ﬁles,
> 
> 3. /EOS-Data → working directory for table generation and visualization.
> 
> The directory /Code contains all the source ﬁles of the package. These
> ﬁles are subdivided into four classes. The ﬁles which begin with the preﬁx
> ”COMMON-” (Table 1) contain the routines which are used by all three
> parts of the FEOS package. The ﬁles which begin with the preﬁx ”LIB-”
> contain all routines of the FEOS library. They are explained in detail in the
> library part of the documentation. Furthermore, the library interface header
> ﬁle ”libfeos.h” also belongs to the FEOS library. The ﬁles which begin with
> the preﬁxes ”FE-” / ”SE-” contain the routines of the FEOS table generation
> / FEOS table visualization tools. Their content is explained in detail in the
> 
> 8

### [FEOS-Package-Documentation2012.pdf] 第 9 页

> COMMON-00 DEFINITS.H Conversion factors, physical and mathe-
> matical constants, and EOS table storage
> structures
> 
> COMMON-01 UTILITIES.C Routines
> 
> for memory allocation and
> 
> deallocation
> 
> COMMON-02 READFILE.C Routines for reading ASCII ﬁles
> 
> Table 1: Common source ﬁles used by all parts of the FEOS package.
> 
> corresponding parts of the documentation. Finally, the Makeﬁle contains all
> commands for the compilation of the code (Section 3).
> 
> The directory /Documents contains the documentations of the FEOS package
> and several pdf ﬁles about QEOS and MPQeos.
> 
> In the directory /EOS-Data all the calculations with the table generation
> and the table visualization tools, whose exectuables will be present after in-
> stallation, are supposed to be done. The directory contains the precalculated
> Thomas-Fermi table ﬁle for hydrogen and the material parameter database
> ﬁle. These two ﬁles are both read by the FEOS library. The two examplary
> parameter ﬁles for aluminum (Al) and fused silica (SiO2) contain all the nec-
> essary settings for the table generation and table visualization tools. The
> general structure of the material parameter database and the tools’ param-
> eter ﬁles will be explained in Section 4. Details on the settings inside these
> ﬁles are given in the corresponding sections of the documentation.
> 
> 3
> 
> Installation
> 
> The Makeﬁle contains all information for the compilation of the source code.
> The whole source code inside the directory /Code is compiled under Unix
> with the command ”make all”. By default, the GNU C++ compiler g++ is
> used. After FEOS has been installed, the FEOS library ﬁle ”libfeos.a” will
> be present. Also the executables ”feos” and ”showeos” of the package tools
> will be there and automatically copied to the tools’ working directory /EOS-
> Data. In order to reset the package to the uncompiled status, the command
> ”make clean” can be used and all executables and object ﬁles will be deleted.
> In principle, the code can be also compiled under Windows, but then the
> user has to take care by himself/herself of the compilation.
> 
> 9

### [FEOS-Package-Documentation2012.pdf] 第 10 页

> 4 Parameter & Database File Structure
> 
> A parameter ﬁle ”Materialname.par” and the material parameter database
> ﬁle ”FEOS Material-DB.dat” are ASCII ﬁles devided into several sections by
> headlines (”Q-table”, ”Material-7386:”, etc.). Each section contains one or
> several lines with a key-word (like ”Rhonorm”, ”[7386] A[1]”), a ”=” sign,
> and some value. Lines can be commented out by a % or # at the beginning.
> Furthermore, the sections in a parameter ﬁle are grouped into two parts.
> The ﬁrst part contains the settings for the FEOS table generation tool, the
> second part those for the SHOWEOS table visualization tool.
> 
> 5 Package Standard Units
> 
> The code-internal units of the whole FEOS package are ﬁxed to cgs-units,
> except for the temperature which is given in eV. Thus, the following units
> are used:
> 
> • Temperature: eV
> 
> • Pressure: dyne/cm2 or erg/cm3
> 
> • Speciﬁc internal energy: erg/g
> 
> • Speciﬁc Helmholtz free energy: erg/g
> 
> • Speciﬁc entropy: erg/eVg
> 
> • Charge state: multiple of the unit electron charge
> 
> 10

### [FEOS-Package-Documentation2012.pdf] 第 11 页

> The FEOS Library
> 
> 6 The Physics behind the QEOS Model
> 
> The FEOS library contains all the routines which are required to calculate
> an EOS as a function of density and temperature. Before going deeper into
> the technical details, this section gives a short overview of the physics of the
> QEOS model and the improvements which have been applied to the FEOS
> library with regard to the original MPQeos code. In order to understand all
> settings of the FEOS library and of the tools, it is inevitable to understand
> the basical physics behind them. Users which are interested in really all
> details of the model are referred to Ref. [2, 5].
> 
> 6.1 General Facts
> 
> In the QEOS model the speciﬁc Helmholtz free energy F = E − T S is
> composed of three contributions, an electronic part, an ionic part, and the
> phenomenological bonding correction:
> 
> F (ρ, T ) = Fe(ρ, T ) + Fi(ρ, T ) + Fb(ρ, T )
> 
> (1)
> 
> In this documentation, all three components of F are assumed to be a func-
> tion of a single temperature T . However, the electronic part does not depend
> on the ionic part and in principle there is no diﬃculty in separating the ion
> and the electron temperatures with the FEOS library. The thermodynamical
> quantities like pressure p, speciﬁc internal energy E, and speciﬁc entropy S
> are derived from the speciﬁc Helmholtz free energy:
> 
> pe,i,b = ρ2 ∂Fe,i,b
> ∂ρ
> 
> , Se,i,b = −
> 
> ∂Fe,i,b
> ∂T
> 
> , Ee,i,b = Fe,i,b + T Se,i,b
> 
> (2)
> 
> Besides these quantities, the charge state Q is calculated. In the following
> subsections the three parts of the QEOS model will be described shortly.
> 
> To calculate an EOS for any particular element or mixture, the material
> composition must be speciﬁed: atomic number Z[i], atomic weight A[i], and
> number of atoms X[i] per ”molecule” of each single element i. Furthermore,
> the QEOS model requires two empirical parameters to calibrate the generated
> EOS, namely, the density ρo and the bulk modulus Ko = ρ (∂p/∂ρ) at a
> 
> 11

### [FEOS-Package-Documentation2012.pdf] 第 12 页

> certain reference value of temperature To and zero pressure p = po = 0. For
> substances that are in the solid state at normal conditions, usually the values
> To ≈ 300 K are used. For details on the calibration, see Subsection 6.3.
> 
> The original MPQeos code was designed to calculate an EOS within the
> following range:
> ρ
> ρo
> 
> 10−4 eV ≤ T ≤ 106 eV.
> 
> 10−7 ≤
> 
> ≤ 106,
> 
> (3)
> 
> In the FEOS library a hard lower limit (numerical ﬂoor) was introduced due
> to numerical limitations and is currently set to (see constants ”T ZERO”
> and ”RHO ZERO” in ”LIB-00 DEFINITS.H”):
> 
> ρmin = 10−50 g
> 
> cm3 ,
> 
> Tmin = 10−4 eV.
> 
> (4)
> 
> One important feature of the QEOS model is the description of van-der-Waals
> loops [6] in the liquid-vapor region. This means that liquid-vapor phase
> coexistence can be described by applying a Maxwell construction. More
> information about the corresponding procedure can be found in Section 6.6.
> 
> 6.2 Electronic EOS: TF Model
> 
> For the calculation of the electronic contribution of a single element – the
> most important part of an EOS for hot dense matter – the simple Thomas-
> Fermi (TF) model [7, 8] is used. In this model the electrons are described
> as a Fermi gas in the self-consistent electrostatic ﬁeld of the atom which is
> produced by the ion mesh and the electrons themselves. Matter is segmented
> into spherical cells for which the equilibrium electron distribution is calcu-
> lated by solving the TF equation. For the segmentation Wigner-Seitz cells
> [9] are used. Hence, the radius r0 of the cells with atomic mass A, density ρ,
> and proton mass Mp is choosen in the following way:
> 
> 4πr3
> 
> 0/3 = AMp/ρ
> 
> (5)
> 
> Since the electrons are assumed to be a Fermi gas in the electrostatic ﬁeld of
> the electrons and the ions, there is no distinction between valence electrons
> and electrons from the inner shells. Instead of this they can be seperated
> in localized and non-localized electrons. If the electrostatic potential V (r) is
> normalized to disappear at the cell boundary, those electrons are localized
> which have negative total energy (cid:15) = p2/2me − eV (r) with the classical
> momentum p. For the free atom for T = 0 this is the case for all electrons.
> Electrons with positive energy are called non-localized. They are responsible
> for the electron pressure and ionization eﬀects.
> 
> 12

### [FEOS-Package-Documentation2012.pdf] 第 13 页

> TF equation for T = 0
> 
> For T = 0 [10] the TF equation is:
> 
> d2χ(x)
> dx2 =
> 
> 1
> x1/2 χ3/2
> 
> (6)
> 
> It is a dimensionless function where x = r/a0, and the function χ is deﬁned
> by the potential V (r) and the chemical potential µ. µ is determined by
> the condition of charge neutrality of the cell. Zχ(r) can be regarded as the
> eﬀective nuclear charge.
> 
> eV (r) + µ ≡
> 
> Ze2
> r
> 
> χ(r)
> 
> a0 =
> 
> (cid:18) 3π
> 4
> 
> 1
> 2
> 
> (cid:19)2/3 ¯h2
> 
> me2 Z −1/3
> 
> The boundary conditions for the TF equation are:
> 
> χ(x) → 1,
> 
> x → 0
> 
> (cid:21)
> 
> (cid:20) x
> χ(x)
> 
> dχ
> dx
> 
> = 1
> 
> x=x0
> 
> (7)
> 
> (8)
> 
> (9)
> 
> (10)
> 
> The ﬁrst boundary condition is a result of the divergence of the potential
> close to the nucleus. The second condition follows from the charge neutrality
> of the cell. With other words: the electrical ﬁeld Er(r) = −(∂φ/∂r) at the
> boundary of the neutral cell x0 must disappear in the spherical case because
> of the law of Gauß:
> 
> (cid:20)dφ
> dx
> 
> (cid:21)
> 
> x=x0
> 
> = 0 ⇔
> 
> (cid:21)
> 
> (cid:20) x
> χ(x)
> 
> dχ
> dx
> 
> = 1
> 
> x=x0
> 
> (11)
> 
> TF equation for ﬁnite temperatures
> 
> For ﬁnite temperatures Feynman, Metropolis and Teller [9] derived a similar
> version of the TF equation
> 
> d2Ψ(ξ)
> dξ2 = aξF1/2
> 
> (cid:21)
> 
> (cid:20)Ψ(ξ)
> ξ
> 
> (12)
> 
> 13

### [FEOS-Package-Documentation2012.pdf] 第 14 页

> with the following deﬁnitions:
> 
> ξ =
> 
> r
> r0
> 
> Ψ(ξ) = ξ
> 
> eV + µ
> kT
> 
> a =
> 
> 4πmee2r2
> 
> 0(2mekT )1/2
> π¯h3
> 
> (13)
> 
> (14)
> 
> (15)
> 
> r0 is the cell radius, and F1/2 denotes the Fermi-Dirac integral. The boundary
> conditions for ﬁnite T are similar to those for T = 0:
> 
> Ψ(0) =
> 
> Ze2
> kT r0
> 
> Ψ(cid:48)(1) = Ψ(1)
> 
> Thermodynamic variables
> 
> (16)
> 
> (17)
> 
> By solving the TF equation one obtains the equilibrium electron distribution
> in the cell and thereby the energy of the electrons which consists of three
> contributions: kinetic energy K, potential energy of the electrons among
> each other Uee, and potential energy of the electrons with the nucleus Uen:
> 
> Etot
> 
> e = K + Uen + Uee
> 
> (18)
> 
> The Helmholtz free energy Fe = Ee − T Se is obtained by integrating the
> Gibbs-Helmholtz relation [11]:
> 
> Etot
> 
> e =
> 
> ∂
> ∂β
> 
> [βFe] ,
> 
> β = 1/kT
> 
> (19)
> 
> The charge state depends on the number of electrons in non-localized states
> (g(r, p) denotes the Fermi distribution function):
> 
> (cid:90)
> 
> (cid:90)
> 
> d3r
> 
> Q =
> 
> (cid:15)>0
> 
> 2d3p
> h3 g(r, p)
> 
> (20)
> 
> Advantages / disadvantages of the simple TF model
> 
> The most important advantage of the simple TF model is the fact that calcu-
> lations are faster than with advanced TF theories because the TF equation
> 
> 14

### [FEOS-Package-Documentation2012.pdf] 第 15 页

> and all thermodynamical quantities scale with the atomic number and hence
> must be calculated only once for e.g. hydrogen. For example the internal
> energy E of a element (A, Z) at density ρ and temperature T shall be calcu-
> lated. Then one ﬁrst has to rescale ρ and T :
> 
> ρ1 = ρ/AZ T1 = t/Z 4/3
> 
> (21)
> 
> Now the internal energy E1 is calculated for ρ1 and T1 for hydrogen A = Z =
> 1. E is obtained by the proper scaling formula:
> 
> E(ρ, T ) =
> 
> Z 7/3
> A
> 
> E1(ρ1, T1)
> 
> (22)
> 
> For all other thermodynamical quantities similar formulas exist. The only
> restraint for the use of the scaling property is that the original TF table
> (A = Z = 1) must cover a large density-temperature area which becomes
> clear when looking at equation (21).
> 
> The most important disadvantage of the simple TF model is the negligence
> of attractive (bonding) forces between neutral atoms. This is the reason for
> an overestimation of the critical pressure and the critical temperature and
> an overall overestimation of pressures near normal conditions. The bond-
> ing forces originate from quantum eﬀects in the electron-electron interaction.
> There exist extended TF theories like the Thomas-Fermi-Dirac (TFD) the-
> ory [12], the Thomas-Fermi-Kirzhnitz (TSK) theory [13] and the quantum
> statistical model (QSM) [14, 15]. Unfortunately, they are computationally
> more intensive and do not contain the scaling property of the simple TF
> theory.
> 
> For more details about the TF theory, its limiting cases, and inter-/extrapo-
> lation methods in the QEOS model the reader ist referred to Ref. [3, 2].
> 
> 6.3 Semiempirical Bonding Correction
> 
> The semiempirical bonding correction, the recalibration scheme of QEOS, is
> added to the total EOS in order to improve the previously mentioned fail-
> ures of the Thomas-Fermi EOS not to take care of exchange forces and to
> overestimate the electronic pressure in the solid body. A fully quantum me-
> chanical treatment of the electrons in the solid body would be too elaborate
> within the framework of the QEOS model. The free energy of the bonding
> correction is:
> 
> Fb = E0
> 
> (cid:110)
> 
> 1 − exp
> 
> (cid:16)
> 
> (cid:104)
> 
> 1 − (ρo/ρ)1/3(cid:105)(cid:17)(cid:111)
> 
> b
> 
> (23)
> 
> 15

### [FEOS-Package-Documentation2012.pdf] 第 16 页

> Since Fb does not depend on the temperature, it follows Eb = Fb. The
> pressure then is:
> 
> pb = ρ2 ∂Eb
> ∂ρ
> 
> = −
> 
> (cid:18)E0bρo
> 3
> 
> (cid:19) (cid:18) ρ
> ρo
> 
> (cid:19)2/3
> 
> (cid:34)
> 
> (cid:32)
> b
> 
> 1 −
> 
> exp
> 
> (cid:18) ρo
> ρ
> 
> (cid:19)1/3(cid:35)(cid:33)
> 
> (24)
> 
> The constants E0 and b determine the bonding correction. They characterize
> the range and the magnitude of the bonding forces. In order to determine
> them, two conditions must be fulﬁlled:
> 
> 1. The total pressure po = pio + peo + pbo must vanish at the user-deﬁned
> reference conditions (ρo,To). For substances that are in the solid state
> at normal conditions, usually the values To ≈ 300 K are used.
> 
> 2. The value of the bulk modulus [16] (and thereby the sound speed)
> 
> Ko = ρ
> 
> (cid:18) ∂p
> ∂ρ
> 
> (cid:19)
> 
> ρo
> 
> (25)
> 
> at the reference conditions must be equal to the user-deﬁned value. A
> relatively small diﬀerence between the isothermal and isentropic bulk
> moduli is usually ignored.
> 
> The theoretical motivation for the form of the Helmholtz free energy Fb [17]
> is the Morse potential in a two-atomic molecule with the bonding energy
> D, the equilibrium distance Re, and a constant b which must be determined
> empirically:
> 
> UM (R) = D (cid:2)e−2b(R−Re) − 2e−b(R−Re)(cid:3)
> 
> (26)
> 
> The bonding correction has the strongest eﬀect on the total EOS near the
> solid density. At higher densities the TF electronic contribution dominates.
> 
> 6.4 Ionic EOS: Cowan Model
> 
> The thermodynamical properties of the ionic contribution which in the QEOS
> model is totally independent of the electronic contribution are described
> through the ionic EOS. The contribution of the ions to the total EOS is sig-
> niﬁcant for temperatures T < 10 eV and densities near the reference (solid)
> density ρ/ρo < 2. For higher temperatures and/or densities the electronic
> and bonding contributions dominate. In QEOS the Cowan model is used.
> 
> 16

### [FEOS-Package-Documentation2012.pdf] 第 17 页

> It interpolates between known limiting thermodynamical cases by the aid of
> empirical formulas. The energy in the model is of purely thermal nature.
> Coulomb and bonding energies are taken care of in the electronic and the
> bonding contributions. The following list gives an overview of the limiting
> physical cases of the Cowan model:
> 
> • Ideal gas law [12] (high temperatures and/or low densities):
> 
> pi = ρkT /AMp, Ei =
> 
> 3
> 2
> 
> kT /AMp,
> 
> Si = k
> 
> (cid:20)
> S0 +
> 
> 3
> 2
> 
> (cid:21)
> log (cid:0)kT /ρ2/3(cid:1)
> 
> /AMp
> 
> S0 is given through the Sackur-Tetrode formula:
> 
> S0 =
> 
> 5
> 2
> 
> + log (2AMp) −
> 
> log (cid:0)h2/2πAMp
> 
> (cid:1)
> 
> 3
> 2
> 
> (27)
> 
> (28)
> 
> • Melting scaling law [18] (energy and density for non-ideal dense liquids):
> 
> pi =
> 
> (cid:20)
> 
> ρkT
> AMp
> 
> 1 + γF (ρ) f
> 
> (cid:19)(cid:21)
> 
> (cid:18) Tm
> T
> 
> Ei =
> 
> 3
> 2
> 
> (cid:20)
> 
> kT /AMp
> 
> 1 + f
> 
> (cid:19)(cid:21)
> 
> (cid:18) Tm
> T
> 
> (29)
> 
> (30)
> 
> γF is determined by the melting temperature Tm(ρ) and f (Tm/T ) is a
> scaling function.
> 
> • Lindemann melting law:
> 
> Tm (ρ) /Θ2
> 
> D (ρ) = α/ρ2/3
> 
> ΘD – Debye temperature, α – material dependent constant
> 
> • Dulong-Petit law (ΘD(ρ) ≤ T ≤ Tm(ρ)):
> 
> Ei ≈ 3kT /AMp
> 
> • Gr¨uneisen EOS [12] (T < Tm(ρ)):
> 
> pi = Γ (ρ) ρEi
> 
> Dependence of the Gr¨uneisen parameter Γ on ΘD [12]:
> 
> Γ (ρ) = −
> 
> V
> ΘD
> 
> ∂ΘD
> ∂V
> 
> =
> 
> ∂ log ΘD
> ∂ log ρ
> 
> 17
> 
> (31)
> 
> (32)
> 
> (33)
> 
> (34)

### [FEOS-Package-Documentation2012.pdf] 第 18 页

> • Debye-Modell:
> 
> hνD = kΘD
> 
> νD – Debye frequency, ΘD – Debye temperature
> ⇒ Speciﬁc heat of non-conductors for T < ΘD:
> 
> cV =
> 
> 12π4R
> 5
> 
> (cid:18) T
> ΘD
> 
> (cid:19)3
> 
> • Third law of thermodynamics (Nernst’s law):
> 
> lim
> T →0
> 
> S (ρ, T ) = 0
> 
> (35)
> 
> (36)
> 
> (37)
> 
> The Cowan model consists of two independent parts. The empirical part of
> the model makes estimations for the Debye and the melting temperatures
> depending on the density.
> In the structural part the EOS is calculated.
> Therefore, the scaling variables u and w are introduced:
> 
> u = ΘD (ρ) /T
> 
> w = Tm (ρ) /T
> 
> (38)
> 
> (39)
> 
> Cowan deﬁnes a scaling function f (u, w) which determines the Helmholtz
> free energy of the ions:
> 
> Fi (ρ, T ) =
> 
> kT
> AMp
> 
> f (u, w)
> 
> (40)
> 
> There are three diﬀerent areas in u-w space for which the scaling function
> is deﬁned. For temperatures above the melting temperature (T > Tm) the
> following empirical formula is used:
> 
> f (u, w) = −
> 
> 11
> 2
> 
> +
> 
> 9
> 2
> 
> w1/3 +
> 
> 3
> 2
> 
> log
> 
> (cid:19)
> 
> (cid:18) u2
> w
> 
> , w ≤ 1
> 
> (41)
> 
> For the ”hot” solid body (Tm > T > 3ΘD) holds:
> 
> f (u) = −1 + 3 log u + (cid:0)3u2/40 − u4/2240(cid:1) , w > 1, u < 3
> 
> (42)
> 
> For the ”cold” solid body (T ≤ 3ΘD) applies:
> 
> f (u) =
> 
> π4
> 9
> u + 3 log (cid:0)1 − e−u(cid:1) −
> 5u3
> 8
> + e−u (cid:0)3 + 9u−1 + 18u−2 + 18u−3(cid:1) , w > 1, u ≥ 3
> 
> (43)
> 
> 18

### [FEOS-Package-Documentation2012.pdf] 第 19 页

> In the Cowan model the Gibbs free energies in the liquid and in the solid
> phase on the melting curve are exactly the same [3]. This means that the
> QEOS model does not contain melting.
> 
> The task of the empirical part of the Cowan model is to make the Debye and
> melting temperatures and the Gr¨uneisen parameter available to the struc-
> tural part as functions of the density. It has to be pointed out that a failure
> in the estimation of these quantities only has little inﬂuence on the pres-
> sure and the energy of the ionic EOS. The empirical part should fulﬁll the
> formulas for the Gr¨uneisen parameter (34) and the Lindemann melting law
> (31).
> 
> Using a reference density ρref = (A/9Z 0.3) g/cm3 the densities are scaled
> with ξ = ρ/ρref . Thereby, the reference density corresponds with a atomic
> radius of Ra ≈ 1, 5 · 10−8Z 0.1 cm. Then Cowan’s estimations are:
> 
> kTm = 0.32
> 
> ξ2b+10/3
> (1 + ξ)4 [eV]
> 
> kΘD =
> 
> 1, 68
> Z + 22
> 
> ξb+2
> (1 + ξ)2 [eV]
> 
> Γ = b +
> 
> 2
> 1 + ξ
> 
> b = 0.6Z 1/9
> 
> (44)
> 
> (45)
> 
> (46)
> 
> Together with α = 0.0262 (cid:0)A2/3Z 0.2(cid:1) (Z + 22)2 the equations (31) and (34)
> are fulﬁlled. Since the formulas of the empirical model are simple, it is clear
> that no exact estimations can be done, and the calculated quantities have
> only a qualitative character.
> 
> 6.5 Homogeneous Mixtures of Elements
> 
> Besides pure elements, the QEOS model includes the possibility to calculate
> the EOS of homogenous mixtures of elements. Unfortunately, the corre-
> sponding procedure described in [2] was not implemented in version 2.0 of
> MPQeos. Hence, the so-called TF-mixing-of-elements method was added to
> the FEOS library. The ionic contribution and the bonding correction are
> handled as a single species with mean atomic number ¯Z and weight ¯A. For
> the electronic contribution of the mixture the densities ρ[i] (eﬀectively the
> partial volumes) of all species i are iteratively adjusted in order to equilibrate
> 
> 19

### [FEOS-Package-Documentation2012.pdf] 第 20 页

> all TF pressures pe[i] and to fulﬁll an additive volume rule:
> 
> 1) pe[i] (ρ[i], T ) = pe ∀i,
> 
> 2)
> 
> ¯A
> ρ
> 
> (cid:88)
> 
> =
> 
> x[i]
> 
> i
> 
> A[i]
> ρ[i]
> 
> (cid:88)
> 
> ( ¯A =
> 
> x[i]A[i]) . (47)
> 
> i
> 
> In these equations x[i] = X[i]/ (cid:80)
> the atomic weight of species i.
> 
> i X[i] is the number fraction, and A[i] is
> 
> The thermodynamic values for the electronic component of the mixture are
> ﬁnally obtained by summing up the single element values (with densities
> obtained by the above scheme), each weighted by x[i]A[i]/ ¯A.
> 
> The described procedure must be called for every density and temperature,
> and therefore it is clear that the calculation of mixtures of elements is com-
> putationally more intensive than for a single element. Actually, in some few
> cases the iteration process does not converge. In this case the user is rec-
> ommended to start the calculation again or to slightly change the density
> and/or temperature.
> 
> 6.6 Liquid-Vapor Phase Coexistence
> 
> The QEOS model describes van-der-Waals loops [6] (liquid-vapor metastable
> states) on isotherms below the critical point. Liquid-vapor phase coexis-
> tence can be described through a fully equilibrium EOS which is obtained
> by a Maxwell construction eliminating the van-der-Waals loops. Figure 2
> shows a metastable isotherm with a van-der-Waals loop (solid line) as well
> as the corresponding equilibrium isotherm with saturated vapor / equilib-
> rium pressure psat (dashed line). The region of liquid-vapor metastable and
> equilibrium states is delimited by the so-called binodal / vaporization curve.
> The extrema of the van-der-Waals loops are connected through the so-called
> spinodal. The question whether one has to use the metastable or the equilib-
> rium EOS below the binodal must be individually answered for each problem
> under consideration. Ref. [4] gives an answer for hydrodynamic simulations
> and shows results for volumetrically heated matter.
> 
> According to Maxwell’s rule the saturated vapor pressures for each isotherm
> below the critical point are determined by ﬁnding such two points along
> the isotherm with equal pressure p = psat and equal Gibbs free energy
> G = E + pV − T S (chemical potential). This rule corresponds to the well
> known geometrical rule of equal areas between the van-der-Waals loop and
> 
> 20

### [FEOS-Package-Documentation2012.pdf] 第 21 页

> Figure 2: Isotherm with and without the
> Maxwell
> the
> construction
> volume-pressure phase plane; the
> binodal and the spinodal touch
> each other at the critical point
> CP.
> 
> on
> 
> the equilibrium isotherm:
> 
> (T = const.)
> 
> (cid:90) Vliq
> 
> Vvap
> 
> pdV = psat (Vvap − Vliq) .
> 
> (48)
> 
> In the original MPQeos code the Maxwell construction was calculated with
> this geometrical rule which is especially for low temperatures in the two-
> phase region computationally very intensive and imprecise.
> In FEOS the
> MPQeos method was replaced by a root ﬁnding algorithm which determines
> the points on the liquid and the vapor sides of the binodal with equal Gibbs’
> free energies and pressures. Since this ”new” method involves no numerical
> integrations, it is much faster and more accurate.
> 
> Nevertheless, there exists one important limitation for the calculation of the
> Maxwell construction: Since psat and the density at the vapor branch of the
> binodal become very low for temperatures around room temperature, the
> EOS has to be calculated down to very low densities. As already mentioned
> in Subsection 6.1, computational limits determine the lowest calculatable
> density. The Maxwell routines of the library will print out warnings if the
> Maxwell construction cannot be done consistently for a given temperature.
> Furthermore, the lowest temperature which could be calculated consistently
> is returned by the library. Note that even if the Maxwell construction can
> be done consistently one should be carefull to check the correct behaviour
> of the EOS for such very low densities. In some cases, it can happen that
> the code violates the ideal gas law limit. This is a construction site for the
> future.
> 
> If the user decides to calculate the Maxwell equilibrium EOS, the library
> applies two additional steps: In the ﬁrst step, the critical point is looked up
> via a bisectioning algorithm. A check is done on loops in each isotherm, until
> the one with loops at maximum temperature is found. On this isotherm, the
> 
> 21

### [FEOS-Package-Documentation2012.pdf] 第 22 页

> density where d2p/dρ2 = 0 is determined. In the second step, the vaporisation
> curve is calculated by applying the Maxwell construction to each temperature
> speciﬁed by the user below the critical point. In order to save computational
> time, both steps are performed during the material initialization stage.
> 
> Later, for computing EOS data at some point inside the two-phase region,
> the thermodynamic quantities are interpolated linearly. Outside the two-
> phase region, the computation of the thermodynamic quantities goes as in
> the normal case. As the user speciﬁed temperature grid for the Maxwell con-
> struction strongly determines the quality or even the existence of the critical
> data and vaporisation curve, one should not specify too few temperatures
> near and inside the critical region.
> 
> 6.7 Cold Curve Improvement
> 
> Despite the existence of the bonding correction (Section 6.3), the QEOS
> model still overestimates the location of the critical point (pressure pc and
> temperature Tc). Furthermore, in a few cases the value of the cohesive energy
> Ecoh – better known as enthalpy of sublimation – can become negative. In
> order to solve this problem in the FEOS library, the TF cold curve and the
> bonding correction can now be replaced for densities ρ < ρo by a soft-sphere
> function which was proposed by Young et al. [5]:
> 
> Ecold (ρ, T = 0) = Aρn − Bρm + Ecoh .
> 
> (49)
> 
> The constants A and B are adjusted so as to make the total pressure and
> the internal energy be equal to zero at the reference point (ρo, To):
> 
> p(ρo, To) = E(ρo, To) = 0 .
> 
> (50)
> 
> The free parameters m and n are used to improve the agreement with the
> experimentally (or theoretically) known critical point. At ρ = ρo the sound
> velocity is allowed to be discontinuous.
> 
> The following list demonstrates how the soft-sphere function aﬀects the lo-
> cation of the critical point for aluminum:
> 
> Experimental / theoretical values [5]: Tc = 5700 K,
> Tc = 13487 K,
> Original MPQeos (version 2.0):
> Tc = 5558 K,
> FEOS library:
> 
> pc = 1820 bar
> pc = 23487 bar
> pc = 1722 bar
> 
> (m = 0.5, n = 2.0, Ecoh = 12.123 kJ/g)
> 
> 22

### [FEOS-Package-Documentation2012.pdf] 第 23 页

> 7 Technical Design of the Library
> 
> The static library ﬁle ”libfeos.a” is basically a collection of object ﬁles /
> routines. Those routines which are intended to be used from outside the
> library, namely from the user’s code or the FEOS table generation tool,
> form the FEOS library interface. The interface is designed in such a way
> that all routines can be either called from a C, a C++, or a Fortran code.
> Instructions concerning the implementation of the library ﬁle into the user’s
> code and detailed descriptions of the interface routines are given in Sections
> 11 and 12.
> 
> In principle, the FEOS library can calculate the EOS of an arbitrary number
> of materials with ﬁxed composition in parallel. The work done by the library
> routines can be classiﬁed into two categories: 1) routines which are respon-
> sible for the initialization of the library and of the materials which shall be
> calculated, and 2) routines which calculate the thermodynamic functions.
> Analogously, also the interface routines can be basically classiﬁed into two
> categories: 1) the obligatory routines which are responsible for the initializa-
> tion and ﬁnalization, 2) the facultative routines which return the information
> calculated during the initialization stage and the thermodynamic functions
> (Section 12).
> 
> Figure 3 gives an overview of the logical structure how the library is in-
> tended to be implemented into a user’s code for three diﬀerent materials.
> First, the library itself is initialized with an arbitrary number of material en-
> tities. Then, all materials must be initialized with several parameters by the
> material initialization procedure described in the next subsection. Having
> initialized a material, one can either retrieve the information about the ma-
> terial which are already present and/or one can calculate the thermodynamic
> functions (of the full EOS and/or of the EOS contributions with or without a
> Maxwell construction) as a function of density and temperature (see Section
> 8 for a list of information provided by the library). Finally, if the library is
> not to be used anymore, it must be ﬁnalized to free the occupied memory.
> 
> 7.1 Material Initialization Stage
> 
> Figure 4 gives an overview of the initialization procedure of a material within
> the FEOS library. The material initialization is controlled by the interface
> routine ”FEOS Init Mat(...)”. Several arguments have to be passed which
> 
> 23

### [FEOS-Package-Documentation2012.pdf] 第 24 页

> Figure 3: Operational sequence for implementation of the FEOS library.
> 
> 24

### [FEOS-Package-Documentation2012.pdf] 第 25 页

> Figure 4: Operational sequence of the FEOS library material initialization.
> 
> 25

### [FEOS-Package-Documentation2012.pdf] 第 26 页

> control the following options:
> 
> • The number of the material in the FEOS material parameter database
> 
> ﬁle (Section 10) must be deﬁned.
> 
> • A ﬂag tells the library if a Maxwell construction shall be initialized
> for the material. If set to yes, an array with temperatures and its size
> must be passed. These temperatures control the quality of the Maxwell
> construction.
> 
> • Another ﬂag tells the library if the improved cold curve (Section 6.7)
> 
> shall be used for the material.
> 
> Within the several steps of the initialization procedure the diﬀerent class
> objects of the FEOS library are constructed for the material. The FEOS li-
> brary knows basically three classes: 1) a class ”Ionpart” for the storage of the
> general material parameters and for the routines used for the calculation of
> the ionic contribution, the bonding correction, and the improved cold curve,
> 2) a class ”QIPscheme” for the electronic contribution / interpolation on the
> TF table for each single element in a material, and 3) a class ”CriticalData”
> for the Maxwell construction data and routines.
> 
> First, the ”Ionpart” class object is constructed.
> In this step the material
> parameters are read-out from the material parameter database ﬁle (Section
> 10). Then, ”QIPscheme” class objects are constructed for each element in
> the material. Therefore, the precalculated TF table ﬁle for hydrogen is read-
> out and the TF interpolation scheme is set-up for the corresponding atomic
> numbers and atomic weights. In the third step, the parameters of the bonding
> correction (and soft sphere function) are determined.
> 
> If a Maxwell construction (Section 6.6) is desired, a ”CriticalData” class ob-
> ject is constructed and at the same time ﬁlled with data. Therefore, ﬁrst the
> critical point is determined with a bisectioning procedure. Then, for each
> deﬁned temperature below the critical point, the Maxwell construction is it-
> eratively calculated and the binodal / vaporization curve is stored. Later on,
> when calculating a density-temperature point within the two-phase region,
> this precalculated critical data can be used for linear interpolations.
> 
> At the end of a material initialization the routine ”FEOS Init Mat(...)” re-
> turns the number of elements in the choosen material and, if available, the
> quality of the calculated Maxwell construction data.
> 
> 26

### [FEOS-Package-Documentation2012.pdf] 第 27 页

> 8
> 
> Information provided by the Library
> 
> The FEOS library provides a wide set of information. The following list
> summarizes all the properties and parameters which can be retrieved with
> the library interface routines:
> 
> • The following thermodynamic functions as a function of density and
> temperature for the complete EOS and/or for one component (elec-
> tronic EOS, ionic EOS, or pure Thomas-Fermi EOS), either with or
> without a Maxwell construction:
> 
> – Pressure
> 
> – Speciﬁc internal energy
> 
> – Speciﬁc Helmholtz free energy
> 
> – Speciﬁc entropy
> 
> – Charge state for each element in a mixture
> 
> – Summed-up (not mean) charge state for a ”molecule”
> 
> • All the material parameters which are stored in the material parameter
> 
> database (Section 10), especially the material’s composition
> 
> • If initialized, critical point data: temperature, density, pressure, en-
> 
> thalpy, entropy, and compressibility factor at the critical point
> 
> • If initialized: temperatures, densities, pressures, speciﬁc Gibbs free en-
> ergies, speciﬁc enthalpies, and compressibility factors along the binodal
> 
> • If initialized: temperatures, densities, and pressures along the spinodal
> 
> • The temperature and density ﬂoor values of the library, below which
> 
> the EOS cannot be calculated for numerical reasons (Section 6.1)
> 
> • The energy oﬀsets of the electronic and the ionic EOS which are sub-
> stracted to zero the complete speciﬁc energy at reference conditions
> 
> 9 Source Code Structure
> 
> As the QEOS model itself, also the source code of the FEOS library is divided
> into several parts. Table 2 gives an overview of the source ﬁles of the library.
> 
> 27

### [FEOS-Package-Documentation2012.pdf] 第 28 页

> LIB-00 DEFINITS.H
> 
> LIB-01 TF SERVICES.C
> 
> LIB-02 TF TABLE 1.C,
> LIB-02 TF TABLE 2.C
> 
> LIB-03 TF MIXTURE.C
> 
> LIB-04 IONMOD.C
> 
> LIB-05 EOS SERVICES.C
> 
> LIB-06 MAXWELL.C
> 
> Numerical constants for the library
> and paths of the material database
> and the Thomas-Fermi table ﬁles
> 
> Routines for reading the TF-ﬁle
> and calculating the Fermi-Dirac
> functions
> 
> Routines for calculation of the single
> element Thomas-Fermi EOS
> 
> Routines
> Thomas-Fermi EOS of a mixture
> 
> calculation of
> 
> for
> 
> the
> 
> Routines for reading the material
> parameter database and calculation
> of the ionic EOS, the bonding cor-
> rection, and the soft-sphere function
> 
> for
> 
> calculation of
> 
> the
> Routines
> thermodynamic functions without
> Maxwell construction
> 
> Routines for initialization of the
> Maxwell construction and calcula-
> tion of
> the EOS with Maxwell
> construction
> 
> LIB-07 C INTERFACE.C,
> LIB-08 FORTRAN INTERFACE.C
> 
> C/C++ and Fortran interface rou-
> tines
> 
> Table 2: Source ﬁles of the FEOS library.
> 
> The diﬀerent classes of the code were already explained in Section 7.1. The
> ”QIPscheme” class for the calculation of the Thomas-Fermi EOS for a single
> element is deﬁned in the ”LIB-02...” ﬁles. The Thomas-Fermi EOS for a
> mixture of elements (Section 6.5) is obtained in the ”LIB-03...” ﬁle. The
> ”Ionpart” class is deﬁned in the ”LIB-04...” ﬁle.
> 
> The ”LIB-05...” ﬁle combines the diﬀerent parts of the QEOS model and con-
> tains all the routines which calculate the thermodynamic functions without
> a Maxwell construction. These routines may be called by the ”CriticalData”
> class, deﬁned in the ”LIB-06...” ﬁle, to initialize and to calculate the ther-
> modynamic functions with a Maxwell construction. Finally, the interface
> 
> 28

### [FEOS-Package-Documentation2012.pdf] 第 29 页

> routines are deﬁned in the ”LIB-07...” and the ”LIB-08...” ﬁles where the
> Fortran interface routines simply call the C/C++ interface routines.
> 
> 10 Material Parameter Database
> 
> The material parameter database ﬁle ”FEOS Material-DB.dat” contains all
> collected physical material properties and parameters. The FEOS library
> routines access this ﬁle for each material to be initialized. Each parameter
> set / section in the ﬁle begins with the headline ”Material-xxxx:” where xxxx
> is the material number. Allowed material numbers are 1000-9999. Each
> parameter inside a section begins with the preﬁx ”[xxxx] ”. Table 3 lists all
> parameters which must be set for a material. The soft-sphere parameters
> must be only set if the improved cold curve (see Section 6.7) shall be used.
> 
> 11
> 
> Implementation of the Library
> 
> The static library ﬁle ”libfeos.a” is automatically created within the FEOS
> package installation / compilation process (Section 3). It can be implemented
> into any C/C++ or Fortran code.
> 
> If the library accessing code is compiled with the GNU or Intel C++ compiler,
> the following options must be applied for the linking stage:
> 
> -L. -lfeos
> 
> or
> 
> libfeos.a
> 
> For the GNU or Intel C or Fortran compiler, the corresponding options are:
> 
> -L. -lstdc++ -lfeos
> 
> or
> 
> -lstdc++ libfeos.a
> 
> The -L. ﬂag prompts the compiler to search for librariy ﬁles in the same
> directory where it is executed. The -lstdc++ ﬂag tells the compiler to employ
> the C++ library, and the -lfeos ﬂag ﬁnally enables the FEOS library.
> 
> If the library shall be used with a C/C++ code, the ”libfeos.h” header ﬁle
> must be also copied to the code directory, and the ”include ”libfeos.h””
> statement must be used inside the code.
> 
> Once a code is successfully linked together with the FEOS library and the
> executable ﬁle shall be used, one must be careful also to copy the ﬁles
> 
> 29

### [FEOS-Package-Documentation2012.pdf] 第 30 页

> SESAME-Number
> 
> the material
> 
> in the SESAME
> Number of
> database. If not known, this parameter can be
> set to 1000. It is only required for the SESAME
> output format (Section 16.3).
> 
> Treference
> 
> Reference temperature in eV
> 
> Rhoreference
> 
> Bulk-Modulus
> 
> Density at Treference and zero pressure in g/cm3
> 
> Bulk modulus at Treference and Rhoreference in
> dyne/cm2
> 
> Number-of-Elements
> 
> Number of elements which form a mixture. For
> single elements this parameter must be set to 1
> 
> A[1...Element-Number] Atomic weights of all included elements
> 
> Z[1...Element-Number] Atomic numbers of all included elements
> 
> X[1...Element-Number] Number of atoms in one ”molecule” of all in-
> 
> cluded elements
> 
> Ecohesive
> 
> Cohesive energy / enthalphy of sublimation in
> erg/g; used for the soft-sphere function
> 
> Soft-Sphere-m
> 
> Parameter m in soft-sphere function
> 
> Soft-Sphere-n
> 
> Parameter n in soft-sphere function
> 
> Table 3: Parameters to be set for each material entry in the material param-
> eter database ﬁle. A corresponding preﬁx [xxxx] with the material
> number must be put in front of each parameter name.
> 
> ”FEOS Material-DB.dat” and ”FEOS TF-Table 1197.dat” from /EOS-Data
> into the directory where the code is executed. The material parameter
> database and the precalculated Thomas-Fermi table are read during the ini-
> tialization stage of any material to be calculated with the library. If a material
> is not present in the database, a new entry must be created (Section 10).
> 
> 12
> 
> Interface Routines
> 
> The FEOS library provides several routines for the usage in any user’s code.
> To calculate an EOS, some of these routines are obligatory. The other rou-
> 
> 30

### [FEOS-Package-Documentation2012.pdf] 第 31 页

> tines are facultative and can only be called if the obligatory ones are used.
> To get an impression, how the interface routines may be used, one can also
> have a look into the main ﬁle of the FEOS table generation tool (Section 14).
> 
> All interface routines begin with the preﬁx ”FEOS ”. Furthermore, all inter-
> face routines are present in two versions. One version is intended to be called
> from C/C++ codes. The corresponding routines will be marked in blue in
> this section. The other version is intended to be called from Fortran codes,
> and the corresponding routines will be marked in red in the following. The
> ﬁle ”LIB-07 C INTERFACE.C” contains all the C/C++ interface routines.
> In ”LIB-08 FORTRAN INTERFACE.C” the Fortran interface routines are
> located.
> 
> Fortran programmers should take care of the fact that most Fortran com-
> pilers add automatically a ” ” sign at the end of each subroutine’s name
> during linking. The FEOS library assumes that this ” ” sign is present. If
> one of the library Fortran interface routines is called and the Fortran com-
> piler does not automatically add the ” ” sign, then one must manually add
> it (e.g., instead of using ”call FEOS FINALIZE(...)”, the command ”call
> FEOS FINALIZE (...)” must be used).
> 
> If the interface routines are intended to be called from an OpenMP paral-
> lelized code, one must assure that any FEOS interface routine is only called
> by the OpenMP master thread.
> 
> Finally, one should always keep in mind, that any physical quantity argument
> in the interface routines, no matter if input or output, is or must be given in
> the FEOS standard units (Section 5).
> 
> 12.1 Obligatory Interface Routines
> 
> void FEOS Initialize( int entitynumber, int printﬂag )
> 
> FEOS INITIALIZE( entitynumber, printﬂag )
> 
> integer(4) :: entitynumber, printﬂag
> 
> entitynumber (INPUT): Number of diﬀerent materials which the EOS shall
> be calculated for. E.g., to calculate the EOS for Al, Cu and Li, enti-
> tynumber must be set to 3 (or any higher integer).
> 
> 31

### [FEOS-Package-Documentation2012.pdf] 第 32 页

> printﬂag (INPUT): If set to 0, the library will write no output to the console
> (except for error messages). If set to 1, the library will write full output
> to the console. For MPI parallelized codes this ﬂag should only be 1
> for the MPI master task to reduce the output to the console.
> 
> FEOS Initialize must be called before all the other interface routines. It can
> only be called again, if one calls FEOS Finalize before.
> 
> —————————————————————————————————
> 
> void FEOS Finalize( )
> 
> FEOS FINALIZE( )
> 
> FEOS Finalize will free the memory used by the library. Once one has called
> it, except for FEOS Initialize, the other interface routines cannot be called
> anymore.
> 
> —————————————————————————————————
> 
> void FEOS Init Mat( int entity, int materialnumber, int Maxwellﬂag,
> 
> int softsphereﬂag, double* MaxwellTtab, int sizeofMaxwellTtab,
> int* numofelements, int* numofMaxwelliso,
> double* MaxwellTreliable )
> 
> FEOS INIT MAT( entity, materialnumber, Maxwellﬂag, softsphereﬂag,
> 
> MaxwellTtab, sizeofMaxwellTtab, numofelements, numofMaxwelliso,
> MaxwellTreliable )
> 
> integer(4) :: entity, materialnumber, Maxwellﬂag, softsphereﬂag,
> 
> sizeofMaxwellTtab, numofelements, numofMaxwelliso
> 
> real(8) :: MaxwellTtab(sizeofMaxwellTtab), MaxwellTreliable
> 
> entity (INPUT): This integer deﬁnes a unique code-internal identiﬁer for
> any material which will be calculated. Every number is only allowed
> to be initialized once. The allowed range is [1, entitynumber] (see
> FEOS Initialize).
> 
> materialnumber (INPUT): Number of the material in the FEOS material
> 
> parameter database ﬁle.
> 
> 32

### [FEOS-Package-Documentation2012.pdf] 第 33 页

> Maxwellﬂag (INPUT): If set to 1, the critical point will be calculated, and
> the Maxwell construction will be initialized for this material entity. If
> set to 0, no critical point and no Maxwell construction will be available.
> 
> softsphereﬂag (INPUT): If set to 1, the soft-sphere function will be used.
> If set to 0, only the bonding correction will be used. The soft-sphere
> function can only be used if the soft-sphere parameters have been
> deﬁned in the FEOS material parameter database for the material
> with number ”materialnumber”.
> 
> MaxwellTtab (INPUT): Array of size ”sizeofMaxwellTtab” containing a
> list of temperatures in eV in ascending order.
> If the Maxwell con-
> struction should be initialized, it will be explicitly calculated for those
> temperatures. The more temperatures are used, the better the quality
> of the Maxwell data will be, but the longer the initialization will take.
> If the library is used to calculate the EOS for a ﬁxed table, you the
> best result will be achieved if the same temperatures of the EOS table
> It must be assured that at
> are used for the Maxwell initialization.
> least one temperature lies above the critial point!
> 
> sizeofMaxwellTtab (INPUT): Number of temperatures in or size of the
> 
> array ”MaxwellTtab”.
> 
> numofelements (OUTPUT): Number of elements within the material with
> 
> number ”materialnumber”.
> 
> numofMaxwelliso (OUTPUT): If the Maxwell construction is initialized,
> this integer will give the number of temperatures which lie below the
> critical point and for which the Maxwell construction was calculated.
> Attention: This does not imply that these temperatures are the same
> temperatures within your input array ”MaxwellTtab” up to element
> ”numofMaxwelliso”.
> 
> MaxwellTreliable (OUTPUT): If the Maxwell construction is initialized,
> this will represent the lowest temperature for which the Maxwell con-
> struction could be calculated consistently without any problems. This
> means, that the EOS with Maxwell construction is reliable above this
> temperature.
> 
> FEOS Init Mat must be called until any other interface routine for a material
> entity can be called. It must be called for any material the EOS should be
> calculated for (of course, with diﬀerent entity numbers between 1 and enti-
> 
> 33

### [FEOS-Package-Documentation2012.pdf] 第 34 页

> tynumber). Until FEOS Init Mat can be called, the library must have been
> initialized with FEOS Initialize before. For the same entity, FEOS Init Mat
> can only be called again if FEOS Delete Mat has been called before in order
> to delete the material entity, or the whole library has been reinitialized with
> FEOS Finalize followed by FEOS Initialize.
> 
> 12.2 Facultative Interface Routines
> 
> All facultative routines can only be used if the library was (re-)initialized
> with FEOS Initialize and not ﬁnalized with FEOS Finalize. Some facultative
> routines are material-speciﬁc or return information only for one entity. These
> routines can only be called if the material entity has been initialized with
> FEOS Init Mat. Furthermore, some facultative routines require Maxwell-
> construction data. These routines can only be called for a given material
> entity if ”Maxwellﬂag” was set to 1 in FEOS Init Mat.
> 
> void FEOS Get EOS All( int entity, int Maxwell,
> 
> double Rho, double T, int* belowbinodal,
> double* p, double* e, double* s, double* f, double* q, double* qtot,
> double* pe, double* ee, double* se, double* fe,
> double* pi, double* ei, double* si, double* ﬁ,
> double* pTF, double* eTF, double* sTF, double* fTF )
> 
> FEOS GET EOS ALL( entity, Maxwell, Rho, T, belowbinodal,
> 
> p, e, s, f, q, qtot, pe, ee, se, fe, pi, ei, si, ﬁ, pTF, eTF, sTF, fTF )
> 
> integer(4) :: entity, Maxwell, belowbinodal
> 
> real(8) :: Rho, T, p, e, s, f, q(numofelements), qtot, pe, ee, se, fe,
> 
> pi, ei, si, ﬁ, pTF, eTF, sTF, fTF
> 
> entity (INPUT): Deﬁnes the material entity the EOS will be calculated for.
> 
> Maxwell (INPUT): If set to 1, the EOS will be returned with Maxwell
> construction. If set to 0, the EOS will be calculated without Maxwell
> construction. Attention: ”Maxwell” = 1 is only allowed if the Maxwell
> construction has been initialized in FEOS Init Mat for the entity under
> consideration (”Maxwellﬂag” = 1).
> 
> Rho (INPUT): Density in g/cm3 for which the EOS will be calculated.
> 
> 34

### [FEOS-Package-Documentation2012.pdf] 第 35 页

> T (INPUT): Temperature in eV for which the EOS will be calculated.
> 
> belowbinodal (OUTPUT): If ”Maxwell” is set to 1, this integer will be 1
> if the density-temperature point lies inside the two-phase region, and,
> thus, the Maxwell construction is used.
> It will be 0 if the density-
> temperature point lies outside the two-phase region. If ”Maxwell” is
> set to 0, ”belowbinodal” will be always 0, even if the temperature-
> density point lies inside the two-phase region.
> 
> p, e, s, f (OUTPUT): Pressure, speciﬁc internal energy, speciﬁc entropy,
> and speciﬁc Helmholtz free energy of the total EOS (which is the sum
> of the electronic and the ionic EOS).
> 
> q (OUTPUT): Array of size ”numofelements” containing the charge states
> 
> for every element of the material.
> 
> qtot (OUTPUT): Charge state of one ”molecule”. To get the mean charge
> state of a mixture, divide ”qtot” by ”Xtot” (see FEOS Get Mat Par).
> 
> pe, ee, se, fe (OUTPUT): Pressure, speciﬁc internal energy, speciﬁc entropy,
> and speciﬁc Helmholtz free energy of the electronic EOS (which is the
> sum of the pure Thomas-Fermi contribution and the corrections - the
> bonding correction and the soft-sphere function).
> 
> pi, ei, si, ﬁ (OUTPUT): Pressure, speciﬁc internal energy, speciﬁc entropy,
> and speciﬁc Helmholtz free energy of the ionic EOS (which is calculated
> with the Cowan model).
> 
> pTF, eTF, sTF, fTF (OUTPUT): Pressure, speciﬁc internal energy, spe-
> ciﬁc entropy, and speciﬁc Helmholtz free energy of the pure Thomas-
> Fermi EOS.
> 
> Always remember: The total pressure in the FEOS model is set to 0 for a
> given reference point ρo and To. The speciﬁc internal energy and speciﬁc
> Helmholtz free energy are shifted by an oﬀset such that both become 0 for
> each component (total EOS, electronic EOS, ionic EOS, and pure Thomas-
> Fermi EOS) at ρo and To. The ionic and electronic oﬀsets can be retrieved
> out of the library for each material entity with FEOS Get Energy Oﬀsets.
> 
> If the EOS is calculated with a Maxwell construction, the charge states and
> all the quantities from the electronic, ionic, and pure Thomas-Fermi EOS
> become physically meaningless inside the two-phase region.
> 
> 35

### [FEOS-Package-Documentation2012.pdf] 第 36 页

> If one only wants to calculate the electronic EOS, the ionic EOS, or the pure
> Thomas-Fermi EOS, it is highly advisable to use FEOS Get EOS instead of
> FEOS Get EOS All. This will safe computational time, since the unwanted
> contributions are not calculated.
> 
> —————————————————————————————————
> 
> void FEOS Get EOS( int entity, int task, int Maxwell,
> double Rho, double T, int* belowbinodal,
> double* p, double* e, double* s, double* f, double* q, double* qtot )
> 
> FEOS GET EOS( entity, task, Maxwell, Rho, T, belowbinodal,
> 
> p, e, s, f, q, qtot )
> 
> integer(4) :: entity, task, Maxwell, belowbinodal
> 
> real(8) :: Rho, T, p, e, s, f, q(numofelements), qtot
> 
> entity (INPUT): Deﬁnes the material entity the EOS will be calculated for.
> 
> task (INPUT): Deﬁnes the kind of EOS which will be returned.
> 
> ”task” = 0 → The total EOS will be returned.
> ”task” = 1 → The ionic EOS will be returned.
> ”task” = 2 → The electronic EOS will be returned.
> ”task” = 3 → The pure Thomas-Fermi EOS will be returned.
> Note that the total EOS is the sum of the electronic and the ionic
> EOS. The electronic EOS is the pure Thomas-Fermi EOS including
> all corrections - the bonding correction and the soft-sphere function.
> 
> Maxwell (INPUT): If set to 1, the EOS will be returned with Maxwell
> construction. If set to 0, the EOS will be calculated without Maxwell
> construction. Attention: ”Maxwell” = 1 is only allowed if the Maxwell
> construction has been initialized in FEOS Init Mat for the entity under
> consideration (”Maxwellﬂag” = 1).
> 
> Rho (INPUT): Density in g/cm3 for which the EOS will be calculated.
> 
> T (INPUT): Temperature in eV for which the EOS will be calculated.
> 
> belowbinodal (OUTPUT): If ”Maxwell” is set to 1, this integer will be 1
> if the density-temperature point lies inside the two-phase region, and,
> thus, the Maxwell construction is used.
> It will be 0 if the density-
> temperature point lies outside the two-phase region. If ”Maxwell” is
> 
> 36

### [FEOS-Package-Documentation2012.pdf] 第 37 页

> set to 0, ”belowbinodal” will be always 0, even if the temperature-
> density point lies inside the two-phase region.
> 
> p, e, s, f (OUTPUT): Pressure, speciﬁc internal energy, speciﬁc entropy,
> and speciﬁc Helmholtz free energy of the EOS deﬁned by ”task”.
> 
> q (OUTPUT): Array of size ”numofelements” containing the charge states
> for every element of the material. Note that the charge states are only
> calculated, if ”task” is not equal to 1.
> 
> qtot (OUTPUT): Charge state of one ”molecule”. Note that ”qtot” is only
> calculated, if ”task” is not equal to 1. To get the mean charge state
> of a mixture, divide ”qtot” by ”Xtot” (see FEOS Get Mat Par).
> 
> Always remember: The total pressure in the FEOS model is set to 0 for a
> given reference point ρo and To. The speciﬁc internal energy and speciﬁc
> Helmholtz free energy are shifted by an oﬀset such that both become 0 for
> each component (total EOS, electronic EOS, ionic EOS, and pure Thomas-
> Fermi EOS) at ρo and To. The ionic and electronic oﬀsets can be retrieved
> out of the library for each material entity with FEOS Get Energy Oﬀsets.
> 
> If the EOS is calculated with a Maxwell construction, the charge states and
> all the quantities from the electronic, ionic, and pure Thomas-Fermi EOS
> become physically meaningless inside the two-phase region.
> 
> —————————————————————————————————
> 
> void FEOS Delete Mat( int entity )
> 
> FEOS DELETE MAT( entity )
> 
> integer(4) :: entity
> 
> entity (INPUT): Deﬁnes the material entity which shall be deleted.
> 
> This routine can be used if a given entity shall be deleted during the runtime
> in order to initialize the same number afterwards again with FEOS Mat Init
> with a diﬀerent material or diﬀerent conditions.
> 
> —————————————————————————————————
> 
> void FEOS Get Calc Limits( double* Tzero, double* Rhozero )
> 
> 37

### [FEOS-Package-Documentation2012.pdf] 第 38 页

> FEOS GET CALC LIMITS( Tzero, Rhozero )
> 
> real(8) :: Tzero, Rhozero
> 
> Tzero (OUTPUT): Lower temperature ﬂoor of the library.
> 
> Rhozero (OUTPUT): Lower density ﬂoor of the library.
> 
> If one calls any interface routine for a density and/or a temperature below
> these limits, the library will set the density and/or the temperature to these
> limits.
> 
> —————————————————————————————————
> 
> void FEOS Get Mat Par( int entity, double* A, double* Z, double* X,
> double* Atot, double* Ztot, double* Xtot, double* Tref,
> double* Rhoref, double* BulkModref, int* SESAMEnumber )
> 
> FEOS GET MAT PAR( entity, A, Z, X, Atot, Ztot, Xtot, Tref, Rhoref,
> 
> BulkModref, SESAMEnumber )
> 
> integer(4) :: entity, SESAMEnumber
> 
> real(8) :: A(numofelements), Z(numofelements), X(numofelements),
> 
> Atot, Ztot, Xtot, Tref, Rhoref, BulkModref
> 
> entity (INPUT): Deﬁnes the material entity for which the material param-
> 
> eters will be returned.
> 
> A (OUTPUT): Array of size ”numofelements” containing the atomic weights
> 
> of all elements.
> 
> Z (OUTPUT): Array of size ”numofelements” containing the atomic numbers
> 
> of all elements.
> 
> X (OUTPUT): Array of size ”numofelements” containing the number of
> 
> atoms of all elements within one ”molecule”.
> 
> Atot (OUTPUT): Atomic weight of one ”molecule”. To get the mean atomic
> 
> weight of a mixture, ”Atot” must be divided by ”Xtot”.
> 
> Ztot (OUTPUT): Atomic number of one ”molecule”. To get the mean
> atomic number of a mixture, ”Ztot” must be divided by ”Xtot”.
> 
> 38

### [FEOS-Package-Documentation2012.pdf] 第 39 页

> Xtot (OUTPUT): Number of atoms within one ”molecule”.
> 
> Tref, Rhoref (OUTPUT): Reference temperature and density for which the
> 
> total pressure is set to zero.
> 
> BulkModref (OUTPUT): Reference bulk modulus at reference density and
> 
> reference temperature.
> 
> This routine returns all the basic material parameters from the material
> parameter database.
> 
> —————————————————————————————————
> 
> void FEOS Get Crit Point( int entity, double* T, double* Rho,
> 
> double* P, double* H, double* S, double* Z )
> 
> FEOS GET CRIT POINT( entity, T, Rho, P, H, S, Z )
> 
> integer(4) :: entity
> 
> real(8) :: T, Rho, P, H, S, Z
> 
> entity (INPUT): Deﬁnes the material entity for which the critical point
> 
> parameters will be returned.
> 
> T (OUTPUT): Critical temperature.
> 
> Rho (OUTPUT): Critical density.
> 
> P (OUTPUT): Critical pressure.
> 
> H (OUTPUT): Critical speciﬁc enthalpy.
> 
> S (OUTPUT): Critical speciﬁc entropy.
> 
> Z (OUTPUT): Critical compressibility factor.
> 
> This routine returns the location of the critical point. Attention: This data is
> only available if the Maxwell construction was initialized in FEOS Init Mat
> for the entity under consideration (”Maxwellﬂag” = 1).
> 
> —————————————————————————————————
> 
> void FEOS Get SoftSphere Par( int entity, double* Ecoh, double* softsp n,
> 
> 39

### [FEOS-Package-Documentation2012.pdf] 第 40 页

> double* softsp m, double* softsp A, double* softsp B )
> 
> FEOS GET SOFTSPHERE PAR( entity, Ecoh, softsp n, softsp m, softsp A,
> 
> softsp B )
> 
> integer(4) :: entity
> 
> real(8) :: Ecoh, softsp n, softsp m, softsp A, softsp B
> 
> entity (INPUT): Deﬁnes the material entity for which the soft-sphere pa-
> 
> rameters will be returned.
> 
> Ecoh (OUTPUT): Cohesive energy in erg/g.
> 
> softsp n (OUTPUT): Parameter n in soft-sphere function.
> 
> softsp m (OUTPUT): Parameter m in soft-sphere function.
> 
> softsp A (OUTPUT): Parameter A in soft-sphere function.
> 
> softsp B (OUTPUT): Parameter B in soft-sphere function.
> 
> This routine returns the parameters which are used in and calculated for the
> soft-sphere function. Attention: This data is only available if the soft-sphere
> function was initialized in FEOS Init Mat for the entity under consideration
> (”softsphereﬂag” = 1).
> 
> —————————————————————————————————
> 
> void FEOS Get Energy Oﬀsets( int entity, double* ElectronOﬀs,
> 
> double* IonOﬀs )
> 
> FEOS GET ENERGY OFFSETS( entity, ElectronOﬀs, IonOﬀs )
> 
> integer(4) :: entity
> 
> real(8) :: ElectronOﬀs, IonOﬀs
> 
> entity (INPUT): Deﬁnes the material entity for which the energy oﬀsets will
> 
> be returned.
> 
> ElectronOﬀs (OUTPUT): Energy oﬀset of the electronic part of the EOS.
> 
> IonOﬀs (OUTPUT): Energy oﬀset of the ionic part of the EOS.
> 
> 40

### [FEOS-Package-Documentation2012.pdf] 第 41 页

> This routine returns the speciﬁc energy and Helmholtz free energy oﬀsets of
> the electronic and the ionic part of the EOS. These oﬀsets assure that the
> energies are zero at the reference point ρo and To.
> 
> —————————————————————————————————
> 
> void FEOS Get Binodal( int entity, double* T, double* P, double* Rholiq,
> 
> double* Rhovap, double* Pliq, double* Pvap, double* Gliq,
> double* Gvap, double* Hliq, double* Hvap, double* Zliq,
> double* Zvap, double* Tboil )
> 
> FEOS GET BINODAL( entity, T, P, Rholiq, Rhovap, Pliq, Pvap, Gliq,
> 
> Gvap, Hliq, Hvap, Zliq, Zvap, Tboil )
> 
> integer(4) :: entity
> 
> real(8) :: T(numofMaxwelliso), P(numofMaxwelliso), Rholiq(numofMaxwelliso),
> 
> Rhovap(numofMaxwelliso), Pliq(numofMaxwelliso),
> Pvap(numofMaxwelliso), Gliq(numofMaxwelliso),
> Gvap(numofMaxwelliso), Hliq(numofMaxwelliso),
> Hvap(numofMaxwelliso), Zliq(numofMaxwelliso),
> Zvap(numofMaxwelliso), Tboil
> 
> entity (INPUT): Deﬁnes the material entity for which the binodal will be
> 
> returned.
> 
> T (OUTPUT): Array of size ”numofMaxwelliso” which contains all the tem-
> 
> peratures for which the Maxwell construction has been calculated.
> 
> P (OUTPUT): Array of size ”numofMaxwelliso” containing the calculated
> 
> saturated vapor pressures.
> 
> Rholiq (OUTPUT): Array of size ”numofMaxwelliso” containing the densi-
> 
> ties on the liquid branch of the binodal.
> 
> Rhovap (OUTPUT): Array of size ”numofMaxwelliso” containing the den-
> 
> sities on the vapor branch of the binodal.
> 
> Pliq (OUTPUT): Array of size ”numofMaxwelliso” containing the pressures
> on the liquid branch of the binodal. For a Maxwell construction of
> good quality this array should correspond to the pressures on the vapor
> branch of the binodal and to the saturated vapor pressures.
> 
> 41

### [FEOS-Package-Documentation2012.pdf] 第 42 页

> Pvap (OUTPUT): Array of size ”numofMaxwelliso” containing the pressures
> on the vapor branch of the binodal. For a Maxwell construction of good
> quality this array should correspond to the pressures on the liquid
> branch of the binodal and to the saturated vapor pressures.
> 
> Gliq (OUTPUT): Array of size ”numofMaxwelliso” containing the speciﬁc
> Gibbs free energies on the liquid branch of the binodal. For a Maxwell
> construction of good quality this array should correspond to the spe-
> ciﬁc Gibbs free energies on the vapor branch of the binodal.
> 
> Gvap (OUTPUT): Array of size ”numofMaxwelliso” containing the speciﬁc
> Gibbs free energies on the vapor branch of the binodal. For a Maxwell
> construction of good quality this array should correspond to the spe-
> ciﬁc Gibbs free energies on the liquid branch of the binodal.
> 
> Hliq (OUTPUT): Array of size ”numofMaxwelliso” containing the speciﬁc
> 
> enthalpies on the liquid branch of the binodal.
> 
> Hvap (OUTPUT): Array of size ”numofMaxwelliso” containing the speciﬁc
> 
> enthalpies on the vapor branch of the binodal.
> 
> Zliq (OUTPUT): Array of size ”numofMaxwelliso” containing the compress-
> 
> ibility factors on the liquid branch of the binodal.
> 
> Zvap (OUTPUT): Array of size ”numofMaxwelliso” containing the com-
> 
> pressibility factors on the vapor branch of the binodal.
> 
> Tboil (OUTPUT): Boiling temperature which corresponds to the tempera-
> 
> ture with saturated vapor pressure = 1 bar.
> 
> This routine returns several thermodynamic quantities on the liquid-vapor
> two-phase boundary (binodal). Attention: This data is only available if the
> Maxwell construction was initialized in FEOS Init Mat for the entity under
> consideration (”Maxwellﬂag” = 1).
> 
> —————————————————————————————————
> 
> void FEOS Get Spinodal( int entity, double* T, double* RhoMin,
> 
> double* RhoMax, double* PMin, double* PMax )
> 
> FEOS GET SPINODAL( entity, T, RhoMin, RhoMax, PMin, PMax )
> 
> integer(4) :: entity
> 
> 42

### [FEOS-Package-Documentation2012.pdf] 第 43 页

> real(8) :: T(numofMaxwelliso), RhoMin(numofMaxwelliso),
> 
> RhoMax(numofMaxwelliso), PMin(numofMaxwelliso),
> PMax(numofMaxwelliso)
> 
> entity (INPUT): Deﬁnes the material entity for which the spinodal will be
> 
> returned.
> 
> T (OUTPUT): Array of size ”numofMaxwelliso” which contains all the tem-
> 
> peratures for which the Maxwell construction has been calculated.
> 
> RhoMin (OUTPUT): Array of size ”numofMaxwelliso” which contains all
> 
> the densities of the van der Waals loop minima.
> 
> RhoMax (OUTPUT): Array of size ”numofMaxwelliso” which contains all
> 
> the densities of the van der Waals loop maxima.
> 
> PMin (OUTPUT): Array of size ”numofMaxwelliso” which contains all the
> 
> pressures of the van der Waals loop minima.
> 
> PMax (OUTPUT): Array of size ”numofMaxwelliso” which contains all the
> 
> pressures of the van der Waals loop maxima.
> 
> This routine returns the minimal and maximum pressures on the van der
> Waals loops of the isotherms the Maxwell construction has been calculated
> for. The corresponding curve is also called the spinodal. Attention: This data
> is only available if the Maxwell construction was initialized in FEOS Init Mat
> for the entity under consideration (”Maxwellﬂag” = 1).
> 
> —————————————————————————————————
> 
> void FEOS Get Pmin Pmax( int entity, double T, double* RhoMin,
> 
> double* RhoMax, double* PMin, double* PMax )
> 
> FEOS GET PMIN PMAX( entity, T, RhoMin, RhoMax, PMin, PMax )
> 
> integer(4) :: entity
> 
> real(8) :: T, RhoMin, RhoMax, PMin, PMax
> 
> entity (INPUT): Deﬁnes the material entity for which the minimum and
> 
> maximum pressures shall be calculated.
> 
> T (INPUT): Temperature for which the minimum and maximum pressures
> 
> 43

### [FEOS-Package-Documentation2012.pdf] 第 44 页

> will be calculated.
> 
> RhoMin (OUTPUT): Density of the van der Waals loop minima.
> 
> RhoMax (OUTPUT): Density of the van der Waals loop maxima.
> 
> PMin (OUTPUT): Pressure of the van der Waals loop minima.
> 
> PMax (OUTPUT): Pressure of the van der Waals loop maxima.
> 
> This routine allows to calculate the minimal and maximum pressures on the
> van der Waals loop for a given temperature. One has to assure that the input
> temperature lies below the critical point.
> 
> 44

### [FEOS-Package-Documentation2012.pdf] 第 45 页

> The FEOS Table Generation
> Tool
> 
> 13 Generation of EOS Tables
> 
> The FEOS table generation tool allows for a quick access to the FEOS library
> in order to generate a new equation-of-state table of one material. Figure 5
> gives an overview of the tool’s operational sequence.
> 
> The parameters which are required for a calculation must be set in a param-
> eter ﬁle (Section 4). Thus, in order to start a calculation one ﬁrst should
> make a copy of one of the parameter ﬁles given as examples in the direc-
> tory /EOS-Data. Then this ﬁle must be modiﬁed according to the desired
> properties and precision. Obligatory parameters are explained in Section 15.
> 
> The new parameter ﬁle must be located together with the executable ”feos”
> generated during the FEOS package installation (Section 3), the material
> parameter database ﬁle and the TF table ﬁle in one directory (usually in
> /EOS-Data). The executable is started with the parameter ﬁle name (with-
> out suﬃx ”.par”!) as argument. As an example, for the parameter ﬁle
> ”Aluminum.par” the command ”./feos Aluminum” must be used. The name
> of the parameter ﬁle will be also the name of the EOS table output ﬁles.
> 
> 13.1 Additional Features
> 
> Besides the calculation of EOS tables the tool allows for two other options:
> 
> 1. Single Point Information: If the EOS shall be calculated only for one
> given density-temperature point, then as an example for ρ = 2.0 g/cm3,
> T = 100 eV, and for the parameter ﬁle ”Aluminum.par” the user must
> execute the command ”./feos Aluminum 2.0e0 1.0e2”. The single point
> information will be printed out directly onto the console.
> 
> 2. User-deﬁned calculations: If executed in the table and not in the single
> point information modus, the code allows to call user-deﬁned routines
> for simple and short calculations. How and where these routines have
> to be deﬁned and called is explained in Section 17.
> 
> 45

### [FEOS-Package-Documentation2012.pdf] 第 46 页

> Figure 5: Operational sequence of the FEOS table generation tool.
> 
> 46

### [FEOS-Package-Documentation2012.pdf] 第 47 页

> 14 Source Code Structure
> 
> The FEOS tool’s source code consists of four ﬁles listed in Table 4.
> 
> FE-00 DEFINITS.H
> 
> Deﬁnitions used by the FEOS tool
> 
> FE-01 TABTOOLS.C
> 
> Routines for writing output ﬁles and for
> generating the density and temperature
> grids
> 
> FE-02 CALCULATIONS.C User-deﬁned routines for ”simple” calcula-
> tions using the FEOS library and/or the cal-
> culated tables
> 
> FE-03 MAIN.C
> 
> Main ﬁle of the FEOS tool
> 
> Table 4: Source ﬁles of the FEOS table generation tool.
> 
> The main routine of the tool is located in the source ﬁle ”FE-03 MAIN.C”.
> Users which want to use the FEOS library directly maybe interested in the
> main routine of the FEOS tool since it demonstrates the usage of nearly all
> of the library interface routines.
> 
> The ﬁle ”FE-01 TABTOOLS.C” contains the routines (”getPointDensity(...)”
> and ”makeRTPointArray(...)”) which are used to create the density-temperature
> grid. Furthermore, all the table output ﬁle routines (Section 16) are located
> there.
> 
> In the ﬁle ”FE-02 CALCULATIONS.C” the user can add own routines for
> (short and simple) calculations accessing the calculated table data or the
> library interface routines (Section 17).
> 
> 15
> 
> Input Parameters
> 
> The variables for a calculation with the FEOS table generation tool are
> located in the ﬁrst part (sections ”Computation-Settings” and ”Q-table”) of
> a parameter ﬁle (Section 4). Table 5 lists all necessary settings.
> 
> One should keep in mind that for any calculation, the physical parameters of
> the material must be present with a corresponding material number in the
> material parameter database (Section 10). Especially, if one wants to use the
> 
> 47

### [FEOS-Package-Documentation2012.pdf] 第 48 页

> Material-Number
> 
> Number of the material in the FEOS material
> parameter database
> 
> Maxwell Flag
> 
> Maxwell construction desired? (0: no, 1: yes)
> 
> SoftSphere Flag
> 
> Replace TF cold curve and bonding correction for
> ρ < ρo with soft-sphere function? (0: no, 1: yes)
> 
> UserCalculations Flag Perform user-deﬁned calculations? (0: no, 1: yes)
> 
> Rhonorm
> 
> Rhoratio x
> 
> Tnorm
> 
> Tratio x
> 
> Density norm in g/cm3
> 
> of
> 
> logarithmically equidistant dis-
> Number
> tributed density points in range Rhonorm·10x−1
> to Rhonorm·10x, x=-6...6; Attention: The lower
> density library limit should not be violated!
> 
> Temperature norm in eV
> 
> of
> 
> temperature
> 
> logarithmically
> 
> equidistant
> Number
> range
> in
> distributed
> Tnorm·10x−1
> to Tnorm·10x,
> x=-6...6; At-
> tention: The lower temperature library limit
> should not be violated!
> 
> points
> 
> Table 5: Settings in the parameter ﬁle for the FEOS table generation tool
> 
> (sections ”Computation-Settings” and ”Q-table”).
> 
> soft-sphere function, the corresponding parameters must be available.
> 
> To calculate a table with a Maxwell construction (Section 6.6) one should
> take care of the quality of the critical data calculation which depends strongly
> on the choice of the temperature grid density in the two-phase region. One
> should not be too thrifty spending mesh points. The Maxwell construction
> is set-up during the library material initialization stage with the same tem-
> peratures which are used later on to calculate the EOS table.
> 
> If the UserCalculations Flag is set to 1 the routines deﬁned in the ﬁle ”FE-
> 02 CALCULATIONS.C” will be performed (Section 17).
> 
> Finally, it is important to take care of the lower density and temperature ﬂoor
> of the library (Section 6.1) when deﬁning the density-temperature mesh.
> If points are deﬁned below these limits, the EOS will not be consistent.
> Nevertheless, the FEOS table generation tool automatically adds T = 0.0 eV
> and ρ = 0.0 g/cm3 to the density-temperature mesh.
> 
> 48

### [FEOS-Package-Documentation2012.pdf] 第 49 页

> 16 EOS Table Structure
> 
> 16.1 Qtable / CriticalDataTable Structures
> 
> The FEOS table generation tool stores the calculated EOS data and the crit-
> ical data information (thermodynamic quantities on the vaporization curve)
> in two separate structures. Therefore, these structures contain several arrays
> and are deﬁned in the ﬁle ”COMMON-00 DEFINITS.H”. The structure type
> ”Qtable” contains the arrays for the calculated EOS table. The name of the
> most important arrays and their index ranges are listed in Table 6.
> 
> NRho, NT, Nelements Number of densities, temperatures, and elements
> 
> in the material
> 
> A[k], Z[k], X[k]
> 
> Atot, Ztot, Xtot
> 
> T[j]
> 
> Rho[i]
> 
> Atomic weights, atomic numbers and number
> of atoms per ”molecule” for all elements in the
> material
> Summed-up values: Atot=(cid:80) X[k] A[k], ...
> 
> Temperatures
> 
> Densities
> 
> P[i][j] (Pe, Pi, PTF)
> 
> Pressures (separate for EOS components)
> 
> E[i][j] (Ee, Ei, ET)
> 
> Speciﬁc energies (separate for EOS components)
> 
> S[i][j] (Se, Si, STF)
> 
> Speciﬁc entropies (separate for EOS components)
> 
> F[i][j] (Fe, Fi, FTF)
> 
> Speciﬁc Helmholtz free energies (separate for
> EOS components)
> 
> Q[i][j][k]
> 
> Qtot[i][j]
> 
> Charge states for all elements in the material
> 
> Summed-up (not mean!) charge states for one
> ”molecule” (=(cid:80) X[k] Q[i][j][k])
> 
> Table 6: Most important variables and arrays stored in the ”Qtable” struc-
> ture. The indizes cover the following ranges: k=0..Nelements-1,
> j=0..NT-1, i=0..NRho-1.
> 
> The critical data information is stored in a structure type ”CriticalDataT-
> able”. This type is explained in Table 7.
> 
> 49

### [FEOS-Package-Documentation2012.pdf] 第 50 页

> Niso
> 
> Number of calculated isotherms below the critical
> point
> 
> Rhoc, Pc, Tc, Hc
> 
> Density, pressure, temperature, and speciﬁc en-
> thalpy at the critical point
> 
> Tiso[i]
> 
> Peq[i]
> 
> Temperatures
> 
> Saturated vapor pressures
> 
> Pmax[i], Pmin[i]
> 
> Minimum and maximum pressures on the van-der-
> Waals loops
> 
> Rhomax[i], Rhomin[i] Densities which correspond to the pressure minima
> 
> and maxima
> 
> Rhol[i], Rhov[i]
> 
> Hl[i], Hv[i]
> 
> Densities on the liquid and the vapor branch of the
> binodal
> 
> Speciﬁc enthalpies on the liquid and the vapor
> branch of the binodal
> 
> Table 7: Most important variables and arrays stored in the ”CriticalDataT-
> able” structure. The index i covers the following range: i=0..Niso-1.
> 
> 16.2 FEOS Format
> 
> The standard table output format of the FEOS table generation tool is a
> ASCII ﬁle with the extension ”.feos”. This type of ﬁle contains all informa-
> tion about the composition of the material, the calculation parameters and
> the calculated EOS table in the FEOS standard units (Section 5) itself. The
> format was designed to be used by the SHOWEOS table visualization tool
> and thus, it contains the whole set of calculated EOS data. In contrast to
> the SESAME format the ﬁle contains the complete EOS, all contributions
> to the EOS (electronic, ionic, Thomas-Fermi), and all thermodynamic func-
> tions (also the charge state). The FEOS format is controlled by the routine
> ”write FEOS format(...)” in the source ﬁle ”FE-01 TABTOOLS.C”.
> 
> 16.3 SESAME Formats
> 
> The FEOS table generation tool also writes tables in the SESAME-301, -
> 304, and -305 formats with ﬁle extensions ”.301”, ”.304”, and ”.305”. The
> 
> 50

### [FEOS-Package-Documentation2012.pdf] 第 51 页

> SESAME EOS library is a widely known set of equation-of-state tables for
> various materials, produced by the Los Alamons National Laboratory [19].
> SESAME-301 tables contain information about the total pressure, speciﬁc
> energy, and speciﬁc Helmholtz free energy of a given material as functions
> of density and temperature. SESAME-304/305 tables contain the same
> information, but for the electronic/ionic contributions. The tables in the
> SESAME database are based on experimental results as well as on theoret-
> ical models, sometimes on both. Additional information, for example about
> the vaporisation curve etc., is usually available in extra archive ﬁles (in case
> of FEOS this data is written to other formats).
> 
> A typical SESAME table is an ASCII-ﬁle consisting of several lines which
> contain four words each, where each word is a real number.
> Its ﬁrst line
> contains a material code, the solid density of the material described (in cgs
> units), the number of points on the density mesh (as real number), and the
> number of points on the temperature mesh (as real number), example:
> 
> 3717
> 
> 2.70000000e+00 1.92000000e+02 7.30000000e+01
> 
> The next few lines contain information about the density mesh (Rho[I],
> I=1...NI) and the temperature mesh (T[J], J=1...NJ):
> 
> 0.00000000e+00 2.70000000e-07 5.81697366e-07 2.70000000e-06 ...
> 
> The next lines contain all pressure isotherms, ((P[I,J], I=1..NI), J=1..NJ),
> then speciﬁc energy and speciﬁc Helmholtz free energy isotherms in the same
> manner as for the pressure.
> 
> The units used in the SESAME library are:
> 
> • Pressure: GPa
> 
> • Energy: MJ/kg
> 
> • Density: g/cm3
> 
> • Temperature: Kelvin
> 
> In ”FE-01 TABTOOLS.C” the routines ”write 301(304,305) format(...)” are
> responsible for the ﬁle output of the SESAME tables. Furthermore, the rou-
> tine ”write mexport format(...)” writes the SESAME mexport format (ex-
> tension ”.mexport”). The mexport format is a database ﬁle which usually
> 
> 51

### [FEOS-Package-Documentation2012.pdf] 第 52 页

> contains all the EOS tables (301,...) of all materials from the SESAME
> database. In the case of the FEOS table generation tool the mexport ﬁle of
> course contains only the 301, 304, and 305 tables of the calculated material.
> 
> 16.4 Other Output Formats
> 
> Besides the FEOS and the SESAME output formats, two other formats are
> written to ﬁles. The ﬁrst one, the txt format with ﬁle extension ”.data.txt”
> (routine ”write txt format” in ”FE-01 TABTOOLS.C”) contains pressure-
> energy isotherms as function of mass density. The second one, the Rostock
> format with ﬁle extension ”.cst” (routine ”write Rostock format(...)” in ”FE-
> 01 TABTOOLS.C”) contains pressure-charge state isotherms as function of
> particle density and mass density.
> 
> If a material is initialized with a Maxwell construction (Section 6.6), the
> FEOS table generation tool also writes out the information from the Criti-
> calDataTable structure (Section 16.1). The corresponding output ﬁle (rou-
> tine ”write criticaldata(...)” in ”FE-01 TABTOOLS.C”) has the extension
> ”.critical.dat”and contains the following information:
> 
> • Critical point data
> 
> • Boiling temperature
> 
> • Information about the accuracy of the Maxwell construction
> 
> • Binodal and spinodal in ρ-p-plane
> 
> • Binodal, spinodal, and diamener curve in T -ρ-plane
> 
> • Binodal in T -H-plane (speciﬁc enthalpy)
> 
> • Evaporation heat ∆H in T -∆H-plane
> 
> • Saturation curve in Arrhenius coordinates
> 
> • Compressibility factor on the binodal as function of temperature and
> 
> pressure
> 
> If the user wants to add a own table format to the FEOS table generation
> tool, a corresponding routine which may access the ”Qtable” and/or ”Crit-
> icalDataTable” structures (Section 16.1) must be added to the source ﬁle
> 
> 52

### [FEOS-Package-Documentation2012.pdf] 第 53 页

> ”FE-01 TABTOOLS.C” and the corresponding header ﬁle. The new routine
> must be called with appropriate arguments (together with the other out-
> put routines) at the end of step 4b in the main function in the source ﬁle
> ”FE-03 MAIN.C”.
> 
> 17 User-Deﬁned Calculations
> 
> The FEOS table generation tool provides an extra source ﬁle for the user
> reserved for routines which access the calculated EOS table and/or call the
> FEOS interface routines. The advantage of this special option is that the user
> can beneﬁt for ”simple” calculations from an existing infrastructure for the
> initialization of the FEOS library and of an EOS table. For more complicated
> calculations of course it may become necessary that the user writes a fully
> new program which calls the FEOS library from the beginning.
> 
> The user-deﬁned routines are all located and called by the routine ”User-
> Calculations(...)” in the source ﬁle ”FE-02 CALCULATIONS.C”. Four ar-
> guments maybe passed by the ”UserCalculations(...)” routine, nameley the
> entitynumber of the material (for the FEOS table generation tool normally
> always 1), the name of the parameter ﬁle, and the stored data in the ”Qtable”
> and ”CriticalDataTable” structures (Section 16.1).
> 
> If a new routine needs the Maxwell construction data, the user should make
> sure that it was calculated before by checking the integer ”Niso” in the ”Crit-
> icalDataTable” structure to be greater than zero.
> 
> 17.1
> 
> Isobaric Expansion Data
> 
> One (exemplary) application comes already with the delivery version of the
> FEOS package. The routine ”IsobaricExpansion(...)” can be used for the
> calculation of thermodynamic functions along the isobaric curve p = 0 of the
> metastable EOS (without Maxwell construction) up to the spinodal limit
> which means: up to that temperature for which the van-der-Waals loop does
> not cross p = 0 anymore. The minimum and maximum temperatures, as
> well as the number of linearly equidistant distributed temperature points are
> set at the beginning of the routine ”IsobaricExpansion(...)”. The following
> data is calculated along the isobaric curve and written to an output ﬁle with
> extension ”.isobaric.dat”:
> 
> 53

### [FEOS-Package-Documentation2012.pdf] 第 54 页

> • Temperatures T
> 
> • Densities ρ
> 
> • Pressures p (for checking accuracy only)
> 
> • Thermal expansion coeﬃcients α
> 
> • Speciﬁc enthalpies H
> 
> • Speciﬁc isobaric heat capacities Cp
> 
> This data, especially the expansion coeﬃcient, can be helpful for the adjust-
> ment of the soft-sphere function parameters (Section 6.7) of a new material
> entry in the material parameter database.
> 
> 54

### [FEOS-Package-Documentation2012.pdf] 第 55 页

> The SHOWEOS Table
> Visualization Tool
> 
> 18 Visualization of EOS Tables
> 
> SHOWEOS is a tool for calculating plots of the EOS tables generated with
> the FEOS table generation tool. The tool is designed for table ﬁles which
> are present in the FEOS format (Section 16.2) with extension ”.feos”. Al-
> ternatively, the SESAME ﬁle format (Section 16.3) with extensions ”.301”,
> ”.304”, and ”.305” can be loaded. The latter feature provides the option to
> visualize also tables from the SESAME database and to compare them with
> the corresponding FEOS tables.
> 
> Figure 6 shows the general operational sequence of the tool. In order to start
> a calculation one ﬁrst must ensure that the executable ”showeos” generated
> during the FEOS package installation (Section 3), the parameter ﬁle with
> 
> Figure 6: Operational sequence of the SHOWEOS table visualization tool.
> 
> 55

### [FEOS-Package-Documentation2012.pdf] 第 56 页

> extension ”.par” (Section 4), and the table ﬁle, which must have the same
> name as the parameter ﬁle, are located in the same directory (usually /EOS-
> Data). Usually, the same parameter ﬁle which was used for the generation of
> the table with the FEOS table generation tool contains also the parameters
> for SHOWEOS. Only if a table from the SESAME database shall be visual-
> ized, a new parameter ﬁle must be created. The name of the parameter ﬁle
> will be also the name of the output ﬁle(s).
> 
> The executable ”showeos” is started with two arguments. The ﬁrst argu-
> ment is the name of the parameter ﬁle (without suﬃx ”.par”!). The second
> argument is an integer number between 1 and 6 which deﬁnes the type of
> the calculation which will be done. As an example, for the parameter ﬁle
> ”Aluminum.par” and option number 3 one has to execute the command
> ”./showeos Aluminum 3”. Table 8 explains the meaning of the six available
> options. The corresponding procedures and settings in the parameter ﬁle are
> explained in Section 20. Options 1-3 are collected under the umbrella term
> ”Isocurves”.
> 
> 1 Calculate isotherms (lines of constant temperature)
> 
> 2 Calculate isochores (lines of constant density)
> 
> 3 Calculate isentropes (lines of constant speciﬁc entropy)
> 
> 4 Calculate mountain plot (three-dimensional plot of thermodynamic
> quantity as function of density / speciﬁc volume and temperature)
> 
> 5 Calculate Hugoniot curve [16]
> 
> 6 Print out single point information
> 
> Table 8: Calculational options provided by the SHOWEOS table visualiza-
> 
> tion tool.
> 
> Once the tool has been started, ﬁrst the general parameters (Section 20.1) are
> read from the parameter ﬁle, then the appropriate EOS table ﬁle is loaded,
> and ﬁnally the desired option is performed. For options 1-5 the information is
> printed out into an ASCII ﬁle which then again can be loaded by a plotting
> tool. Here, the user has to take care by himself/herself of the format of
> the ASCII ﬁle by modifying the routine which is responsible for the desired
> option. Finally, although SHOWEOS, like the other parts of the package,
> internaly uses the FEOS standard units, the units of the SHOWEOS input
> parameters and of the quantities written to the output ﬁle(s) can be changed
> and have to be speciﬁed in the parameter ﬁle (Section 20.1).
> 
> 56

### [FEOS-Package-Documentation2012.pdf] 第 57 页

> 19 Source Code Structure
> 
> The SHOWEOS tool’s source code consists of ﬁve ﬁles listed in Table 9.
> 
> SE-00 DEFINITS.H
> 
> Deﬁnitions for the output ﬁles of the
> SHOWEOS tool
> 
> SE-01 READTABLE.C
> 
> Routines for reading EOS table ﬁles
> 
> SE-02 INTERPOLTOOLS.C Routines for table interpolations
> 
> SE-03 SERVICES.C
> 
> SE-04 MAIN.C
> 
> ”Working” routines for isocurves, Hugo-
> niots, etc.
> 
> Main ﬁle and main routine of
> SHOWEOS tool
> 
> the
> 
> Table 9: Source ﬁles of the SHOWEOS table visualization tool.
> 
> The main routine of the tool is located in the source ﬁle ”SE-04 MAIN.C”.
> The ﬁle ”SE-01 READTABLE.C” contains the routines which are used to
> read and load the EOS tables. In the ﬁle ”SE-03 SERVICES.C” the ”work-
> ing” routines which are responsible for the diﬀerent options of the tool are
> located. In these routines the user must adjust the output ﬁle write state-
> ments to ﬁt the requirements of the used plotting tool.
> 
> 20
> 
> Input Parameters and Procedures
> 
> The variables for a calculation with the SHOWEOS table visualization tool
> are located in the second part of a parameter ﬁle (Section 4). The SHOWEOS
> parameters are separated into two categories: 1) the obligatory parameters
> which are used by all options of the tool and are explained in Section 20.1
> and 2) the facultative parameters which are only used if the corresponding
> option is performed (Sections 20.2, 20.3, 20.4, and 20.5).
> 
> 20.1 General Settings
> 
> In a parameter ﬁle three sections ”General”, ”Units”, and ”Rho-T-Mesh”
> contain parameters which are (partially) used by all options of the SHOWEOS
> 
> 57

### [FEOS-Package-Documentation2012.pdf] 第 58 页

> tool. The parameters of the ”General” and ”Units” sections are explained in
> Table 10.
> 
> File-Format Type of table ﬁle (1: FEOS format, 2: SESAME format)
> 
> EOS-Type
> 
> Type of EOS (1: total, 2: electronic, 3: ionic, 4: Thomas-
> Fermi)
> 
> Rho unit
> 
> Density unit (1.0 → g/cm3)
> 
> T unit
> 
> P unit
> 
> E unit
> 
> U unit
> 
> Temperature unit (1.0 → eV, 8.61753e-5 → K)
> 
> Pressure unit (1.0 → dyne/cm2, 1.0e12 → MBar)
> 
> Energy unit (1.0 → erg/g, 1.0e10 → MJ/kg)
> 
> Velocity unit (1.0 → cm/s, 1.0e5 → km/s)
> 
> Table 10: Settings in the parameter ﬁle for the SHOWEOS table visualiza-
> 
> tion tool (sections ”General” and ”Units”).
> 
> The parameter ”EOS-Type” controls whether the complete or the electronic
> / ionic / pure Thomas-Fermi contribution shall be loaded. While the FEOS
> formatted ﬁles (Section 16.2) contain all the required data, for the complete
> EOS as well as for the contributions, a SESAME table ﬁle does not. In this
> case the SHOWEOS tool automatically chooses the appropriate ﬁle exten-
> sion (”.301”, ”.304”, or ”.305”) depending on the ”EOS-Type” parameter.
> Note, that the option ”EOS-Type=4” is not available for SESAME tables.
> Furthermore, one should keep in mind that the SESAME table ﬁles which
> can be loaded contain no information about the charge state.
> 
> The unit parameters are set in such a way that the value corresponds to a
> multiplication factor of the FEOS standard units (Section 5). All input has
> to be deﬁned and all output quantities are printed-out in the deﬁned units.
> The units of the speciﬁc Helmholtz free energy, the speciﬁc entropy, and the
> speciﬁc volume are determined from the other unit settings. The unit of the
> charge state is ﬁxed in terms of multiples of the unit electron charge.
> 
> Table 11 lists all parameters of the ”Rho-T-Mesh” section. This section
> is important for all SHOWEOS options, except for the single point infor-
> mation and the Hugoniot option. The corresponding parameters deﬁne the
> strucuture of the density-temperature grid. The user can choose whether the
> original densities and temperatures from the table ﬁle shall be used, or a new
> mesh with linearly or logarithmically equidistant distributed points shall be
> created.
> 
> 58

### [FEOS-Package-Documentation2012.pdf] 第 59 页

> Rhomin, Tmin
> 
> Rhomax, Tmax
> 
> Minimum density / temperature (in units deﬁned
> in section ”Units”)
> 
> Maximum density / temperature (in units deﬁned
> in section ”Units”)
> 
> Rhooriginal, Toriginal Use only original tabulated densities / tempera-
> 
> tures? (0: no, 1: yes)
> 
> Rhonumber, Tnumber Number of densities / temperatures if Rhoorigi-
> nal / Toriginal is set to 0
> 
> Rholog, Tlog
> 
> Rhoﬁrst, Tﬁrst
> 
> Kind of distribution if Rhooriginal / Toriginal is
> set to 0 (0: linear, 1: logarithmical)
> 
> Only for isotherms, isochores, or Mountain plots:
> Print out lowest density / temperature of table?
> (0: no, 1: yes)
> 
> Table 11: Settings in the parameter ﬁle for the SHOWEOS table visualiza-
> 
> tion tool (section ”Rho-T-Mesh”).
> 
> 20.2 Isocurves
> 
> For the ﬁrst three options of the SHOWEOS table visualization tool (calcula-
> tion of isotherms, isochores, or isentropes) the parameters from the parameter
> ﬁle section ”Isocurves” are read. The corresponding settings are explained
> in Table 12.
> 
> Xquantity, Yquantity Quantity which is printed out on the x-axis / y-
> axis (1,2,3,...,8 → Table 13)
> 
> Xelement, Yelement
> 
> For charge state of mixtures (Xquantity=8 /
> Yquantity=8): element number or 0 for summed-
> up value
> 
> Table 12: Settings in the parameter ﬁle for the SHOWEOS table visualiza-
> 
> tion tool (section ”Isocurves”).
> 
> The user must choose which quantities shall be plotted on the x- and on
> the y-axis. Therefore, the diﬀerent thermodynamic quantities correspond to
> number between 1 and 8 (Table 13). If the charge state shall be plotted for
> a mixture, the user must decide whether the charge state shall be plotted
> for a participating element or summed up for a ”molecule” of the mixture.
> 
> 59

### [FEOS-Package-Documentation2012.pdf] 第 60 页

> Attention: The charge state is only available for the FEOS table format and
> not for the supported SESAME table ﬁles.
> 
> 1 Density
> 
> 2 Speciﬁc volume
> 
> 3 Temperature
> 
> 4 Pressure
> 
> 5 Speciﬁc internal energy
> 
> 6 Speciﬁc Helmholtz free energy
> 
> 7 Speciﬁc entropy
> 
> 8 Summed-up or single-element charge state
> 
> Table 13: Possible quantity choices.
> 
> The output ﬁle will be an ASCII ﬁle with the same name as the parameter
> ﬁle. The ﬁrst part of the ﬁle extension is composed of the names of the
> plotted quantities on the x- and on the y-axis. The second and last part
> of the extension denotes the type of isocurve: ”.ist” for isotherms, ”.isc” for
> isochores, and ”.ise” for isentropes. In the delivery version of the SHOWEOS
> tool successive isocurves inside the ASCII ﬁle are divided by an ”&” sign.
> Each isocurve contains a headline with information of the plotted quantities
> and units. This sort of ﬁle can be graphically visualized with the Unix tool
> xmgrace, for example.
> 
> For isotherms, the plotted temperatures are given by the temperature grid
> which was set-up in the section ”Rho-T-Mesh” (Section 20.1). For isochores,
> the plotted densities are given by the density grid. For isentropes, the used
> entropies are calculated for the lowest density and for all temperatures of the
> density-temperature grid.
> 
> 20.3 Mountain Plots
> 
> For showing total phase planes which means some quantity (parameter ”Quan-
> tity”) as a function of density or speciﬁc volume (parameter ”Xquantity”)
> and temperature in a three-dimensional diagram, one has to make speciﬁ-
> cations in the parameter ﬁle section ”Mountain” (Table 14). The densities
> and temperatures are given by the density-temperature grid (Section 20.1).
> 
> 60

### [FEOS-Package-Documentation2012.pdf] 第 61 页

> The output ﬁle will be an ASCII ﬁle with the same name as the parameter
> ﬁle. The ﬁle ﬁrst contains the density and temperature grid and then a list
> of isochores of the desired quantity. The ﬁrst part of the ﬁle extension is
> composed of the names of the plotted quantities on the x-, y-, and z-axis.
> The second and last part of the extension is ”.mnt”.
> 
> Xquantity Quantity which is printed out on the x-axis (1: density, 2:
> 
> speciﬁc volume)
> 
> Quantity Mountain quantity as function of Xquantity and temperature
> 
> (4,5,6,7,8 → Table 13)
> 
> Element
> 
> For charge state of mixtures (Quantity=8): element number
> or 0 for summed-up value
> 
> Table 14: Settings in the parameter ﬁle for the SHOWEOS table visualiza-
> 
> tion tool (section ”Mountain”).
> 
> 20.4 Hugoniots
> 
> For computing a Hugoniot curve [16] the corresponding settings in the pa-
> rameter ﬁle section ”Hugoniot” must be speciﬁed (Table 15). The user must
> set the initial density and temperature where the Hugoniot curve calcula-
> tion shall start. Furthermore, a maximum pressure must be set to limit the
> calculation. The stepsizes for the calculation and for the print-out can be
> changed in the source code header ﬁle ”SE-03 SERVICES.H”. The output
> ﬁle will be an ASCII ﬁle with the same name as the parameter ﬁle and ex-
> tension ”.hug”. The ﬁle contains the density or speciﬁc volume (parameter
> ”Xquantity”), the temperature, the pressure, the speciﬁc internal energy, the
> shock wave velocity, and the particle velocity behind the shock wave.
> 
> Rho0
> 
> T0
> 
> Initial density (in units deﬁned in section ”Units”)
> 
> Initial temperature (in units deﬁned in section ”Units”)
> 
> Pmax
> 
> Maximum pressure (in units deﬁned in section ”Units”)
> 
> Xquantity Quantity which is printed out on the ”x-axis” (1: density, 2:
> 
> speciﬁc volume)
> 
> Table 15: Settings in the parameter ﬁle for the SHOWEOS table visualiza-
> 
> tion tool (section ”Hugoniot”).
> 
> 61

### [FEOS-Package-Documentation2012.pdf] 第 62 页

> 20.5 Single Point Information
> 
> A single point information for a given density and temperature can be printed
> out with the option 6 of the SHOWEOS table visualization tool. The density
> and the temperature in the units deﬁned in the parameter ﬁle section ”Units”
> must be passed as a third and a fourth argument in the command line call
> of SHOWEOS. As an example, for the parameter ﬁle ”Aluminum.par”, the
> value 1.0 for the temperature and density units in the parameter ﬁle, den-
> sity 0.3 g/cm3, and temperature 10 eV one has to execute the command
> ”./showeos Aluminum 6 0.3 1.e2”.
> 
> 62

### [FEOS-Package-Documentation2012.pdf] 第 63 页

> References
> 
> [1] A. Kemp and J. Meyer-ter Vehn. An equation of state code for hot
> dense matter, based on the QEOS description. Nucl. Instrum. Methods
> A, 415:674–676, 1998. 2, 8
> 
> [2] R. M. More, K. H. Warren, D. A. Young, and G. B. Zimmerman. A
> new quotidian equation of state (QEOS) for hot dense matter. Physics
> of Fluids, 31:3059, 1988. 6, 8, 11, 15, 19
> 
> [3] A. Kemp and J. Meyer-ter Vehn. Das Zustandsgleichungs-Modell QEOS
> f¨ur heisse, dichte Materie. Technical Report 229, Max-Planck-Institut
> f¨ur Quantenoptik, 1998. 6, 15, 19
> 
> [4] S. Faik, M. M. Basko, An. Tauschwitz, I. Iosilevskiy, and J. A. Maruhn.
> Dynamics of volumetrically heated matter passing through the liquid-
> vapor metastable states. High Energy Density Physics, 8(4):349–359,
> 2012. 8, 20
> 
> [5] D. A. Young and E. M. Corey. A new global equation of state model for
> hot, dense matter. Journal of Applied Physics, 78(6):3748, 1995. 11, 22
> 
> [6] L. D. Landau and E. M. Lifshitz. Statistical Physics. Butterworth
> 
> Heinemann, 3 edition, 1996. 12, 20
> 
> [7] L. H. Thomas. The calculation of atomic ﬁelds. Mathematical Proceed-
> ings of the Cambridge Philosophical Society, 23(5):542–548, 1927. 12
> 
> [8] E. Fermi. Eine statistische Methode zur Bestimmung einiger Eigen-
> schaften des Atoms und ihre Anwendung auf die Theorie des periodis-
> chen Systems der Elemente. Zeitschrift f¨ur Physik, 48:73–79, 1928. 12
> 
> [9] R. Feynman, N. Metropolis, and E. Teller. Equations of state of ele-
> ments based on the generalized Thomas-Fermi theory. Physical Review,
> 75:1561, 1949. 12, 13
> 
> [10] L. D. Landau and E. M. Lifshitz. Quantum Mechanics: Non Relativistic
> 
> Theory. Butterworth Heinemann, 3 edition, 1981. 13
> 
> [11] M. Brachmann. Thermodynamic functions on the generalized Thomas-
> 
> Fermi theory. Physical Review, 84:1263, 1951. 14
> 
> [12] S. Eliezer, A. Ghatak, and H. Hora. Fundamentals of Equations of State.
> 
> World Scientiﬁc Pub Co, 1 edition, 2002. 15, 17
> 
> 63

### [FEOS-Package-Documentation2012.pdf] 第 64 页

> [13] D. A. Kirzhnits, Y. E. Lozovik, and G. V. Shpatakovskaya. Statistical
> model of matter. Soviet Physics Uspekhi, 18(9):649–672, 1975. 15
> 
> [14] B.-G. Englert.
> 
> Semiclassical Theory of Atoms (Lecture Notes in
> 
> Physics). Springer, Berlin, 1 edition, 1988. 15
> 
> [15] W. Zittel. Elektronische Struktur hochkomprimierter Materie. Technical
> 
> Report 111, Max-Planck-Institut f¨ur Quantenoptik, 1986. 15
> 
> [16] Ya. B. Zeldovich and Yu. P. Raizer. Physics of Shock-Waves and High-
> Temperature Hydrodynamic Phenomena. Dover Pubn Inc, illustrated
> edition, 2002. 16, 56, 61
> 
> [17] J. F. Barnes. Statistical Atom Theory and the Equation of State of
> 
> Solids. Physical Review, 153(1):269–275, 1967. 16
> 
> [18] M. Ross. Generalized Lindemann Melting Law. Physical Review,
> 
> 184(1):233–242, 1969. 17
> 
> [19] T. Group. SESAME Report on the Los Alamos Equation of State Li-
> brary. Technical Report LALP-83-4, Los Alamos National Laboratory,
> 1983. 51
> 
> 64

## doc/FEOS/FEOS-Package-Documentation2016.pdf (611826 B)

<!-- 提取说明: 共 64 页（pdfminer 解析出 65 段） -->

### [FEOS-Package-Documentation2016.pdf] 第 1 页

> FEOS
> 
> A new equation-of-state code for hot dense matter
> 
> Package Documentation
> 
> Version: 16.7 (July 2016)
> 
> Dr. Steﬀen Faik
> Institute for Applied Physics
> Goethe University Frankfurt am Main, Germany
> 
> MPQeos Version 2.0 (09/99):
> 
> A.J. Kemp and J. Meyer-ter-Vehn
> Max-Planck Institute for Quantum Optics
> Garching, Germany

### [FEOS-Package-Documentation2016.pdf] 第 2 页

> Foreword / Contact
> 
> First of all I would like to thank Dr Anna Tauschwitz, Prof Dr Joachim
> Maruhn (both Goethe University Frankfurt am Main & GSI Darmstadt),
> Prof Dr Igor Iosilevskiy (Joint Institute for High Temperatures Moscow &
> GSI Darmstadt), and Prof Dr Mikhail Basko (Institute for Theoretical and
> Experimental Physics Moscow & GSI Darmstadt) for very helpful and con-
> structive discussions. The whole work was supported by the Extreme Mat-
> ter Institute EMMI and the Bundesministerium f¨ur Bildung und Forschung
> BMBF (Project 06FY9085).
> 
> This present new revised version of the original code MPQeos by A. Kemp
> [1] was built within the last four years, partially within the framework of
> my diploma thesis at the university of Frankfurt, Germany. For this reason,
> the new package is called ”Frankfurt equation-of-state (FEOS)”.
> It was
> mainly built for usage at GSI – Helmholtz Center for Heavy Ion Research in
> Darmstadt, but is already used by several institutions and working groups
> around the world.
> 
> At this point I want to emphasize that some parts of this documentation are
> based on the original documentation of MPQeos (version 2.0) by A. Kemp
> and J. Meyer-ter-Vehn. I updated these parts concerning the new features
> of FEOS. So, the reader does not have to read the original documentation of
> MPQeos in order to understand the new manual.
> 
> Address of the author of FEOS
> 
> Dr. Steﬀen Faik
> Nikolausstr. 10
> 65936 Frankfurt am Main
> 
> Phone: +49 (0)69 30858211
> steﬀen@faik.net
> http://physik.faik.net/

### [FEOS-Package-Documentation2016.pdf] 第 3 页

> Contents
> 
> The FEOS Package
> 
> 1 Introduction / Overview
> 
> 1.1 Citation Rules . . . . . . . . . . . . . . . . . . . . . . . . . . .
> 
> 2 Package File Structure
> 
> 3 Installation
> 
> 4 Parameter & Database File Structure
> 
> 5 Package Standard Units
> 
> The FEOS Library
> 
> 6 The Physics behind the QEOS Model
> 
> 6
> 
> 6
> 
> 8
> 
> 8
> 
> 9
> 
> 10
> 
> 10
> 
> 11
> 
> 11
> 
> 6.1 General Facts . . . . . . . . . . . . . . . . . . . . . . . . . . . 11
> 
> 6.2 Electronic EOS: TF Model . . . . . . . . . . . . . . . . . . . . 12
> 
> 6.3 Semiempirical Bonding Correction . . . . . . . . . . . . . . . . 15
> 
> 6.4
> 
> Ionic EOS: Cowan Model . . . . . . . . . . . . . . . . . . . . . 16
> 
> 6.5 Homogeneous Mixtures of Elements . . . . . . . . . . . . . . . 19
> 
> 6.6 Liquid-Vapor Phase Coexistence . . . . . . . . . . . . . . . . . 20
> 
> 6.7 Cold Curve Improvement . . . . . . . . . . . . . . . . . . . . . 22
> 
> 7 Technical Design of the Library
> 
> 23
> 
> 7.1 Material Initialization Stage . . . . . . . . . . . . . . . . . . . 23
> 
> 3

### [FEOS-Package-Documentation2016.pdf] 第 4 页

> 8 Information provided by the Library
> 
> 9 Source Code Structure
> 
> 10 Material Parameter Database
> 
> 11 Implementation of the Library
> 
> 12 Interface Routines
> 
> 27
> 
> 27
> 
> 29
> 
> 29
> 
> 30
> 
> 12.1 Obligatory Interface Routines . . . . . . . . . . . . . . . . . . 31
> 
> 12.2 Facultative Interface Routines . . . . . . . . . . . . . . . . . . 34
> 
> The FEOS Table Generation Tool
> 
> 13 Generation of EOS Tables
> 
> 45
> 
> 45
> 
> 13.1 Additional Features . . . . . . . . . . . . . . . . . . . . . . . . 45
> 
> 14 Source Code Structure
> 
> 15 Input Parameters
> 
> 16 EOS Table Structure
> 
> 47
> 
> 47
> 
> 49
> 
> 16.1 Qtable / CriticalDataTable Structures
> 
> . . . . . . . . . . . . . 49
> 
> 16.2 FEOS Format . . . . . . . . . . . . . . . . . . . . . . . . . . . 50
> 
> 16.3 SESAME Formats
> 
> . . . . . . . . . . . . . . . . . . . . . . . . 50
> 
> 16.4 Other Output Formats . . . . . . . . . . . . . . . . . . . . . . 52
> 
> 17 User-Deﬁned Calculations
> 
> 53
> 
> 17.1 Isobaric Expansion Data . . . . . . . . . . . . . . . . . . . . . 53
> 
> 4

### [FEOS-Package-Documentation2016.pdf] 第 5 页

> The SHOWEOS Table Visualization Tool
> 
> 18 Visualization of EOS Tables
> 
> 19 Source Code Structure
> 
> 20 Input Parameters and Procedures
> 
> 55
> 
> 55
> 
> 57
> 
> 57
> 
> 20.1 General Settings . . . . . . . . . . . . . . . . . . . . . . . . . . 57
> 
> 20.2 Isocurves . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 59
> 
> 20.3 Mountain Plots . . . . . . . . . . . . . . . . . . . . . . . . . . 60
> 
> 20.4 Hugoniots . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 61
> 
> 20.5 Single Point Information . . . . . . . . . . . . . . . . . . . . . 62
> 
> References
> 
> 63
> 
> 5

### [FEOS-Package-Documentation2016.pdf] 第 6 页

> The FEOS Package
> 
> 1
> 
> Introduction / Overview
> 
> The FEOS package is a C++ computer code which consists of three parts:
> 
> 1. the FEOS library (ﬁle ”libfeos.a”),
> 
> 2. the FEOS table generation tool (executable ”feos”),
> 
> 3. the SHOWEOS table visualization tool (executable ”showeos”).
> 
> The main part of the new package, the FEOS library, provides all the routines
> which are needed to calculate the equation-of-state (EOS) of an, in principle,
> arbitrary material as a function of density and temperature. The underlying
> physical model is the ”quotidian equation-of-state model (QEOS)”, described
> further in Ref. [2]. The background of the original code MPQeos, together
> with some applications, is described in a correspondig MPQ Report 229 [3].
> Having outsourced the main EOS routines into a static library an implemen-
> tation of the EOS directly into the user’s code was made possible. For this
> purpose the library provides several interfaces, for codes written in C, C++,
> or Fortran. Furthermore, a ﬁle containing a database of material parameters
> which is accessed by the FEOS library is intended to be exchanged between
> a growing community of FEOS users.
> 
> The second part, the FEOS table generation tool makes use of the FEOS
> library and can be used to create EOS table ﬁles as a function of density
> and temperature. Several output formats, like the SESAME format, already
> come with the package, but the user is free to write her/his own output
> routines. Also, the FEOS table generation tool provides the possibility to
> perform ”simple” user-deﬁned calculations which require an EOS.
> 
> The SHOWEOS table visualization tool can be used to visualize the FEOS
> (or SESAME) table ﬁles, i.e. to make plots of isotherms, isochores, isen-
> tropes, Hugoniot curves, or to show three-dimensional phase planes.
> 
> Figure 1 gives an overview of the whole package’s structure. The documen-
> tation explains in detail how to use the three diﬀerent parts of the package
> and gives hints how and where to change the source code in order to cus-
> tomize it for the user’s own needs. The part which deals with the FEOS
> 
> 6

### [FEOS-Package-Documentation2016.pdf] 第 7 页

> Figure 1: Outline of the FEOS package.
> 
> 7

### [FEOS-Package-Documentation2016.pdf] 第 8 页

> library includes also a short description of the physical model and the im-
> provements and changes applied to the original MPQeos code. Furthermore,
> the library interface routines and their implementation into any user’s code
> are explained in detail.
> 
> 1.1 Citation Rules
> 
> Whenever the FEOS package or parts of it are used the most recent pub-
> lication in the journal ”Computer Physics Communications” or Reference
> [4], which contains a short section about the package, must be cited. The
> user can ﬁnd links to all publications on the webpage http://physik.faik.net.
> Also, since the package relies on the QEOS model and on the MPQeos code,
> one should always cite the original publications (Ref. [1, 2]).
> 
> 2 Package File Structure
> 
> The FEOS package comes in a packed ﬁle ”FEOS 16.7 20160729.zip”. Under
> Unix this ﬁle can be unzipped with the command ”unzip”. After having
> unzipped the ﬁle, three directories will be present:
> 
> 1. /Code → contains all source ﬁles of the package,
> 
> 2. /Documents → documentation and QEOS/MPQeos pdf ﬁles,
> 
> 3. /EOS-Data → working directory for table generation and visualization.
> 
> The directory /Code contains all the source ﬁles of the package. These
> ﬁles are subdivided into four classes. The ﬁles which begin with the preﬁx
> ”COMMON-” (Table 1) contain the routines which are used by all three
> parts of the FEOS package. The ﬁles which begin with the preﬁx ”LIB-”
> contain all routines of the FEOS library. They are explained in detail in the
> library part of the documentation. Furthermore, the library interface header
> ﬁle ”libfeos.h” also belongs to the FEOS library. The ﬁles which begin with
> the preﬁxes ”FE-” / ”SE-” contain the routines of the FEOS table generation
> / FEOS table visualization tools. Their content is explained in detail in the
> corresponding parts of the documentation. Finally, the Makeﬁle contains all
> commands for the compilation of the code (Section 3).
> 
> 8

### [FEOS-Package-Documentation2016.pdf] 第 9 页

> COMMON-00 DEFINITS.H Conversion factors, physical and mathe-
> matical constants, and EOS table storage
> structures
> 
> COMMON-01 UTILITIES.C Routines
> 
> for memory allocation and
> 
> deallocation
> 
> COMMON-02 READFILE.C Routines for reading ASCII ﬁles
> 
> Table 1: Common source ﬁles used by all parts of the FEOS package.
> 
> The directory /Documents contains the documentations of the FEOS package
> and several pdf ﬁles about QEOS and MPQeos.
> 
> In the directory /EOS-Data all the calculations with the table generation
> and the table visualization tools, whose exectuables will be present after in-
> stallation, are supposed to be done. The directory contains the precalculated
> Thomas-Fermi table ﬁle for hydrogen and the material parameter database
> ﬁle. These two ﬁles are both read by the FEOS library. The two examplary
> parameter ﬁles for aluminum (Al) and fused silica (SiO2) contain all the nec-
> essary settings for the table generation and table visualization tools. The
> general structure of the material parameter database and the tools’ param-
> eter ﬁles will be explained in Section 4. Details on the settings inside these
> ﬁles are given in the corresponding sections of the documentation.
> 
> 3
> 
> Installation
> 
> The Makeﬁle contains all information for the compilation of the source code.
> The whole source code inside the directory /Code is compiled under Unix
> with the command ”make all”. By default, the GNU C++ compiler g++ is
> used. After FEOS has been installed, the FEOS library ﬁle ”libfeos.a” will
> be present. Also the executables ”feos” and ”showeos” of the package tools
> will be there and automatically copied to the tools’ working directory /EOS-
> Data. In order to reset the package to the uncompiled status, the command
> ”make clean” can be used and all executables and object ﬁles will be deleted.
> In principle, the code can be also compiled under Windows, but then the
> user has to take care by himself/herself of the compilation.
> 
> 9

### [FEOS-Package-Documentation2016.pdf] 第 10 页

> 4 Parameter & Database File Structure
> 
> A parameter ﬁle ”Materialname.par” and the material parameter database
> ﬁle ”FEOS Material-DB.dat” are ASCII ﬁles devided into several sections by
> headlines (”Q-table”, ”Material-7386:”, etc.). Each section contains one or
> several lines with a key-word (like ”Rhonorm”, ”[7386] A[1]”), a ”=” sign,
> and some value. Lines can be commented out by a % or # at the beginning.
> Furthermore, the sections in a parameter ﬁle are grouped into two parts.
> The ﬁrst part contains the settings for the FEOS table generation tool, the
> second part those for the SHOWEOS table visualization tool.
> 
> 5 Package Standard Units
> 
> The code-internal units of the whole FEOS package are ﬁxed to cgs-units,
> except for the temperature which is given in eV. Thus, the following units
> are used:
> 
> • Temperature: eV
> 
> • Pressure: dyne/cm2 or erg/cm3
> 
> • Speciﬁc internal energy: erg/g
> 
> • Speciﬁc Helmholtz free energy: erg/g
> 
> • Speciﬁc entropy: erg/eVg
> 
> • Charge state: multiple of the unit electron charge
> 
> 10

### [FEOS-Package-Documentation2016.pdf] 第 11 页

> The FEOS Library
> 
> 6 The Physics behind the QEOS Model
> 
> The FEOS library contains all the routines which are required to calculate
> an EOS as a function of density and temperature. Before going deeper into
> the technical details, this section gives a short overview of the physics of the
> QEOS model and the improvements which have been applied to the FEOS
> library with regard to the original MPQeos code. In order to understand all
> settings of the FEOS library and of the tools, it is inevitable to understand
> the basical physics behind them. Users which are interested in really all
> details of the model are referred to Ref. [2, 5].
> 
> 6.1 General Facts
> 
> In the QEOS model the speciﬁc Helmholtz free energy F = E − T S is
> composed of three contributions, an electronic part, an ionic part, and the
> phenomenological bonding correction:
> 
> F (ρ, T ) = Fe(ρ, T ) + Fi(ρ, T ) + Fb(ρ, T )
> 
> (1)
> 
> In this documentation, all three components of F are assumed to be a func-
> tion of a single temperature T . However, the electronic part does not depend
> on the ionic part and in principle there is no diﬃculty in separating the ion
> and the electron temperatures with the FEOS library. The thermodynamical
> quantities like pressure p, speciﬁc internal energy E, and speciﬁc entropy S
> are derived from the speciﬁc Helmholtz free energy:
> 
> pe,i,b = ρ2 ∂Fe,i,b
> ∂ρ
> 
> , Se,i,b = −
> 
> ∂Fe,i,b
> ∂T
> 
> , Ee,i,b = Fe,i,b + T Se,i,b
> 
> (2)
> 
> Besides these quantities, the charge state Q is calculated. In the following
> subsections the three parts of the QEOS model will be described shortly.
> 
> To calculate an EOS for any particular element or mixture, the material
> composition must be speciﬁed: atomic number Z[i], atomic weight A[i], and
> number of atoms X[i] per ”molecule” of each single element i. Furthermore,
> the QEOS model requires two empirical parameters to calibrate the generated
> EOS, namely, the density ρo and the bulk modulus Ko = ρ (∂p/∂ρ) at a
> 
> 11

### [FEOS-Package-Documentation2016.pdf] 第 12 页

> certain reference value of temperature To and zero pressure p = po = 0. For
> substances that are in the solid state at normal conditions, usually the values
> To ≈ 300 K are used. For details on the calibration, see Subsection 6.3.
> 
> The original MPQeos code was designed to calculate an EOS within the
> following range:
> ρ
> ρo
> 
> 10−4 eV ≤ T ≤ 106 eV.
> 
> 10−7 ≤
> 
> ≤ 106,
> 
> (3)
> 
> In the FEOS library a hard lower limit (numerical ﬂoor) was introduced due
> to numerical limitations and is currently set to (see constants ”T ZERO”
> and ”RHO ZERO” in ”LIB-00 DEFINITS.H”):
> 
> ρmin = 10−50 g
> 
> cm3 ,
> 
> Tmin = 10−4 eV.
> 
> (4)
> 
> One important feature of the QEOS model is the description of van-der-Waals
> loops [6] in the liquid-vapor region. This means that liquid-vapor phase
> coexistence can be described by applying a Maxwell construction. More
> information about the corresponding procedure can be found in Section 6.6.
> 
> 6.2 Electronic EOS: TF Model
> 
> For the calculation of the electronic contribution of a single element – the
> most important part of an EOS for hot dense matter – the simple Thomas-
> Fermi (TF) model [7, 8] is used. In this model the electrons are described
> as a Fermi gas in the self-consistent electrostatic ﬁeld of the atom which is
> produced by the ion mesh and the electrons themselves. Matter is segmented
> into spherical cells for which the equilibrium electron distribution is calcu-
> lated by solving the TF equation. For the segmentation Wigner-Seitz cells
> [9] are used. Hence, the radius r0 of the cells with atomic mass A, density ρ,
> and proton mass Mp is choosen in the following way:
> 
> 4πr3
> 
> 0/3 = AMp/ρ
> 
> (5)
> 
> Since the electrons are assumed to be a Fermi gas in the electrostatic ﬁeld of
> the electrons and the ions, there is no distinction between valence electrons
> and electrons from the inner shells. Instead of this they can be seperated
> in localized and non-localized electrons. If the electrostatic potential V (r) is
> normalized to disappear at the cell boundary, those electrons are localized
> which have negative total energy (cid:15) = p2/2me − eV (r) with the classical
> momentum p. For the free atom for T = 0 this is the case for all electrons.
> Electrons with positive energy are called non-localized. They are responsible
> for the electron pressure and ionization eﬀects.
> 
> 12

### [FEOS-Package-Documentation2016.pdf] 第 13 页

> TF equation for T = 0
> 
> For T = 0 [10] the TF equation is:
> 
> d2χ(x)
> dx2 =
> 
> 1
> x1/2 χ3/2
> 
> (6)
> 
> It is a dimensionless function where x = r/a0, and the function χ is deﬁned
> by the potential V (r) and the chemical potential µ. µ is determined by
> the condition of charge neutrality of the cell. Zχ(r) can be regarded as the
> eﬀective nuclear charge.
> 
> eV (r) + µ ≡
> 
> Ze2
> r
> 
> χ(r)
> 
> a0 =
> 
> (cid:18) 3π
> 4
> 
> 1
> 2
> 
> (cid:19)2/3 ¯h2
> 
> me2 Z −1/3
> 
> The boundary conditions for the TF equation are:
> 
> χ(x) → 1,
> 
> x → 0
> 
> (cid:21)
> 
> (cid:20) x
> χ(x)
> 
> dχ
> dx
> 
> = 1
> 
> x=x0
> 
> (7)
> 
> (8)
> 
> (9)
> 
> (10)
> 
> The ﬁrst boundary condition is a result of the divergence of the potential
> close to the nucleus. The second condition follows from the charge neutrality
> of the cell. With other words: the electrical ﬁeld Er(r) = −(∂φ/∂r) at the
> boundary of the neutral cell x0 must disappear in the spherical case because
> of the law of Gauß:
> 
> (cid:20)dφ
> dx
> 
> (cid:21)
> 
> x=x0
> 
> = 0 ⇔
> 
> (cid:21)
> 
> (cid:20) x
> χ(x)
> 
> dχ
> dx
> 
> = 1
> 
> x=x0
> 
> (11)
> 
> TF equation for ﬁnite temperatures
> 
> For ﬁnite temperatures Feynman, Metropolis and Teller [9] derived a similar
> version of the TF equation
> 
> d2Ψ(ξ)
> dξ2 = aξF1/2
> 
> (cid:21)
> 
> (cid:20)Ψ(ξ)
> ξ
> 
> (12)
> 
> 13

### [FEOS-Package-Documentation2016.pdf] 第 14 页

> with the following deﬁnitions:
> 
> ξ =
> 
> r
> r0
> 
> Ψ(ξ) = ξ
> 
> eV + µ
> kT
> 
> a =
> 
> 4πmee2r2
> 
> 0(2mekT )1/2
> π¯h3
> 
> (13)
> 
> (14)
> 
> (15)
> 
> r0 is the cell radius, and F1/2 denotes the Fermi-Dirac integral. The boundary
> conditions for ﬁnite T are similar to those for T = 0:
> 
> Ψ(0) =
> 
> Ze2
> kT r0
> 
> Ψ(cid:48)(1) = Ψ(1)
> 
> Thermodynamic variables
> 
> (16)
> 
> (17)
> 
> By solving the TF equation one obtains the equilibrium electron distribution
> in the cell and thereby the energy of the electrons which consists of three
> contributions: kinetic energy K, potential energy of the electrons among
> each other Uee, and potential energy of the electrons with the nucleus Uen:
> 
> Etot
> 
> e = K + Uen + Uee
> 
> (18)
> 
> The Helmholtz free energy Fe = Ee − T Se is obtained by integrating the
> Gibbs-Helmholtz relation [11]:
> 
> Etot
> 
> e =
> 
> ∂
> ∂β
> 
> [βFe] ,
> 
> β = 1/kT
> 
> (19)
> 
> The charge state depends on the number of electrons in non-localized states
> (g(r, p) denotes the Fermi distribution function):
> 
> (cid:90)
> 
> (cid:90)
> 
> d3r
> 
> Q =
> 
> (cid:15)>0
> 
> 2d3p
> h3 g(r, p)
> 
> (20)
> 
> Advantages / disadvantages of the simple TF model
> 
> The most important advantage of the simple TF model is the fact that calcu-
> lations are faster than with advanced TF theories because the TF equation
> 
> 14

### [FEOS-Package-Documentation2016.pdf] 第 15 页

> and all thermodynamical quantities scale with the atomic number and hence
> must be calculated only once for e.g. hydrogen. For example the internal
> energy E of a element (A, Z) at density ρ and temperature T shall be calcu-
> lated. Then one ﬁrst has to rescale ρ and T :
> 
> ρ1 = ρ/AZ T1 = t/Z 4/3
> 
> (21)
> 
> Now the internal energy E1 is calculated for ρ1 and T1 for hydrogen A = Z =
> 1. E is obtained by the proper scaling formula:
> 
> E(ρ, T ) =
> 
> Z 7/3
> A
> 
> E1(ρ1, T1)
> 
> (22)
> 
> For all other thermodynamical quantities similar formulas exist. The only
> restraint for the use of the scaling property is that the original TF table
> (A = Z = 1) must cover a large density-temperature area which becomes
> clear when looking at equation (21).
> 
> The most important disadvantage of the simple TF model is the negligence
> of attractive (bonding) forces between neutral atoms. This is the reason for
> an overestimation of the critical pressure and the critical temperature and
> an overall overestimation of pressures near normal conditions. The bond-
> ing forces originate from quantum eﬀects in the electron-electron interaction.
> There exist extended TF theories like the Thomas-Fermi-Dirac (TFD) the-
> ory [12], the Thomas-Fermi-Kirzhnitz (TSK) theory [13] and the quantum
> statistical model (QSM) [14, 15]. Unfortunately, they are computationally
> more intensive and do not contain the scaling property of the simple TF
> theory.
> 
> For more details about the TF theory, its limiting cases, and inter-/extrapo-
> lation methods in the QEOS model the reader ist referred to Ref. [3, 2].
> 
> 6.3 Semiempirical Bonding Correction
> 
> The semiempirical bonding correction, the recalibration scheme of QEOS, is
> added to the total EOS in order to improve the previously mentioned fail-
> ures of the Thomas-Fermi EOS not to take care of exchange forces and to
> overestimate the electronic pressure in the solid body. A fully quantum me-
> chanical treatment of the electrons in the solid body would be too elaborate
> within the framework of the QEOS model. The free energy of the bonding
> correction is:
> 
> Fb = E0
> 
> (cid:110)
> 
> 1 − exp
> 
> (cid:16)
> 
> (cid:104)
> 
> 1 − (ρo/ρ)1/3(cid:105)(cid:17)(cid:111)
> 
> b
> 
> (23)
> 
> 15

### [FEOS-Package-Documentation2016.pdf] 第 16 页

> Since Fb does not depend on the temperature, it follows Eb = Fb. The
> pressure then is:
> 
> pb = ρ2 ∂Eb
> ∂ρ
> 
> = −
> 
> (cid:18)E0bρo
> 3
> 
> (cid:19) (cid:18) ρ
> ρo
> 
> (cid:19)2/3
> 
> (cid:34)
> 
> (cid:32)
> b
> 
> 1 −
> 
> exp
> 
> (cid:18) ρo
> ρ
> 
> (cid:19)1/3(cid:35)(cid:33)
> 
> (24)
> 
> The constants E0 and b determine the bonding correction. They characterize
> the range and the magnitude of the bonding forces. In order to determine
> them, two conditions must be fulﬁlled:
> 
> 1. The total pressure po = pio + peo + pbo must vanish at the user-deﬁned
> reference conditions (ρo,To). For substances that are in the solid state
> at normal conditions, usually the values To ≈ 300 K are used.
> 
> 2. The value of the bulk modulus [16] (and thereby the sound speed)
> 
> Ko = ρ
> 
> (cid:18) ∂p
> ∂ρ
> 
> (cid:19)
> 
> ρo
> 
> (25)
> 
> at the reference conditions must be equal to the user-deﬁned value. A
> relatively small diﬀerence between the isothermal and isentropic bulk
> moduli is usually ignored.
> 
> The theoretical motivation for the form of the Helmholtz free energy Fb [17]
> is the Morse potential in a two-atomic molecule with the bonding energy
> D, the equilibrium distance Re, and a constant b which must be determined
> empirically:
> 
> UM (R) = D (cid:2)e−2b(R−Re) − 2e−b(R−Re)(cid:3)
> 
> (26)
> 
> The bonding correction has the strongest eﬀect on the total EOS near the
> solid density. At higher densities the TF electronic contribution dominates.
> 
> 6.4 Ionic EOS: Cowan Model
> 
> The thermodynamical properties of the ionic contribution which in the QEOS
> model is totally independent of the electronic contribution are described
> through the ionic EOS. The contribution of the ions to the total EOS is sig-
> niﬁcant for temperatures T < 10 eV and densities near the reference (solid)
> density ρ/ρo < 2. For higher temperatures and/or densities the electronic
> and bonding contributions dominate. In QEOS the Cowan model is used.
> 
> 16

### [FEOS-Package-Documentation2016.pdf] 第 17 页

> It interpolates between known limiting thermodynamical cases by the aid of
> empirical formulas. The energy in the model is of purely thermal nature.
> Coulomb and bonding energies are taken care of in the electronic and the
> bonding contributions. The following list gives an overview of the limiting
> physical cases of the Cowan model:
> 
> • Ideal gas law [12] (high temperatures and/or low densities):
> 
> pi = ρkT /AMp, Ei =
> 
> 3
> 2
> 
> kT /AMp,
> 
> Si = k
> 
> (cid:20)
> S0 +
> 
> 3
> 2
> 
> (cid:21)
> log (cid:0)kT /ρ2/3(cid:1)
> 
> /AMp
> 
> S0 is given through the Sackur-Tetrode formula:
> 
> S0 =
> 
> 5
> 2
> 
> + log (2AMp) −
> 
> log (cid:0)h2/2πAMp
> 
> (cid:1)
> 
> 3
> 2
> 
> (27)
> 
> (28)
> 
> • Melting scaling law [18] (energy and density for non-ideal dense liquids):
> 
> pi =
> 
> (cid:20)
> 
> ρkT
> AMp
> 
> 1 + γF (ρ) f
> 
> (cid:19)(cid:21)
> 
> (cid:18) Tm
> T
> 
> Ei =
> 
> 3
> 2
> 
> (cid:20)
> 
> kT /AMp
> 
> 1 + f
> 
> (cid:19)(cid:21)
> 
> (cid:18) Tm
> T
> 
> (29)
> 
> (30)
> 
> γF is determined by the melting temperature Tm(ρ) and f (Tm/T ) is a
> scaling function.
> 
> • Lindemann melting law:
> 
> Tm (ρ) /Θ2
> 
> D (ρ) = α/ρ2/3
> 
> ΘD – Debye temperature, α – material dependent constant
> 
> • Dulong-Petit law (ΘD(ρ) ≤ T ≤ Tm(ρ)):
> 
> Ei ≈ 3kT /AMp
> 
> • Gr¨uneisen EOS [12] (T < Tm(ρ)):
> 
> pi = Γ (ρ) ρEi
> 
> Dependence of the Gr¨uneisen parameter Γ on ΘD [12]:
> 
> Γ (ρ) = −
> 
> V
> ΘD
> 
> ∂ΘD
> ∂V
> 
> =
> 
> ∂ log ΘD
> ∂ log ρ
> 
> 17
> 
> (31)
> 
> (32)
> 
> (33)
> 
> (34)

### [FEOS-Package-Documentation2016.pdf] 第 18 页

> • Debye-Modell:
> 
> hνD = kΘD
> 
> νD – Debye frequency, ΘD – Debye temperature
> ⇒ Speciﬁc heat of non-conductors for T < ΘD:
> 
> cV =
> 
> 12π4R
> 5
> 
> (cid:18) T
> ΘD
> 
> (cid:19)3
> 
> • Third law of thermodynamics (Nernst’s law):
> 
> lim
> T →0
> 
> S (ρ, T ) = 0
> 
> (35)
> 
> (36)
> 
> (37)
> 
> The Cowan model consists of two independent parts. The empirical part of
> the model makes estimations for the Debye and the melting temperatures
> depending on the density.
> In the structural part the EOS is calculated.
> Therefore, the scaling variables u and w are introduced:
> 
> u = ΘD (ρ) /T
> 
> w = Tm (ρ) /T
> 
> (38)
> 
> (39)
> 
> Cowan deﬁnes a scaling function f (u, w) which determines the Helmholtz
> free energy of the ions:
> 
> Fi (ρ, T ) =
> 
> kT
> AMp
> 
> f (u, w)
> 
> (40)
> 
> There are three diﬀerent areas in u-w space for which the scaling function
> is deﬁned. For temperatures above the melting temperature (T > Tm) the
> following empirical formula is used:
> 
> f (u, w) = −
> 
> 11
> 2
> 
> +
> 
> 9
> 2
> 
> w1/3 +
> 
> 3
> 2
> 
> log
> 
> (cid:19)
> 
> (cid:18) u2
> w
> 
> , w ≤ 1
> 
> (41)
> 
> For the ”hot” solid body (Tm > T > 3ΘD) holds:
> 
> f (u) = −1 + 3 log u + (cid:0)3u2/40 − u4/2240(cid:1) , w > 1, u < 3
> 
> (42)
> 
> For the ”cold” solid body (T ≤ 3ΘD) applies:
> 
> f (u) =
> 
> π4
> 9
> u + 3 log (cid:0)1 − e−u(cid:1) −
> 5u3
> 8
> + e−u (cid:0)3 + 9u−1 + 18u−2 + 18u−3(cid:1) , w > 1, u ≥ 3
> 
> (43)
> 
> 18

### [FEOS-Package-Documentation2016.pdf] 第 19 页

> In the Cowan model the Gibbs free energies in the liquid and in the solid
> phase on the melting curve are exactly the same [3]. This means that the
> QEOS model does not contain melting.
> 
> The task of the empirical part of the Cowan model is to make the Debye and
> melting temperatures and the Gr¨uneisen parameter available to the struc-
> tural part as functions of the density. It has to be pointed out that a failure
> in the estimation of these quantities only has little inﬂuence on the pres-
> sure and the energy of the ionic EOS. The empirical part should fulﬁll the
> formulas for the Gr¨uneisen parameter (34) and the Lindemann melting law
> (31).
> 
> Using a reference density ρref = (A/9Z 0.3) g/cm3 the densities are scaled
> with ξ = ρ/ρref . Thereby, the reference density corresponds with a atomic
> radius of Ra ≈ 1, 5 · 10−8Z 0.1 cm. Then Cowan’s estimations are:
> 
> kTm = 0.32
> 
> ξ2b+10/3
> (1 + ξ)4 [eV]
> 
> kΘD =
> 
> 1, 68
> Z + 22
> 
> ξb+2
> (1 + ξ)2 [eV]
> 
> Γ = b +
> 
> 2
> 1 + ξ
> 
> b = 0.6Z 1/9
> 
> (44)
> 
> (45)
> 
> (46)
> 
> Together with α = 0.0262 (cid:0)A2/3Z 0.2(cid:1) (Z + 22)2 the equations (31) and (34)
> are fulﬁlled. Since the formulas of the empirical model are simple, it is clear
> that no exact estimations can be done, and the calculated quantities have
> only a qualitative character.
> 
> 6.5 Homogeneous Mixtures of Elements
> 
> Besides pure elements, the QEOS model includes the possibility to calculate
> the EOS of homogenous mixtures of elements. Unfortunately, the corre-
> sponding procedure described in [2] was not implemented in version 2.0 of
> MPQeos. Hence, the so-called TF-mixing-of-elements method was added to
> the FEOS library. The ionic contribution and the bonding correction are
> handled as a single species with mean atomic number ¯Z and weight ¯A. For
> the electronic contribution of the mixture the densities ρ[i] (eﬀectively the
> partial volumes) of all species i are iteratively adjusted in order to equilibrate
> 
> 19

### [FEOS-Package-Documentation2016.pdf] 第 20 页

> all TF pressures pe[i] and to fulﬁll an additive volume rule:
> 
> 1) pe[i] (ρ[i], T ) = pe ∀i,
> 
> 2)
> 
> ¯A
> ρ
> 
> (cid:88)
> 
> =
> 
> x[i]
> 
> i
> 
> A[i]
> ρ[i]
> 
> (cid:88)
> 
> ( ¯A =
> 
> x[i]A[i]) . (47)
> 
> i
> 
> In these equations x[i] = X[i]/ (cid:80)
> the atomic weight of species i.
> 
> i X[i] is the number fraction, and A[i] is
> 
> The thermodynamic values for the electronic component of the mixture are
> ﬁnally obtained by summing up the single element values (with densities
> obtained by the above scheme), each weighted by x[i]A[i]/ ¯A.
> 
> The described procedure must be called for every density and temperature,
> and therefore it is clear that the calculation of mixtures of elements is com-
> putationally more intensive than for a single element. Actually, in some few
> cases the iteration process does not converge. In this case the user is rec-
> ommended to start the calculation again or to slightly change the density
> and/or temperature.
> 
> 6.6 Liquid-Vapor Phase Coexistence
> 
> The QEOS model describes van-der-Waals loops [6] (liquid-vapor metastable
> states) on isotherms below the critical point. Liquid-vapor phase coexis-
> tence can be described through a fully equilibrium EOS which is obtained
> by a Maxwell construction eliminating the van-der-Waals loops. Figure 2
> shows a metastable isotherm with a van-der-Waals loop (solid line) as well
> as the corresponding equilibrium isotherm with saturated vapor / equilib-
> rium pressure psat (dashed line). The region of liquid-vapor metastable and
> equilibrium states is delimited by the so-called binodal / vaporization curve.
> The extrema of the van-der-Waals loops are connected through the so-called
> spinodal. The question whether one has to use the metastable or the equilib-
> rium EOS below the binodal must be individually answered for each problem
> under consideration. Ref. [4] gives an answer for hydrodynamic simulations
> and shows results for volumetrically heated matter.
> 
> According to Maxwell’s rule the saturated vapor pressures for each isotherm
> below the critical point are determined by ﬁnding such two points along
> the isotherm with equal pressure p = psat and equal Gibbs free energy
> G = E + pV − T S (chemical potential). This rule corresponds to the well
> known geometrical rule of equal areas between the van-der-Waals loop and
> 
> 20

### [FEOS-Package-Documentation2016.pdf] 第 21 页

> Figure 2: Isotherm with and without the
> Maxwell
> the
> construction
> volume-pressure phase plane; the
> binodal and the spinodal touch
> each other at the critical point
> CP.
> 
> on
> 
> the equilibrium isotherm:
> 
> (T = const.)
> 
> (cid:90) Vliq
> 
> Vvap
> 
> pdV = psat (Vvap − Vliq) .
> 
> (48)
> 
> In the original MPQeos code the Maxwell construction was calculated with
> this geometrical rule which is especially for low temperatures in the two-
> phase region computationally very intensive and imprecise.
> In FEOS the
> MPQeos method was replaced by a root ﬁnding algorithm which determines
> the points on the liquid and the vapor sides of the binodal with equal Gibbs’
> free energies and pressures. Since this ”new” method involves no numerical
> integrations, it is much faster and more accurate.
> 
> Nevertheless, there exists one important limitation for the calculation of the
> Maxwell construction: Since psat and the density at the vapor branch of the
> binodal become very low for temperatures around room temperature, the
> EOS has to be calculated down to very low densities. As already mentioned
> in Subsection 6.1, computational limits determine the lowest calculatable
> density. The Maxwell routines of the library will print out warnings if the
> Maxwell construction cannot be done consistently for a given temperature.
> Furthermore, the lowest temperature which could be calculated consistently
> is returned by the library. Note that even if the Maxwell construction can
> be done consistently one should be carefull to check the correct behaviour
> of the EOS for such very low densities. In some cases, it can happen that
> the code violates the ideal gas law limit. This is a construction site for the
> future.
> 
> If the user decides to calculate the Maxwell equilibrium EOS, the library
> applies two additional steps: In the ﬁrst step, the critical point is looked up
> via a bisectioning algorithm. A check is done on loops in each isotherm, until
> the one with loops at maximum temperature is found. On this isotherm, the
> 
> 21

### [FEOS-Package-Documentation2016.pdf] 第 22 页

> density where d2p/dρ2 = 0 is determined. In the second step, the vaporisation
> curve is calculated by applying the Maxwell construction to each temperature
> speciﬁed by the user below the critical point. In order to save computational
> time, both steps are performed during the material initialization stage.
> 
> Later, for computing EOS data at some point inside the two-phase region,
> the thermodynamic quantities are interpolated linearly. Outside the two-
> phase region, the computation of the thermodynamic quantities goes as in
> the normal case. As the user speciﬁed temperature grid for the Maxwell con-
> struction strongly determines the quality or even the existence of the critical
> data and vaporisation curve, one should not specify too few temperatures
> near and inside the critical region.
> 
> 6.7 Cold Curve Improvement
> 
> Despite the existence of the bonding correction (Section 6.3), the QEOS
> model still overestimates the location of the critical point (pressure pc and
> temperature Tc). Furthermore, in a few cases the value of the cohesive energy
> Ecoh – better known as enthalpy of sublimation – can become negative. In
> order to solve this problem in the FEOS library, the TF cold curve and the
> bonding correction can now be replaced for densities ρ < ρo by a soft-sphere
> function which was proposed by Young et al. [5]:
> 
> Ecold (ρ, T = 0) = Aρn − Bρm + Ecoh .
> 
> (49)
> 
> The constants A and B are adjusted so as to make the total pressure and
> the internal energy be equal to zero at the reference point (ρo, To):
> 
> p(ρo, To) = E(ρo, To) = 0 .
> 
> (50)
> 
> The free parameters m and n are used to improve the agreement with the
> experimentally (or theoretically) known critical point. At ρ = ρo the sound
> velocity is allowed to be discontinuous.
> 
> The following list demonstrates how the soft-sphere function aﬀects the lo-
> cation of the critical point for aluminum:
> 
> Experimental / theoretical values [5]: Tc = 5700 K,
> Tc = 13487 K,
> Original MPQeos (version 2.0):
> Tc = 5558 K,
> FEOS library:
> 
> pc = 1820 bar
> pc = 23487 bar
> pc = 1722 bar
> 
> (m = 0.5, n = 2.0, Ecoh = 12.123 kJ/g)
> 
> 22

### [FEOS-Package-Documentation2016.pdf] 第 23 页

> 7 Technical Design of the Library
> 
> The static library ﬁle ”libfeos.a” is basically a collection of object ﬁles /
> routines. Those routines which are intended to be used from outside the
> library, namely from the user’s code or the FEOS table generation tool,
> form the FEOS library interface. The interface is designed in such a way
> that all routines can be either called from a C, a C++, or a Fortran code.
> Instructions concerning the implementation of the library ﬁle into the user’s
> code and detailed descriptions of the interface routines are given in Sections
> 11 and 12.
> 
> In principle, the FEOS library can calculate the EOS of an arbitrary number
> of materials with ﬁxed composition in parallel. The work done by the library
> routines can be classiﬁed into two categories: 1) routines which are respon-
> sible for the initialization of the library and of the materials which shall be
> calculated, and 2) routines which calculate the thermodynamic functions.
> Analogously, also the interface routines can be basically classiﬁed into two
> categories: 1) the obligatory routines which are responsible for the initializa-
> tion and ﬁnalization, 2) the facultative routines which return the information
> calculated during the initialization stage and the thermodynamic functions
> (Section 12).
> 
> Figure 3 gives an overview of the logical structure how the library is in-
> tended to be implemented into a user’s code for three diﬀerent materials.
> First, the library itself is initialized with an arbitrary number of material en-
> tities. Then, all materials must be initialized with several parameters by the
> material initialization procedure described in the next subsection. Having
> initialized a material, one can either retrieve the information about the ma-
> terial which are already present and/or one can calculate the thermodynamic
> functions (of the full EOS and/or of the EOS contributions with or without a
> Maxwell construction) as a function of density and temperature (see Section
> 8 for a list of information provided by the library). Finally, if the library is
> not to be used anymore, it must be ﬁnalized to free the occupied memory.
> 
> 7.1 Material Initialization Stage
> 
> Figure 4 gives an overview of the initialization procedure of a material within
> the FEOS library. The material initialization is controlled by the interface
> routine ”FEOS Init Mat(...)”. Several arguments have to be passed which
> 
> 23

### [FEOS-Package-Documentation2016.pdf] 第 24 页

> Figure 3: Operational sequence for implementation of the FEOS library.
> 
> 24

### [FEOS-Package-Documentation2016.pdf] 第 25 页

> Figure 4: Operational sequence of the FEOS library material initialization.
> 
> 25

### [FEOS-Package-Documentation2016.pdf] 第 26 页

> control the following options:
> 
> • The number of the material in the FEOS material parameter database
> 
> ﬁle (Section 10) must be deﬁned.
> 
> • A ﬂag tells the library if a Maxwell construction shall be initialized
> for the material. If set to yes, an array with temperatures and its size
> must be passed. These temperatures control the quality of the Maxwell
> construction.
> 
> • Another ﬂag tells the library if the improved cold curve (Section 6.7)
> 
> shall be used for the material.
> 
> Within the several steps of the initialization procedure the diﬀerent class
> objects of the FEOS library are constructed for the material. The FEOS li-
> brary knows basically three classes: 1) a class ”Ionpart” for the storage of the
> general material parameters and for the routines used for the calculation of
> the ionic contribution, the bonding correction, and the improved cold curve,
> 2) a class ”QIPscheme” for the electronic contribution / interpolation on the
> TF table for each single element in a material, and 3) a class ”CriticalData”
> for the Maxwell construction data and routines.
> 
> First, the ”Ionpart” class object is constructed.
> In this step the material
> parameters are read-out from the material parameter database ﬁle (Section
> 10). Then, ”QIPscheme” class objects are constructed for each element in
> the material. Therefore, the precalculated TF table ﬁle for hydrogen is read-
> out and the TF interpolation scheme is set-up for the corresponding atomic
> numbers and atomic weights. In the third step, the parameters of the bonding
> correction (and soft sphere function) are determined.
> 
> If a Maxwell construction (Section 6.6) is desired, a ”CriticalData” class ob-
> ject is constructed and at the same time ﬁlled with data. Therefore, ﬁrst the
> critical point is determined with a bisectioning procedure. Then, for each
> deﬁned temperature below the critical point, the Maxwell construction is it-
> eratively calculated and the binodal / vaporization curve is stored. Later on,
> when calculating a density-temperature point within the two-phase region,
> this precalculated critical data can be used for linear interpolations.
> 
> At the end of a material initialization the routine ”FEOS Init Mat(...)” re-
> turns the number of elements in the choosen material and, if available, the
> quality of the calculated Maxwell construction data.
> 
> 26

### [FEOS-Package-Documentation2016.pdf] 第 27 页

> 8
> 
> Information provided by the Library
> 
> The FEOS library provides a wide set of information. The following list
> summarizes all the properties and parameters which can be retrieved with
> the library interface routines:
> 
> • The following thermodynamic functions as a function of density and
> temperature for the complete EOS and/or for one component (elec-
> tronic EOS, ionic EOS, or pure Thomas-Fermi EOS), either with or
> without a Maxwell construction:
> 
> – Pressure
> 
> – Speciﬁc internal energy
> 
> – Speciﬁc Helmholtz free energy
> 
> – Speciﬁc entropy
> 
> – Charge state for each element in a mixture
> 
> – Summed-up (not mean) charge state for a ”molecule”
> 
> • All the material parameters which are stored in the material parameter
> 
> database (Section 10), especially the material’s composition
> 
> • If initialized, critical point data: temperature, density, pressure, en-
> 
> thalpy, entropy, and compressibility factor at the critical point
> 
> • If initialized: temperatures, densities, pressures, speciﬁc Gibbs free en-
> ergies, speciﬁc enthalpies, and compressibility factors along the binodal
> 
> • If initialized: temperatures, densities, and pressures along the spinodal
> 
> • The temperature and density ﬂoor values of the library, below which
> 
> the EOS cannot be calculated for numerical reasons (Section 6.1)
> 
> • The energy oﬀsets of the electronic and the ionic EOS which are sub-
> stracted to zero the complete speciﬁc energy at reference conditions
> 
> 9 Source Code Structure
> 
> As the QEOS model itself, also the source code of the FEOS library is divided
> into several parts. Table 2 gives an overview of the source ﬁles of the library.
> 
> 27

### [FEOS-Package-Documentation2016.pdf] 第 28 页

> LIB-00 DEFINITS.H
> 
> LIB-01 TF SERVICES.C
> 
> LIB-02 TF TABLE 1.C,
> LIB-02 TF TABLE 2.C
> 
> LIB-03 TF MIXTURE.C
> 
> LIB-04 IONMOD.C
> 
> LIB-05 EOS SERVICES.C
> 
> LIB-06 MAXWELL.C
> 
> Numerical constants for the library
> and paths of the material database
> and the Thomas-Fermi table ﬁles
> 
> Routines for reading the TF-ﬁle
> and calculating the Fermi-Dirac
> functions
> 
> Routines for calculation of the single
> element Thomas-Fermi EOS
> 
> Routines
> Thomas-Fermi EOS of a mixture
> 
> calculation of
> 
> for
> 
> the
> 
> Routines for reading the material
> parameter database and calculation
> of the ionic EOS, the bonding cor-
> rection, and the soft-sphere function
> 
> for
> 
> calculation of
> 
> the
> Routines
> thermodynamic functions without
> Maxwell construction
> 
> Routines for initialization of the
> Maxwell construction and calcula-
> tion of
> the EOS with Maxwell
> construction
> 
> LIB-07 C INTERFACE.C,
> LIB-08 FORTRAN INTERFACE.C
> 
> C/C++ and Fortran interface rou-
> tines
> 
> Table 2: Source ﬁles of the FEOS library.
> 
> The diﬀerent classes of the code were already explained in Section 7.1. The
> ”QIPscheme” class for the calculation of the Thomas-Fermi EOS for a single
> element is deﬁned in the ”LIB-02...” ﬁles. The Thomas-Fermi EOS for a
> mixture of elements (Section 6.5) is obtained in the ”LIB-03...” ﬁle. The
> ”Ionpart” class is deﬁned in the ”LIB-04...” ﬁle.
> 
> The ”LIB-05...” ﬁle combines the diﬀerent parts of the QEOS model and con-
> tains all the routines which calculate the thermodynamic functions without
> a Maxwell construction. These routines may be called by the ”CriticalData”
> class, deﬁned in the ”LIB-06...” ﬁle, to initialize and to calculate the ther-
> modynamic functions with a Maxwell construction. Finally, the interface
> 
> 28

### [FEOS-Package-Documentation2016.pdf] 第 29 页

> routines are deﬁned in the ”LIB-07...” and the ”LIB-08...” ﬁles where the
> Fortran interface routines simply call the C/C++ interface routines.
> 
> 10 Material Parameter Database
> 
> The material parameter database ﬁle ”FEOS Material-DB.dat” contains all
> collected physical material properties and parameters. The FEOS library
> routines access this ﬁle for each material to be initialized. Each parameter
> set / section in the ﬁle begins with the headline ”Material-xxxx:” where xxxx
> is the material number. Allowed material numbers are 1000-9999. Each
> parameter inside a section begins with the preﬁx ”[xxxx] ”. Table 3 lists all
> parameters which must be set for a material. The soft-sphere parameters
> must be only set if the improved cold curve (see Section 6.7) shall be used.
> 
> 11
> 
> Implementation of the Library
> 
> The static library ﬁle ”libfeos.a” is automatically created within the FEOS
> package installation / compilation process (Section 3). It can be implemented
> into any C/C++ or Fortran code.
> 
> If the library accessing code is compiled with the GNU or Intel C++ compiler,
> the following options must be applied for the linking stage:
> 
> -L. -lfeos
> 
> or
> 
> libfeos.a
> 
> For the GNU or Intel C or Fortran compiler, the corresponding options are:
> 
> -L. -lstdc++ -lfeos
> 
> or
> 
> -lstdc++ libfeos.a
> 
> The -L. ﬂag prompts the compiler to search for librariy ﬁles in the same
> directory where it is executed. The -lstdc++ ﬂag tells the compiler to employ
> the C++ library, and the -lfeos ﬂag ﬁnally enables the FEOS library.
> 
> If the library shall be used with a C/C++ code, the ”libfeos.h” header ﬁle
> must be also copied to the code directory, and the ”include ”libfeos.h””
> statement must be used inside the code.
> 
> Once a code is successfully linked together with the FEOS library and the
> executable ﬁle shall be used, one must be careful also to copy the ﬁles
> 
> 29

### [FEOS-Package-Documentation2016.pdf] 第 30 页

> SESAME-Number
> 
> the material
> 
> in the SESAME
> Number of
> database. If not known, this parameter can be
> set to 1000. It is only required for the SESAME
> output format (Section 16.3).
> 
> Treference
> 
> Reference temperature in eV
> 
> Rhoreference
> 
> Bulk-Modulus
> 
> Density at Treference and zero pressure in g/cm3
> 
> Bulk modulus at Treference and Rhoreference in
> dyne/cm2
> 
> Number-of-Elements
> 
> Number of elements which form a mixture. For
> single elements this parameter must be set to 1
> 
> A[1...Element-Number] Atomic weights of all included elements
> 
> Z[1...Element-Number] Atomic numbers of all included elements
> 
> X[1...Element-Number] Number of atoms in one ”molecule” of all in-
> 
> cluded elements
> 
> Ecohesive
> 
> Cohesive energy / enthalphy of sublimation in
> erg/g; used for the soft-sphere function
> 
> Soft-Sphere-m
> 
> Parameter m in soft-sphere function
> 
> Soft-Sphere-n
> 
> Parameter n in soft-sphere function
> 
> Table 3: Parameters to be set for each material entry in the material param-
> eter database ﬁle. A corresponding preﬁx [xxxx] with the material
> number must be put in front of each parameter name.
> 
> ”FEOS Material-DB.dat” and ”FEOS TF-Table 1197.dat” from /EOS-Data
> into the directory where the code is executed. The material parameter
> database and the precalculated Thomas-Fermi table are read during the ini-
> tialization stage of any material to be calculated with the library. If a material
> is not present in the database, a new entry must be created (Section 10).
> 
> 12
> 
> Interface Routines
> 
> The FEOS library provides several routines for the usage in any user’s code.
> To calculate an EOS, some of these routines are obligatory. The other rou-
> 
> 30

### [FEOS-Package-Documentation2016.pdf] 第 31 页

> tines are facultative and can only be called if the obligatory ones are used.
> To get an impression, how the interface routines may be used, one can also
> have a look into the main ﬁle of the FEOS table generation tool (Section 14).
> 
> All interface routines begin with the preﬁx ”FEOS ”. Furthermore, all inter-
> face routines are present in two versions. One version is intended to be called
> from C/C++ codes. The corresponding routines will be marked in blue in
> this section. The other version is intended to be called from Fortran codes,
> and the corresponding routines will be marked in red in the following. The
> ﬁle ”LIB-07 C INTERFACE.C” contains all the C/C++ interface routines.
> In ”LIB-08 FORTRAN INTERFACE.C” the Fortran interface routines are
> located.
> 
> Fortran programmers should take care of the fact that most Fortran com-
> pilers add automatically a ” ” sign at the end of each subroutine’s name
> during linking. The FEOS library assumes that this ” ” sign is present. If
> one of the library Fortran interface routines is called and the Fortran com-
> piler does not automatically add the ” ” sign, then one must manually add
> it (e.g., instead of using ”call FEOS FINALIZE(...)”, the command ”call
> FEOS FINALIZE (...)” must be used).
> 
> If the interface routines are intended to be called from an OpenMP paral-
> lelized code, one must assure that any FEOS interface routine is only called
> by the OpenMP master thread.
> 
> Finally, one should always keep in mind, that any physical quantity argument
> in the interface routines, no matter if input or output, is or must be given in
> the FEOS standard units (Section 5).
> 
> 12.1 Obligatory Interface Routines
> 
> void FEOS Initialize( int entitynumber, int printﬂag )
> 
> FEOS INITIALIZE( entitynumber, printﬂag )
> 
> integer(4) :: entitynumber, printﬂag
> 
> entitynumber (INPUT): Number of diﬀerent materials which the EOS shall
> be calculated for. E.g., to calculate the EOS for Al, Cu and Li, enti-
> tynumber must be set to 3 (or any higher integer).
> 
> 31

### [FEOS-Package-Documentation2016.pdf] 第 32 页

> printﬂag (INPUT): If set to 0, the library will write no output to the console
> (except for error messages). If set to 1, the library will write full output
> to the console. For MPI parallelized codes this ﬂag should only be 1
> for the MPI master task to reduce the output to the console.
> 
> FEOS Initialize must be called before all the other interface routines. It can
> only be called again, if one calls FEOS Finalize before.
> 
> —————————————————————————————————
> 
> void FEOS Finalize( )
> 
> FEOS FINALIZE( )
> 
> FEOS Finalize will free the memory used by the library. Once one has called
> it, except for FEOS Initialize, the other interface routines cannot be called
> anymore.
> 
> —————————————————————————————————
> 
> void FEOS Init Mat( int entity, int materialnumber, int Maxwellﬂag,
> 
> int softsphereﬂag, double* MaxwellTtab, int sizeofMaxwellTtab,
> int* numofelements, int* numofMaxwelliso,
> double* MaxwellTreliable )
> 
> FEOS INIT MAT( entity, materialnumber, Maxwellﬂag, softsphereﬂag,
> 
> MaxwellTtab, sizeofMaxwellTtab, numofelements, numofMaxwelliso,
> MaxwellTreliable )
> 
> integer(4) :: entity, materialnumber, Maxwellﬂag, softsphereﬂag,
> 
> sizeofMaxwellTtab, numofelements, numofMaxwelliso
> 
> real(8) :: MaxwellTtab(sizeofMaxwellTtab), MaxwellTreliable
> 
> entity (INPUT): This integer deﬁnes a unique code-internal identiﬁer for
> any material which will be calculated. Every number is only allowed
> to be initialized once. The allowed range is [1, entitynumber] (see
> FEOS Initialize).
> 
> materialnumber (INPUT): Number of the material in the FEOS material
> 
> parameter database ﬁle.
> 
> 32

### [FEOS-Package-Documentation2016.pdf] 第 33 页

> Maxwellﬂag (INPUT): If set to 1, the critical point will be calculated, and
> the Maxwell construction will be initialized for this material entity. If
> set to 0, no critical point and no Maxwell construction will be available.
> 
> softsphereﬂag (INPUT): If set to 1, the soft-sphere function will be used.
> If set to 0, only the bonding correction will be used. The soft-sphere
> function can only be used if the soft-sphere parameters have been
> deﬁned in the FEOS material parameter database for the material
> with number ”materialnumber”.
> 
> MaxwellTtab (INPUT): Array of size ”sizeofMaxwellTtab” containing a
> list of temperatures in eV in ascending order.
> If the Maxwell con-
> struction should be initialized, it will be explicitly calculated for those
> temperatures. The more temperatures are used, the better the quality
> of the Maxwell data will be, but the longer the initialization will take.
> If the library is used to calculate the EOS for a ﬁxed table, you the
> best result will be achieved if the same temperatures of the EOS table
> It must be assured that at
> are used for the Maxwell initialization.
> least one temperature lies above the critial point!
> 
> sizeofMaxwellTtab (INPUT): Number of temperatures in or size of the
> 
> array ”MaxwellTtab”.
> 
> numofelements (OUTPUT): Number of elements within the material with
> 
> number ”materialnumber”.
> 
> numofMaxwelliso (OUTPUT): If the Maxwell construction is initialized,
> this integer will give the number of temperatures which lie below the
> critical point and for which the Maxwell construction was calculated.
> Attention: This does not imply that these temperatures are the same
> temperatures within your input array ”MaxwellTtab” up to element
> ”numofMaxwelliso”.
> 
> MaxwellTreliable (OUTPUT): If the Maxwell construction is initialized,
> this will represent the lowest temperature for which the Maxwell con-
> struction could be calculated consistently without any problems. This
> means, that the EOS with Maxwell construction is reliable above this
> temperature.
> 
> FEOS Init Mat must be called until any other interface routine for a material
> entity can be called. It must be called for any material the EOS should be
> calculated for (of course, with diﬀerent entity numbers between 1 and enti-
> 
> 33

### [FEOS-Package-Documentation2016.pdf] 第 34 页

> tynumber). Until FEOS Init Mat can be called, the library must have been
> initialized with FEOS Initialize before. For the same entity, FEOS Init Mat
> can only be called again if FEOS Delete Mat has been called before in order
> to delete the material entity, or the whole library has been reinitialized with
> FEOS Finalize followed by FEOS Initialize.
> 
> 12.2 Facultative Interface Routines
> 
> All facultative routines can only be used if the library was (re-)initialized
> with FEOS Initialize and not ﬁnalized with FEOS Finalize. Some facultative
> routines are material-speciﬁc or return information only for one entity. These
> routines can only be called if the material entity has been initialized with
> FEOS Init Mat. Furthermore, some facultative routines require Maxwell-
> construction data. These routines can only be called for a given material
> entity if ”Maxwellﬂag” was set to 1 in FEOS Init Mat.
> 
> void FEOS Get EOS All( int entity, int Maxwell,
> 
> double Rho, double T, int* belowbinodal,
> double* p, double* e, double* s, double* f, double* q, double* qtot,
> double* pe, double* ee, double* se, double* fe,
> double* pi, double* ei, double* si, double* ﬁ,
> double* pTF, double* eTF, double* sTF, double* fTF )
> 
> FEOS GET EOS ALL( entity, Maxwell, Rho, T, belowbinodal,
> 
> p, e, s, f, q, qtot, pe, ee, se, fe, pi, ei, si, ﬁ, pTF, eTF, sTF, fTF )
> 
> integer(4) :: entity, Maxwell, belowbinodal
> 
> real(8) :: Rho, T, p, e, s, f, q(numofelements), qtot, pe, ee, se, fe,
> 
> pi, ei, si, ﬁ, pTF, eTF, sTF, fTF
> 
> entity (INPUT): Deﬁnes the material entity the EOS will be calculated for.
> 
> Maxwell (INPUT): If set to 1, the EOS will be returned with Maxwell
> construction. If set to 0, the EOS will be calculated without Maxwell
> construction. Attention: ”Maxwell” = 1 is only allowed if the Maxwell
> construction has been initialized in FEOS Init Mat for the entity under
> consideration (”Maxwellﬂag” = 1).
> 
> Rho (INPUT): Density in g/cm3 for which the EOS will be calculated.
> 
> 34

### [FEOS-Package-Documentation2016.pdf] 第 35 页

> T (INPUT): Temperature in eV for which the EOS will be calculated.
> 
> belowbinodal (OUTPUT): If ”Maxwell” is set to 1, this integer will be 1
> if the density-temperature point lies inside the two-phase region, and,
> thus, the Maxwell construction is used.
> It will be 0 if the density-
> temperature point lies outside the two-phase region. If ”Maxwell” is
> set to 0, ”belowbinodal” will be always 0, even if the temperature-
> density point lies inside the two-phase region.
> 
> p, e, s, f (OUTPUT): Pressure, speciﬁc internal energy, speciﬁc entropy,
> and speciﬁc Helmholtz free energy of the total EOS (which is the sum
> of the electronic and the ionic EOS).
> 
> q (OUTPUT): Array of size ”numofelements” containing the charge states
> 
> for every element of the material.
> 
> qtot (OUTPUT): Charge state of one ”molecule”. To get the mean charge
> state of a mixture, divide ”qtot” by ”Xtot” (see FEOS Get Mat Par).
> 
> pe, ee, se, fe (OUTPUT): Pressure, speciﬁc internal energy, speciﬁc entropy,
> and speciﬁc Helmholtz free energy of the electronic EOS (which is the
> sum of the pure Thomas-Fermi contribution and the corrections - the
> bonding correction and the soft-sphere function).
> 
> pi, ei, si, ﬁ (OUTPUT): Pressure, speciﬁc internal energy, speciﬁc entropy,
> and speciﬁc Helmholtz free energy of the ionic EOS (which is calculated
> with the Cowan model).
> 
> pTF, eTF, sTF, fTF (OUTPUT): Pressure, speciﬁc internal energy, spe-
> ciﬁc entropy, and speciﬁc Helmholtz free energy of the pure Thomas-
> Fermi EOS.
> 
> Always remember: The total pressure in the FEOS model is set to 0 for a
> given reference point ρo and To. The speciﬁc internal energy and speciﬁc
> Helmholtz free energy are shifted by an oﬀset such that both become 0 for
> each component (total EOS, electronic EOS, ionic EOS, and pure Thomas-
> Fermi EOS) at ρo and To. The ionic and electronic oﬀsets can be retrieved
> out of the library for each material entity with FEOS Get Energy Oﬀsets.
> 
> If the EOS is calculated with a Maxwell construction, the charge states and
> all the quantities from the electronic, ionic, and pure Thomas-Fermi EOS
> become physically meaningless inside the two-phase region.
> 
> 35

### [FEOS-Package-Documentation2016.pdf] 第 36 页

> If one only wants to calculate the electronic EOS, the ionic EOS, or the pure
> Thomas-Fermi EOS, it is highly advisable to use FEOS Get EOS instead of
> FEOS Get EOS All. This will safe computational time, since the unwanted
> contributions are not calculated.
> 
> —————————————————————————————————
> 
> void FEOS Get EOS( int entity, int task, int Maxwell,
> double Rho, double T, int* belowbinodal,
> double* p, double* e, double* s, double* f, double* q, double* qtot )
> 
> FEOS GET EOS( entity, task, Maxwell, Rho, T, belowbinodal,
> 
> p, e, s, f, q, qtot )
> 
> integer(4) :: entity, task, Maxwell, belowbinodal
> 
> real(8) :: Rho, T, p, e, s, f, q(numofelements), qtot
> 
> entity (INPUT): Deﬁnes the material entity the EOS will be calculated for.
> 
> task (INPUT): Deﬁnes the kind of EOS which will be returned.
> 
> ”task” = 0 → The total EOS will be returned.
> ”task” = 1 → The ionic EOS will be returned.
> ”task” = 2 → The electronic EOS will be returned.
> ”task” = 3 → The pure Thomas-Fermi EOS will be returned.
> Note that the total EOS is the sum of the electronic and the ionic
> EOS. The electronic EOS is the pure Thomas-Fermi EOS including
> all corrections - the bonding correction and the soft-sphere function.
> 
> Maxwell (INPUT): If set to 1, the EOS will be returned with Maxwell
> construction. If set to 0, the EOS will be calculated without Maxwell
> construction. Attention: ”Maxwell” = 1 is only allowed if the Maxwell
> construction has been initialized in FEOS Init Mat for the entity under
> consideration (”Maxwellﬂag” = 1).
> 
> Rho (INPUT): Density in g/cm3 for which the EOS will be calculated.
> 
> T (INPUT): Temperature in eV for which the EOS will be calculated.
> 
> belowbinodal (OUTPUT): If ”Maxwell” is set to 1, this integer will be 1
> if the density-temperature point lies inside the two-phase region, and,
> thus, the Maxwell construction is used.
> It will be 0 if the density-
> temperature point lies outside the two-phase region. If ”Maxwell” is
> 
> 36

### [FEOS-Package-Documentation2016.pdf] 第 37 页

> set to 0, ”belowbinodal” will be always 0, even if the temperature-
> density point lies inside the two-phase region.
> 
> p, e, s, f (OUTPUT): Pressure, speciﬁc internal energy, speciﬁc entropy,
> and speciﬁc Helmholtz free energy of the EOS deﬁned by ”task”.
> 
> q (OUTPUT): Array of size ”numofelements” containing the charge states
> for every element of the material. Note that the charge states are only
> calculated, if ”task” is not equal to 1.
> 
> qtot (OUTPUT): Charge state of one ”molecule”. Note that ”qtot” is only
> calculated, if ”task” is not equal to 1. To get the mean charge state
> of a mixture, divide ”qtot” by ”Xtot” (see FEOS Get Mat Par).
> 
> Always remember: The total pressure in the FEOS model is set to 0 for a
> given reference point ρo and To. The speciﬁc internal energy and speciﬁc
> Helmholtz free energy are shifted by an oﬀset such that both become 0 for
> each component (total EOS, electronic EOS, ionic EOS, and pure Thomas-
> Fermi EOS) at ρo and To. The ionic and electronic oﬀsets can be retrieved
> out of the library for each material entity with FEOS Get Energy Oﬀsets.
> 
> If the EOS is calculated with a Maxwell construction, the charge states and
> all the quantities from the electronic, ionic, and pure Thomas-Fermi EOS
> become physically meaningless inside the two-phase region.
> 
> —————————————————————————————————
> 
> void FEOS Delete Mat( int entity )
> 
> FEOS DELETE MAT( entity )
> 
> integer(4) :: entity
> 
> entity (INPUT): Deﬁnes the material entity which shall be deleted.
> 
> This routine can be used if a given entity shall be deleted during the runtime
> in order to initialize the same number afterwards again with FEOS Mat Init
> with a diﬀerent material or diﬀerent conditions.
> 
> —————————————————————————————————
> 
> void FEOS Get Calc Limits( double* Tzero, double* Rhozero )
> 
> 37

### [FEOS-Package-Documentation2016.pdf] 第 38 页

> FEOS GET CALC LIMITS( Tzero, Rhozero )
> 
> real(8) :: Tzero, Rhozero
> 
> Tzero (OUTPUT): Lower temperature ﬂoor of the library.
> 
> Rhozero (OUTPUT): Lower density ﬂoor of the library.
> 
> If one calls any interface routine for a density and/or a temperature below
> these limits, the library will set the density and/or the temperature to these
> limits.
> 
> —————————————————————————————————
> 
> void FEOS Get Mat Par( int entity, double* A, double* Z, double* X,
> double* Atot, double* Ztot, double* Xtot, double* Tref,
> double* Rhoref, double* BulkModref, int* SESAMEnumber )
> 
> FEOS GET MAT PAR( entity, A, Z, X, Atot, Ztot, Xtot, Tref, Rhoref,
> 
> BulkModref, SESAMEnumber )
> 
> integer(4) :: entity, SESAMEnumber
> 
> real(8) :: A(numofelements), Z(numofelements), X(numofelements),
> 
> Atot, Ztot, Xtot, Tref, Rhoref, BulkModref
> 
> entity (INPUT): Deﬁnes the material entity for which the material param-
> 
> eters will be returned.
> 
> A (OUTPUT): Array of size ”numofelements” containing the atomic weights
> 
> of all elements.
> 
> Z (OUTPUT): Array of size ”numofelements” containing the atomic numbers
> 
> of all elements.
> 
> X (OUTPUT): Array of size ”numofelements” containing the number of
> 
> atoms of all elements within one ”molecule”.
> 
> Atot (OUTPUT): Atomic weight of one ”molecule”. To get the mean atomic
> 
> weight of a mixture, ”Atot” must be divided by ”Xtot”.
> 
> Ztot (OUTPUT): Atomic number of one ”molecule”. To get the mean
> atomic number of a mixture, ”Ztot” must be divided by ”Xtot”.
> 
> 38

### [FEOS-Package-Documentation2016.pdf] 第 39 页

> Xtot (OUTPUT): Number of atoms within one ”molecule”.
> 
> Tref, Rhoref (OUTPUT): Reference temperature and density for which the
> 
> total pressure is set to zero.
> 
> BulkModref (OUTPUT): Reference bulk modulus at reference density and
> 
> reference temperature.
> 
> This routine returns all the basic material parameters from the material
> parameter database.
> 
> —————————————————————————————————
> 
> void FEOS Get Crit Point( int entity, double* T, double* Rho,
> 
> double* P, double* H, double* S, double* Z )
> 
> FEOS GET CRIT POINT( entity, T, Rho, P, H, S, Z )
> 
> integer(4) :: entity
> 
> real(8) :: T, Rho, P, H, S, Z
> 
> entity (INPUT): Deﬁnes the material entity for which the critical point
> 
> parameters will be returned.
> 
> T (OUTPUT): Critical temperature.
> 
> Rho (OUTPUT): Critical density.
> 
> P (OUTPUT): Critical pressure.
> 
> H (OUTPUT): Critical speciﬁc enthalpy.
> 
> S (OUTPUT): Critical speciﬁc entropy.
> 
> Z (OUTPUT): Critical compressibility factor.
> 
> This routine returns the location of the critical point. Attention: This data is
> only available if the Maxwell construction was initialized in FEOS Init Mat
> for the entity under consideration (”Maxwellﬂag” = 1).
> 
> —————————————————————————————————
> 
> void FEOS Get SoftSphere Par( int entity, double* Ecoh, double* softsp n,
> 
> 39

### [FEOS-Package-Documentation2016.pdf] 第 40 页

> double* softsp m, double* softsp A, double* softsp B )
> 
> FEOS GET SOFTSPHERE PAR( entity, Ecoh, softsp n, softsp m, softsp A,
> 
> softsp B )
> 
> integer(4) :: entity
> 
> real(8) :: Ecoh, softsp n, softsp m, softsp A, softsp B
> 
> entity (INPUT): Deﬁnes the material entity for which the soft-sphere pa-
> 
> rameters will be returned.
> 
> Ecoh (OUTPUT): Cohesive energy in erg/g.
> 
> softsp n (OUTPUT): Parameter n in soft-sphere function.
> 
> softsp m (OUTPUT): Parameter m in soft-sphere function.
> 
> softsp A (OUTPUT): Parameter A in soft-sphere function.
> 
> softsp B (OUTPUT): Parameter B in soft-sphere function.
> 
> This routine returns the parameters which are used in and calculated for the
> soft-sphere function. Attention: This data is only available if the soft-sphere
> function was initialized in FEOS Init Mat for the entity under consideration
> (”softsphereﬂag” = 1).
> 
> —————————————————————————————————
> 
> void FEOS Get Energy Oﬀsets( int entity, double* ElectronOﬀs,
> 
> double* IonOﬀs )
> 
> FEOS GET ENERGY OFFSETS( entity, ElectronOﬀs, IonOﬀs )
> 
> integer(4) :: entity
> 
> real(8) :: ElectronOﬀs, IonOﬀs
> 
> entity (INPUT): Deﬁnes the material entity for which the energy oﬀsets will
> 
> be returned.
> 
> ElectronOﬀs (OUTPUT): Energy oﬀset of the electronic part of the EOS.
> 
> IonOﬀs (OUTPUT): Energy oﬀset of the ionic part of the EOS.
> 
> 40

### [FEOS-Package-Documentation2016.pdf] 第 41 页

> This routine returns the speciﬁc energy and Helmholtz free energy oﬀsets of
> the electronic and the ionic part of the EOS. These oﬀsets assure that the
> energies are zero at the reference point ρo and To.
> 
> —————————————————————————————————
> 
> void FEOS Get Binodal( int entity, double* T, double* P, double* Rholiq,
> 
> double* Rhovap, double* Pliq, double* Pvap, double* Gliq,
> double* Gvap, double* Hliq, double* Hvap, double* Zliq,
> double* Zvap, double* Tboil )
> 
> FEOS GET BINODAL( entity, T, P, Rholiq, Rhovap, Pliq, Pvap, Gliq,
> 
> Gvap, Hliq, Hvap, Zliq, Zvap, Tboil )
> 
> integer(4) :: entity
> 
> real(8) :: T(numofMaxwelliso), P(numofMaxwelliso), Rholiq(numofMaxwelliso),
> 
> Rhovap(numofMaxwelliso), Pliq(numofMaxwelliso),
> Pvap(numofMaxwelliso), Gliq(numofMaxwelliso),
> Gvap(numofMaxwelliso), Hliq(numofMaxwelliso),
> Hvap(numofMaxwelliso), Zliq(numofMaxwelliso),
> Zvap(numofMaxwelliso), Tboil
> 
> entity (INPUT): Deﬁnes the material entity for which the binodal will be
> 
> returned.
> 
> T (OUTPUT): Array of size ”numofMaxwelliso” which contains all the tem-
> 
> peratures for which the Maxwell construction has been calculated.
> 
> P (OUTPUT): Array of size ”numofMaxwelliso” containing the calculated
> 
> saturated vapor pressures.
> 
> Rholiq (OUTPUT): Array of size ”numofMaxwelliso” containing the densi-
> 
> ties on the liquid branch of the binodal.
> 
> Rhovap (OUTPUT): Array of size ”numofMaxwelliso” containing the den-
> 
> sities on the vapor branch of the binodal.
> 
> Pliq (OUTPUT): Array of size ”numofMaxwelliso” containing the pressures
> on the liquid branch of the binodal. For a Maxwell construction of
> good quality this array should correspond to the pressures on the vapor
> branch of the binodal and to the saturated vapor pressures.
> 
> 41

### [FEOS-Package-Documentation2016.pdf] 第 42 页

> Pvap (OUTPUT): Array of size ”numofMaxwelliso” containing the pressures
> on the vapor branch of the binodal. For a Maxwell construction of good
> quality this array should correspond to the pressures on the liquid
> branch of the binodal and to the saturated vapor pressures.
> 
> Gliq (OUTPUT): Array of size ”numofMaxwelliso” containing the speciﬁc
> Gibbs free energies on the liquid branch of the binodal. For a Maxwell
> construction of good quality this array should correspond to the spe-
> ciﬁc Gibbs free energies on the vapor branch of the binodal.
> 
> Gvap (OUTPUT): Array of size ”numofMaxwelliso” containing the speciﬁc
> Gibbs free energies on the vapor branch of the binodal. For a Maxwell
> construction of good quality this array should correspond to the spe-
> ciﬁc Gibbs free energies on the liquid branch of the binodal.
> 
> Hliq (OUTPUT): Array of size ”numofMaxwelliso” containing the speciﬁc
> 
> enthalpies on the liquid branch of the binodal.
> 
> Hvap (OUTPUT): Array of size ”numofMaxwelliso” containing the speciﬁc
> 
> enthalpies on the vapor branch of the binodal.
> 
> Zliq (OUTPUT): Array of size ”numofMaxwelliso” containing the compress-
> 
> ibility factors on the liquid branch of the binodal.
> 
> Zvap (OUTPUT): Array of size ”numofMaxwelliso” containing the com-
> 
> pressibility factors on the vapor branch of the binodal.
> 
> Tboil (OUTPUT): Boiling temperature which corresponds to the tempera-
> 
> ture with saturated vapor pressure = 1 bar.
> 
> This routine returns several thermodynamic quantities on the liquid-vapor
> two-phase boundary (binodal). Attention: This data is only available if the
> Maxwell construction was initialized in FEOS Init Mat for the entity under
> consideration (”Maxwellﬂag” = 1).
> 
> —————————————————————————————————
> 
> void FEOS Get Spinodal( int entity, double* T, double* RhoMin,
> 
> double* RhoMax, double* PMin, double* PMax )
> 
> FEOS GET SPINODAL( entity, T, RhoMin, RhoMax, PMin, PMax )
> 
> integer(4) :: entity
> 
> 42

### [FEOS-Package-Documentation2016.pdf] 第 43 页

> real(8) :: T(numofMaxwelliso), RhoMin(numofMaxwelliso),
> 
> RhoMax(numofMaxwelliso), PMin(numofMaxwelliso),
> PMax(numofMaxwelliso)
> 
> entity (INPUT): Deﬁnes the material entity for which the spinodal will be
> 
> returned.
> 
> T (OUTPUT): Array of size ”numofMaxwelliso” which contains all the tem-
> 
> peratures for which the Maxwell construction has been calculated.
> 
> RhoMin (OUTPUT): Array of size ”numofMaxwelliso” which contains all
> 
> the densities of the van der Waals loop minima.
> 
> RhoMax (OUTPUT): Array of size ”numofMaxwelliso” which contains all
> 
> the densities of the van der Waals loop maxima.
> 
> PMin (OUTPUT): Array of size ”numofMaxwelliso” which contains all the
> 
> pressures of the van der Waals loop minima.
> 
> PMax (OUTPUT): Array of size ”numofMaxwelliso” which contains all the
> 
> pressures of the van der Waals loop maxima.
> 
> This routine returns the minimal and maximum pressures on the van der
> Waals loops of the isotherms the Maxwell construction has been calculated
> for. The corresponding curve is also called the spinodal. Attention: This data
> is only available if the Maxwell construction was initialized in FEOS Init Mat
> for the entity under consideration (”Maxwellﬂag” = 1).
> 
> —————————————————————————————————
> 
> void FEOS Get Pmin Pmax( int entity, double T, double* RhoMin,
> 
> double* RhoMax, double* PMin, double* PMax )
> 
> FEOS GET PMIN PMAX( entity, T, RhoMin, RhoMax, PMin, PMax )
> 
> integer(4) :: entity
> 
> real(8) :: T, RhoMin, RhoMax, PMin, PMax
> 
> entity (INPUT): Deﬁnes the material entity for which the minimum and
> 
> maximum pressures shall be calculated.
> 
> T (INPUT): Temperature for which the minimum and maximum pressures
> 
> 43

### [FEOS-Package-Documentation2016.pdf] 第 44 页

> will be calculated.
> 
> RhoMin (OUTPUT): Density of the van der Waals loop minima.
> 
> RhoMax (OUTPUT): Density of the van der Waals loop maxima.
> 
> PMin (OUTPUT): Pressure of the van der Waals loop minima.
> 
> PMax (OUTPUT): Pressure of the van der Waals loop maxima.
> 
> This routine allows to calculate the minimal and maximum pressures on the
> van der Waals loop for a given temperature. One has to assure that the input
> temperature lies below the critical point.
> 
> 44

### [FEOS-Package-Documentation2016.pdf] 第 45 页

> The FEOS Table Generation
> Tool
> 
> 13 Generation of EOS Tables
> 
> The FEOS table generation tool allows for a quick access to the FEOS library
> in order to generate a new equation-of-state table of one material. Figure 5
> gives an overview of the tool’s operational sequence.
> 
> The parameters which are required for a calculation must be set in a param-
> eter ﬁle (Section 4). Thus, in order to start a calculation one ﬁrst should
> make a copy of one of the parameter ﬁles given as examples in the direc-
> tory /EOS-Data. Then this ﬁle must be modiﬁed according to the desired
> properties and precision. Obligatory parameters are explained in Section 15.
> 
> The new parameter ﬁle must be located together with the executable ”feos”
> generated during the FEOS package installation (Section 3), the material
> parameter database ﬁle and the TF table ﬁle in one directory (usually in
> /EOS-Data). The executable is started with the parameter ﬁle name (with-
> out suﬃx ”.par”!) as argument. As an example, for the parameter ﬁle
> ”Aluminum.par” the command ”./feos Aluminum” must be used. The name
> of the parameter ﬁle will be also the name of the EOS table output ﬁles.
> 
> 13.1 Additional Features
> 
> Besides the calculation of EOS tables the tool allows for two other options:
> 
> 1. Single Point Information: If the EOS shall be calculated only for one
> given density-temperature point, then as an example for ρ = 2.0 g/cm3,
> T = 100 eV, and for the parameter ﬁle ”Aluminum.par” the user must
> execute the command ”./feos Aluminum 2.0e0 1.0e2”. The single point
> information will be printed out directly onto the console.
> 
> 2. User-deﬁned calculations: If executed in the table and not in the single
> point information modus, the code allows to call user-deﬁned routines
> for simple and short calculations. How and where these routines have
> to be deﬁned and called is explained in Section 17.
> 
> 45

### [FEOS-Package-Documentation2016.pdf] 第 46 页

> Figure 5: Operational sequence of the FEOS table generation tool.
> 
> 46

### [FEOS-Package-Documentation2016.pdf] 第 47 页

> 14 Source Code Structure
> 
> The FEOS tool’s source code consists of four ﬁles listed in Table 4.
> 
> FE-00 DEFINITS.H
> 
> Deﬁnitions used by the FEOS tool
> 
> FE-01 TABTOOLS.C
> 
> Routines for writing output ﬁles and for
> generating the density and temperature
> grids
> 
> FE-02 CALCULATIONS.C User-deﬁned routines for ”simple” calcula-
> tions using the FEOS library and/or the cal-
> culated tables
> 
> FE-03 MAIN.C
> 
> Main ﬁle of the FEOS tool
> 
> Table 4: Source ﬁles of the FEOS table generation tool.
> 
> The main routine of the tool is located in the source ﬁle ”FE-03 MAIN.C”.
> Users which want to use the FEOS library directly maybe interested in the
> main routine of the FEOS tool since it demonstrates the usage of nearly all
> of the library interface routines.
> 
> The ﬁle ”FE-01 TABTOOLS.C” contains the routines (”getPointDensity(...)”
> and ”makeRTPointArray(...)”) which are used to create the density-temperature
> grid. Furthermore, all the table output ﬁle routines (Section 16) are located
> there.
> 
> In the ﬁle ”FE-02 CALCULATIONS.C” the user can add own routines for
> (short and simple) calculations accessing the calculated table data or the
> library interface routines (Section 17).
> 
> 15
> 
> Input Parameters
> 
> The variables for a calculation with the FEOS table generation tool are
> located in the ﬁrst part (sections ”Computation-Settings” and ”Q-table”) of
> a parameter ﬁle (Section 4). Table 5 lists all necessary settings.
> 
> One should keep in mind that for any calculation, the physical parameters of
> the material must be present with a corresponding material number in the
> material parameter database (Section 10). Especially, if one wants to use the
> 
> 47

### [FEOS-Package-Documentation2016.pdf] 第 48 页

> Material-Number
> 
> Number of the material in the FEOS material
> parameter database
> 
> Maxwell Flag
> 
> Maxwell construction desired? (0: no, 1: yes)
> 
> SoftSphere Flag
> 
> Replace TF cold curve and bonding correction for
> ρ < ρo with soft-sphere function? (0: no, 1: yes)
> 
> UserCalculations Flag Perform user-deﬁned calculations? (0: no, 1: yes)
> 
> Rhonorm
> 
> Rhoratio x
> 
> Tnorm
> 
> Tratio x
> 
> Density norm in g/cm3
> 
> of
> 
> logarithmically equidistant dis-
> Number
> tributed density points in range Rhonorm·10x−1
> to Rhonorm·10x, x=-6...6; Attention: The lower
> density library limit should not be violated!
> 
> Temperature norm in eV
> 
> of
> 
> temperature
> 
> logarithmically
> 
> equidistant
> Number
> range
> in
> distributed
> Tnorm·10x−1
> to Tnorm·10x,
> x=-6...6; At-
> tention: The lower temperature library limit
> should not be violated!
> 
> points
> 
> Table 5: Settings in the parameter ﬁle for the FEOS table generation tool
> 
> (sections ”Computation-Settings” and ”Q-table”).
> 
> soft-sphere function, the corresponding parameters must be available.
> 
> To calculate a table with a Maxwell construction (Section 6.6) one should
> take care of the quality of the critical data calculation which depends strongly
> on the choice of the temperature grid density in the two-phase region. One
> should not be too thrifty spending mesh points. The Maxwell construction
> is set-up during the library material initialization stage with the same tem-
> peratures which are used later on to calculate the EOS table.
> 
> If the UserCalculations Flag is set to 1 the routines deﬁned in the ﬁle ”FE-
> 02 CALCULATIONS.C” will be performed (Section 17).
> 
> Finally, it is important to take care of the lower density and temperature ﬂoor
> of the library (Section 6.1) when deﬁning the density-temperature mesh.
> If points are deﬁned below these limits, the EOS will not be consistent.
> Nevertheless, the FEOS table generation tool automatically adds T = 0.0 eV
> and ρ = 0.0 g/cm3 to the density-temperature mesh.
> 
> 48

### [FEOS-Package-Documentation2016.pdf] 第 49 页

> 16 EOS Table Structure
> 
> 16.1 Qtable / CriticalDataTable Structures
> 
> The FEOS table generation tool stores the calculated EOS data and the crit-
> ical data information (thermodynamic quantities on the vaporization curve)
> in two separate structures. Therefore, these structures contain several arrays
> and are deﬁned in the ﬁle ”COMMON-00 DEFINITS.H”. The structure type
> ”Qtable” contains the arrays for the calculated EOS table. The name of the
> most important arrays and their index ranges are listed in Table 6.
> 
> NRho, NT, Nelements Number of densities, temperatures, and elements
> 
> in the material
> 
> A[k], Z[k], X[k]
> 
> Atot, Ztot, Xtot
> 
> T[j]
> 
> Rho[i]
> 
> Atomic weights, atomic numbers and number
> of atoms per ”molecule” for all elements in the
> material
> Summed-up values: Atot=(cid:80) X[k] A[k], ...
> 
> Temperatures
> 
> Densities
> 
> P[i][j] (Pe, Pi, PTF)
> 
> Pressures (separate for EOS components)
> 
> E[i][j] (Ee, Ei, ET)
> 
> Speciﬁc energies (separate for EOS components)
> 
> S[i][j] (Se, Si, STF)
> 
> Speciﬁc entropies (separate for EOS components)
> 
> F[i][j] (Fe, Fi, FTF)
> 
> Speciﬁc Helmholtz free energies (separate for
> EOS components)
> 
> Q[i][j][k]
> 
> Qtot[i][j]
> 
> Charge states for all elements in the material
> 
> Summed-up (not mean!) charge states for one
> ”molecule” (=(cid:80) X[k] Q[i][j][k])
> 
> Table 6: Most important variables and arrays stored in the ”Qtable” struc-
> ture. The indizes cover the following ranges: k=0..Nelements-1,
> j=0..NT-1, i=0..NRho-1.
> 
> The critical data information is stored in a structure type ”CriticalDataT-
> able”. This type is explained in Table 7.
> 
> 49

### [FEOS-Package-Documentation2016.pdf] 第 50 页

> Niso
> 
> Number of calculated isotherms below the critical
> point
> 
> Rhoc, Pc, Tc, Hc
> 
> Density, pressure, temperature, and speciﬁc en-
> thalpy at the critical point
> 
> Tiso[i]
> 
> Peq[i]
> 
> Temperatures
> 
> Saturated vapor pressures
> 
> Pmax[i], Pmin[i]
> 
> Minimum and maximum pressures on the van-der-
> Waals loops
> 
> Rhomax[i], Rhomin[i] Densities which correspond to the pressure minima
> 
> and maxima
> 
> Rhol[i], Rhov[i]
> 
> Hl[i], Hv[i]
> 
> Densities on the liquid and the vapor branch of the
> binodal
> 
> Speciﬁc enthalpies on the liquid and the vapor
> branch of the binodal
> 
> Table 7: Most important variables and arrays stored in the ”CriticalDataT-
> able” structure. The index i covers the following range: i=0..Niso-1.
> 
> 16.2 FEOS Format
> 
> The standard table output format of the FEOS table generation tool is a
> ASCII ﬁle with the extension ”.feos”. This type of ﬁle contains all informa-
> tion about the composition of the material, the calculation parameters and
> the calculated EOS table in the FEOS standard units (Section 5) itself. The
> format was designed to be used by the SHOWEOS table visualization tool
> and thus, it contains the whole set of calculated EOS data. In contrast to
> the SESAME format the ﬁle contains the complete EOS, all contributions
> to the EOS (electronic, ionic, Thomas-Fermi), and all thermodynamic func-
> tions (also the charge state). The FEOS format is controlled by the routine
> ”write FEOS format(...)” in the source ﬁle ”FE-01 TABTOOLS.C”.
> 
> 16.3 SESAME Formats
> 
> The FEOS table generation tool also writes tables in the SESAME-301, -
> 304, and -305 formats with ﬁle extensions ”.301”, ”.304”, and ”.305”. The
> 
> 50

### [FEOS-Package-Documentation2016.pdf] 第 51 页

> SESAME EOS library is a widely known set of equation-of-state tables for
> various materials, produced by the Los Alamons National Laboratory [19].
> SESAME-301 tables contain information about the total pressure, speciﬁc
> energy, and speciﬁc Helmholtz free energy of a given material as functions
> of density and temperature. SESAME-304/305 tables contain the same
> information, but for the electronic/ionic contributions. The tables in the
> SESAME database are based on experimental results as well as on theoret-
> ical models, sometimes on both. Additional information, for example about
> the vaporisation curve etc., is usually available in extra archive ﬁles (in case
> of FEOS this data is written to other formats).
> 
> A typical SESAME table is an ASCII-ﬁle consisting of several lines which
> contain four words each, where each word is a real number.
> Its ﬁrst line
> contains a material code, the solid density of the material described (in cgs
> units), the number of points on the density mesh (as real number), and the
> number of points on the temperature mesh (as real number), example:
> 
> 3717
> 
> 2.70000000e+00 1.92000000e+02 7.30000000e+01
> 
> The next few lines contain information about the density mesh (Rho[I],
> I=1...NI) and the temperature mesh (T[J], J=1...NJ):
> 
> 0.00000000e+00 2.70000000e-07 5.81697366e-07 2.70000000e-06 ...
> 
> The next lines contain all pressure isotherms, ((P[I,J], I=1..NI), J=1..NJ),
> then speciﬁc energy and speciﬁc Helmholtz free energy isotherms in the same
> manner as for the pressure.
> 
> The units used in the SESAME library are:
> 
> • Pressure: GPa
> 
> • Energy: MJ/kg
> 
> • Density: g/cm3
> 
> • Temperature: Kelvin
> 
> In ”FE-01 TABTOOLS.C” the routines ”write 301(304,305) format(...)” are
> responsible for the ﬁle output of the SESAME tables. Furthermore, the rou-
> tine ”write mexport format(...)” writes the SESAME mexport format (ex-
> tension ”.mexport”). The mexport format is a database ﬁle which usually
> 
> 51

### [FEOS-Package-Documentation2016.pdf] 第 52 页

> contains all the EOS tables (301,...) of all materials from the SESAME
> database. In the case of the FEOS table generation tool the mexport ﬁle of
> course contains only the 301, 304, and 305 tables of the calculated material.
> 
> 16.4 Other Output Formats
> 
> Besides the FEOS and the SESAME output formats, two other formats are
> written to ﬁles. The ﬁrst one, the txt format with ﬁle extension ”.data.txt”
> (routine ”write txt format” in ”FE-01 TABTOOLS.C”) contains pressure-
> energy isotherms as function of mass density. The second one, the Rostock
> format with ﬁle extension ”.cst” (routine ”write Rostock format(...)” in ”FE-
> 01 TABTOOLS.C”) contains pressure-charge state isotherms as function of
> particle density and mass density.
> 
> If a material is initialized with a Maxwell construction (Section 6.6), the
> FEOS table generation tool also writes out the information from the Criti-
> calDataTable structure (Section 16.1). The corresponding output ﬁle (rou-
> tine ”write criticaldata(...)” in ”FE-01 TABTOOLS.C”) has the extension
> ”.critical.dat”and contains the following information:
> 
> • Critical point data
> 
> • Boiling temperature
> 
> • Information about the accuracy of the Maxwell construction
> 
> • Binodal and spinodal in ρ-p-plane
> 
> • Binodal, spinodal, and diamener curve in T -ρ-plane
> 
> • Binodal in T -H-plane (speciﬁc enthalpy)
> 
> • Evaporation heat ∆H in T -∆H-plane
> 
> • Saturation curve in Arrhenius coordinates
> 
> • Compressibility factor on the binodal as function of temperature and
> 
> pressure
> 
> If the user wants to add a own table format to the FEOS table generation
> tool, a corresponding routine which may access the ”Qtable” and/or ”Crit-
> icalDataTable” structures (Section 16.1) must be added to the source ﬁle
> 
> 52

### [FEOS-Package-Documentation2016.pdf] 第 53 页

> ”FE-01 TABTOOLS.C” and the corresponding header ﬁle. The new routine
> must be called with appropriate arguments (together with the other out-
> put routines) at the end of step 4b in the main function in the source ﬁle
> ”FE-03 MAIN.C”.
> 
> 17 User-Deﬁned Calculations
> 
> The FEOS table generation tool provides an extra source ﬁle for the user
> reserved for routines which access the calculated EOS table and/or call the
> FEOS interface routines. The advantage of this special option is that the user
> can beneﬁt for ”simple” calculations from an existing infrastructure for the
> initialization of the FEOS library and of an EOS table. For more complicated
> calculations of course it may become necessary that the user writes a fully
> new program which calls the FEOS library from the beginning.
> 
> The user-deﬁned routines are all located and called by the routine ”User-
> Calculations(...)” in the source ﬁle ”FE-02 CALCULATIONS.C”. Four ar-
> guments maybe passed by the ”UserCalculations(...)” routine, nameley the
> entitynumber of the material (for the FEOS table generation tool normally
> always 1), the name of the parameter ﬁle, and the stored data in the ”Qtable”
> and ”CriticalDataTable” structures (Section 16.1).
> 
> If a new routine needs the Maxwell construction data, the user should make
> sure that it was calculated before by checking the integer ”Niso” in the ”Crit-
> icalDataTable” structure to be greater than zero.
> 
> 17.1
> 
> Isobaric Expansion Data
> 
> One (exemplary) application comes already with the delivery version of the
> FEOS package. The routine ”IsobaricExpansion(...)” can be used for the
> calculation of thermodynamic functions along the isobaric curve p = 0 of the
> metastable EOS (without Maxwell construction) up to the spinodal limit
> which means: up to that temperature for which the van-der-Waals loop does
> not cross p = 0 anymore. The minimum and maximum temperatures, as
> well as the number of linearly equidistant distributed temperature points are
> set at the beginning of the routine ”IsobaricExpansion(...)”. The following
> data is calculated along the isobaric curve and written to an output ﬁle with
> extension ”.isobaric.dat”:
> 
> 53

### [FEOS-Package-Documentation2016.pdf] 第 54 页

> • Temperatures T
> 
> • Densities ρ
> 
> • Pressures p (for checking accuracy only)
> 
> • Thermal expansion coeﬃcients α
> 
> • Speciﬁc enthalpies H
> 
> • Speciﬁc isobaric heat capacities Cp
> 
> This data, especially the expansion coeﬃcient, can be helpful for the adjust-
> ment of the soft-sphere function parameters (Section 6.7) of a new material
> entry in the material parameter database.
> 
> 54

### [FEOS-Package-Documentation2016.pdf] 第 55 页

> The SHOWEOS Table
> Visualization Tool
> 
> 18 Visualization of EOS Tables
> 
> SHOWEOS is a tool for calculating plots of the EOS tables generated with
> the FEOS table generation tool. The tool is designed for table ﬁles which
> are present in the FEOS format (Section 16.2) with extension ”.feos”. Al-
> ternatively, the SESAME ﬁle format (Section 16.3) with extensions ”.301”,
> ”.304”, and ”.305” can be loaded. The latter feature provides the option to
> visualize also tables from the SESAME database and to compare them with
> the corresponding FEOS tables.
> 
> Figure 6 shows the general operational sequence of the tool. In order to start
> a calculation one ﬁrst must ensure that the executable ”showeos” generated
> during the FEOS package installation (Section 3), the parameter ﬁle with
> 
> Figure 6: Operational sequence of the SHOWEOS table visualization tool.
> 
> 55

### [FEOS-Package-Documentation2016.pdf] 第 56 页

> extension ”.par” (Section 4), and the table ﬁle, which must have the same
> name as the parameter ﬁle, are located in the same directory (usually /EOS-
> Data). Usually, the same parameter ﬁle which was used for the generation of
> the table with the FEOS table generation tool contains also the parameters
> for SHOWEOS. Only if a table from the SESAME database shall be visual-
> ized, a new parameter ﬁle must be created. The name of the parameter ﬁle
> will be also the name of the output ﬁle(s).
> 
> The executable ”showeos” is started with two arguments. The ﬁrst argu-
> ment is the name of the parameter ﬁle (without suﬃx ”.par”!). The second
> argument is an integer number between 1 and 6 which deﬁnes the type of
> the calculation which will be done. As an example, for the parameter ﬁle
> ”Aluminum.par” and option number 3 one has to execute the command
> ”./showeos Aluminum 3”. Table 8 explains the meaning of the six available
> options. The corresponding procedures and settings in the parameter ﬁle are
> explained in Section 20. Options 1-3 are collected under the umbrella term
> ”Isocurves”.
> 
> 1 Calculate isotherms (lines of constant temperature)
> 
> 2 Calculate isochores (lines of constant density)
> 
> 3 Calculate isentropes (lines of constant speciﬁc entropy)
> 
> 4 Calculate mountain plot (three-dimensional plot of thermodynamic
> quantity as function of density / speciﬁc volume and temperature)
> 
> 5 Calculate Hugoniot curve [16]
> 
> 6 Print out single point information
> 
> Table 8: Calculational options provided by the SHOWEOS table visualiza-
> 
> tion tool.
> 
> Once the tool has been started, ﬁrst the general parameters (Section 20.1) are
> read from the parameter ﬁle, then the appropriate EOS table ﬁle is loaded,
> and ﬁnally the desired option is performed. For options 1-5 the information is
> printed out into an ASCII ﬁle which then again can be loaded by a plotting
> tool. Here, the user has to take care by himself/herself of the format of
> the ASCII ﬁle by modifying the routine which is responsible for the desired
> option. Finally, although SHOWEOS, like the other parts of the package,
> internaly uses the FEOS standard units, the units of the SHOWEOS input
> parameters and of the quantities written to the output ﬁle(s) can be changed
> and have to be speciﬁed in the parameter ﬁle (Section 20.1).
> 
> 56

### [FEOS-Package-Documentation2016.pdf] 第 57 页

> 19 Source Code Structure
> 
> The SHOWEOS tool’s source code consists of ﬁve ﬁles listed in Table 9.
> 
> SE-00 DEFINITS.H
> 
> Deﬁnitions for the output ﬁles of the
> SHOWEOS tool
> 
> SE-01 READTABLE.C
> 
> Routines for reading EOS table ﬁles
> 
> SE-02 INTERPOLTOOLS.C Routines for table interpolations
> 
> SE-03 SERVICES.C
> 
> SE-04 MAIN.C
> 
> ”Working” routines for isocurves, Hugo-
> niots, etc.
> 
> Main ﬁle and main routine of
> SHOWEOS tool
> 
> the
> 
> Table 9: Source ﬁles of the SHOWEOS table visualization tool.
> 
> The main routine of the tool is located in the source ﬁle ”SE-04 MAIN.C”.
> The ﬁle ”SE-01 READTABLE.C” contains the routines which are used to
> read and load the EOS tables. In the ﬁle ”SE-03 SERVICES.C” the ”work-
> ing” routines which are responsible for the diﬀerent options of the tool are
> located. In these routines the user must adjust the output ﬁle write state-
> ments to ﬁt the requirements of the used plotting tool.
> 
> 20
> 
> Input Parameters and Procedures
> 
> The variables for a calculation with the SHOWEOS table visualization tool
> are located in the second part of a parameter ﬁle (Section 4). The SHOWEOS
> parameters are separated into two categories: 1) the obligatory parameters
> which are used by all options of the tool and are explained in Section 20.1
> and 2) the facultative parameters which are only used if the corresponding
> option is performed (Sections 20.2, 20.3, 20.4, and 20.5).
> 
> 20.1 General Settings
> 
> In a parameter ﬁle three sections ”General”, ”Units”, and ”Rho-T-Mesh”
> contain parameters which are (partially) used by all options of the SHOWEOS
> 
> 57

### [FEOS-Package-Documentation2016.pdf] 第 58 页

> tool. The parameters of the ”General” and ”Units” sections are explained in
> Table 10.
> 
> File-Format Type of table ﬁle (1: FEOS format, 2: SESAME format)
> 
> EOS-Type
> 
> Type of EOS (1: total, 2: electronic, 3: ionic, 4: Thomas-
> Fermi)
> 
> Rho unit
> 
> Density unit (1.0 → g/cm3)
> 
> T unit
> 
> P unit
> 
> E unit
> 
> U unit
> 
> Temperature unit (1.0 → eV, 8.61753e-5 → K)
> 
> Pressure unit (1.0 → dyne/cm2, 1.0e12 → MBar)
> 
> Energy unit (1.0 → erg/g, 1.0e10 → MJ/kg)
> 
> Velocity unit (1.0 → cm/s, 1.0e5 → km/s)
> 
> Table 10: Settings in the parameter ﬁle for the SHOWEOS table visualiza-
> 
> tion tool (sections ”General” and ”Units”).
> 
> The parameter ”EOS-Type” controls whether the complete or the electronic
> / ionic / pure Thomas-Fermi contribution shall be loaded. While the FEOS
> formatted ﬁles (Section 16.2) contain all the required data, for the complete
> EOS as well as for the contributions, a SESAME table ﬁle does not. In this
> case the SHOWEOS tool automatically chooses the appropriate ﬁle exten-
> sion (”.301”, ”.304”, or ”.305”) depending on the ”EOS-Type” parameter.
> Note, that the option ”EOS-Type=4” is not available for SESAME tables.
> Furthermore, one should keep in mind that the SESAME table ﬁles which
> can be loaded contain no information about the charge state.
> 
> The unit parameters are set in such a way that the value corresponds to a
> multiplication factor of the FEOS standard units (Section 5). All input has
> to be deﬁned and all output quantities are printed-out in the deﬁned units.
> The units of the speciﬁc Helmholtz free energy, the speciﬁc entropy, and the
> speciﬁc volume are determined from the other unit settings. The unit of the
> charge state is ﬁxed in terms of multiples of the unit electron charge.
> 
> Table 11 lists all parameters of the ”Rho-T-Mesh” section. This section
> is important for all SHOWEOS options, except for the single point infor-
> mation and the Hugoniot option. The corresponding parameters deﬁne the
> strucuture of the density-temperature grid. The user can choose whether the
> original densities and temperatures from the table ﬁle shall be used, or a new
> mesh with linearly or logarithmically equidistant distributed points shall be
> created.
> 
> 58

### [FEOS-Package-Documentation2016.pdf] 第 59 页

> Rhomin, Tmin
> 
> Rhomax, Tmax
> 
> Minimum density / temperature (in units deﬁned
> in section ”Units”)
> 
> Maximum density / temperature (in units deﬁned
> in section ”Units”)
> 
> Rhooriginal, Toriginal Use only original tabulated densities / tempera-
> 
> tures? (0: no, 1: yes)
> 
> Rhonumber, Tnumber Number of densities / temperatures if Rhoorigi-
> nal / Toriginal is set to 0
> 
> Rholog, Tlog
> 
> Rhoﬁrst, Tﬁrst
> 
> Kind of distribution if Rhooriginal / Toriginal is
> set to 0 (0: linear, 1: logarithmical)
> 
> Only for isotherms, isochores, or Mountain plots:
> Print out lowest density / temperature of table?
> (0: no, 1: yes)
> 
> Table 11: Settings in the parameter ﬁle for the SHOWEOS table visualiza-
> 
> tion tool (section ”Rho-T-Mesh”).
> 
> 20.2 Isocurves
> 
> For the ﬁrst three options of the SHOWEOS table visualization tool (calcula-
> tion of isotherms, isochores, or isentropes) the parameters from the parameter
> ﬁle section ”Isocurves” are read. The corresponding settings are explained
> in Table 12.
> 
> Xquantity, Yquantity Quantity which is printed out on the x-axis / y-
> axis (1,2,3,...,8 → Table 13)
> 
> Xelement, Yelement
> 
> For charge state of mixtures (Xquantity=8 /
> Yquantity=8): element number or 0 for summed-
> up value
> 
> Table 12: Settings in the parameter ﬁle for the SHOWEOS table visualiza-
> 
> tion tool (section ”Isocurves”).
> 
> The user must choose which quantities shall be plotted on the x- and on
> the y-axis. Therefore, the diﬀerent thermodynamic quantities correspond to
> number between 1 and 8 (Table 13). If the charge state shall be plotted for
> a mixture, the user must decide whether the charge state shall be plotted
> for a participating element or summed up for a ”molecule” of the mixture.
> 
> 59

### [FEOS-Package-Documentation2016.pdf] 第 60 页

> Attention: The charge state is only available for the FEOS table format and
> not for the supported SESAME table ﬁles.
> 
> 1 Density
> 
> 2 Speciﬁc volume
> 
> 3 Temperature
> 
> 4 Pressure
> 
> 5 Speciﬁc internal energy
> 
> 6 Speciﬁc Helmholtz free energy
> 
> 7 Speciﬁc entropy
> 
> 8 Summed-up or single-element charge state
> 
> Table 13: Possible quantity choices.
> 
> The output ﬁle will be an ASCII ﬁle with the same name as the parameter
> ﬁle. The ﬁrst part of the ﬁle extension is composed of the names of the
> plotted quantities on the x- and on the y-axis. The second and last part
> of the extension denotes the type of isocurve: ”.ist” for isotherms, ”.isc” for
> isochores, and ”.ise” for isentropes. In the delivery version of the SHOWEOS
> tool successive isocurves inside the ASCII ﬁle are divided by an ”&” sign.
> Each isocurve contains a headline with information of the plotted quantities
> and units. This sort of ﬁle can be graphically visualized with the Unix tool
> xmgrace, for example.
> 
> For isotherms, the plotted temperatures are given by the temperature grid
> which was set-up in the section ”Rho-T-Mesh” (Section 20.1). For isochores,
> the plotted densities are given by the density grid. For isentropes, the used
> entropies are calculated for the lowest density and for all temperatures of the
> density-temperature grid.
> 
> 20.3 Mountain Plots
> 
> For showing total phase planes which means some quantity (parameter ”Quan-
> tity”) as a function of density or speciﬁc volume (parameter ”Xquantity”)
> and temperature in a three-dimensional diagram, one has to make speciﬁ-
> cations in the parameter ﬁle section ”Mountain” (Table 14). The densities
> and temperatures are given by the density-temperature grid (Section 20.1).
> 
> 60

### [FEOS-Package-Documentation2016.pdf] 第 61 页

> The output ﬁle will be an ASCII ﬁle with the same name as the parameter
> ﬁle. The ﬁle ﬁrst contains the density and temperature grid and then a list
> of isochores of the desired quantity. The ﬁrst part of the ﬁle extension is
> composed of the names of the plotted quantities on the x-, y-, and z-axis.
> The second and last part of the extension is ”.mnt”.
> 
> Xquantity Quantity which is printed out on the x-axis (1: density, 2:
> 
> speciﬁc volume)
> 
> Quantity Mountain quantity as function of Xquantity and temperature
> 
> (4,5,6,7,8 → Table 13)
> 
> Element
> 
> For charge state of mixtures (Quantity=8): element number
> or 0 for summed-up value
> 
> Table 14: Settings in the parameter ﬁle for the SHOWEOS table visualiza-
> 
> tion tool (section ”Mountain”).
> 
> 20.4 Hugoniots
> 
> For computing a Hugoniot curve [16] the corresponding settings in the pa-
> rameter ﬁle section ”Hugoniot” must be speciﬁed (Table 15). The user must
> set the initial density and temperature where the Hugoniot curve calcula-
> tion shall start. Furthermore, a maximum pressure must be set to limit the
> calculation. The stepsizes for the calculation and for the print-out can be
> changed in the source code header ﬁle ”SE-03 SERVICES.H”. The output
> ﬁle will be an ASCII ﬁle with the same name as the parameter ﬁle and ex-
> tension ”.hug”. The ﬁle contains the density or speciﬁc volume (parameter
> ”Xquantity”), the temperature, the pressure, the speciﬁc internal energy, the
> shock wave velocity, and the particle velocity behind the shock wave.
> 
> Rho0
> 
> T0
> 
> Initial density (in units deﬁned in section ”Units”)
> 
> Initial temperature (in units deﬁned in section ”Units”)
> 
> Pmax
> 
> Maximum pressure (in units deﬁned in section ”Units”)
> 
> Xquantity Quantity which is printed out on the ”x-axis” (1: density, 2:
> 
> speciﬁc volume)
> 
> Table 15: Settings in the parameter ﬁle for the SHOWEOS table visualiza-
> 
> tion tool (section ”Hugoniot”).
> 
> 61

### [FEOS-Package-Documentation2016.pdf] 第 62 页

> 20.5 Single Point Information
> 
> A single point information for a given density and temperature can be printed
> out with the option 6 of the SHOWEOS table visualization tool. The density
> and the temperature in the units deﬁned in the parameter ﬁle section ”Units”
> must be passed as a third and a fourth argument in the command line call
> of SHOWEOS. As an example, for the parameter ﬁle ”Aluminum.par”, the
> value 1.0 for the temperature and density units in the parameter ﬁle, den-
> sity 0.3 g/cm3, and temperature 10 eV one has to execute the command
> ”./showeos Aluminum 6 0.3 1.e2”.
> 
> 62

### [FEOS-Package-Documentation2016.pdf] 第 63 页

> References
> 
> [1] A. Kemp and J. Meyer-ter Vehn. An equation of state code for hot
> dense matter, based on the QEOS description. Nucl. Instrum. Methods
> A, 415:674–676, 1998. 2, 8
> 
> [2] R. M. More, K. H. Warren, D. A. Young, and G. B. Zimmerman. A
> new quotidian equation of state (QEOS) for hot dense matter. Physics
> of Fluids, 31:3059, 1988. 6, 8, 11, 15, 19
> 
> [3] A. Kemp and J. Meyer-ter Vehn. Das Zustandsgleichungs-Modell QEOS
> f¨ur heisse, dichte Materie. Technical Report 229, Max-Planck-Institut
> f¨ur Quantenoptik, 1998. 6, 15, 19
> 
> [4] S. Faik, M. M. Basko, An. Tauschwitz, I. Iosilevskiy, and J. A. Maruhn.
> Dynamics of volumetrically heated matter passing through the liquid-
> vapor metastable states. High Energy Density Physics, 8(4):349–359,
> 2012. 8, 20
> 
> [5] D. A. Young and E. M. Corey. A new global equation of state model for
> hot, dense matter. Journal of Applied Physics, 78(6):3748, 1995. 11, 22
> 
> [6] L. D. Landau and E. M. Lifshitz. Statistical Physics. Butterworth
> 
> Heinemann, 3 edition, 1996. 12, 20
> 
> [7] L. H. Thomas. The calculation of atomic ﬁelds. Mathematical Proceed-
> ings of the Cambridge Philosophical Society, 23(5):542–548, 1927. 12
> 
> [8] E. Fermi. Eine statistische Methode zur Bestimmung einiger Eigen-
> schaften des Atoms und ihre Anwendung auf die Theorie des periodis-
> chen Systems der Elemente. Zeitschrift f¨ur Physik, 48:73–79, 1928. 12
> 
> [9] R. Feynman, N. Metropolis, and E. Teller. Equations of state of ele-
> ments based on the generalized Thomas-Fermi theory. Physical Review,
> 75:1561, 1949. 12, 13
> 
> [10] L. D. Landau and E. M. Lifshitz. Quantum Mechanics: Non Relativistic
> 
> Theory. Butterworth Heinemann, 3 edition, 1981. 13
> 
> [11] M. Brachmann. Thermodynamic functions on the generalized Thomas-
> 
> Fermi theory. Physical Review, 84:1263, 1951. 14
> 
> [12] S. Eliezer, A. Ghatak, and H. Hora. Fundamentals of Equations of State.
> 
> World Scientiﬁc Pub Co, 1 edition, 2002. 15, 17
> 
> 63

### [FEOS-Package-Documentation2016.pdf] 第 64 页

> [13] D. A. Kirzhnits, Y. E. Lozovik, and G. V. Shpatakovskaya. Statistical
> model of matter. Soviet Physics Uspekhi, 18(9):649–672, 1975. 15
> 
> [14] B.-G. Englert.
> 
> Semiclassical Theory of Atoms (Lecture Notes in
> 
> Physics). Springer, Berlin, 1 edition, 1988. 15
> 
> [15] W. Zittel. Elektronische Struktur hochkomprimierter Materie. Technical
> 
> Report 111, Max-Planck-Institut f¨ur Quantenoptik, 1986. 15
> 
> [16] Ya. B. Zeldovich and Yu. P. Raizer. Physics of Shock-Waves and High-
> Temperature Hydrodynamic Phenomena. Dover Pubn Inc, illustrated
> edition, 2002. 16, 56, 61
> 
> [17] J. F. Barnes. Statistical Atom Theory and the Equation of State of
> 
> Solids. Physical Review, 153(1):269–275, 1967. 16
> 
> [18] M. Ross. Generalized Lindemann Melting Law. Physical Review,
> 
> 184(1):233–242, 1969. 17
> 
> [19] T. Group. SESAME Report on the Los Alamos Equation of State Li-
> brary. Technical Report LALP-83-4, Los Alamos National Laboratory,
> 1983. 51
> 
> 64

## doc/FEOS/MPQeos-JWGU-Documentation.pdf (405553 B)

<!-- 提取说明: 共 34 页（pdfminer 解析出 35 段） -->

### [MPQeos-JWGU-Documentation.pdf] 第 1 页

> MPQeos-JWGU
> 
> A new equation-of-state code for hot dense matter
> 
> Short documentation
> 
> Version: 2.2 (November 2010)
> 
> Steﬀen Faik
> Institute for Theoretical Physics
> Goethe University Frankfurt am Main, Germany
> 
> MPQeos Version 2.0 (09/99):
> 
> A.J. Kemp and J. Meyer-ter-Vehn
> Max-Planck Institute for Quantum Optics
> Garching, Germany

### [MPQeos-JWGU-Documentation.pdf] 第 2 页

> Foreword / Contact
> 
> First of all I would like to thank Dr Anna Tauschwitz, Prof Dr Joachim
> Maruhn (both Goethe University Frankfurt am Main & GSI Darmstadt),
> and Prof Dr Igor Iosilevskiy (Joint Institute for High Temperatures Moscow
> & GSI Darmstadt) for very helpful and constructive discussions.
> 
> This present new version of MPQeos was built as a part of my diploma thesis.
> I called it MPQeos-JWGU since the university of Frankfurt is named after
> the famous German poet Johann Wolfgang von Goethe.
> It was built for
> usage at GSI – Helmholtz Center for Heavy Ion Research in Darmstadt.
> 
> At this point I want to emphasize that the manual part of this documen-
> tation is based on the original documentation of MPQeos (version 2.0) by
> A. Kemp and J. Meyer-ter-Vehn. I updated this part concerning the new
> features of MPQeos-JWGU. So, the reader does not have to read the original
> documentation of MPQeos in order to understand the new manual.
> 
> Address of the author of MPQeos-JWGU
> 
> Steﬀen Faik
> Goethe University Frankfurt am Main
> Institute for Theoretical Physics
> Max von Laue-Str. 1
> 60438 Frankfurt am Main
> 
> Room: 02.142
> Phone: +49 (0)69 798-47870
> Fax: +49 (0)69 798-47879
> faik@th.physik.uni-frankfurt.de
> http://th.physik.uni-frankfurt.de/˜faik/

### [MPQeos-JWGU-Documentation.pdf] 第 3 页

> Contents
> 
> Introduction
> 
> Physics
> 
> 1 The QEOS Model
> 
> 1.1 General Facts . . . . . . . . . . . . . . . . . . . . . . . . . . .
> 
> 1.2 Electronic EOS: TF Model . . . . . . . . . . . . . . . . . . . .
> 
> 5
> 
> 6
> 
> 6
> 
> 6
> 
> 6
> 
> 1.3 Semiempirical Bonding Correction . . . . . . . . . . . . . . . . 10
> 
> 1.4
> 
> Ionic EOS: Cowan Model . . . . . . . . . . . . . . . . . . . . . 11
> 
> 2 MPQeos-JWGU – Improvements
> 
> 14
> 
> 2.1 New Cold Curve
> 
> . . . . . . . . . . . . . . . . . . . . . . . . . 14
> 
> 2.2 Mixtures of Elements . . . . . . . . . . . . . . . . . . . . . . . 15
> 
> 2.3 Calculation of Liquid-Vapor Phase Coexistence
> 
> . . . . . . . . 15
> 
> 2.4
> 
> Isobaric Expansion Data . . . . . . . . . . . . . . . . . . . . . 17
> 
> Manual
> 
> 3 Installation
> 
> 4 Generation of EOS Tables
> 
> 5 Parameter File Structure
> 
> 6 Input Parameters
> 
> 3
> 
> 18
> 
> 18
> 
> 18
> 
> 19
> 
> 19

### [MPQeos-JWGU-Documentation.pdf] 第 4 页

> 7 EOS Table Structure
> 
> 22
> 
> 7.1 SESAME-301 Format . . . . . . . . . . . . . . . . . . . . . . . 22
> 
> 7.2 Other Output Formats . . . . . . . . . . . . . . . . . . . . . . 23
> 
> 8 Phase Coexistence Calculation
> 
> 9 Source Code Structure
> 
> 10 Visualizing EOS Tables with showeos
> 
> 23
> 
> 24
> 
> 25
> 
> 10.1 Isotherms
> 
> . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 25
> 
> 10.2 Isochores . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 26
> 
> 10.3 Mountain Plots . . . . . . . . . . . . . . . . . . . . . . . . . . 27
> 
> 10.4 Isentropes . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 27
> 
> 10.5 Hugoniots . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 28
> 
> 10.6 Single Point Information . . . . . . . . . . . . . . . . . . . . . 28
> 
> A Example Input Parameter File (Si02)
> 
> References
> 
> 29
> 
> 33
> 
> 4

### [MPQeos-JWGU-Documentation.pdf] 第 5 页

> Introduction
> 
> MPQeos-JWGU is a C++ computer code that can generate equation-of-
> state (eos) tables for, in principle, arbitrary materials at any density and
> temperature. The underlying physical model is the ’quotidian equation-of-
> state model (QEOS)’, described further in Ref. [1]. The background of the
> original code MPQeos, together with some applications, is described in a
> correspondig MPQ Report 229 [2].
> 
> The ﬁrst part of this documentation concentrates on physical aspects.
> In
> Section 1 a short description of the QEOS model is given. The improvements
> and changes which lead to the new version MPQeos-JWGU are described in
> Section 2.
> 
> The main intent of the manual (second part of this documentation) is to show
> how a user can generate an eos table with the MPQeos-JWGU code, and to
> give hints how and where to change the source code in order to customize it
> for the user’s own needs.
> 
> Together with the eos code comes another program, showeos, that can be
> used to visualize MPQeos-JWGU results, i.e. to make plots of isotherms,
> isochores, or to show two-dimensional phase planes, and for calculating Hugo-
> niot curves from eos tables or visualizing isentropes in a density-temperature
> plane. The usage of showeos is described in Section 10.
> 
> At the end of this documentation in the appendix an example input param-
> eter ﬁle for MPQeos-JWGU and showeos is presented.
> 
> 5

### [MPQeos-JWGU-Documentation.pdf] 第 6 页

> Physics
> 
> 1 The QEOS Model
> 
> 1.1 General Facts
> 
> In the QEOS model the Helmholtz free energy F = E − T S is composed of
> three contributions, an electronic part, an ionic part, and the phenomeno-
> logical bonding correction:
> 
> F (ρ, T ) = Fe(ρ, T ) + Fi(ρ, T ) + Fb(ρ, T )
> 
> (1)
> 
> Here, it is assumed that the electronic part does not depend on the ionic
> part. The thermodynamical quantities like pressure, speciﬁc internal energy,
> and speciﬁc entropy are derived from the Helmholtz free energy:
> 
> pe,i,b = ρ2 ∂Fe,i,b
> ∂ρ
> 
> , Se,i,b = −
> 
> ∂Fe,i,b
> ∂Te,i,b
> 
> , Ee,i,b = Fe,i,b + Te,i,bSe,i,b
> 
> (2)
> 
> Besides these quantities, the charge state is calculated.
> subsections the three parts of the QEOS model will be described shortly.
> 
> In the following
> 
> The input variables for the eos calculation of one single element are: atomic
> number, atomic weight, normal conditions (solid density and standard tem-
> perature), and bulk modulus at normal conditions. Furthermore, the density
> and temperature grid have to be speciﬁed. Currently, with MPQeos data
> can be calculated in the following range:
> 
> 10−7 ≤
> 
> ρ
> ρsolid
> 
> ≤ 106,
> 
> 10−4 eV ≤ T ≤ 106 eV.
> 
> (3)
> 
> With MPQeos the calculations can be done with or without a Maxwell con-
> struction which eliminates the van-der-Waals loops [3] in the liquid-vapor
> phase coexistence region. More information about this can be found in Sub-
> section 2.3 and in Section 8.
> 
> 1.2 Electronic EOS: TF Model
> 
> For the calculation of the electronic contribution – the most important part
> of an eos for hot dense matter – the simple Thomas-Fermi (TF) model [4]
> 
> 6

### [MPQeos-JWGU-Documentation.pdf] 第 7 页

> is used. In this model the electrons are described as a Fermi gas in the self-
> consistent electrostatic ﬁeld of the atom which is produced by the ion mesh
> and the electrons themselves. Matter is segmented into spherical cells for
> which the equilibrium electron distribution is calculated by solving the TF
> equation. For the segmentation Wigner-Seitz cells [5] are used. Hence, the
> radius r0 of the cells with atomic mass A, density ρ, and proton mass Mp is
> choosen in the following way:
> 
> 4πr3
> 
> 0/3 = AMp/ρ
> 
> (4)
> 
> Since the electrons are assumed to be a Fermi gas in the electrostatic ﬁeld of
> the electrons and the ions, there is no distinction between valence electrons
> and electrons from the inner shells. Instead of this they can be seperated
> in localized and non-localized electrons. If the electrostatic potential V (r) is
> normalized to disappear at the cell boundary, those electrons are localized
> which have negative total energy (cid:15) = p2/2me − eV (r) with the classical
> momentum p. For the free atom for T = 0 this is the case for all electrons.
> Electrons with positive energy are called non-localized. They are responsible
> for the electron pressure and ionization eﬀects.
> 
> TF equation for T = 0
> 
> For T = 0 [6] the TF equation is:
> 
> d2χ(x)
> dx2 =
> 
> 1
> x1/2 χ3/2
> 
> (5)
> 
> It is a dimensionless function where x = r/a0, and the function χ is deﬁned
> by the potential V (r) and the chemical potential µ. µ is determined by
> the condition of charge neutrality of the cell. Zχ(r) can be regarded as the
> eﬀective nuclear charge.
> Ze2
> r
> 
> eV (r) + µ ≡
> 
> χ(r)
> 
> (6)
> 
> a0 =
> 
> (cid:18) 3π
> 4
> 
> 1
> 2
> 
> (cid:19)2/3 ¯h2
> 
> me2 Z −1/3
> 
> The boundary conditions for the TF equation are:
> 
> χ(x) → 1,
> 
> x → 0
> 
> (cid:21)
> 
> (cid:20) x
> χ(x)
> 
> dχ
> dx
> 
> = 1
> 
> x=x0
> 
> 7
> 
> (7)
> 
> (8)
> 
> (9)

### [MPQeos-JWGU-Documentation.pdf] 第 8 页

> The ﬁrst boundary condition is a result of the divergence of the potential
> close to the nucleus. The second condition follows from the charge neutrality
> of the cell. With other words: the electrical ﬁeld Er(r) = −(∂φ/∂r) at the
> boundary of the neutral cell x0 must disappear in the spherical case because
> of the law of Gauß:
> (cid:21)
> 
> (cid:21)
> 
> (cid:20)dφ
> dx
> 
> = 0 ⇔
> 
> x=x0
> 
> (cid:20) x
> χ(x)
> 
> dχ
> dx
> 
> = 1
> 
> x=x0
> 
> (10)
> 
> TF equation for ﬁnite temperatures
> 
> For ﬁnite temperatures Feynman, Metropolis and Teller [5] derived a similar
> version of the TF equation
> 
> d2Ψ(ξ)
> dξ2 = aξF1/2
> with the following deﬁnitions:
> 
> (cid:20)Ψ(ξ)
> ξ
> 
> (cid:21)
> 
> ξ =
> 
> r
> r0
> 
> Ψ(ξ) = ξ
> 
> eV + µ
> kT
> 
> a =
> 
> 4πmee2r2
> 
> 0(2mekT )1/2
> π¯h3
> 
> (11)
> 
> (12)
> 
> (13)
> 
> (14)
> 
> r0 is the cell radius, and F1/2 denotes the Fermi-Dirac integral. The boundary
> conditions for ﬁnite T are similar to those for T = 0:
> 
> Ψ(0) =
> 
> Ze2
> kT r0
> 
> Ψ(cid:48)(1) = Ψ(1)
> 
> Thermodynamic variables
> 
> (15)
> 
> (16)
> 
> By solving the TF equation one obtains the equilibrium electron distribution
> in the cell and thereby the energy of the electrons which consists of three
> contributions: kinetic energy K, potential energy of the electrons among
> each other Uee, and potential energy of the electrons with the nucleus Uen:
> 
> Etot
> 
> e = K + Uen + Uee
> 
> (17)
> 
> 8

### [MPQeos-JWGU-Documentation.pdf] 第 9 页

> The Helmholtz free energy Fe = Ee − T Se is obtained by integrating the
> Gibbs-Helmholtz relation [7]:
> 
> Etot
> 
> e =
> 
> ∂
> ∂β
> 
> [βFe] ,
> 
> β = 1/kT
> 
> (18)
> 
> The charge state depends on the number of electrons in non-localized states
> (g(r, p) denotes the Fermi distribution function):
> 
> (cid:90)
> 
> (cid:90)
> 
> d3r
> 
> Q =
> 
> (cid:15)>0
> 
> 2d3p
> h3 g(r, p)
> 
> (19)
> 
> Advantages / disadvantages of the simple TF model
> 
> The most important advantage of the simple TF model is the fact that calcu-
> lations are faster than with advanced TF theories because the TF equation
> and all thermodynamical quantities scale with the atomic number and hence
> must be calculated only once for e.g. hydrogen. For example the internal
> energy E of a material (A, Z) at density ρ and temperature T shall be cal-
> culated. Then you ﬁrst have to rescale ρ and T :
> 
> ρ1 = ρ/AZ T1 = t/Z 4/3
> 
> (20)
> 
> Now the internal energy E1 is calculated for ρ1 and T1 for hydrogen A = Z =
> 1. E is obtained by the proper scaling formula:
> 
> E(ρ, T ) =
> 
> Z 7/3
> A
> 
> E1(ρ1, T1)
> 
> (21)
> 
> For all other thermodynamical quantities similar formulas exist. The only
> restraint for the use of the scaling property is that the original TF table
> (A = Z = 1) must cover a large density-temperature area which becomes
> clear when looking at equation (20).
> 
> The most important disadvantage of the simple TF model is the negligence
> of attractive (bonding) forces between neutral atoms. This is the reason for
> an overestimation of the critical pressure and the critical temperature and
> an overall overestimation of pressures near normal conditions. The bond-
> ing forces originate from quantum eﬀects in the electron-electron interaction.
> There exist extended TF theories like the Thomas-Fermi-Dirac (TFD) theory
> [8], the Thomas-Fermi-Kirzhnitz (TSK) theory [9] and the quantum statis-
> tical model (QSM) [10, 11]. Unfortunately, they are computationally more
> intensive and do not contain the scaling property of the simple TF theory.
> 
> 9

### [MPQeos-JWGU-Documentation.pdf] 第 10 页

> For more details about the TF theory, its limiting cases, and inter-/extrapolation
> methods in the QEOS model and MPQeos the reader ist referred to Ref.
> [1, 2].
> 
> 1.3 Semiempirical Bonding Correction
> 
> The semiempirical bonding correction, the recalibration scheme of QEOS,
> is added to the total eos in order to improve the previously mentioned fail-
> ures of the electronic contribution not to take care of exchange forces and to
> overestimate the electronic pressure in the solid body. A fully quantum me-
> chanical treatment of the electrons in the solid body would be too elaborate
> within the framework of the QEOS model. The free energy of the bonding
> correction is:
> 
> Fb = E0
> 
> (cid:110)
> 
> 1 − exp
> 
> (cid:16)
> 
> (cid:104)
> 
> 1 − (ρs/ρ)1/3(cid:105)(cid:17)(cid:111)
> 
> b
> 
> (22)
> 
> Since Fb does not depend on the temperature, it follows Eb = Fb. The
> pressure then is:
> pb = ρ2 ∂Eb
> ∂ρ
> 
> (cid:18)E0bρs
> 3
> 
> (cid:18)ρs
> ρ
> 
> (cid:19) (cid:18) ρ
> ρs
> 
> (cid:19)1/3(cid:35)(cid:33)
> 
> (cid:32)
> b
> 
> = −
> 
> (cid:19)2/3
> 
> (23)
> 
> exp
> 
> 1 −
> 
> (cid:34)
> 
> The constants E0 and b determine the bonding correction. They characterize
> the range and the magnitude of the bonding forces. In order to determine
> them, two conditions must be fulﬁlled:
> 
> 1. The total pressure ptot = pi +pe +pb must vanish at standard conditions
> 
> (solid density, standard temperature).
> 
> 2. The value of the bulk modulus [12] (and thereby the sound speed)
> 
> K0 = ρ
> 
> (cid:18) ∂ptot
> ∂ρ
> 
> (cid:19)
> 
> ρs
> 
> (24)
> 
> at standard conditions must be equal to the experimental value.
> 
> The theoretical motivation for the form of the Helmholtz free energy Fb [13]
> is the Morse potential in a two-atomic molecule with the bonding energy
> D, the equilibrium distance Re and a constant b which must be determined
> empirically:
> 
> UM (R) = D (cid:2)e−2b(R−Re) − 2e−b(R−Re)(cid:3)
> 
> (25)
> 
> The bonding correction has the most inﬂuence on the total eos near the solid
> density. At higher densities the electronic contribution dominates.
> 
> 10

### [MPQeos-JWGU-Documentation.pdf] 第 11 页

> 1.4
> 
> Ionic EOS: Cowan Model
> 
> The thermodynamical properties of the ionic contribution which in the QEOS
> model is totally independent of the electronic contribution are described
> through the ionic eos. The contribution of the ions to the total eos is sig-
> niﬁcant for temperatures T < 10 eV and densities near the solid density
> ρ/ρs < 2. For higher temperatures and/or densities the electronic and bond-
> ing contributions dominate. In QEOS the Cowan model is used. It interpo-
> lates between known limiting thermodynamical cases by the aid of empirical
> formulas. The energy in the model is of purely thermal nature. Coulomb
> and bonding energies are taken care of in the electronic and the bonding
> contributions. The following list gives an overview of the limiting physical
> cases of the Cowan model.
> 
> • Ideal gas law [8] (high temperatures and/or low densities):
> 
> pi = ρkT /AMp, Ei =
> 
> 3
> 2
> 
> kT /AMp,
> 
> Si = k
> 
> (cid:20)
> S0 +
> 
> 3
> 2
> 
> (cid:21)
> log (cid:0)kT /ρ2/3(cid:1)
> 
> /AMp
> 
> S0 is given through the Sackur-Tetrode formula:
> 
> S0 =
> 
> 5
> 2
> 
> + log (2AMp) −
> 
> log (cid:0)h2/2πAMp
> 
> (cid:1)
> 
> 3
> 2
> 
> (26)
> 
> (27)
> 
> • Melting scaling law [14] (energy and density for non-ideal dense liquids):
> 
> pi =
> 
> (cid:20)
> 
> ρkT
> AMp
> 
> 1 + γF (ρ) f
> 
> (cid:19)(cid:21)
> 
> (cid:18) Tm
> T
> 
> Ei =
> 
> 3
> 2
> 
> (cid:20)
> 
> kT /AMp
> 
> 1 + f
> 
> (cid:19)(cid:21)
> 
> (cid:18) Tm
> T
> 
> (28)
> 
> (29)
> 
> γF is determined by the melting temperature Tm(ρ) and f (Tm/T ) is a
> scaling function.
> 
> • Lindemann melting law:
> 
> Tm (ρ) /Θ2
> 
> D (ρ) = α/ρ2/3
> 
> (30)
> 
> ΘD – Debye temperature, α – material dependent constant
> 
> 11

### [MPQeos-JWGU-Documentation.pdf] 第 12 页

> • Dulong-Petit law (ΘD(ρ) ≤ T ≤ Tm(ρ)):
> 
> Ei ≈ 3kT /AMp
> 
> • Gr¨uneisen eos [8] (T < Tm(ρ)):
> 
> pi = Γ (ρ) ρEi
> 
> Dependence of the Gr¨uneisen parameter Γ on ΘD [8]:
> 
> Γ (ρ) = −
> 
> V
> ΘD
> 
> ∂ΘD
> ∂V
> 
> =
> 
> ∂ log ΘD
> ∂ log ρ
> 
> • Debye-Modell:
> 
> hνD = kΘD
> 
> νD – Debye frequency, ΘD – Debye temperature
> ⇒ Speciﬁc heat of non-conductors for T < ΘD:
> 
> cV =
> 
> 12π4R
> 5
> 
> (cid:18) T
> ΘD
> 
> (cid:19)3
> 
> • Third law of thermodynamics (Nernst’s law):
> 
> lim
> T →0
> 
> S (ρ, T ) = 0
> 
> (31)
> 
> (32)
> 
> (33)
> 
> (34)
> 
> (35)
> 
> (36)
> 
> The Cowan model consists of two independent parts. The empirical part
> of the model makes estimations for the Debye and the melting temperatures
> depending on the density. In the structural part the eos is calculated. There-
> fore, the scaling variables u and w are introduced:
> 
> u = ΘD (ρ) /T
> 
> w = Tm (ρ) /T
> 
> (37)
> 
> (38)
> 
> Cowan deﬁnes a scaling function f (u, w) which determines the Helmholtz
> free energy of the ions:
> 
> Fi (ρ, T ) =
> 
> kT
> AMp
> 
> f (u, w)
> 
> (39)
> 
> 12

### [MPQeos-JWGU-Documentation.pdf] 第 13 页

> There are three diﬀerent areas in u-w space for which the scaling function
> is deﬁned. For temperatures above the melting temperature (T > Tm) the
> following empirical formula is used:
> 
> f (u, w) = −
> 
> 11
> 2
> 
> +
> 
> 9
> 2
> 
> w1/3 +
> 
> 3
> 2
> 
> log
> 
> (cid:19)
> 
> (cid:18) u2
> w
> 
> , w ≤ 1
> 
> (40)
> 
> For the ”hot” solid body (Tm > T > 3ΘD) holds:
> 
> f (u) = −1 + 3 log u + (cid:0)3u2/40 − u4/2240(cid:1) , w > 1, u < 3
> 
> (41)
> 
> For the ”cold” solid body (T ≤ 3ΘD) applies:
> 
> f (u) =
> 
> π4
> 9
> u + 3 log (cid:0)1 − e−u(cid:1) −
> 5u3
> 8
> + e−u (cid:0)3 + 9u−1 + 18u−2 + 18u−3(cid:1) , w > 1, u ≥ 3
> 
> (42)
> 
> In the Cowan model the Gibbs free energies in the liquid and in the solid
> phase on the melting curve are exactly the same [2]. This means that the
> QEOS model does not contain melting.
> 
> The task of the empirical part of the Cowan model is to make the Debye and
> melting temperatures and the Gr¨uneisen parameter available to the struc-
> tural part as functions of the density. It has to be pointed out that a failure
> in the estimation of these quantities only has little inﬂuence on the pressure
> and the energy of the ionic eos. The empirical part should fulﬁll the formulas
> for the Gr¨uneisen parameter (33) and the Lindemann melting law (30).
> 
> Using a reference density ρref = (A/9Z 0.3) g/cm3 the densities are scaled
> with ξ = ρ/ρref . Thereby, the reference density corresponds with a atomic
> radius of Ra ≈ 1, 5 · 10−8Z 0.1 cm. Then Cowan’s estimations are:
> 
> kTm = 0.32
> 
> ξ2b+10/3
> (1 + ξ)4 [eV]
> 
> kΘD =
> 
> Γ = b +
> 
> 1, 68
> Z + 22
> 2
> 1 + ξ
> 
> ξb+2
> (1 + ξ)2 [eV]
> b = 0.6Z 1/9
> 
> (43)
> 
> (44)
> 
> (45)
> 
> Together with α = 0.0262 (cid:0)A2/3Z 0.2(cid:1) (Z + 22)2 the equations (30) and (33)
> are fulﬁlled. Since the formulas of the empirical model are simple, it is clear
> that no exact estimations can be done, and the calculated quantities have
> only a qualitative character.
> 
> 13

### [MPQeos-JWGU-Documentation.pdf] 第 14 页

> 2 MPQeos-JWGU – Improvements
> 
> Currently there are four main changes of physical and practical importance
> which were applied to the original code of MPQeos. They are described
> in the following four subsections. The corresponding settings in the input
> parameter ﬁle are described later on in the manual.
> 
> 2.1 New Cold Curve
> 
> Despite the existence of the bonding correction, the QEOS model still over-
> estimates the location of the critical point (pressure pc and temperature Tc).
> Furthermore, in a few cases the value of the cohesive energy Ecoh – better
> known as enthalpy of sublimation – can become negative. In order to solve
> this problem, the TF cold curve and the bonding correction can be replaced
> for densities ρ < ρsolid by a soft-sphere function which was proposed by Young
> et al. [15]:
> 
> Ecold (ρ, T = 0) = Aρn − Bρm + Ecoh .
> 
> (46)
> 
> The constants A and B are adjusted in that way that total pressure and
> internal energy become zero at solid density and standard temperature; m
> and n are free parameters. They are used to approach the experimentally or
> theoretically known critical point.
> 
> The following listing demonstrates how the soft-sphere function aﬀects the
> location of the critical point for aluminum:
> 
> Experimental / theoretical values [15]: Tc = 5700 K,
> Tc = 13487 K,
> Original MPQeos (version 2.0):
> Tc = 5558 K,
> MPQeos-JWGU:
> 
> pc = 1820 bar
> pc = 23487 bar
> pc = 1722 bar
> 
> (m = 0.5, n = 2.0, Ecoh = 12.123 kJ/g)
> 
> The disadvantages of the simple form of this new cold curve are on the one
> hand a lack of ﬂexibility with only two free parameters. On the other hand
> sound speed is discontinuous at solid density which could be problematic e.g.
> for hydrodynamic simulations using the MPQeos-JWGU eos. Hence, some
> further improvements concerning the cold curve will probably be made in the
> future.
> 
> 14

### [MPQeos-JWGU-Documentation.pdf] 第 15 页

> 2.2 Mixtures of Elements
> 
> In version 2.0 of MPQeos the possibility for the calculation of mixtures of ele-
> ments was not included. Hence, the so-called TF-mixing-of-elements method
> described in the QEOS description [1] was added to MPQeos-JWGU. The
> ionic contribution and the bonding correction are handled as a single species
> with mean atomic number ¯Z and weight ¯A. For the electronic contribution
> of the mixture the densities ρk (eﬀectively the partial volumes) of all species
> are iteratively adjusted in order to equilibrate all TF pressures pe,k and to
> fulﬁll an additive volume rule:
> 
> i) pe,k (ρk, T ) = pe ∀k,
> 
> ii)
> 
> ¯A
> ρ
> 
> (cid:88)
> 
> =
> 
> xk
> 
> k
> 
> Ak
> ρk
> 
> (cid:88)
> 
> ( ¯A =
> 
> xkAk) .
> 
> (47)
> 
> k
> 
> In these equations xk is the number fraction, and Ak is the atomic weight of
> species k.
> 
> The thermodynamic values for the electronic component of the mixture are
> ﬁnally obtained by summing up the single element values (with densities
> obtained by the above scheme), each weighted by xkAk/ ¯A.
> 
> The described procedure is called for every density-temperature point, and
> therefore it is clear that the calculation of mixtures of elements is compu-
> tationally more intensive than for a single element. Actually, in some few
> In this case the user is rec-
> cases the iteration-process can come to rest.
> ommended to start the calculation again or to make a little change in the
> density-temperature-grid.
> 
> The routines for the mixing procedure of the electronic part are located
> in a new ﬁle MIXTURE.C. Constants concerning the precision of this new
> routines can be found in MIXTURE.H. The maximum number of elements
> included in the mixture can be modiﬁed in DEFINITS.H.
> 
> 2.3 Calculation of Liquid-Vapor Phase Coexistence
> 
> In the original MPQeos code phase-coexistence data was calculated by the
> usage of Maxwell’s geometrical rule of equal areas below and above the van-
> der-Waals loop [3] for each isotherm below the critical temperature:
> 
> (T = const.)
> 
> (cid:90) Vliq
> 
> Vvap
> 
> pdV = psat (Vvap − Vliq) .
> 
> (48)
> 
> 15

### [MPQeos-JWGU-Documentation.pdf] 第 16 页

> Maxwell’s rule is especially for low temperatures in the two-phase region com-
> putationally very intensive and imprecise. In MPQeos-JWGU this problem
> was solved by applying a new routine for the coexistence data calculation.
> Now the coexistence boundary – also called the binodal or the vaporization
> curve – and the equilibrium or saturated vapor pressure psat are calculated
> with regard to the equilibrium of Gibbs’ free energies and pressures on the
> liquid and the vapor side for each isotherm below the critical temperature.
> This leads to a large improvement of computational time and accuracy.
> 
> The new routines (together with the old routines using Maxwell’s rule) are
> located in ELILOOP.C. In the (old) routines for ﬁnding the critical point
> and the minimum and maximum pressure along the van-der-Waals loops
> also some modiﬁcations were done. All constants concerning the precision of
> the calculations can be found in ELILOOP.H.
> 
> Since psat and the density at the vapor branch of the binodal become very
> low for temperatures around room temperature, the eos has to be calculated
> down to very low densities. The original MPQeos was limited to densities
> above 10−7 g/cm3 and temperatures above 10−4 eV. These limits appeared
> in diﬀerent parts of the code, partially with diﬀerent values e.g. for the elec-
> tronic and the ionic part. The limits were removed and placed instead at one
> single place in the code at DEFINITS.H. Now there the constants T ZERO
> and RHO ZERO appear. Actually RHO ZERO is set to 10−50 g/cm3 in order
> to calculate coexistence data at room temperature.
> 
> Attention: At the moment physically correct behaviour of the eos at those
> low densities cannot be assured. When looking at the compressibility factor
> along the vapor branch of the binodal curve, in some parts it becomes greater
> than 1.0 in contradiction to the ideal gas law limit. This is a construction
> site for the future. For temperatures, where the vapor density is less than
> RHO ZERO, the pressure at RHO ZERO is taken as the equilibrium pres-
> sure. For T = 0 the pressure psat is set to zero.
> 
> Finally, new routines for the calculation of the boiling temperature (con-
> straint: psat = 1 bar) and for a critical data output ﬁle were added to
> ELILOOP.C. The output ﬁle with extension .critical.dat is automatically
> created when doing an eos calculation with a ”Maxwell construction”.
> It
> contains the following information:
> 
> • Critical point data
> 
> • Boiling temperature
> 
> 16

### [MPQeos-JWGU-Documentation.pdf] 第 17 页

> • Information concerning the accuracy of the calculation
> 
> • Binodal and spinodal in ρ-p-plane
> 
> • Binodal, spinodal, and diamener curve in T -ρ-plane
> 
> • Binodal in T -H-plane (speciﬁc enthalpy)
> 
> • Evaporation heat ∆H in T -∆H-plane
> 
> • Saturation curve in Arrhenius coordinates
> 
> • Compressibility factor Z in T -Z-plane and P -Z-plane
> 
> 2.4 Isobaric Expansion Data
> 
> The last extension is a new routine in ELILOOP.C for the calculation of
> data along the isobaric curve p = 0 up to the spinodal limit – that means:
> up to that temperature for which the van-der-Waals loop does not cross
> p = 0 anymore. The following data is calculated along the isobaric curve and
> written to a new output ﬁle with extension .isobaric.dat:
> 
> • Temperature T
> 
> • Density ρ
> 
> • Pressure p (for checking accuracy only)
> 
> • Thermal expansion coeﬃcient α
> 
> • Speciﬁc enthalpy H
> 
> • Isobaric heat capacity Cp
> 
> In the future this data perhaps can be used for adjusting the parameters in
> the soft-sphere function described in Section 2.1.
> 
> 17

### [MPQeos-JWGU-Documentation.pdf] 第 18 页

> Manual
> 
> 3
> 
> Installation
> 
> The C++ source codes for MPQeos-JWGU and showeos, together with some
> examples, are in a packed ﬁle called MPQeos-JWGU 2.2 20101102.zip. To
> unzip this ﬁle type ’unzip MPQeos-JWGU 2.2 20101102.zip’. The directory
> MPQeos-JWGU 2.2 20101102 will be created. Change to the subdirectory
> /src and compile the source code by typing ’make all’. By default, the GNU
> C++ compiler g++ is used. The Makeﬁle contains all information about
> compilation of the source code.
> 
> After MPQeos-JWGU has been installed, all relevant ﬁles for using the code
> can be found in the subdirectory /EOS-Data. The executable mpqeos will be
> there, as well as the input parameter ﬁles (.PAR) for generating EOS tables,
> and ﬁnally the MPQeos-JWGU-produced tables themselves will be there.
> 
> The Thomas-Fermi table, which contains the pre-computed results of the
> Thomas-Fermi model, can be found in the subdirectory /TF-table. Docu-
> ments concerning MPQeos-JWGU are located in /documents.
> 
> 4 Generation of EOS Tables
> 
> To generate a new equation-of-state table, ﬁrst make a copy of one of the
> parameter ﬁles given as examples in the subdirectory /EOS-Data. Then
> modify this ﬁle according to your material’s properties and the precision
> you desire.
> (Note: the quality of the critical data calculation and of the
> liquid-vapor coexistence data calculation that follows depend strongly on
> the choice of the (ρ − T ) grid density in the critical region. So don’t be too
> thrifty spending mesh points.) The name of the parameter ﬁle will be also
> the name of the eos table output ﬁles (the suﬃx ’.301’ and all other suﬃxes
> are appended automatically by the code).
> 
> The new parameter ﬁle must be located together with the executable mpqeos
> in one directory (e.g. in /EOS-Data). Start the code mpqeos with the new
> parameter ﬁle name (without suﬃx ’.PAR’ !) as argument. As an example, for
> the parameter ﬁle Aluminum.PAR you have to type ’./mpqeos Aluminum’.
> 
> 18

### [MPQeos-JWGU-Documentation.pdf] 第 19 页

> If you want to calculate the eos only for one given density-temperature point
> then as an example for ρ = 2.0 g/cm3 and T = 102 eV you have to type
> ’mpqeos Aluminum 2.0e0 1.0e2’. The single point information will be printed
> out directly on the console.
> 
> 5 Parameter File Structure
> 
> A parameter ﬁle Materialname.PAR is an ASCII ﬁle consisting out of two
> parts. The ﬁrst part is an input ﬁle for MPQeos-JWGU that contains all
> necessary information about the ﬁnal eos table, like material information
> etc. The second part is an input ﬁle for showeos, telling it which isotherms
> to display, etc.
> 
> The two parts are divided into sections by indented headlines (’TF-Table’,
> etc.). Each section contains one or several lines with a key-word (like ’Path’),
> an ’=’ sign and some value / string. Lines can be commented out by a % or
> # at the beginning. An example parameter ﬁle is shown in Appendix A.
> 
> 6
> 
> Input Parameters
> 
> The MPQeos-JWGU code needs the following input information:
> 
> • TF-Table
> 
> – Path: Path of the Thomas-Fermi table
> 
> • Computation-Settings:
> 
> – Maxwell Flag: ”Maxwell construction” desired for each eos point?
> 
> 0: no / 1: equal Gibbs free energy and pressure
> (2: Maxwell’s geometrical rule of equal areas)
> 
> – Charge Flag: charge state computation desired for each eos point?
> 
> 0: no / 1: yes
> 
> – SoftSphere Flag: replace TF cold curve and bonding correction
> 
> for ρ < ρsolid with soft-sphere function?
> 
> 0: no / 1: yes
> 
> 19

### [MPQeos-JWGU-Documentation.pdf] 第 20 页

> – IsobaricExpansion Flag: isobaric expansion data desired?
> 
> 0: no / 1: yes
> 
> • Material-Data:
> 
> – Atomic masses A[i], nuclear charges Z[i], and number of atoms in
> 
> one molecule X[i] for the elements included in the material
> 
> The index i can be chosen freely for every element between 1
> and the constant integer MAX ELEMENTS (standard value:
> 10) deﬁned in DEFINITS.H.
> 
> – Rsolid: density at Tstandard in g/cm3
> – Bulk-Modulus: density at Tstandard and ρsolid in dyne/cm2
> – T standard: standard temperature in eV
> 
> – SESAME-Number: SESAME database material number
> 
> • Soft-Sphere-Function (SoftSphere Flag = 1):
> 
> – m and n: free parameters in soft-sphere function
> 
> – Ecohesive: cohesive energy or enthalpy of sublimation in erg/g
> 
> • Isobaric-Expansion-Settings (IsobaricExpansion Flag = 1):
> 
> – Tmin and Tmax: minimum and maximum temperature for calcu-
> 
> lation of isobaric data along p = 0 in eV
> 
> – Number: number of calculated linearly equidistant distributed
> 
> temperature points in range Tmin - Tmax
> 
> • Q-table (density-temperature grid):
> 
> – Rratio x: deﬁnes the number of logarithmically equidistant dis-
> 
> tributed density points in range ρsolid · 10x−1 - ρsolid · 10x
> 
> – Tratio x: deﬁnes the number of logarithmically equidistant dis-
> 
> tributed temperature points in range 10x−1 - 10x eV
> 
> Attention: Take care of the limits T ZERO and RHO ZERO
> in DEFINITS.H.
> 
> The Maxwell Flag must be set to 1, if the user wants to perform the calcu-
> lation of zjr liquid-vapor coexistence data. This will be done directly before
> and while computing the eos table. For this reason, the computation time
> for corrected eos tables is longer than for simple tables with van-der-Waals
> 
> 20

### [MPQeos-JWGU-Documentation.pdf] 第 21 页

> loops. If the ﬂag is set to 1, the vaporisation curve / coexistence boundary
> is calculated with the new method described in Section 2.3. The old method
> using Maxwell’s geometrical rule should not be used anymore but it is actu-
> ally still selectable (Maxwell Flag = 2). For details about the construction
> with the old method see Ref. [2].
> 
> The charge Flag is usually set to zero, as the charge state has to be computed
> out of the pressure in a iteration routine. In case the user wishes to print
> out charge-state information, the ﬂag has to be set to a non-zero value, and
> some additional modiﬁcations on the code have to be done. Actually, when
> charge Flag is set to 1, the charge state is written to the SESAME tables
> and to an additional output ﬁle with suﬃx .CST (Rostock format).
> 
> In the Material-data section of the input ﬁle, the material’s properties have
> to be speciﬁed. A[i] is the nuclear mass, Z[i] the nuclear charge, and X[i] the
> number of atoms of element i participating in one molecule of the mixture.
> The index i can be chosen freely for every element between 1 and the integer
> deﬁned through the constant MAX ELEMENTS (standard value: 10) in
> DEFINITS.H. Note that for a single element also an index must be present!
> Solid density and bulk modulus of the material must be given in cgs units.
> The standard temperature, for which the bulk modulus is given, must be
> given in electron volts. The SESAME number is a number consisting of four
> digits. It is written to the SESAME output ﬁles.
> 
> The Soft-Sphere-Function and Isobaric-Expansion-Settings sections contain
> all information which is needed if the corresponding ﬂags are set to a non-zero
> value.
> 
> The Q-table section determines the number of points per decade in the den-
> sity and temperature grids, respectively. The value behind the key word
> Rratio-6 for example means the number of grid points in the interval 10−7 <
> ρ/ρsolid < 10−6. In this interval, the mesh points are distributed logarithmi-
> cally equidistant. The key words Tratio determine the mesh point density of
> temperature values, similar to the density grid information, in units of 1 eV.
> Attention: since the standard value of the constant T ZERO in DEFINITS.H
> is 10−4 eV the temperature will be automatically reset to 10−4 eV for all tem-
> peratures below.
> 
> 21

### [MPQeos-JWGU-Documentation.pdf] 第 22 页

> 7 EOS Table Structure
> 
> 7.1 SESAME-301 Format
> 
> MPQeos-JWGU is designed to generate tables in the SESAME-301 format.
> The SESAME eos library is a widely known set of equation-of-state tables for
> various materials, produced by the Los Alamons National Laboratory [16].
> SESAME-301 tables contain information about the total pressure, energy,
> and (sometimes) Helmholtz free energy of a given material as functions of
> density and temperature. They are based on experimental results as well
> as on theoretical models, sometimes on both. Additional information, for
> example about critical data vaporisation curve etc., is usually also contained
> in extra archive ﬁles (in case of MPQeos-JWGU critical data is written to a
> ﬁle with suﬃx .critical.dat).
> 
> A typical SESAME-301 table is an ASCII-ﬁle consisting of several lines which
> Its ﬁrst line
> contain four words each, where each word is a real number.
> contains a material code, the solid density of the material described (in cgs
> units), the number of points on the density mesh (as real number), and the
> number of points on the temperature mesh (as real number), example:
> 
> 3717
> 
> 2.70000000e+00 1.92000000e+02 7.30000000e+01
> 
> The next few lines contain information about the density mesh (Rho[I],
> I=1...NI) and the temperature mesh (T[J], J=1...NJ):
> 
> 0.00000000e+00 2.70000000e-07 5.81697366e-07 2.70000000e-06 ...
> 
> The next lines contain all pressure isotherms, ((P[I,J], I=1..NI), J=1..NJ),
> then energy and Helmholtz free energy isotherms in the same manner as for
> the pressure.
> 
> The units used in the SESAME library are:
> 
> • Pressure: GPa
> 
> • Energy: MJ/kg
> 
> • Density: g/ccm
> 
> • Temperature: Kelvin
> 
> 22

### [MPQeos-JWGU-Documentation.pdf] 第 23 页

> In MPQeos-JWGU the 301 ﬁle actually contains no Helmholtz free energy. If
> available charge state is written at the end of the ﬁle. Important for the cus-
> tomization of the 301 output are the read and write routines write 301 format
> and read 301 format in the module TABTOOLS.C. They, together with the
> routine make 301 table of the main ﬁle mpqeos main.C, have to be suited
> to the user’s own needs, regarding table structure. For the eos visualization
> with showeos it is important to modify the 301 read and write routines in or-
> der to make all relevant values available (e.g. entropy which is not contained
> in the ﬁle for standard).
> 
> 7.2 Other Output Formats
> 
> Together with the SESAME-301 ﬁle, there exist some other output ﬁle rou-
> tines in MPQeos-JWGU written by several people. The critical data and
> isobaric expansion output ﬁles were described in Sections 2.3 and 2.4.
> 
> Thanks to Tommaso Vinci, SESAME-304 and -305 tables and the mexport
> format are created at the end of each eos calculation. Furthermore, there
> exists a format with suﬃx data.txt containing pressure and energy data.
> Finally a routine for the KATACO format is present in TABTOOLS.C but
> it is not used.
> 
> If the charge state is calculated, Rostock format is written to a ﬁle with suﬃx
> .CST. In this ﬁle pressure and charge state isotherms are written against
> particle density and mass density for all temperatures.
> 
> 8 Phase Coexistence Calculation
> 
> In order to eliminate van-der-Waals loops out of an eos, a ”Maxwell construc-
> tion” must be applied to each isotherm below the critical point. Its position
> is found by ﬁrst looking up the critical isotherm via a bisectioning algorithm:
> a check is done on loops in each isotherm, until the one with loops at maxi-
> mum temperature is found. On this isotherm, the density where d2p/dρ2 = 0
> is looked up.
> 
> In the next step, the vaporisation curve is deterimined. The vaporisation
> curve is the boundary of the two-phase region, a ”Maxwell construction”
> is applied to each isotherm below the critical point speciﬁed in the input
> 
> 23

### [MPQeos-JWGU-Documentation.pdf] 第 24 页

> parameter ﬁle. In order to save computation time, this construction is done
> in one step, beforehand.
> 
> Note: As already mentioned in Section 2.3 in the original version of MPQeos
> the vaporisation curve was determined by Maxwell’s geometrical rule.
> In
> MPQeos-JWGU the essential condition is the equilibrium between Gibbs’
> free energies and pressures on the liquid and the vapor branch of the vapori-
> sation curve. This saves computational time and improves the quality of the
> calculation.
> 
> Later, for computing eos data at some point inside the two-phase region, the
> thermodynamic quantities have to be interpolated only linearly. Outside the
> two-phase region, the computation of the thermodynamic quantities goes as
> in the normal case. Critical data (see section 2.3) is written to a ﬁle with
> suﬃx critical.dat.
> 
> As the user speciﬁed density-temperature grid strongly determines the qual-
> ity or even the existence of the critical data and vaporisation curve, one
> should use not too few points near the critical region and also at high den-
> sities.
> 
> 9 Source Code Structure
> 
> As the QEOS model itself, also MPQeos-JWGU consists out of three main
> parts:
> ionic eos, electronic eos, and the bonding correction (or soft-sphere
> function). In the code, ionic eos and the bonding correction (or soft-sphere
> function) as the analytical part of the model were bound together in one C++
> class called Ionpart, deﬁned in IONMOD.C. This class is also responsible for
> reading the input ﬁle.
> 
> The electronic eos information for a single element is obtained in a class called
> QIPscheme, deﬁned in TF TABLE.F and TF TAB 2.C. This class reads the
> Thomas-Fermi table from a ﬁle and handles the interpolation / extrapolation
> on this TF table. The electronic eos for a mixture of elements is obtained in
> MIXTURE.C.
> 
> Critical data and the vaporisation curve are determined in a class called
> CriticalData, contained in ELILOOP.C. Important for the customization of
> the table input and output are the routines in TABTOOLS.C. The main ﬁle
> of MPQeos-JWGU is mpqeos main.C.
> 
> 24

### [MPQeos-JWGU-Documentation.pdf] 第 25 页

> 10 Visualizing EOS Tables with showeos
> 
> showeos is a tool for viewing eos tables generated with MPQeos-JWGU. Its
> input table format is the SESAME-301 format, described in Section 7.1. The
> eos table (301 ﬁle) must be in the same directory as the input ﬁle (identically
> with the MPQeos-JWGU input ﬁle) and as the showeos executable. Note
> that only quantities which are contained in and read out of the 301 ﬁle can
> be visualized. Once an eos table is read, showeos is able to perform the
> operations listed below. To tell showeos which operation to perform, one
> ’showeos
> has to type a number as second argument in the command line:
> Aluminum 1’ for example gives isotherms speciﬁed in ’Aluminum.PAR’ for
> the table ’Aluminum.301’. The physical units of
> 
> • the parameters given in the showeos part of the input ﬁle and
> 
> • the results of the following showeos sections: ’Hugoniot’, ’Isentropes’,
> 
> ’Single Point Info’
> 
> are speciﬁed in the input parameter ﬁle in the section ’Units’. The default
> units of showeos are cgs units (and electron volts as the unit of temperature).
> The units of the calculated quantity in the sections ’Isotherms’, ’Isochores’
> and ’Mountain’ are speciﬁed directly in these sections.
> 
> 10.1 Isotherms
> 
> showeos arguments: xxx 1
> 
> (xxx: parameter ﬁle name without .PAR)
> 
> For viewing isotherms the following speciﬁcations in the section ’Isotherms’
> must be made:
> 
> • Quantity: ’Pressure’, ’Energy’, ’FreeEnergy’, ’Entropy’, ’ChargeState’
> 
> – Note: The desired quantity must be included and read out of the
> 
> SESAME-301 ﬁle (TABTOOLS.C).
> 
> • Tmin and Tmax: min. and max. temperature
> 
> • Rmin and Rmax: min. and max. density
> 
> 25

### [MPQeos-JWGU-Documentation.pdf] 第 26 页

> • logarithmic: distribution in the desired interval
> 
> 0: linearly equidistant / 1: logarithmically equidistant
> 
> • Number: number of calculated curves
> 
> • ColdIso: calculation of the cold isotherm (T = 0)
> 
> 0: no / 1: yes
> 
> • Volume: dependent variable
> 
> 0: density / 1: speciﬁc volume v = 1/ρ
> 
> • Original: display only original data in the given intervall
> 
> 0: no / 1: yes
> 
> • Oﬀset: subtract value calculated at ρsolid and T = 0
> 
> 0: no / 1: yes
> 
> • Units: scaling factor for the calculated quantity (default: cgs units)
> 
> The output will be written to the ﬁle ’xxx.ist.e (p,s,f,q)’. The last letter of
> the ﬁlename will be an ’e’, if the isotherms are for energy, ’p’ for pressure,
> ’s’ for entropy, ’f’ for free energy, ’q’ for charge state.
> 
> The output of showeos will be a documented ASCII ﬁle that contains the de-
> sired information. Successive isotherms are divided by an ’&’ sign. This
> sort of ﬁle can be graphically visualized with Grace (see http://plasma-
> gate.weizmann.ac.il/Grace/), for example.
> 
> 10.2
> 
> Isochores
> 
> showeos arguments: xxx 2
> 
> (xxx: parameter ﬁle name without .PAR)
> 
> For isochores (= lines of constant density), the same comments apply as for
> isotherms for the section ’Isochores’. Of course, the options ’ColdIso’ and
> ’Volume’ are not available here. Here, the name of the output ﬁle will be
> ’xxx.isc.z’, where z means one of the letters (e,p,s,f,q).
> 
> 26

### [MPQeos-JWGU-Documentation.pdf] 第 27 页

> 10.3 Mountain Plots
> 
> showeos arguments: xxx 5
> 
> (xxx: parameter ﬁle name without .PAR)
> 
> For showing total phase planes (some quantity as a function of density and
> temperature in a three-dimensional diagram), one has to make the following
> speciﬁcations in the section ’Mountain’:
> 
> • Quantity: see section ’Isotherms’
> 
> • Tmin, Tmax, Rmin, Rmax: range in density and temperature
> 
> • Number: number of points on both, density and temperature grids
> 
> • Volume: dependent variable
> 
> 0: density / 1: speciﬁc volume v = 1/ρ
> 
> • OriginalFlag: display only original data in the given intervall
> 
> 0: no / 1: yes
> 
> • OﬀsetFlag: subtract value calculated at ρsolid and T = 0
> 
> 0: no / 1: yes
> 
> • IsoUnits: scaling factor for the calculated quantity
> 
> The output ﬁle ’xxx.mount.z’ ﬁrst shows the density and temperature grid,
> then a list of isochores of the desired quantity. z means one of the letters
> (e,p,s,f,q). For visualization, the program IDL V8.0 can be used.
> 
> 10.4 Isentropes
> 
> showeos arguments: xxx 4
> 
> (xxx: parameter ﬁle name without .PAR)
> 
> The visualization of isentropes can be speciﬁed by giving the number of
> isentropes ’Number’ and the range of the density-temperature phaseplane
> (’Rmin’, ’Rmax’, ’Tmin’, ’Tmax’) in which the isentropes will be traced in
> the section ’Isentropes’. The results are written to the ﬁle ’xxx.IST’.
> 
> 27

### [MPQeos-JWGU-Documentation.pdf] 第 28 页

> 10.5 Hugoniots
> 
> showeos arguments: xxx 3
> 
> (xxx: parameter ﬁle name without .PAR)
> 
> For computing an arbitrary Hugoniot curve from an EOS table, the starting
> point (density ’Ro’ and temperature ’To’) and a maximum pressure ’Pmax’
> must be given in the section ’Hugoniot’ of the input parameter ﬁle. The
> result will be written to the ﬁle ’xxx.HUG’.
> 
> 10.6 Single Point Information
> 
> showeos arguments: xxx 6 ρ T
> 
> (xxx: parameter ﬁle name without .PAR)
> 
> A single point information at the point (ρ, T ) – given in g/cm3 and eV – can
> be obtained by using the density and the temperature as third and fourth
> arguments in the command line call of showeos. The result will be printed
> out directly.
> 
> 28

### [MPQeos-JWGU-Documentation.pdf] 第 29 页

> A Example Input Parameter File (Si02)
> 
> %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
> % EOS calculation (mpqeos):
> %
> %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
> 
> TF-Table
> 
> Path = ../TF-table/tabelle1197
> 
> %%%%%%%%%%%%%%%%%%%%%%%%
> 
> Computation-Settings
> 
> Maxwell_Flag = 1
> 
> Charge_Flag = 1
> 
> SoftSphere_Flag = 1
> 
> IsobaricExpansion_Flag = 1
> 
> %%%%%%%%%%%%%%%%%%%%%%%%
> 
> % "Maxwell construction" desired?
> % (0: no, 1: equal Gibbs free energy
> % and pressure, 2: Maxwell’s rule)
> % charge state computation desired?
> % (0: no, 1: yes)
> % replace TF cold curve for densities
> % < Rsolid with soft sphere function?
> % (0: no, 1: yes)
> % isobaric expansion data desired?
> % (0: no, 1: yes)
> 
> Material-Data
> 
> SESAME-Number = 7386
> Rsolid = 2.2
> Bulk-Modulus = 3.7e11
> 
> T_standard = 2.585257e-2
> A[1] = 28.0855, Z[1] = 14.0, X[1] = 1
> X[2] = 2
> A[2] = 15.9994, Z[2] = 8.0,
> 
> %%%%%%%%%%%%%%%%%%%%%%%%
> 
> Soft-Sphere-Function
> 
> % SESAME table number
> % density at T_standard
> % multiply the GPa value by
> % 1.0e10 to get dyne/cm^2
> % 2.585257771e-2 ---> 300 K
> % silicon (Si)
> % oxygen (O)
> 
> Ecohesive = 9.736e10
> 
> % cohesive / bonding energy in erg/g
> 
> 29

### [MPQeos-JWGU-Documentation.pdf] 第 30 页

> m = 0.8
> n = 2.8
> 
> % m and n: adjustable parameters in
> %
> 
> soft-sphere function
> 
> %%%%%%%%%%%%%%%%%%%%%%%%
> 
> Isobaric-Expansion-Settings
> 
> Tmin = 1.786383e-1
> Tmax = 3.625855e-1
> Number = 30
> 
> % minimum temperature in eV
> % maximum temperature in eV
> % number of calculated temperatures
> % in range Tmin to Tmax
> 
> %%%%%%%%%%%%%%%%%%%%%%%%
> 
> Q-table
> 
> Rratio-6 = 0
> Rratio-5 = 0
> Rratio-4 = 0
> Rratio-3 = 0
> Rratio-2 = 0
> Rratio-1 = 3
> Rratio0 = 50
> Rratio1 = 50
> Rratio2 = 3
> Rratio3 = 3
> Rratio4 = 0
> Rratio5 = 0
> Rratio6 = 0
> 
> Tratio-6 = 0
> Tratio-5 = 0
> Tratio-4 = 0
> Tratio-3 = 1
> Tratio-2 = 2
> Tratio-1 = 30
> Tratio0 = 30
> Tratio1 = 2
> Tratio2 = 1
> Tratio3 = 1
> Tratio4 = 0
> Tratio5 = 0
> Tratio6 = 0
> 
> % Rratiox defines number of density points in
> % range Rsolid*1.0e(x-1) to Rsolid*1.0ex g/cm^3
> 
> % Tratiox defines number of temperature points
> % in range 1.0e(x-1) to 1.0ex eV
> 
> % Attention: Lower temperature limit for eos
> %
> 
> calculation: 1.0e-4 eV
> 
> 30

### [MPQeos-JWGU-Documentation.pdf] 第 31 页

> %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
> % EOS visualization (showeos):
> %
> %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
> 
> Units
> 
> P_unit = 1.0e12
> 
> T_unit = 1.0
> R_unit = 1.0
> V_unit = 1.0e5
> E_unit = 1.0
> 
> % 1.0 ---> dyne/cm^2;
> % 1.0e10 ---> GP
> % 1.0 ---> eV;
> % 1.0 ---> g/cm^3;
> % 1.0e5 ---> km/s
> % 1.0 ---> cgs (erg/g);
> 
> 1.0e12 ---> MBar;
> 
> 8.617525902e-5 ---> K
> 
> 1.0 ---> Mg/m^3
> 
> 1.0e10 ---> MJ/Kg
> 
> %%%%%%%%%%%%%%%%%%%%%%%
> 
> Isotherms
> 
> Quantity = Pressure
> Tmin
> Tmax
> Rmin
> Rmax
> 
> = 1.0e-4
> = 1.0e3
> = 0.0001
> = 10
> 
> logarithmic = 0
> = 0
> Number
> = 0
> ColdIso
> = 0
> Volume
> = 1
> Original
> = 0
> Offset
> = 1.0e6
> Units
> 
> % example: 1.0e12 --> pressure in Mbar (see
> % section Units at top for conversion factors)
> 
> %%%%%%%%%%%%%%%%%%%%%%%
> 
> Isochores
> 
> Quantity = Pressure
> Tmin
> Tmax
> Rmin
> Rmax
> 
> = 1.0e-4
> = 1.0e3
> = 0.0001
> = 10
> 
> logarithmic = 0
> 
> 31

### [MPQeos-JWGU-Documentation.pdf] 第 32 页

> Number
> Original
> Offset
> Units
> 
> = 1
> = 0
> = 0
> = 1.0e6
> 
> % example: 1.0e12 --> pressure in Mbar (see
> % section Units at top for conversion factors)
> 
> %%%%%%%%%%%%%%%%%%%%%%%
> 
> Hugoniot
> 
> Ro = 2.2
> To = 2.585257e-2
> Pmax = 1.0e8
> 
> %%%%%%%%%%%%%%%%%%%%%%%
> 
> Isentropes
> 
> Number = 20
> Rmin = 0.01
> Rmax = 1.0e2
> Tmin = 0.1
> Tmax = 1.0e3
> 
> %%%%%%%%%%%%%%%%%%%%%%%
> 
> Mountain
> 
> Quantity = Pressure
> Tmin
> Tmax
> Rmin
> Rmax
> 
> = 0.5
> = 1.5
> = 0.01
> = 10.0
> 
> = 50
> 
> Number
> VolumeFlag
> = 0
> OriginalFlag = 0
> = 0
> OffsetFlag
> = 1.0e0
> IsoUnits
> 
> % example: 1.0e12 --> pressure in Mbar (see
> % section Units at top for conversion factors)
> 
> 32

### [MPQeos-JWGU-Documentation.pdf] 第 33 页

> References
> 
> [1] R. More, K. Warren, D. Young und G. Zimmerman; A new quotidian
> equation of state (QEOS) for hot dense matter; Phys. Fluids 31 (1988)
> 3059; 5, 10, 15
> 
> [2] A. Kemp, J. Meyer-ter-Vehn; Das Zustandsgleichungs-Modell QEOS
> f¨ur heisse, dichte Materie; Max-Planck-Institute for Quantum Optics,
> Report MPQ 229 (1998); 5, 10, 13, 21
> 
> [3] L. Landau, E. Lifshitz; Statistical Physics; Pergamon Press, Oxford
> 
> (1969); 6, 15
> 
> [4] L. Thomas; Proc. Camb. Phil. Soc 23 (1927) 542;
> E. Fermi; Zeitschrift f¨ur Physik 48 (1928) 73; 6
> 
> [5] R. Feynman, N.Metropolis und E. Teller; Equations of state of ele-
> ments based on the generalized Thomas-Fermi theory; Physical Review
> 75 (1949) 1561; 7, 8
> 
> [6] L. Landau und E. Lifshitz; Quantum Mechanics: Non Relativistic The-
> 
> ory; Pergamon Press, Oxford (1965); 7
> 
> [7] M. Brachmann; Thermodynamic functions on the generalized Thomas-
> 
> Fermi theory; Physical Review 84 (1951) 1263; 9
> 
> [8] S. Eliezer, A. Ghatak und H. Hora; Fundamentals of Equations of State;
> 
> World Scientiﬁc Pub Co (Mai 2002); 9, 11, 12
> 
> [9] D. Kirzhnitz, Y. Lozovik und G. Shpatakovskaya; Sov.Phys.Usp. 18
> 
> (1976) 649; 9
> 
> [10] B.-G. Englert; Semiclassical Theory of Atoms; Springer, Berlin (1988);
> 
> 9
> 
> [11] W. Zittel; Elektronische Struktur hochkomprimierter Materie; MPQ-
> 
> Report 111 (1986); 9
> 
> [12] Ya. B. Zeldovich, Yu. P. Raizer; Physics of Shock-Waves and High-
> Temperature Hydrodynamic Phenomena; Vol. II, Academic Press, New
> York (1967); 10
> 
> [13] J. Barnes; Physical Review 153 (1967); 10
> 
> 33

### [MPQeos-JWGU-Documentation.pdf] 第 34 页

> [14] M. Ross; Generalized Lindemann melting law; Physical Review 184, 233
> 
> (1969). 11
> 
> [15] D. Young und E.M. Corey; A new global equation of state model for
> 
> hot, dense matter; J. Appl. Phy. 6 (1995) 3748; 14
> 
> [16] T. Group; SESAME Report on the Los Alamos Equation of State Li-
> brary; Report No. LALP-83-4, Los Alamos National Laboratory, Los
> Alamos (1983); 22
> 
> 34

## doc/FEOS/Multi1D++ EOS and Opacity - FEOS程序说明.pdf (2590125 B)

<!-- 提取说明: 共 43 页（pdfminer 解析出 44 段） -->

### [Multi1D++ EOS and Opacity - FEOS程序说明.pdf] 第 1 页

> FEOS 程序相关修改说明 
> 
> 1  理论介绍 
> 
> 1.1  参考文献 
> 
> 参见 QEOS 文献：fdm229 in Germany 
> MPQ229_Das Zustandsgleichungs-Modell QEOS fur heisse, dichte Materie 
> 1988,  R.M.  More  et  al.  A  new  quotidian  equation  of  state  for  hot  dense  matter[1],  Physics  of 
> Fluids 
> 1993PRE47.3547_Optical probing of hot expanded states produced by shock release 
> 介绍了 QEOS 模型和不足之处（低温低密度区。） 
> 2018CPC227(Steffen Faik)_The EOS package FEOS for HED matter 
> FEOS 是在 MPQeos 的进一步开发。 
> 
> 2  源代码的修改 
> 
> 2.1  从 Mac 到 Win 的源代码修改 
> 
> 主要有： 
> 头文件包含不用尖括号而用“” 
> 部分文件为 MAC 格式，拷贝到 Notepad++中再粘贴回去即可 
> 函数中数组定义大小不是常数，必须使用动态定义 
> 输出格式%15.8e,在 Windows 下默认 e 指数为 3 位数，强制设定为 2 位数。 
> 
> 2.2  程序代码功能 
> 
> Readfile 类库用来读取输入文件

### [Multi1D++ EOS and Opacity - FEOS程序说明.pdf] 第 2 页

> 3  FEOS 相关 
> 
> 3.1  运行 
> 
> Feos.exe Al 
> 如上命令寻找 Al.par 并执行相关的计算 
> 
> 3.2  数据库文件 
> 
> 3.2.1 FEOS_Material-DB.dat 
> 
> %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% 
> 
> %%%% FEOS material properties database %%%%%%%%%%%%%%%%%%% 
> 
> %%%%%%%%% version: 2012-08-31 %%%%%%%%%%%%%%%%%%%%%%%%% 
> 
> %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% 
> 
> % This file contains the FEOS material properties database. To add a new material, 
> 
> introduce a new section with an unused FEOS material number. Allowed numbers are: 1000-9999 
> 
> % The material number comes before each parameter in squared brackets. % 
> 
> %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% 
> 
> % The following properties have to be specified for each material:     % 
> 
> % - SESAME-Number: SESAME table number (if not known, set to 1000)     % 
> 
> % - Treference: Reference temperature in eV                            % 
> 
> % - Rhoreference: Density at Treference and zero pressure in g/cm^3    % 
> 
> % - Buld-Modulus: Bulkmodulus at Treference, Rreference in dyne/cm^2   % 
> 
> % - Number-of-Elements: Number of elements included in the material    % 
> 
> % - A[1...Element-Number]: Atomic weights of all included elements     % 
> 
> % - Z[1...Element-Number]: Atomic numbers of all included elements     % 
> 
> % - X[1...Element-Number]: Number of atoms per molecule                % 
> 
> %                          of all included elements                    % 
> 
> %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% 
> 
> % If you want to use the soft-sphere function, please specify also:    % 
> 
> % - Ecohesive: Cohesive energy / enthalphy of sublimation in erg/g     % 
> 
> % - Soft-Sphere-m: Parameter m in soft-sphere function                 % 
> 
> % - Soft-Sphere-n: Parameter n in soft-sphere function                 % 
> 
> %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% 
> 
> % Note that the equation-of-state is also calculated correctly if      % 
> 
> % X[1...Element-Number] is the percental fraction of each element in   % 
> 
> % a mixture, but then the total values of A, Z, and Q do not have a    % 
> 
> % physical meaning any more in the code and the output tables.         %

### [Multi1D++ EOS and Opacity - FEOS程序说明.pdf] 第 3 页

> %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% 
> 
> %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% 
> 
> %%%%%%%%%%%% Aluminum (Al) %%%%%%%%%%%%%%%%%%%%%%%%%%%% 
> 
> %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% 
> 
> Material-3717: 
> 
> [3717]_SESAME-Number = 3717 
> 
> [3717]_Treference = 2.585257e-2         % 2.585257771e-2 ---> 300 K 
> 
> [3717]_Rhoreference = 2.7 
> 
> [3717]_Bulk-Modulus = 7.5e11            % GPa value multiplied by 1.0e10  
> 
> [3717]_Number-of-Elements = 1 
> 
> [3717]_A[1] = 26.9815                   % Element 1: Aluminum (Al) 
> 
> [3717]_Z[1] = 13.0 
> 
> [3717]_X[1] = 1.0 
> 
> [3717]_Ecohesive = 12.123e10 
> 
> [3717]_Soft-Sphere-m = 0.5 
> 
> [3717]_Soft-Sphere-n = 2.0 
> 
> %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% 
> 
> %%%%%%%%%%%% Au (Au) %%%%%%%%%%%%%%%%%%%%%%%%%%%% 
> 
> %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% 
> 
> Material-1079: 
> 
> [1079]_SESAME-Number = 1079 
> 
> [1079]_Treference = 2.585257e-2         % 2.585257771e-2 ---> 300 K 
> 
> [1079]_Rhoreference = 19.28 
> 
> [1079]_Bulk-Modulus = 2.61e+12          % GPa value multiplied by 1.0e10  
> 
> [1079]_Number-of-Elements = 1 
> 
> [1079]_A[1] = 196.967                   % Element 1: Gold (Au) 
> 
> [1079]_Z[1] = 79.0 
> 
> [1079]_X[1] = 1.0 
> 
> %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% 
> 
> %%%%%% Fused silica (SiO2) %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% 
> 
> %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

### [Multi1D++ EOS and Opacity - FEOS程序说明.pdf] 第 4 页

> Material-7386: 
> 
> [7386]_SESAME-Number = 7386 
> 
> [7386]_Treference = 2.585257e-2         % 2.585257771e-2 ---> 300 K 
> 
> [7386]_Rhoreference = 2.2 
> 
> [7386]_Bulk-Modulus = 3.7e11            % GPa value multiplied by 1.0e10  
> 
> [7386]_Number-of-Elements = 2 
> 
> [7386]_A[1] = 28.0855                   % Element 1: Silicon (Si) 
> 
> [7386]_Z[1] = 14.0 
> 
> [7386]_X[1] = 1.0 
> 
> [7386]_A[2] = 15.9994                   % Element 2: Oxygen (O) 
> 
> [7386]_Z[2] = 8.0 
> 
> [7386]_X[2] = 2.0 
> 
> [7386]_Ecohesive = 9.736e10 
> 
> [7386]_Soft-Sphere-m = 0.8 
> 
> [7386]_Soft-Sphere-n = 2.8 
> 
> %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% 
> 
> %%%%%%%%%%%%%%%%%%%%%%%%%%%% end of database %%%%%%%%%%%%%%%%%%%%%%%%%%% 
> 
> %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% 
> 
> 3.2.2 FEOS_TF-Table_1197.dat 
> 
> 3.3  配置文件的修改  *.par 
> 
>                                       Computation-Settings 
> 
> Material-Number = 3717              % Material number in FEOS parameter database 
> 
> Maxwell_Flag = 1                          % "Maxwell construction" desired? (0: no, 1: yes) 
> 
> SoftSphere_Flag = 1                    % Replace TF cold curve for densities < Rsolid with   
> 
>                                                           %      soft sphere function? (0: no, 1: yes) 
> 
> UserCalculations_Flag = 1        % Perform user-defined calculations? (0: no, 1: yes) 
> 
>                                       Q-table   
> 
> % Distribution of densities:

### [Multi1D++ EOS and Opacity - FEOS程序说明.pdf] 第 5 页

> Rhonorm = 2.7          % Norm in g/cm^3 
> 
> Rhoratio-6 = 0        % Rhoratiox defines number of logarithmically distributed density   
> 
> Rhoratio-5 = 3        %      points in range Rnorm*1.0e(x-1) to Rnorm*1.0ex, x=-6...6 
> 
> Rhoratio-4 = 3        % Attention: Take care of lower density library limit! 
> 
> Rhoratio-3 = 3         
> 
> Rhoratio-2 = 10 
> 
> Rhoratio-1 = 50 
> 
> Rhoratio0 = 50 
> 
> Rhoratio1 = 50 
> 
> Rhoratio2 = 10 
> 
> Rhoratio3 = 3 
> 
> Rhoratio4 = 3 
> 
> Rhoratio5 = 3 
> 
> Rhoratio6 = 3 
> 
> % Distribution of temperatures: 
> 
> Tnorm = 1.0e3          % Norm in eV 
> 
> Tratio-6 = 1            % Tratiox defines number of logarithmically distributed temperature   
> 
> Tratio-5 = 2            %      points in range Tnorm*1.0e(x-1) to Tnorm*1.0ex, x=-6...6 
> 
> Tratio-4 = 10          % Attention: Take care of lower temperature library limit! 
> 
> Tratio-3 = 20           
> 
> Tratio-2 = 20 
> 
> Tratio-1 = 10 
> 
> Tratio0 = 2 
> 
> Tratio1 = 1 
> 
> Tratio2 = 1 
> 
> Tratio3 = 1 
> 
> Tratio4 = 0 
> 
> Tratio5 = 0 
> 
> Tratio6 = 0 
> 
> %% EOS table visualization (showeos): 
> 
>                                       General 
> 
> File-Format = 1        % 1: FEOS (recommended), 2: SESAME 301/304/305 
> 
> EOS-Type = 1              % 1: total, 2: electronic, 3: ionic, 4: Thomas-Fermi 
> 
> % FEOS format: Implies .feos file.   
> 
> %      All thermodynamic quantities are available! 
> 
> % SESAME format: Implies .301 (total), .304 (electrons), or .305 (ions) file.   
> 
> %      Thomas-Fermi EOS and charge state are not available! 
> 
> %%%%%%%%%%%%%%%%%%%%%%%

### [Multi1D++ EOS and Opacity - FEOS程序说明.pdf] 第 6 页

> Units 
> 
> Rho_unit = 1.0          % 1.0 ---> g/cm^3 
> 
> T_unit = 1.0              % 1.0 ---> eV, 8.617525902e-5 ---> K 
> 
> P_unit = 1.0e12        % 1.0 ---> dyne/cm^2, 1.0e12 ---> MBar 
> 
> E_unit = 1.0              % 1.0 ---> erg/g, 1.0e10 ---> MJ/kg 
> 
> U_unit = 1.0e5          % 1.0 ---> cm/s, 1.0e5 ---> km/s 
> 
> % The following units are set automatically: 
> 
> %      F_unit = E_unit, S_unit = E_unit / T_unit, 
> 
> %      V_unit = 1.0 / Rho_unit, Q_unit = 1.0 
> 
> %%%%%%%%%%%%%%%%%%%%%%% 
> 
>                                       Rho-T-Mesh 
> 
> % Distribution of densities: 
> 
> Rhomin = 1.0e-3        % Minimum density (in units which are defined above) 
> 
> Rhomax = 10                % Maximum density (in units which are defined above) 
> 
> Rhooriginal = 0        % Use only original tabulated densities? (0: no, 1: yes) 
> 
> Rhonumber = 5            % Number of densities (if Rhooriginal is set to 0)   
> 
> Rholog = 0                  % 0: linearly distributed, 1: logarithmically distributed 
> 
> % Distribution of temperatures (for isentropes only at Rhomin): 
> 
> Tmin = 1.0e-4        % Minimum temperature (in units which are defined above) 
> 
> Tmax = 1.0e3          % Maximum temperature (in units which are defined above) 
> 
> Toriginal = 0        % Use only original tabulated temperatures? (0: no, 1: yes) 
> 
> Tnumber = 7            % Number of temperatures (if Toriginal is set to 0)   
> 
> Tlog = 1                  % 0: linearly distributed, 1: logarithmically distributed 
> 
> % Only for isotherms, isochores, or Mountain plots: 
> 
> Rhofirst = 0          % Print out lowest density of table? (0: no, 1: yes) 
> 
> Tfirst = 1              % Print out lowest temperature of table? (0: no, 1: yes) 
> 
> % For isentropes, the entropies are initialized at (Rho=Rhomin, T=Tmin,...,Tmax). 
> 
> % => Number of isentropes = Number of temperatures 
> 
> % For isentropes, the maximum and minimum temperatures for Rho > Rhomin are given 
> 
> %      by the table boundaries, not by Tmin and Tmax. 
> 
>                                       Isocurves

### [Multi1D++ EOS and Opacity - FEOS程序说明.pdf] 第 7 页

> % Output settings for isotherms, isochores, and isentropes: 
> 
> Xquantity = 1        % Quantity which is printed out on the x-axis 
> 
> Xelement = 0          % Element number (only for charge state of mixtures, 0: sum) 
> 
> Yquantity = 4        % Quantity which is printed out on the y-axis 
> 
> Yelement = 0          % Element number (only for charge state of mixtures, 0: sum) 
> 
> % Possible choices for Xquantity and Yquantity:   
> 
> %      1: density, 2: specific volume, 3: temperature, 4: pressure,   
> 
> %      5: specific internal energy, 6: specific Helmholtz free energy,   
> 
> %      7: specific entropy, 8: summed-up or single-element charge state 
> 
>                                       Mountain 
> 
> % Quantity printed out as function of density / specific volume and temperature: 
> 
> Xquantity = 1        % 1: density, 2: specific volume 
> 
> Quantity = 4          % Mountain quantity as function of Xquantity and temperature 
> 
> Element = 0            % Element number (only for charge state of mixtures, 0: sum) 
> 
> % Possible choices for Quantity:   
> 
> %      4: pressure, 5: specific internal energy, 6: specific Helmholtz free energy,   
> 
> %      7: specific entropy, 8: summed-up or single-element charge state 
> 
> %%%%%%%%%%%%%%%%%%%%%%%   
> 
>                                       Hugoniot 
> 
> % Initial density and temperature: 
> 
> Rho0 = 2.7                    % Initial density (in units which are defined above) 
> 
> T0 = 2.585257e-2        % Initial temperature (in units which are defined above) 
> 
> % Calculation and output settings: 
> 
> Pmax = 1.0e8          % Maximum pressure (in units which are defined above) 
> 
> Xquantity = 1        % 1: density, 2: specific volume 
> 
> % Printed-out quantities are: density / specific volume, temperature,   
> 
> %      pressure, specific energy, shock wave velocity, particle velocity 
> 
> 3.4  MPQeos 的输入配置文件  *.PAR 
> 
> 给出老版本 MPQeos 的配置文件共参考： 
> AU.PAR 的内容解释

### [Multi1D++ EOS and Opacity - FEOS程序说明.pdf] 第 8 页

> 固体密度 
> 体积的弹性模量，可从元素周期表数据中查询 
> 标准温度 
> 
> 密度与固体密度比例在 10-7~10-6 间有 0 个点 
> 密度与固体密度比例在 10-6~10-5 间有 0 个点 
> 
> MPQeos 要设置的参数 
>           TF-Table 
> 
> Path = ../tabelle/tabelle1197 
> 
>           Maxwell-Construction 
> 
> Maxwell_Flag = 1 
> 
> Charge_Flag = 1 
> 
>           Material-Data 
> 
> A = 196.967 
> 
> Z = 79 
> 
> Rsolid = 19.28 
> 
> Bulk-Modulus = 2.61e+12 
> 
> T_standard = 0.0235 
> 
>           Q-table 
> 
> Rratio-6 = 0 
> 
> Rratio-5 = 0 
> 
> Rratio-4 = 4 
> 
> Rratio-3 = 4 
> 
> Rratio-2 = 10 
> 
> Rratio-1 = 20 
> 
> Rratio0 = 40 
> 
> Rratio1 = 40 
> 
> Rratio2 = 4 
> 
> Rratio3 = 0 
> 
> Rratio4 = 0 
> 
> Rratio5 = 0 
> 
> Rratio6 = 0 
> 
> Tratio-6 = 0 
> 
> Tratio-5 = 0 
> 
> Tratio-4 = 0 
> 
> Tratio-3 = 0 
> 
> Tratio-2 = 4 
> 
> Tratio-1 = 20 
> 
> Tratio0 = 40 
> 
> Tratio1 = 20 
> 
> Tratio2 = 4 
> 
> Tratio3 = 4 
> 
> Tratio4 = 4 
> 
> Tratio5 = 4 
> 
> Tratio6 = 0 
> 
> Showeos 程序需要的参数设置 
> 
> Units

### [Multi1D++ EOS and Opacity - FEOS程序说明.pdf] 第 9 页

> ChargeState, Pressure, Energy, Entropy, FreeEnergy 
> Isotherm  对应输出文件的后缀为( q, p, e, s, f)  如 Au.ist.e, 
> 
> 间距为指数否？ 
> 等*线条数 
> 是否包括一个 Cold Isotherm 
> 变量为密度或者体积 
> 是否只有给定表格中的等*线才显示？ 
> 
> 默认 Quantity 的单位为 cgs，这里可以设置转化数 
> 对应的输出文件后缀为 Au.isc.1 
> 
> P_unit=1 
> 
> R_unit=1 
> 
> E_unit=1 
> 
> V_unit=1 
> 
> T_unit=1 
> 
>           Isotherm 
> 
> Quantity = Pressure 
> 
> Tmin = 100 
> 
> Tmax = 200 
> 
> Rmin = 0.01 
> 
> Rmax = 1 
> 
> logarithmic = 0 
> 
> Number = 10 
> 
> ColdIso = 0 
> 
> Volume = 0 
> 
> Original = 0 
> 
> Offset = 0 
> 
> Units = 1 
> 
>           Isochores 
> 
> Quantity = Pressure 
> Tmin = 100 
> Tmax = 200 
> Rmin = 0.01 
> Rmax = 1 
> logarithmic = 0 
> Number = 10 
> Original = 0 
> Offset = 0 
> Units = 1 
> 
>           Isentropes 
> 
> Isentropes  对应的输出文件为  Au.IST 
> 
> Number = 10 
> Tmin = 100 
> Tmax = 200 
> Rmin = 0.01 
> Rmax = 1 
> 
>           Hugoniot 
> 
> Ro = 1 
> 
> To = 200 
> 
> Pmax = 1 
> 
> Mountain 
> 
> 输出文件为  .HUG 
> 起始点 
> 
> 最大压强 
> 
> *.mount.p

### [Multi1D++ EOS and Opacity - FEOS程序说明.pdf] 第 10 页

> Quantity = Pressure 
> 
> ChargeState, Pressure, Energy, Entropy,FreeEnergy 
> 
> Tmin = 100 
> 
> Tmax = 200 
> 
> Rmin = 0.01 
> 
> Rmax = 1 
> 
> Number = 10 
> 
> VolumeFlag = 1 
> 
> OriginalFlag = 1 
> 
> OffsetFlag = 1 
> 
> IsoUnits = 1 
> 参数的设置，要参考源代码  hugoniot_main.c 和  HugService.c/h 等文件才能够比较全面的梳
> 理 
> 
> 3.5  输出 log 
> 
> 3.5.1 典型输出 
> 
> FEOS.exe Ta2O5 
> 
> FEOS output file for Ta2O5.PAR: 
> SESAME EOS/Electron EOS/Ion EOS 
> Ta2O5.301/.304/.305 
> FEOS file 
> Ta2O5.feos                 
> Rostock format 
> Ta2O5.cst                   
> Ta2O5.mexport           
> SESAME mexport format 
> Ta2O5.data.txt         SESAME 301 standard format 
> Ta2O5.critical.dat  binodal, spinodal, boiling- and cp-data 
> 
> FEOS table generation tool 16.7 
> 
> => Initialize material entity 1... 
> 
> 执行的命令 
> 
> 输出文件罗列 
> 
> 程序版本 
> 初始化材料，只支持
> 一个材料

### [Multi1D++ EOS and Opacity - FEOS程序说明.pdf] 第 11 页

> 读取材料信息 
> 
>   Initialize Ionpart: 
> 
>     Read parameters for material 107522 from database: 
> 
>       SESAME-Number: 107522 
> 
>       Reference temperature: 2.585257e-002 eV 
> 
>       Reference density: 1.000000e+000 g/cm^3 
> 
>       Bulk modulus: 0.000000e+000 dyne/cm^2 
> 
>       Number of elements: 2 
> 
>       Element 1 of 2: A = 15.999360, Z = 8.000000, X = 5.000000 
> 
>       Element 2 of 2: A = 180.948368, Z = 73.000000, X = 2.000000 
> 
>     Done. 
> 
>     Total (mean) value of A: 441.893536 (63.127648) 
> 
>     Total (mean) value of Z: 186.000000 (26.571429) 
> 
>   Ionpart successfully initialized. 
> 
>   Initialize QIPscheme for element 1 (A = 15.999360, Z = 8.000000): 
> 
> 元素 1 的 QIPscheme 
> 
>     Read Thomas-Fermi table: 
> 
>       Source: ./FEOS_TF-Table_1197.dat 
> 
>       Allocate memory for Thomas-Fermi table... done. 
> 
>       Table size (densities x temperatures): 93 x 44 
> 
>       Table boundaries (density, temperature): 
> 
>         (1.000000e-006 g/cm^3, 0.000000e+000 eV) ... 
> 
>         ... (1.584893e+003 g/cm^3, 1.000000e+006 eV) 
> 
>     Done. 
> 
>     Generate H table... done. 
> 
>     Initialize QEOS interpolation scheme... done. 
> 
>   QIPscheme for element 1 successfully initialized. 
> 
> Initialize QIPscheme for element 2 (A = 180.948368, Z = 73.000000): 
> 
> 元素 2 的 QIPscheme 
> 
>     Read Thomas-Fermi table: 
> 
>       Source: ./FEOS_TF-Table_1197.dat 
> 
>       Allocate memory for Thomas-Fermi table... done. 
> 
>       Table size (densities x temperatures): 93 x 44 
> 
>       Table boundaries (density, temperature): 
> 
>         (1.000000e-006 g/cm^3, 0.000000e+000 eV) ... 
> 
>         ... (1.584893e+003 g/cm^3, 1.000000e+006 eV) 
> 
>     Done. 
> 
>     Generate H table... done. 
> 
>     Initialize QEOS interpolation scheme... done. 
> 
>   QIPscheme for element 2 successfully initialized.

### [Multi1D++ EOS and Opacity - FEOS程序说明.pdf] 第 12 页

> Compute dPe/dRho at reference temperature and density: 
> 
>     Pe(1.000000e+000 g/cm^3, 2.585257e-002 eV) = 1.118072e+010 dyne/cm^2 
> 
>     dPe/dRho(1.000000e+000  g/cm^3,  2.585257e-002  eV)  =  2.700151e+010 
> 
> dyne*cm/g 
> 
>   Done. 
> 
>   Calculate bonding contribution parameters: 
> 
>     E0 = 7.270869e+009 erg/g 
> 
>     b = 5.059149e+000 
> 
>   Done. 
> 
>   Calculate energy offsets: 
> 
>     Ei_Offset = +7.624256e+008 erg/g 
> 
>     Ee_Offset = -2.048830e+015 erg/g 
> 
>   Done. 
> 
> <= Material entity 1 successfully initialized. 
> 
> Allocate & reset memory for EOS parameters / charge state... done. 
> <=> Material parameters of material entity 1 successfully passed. 
> <=> Energy offsets of material entity 1 successfully passed. 
> 
> Compute EOS-table data: 
>   Processing temperature [eV]: 
>     0.000000e+000, 1.000000e-001, 1.778279e-001, 3.162278e-001, 5.623413e-001, 
> 
>     1.000000e+000, 1.122018e+000, 1.258925e+000, 1.412538e+000, 1.584893e+000, 
> 
>     1.778279e+000, 1.995262e+000, 2.238721e+000, 2.511886e+000, 2.818383e+000, 
> 
>     3.162278e+000, 3.548134e+000, 3.981072e+000, 4.466836e+000, 5.011872e+000, 
> 
>     5.623413e+000, 6.309573e+000, 7.079458e+000, 7.943282e+000, 8.912509e+000, 
> 
>     1.000000e+001, 1.059254e+001, 1.122018e+001, 1.188502e+001, 1.258925e+001, 
> 
>     1.333521e+001, 1.412538e+001, 1.496236e+001, 1.584893e+001, 1.678804e+001, 
> 
>     1.778279e+001, 1.883649e+001, 1.995262e+001, 2.113489e+001, 2.238721e+001, 
> 
>     2.371374e+001, 2.511886e+001, 2.660725e+001, 2.818383e+001, 2.985383e+001, 
> 
>     3.162278e+001, 3.349654e+001, 3.548134e+001, 3.758374e+001, 3.981072e+001, 
> 
>     4.216965e+001, 4.466836e+001, 4.731513e+001, 5.011872e+001, 5.308844e+001, 
> 
>     5.623413e+001, 5.956621e+001, 6.309573e+001, 6.683439e+001, 7.079458e+001, 
> 
>     7.498942e+001, 7.943282e+001, 8.413951e+001, 8.912509e+001, 9.440609e+001, 
> 
>     1.000000e+002, 1.122018e+002, 1.258925e+002, 1.412538e+002, 1.584893e+002, 
> 
>     1.778279e+002, 1.995262e+002, 2.238721e+002, 2.511886e+002, 2.818383e+002, 
> 
>     3.162278e+002, 3.548134e+002, 3.981072e+002, 4.466836e+002, 5.011872e+002, 
> 
>     5.623413e+002, 6.309573e+002, 7.079458e+002, 7.943282e+002, 8.912509e+002, 
> 
>     1.000000e+003, 1.778279e+003, 3.162278e+003, 5.623413e+003, 1.000000e+004, 
> 
>     1.778279e+004, 3.162278e+004, 5.623413e+004, 1.000000e+005, 1.778279e+005, 
> 
>     3.162278e+005, 5.623413e+005. 
> 
>   WARNING:  219  density-temperature  points  below  library  calculation 
> limits! 
> 
> 初始化结果 
> 
> 按 照 温 度 密 度 网 格
> 计算 EOS 
> 
> 警告多少温度、密度
> 在计算限制以下，对
> 低 温
> Maxwell 
> reconstruction 情 况
> 有影响。

### [Multi1D++ EOS and Opacity - FEOS程序说明.pdf] 第 13 页

> 输出文件的日志 
> 
> Done. 
> 
> Write FEOS table format (Ta2O5.feos): 
>   Table size (densities x temperatures): 123 x 97 
>   Table boundaries (density, temperature): 
>     (0.000000e+000 g/cm^3, 0.000000e+000 eV) ... 
>     ... (1.000000e-005 g/cm^3, 1.000000e-001 eV) ... 
>     ... (5.623413e+001 g/cm^3, 5.623413e+005 eV) 
> Done. 
> 
> Write SESAME mexport table format (Ta2O5.mexport): 
>   Table size (densities x temperatures): 123 x 97 
>   Table boundaries (density, temperature): 
>     (0.000000e+000 g/cm^3, 0.000000e+000 eV) ... 
>     ... (1.000000e-005 g/cm^3, 1.000000e-001 eV) ... 
>     ... (5.623413e+001 g/cm^3, 5.623413e+005 eV) 
> Done. 
> 
> Write SESAME table format (Ta2O5.301): 
>   Table size (densities x temperatures): 123 x 97 
>   Table boundaries (density, temperature): 
>     (0.000000e+000 g/cm^3, 0.000000e+000 eV) ... 
>     ... (1.000000e-005 g/cm^3, 1.000000e-001 eV) ... 
>     ... (5.623413e+001 g/cm^3, 5.623413e+005 eV) 
> Done. 
> 
> Write SESAME table format for electrons (Ta2O5.304): 
>   Table size (densities x temperatures): 123 x 97 
>   Table boundaries (density, temperature): 
>     (0.000000e+000 g/cm^3, 0.000000e+000 eV) ... 
>     ... (1.000000e-005 g/cm^3, 1.000000e-001 eV) ... 
>     ... (5.623413e+001 g/cm^3, 5.623413e+005 eV) 
> Done. 
> 
> Write SESAME table format for ions (Ta2O5.305): 
>   Table size (densities x temperatures): 123 x 97 
>   Table boundaries (density, temperature): 
>     (0.000000e+000 g/cm^3, 0.000000e+000 eV) ... 
>     ... (1.000000e-005 g/cm^3, 1.000000e-001 eV) ... 
>     ... (5.623413e+001 g/cm^3, 5.623413e+005 eV) 
> Done. 
> 
> Write text table format (Ta2O5.data.txt):

### [Multi1D++ EOS and Opacity - FEOS程序说明.pdf] 第 14 页

> Table size (densities x temperatures): 123 x 97 
>   Table boundaries (density, temperature): 
>     (0.000000e+000 g/cm^3, 0.000000e+000 eV) ... 
>     ... (1.000000e-005 g/cm^3, 1.000000e-001 eV) ... 
>     ... (5.623413e+001 g/cm^3, 5.623413e+005 eV) 
> Done. 
> 
> Write charge state table / Rostock format (Ta2O5.cst)... done. 
> 
> ====================== 
> ====================== 
> 
> Start 
> 
> user-defined 
> 
> calculations 
> 
> Calculate isobaric expansion data along P ~ 0 bar: 
>   Tstart = 1.000000e-004 eV 
>   Tend = 5.170430e-001 eV 
>   T [eV]          Rho [g/cm^3] Alpha [1/eV] H [erg/g]        P [dyne/cm^2] Cp 
> [erg/eVg] 
>   1.0000e-004 
> -1.510934e+001 -1.37914e+009 
>   2.5947e-002  0.000000e+000 
> +0.000000e+000            --- 
> Done. 
> 
> 1.514104e+000 
> 
> +2.17864e-001 
> 
> -1.09611e+009 
> 
> --- 
> 
> ---         
> 
> 用户自定义计算 
> UserCalculations_Flag 
> 需 要 修 改 代 码 来 修
> 改，界面上禁止。 
> 
> Write isobaric expansion data (Ta2O5.isobaric.dat)... done. 
> 
> End 
> 
> user-defined 
> 
> calculations 
> 
> 结束计算 
> 
> ======================= 
> ======================= 
> 
> => Finalize FEOS library... 
> 
> <=> Material entity 1 successfully deleted. 
> 
> <= FEOS library successfully finalized. 
> 
> Free all memory... done. 
> 
> CPU runtime: 29.66 seconds 
> 
> 2023-04-26T134826> Execution of Ta2O5.PAR finished OK.

### [Multi1D++ EOS and Opacity - FEOS程序说明.pdf] 第 15 页

> 3.5.2 library calculation limit 
> 
> 日志中对温度和密度的检查结果： 
> WARNING: 1 temperature below library calculation limit 1.00e-004 eV! 
> WARNING: 1 density below library calculation limit 1.00e-050 g/cm^3! 
> 程序中定义了 T_ZERO=1.00e-004  eV,  RHO_ZERO=1.00e-050  g/cm^3，对低温下的 Maxwell 
> construction 很重要。 
> lower  borders  for  density  and  temperature;  take  care  for  stability  and  constant  ZERO!  T  in  eV, 
> RHO in g/ccm; important for low temperature Maxwell construction 
> 
> 3.6  输出数据文件 
> 
> 一次 FEOS 运行将生成如下几种数据文件。 
> 
> 3.6.1 SESAME *.301/304/305 
> 
> table contains pressure, energy and charge state data 
> 301: Total EOS 
> 304: Ion EOS + Cold Curve 
> 305: Electron EOS 
> Check matter-tablegui.0_0507.pdf, or  
> 1994 Johnson, The SESAME database 
> 
>         // SESAME 301 standard format 
>         // indices start at 0 
>         // 
>         // with Pressure, Energy, Charge State 
>         // 
>         // SESAME units are 
>         // 
>         // Pressure in GPa 
>         // energy in MJ/kg 
>         // density Mg/m3 
> 
> // temperature in Kelvin 
> 
> 批注 [T1]: FEOS 中 304 是电子
> 
> EOS,305 是离子 EOS

### [Multi1D++ EOS and Opacity - FEOS程序说明.pdf] 第 16 页

> 3.6.2 SESAME 材料数据表格种类

### [Multi1D++ EOS and Opacity - FEOS程序说明.pdf] 第 19 页

> 3.6.3 SESAME 中的材料编号 
> 
> 表  1

### [Multi1D++ EOS and Opacity - FEOS程序说明.pdf] 第 21 页

> 3.6.4 *.critical.dat 
> 
> write_criticaldata() 
> 包括 binodal, spinodal, boiling- and cp-data 
> 信息不是格式化的，而是分块显示的： 
> # Critical point: Tc = 5657.66 K, Pc = 1721.46 bar, Rhoc = 0.3317 g/cm³, 
> 
> #                                  Hc = 11.56 kJ/g, Sc/R = 16.7166, Zc = 0.30 
> 
> # Two-phase-boundary (binodal) calculated by finding densities with equal pressure and Gibbs free energy!   
> 
> # Boiling temperature: Tb = 2739.81 K   
> 
> # Number of calculated isotherms below cp: Niso = 27   
> 
> # Temperatures in Kelvin: 
> 
> # 1.160445e+00, 1.160445e+01, 3.669649e+01, 1.160445e+02, 1.460914e+02, 1.839181e+02,   
> 
> # 2.315392e+02, 2.914906e+02, 3.669649e+02, 4.619815e+02, 5.816002e+02, 7.321913e+02,   
> 
> # 9.217742e+02, 1.160445e+03, 1.302041e+03, 1.460914e+03, 1.639172e+03, 1.839181e+03,   
> 
> # 2.063595e+03, 2.315392e+03, 2.597913e+03, 2.914906e+03, 3.270578e+03, 3.669649e+03,   
> 
> # 4.117414e+03, 4.619815e+03, 5.183517e+03 
> 
> # Check P_sat = P_vap = P_liq and G_vap = G_liq for good accuracy of binodal: 
> 
> # T [Kelvin]    Rho_vap [g/cm³]    Rho_liq [g/cm³]    P_sat [bar]    P_vap [bar]    P_liq [bar]    G_vap [kJ/g]    G_liq [kJ/g] 
> 
> 1.160445e+00    1.000000e-50    2.722570e+00    3.550148e-50    +3.550148e-50    -2.472565e-02    +1.208268e+01    -1.615546e-01 
> 
> 1.160445e+01    1.000000e-50    2.722569e+00    3.554948e-49    +3.554948e-49    -4.720435e-03    +1.170708e+01    -1.615580e-01 
> 
> # Binodal in Rho-P-plane 
> # Rho [g/cm³]    P_sat [bar] 
> 1.000000e-50    +3.550148e-50 
> 
> # Spinodal in Rho-P-plane 
> # Rho [g/cm³]    P_sat [bar] 
> 2.274633e-09    +2.704238e-09 
> 
> # Binodal in T-Rho-plane 
> # T [Kelvin]    Rho [g/cm³] 
> 1.160445e+00    1.000000e-50 
> 
> # Spinodal in T-Rho-plane 
> # T [Kelvin]    Rho [g/cm³] 
> 1.160445e+00    2.274633e-09 
> 
> # Diamener curve in T-Rho-plane

### [Multi1D++ EOS and Opacity - FEOS程序说明.pdf] 第 22 页

> # T [Kelvin]    1/2*Rho_liq+1/2*Rho_vap [g/cm³] 
> 1.160445e+00    1.361285e+00 
> 
> # Binodal in T-H-plane 
> # T [Kelvin]    H [kJ/g] 
> 1.160445e+00    +1.212389e+01 
> 
> # Evaporation heat in T-DeltaH-plane 
> # T [Kelvin]    DeltaH [kJ/g] 
> 1.160445e+00    +1.228544e+01 
> 
> # Saturation curve in Arrhenius coordinates 
> # 1/T [T in Kelvin]    log10(P_sat) [P_sat in bar] 
> 1.767516e-04    +3.235896e+00 
> 
> # Compressibility factor in T-Z-plane 
> # T [Kelvin]    Z 
> 1.160445e+00    +9.992845e-01 
> 
> # Compressibility factor in P-Z-plane 
> # P_sat [bar]    Z 
> 3.550148e-50    +9.992845e-01 
> …… 
> 3.550148e-50    -2.556298e-03 
> # eof. 
> 
> 3.6.5 (MPQeos)KATACO 数据库  *.KAT 
> 
> KATACO: Karlsruhe Target radiation-hydrodynamics Code. 
> 文件内容如：

### [Multi1D++ EOS and Opacity - FEOS程序说明.pdf] 第 23 页

> KATACO table for AU   
>       122    100    1 
>     ***** mass density rho [kg/m**3] 
> 1.92800000e-001 3.42852270e-001 6.09687133e-001 1.08419407e+000 
> 
> 1.92800000e+000 3.42852270e+000 6.09687133e+000 1.08419407e+001 
> 
> 1.92800000e+001 2.42720819e+001 3.05567408e+001 3.84686574e+001 
> 
> …… 
> 6.09687133e+005 1.08419407e+006   
>     ***** temperature T [K] 
> 1.16044500e+001 2.06359545e+001 3.66964930e+001 6.52566179e+001 
> …… 
> 1.16044500e+008 2.06359545e+008 3.66964930e+008 6.52566179e+008 
>     ***** Zeff 
> 9.70149975e+000 8.09330375e+000 7.18894869e+000 6.68039246e+000 
> …… 
> 1.71720578e+001 1.75850806e+001 1.80013812e+001 2.24292833e+001 
> 2.72501027e+001 3.23084483e+001   
> 9.70149975e+000 8.09330375e+000 7.18894869e+000 6.68039246e+000 
> …. 
> 
> 3.6.6 Rostock 数据库*.cst 
> 
> Rostock format,  相同温度下不同的密度下的压力和电离度 
> 
> Isotherme T = 0 Kelvin   
> Moleküldichte[1/cm^3]    Massendichte[g/cm^3]    Druck[MBar]    Ladungszustand 
> 0.000000e+00                    0.000000e+00                    3.550148e-56        2.781091e+01 
> 
> Isotherme T = 1 Kelvin   
> Moleküldichte[1/cm^3]    Massendichte[g/cm^3]    Druck[MBar]    Ladungszustand 
> MolecularDensity[1/cm^3] MassDensity[g/cm^3] Pressure[Mbar] ChargeState 
> 
> 3.6.7 *.data.txt 
> 
> 数据为多行的 GNUPlot 格式，每个温度一个数据块。 
> 密度 index,  温度 index,  密度,  温度, P, Pi,Pe,E,Ei,Ee 
> 
> 此数据可以直接用 gnuplot 绘图

### [Multi1D++ EOS and Opacity - FEOS程序说明.pdf] 第 24 页

> 3.6.8 *.feos 
> 
> 总的，电子，离子 EOS 和 Thomas-Fermi 电离度的结果。 
> 
> 3.6.8.1   格式说明 
> 
> Feos 的格式根据 FEOS 代码 FE-01_TABTOOLS::write_FEOS_format()整理如下： 
> 输出包括 Pressure, Energy, Free Energy, Entropy, Charge states, EOS parameters 
> 单位为 cgs + eV for temperature 
> 开头两行为 EOS parameter，以%15.8le 格式输出，每行 10 个数字 
> FileVersion,  NR+1,  NT+1,  Nelements+1,  Tcalclimit,  Rhocalclimit,  RhoRef,  TRef,  BulkModulusRef, 
> SESAMEnumber 
> 
> ElectronOffset,  IonOffset,  Ecoh,  softsphere_n,  softsphere_m,  softsphere_A,  softsphere_B,  Atot, 
> Ztot, Xtot 
> 
> 然后是数据，每 10 个换行 
> Nelements+1 个 A 
> Nelements+1 个 Z   
> Nelements+1 个 X 
> NR+1 个 Rho, NT+1 个 T 
> 
> 然后是 EOS 数据，按照某一温度下的各个密度点的参数打印（与 SESAME 格式相同）。 
> 总的 EOS: 
> P[NR+1][NT+1], E[NR+1][NT+1], S[NR+1][NT+1], F[NR+1][NT+1], 
> 电子 EOS: 
> Pe[NR+1][NT+1], Ee[NR+1][NT+1], Se[NR+1][NT+1], Fe[NR+1][NT+1], 
> 离子 EOS: 
> Pi[NR+1][NT+1], Ei[NR+1][NT+1], Si[NR+1][NT+1], Fi[NR+1][NT+1], 
> pure Thomas-Fermi EOS: 
> PTF[NR+1][NT+1], ETF [NR+1][NT+1], STF [NR+1][NT+1], FTF [NR+1][NT+1], 
> Charge States: 
> Qtot[NR+1][NT+1] 
> 各个成分的电离度 
> Q[NR+1][NT+1][Nelements+1] 
> 完毕 
> 
> 3.6.9 *.isobaric.dat 
> 
> FE-02_CALCULATIONS.Cpp: write_isobaricdata() 
> 包含 isobaric expansion 数据

### [Multi1D++ EOS and Opacity - FEOS程序说明.pdf] 第 25 页

> # Calculated isobaric expansion data (P ~= 0) from 1.16 to 6000.00 Kelvin: 
> 
> # T [K]              Rho [g/cm^3]    P [bar]                Alpha [1/K]        H [J/g]                Cp [J/gK] 
> 
> 1.160445e+00    2.722570e+00    -1.437096e-02    -0.000000e+00    -1.615541e+02    +3.605368e-05 
> 
> …… 
> 
> 5.100174e+03    8.851015e-01    -2.009758e-04    +1.319761e-03    +7.051855e+03    +5.834802e+00 
> 
> 5.400116e+03    0.000000e+00    +0.000000e+00              ---                        ---                        --- 
> 
> # Data in T-Rho-plane 
> 
> # T [Kelvin]    Rho [g/cm³] 
> 
> 1.160445e+00    2.722570e+00   
> 
> … 
> 
> 5.400116e+03    0.000000e+00 
> 
> # eof. 
> 
> 3.6.10 *.mexport 
> 
> 参考 write_mexport_format() 
> SESAME mexport 文件格式，输出 Pressure, Energy, Free Energy 
> SESAME 单位制为： 
> Pressure in GPa ~ 1e10 dyne/cm2 
> energy in MJ/kg – 1e10 erg/g 
> density Mg/m3 – g/cm3 
> temperature in Kelvin 
> 开头的几行如下 
> 第 1 行：0, SESAME number,  固定的几个数 
> 0    3717      101      160      r                0                0      1                                                                  1 
> 第 2 行：材料的信息和时间（补足 80 个字符一行） 
> material. Al (Zmean=13.0, Amean=26.98) /source. feos /date 201311211706                   
> 第 3 行：文字 
> /refs. none /comp. LULI /codes. FEOS /             
> 第 4 行：类似第 1 行                                                                         
> 1    3717      102        80      r                0                0      1                                                                  1 
> 第 5 行：文字 
> contact: tommaso.vinci@polytechnique.edu   
> 第 5 行：文字                                                                               
> 1    3717      201          5      r                0                0      1                                                                1 
> 第 6 行：Zmat, Amat, rhosolid, Bulkmat/1e10, 0,+11100 
>   1.30000000e+01 2.69815000e+01 2.70000000e+00 7.50000000e+01 0.00000000e+0011100 
> 第 7 行：1, SESAMEnumber, 301, 2+(NR+1)+(NT+1)+ 3*(NR+1)*(NT+1),0,0,1,1 
> 1    3717      301 40007      r                0                0      1                                                                  1 
> 下面是正式数据(每行 5 个数，后加五位控制字符，表示该行五个数中哪个为 0)： 
> NR+1, NT+1, Rho[NR+1], T[NT+1], P[NR+1][NT+1], E[NR+1][NT+1], F[NR+1][NT+1] 
> 最后以空格塞满数据行，control 标示处无效数字的个数。 
> Electron EOS 304

### [Multi1D++ EOS and Opacity - FEOS程序说明.pdf] 第 26 页

> 批注 [T2]: 程序中此处为 F 不是 Fe 是
> 
> 否是编程错误？ 
> 
> 1, SESAMEnumber, 304, 2+(NR+1)+(NT+1)+ 3*(NR+1)*(NT+1),0,0,1,1 
> NR+1, NT+1, Rho[NR+1], T[NT+1], Pe[NR+1][NT+1], Ee[NR+1][NT+1], F[NR+1][NT+1] 
> Ionic EOS 305 
> 1, SESAMEnumber, 305, 2+(NR+1)+(NT+1)+ 3*(NR+1)*(NT+1),0,0,1,1 
> NR+1, NT+1, Rho[NR+1], T[NT+1], Pi[NR+1][NT+1], Ei[NR+1][NT+1], F[NR+1][NT+1] 
> 最后结束行为: 
> 2                                                                                                                                                      2 
> 
> 3.7  如何在 Multi1D++中使用输出文件 
> 
> Multi1D++支持 FEOS 格式的状态方程，可以直接将*.feos 添加到新建材料的 EOS 中，程序自
> 动解析 FEOS 并生成 EOS, IEOS 和 EEOS。 
> 推荐使用*.feos 格式。 
> 或者：使用 SESAME 格式的 301，或者使用 304/305 单独制定电子和离子的状态方程。 
> 
> 示例操作： 
> 在 Multi1D++界面，打开材料列表。选择以某个材料为基础构建新材料则选中材料点击右键，
> 在菜单中选择 Creat new material based on selected one 或者点击 Add New Material 按钮直接
> 添加新材料。 
> 
> 在材料定义界面下的 EOS 标签页，点击 EOS 右侧的…按钮浏览找到新生成的*.feos 选中即可。 
> 
> 如果是新建材料，那么你还需要继续完成剩余的材料定义。

### [Multi1D++ EOS and Opacity - FEOS程序说明.pdf] 第 27 页

> 4  ShowEOS 相关 
> 
> 4.1  运行 
> 
> 4.1.1 MPQeos 的处理 
> 
> Showeos.exe 从*.301 文件读入数据并转化为方便处理的数据文件 
> Choose type of plot 
> 1 for Isotherms 
> 2 for Isochores  
> 3 for Hugoniot  
> 4 for Isentropes 
> 5 for Mountain-Plot 
> 6 for a single point info.  结果直接打印在屏幕上 
> 而 FEOS 则从*.feos 文件中读取数据，并转化为方便处理的数据文件。 
> 
> Au.ist.p 
> Au.isc.1 
> Au.HUG 
> Au.IST 
> 
> Au.mount.p 
> 
> 4.1.2 图形界面 ShowEOS Parameters 
> 
> 状态方程计算页面有 ShowEOS  Parameters 标签页，可以调用 ShowEOS.exe 并生成 GNUPlot
> 脚本生成图片。 
> 具体操作为： 
> a)  选择要绘制的图像 
> b)  修改下方标签页的参数 
> c)  保存（因为 ShowEOS 用到的参数也是存在*.par 里面的） 
> d)  点击运行 Run ShowEOS，程序会根据选项生成想要的数据和绘图脚本 
> e)  点击 Plot 可以绘制。 
> 更多信息可以查看 log 日志中的说明，包括保存的文件等。 
> 
> 4.1.3 基本命令 
> 
> showeos <name of parameter file> <option> [<rho(Rho_unit)> <T(T_unit)>] 
> 
> showeos %s <option> [<rho(Rho_unit)> <T(T_unit)>] 
> 
> showeos %s 6 <rho(Rho_unit)> <T(T_unit)>\n\nValues for Rho and T are not correctly specified. 
> 
> SHOWEOS table visualization tool 12.9-beta 
> 
> Usage: showeos Al <option> [<rho(Rho_unit)> <T(T_unit)>]

### [Multi1D++ EOS and Opacity - FEOS程序说明.pdf] 第 28 页

> Possible values for <option> are: 
>   1 for Isotherms 
>   2 for Isochores 
>   3 for Isentropes 
>   4 for Mountain-Plot 
>   5 for Hugoniot-Curves 
>   6 <rho(Rho_unit)> <T(T_unit)> for a single point info 
> 
> 4.1.4   Showeos Al 1(Isotherms)   
> 
> 等温下的密度、压强 
> SHOWEOS table visualization tool 12.9-beta 
> Read and check general parameters and units from source Al.par... done. 
> Check file version and read table size from source Al.feos... done. 
> Allocate & reset memory for EOS-table... done. 
> Allocate & reset memory for EOS parameters / charge state... done. 
> Read FEOS table format (Al.feos): 
>   Table size (densities x temperatures): 192 x 69 
>   Table boundaries (Rho [1.000000e+000 g/cm^3], T [1.000000e+000 eV]): 
>     (0.000000e+000, 0.000000e+000) ... 
>     ... (2.700000e-006, 1.000000e-004) ... 
>     ... (1.253229e+006, 1.000000e+005) 
> Done. 
> 
> Calculate isotherms: 
>   Read and check mesh parameters from source Al.par... done. 
>   Initialize density-temperature mesh... done. 
>   Determine output-quantities from source Al.par... done. 
>   Processing temperature [1.000000e+000 eV]: 
>     0.000000e+000, 1.000000e-004, 2.511886e-003, 6.309573e-002, 1.584893e+000, 
>     3.981072e+001, 1.000000e+003. 
>   Wrote 7 isotherms to file Al.Rho-P.ist. 
> Done. 
> 
> Free all memory... done. 
> CPU runtime: 0.36 seconds 
> 
> 4.1.4.1 Al.Rho-P.ist 
> 
> # T = 0.000000e+000 [1.000000e+000 eV]: 
> # Rho [1.000000e+000 g/cm^3]    P [1.000000e+012 dyne/cm^2]

### [Multi1D++ EOS and Opacity - FEOS程序说明.pdf] 第 29 页

> 1.000000e-003    3.550148e-056 
> …… 
> 1.000000e+001    1.348279e+001 
> & 
> # T = 1.000000e-004 [1.000000e+000 eV]: 
> # Rho [1.000000e+000 g/cm^3]    P [1.000000e+012 dyne/cm^2] 
> 1.000000e-003    3.550148e-056 
> …… 
> …… 
> 1.000000e+001    4.684977e+003 
> # eof. 
> 
> 4.1.5   Showeos Al 2(Isochores) 
> 
> 等容（等密度） 
> Calculate isochores: 
>   Read and check mesh parameters from source Al.par... done. 
>   Initialize density-temperature mesh... done. 
>   Determine output-quantities from source Al.par... done. 
>   Processing density [1.000000e+000 g/cm^3]: 
>     1.000000e-003, 2.500750e+000, 5.000500e+000, 7.500250e+000, 1.000000e+001. 
>   Wrote 5 isochores to file Al.Rho-P.isc. 
> Done. 
> 
> Free all memory... done. 
> CPU runtime: 0.19 seconds 
> 
> 4.1.5.1 Al.Rho-P.isc 
> 
> # Rho = 1.000000e-003 [1.000000e+000 g/cm^3]: 
> # Rho [1.000000e+000 g/cm^3]    P [1.000000e+012 dyne/cm^2] 
> 1.000000e-003    3.550148e-056 
> …… 
> 1.000000e-003    4.940793e-001 
> & 
> # Rho = 2.500750e+000 [1.000000e+000 g/cm^3]: 
> # Rho [1.000000e+000 g/cm^3]    P [1.000000e+012 dyne/cm^2] 
> 2.500750e+000    3.550148e-056 
> …… 
> …… 
> 1.000000e+001    4.684977e+003 
> # eof.

### [Multi1D++ EOS and Opacity - FEOS程序说明.pdf] 第 30 页

> 4.1.6   Showeos Al 3(Isentropes) 
> 
> 等熵下的密度压强等 
> Calculate isentropes: 
>   Read and check mesh parameters from source Al.par... done. 
>   Initialize density-temperature mesh... done. 
>   Determine output-quantities from source Al.par... done. 
>   Processing entropy [1.000000e+000 erg/(g*eV)]: 
>     5.448559e+006, 5.305283e+008, 9.596874e+010, 8.799830e+011, 1.934859e+012, 
>     5.519404e+012, 8.483292e+012. 
>   Wrote 7 isentropes to file Al.Rho-P.ise. 
>   Attention: Not all isentropes could be calculated up to Rhomax! 
> Done. 
> 
> Free all memory... done. 
> CPU runtime: 0.20 seconds 
> 
> 4.1.6.1 Al.Rho-P.ise 
> 
> # S = 5.448559e+006 [1.000000e+000 erg/(g*eV)]: 
> # Rho [1.000000e+000 g/cm^3]    P [1.000000e+012 dyne/cm^2] 
> 1.000000e-003    3.550148e-056 
> … 
> 1.000000e+001    1.348279e+001 
> & 
> # S = 5.305283e+008 [1.000000e+000 erg/(g*eV)]: 
> # Rho [1.000000e+000 g/cm^3]    P [1.000000e+012 dyne/cm^2] 
> 1.000000e-003    5.225144e-055   
> …… 
> …… 
> 1.000000e+001    4.751915e+004 
> & 
> # S = 8.483292e+012 [1.000000e+000 erg/(g*eV)]: 
> # Rho [1.000000e+000 g/cm^3]    P [1.000000e+012 dyne/cm^2] 
> 1.000000e-003    4.940793e-001 
> # eof. 
> 
> 4.1.7   Showeos Al 4(Mountain-Plot) 
> 
> 温度、密度下的压强等参数 
> Calculate mountain data: 
>   Read and check mesh parameters from source Al.par... done.

### [Multi1D++ EOS and Opacity - FEOS程序说明.pdf] 第 31 页

> Initialize density-temperature mesh... done. 
>   Determine output-quantities from source Al.par... done. 
>   Table size (densities x temperatures): 5 x 7 
>   Processing table... done. 
>   Wrote mountain data to file Al.Rho-T-P.mnt. 
> Done. 
> 
> Free all memory... done. 
> CPU runtime: 0.20 seconds 
> 
> 4.1.7.1 Al.Rho-T-P.mnt 
> 
> # NRho    NT    NP 
> 5    7    35 
> & 
> # Rho [1.000000e+000 g/cm^3] 
> 1.000000e-003 
> 2.500750e+000 
> 5.000500e+000 
> 7.500250e+000 
> 1.000000e+001 
> & 
> # T [1.000000e+000 eV] 
> 0.000000e+000 
> 1.000000e-004 
> 2.511886e-003 
> 6.309573e-002 
> 1.584893e+000 
> 3.981072e+001 
> 1.000000e+003 
> & 
> # P [1.000000e+012 dyne/cm^2] 
> 3.550148e-056   
> …… 
> 4.684977e+003 
> # eof. 
> 
> 4.1.8   Showeos Al 5(Hugoniot-Curves) 
> 
> Calculate Hugoniot: 
>   Read Hugoniot parameters from source Al.par... done. 
>   Upper calculation boundary:

### [Multi1D++ EOS and Opacity - FEOS程序说明.pdf] 第 32 页

> Tmax = 1.000000e+005 [1.000000e+000 eV] 
>     Pmax = 1.000000e+008 [1.000000e+012 dyne/cm^2] 
>   Start point: 
>     Rho0 = 2.700000e+000 [1.000000e+000 g/cm^3] 
>     T0 = 2.585257e-002 [1.000000e+000 eV] 
>     P0 = 2.578641e-004 [1.000000e+012 dyne/cm^2] 
>     E0 = 1.041546e+005 [1.000000e+000 erg/g] 
>   Processing Hugoniot... done. 
>   Wrote Hugoniot to file Al.hug. 
> Done. 
> 
> Free all memory... done. 
> CPU runtime: 0.55 seconds 
> 
> 4.1.8.1 Al.hug 
> 
> 每行 6 列数据 
> #  Rho  [1.000000e+000  g/cm^3]    T  [1.000000e+000  eV]    P  [1.000000e+012  dyne/cm^2]    E 
> 
> [1.000000e+000 erg/g]    Us [1.000000e+005 cm/s]    Up [1.000000e+005 cm/s] 
> 
> 2.585257e-002 
> 
> 2.578641e-004 
> 
> 1.041546e+005 
> 
> 0.000000e+000   
> 
>   9.502479e+004 
> 
>   5.122256e+005 
> 
>   7.117183e+016 
> 
>   5.028384e+003   
> 
> 2.700000e+000 
> 0.000000e+000   
> 
> …… 
> 1.081340e+001 
> 
> 3.772846e+003 
> 
> # eof. 
> 
> 4.1.9   Showeos Al 6    <rho(Rho_unit)> <T(T_unit)> for a single 
> 
> point info 
> 
> F:\Programming\FEOS\FEOS\Release>ShowEOS.exe Al 6 10 10 
> 
> Single point info: 
>   Rho = 1.000000e+001 [1.000000e+000 g/cm^3] 
>   T = 1.000000e+001 [1.000000e+000 eV] 
>   P = +2.743131e+001 [1.000000e+012 dyne/cm^2] 
>   E = +2.562623e+012 [1.000000e+000 erg/g] 
>   F = -4.964499e+012 [1.000000e+000 erg/g] 
>   S = +7.527121e+011 [1.000000e+000 erg/(g*eV)] 
>   Q[1] = 4.1364e+000 for element Z[1] = 13.00 
> 
> Free all memory... done.

### [Multi1D++ EOS and Opacity - FEOS程序说明.pdf] 第 33 页

> CPU runtime: 0.19 seconds 
> 
> 4.2  配置文件的修改（与 MPQeos 的对比） 
> 
> General 
> File-Format 
> EOS-Type 
> Units 
> Rho_unit 
> T_unit 
> P_unit 
> E_unit 
> U_unit 
> 
> Rho-T-Mesh 
> Tmin 
> Tmax 
> Tfirst 
> Toriginal 
> Tnumber 
> Tlog 
> Rhomin 
> Rhomax 
> Rhofirst 
> Rhooriginal 
> Rhonumber 
> Rholog 
> 
> Isocurves 
> Xquantity 
> Xelement 
> Yquantity 
> Yelement 
> 
> Mountain 
> Xquantity 
> Xquantity 
> Quantity 
> Element 
> 
> Hugoniot

### [Multi1D++ EOS and Opacity - FEOS程序说明.pdf] 第 34 页

> Rho0 
> T0 
> Pmax 
> Xquantity 
> 
> 5  GUI4Multi1D 中 FEOS 的界面使用 
> 
> 5.1  界面切换 
> 
> 在 GUI4Multi1D.exe 的左上角下拉选单中选择 FEOS，程序即切换到 FEOS 的图形界面。 
> 
> 界面上 Computation  Settings 标签页的材料参数必须从数据库中选取，需要修改必须从数据
> 库中修改或者添加新材料。 
> 相关参数说明请搜索本文即相关参考文献。 
> 
> 5.2  材料数据 
> 
> FEOS 的材料参数通过点击 FEOS Material DB 按钮选择。其中整理了部分文献中的参数，主要
> 是 EOS 计算中需要使用的材料的 Bulk Modulus 的数值。 
> 选择目标材料，然后点击 OK.

### [Multi1D++ EOS and Opacity - FEOS程序说明.pdf] 第 35 页

> 5.3  温度密度网格 
> 
> Q-table(density-temperature grid)标签页用于编写计算所需的温度密度数据节点。 
> FEOS 采用定义一个归一化的温度、密度，基于此值进行扩展的方法构建温度密度网格。 
> 填写 Rhonorm 和 Tnorm 之后，根据 Ratios  for  grids  definition 表格中定义的比值，分配温度
> 密度节点及其疏密情况。详见界面 Help 的相关说明。 
> 注意：归一化温度密度值不能太离谱（比如温度 1000eV 太高了），否则程序报错无法继续
> 计算。请酌情填写必要的温度密度值及其温度密度的比值。 
> 
> 5.4  计算 
> 
> 填写完前两个标签页的内容，即可点击运行按钮生成想要的数据了。 
> 如果配置文件还未保存，则需要保存*.PAR，以备后续使用或者查看。 
> 图形界面将调用 FEOS.exe 生成若干输出文件，详见 3.5 节的介绍。 
> 在 Multi1D++中使用输出文件，请见 3.6 节的说明。 
> 
> 5.5  查看 EOS 计算结果 
> 
> Showeos Parameters 用于查看生成的 EOS 数据。详见第 4 章的说明。 
> 
> 6  状态方程的计算 
> 
> 6.1  MPQeos 简介 
> 
> 输入：标准条件下的温度 T0、密度 rho0 和该温度密度下的 bulk modulus K0

### [Multi1D++ EOS and Opacity - FEOS程序说明.pdf] 第 36 页

> 6.2  EOS 的计算方法 
> 
> 6.3  Bulk-Modulus 
> 
> FEOS 计算 EOS 的时候，除了材料的组分之外，还需要提供参考温度和密度，以及对应的体
> 积模量。参考温度通常选择压力为 0 的点，此时材料为固态(p, T) = (0, T0)。 
> 体积模量的定义： 
> 
> 或者 1980 LA-8209 HYADES A subroutine package for using SESAME in hydrodynamic codes[2] 
> 
> 初始密度*bulk 声速(km/s) 
> 
> Crush 压力曲线为

### [Multi1D++ EOS and Opacity - FEOS程序说明.pdf] 第 37 页

> A3 为调节量，默认为 0 
> 
> 用户给定 Bulk modulus 之后，可以用于确定冷能计算时的系数。见 PIF, p343 中，QEOS 模型
> 
> 修正自由能Fb(ρ) = E0*1 − exp⁡(b [1 − (
> 
> ρ
> ρ0
> 
> )
> 
> 3])+，其中的系数 E0 和 b 通过使在密度为 rho0 和
> 
> 1
> 
> 温度为 0 时总压为 0.以及实验测量的B = ρ (
> 
> ∂P
> 
> ∂ρ
> 
> )
> 
> ρ0
> 
> 与计算值吻合。 
> 
> 6.3.1 FEOS 程序中使用实验测量的模量来标定 EOS。 
> 
> 6.4  Soft-Sphere function 
> 
> 1995JAP(D.A. Young)_A new global EOS model for hot, dense matter 
> Young 和 Corey 对原有的基于 TF 的 QEOS 进行了改进：包括固固相变，任意 Gruneisen gamma
> 函数输入，临界点和液汽区域的 soft-sphere 模型；双原子分子 dissociation 等 
> Soft-sphere function: 
> 
> 6.5  理想气体状态方程 
> 
> 自由能 
> 
> 6.6  简并(Thomas-Fermi) 
> 
> 区域 2：离子的理想气体自由能为

### [Multi1D++ EOS and Opacity - FEOS程序说明.pdf] 第 38 页

> 6.7  Saha EOS 
> 
> 区域 3：理想气体萨哈方程 
> 
> 6.8  WDM 
> 
> 区域 4 为温稠密等离子体，涉及相变、分解和高价态的电离等，为最复杂区域。 
> 
> 6.9  QEOS 
> 
> QEOS 的基本思路为： 
> 电子的离化平衡 EOS 根据费因曼 Feynman 的 Thomas-Fermi 模型计算，并使用 Barnes 的半经
> 验的约束修正（semiempirical bonding correction）。 
> 离子的状态方程则结合了 Debye, Grueneisen, Lindemann 和 fluid scaling-law theories   
> 相关参考文献： 
> [2]    R.M. More, K.H. Warren, D.A. Young, G.B. Zimmerman, Phys. Fluids 31 (1988) 
> 3059. 
> [3]    R.P. Feynman, N. Metropolis, E. Teller, Physiol. Rev. 75 (1949) 1561. 
> [4]    J.F. Barnes, Physiol. Rev. 153 (1967) 269. 
> Pressure  ionization:  [5]    G.B.  Zimmerman,  R.M.  More,  J.  Quant.  Spectrosc.  Radiat.  Transf.  23 
> (1980) 517. 
> Transport coefficients: [6]    Y.T. Lee, R.M. More, Phys. Fluids 27 (1984) 1273. 
> l-splitting,  photoabsorption  coefficients[7]    G.  Faussurier,  C.  Blancard,  A.  Decoster,  J.  Quant. 
> Spectrosc. Radiat. Transf. 58, (1997) 233. 
> photoabsorption coefficients [8]    G. Faussurier, C. Blancard, A. Decoster, Phys. Rev. E 56 (1997) 
> 3488. 
> photoabsorption  coefficients  [9]    G.  Faussurier,  C.  Blancard,  A.  Decoster,  J.  Quant.  Spectrosc. 
> Radiat. Transf. 58 
> (1997) 571. 
> 
> 6.10  Maxwell-Construction 
> 
> 在计算液体蒸汽两相区域，完整的平衡 EOS 使用迭代 Maxwell construction 方法。 
> Within  the  double-valued  liquid–vapor  two-phase  region,  different  EOS  are  generated  for  the 
> MetaStable  (MS)  state  with  van-der-Waals  loops  (the  MS-EOS)  and  the  fully  EQuilibrium  (EQ) 
> state (the EQ-EOS) obtained by a Maxwell construction.

### [Multi1D++ EOS and Opacity - FEOS程序说明.pdf] 第 39 页

> 6.11  MPQeos 的提高 MPQeos-JWGU 
> 
> 6.11.1 混合物的 EOS 计算 
> 
> 调整分密度使得压力平衡 
> 
> 其他参数据此计算出平均值 
> 自由能加权权重为

### [Multi1D++ EOS and Opacity - FEOS程序说明.pdf] 第 40 页

> 7  程序代码 
> 
> 7.1  COMMON 
> 
> 7.1.1 COMMON-00_DEFINITS.h 
> 
> 7.1.1.1 简介 
> 
> 常数的定义和几个结构的定义。 
> 
> 7.1.1.2 Qtable 
> 
> 保存 FEOS 的所有数据。 
> 
> 7.1.2 COMMON-01_UTILITIES.H 
> 
> 7.1.3 COMMON-02_READFILE.H 
> 
> 7.2  FEOS 
> 
> 7.2.1 FE-00_DEFINITS.H 
> 
> 7.2.2 FE-01_TABTOOLS.H 
> 
> 7.2.3 FE-02_CALCULATIONS.H 
> 
> 7.2.4 FE-03_MAIN.Cpp

### [Multi1D++ EOS and Opacity - FEOS程序说明.pdf] 第 41 页

> 7.3  LIB 
> 
> 7.3.1 LIB-00_DEFINITS.H 
> 
> 7.3.2 LIB-01_TF_SERVICES.H 
> 
> 7.3.3 LIB-02_TF_TABLE.H 
> 
> 7.3.4 LIB-03_TF_MIXTURE.H 
> 
> 7.3.5 LIB-04_IONMOD.H 
> 
> 7.3.6 LIB-05_EOS_SERVICES.H 
> 
> 7.3.7 LIB-06_MAXWELL.H 
> 
> 7.4  ShowEOS 
> 
> 7.4.1 SE-00_DEFINITS 
> 
> 7.4.2 SE-01_READTABLE 
> 
> 7.4.3 SE-02_INTERPOLTOOLS 
> 
> 7.4.4 SE-03_SERVICES 
> 
> 7.4.4.1 Hugoniot 的计算 
> 
> 初始状态(R, T, P) = (R0, T0, P0) 
> 得到 P(R,T),E(R,T) 
> 
> f =
> 
> 𝜌0(𝑃 + 𝑃0)
> 𝑃 + 𝑃0 − 2𝜌0(𝑒 − 𝑒0)
> 
> − ρ

### [Multi1D++ EOS and Opacity - FEOS程序说明.pdf] 第 42 页

> dx = 0.1*f 
> 密度步长 R=R+dx 
> 反复查找直到 dx < 1e-4  或者  f/R0 < 1e-6 
> 计算新的密度下的 P/E/Us/Up 
> 其中 
> 
> Us =
> 
> 1
> R0 √
> 
> P − P0
> 1
> 1
> R
> R0
> 
> −
> 
> Up = |1 −
> 
> R0
> R
> 
> | Us 
> 
> 温度和密度都变大 T*1.005, R*1.005；回头循环计算 
> 
> 7.4.5 SE-04_MAIN.Cpp 
> 
> 7.4.6 Multi1D++使用版本的修改 
> 
> 记录在 Changes.log 中 
> 
> 8  参考文献 
> 
> R. More, K. Warren, D. Young und G. Zimmerman; A new quotidian equation of state (QEOS) for 
> hot dense matter; Phys. Fluids 31 (1988) 3059; 5, 10, 15 
> 
> A. Kemp,    J. Meyer-ter-Vehn;    Das Zustandsgleichungs-Modell QEOS f¨ur heisse, dichte Materie; 
> Max-Planck-Institute for Quantum Optics, Report MPQ 229 (1998); 5, 10, 13, 21 
> 
> Physics  of  Extreme  States  of  Matter—2011  /  Eds.  Fortov  V.  E.  et  al.  Chernogolovka:  IPCP  RAS, 
> 2011. P. 105–108 LIFETIME OF METASTABLE STATES IN ION-BEAM IRRADIATED SiO 2 FOILS Faik S. 
> ∗1  ,  Tauschwitz  An.  2,  Maruhn  J.1,  Iosilevskiy  I.L.  3  1  UFTP,  Frankfurt  am  Main,  2  GSI,  EMMI, 
> Darmstadt, Germany, 3 JIHT RAS, Moscow, Russia *faik@th.physik.uni-frankfurt.de 
> MPQEOS 的改进 JWGU:  MPQeos-JWGU  A  new  equation-of-state  code  for  hot  dense  matter, 
> Short documentation Version: 2.2 (November 2010) 
> Steffen  Faik,  Institute  for  Theoretical  Physics,  Goethe  University  Frankfurt  am  Main,  Germany 
> MPQeos Version 2.0 (09/99): 
> A.J. Kemp and J. Meyer-ter-Vehn, Max-Planck Institute for Quantum Optics, Garching, Germany

### [Multi1D++ EOS and Opacity - FEOS程序说明.pdf] 第 43 页

> [1] R.M. More, K.H. Warren, D.A. Young, G.B. Zimmerman, A new quotidian equation of state (QEOS) 
> 
> for hot dense matter, Physics of Fluids, 31 (1988) 3059-3078. 
> 
> [2] J. J. Abdallah, G.I. Kerley, B.I. Bennett, J.D. Johnson, R.C. Albers, W.F. Huebner, HYADES:A subroutine 
> 
> package for using SESAME in hydrodynamic codes,  in, Los  Alamos Scientific Laboratory, Los Alamos, 
> 
> New Mexico 87545, 1980, pp. 29.

---

## 提取统计

- 成功：14
- 失败：0
