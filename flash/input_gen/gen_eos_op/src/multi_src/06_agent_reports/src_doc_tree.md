# Multi1D++Portable20241128 目录树与 README 清单

## 提取方法与局限

- 工具：Python 3 `os.walk` + `os.path.getsize`（UTF-8 / LF 写出）。
- 本机 bash shim 缺 coreutils，未使用任何 shell 文件工具。
- 两级目录树：列出 `src/Multi1D++Portable20241128/` 下深度 <= 2 的所有目录，
  每目录给出「直接文件数 / 直接字节数 / 递归总文件数 / 递归总字节数」。
- 文件计数含所有类型（含二进制、数据文件），不是只算文档。

---

## 两级目录树

| 目录（相对根） | 直接文件数 | 直接字节 | 递归总文件数 | 递归总字节 |
|---|---:|---:|---:|---:|
| `(根目录)` | 38 | 38861930 | 2211 | 1266594239 |
| `cases_1988CPC` | 7 | 20435 | 7 | 20435 |
| `cases_Experiments` | 2 | 9054 | 2 | 9054 |
| `cases_HotElectrons` | 2 | 14500 | 2 | 14500 |
| `cases_M1_78` | 4 | 10187 | 4 | 10187 |
| `cases_multi-ife` | 11 | 70416 | 11 | 70416 |
| `cases_multifs` | 15 | 53455 | 15 | 53455 |
| `cases_RadiativeShock` | 3 | 26216 | 3 | 26216 |
| `cases_simple` | 48 | 143965 | 48 | 143965 |
| `cases_ZhangLu` | 36 | 431061444 | 36 | 431061444 |
| `doc` | 14 | 11885354 | 58 | 32385039 |
| `doc/Conservation` | 0 | 0 | 0 | 0 |
| `doc/FEOS` | 7 | 5277706 | 7 | 5277706 |
| `doc/gnuplot_files_for_plot` | 23 | 6406238 | 23 | 6406238 |
| `doc/multi1d7.6` | 4 | 34878 | 4 | 34878 |
| `doc/References` | 6 | 8697036 | 6 | 8697036 |
| `doc/solution of unsymmetry` | 4 | 83827 | 4 | 83827 |
| `matlab` | 175 | 13281763 | 197 | 14622042 |
| `matlab/Backlighter` | 3 | 16209 | 3 | 16209 |
| `matlab/Optimization` | 2 | 0 | 2 | 0 |
| `matlab/PostProcess` | 6 | 129628 | 7 | 129667 |
| `matlab/RadiationSource` | 10 | 1194403 | 10 | 1194403 |
| `matter++` | 11 | 167756 | 1214 | 729653606 |
| `matter++/ANEOS` | 0 | 0 | 0 | 0 |
| `matter++/ATOMIC` | 69 | 276117373 | 69 | 276117373 |
| `matter++/CH` | 19 | 13453140 | 19 | 13453140 |
| `matter++/CHBr3at%` | 2 | 1176200 | 2 | 1176200 |
| `matter++/ColdOpacity` | 71 | 7762868 | 71 | 7762868 |
| `matter++/Crystal` | 3 | 1183 | 3 | 1183 |
| `matter++/Diamond` | 0 | 0 | 0 | 0 |
| `matter++/FEOS` | 2 | 599833 | 2 | 599833 |
| `matter++/HeatCapacity` | 3 | 13134 | 5 | 25905 |
| `matter++/hyades` | 11 | 247811 | 158 | 10850675 |
| `matter++/Ionmix` | 17 | 7124596 | 17 | 7124596 |
| `matter++/Isotopes` | 0 | 0 | 0 | 0 |
| `matter++/mat_Ac` | 0 | 0 | 0 | 0 |
| `matter++/mat_Ag-Thermos` | 0 | 0 | 0 | 0 |
| `matter++/mat_Al-1.0` | 35 | 9837986 | 39 | 13360379 |
| `matter++/mat_Ar` | 0 | 0 | 0 | 0 |
| `matter++/mat_Ar-Thermos` | 0 | 0 | 0 | 0 |
| `matter++/mat_Au` | 4 | 6974 | 4 | 6974 |
| `matter++/mat_Au-1.0` | 27 | 9083292 | 27 | 9083292 |
| `matter++/mat_B` | 11 | 9718166 | 11 | 9718166 |
| `matter++/mat_Ba` | 17 | 9619158 | 17 | 9619158 |
| `matter++/mat_Be-1.0` | 23 | 2392469 | 23 | 2392469 |
| `matter++/mat_Bi` | 9 | 9610620 | 9 | 9610620 |
| `matter++/mat_Br-Thermos` | 0 | 0 | 0 | 0 |
| `matter++/mat_C-1.0` | 43 | 19177615 | 43 | 19177615 |
| `matter++/mat_Ca-Thermos` | 0 | 0 | 0 | 0 |
| `matter++/mat_Cd` | 0 | 0 | 0 | 0 |
| `matter++/mat_Ce` | 16 | 9660233 | 16 | 9660233 |
| `matter++/mat_CELIA` | 39 | 3760381 | 39 | 3760381 |
| `matter++/mat_CH2` | 3 | 2060874 | 3 | 2060874 |
| `matter++/mat_CHBr` | 2 | 1176200 | 4 | 2352400 |
| `matter++/mat_Cl` | 9 | 9618162 | 9 | 9618162 |
| `matter++/mat_Co` | 11 | 9707847 | 11 | 9707847 |
| `matter++/mat_CPC` | 8 | 761803 | 8 | 761803 |
| `matter++/mat_Cr` | 11 | 9714136 | 11 | 9714136 |
| `matter++/mat_Cu` | 0 | 0 | 0 | 0 |
| `matter++/mat_Cu-Thermos` | 0 | 0 | 0 | 0 |
| `matter++/mat_DT-1.0` | 13 | 532125 | 13 | 532125 |
| `matter++/mat_Dy` | 11 | 9707845 | 11 | 9707845 |
| `matter++/mat_Er` | 0 | 0 | 0 | 0 |
| `matter++/mat_Eu` | 4 | 559 | 4 | 559 |
| `matter++/mat_F` | 8 | 9612202 | 8 | 9612202 |
| `matter++/mat_Fe` | 0 | 0 | 0 | 0 |
| `matter++/mat_Fe-` | 0 | 0 | 0 | 0 |
| `matter++/mat_Fr` | 0 | 0 | 0 | 0 |
| `matter++/mat_Ga` | 0 | 0 | 0 | 0 |
| `matter++/mat_Gd` | 12 | 15687797 | 12 | 15687797 |
| `matter++/mat_Ge` | 8 | 2041 | 8 | 2041 |
| `matter++/mat_H` | 0 | 0 | 0 | 0 |
| `matter++/mat_H-Thermos` | 0 | 0 | 0 | 0 |
| `matter++/mat_He` | 9 | 3266503 | 9 | 3266503 |
| `matter++/mat_Hf` | 0 | 0 | 0 | 0 |
| `matter++/mat_Hg` | 0 | 0 | 0 | 0 |
| `matter++/mat_I` | 0 | 0 | 0 | 0 |
| `matter++/mat_In` | 0 | 0 | 0 | 0 |
| `matter++/mat_Ir` | 0 | 0 | 0 | 0 |
| `matter++/mat_K` | 11 | 9622645 | 11 | 9622645 |
| `matter++/mat_Kr-Thermos` | 0 | 0 | 0 | 0 |
| `matter++/mat_La` | 0 | 0 | 0 | 0 |
| `matter++/mat_Li-Thermos` | 0 | 0 | 0 | 0 |
| `matter++/mat_Lu` | 0 | 0 | 0 | 0 |
| `matter++/mat_Mg-Thermos` | 0 | 0 | 0 | 0 |
| `matter++/mat_Mn` | 0 | 0 | 0 | 0 |
| `matter++/mat_Mo` | 0 | 0 | 0 | 0 |
| `matter++/mat_Mo-Thermos` | 0 | 0 | 0 | 0 |
| `matter++/mat_N` | 9 | 9612815 | 9 | 9612815 |
| `matter++/mat_Na` | 11 | 9712841 | 11 | 9712841 |
| `matter++/mat_Nb` | 0 | 0 | 0 | 0 |
| `matter++/mat_Nd` | 0 | 0 | 0 | 0 |
| `matter++/mat_Ne` | 9 | 9621249 | 9 | 9621249 |
| `matter++/mat_Ni-Thermos` | 0 | 0 | 0 | 0 |
| `matter++/mat_Np` | 0 | 0 | 0 | 0 |
| `matter++/mat_O` | 9 | 9607043 | 9 | 9607043 |
| `matter++/mat_Os` | 0 | 0 | 0 | 0 |
| `matter++/mat_Others` | 6 | 4491595 | 14 | 9936601 |
| `matter++/mat_P` | 14 | 11447040 | 14 | 11447040 |
| `matter++/mat_Pb` | 0 | 0 | 0 | 0 |
| `matter++/mat_Pb-Thermos` | 0 | 0 | 0 | 0 |
| `matter++/mat_Pd` | 11 | 9708878 | 11 | 9708878 |
| `matter++/mat_Pm` | 0 | 0 | 0 | 0 |
| `matter++/mat_Po` | 0 | 0 | 0 | 0 |
| `matter++/mat_Pr` | 0 | 0 | 0 | 0 |
| `matter++/mat_Pt` | 0 | 0 | 0 | 0 |
| `matter++/mat_Pu` | 0 | 0 | 0 | 0 |
| `matter++/mat_Ra` | 0 | 0 | 0 | 0 |
| `matter++/mat_Rb` | 0 | 0 | 0 | 0 |
| `matter++/mat_Re` | 0 | 0 | 0 | 0 |
| `matter++/mat_Rh` | 0 | 0 | 0 | 0 |
| `matter++/mat_Rn` | 0 | 0 | 0 | 0 |
| `matter++/mat_Ru` | 0 | 0 | 0 | 0 |
| `matter++/mat_S` | 32 | 28947941 | 32 | 28947941 |
| `matter++/mat_Sb` | 0 | 0 | 0 | 0 |
| `matter++/mat_Sc` | 22 | 19346202 | 22 | 19346202 |
| `matter++/mat_Se` | 0 | 0 | 0 | 0 |
| `matter++/mat_Si-Thermos` | 0 | 0 | 0 | 0 |
| `matter++/mat_Sm` | 11 | 9707848 | 11 | 9707848 |
| `matter++/mat_Sn` | 4 | 558 | 4 | 558 |
| `matter++/mat_Sr` | 0 | 0 | 0 | 0 |
| `matter++/mat_Ta-Thermos` | 0 | 0 | 0 | 0 |
| `matter++/mat_Tb` | 0 | 0 | 0 | 0 |
| `matter++/mat_Tc` | 0 | 0 | 0 | 0 |
| `matter++/mat_Te` | 0 | 0 | 0 | 0 |
| `matter++/mat_Th` | 0 | 0 | 0 | 0 |
| `matter++/mat_Ti` | 16 | 1640716 | 16 | 1640716 |
| `matter++/mat_Tl` | 0 | 0 | 0 | 0 |
| `matter++/mat_Tm` | 0 | 0 | 0 | 0 |
| `matter++/mat_U` | 0 | 0 | 0 | 0 |
| `matter++/mat_U-Thermos` | 0 | 0 | 0 | 0 |
| `matter++/mat_V-Thermos` | 0 | 0 | 0 | 0 |
| `matter++/mat_Vacuum` | 1 | 186 | 1 | 186 |
| `matter++/mat_W` | 0 | 0 | 0 | 0 |
| `matter++/mat_W-Thermos` | 0 | 0 | 0 | 0 |
| `matter++/mat_Xe` | 0 | 0 | 0 | 0 |
| `matter++/mat_Xe-Thermos` | 0 | 0 | 0 | 0 |
| `matter++/mat_Y` | 0 | 0 | 0 | 0 |
| `matter++/mat_Yb` | 0 | 0 | 0 | 0 |
| `matter++/mat_Zn-Thermos` | 0 | 0 | 0 | 0 |
| `matter++/mat_Zr` | 0 | 0 | 0 | 0 |
| `matter++/others` | 0 | 0 | 0 | 0 |
| `matter++/PeriodicTable` | 0 | 0 | 0 | 0 |
| `matter++/PowerLaws` | 5 | 45079 | 5 | 45079 |
| `matter++/PROPACEOS` | 1 | 120 | 1 | 120 |
| `matter++/RadiativeCoolingRates` | 5 | 154986 | 5 | 154986 |
| `matter++/Reactivity` | 0 | 0 | 0 | 0 |
| `matter++/SiO2` | 9 | 27378950 | 9 | 27378950 |
| `matter++/SNOP` | 10 | 838189 | 10 | 838189 |
| `matter++/Ta2O5` | 45 | 16573847 | 45 | 16573847 |
| `matter++/Thermos` | 1 | 576 | 228 | 68750932 |
| `matter++/XrayMassCoef` | 2 | 9948 | 41 | 305830 |
| `Microsoft.VC90.CRT` | 4 | 1449996 | 4 | 1449996 |
| `Microsoft.VC90.MFC` | 5 | 2439700 | 5 | 2439700 |
| `tabelle` | 3 | 567699 | 3 | 567699 |
| `templates` | 2 | 13208 | 183 | 2092091 |
| `templates/color` | 165 | 2061492 | 165 | 2061492 |
| `templates/data` | 16 | 17391 | 16 | 17391 |
| `templates/profiles` | 0 | 0 | 0 | 0 |
| `tools` | 0 | 0 | 381 | 13112464 |
| `tools/npp` | 15 | 2556683 | 381 | 13112464 |

## 根目录文件清单（含字节数）

| 文件 | 字节 |
|---|---:|
| `Changes.log` | 69807 |
| `FEOS.exe` | 111616 |
| `FEOS_Material-DB.dat` | 114029 |
| `FEOS_TF-Table_1197.dat` | 567342 |
| `Flux0.dat` | 4355 |
| `Flux3ns.dat` | 1992 |
| `GUI4Multi1D.exe` | 18002944 |
| `Ioniz.exe` | 393216 |
| `MG.opj` | 852312 |
| `MULTIfs.exe` | 310784 |
| `Multi1D++.exe` | 7439872 |
| `Multi1D.exe` | 145920 |
| `Shot20120821015.Spline3OrderIterative.Flux0.dat` | 4044 |
| `Shot20120821015.Spline3OrderIterative.Flux3ns.dat` | 4042 |
| `Shot20120821015.Spline3OrderIterative.TotalRadiation2DVertical0.dat` | 659996 |
| `Shot20120821015.Spline3OrderIterative.TotalRadiation2DVertical0.opj` | 864041 |
| `ShowEOS.exe` | 46592 |
| `Snop++.exe` | 1320960 |
| `TotalRadiation2D0Vertical.dat` | 295923 |
| `Untitled.case` | 6923 |
| `Untitled.case.log` | 1983 |
| `ZedGraph.dll` | 299008 |
| `default.ini` | 442 |
| `gnuplot.exe` | 1982976 |
| `gsl.dll` | 1441792 |
| `gslcblas.dll` | 389120 |
| `mpqeos.exe` | 143360 |
| `msvcr71.dll` | 348160 |
| `multi7.exe` | 145408 |
| `settings.ini` | 27 |
| `snop.exe` | 380928 |
| `wgnuplot.GID` | 70152 |
| `wgnuplot.exe` | 1977856 |
| `wgnuplot.hlp` | 434726 |
| `wgnuplot.mnu` | 14858 |
| `~temp.dat` | 13921 |
| `~tmp.animate` | 286 |
| `~tmp.gplt` | 217 |

## 全部 README / Readme / readme / Info / License 文件（全库扫描）

| 相对路径 | 字节 |
|---|---:|
| `matlab/Backlighter/Readme.txt` | 34 |
| `matlab/PostProcess/CrystalSpectrometer/Readme.txt` | 39 |
| `matter++/mat_Au/Au_Rosseland_2003POPHammerRosen.readme` | 90 |
| `matter++/HeatCapacity/Readme.txt` | 91 |
| `matter++/mat_CELIA/Readme.txt` | 92 |
| `matter++/mat_Sn/Sn_Rosseland_1987JQSRT.readme` | 92 |
| `matter++/mat_Eu/Eu_Rosseland_1987JQSRT.readme` | 93 |
| `matter++/mat_Ge/Ge_Rosseland_1999Minguez.readme` | 93 |
| `matter++/mat_Ba/Ba_Planck_1987JQSRT.readme` | 94 |
| `matter++/mat_Ba/Ba_Rosseland_1987JQSRT.readme` | 94 |
| `matter++/mat_Eu/Eu_Planck_1987JQSRT.readme` | 94 |
| `matter++/mat_Ge/Ge_Planck_1999Minguez.readme` | 94 |
| `matter++/mat_Sn/Sn_Planck_1987JQSRT.readme` | 94 |
| `matter++/PROPACEOS/Readme.txt` | 120 |
| `matter++/mat_Ti/readme.txt` | 133 |
| `templates/data/readme.txt` | 180 |
| `matter++/mat_CELIA/C.ZEFF.readme` | 223 |
| `templates/color/readme.txt` | 305 |
| `matter++/Ta2O5/Ta2O5_mop.readme` | 343 |
| `tabelle/readme.txt` | 357 |
| `matter++/mat_Ba/Readme.txt` | 403 |
| `matter++/RadiativeCoolingRates/readme.txt` | 429 |
| `matter++/mat_Be-1.0/README` | 510 |
| `tools/npp/plugins/doc/SelectNLaunch/readme.txt` | 524 |
| `matter++/Readme.txt` | 530 |
| `matter++/Thermos/Readme.txt` | 576 |
| `matter++/mat_Al-1.0/README` | 617 |
| `matter++/mat_C-1.0/README` | 654 |
| `matter++/mat_DT-1.0/README` | 715 |
| `matter++/mat_Ge/Readme.txt` | 939 |
| `matter++/mat_Au-1.0/README` | 1221 |
| `tools/npp/readme.txt` | 1543 |
| `doc/FEOS/Info.txt` | 2475 |
| `tools/npp/plugins/doc/ZenCodingPython/readme.txt` | 2798 |
| `tools/npp/plugins/doc/NppFTP/Readme.txt` | 5231 |
| `doc/multi1d7.6/README` | 5619 |
| `tools/npp/license.txt` | 14971 |
| `tools/npp/plugins/doc/SelectNLaunch/license.txt` | 14971 |
| `doc/FEOS/License.txt` | 28360 |

命中数：39
