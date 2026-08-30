# flash-sim 场景系统 — 使用指南

> flash-sim 场景系统使用指南：从即插即用仿真入口到可参数化、可优化的工程工具。

---

**flash-sim** 是 [FLASH](https://flash.rochester.edu/) 高能量密度物理 (HEDP) 仿真代码的全功能 Python 封装。提供**场景系统**（即插即用仿真入口）、参数文件生成、多环境运行管理、HDF5 输出分析与自适应可视化的一站式工作流。

## 仓库地址 (Repository)

本项目托管于 Gitee (码云), 支持 HTTPS 克隆与在线浏览:

```
https://gitee.com/physimx/flash
```

| 操作 | 命令 |
|------|------|
| **HTTPS 克隆** | `git clone https://gitee.com/physimx/flash.git` |
| **在线浏览** | https://gitee.com/physimx/flash (Code/Issues/Releases 页签) |
| **版本标签** | 以 `git tag -l` 查看全部 (PyPI 按阶段更新) |
| **问题反馈** | 通过 Gitee Issues 提交 (登录后新建 Issue) |

---

## 场景系统的重要性与广泛应用

场景系统是 flash-sim 的核心价值所在，也是把 FLASH 这一庞大、门槛较高的 HEDP 仿真代码转化为「可计算、可复用、可优化」工程工具的关键枢纽：

- **简单参数扫描**：批量覆盖材料厚度、密度、激光功率、AMR 层级等参数，无需改动任何 FLASH 源文件，即可在 Python 循环中自动生成 `.par` 并运行多组仿真。
- **多组仿真数据对比**：运行输出统一规格的 HDF5 文件与统一命名的分析图像，天然便于跨工况、跨方案的定量对比。
- **参数化接入优化算法**：场景以**结构化参数**为唯一输入、以物理量为输出，可无缝接入网格搜索、贝叶斯优化、遗传算法或代理模型，作为「黑盒仿真器」反复调用。
- **为靶结构、脉冲波形等设计提供便利**：设计变量参数化后结合优化闭环，系统性探索设计空间，缩短「试错—仿真」迭代周期。

---

## 什么是场景系统？

场景系统（`scenarios/`）是 **flash-sim 的顶层仿真入口**，将 FLASH 的完整工作流
（输入文件生成 → 编译 → 运行 → HDF5 收集 → 分析绘图）封装为即插即用的**物理场景**。

用户无需手动配置 FLASH 源文件、编写 `.par`、处理编译，也不需要写 HDF5 读取和插值代码。

---

## 当前场景总览

| 场景 | 位置 | 运行方式 | 物理内容 |
|------|------|---------|---------|
| `ch_center` | `center_evolution/ch_center/` | 注册表 + 引擎 / `python -m` 直跑 | CH 泡沫靶 + 两侧 He，双束 351nm 激光相向，中心等离子体状态时域演化 |
| `laserslab1d_local_demo` | `flash_demo/demo_local/` | `python -m` 直跑 | FLASH 1D LaserSlab 本机 (WSL) 演示 |
| `laserslab1d_hpc_demo` | `flash_demo/demo_hpc/` | `python -m` 直跑 | FLASH 1D LaserSlab 超算 (SLURM) 演示 |
| `hello_flash` | `flash_demo/hello_flash/` | `python -m` 直跑 | FLASH 安装/部署冒烟测试 + 密度图 |
| `layer_tracer_CH` | `private/tracer/layer_tracer_CH/` | `python -m` 直跑 (wsl/hpc 一键切换) | 1D 分层示踪靶 (CH)：cham(He)→samp(CH)→targ(CH)→samp(CH)，MGD 10 群辐射 |
| `VCH_ml` | `private/tracer/VCH_ml/` | `python -m` 直跑 (wsl/hpc 一键切换) | 1D **多薄层**示踪靶 (8 物种, V 屏蔽层)：cham(He)→shld(V 0.1µm)→samp→tar1@1µm→samp→tar2@2µm→samp→tar3@3µm→samp→tar4@4µm→samp→tar6@6µm→samp(D=50µm) |
| `OneCH_ml` | `private/tracer/OneCH_ml/` | `python -m` 直跑 (wsl/hpc 一键切换) | 1D **多薄层**示踪靶 (8 物种, 纯 CH)：与 VCH_ml 唯一物理差异为 shld 材质 V→CH (ρ=1.0)，其余设置完全一致 |
| `run_ml_suite` | `private/tracer/run_ml_suite.py` | `python run_ml_suite.py` | 一键顺序执行 OneCH_ml、VCH_ml 双场景仿真（tmax 可指定，默认 1e-11 验证） |
| `layer_tracer_Ti` | `private/tracer/layer_tracer_Ti/` | `python -m` 直跑 (wsl/hpc 一键切换) | 1D 分层示踪靶 (Ti tracer)，CH 靶 + Ti 示踪层 X-ray 谱学诊断 |

> ⚠️ **private/ 场景不随发布包分发**（.gitignore 排除），仅限内部使用；tracer 系列以
> `python -m` 直跑，不进入注册表。

### 注册场景明细

#### ch_center

| 属性 | 值 |
|------|-----|
| **物理** | CH 泡沫靶 + 两侧 He, 双束 351nm 激光相向 |
| **应用** | 中心等离子体状态时域演化观测 |
| **激光** | 5e14 W/cm² |
| **CH 靶** | ρ=1.0 g/cm³ |
| **He** | ρ=1e-6 g/cm³ (eos_tab) |
| **EOS 表** | 自研 IONMIX 表 (Z02, Z06-Z01, 随包分发, 无版权障碍) |
| **tmax** | 1.2e-9 s |
| **输出字段** | 7 个 (dens, tele, tion, trad, ye, sumy, pres) |
| **备注** | 基于原始 FLASH LaserSlab 配置, EOS 表已替换为自研高分辨表 |

#### VCH_ml / OneCH_ml (private, 多薄层, 2026-08-30 由 layer_tracer_CH_ml 更名拆分)

| 属性 | 值 |
|------|-----|
| **物理** | 1D 多薄层示踪靶, 8 物种 13 区: cham(He, ρ=1e-6) → shld(0.1µm) → samp(CH) → tar1(CH@1µm, 0.1µm) → samp → tar2(CH@2µm) → samp → tar3(CH@3µm) → samp → tar4(CH@4µm) → samp → tar6(CH@6µm) → samp(D=50µm) → cham |
| **两场景差异** | **仅 shld 材质**: VCH_ml = V (ρ=6.11, V-BADGER-TOPS.cn4)；OneCH_ml = CH (ρ=1.0, CH-QC-1-001.cn4)。其余 F90/par/几何/物种标记完全一致 |
| **目录结构** | 主脚本 `VCH_ml.py` / `OneCH_ml.py`；其余脚本收纳于 `VCH_ml/src/`（analysis=chk 分析, tools=par 对比, docs=差异文档） |
| **一键批量** | `python run_ml_suite.py [tmax]` (tracer/ 下)：顺序执行 OneCH_ml → VCH_ml，tmax 缺省 1.0e-11 验证值 |
| **仿真域** | x = [-0.04, 0.01] cm, 1D 笛卡尔, NXB=16, lrefine_max=9 |
| **激光** | 单光束 0.351µm (透镜 x=-1.0, 靶 x=0), 82 点功率脉冲 |
| **初始状态** | 固体层常温 (290.11375 K) 固体密度; tar1/tar2/tar3/tar4/tar6 物质同为 CH, 独立物种标记 |
| **tmax** | 规范值 1.6e-9 s; 搭建验证时可覆写为 1.0e-11 |
| **输出分析** | dens 剖面 (全域 + [-5,10]µm 放大) + 8 物种分布图 + 物种时空图 + 预诊断图 (脉冲/初始分层) |
| **与纯 CH 基准一致性** | 除几何/物质设置外与 `CH_CH_**um8.00e-02` 基准一致 (killdivb 段逐行一致, plotFileIntervalStep=2000 已对齐); 详见 `VCH_ml/src/docs/VCH与纯CH的差异.md` |
| **历史运行** | 更名前快照保留在 `VCH_ml/flash_input/run_00000{1,4,5}/` (run_id 自动续接) |

#### layer_tracer_CH (private)

| 属性 | 值 |
|------|-----|
| **物理** | 1D 分层示踪靶: cham(He, ρ=1e-6) → samp(CH 示踪首层) → targ(CH 靶芯 0.1µm) → samp(CH) |
| **仿真域** | x = [-0.04, 0.01] cm, 1D 笛卡尔, NXB=16, lrefine_max=9 |
| **激光** | 单光束 0.351µm (透镜 x=-1.0, 靶 x=0), 82 点功率脉冲 (内嵌于 `_par_layers.py`) |
| **辐射** | MGD 10 能群, tabular EOS/opacity (ionmix4: He-BADGER + CH-QC) |
| **tmax** | 规范值 1.6e-9 s; 搭建验证时可覆写为 1.0e-11 (见「快速搭建工作流」) |
| **运行模式** | `RUN_MODE = "wsl"` / `"hpc"` 一键切换 (环境变量 `FLASH_RUN_MODE` 可覆盖) |
| **输出分析** | dens(x,t) 时空彩图 + 不同时刻密度剖面线图 (全域 + [-10,20]µm 放大) |

---

## 外部使用方式

### 前提条件

1. 已安装 FLASH 4.8（在 WSL 或超算上）
2. Python ≥ 3.10，已安装 `h5py`, `numpy`, `matplotlib`

### 1. 导入 flash 包

```python
import sys
sys.path.insert(0, "/path/to/flash")   # flash 包根目录 (含 pyproject.toml)

from flash.scenarios.registry import get_scenario, list_scenarios
from flash.scenarios.simulator import FlashSimulatorEngine
```

### 2. 列出可用场景

```python
for name, desc in list_scenarios():
    print(f"  {name:30s} → {desc}")
```

### 3. 运行注册场景 (ch_center)

```python
scenario = get_scenario("ch_center")
engine = FlashSimulatorEngine(scenario, verbose=True)

output = engine.run(
    flash_timeout=900,       # FLASH 运行超时 (秒)
    keep_flash_raw=True,     # 保留原始 chk 文件
)

print(f"✅ result.h5: {output.result_h5_path}")
print(f"   运行目录:   {output.run_dir}")
```

### 4. 覆盖默认参数

```python
output = engine.run(
    params_overrides={
        "lrefine_max": 7,           # 提高 AMR 分辨率
        # ...其它参数见 scenario.default_params.keys()
    },
    keep_flash_raw=True,
)
```

> ⚠️ **重要规则**: 未在 `params_overrides` 中指定的参数**保持默认值**，不得私自修改。

### 5. 直跑场景模块 (flash_demo / private tracer 系列)

demo 与 tracer 系列场景为自包含模块，直接以 `python -m` 运行：

```bash
cd /path/to/flash                      # flash 包根目录

# layer_tracer_CH: wsl/hpc 一键切换 (模块内 RUN_MODE 常量或 FLASH_RUN_MODE 环境变量)
python -m flash.scenarios.private.tracer.layer_tracer_CH.layer_tracer_CH

# ch_center 本地直跑入口
python -m flash.scenarios.center_evolution.ch_center.laserslab1d_local_custom

# FLASH 本地演示
python -m flash.scenarios.flash_demo.demo_local.laserslab1d_local_demo
```

直跑场景的内置流程：

```
依赖检查 (7 个必须文件) → 缺失则自动调用 input_gen 生成器 (8 步)
  → .par / Config / Makefile / Simulation_data / Simulation_init /
    Simulation_initBlock / .cn4 复制 / run_flash.sh + submit_flash.sh
→ WSL: run_flash.sh (setup→make→mpirun) → 收集 outputfiles/
→ 本地分析绘图 (plots/)
```

HPC 模式支持分阶段断点续跑：`python -m ... all|upload|submit|monitor|analyze|download|status`。

### 6. 跳过运行（仅生成输入文件）

依赖检查发现文件缺失时才触发生成；如需强制重新生成，删除场景目录下的
`flash_input/` 后重跑即可。

---

## 编译与缓存

FLASH 的编译（`./setup` + `make`）只取决于**编译期输入**：`Config`、`Makefile`、
`*.F90` 源文件以及 setup 参数。运行时参数 `.par` **不参与编译**。

- **引擎方式** (`FlashSimulatorEngine.run`)：内置编译缓存（指纹 = setup 参数 +
  源文件哈希），同一场景首次编译后自动命中缓存，改 `.par` 不触发重编译。
- **直跑方式** (`python -m` + `run_wsl`)：每次运行前**清理旧 objdir** 再全新
  `setup + make`（约 10~60 分钟），保证编译状态与当前输入文件严格一致——
  适合搭建验证阶段；频繁迭代时建议保留 flash4 二进制手动复用（见下）。

### 手动复用 flash4 二进制

```bash
mkdir -p /tmp/run_mycase && cd /tmp/run_mycase
cp ~/<user>/FLASH/FLASH4.8/<user>/<objdir>/flash4 ./flash4
cp <场景 flash_input 目录>/*.cn4 ./
cp <场景 flash_input 目录>/laserslab_custom.par flash.par
mpirun -np N ./flash4
```

### MPI 进程数 N 的来源

N 由**装置 × 维度**自动计算（详见 `flash_run/env/resource_config.py`）：

| 装置 (按总核数) | 1D | 2D | 3D |
|------|------|------|------|
| 笔记本 (<10 核) | 80% CPU，不支持并行 | 80% CPU，不支持并行 | 80% CPU，不支持并行 |
| 台式机 (<30 核) | 80% CPU，2 个并行 | 80% CPU，不支持并行 | 80% CPU，不支持并行 |
| 超算 (≥30 核) | 80% CPU，3 个并行 | 80% CPU，2 个并行 | 80% CPU，不支持并行 |

```bash
python scripts/01_env_diagnose/gen_resource_config.py --show          # 探测本机并生成控制文件
python -m flash.flash_run.env.resource_config show    # 查看当前配置
```

---

## 输出结构

### 引擎方式 (注册场景)

```
{当前工作目录}/runs_{scenario_name}/{run_id:06d}/
├── sim_input/              ← FLASH 源文件 + .par + .cn4 (always)
├── sim_output/             ← FLASH 原始 chk HDF5 (keep_flash_raw=True 时)
└── database/
    ├── flash_in/
    │   ├── input_params.json   ← 输入参数快照 (可追溯)
    │   └── run.log             ← 运行日志
    └── flash_out/
        └── result.h5           ← ★ 核心输出 (变分辨率插值网格)
```

`result.h5` 数据集: `t (Nt,)`、`x (Nx,)`、`dens/tele/tion/trad/pres/pele/pion/prad/
velx/ye/sumy/poly/targ`，均为 `(Nt, Nx)`。

### 直跑方式 (python -m 场景)

> **run_id 规范（06d，自动分配）**：`WslSpec.outputfiles_dir` 显式指定时，
> `run_wsl` 每次运行自动扫描现有 `run_NNNNNN*` 目录取 max+1 作为本轮
> run_id（`allocate_run_id()`，同时扫描 flash_input 快照目录），三层产物
> 按 id 对称归档：**输入快照** `flash_input/run_NNNNNN/`、**输出**
> `flash_output/outputfiles/run_NNNNNN/`（经环境变量 `FLASH_COLLECT_DIR`
> 注入 run_flash.sh，优先于脚本内置 COLLECT_DIR）、**分析图**
> `flash_output/plots/run_NNNNNN/`。run_id 用 6 位零填充为大规模仿真预留
> 扩展位。旧场景（未指定 outputfiles_dir）保持旧行为。

```
{场景目录}/
├── flash_input/            ← 工作输入文件 + run_flash.sh + wsl 运行日志
│   ├── laserslab_custom.par / Config / *.F90 / *.cn4
│   ├── run_flash.sh / submit_flash.sh
│   ├── pre_diag_laser_pulse.png      ← 预诊断: 激光脉冲时间-功率 (gen_checker.ploter)
│   ├── pre_diag_initial_density.png  ← 预诊断: 初始密度分层 + 区域边界
│   ├── wsl_run.log / wsl_console.log   ← 运行日志 (排查编译/运行错误)
│   ├── run_000001/         ← ★ run_000001 的输入快照 (par/Config/F90/cn4/预诊断图)
│   └── run_000002/         ← ★ run_000002 的输入快照 (不同 id 输入可能不同)
└── flash_output/
    ├── outputfiles/
    │   ├── run_000001/     ← ★ run_000001 的 FLASH 原始 HDF5 (plt_cnt_* / chk_*)
    │   └── run_000002/     ← ★ run_000002 的 FLASH 原始 HDF5
    └── plots/
        ├── run_000001/     ← ★ 该轮分析图
        └── run_000002/
```

---

## 快速搭建新场景工作流

以 `layer_tracer_CH` → 派生新场景为例，推荐六步流程：

### 第 1 步：复制最接近的现有场景

```
flash/scenarios/private/tracer/
├── _par_layers.py          ← 规范物理参数字典 (82 点脉冲/MGD 群边界等, 自包含)
├── layer_tracer_CH/        ← CH 示踪场景 (模板)
│   ├── layer_tracer_CH.py          ← 场景主脚本
│   └── layer_tracer_CH_remote_analysis.py  ← HPC 远程分析脚本
└── layer_tracer_Ti/        ← Ti 示踪场景 (由 CH 模板派生)
```

复制整个场景目录并重命名，物理参数字典放回 `_par_layers.py` 统一维护，避免转录错误。

### 第 2 步：修改场景主脚本的可配置参数

只需调整 `layer_tracer_XXX.py` 顶部的 `config_constants` 与 `SETUP_FLAGS`：

| 参数 | 说明 | 示例值 |
|------|------|--------|
| `layer_samp_um` | 首层厚度 (µm) | `2.0` |
| `xmin` / `xmax` | 仿真域 (cm) | `-0.04` / `0.01` |
| `nblockx` / `lrefine_max` | 初始分块 / 最大 AMR 层级 | `8` / `9` |
| `tmax` | 仿真结束时间 (s)；**验证期设 1.0e-11** | `1.0e-11` |
| `plot_interval_step` | plt 输出频率 (步) | `1000` |
| `nprocs` | MPI 进程数 (None=自动) | `None` |

物种/分层几何在 `build_species_defs` 与 `GridBuilder.add_region` 中修改；
新增材料时需在 `Config` 的 `DATAFILES` 追加对应 `.cn4` 条目。

### 第 3 步：极小 tmax 快速验证（关键技巧）

**首次搭建场景时，把 `.par` 中的 `tmax` 设为极小值（如 `tmax=1.0e-11`）**：
FLASH 到达该仿真时间立即结束，编译完成后几分钟内跑完，专用于验证场景搭建
（网格/物种/初始密度分层/激光配置）是否正确，不必等待完整物理演化。

```python
config_constants = {
    ...
    "tmax": 1.0e-11,   # 搭建验证用; 正式运行恢复规范值 (如 1.6e-9)
}
```

### 第 4 步：一键运行

```bash
cd /path/to/flash
python -m flash.scenarios.private.tracer.<新场景>.<新场景脚本>
```

自动完成：依赖检查 → 生成 8 类输入文件 → WSL 编译运行 → 收集输出 → 分析绘图。

### 第 5 步：结果判读清单

通过以下五类产物快速判断场景搭建是否正确：

| 产物 | 判读要点 |
|------|---------|
| **密度剖面图** (`dens_profiles.png`) | ① 各物种分界面位置与厚度正确；② 各层密度平台值正确（log 轴上台阶清晰，V 层应显著高于 CH）；③ 域两端为腔室气体本底；④ 全域图 + 局部放大图结合看边界过渡 |
| **物种分布图** (`species_zoom.png`) | 每个空间位置恰有一个物种为 1（0/1 阶跃干净）；各 tar 层位置/厚度与设计一致 |
| **预诊断图** (`pre_diag_laser_pulse.png` / `pre_diag_initial_density.png`) | 激光脉冲 82 段形状/峰值功率与设计一致；初始密度分层台阶与区域边界标注正确（生成阶段即可核对，无需等仿真） |
| **时空彩图** (`dens_timespace.png`) | 时间方向初始场无异常漂移（tmax 极小时仅 1 帧自动跳过） |
| **FLASH 输入文件** | `.par` 参数（尤其 tmax/物种表绑定/plot_var 白名单）、`Config` DATAFILES+SPECIES、`Simulation_initBlock.F90` 分层边界逐一核对 |
| **运行日志 + 输出文件** | `wsl_run.log` 无 `DRIVER_ABORT`/unknown parameter 告警；`flash_output/outputfiles/` 中 plt/chk 数量与输出频率设置一致 |

### 第 6 步：恢复正式参数并提交

验证通过后，把 `tmax` 恢复为规范值（如 `1.6e-9`），再跑正式仿真；一切稳定后
推送 Gitee（`scripts/03_git_publish/git_push.py`）。

### 注意事项（血泪经验）

#### ★ par 参数控制规范化（layer_tracer_CH_ml 范式）

场景几何**不再硬编码**于场景脚本/生成的 F90 中，而是全部经 FLASH 运行时参数控制——
**只修改 `.par` 文件即可改变场景几何，无需改代码**（改 .par 不触发重编译）。

layer_tracer_CH_ml 的分层几何参数（.par INITIAL CONDITIONS 段）：

| par 参数 | 含义 | 默认值 | 控制的区域边界 |
|----------|------|--------|----------------|
| `sim_shldRadius` | delta: 屏蔽层/示踪薄层厚度 | 0.1 µm | shld=[0,shldR]；各 tar 层上界=L+shldR |
| `sim_tar1Radius` | L1: tar1 外边界累积位置 | 1 µm | tar1=[tar1R, tar1R+shldR] |
| `sim_tar2Radius` | L2 | 2 µm | tar2=[tar2R, tar2R+shldR] |
| `sim_tar3Radius` | L3 | 3 µm | tar3=[tar3R, tar3R+shldR] |
| `sim_sampHeight` | D: 尾部 samp 厚度 | 50 µm | samp_rear=[tar3R+shldR, +sampH] |

声明链路（生成器自动维护，无需手写）：
1. 场景 `build_species_defs` 给物种定义 `radius/height`（+ 可选
   `radius_param/height_param` 自定义参数名）；
2. `ConfigGenerator` 生成 `PARAMETER sim_* REAL <默认值>`；
3. `SimDataGenerator` 生成 `Simulation_data.F90` 声明、`SimInitGenerator`
   生成 `RuntimeParameters_get` 读取；
4. `BlockGenerator` 区域用 `x_expr=("sim_tar1Radius", "sim_tar1Radius + sim_shldRadius")`
   生成参数化边界（数值 `x_range` 仅用于采样/预诊断）；
5. `.par` 经 `par_gen.set("sim_tar1Radius", ...)` 设定实际值。

配套机制：
- **lrefine 分辨率自动注释**（gen_par 全场景生效，行尾简化格式）：生成的
  `.par` 在 `lrefine_max`/`lrefine_min` 行尾自动附理论网格分辨率
  `res = dir_delta/(nxb*nblock*2^(lrefine-1))`，便于核对 AMR 是否能解析最薄层
  （0.1 µm 层需 res_min ≤ 0.03 µm）。
- **plot_var 白名单**：物种增删必须同步重写 `plot_var_1..N`（见下条 9）。
- **par 行尾注释**（gen_par 全场景生效）：绝大多数参数行尾自动追加对齐的
  `# 说明`（静态字典 + 脉冲序列/能群边界/物种族动态规则），lrefine 行尾
  直接给出分辨率公式与结果——详情见 `gen_par/GEN_PAR_GUIDE.md`。

#### 通用注意事项

1. **tmax 极小值验证**是场景搭建的标准做法——先保证"能跑、初始场对"，再谈物理演化。
2. **EOS/opacity 表温度下界**：`.cn4` 温度网格单位为 eV。旧表下界 2.0 eV，新表
   0.01 eV；初始温度低于表下界时扩散求解器可能报 `[Diffuse]: computed dt is not positive!`。
   优先用自研新表（Z02/Z06/Z14 等，`gen_eos_op` 规范库复制）。
3. **物种名 ≤ 4 字符**（如 cham/samp/targ），FLASH Fortran 侧变量长度受限。
4. **文件换行符必须 LF**：`run_flash.sh`/`submit_flash.sh` 等在 WSL/Linux 下运行，
   CRLF 会导致 `/bin/bash^M` 错误（HPC 上传后 runner 会自动 `sed -i 's/\r$//'` 兜底）。
5. **参数默认值的权威来源**是 `flash/input_gen/gen_par/defaults.py`；场景覆写之外的
   参数不得私自修改，`.par` 基础参数通过 `ParGeneratorExtended` API 生成，禁止手写。
6. **内在关联检查**：`flash/input_gen/gen_checker` 提供 14 条规则（`.par`↔`Config`↔F90↔
   脚本一致性），场景验证 FAIL 时先跑
   `python flash/input_gen/gen_checker/check_relations.py <flash_input 目录>` 定位。
7. **编译缓存权衡**：`run_wsl` 每次清 objdir 全新编译（状态严格一致但慢）；
   频繁改 `.par` 迭代时手动复用 flash4 二进制（编译期输入不变则无需重编译）。
8. **凭据安全**：超算 SSH 凭据经加密存储读取（`flash._core.credentials`），禁止在任何
   脚本中硬编码用户名/密码/token。
9. **★ 增删物种必须同步重写 `plot_var` 白名单**：`.par` 模板中的 `plot_var_1..N`
   是 plotfile 输出变量的**白名单**——FLASH 只输出名单内的变量，名单外的新物种
   **静默丢失**（dens/sumy 看似正常，极难察觉）。layer_tracer_CH_ml 已按
   6 物种重写 plot_var_1..14；派生新物种场景时务必照做。
10. **增删物种时同步清理 par 残留键**：物种删除后其 `sim_rho*/ms_*/op_*/eos_*`
    键须从 par 显式剔除（Config 不再声明 → 成为 unknown parameter）。剔除时
    用**显式键列表**，禁止 `"targ" in k` 式模糊匹配——会误删激光 `ed_targetX_1`
    （"target" 包含 "targ"）。改材料密度同理：模板的 `sim_rhoShld` 等占位值
    会覆盖 Config 默认，须显式覆写（如 V 层 1 → 6.11）。
11. **EOS 表复制须校验返回值**：`copy_eos_file` 源缺失时返回 `None` 而非抛异常，
    仅判 `FileNotFoundError` 会漏检。新克隆仓库的注册表路径可能与实际数据布局
    不符（He/CH BADGER 表目前仅在旧 flash_c 仓库）——layer_tracer_CH_ml 的
    `_copy_cn4()` 实现了 注册表别名 → eos_op_data 递归 → 旧仓库兜底 的三级查找。
12. **outputfiles 收集位置与 run_id**：`WslSpec.outputfiles_dir`（Python 端）与
    `ShellScriptGenerator` 的 `config["collect_dir"]`（run_flash.sh 端）必须
    指向同一基目录；运行时 `run_wsl` 自动分配 run_id（06d）并以环境变量
    `FLASH_COLLECT_DIR` 注入 `run_NNNNNN` 子目录（优先于脚本内置值），
    输入快照同步归档到 `flash_input/run_NNNNNN/`。推荐基目录统一
    `{场景}/flash_output/outputfiles`。
13. **HDF5 剖面分析必须走 `extraction_mode` 路径**（2026-08-29 三方交叉验证结论）：
   `FlashDataLoader` 的**默认 `load()` 走 `read_var`，不过滤 `node type`**，非叶子
   父块的陈旧粗网格数据被混入且坐标/数据错位——实测 16352 点中 81 个与真值不符，
   最大偏差 1.0 g/cm³（真值 1.0 处报 1e-6，反之亦然）。涉及剖面、界面、极值的
   分析**禁止使用默认 `load()`**，应显式指定提取模式：

   ```python
   from flash.output_processors.loader import FlashDataLoader
   c = FlashDataLoader(path).load(compute_derived=False, extraction_mode="yt")
   # extraction_mode="yt"  → FlashHDF5File.extract_var_with_yt (只取 node_type==1)
   # extraction_mode="h5py" → extract_var_yt_style (同样只取叶子, 无 yt 依赖, 超算推荐)
   ```

   两种模式均已实现叶子块过滤并经三方交叉验证一致（yt vs h5py-leaf：
   max rel diff ≈ 2e-6，来自间断处插值）。可全局切换默认模式：
   `flash.output_processors.extraction_modes.set_extraction_mode("yt")`
   或环境变量 `FLASH_EXTRACTION_MODE=yt`。

---

## 架构说明

```
flash/
├── scenarios/
│   ├── __init__.py               ← 容错导入各场景包 (触发注册)
│   ├── base.py                   ← SimulationScenario 数据类
│   ├── registry.py               ← 场景注册表 (get/list/register)
│   ├── simulator.py              ← FlashSimulatorEngine (注册场景统一引擎)
│   ├── runner.py                 ← 统一运行器 (RUN_MODE 一键切换 wsl/hpc)
│   ├── interpolator.py           ← 时空插值共享模块
│   ├── README.md                 ← 本文档
│   │
│   ├── center_evolution/         ← 物理专题: 中心演化
│   │   └── ch_center/            ← CH 靶中心演化 (注册场景 + 本地直跑入口)
│   │
│   ├── collision_compression/    ← 物理专题: 预留 (暂无场景)
│   │
│   ├── plasma_preparation/       ← 物理专题: 预留 (暂无场景)
│   │
│   ├── flash_demo/               ← 演示场景
│   │   ├── demo_local/           ← 本机 (WSL) 1D LaserSlab 演示
│   │   ├── demo_hpc/             ← 超算 (SLURM) 1D LaserSlab 演示
│   │   └── hello_flash/          ← 安装部署冒烟测试
│   │
│   └── private/                  ← 私有场景 (不随发布包分发)
│       └── tracer/               ← 分层示踪靶系列 (_par_layers.py 共享规范参数)
│           ├── layer_tracer_CH/  ← CH 示踪场景 (单示踪层模板)
│           ├── layer_tracer_CH_ml/ ← 多薄层示踪场景 (6 物种, 预诊断图 + 新输出布局)
│           └── layer_tracer_Ti/  ← Ti 示踪场景
│
└── test/scenarios/               ← 场景接口测试
    ├── run_all_scenario_tests.py ← 批量测试运行器
    ├── test_scenarios_imports.py ← 导入与注册表测试
    ├── test_scenario_par_build.py← .par 生成测试
    ├── test_engine_dryrun.py     ← 引擎 dry-run 测试
    └── test_real_flash_run.py    ← 真实 FLASH 端到端测试
```

### 关键设计原则

1. **场景 = 参数 + 组装流程**：场景差异在 `config_constants`/物种定义/参数字典，共享
   runner 与 input_gen 生成器，不复制工作流代码。
2. **规范参数自包含**：`.par` 全文参数内嵌于 `_par_layers.py` 等参数字典，避免手抄错。
3. **输出可追溯**：输入文件与运行日志长期保留在 `flash_input/`，每次运行可复现。
4. **一键切换运行环境**：`RUN_MODE = "wsl" | "hpc"`（或环境变量 `FLASH_RUN_MODE`），
   同一场景本机调试与超算正式运行零改动切换。

---

## EOS/Opacity 表 (`.cn4`) 温度单位

所有 `.cn4` 文件的**温度网格单位为 eV**（电子伏特），而非 K（开尔文）。FLASH 运行时
将 `sim_*` 系列参数（如 `sim_teleCham`）中设定的 K 值自动转换为 eV 查表。

| 值 | eV | K |
|-----|-----|-----|
| 室温 | 0.025 eV | 290.11375 K |
| 旧 EOS 表下界 | 2.0 eV | 23209 K |
| 新 EOS 表下界 | 0.01 eV | 116 K |

初始温度注意事项:
- **旧 EOS 表**（`he-imx-*`, `polystyrene-imx-008*`）起始温度 2.0 eV，室温低于下界时
  FLASH 外推；简单场景（低功率）可用，高功率下扩散求解器易报
  `[Diffuse]: computed dt is not positive!`。
- **新 EOS 表**（`Z02_*`, `Z06_*`, `Z14_*`）起始温度 0.01 eV，室温在有效范围内，优先使用。
- 如需自定义初始温度，在场景 `config_constants` 或 `params_overrides` 中显式传入
  `sim_teleCham=290.11375` 等参数。

> 此说明适用于 `sim_tele*`（电子温度）、`sim_tion*`（离子温度）、`sim_trad*`（辐射温度）
> 所有温度参数。

```bash
# 运行所有接口测试 (无需 FLASH, 快速)
cd flash/test/scenarios
python run_all_scenario_tests.py

# 运行真实 FLASH 端到端测试 (需要 5-10 分钟)
python test_real_flash_run.py --scenario ch_center
```

---

## 常见问题

### Q: FLASH 编译失败？

检查:
1. WSL 中 `~/<user>/FLASH/FLASH4.8/` 是否存在
2. `Config` 中 `DATAFILES` 指向的 `.cn4` 文件是否齐全（场景目录内要有实际文件）
3. `SETUP_FLAGS` 中的 FLASH 单位是否已安装 (`+laser`, `+uhd3t`, `+mgd`)

### Q: `[Diffuse]: computed dt is not positive!`

EOS/opacity 表与初始温度不匹配。检查:
- 初始温度是否低于 `.cn4` 表的最低温度节点（见上节）
- `rt_mgdNumGroups` 和 `rt_mgdBounds` 必须与 `.cn4` 文件的 grupbd 匹配
- 更换为新 EOS 表或调整 `eos_*EosType`

### Q: `.par` 中出现 Unknown runtime parameter 告警？

`.par` 的 `sim_*` 键未在 `Config` 中声明 `PARAMETER`。运行内在关联检查定位:

```bash
python flash/input_gen/gen_checker/check_relations.py <flash_input 目录>
```

### Q: WSL 运行报 `/bin/bash^M: bad interpreter`？

脚本为 CRLF 换行。用 `dos2unix` 或编辑器转为 LF 后重跑（生成器默认输出 LF）。

### Q: 如何并行运行多个仿真？

直跑场景在 Python 中循环调用生成器并改写 `config_constants`（注意输出目录隔离）；
引擎场景每次 `engine.run()` 自增 run_id，天然互不冲突。

---

## 许可、致谢与商用

flash-sim 采用双重许可，完整条款见根目录 [README.md 许可章节](../README.md#许可)、[LICENSE](../LICENSE) 与 [NOTICE](../NOTICE)。

- **出版物致谢**：使用本场景系统（flash-sim）产生的任何出版物，请感谢**绵阳市的 PhySimX 团队**开发了该仿真辅助 Python 包。建议文案：*"We acknowledge the PhySimX team (Mianyang, China) for developing the flash-sim auxiliary Python package used in this work."*
- **商用说明**：flash-sim 的 Python 代码以 Apache 2.0 许可，其商用须遵守所有适用许可（含 FLASH 仿真引擎的 FLASH License Agreement §5）；商用场景下的授权与责任以届时适用的许可及书面约定为准。
