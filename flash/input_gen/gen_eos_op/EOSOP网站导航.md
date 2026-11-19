各种元素信息链接：[元素周期表](https://ptable.com/?lang=zh-hans#%E6%80%A7%E8%B4%A8)



| 表号 | 表名 | 覆盖内容 | 在材料数据链中的位置 | 主要回答的问题 |
| --- | --- | --- | --- | --- |
| T0 | 文档总索引 | 含 T0 索引共 13 张表，全部为表格，无正文段落 | 入口 | 等离子体辐射流体仿真需要哪些 EOS、不透明度、原子数据、格式工具、宿主代码与验证基准 |
| T1 | 核心状态方程库与模型 | SESAME、LEOS/Lynx/Purgatorio、QEOS、ANEOS/M-ANEOS、THERMOS EOS 侧 | 热力学闭合 | 压力、内能、自由能、电离度由哪张表给出 |
| T2 | 不透明度库与代码 | THERMOS、SESAME 附库、OPLIB/TOPS、OPAL、OP、OPAS/SCO-RCG、CASSANDRA | 辐射输运闭合 | Rosseland / Planck / 多群 / 单色吸收系数从哪来 |
| T3 | 一体化生成器与原子物理套件 | PrOpacEOS、ATBASE、LANL 全套代码、TOPS/GANDOLF/IPCRESS、ChemEOS、FAC/HULLAC | 自洽产表 | 如何由同一套原子模型同时产出 EOS 与不透明度 |
| T4 | NLTE 与精细谱模型 | CRETIN、FLYCHK、表格化 NLTE、DCA/UTA/STA、PrismSPECT、SPECT3D | 冕区与高 Z 修正 | LTE 表失效时用什么补发射率、吸收系数与电离态 |
| T5 | 输运系数与补充数据源 | 电导/热导、Lee–More、QMD、REFPROP/CoolProp、冲击 Hugoniot 库 | 三温与初始态 | 电子热导、冷曲线、温稠密区与实验标定数据 |
| T6 | 表号、格式与转换工具 | SESAME 300 系列、EOSPAC、IONMIX、IPCRESS、opacplot2、Spiner/HDF5 | 数据工程层 | 表怎么读、怎么转、怎么插值、单位和网格怎么核对 |
| T7 | 宿主辐射流体代码 | HYDRA、xRAGE、LASNEX、HELIOS、MULTI、FLASH、Jayenne/CRASH、LARED | 消费端 | 各代码实际吃什么表、用什么混合闭包 |
| T8 | 验证基准与实验数据 | NLTE-10、RPHDM、Sandia Z、神光-III、LASL/IHED/Van Thiel | V&V | 上线前拿什么算例和实验验表 |
| T9 | 配套原子分子光谱数据库 | TOPbase、TIPbase、OPserver、Spectr-W3、NIST ASD、CHIANTI、VAMDC、ExoMol、HITRAN、MAESTRO | 原子数据底座 | 能级、振子强度、光电离截面、谱线参数 |
| T10 | 国内资源与文献入口 | CAEP、LARED、MRE、强激光与粒子束、神光-III、国内 QMD 数据 | 中文一手资料 | 国内 EOS/不透明度数据与程序进展去哪查 |
| T11 | 获取门槛与许可 | 申请表、商业授权、出口管制、注册制、在线直取 | 合规层 | 哪些能直接下载，哪些要申请、合作或邮件索取 |
| T12 | 按仿真对象的推荐组合 | 黑腔、靶丸、冕区、Z-pinch、温稠密、高 Z 混合、冲击、天体对照 | 选型速查 | 具体算例该拼哪一套 EOS + 不透明度 + 热导 + NLTE |

| 表号 | 名称 | 机构 / 来源 | 数据形态与范围 | 在 RHD 中的作用 | 官网 / 数据入口 | 获取方式 |
| --- | --- | --- | --- | --- | --- | --- |
| T1 | SESAME | LANL | 约 150 种材料表格化 EOS；P、E、A 随 ρ、T；典型 10⁻⁶–10⁴ g/cm³、0–10⁵ eV；含熔化、汽化、剪切表 | 主 EOS 表；多材料单元压力-温度平衡查表基础 | https://www.lanl.gov/engage/organizations/aldsct/theoretical/pcm<br>https://cdn.lanl.gov/files/laur-92-3407_a0e99.pdf<br>https://www.osti.gov/biblio/2570872 | 提交申请表，公开资料标注为受地域限制的许可数据 |
| T1 | SESAME 历史与附库说明 | LANL / OSTI | 1972 年起公开；库内另含不透明度与电导率表；早期报告给出表结构 | 确认附库边界与表号语义 | https://www.osti.gov/biblio/6349782 | 报告全文公开 |
| T1 | LEOS / Lynx + Purgatorio | LLNL | 基于 QEOS 方法建表；Lynx 用相对论平均原子 DFT 的 Purgatorio 计算电子热贡献；表库本身不在线公开分发 | HYDRA 黑腔与靶丸计算的标准 EOS | https://www.osti.gov/servlets/purl/900053<br>https://searchworks-lb.stanford.edu/view/12053805 | 合作 / 许可；表本身需通过机构获取 |
| T1 | QEOS | LLNL，More / Warren / Young / Zimmerman 1988 | 解析通用 EOS：修正 Thomas–Fermi 电子项 + Debye / Grüneisen / Lindemann 离子项 + 成键修正；给 P、E、S、F、电离态 | 无表时快速建 EOS；LEOS 的方法学母体 | https://doi.org/10.1063/1.866963<br>https://www.osti.gov/biblio/7062364<br>https://www.sciencedirect.com/science/article/abs/pii/S016890029800446X | 论文与公开代码实现可查 |
| T1 | ANEOS | Sandia | 解析型冲击物理 EOS，Helmholtz 自由能分冷项、离子热项、电子项；固 / 液 / 气 / 等离子体与相混合热力学自洽 | 冲击、烧蚀层、多相材料 | https://www.sandia.gov/research/publications/details/aneos-analytic-equations-of-state-for-shock-physics-codes-input-manual-1990-03-01/ | 手册公开 |
| T1 | M-ANEOS | Melosh / Collins / Stewart 等 | ANEOS 改进版：分子团簇气相、Mie 势膨胀固态、可同时处理固-固与熔融相变、可调 Debye 模型 | 地质材料、含水 / 硅酸盐靶、撞击与烧蚀 EOS | https://doi.org/10.5281/zenodo.3525030<br>https://sarahtstewart.net/community-tools/ | Zenodo 归档与社区工具页 |
| T1 | THERMOS（EOS 侧） | KIAM RAS | Thomas–Fermi / Hartree–Fock–Slater 平均原子；输出压力、比内能、熵、化学势、平均电荷、离子组份 | 与同一模型的不透明度自洽配套，支持任意混合物 | https://www.keldysh.ru/thermos/en<br>https://www.sciencedirect.com/science/article/pii/S1574181819300552 | 官网为描述页，无公开直接下载入口 |
| T1 | ChemEOS | LANL | 自由能最小化给离子布居与态溶解；OPLIB 不透明度表的底层 EOS | 保证 OPLIB 的 EOS 与不透明度同源 | http://aphysics2.lanl.gov/opacity/lanl<br>https://arxiv.org/pdf/1601.01005 | 随 OPLIB 在线服务使用 |

| 表号 | 名称 | 机构 / 来源 | 输出量 / 网格 | 适用区 | 官网 / 数据入口 | 获取方式 |
| --- | --- | --- | --- | --- | --- | --- |
| T2 | THERMOS（不透明度侧） | KIAM RAS | 光谱吸收与发射系数、Planck / Rosseland 平均吸收系数、电子热导、谱线位置 / 强度 / 宽度；Rosseland 区间 0.1T < hω < 20T | LTE 与 NLTE、任意辐射场、任意混合物 | https://www.keldysh.ru/thermos/en | 工具包 / 数据库，需联系机构 |
| T2 | SESAME 不透明度附库 | LANL | Rosseland 与 Planck 平均不透明度、电子传导不透明度、平均离子电荷；Z≤30；温度下限约 1 eV | 与 SESAME EOS 同库同表号体系 | https://cdn.lanl.gov/files/laur-92-3407_a0e99.pdf<br>https://www.osti.gov/biblio/6349782 | 随 SESAME 申请 |
| T2 | SESAME 电导率附库 | LANL | 平均离子电荷、电导率、热导率、热电系数、电子传导不透明度；Z=1–96 | 三温模型电子热导与传导不透明度 | https://cdn.lanl.gov/files/laur-92-3407_a0e99.pdf | 随 SESAME 申请 |
| T2 | OPLIB / TOPS（ATOMIC、LEDCOP） | LANL T-1 / XCP-5 | 前 30 号元素 LTE 单色不透明度，u=hν/kT 网格 14,900 点，u 从 1e-4 到 3e4；多群、灰体、Rosseland / Planck 平均；任意混合物 | ICF、黑腔、辐射流体主用表 | http://aphysics2.lanl.gov/opacity/lanl<br>https://aphysics2.lanl.gov/static/opacdocs/opac-help.html<br>https://arxiv.org/pdf/1601.01005 | 网页直接生成 / 下载 |
| T2 | TOPS 多群默认参数 | LANL | 默认 33 个光子边界、32 群，0.001–300 keV；单色输出 3000 或 3900 频点；可算等离子体截止频率 | 从单元素截面表合成混合物多群表 | https://aphysics2.lanl.gov/static/opacdocs/opac-help.html<br>https://physics.nist.gov/Icamdata/PDF/1Databases/magee.pdf | 在线服务 |
| T2 | OPLIB 预计算天体混合物表 | LANL | 复杂天体混合物预计算 Rosseland 表 | 快速对照与低密度区参考 | https://aphysics2.lanl.gov/apps/astro_atomic.py | 在线 |
| T2 | OPAL | LLNL | 21 元素混合物单色不透明度归档在 R-T₆ 网格；Rosseland 平均表；可按组分申请新表 | 恒星包层、太阳模型；HED 中作低密度对照 | https://opalopacity.llnl.gov/opal.html | 在线取表 / 在线申请生成 |
| T2 | Opacity Project OPCD3.3 / IPOPv2 | 巴黎天文台 / CDS | 单色不透明度；IPOPv2 输出 OPAL 兼容 Type-1 表 | 低密度等离子体与天体混合物 | http://op-opacity.obspm.fr/opacity/<br>http://tiptopbase.obspm.fr/topbase | 在线计算 / 邮件返回结果 |
| T2 | OPserver | Ohio Supercomputer Center | OP 单色不透明度远程服务，本地库 / 云端 / 网页三种模式 | 不透明度在线查询 | http://opacities.osc.edu/ | 在线 |
| T2 | OPAS / SCO-RCG | CEA DAM | 详细组态、精细谱线、Stark 展宽；铁与 K 壳层谱；无公开表库 | 太阳辐射区 Fe 不透明度、ICF 高 Z 谱验证 | https://arxiv.org/pdf/1512.00603.pdf<br>https://doi.org/10.1038/s41467-024-54793-y | 数据需向作者邮件申请 |
| T2 | CASSANDRA | AWE | 相对论 Hartree–Slater–Dirac 平均原子，同一模型给 EOS 与不透明度；自由-自由、束缚-自由、束缚-束缚、散射分解 | 稠密等离子体 / 液态金属自洽表 | https://www.sciencedirect.com/science/article/pii/S0022407301000735<br>https://www.osti.gov/pages/biblio/2350885 | 无公开在线库，论文与实验对照 |
| T2 | LEDCOP / ATMED / CORONA / OPIND / STA | 多机构 | 平均原子与屏蔽氢模型、超跃迁阵列、详细组态；快速生成宽温密区不透明度表 | 高 Z、混合物、RHD 表批量生成 | https://www.sciencedirect.com/science/article/abs/pii/S0022407320301333<br>https://worldscientific.com/worldscibooks/10.1142/1412 | 文献与代码描述，多数需合作 |

| 表号 | 名称 | 机构 | 自洽产出 | 上游原子数据 | 下游格式 / 宿主 | 官网 / 入口 |
| --- | --- | --- | --- | --- | --- | --- |
| T3 | PrOpacEOS | Prism Computational Sciences | 直接生成辐射流体代码所需的 EOS 与多群不透明度表，支持元素与混合物 | ATBASE 原子数据套件 | HELIOS、HELIOS-CR、外部 RHD 代码 | https://www.prism-cs.com/Software/overview.html |
| T3 | ATBASE / PrismSPECT / HELIOS-CR / SPECT3D / VisRad | Prism | ATBASE 给能级与跃迁；PrismSPECT 给 LTE / NLTE 发射吸收与电离分布；HELIOS-CR 内联碰撞辐射；SPECT3D 后处理出谱与图像；VisRad 给黑腔视角因子与辐射场 | ATBASE | HELIOS 表、实验诊断比对 | https://www.prism-cs.com/<br>https://www.prism-cs.com/Software/overview.html<br>https://prism-cs.com/Software/Spect3D/major_features.html |
| T3 | LANL 原子物理套件 | LANL T-1 / XCP-5 | CATS 与 RATS 算原子结构与振子强度；ACE 算扭曲波碰撞激发；GIPPER 算碰撞、光电、自电离截面；TAPS 查看数据；FINE 与 ATOMIC 建模布居与光谱；FESTR 做谱建模 | Cowan 代码、实验能级修正 | ATOMIC 数据文件 → OPLIB / SESAME / TOPS | http://aphysics2.lanl.gov/tempweb/lanl/<br>https://www.osti.gov/servlets/purl/1053576 |
| T3 | TOPS / GANDOLF / IPCRESS | LANL | TOPS 把单元素截面表合成混合物与多群平均；GANDOLF 读取 IPCRESS 格式不透明度数据 | ATOMIC / LEDCOP 截面表 | 多群表 → 辐射输运代码 | https://aphysics2.lanl.gov/static/opacdocs/opac-help.html<br>https://physics.nist.gov/Icamdata/PDF/1Databases/magee.pdf |
| T3 | ChemEOS + ATOMIC | LANL | 自由能最小化给布居，ATOMIC 给单色 / 多群 / 平均不透明度与光谱 | CATS / RATS / ACE / GIPPER | OPLIB 新表 | http://aphysics2.lanl.gov/opacity/lanl<br>https://arxiv.org/pdf/1601.01005 |
| T3 | THERMOS 工具包 | KIAM RAS | 同一平均原子模型给 EOS、光谱吸收发射、平均不透明度、电子热导、离子组份与速率 | 可接 FAC、RCG、NIST、Spectr-W3 修正 | 任意混合物表 | https://www.keldysh.ru/thermos/en |
| T3 | FAC / cFAC / HULLAC / Cowan 代码 | 多机构 | 相对论原子结构、能级、光电离与碰撞截面 | 第一性原理原子计算 | CRETIN、ATOMIC、THERMOS 的外部原子模型 | https://softwarelicensing.llnl.gov/product/cretin-software<br>https://www.keldysh.ru/thermos/en |
| T3 | CASSANDRA / OPIND / ATMED / CORONA | AWE / 多机构 | 平均原子框架下一次算出 EOS 与不透明度，避免两套模型拼表 | 屏蔽氢或 HFS 平均原子 | RHD 表生成 | https://www.sciencedirect.com/science/article/pii/S0022407301000735<br>https://www.sciencedirect.com/science/article/abs/pii/S0022407320301333 |

| 表号 | 名称 | 机构 | 模型类别 | RHD 用途 | 入口 | 许可 / 限制 |
| --- | --- | --- | --- | --- | --- | --- |
| T4 | CRETIN | LLNL | 1D / 2D / 3D NLTE 原子动力学 + 辐射输运，跟踪布居与光子分布随时间演化 | 产生详细谱；xRAGE 表格化 NLTE 表的上游模型 | https://softwarelicensing.llnl.gov/product/cretin-software | 需 LLNL 软件许可，出口管制，合格学术用户可申请 |
| T4 | FLYCHK / FLY | NIST，IAEA 镜像 | 快速 NLTE 碰撞辐射；H–Au（Z≤79）；电荷态分布、平均电离度、辐射损失、发射率、不透明度、光深 | 建表前条件扫描、实验诊断、NLTE 初值 | https://nlte.nist.gov/FLY/<br>https://nlte.nist.gov/FLY/Doc/Manual_FLYCHK_Nov08.pdf<br>https://www-amdis.iaea.org/FLYCHK/ZBAR/index.php | NIST 站点需注册；IAEA 镜像可查说明；中性近邻区结果不可靠 |
| T4 | 表格化 NLTE | LANL / LLNL | 预计算 η_g、α_g、电离度、EOS 于 (Te, ne, Tr) 表；运行时查表并对参考谱做线性修正 | 比内联 NLTE 快得多，适合黑腔整体模拟 | https://pubs.aip.org/aip/pop/article/29/8/083901/2845168/ | 依赖 CRETIN 类模型预计算 |
| T4 | HYDRA-DCA / CRETIN NLTE | LLNL | 详细组态 accounting + 时间依赖 NLTE 动力学 | 短脉冲激光铁不透明度实验设计、高 Z 发射谱 | https://pubs.aip.org/aip/pop/article-pdf/doi/10.1063/1.4976710/13592906/022705_1_online.pdf | 随 HYDRA / CRETIN 许可 |
| T4 | PrismSPECT | Prism | 碰撞辐射谱分析，按用户给定温密网格算 LTE / NLTE 发射吸收与电离性质 | 快速扫描 NLTE 条件、生成诊断谱 | https://www.prism-cs.com/Software/overview.html | 商业授权 |
| T4 | SPECT3D | Prism | 1D / 2D / 3D 后处理流体结果，算辐射通量、滤波图像、单色像、门控谱与条纹谱 | 把 RHD 输出变成可与实验直接比的量 | https://prism-cs.com/Software/Spect3D/major_features.html | 商业授权 |
| T4 | DCA / UTA / MUTA / STA 类 | 多机构 | 详细组态、未分辨跃迁阵列、混合 UTA、超跃迁阵列 | 高 Z 元素精细谱与透射谱验证 | https://www.osti.gov/servlets/purl/1053576<br>https://worldscientific.com/worldscibooks/10.1142/1412 | 计算昂贵，多用于离线建表 / 校验 |
| T4 | SCO-RCG / OPAS | CEA DAM | 详细谱线、Stark 展宽、K 壳层谱 | 铁不透明度与 Z 机透射谱对照 | https://arxiv.org/pdf/1512.00603.pdf | 数据邮件申请 |
| T4 | DEDALE / DLAYZ / SEMILLAC 等 NLTE 代码 | 多机构 | NLTE 布居动力学与辐射性质，参与历届代码比对 | 交叉验证 NLTE 模型差异 | https://www.osti.gov/biblio/1529152 | 见 NLTE 综述文献索引 |
| T4 | 电离势降低 IPD 模型 | 多机构 | Stewart–Pyatt / Ecker–Kröll 公式，稠密等离子体压低电离势 | 影响电离度、不透明度与 EOS 自洽 | https://www.sciencedirect.com/science/article/pii/S1574181819300552<br>https://nlte.nist.gov/FLY/Doc/Manual_FLYCHK_Nov08.pdf | 作为模型选项内置于 THERMOS / FLYCHK |

| 表号 | 名称 | 类型 | 关键量 | RHD 用途 | 入口 |
| --- | --- | --- | --- | --- | --- |
| T5 | SESAME 电导 / 热导附库 | 表格输运系数 | 平均离子电荷、电导率、热导率、热电系数、电子传导不透明度 | 三温方程电子热导、传导不透明度 | https://cdn.lanl.gov/files/laur-92-3407_a0e99.pdf |
| T5 | Lee–More / SpitzerHighZ / Epperlein–Haines / Ji–Held | 解析热导模型 | 电子热导系数；各向异性 K∥、K⊥、K∧ | FLASH 的 Conductivity 单元；低温简并区 Lee–More 优于 Spitzer；磁化 HEDP 用各向异性模型 | https://flash.rochester.edu/site/flashcode/user_support.html<br>https://flash.rochester.edu/site/flashcode/ |
| T5 | StellarCollapse EOS 与 NuLib | 核物质 EOS / 中微子不透明度表 | APR、SRO、O'Connor–Ott 表；中微子相互作用库 | 极高密度区 EOS 表，Singularity-EOS 可直接读 | https://stellarcollapse.org/node/5.html<br>https://stellarcollapse.org/APREOS<br>https://stellarcollapse.org/SROEOS |
| T5 | QMD / DFT-MD / PIMC 第一性原理数据 | 温稠密区计算数据 | EOS、电子热导、辐射不透明度 | 补齐 SESAME / LEOS 在温稠密与预热层的空缺 | https://militzer.berkeley.edu/<br>https://sarahtstewart.net/community-tools/ |
| T5 | NIST REFPROP / CoolProp / IAPWS-IF97 | 工程流体 EOS | 136 种流体 Helmholtz EOS、混合物、IF97 水与蒸汽 | 仅初始态、低温边界与常规工程介质，不用于 HED 主链路 | https://www.nist.gov/srd/refprop<br>https://coolprop.org/<br>https://webbook.nist.gov/chemistry/fluid/ |
| T5 | NIST Chemistry WebBook | 热化学与热物性 | 7000+ 化合物热化学数据；74 种流体密度、Cp、Cv、焓、内能、熵、黏度、热导、声速 | 初始材料参数与低温端校验 | https://webbook.nist.gov/ |
| T5 | NIST-JANAF / ENKI | 热化学表 / 热化学引擎 | 热化学函数、化学组份平衡 | 低温端与化学平衡补项 | https://janaf.nist.gov/<br>https://server.enki-portal.org/ |
| T5 | RFBR Shock Wave Database | 冲击实验 + EOS 在线库 | 冲击波实验数据与 EOS，含抽取工具 | Hugoniot、冷曲线标定 | http://www.ihed.ras.ru/<br>https://doi.org/10.1063/1.1780190 |
| T5 | LASL Shock Hugoniot Data | 冲击 Hugoniot 汇编 | Marsh 1980，674 页，元素 / 化合物 / 炸药冲击数据 | SESAME / QEOS 经典实验基准 | https://archive.org/details/LASL_Shock_Hugoniot_Data |
| T5 | Van Thiel Compendium / IHED extractor | 冲击数据汇编与抽取 | UCRL-50108 系列；IHED 物质编号可与阻抗匹配工具联用 | 冲击阻抗匹配、Hugoniot 拟合 | https://impactswiki.net/impact-tools-book/im/manual.html<br>https://github.com/ImpactsWiki/impact-tools-book |
| T5 | Stewart Group / ImpactsWiki 高压 EOS 汇编 | 社区 EOS 模型库 | ANEOS / M-ANEOS 导出的 forsterite、Fe、Fe-Si、水、SiO₂ 等 EOS；pyKO 1D 冲击代码 | 多相、地质靶材与开源 EOS 对照 | https://sarahtstewart.net/community-tools/<br>https://impactswiki.net/impact-tools-book/ |

| 表号 | 条目 | 说明 | 关键字段 / 命令 | 入口 |
| --- | --- | --- | --- | --- |
| T6 | SESAME 300 系列表号 | 读表前必须确认表号，否则能量与压力错位 | 301 总 EOS = 304 + 305 + 306；303 离子 EOS + 冷曲线 = 305 + 306；304 电子 EOS；305 离子 EOS 含零点；306 冷曲线 | http://opacplot2.readthedocs.io/en/latest/format.html |
| T6 | SESAME `.ses` ASCII | 单精度 15 位或双精度 22 位；按材料 ID 索引，如 Al 为 13719 | `OpgSesame('sesame.ses', opp.OpgSesame.SINGLE)`；前缀 total_、ioncc_、ele_、ion_、cc_ | http://opacplot2.readthedocs.io/en/latest/format.html |
| T6 | EOSPAC | SESAME 表读取、插值、反演（由 ρ、E 反查 T），供多语言宿主代码调用 | 查表 / 插值 / 反演接口；`invert_at_setup` 可在初始化时预计算 T(ρ,E) 反表；表号 matid | https://www.osti.gov/biblio/1998088<br>https://lanl.github.io/singularity-eos/gopsub/crest/src/models.html |
| T6 | IPCRESS / GANDOLF | LANL 新不透明度数据文件格式与读取例程 | GANDOLF 读取 IPCRESS；TOPS 输出配套 | https://www.osti.gov/servlets/purl/1053576<br>https://physics.nist.gov/Icamdata/PDF/1Databases/magee.pdf |
| T6 | IONMIX | FLASH 生态常用 EOS + 多群不透明度交换格式 | idens、temps、Zf_DT、Pi_DT、Pec_DT、Ui_DT、Uec_DT、groups、opr_mg、opp_mg、emp_mg | http://opacplot2.readthedocs.io/en/latest/format.html |
| T6 | opacplot2 / opac-convert / opac-error | Python 读写与比对 EOS / 不透明度表 | 输入：Propaceos、SESAME `.ses`、QEOS SESAME `.mexport`、MULTI `.opp / .opr / .opz / .eps`；输出：IONMIX；`opac-error` 逐点比两表；`write2hdf` 出 HDF5 | https://github.com/flash-center/opacplot2<br>http://opacplot2.readthedocs.io/en/latest/format.html |
| T6 | opac-convert 示例 | 混合物 CH 表转换并显式给原子序数与分数 | `opac-convert --Znum 1,6 --Xfracs .5,.5 myfile.ses`；`--log emp_mg` 处理超两位指数 | http://opacplot2.readthedocs.io/en/latest/format.html |
| T6 | MULTI 表格式 | MPQ MULTI 代码使用的不透明度与 EOS 表 | `.opp`、`.opr`、`.opz`、`.eps`；opacplot2 的 `OpgMulti` 可读写并 `write2hdf` | http://opacplot2.readthedocs.io/en/latest/format.html |
| T6 | Propaceos 表 | PrOpacEOS 产出的 EOS / 多群不透明度表；opacplot2 需额外 Python reader | 安装时把 `opg_propaceos.py` 放入包目录 | https://github.com/flash-center/opacplot2<br>https://www.prism-cs.com/Software/overview.html |
| T6 | Spiner / HDF5 / sesame2spiner / stellarcollapse2spiner | LANL 开源 EOS 闭包库：把 SESAME 与 StellarCollapse 表转成 GPU 友好的 Spiner / HDF5 表 | `SINGULARITY_USE_HDF5`、`SINGULARITY_USE_EOSPAC`、`sesame2spiner`；内部统一 cgs | https://lanl.github.io/singularity-eos/<br>https://github.com/lanl/singularity-eos<br>https://www.hdfgroup.org/solutions/hdf5/ |
| T6 | TOPS 多群网格 | 在线生成时显式定义群边界，避免默认网格与宿主代码群结构不一致 | 默认 33 边界 / 32 群，0.001–300 keV；温度、密度、群边界乘积上限 50000；单色 3000 或 3900 频点 | https://aphysics2.lanl.gov/static/opacdocs/opac-help.html |
| T6 | OPLIB u 网格与 OPAL R-T₆ 网格 | 不同库的独立变量不同，混用前必须重映射 | OPLIB：u=hν/kT，14,900 点，1e-4–3e4；OPAL：R=ρ/T₆³，T₆=T/1e6 K | https://arxiv.org/pdf/1601.01005<br>https://opalopacity.llnl.gov/opal.html |
| T6 | 单位约定 | 转换时显式核对，否则辐射热波速度会系统性偏差 | cgs；ρ 用 g/cm³；T 用 eV 或 K 需标注；光子能量用 keV；不透明度 cm²/g | https://lanl.github.io/singularity-eos/<br>http://opacplot2.readthedocs.io/en/latest/format.html |

| 表号 | 代码 | 机构 | EOS | 不透明度 / 发射率 | 热导 | 辐射输运与混合闭包 | 入口 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T7 | HYDRA | LLNL | LEOS（QEOS 类）、Purgatorio、Thomas–Fermi、内联 QEOS | OPLIB、HYDRA-DCA / CRETIN NLTE、多群扩散 | Lee–More 限流热导、SESAME 电子热导、Spitzer 型离子热导 | 多群扩散；离散纵标可作对照；靶丸 / 黑腔主用 | https://pubs.aip.org/aip/pop/article/24/5/052701/990207/<br>https://pubs.aip.org/aip/pop/article-pdf/doi/10.1063/1.4976710/13592906/022705_1_online.pdf |
| T7 | xRAGE | LANL | 每个材料 LTE 表格 EOS；NLTE 表在 EOS 查表迭代中替换电子 EOS | 表格化 NLTE 发射率 η_g / 吸收系数 α_g，参考谱 + 线性修正 | 基于表查得的热力学导数 | 默认多材料压力-温度平衡 PTE；电子 / 离子分别查表；Picard 迭代使 ne 与电离度自洽；Jayenne IMC | https://pubs.aip.org/aip/pop/article/29/8/083901/2845168/ |
| T7 | LASNEX | LLNL | 理想气体到 QEOS / 表格 EOS | LTE 到 NLTE 原子模型给出不透明度、发射率、电离态 | 与 EOS 配套 | 多群辐射扩散；黑腔 X 射线驱动对称性设计 | https://pubs.aip.org/aip/pop/article/29/8/083901/2845168/<br>https://grokipedia.opelly.me/articles/lasnex |
| T7 | HELIOS / HELIOS-CR | Prism | PrOpacEOS 生成的表 | PrOpacEOS 多群表；CR 版内联 NLTE 碰撞辐射 | 内置 | 1D 平面 / 柱 / 球辐射流体；激光或外辐射源加热 | https://www.prism-cs.com/Software/overview.html |
| T7 | MULTI | MPQ 等 | QEOS / SESAME 类 EOS | `.opp / .opr / .opz / .eps` 多群不透明度表 | 配套电子热导 | 1D 拉格朗日辐射流体；QEOS 论文明确以替代 SESAME 表为目标 | https://www.sciencedirect.com/science/article/abs/pii/S016890029800446X<br>http://opacplot2.readthedocs.io/en/latest/format.html |
| T7 | FLASH | Flash Center | 表格 EOS：SESAME、StellarCollapse、IONMIX；Singularity-EOS 闭包 | 多群不透明度表 | SpitzerHighZ / LeeMore / EppHain / JiHeld | 多物理 HEDP；PPM / unsplit hydro；可接 HDF5 表 | https://flash.rochester.edu/site/flashcode/<br>https://flash.rochester.edu/site/flashcode/user_support.html |
| T7 | Jayenne / CRASH | LANL / 密歇根 | 表格 EOS | 表格不透明度 / 发射率 | 表格热导 | IMC 辐射输运；CRASH 常用于辐射烧蚀与激波管基准 | https://pubs.aip.org/aip/pop/article/29/8/083901/2845168/ |
| T7 | LARED 集成程序 | 北京应用物理与计算数学研究所 | 实际气体状态方程；重映时按 EOS 类型分别累加能量 | 发射 / 吸收系数：LTE 由数据库插值，NLTE 由平均原子模型 Pn 方程求解 | 限流电子 / 离子热导 κe | 三温建模与辐射多群输运对照；多群方程含 Bg、kPg、Newton 线性化 | https://www.cpsjournals.cn/article/doi/10.11884/HPLPB202638.260195<br>https://www.hplpb.com.cn/cn/article/pdf/preview/10.11884/HPLPB201628.122001.pdf |

| 表号 | 资源 | 类型 | 可校验量 | 关联模型 / 代码 | 入口 |
| --- | --- | --- | --- | --- | --- |
| T8 | 第 10 届 Non-LTE Code Comparison Workshop | 标准算例 | Ne、Al、Si、Cl 稳态与时变；Te、ne、Tr、谱线区间；15 个代码交叉比对 | NLTE 布居、电离分布、发射 / 吸收谱 | https://nlte.nist.gov/NLTE10<br>https://nlte.nist.gov/NLTE10/Docs/NLTE10.pdf |
| T8 | NLTE-10 综述 | 文献 | 代码结构、完备性、密度效应、速率保真度差异 | CRETIN、FLYCHK、ATOMIC、PrismSPECT 等 | https://www.osti.gov/biblio/1529152 |
| T8 | RPHDM 系列 | 会议 / 文集 | 稠密等离子体辐射输运、不透明度、谱线展宽、NLTE 动力学、X 射线谱 | OPAL、STA、平均原子、DCA | https://www-amdis.iaea.org/meetings/RPHDM2014/purpose.php<br>https://worldscientific.com/worldscibooks/10.1142/1412 |
| T8 | Sandia Z 机铁不透明度 / 辐射烧穿 | 实验 | 太阳辐射区条件下 Fe 透射谱、平均不透明度与 X 射线段约束 | CASSANDRA、DCA、OPAS、OPLIB | https://www.osti.gov/pages/biblio/2350885 |
| T8 | 神光-III 原型装置辐射输运 | 实验 + 反演 | 直管超声速辐射热波峰值与传输时间，反演并修正 Au 等离子体不透明度与 EOS | 高 Z 平均原子 / 辐射输运表 | https://doi.org/10.1063/5.0043745 |
| T8 | LASL Shock Hugoniot / Van Thiel / IHED | 冲击实验库 | Us-up、P、ρ、E 沿 Hugoniot；冷曲线与相变 | SESAME、QEOS、ANEOS、M-ANEOS | https://archive.org/details/LASL_Shock_Hugoniot_Data<br>https://doi.org/10.1063/1.1780190<br>https://impactswiki.net/impact-tools-book/im/manual.html |
| T8 | NIST ASD 谱线基准 | 原子数据基准 | 能级、波长、跃迁概率、电离能 | 精细谱不透明度模型 | https://physics.nist.gov/PhysRefData/ASD/levels_form.html |
| T8 | 阻抗匹配 / Hugoniot 拟合工具 | 开源工具 | 由 IHED 数据拟合线性、二次、通用 Hugoniot 形式 | 冲击 EOS 参数化 | https://impactswiki.net/impact-tools-book/im/manual.html<br>https://github.com/ImpactsWiki/impedance-match-app |

| 表号 | 名称 | 机构 | 数据内容 | 与 RHD 关系 | 入口 |
| --- | --- | --- | --- | --- | --- |
| T9 | TOPbase | Opacity Project / CDS | Z=1–26 离子 LS 耦合项能量、f 值、光电离截面；Fe 的 PLUS 数据 | OP / OPCD3.3 的原子数据底座 | http://tiptopbase.obspm.fr/topbase<br>http://cdsweb.u-strasbg.fr/topbase/topbase.html |
| T9 | TIPbase | Iron Project / CDS | Fe 与铁峰元素能级、跃迁、碰撞数据 | 高 Z 精细谱补充 | http://cdsweb.u-strasbg.fr/tipbase/home.html |
| T9 | OPserver | Ohio Supercomputer Center | OP 单色不透明度远程服务 | 低密度等离子体不透明度查询 | http://opacities.osc.edu/ |
| T9 | Spectr-W3 | RFNC-VNIITF / JIHT RAS | 约 45 万条多电荷离子光谱记录：能级、跃迁波长与概率、电离势、自电离速率、碰撞截面拟合、发射谱图 | 常被 THERMOS 用作实验数据修正源 | http://spectr-w3.snz.ru/index.phtml<br>https://link-proxy.springer.com/article/10.1134/S0030400X16040238 |
| T9 | NIST ASD | NIST | 原子能级、谱线、跃迁概率 | 不透明度 / 光谱计算的实验基准 | https://physics.nist.gov/PhysRefData/ASD/levels_form.html |
| T9 | CHIANTI | 国际协作 | 天体与实验室等离子体谱线、连续辐射、电离 / 复合数据 | 低密度等离子体谱诊断 | https://www.chiantidatabase.org/ |
| T9 | VAMDC | EU 虚拟原子分子数据中心 | 聚合 TOPbase、TIPbase、Spectr-W3 等，遵循 XSAMS 标准 | 统一检索原子分子数据 | https://portal.vamdc.eu/vamdc_portal/ |
| T9 | IAEA 原子分子数据单元 / ALADDIN / FLYCHK 镜像 | IAEA | 聚变基础数据；ALADDIN 为 IAEA 采用的原子数据交换格式，含 ALPACK 检索例程 | 数据交换标准与 NLTE 镜像 | https://www-amdis.iaea.org/<br>https://www-amdis.iaea.org/FLYCHK/ZBAR/index.php<br>https://www.nstl.gov.cn/paper_detail_picture.html?id=4a66999beef088a415e6dfe883207bda |
| T9 | ExoMol | UCL 等 | 分子线表与高温吸收截面 | 低温 / 行星大气，通常不进 HED 主链路 | https://www.exomol.com/ |
| T9 | HITRAN / HITEMP | Harvard–CfA 等 | 分子高分辨吸收谱线参数，HITEMP 面向高温气体 | 低温分子不透明度对照 | https://hitran.org/ |
| T9 | Kurucz 线表 / PHOENIX | Harvard / 汉堡大学 | 恒星大气不透明度与谱线表、大气模型与合成光谱 | 低密度天体对照 | http://kurucz.harvard.edu/<br>https://www.physik.uni-hamburg.de/en/hs/group-hauschildt/research/phoenix.html |
| T9 | NASA MAESTRO | NASA Ames 等 | 系外行星大气分子 / 原子不透明度，按分子检索、可视化、对比、下载 | 非 HED，仅作数据平台对照 | https://science.data.nasa.gov/opacities/ |
| T9 | OPTAB | 开源 | 生成辐射流体用气体不透明度表的公开代码，聚合 OPAL、OP、ExoMol、HITRAN、Kurucz、PHOENIX 等源 | 低密度气体表生成流程参考 | https://github.com/nombac/optab |
| T9 | NIST LIBS / Saha-LTE 在线工具 | NIST | 等离子体发射谱、Saha-LTE 谱、元素混合比与 Te / ne 输入 | 快速谱诊断对照 | https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=930947 |

| 表号 | 名称 | 类型 | 内容 | 入口 |
| --- | --- | --- | --- | --- |
| T10 | 中国工程物理研究院 CAEP | 机构 | 等离子体物理与计算物理、冲击波与爆轰物理、激光技术、脉冲功率技术；国内 EOS / 不透明度数据主要产出单位 | https://www.caep.ac.cn/index.shtml |
| T10 | LARED 集成程序 | 程序 / 文献 | 三温与辐射多群输运建模对照；多群发射吸收系数由数据库插值或平均原子 Pn 方程给出；六孔球腔整体模拟 | https://www.cpsjournals.cn/article/doi/10.11884/HPLPB202638.260195<br>https://www.hplpb.com.cn/cn/article/pdf/preview/10.11884/HPLPB201628.122001.pdf |
| T10 | Matter and Radiation at Extremes（MRE） | 期刊 | CAEP 主办、AIP 合作出版，Diamond OA；设 Radiation and Hydrodynamics、ICF Physics、High Pressure Physics 栏目；EOS / 不透明度新数据首发地 | https://www.mre.org.cn/<br>https://pubs.aip.org/aip/mre/pages/about |
| T10 | 强激光与粒子束 | 期刊 | 黑腔辐射建模、LARED、多群输运、三温模型、激光等离子体中文一手文献 | https://www.hplpb.com.cn/<br>https://www.hplpb.com.cn/en/ |
| T10 | 中国物理学会期刊网 | 期刊平台 | LARED 三维集成程序、状态方程重映、多群输运方程与 Newton 线性化全文 | https://www.cpsjournals.cn/ |
| T10 | 神光-III 原型辐射输运实验 | 实验 / 反演 | 用 Au 直管辐射热波峰值与传输时间修正高 Z 不透明度与 EOS 参数，并与辐射烧蚀、金壁运动实验自洽 | https://doi.org/10.1063/5.0043745 |
| T10 | 国内温稠密物质 QMD 数据 | 计算数据 | 量子 Langevin MD 构建温稠密 He 的 EOS、电子热导与辐射不透明度数据库，10–60 kK、1–24 g/cm³；另有氮解离相变区 EOS 与不透明度实验研究 | https://www.caep.ac.cn/index.shtml<br>https://www.mre.org.cn/ |
| T10 | 国内高 Z 参数校验 | 实验 / 文献 | 结合辐射流峰值、传输时间与误差传递理论修正金等离子体参数范围 | https://doi.org/10.1063/5.0043745<br>https://www.mre.org.cn/ |

| 表号 | 条目 | 获取方式 | 公开程度 | 使用注意 | 入口 |
| --- | --- | --- | --- | --- | --- |
| T11 | SESAME 数据表 | 提交 SESAME Database Request Form，登记主用户与附加用户、国籍、邮箱 | 受地域限制的许可数据 | 论文需注明表号、版本与获取途径 | https://www.lanl.gov/org/ddste/aldsc/theoretical/physics-chemistry-materials/_assets/docs/sesame-request-form.pdf |
| T11 | LEOS / Lynx 表 | 机构合作 / 许可 | 不在线分发 | 与 HYDRA 辐射边界源配套，换 EOS 需重新调源 | https://searchworks-lb.stanford.edu/view/12053805 |
| T11 | CRETIN | LLNL 软件许可，合格用户签协议；有 3 个月学术 Demo | 出口管制 | 原子模型可自建或读 FAC / HULLAC | https://softwarelicensing.llnl.gov/product/cretin-software |
| T11 | PrOpacEOS / HELIOS / PrismSPECT / SPECT3D | 商业授权与培训 | 商业软件 | 表格式需与宿主代码群结构对齐 | https://www.prism-cs.com/ |
| T11 | THERMOS | 官网为软件与数据库描述页 | 无直接下载入口 | 可接 FAC、RCG、NIST、Spectr-W3 数据修正 | https://www.keldysh.ru/thermos/en |
| T11 | OPAS / SCO-RCG / CASSANDRA | 向作者邮件申请或合作 | 无公开在线库 | 写明所用模型版本与实验对照 | https://arxiv.org/pdf/1512.00603.pdf<br>https://www.sciencedirect.com/science/article/pii/S0022407301000735 |
| T11 | FLYCHK | NIST 站点需 User ID / Password；IAEA 镜像可查说明 | 注册制 | 中性近邻区结果不可靠；适合高度电离、中间密度、非完全 LTE 区 | https://nlte.nist.gov/FLY/<br>https://www-amdis.iaea.org/FLYCHK/ZBAR/index.php |
| T11 | OPLIB / TOPS / OPAL / OP / TOPbase / OPserver | 网页直接生成或下载表 | 公开在线 | 老站点多为 http；CDS 旧链接已部分迁移到巴黎天文台镜像 | http://aphysics2.lanl.gov/opacity/lanl<br>https://opalopacity.llnl.gov/opal.html<br>http://op-opacity.obspm.fr/opacity/<br>http://tiptopbase.obspm.fr/topbase<br>http://opacities.osc.edu/ |
| T11 | FLASH | 注册后下载代码；用户指南公开 | 公开但需注册 | 当前版本 FLASH4.8；User's Guide 有 HTML 与 PDF | https://flash.rochester.edu/site/flashcode/user_support.html |
| T11 | 引用与版本记录 | 建表时记录库版本、表号、材料 ID、温度密度网格、群边界、获取日期 | 项目内控 | 同一材料不同版本表差异可能改变辐射热波速度 | https://www.osti.gov/biblio/2570872<br>https://arxiv.org/pdf/1601.01005 |

| 表号 | 仿真对象 | 推荐 EOS | 推荐不透明度 | 热导 | NLTE 补充 | 验证基准 | 入口索引 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T12 | ICF 黑腔 / Au 壁 X 射线输运 | LEOS 或 SESAME + Purgatorio 高 Z 修正 | OPLIB / TOPS 多群表；高 Z 用 DCA 或平均原子表 | SESAME 电子热导 + Lee–More 限流 | 黑腔低密度区用 CRETIN 表格化 NLTE | 神光-III Au 辐射热波、NLTE-10 | T1 / T2 / T4 / T7 / T8 |
| T12 | ICF 靶丸内爆（CH、DT、掺杂层） | LEOS（QEOS 类）或 SESAME；Purgatorio 用于埋层 | OPLIB / ATOMIC 单色转多群 | SESAME 电子热导、Spitzer 型离子热导 | 冕区与烧蚀前沿切 NLTE | HYDRA / xRAGE 对照、LASL Hugoniot | T1 / T2 / T7 / T8 |
| T12 | 激光直接驱动 / 低密度冕区 | QEOS 或 SESAME 表格 EOS | OPLIB 单色或多群；OPAL 仅作低密度对照 | Lee–More / SpitzerHighZ | FLYCHK、CRETIN、PrismSPECT | NLTE-10、RPHDM | T1 / T2 / T4 / T8 |
| T12 | Z-pinch / 高 Z 辐射源 | SESAME 或 THERMOS 平均原子 EOS | CASSANDRA、OPIND、STA / UTA、SCO-RCG 精细谱 | 平均原子电子热导 | PrismSPECT、SPECT3D 后处理 | Sandia Z 铁透射谱、NLTE-10 | T2 / T3 / T4 / T8 |
| T12 | 温稠密物质 / 预热层 | QMD / DFT-MD / PIMC 补表，或 THERMOS 平均原子 | 同一 QMD 或平均原子模型的不透明度 | QMD 电子热导 | 视电离度决定是否 NLTE | 神光-III、RFBR 冲击库 | T1 / T3 / T5 / T8 |
| T12 | 高 Z 混合材料 / 多材料 PTE 单元 | SESAME / LEOS 按材料分别查表 | TOPS 按电子温度与电子简并度平衡混合单元素表 | 表格热导 | 表格化 NLTE 替换电子 EOS | xRAGE PTE 算例 | T2 / T3 / T6 / T7 |
| T12 | 辐射烧蚀 / 热波传播基准 | SESAME 或 QEOS | Rosseland / Planck 平均或多群表，群边界与宿主一致 | Lee–More 限流 | 辐射场偏离 Planck 时用表格化 NLTE 线性修正 | CRASH、神光-III 直管热波 | T2 / T4 / T7 / T8 |
| T12 | 冲击压缩 / Hugoniot 标定 | ANEOS / M-ANEOS / QEOS / SESAME | 冲击区不透明度通常次要，仍需多群表做辐射耦合 | 表格或解析热导 | 一般 LTE 足够 | LASL、Van Thiel、IHED、阻抗匹配工具 | T1 / T5 / T8 |
| T12 | 低密度天体混合物（仅作模型对照） | OPAL / OP 配套 EOS | OPAL、OPCD3.3、OPserver、OPLIB 天体预计算表 | 传导不透明度 | 非 RHD 主链路 | OP 与 OPAL Rosseland 对比文献 | T2 / T9 / T11 |
