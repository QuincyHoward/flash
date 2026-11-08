# flash-sim 场景系统

> 最后核对：2026-11-08 · commit 96aa10d · 本文件为 2026-11-08 重写版（旧版 820 行指南已归档至 [temp_delete/README.md.outdated-20261108.md](temp_delete/README.md.outdated-20261108.md)，历史细节仍可查阅）

flash-sim 场景系统：把 FLASH 仿真物理构型封装为**可发现、可移动、可参数覆盖、可超算批量运行**的独立目录。

---

## 1. 目录总览

```
scenarios/
├── public/            # ★ 公开场景区（官方可分享，见 §2）
│   ├── sandwich/      #   多层靶族：thin_layer_sandwich_si · grad_dens_sandwich
│   ├── center_evolution/  # 中心演化族：ch_center · ch_center_t
│   ├── laserfusion/   #   激光聚变族：hohlraum_auch（2D rz 黑腔验证）
│   └── runs_*/        #   运行产物目录（非场景）
├── private/           # 私有科研场景区（SNB / Sandwich / tracer 家族，不对外介绍）
├── flash_demo/        # 演示场景区（hello_flash / demo_local / demo_hpc）
├── core/              # 场景系统核心（engine 运行引擎 · hpc 提交 · entry CLI · scene_reg 发现）
├── common/            # 场景公共工具（时间控制等）
└── scripts/           # 场景工具链（relocate 整理六件套 · checks 校验 · validation）
```

每个场景目录自包含（`scene.json` + `run.py` + 物理构建脚本），**身份随目录位置自动派生**——整理/移动场景目录无需改任何代码（"位置优先"原则）。

## 2. 公开场景一览（private 区不做介绍）

| 场景 | 目录 | 构型 | 说明 |
|---|---|---|---|
| **thin_layer_sandwich_si** | [public/sandwich/thin_layer_sandwich](public/sandwich/README.md) | Si(0.4µm)/CH(8µm)/He，5e14 W/cm² 双束 1D | 新 EOS 表；已接入超算批量提速（实测最优打包 12×4=196.5 步/s） |
| **grad_dens_sandwich** | [public/sandwich](public/sandwich/README.md) | HE-CH-Si-CH-HE 渐变密度靶，超高斯脉冲 | 1D |
| **ch_center** / **ch_center_t** | [public/center_evolution](public/center_evolution/README.md) | 1D LaserSlab CH 中心层 | 官方一键场景 / 克隆实验版 |
| **hohlraum_auch** | [public/laserfusion/indirect_drive](public/laserfusion/README.md) | Au 黑腔 + CH 靶丸 + He 充气，2D rz | 几何验证（tmax=1e-13） |
| hello_flash / demo_local / demo_hpc | [flash_demo](flash_demo/README.md) | 最小 LaserSlab | 安装冒烟与本机/超算用法示范（demo_hpc 为遗留脚本集，正式批量请用 §5 模块） |

## 3. 如何运行场景

```bash
# ① 场景目录内一键运行（run.py 内容全仓逐字节相同，实现在 core/entry/launcher.py）
python run.py [--mode auto|wsl|hpc] [--tmax 1e-11]

# ② 统一 CLI（list / explain / run / submit）
python -m flash.scenarios.core.entry.cli list
python -m flash.scenarios.core.entry.cli run thin_layer_sandwich_si --tmax 1e-11

# ③ 引擎 API（参数化调用）
from flash.scenarios.core.entry import run_scenario
```

**要点**：
- `--mode auto` = 平台自适应（本机 WSL / 超算 SLURM 自动判定）
- **极短验证技巧**：`--tmax 1e-11`（或场景覆盖 `tmax`）先跑几百步验证链路，再放全程——时间控制（dtinit/dtmax）会随 tmax 自动收缩
- 参数覆盖走场景 `default_params`/`build_par`（场景层只管物理，运行细节一律归 `flash.flash_run`，见 §6 场景层约定）
- 输出结构与编译缓存说明见旧指南归档（§输出结构/编译与缓存章）

## 4. 如何新建 / 修改 / 整理场景

### 4.1 新建（去注册化三件套）

1. **复制最接近的现有场景目录**（或 `python flash/scenarios/scripts/relocate/clone_scene.py` 克隆 + 身份再标识）
2. 改 `scene.json`（name/aliases/description/module/attr——发现系统扫描 manifest，无需注册代码）
3. 改物理构建脚本（`default_params` + `build_par`）；需要 sim_input 自动生成则实现 `ensure_sim_input`
4. **极短 tmax 验证** → 全程运行

### 4.2 修改

- 场景目录内改物理参数/构建脚本即可；**身份不动**（scene.json 派生）
- par 参数释义/排版规范见 `skills/flash-par-gen`；行尾释义由 `flash/input_gen/gen_par/par_comments.py` 提供

### 4.3 整理/移动（relocate 六件套）

```bash
python flash/scenarios/scripts/relocate/audit_portable.py       # 可移植性审计（strict 须 ERROR=0）
python flash/scenarios/scripts/relocate/make_scene_portable.py  # manifest/parents/initfiles 幂等改造
python flash/scenarios/scripts/relocate/decouple_imports.py     # 跨场景 import 解耦
python flash/scenarios/scripts/relocate/relocate_scene.py       # 收纳执行器（git mv + 锚点重写 + 残留扫描）
python flash/scenarios/scripts/relocate/verify_all_scenes.py    # 全场景静态验证
python flash/scenarios/scripts/relocate/clone_scene.py          # 克隆 + 身份再标识
```

**场景层约定**（2026-10-22 模块化改造铁律）：场景目录只做**物理搭建 + 参数覆盖**（SCENE VARS、RUN_MODE 常量、nprocs/account/tmax 覆盖）；**禁止** sbatch/scancel/paramiko 直连、装置绝对路径硬编码——一律下沉 `flash.flash_run`。检查器：`python -m flash.input_gen.gen_checker.check_scene_sources`。

## 5. 超算并行提速（批量仿真）

正式能力在 **`flash/flash_run/remote/batch/`**（场景无关，2026-11-08 定版；由 SandwichTxN 与 thin_layer 两轮超算实测校准）：

```bash
# 一键批量（方案缺省 = 单节点单任务 p1x12；多任务 seq 顺序复用整节点）
python -m flash.flash_run.remote.batch.runner \
    --adapter "<场景模块路径>.batch_adapter:ADAPTER" \
    run --overrides-json '[{"power_factor":1.0},{"power_factor":2.0}]'

# 批量前标定（E1 核数扫描 + E2 打包扫描，多节点并行，产出 calibration.json）
python -m flash.flash_run.remote.batch.calibrate --adapter "<…>:ADAPTER"

# 显式选择打包方案（方案库 = 纯分配拓扑，场景快慢由各场景 leaderboard 实测）
… run --plan p12x4 --overrides-json '…'
```

**核心机制**：

| 机制 | 说明 |
|---|---|
| 方案库 `plans.py` | 纯分配拓扑（instances × ntasks / conc·seq / 绑核 / 墙钟），**不含场景评分**；两级回退：`--plan` 显式 → 默认 p1x12 |
| 适配器协议 `adapter.py` | 子场景实现 ~40 行 SceneBatchAdapter（render_par/static_inputs/hpc_decl/touch_files）即接入 |
| 渲染 `scripts.py` | build 一次 + N 实例 + 显式绑核（conc=累计偏移 / seq=shared 复用）+ 归档内联（超时丢数据教训固化） |
| 控制层 `control.py` | submit/poll/collect + 逐实例 steps/s 解析 + 榜单 `leaderboard.json`（每场景独立沉淀） |
| **自动早停** | 探针投影终值 < 90%×榜单最优 → 自动 scancel、记录、部分数据照常收集（`--no-early-cancel` 关闭） |
| 标定 `calibrate.py` | E1（单任务核数扫描）/ E2（打包密度扫描）/ 余量档；**同任务公平对比**（相同 par、相同 tmax） |

**实测结论速览**（详见 `public/sandwich/thin_layer_sandwich/超算并行提速方案探索报告.md` 与 `private/Sandwich/TxN/SandwichTxN/docs/超算并行仿真提速报告.md`）：单任务最优核数与聚合最优打包**不可跨场景移植**（thin_layer 峰 24r/打包 12×4；SandwichTxN 峰 32r/打包 12×4）；聚合吞吐随打包密度上升但 24×2 型极限密度触顶回落。

## 6. 场景层约定速查

| 允许（场景层） | 禁止（下沉 flash_run / deploy） |
|---|---|
| SCENE VARS（物理参数、材料、层厚、脉冲） | sbatch/scancel/sacct 原始命令 |
| RUN_MODE 常量、nprocs/account/tmax 覆盖 | paramiko/SSH 直连 |
| ensure_sim_input 输入生成 | 装置绝对路径硬编码 |

## 7. 导航

- 各级 README：[public](public/README.md) · [private](private/README.md) · [flash_demo](flash_demo/README.md) · [core](core/README.md) · [common](common/README.md) · [scripts](scripts/README.md)
- 仓库技能（SKILL.md）：`skills/flash-scenario-setup`（新建）· `flash-scenario-family`（家族）· `flash-readme-sync`（本文档体系维护）· `flash-par-gen`（par 生成）· `flash-run-deploy`（提交）· `flash-output-analysis`（结果分析）
- 文档门禁：`python scripts/08_docs/check_docs.py`（链接/模块引用/锚点/敏感信息）
