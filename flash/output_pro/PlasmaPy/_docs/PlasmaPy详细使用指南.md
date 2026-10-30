# PlasmaPy 详细使用指南

> ⚠️ **本 Markdown 指南已不再更新**：其系统化、公式+代码并重的可执行版本已迁移至 **`docs/scripts/demo_PlasmaPy.ipynb`**（Jupyter Notebook，7 篇 / 33 节，已在 Anaconda3 下完整执行、含 9 张内嵌插图、0 报错）。请优先阅读该 Notebook；本文档仅作为离线备份保留。

> **基准版本**: PlasmaPy 2026.2.0（本地源码 `PlasmaPy/src/plasmapy/`，与官方 `https://docs.plasmapy.org/en/stable/` 同版本）
> **适用 Python**: ≥ 3.12（本地工作区 venv 为 3.13）
> **覆盖范围**: 8 个顶层子包（particles / formulary / dispersion / plasma / simulation / analysis / diagnostics / utils）全部公开 API
> **姊妹文档**: [`PlasmaPy使用说明书.md`](PlasmaPy使用说明书.md)（安装与速查）、[`相关公式接口速览.md`](相关公式接口速览.md)（公式-API 对照）
> **官方教程总目录**: <https://docs.plasmapy.org/en/stable/examples.html>

---

# 第一篇 准备与基础

## 第 1 章 导论与全书使用方法

### 1.1 PlasmaPy 是什么

PlasmaPy 是一个由等离子体物理社区共同开发的开源 Python 包，定位类似于 Astropy 之于天文学——它不试图替代任何大型模拟程序（如 FLASH、PIC 代码），而是为等离子体研究与教学提供**可复用的基础设施层**：粒子物理数据、解析公式库、色散关系求解器、诊断数据处理、粒子轨道追踪等。官方首页对其定位的表述是 "an open source community-developed Python 3.12+ package for plasma research and education"，即面向研究与教育的社区共享平台。

对本项目（PhySimX / FLASH / FLYCHK）而言，PlasmaPy 的典型用途包括：

1. **参数量级核验**：用 `formulary` 快速计算 Debye 长度、等离子体频率、库仑对数、Spitzer 电阻率，与 FLASH 输运系数做交叉检查；
2. **粒子与电离态数据**：`particles` 提供元素/同位素/离子的质量、电荷、电离能查询，以及 CH 混合物等效离子建模；
3. **诊断方法学**：`diagnostics.thomson` 是汤姆逊散射谱合成与拟合的标准工具，与 FLYCHK 光谱诊断工作互补；
4. **耦合/简并判据**：`coupling_parameter`、`quantum_theta` 可对 FLASH 输出的 dens/tele 场逐点判断强耦合/强简并区域，评估经典输运模型的适用域。

### 1.2 版本基准与架构总览

本指南以 **PlasmaPy 2026.2.0** 为准（本地源码 commit gfca3bc8a9，官方 stable 文档同版本）。需要特别说明：**PlasmaPy 没有 `transport` 或 `database` 子包**——输运物理（Braginskii 系数、碰撞频率）位于 `formulary` 内部；原子数据库（元素、同位素、电离能）以 JSON 形式内置在 `particles/data/` 目录下，随包分发。

八个顶层子包的依赖关系可概括为：

```
utils（单位校验、异常、装饰器，横切所有子包）
   ↑
particles（粒子对象与原子数据）
   ↑
formulary（解析公式库，含 collisions 子包）
   ↑                    ↑
dispersion（色散关系）   plasma（等离子体对象与网格）
   ↑                    ↑
   └── simulation（粒子模拟）──┘
        ↑
analysis（数据分析） + diagnostics（诊断）—— 依赖 particles 与 formulary
```

| 子包 | 一句话定位 | 本指南篇幅 |
|---|---|---|
| `particles` | 粒子对象、原子/核数据、电离态建模 | 第二篇（第 4–6 章） |
| `formulary` | 等离子体特征量与输运系数的解析公式 | 第三篇（第 7–19 章） |
| `dispersion` | 等离子体色散关系（解析 + 数值求解器） | 第四篇（第 20–22 章） |
| `plasma` | 等离子体状态对象与网格抽象 | 第五篇（第 23–24 章） |
| `simulation` | 粒子模拟框架（Boris 积分器、轨迹追踪） | 第五篇（第 25–26 章） |
| `analysis` | 通用数据分析（磁零点、拟合、朗缪尔、时序） | 第六篇（第 27–28、31 章） |
| `diagnostics` | 诊断物理（Thomson 散射、带电粒子射线照相） | 第六篇（第 29–30 章） |
| `utils` | 单位校验装饰器、异常体系、辅助工具 | 第七篇（第 32–34 章） |

这张表同时暗示了学习依赖顺序：`utils` 的单位体系（第 3 章）与 `particles` 的粒子对象（第二篇）是所有其他子包的输入语言——先掌握这两者，后续子包的 API 只需"扫一眼签名"即可上手，因为参数命名与校验风格全库统一（`T_e/n_e/B/V` + `validate_quantities`）。

### 1.3 阅读路线建议

- **只想快速查 API**：直接看第 36 章的 API 速查总表，或姊妹文档《PlasmaPy使用说明书》；
- **只关心公式对应关系**：看《相关公式接口速览》，本指南第三篇在其基础上补充签名、参数语义与示例；
- **第一次系统学习**：按篇顺序通读，第 3 章的单位体系是全库通用前提，务必先读；
- **移植旧代码**：先看第 33 章弃用迁移表，确认所用 API 是否已换名。

### 1.4 全书约定

1. 所有代码示例默认已执行 `import astropy.units as u` 与 `import numpy as np`；
2. `ParticleLike` 指可被解析为粒子对象的任意输入（字符串 `"e-"`、`Particle` 实例、整数原子序数等），第 4 章详述；
3. 标注 ⚠ 的 API 为已弃用或带有 `|expect-api-changes|` 标记（官方声明未来版本可能变更签名）；
4. 每章末尾的"官方文档"给出对应教程 notebook 链接，方便交叉验证；
5. 涉及单位时一律使用 astropy Quantity 写法（如 `1e20 * u.m**-3`），裸数值仅在 `_lite` 函数（第 34 章）中出现。

### 1.5 PlasmaPy 在仿真工具链中的位置：能做什么、不做什么

把 PlasmaPy 放进本项目的完整工具链里看，它的边界非常清晰：

**它做**：解析公式（确定性计算，给定输入即得输出，无求解器迭代）、原子/核数据查询、小型正演诊断（Thomson 谱合成、质子照相合成）、教学级粒子轨道。计算成本 O(N) 且无隐式方程——这意味着 PlasmaPy 的所有输出都是**可复现的纯函数**，适合写进自动化校验脚本。

**它不做**：辐射流体演化（FLASH）、非 LTE 原子态布居（FLYCHK）、不透明度与谱线精细结构（FLYCHK/ATOMIC 类代码）、PIC 级动理学模拟、大规模并行计算。凡涉及"解方程组"而非"代公式"的场景，PlasmaPy 只提供求解器的**构件**（如色散函数）而非成品。

对日常工作流的具体映射：FLASH 输入文件生成（`flash/input_gen`）阶段的参数量级检查用 PlasmaPy；NSGA-II 优化的物理约束（如 $\ln\Lambda>2$、$N_D>10$ 的可行域判定）可用 PlasmaPy 构造向量化判据；后处理诊断阶段（`output_pro`）的物理量换算（数密度↔质量密度、$n_e=Z\,n_i$ 自洽性）亦然。把"PlasmaPy 校验层"插在数据管道的关键节点，是本指南推荐的工程模式。

### 1.6 与其他 Python 生态的关系

- **astropy**：单位与常数体系的提供者，PlasmaPy 是其"领域消费者"的典范——学好第 3 章等于同时解锁 astropy 全生态；
- **NumPy/SciPy**：数值底座；SciPy 用于求根（色散求解器）、优化（lmfit 内部）；
- **xarray/pandas**：网格数据容器（第 24 章），熟悉 xarray 的用户可直接操作 `CartesianGrid` 的场量；
- **lmfit**：拟合引擎（第 27.2、29.2 章）；
- **h5py**：二进制 I/O（网格序列化、粒子轨迹存档、Thomson 配置）。

生态互补而非竞争：PICTuRE/torchandes 等 PIC 代码、OEDGE 等输运代码不与 PlasmaPy 重叠；社区 wiki 维护了完整的"等离子体 Python 生态地图"。

**关于本指南的生成方式**：本指南基于本地源码逐包盘点（全部 `__all__` 清单）与官方文档（docs.plasmapy.org stable，v2026.2.0）交叉确认写成；关键章节的示例遵循 PlasmaPy 官方 notebook 的推荐用法，并结合本工作区（FLASH/FLYCHK/NSGA 优化）的实际场景做了适配改写。发现与本地行为不一致之处时，以本地 `help()` 输出为准并回改本指南（附录 F 约定）。

## 第 2 章 安装与环境配置

### 2.1 安装方式

PlasmaPy 支持 pip 与 conda-forge 两种主流安装方式：

```bash
# pip（推荐，自动解析 astropy/numpy/scipy 等核心依赖）
pip install plasmapy

# conda-forge
conda install -c conda-forge plasmapy

# 从本工作区源码安装（install_from_source.sh 的核心逻辑）
cd PlasmaPy/PlasmaPy && pip install -e .
```

核心依赖（2026.2.0 的 `pyproject.toml` 声明）：astropy>=6.1.3、numpy>=1.26、scipy、matplotlib、h5py、lmfit>=1.3、mpmath>=1.3、pandas、xarray、tqdm、requests、wrapt。注意 2026.2.0 **没有可选依赖组**（`[project.optional-dependencies]` 为空），上述包全部随主包安装，因此 `import plasmapy.diagnostics.thomson` 不会因缺 lmfit 失败——但了解哪个功能依赖哪个库仍有价值（便于排查版本冲突），映射表见第 36 章附录。

Python 版本要求 **≥ 3.12**（官方 classifiers 覆盖 3.12/3.13/3.14）。若系统 Python 过旧，建议用 conda 或 uv 新建环境。

### 2.2 本地环境验证

工作区 `.venv`（Python 3.13）已装好源码包，验证方法：

```bash
# Windows (bash)
.venv/Scripts/python.exe -c "import plasmapy; print(plasmapy.__version__, plasmapy.__citation__[:50])"
```

更完整的端到端验证用 `demos/run_all_tests.py`，它依次运行 5 个 demo 脚本（formulary 基础、particles、碰撞输运、Thomson 散射、激光等离子体波）并报告 PASS/FAIL，同时产出 4 张图到 `demos/figures/`。第 36 章对这些 demo 有逐个精讲。

### 2.3 Windows 环境注意事项

1. **编码**：所有脚本建议显式 `# -*- coding: utf-8 -*-` 并以 UTF-8 保存；路径含中文时优先用 `pathlib.Path`；
2. **h5py 二进制**：h5py 由 pip 直接分发预编译 wheel，一般无需自行编译；若遇到 DLL 加载失败，先升级 pip 再重装；
3. **换行符**：本工作区约定所有输出文件强制 LF，写文件时用 `open(..., newline="\n")`；
4. **多环境并存**：系统 Python、conda 与 venv 混用时，`pip` 装到哪个环境取决于激活状态——固定用 `python -m pip install`（明确指向解释器）避免"装了却 import 不到"的经典问题；工作区脚手架统一走 `.venv/Scripts/python.exe -m pip`；
5. 安装的更多细节与常见问答，直接引用《PlasmaPy使用说明书》第 2–3 节，此处不再重复。

### 2.4 引用与致谢

官方要求：凡在论文或报告中使用 PlasmaPy，请按 <https://docs.plasmapy.org/en/stable/about/citation.html> 的指引引用。程序内可随时取 `plasmapy.__citation__`。

### 2.5 从源码安装的完整流程与版本切换

工作区 `install_from_source.sh` 的标准流程（供手动复现）：

```bash
# 1. 克隆官方仓库（或使用本地已有内层仓库）
git clone https://github.com/PlasmaPy/PlasmaPy.git
# 2. 切换到目标版本
cd PlasmaPy && git checkout v2026.2.0    # 或 commit gfca3bc8a9
# 3. 建独立环境并安装（可编辑模式便于改源码）
python -m venv .venv && source .venv/bin/activate   # Windows: .venv/Scripts/activate
pip install -e .
# 4. 验证
python -c "import plasmapy; print(plasmapy.__version__)"
```

版本切换要点：版本号由 setuptools_scm 按 git 标签动态生成——**直接改源码目录内容而不打标签会导致版本号带脏标记**（如 `2026.2.1.dev3+gxxxx`）；在可编辑模式下切换版本后，务必清掉 `__pycache__` 再验证。工作区内层仓库已固定在 2026.2.0，多版本并存时建议每版本一个独立 venv，用 `run_all_tests.py` 做回归后切换。

### 2.6 依赖冲突排查

PlasmaPy 的依赖面较宽（astropy/scipy/lmfit/h5py/xarray），与其他科学包共存时的两个高频冲突点：① astropy 主版本（PlasmaPy 2026.2.0 要 ≥6.1.3，老项目钉在 5.x 会解析失败）；② numpy 2.x 与旧扩展包的 ABI（h5py/lmfit 都需较新版本）。排查口诀：先 `pip check`，再 `pip install "package==x.y" --upgrade-strategy only-if-needed` 最小化升级，最后以 venv 隔离彻底解决。

## 第 3 章 单位体系：astropy.units 实战（全库通用前提）

### 3.1 为什么必须先学单位体系

PlasmaPy 的**几乎所有** `formulary` 函数和大部分类（`Particle` 除外，它返回纯 astropy 常量）都经过 `validate_quantities` 装饰器（第 32 章剖析其实现）——入参和返回值都是 astropy `Quantity`，单位不匹配会直接抛 `UnitConversionError`。这带来两个结果：

- **收益**：单位错误在调用点立即暴露，而不是算出错误量级后默默传播——对物理仿真脚手架是巨大的安全网；
- **代价**：必须熟悉 astropy.units 的基本操作，否则会在单位换算上反复碰壁。

### 3.2 Quantity 基础

```python
import astropy.units as u
import numpy as np

n_e = 1e20 * u.m**-3            # 标量
T_e = np.array([50, 100, 200]) * u.eV   # 数组
B   = 5 * u.T

# 单位换算（用 .to，返回新对象；.si / .cgs 快捷转到 SI/CGS 基准）
print(T_e.to(u.K))        # [5.8e5, 1.16e6, 2.32e6] K
print((1e-4 * u.cm**-3).to(u.m**-3))

# 组合单位自动约化
E = B**2 / (2 * u.mu0)
print(E.unit)             # J/m3（即 Pa）
```

要点：**电子伏特不是温度单位**。`100 * u.eV` 是能量，要当温度用必须显式声明等价性（见 3.3）。这是 PlasmaPy 新手第一大报错来源。

### 3.3 等价性转换 equivalencies：温度 ↔ 能量

```python
T_e = (100 * u.eV).to(u.K, equivalencies=u.temperature_energy())
# 1.160e6 K

# PlasmaPy 的 T_e 参数多数声明了 equivalencies=u.temperature_energy()，
# 因此可以直接传 eV：
from plasmapy.formulary import Debye_length
lambda_D = Debye_length(T_e=100 * u.eV, n_e=1e20 * u.m**-3)   # 合法！
```

规律：PlasmaPy 中名为 `T_e`/`T_i` 的参数几乎都启用了 `temperature_energy()` 等价性，可直接传 eV 数值；但自己写裸 `u.eV.to(u.K)`（不带等价性）会报错，因为两者量纲不同。

### 3.4 读得懂 UnitConversionError

典型报错长这样：

```
UnitConversionError: The argument 'n_e' to function 'Debye_length()' can not be
converted to units of m^-3: 'eV' and 'm^3' are not convertible.
```

排查三步：① 看参数名（哪个参数传错）；② 看目标单位（函数期望什么）；③ 看你给的实际单位。最常见错误是：忘了乘单位（裸 float）、传了 cm^-3 忘转 m^-3（astropy 会自动转，但传裸数值不会）、把电子密度传成了质量密度（应用 `mass_density` 区分，第 10 章）。

### 3.4.1 三个真实错误案例的还原

**案例一（量纲对但单位错）**：把 `1e21`（cm⁻³ 口径的心算值）直接乘 `u.m**-3` 传入 `Debye_length`——量纲是数密度、校验通过、但结果差 $10^6$ 倍。教训：**校验器拦不住"口径错"**，单位正确 ≠ 数值正确；跨单位制搬运数值时必须显式换算（`(1e21*u.cm**-3).to(u.m**-3)`）。

**案例二（等价性缺失）**：自写函数里 `T_e.to(u.K)` 直接转——eV 到 K 无等价性声明时 astropy 拒绝。教训：温度能量转换只能通过 `temperature_energy()` 等价性，或者干脆学 PlasmaPy 的接口约定让函数自己声明等价性。

**案例三（静默广播错）**：`T_e` 形状 (100,)、`n_e` 形状 (200,) 传入——astropy 广播规则下这会抛 `ValueError`（100 与 200 不可广播），但 `(100,1)` 与 `(200,)` 会广播成 (100,200)——形状对了、语义错了（每对组合而非逐点配对）。教训：批量调用前 `assert T_e.shape == n_e.shape` 或显式对齐（第 3.8 节）。

### 3.5 用户视角的 validate_quantities

对使用者只需记住三条规则：

1. **能传 Quantity 就传 Quantity**，带单位的入参永远安全；
2. 数组化输入自动广播——`T_e` 传 `(N,)` 数组，返回也是 `(N,)`，这是参数扫描的基础；
3. 关键字默认值自带单位（如某参数默认 `u.radian`），传裸数值会被当作"无单位量"拒绝或警告。

### 3.6 `_lite` 函数：绕过单位系统的快速通道

`formulary` 中带 `_lite` 后缀的函数（如 `plasma_frequency_lite`、`thermal_speed_lite`、`Bethe_stopping_lite`）接受**裸数值数组**，按文档写明的 SI 单位直接计算，无校验、无对象包装。性能可提升一个数量级，适合大规模网格的内层循环；代价是失去单位安全网。调用约定与取舍详见第 34 章。

### 3.7 常用单位速查（等离子体语境）

| 物理量 | 推荐写法 | 备注 |
|---|---|---|
| 数密度 | `1e20 * u.m**-3` | PlasmaPy 内部一律 SI；`u.cm**-3` 输入会被自动转换 |
| 温度 | `(100 * u.eV)` 或 `1.16e6 * u.K` | 函数内已启用 temperature_energy 等价性 |
| 磁场 | `5 * u.T` | 1 T = 10⁴ G，`u.G` 可直接换算 |
| 频率 | `2 * np.pi * 5e9 * u.rad / u.s` | 注意 `gyrofrequency` 返回角频率（rad/s），除非设 `to_hz=True` |
| 截面 | `1e-20 * u.m**2` | barn：`u.barn` |

### 3.8 数组化与广播：参数扫描的正确姿势

astropy Quantity 完全继承 NumPy 广播语义，PlasmaPy 函数因此天然支持"一次调用算一条曲线"：

```python
import astropy.units as u
import numpy as np
from plasmapy.formulary import Debye_length

T_scan = np.logspace(1, 4, 100) * u.eV          # 10 eV ~ 10 keV
lam = Debye_length(T_e=T_scan, n_e=1e20 * u.m**-3)   # 返回 (100,) Quantity
# 二维广播：温度 × 密度的二维参数面
n_scan = np.logspace(18, 24, 200) * u.m**-3
lam2d = Debye_length(T_e=T_scan[:, None], n_e=n_scan[None, :])   # (100, 200)
```

两条纪律：① 广播靠 `[:, None]` 显式对齐维度，靠隐式规则容易差一个转置；② 结果仍是带单位数组，画图前用 `.to(u.um).value` 剥单位，别对 Quantity 直接 `plt.plot`（低版本 matplotlib 会静默忽略单位导致图错）。

### 3.9 物理常数：统一走 astropy

PlasmaPy 内部全部使用 astropy.constants（CODATA 精确值），用户侧应保持一致，避免手抄常数引入的不一致：

```python
from astropy.constants import m_e, c, eps0, k_B, hbar
m_e, c, eps0    # 质量自动带单位与不确定度
(m_e * c**2).to(u.J), (m_e * c**2).to(u.MeV)   # 电子静能 0.511 MeV
```

特别是有效玻尔半径 `a0`、经典电子半径 `r_e`（`astropy.constants.si.r_e`）这类等离子体公式常客，手抄 2.8179e-15 m 与库内值不一致时，Coulomb 对数类的结果会对不上——这是复现文献数值失败的常见原因之一。

### 3.10 单位调试工作流小结

遇到单位问题的固定排查顺序：

1. 读报错文本：哪个参数、期望什么单位、实际是什么（PlasmaPy 的报错信息由 `validate_quantities` 生成，包含参数名与目标单位，信息完整）；
2. 检查是否裸数值（忘乘单位）；
3. 检查温度是否需要 `temperature_energy()` 等价性；
4. 检查角频率/频率、数密度/质量密度两类"近义单位"混淆；
5. 复杂换算不确定时，用 `.si.bases` 看单位的构成基（如 `(u.V/u.m).si.bases`）确认量纲。

---

# 第二篇 粒子系统 particles

`plasmapy.particles` 是全库的地基：它提供原子、同位素、离子、基本粒子的数据访问与对象模型，`formulary` 的每个函数都通过 `particle_input` 装饰器消费这里的对象。官方教程：[Using PlasmaPy Particles](https://docs.plasmapy.org/en/stable/notebooks/getting_started/particles.html)。

## 第 4 章 Particle 对象全解

### 4.1 ParticleLike 与五种构造方式

`ParticleLike` 是一个类型协议：任何能被解析为粒子的输入。`Particle` 类接受：

```python
from plasmapy.particles import Particle

p1 = Particle("e-")          # 电子（标准符号）
p2 = Particle("p+")          # 质子
p3 = Particle("Fe")          # 元素（中性铁原子）
p4 = Particle("Fe 5+")       # 五价铁离子（电荷后缀前必须有空格，不可省略）
p5 = Particle("D")           # 氘（简写），等价 "H-2 1+"
p6 = Particle("alpha")       # 阿尔法粒子（He-4 2+）
p7 = Particle(26)            # 整数 = 原子序数（中性铁）
```

符号语法要点：电荷用 `n+`/`n-` 后缀（`Fe 2+` 是失去两个电子的离子，不是二价阴离子）；同位素写 `元素名-质量数`（`H-2`、`C-13`）；激发态可用 `element | level` 记法（如 `"Ca | level 2"` 表示中性钙第二激发态，物理属性如激发能可用 `excitation_energy` 查询）。解析失败抛 `InvalidParticleError`。

### 4.2 核心属性组

**基本物理量**（均返回 astropy Quantity 或 Python 数值）：

| 属性 | 含义 | 示例 |
|---|---|---|
| `symbol` | 规范符号 | `"Fe 5+"` |
| `charge` | 电荷（库仑） | `8.01e-19 C` |
| `charge_number` | 电荷数 Z（整数） | `5` |
| `mass` | 静止质量 | `9.22e-26 kg` |
| `mass_energy` | 静能（mc²） | J |
| `spin` | 自旋 | `-0.5`（电子） |
| `half_life` | 半衰期 | 中子 `881.5 s`（≈10.2 min） |
| `atomic_number` | 原子序数 | `26` |
| `mass_number` | 质量数 A | 同位素才有，元素上取常见同位素加权 |
| `neutron_number` / `electron_number` | 中子数 / 电子数 | 离子的 electron_number 已扣除电离 |
| `baryon_number` / `lepton_number` | 重子数 / 轻子数 | 守恒律检查用 |

**周期表与核素信息**：`element`（元素符号）、`isotope`（同位素符号）、`nucleus`（核符号）、`element_name`、`isotope_name`、`ionic_symbol`、`roman_symbol`（罗马数字电离态记法 `Fe V`）、`isotopic_abundance`（天然丰度）、`standard_atomic_weight`、`nuclide_mass`（纯核质量，不含电子）、`nuclear_binding_energy`（核结合能）、`ionization_energy`（逐级电离能）、`electron_binding_energy(level)`（逐壳层结合能）。2026.2.0 新增 `periodic_table` 命名元组与模块级 `periodic_table_block/category/group/period` 四个函数（第 6 章示例）。

**分类系统**：`categories` 返回集合，如 `{"ion", "charged", "nonneutral", "element", ...}`；`is_category("any_of", ["ion", "isotope"], exclude="charged")` 支持三段式过滤（`require`/`any_of`/`exclude`）；布尔快捷属性 `is_electron`、`is_ion`。分类体系是 `ParticleList` 和电离态集合做批量筛选的基础。

### 4.3 反应方法：ionize / recombine / antiparticle

```python
fe = Particle("Fe 4+")
fe5 = fe.ionize()            # → Particle("Fe 5+")，默认电离一级
fe3 = fe5.recombine(n=2)     # → Particle("Fe 3+")，复合两级
# inplace=True 可原地修改；电离能查询用 ionization_energy 属性

p = Particle("p+")
p.antiparticle               # → Particle("p-")，反质子
```

注意：`ionize` 不会自动算电离能消耗，它只做"计数 +1"的符号变换；能量账目要用 `ionization_energy` 或 `nuclear` 模块（4.5）自己算。

### 4.3.1 电离链的完整能量结算示例

逐级电离到全剥离的总能量账（制造全电离碳需要的电子伏数）：

```python
from plasmapy.particles import Particle
import astropy.units as u

total = 0 * u.eV
c = Particle("C")
for _ in range(6):
    total += c.ionization_energy.to(u.eV)   # 当前电离级的电离能
    c = c.ionize()
print(total)                                # ≈ 490 eV（碳的逐级电离能之和）
```

这笔账的仿真意义：靶材从冷态加热到全电离，电离能消耗占总吸收能量的比例在中 Z 元素上不可忽略（碳约 490 eV/核，而 100 eV 温度仅对应 ~12 eV/电子热能）——FLASH EOS（ionmix 表）内含这部分（内能含电离能贡献），自写简化模型时漏掉它会导致温升系统性偏高。`electron_binding_energy(level)` 提供逐壳层版本，用于能损计算中的壳层修正。

### 4.4 非实物粒子的三种建模

| 类 | 用途 | 特点 |
|---|---|---|
| `Particle` | 实物粒子（元素/同位素/离子/基本粒子） | 数据来自内置 JSON 库 |
| `CustomParticle(mass=..., charge=...)` | 自定义等效粒子（如混合物平均离子） | 任意质量/电荷组合，可带单位 |
| `DimensionlessParticle(mass=..., charge=...)` | 无量纲粒子（归一化模拟用） | 接受无量纲浮点 |

CH 泡沫等效离子示例：

```python
from plasmapy.particles import CustomParticle
import astropy.units as u

# C:H=1:1 的等效离子，Zbar=3.5
ch_mean = CustomParticle(mass=6.5 * u.u, charge=3.5 * u.C.to(u.e) * u.e)
# 等价写法：CustomParticle(mass=6.5*u.u, Z=3.5)  —— Z 参数接受无量纲电荷数
```

### 4.5 核反应能量学（nuclear.py 与 Particle 方法）

```python
from plasmapy.particles import nuclear_binding_energy, nuclear_reaction_energy

nuclear_binding_energy("Fe-56")   # 铁核总结合能 ≈ 4.39e-11 J
# D-T 聚变 Q 值
nuclear_reaction_energy("D + T --> alpha + n")   # ≈ 2.82e-12 J ≈ 17.6 MeV
```

反应式用字符串 + 箭头语法，`+` 连接反应物，`-->`（或 `->`）分隔两侧；质量亏损自动由 `Particle` 质量表核算，遵守重子数/电荷守恒（不守恒抛 `ParticleError`）。`mass_energy` 是 2026.2.0 新增的便捷函数（mc² 换算）。

### 4.6 分子与序列化

- `molecule("H2O")` 解析分子式为粒子组合（返回 `CustomParticle` 或 `Particle` 列表加权和），支持括号嵌套如 `"Ca(OH)2"`；
- 序列化：`p.json_dict` 输出 JSON 兼容字典；`json_dumps`/`json_dump` 序列化；`ParticleJSONDecoder`（或模块级 `json_loads_particle`）反序列化。跨进程传递粒子对象（如存入 HDF5 元数据）时使用。

### 4.7 ParticleList 批量操作

```python
from plasmapy.particles import ParticleList

pl = ParticleList(["e-", "p+", "Fe 5+"])
pl.mass           # Quantity 数组（kg）
pl.charge_number  # [-1, 1, 5]
pl.categories     # 每个粒子的 categories 列表
pl[0]             # Particle("e-")，支持索引与迭代
"e-" + "p+"       # Particle.__add__ 直接拼出 ParticleList
```

`ParticleList` 实现了 `__add__`/`__mul__`（重复拼接），并批量代理了常用属性，适合给 `formulary` 的多组分函数（如 `cold_plasma_permittivity_SDP` 的 `species` 参数）供料。

模块级还预置了常用粒子实例：`proton, electron, neutron, positron, deuteron, triton, alpha`，可直接 `from plasmapy.particles import electron` 使用。

### 4.8 常见报错

| 报错 | 原因 | 处置 |
|---|---|---|
| `InvalidParticleError` | 符号无法解析（拼写、非法电荷） | 检查 `Fe 5+`（合法）vs `Fe+5`/`Fe5+`（非法，电荷后缀前必须有空格）、同位素 `-` 写法 |
| `ChargeError` | 该操作需要确定电荷但粒子无电荷 | 先 `ionize()` 或显式给电荷 |
| `MissingParticleDataError` | 查询的属性对该粒子不存在（如电子的 atomic_number） | 用 `is_category` 先判类型 |

### 4.9 属性访问实战：一张表跑通 Particle

```python
from plasmapy.particles import Particle
import astropy.units as u

p = Particle("Fe 5+")

# —— 身份信息 ——
p.symbol, p.ionic_symbol, p.roman_symbol   # 'Fe 5+', 'Fe 5+', 'Fe VI'
p.element, p.element_name                  # 'Fe', 'iron'
p.atomic_number                            # 26
p.categories                               # {'ion', 'charged', 'element', 'nonneutral', ...}
p.is_ion, p.is_electron                    # True, False

# —— 质量与电荷 ——
p.mass.to(u.u)                             # ≈ 55.85 u（减 5 电子质量）
p.charge.to(u.C), p.charge_number          # 8.01e-19 C, 5
p.nuclide_mass.to(u.u)                     # 纯核质量（不含电子）
p.standard_atomic_weight                   # 55.845 u（天然同位素加权，仅中性元素有意义）

# —— 电子结构 ——
p.electron_number                          # 21（26-5）
p.ionization_energy                        # 第 6 级电离能（Fe 5+ → Fe 6+）
p.nuclear_binding_energy                   # 核结合能

# —— 反应操作 ——
p.ionize()                                 # → Particle("Fe 6+")
p.antiparticle                             # → Particle("Fe 5-")（反离子，数学对偶）

# —— 序列化 ——
p.json_dict["symbol"]                      # 'Fe 5+'，可 json.dumps 跨进程传递
```

两个容易误解的点：① `standard_atomic_weight` 只对**中性元素**有定义（同位素加权的天然丰度平均），对离子/同位素访问该属性返回的是元素基准值或 `MissingParticleDataWarning`，做离子质量相关计算请用 `mass` 或 `nuclide_mass`；② `ionize()` 返回新对象且默认不改原对象，`inplace=True` 才原地修改——在循环里做逐级电离链时注意接收返回值。

### 4.10 数据来源与精度说明

`Particle` 的数据来自包内置的 JSON 数据库（`particles/data/` 下 `_elements.json`、`_isotopes.json`、`_ionization_energy.json`），来源包括 NIST 原子权重表、AME 原子质量评估与 NIST 电离能表。这意味着：**离线可用**（不联网）、**随包版本冻结**（升级包才更新数据）；对质量精度要求极端的场景（如核物理量能学）应核对官方数据源版本。半衰期字段对部分不稳定核素缺失时抛 `MissingParticleDataWarning` 而非报错——返回 None 前先处理警告。

**官方文档**: <https://docs.plasmapy.org/en/stable/notebooks/getting_started/particles.html>

## 第 5 章 电离态建模：IonizationState / IonicLevel / IonizationStateCollection

### 5.1 单元素电离态 IonizationState

描述一种元素在各电离级之间的分布（如铁等离子体中 Fe⁰…Fe²⁴⁺ 各占多少）：

```python
from plasmapy.particles import IonizationState
import astropy.units as u

fe = IonizationState(
    "Fe",
    ionic_fractions=[0.01, 0.99] + [0.0] * 23,   # 长度 = Z+1 = 25
    T_e=1000 * u.K, n_e=1e17 * u.m**-3, tol=1e-3,
)
fe.Z_mean          # 平均电离度 ≈ 0.99
fe.n_e             # 电子数密度
fe.number_densities  # 各电离级的数密度数组
fe[5]              # IonicLevel：Fe 5+ 这一级
fe.is_electron_consistent   # ionic_fractions 推出的 n_e 与给定 n_e 是否一致
```

构造约束：`ionic_fractions` 长度必须等于 Z+1；也可传 `n_elements` 总密度代替 `T_e/n_e`。`tol` 控制电荷一致性容差，超差时可设 `tol=0` 强制豁免（等效忽略不一致）。

### 5.1.1 IonicLevel 与逐级访问模式

`IonizationState` 支持三种遍历写法，分别服务不同用途：

```python
fe = IonizationState("Fe", ionic_fractions=fracs, T_e=T, n_e=n)

# 写法一：索引访问（取单级做后续计算）
fe5 = fe[5]                 # IonicLevel：Particle("Fe 5+") + fraction + number_density
fe5.ion, fe5.fraction, fe5.number_density

# 写法二：迭代全部级（电离能/谱线清单生成）
for lvl in fe:              # IonicLevel 序列，从中性到裸核
    print(lvl.ion.symbol, f"{lvl.fraction:.3f}")

# 写法三：切片（只看高电离级，X 射线谱学常用）
hot = fe[16:]               # Fe 17+ 及以上（类氦及更裸）
```

`IonicLevel` 是轻量视图（不复制数据），修改其属性会同步回父对象——把它当"行游标"而非独立容器。

### 5.2 单电离级 IonicLevel

`fe[5]` 返回 `IonicLevel` 对象：绑定 `ion`（Particle）、`fraction`（丰度分数）、`number_density`。它是 IonizationState 的"一行视图"，自身不携带独立状态。

### 5.3 多元素集合 IonizationStateCollection

模拟 CH+Si+He 多层靶时，整块等离子体是多元素的电离态集合：

```python
from plasmapy.particles import IonizationStateCollection

states = IonizationStateCollection(
    {"H": [0.2, 0.8], "He": [0.9, 0.1]},
    n_elements=1e20 * u.m**-3 * np.array([0.6, 0.4]),  # 各元素总数密度
)
states.Z_mean        # 每元素平均电离度
states.n_e           # 总电子密度（各元素贡献求和）
states.ionic_fractions["H"]   # 按元素取分布
states["H"]          # 该元素的 IonizationState
```

支持 `abundances`（元素丰度归一化）参数；`normalize` 控制是否自动归一分数。`charge_consistency` 检查整体电中性一致性。这个类与 `formulary.ionization_balance`（第 13 章）衔接：后者给出 LTE 假设下的 $\bar Z$，可作为集合的初值来源。

### 5.5 电荷一致性与常见坑

电离态类最有价值的功能是**自动电中性检查**：`ionic_fractions` 给出的 $\bar Z$ 乘以各元素数密度，必须等于提供的 `n_e`（容差 `tol` 内）。实践中三个高频错误：

1. ionic_fractions 数组长度不对——必须是 Z+1（Fe 是 25 不是 24），且顺序从电离级 0（中性）排到 Z（裸核），顺序颠倒不会报错但全部后续计算皆错；
2. 混合物的 `n_elements` 与 `abundances` 口径混淆：前者是**各元素**核数密度（绝对量），后者是归一化丰度（相对量），二者只能给一个；
3. `tol=0` 的语义是"跳过检查"而非"零容差"——想严格校验应保持默认 tol 并让不一致时抛错。

### 5.6 与 ionmix/FLYCHK 数据的对接模式

生产场景中电离态分布来自表格（ionmix4 文件的 Zbar 列或 FLYCHK 输出），标准对接模式：

```python
# 伪代码：从表格到集合
states = IonizationStateCollection(
    {"C": zbar_to_fractions(Zbar_C), "H": zbar_to_fractions(Zbar_H)},
    n_elements=rho * np.array([X_C / A_C, X_H / A_H]) * u.kg / u.m**3,
)
assert states.charge_consistency   # 表格 Zbar 与电中性自洽性检查
```

这一步能把 ionmix 表格生成时的常见错误（ntemp/ndens 网格错位、Zbar 与 ye 不自洽）在进入 FLASH 之前拦截——比仿真后追查便宜得多。FLYCHK 的逐温度分布（非单一 Zbar）灌入时保留完整分数数组即可，类对非 LTE 分布不做任何假设。

### 5.4 与 FLYCHK/离子混排的分工

PlasmaPy 的电离态类只是**数据容器 + 一致性检查器**，不含碰撞辐射模型。真正的电离态分布需由 FLYCHK（CR 模型）或 ionmix 表提供，然后灌入 `IonizationStateCollection` 做后续计算（平均电离度、压强、不透明度耦合点）。官方教程 [Ionization states in an interplanetary coronal mass ejection](https://docs.plasmapy.org/en/stable/notebooks/particles/ace.html) 演示了用太阳风实测丰度构造集合的完整流程。

## 第 6 章 particles 高级主题与工具函数

### 6.1 atomic.py 函数族导读

约 25 个模块级函数，按用途分三组记忆即可，不必逐个背：

**查性质**（传 ParticleLike，返回数值/Quantity）：
`atomic_number`、`mass_number`、`charge_number`、`standard_atomic_weight`、`particle_mass`、`electric_charge`、`half_life`、`nuclear_binding_energy`、`reduced_mass`（两粒子约化质量）、`isotopic_abundance`。

**做转换**：
`ionic_levels`（元素 → 从中性到全电离的 Particle 序列）、`particle_symbol` ↔ `atomic_symbol` ↔ `element_name` ↔ `ionic_symbol` ↔ `isotope_symbol`（符号互转五件套）。

**做判断/筛选**：
`is_stable`、`known_isotopes`/`stable_isotopes`/`common_isotopes`（元素的全部/稳定/常见同位素列表，可选传质量数）。

2026.2.0 新增的周期表函数：

```python
from plasmapy.particles.atomic import periodic_table_block, periodic_table_category, periodic_table_group, periodic_table_period

periodic_table_block("Fe")        # 'd'（注意：返回短名 'd'，不是 'd-block'）
periodic_table_category("Fe")     # 'transition metal'
periodic_table_group("Fe")        # 8
periodic_table_period("Fe")       # 4
```

`stopping_power`（新 API，依赖 h5py 读 NIST ASTAR 数据）：目前仅支持质子与 α 粒子在指定材料（如 "Al"、"water"）中的阻止本领，返回质量阻止本领（MeV cm²/g），做诊断箔/探测器设计时有用。

### 6.2 particle_input 装饰器：用户视角

`@particle_input` 是全库的粘合剂——它把函数的 `ParticleLike` 参数自动转换为 `Particle`/`CustomParticle`/`ParticleList` 对象。用户通常不直接写它，但会在两类场景遇到：

1. **报错信息**：传了非法粒子字符串时，异常链最深处是 `particle_input` 抛出的 `InvalidParticleError`；
2. ⚠ **`z_mean` 参数已弃用**（2026.2.0 起 `particle_input(z_mean=...)` 发 DeprecationWarning）：过去用它在装饰层注入平均电离度，现在应在调用处显式传 `z_mean=` 给各 formulary 函数（如 `Coulomb_logarithm`）。

### 6.3 异常与警告体系速查

| 异常/警告 | 触发场景 |
|---|---|
| `ParticleError` | particles 基异常 |
| `InvalidParticleError` | 符号解析失败 |
| `ChargeError` | 需要电荷信息而缺失 |
| `InvalidElementError` / `InvalidIonError` / `InvalidIsotopeError` | 类别不匹配（对电子取 atomic_number 等） |
| `MissingParticleDataError` / `Warning` | 数据库中无该项（半衰期未知等） |
| `UnexpectedParticleError` | 传入类型意外（如传了 ParticleList 到单粒子参数） |

这些类都继承自 `plasmapy.utils.exceptions.PlasmaPyError`（第 32 章统一讲解），可用 `except PlasmaPyError` 兜底。

### 6.4 函数族的批量使用模式

atomic 函数全部支持 ParticleLike 与数组化输入的组合，推荐三种批量模式：

```python
from plasmapy.particles import (particle_mass, reduced_mass, ionic_levels,
                                isotopic_abundance, common_isotopes)
import astropy.units as u

# 模式一：符号列表 → 属性数组
species = ["e-", "p+", "C 3+", "He+1"]
masses = [particle_mass(s) for s in species]        # 4 个 Quantity

# 模式二：电离级序列生成（输运/电离链的标准起点）
levels = ionic_levels("C")          # C⁰…C⁶⁺ 的 Particle 迭代
for p in levels:
    print(p.symbol, p.charge_number)

# 模式三：约化质量（双粒子碰撞系数的输入）
mr = reduced_mass("e-", "p+")       # ≈ m_e（悬殊质量对）
```

`ionic_levels` 与第 5 章 `IonizationState` 的内部结构一致——把一种元素的全部电离级当作粒子序列处理，是从"单粒子思维"切换到"电离态思维"的桥梁。

### 6.5 particle_input 的自定义函数用法

自写物理函数想让参数自动获得粒子解析能力，只需一个装饰器：

```python
from plasmapy.particles import particle_input
from plasmapy.particles.particle_class import ParticleLike
import astropy.units as u

@particle_input
def my_plasma_frequency(n: u.Quantity[u.m**-3], particle: ParticleLike) -> u.Quantity[u.rad / u.s]:
    """particle 参数自动变成 Particle 对象，非法符号在入口被拦截。"""
    return (n * particle.charge**2 / (particle.mass * u.eps0)).to(u.rad / u.s) ** 0.5 * (-1) ** 0.5
```

价值与 `validate_quantities` 对称：`validate_quantities` 管单位，`particle_input` 管粒子语义——两者组合后自定义函数获得与 PlasmaPy 内置函数同级的输入安全。注意 ⚠ 前文所述 `z_mean` 装饰参数已弃用，平均电离度请走函数普通参数。

---

# 第三篇 公式库 formulary

`plasmapy.formulary` 是 PlasmaPy 的核心板块，收录了 NRL Plasma Formulary 及经典文献（Braginskii 1965、Spitzer-Härm、Stix 1992、Gericke-Murillo-Schlanges 2002 等）中的解析公式。设计上有三条统一约定，先立后破：

1. **单位校验**：几乎所有函数都由 `validate_quantities` 装饰（第 32 章详解），入参出参全是 `Quantity`，温度参数支持 eV 直接传入；
2. **别名体系**：每个函数注册一个短别名（`plasma_frequency` → `wp_`，`Debye_length` → `lambdaD_`），公式语境下代码更紧凑，第 34 章汇总；
3. **lite 版本**：核心高频函数提供 `*_lite` 无单位快速版，见第 34 章。

各函数与物理公式的逐一对照见姊妹文档《相关公式接口速览.md》，本篇侧重**参数语义、适用条件、示例与坑**。官方教程总览见 [examples#formulary](https://docs.plasmapy.org/en/stable/examples.html#formulary)。

## 第 7 章 特征频率

### 7.1 等离子体频率 plasma_frequency

等离子体振荡角频率，是全库最基础的量之一：

```python
from plasmapy.formulary import plasma_frequency

wp_e = plasma_frequency(n_e=1e20 * u.m**-3)          # 默认电子，角频率 rad/s
wp_e_hz = plasma_frequency(n=1e20 * u.m**-3, particle="e-", to_hz=True)  # Hz
wp_i = plasma_frequency(n=1e20 * u.m**-3, particle="p+")
```

参数语义：`n` 是**该种粒子**的数密度（不是总密度）；`particle` 指定种类（默认电子）；`to_hz=True` 时返回 $f=\omega/2\pi$。返回的是**角频率**——与激光频率比较时注意三倍频 0.351 μm 对应 $\omega\approx5.37\times10^{15}$ rad/s，密度超过临界密度（第 10 章）后 $\omega_{pe}>\omega$ 即截止。别名 `wp_`。

典型用法：对 FLASH 输出的电子密度场做逐点 $\omega_{pe}$ 计算，标记激光传播区域与屏蔽区域。

### 7.2 回旋频率 gyrofrequency

$$\omega_c = \frac{|q|B}{m}$$

```python
from plasmapy.formulary import gyrofrequency

wc = gyrofrequency(B=5 * u.T, particle="e-")             # rad/s
wc_hz = gyrofrequency(B=5 * u.T, particle="e-", to_hz=True, signed=False)
```

要点：`signed=True` 可保留带符号角频率（区分正负电荷回旋方向）；`Z` 参数可注入平均电离度（用于等效离子）。与 `gyroradius`（第 8 章）配对使用得到回旋运动完整描述。

### 7.2.1 回旋频率与偏振的选择定则

回旋频率不只是"转多快"，它还是**波的偏振选择定则**的锚点：平行于 B 传播的电磁波分解为左旋（L）与右旋（R）两支（第 11 章 LRP 表示），其中与电子回旋同向的一支在 $\omega\to\omega_{ce}$ 处共振——电子回旋共振加热（ECRH）与微波在磁化等离子体中的吸收窗口即由此而来；离子的对应共振在 $\omega_{ci}$。判读方法：比较入射波频率与 $\omega_{ce}/\omega_{ci}$ 的相对位置（用本章函数），在 CMA 图上定位，即可预判"这束波会在哪层被吸收"——这是任何"激光/微波 + 磁场"实验设计的第一步纸面检查。

### 7.3 杂化频率与 Buchsbaum 频率

```python
from plasmapy.formulary import lower_hybrid_frequency, upper_hybrid_frequency, Buchsbaum_frequency

f_lh = lower_hybrid_frequency(B=2.5 * u.T, n_i=1e18 * u.m**-3, ion="p+")
f_uh = upper_hybrid_frequency(B=2.5 * u.T, n_e=1e18 * u.m**-3)
f_bb = Buchsbaum_frequency(B=2.5 * u.T, n_i=1e18 * u.m**-3, ion="p+", z_mean=1)
```

- 上杂化 $\omega_{uh}=\sqrt{\omega_{pe}^2+\omega_{ce}^2}$：垂直传播电磁波共振点；
- 下杂化 $\omega_{lh}\approx\sqrt{\omega_{ci}\omega_{ce}}$（高密度修正含离子等离子体频率）：ICRF 加热、离子波共振的基础；
- Buchsbaum（双离子杂化）频率：两种离子组分存在时的共振（如 D-T 混合等离子体），签名要求给出主离子 `ion`、其数密度、以及第二离子信息（`ion2`/`z_mean`/`abundance` 等，以本地 docstring 为准）。

### 7.3.1 杂化频率的仿真应用场景

杂化频率在 ICF 仿真中最实际的用途是**波加热与反常输运的判据**：激光等离子体中参量不稳定性（SRS/SBS）产生的静电波频率落在电子等离子体频率附近，而双等离子体衰变（TPD）机制恰好要求 $\omega_0\approx2\omega_{pe}$ 附近的密度区间（四分之一临界密度面）——判断 TPD 是否可能发生，只需比较激光频率、2×上杂化频率与局域密度处频率族的相对位置，全部可由本章函数计算。对 0.351 μm 驱动、CH 靶的常规参数，TPD 区在 $n_e\approx n_c/4\approx2.3\times10^{21}\,\mathrm{m^{-3}}$——把这类"频率几何"检查固化进场景文档，是预防超热电子意外产生的廉价保险。

### 7.4 常见报错与提示

- 传裸数值（忘乘单位）→ `UnitConversionError`，报错文本会列出期望单位；
- `particle` 传混合物名字符串（如 `"CH"`）→ 不支持，应先用 `CustomParticle` 构造等效离子；
- 频率类函数返回角频率导致与 Hz 差 $2\pi$——常见于与激光参数比较，建议统一 `to_hz=True` 或统一 rad/s。

### 7.5 场景应用：激光入射前的频率账本

三倍频激光（0.351 μm）打 CH 靶时，先算清三笔频率账：① 激光角频率 $\omega_0=2\pi c/\lambda\approx5.37\times10^{15}$ rad/s；② 峰值电子密度（固体 CH 约 $5\times10^{29}$ m⁻³）处的 $\omega_{pe}\approx4\times10^{16}$ rad/s——远大于 $\omega_0$，故激光只能在临界面附近被吸收、无法进入固体密度区，这正是 FLASH 激光能量沉积按临界密度截断的物理根源；③ 电子回旋频率在外加场为零时无意义，但自生磁场（百 T 量级）下 $\omega_{ce}$ 可与下杂化频率相比，影响输运各向异性。这三笔账都能用第 7 章四个函数 + `critical_density` 一次算清，建议固化为脚本放在仿真前置检查中。

**官方文档**: [ITER 参数分析](https://docs.plasmapy.org/en/stable/notebooks/formulary/iter.html)、[地球磁层等离子体参数](https://docs.plasmapy.org/en/stable/notebooks/formulary/magnetosphere.html) 演示了频率族的批量用法。

## 第 8 章 特征长度

### 8.1 Debye 长度 Debye_length

$$\lambda_D=\sqrt{\frac{\varepsilon_0 k_B T_e}{n_e e^2}}$$

```python
from plasmapy.formulary import Debye_length

lambda_D = Debye_length(T_e=100 * u.eV, n_e=1e20 * u.m**-3)   # ≈ 7.43e-6 m
```

物理意义：静电屏蔽长度，也是"准中性成立的尺度下限"与 Coulomb 对数中 $b_{\max}$ 的取值。FLASH 中网格尺度 $\Delta x \ll \lambda_D$ 是显式 PIC 类方法的前提；对辐射流体（FLASH）则天然满足。参数只有 `T_e` 与 `n_e`（电子 Debye 长度；离子 Debye 长度在 2026.2.0 中未单独开函数，需要时用 `T_i`、离子质量自查公式或用 `Debye_number` 间接构造）。别名 `lambdaD_`。

### 8.2 回旋半径 gyroradius

$$r_c=\frac{v_\perp}{\omega_c}$$

```python
from plasmapy.formulary import gyroradius

r1 = gyroradius(B=5 * u.T, T_e=1e6 * u.K, particle="e-")            # 热速度版
r2 = gyroradius(B=5 * u.T, Vperp=1e5 * u.m / u.s, particle="p+")     # 显式速度版
r3 = gyroradius(B=5 * u.T, T=1e6 * u.K, particle="e-",
                relativistic=True)                                   # 相对论修正
```

`Vperp` 与 `T` 二选一：给了速度就用速度，否则取热速度；`relativistic=True` 时速度先过 `RelativisticBody`（第 15 章）换算。别名 `rc_`/`rhoc_`。这是磁化输运、Braginskii 磁化参数 $\chi=\omega_c\tau$ 的空间尺度构件。

### 8.3 惯性长度 inertial_length

$$d = c/\omega_p$$

```python
from plasmapy.formulary import inertial_length

d_e = inertial_length(n=1e20 * u.m**-3, particle="e-")   # 电子趋肤深度 c/wp_e
d_i = inertial_length(n=1e20 * u.m**-3, particle="p+")
```

即电磁场对等离子体"穿透"的特征深度，双流体模拟中离子惯性长度决定 Hall 项重要尺度；无碰撞磁重联厚度取 $d_i$ 量级。别名 `cwp_`。

### 8.4 长度尺度族全景与"尺度阶梯"

把全库长度类特征量排成一张尺度阶梯，读物理问题的能力立刻清晰（以 $n_e=10^{21}\,\mathrm{m^{-3}}$、$T_e=100$ eV、$B=50$ T 的典型 ICF 冕区参数为例）：

| 尺度 | 公式量级 | 物理含义 |
|---|---|---|
| 电子 de Broglie 热波长 | $\lambda_{db}\sim 10^{-10}$ m | 量子衍射下限（简并判据） |
| 粒子间距（Wigner-Seitz） | $a\sim 6\times10^{-11}$ m | 强耦合判据的长度单位 |
| 电子回旋半径 | $r_{ce}\sim 10^{-6}$ m | 磁化电子输运的各向异性尺度 |
| Debye 长度 | $\lambda_D\sim 7\times10^{-8}$ m | 静电屏蔽；$b_{\max}$ |
| 离子回旋半径 | $r_{ci}\sim 10^{-4}$ m | 离子磁化输运 |
| 电子惯性长度 | $d_e\sim 5\times10^{-7}$ m | 无碰撞电磁穿透（趋肤） |
| 离子惯性长度 | $d_i\sim 2\times10^{-5}$ m | Hall 效应/重联厚度 |
| 系统尺度 L | mm–cm | Knudsen 数的分母 |

读法：$\lambda_D\ll L$ 准中性成立；$r_{ce}\ll r_{ci}$ 意味电子先磁化；$d_i$ 与 $L$ 之比决定 Hall MHD 是否必要；$\lambda_{db}$ 与 $a$ 之比标记量子效应（衔接第 14 章）。这张表就是"用 PlasmaPy 长度族读 regime"的全部内容——四个函数、一次脚本、一张阶梯图。

### 8.4 长度族的组合检查

ICF 参数核验的组合拳（对应 demo_01 的核心逻辑）：

```python
import astropy.units as u
from plasmapy.formulary import Debye_length, inertial_length, plasma_frequency

n_e, T_e = 1e21 * u.m**-3, (300 * u.eV).to(u.K, equivalencies=u.temperature_energy())
lambda_D = Debye_length(T_e, n_e)         # ~5e-8 m：远小于网格，准中性良好
d_e      = inertial_length(n_e, "e-")     # ~5e-7 m
wp_e     = plasma_frequency(n_e)          # ~5.6e13 rad/s：与激光 5.4e15 相比 wp/ω~0.01
```

## 第 9 章 特征速度

### 9.1 thermal_speed：一种分布，三种速度

Maxwellian 分布可定义"最概然速度"（most probable）、"平均速度"（mean）与"均方根速度"（rms），三者相差常数因子。`thermal_speed` 用 `method`（或历史参数 `ndim`）区分：

```python
from plasmapy.formulary import thermal_speed

v_rms   = thermal_speed(T=1e6 * u.K, particle="e-")                    # 默认 rms
v_mp    = thermal_speed(T=1e6 * u.K, particle="e-", method="most_probable")
v_mean  = thermal_speed(T=1e6 * u.K, particle="e-", method="mean")
```

三个约定要记住：① 默认返回 **rms**；② `method` 取 `"most_probable"`/`"mean"`/`"rms"`（旧 API 用 `ndim=1,2,3` 对应，已收敛到字符串写法）；③ 它与 `Maxwellian_velocity_3D` 的 $v_{th}$ 参数一致（第 12 章），联动时保持同一 method 免得差 $\sqrt{2}$ 因子。lite 版 `thermal_speed_lite` 接受裸数组。别名 `vth_`。

官方教程 [Thermal Speed](https://docs.plasmapy.org/en/stable/notebooks/formulary/thermal_speed.html) 用图像展示了三种定义在分布曲线上的位置，强烈建议过一遍。

### 9.5 速度尺度组合：判断物理 regime 的标尺

速度族真正的价值在于**相互比较**：电子热速度 $v_{th,e}$ 与离子声速 $c_s$ 之比 $\sim\sqrt{m_i/m_e Z}$（约 43 倍，氢）说明电子总能瞬时响应——FLASH 双温模型（tele 与 tion 分开）的合理性根源；Alfvén 速度与声速之比决定快/慢磁声波性质（$\beta\ll1$ 时快波≈Alfvén 波）；$v_{th,i}$ 与离子回旋半径组合给出有限拉莫尔效应判据 $k\rho_i$（衔接第 22 章 KAW）。把这些比值做成常量函数放在工具库里，比每次临时推导更不易错。

### 9.6 报错与边界

- `thermal_speed` 传负温度 → `ValueError`（`check_values` 拦截）；
- `ion_sound_speed` 的 `gamma_e/gamma_i` 传 0 或负值 → 无物理意义，不会显式报错但结果荒谬，务必显式声明；
- `kappa_thermal_speed` 要求 $\kappa>3/2$：kappa 分布的 rms 速度在 $\kappa\le3/2$ 时发散，传小值直接抛错而非警告。

---

### 9.2 Alfven_speed

$$v_A=\frac{B}{\sqrt{\mu_0 \rho}}$$

```python
from plasmapy.formulary import Alfven_speed

vA = Alfven_speed(B=2.5 * u.T, density=1e-6 * u.kg / u.m**3)
```

注意参数是**质量密度** `density`（kg/m³），不是数密度——这是速度类函数中最常犯的错。数密度场景先用 `mass_density`（第 10 章）换算。别名 `va_`。MHD 波（第 21 章）、磁压与动压比较（$\beta$，第 18 章）都基于它。

### 9.2.1 Alfvén 速度的三种误用与纠正

1. **数密度直传**：`Alfven_speed(B=5*u.T, density=1e20*u.m**-3)`——单位校验会拦下（m⁻³ ≠ kg/m³），但有人会"顺手"去掉单位绕过校验，结果是荒谬数值；正确链路：`rho = mass_density(1e20*u.m**-3, "p+")` 再传入；
2. **多组分总密度**：混合等离子体的 $\rho$ 是**全部**组分（含电子）质量密度之和——电子贡献常可忽略（$\sim m_e/m_i$），但高 Z 杂质（如钨）混入百分之几即可改变 $\rho$ 数个百分点，进而影响 $\beta$ 判读；
3. **相对论修正**：$v_A$ 超过 $c$ 的参数区（超强场低密度）物理上不存在——超相对论 Alfvén 速度饱和于 $c$，库内非相对论公式会"算出"超光速值，此时应检查参数而非相信输出。

### 9.3 ion_sound_speed

$$c_s=\sqrt{\frac{\gamma_e Z k_B T_e + \gamma_i k_B T_i}{m_i}}$$

```python
from plasmapy.formulary import ion_sound_speed

cs = ion_sound_speed(T_e=100 * u.eV, T_i=10 * u.eV,
                     ion="p+", z_mean=1, gamma_e=1, gamma_i=3)
```

要点：绝热指数默认 `gamma_e=1`（等温电子）、`gamma_i=3`（一维绝热离子）——**这与很多教科书默认不同**，做 IAW 色散对比时务必显式声明；`z_mean` 注入平均电离度，混合物用 `CustomParticle` 当 `ion` 传入。别名 `cs_`。

### 9.4 kappa_thermal_speed：非麦氏尾的速度尺度

```python
from plasmapy.formulary import kappa_thermal_speed

vth_k = kappa_thermal_speed(T=1e6 * u.K, particle="e-", kappa=4)
```

kappa 分布（第 12 章）的 rms 速度尺度，$\kappa\to\infty$ 时退化为 Maxwellian rms。要求 $\kappa>3/2$（分布可归一化的下限），传更小值抛错。

## 第 10 章 密度与漂移速度

### 10.1 critical_density 与 mass_density

```python
from plasmapy.formulary import critical_density, mass_density

n_c = critical_density(omega=5.37e15 * u.rad / u.s)     # 0.351 μm 激光 → ~9e27 m^-3
rho = mass_density(density=1e20 * u.m**-3, particle="p+")     # 数密度 → 质量密度
```

`critical_density(omega)` 从角频率直接算 $n_c=m_e\varepsilon_0\omega^2/e^2$；与激光波长的换算（波长 → 角频率）用 `formulary.laser.em_angular_frequency`（第 15 章）。`mass_density` 是数密度 × 粒子质量，反向需求（质量密度 → 数密度）用 `rho / particle_mass`，别名 `rho_`。

### 10.1.1 密度口径的全库一致性

密度类参数在 PlasmaPy 各接口间的口径差异值得单独一张对照表（这是实际使用中引发结果错误最多的一组）：

| 接口 | 参数 | 期望口径 |
|---|---|---|
| `plasma_frequency`/`inertial_length` | `n` | 物种**数密度**（m⁻³） |
| `Debye_length`/`Debye_number` | `n_e` | 电子数密度 |
| `Alfven_speed` | `density` | **总质量密度**（kg/m³） |
| `beta` | `n` | 数密度（m⁻³） |
| `thermal_pressure` | `n` + `T` | 数密度与温度（无 species） |
| `mean_free_path`/碰撞频率类 | `n_e` | 场粒子数密度 |
| `Saha` | `n_g` | **基态中性原子**数密度（第 13.3 节） |

规律：频率/长度族用数密度，MHD 量（Alfvén、β）用质量密度。把这张表贴在项目工具库的 README 里，密度口径错误基本绝迹。

### 10.2 漂移速度三件套（drifts.py）

```python
from plasmapy.formulary import ExB_drift, force_drift, diamagnetic_drift
import astropy.units as u

v_exb = ExB_drift(E=1e4 * u.V / u.m, B=5 * u.T)          # E×B 漂移
v_f   = force_drift(F=1e-19 * u.N, B=5 * u.T, particle="e-")  # 广义力漂移（如重力）
v_dia = diamagnetic_drift(T=1e6 * u.K, grad_p=1e-5 * u.Pa / u.m, B=5 * u.T,
                          particle="p+", Z=1)             # 抗磁漂移
```

物理背景：带电粒子在垂直磁场方向受到任何力（电场力、重力、压力梯度力）都会产生与力、磁场都垂直的漂移 $\mathbf{v}_d=\frac{\mathbf{F}\times\mathbf{B}}{qB^2}$，且**与电荷符号无关的 E×B 漂移不产生电流**（正负粒子同向漂移），而抗磁漂移正负相反、等效出抗磁电流。官方教程 [Physics of the E×B drift](https://docs.plasmapy.org/en/stable/notebooks/formulary/ExB_drift.html) 有完整推导。签名中 `grad_p` 是压力梯度（Pa/m），`Z` 用于等效离子。

### 10.3 场景应用：临界面附近的参数核对

`critical_density` 与 FLASH 激光配置的三个核对点：① 材料临界密度（如 0.351 μm 对 CH 泡沫）决定激光沉积位置——仿真域内密度超过 $n_c$ 的区域对激光不可见；② 转换为临界**面**的位置需要密度剖面，一维场景用 `mass_density` 把 ionmix 的数密度场换成质量密度场，与 EOS 的输入口径对齐；③ 多倍频（基频 1.053 μm、二倍频 0.527 μm、三倍频 0.351 μm）的 $n_c$ 依次相差 4 倍与 9 倍——用 `critical_density(em_angular_frequency(lam))` 一行循环即可生成对照表，写进场景文档。

## 第 11 章 介电张量

### 11.1 冷等离子体介电张量：SDP 与 LRP 两种表示

```python
from plasmapy.formulary import cold_plasma_permittivity_SDP, cold_plasma_permittivity_LRP

B = 2.35 * u.T
species = ["e-", "p+"]
n = [1e18 * u.m**-3, 1e18 * u.m**-3]
omega = 4e10 * u.rad / u.s

result = cold_plasma_permittivity_SDP(B=B, species=species, n=n, omega=omega)
result.sum, result.difference, result.plasma   # StixTensorElements 属性
resultLRP = cold_plasma_permittivity_LRP(B=B, species=species, n=n, omega=omega)
resultLRP.right, resultLRP.left, resultLRP.plasma  # RotatingTensorElements 属性
```

⚠ **属性名不是 S/D/P、L/R/P**：2026.2.0 的 `StixTensorElements` / `RotatingTensorElements` 暴露的是组合量，需要自己反解：

- **SDP**：`.plasma` = P；`.sum` = R + L = 2S；`.difference` = R − L = 2D。要单独拿 S、D：$\mathrm S = \texttt{.sum}/2$，$\mathrm D = \texttt{.difference}/2$；
- **LRP**：`.right` = R，`.left` = L，`.plasma` = P；
- 互推关系：$R = S + D$，$L = S - D$，$P$ 两表示共用。

- **SDP 表示**：平行 B 取 P，垂直取 S、D，适合讨论共振/截止；
- **LRP 表示**：左旋/右旋圆偏振分解（`.right`=R、`.left`=L），适合讨论波的偏振吸收（ECR/ICR 共振）；
- 多组分直接用 `species` 列表 + 密度列表，等效离子用 `CustomParticle`。

张量元是 Stix 色散求解器（第 21 章）的输入；两者配对构成"冷等离子体波传播分析"完整工具链。官方教程 [Cold Magnetized Plasma Dielectric Permittivity Tensor](https://docs.plasmapy.org/en/stable/notebooks/formulary/cold_plasma_tensor_elements.html) 绘制了 CMA 图。

### 11.1.1 三个张量元的物理读法

拿到 $S, D, P$ 之后，读波物理的口诀：

- **P（平行元）**：$P=1-\omega_{pe}^2/\omega^2$——与磁场无关的纵向响应，$P=0$ 即等离子体截止（对电磁波传播的"密度墙"）；
- **S（垂直元）**：$S=\frac12(R+L)$——垂直传播的横向响应，$S=0$ 给出杂化共振层；
- **D（差元）**：$D=\frac12(R-L)$——左右旋不对称度，正负号决定波的偏振面旋转方向（法拉第旋转的基础）；$D\to0$（高密度或弱场）时波偏振退化为线偏振。

CMA 图（Clemmow-Mullaly-Allis 图）正是以 $\omega_{ce}/\omega$ 与 $\omega_{pe}^2/\omega^2$ 为坐标、按 S/D/P 零点分区的波传播"地图"——每个区域标注该 (B, n) 下允许的波分支。做激光在磁化等离子体中传播的快速判断时，先在 CMA 图上定位参数点，再决定是否需要完整的 `stix` 求解。

### 11.1.2 等效离子的张量元实践

激光等离子体的电子/离子 often 以平均电离度 $\bar Z$ 表示（如 CH 的 $\bar Z=3.5$）：`species` 传 `CustomParticle(Z=3.5, mass=...)`（第 4.4 节构造）+ 对应数密度即可，函数内部只消费 $q/m$ 与密度。注意：两种离子组分（如 D-T）不能合并成一个"等效离子"再算 Buchsbaum/双离子共振——凡是共振结构依赖离子种类的物理，必须保留各自组分分别传入。

### 11.2 Maxwellian 1D 介电函数 permittivity_1D_Maxwellian

$$\varepsilon(k,\omega)=1+\frac{1}{k^2\lambda_D^2}\left[1+\zeta Z(\zeta)\right],\quad \zeta=\frac{\omega}{\sqrt{2}k v_{th}}$$

```python
from plasmapy.formulary import permittivity_1D_Maxwellian

eps = permittivity_1D_Maxwellian(omega=1e11 * u.rad / u.s, kWave=1e4 * u.rad / u.m,
                                 T=1e6 * u.K, n=1e20 * u.m**-3, particle="e-")
```

这是**动理学**（热等离子体）介电函数，内部调用等离子体色散函数 $Z(\zeta)$（第 20 章），复数输出自动携带朗道阻尼信息。与冷等离子体介电（无碰撞阻尼为零）对照使用可演示朗道阻尼的来源。lite 版 `permittivity_1D_Maxwellian_lite` 接受裸数组。

### 11.3 从介电函数到色散关系：一张逻辑链

本库波动物理的四层结构值得整体记住：**张量元**（`cold_plasma_permittivity_SDP/LRP`，给定 B 与组分）→ **冷等离子体色散关系**（`stix`，张量元代数化）→ **双流体含温色散**（`two_fluid`/`hollweg`，加入压强）→ **动理学色散**（`kinetic_alfven` 与自写 $\varepsilon(k,\omega)$，加入朗道阻尼）。每一层只在自己假设的范围内可信：冷等离子体层忽略温度（ICF 冕区高场强下够用），双流体层缺动理学阻尼，动理学层最完整但求解最贵。做波分析时先问"我的场景落在哪一层"，再选接口——跳层使用（如用冷等离子体结果讨论阻尼）是最常见的系统性错误。

## 第 12 章 分布函数

### 12.1 Maxwellian 速度分布 vs 速率分布

`distribution.py` 提供 **6 个** Maxwellian 分布函数，命名规则=`分布名_维度_变量类型`：

| 函数 | 自变量 | 说明 / 归一化 |
|---|---|---|
| `Maxwellian_1D(v, T, particle, v_drift=0, vTh=nan)` | 一维速度分量 | 一维速度概率密度，$\int f\,dv=1$ |
| `Maxwellian_speed_1D(v, T, particle, v_drift=0, vTh=nan)` | 一维速率 $\lvert v\rvert$（$v\ge0$） | 一维速度空间，$\int f\,dv=1$ |
| `Maxwellian_speed_2D` / `3D` | 速率 | 含相空间体积元 $2\pi v\,dv$ / $4\pi v^2 dv$ |
| `Maxwellian_velocity_2D` / `3D` | 速度矢量（数组逐分量） | $\int f\,d^2v$ / $d^3v$ |

⚠ 注意：**没有 `Maxwellian_velocity_1D`**（一维只有 `Maxwellian_1D` 与 `Maxwellian_speed_1D`）；velocity 版从 2D 起才有。

```python
from plasmapy.formulary import Maxwellian_velocity_3D, Maxwellian_speed_3D
import numpy as np
import astropy.units as u

T, particle = 1e6 * u.K, "e-"
v = np.array([1e6, 0, 0]) * u.m / u.s
f_vec = Maxwellian_velocity_3D(v=v, T=T, particle=particle, V_drift=[0,0,0] * u.m/u.s)
speed = np.linspace(0, 1e7, 500) * u.m / u.s
f_spd = Maxwellian_speed_3D(speed, T=T, particle=particle)   # 画速度分布谱用这个
```

**最大的坑**：velocity 分布的积分元是 $d^3v$，speed 分布的积分元是 $4\pi v^2 dv$——同一物理状态两者数值差 $4\pi v^2$ 因子。画能谱用 speed 版；做速度空间的矩（如计算通量）用 velocity 版。`V_drift` 支持漂移麦氏（各向异性漂移速度）。

### 12.1.1 各维度的适用场景与降维检查

6 个函数的维度选择不是任意的：**物理问题的对称性决定维度**——

- 一维模型（1D 速率）：FLASH 1D 激光-CH 基准这类沿激光轴的问题，横向自由度被积掉，直接用 `Maxwellian_speed_1D`（或 `Maxwellian_1D`）；
- 二维（速度/速率）：轴对称问题（丝阵 Z 箍缩、圆柱靶）；
- 三维：全对称参数空间、以及需要与解析矩（密度/压强）对账的场合。

降维自查法：对 3D 分布按 $v_y=v_z=0$ 切片，应与 1D 分布在相同 $v_x$ 处取值一致（差一个归一化因子）；这一致性检查可写成单元测试——曾经有项目因把 speed 分布错当 velocity 分布用于矩计算，压强错 $4\pi v^2$ 倍而全链路报废，几分钟的单测即可杜绝。

### 12.2 kappa 分布：超热尾建模

```python
from plasmapy.formulary import kappa_velocity_1D, kappa_velocity_3D

f = kappa_velocity_1D(v=1e6 * u.m / u.s, T=1e6 * u.K, kappa=4, particle="e-")
```

kappa 分布 $f_{\kappa}(v)\propto(1+v^2/(\kappa\theta^2))^{-(\kappa+1)}$ 用于空间等离子体与激光等离子体超热电子尾。约束 $\kappa>3/2$；$\kappa\to\infty$ 恢复 Maxwellian。激光等离子体中参量不稳定性（SRS）产生的超热电子常用 $\kappa=2\sim5$ 拟合。官方教程 [1D Maxwellian distribution function](https://docs.plasmapy.org/en/stable/notebooks/formulary/distribution.html) 对比了两族分布曲线。

### 12.3 分布函数的三个用途

1. **给色散关系供料**：动理学介电函数（第 11 章）与色散求解器（第四篇）的全部积分都定义在分布上——换分布（Maxwellian → kappa）就改变了阻尼率，这是"超热尾增强参量不稳定性"表述的数学出处；
2. **合成诊断谱**：Thomson 散射谱的形状由电子/离子分布的 Fourier 变换决定（第 29 章 `spectral_density` 内部即此逻辑）；非麦氏偏离会直接改变 EPW/IAP 线形，拟合时若发现残差系统偏离，首先怀疑非麦氏修正；
3. **算矩**：用 `Maxwellian_velocity_3D` 的解析矩（零阶=密度、一阶=漂移、二阶=压强张量）核对自写流体方程的守恒性——这也是检验 `ClassicalTransport` 输入自洽性的方式。

### 12.4 数值注意事项

分布函数在 $|v|\gg v_{th}$ 处指数级衰减，直接用 float64 算双 Maxwellian 的大速度差项会下溢——需要尾部分布精确值时改用对数空间采样或解析公式；kappa 分布的归一化常数含 Gamma 函数（大 $\kappa$ 数值稳定），但 $\kappa$ 逼近下限 1.5 时分布变"胖尾"，图轴建议用 log-log 才能看清尾行为。

## 第 13 章 电离平衡

### 13.1 Saha 方程 Saha

LTE 假设下相邻两级电离的丰度比：

$$\frac{n_{j+1} n_e}{n_j}=\frac{2}{\lambda_{db}^3}\frac{U_{j+1}}{U_j}\exp\left(-\frac{E_I}{k_B T_e}\right)$$

```python
from plasmapy.formulary import Saha
import astropy.units as u

# Saha 是 LTE 相邻电离级丰度比函数（非可复用对象）：
# 给定简并度 g_j/g_k、电子数密度 n_e、电离能 E_jk（J 或 eV 均可，自动换算）
# 与温度 T_e，返回该级分数（无量纲 Quantity）。
n_e = 1e20 * u.m**-3
E_jk = 13.6 * u.eV                         # 氢原子基态电离能
frac = Saha(g_j=2, g_k=1, n_e=n_e, E_jk=E_jk, T_e=5000 * u.K)
# frac ≈ 中性氢占比分数（@5000K, 1e20 几乎完全中性）
```

`Saha` 是一个**纯函数**（2026.2.0 起不再是类对象）：每次调用直接传入 $g_j, g_k, n_e, E_{jk}, T_e$ 五个量，返回相邻两级电离的丰度比（式 13.1 右端的分数）。适用条件要清醒：**LTE + 理想气体**，对致密激光等离子体（非 LTE、简并修正）只作量级参考；真正的非 LTE 电离态分布由 FLYCHK 的碰撞辐射模型给出，两者对照可估计偏离 LTE 的程度。

### 13.2 平均电离度 ionization_balance

```python
from plasmapy.formulary import ionization_balance

Zbar = ionization_balance(n=1e20 * u.m**-3, T_e=100 * u.eV)
```

给定数密度与温度，返回 LTE 框架下（Saha 型公式）的平均电离度 $\bar Z$（纯公式，不接收物种参数）。别名 `Z_bal_`。用途：① 给 `Coulomb_logarithm`、`ion_sound_speed` 等函数提供 `z_mean` 初值；② 与 ionmix/FLYCHK 输出的 $\bar Z$ 表做一致性检查。

### 13.3 Saha 与 ionization_balance 的分工与陷阱

两个接口的关系：`Saha` 是求解单级电离平衡（给定 $g_j,g_k,n_e,E_{jk},T_e$ 返回该级分数），`ionization_balance` 给出 LTE 下的约化平均电离度（$\bar Z$）。两者都基于 Saha 型公式但接口不同——`ionization_balance` 是单步闭合公式，不宜与 `Saha` 混用。使用陷阱：

1. **n_g 的口径**：Saha 里的 `n_g` 是**基态中性原子**数密度，不是总核密度——高电离度时用总密度代入会低估电离，迭代一次（$\bar Z$ → 修正 n_g → 重解）即可收敛；
2. **简并修正缺失**：Saha 用经典统计配分函数，压缩区（衔接第 14 章 θ<1）会系统性高估电离——continuum lowering（压致电离）效应完全不在模型里，这正是 ICF 致密区必须用 FLYCHK/ionmix 的原因；
3. **激发配分函数**：内置数据取基态近似（$U_j\approx1$），对碱金属类（低激发能）元素在低温区偏差可达数倍。

正确姿势：把 `ionization_balance` 当作"LTE 端的快速参考点"——与 FLYCHK 曲线画在同一张图上，两条曲线的分离程度本身就是"偏离 LTE 多远"的定量指标，这比单独任何一个数值都更有诊断价值。

## 第 14 章 量子与简并效应

### 14.1 判据类：quantum_theta 与 thermal_deBroglie_wavelength

```python
from plasmapy.formulary import quantum_theta, thermal_deBroglie_wavelength

theta = quantum_theta(T=1e6 * u.K, n_e=1e30 * u.m**-3)     # T/T_F，≪1 强简并
lam   = thermal_deBroglie_wavelength(T=1e6 * u.K)          # √(2πħ²/mkT)
# 简并判据：n_e * lam^3 ≳ 1
```

对 ICF 压缩末期的 CH 靶（$n_e\sim10^{30}$ m⁻³、$T\sim100$ eV），$\theta$ 可能落到 1 以下——此时经典 Coulomb 对数、Spitzer 电阻率都开始失效，FLASH 的 EOS（ionmix 表）承担简并修正，PlasmaPy 的判据函数用于**标记哪些网格进入了简并区**。别名：`lambdaDB_th_`。

### 14.2 Fermi 物理：Fermi_energy、chemical_potential、Fermi_integral

```python
from plasmapy.formulary import Fermi_energy, chemical_potential
from plasmapy.formulary.mathematics import Fermi_integral

E_F = Fermi_energy(n_e=1e30 * u.m**-3)                     # 简并基态费米能
mu  = chemical_potential(T=1e6 * u.K, n_e=1e30 * u.m**-3)  # 真实化学势（含热修正）
F   = Fermi_integral(x=0.5, j=0.5)                         # 完全费米-狄拉克积分
```

- `Fermi_energy`：$E_F=\hbar^2(3\pi^2 n_e)^{2/3}/2m_e$，纯零温公式；
- `chemical_potential`：在强简并极限用解析式，中间区（$T\sim T_F$）用 lmfit 拟合的插值表——因此该函数**依赖 lmfit**；别名 `Ef_`；
- `Fermi_integral(x, j)`：$F_j(x)=\Gamma(j+1)^{-1}\int_0^\infty \frac{t^j}{e^{t-x}+1}dt$，由 mpmath 的 polylog 实现，支持复数与数组，是自写简并 EOS 的构件。

### 14.2.1 chemical_potential 的三段式实现细节

`chemical_potential` 内部按简并程度分三段处理，理解分段才能预判精度：① 强简并区（$\beta\mu\gg1$）：Sommerfeld 展开解析式，精度最高；② 经典区（$\beta\mu\ll-3$）：Boltzmann 极限 $\mu\approx k_BT\ln(n\lambda_{db}^3)$；③ **中间区（$-3\lesssim\beta\mu\lesssim$ 数量级若干）**：无简单解析式，库内用预计算表 + lmfit 插值——此段的返回值精度受插值表分辨率限制（相对误差典型为千分之一至百分之一量级），做 EOS 精确对账时对此段结果标注不确定性。判别自己落在哪段：先算 $\beta E_F$（或直接看 `quantum_theta`），$\theta\in[0.1, 10]$ 即中间区。

### 14.3 屏蔽长度：Thomas_Fermi_length 与 Wigner_Seitz_radius

```python
from plasmapy.formulary import Thomas_Fermi_length, Wigner_Seitz_radius

kTF = Thomas_Fermi_length(n_e=1e30 * u.m**-3)   # 强简并下的屏蔽长度（替代 λD）
a   = Wigner_Seitz_radius(n=1e30 * u.m**-3)     # 粒子平均间距 (3/4πn)^(1/3)
```

`Wigner_Seitz_radius` 是耦合参数 $\Gamma=e^2/(4\pi\varepsilon_0 a k_B T)$ 的分母构件（第 19 章）；`Thomas_Fermi_length` 在 $\theta\ll1$ 时替代 Debye 长度进 Coulomb 对数的 $b_{\max}$。别名 `lambdaDB_`（德布罗意）等见第 34 章总表。

### 14.4 ICF 末期的量子账本：一次完整演算

以压缩峰值附近的 CH 等离子体（$n_e=10^{30}$ m⁻³、$T_e=100$ eV）为例走一遍判据链：

```python
import astropy.units as u
from plasmapy.formulary import quantum_theta, Fermi_energy, Thomas_Fermi_length, Wigner_Seitz_radius

n_e, T = 1e30 * u.m**-3, (100 * u.eV).to(u.K, equivalencies=u.temperature_energy())
theta = quantum_theta(T=T, n_e=n_e)          # E_F ≈ 3.7e-17 J ≈ 230 eV → θ ≈ 0.43
E_F = Fermi_energy(n_e)
lam_TF = Thomas_Fermi_length(n_e)            # 强简并屏蔽长度
a_ws = Wigner_Seitz_radius(n_e)              # 粒子间距 ~0.66e-10 m
```

解读：$\theta\approx0.43$ 已进入中度简并区（$\theta<1$），此时 ① Coulomb 对数的 $b_{\min}$ 该取热德布罗意波长而非 $b_\perp$（`Coulomb_logarithm` 的量子分支自动处理，第 19 章）；② Spitzer 电阻率偏低，简并电子的输运系数要用含 Fermi 统计修正的模型（PlasmaPy 不提供，FLASH 靠 ionmix EOS 隐式承担）；③ Debye 屏蔽被 Thomas-Fermi 屏蔽取代，$\lambda_D$ 与 $\lambda_{TF}$ 相差数倍。结论：**强简并标记（θ<1）应作为输出场的例行诊断项**，与耦合参数 Γ 一起构成"经典输运适用域地图"。

## 第 15 章 辐射、激光与相对论

### 15.1 热韧致辐射 thermal_bremsstrahlung

```python
from plasmapy.formulary import thermal_bremsstrahlung
import astropy.units as u
import numpy as np

freqs = np.linspace(1e15, 1e17, 300) * u.Hz
j = thermal_bremsstrahlung(frequencies=freqs, n_e=1e20 * u.m**-3,
                           n_i=1e20 * u.m**-3, T_e=1e6 * u.K,
                           k_para=1.0)      # 返回谱发射率
```

Maxwellian 电子系综的热韧致辐射谱（含热 Gaunt 因子近似，非相对论），输入频率数组返回单频发射率，$\exp(-\omega/\omega_{pe})$ 高频截断由电子热运动决定。典型用途：合成 X 射线连续谱背景（谱线用 FLYCHK）。官方教程 [Emission of Thermal Bremsstrahlung](https://docs.plasmapy.org/en/stable/notebooks/formulary/thermal_bremsstrahlung.html) 有完整绘图流程。

**谱形解读三要素**：① 低频端 $j_\omega\propto\omega^0$ 平坦（经典韧致辐射的自吸收截止前）；② 指数截止位置 $\omega\sim\omega_{pe}(k_BT_e/m_ec^2)^{-1}$ 直接编码 $T_e$——这就是"连续谱斜率测电子温度"的经典方法的函数来源；③ $\bar Z^2$ 标度（有效电荷平方）意味着混合物连续谱对高 Z 杂质极端敏感——CH 靶混入 1% 的 Si 即可让连续谱强度翻倍，反过来这也是用连续谱监测杂质浓度的物理基础。合成实验谱时记得把这三要素与仪器响应卷积（探测器窗吸收、滤片透过率），否则低能端会系统性偏高。

**必须重申的边界**（与《相关公式接口速览》结论一致）：PlasmaPy **没有**不透明度（ff/bf/bb、Planck/Rosseland 平均）、辐射输运方程、SNB 流限热传导的任何实现。这些在 PhySimX 工作流中由 FLYCHK（不透明度与谱线）与 FLASH 扩散模块（辐射输运）承担，PlasmaPy 只负责发射谱一级量级与参数判据。

### 15.2 激光参数族 laser.py（9 个函数）

```python
from plasmapy.formulary.laser import (
    em_angular_frequency, em_wavelength, electric_field_amplitude, intensity,
    normalized_vector_potential, Gaussian_beam_waist_radius, Gaussian_power,
    Gaussian_Rayleigh_length, Gaussian_spot_size_FWHM,
)
import astropy.units as u

lam = 0.351 * u.um
omega = em_angular_frequency(lam)                  # 波长 → 角频率
E0 = electric_field_amplitude(intensity=5e14 * u.W / u.cm**2)   # I → 峰值场
I = intensity(E0=E0)                               # 反向换算
a0 = normalized_vector_potential(intensity=5e14 * u.W / u.cm**2,
                                 wavelength=lam)   # 无量纲矢量势（返回裸 float）
w0 = Gaussian_beam_waist_radius(spot_size_FWHM=30 * u.um)   # FWHM → 腰半径
P = Gaussian_power(intensity=5e14 * u.W / u.cm**2, beam_waist_radius=w0)
zR = Gaussian_Rayleigh_length(wavelength=lam, beam_waist_radius=w0)
FWHM = Gaussian_spot_size_FWHM(beam_waist_radius=w0)        # 腰半径 ↔ FWHM
```

这组函数覆盖 1D/2D 激光参数化全部常用换算：波长↔频率（`em_angular_frequency`/`em_wavelength` 互逆）、强度↔场幅 $I=\varepsilon_0 c E_0^2/2$、$a_0$（**入参是强度+波长**，返回裸 float，内部完成 $a_0=eE_0/m_ec\omega$ 换算）、高斯光束四件套（FWHM↔腰半径、功率、瑞利长度）。对 FLASH 配置的直接价值：**核验 `ed_lens` 系列与仿真域的几何关系**（焦斑尺寸 vs 网格分辨率）与 $a_0$ 判断是否需要特殊模块。别名 `a0_`/`omega_`/`E0_`/`I_`/`w0_`。⚠ 整模块带 `|expect-api-changes|` 标记，升级版本时检查签名。

### 15.3 相对论工具 relativity.py

```python
from plasmapy.formulary.relativity import RelativisticBody, Lorentz_factor, relativistic_energy
from astropy.constants import c

body = RelativisticBody(V=0.9 * c, particle="e-")
body.lorentz_factor         # 洛伦兹因子 ≈ 2.29（属性名是 lorentz_factor，不是 gamma）
body.momentum, body.E       # 相对论动量/总能量
gamma = Lorentz_factor(V=0.9 * c)                  # 纯数值接口
E = relativistic_energy(m=9.11e-31 * u.kg, V=0.5 * c)
```

`RelativisticBody` 是统一入口：给定速度、动量或能量之一即可（内部互解），带 `check_relativistic` 警告机制——速度超光速抛 `RelativityError`，接近光速发 `RelativityWarning`。`gyroradius(relativistic=True)` 与 `deBroglie_wavelength(relativistic=True)` 内部即调用此类。

### 15.4 场景应用：激光参数前置核对脚本

FLASH 场景 `ed_lens` 配置的常用核对项，用 laser 族十行内完成：

```python
import astropy.units as u
from plasmapy.formulary.laser import em_angular_frequency, normalized_vector_potential

lam, I0 = 0.351 * u.um, 5e14 * u.W / u.cm**2
omega = em_angular_frequency(lam)
a0 = normalized_vector_potential(intensity=I0, wavelength=lam)   # ≈ 0.0067：非相对论区（I=5e14 W/cm², λ=0.351 µm）
```

结论读法：$a_0\approx0.04$ 意味着有质动力效应（$U_p\propto a_0^2$）可忽略、热压主导——这决定了后烧蚀期自相似模型的适用性；若换成拍瓦级短脉冲（$a_0\gtrsim1$），整个烧蚀物理换成相对论透明/空泡区，FLASH 的常规激光模块不再适用。这类"一算定 regime"的判断建议写入每个场景的测试文档开头。

## 第 16 章 静磁场源建模 magnetostatics

### 16.1 类族与工厂

```python
from plasmapy.formulary import (
    MagneticDipole, CircularWire, FiniteStraightWire, InfiniteStraightWire, Wire
)
import astropy.units as u
import numpy as np

# 磁偶极子（定位在 p，磁矩 m 沿 z）
dip = MagneticDipole(moment=np.array([0, 0, 1]) * u.A * u.m**2,
                     p=np.array([0, 0, 0]) * u.m)
# 圆环电流（中心 p0，半径 R，法向 n，电流 I）
ring = CircularWire(R=0.5 * u.m, p0=np.array([0,0,0]) * u.m,
                    normal=np.array([0,0,1]), current=1e5 * u.A)
# 有限长直导线（两顶点 + 电流）
wire = FiniteStraightWire(p1=np.array([-1,0,0]) * u.m, p2=np.array([1,0,0]) * u.m,
                          current=1e4 * u.A)
# 无限长直导线（方向 + 过点 + 电流）
inf = InfiniteStraightWire(direction=np.array([0,0,1]), p0=np.array([0,0,0]) * u.m,
                           current=1e4 * u.A)
```

所有场源实现统一接口：`magnetic_field(q)` 在给定点/点阵返回 B 场 Quantity；`Wire` 是工厂别名，按参数形状自动选择具体类。多个场源的场可用 `MagnetoStatics`（容器）组合后统一求和。

### 16.2 典型工作流

给 `simulation.particle_tracker`（第 26 章）提供磁场栅格：先用类族在 CartesianGrid 的格点上算 `magnetic_field`，写入网格的 B 分量，再交给粒子追踪器。这构成了"线圈磁场 + 粒子轨道"的合成演示闭环（官方教程 [Magnetostatic Fields](https://docs.plasmapy.org/en/stable/notebooks/formulary/magnetostatics.html) 即此流程）。

### 16.3 设计细节与注意事项

1. **单位与坐标**：所有位置参数是 `Quantity`（米），方向参数是**裸数组**（内部自动归一化）——这一不一致是本模块最常见的报错来源，传方向向量时不要乘单位；
2. **场点密度**：`magnetic_field(q)` 逐点解析计算无奇异性保护——圆环导线自身轴线上（$r\to R$）场值有限但数值求导类应用会病态；有限长导线端点附近梯度极大，粒子追踪网格在这些区域应加密；
3. **叠加组合**：`MagnetoStatics` 容器把多个场源打包后统一调用，等价于对各自 `magnetic_field` 求和，适合"螺线管 + 引导场"式组合；
4. **与真实线圈的差距**：解析模型假设细丝电流（无导线粗细、无磁介质），核验真实磁体（RCL 线圈、磁光阱线圈）时先对照厂商场图，偏差通常在几何因子 5%–15% 量级。

## 第 17 章 经典输运：Braginskii

### 17.1 ClassicalTransport 类

```python
from plasmapy.formulary.braginskii import ClassicalTransport
from plasmapy.formulary import Coulomb_logarithm
import astropy.units as u
from plasmapy.particles import Particle

T_e = (100 * u.eV).to(u.K, equivalencies=u.temperature_energy())
n_e = 1e27 * u.m**-3
lnL = Coulomb_logarithm(T_e, n_e, ["e", "C 3+"], z_mean=3.5)

tr = ClassicalTransport(
    T_e, n_e=n_e, T_i=T_e, n_i=n_e / 3.5,
    ion=Particle("C 3+"), Z=3,         # 离子电荷态（整数）；混合物平均 Z 单独由 z_mean 给定
    B=0 * u.T,                       # 非磁化；磁化时给 B 并配 hall_e/hall_i
    coulomb_log_ei=lnL,              # 也可省略，改用 coulomb_log_method="GMS-3" 内部自算
    field_orientation="parallel",    # 取值以本地 docstring 为准（parallel 等）
)
tr.resistivity                      # η ∥（Spitzer 量级）
tr.thermoelectric_conductivity      # 热电系数 α
tr.electron_thermal_conductivity    # 电子热导 κ_e（FLASH 热传导系数对照）
tr.ion_thermal_conductivity
tr.electron_viscosity, tr.ion_viscosity   # 黏滞张量元组合
```

要点与限制：① 系数是 Braginskii 1965 的 Lorentz 拟合，**弱耦合（Γ≪1）、经典库仑碰撞、σ(v) 各向同性**假设——强耦合/简并区（Γ≳1、θ≲1）失效，用第 14/19 章判据先筛；② 磁化时同时给 `B` 与 `hall_e`/`hall_i`（Hall 数值可从 `dimensionless.Hall_parameter` 算）；③ 各系数是 cached_property，首次访问后缓存，多系数复用同一实例最划算；⚠ 类带 `|expect-api-changes|` 标记。

### 17.2 六个便捷函数

```python
from plasmapy.formulary.braginskii import (
    resistivity, thermoelectric_conductivity, electron_thermal_conductivity,
    ion_thermal_conductivity, electron_viscosity, ion_viscosity,
)

eta = resistivity(T_e, n_e, T_i=T_e, n_i=n_e / 3.5, ion="C 3+", Z=3.5,
                  coulomb_log_method="GMS-3")
kappa_e = electron_thermal_conductivity(T_e, n_e, T_i=T_e, n_i=n_e / 3.5,
                                        ion="C 3+", Z=3.5, coulomb_log_method="GMS-3")
```

函数式封装等于"临时建一个 ClassicalTransport 再取一个系数"，适合一次性调用；批量取多个系数请用类实例。注意便捷函数与类共享同一套参数名（`ion`/`Z`/`T_i`/`n_i`，无 `z_mean`——平均电离度走 `Z`），离子温度与密度**必须显式给出**。官方教程 [Braginskii coefficients](https://docs.plasmapy.org/en/stable/notebooks/formulary/braginskii.html) 画了系数随磁化参数 χ 的三支曲线（∥/⊥/cross），理解 FLASH 磁化输运开关时值得一看。

### 17.2.1 便捷函数与类接口的参数差异

六个便捷函数的签名与类构造高度一致（都要求 `T_e/n_e/T_i/n_i/ion/Z` 全量显式），差异只在返回值：函数式版本内部构造临时 ClassicalTransport 并只取一个系数。因此"函数算的值"与"类算的值"在相同参数下应当一致——不一致时优先怀疑 `coulomb_log_ei`（类）与 `coulomb_log_method`（函数）两条库仑对数路径的口径差。另外便捷函数内部每次都重新解析粒子与单位，热路径（循环内）的性能比复用类实例差一个数量级，第 35.5 节反模式清单已点名。

### 17.3 与 FLASH/Spitzer 的衔接

`electron_thermal_conductivity` 的非磁化极限即 Spitzer-Härm 热导（系数差约 0.9 的拟合因子），本工作区用它核验 FLASH 热传导系数设置；`resistivity` 即 Spitzer 电阻率，与 `collisions.misc.Spitzer_resistivity`（第 19 章）等价但接口不同（前者走完整 Braginskii 机器，后者是直接公式）。

### 17.4 磁化输运的三支系数与 FLASH 开关对应

Braginskii 系数随磁化参数 $x=\omega_c\tau$ 的行为分三支，直接对应 FLASH 输运开关的三种模式：

1. **平行系数**（$x\ll1$ 极限）：即经典 Spitzer-Härm 值——FLASH 非磁化模式的热传导系数应与 `field="parallel"` 结果一致（约 0.9 的拟合因子差异来自系数表版本）；
2. **垂直系数**（$x\gg1$）：$\kappa_\perp\propto1/x$ 衰减——强磁化时垂直热输运被压制，若 FLASH 打开 E×B 与磁化传导而场值来自合成磁场，需确认与这里的量级一致；
3. **交叉系数**（Nernst/Righi-Leduc 型）：影响热波前的场演化——辐射磁流体耦合研究的关键项，PlasmaPy 的 `field="cross"` 分支给出量级核验值。

实际工作流：对 FLASH 输出的 (n, T, B) 场抽样若干代表点 → 每点算 $x$ 与三支系数 → 与 FLASH 内部使用的系数表比对 → 偏差超 10% 时检查库仑对数与 z_mean 口径是否一致（最常见的偏差来源是 `Coulomb_logarithm` 的 method 与 FLASH 内置公式不同，先统一 method 再比）。

## 第 18 章 无量纲数、数学工具与杂项

### 18.1 dimensionless.py

```python
from plasmapy.formulary import beta, Debye_number, Hall_parameter, quantum_theta
from plasmapy.formulary.dimensionless import Reynolds_number, Mag_Reynolds, Lundquist_number
import astropy.units as u

plasma_beta = beta(T=1e6 * u.K, n=1e20 * u.m**-3, B=0.01 * u.T)  # 热压/磁压
N_D = Debye_number(T_e=1e6 * u.K, n_e=1e20 * u.m**-3)      # Debye 球内粒子数
x = Hall_parameter(B=5 * u.T, n=1e20 * u.m**-3, T=1e6 * u.K,
                   ion="p+", particle="e-", coulomb_log=14)   # ω_c τ
rho_f = 1e3 * u.kg / u.m**3
mu    = (rho_f * 1e-4 * u.m**2 / u.s)          # 动黏度 = 密度 × 运动黏度
Re  = Reynolds_number(rho=rho_f, U=1e5 * u.m/u.s, L=0.01 * u.m, mu=mu)
Rm  = Mag_Reynolds(U=1e5 * u.m/u.s, L=0.01 * u.m, sigma=1e4 * u.S/u.m)
S   = Lundquist_number(L=1.0 * u.m, B=0.01 * u.T, density=1e20 * u.m**-3,
                       sigma=1e4 * u.S/u.m, ion="p+")
```

- `beta`：等离子体 β，入参为温度 `T` 与**数密度** `n`（非质量密度 rho）；
- `Debye_number`：理想等离子体判据 $N_D\gg1$，$N_D\lesssim10$ 时强关联修正必须考虑（衔接第 19 章耦合参数）；
- `Hall_parameter`：Braginskii 与 dielectric 的磁化强度输入，直接连到第 17 章的 `Hall=` 参数；
- `Reynolds_number`/`Mag_Reynolds`/`Lundquist_number`：MHD 湍流与重联的相似性参数。别名 `betaH_`/`nD_`/`Re_`/`Rm_`。

### 18.1.1 各无量纲数的物理出处一览

为便于"看到数就想到物理"，把每个数的定义式与失效信号并列：

| 无量纲数 | 定义 | ≪1 含义 | ≫1 含义 |
|---|---|---|---|
| $\beta$ | $2\mu_0 p/B^2$ | 磁主导（快波≈Alfvén） | 热主导（快波≈声波） |
| $N_D$ | $4\pi n\lambda_D^3/3$ | 强关联，Debye 图景失效 | 理想等离子体 |
| $x$（Hall） | $\omega_c\tau$ | 非磁化，Spitzer 输运 | 磁化，Braginskii 各向异性 |
| $Re$ | $VL/\nu$ | 层流 | 湍流 |
| $Rm$ | $\mu_0\sigma VL$ | 场被耗散 | 场冻结于流体 |
| $S$（Lundquist） | $v_A L/\eta_m$ | 重联阻尼 | 无碰撞重联/Hall 区 |
| $\theta$ | $T/T_F$ | 强简并 | 经典统计 |
| $\Gamma$ | 势能/动能 | 弱耦合 | 强耦合（液态） |

失效信号一栏是"这个数越界时要换模型"的直接对照——与第 18.4 节的质检层设计配套。

### 18.2 mathematics.py

`Fermi_integral(x, j)` 见第 14 章；`rot_a_to_b(a, b)` 把向量 a 旋到向量 b 的旋转矩阵（构造随机场方向、偶极子指向变换的小工具）。

### 18.3 misc.py

```python
from plasmapy.formulary import Bohm_diffusion, magnetic_pressure, magnetic_energy_density, thermal_pressure
import astropy.units as u

D_B = Bohm_diffusion(T=1e6 * u.K, B=5 * u.T)      # 反常扩散上界 eB/16me
p_B = magnetic_pressure(B=5 * u.T)                # B²/2μ0
u_B = magnetic_energy_density(B=5 * u.T)          # 数值上与 p_B 相同，语义不同
p_th = thermal_pressure(n=1e20 * u.m**-3, T=1e6 * u.K)
```

`thermal_pressure(n, T)` 接受数密度与温度（无 species/Z），求单一组分压强；多组分总压强按组分分别调用后求和——这是把 FLASH 输出的 (dens, tele) 场换算压强的直接工具。别名 `DB_`/`pmag_`/`ub_`/`pth_`。

### 18.4 无量纲数在仿真质检中的组合应用

无量纲数族的工程价值在于**把"模型是否适用"变成可计算的布尔判据**，推荐在数据管道中固定使用四件套：

1. **电中性/理想性**：`Debye_number > 10`（否则准中性假设可疑）且 $\Gamma<0.1$（弱耦合）→ 经典双流体模型成立域；
2. **磁化状态**：`Hall_parameter ≫ 1` → 磁化输运分支（第 17.4 节三支系数）；$x\ll1$ → 非磁化 Spitzer；
3. **相对论性**：$v_{th}/c$（`thermal_speed`/c）< 0.1 → 非相对论输运公式有效；电子预热场景（SRS 超热尾）要重查；
4. **连续性**：`Knudsen_number < 0.1` → 流体封闭（Braginskii）成立；Kn~1 区域是 SNB 非局域热传导的领地（衔接本工作区 SNB 场景族）。

把四个判据封装成一个"regime 标签函数"（输入 dens/tele/B 数组，输出每点的适用模型标签），插在 `output_pro` 之后——这是把 PlasmaPy 从"查表工具"升级为"自动质检层"的关键一步，也为 NSGA 优化的约束函数提供物理依据。

## 第 19 章 碰撞物理专章（重点与蓄水池）

碰撞是 PlasmaPy 覆盖最深、对本项目价值最高的板块。公式对照见《相关公式接口速览》第 2 节，本节聚焦**方法选择与正确用法**。官方教程：[Coulomb logarithms](https://docs.plasmapy.org/en/stable/notebooks/formulary/coulomb.html)。

### 19.1 Coulomb_logarithm：方法全解

```python
from plasmapy.formulary import Coulomb_logarithm
import astropy.units as u

T_e = (100 * u.eV).to(u.K, equivalencies=u.temperature_energy())
n_e = 1e27 * u.m**-3
lnL = Coulomb_logarithm(T=T_e, n_e=n_e, species=["e", "C 3+"], z_mean=3.5)
lnL2 = Coulomb_logarithm(T=T_e, n_e=n_e, species=["e", "C 3+"],
                         z_mean=3.5, method="GMS-3")
```

`method` 参数决定 $b_{\min}$ 的物理取法与 $b_{\max}$ 的收集方式：

| method | 出处 | 特点 |
|---|---|---|
| `classical` | NRL 经典 | $b_{\max}=\lambda_D$，$b_{\min}=\max(b_\perp, \lambda_{db})$；最朴素，强耦合无保护 |
| `GMS-1` ~ `GMS-6` | Gericke-Murillo-Schlanges 2002 | 从"完全不考虑强耦合"到"含渐进修正"的六档；**推荐**，尤其 `GMS-3` 起在 $\Gamma\sim1$ 仍有合理行为 |
| `hls_max` / `hls_min` / `hls_expx` 等 | Hahn-Lee-Selchow 系列 | 动理学屏蔽（$b_{\max}$ 取德拜/热波长组合），等离子体物理文献近年主流 |
| `ls` / `ls_clamp_mininterp` | Lie-Suzuki 插值 | 强耦合插值方案，$\Gamma>1$ 时仍可给有限值 |

选择建议：ICF 参数区（Γ≲0.1）`classical` 与各档差别 <1%；接近强耦合时先用 `coupling_parameter` 算 Γ，Γ≳0.5 换 `GMS-3` 以上并交叉对比 `ls`。警告阈值要记牢：`Coulomb_logarithm` 在 lnΛ ≲ 4 时即发 `CouplingWarning`（官方提示"≲4 时强耦合效应带来的不确定度增大"）——这不是数值 bug，而是"经典库仑图景开始退化"的信号；lnΛ 掉到 2 以下则结果基本不可信。

**返回类型说明（易踩坑）**：2026.2.0 的 `Coulomb_logarithm` 返回**裸 `numpy.float64`**（库仑对数本身无量纲，不带 Quantity 包装）。两个后果：① 喂给要求 Quantity 的接口（如 `MaxwellianCollisionFrequencies` 的 `Coulomb_log=` 参数）时会发 UnitsWarning——显式包一层 `u.Quantity(lnL)` 消除；② 代码里不要对它调 `.value`。下游接口同理：`coulomb_log` 类参数接受裸 float 也能算，但显式 Quantity 是干净写法。

### 19.2 碰撞参数与平均自由程

```python
from plasmapy.formulary.collisions import impact_parameter_perp, impact_parameter, mean_free_path

b_perp = impact_parameter_perp(T=T_e, species=["e", "C 3+"], V=None)  # 90° 散射瞄准距离
bp = impact_parameter(T=T_e, n_e=n_e, species=["e", "C 3+"], z_mean=3.5)  # namedtuple(bmin, bmax)
lam = mean_free_path(T=T_e, n_e=n_e, species=["e", "C 3+"], z_mean=3.5, V=None)
```

`impact_parameter` 返回 `(bmin, bmax)` 二元组——自写库仑对数或蒙特卡罗散射时直接取用；`mean_free_path` = v/ν（速度用热速度，可传显式 `V`）。`Knudsen_number(characteristic_length, T, n_e, species)` 由内部平均自由程给出克努森数，与本项目 Knudsen 数研究直接对应（速览文档第 2 节）。

### 19.3 碰撞频率：两个类 + 两个基频函数

⚠ 首先记迁移规则：**`collision_frequency` 函数已弃用**（2026.2.0 起 DeprecationWarning），替代方案按需求二选一：

```python
from plasmapy.formulary.collisions import (
    SingleParticleCollisionFrequencies, MaxwellianCollisionFrequencies,
    fundamental_electron_collision_freq, fundamental_ion_collision_freq,
)

# 方案 A：单粒子碰撞频率（测试粒子以确定速度穿过场粒子系综）
single = SingleParticleCollisionFrequencies(
    test_particle="e", field_particle="p+",
    v_drift=3e5 * u.m / u.s,        # 相对速度
    T_b=1e6 * u.K, n_b=1e20 * u.m**-3,   # 场粒子的温度与密度
    Coulomb_log=lnL)                # 库仑对数显式传入
single.momentum_loss             # 动量弛豫率 ν_m
single.transverse_diffusion      # 横向扩散 ν_D
single.parallel_diffusion        # 纵向扩散 ν_∥
single.energy_loss               # 能量弛豫率 ν_E
single.Lorentz_collision_frequency  # Lorentz 模型频率

# 方案 B：Maxwellian 平均碰撞频率（测试粒子 + Maxwellian 场粒子）
mx = MaxwellianCollisionFrequencies(
    test_particle="e", field_particle="p+",
    T_a=T_e, n_a=n_e, T_b=T_e, n_b=n_e,   # 两侧各自的温度/密度
    Coulomb_log=lnL)
mx.Maxwellian_avg_ei_collision_freq      # ⟨ν_ei⟩（Braginskii 输入）
mx.Maxwellian_avg_ii_collision_freq      # 场粒子为离子时（test=ion）
mx.Lorentz_collision_frequency

# 基频（Spitzer/Braginskii 定义）快捷函数：无 z_mean，库仑对数用 coulomb_log 或 method
nu_e = fundamental_electron_collision_freq(T_e=T_e, n_e=n_e, ion="C 3+", coulomb_log=lnL)
nu_i = fundamental_ion_collision_freq(T_i=T_e, n_i=n_e, ion="C 3+", coulomb_log=lnL)
```

选型建议：给 Braginskii 供料用方案 B（其系数定义即基于 Maxwellian 平均矩）；轨迹模拟/输运方程右端项用方案 A（保留速度依赖）；只要 Spitzer 电阻率/热导的量级，用基频函数最省事（注意它**不接受 z_mean**，平均电离度效应通过预先算好的 `coulomb_log` 或 `coulomb_log_method` 体现）。类的属性都是 cached_property，一次构造多矩复用。

### 19.3.1 两个碰撞频率类的接口说明

两个类共用"测试粒子 + 场粒子"的构造哲学（这正是 `collision_frequency` 老函数被弃用后推荐的新范式——把"谁撞谁"写明确）：

```python
# Maxwellian 类：测试粒子 a 在 Maxwellian 场粒子 b 中
mx = MaxwellianCollisionFrequencies(test_particle="e", field_particle="p+",
                                    T_a=T_e, n_a=n_e, T_b=T_e, n_b=n_e,
                                    Coulomb_log=lnL)
mx.Maxwellian_avg_ei_collision_freq   # ⟨ν_ei⟩：Braginskii 电阻率/热导的输入
mx.Maxwellian_avg_ii_collision_freq   # test=离子时：离子平衡时间
mx.Lorentz_collision_frequency        # Lorentz 模型（不反射测试粒子）
mx.v_T_a, mx.v_T_b                    # 两侧热速度（中间量，也可单独用）
```

注意：2026.2.0 的 Maxwellian 类**只提供 ei/ii/Lorentz 三类矩**——电子-电子平衡（⟨ν_ee⟩）与双温能量交换矩未单列；做双温弛豫估算时用 `Maxwellian_avg_ei_collision_freq` 的能量矩近似（或按 $\sqrt{m_e/m_i}$ 标度换算），精确值需自写 Spitzer 能量交换公式。`SingleParticleCollisionFrequencies` 的五个矩属性（momentum_loss/transverse_diffusion/parallel_diffusion/energy_loss/Lorentz）与 Fokker-Planck 方程的五个 Landau 碰撞矩一一对应，另附 `phi`/`x` 两个中间变量。

### 19.4 无量纲碰撞物理与输运杂项

```python
from plasmapy.formulary.collisions import coupling_parameter, Knudsen_number, mobility, Bethe_stopping, Spitzer_resistivity
from plasmapy.formulary.collisions.helio import temp_ratio

Gamma = coupling_parameter(T=1e6 * u.K, n_e=1e30 * u.m**-3, species=["e", "p+"])
Kn = Knudsen_number(characteristic_length=1e-4 * u.m, T=1e6 * u.K, n_e=1e20 * u.m**-3, species=["e", "p+"])
mu_e = mobility(T=T_e, n_e=n_e, species="e-", z_mean=1)   # 电迁移率 q/(mν)
# Bethe 阻止本领：I=靶粒子电离能, n=数密度, v=入射速度, z=入射粒子电荷数（整数）
S = Bethe_stopping(I=Particle("H").ionization_energy,
                   n=1e20 * u.m**-3, v=1e7 * u.m / u.s, z=1)
eta = Spitzer_resistivity(T=T_e, n=n_e, species=["e", "C 3+"], z_mean=3.5)
```

- `coupling_parameter`：$\Gamma=e^2/(4\pi\varepsilon_0 a k_BT)$（含德拜屏蔽修正因子 $\exp(-\kappa)$），**Γ≳1 发 CouplingWarning**——该参数本身就只在弱耦合有效，警告即适用域边界；
- `Knudsen_number`：输运方程连续性判据（Kn≪1 流体 / Kn≳1 动理学），FLASH 侧判读无碰撞热传导区域的核心；
- `Bethe_stopping`：快带电粒子在等离子体中的碰撞能损（-dE/dx），签名 `(I, n, v, z)`——I 为靶物种电离能（用 `Particle(...).ionization_energy` 取）、z 为入射粒子电荷数（整数）；lite 版 `Bethe_stopping_lite` 接受裸数组；诊断箔设计、质子照相能损条目用；
- `Spitzer_resistivity`：与 `braginskii.resistivity` 非磁化极限一致，接口更轻（species 为**二体列表** + z_mean）；
- `helio.temp_ratio`：太阳风电子-离子温度比的经验/解析模型（`collisions.helio` 小子包），与 ICF 场景无关，按需取用。

### 19.4.1 碰撞板块的接口一致性总结

collisions 子包的函数在"如何指定粒子组分"上有三种风格并存，混用时极易出错，在此统一梳理：

| 风格 | 示例接口 | 组分指定方式 |
|---|---|---|
| species 列表 | `Coulomb_logarithm`, `mean_free_path`, `Spitzer_resistivity` | `species=["e", "C 3+"]`（二体按列表顺序） |
| 测试/场粒子对 | 两个碰撞频率类 | `test_particle=` + `field_particle=`（方向显式，弃用的 `collision_frequency` 的替代范式） |
| 显式离子 | `fundamental_electron/ion_collision_freq`, `mobility` | `ion="C 3+"`（**无 z_mean**，库仑对数经 `coulomb_log` 或 `coulomb_log_method` 传入） |
| 单粒子分体 | `Bethe_stopping` | `(I, n, v, z)`——靶物种电离能与入射电荷数分开传 |
| 耦合参数 | `coupling_parameter` | `species=["e", "C 3+"]`（**必须二体列表**，内部按两体相互作用计算） |

三条纪律：① species 列表风格中**顺序决定谁是入射粒子**（第一项打第二项），`["e","C 3+"]` 与 `["C 3+","e"]` 的结果不同；② 所有接口的 `z_mean` 都只作用于**离子侧**，电子总是 -1；③ 任何接口传 `CustomParticle`（等效离子）都必须同时给 `z_mean`（CustomParticle 的电荷会被 z_mean 覆盖，两者不一致时以 z_mean 为准并发警告）。

### 19.5 本项目推荐组合（速查）

| 需求 | 组合 |
|---|---|
| FLASH 热传导系数量级核验 | `Coulomb_logarithm(GMS-3)` → `ClassicalTransport.electron_thermal_conductivity` |
| SNB 适用域判读 | `mean_free_path` → `Knudsen_number`（Kn 接近 1 的区域即非局域区） |
| 简并/强耦合标记 | `coupling_parameter` + `quantum_theta` 逐网格点扫描 |
| $\bar Z$ 初值 | `ionization_balance`（LTE）与 FLYCHK 输出对照 |
| 诊断箔能损 | `Bethe_stopping` |

### 19.6 库仑碰撞的物理图像：从二体散射到流体矩

理解这一章全部公式的统一框架是**二体库仑散射 + 小角度累积**。一次二体库仑散射中，瞄准距离为 $b$ 的入射粒子偏转角 $\theta_b\approx 2b_\perp/b$（小角近似，$b_\perp=|q_1q_2|/(4\pi\varepsilon_0 m_r u^2)$ 是 90° 散射的瞄准距离）；等离子体中单次大角散射极罕见，方向/能量的弛豫由大量小角散射累积——对偏转角平方求和得到扩散型输运系数，对数发散的远近截止分别引入 $b_{\min}$（经典取 $b_\perp$，量子取热德布罗意波长，取大者）与 $b_{\max}$（Debye 长度或其变体），两者的比值即库仑对数。这就是 `impact_parameter` 返回 $(b_\min,b_\max)$、`Coulomb_logarithm` 提供 method 选项、`Coulomb_cross_section` 存在的全部原因——它们是同一积分的不同截面。

五个矩频率的相对大小有普适排序（同种粒子、Maxwellian）：$\nu_\epsilon \sim \sqrt{m_e/m_i}\,\nu_m^{(e)}$，即**电子能量弛豫远慢于动量弛豫**——电子-电子碰撞在纳秒内建立 Maxwellian（tele 有意义），而电子把能量交给离子要慢 $\sqrt{m_i/m_e}$ 倍，这正是 FLASH 双温模型（tele≠tion）与"电子预热/离子滞后"现象的碰撞论基础。`SingleParticleCollisionFrequencies` 的五个属性（momentum_loss/transverse_diffusion/parallel_diffusion/energy_loss/Lorentz）与 Fokker-Planck 方程的五个 Landau 碰撞矩一一对应，做输运方程右端项时可直接映射。

GMS 方法的价值再强调一次：经典 NRL 取法在 $\Gamma\gtrsim0.1$ 后因 $b_{\min}$ 与离子间距 $a$ 可比而系统性高估 $\ln\Lambda$；GMS-1~6 是把 $b_{\min}$（含关联修正）与 $b_{\max}$（含从 Debye 到动理学屏蔽的插值）逐级改进的六档开关，`GMS-3` 是"保守改进"的分水岭（含有限 de Broglie 修正）。定量结论：$\Gamma=0.1$ 时 classical 与 GMS-3 差约 5%；$\Gamma=0.5$ 时差可超 30%——所以第 19.5 节推荐"先算 Γ 再选 method"而不是一律 classical。

### 19.7 强耦合区的出路

PlasmaPy 的碰撞板块整体停在弱耦合库仑图景（`coupling_parameter` 的警告即边界）。Γ≳1（致密 ICF 压缩区、液态金属密度等离子体）时的替代路径：① `ls`/`ls_clamp_mininterp` 插值方案给有限值但无严格理论地位；② 有效势方法（IPD 模型、平均力实验）在 `Coulomb_logarithm` 的部分 method 中有近似体现；③ 严格处理需动理学模拟或 MD——对本项目，实用做法是把 Γ>1 的网格点标记出来，其输运系数交给 FLASH 的 EOS/表格（ionmix 含简并修正），PlasmaPy 只负责"圈地"。

---

# 第四篇 色散分析 dispersion

`plasmapy.dispersion` 把"波的色散关系"从纸面公式变成可执行接口：既包括等离子体色散函数这类数学构件，也包括从冷等离子体（Stix）、双流体（Bellan/Stringer）到动理学（Hollweg、kinetic Alfvén）的完整求解链。⚠ 整个子包带 `|expect-api-changes|` 标记，接口在未来版本可能调整——升级前用 `help()` 复核签名。

## 第 20 章 等离子体色散函数

### 20.1 plasma_dispersion_func 与其导数

$$Z(\zeta)=\frac{1}{\sqrt{\pi}}\int_{-\infty}^{\infty}\frac{e^{-x^2}}{x-\zeta}\,dx,\qquad \mathrm{Im}\,\zeta>0$$

```python
from plasmapy.dispersion import plasma_dispersion_func, plasma_dispersion_func_deriv
import numpy as np

Z = plasma_dispersion_func(0.5 + 0.1j)          # 复数输入
dZ = plasma_dispersion_func_deriv(0.5 + 0.1j)   # Z'(ζ)
# 数组输入自动广播
vals = plasma_dispersion_func(np.linspace(-3, 3, 61) * (1 + 0.05j))
```

物理意义：$Z(\zeta)$ 是 Maxwellian 热速度积分下的响应函数，动理学介电函数（第 11 章 `permittivity_1D_Maxwellian`）的内核；$\zeta$ 在上半平面（增长波）与实轴附近（阻尼波）都有定义，函数内部用 Faddeeva 类算法处理解析延拓。常用关系：$Z'(\zeta)=-2[1+\zeta Z(\zeta)]$、$\zeta\to0$ 时 $Z\approx i\sqrt{\pi}-2\zeta$。

### 20.1.1 与手工实现的对照：为什么不要自己写 Z

初学者常问：一个积分而已，为什么不用 scipy 直接积？三个理由：① **解析延拓不可积**——$\zeta$ 在上半平面时积分路径必须绕极点，普通高斯积分静默给错答案（差一个 $2\pi i$ 型残差项），而 Faddeeva 算法（库内实现基于 `scipy.special.wofz`）精确处理全复平面；② **实轴附近 1/x 型奇异**，数值积分需要特别的容差设计；③ **精度一致性**——自写实现与库内实现的差异会污染所有下游色散分析，色散类问题的"不同代码不同答案"多数源自这里。结论：$Z$ 及其导数一律用库内函数，自己写的版本最多用于交叉验证（且要标明适用域）。

### 20.3 数值行为与使用边界

1. **实轴附近**（$|\mathrm{Im}\,\zeta|\to0$）：函数趋于主值积分 + $\pm i\sqrt{\pi}e^{-\zeta^2}$——阻尼率计算正靠这个小虚部，输入 $\mathrm{Im}\,\zeta$ 不要取严格 0（取 $10^{-6}$ 量级数值稳定）；
2. **大 $|\zeta|$ 渐近**：$Z\sim-1/\zeta-1/2\zeta^3-\cdots$，渐近式与库内精确值在 $|\zeta|\gtrsim4$ 时偏差 <1%——自己写快速分支时以此为界；
3. **数组复输入**：`np.linspace` + 复数化（`* (1 + 0.05j)`）是最常用的扫描模式；函数完全向量化，无需循环；
4. 与 mpmath `Fermi_integral` 的关系：两者分属费米-狄拉克与麦克斯韦-玻尔兹曼统计的"特殊函数层"，自写简并色散关系（第 14 章）用后者，经典动理学色散用前者。

### 20.2 用途定位

自写色散关系求解器时的标准构件：任何"Maxwellian 响应 + 介电函数 = 0"的求根问题都可以用 $Z$ 表达后交给 `scipy.optimize`。官方教程 [The plasma dispersion function](https://docs.plasmapy.org/en/stable/notebooks/dispersion/dispersion_function.html) 展示了 $Z$ 的实虚部曲面与渐近行为。

## 第 21 章 解析波动解

### 21.1 Stix 冷等离子体色散关系 stix

```python
from plasmapy.formulary import cold_plasma_permittivity_SDP
from plasmapy.dispersion.analytical.stix_ import stix
from plasmapy.particles import Particle
import astropy.units as u
import numpy as np

B, n_i = 8.3e-9 * u.T, 5e6 * u.m**-3
theta = 30 * u.deg          # 波矢与 B 的夹角

# ions 是单个 Particle（电子密度由准中性自动从 n_i 推出），n_i 是离子数密度
k = stix(B=B, w=2e5 * u.rad / u.s, ions=Particle("p+"), n_i=n_i, theta=theta)
# 返回四支波数（O/X/R/L 模式，单位 rad/m；含 evanescent 复值）
```

`stix` 求解 Stix 1992 冷等离子体色散关系（由 SDP 张量元组装的关于 $k^2$ 的双二次方程），给定频率 $\omega$ 与传播角 $\theta$ 返回波数。配套工作流：先用 `cold_plasma_permittivity_SDP` 看 CMA 图确定感兴趣的模式分支（O/X/S/Alfvén/快慢磁声波），再用 `stix` 算具体 $k(\omega)$。官方教程 [Stix Dispersion Solver](https://docs.plasmapy.org/en/stable/notebooks/dispersion/stix_dispersion.html) 完整复现了平行传播三种分支。

### 21.1.1 返回值与多支解的辨认

Stix 方程对 $k^2$ 是二次的——`stix(B, w, ions, n_i, theta)` 直接返回**四支波数**数组（`rad/m`，顺序为 O/X/R/L 四种模式，与本地 docstring 为准）。辨认纪律：① 平行传播（θ=0）下 O/X 两支与 R/L 两支分别对应四个解析式，用它们标定返回顺序；② 复波数出现意味着该频率下波是消逝的（evanescent，位于截止与共振层之间）——这不是错误而是物理，画 $k(\omega)$ 曲线时如实画出 $\mathrm{Im}\,k\neq0$ 区间；③ 波数求解的逆问题（给定 k 求 ω）需要自己在外层做求根循环（scipy.optimize.brentq 包住 `stix`），这是冷等离子体工具链少有的需要自补的胶水代码。

### 21.2 双流体色散关系 two_fluid

```python
from plasmapy.dispersion.analytical.two_fluid_ import two_fluid

result = two_fluid(B=8.3e-9 * u.T, n_i=5e6 * u.m**-3, T_e=1.6e6 * u.K,
                   T_i=4.1e5 * u.K, ion="p+", theta=25 * u.deg,
                   k=1e-6 * u.rad / u.m)           # 注意 k 单位必须是 rad/m
result['alfven_mode'], result['fast_mode'], result['acoustic_mode']   # dict 取值
# 也可 result.get('alfven_mode')；three keys: fast_mode / alfven_mode / acoustic_mode
```

基于 Bellan 2012（含 Stringer 1963 低频极限）的双流体色散关系，把快/慢磁声波、Alfvén 波、离子回旋波统一到一个方程中，返回各模式分支。与 `stix` 的分工：`stix` 是冷等离子体（无温度）、高低频通吃；`two_fluid` 含有限温度修正但限于低频。输入既可给 $\omega$ 求 $k$，也可给 $k$ 求 $\omega$（方向性参数以本地 docstring 为准）。

### 21.2.1 stix 与 two_fluid 的参数对齐细节

两个解析求解器的参数表高度相似但语义有别，混用时三个对齐点：

1. **密度参数**：`stix` 用单个 `ions=Particle(...)`（如 `Particle("p+")`）与 `n_i`（离子数密度，电子密度由准中性自动推出）；`two_fluid` 同样用 `ion`+`n_i`——两者都把电子密度从离子密度自洽推出，切勿再喂入电子密度；
2. **角度**：`theta` 是波矢与 B 的夹角（`u.deg` 或 `u.rad` 都收）；平行传播（θ=0）下 `two_fluid` 退化分支与 `stix` 的 R/L 两支一致，可作交叉验证；
3. **温度**：`stix` 无温度参数（冷等离子体）；`two_fluid` 的 `T_e/T_i` 进声速与压强项——两解的一致性检验只在无温极限（T→0）下做才有意义。

建议的联用顺序：`cold_plasma_permittivity_SDP` 画 CMA 图定分支 → `stix` 定冷分支波数 → `two_fluid` 加温度修正 → 需要阻尼再上 `hollweg`/`kinetic_alfven`（第 22 章）。每一层只解决上一层没覆盖的物理，逐层叠加而不是一步到位。

### 21.3 MHD 波类族 mhd_waves（新 API）

```python
from plasmapy.dispersion.analytical.mhd_waves_ import mhd_waves, AlfvenWave, FastMagnetosonicWave, SlowMagnetosonicWave
import astropy.units as u

# 工厂用法（推荐）：给参数，返回 MHD_Waves 命名元组（三元素，按
# alfven_wave / fast_magnetosonic_wave / slow_magnetosonic_wave 顺序）
waves = mhd_waves(B=8.3e-9 * u.T, density=5e6 * u.m**-3 * 1.67e-27 * u.kg,
                  T=1.6e6 * u.K, ion="p+")     # 注意：单温度 T（关键字，不是 T_e/T_i）
alfven, fast, slow = waves                      # 位置解包到三个波对象
alfven.alfven_speed                 # vA
fast.sound_speed, slow.sound_speed  # c_s 分支
# 也可直接实例化某一支
alf = AlfvenWave(B=8.3e-9 * u.T, density=8.35e-21 * u.kg/u.m**3, ion="p+")
```

类族结构：抽象基类 `AbstractMHDWave` 定义公共属性（`alfven_speed`、`sound_speed`、`gamma_e/gamma_i`），三个具体类实现各自相速度与色散面。工厂 `mhd_waves(...)` 一次构造三支并打包返回——这比老式的手写 $v_A=\sqrt{B^2/\mu_0\rho}$ 更不易出错，且温度自动进声速。⚠ 新 API，`|expect-api-changes|`。

### 21.4 MHD 波类族的完整属性清单

```python
waves = mhd_waves(B=8.3e-9 * u.T, density=8.35e-21 * u.kg / u.m**3,
                  T=1.6e6 * u.K, ion="p+")     # 单温度 T（关键字）
alfven, fast, slow = waves

# 三支波共享的基础速度
alfven.alfven_speed      # vA = B/√(μ0ρ)
alfven.sound_speed       # c_s（含 gamma_e/gamma_i 组合，可传参覆盖）
fast.magnetosonic_speed  # √(vA² + c_s²) 型组合速度

# 每支波的色散查询（k 给定 → ω；或反向，以本地 docstring 为准）
fast.omega? / fast.dispersion_function?   # 属性名随版本演进，help(fast) 查看
```

使用建议：教学/快速估算直接用工厂 + 基础速度属性；严格色散分析（需要 $\omega(k)$ 曲线族）用第 21.1–21.2 节的 `stix`/`two_fluid`——MHD 类族是"常量速查层"，不是完整求解器，这个定位不要混淆。

## 第 22 章 数值色散解

### 22.1 Hollweg 双流体求解器 hollweg

```python
from plasmapy.dispersion.numerical.hollweg_ import hollweg
import astropy.units as u

b0 = 8.3e-9 * u.T
n0 = 5e6 * u.m**-3
k = (1e-7 + 1e-6j) * u.m**-1    # 复波数（含阻尼/增长）
result = hollweg(B=b0, n_i=n0, T_e=1.6e6 * u.K, T_i=4.1e5 * u.K,
                 ion="p+", k=k, theta=25 * u.deg, gamma_e=5 / 3, gamma_i=5 / 3)
# 返回复频率（实部=振荡，虚部=阻尼率）
```

Hollweg 1997 双流体数值色散关系：在 `two_fluid` 解析框架上加入有限拉莫尔半径（FLR）修正，能给出复频率（阻尼/增长）。适合分析接近离子回旋尺度的波（$k\rho_i\sim1$），是解析 `two_fluid` 与完整动理学求解器之间的中间台阶。

### 22.2 kinetic_alfven 动理学 Alfvén 波

```python
from plasmapy.dispersion.numerical.kinetic_alfven_ import kinetic_alfven

result = kinetic_alfven(B=b0, n_i=n0, T_e=1.6e6 * u.K, T_i=4.1e5 * u.K,
                        ion="p+", k=1e-5 * u.m**-1, theta=89.8 * u.deg)
```

基于 Hirose 2004 的动理学 Alfvén 波求解：近垂直传播（$\theta\to90°$）、$k_\perp\rho_i\gtrsim1$ 区间，包含电子沿力线响应与离子有限拉莫尔轨道效应，输出复频率。典型应用：磁重联/日冕加热中 KAW 的色散与阻尼谱。与第 20 章 $Z$ 函数的关系：求解器内部正是用 `plasma_dispersion_func` 在复平面迭代求根。

### 22.2.1 两个数值求解器的收敛与调试

数值色散求解器的常见故障模式与定位：

1. **不收敛/多根**：给定 $\theta$ 与 $k$ 后方程可能有多支解——返回值是"最靠近初猜的那支"，初猜由内部算法决定；怀疑拿错分支时，扫 $\theta$ 从小到大连续算，看 $\omega$ 曲线是否连续（跳变即分支切换）；
2. **复频率的解读纪律**：$\mathrm{Im}\,\omega<0$ 是阻尼（正常）、$\mathrm{Im}\,\omega>0$ 是增长——增长解必须先检查物理（有自由能的驱动才可能有增长），数值伪增长通常源于 $k$ 或 $\theta$ 超出求解器渐近适用域；
3. **参数域边界**：`hollweg` 要求 $k\rho_i\lesssim1$、`kinetic_alfven` 要求近垂直（$\theta\gtrsim85°$）——越界不报错但结果失去物理意义，调用前先按第 9.5 节的尺度比自查。

与实验/仿真的对接：KAW 色散曲线的斜率段直接对应观测到的"波包色散展宽"——把求解器输出与 FLASH MHD 快照的波谱（Fourier 诊断）并排画，是判定"是否进入动理学尺度"的实用检查。

### 22.3 求解器选型速查

| 场景 | 接口 |
|---|---|
| 冷等离子体任意角传播、O/X 波分析 | `stix`（配 `cold_plasma_permittivity_SDP`） |
| 低频三支 MHD 波相速度速查 | `mhd_waves` 工厂 |
| 含温度的双流体低频波 | `two_fluid` |
| 离子回旋尺度、需要阻尼率 | `hollweg` |
| KAW（近垂直、$k\rho_i\sim1$） | `kinetic_alfven` |
| 自写介电函数求根 | `plasma_dispersion_func` + scipy |

### 22.4 动手示例：从色散函数到朗道阻尼率

把第四篇的工具串起来的最小完整例子——Langmuir 波的玻姆-格罗斯色散与朗道阻尼：

```python
import numpy as np
import astropy.units as u
from plasmapy.dispersion import plasma_dispersion_func
from plasmapy.formulary import plasma_frequency, thermal_speed, Debye_length

n_e, T_e = 1e18 * u.m**-3, (50 * u.eV).to(u.K, equivalencies=u.temperature_energy())
wp = plasma_frequency(n_e)
vth = thermal_speed(T=T_e, particle="e-", method="most_probable")
lambda_D = Debye_length(T_e, n_e)

# 对给定 k 扫 omega，找介电函数实部零点（Langmuir 波）
k = 1e4 * u.m**-1
zeta = lambda w: (w / (np.sqrt(2) * k * vth.si.value)).decompose().value
# eps = 1 + 1/(k^2 λD^2) (1 + ζ Z(ζ))；实现留作练习，模板见官方色散函数教程
```

工程要点：阻尼率 $\gamma=-\mathrm{Im}\,\varepsilon/\partial(\mathrm{Re}\,\varepsilon)/\partial\omega$ 在实轴附近取 $Z$ 的解析延拓值——`plasma_dispersion_func` 对小虚部输入稳定；$k\lambda_D\gtrsim0.3$ 后强阻尼、Langmuir 波不复存在（玻姆-格罗斯 $\omega^2\approx\omega_p^2+3k^2v_{th}^2$ 的适用条件），这给 Thomson 诊断的 $k$ 选择划了界（衔接第 29 章）。

---

# 第五篇 等离子体对象与模拟

## 第 23 章 等离子体对象体系

### 23.1 模块真实构成（2026.2.0）

⚠ **重要更正**：网上大量旧教程里的 `Plasma3D` 与 `PlasmaBlob` 类在 2026.2.0 **已经不存在**（`from plasmapy.plasma import Plasma3D, PlasmaBlob` 会 `ImportError`）。`plasma` 子包当前的真实导出是：

```python
import plasmapy.plasma as pp
# 真实导出（节选）：BasePlasma, GenericPlasma, Plasma, HarrisSheet,
#                   ForceFreeFluxRope, equilibria1d, cylindrical_equilibria,
#                   sources, grids, plasma_factory, plasma_base, exceptions
```

也就是说，`plasma` 子包只提供**抽象基类 + 若干具体平衡位形 + 工厂**，不再提供"网格化均匀等离子体容器"。真正承载网格化场量、并被第 26 章粒子追踪器消费的，是 **`plasmapy.plasma.grids.CartesianGrid`**（见第 24 章）。

### 23.2 抽象基类与工厂：BasePlasma / GenericPlasma / Plasma

```
BasePlasma                # 抽象基类：约定"等离子体由若干组分构成"，访问器为抽象方法
 └─ GenericPlasma         # 通用实现骨架（访问器仍为占位 NotImplementedError）
Plasma                    # 工厂：按关键字参数返回 GenericPlasma 子类实例
```

```python
from plasmapy.plasma import Plasma
import astropy.units as u

p = Plasma(density=1e20 * u.m**-3, T=1e6 * u.K)   # 返回 GenericPlasma 实例
type(p).__name__                                  # 'GenericPlasma'
```

⚠ 工厂返回的 `GenericPlasma` 的访问器（`electron_density()`、`electron_temperature()`、`ion_density()`、`ion_temperature()`、`average_ionization()`）在 2026.2.0 里仍是**抽象占位**——不带具体平衡参数时调用会抛 `NotImplementedError`。所以 `Plasma(density=, T=)` 在这里**不能**当作可用的标量状态容器；它只是框架入口。要做"标量等离子体参数"计算，直接用 `plasmapy.formulary` 的函数（`mass_density`、`thermal_pressure`、`beta` 等）即可，不必绕道此对象。

### 23.3 具体平衡位形：HarrisSheet / ForceFreeFluxRope

`plasma` 子包真正能用的是若干**具体平衡位形**类。以磁重联常用的 Harris 电流片为例：

```python
from plasmapy.plasma import HarrisSheet
import astropy.units as u

# 参数：B0（片外磁场）、delta（半厚度）、P0（片外等离子体压强）
sheet = HarrisSheet(B0=1 * u.T, delta=0.1 * u.m, P0=1 * u.Pa)
sheet.magnetic_field(0 * u.m)        # 中心面磁场（T），返回 Quantity
sheet.current_density(0 * u.m)       # 片电流密度（A/m²）
sheet.plasma_pressure(0 * u.m)       # 片内等离子体压强（Pa）
```

`HarrisSheet` 的属性 `B0 / delta / P0` 在构造后可直接读取；`magnetic_field` / `current_density` / `plasma_pressure` 是**按空间坐标求值的方法**（传入 1D 位置 Quantity）。同族的 `ForceFreeFluxRope`（无力通量绳）、以及 `equilibria1d`、`cylindrical_equilibria` 子模块里的 1D / 柱对称平衡，用法类似——它们服务于磁层/日冕/实验室磁约束场景，本工作区的激光等离子体（FLASH 输出）一般不走这条线，直接用 CartesianGrid 即可。

### 23.4 openPMD HDF5 读取

`plasma.sources` 下提供按 openPMD 标准读 HDF5 快照的入口（依赖 h5py），可把 PIC/流体代码的输出转入 PlasmaPy 生态。本工作区 FLASH 的 HDF5 输出**不是** openPMD 格式，直接读取会抛 `DataStandardError`，需先转换元数据结构（或改用第 24 章的 `CartesianGrid.add_quantities` 手动装载 FLASH 场）。

### 23.5 何时用 plasma 子包，何时直接用 Grid

经验法则：**要"解析平衡位形"用 `plasmapy.plasma` 的具体平衡类（HarrisSheet 等）；要"承载网格化场量并跑粒子"必须用 `CartesianGrid`（第 24 章）**。`Plasma`/`GenericPlasma` 不是网格容器，第 26 章的 `ParticleTracker` 也只接受 `CartesianGrid`，不接收 `BasePlasma`/`GenericPlasma` 对象。两者分工清晰，不要混用。

## 第 24 章 网格与平衡位形

### 24.1 网格类 grids.py

```python
from plasmapy.plasma.grids import CartesianGrid, NonUniformCartesianGrid
import astropy.units as u
import numpy as np

# 构造：三个 3D meshgrid 坐标数组（先造一维轴再 meshgrid）
ax = np.linspace(0, 1, 64)
x, y, z = np.meshgrid(ax, ax, ax, indexing="ij")
g = CartesianGrid(x * u.mm, y * u.mm, z * u.mm)
# 非均匀网格：各轴节点任意分布，同样给三维坐标数组
axn = np.concatenate([np.linspace(0, 0.8, 20), np.linspace(0.81, 1.0, 44)])
xn, yn, zn = np.meshgrid(axn, axn, axn, indexing="ij")
gn = NonUniformCartesianGrid(xn * u.mm, yn * u.mm, zn * u.mm)

g.pts0, g.grids          # 坐标网格 (nx,ny,nz) 与堆叠形式 (3,nx,ny,nz)
g.ax0, g.dax0            # 一维轴与该轴间距（间隔属性为 dax0/dax1/dax2）
g.shape, g.is_uniform, g.grid_resolution, g.quantities
g.add_quantities(rho=np.ones((64, 64, 64)) * u.kg / u.m**3)   # 字典式关键字传参！
g["rho"]                 # 取用；插值用 g.volume_averaged_interpolator / nearest_neighbor_interpolator
```

- `CartesianGrid`（`is_uniform=True` 自动判定）与 `NonUniformCartesianGrid` 都继承 `AbstractGrid`；底层是 xarray 数据容器（依赖 pandas/xarray），序列化依赖 h5py；
- **插值器是粒子追踪的关键**：`volume_averaged_interpolator("E_x", pos)` 与 `nearest_neighbor_interpolator` 分别对应第 26 章 `field_weighting` 的两种模式，位置入参为 `(N,3)` Quantity；
- **数量注册机制**（`add_quantities(**kwargs)` 字典式关键字传参，键名按 `"<场名>_<分量>"` 约定）让自定义场（比如从 FLASH 快照插出来的 B、E）能直接挂上网格——矢量场注册三个分量。

### 24.1.1 两种网格类的详细对比

| 特性 | CartesianGrid | NonUniformCartesianGrid |
|---|---|---|
| 构造输入 | 各轴宽度 + 均分点数 `num` | 各轴节点数组 + 点数 |
| `grid_spacing` | 标量（均匀 Δx） | 逐点数组 |
| 内存 | 紧凑（存范围即可） | 全格点存储（O(N)） |
| 插值器 | 两类都支持 | 两类都支持 |
| 典型用途 | 演示、解析场 | FLASH 剖面重采样、局域加密 |

选择原则：能用均匀就均匀——非均匀网格的插值器在剧烈变距区域（相邻格距比 >3）精度下降明显，且 CFL 上限由**最小**格距决定，非均匀网格会吃掉最大允许时间步。FLASH 数据的 Imported 网格通常是均匀的（1D 激光场景），直接 `CartesianGrid(width=..., num=...)` 对齐即可；2D AMR 数据才需要非均匀类。

### 24.2 平衡位形：HarrisSheet 与 ForceFreeFluxRope

```python
from plasmapy.plasma.equilibria1d import HarrisSheet
from plasmapy.plasma.cylindrical_equilibria import ForceFreeFluxRope
```

`HarrisSheet` 一维电流片（磁重联经典初始位形，B 随 x 变化满足 $\nabla\times B=\mu_0 J$）；`ForceFreeFluxRope` 轴对称无力磁绳（$\nabla\times B=\alpha B$）。两者都是"生成解析 B/J 场并挂到网格"的便捷类，常用于给粒子追踪与磁零点分析（第 27 章）造初始条件。

### 24.4 网格工作流的五步法

把任意场数据（FLASH 快照、解析公式）变成粒子追踪可用网格的固定流程：

1. **建网格**：`CartesianGrid`（均匀）或 `NonUniformCartesianGrid`（非均匀），给定域与分辨率——分辨率受第 26 章 CFL 限制约束；
2. **注册场**：`g.add_quantities("B_x", Bx_arr * u.T)` 逐分量注册；矢量场注册三个分量（命名约定 `"E_x"` 等由追踪器识别）；
3. **校验**：抽查 `g.volume_averaged_interpolator("B_x", test_points)` 与解析值/快照值的偏差，非均匀网格尤其要看插值器收敛；
4. **喂给追踪器**：`ParticleTracker(grids=g, field_weighting=...)`；
5. **一致性回归**：每次换场数据后重跑同一粒子束案例，对比落点统计（`fract_entered`、`vmax`）确认数据管道无回归。

从 FLASH HDF5 提取 B 场的建议：用本工作区 `output_pro` 的 data_loader 读快照 → 中心差分算 $\nabla\times B$ 得电流 → 网格重采样到 PlasmaPy 网格分辨率 → 注册。这套"FLASH 场 → PlasmaPy 网格"的桥接脚本是粒子诊断链路的地基，建议固化为独立模块并写场景测试文档。

### 24.5 插值器选择与精度验证

两种插值器 (`volume_averaged_interpolator` / `nearest_neighbor_interpolator`) 的选择不只是精度问题，还是**物理保真问题**：

- **体积平均插值**：等价于对场做低通滤波，光滑解析场（磁静力学解析解、平滑快照）首选；在激波/接触间断处会抹平梯度，导致粒子轨道缺少真实的锐利偏转；
- **最近邻插值**：保持原始格点值（不引入新值），锐利结构保真，但轨道对网格噪声敏感，CFL 约束也更紧；
- **验证方法**：构造一个有解析解的场景（如第 16 章磁偶极子），在两种插值下各跑一遍粒子追踪，对比回旋半径统计的偏差——偏差即插值误差的直接度量，这个案例可固化成回归测试。

### 24.3 官方教程

[Grids: Uniformly-Spaced Cartesian Grids](https://docs.plasmapy.org/en/stable/notebooks/plasma/grids_cartesian.html) 与 [Grids: Non-Uniform Grids](https://docs.plasmapy.org/en/stable/notebooks/plasma/grids_nonuniform.html) 覆盖了网格创建、场注册、插值全流程。

## 第 25 章 模拟框架抽象层

### 25.1 三个抽象基类

```python
from plasmapy.simulation import AbstractSimulation, AbstractTimeDependentSimulation, AbstractNormalizations
```

- `AbstractSimulation`：约定"模拟必须能 `run()`、能取 result"，并管理输入校验；
- `AbstractTimeDependentSimulation`：在上一基础上加入时间步进协议（`time`, `dt`, 推进函数），`ParticleTracker` 即其子类；
- `AbstractNormalizations`：归一化体系（把物理量无量纲化），PIC/双流体代码常见的单位变换在 PlasmaPy 中抽象成此类（如 `CartesianGrid` 的场量可导出一套 $\omega_p^{-1}$、$c/\omega_p$ 基准）。

三个基类的设计意图值得展开一层：PlasmaPy 用它们把"模拟"这个过于宽泛的词拆成**可校验的协议**——任何声称是"模拟"的类必须能 `run()` 并返回结果对象（基类强制），任何时间演化类必须暴露 `time/dt` 且推进函数是纯时间步进（子类强制）。这带来的实际收益是：自己写的实验性模拟器只要继承协议，就能直接接上项目的测试框架与 GA 优化回路（优化器只调 `run()`，不关心内部实现）——协议即解耦点。

### 25.2 何时自己继承

PlasmaPy 内置的模拟器只有粒子追踪一族；写双流体/PIC 原型时，继承 `AbstractTimeDependentSimulation` 可以白得时间循环骨架与校验，只需实现 `_advance_dt()`。⚠ `simulation.abstractions` 带 `|expect-api-changes|`，自行继承前先读本地 docstring 确认协议方法名。

### 25.3 归一化体系：AbstractNormalizations 详解

无量纲化是 PIC/双流体代码的标配，`AbstractNormalizations` 把"单位基准选取"抽象成可复用对象：给定基准密度、磁场等，派生 $\omega_p^{-1}$（时间单位）、$c/\omega_p$（长度单位）等基准量。价值在于**消除跨代码对比的单位换算错误**——FLASH（SI）与自写无量纲代码对表时，用同一 Normalizations 对象导出两边的量，换算链只写一次。自定义模拟器继承时，把基准量声明为构造参数而非硬编码常量，归一化即随输入自动适配（第 35.4 节"口径显式声明"原则的框架级体现）。

## 第 26 章 粒子推进与轨迹追踪（重点）

### 26.1 Boris 积分器

```python
from plasmapy.simulation.particle_integrators import BorisIntegrator, RelativisticBorisIntegrator
```

Boris 算法是带电粒子在 E/B 场中推进的事实标准：二阶精度、**长时间守恒相空间体积**（不 artificially 加热），相对论版改推进动量。两者都实现了 `__call__` 式单步推进接口（推一个粒子群一步），适合教学与自写循环；完整轨迹追踪请用下一节的 `ParticleTracker`（它内置了 Boris 推进 + 网格插值 + 终止/存档管理）。

### 26.2 ParticleTracker 全解

```python
import astropy.units as u
import numpy as np
# 注意导入路径：ParticleTracker 类在深层模块，不在 plasmapy.simulation 顶层
from plasmapy.simulation.particle_tracker.particle_tracker import ParticleTracker
from plasmapy.simulation.particle_tracker.termination_conditions import (
    TimeElapsedTerminationCondition, NoParticlesOnGridsTerminationCondition,
    AllParticlesOffGridTerminationCondition)
from plasmapy.simulation.particle_tracker.save_routines import (
    DoNotSaveSaveRoutine, SaveOnceOnCompletion, IntervalSaveRoutine)
from plasmapy.simulation import CFL_limit_electromagnetic_yee

# 1) 初速度分布（准单能质子束）
v0 = np.zeros((10000, 3)) * u.m / u.s
v0[:, 2] = 1e7 * u.m / u.s

# 2) 构造追踪器（另有 particle_integrator/dt/dt_range/verbose 可选参数）
tracker = ParticleTracker(
    grids=my_grid,                          # 第 24 章的 CartesianGrid（含 E、B 场）
    termination_condition=TimeElapsedTerminationCondition(1e-9 * u.s),
    save_routine=SaveOnceOnCompletion(),
    field_weighting="volume averaged",      # 或 "nearest neighbor"
)
tracker.load_particles(x0, v0, particle="p+")     # x0: (N,3) 初始位置 Quantity；参数名是 particle

# 3) 推进与统计
tracker.run()
tracker.num_particles_tracked, tracker.num_entered, tracker.fract_entered
tracker.particles_on_grid, tracker.vmax   # 仍在网格内的索引 / 最大速度（能量上限检查）
```

设计四要素，逐个说清：

1. **`field_weighting`**：场插值方式。"volume averaged"（体积平均，二阶平滑）适合光滑解析场；"nearest neighbor"（最近邻，一阶）适合锐利梯度（激波、箔面）。两种模式与第 24 章两个插值器一一对应；
2. **终止条件（三选多）**：`TimeElapsedTerminationCondition(Δt)`（跑够物理时间）、`NoParticlesOnGridsTerminationCondition`（网格清空）、`AllParticlesOffGridTerminationCondition`（全部出界）；可组合传入列表，任一满足即停。终止原因记录在结果里，事后可查；
3. **存档例程（三种）**：`DoNotSaveSaveRoutine`（只算不存）、`SaveOnceOnCompletion`（结束时一次写 HDF5）、`IntervalSaveRoutine(Δt)`（按时间间隔写快照）——底层用 h5py 写 HDF5，粒子位置/速度/时间全部入档，可供后续读出画轨迹；
4. **时间步与 CFL**：自适应步（`is_adaptive_time_step`）按场强度自动缩步长；显式电磁推进的稳定性上界由 `CFL_limit_electromagnetic_yee` 给出（Yee 网格 CFL 条件），网格过粗时会得到警告——这与 FLASH/PIC 的 CFL 直觉一致。

统计属性速查：`num_particles_tracked`（总数）、`num_entered`/`fract_entered`（曾入网格的比例）、`particles_on_grid`/`on_any_grid`（在场内）、`num_particles_stopped`（被 `add_stopping` 能损模型停下的）、`num_particles_removed`（出界移除的）。

⚠ **兼容性关键**：2026.2.0 的 `ParticleTracker` 只接受 **grid 体系**（第 24 章）；旧教程里传 `BasePlasma` 对象的写法已废弃——构造时给 Plasma 对象会直接报错并提示回退 2023.5.1。

### 26.5 时间步进与精度控制详解

`ParticleTracker` 的时间步控制有三种形态，理解它们的分工能避免大量"轨迹不收敛"类问题：

1. **同步步进**（`is_synchronized_time_step`）：所有粒子用同一 $\Delta t$，最直观，适合均匀场与单能束；
2. **自适应步进**（`is_adaptive_time_step`，`setup_adaptive_time_step` 配置）：按局域场强与粒子速度动态缩步——强场区自动加密，是默认推荐；但注意自适应步会在粒子间失同步，统计量（`particles_on_grid` 等）按"每个粒子各自的时间"解释；
3. **CFL 上限**：`CFL_limit_electromagnetic_yee` 给出显式电磁推进在给定网格上的稳定性上限 $\Delta t \le \mathrm{CFL}\cdot\Delta x/c$——即使自适应，也不应超过该值；网格太粗时先加密网格再谈精度。

调试口诀：轨迹发散 → 先查 CFL 与场数据 NaN（插值器遇到未注册区域返回 NaN 会静默污染轨道）；能量漂移 → 确认用 Boris 族积分器（守恒性好）而非自写 Euler；粒子"消失" → 出界移除（`num_particles_removed`）而非 bug，把终止条件从 `AllParticlesOffGrid` 换成 `NoParticlesOnGrids` 并加大域再试。

### 26.5.1 与 FLASH 工作流的完整对接清单

把 ParticleTracker 嵌入 PhySimX 数据管道的检查单（按顺序执行）：

1. **场提取**：FLASH 快照 → `output_pro` 提取 E/B（或由 $\nabla\times B$ 构造电流自洽场）；
2. **网格对齐**：重采样到 CartesianGrid（第 24.4 节），分辨率满足 CFL（第 26.5 节）；
3. **粒子源定义**：初始位置/速度分布（单能束、热分布用第 12 章分布函数采样），固定随机种子；
4. **终止与存档配置**：物理时间终止 + IntervalSaveRoutine（间隔取回旋周期的 1/10 量级）；
5. **零场回归**：场清零重跑，落点统计应复现初始分布（几何正确性验收）；
6. **物理验证**：均匀场下回旋半径/周期与 `gyroradius`/`gyrofrequency` 解析值对账（2% 内）；
7. **生产运行 + 统计**：`fract_entered`/`vmax` 记录进场景测试文档。

这份清单把第 24–26 章的粒子链路收敛为可勾选的验收流程，适合直接作为新场景的 SOP。

### 26.6 最小可运行完整案例（构造型）

```python
import numpy as np
import astropy.units as u
from plasmapy.plasma.grids import CartesianGrid
from plasmapy.simulation.particle_tracker.particle_tracker import ParticleTracker
from plasmapy.simulation.particle_tracker.termination_conditions import TimeElapsedTerminationCondition
from plasmapy.simulation.particle_tracker.save_routines import SaveOnceOnCompletion

# 1) 网格：1 cm^3 均匀网格 + 纯 Bz 磁场（演示回旋）
ax = np.linspace(0, 1, 32)
X, Y, Z = np.meshgrid(ax, ax, ax, indexing="ij")
g = CartesianGrid(X * u.cm, Y * u.cm, Z * u.cm)
Bz = 0.5 * np.ones_like(X.si.value) * u.T
g.add_quantities(B_x=0 * Bz, B_y=0 * Bz, B_z=Bz)

# 2) 追踪器：1 ns、结束时存档
tracker = ParticleTracker(
    grids=g,
    termination_condition=TimeElapsedTerminationCondition(1 * u.ns),
    save_routine=SaveOnceOnCompletion(),
)
x0 = np.c_[np.zeros(100), np.zeros(100), np.zeros(100)] * u.mm
v0 = np.zeros((100, 3)) * u.m / u.s
v0[:, 0] = 1e6 * u.m / u.s                        # 垂直 B 的速度 → 回旋
tracker.load_particles(x0, v0, particle="p+")
tracker.run()
print(tracker.num_particles_tracked, tracker.vmax)
```

此例跑通即验证了"网格注册 → 终止条件 → 存档 → 统计"全链路；将 Bz 换成 FLASH 快照场即进入生产用法（第 24.4 节五步法）。

### 26.7 排错决策表

| 症状 | 首查 | 次查 | 处置 |
|---|---|---|---|
| 轨迹 NaN | 场数据含 NaN/未注册区域 | 粒子初始位置在域外 | `np.isfinite` 全场预检；扩域或裁剪初始分布 |
| 轨迹发散/能量暴增 | CFL 上限 | 场梯度异常大（插值毛刺） | 换 volume averaged 插值；加密网格 |
| 粒子"全消失" | 终止条件语义 | 出界即移除是正常行为 | 读 `num_particles_removed`；改用 NoParticlesOnGrids 终止 |
| `vmax` 超物理预期 | 积分器非 Boris 族 | 时间步过大 | 确认默认 Boris；减步或自适应 |
| 存档文件读不出 | h5py 版本 | 存档例程未触发 | 检查 save_routine 是否 DoNotSave；h5py ≥3.11 |
| 进度条不动 | 粒子数为 0 | load_particles 形状错 | x0/v0 必须是 (N,3) Quantity |

这张表把 ParticleTracker 的绝大多数"疑难杂症"收敛成 5 分钟内的定位流程，建议随项目脚手架一起维护。

### 26.8 规模与性能参考

单机（24 核级工作站）经验参考值：10⁵ 粒子 × 10⁴ 步（10⁶ 粒子·步）量级的追踪在分钟级完成；瓶颈通常不在推进而在**插值**（每步每粒子 6 次场查询）—— hence 最近邻插值明显快于体积平均。提效手段按序：① 减少存档频率（I/O 常占 30%+）；② 精简网格分辨率（CFL 允许内）；③ DoNotSave 粗扫 + SaveOnce 精扫两级流程；④ 粒子分批串行天然可并行（分进程跑多批），无需包内并行支持。

### 26.3 add_stopping：能损通道

`tracker.add_stopping(...)` 挂载粒子能损模型（如与背景等离子体的碰撞慢化），配合 `num_particles_stopped` 统计可模拟"质子束在靶中减速沉积"的最小闭环；精确的 -dE/dx 数值用第 19 章 `Bethe_stopping` 自行计算后做查表。

### 26.4 与诊断射线照相的分工

`simulation.ParticleTracker` 是**通用轨道求解器**（给场、追轨迹、给统计）；`diagnostics.charged_particle_radiography.Tracker`（第 30 章）是**面向质子照相的专用封装**（源/探测器几何、合成 radiograph）。前者造工具，后者出图像，不要混用。官方教程：[Particle Tracker](https://docs.plasmapy.org/en/stable/notebooks/simulation/particle_tracker.html)。

---

# 第六篇 分析与诊断

## 第 27 章 磁零点与曲线拟合（analysis 基础件）

### 27.1 磁零点分析 nullpoint.py

磁零点是 $\mathbf{B}=0$ 的空间点——磁重联、磁绳拓扑的枢纽结构。模块提供两类接口：

```python
from plasmapy.analysis.nullpoint import (
    null_point_find, uniform_null_point_find, trilinear_approx, NullPoint,
)
import numpy as np
import astropy.units as u

# 均匀网格情形：直接喂 B 场三维数组（Bx, By, Bz）
nulls = uniform_null_point_find(Bx, By, Bz)     # 返回 NullPoint 对象列表
for p in nulls:
    p.loc                                        # 零点坐标
    p.jacobian_matrix                            # ∇B 特征值 → A/B/C/A1/B1/C1 型拓扑分类
# 非均匀网格/任意函数：先建三线性插值器
interp = trilinear_approx(Bx, By, Bz, grid)      # 返回可调用对象
nulls2 = null_point_find(interp, x_min, x_max, y_min, y_max, z_min, z_max)
```

算法骨架：粗网格扫描符号变化 → 二分细化定位 → 三线性插值算雅可比矩阵 → 按 $\nabla B$ 特征值分类（A/B/C/A1/B1/C1 六类零点拓扑）。与第 24 章 `ForceFreeFluxRope` 配合可以完整演示"磁绳中的零点提取"。⚠ 模块带 `|expect-api-changes|`；异常类 `NullPointError`（雅可比奇异）、`NonZeroDivergence`（数值散度非零）与警告 `MultipleNullPointWarning`、`NullPointWarning` 均在同模块，`except NullPointError` 可精准兜住定位失败。官方教程：[Null Point Finder](https://docs.plasmapy.org/en/stable/notebooks/analysis/nullpoint.html)。

**六个拓扑类的直觉**：A 型（两正一负特征值）与 A1 型是"镜像对"，分别对应磁通汇聚/发散的零点；B/B1 型类似但特征值为复对（螺旋结构）；C/C1 型是纯螺旋零点。重联物理中 X 点（鞍点结构）对应雅可比有正负特征值对的情形——分类标签是判断"这个零点会不会演化成重联位点"的第一道筛子。网格分辨率要求：零点邻域至少要有 3–5 个格点覆盖特征尺度，否则三线性雅可信度不足——粗扫出候选后先局部加密再精定位，比全网格高分辨率省一个量级的计算。

### 27.2 拟合函数 fit_functions.py

```python
from plasmapy.analysis.fit_functions import Linear, Exponential, ExponentialPlusLinear, ExponentialPlusOffset
import numpy as np

f = ExponentialPlusOffset()
result = f(xdata, ydata)         # 内部委托 lmfit 拟合
result.best_fit_params           # 拟合参数（带误差）
result.r_squared
y_fit = f(x_fit, result.best_fit_params)   # 用拟合参数外推
```

四个预设函数类（线性、指数、指数+线性、指数+偏置）统一封装 lmfit 的模型构建、初值猜测与结果对象，免去每次手写 lmfit.Model 的模板代码。朗缪尔探针旧模块内部即用它们外推电子/离子电流；自写诊断标定（暗电流扣除等）直接受益。官方教程：[Fit Functions](https://docs.plasmapy.org/en/stable/notebooks/analysis/fit_functions.html)。

### 27.3 磁零点分析的完整实战流程

以第 24 章 `ForceFreeFluxRope` 生成的磁绳场为例，零点提取的完整链条：

1. **造场**：磁绳解析场挂到均匀网格（`uniform_null_point_find` 的输入要求三维规则网格上的 (Bx,By,Bz) 数组）；
2. **粗扫**：先在降采样网格上跑一遍，估计零点数量与位置量级——直接在全分辨率上跑会因符号变化区域过多而拖慢；
3. **精定位**：全分辨率重跑，`NullPoint` 对象给出坐标与雅可比矩阵；
4. **拓扑分类**：对雅可比特征值分类（A 型：两正一负等），零点的"汇/源/鞍"性质决定重联电流聚集位置；
5. **验证**：零点邻域的 $\nabla\cdot B$ 应接近机器精度（`NonZeroDivergence` 异常即此检查的运行时版本），不满足说明插值或数据有问题。

与重联研究的衔接：零点位置 + 分类标签随时间的演化序列，是判定磁重联事件（X 点崩溃、磁绳合并）的直接观测量——把这套流程接到 FLASH MHD 快照序列上，可自动化提取重联事件表，作为粒子加速分析的输入。

## 第 28 章 扫频朗缪尔探针（新旧 API 迁移）

### 28.1 现行 API：analysis.swept_langmuir

```python
from plasmapy.analysis.swept_langmuir import (
    find_floating_potential, find_ion_saturation_current,
    sort_sweep_arrays, merge_voltage_clusters, check_sweep,
)
import astropy.units as u
import numpy as np

# 数据预处理：排序 + 合并重复电压簇 + 合法性检查
v, cur = sort_sweep_arrays(voltage, current)
v, cur = merge_voltage_clusters(v, cur)
check_sweep(v, cur)     # 抛错则数据不合规（非单调/NaN 等）

# 悬浮电位（线性区拟合）
vf_res = find_floating_potential(v, cur)
vf_res.vf               # 悬浮电位（Quantity）
vf_res.fit              # 附带的线性拟合结果（含外推线）
# 离子饱和电流
isat_res = find_ion_saturation_current(v, cur)
isat_res.isat, isat_res.fit
```

返回对象 `VFExtras` / `ISatExtras` 携带拟合细节（拟合线参数、Applied 区间、R²），便于画图复查。整个子包是为取代旧 `diagnostics.langmuir` 而生的新实现（2023 起开发，2026.2.0 已稳定可用）。

**拟合方法说明**：`find_floating_potential` 在过渡区下端用线性拟合对（上升沿与离子饱和延伸线的交点）定位 $V_f$，区间自动选择算法会迭代剔除弯折段；`find_ion_saturation_current` 在足够负的偏压段做线性拟合取零点截距。两个函数都接受区间提示参数（手动指定拟合窗口）——自动选区对噪声敏感的数据（低信噪比、射频干扰）不可靠时，先画原始曲线人工定窗再传入。`sort_sweep_arrays` 的必要性常被低估：实测扫频数据往往电压非单调（回扫段）且有重复点，不预处理直接拟合会得到静默错误的结果——`check_sweep` 的报错信息会指出具体是哪类违规。

### 28.2 旧 API 与迁移对照 ⚠

`diagnostics.langmuir`（`swept_probe_analysis` + `Characteristic` 类）在 2026.2.0 中**每次 import 发 FutureWarning**，官方明确将移除。迁移对照：

| 旧（diagnostics.langmuir） | 新（analysis.swept_langmuir） |
|---|---|
| `swept_probe_analysis(probe_data)` 一步全算 | 分步：`find_floating_potential` / `find_ion_saturation_current`（电子温度/密度新实现陆续接入） |
| `get_floating_potential(probe_data)` | `find_floating_potential(...).vf` |
| `get_ion_saturation_current(...)` | `find_ion_saturation_current(...).isat` |
| `get_electron_temperature` / `get_electron_density_LM/OML` | 暂无直接替代，可自行组合 fit_functions 实现（或等待新 API 补齐） |
| `get_EEDF` | 无替代；Druyvesteyn 方法自写 |

建议：新代码一律用新 API；旧脚本按上表逐行替换，电子温度/密度部分暂时保留旧模块并静音警告（`warnings.filterwarnings("ignore", category=FutureWarning)`）直到迁移完成。官方教程：[Swept Langmuir Analysis: Floating Potential](https://docs.plasmapy.org/en/stable/notebooks/analysis/swept_langmuir/find_floating_potential.html)。

### 28.3 探针诊断的物理边界

朗缪尔探针分析默认被测等离子体满足：探针尺寸 ≫ Debye 长度（鞘层薄）、电子分布 Maxwellian、无强磁场（或磁化可忽略）。偏离这些条件时新旧 API 都只给"名义值"：强磁化下平行与垂直收集电流差异巨大（Braginskii 第 17 章的各向异性传导直接决定收集几何），非麦氏分布让指数拟合的"温度"只是斜率等价温度（kappa 分布场景衔接第 12 章）。本工作区如果把探针数据用于 FLASH 验证，建议在报告里同时给出悬浮电位、离子饱和电流与电子温度三个量各自的不确定度来源（拟合区间选择、鞘层修正、探针污染），并注明所用 API 版本——新旧 API 的数值差异本身也是一种系统误差来源。

## 第 29 章 汤姆逊散射诊断（重点）

### 29.1 谱密度合成 spectral_density

```python
from plasmapy.diagnostics.thomson import spectral_density
import astropy.units as u
import numpy as np

# 探针激光与几何（90° 散射：probe 沿 +x，收集沿 +y）
probe_wavelength = 532 * u.nm
wavelengths = np.linspace(500, 564, 2000) * u.nm   # 光谱仪波长扫描轴（与返回的 Skw 对齐）

# 单一电子种群 + 双离子种群（C 5+ / C 6+）示例
T_e = 300 * u.eV                        # 电子温度（标量；或多电子种群时给数组）
T_i = [100.0, 100.0] * u.eV             # 每个离子种群的温度（长度 = 离子种群数 Ni）
ions = ["C 5+", "C 6+"]
ifract = [0.6, 0.4]                     # 各离子种群的相对密度分数（须和为 1）
n = 5e18 * u.cm**-3                      # 总电子数密度

alpha, Skw = spectral_density(
    wavelengths, probe_wavelength, n=n,
    T_e=T_e, T_i=T_i, ions=ions, ifract=ifract,
    efract=[1.0],                        # 电子种群分数（单一种群 = [1.0]，须为序列而非标量）
    probe_vec=np.array([1, 0, 0]),        # 探针光方向
    scatter_vec=np.array([0, 1, 0]),      # 收集方向
)
# alpha = 平均散射参数（>1 集合散射，<1 非集合）；Skw = 谱密度（形状与 wavelengths 对齐，单位 s/rad）
```

**参数语义精读**（本地 v2026.2.0 签名与官方旧 notebook 不同，以本节为准）：

- `wavelengths`：**单一**波长轴（nm 注记）——EPW 与 IAP 特征在同一谱上呈现（集合区是双线结构、非集合区单峰），不再分双轴；
- `n`/`T_e`/`T_i`：关键字参数。**关键陷阱**：`T_e`/`T_i` 的数组维度对应**种群数**（Ne 个电子种群 / Ni 个离子种群），**不是空间分区**——不要把 FLASH 径向剖面采样点当数组传进去（本函数不支挰空间分区，要逐区算请在外层循环多次调用）。`efract`/`ifract` 是各电子/离子种群的相对密度分数，须各自**和为 1**（默认单一种群也要写成 `[1.0]`，不能写标量 `1.0`）；
- `ions` + `ifract`：离子种群列表与各组分的相对密度分数（D-T、H-He、C 5+/C 6+ 混合物在此配置）；`efract` 是电子密度分数（部分电离场景 <1）；
- `electron_vel`/`ion_vel`：分布漂移速度（可流动等离子体），形状 `(种群数, 3)`；
- `probe_vec`/`scatter_vec`：裸数组方向向量（自动归一化），散射角由两者夹角隐式确定；
- `instr_func`/`notch`：仪器函数卷积（生产拟合用）与杂光陷波滤片建模；
- **返回二元组 `(alpha, Skw)`**（顺序：先 `alpha` 散射参数，后 `Skw` 谱密度），**没有 `lam` 返回**——波长轴就是输入 `wavelengths`。这与官方旧教程（返回 Skw/lam 或 dict）的差异最大，调用处务必按 `(alpha, Skw)` 顺序接收；
- 另有 `spectral_density_lite`（裸数组快速版）供大规模扫描。

物理要点：合成谱自动按散射角与 $n/\lambda^2$ 判断**集合/非集合**散射区（$\alpha=1/(k\lambda_D)$）；`alpha` 即返回的第一个值，EPW 线形敏感于 $T_e, n_e$，IAP 线形敏感于 $T_i$ 与离子组分。本工作区 `demo_04`（碳等离子体 532 nm 90° 散射）即此接口，可直接对照。

### 29.2 谱拟合 spectral_density_model（lmfit 封装）

```python
from plasmapy.diagnostics.thomson import spectral_density_model
import lmfit

# 本地签名：spectral_density_model(wavelengths, settings, params)
# settings/params 分别承载"固定几何/物种配置"与"待拟合物理参数"（以本地 docstring 为准）
model = spectral_density_model(wavelengths, settings, params)
result = model.fit(measured_spectrum)     # lmfit MinimizerResult
result.best_values
```

依赖 lmfit（模型即 `lmfit.CompositeModel`）。⚠ 本地 2026.2.0 的 `spectral_density_model` 采用 `(wavelengths, settings, params)` 三段式签名，与官方旧教程的"关键字参数直传"写法不同——迁移旧拟合脚本时按此重构，配置/参数分离反而便于序列化。拟合流程与 FLYCHK 谱线拟合（Lyα/He-like 线比）在工程上同构：合成模型 + 最小化残差，但 Thomson 拟合的是连续谱线形、约束 T/n，而 FLYCHK 拟合线强度比、约束 T/n 及不透明度——两者可在同一实验谱上互为验证。官方教程：[Thomson Scattering: Spectral Density](https://docs.plasmapy.org/en/stable/notebooks/diagnostics/thomson.html)、[Fitting Thomson Scattering Spectra](https://docs.plasmapy.org/en/stable/notebooks/diagnostics/thomson_fitting.html)（注意官方页基于旧 API，参数传递方式按本节迁移）。

### 29.3 拟合实战要点与陷阱

1. **初值决定成败**：$T_e$ 初值偏一个量级会掉进错误极小值——先用 EPW 谱的峰间距粗估 $T_e$（离子声双峰间距对 $T_e$ 的近似解析关系），再喂给 lmfit；
2. **配置与参数分离**：本地三段式签名中 settings（几何、物种、仪器函数）与 params（待拟合的 T/n 等）分开——拟合时只动 params，settings 冻结并随结果存档（替代旧版 `doc_io=True` 写 HDF5 的功能），多区参数在 params 中按数组下标区分（`Te_0, Te_1, ...`）；
3. **集合/非集合判据**：$\alpha=1/(k\lambda_D)\gg1$ 集合（EPW/IAP 双结构清晰）、$\alpha\ll1$ 非集合（单宽峰）——拟合模型对两区自动切换，但输入的 $n_e$ 必须自洽，否则谱形错而拟合照常收敛（假收敛）；
4. **与 FLYCHK 的互检**：Thomson 给出连续谱约束的 (T, n)，FLYCHK 给出线谱约束的 (T, n, 不透明度)——两者在同一发次上的偏差是判读非均匀性/非麦氏效应的重要信号，建议在工作流中固定做交叉表。

### 29.4 从 demo_04 到生产拟合的差距

工作区 `demo_04_thomson_scattering.py` 只演示了 `spectral_density` 正演（合成谱绘图）；生产级拟合还需：实测谱的仪器函数卷积（IRENe/带宽）、背景扣除、多区几何映射、以及 `spectral_density_model` + lmfit 的参数界设置——建议按官方 [Fitting Thomson Scattering Spectra](https://docs.plasmapy.org/en/stable/notebooks/diagnostics/thomson_fitting.html) 教程扩展 demo，把"正演 demo"升级为"拟合 pipeline"再接入实验数据。

补充一点方法论：Thomson 拟合的参数可辨识性随数据质量急剧变化——单角度单能段通常只能同时辨 2 个参数（典型配对：T_e+ne 或 T_e+Ti），"一次拟全参数"在信息量不足时会收敛到无意义的协变谷。设计拟合策略时先做参数敏感性扫描（逐参数扰动看谱形响应），把"谱形不敏感"的参数钉死为常量——这与 FLYCHK 谱线拟合（第 29.2 节）的约束选择逻辑同源，可共用同一套敏感性分析脚本。

## 第 30 章 带电粒子射线照相

### 30.1 Tracker 与合成照相

```python
from plasmapy.diagnostics.charged_particle_radiography import Tracker, synthetic_radiograph
import astropy.units as u
import numpy as np

# 网格（第 24 章）需含 B、E 场
tracker = Tracker(
    grids={"B": my_grid},           # 含 B（可再加 "E"）场的网格字典
    source=source_axis,             # 源位置/方向（点源或扩展源）
    detector=detector_axis,         # 探测器位置/法向/尺寸
    field_weighting="nearest neighbor",
)
tracker.create_particles(nparticles=100000, particle="p+", energy=3 * u.MeV)
tracker.run()
hax, vax, hist = synthetic_radiograph(tracker, "both")   # 合成照相（2D 直方图）
```

工作流：源发射单能质子 → 穿过含场的网格（轨道由内置 Boris 推进）→ 打到探测器平面记录落点 → 落点直方图即"合成照相"。FieldName 变体（"source"/"detector"/"both"）对应不同投影平面；`synthetic_radiograph` 还能输出未偏转基准用于作差（场致偏转图）。

### 30.1.1 源与探测器的几何参数详解

`Tracker` 的两个几何对象是易错点，逐参数说明：

- **source**：点源给位置向量 + 发散半角；扩展源（实验中 Rp 莫尔条纹必需）给位置 + 源尺寸分布（均匀/高斯可选），`create_particles(nparticles=..., energy=..., distribution=...)` 控制初始能谱；
- **detector**：位置 + 法向 + 平面尺寸——**法向朝向决定落点符号**，法向指反了照片镜像，是最常见的"图对不上"原因；探测器不必垂直于源-场连线，斜置用于大视场；
- **能量选择**：质子能量决定"切片深度"——低能质子场致偏转灵敏但能损大（`add_stopping` 类修正），高能质子穿透性好但偏转弱；多能量联合（2–10 MeV 扫描）才能反演出场强绝对值而非仅分布形状。

调试顺序建议：先跑零场（B=E=0）确认照片是均匀斑（几何无误）→ 加单一场分量确认偏转方向 → 再上完整场。跳过前两步直接上真实场，几何错误与物理信号混在一起极难排查。

### 30.2 探测器叠层 Stack/Layer 与官方教程族

`detector_stacks.py` 的 `Stack`/`Layer` 模拟多层滤片/探测片（每层给定材质与厚度，能量-厚度响应由 stoping power 表核算，依赖 h5py），对应实验中的 RCF 堆叠诊断。官方教程族完整覆盖进阶用法：[粒子追踪照相](https://docs.plasmapy.org/en/stable/notebooks/diagnostics/charged_particle_radiography_particle_tracing.html)、[多层探测器](https://docs.plasmapy.org/en/stable/notebooks/diagnostics/charged_particle_radiography_film_stacks.html)、[自定义源分布](https://docs.plasmapy.org/en/stable/notebooks/diagnostics/charged_particle_radiography_particle_tracing_custom_source.html)、[网格调制（wire mesh）](https://docs.plasmapy.org/en/stable/notebooks/diagnostics/charged_particle_radiography_particle_tracing_wire_mesh.html)。

### 30.3 与 FLASH 的组合设想

把 FLASH 快照的 $\nabla\times\mathbf{B}$ / 电场插到 CartesianGrid（第 24 章 `add_quantities`），即可用本模块合成"FLASH 场 + 质子照相"的正演图像，用于实验照片（如 OMEGA/神光质子照相）的场反演对照——这是 PlasmaPy 诊断链对本项目最直接的增值点之一。

### 30.4 正演-反演闭环的工作流设计

质子照相的科研用法是"正演-反演"闭环，PlasmaPy 承担正演端：

1. **正演**：FLASH 快照场 → 网格注册 → `Tracker` + `synthetic_radiograph` 得合成照片；
2. **参数化反演**：实验照片与合成照片比较 → 调整场模型参数（如场强倍数、特征尺度）→ 重复正演至最优匹配——此循环外包给 lmfit 或 NSGA-II（衔接本工作区优化框架，把"照片残差"作为目标函数）；
3. **误差条**：对源尺寸、能散、探测器分辨率三个模糊量做扰动传播，每个参数化场模型给出一族合成照片，实验照片落在族内的置信度即反演可信度；
4. **能损修正**：`Stack`/`Layer`（多层探测器）的能-厚度响应用来把"探测到的"质子能谱反推到"进入探测器的"，此步在比较 RCF 各层信号时不可省。

工程提示：正演一次的成本主要在粒子数（10⁵ 起步），反演循环里固定粒子种子可消除蒙特卡罗噪声对目标函数的污染——否则优化器会把噪声当梯度。

## 第 31 章 时间序列分析

### 31.1 工具族一览与基本用法

```python
from plasmapy.analysis.time_series import ConditionalEvents, ExcessStatistics, running_mean, running_moment
import numpy as np

# 条件事件平均：给定触发阈值与参考信号，自动统计触发前后平均波形
ce = ConditionalEvents(
    counts=signal,              # 主信号（触发判定）
    reference=probe_signal,     # 参考信号（可选）
    tau=2e-4,                   # 事件窗半宽（秒）
    thresh=(0.5, None),         # 触发阈值区间
    dtau=1e-6,                  # 平滑步长
)
ce.n_events, ce.wall_times, ce.average
# 超阈统计：信号超过阈值的时间间隔分布
es = ExcessStatistics(signal, thresh=1.5)
es.over_threshold, es.time_over_threshold
# 滑动均值/矩
m = running_mean(signal, window_size=101)
mm = running_moment(signal, "std", window_size=101)
```

- `ConditionalEvents`：条件平均（conditional averaging）——湍流/爆发事件的"触发相平均"标准工具，输入是时间序列数组 + 阈值 + 窗宽；实现含双阈值（下/上）、时间平滑、事件重叠剔除；⚠ 带 `|expect-api-changes|`；
- `ExcessStatistics`：超阈时长/间隔统计（爆发率分析）；
- `running_mean`/`running_moment`：滑动窗口均值与各阶矩（"mean"/"std"/"skew"/"kurtosis"）。

对诊断数据处理（探针电流、光电倍增管信号）做爆发现象分析时，这组工具替代手写卷积循环，注意输入是**裸数组**（无量纲），时间窗参数单位按"采样间隔 × 样本数"理解。

### 31.2 条件平均的三个工程细节

1. **事件重叠**：两个触发事件时间窗重叠时默认合并处理（取决于实现版本），高触发率信号先看 `n_events` 与窗宽的乘积是否远小于信号总时长，否则统计独立性存疑；
2. **阈值选择**：`(下限, 上限)` 元组支持单边阈值（`(0.5, None)`）；阈值用信号分布的分位数（如 75%）比拍脑袋定值更可复现；
3. **参考信号**：`reference` 参数允许"用 A 触发、平均 B"——例如用光电倍增管触发、平均探针电流，这是诊断联动分析的标准用法。

滑动矩（`running_moment`）与条件平均配合：先滑窗去慢漂移（`running_mean` 后相减），再做条件平均，可显著压低低频噪声对事件波形的污染。

### 31.3 诊断数据处理的统一管道模式

把第六篇的四类分析（拟合、朗缪尔、Thomson、时序）放到同一工程视角，推荐的数据管道模式是统一的四段式：

1. **原始层**：仪器原始数据（电压/电流/光子计数）只读存档，永不覆盖；
2. **预处理层**：排序、去簇、背景扣除、单位化（第 28.1 节的 `sort_sweep_arrays`/`merge_voltage_clusters` 属于此层）——每步输出中间文件，可单独质检；
3. **物理层**：调用 PlasmaPy 诊断接口（`find_floating_potential`、`spectral_density_model`、`ConditionalEvents`），记录 API 版本与参数口径；
4. **产品层**：物理量 + 不确定度 + 元数据打包（HDF5 或数据库），供跨发次统计与 FLASH/FLYCHK 对照。

四段式的好处：任何一段的问题都能定位复现（原始层在），且第 3 层换 API 版本（如 langmuir → swept_langmuir 迁移）时只需重跑后两层。这与管理 FLASH 仿真输出的"6 文件夹"纪律同构——诊断数据管道与仿真数据管道共享同一套工程哲学。

---

# 第七篇 工程实践与综合案例

## 第 32 章 utils：装饰器与异常体系

### 32.1 核心装饰器（用户与开发者两个视角）

| 装饰器 | 作用 | 用户何时遇到 |
|---|---|---|
| `validate_quantities` | 全库单位校验主引擎：声明每个参数/返回值的期望单位与等价性 | 单位错误时抛 `UnitConversionError`（第 3 章） |
| `check_relativistic` | 速度参数相对论检查 | 超光速抛 `RelativityError`；接近光速发 `RelativityWarning` |
| `check_values` | 数值范围检查（正数、非负等） | 传负温度/负密度时报错 |
| `particle_input` | ParticleLike 参数解析（第 6 章） | 粒子符号错误时抛 `InvalidParticleError` |
| `angular_freq_to_hz` | 让函数支持 `to_hz=True` 输出 | 用频率族函数时 |
| `deprecated` | 弃用标记机器（自动发警告） | 调用弃用 API 时看到 DeprecationWarning |

自写函数复用校验体系的最小示例：

```python
from plasmapy.utils.decorators import validate_quantities
import astropy.units as u

@validate_quantities(T_e={"can_be_negative": False,
                          "equivalencies": u.temperature_energy()},
                     n_e={"can_be_negative": False})
def my_debye_number(T_e, n_e):
    ...
```

**validate_quantities 常用选项补充**：`equivalencies`（等价性转换，温度能量之外还有 `u.spectral()` 波长↔频率等）、`none_shall_pass=True`（允许传 None 表示缺省）、`pass_through=True`（跳过校验的逃生口）、以及按参数指定的 `default_unit`（裸数值的假定单位——慎用，会掩盖单位错）。选项组合覆盖了 PlasmaPy 全库的校验需求，极少需要写裸 `if` 检查。

照抄这个模板即可让自己的物理函数获得与 PlasmaPy 同款的单位安全网（负值禁止 + 温度能量等价性是最常用的两项）。

### 32.4 自写校验函数的进阶：check_relativistic 与组合

```python
from plasmapy.utils.decorators import check_relativistic
import astropy.units as u

@check_relativistic
def my_drift_speed(V: u.Quantity[u.m / u.s]):
    return V
# V >= c 抛 RelativityError；V 接近 0.1c 以上发 RelativityWarning
```

组合套路：一个生产级物理函数通常叠三层——`@particle_input`（粒子语义）→ `@validate_quantities`（单位）→ `@check_relativistic`（相对论边界，仅速度类）。装饰器从下往上执行，顺序错了会让单位校验先于粒子解析发生而报类型错——**粒子解析永远放最内层（最靠近函数体）**。

### 32.5 异常处理的工程模式

```python
from plasmapy.utils.exceptions import PlasmaPyError, CouplingWarning
import warnings

# 模式一：物理边界警告转结构化日志（不要静音）
with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter("always", CouplingWarning)
    lnL = compute_lnL(grid_point)
    for w in caught:
        log.warning(f"弱耦合失效 @ {point_id}: {w.message}")

# 模式二：数据管道中放行个别坏点而非崩溃
try:
    val = risky_quantity_call(n_e, T_e)
except PlasmaPyError as e:
    val = np.nan          # 标记坏点，末端统计
    bad_points.append((point_id, str(e)))
```

这两个模式构成本工作区"PlasmaPy 质检层"的骨架：警告有账可查，坏点有据可循，都进 GA 优化的 penalty 项或场景测试报告。

最后一条工程纪律：**质检层的输出要回流**——每次 CouplingWarning/简并标记的统计结果都应写入场景测试文档的"适用域"小节，长期积累后这些统计就是"哪些场景需要换输运模型"的证据链，也是论文中方法学部分（模型适用性论证）的现成素材。质检不是终点，是知识的沉淀管道。

### 32.2 异常与警告层级

```
PlasmaPyError                      # 基类
 ├─ ParticleError                  # particles 全家（第 6 章明细）
 ├─ PhysicsError                   # 物理约束被违反（负温度、不可归一等）
 └─ RelativityError                # 超光速等相对论硬错误

PlasmaPyWarning                    # 警告基类
 ├─ PhysicsWarning                 # 物理上可疑但可计算（近光速、弱耦合边界）
 ├─ CouplingWarning                # Γ 过大、lnΛ≲4（第 19 章）
 ├─ PlasmaPyFutureWarning          # "未来将变"（API 变更预告）
 └─ PlasmaPyDeprecationWarning     # 弃用 API（第 33 章）
```

**建议**：脚本入口统一 `import warnings` 后将 `CouplingWarning`/`PhysicsWarning` 转为日志而非静音——它们往往标记了物理模型的适用域边界（强耦合、强简并、相对论区），对判断"这个网格点还能不能用经典输运"有真实信息量。

### 32.3 其他工具

`roman` 模块（罗马数字 ↔ 整数，电离态 `Fe V` 记法解析用）；`code_repr`（对象的短 repr，调试日志友好）；`datatype_factory_base`（⚠ `|expect-api-changes|`，工厂基类，`Plasma` 工厂与 `MagnetoStatics` 的底层机制）。

## 第 33 章 弃用与版本迁移指南

### 33.1 已知弃用对照总表（2026.2.0）

| 弃用项 | 替代 | 状态 |
|---|---|---|
| `formulary.collisions.frequencies.collision_frequency` 函数 | `SingleParticleCollisionFrequencies` 类或 `fundamental_electron/ion_collision_freq` | 调用时发 DeprecationWarning |
| `diagnostics.langmuir` 整模块 | `analysis.swept_langmuir` 子包 | import 即发 FutureWarning，将移除 |
| 旧 `ParticleTracker`（接受 BasePlasma） | 新 grid 体系版 `ParticleTracker`（第 26 章） | 构造即报错（硬失败） |
| `particle_input(z_mean=...)` | 调用处显式传 `z_mean=` 给各函数 | DeprecationWarning |
| `utils.calculator`（plasma-calculator CLI） | 无（官方计划 mid-2026 后移除） | pyproject 声明 |
| `thermal_speed` 的 `ndim` 参数 | `method="most_probable"/"mean"/"rms"` | 收敛中 |

### 33.2 迁移方法论

1. **先跑后改**：升级 PlasmaPy 后先原样运行测试脚本，收集全部 Deprecation/FutureWarning（`python -W all`），按警告信息给出的替代名逐条改；
2. **警惕 |expect-api-changes|**：`dispersion`、`plasma`、`braginskii`、`laser`、`nullpoint`、`time_series` 模块**没有**弃用警告但签名可能变——升级大版本前用 `inspect.signature` 抽查关键函数（或直接跑 demos 回归）；
3. **硬失败的兜底**：`ParticleTracker` 这类"构造即报错"的迁移没有过渡期，只能按新 API 重写；官方建议的"回退 2023.5.1"仅作为应急。
4. 版本变更历史见 <https://docs.plasmapy.org/en/stable/whatsnew/index.html>；本地 2026.2.0 的 CHANGELOG 在 `PlasmaPy/PlasmaPy/CHANGELOG.rst`。与本工作区相关的更早变更摘要见《PlasmaPy使用说明书》第 6 节。

### 33.2.1 迁移中的三个典型坑

1. **静音 ≠ 迁移**：`filterwarnings("ignore")` 让警告消失但移除日会直接崩溃——把静音语句与迁移工单绑定（警告出现即建 issue），不做无期限静音；
2. **新旧并行过渡**：`analysis.swept_langmuir` 与旧 `diagnostics.langmuir` 数值上有差异（拟合区间算法改进），过渡期两版结果都要存档——差异本身就是回归测试基线；
3. **版本钉死策略**：仿真生产环境用 `pip install plasmapy==2026.2.0` 钉死 + 单独 venv；开发环境才跟踪最新。PlasmaPy 的年份版本号（2026.2.0）与 Python 年历版节奏对齐，一年数版，升级窗口建议固定在每年大版本发布后的验证周期内。

### 33.3 弃用警告的自动化捕获脚本

升级后第一件事用这个固定流程：

```python
import warnings, plasmapy.formulary as pf
import astropy.units as u

# 全量收集当前代码用到的 API 的警告
with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter("always")
    # 按项目实际调用清单逐个触发
    pf.Debye_length(T_e=100 * u.eV, n_e=1e20 * u.m**-3)
    pf.thermal_speed(T=1e6 * u.K, particle="e-")
    # ... 其余调用
deps = {f"{w.category.__name__}: {w.message}" for w in caught
        if issubclass(w.category, (DeprecationWarning, FutureWarning))}
for d in sorted(deps):
    print(d)
```

把脚本提交进仓库（每次升级跑一遍），输出即"迁移工作清单"。配合 `python -W all` 运行完整测试套件（含 demos）可覆盖隐式触发的弃用（import 层面的，如旧 langmuir）。

## 第 34 章 别名体系与 `_lite` 无单位版本

### 34.1 别名命名规律

每个 formulary 函数注册一个"符号式"短别名，规律是**物理量符号 + 下划线**：

| 函数 | 别名 | 函数 | 别名 |
|---|---|---|---|
| `plasma_frequency` | `wp_` | `gyrofrequency` | `wc_` |
| `Debye_length` | `lambdaD_` | `gyroradius` | `rc_`/`rhoc_` |
| `thermal_speed` | `vth_` | `Alfven_speed` | `va_` |
| `ion_sound_speed` | `cs_` | `inertial_length` | `cwp_` |
| `critical_density` | （laser 系）`omega_` | `mass_density` | `rho_` |
| `Coulomb_logarithm` | （collisions 内无别名） | `Bohm_diffusion` | `DB_` |
| `thermal_pressure` | `pth_` | `magnetic_pressure` | `pmag_` |
| `ionization_balance` | `Z_bal_` | `Hall_parameter` | `betaH_` |
| `Fermi_energy` | `Ef_` | `deBroglie_wavelength` | `lambdaDB_` |

用法：`from plasmapy.formulary import wp_, lambdaD_` 直接可用；别名与全名完全等价（同一对象的引用）。建议：正式脚本用全名（可读性），交互探索与紧凑公式块用别名。

**别名体系的两个边界**：① 别名只在 `plasmapy.formulary` 命名空间注册——`from plasmapy.formulary.lengths import lambdaD_` 这种子模块级导入可能失败（别名统一聚合到 formulary 顶层 `__init__`），统一从顶层导入最稳；② `_lite` 函数有独立的别名缺省（多数 lite 版没有短别名），混用时以 `dir(plasmapy.formulary)` 的实际输出为准，本表是"设计规律"而非穷举清单。

### 34.2 `_lite` 函数族：约定与取舍

```python
from astropy.constants import m_e
from plasmapy.formulary import plasma_frequency_lite, thermal_speed_lite
from plasmapy.formulary.collisions import Bethe_stopping_lite
import numpy as np

wp = plasma_frequency_lite(1e20, m_e.value, 1)      # (n[m^-3], mass[kg], Z) → rad/s
vth = thermal_speed_lite(1e6, m_e.value, 1.0)       # (T[K], mass[kg], coeff); coeff=1 为最可能速率
S = Bethe_stopping_lite(13.6 * 1.602e-19, 1e20, 1e7, 1)   # (I[J], n[m^-3], v[m/s], z)
```

三条铁律：① **输入输出全是裸数组**，单位约定以 docstring 标注为准（几乎全 SI），错单位不会报错只会错结果；② 无校验（负温度直接算）、无广播保护，调用方自己保证数据合法；③ 适合的场景是**大规模网格内层循环**（如对 FLASH 输出的全场逐点算 $\omega_{pe}$、$v_{th}$），先 lite 算完再按需抽样校验。经验值：lite 版比带校验版快 5–10 倍，一次调用差异可忽略，10⁶ 网格点以上差异显著。

### 34.3 别名与 lite 的组合实战

大规模场后处理的典型组合（对 FLASH 输出的 10⁶ 格点场算 $\omega_{pe}$ 与 $v_{th}$）：

```python
import numpy as np
from astropy.constants import m_e
from plasmapy.formulary import plasma_frequency_lite, thermal_speed_lite

# dens/tele: 从 output_pro 提取的裸数组（SI: m^-3, K）
omega_pe = plasma_frequency_lite(dens, m_e.value, 1)        # (N,) rad/s
vth_e    = thermal_speed_lite(tele, m_e.value, 1.0)         # (N,) m/s
# 校验：抽样 100 点用带校验版对账
idx = np.random.choice(dens.size, 100, replace=False)
ref = [plasma_frequency(dens[i] * u.m**-3).value for i in idx]
assert np.allclose(np.asarray(ref), omega_pe[idx], rtol=1e-12)
```

"lite 全场 + 校验版抽样对账"是本工作区推荐的标准姿势——速度与安全兼得，且对账断言本身就是回归测试的一部分。

## 第 35 章 最佳实践与性能

### 35.1 单位陷阱 Top 5

1. **eV 当温度**：裸 `100 * u.eV` 传给不带等价性的自定义函数会挂；PlasmaPy 的 `T_e` 参数没问题，自写函数记得加 `equivalencies=u.temperature_energy()`；
2. **数密度 vs 质量密度**：`Alfven_speed(density=...)` 要 kg/m³、`plasma_frequency(n=...)` 要 m⁻³——先用 `mass_density` 明确换算；
3. **角频率 vs 频率**：`gyrofrequency`/`plasma_frequency` 默认 rad/s，与 Hz 比较（激光频率、示波器读数）差 $2\pi$；
4. **速度分布 vs 速率分布**：第 12 章 $4\pi v^2$ 因子，画谱用 speed 版、算矩用 velocity 版；
5. **热速度三种定义**：与文献公式对比时确认对方的定义（rms/最概然/平均），`thermal_speed` 默认 rms。

### 35.2 性能清单

- 批量计算：输入 numpy 数组触发广播，**避免 Python 循环逐点调函数**；
- 网格内层循环：`_lite` 版本（第 34 章）；
- Braginskii/碰撞频率类：用类的 cached_property，一次构造多系数复用；
- `ParticleTracker`：粒子数 ≥10⁵ 时关掉不必要的 IntervalSaveRoutine，先用 DoNotSave 粗跑定参数；
- 拟合（thomson/langmuir）：固定已知参数（`params["ne_0"].vary=False`）减少自由度。

### 35.3 工程组织

参考工作区 `demos/` 的模式：每个主题一个独立脚本（自含 import、可单独运行、出图存 `figures/`），外加 `run_all_tests.py` 做一键回归——升级 PlasmaPy 版本时先跑它，再按第 33 章流程处理警告。所有脚本统一 UTF-8 + LF（本工作区约定）。

### 35.4 代码风格与项目组织建议

在 PlasmaPy 之上写项目代码时，建议遵守四条：

1. **显式声明物理口径**：每个函数的 docstring 写明所用的库仑对数 method、gamma 取值、z_mean 来源——PlasmaPy 给了太多可调选项，不记录口径的结果无法复现；
2. **Quantity 进 Quantity 出**：内部函数签名保持单位穿透（不中途 `.value`），只在 IO 边界（画图、写文件）剥单位——中途剥单位是单位错的头号源头；
3. **固定随机性与版本**：涉及抽样（粒子初始分布）时固定 seed 并记录 `plasmapy.__version__`；
4. **测试分层**：单函数 smoke test（单位与量级）→ 组合案例（如 26.6 的闭环）→ 与 FLASH/FLYCHK 的交叉对照（计为集成测试）。

### 35.5 性能反模式清单

- ❌ Python 循环逐点调带校验函数（10⁶ 点可达分钟级）→ ✅ 数组广播或 `_lite`；
- ❌ 在循环内重复构造 `ClassicalTransport`/碰撞频率类 → ✅ 类外提、cached_property 复用；
- ❌ 对 Quantity 数组做 `np.array()` 强转画图 → ✅ `.to(unit).value`（前者会静默丢单位且强制拷贝）；
- ❌ 用 float64 裸算分布函数大速度尾部 → ✅ 对数采样或解析渐近（第 12.4 节）；
- ❌ 粒子追踪每步都存档 → ✅ `IntervalSaveRoutine` 用物理上有意义的时间间隔（回旋周期的整数分之一）。

## 第 36 章 综合案例与附录（蓄水池）

### 36.1 工作区 demos 精讲索引

| Demo | 内容 | 涉及 API | 产出 |
|---|---|---|---|
| `demo_01_formulary_basics.py` | ICF 条件参数表：Debye 长度/等离子体频率/回旋频率/惯性长度 + Debye 长度参数扫描图 | `Debye_length`, `plasma_frequency`, `gyrofrequency`, `inertial_length` | `figures/demo01_debye_length_scan.png` |
| `demo_02_particles.py` | `Particle`/`CustomParticle`/`ParticleList`，CH 混合等效离子建模，数密度换算 | `Particle`, `CustomParticle`, `ParticleList` | 控制台输出 |
| `demo_03_collisions_transport.py` | 库仑对数、碰撞频率、Spitzer 电阻率随温度曲线（对照 Spitzer-Härm 热传导） | `Coulomb_logarithm`, `collision_frequency`⚠, `Spitzer_resistivity` | `figures/demo03_spitzer_resistivity.png` |
| `demo_04_thomson_scattering.py` | 碳等离子体集合/非集合散射谱（532 nm、90°） | `diagnostics.thomson.spectral_density` | `figures/demo04_thomson_spectrum.png` |
| `demo_05_laser_plasma_waves.py` | 各倍频临界密度 + 暖等离子体 Langmuir 色散关系 | `critical_density`, `plasma_frequency`, `thermal_speed` | `figures/demo05_langmuir_dispersion.png` |

注意 demo_03 使用的 `collision_frequency` 已进入第 33 章迁移表，跑通后按警告信息替换为 `fundamental_electron_collision_freq`。

### 36.1.1 demo_01 精讲：ICF 参数表的构建逻辑

demo_01 是"PlasmaPy 作为参数手账"的模板，结构值得逐段拆解：

1. **单点参数块**：给定一组 (n_e, T_e, B)，四个长度/频率函数各算一行，打印成表——这是任何新场景立项时的第一步（"这个等离子体长什么样"）；
2. **扫描块**：Debye 长度对 T_e 的 log-log 扫描图——斜率 1/2 是理论的直接验证，图一旦不吻合说明单位或公式出错，这是隐式自检；
3. **对比块**：把 ICF 典型参数与磁约束参数并排打印——量级差异（如 $\lambda_D$ 差 6 个量级）帮助建立"regime 直觉"。

改造建议：把单点参数块参数化成函数 `icf_param_table(n_e, T_e, B, Zbar)` 接收 FLASH 场景参数，输出直接写进场景测试文档——demo 即可复用的生产代码。

### 36.1.2 demo_03 精讲：碰撞输运核验链

demo_03 演示的"库仑对数 → 碰撞频率 → Spitzer 电阻率"三步链是输运核验的最小完备集：

1. `Coulomb_logarithm` 随 T_e 的曲线在低温端下折（$b_{\min}$ 进入量子区）——图上这条下折位置就是对数适用域的直观边界；
2. 碰撞频率 $\nu_e\propto T_e^{-3/2}$ 的标度检查：log-log 图斜率 -1.5，一旦偏离即 method 或 z_mean 口径漂移；
3. Spitzer 电阻率与 `braginskii.resistivity` 并排对比——两者在非磁化极限应一致到拟合因子水平，差异超 10% 时优先怀疑 z_mean 传法不同（第 17.3 节）。

升级方向：把 demo_03 的三步链扩展成第 19.5 节的完整组合（+Knudsen 数+Γ/θ 标记），即为 SNB 场景族的"输运适用域地图"脚本。

### 36.1.3 demo_04 精讲：Thomson 正演谱的读图法

demo_04 用 `spectral_density` 合成碳等离子体的 EPW/IAP 谱，读图要点：

1. **EPW 双峰间距** → $T_e$（近似解析关系），峰的宽度 → 阻尼（$k\lambda_D$ 越大越宽，强阻尼时双峰糊掉）；
2. **IAP 峰结构** → $T_i$ 与离子组分：多离子时声波分裂成快/慢两支（碳 + 氢杂质是经典案例），峰数即组分数；
3. **集合/非集合**：参数扫描改变 $n_e$ 即可看到 α 从 ≫1 到 ≪1 的谱形嬗变（双线 → 单宽峰）——这一帧动画胜过半页公式推导。

demo 只画了单角度；接第 29.3 节的拟合流程后即成为完整的诊断 pipeline。

### 36.1.4 demo_02 与 demo_05 精讲

**demo_02（particles）**的核心是 CH 混合等效离子的三步构造：按化学计量比配平核数密度（C:H=1:1）→ 用 `ParticleList` 汇总两组分的质量/电荷贡献 → 归一为 `CustomParticle(mass=6.5*u.u, Z=Zbar)`。这个"混合物 → 等效单离子"的模式是全项目离子口径的基础——`z_mean=3.5` 这类参数的出处就在这里，demo 把"等效离子不是真实粒子、只是输运系数的代用键"这一理念代码化。

**demo_05（激光等离子体波）**演示两件事：① 四种倍频（ω/2ω/3ω/4ω）临界密度的表格——4 倍递推关系一目了然，是激光参数选型的速查卡；② 暖等离子体 Langmuir 色散关系 $\omega^2=\omega_p^2+3k^2v_{th}^2$ 的曲线族——不同温度的曲线束展示了热修正量级，与第 22.4 节的完整动理学解对照可看出"何时 $3k^2v_{th}^2$ 近似失效"（$k\lambda_D\gtrsim0.2$）。

两个 demo 共同的工程启示：**表格输出与图输出并存**——表格供脚本间管道消费（机器可读），图供人检查（趋势可见），两者都出自同一段参数定义，保证口径唯一。

### 36.2 全库 API 速查总表（按章）

| 主题 | 章 | 核心 API |
|---|---|---|
| 粒子对象 | 4 | `Particle`, `CustomParticle`, `DimensionlessParticle`, `ParticleList`, `molecule` |
| 电离态 | 5 | `IonizationState`, `IonicLevel`, `IonizationStateCollection` |
| 原子数据 | 6 | `atomic_number`…`stopping_power`, `particle_input` |
| 频率 | 7 | `plasma_frequency`(`wp_`), `gyrofrequency`(`wc_`), `lower/upper_hybrid_frequency`, `Buchsbaum_frequency` |
| 长度 | 8 | `Debye_length`(`lambdaD_`), `gyroradius`(`rc_`), `inertial_length`(`cwp_`) |
| 速度 | 9 | `thermal_speed`(`vth_`), `Alfven_speed`(`va_`), `ion_sound_speed`(`cs_`), `kappa_thermal_speed` |
| 密度/漂移 | 10 | `critical_density`, `mass_density`(`rho_`), `ExB_drift`, `diamagnetic_drift` |
| 介电 | 11 | `cold_plasma_permittivity_SDP/LRP`, `permittivity_1D_Maxwellian` |
| 分布 | 12 | `Maxwellian_velocity/speed_1D/2D/3D`, `kappa_velocity_1D/3D` |
| 电离平衡 | 13 | `Saha`, `ionization_balance`(`Z_bal_`) |
| 量子 | 14 | `Fermi_energy`(`Ef_`), `chemical_potential`, `quantum_theta`, `Thomas_Fermi_length`, `Wigner_Seitz_radius`, `Fermi_integral` |
| 辐射/激光/相对论 | 15 | `thermal_bremsstrahlung`, `laser` 9 函数, `RelativisticBody` |
| 磁静力学 | 16 | `Wire`, `CircularWire`, `MagneticDipole` 等 |
| Braginskii | 17 | `ClassicalTransport` + 6 便捷函数 |
| 无量纲/杂项 | 18 | `beta`, `Debye_number`, `Hall_parameter`, `Bohm_diffusion`, 磁压/热压 |
| 碰撞 | 19 | `Coulomb_logarithm`, `mean_free_path`, 两个碰撞频率类, `coupling_parameter`, `Knudsen_number`, `Spitzer_resistivity`, `Bethe_stopping` |
| 色散 | 20–22 | `plasma_dispersion_func`, `stix`, `two_fluid`, `mhd_waves`, `hollweg`, `kinetic_alfven` |
| 等离子体对象 | 23–24 | `Plasma`(工厂), `CartesianGrid`, `HarrisSheet`, `ForceFreeFluxRope`, `HDF5Reader` |
| 模拟 | 25–26 | `BorisIntegrator`, `ParticleTracker`, 三终止条件 × 三存档例程, `CFL_limit_electromagnetic_yee` |
| 分析 | 27, 28, 31 | `null_point_find`, `fit_functions` 四类, `find_floating_potential`, `ConditionalEvents` |
| 诊断 | 29, 30 | `spectral_density(_model)`, `Tracker`(radiography), `synthetic_radiograph`, `Stack/Layer` |
| 工程设施 | 32–34 | `validate_quantities`, 异常层级, 别名表, `_lite` 族 |

**使用本表的正确姿势**：这张总表的定位是"知道 PlasmaPy 有什么"的完备性索引——先用它确认"这个物理量 PlasmaPy 有没有接口"，再跳转对应章节看"怎么用、什么时候会错"。反向用法（拿着表逐行学）效率最低：全库 200+ 公开接口中，日常高频使用的约 30 个（即 D.4 一行命令集的规模），其余按需取用即可。

### 36.3 官方教程链接总表

- 入门：[units](https://docs.plasmapy.org/en/stable/notebooks/getting_started/units.html) ｜ [particles](https://docs.plasmapy.org/en/stable/notebooks/getting_started/particles.html)
- 公式：[ExB drift](https://docs.plasmapy.org/en/stable/notebooks/formulary/ExB_drift.html) ｜ [Braginskii](https://docs.plasmapy.org/en/stable/notebooks/formulary/braginskii.html) ｜ [冷等离子体张量](https://docs.plasmapy.org/en/stable/notebooks/formulary/cold_plasma_tensor_elements.html) ｜ [库仑对数](https://docs.plasmapy.org/en/stable/notebooks/formulary/coulomb.html) ｜ [分布函数](https://docs.plasmapy.org/en/stable/notebooks/formulary/distribution.html) ｜ [ITER 参数](https://docs.plasmapy.org/en/stable/notebooks/formulary/iter.html) ｜ [磁层参数](https://docs.plasmapy.org/en/stable/notebooks/formulary/magnetosphere.html) ｜ [磁静力学](https://docs.plasmapy.org/en/stable/notebooks/formulary/magnetostatics.html) ｜ [太阳大气 β](https://docs.plasmapy.org/en/stable/notebooks/formulary/solar_plasma_beta.html) ｜ [韧致辐射](https://docs.plasmapy.org/en/stable/notebooks/formulary/thermal_bremsstrahlung.html) ｜ [热速度](https://docs.plasmapy.org/en/stable/notebooks/formulary/thermal_speed.html)
- 色散：[色散函数](https://docs.plasmapy.org/en/stable/notebooks/dispersion/dispersion_function.html) ｜ [Hollweg](https://docs.plasmapy.org/en/stable/notebooks/dispersion/hollweg_dispersion.html) ｜ [Stix](https://docs.plasmapy.org/en/stable/notebooks/dispersion/stix_dispersion.html) ｜ [双流体](https://docs.plasmapy.org/en/stable/notebooks/dispersion/two_fluid_dispersion.html)
- 粒子：[ICME 电离态](https://docs.plasmapy.org/en/stable/notebooks/particles/ace.html)
- 对象：[均匀网格](https://docs.plasmapy.org/en/stable/notebooks/plasma/grids_cartesian.html) ｜ [非均匀网格](https://docs.plasmapy.org/en/stable/notebooks/plasma/grids_nonuniform.html)
- 模拟：[Particle Tracker](https://docs.plasmapy.org/en/stable/notebooks/simulation/particle_tracker.html)
- 诊断：[Thomson 谱密度](https://docs.plasmapy.org/en/stable/notebooks/diagnostics/thomson.html) ｜ [Thomson 拟合](https://docs.plasmapy.org/en/stable/notebooks/diagnostics/thomson_fitting.html) ｜ [粒子追踪照相](https://docs.plasmapy.org/en/stable/notebooks/diagnostics/charged_particle_radiography_particle_tracing.html) ｜ [多层探测器](https://docs.plasmapy.org/en/stable/notebooks/diagnostics/charged_particle_radiography_film_stacks.html) ｜ [自定义源](https://docs.plasmapy.org/en/stable/notebooks/diagnostics/charged_particle_radiography_particle_tracing_custom_source.html) ｜ [wire mesh](https://docs.plasmapy.org/en/stable/notebooks/diagnostics/charged_particle_radiography_particle_tracing_wire_mesh.html) ｜ [旧朗缪尔分析](https://docs.plasmapy.org/en/stable/notebooks/diagnostics/langmuir_analysis.html)
- 分析：[悬浮电位](https://docs.plasmapy.org/en/stable/notebooks/analysis/swept_langmuir/find_floating_potential.html) ｜ [磁零点](https://docs.plasmapy.org/en/stable/notebooks/analysis/nullpoint.html) ｜ [拟合函数](https://docs.plasmapy.org/en/stable/notebooks/analysis/fit_functions.html)

### 36.4 三份文档的分工总结

- **本指南**：全 API 的"为什么 + 怎么用 + 什么时候会错"，含适用条件与迁移指南；
- **《PlasmaPy使用说明书》**：安装、环境验证、demo 一览、与 PhySimX/FLASH 工作流的结合建议；
- **《相关公式接口速览》**：公式 ↔ 接口对照表与适用域警告，辐射输运/不透明度缺口的结论与替代方案（FLYCHK/FLASH）。

### 36.5 依赖-功能映射附录

| 依赖库 | 服务功能 |
|---|---|
| h5py | `plasma.grids` 序列化、`openpmd_hdf5`、粒子追踪存档、`stopping_power` 数据表、thomson io、radiography 探测器 |
| lmfit | `thomson.spectral_density_model`、`quantum.chemical_potential` 插值、`fit_functions` |
| mpmath | `Fermi_integral`、quantum 模块的解析延拓 |
| pandas + xarray | `plasma.grids` 的数据容器 |
| tqdm | `ParticleTracker` 进度条 |
| astropy | 全库单位与常数体系（必需） |

## 附录 A 常见问题 FAQ

**A1. `import plasmapy` 很慢（数秒）怎么办？**
包初始化时加载 astropy 单位体系与原子数据库，冷启动 1–3 秒属正常；脚本里多次 `import` 会被 Python 缓存，不是性能问题。需要极致启动速度的场合只 import 所需子模块（`from plasmapy.formulary import Debye_length`）不改变总耗时——真正耗时的是首次 `import astropy.units`，无解也无须解。

**A2. 两个函数给出略不同的库仑对数/热导系数，谁对？**
多半都对——拟合系数版本不同（Spitzer 1920/1953、Braginskii 1965、Epperlein-Haines 1986 各有系数表）。做法：固定一个口径（推荐 PlasmaPy 默认），在文档里注明 method 与出处，与 FLASH 对照时先统一口径再比数值（第 17.4 节）。

**A3. 如何把 FLASH HDF5 的数据喂给 PlasmaPy？**
两条路：① 公式类（formulary）：用本工作区 `output_pro` 提取 dens/tele 为 numpy 数组，直接按广播方式传入（第 3.8 节）；② 场类（粒子追踪/射线照相）：重采样后注册到 CartesianGrid（第 24.4 节五步法）。FLASH 不是 openPMD 格式，`HDF5Reader` 不能直接读。

**A4. 数组传入后结果形状不对？**
先确认输入是 `(N,)` 还是 `(3,N)`（矢量场是后者）；再用 `[:, None]` 显式广播（第 3.8 节）；最后检查函数是否按"每个参数独立广播"组合维度——二维扫描必须显式对齐。

**A5. 警告（CouplingWarning 等）应该静音吗？**
不。它们标记物理模型适用域边界（第 32.2 节），正确做法是转为日志并检查触发警告的网格点占比——超过几个百分点就意味着该区域需要更换模型（表格 EOS/非局域输运）。

**A6. 版本升级的最小验证集是什么？**
跑 `demos/run_all_tests.py`（覆盖 formulary/particles/collisions/thomson 四大板块）+ 收集全部弃用警告（第 33.2 节流程）。15 分钟内完成，能拦住绝大多数 API 变更。

**A7. 能用 PlasmaPy 算不透明度或辐射输运吗？**
不能（第 15.1 节边界声明）。不透明度走 FLYCHK，辐射输运/流限热传导走 FLASH 扩散模块；PlasmaPy 只覆盖发射谱一级量与参数判据。

**A8. `Particle("C 3.5")` 报错？**
电荷数必须整数（`"C 3.5"` 非法）；平均电离度用 `z_mean=3.5` 参数传入各 formulary 函数（第 4.1、19.1 节），混合物建模用 `CustomParticle`（第 4.4 节）。

## 附录 B 术语对照表

| 英文术语 | 本指南译法 | 一句话定义 |
|---|---|---|
| plasma formulary | 等离子体公式手册 | NRL 等机构编纂的特征量公式集，formulary 子包的出处 |
| Coulomb logarithm | 库仑对数 | 小角散射累积的无量纲积分，碰撞系数的核心因子 |
| coupling parameter | 耦合参数 Γ | 平均势能与动能之比，强/弱耦合分界 |
| degeneracy (quantum theta) | 简并（量子参数 θ） | $T/T_F$，费米统计重要性判据 |
| mean free path | 平均自由程 | 两次碰撞间平均行走距离 |
| Knudsen number | Knudsen 数 | 自由程/系统尺度，流体/动理学分界 |
| Braginskii coefficients | Braginskii 输运系数 | 磁化等离子体的经典输运系数族（电导/热导/黏滞/热电） |
| dielectric tensor | 介电张量 | 等离子体对电磁波的线性响应张量 |
| dispersion relation | 色散关系 | 波的 ω(k) 关系 |
| Landau damping | 朗道阻尼 | 无碰撞波-粒子共振耗散 |
| floating potential | 悬浮电位 | 探针净电流为零时的电位 |
| ion saturation current | 离子饱和电流 | 探针负偏压下收集的饱和离子流 |
| spectral density | 谱密度 | Thomson 散射的微分截面谱 |
| synthetic radiograph | 合成照相 | 粒子追踪正演生成的探测器图像 |
| magnetic null point | 磁零点 | B=0 的拓扑奇点 |
| conditional averaging | 条件平均 | 按触发事件统计平均的时序分析方法 |

## 附录 C 学习路径图（依角色）

- **仿真参数管理员**（FLASH 场景配置）：第 3 章 → 第 7–10 章 → 第 15.4 节 → 第 36.1 节 demo_01/05；
- **输运系数核验**：第 19 章 → 第 17 章 → 第 14.4 节 → 第 36.1 节 demo_03；
- **光谱诊断**：第 29 章 → 第 12 章 → 第 20 章 → 第 36.1 节 demo_04 → FLYCHK 工作流文档；
- **粒子/照相模拟**：第 24 章 → 第 26 章 → 第 30 章 → 官方 radiography 教程族；
- **包开发者/工具维护**：第 32 章 → 第 33 章 → 第 35 章。

本指南的核心主张可以浓缩为一句话：PlasmaPy 的价值不在于替你解方程，而在于**把等离子体物理的"常识层"代码化**——单位不写错、口径不漂移、适用域有判据、弃用有迁移路。把这层基础设施用足，项目脚本里剩下的才是真正属于你研究问题的那部分代码。祝使用顺利。

## 附录 D 十分钟速查卡（打印友好）

### D.1 单位三步自检

1. 温度传 eV 行不行？——PlasmaPy 的 `T_e/T_i` 行，自写函数要加 `equivalencies=u.temperature_energy()`；
2. 频率是角频率还是 Hz？——默认 rad/s，比较激光前 `to_hz=True`；
3. 密度是数密度还是质量密度？——`n` 是 m⁻³，`density/rho` 是 kg/m³。

### D.2 碰撞计算选择卡

```
要什么？
├─ 量级核验（电阻率/热导）→ Coulomb_logarithm(GMS-3) → Spitzer_resistivity
├─ Braginskii 全系数 → ClassicalTransport（复用实例）
├─ 输运方程右端项 → SingleParticleCollisionFrequencies（带 V）
├─ Maxwellian 矩 → MaxwellianCollisionFrequencies
├─ 非局域判据 → mean_free_path → Knudsen_number
└─ 强耦合标记 → coupling_parameter（Γ>1 停用经典公式）
```

### D.3 波动分析选择卡

```
要什么？
├─ 特征速度速查 → mhd_waves 工厂
├─ 冷等离子体分支 → cold_plasma_permittivity_SDP + stix
├─ 含温低频 → two_fluid → 需阻尼 → hollweg
└─ KAW → kinetic_alfven
```

### D.4 一行命令集

```python
Debye_length(T_e=100*u.eV, n_e=1e20*u.m**-3)                      # 屏蔽长度
critical_density(em_angular_frequency(0.351*u.um))                # 激光临界密度
Coulomb_logarithm(T, n_e, ["e-","C 3+"], z_mean=3.5, method="GMS-3")  # 库仑对数（密度参数名 n_e）
coupling_parameter(T, n_e, ["e-","C 3+"], z_mean=3.5)             # Γ 判据（二体列表）
quantum_theta(T, n_e)                                             # 简并判据
ionization_balance(n=1e20*u.m**-3, T_e=100*u.eV)                   # LTE 平均电离度（无 species 参数）
spectral_density(wavelengths, 532*u.nm, n=ne, T_e=Te, T_i=Ti, ions="H+", efract=[1.0], ifract=[1.0])  # 返回 (alpha, Skw)
```

（速查卡与正文第 36.2 节总表配套使用：卡片管"手感"，总表管"完备"。）

## 附录 E 官方资源与社区

### E.1 文档资源分层

| 层级 | 资源 | 用途 |
|---|---|---|
| 入口 | <https://docs.plasmapy.org/en/stable/> | stable 文档首页（与本指南版本一致 2026.2.0） |
| 教程总目录 | [examples.html](https://docs.plasmapy.org/en/stable/examples.html) | 全部 31 个 notebook 教程的分组索引（本指南第 36.3 节已全量收录） |
| API 速查 | `/api_static/plasmapy.*.html` | 静态 API 页，按子包组织，比搜索快 |
| 版本历史 | `/whatsnew/index.html` | changelog，升级前必读 |
| 源码 | <https://github.com/PlasmaPy/PlasmaPy> | 提 issue / 看实现细节 |
| 社区 | GitHub Discussions + 每周社区会 | 提问与功能请求的官方渠道 |

### E.2 如何高效提问/报 bug

官方 issue 模板要求最小可复现示例（MRE）。构造 MRE 的 PlasmaPy 特有要点：① 带上 `plasmapy.__version__` 与 Python 版本；② 单位错误类问题附上完整的 `Quantity` 构造语句而非描述；③ 碰撞/输运类问题注明 `method` 与 `z_mean` 取值（结果依赖口径）。本工作区已遇到过的、值得为社区补档的案例：`Particle` 分数电荷不支持、FLASH 非 openPMD HDF5 不可直读、`ParticleTracker` 新旧接口硬切换——都是文档尚未覆盖的行为细节。

### E.3 版本演进速览（与本项目相关的时间线）

- **2023.5**：旧 `ParticleTracker`（BasePlasma 接口）的最后稳定版——迁移应急回退目标；
- **2023.10 前后**：`analysis.swept_langmuir` 新 API 开始进入；MHD 波类族（`mhd_waves`）引入；
- **2024–2025**：`particles.atomic` 新增 `periodic_table_*` 系列与 `stopping_power`；`collision_frequency` 进入弃用流程；
- **2026.2.0**（当前）：Python 下限 3.12；依赖全面（无 optional 组）；`utils.calculator` 宣布 mid-2026 后移除；
- **后续预期**：`|expect-api-changes|` 模块（dispersion/plasma/braginskii/laser/nullpoint/time_series）的签名收敛是主线，跟踪 whatsnew 即可。

## 附录 F 本指南的维护约定

1. **版本锚定**：本指南内容锚定 PlasmaPy 2026.2.0；升级版本后按第 33 章流程检查第 33.1 节弃用表与各章 `|expect-api-changes|` 标记段落，变更处更新并加日期备注；
2. **与官方文档的分工**：官方文档是"当前准确"的权威（尤其 API 签名），本指南是"结构化理解 + 场景适配"的增值层——两者冲突时以官方为准并回改本指南；
3. **错误反馈**：本指南中的代码示例经过最小验证，但接口细节（尤其 `|expect-api-changes|` 模块的参数名）可能随小版本微调，报错时先 `help(接口)` 核对本地签名，再决定是代码错还是文档过时；
4. **关联文档**：《PlasmaPy使用说明书》（环境与工作流）、《相关公式接口速览》（公式对照）——三份文档的章节号互不引用、只引用文件名，保证各自独立可读。

## 附录 G 经实测核对的 API 修正清单（2026.2.0）

> **本附录的来历**：本指南全部代码示例在 plasmapy **2026.2.0**（Python 3.13.14，venv 见第 1 章）下逐条运行核对，配套脚本见 `docs/verify/verify_guide_api.py`（120 项断言全部 PASS）。下表汇总编写/修订过程中发现的、**与早期版本或直觉不符的真实 API 行为**——即"踩坑后已修正"的条目。升级版本后若再次发现不符，优先用 `inspect.signature` 与 `help()` 核对本地签名（见附录 F 第 3 条）。

### G.1 导入位置与命名空间（最常见的一类坑）

| 对象 | 早期/直觉写法（错误） | 2026.2.0 真实位置 | 备注 |
|---|---|---|---|
| `periodic_table_block` / `periodic_table_category` / `periodic_table_group` / `periodic_table_period` | `from plasmapy.particles import periodic_table_block` | `from plasmapy.particles.atomic import periodic_table_block` | 这几个辅助函数实际住在 `particles.atomic` 子模块，不在 `particles` 顶层 |
| `particle_input` 装饰器 | `from plasmapy.utils.decorators import particle_input` | `from plasmapy.particles import particle_input` | 已迁到 `particles` 命名空间 |
| `CFL_limit_electromagnetic_yee` | `from plasmapy.formulary import CFL_limit_electromagnetic_yee` | `from plasmapy.simulation import CFL_limit_electromagnetic_yee` | 属于 `simulation` 子包，签名 `(dx) -> s` |
| 光速常量 | `import plasmapy.particles as pp; pp.c` 或 `u.c` | `from astropy.constants import c` | `u.c`/`pp.c` 没有 `c` 属性，光速必须取自 `astropy.constants` |

### G.2 返回值类型 / 属性名修正

| 对象 | 早期/直觉（错误） | 2026.2.0 真实行为 |
|---|---|---|
| `cold_plasma_permittivity_SDP` | 返回对象的 `.S`、`.D`、`.P` 属性 | 返回 `StixTensorElements`，属性为 `.sum`（=S）、`.difference`（=D）、`.plasma`（=P）；且 `sum = R+L = 2S`、`difference = R−L = 2D` |
| `cold_plasma_permittivity_LRP` | 返回对象的 `.L`、`.R`、`.P` 属性 | 返回 `RotatingTensorElements`，属性为 `.right`（=R）、`.left`（=L）、`.plasma`（=P） |
| `Saha` | `Saha` 是类，调用 `.evaluate(g_j, g_k, n_e, E_jk, T_e)` | **2026.2.0 起为纯函数**：`Saha(g_j=, g_k=, n_e=, E_jk=, T_e=)` 直接返回无量纲 `Quantity` |
| `RelativisticBody` | `body.gamma` | `body.lorentz_factor`（无 `.gamma` 属性） |
| `spectral_density` | 返回 `(Skw, lam)`，`efract` 传标量，`T_e/T_i` 传空间分布数组 | 返回 **`(alpha, Skw)`**；`efract`/`ifract` 必须是**求和为 1 的序列**（如 `efract=[1.0]`）；`T_e`/`T_i` 的数组维度是**按粒子群**而非空间区域 |
| `Coulomb_logarithm` | 返回带单位的 `Quantity` | 返回**裸 ndarray**（无单位） |
| `ionization_balance(n, T_e)` | 返回 `float` | 返回**无量纲 `Quantity`**（需 `float(...)` 取值） |
| `ionization_state` 系列 | （见 33 章） | — |

### G.3 签名 / 参数名修正

| 对象 | 错误用法 | 正确用法 |
|---|---|---|
| `classicalTransport` | `Z=3.5`（非整数） | `Z` 必须取整数（如 `Z=3`），否则 `PhysicsError` |
| `IonizationState` | 构造时传 `n=1e17*u.m**-3` | 参数名为 **`n_elem=`**（不是 `n=`）；电荷态分数数量须与元素电荷态数匹配（如 Fe 需 27 个分数） |
| `Knudsen_number` | 传 `mean_free_path=...` | **无 `mean_free_path` 参数**；用 `characteristic_length=`、`T=`、`n_e=`、`species=`、`z_mean=`、`V=`、`method=` |
| `stix` | `n_i=n, species=species, n=n` | `stix(B=, w=, ions=Particle("p+"), n_i=, theta=)`；`ions` 是**单个 `Particle`**；返回 4 支波数 `Quantity`（rad/m，顺序 O/X/R/L） |
| `two_fluid` | `k=1e-6*u.m**-1`，取 `.alfven` 属性 | `k=1e-6*u.rad/u.m`（单位是 rad/m）；返回**字典**，键为 `'fast_mode'` / `'alfven_mode'` / `'acoustic_mode'` |
| `mhd_waves` | `T_e=...` / `T_i=...` 分传 | 用单一关键字 **`T=`**；返回命名元组 `MHD_Waves`（字段 `alfven_wave` / `fast_magnetosonic_wave` / `slow_magnetosonic_wave`），可 `alfven, fast, slow = waves` 解包；波对象暴露 `.alfven_speed` / `.sound_speed` / `.magnetosonic_speed` |
| `ParticleTracker.load_particles` | `load_particles(x, v, species="p+")` | 参数名为 **`particle=`**（`load_particles(x, v, particle="p+")`）；`x`、`v` 为 `Quantity` |
| `_lite` 系列 | `plasma_frequency_lite(n, ...)` 参数顺序乱 | `plasma_frequency_lite(n, mass, Z)`；`thermal_speed_lite(T, mass, coeff)`；`Bethe_stopping_lite(I, n, v, z)`（均为裸数组/标量，无单位） |

### G.4 模块结构修正（曾被误写的 API）

| 误写 | 事实 |
|---|---|
| `plasmapy.plasma` 导出 `Plasma3D`、`PlasmaBlob` | **2026.2.0 无此二类**；真实导出含 `BasePlasma`、`GenericPlasma`、`Plasma`（工厂）、`HarrisSheet`、`ForceFreeFluxRope`、`equilibria1d`、`cylindrical_equilibria`、`sources`、`grids`。`Plasma(density=, T=)` 返回 `GenericPlasma`，其 `electron_density()` 等访问器是**抽象方法**（调用抛 `NotImplementedError`）——仅作接口基类，真实 equilibrium 用 `HarrisSheet(B0=, delta=, P0=)` 等 |
| `distribution` 子模块含 `Maxwellian_velocity_1D` | **不存在**；实际 6 个函数：`Maxwellian_1D`、`Maxwellian_speed_1D`、`Maxwellian_speed_2D`、`Maxwellian_speed_3D`、`Maxwellian_velocity_2D`、`Maxwellian_velocity_3D` |
| `a0`（有质动力参数）对 I=5×10¹⁴ W/cm²、λ=0.351 µm 约为 0.042 | 实测 ≈ **0.0067**（注意量纲与归一化定义，勿与另一种归一化混淆） |

### G.5 一页速记（核查结论）

- 光速、电荷态数、`periodic_table_*` 的位置是**导入层面**的最高频坑；
- `Saha`、`spectral_density` 的返回顺序、`_lite` 参数顺序是**签名层面**的坑；
- `plasma` 子包已**无 `Plasma3D`/`PlasmaBlob`**，切勿照旧教程抄；
- 凡 `|expect-api-changes|` 标记的模块（dispersion / plasma / braginskii / laser / nullpoint / time_series），升级后务必跑 `docs/verify/verify_guide_api.py` 与 `demos/run_all_tests.py` 两道回归（`120/120` 与 `5/5` 为当前 2026.2.0 基线）。

（全文完）

