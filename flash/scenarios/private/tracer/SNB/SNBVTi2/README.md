# SNBVTi2 — V+Ti 多层示踪靶 + SNB（精确网格 0.02 µm 版）

**一句话**：与 `SNBVTi2_ml` **物理内容完全一致**（shld=V 6.11、tar2=Ti 4.54、
其余 tar*=CH 1.0，6 层示踪 1/2/3/4/6 µm，SNB 非局域热传导），
唯一差别是**网格精度更严格**：`dx = 0.02 µm 精确`，
使 **0.1 µm 薄层恰为 5 个完整网格**，层边界全部落在网格边上。

---

## 1. 与 SNBVTi2_ml 的网格对照

| 场景 | iProcs × nxb | 总格数 | dx | 0.1 µm 层覆盖 |
|---|---|---|---|---|
| `SNBVTi2_ml` | 131 × 128 | 16 768 | 0.02982 µm | 3.35 格（边界不落格边，质量分数跨格分摊） |
| **`SNBVTi2`** | **125 × 200** | **25 000** | **0.02 µm 精确** | **5 整格（层内质量分数恒为 1.0）** |

**精确网格三重设计约束**（生成期强校验，任一不满足即硬失败）：

1. `iProcs×nxb = 25000 = 500 µm / 0.02 µm` → dx 精确；
2. 域边界整除：`400 µm/0.02 = 20000` ✓，`100 µm/0.02 = 5000` ✓
   → x=0 与全部层边界（0.1 µm 整数倍）落在网格边上；
3. `0.1 µm/dx = 5`（整数）→ 每个示踪薄层 5 整格。

**选型依据**：25000 = 2³×5⁵，偶数因子组合中 (125, 200) 每块计算量最大
（200 格/块，通信/计算比最优），125 进程在 NC-E（48 核/节点）占 3 节点
（144 核，空闲 19）最紧凑。备选精确组合：(100, 250) / (250, 100) / (50, 500)。

⚠ **`--nproc` 只接受 125**：+ug 下 `nproc == iProcs`，传其他值会破坏精确
网格 —— `build_setup_flags_ug()` 对非 125 **硬失败**（拒绝静默偏离）。

## 2. 与 SNBVTi2_ml 逐项一致的部分（未改动）

| 项 | 值 |
|---|---|
| 分层拓扑 | 8 物种 / 12 区 / 13 边界（shld\|samp\|tar1\|…\|tar6\|samp） |
| 几何 | delta=0.1 µm；L1/L2/L3/L4/L6 = 1/2/3/4/6 µm；D=50 µm |
| 材质 | shld=V(6.11)、tar2=Ti(4.54)、samp/tar1/3/4/6=CH(1.0)、cham=He(1e-6) |
| EOS/op 表 | V/Ti/CH/He 四张 cn4（成分已按权威读法核验） |
| SNB 参数 | diff_eleFlMode=fl_harmonic、Coef=0.06、cfl=0.2、gr_hypreUseFloor=.false.（铁律）、RiemannSolver=HLL、tstep 1.10、dtmax=2e-12 |
| 辐射 | MGD 10 群、fl_harmonic/1.0 |
| 激光 | 0.351 µm 单光束、82 点功率脉冲 |
| 域 | [-400, 100] µm（align_domain 吸附；nxb=200 时 rootdx 整除 -400 µm，无吸附位移） |
| HPC 驱动 | 委托 `SNBOneCH_ml.run_hpc`（重绑定命名常量）；构建指纹护栏；重复提交护栏 |
| longrun 管线 | `scripts/longrun/`（与 _ml 同构；`SCEN_MODULE` 由目录名自动派生） |

## 3. 用法

```bash
cd <flash 包目录>

# ① 只生成输入文件 + 静态核验（含精确网格三重断言）
python flash/scenarios/private/tracer/SNB/SNBVTi2/SNBVTi2.py --generate-only

# ② NC-E 短测（首次必须完整编译, 勿加 --skip-build）
python flash/scenarios/private/tracer/SNB/SNBVTi2/SNBVTi2.py \
    --tmax 1.0e-11 --nproc 125 --account flash_ssh

# ③ 层位核查（期望: 每层恰 5 格、frac_min=1.0、dx=0.02）
python flash/scenarios/private/tracer/SNB/SNBVTi2/scripts/analysis/check_layers.py \
    --dir flash/scenarios/private/tracer/SNB/SNBVTi2/flash_output/hpc_flash_ssh \
    --expect-cells 5

# ④ 1.6 ns 全流程（提交→下载 120 帧→绘图; 断点续跑; nproc 自动取场景配置 125）
python flash/scenarios/private/tracer/SNB/SNBVTi2/scripts/longrun/03_run_16ns_pipeline.py \
    --account flash_ssh
```

## 4. 短测验收标准（划分正常才允许发起 1.6 ns）

| 检查项 | 通过标准 |
|---|---|
| setup 接受 `-nxb=200` | RUN_EXIT=0（若拒约，切换备选组合 100×250 并同步改三处常量） |
| leaf dx | 0.02 µm（±1e-9） |
| 每层格数 | 恰 **5**（check_layers `--expect-cells 5`） |
| 层内纯度 | frac_min = 1.0000（无跨格分摊） |
| 层位顺序 | shld→tar1→tar2→tar3→tar4→tar6，间距 1 µm 整 |

## 5. 目录结构

```
SNBVTi2/
├── SNBVTi2.py              场景主脚本（精确网格 + 生成/自检/HPC 委托/出图）
├── README.md               本文件
├── docs/                   说明与流程文档（同 _ml, 物理未变）
├── flash_input/            生成物（snbvti2.par / Config / F90 / cn4 / 预诊断图）
├── flash_output/           超算回传结果（hpc_flash_ssh[_16ns]）
├── plots/                  验证图像
└── scripts/
    ├── analysis/check_layers.py   层位核查（bounding box 块法, 可复用）
    └── longrun/            1.6 ns 全流程管线（与 _ml 同构）
```

## 6. 前置条件

与 `SNBVTi2_ml` 相同：必须在 **FLASHSNB** 中编译运行（9 个 SNB 覆盖 F90，
本地权威镜像 `SNB/SNB/source/snb_package/`，License §3 不入库）；
默认超算 **NC-E**（`--account flash_ssh`）。

> 预算提示：总格数 25000（_ml 的 1.49 倍）⇒ 1.6 ns 墙钟约 25 h
> （_ml 实测 16.7 h × 1.49），HYPRE 占比预计仍 >65%（瓶颈不变）。
