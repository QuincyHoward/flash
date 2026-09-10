# FLASH 输出新变量的设置

**版本**: 1.0
**日期**: 2026-09-08
**适用**: FLASH 4.8 / FLASHSNB (SNB 专用树)
**实例**: SNB 非局域热传导诊断变量 (QESH/QENL 等 18 个)

---

## 目录

1. [总览：一条变量从声明到落盘的完整链路](#1-总览)
2. [第 1 步：Config 声明 VARIABLE（编译期）](#2-config-声明-variable编译期)
3. [第 2 步：源代码写入数据（运行期）](#3-源代码写入数据运行期)
4. [第 3 步：setup 生成索引（Flash.h）](#4-setup-生成索引flashh)
5. [第 4 步：par 设置 plot_var 白名单（输出期）](#5-par-设置-plot_var-白名单输出期)
6. [第 5 步：plt 文件验证](#6-plt-文件验证)
7. [以 SNB 为例的完整实操记录](#7-以-snb-为例的完整实操记录)
8. [常见坑与检查清单](#8-常见坑与检查清单)

---

## 1. 总览

让 FLASH 输出一个新的物理量，本质上是三段接力：
**Config 声明（编译期分配索引）→ 源代码写入（运行期填数据）→ par 白名单（IO 输出到 plt）**。

```
┌─────────────┐   setup    ┌──────────────┐   编译/运行   ┌─────────────┐
│ Config       │ ────────→ │ objdir/Flash.h│ ──────────→ │ solnData unk │
│ VARIABLE QENL│  按序编号  │ #define       │  物理模块    │  #35 槽位    │
└─────────────┘  QENL_VAR  │  QENL_VAR 35  │  写 QENL_VAR │             │
      35                    └──────────────┘              └──────┬──────┘
                                                                │ IO 模块
┌─────────────┐          ┌──────────────────┐                   │
│ flash.par    │ ───────→ │ io 读取 plot_var_N│ ←────────────────┘
│ plot_var_18= │  白名单   │ 名字→索引映射      │   按名字查索引
│   "QENL"     │          └────────┬─────────┘
└─────────────┘                   ↓
                        snbonech_hdf5_plt_cnt_####  (HDF5 数据集 "qenl")
```

关键认知（很多"输出不了"的问题出在对这三点的误解）：

1. **变量索引是编译期分配的**。`VARIABLE` 写进 Config 后必须重新 `setup`
   （Flash.h 重新生成）并重新编译——改 par 永远不会让一个没编译进去的变量出现。
2. **物理量必须有人写**。Config 只开槽位，槽位里的数据要靠源代码（物理模块或
   Simulation 单元）在运行期写入 unk 数组；没写入的变量输出全 0。
3. **plt 是白名单制**。FLASH 的 hdf5typeio 只把 `plot_var_N` 点名的变量写进
   plt 文件；不点名的 unk 即使有数据也不会出现（chk 文件例外，存全量 unk）。

---

## 2. Config 声明 VARIABLE（编译期）

单元 `Config` 文件中用 `VARIABLE` 关键字声明：

```
# ── SNB nonlocal thermal conduction diagnostic variables ──
VARIABLE QESH
VARIABLE QEFL
VARIABLE QENL
VARIABLE NELE
VARIABLE MFPE
VARIABLE MFPR
VARIABLE QESX
VARIABLE QESY
VARIABLE GRQX
VARIABLE GRQY
VARIABLE GRAQ
VARIABLE CORQ
VARIABLE QEXG
VARIABLE QEYG
VARIABLE GRGX
VARIABLE GRGY
VARIABLE GRQG
VARIABLE COGQ
```

（摘自 SNB_1D_laser 单元 Config；本项目场景由
`flash.input_gen.gen_config.ConfigGenerator` 生成基础段后追加这一段。）

语法要点：

| 写法 | 含义 |
|------|------|
| `VARIABLE NAME` | 声明中心 unk 变量，setup 分配一个 unk 槽位 |
| `VARIABLE name TYPE: PER_VOLUME` | 附类型标签（如激光能量沉积 `lase`） |
| `SPECIES cham` | 物种声明——每个物种**自动**成为一个 unk（并自动可用 `cham` 做 plot_var） |

声明顺序即编号顺序：同一 Config 内，先声明者编号小。**在中间插一个变量会使
其后所有变量索引 +1**，若树内有代码硬编码过索引（极少见，正常都用宏）需重编。

## 3. 源代码写入数据（运行期）

Config 的 VARIABLE 只是在 unk 数组里开了槽位，数据靠源代码填。SNB 的例子
（`diff_advanceTherm.F90`，FLASHSNB 增强版，SH 热流与非局域热流）：

```fortran
! SH (Spitzer-Harm) 电子热流
solnVec(QESH_VAR,i,j,1) = ...
! 非局域 (SNB) 电子热流 — 多群求和结果
solnVec(QENL_VAR,i,j,1) = -(&
    0.5*(solnVec(COND_VAR,i+1,j,1)+solnVec(COND_VAR,i,j,1)) * &
    (solnVec(TELE_VAR,i+1,j,1)-solnVec(TELE_VAR,i,j,1)) - ...)
```

要点：

- 代码中**永远用 `<NAME>_VAR` 宏**引用索引，绝不写数字——宏由 setup 生成
  （见第 4 节），重排 Config 时代码零改动。
- 内置变量同理可用：`DENS_VAR`、`TELE_VAR`、`COND_VAR`（电导率）、
  `DEPO_VAR`（激光沉积）等。
- 物种数据由 FLASH 在 `Simulation_initBlock`（或 species 相关模块）里填，
  无需手工管槽位。
- 写入位置必须在计算该变量的物理模块的推进例程里（Diffuse 单元的热传导在
  `diff_advanceTherm`），且每个时间步刷新，否则 plt 记录的是陈旧值。

## 4. setup 生成索引（Flash.h）

`./setup` 时，FLASH 按 Config 的声明顺序为所有 VARIABLE/SPECIES 统一编号，
写入 objdir 的 **`Flash.h`**（注意大写 F）。SNBOneCH_obj 实测（2026-09-08）：

```c
#define DENS_VAR 6
#define QENL_VAR 35
#define QESH_VAR 36
#define CHAM_SPEC 53
#define TARG_SPEC 54
```

整个 Flash.h 共 54 个 `_VAR` 宏（含内置 + SNB 18 个 + 物种）。这些宏经
setup 的 include 机制对所有源文件可见——这就是"改 Config 必须重新 setup +
make"的原因：Flash.h 变了，引用宏的所有 .o 都要重编。

**排查技巧**：想确认某个变量到底有没有被编译进去、编号是多少，直接查
`objdir/Flash.h`：

```bash
grep "define QENL_VAR" $SNB_HOME/<objdir>/Flash.h
```

## 5. par 设置 plot_var 白名单（输出期）

plt 文件写哪些变量由 `plot_var_N`（N = 1, 2, 3, ...）白名单决定。SNB 基线
（t001 flash.par）的写法：

```
plot_var_1  = "dens"
plot_var_2  = "depo"
plot_var_3  = "tele"
plot_var_4  = "tion"
plot_var_5  = "QESH"     # SNB: SH 热流
plot_var_6  = "QESX"     # SH 热流 x 分量
plot_var_7  = "QESY"
plot_var_8  = "GRQX"     # 群分辨热流 x
plot_var_9  = "GRAQ"
plot_var_10 = "CORQ"     # SNB 修正项
plot_var_11 = "MFPE"     # 电子平均自由程
plot_var_12 = "ye"
plot_var_13 = "tar1"     # 物种也可点名 (由 SPECIES 自动成为 unk)
...
```

配套的输出频率控制（plt 按时间或按步触发，二者先到先用）：

```
plotFileIntervalTime = 1e-11     # 每 1e-11 s 出一帧 (推荐: 时间触发便于跨工况对比)
plotFileIntervalStep = 2000      # 或每 2000 步 (可选, 二选一生效即可)
checkpointFileIntervalStep = 400 # chk 与 plot 独立控制
```

要点：

- **名字大小写敏感**，必须与 Config 中 `VARIABLE` 的名字完全一致
  （HDF5 数据集名会转为小写 `qenl`）。
- 点一个不存在的名字 → FLASH 运行启动时 abort（runtime parameter 校验）。
- `plot_var_N` 必须从 1 开始连续编号（本仓库生成器
  `ParGeneratorExtended` 会按白名单列表自动重排，见 SNBOneCH.py 的
  `_PLOT_VARS` → `plot_var_{i}`）。
- 用 `+hdf5typeio` setup 旗标时 plt 为 HDF5 格式（文件名无 `.h5` 后缀，
  形如 `snbonech_hdf5_plt_cnt_0010`）。

## 6. plt 文件验证

输出后用 FlashDataLoader 抽查新变量非零（SNBOneCH_ml.py `analyze_quick`
的判定逻辑）：

```python
from flash.output_processors.loader import FlashDataLoader
c = FlashDataLoader("flash_output/snbonech_hdf5_plt_cnt_0010").load(
    compute_derived=False, extraction_mode="yt")
arr = c.data.get("qenl")          # 数据集名 = 变量名小写
import numpy as np
print(np.nanmax(np.abs(arr)))     # >0 → SNB 变量已激活并有数据
```

命令行快速核对数据集存在性：`h5dump -n <plt文件> | grep -i qenl`。

⚠️ 本仓库加载注意：非 +ug（AMR）输出的 plt 必须用
`load(compute_derived=False, extraction_mode="yt")`（或 "h5py"）——默认
`load()` 不过滤非叶子块，陈旧粗网格数据会混入（实测 81/16352 点错误）。
+ug 均匀网格无此问题。

## 7. 以 SNB 为例的完整实操记录

把 SNB 诊断变量引入一个新的仿真单元（如 SNBOneCH），完整步骤：

1. **Config**：在生成的基础 Config 末尾追加 18 个 `VARIABLE` 行
   （`SNB_CONFIG_VARIABLES` 常量，见
   `flash/scenarios/private/tracer/SNB/SNBOneCH/SNBOneCH.py`）。
2. **源代码**：9 个单元覆盖文件从 FLASHSNB 的 SNB_1D_laser 复制进单元
   （`diff_advanceTherm.F90` 等负责计算并写入 QESH_VAR/QENL_VAR 等；
   `Makefile` 加 `Simulation += Simulation_data.o mgd_qesh.o`）。
3. **setup + make**：`./setup -auto SNBOneCH ... +mgd ...` → 生成 Flash.h
   → 编译。此时 QENL_VAR 等宏生效。
4. **par**：`plot_var_N` 白名单加入 `QESH/QESX/QESY/GRQX/GRAQ/CORQ/MFPE/QENL`
   等需要的诊断量（不必全部 18 个都点）。
5. **运行 + 验证**：跑极短 tmax（如 1e-11）→ 检查 plt 数据集存在且非零
   → 正式运行。

一个变量"从 Config 到 plt"只需 5 步；反过来排查"为什么 plt 里没有我的变量"
也按这 5 步倒查：Config 有没有 → 代码写没写（Flash.h 索引存在吗）→ setup
是不是旧的 → par 点名了吗 → 数据是不是全 0。

## 8. 常见坑与检查清单

| # | 坑 | 现象 / 对策 |
|---|----|-------------|
| 1 | 只改 par 不改 Config | 变量根本没编译进 flash4，plot_var 点名直接 abort。先加 VARIABLE 再 setup。 |
| 2 | 改 Config 后未 setup/重编 | Flash.h 是旧索引，新变量找不到。setup 会重新生成 Flash.h；make 会级联重编引用宏的文件。 |
| 3 | plot_var 名字拼写/大小写不符 | 启动即 abort（unknown/invalid runtime parameter）。逐字对照 Config。 |
| 4 | 物理模块没写数据 | plt 里有数据集但全 0。确认写入代码在推进例程内且每步执行。 |
| 5 | plot_var 编号不连续 | FLASH 从 1 连续读取，断号处停止。用生成器列表化处理（`_PLOT_VARS` 模式）。 |
| 6 | 在 Config 中间插变量 | 其后所有变量索引 +1，跨单元 diff 时 idx 变化正常现象；代码一律用宏不受影响。 |
| 7 | AMR 输出用默认 load() 读 | 非叶子块陈旧数据混入。用 `extraction_mode="yt"/"h5py"`。 |
| 8 | chk 与 plt 混淆 | chk 存全量 unk（不看白名单），plt 才是白名单制；诊断用 plt。 |

**最小检查清单**（新变量上线前）：

- [ ] Config 有 `VARIABLE XXX`
- [ ] 源代码有 `solnVec(XXX_VAR, ...) = ...`（或等效写入）
- [ ] `grep "define XXX_VAR" objdir/Flash.h` 能查到
- [ ] par 有 `plot_var_N = "XXX"` 且编号连续
- [ ] 首跑后 `plt` 数据集 `xxx` 非零

---

## 关联文档

- `input_gen/README.md` — 输入文件生成器总览
- `flash/scenarios/private/tracer/SNB/SNBOneCH/SNBOneCH.py` — SNB 场景完整
  实例（Config 追加段 / par 白名单 / +ug 网格）
- `flash/scenarios/private/SNB/SNBtest/Test/t001/首次SNB代码微调说明.md` —
  SNB 物理覆盖文件的部署与编译细节
