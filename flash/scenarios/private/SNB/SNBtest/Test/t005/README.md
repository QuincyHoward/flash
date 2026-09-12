# t005 —— 2×2 辐射开关对比（薄驱动 · 调用 SNB/SNB 核心模块）

**定位**：本场景**不自己实现任何算法**，全部调用
`flash/scenarios/private/SNB/SNB/`（SNB 场景处理核心模块）的脚本。
这同时是对核心模块的一次**端到端验证**。

---

## 1. 调用链

```
t005/run_t005.py                                        ← 薄驱动（本目录唯一脚本）
  ├─ generate : SNB/SNB/scripts/generate/gen_scene.py    F90 复制 + 2×2 par 生成 + 受控性自检
  ├─ run      : SNB/SNB/scripts/run/run_scene.py         部署→setup→make→run→收集（校验后删）
  └─ plot     : SNB/SNB/scripts/analysis/compare_4way.py 2×2 四联图 + 定量表
```

核心模块路径由 `run_t005.py` 内的 `_find_snb_core()` **向上逐级查找**
（名为 `SNB` 且含 `scripts/` 与 `source/` 的目录），不写死层数。

---

## 2. 四腿设计（受控）

| 腿 | 树 | 热传导源 | 辐射三开关 |
|---|---|---|---|
| FL-SH radON  | 标准 FLASH | 树原生（本就调用辐射） | `.true.` ×3 |
| FL-SH radOFF | 标准 FLASH | 树原生 | `.false.` ×3 |
| SNB radON    | FLASHSNB | 作者 SNB 版 | `.true.` ×3 |
| SNB radOFF   | FLASHSNB | 作者 SNB 版 | `.false.` ×3 |

★ **SNB 侧两腿必须用 `radON` 驱动变体**（恢复被注释的辐射推进调用）。
不做这一步，radON 腿的辐射**开不起来** —— par 三开关形同虚设。

**效率**：辐射是纯 par 开关 → **同侧两腿共用 objdir 与二进制**，
每侧只 setup/make 一次，换 par 跑两次。

**受控性由生成器自动断言**（实测输出）：
```
[同腿 snb]  snb_radon.par vs snb_radoff.par: 差异键
           ['basenm','log_file','rt_useMGD','useOpacity','useRadTrans']
[同腿 snb]  F90 文件数 = 12 (两状态共用同一份 ✓)
[同腿 flsh] 差异键同上; F90 文件数 = 4
[跨腿 snb vs flsh] 逐字节相同 8 个
```

---

## 3. 用法

```bash
cd <flash 包目录>
PY=python
T=flash/scenarios/private/SNB/SNBtest/Test/t005

# 全流程（生成 → 四腿运行 → 出图）
$PY $T/run_t005.py

# 分步
$PY $T/run_t005.py --stage generate      # 只生成场景
$PY $T/run_t005.py --stage run           # 只跑仿真
$PY $T/run_t005.py --stage plot          # 只出图

# 短时验证（★ 新场景先跑这个）
$PY $T/run_t005.py --tmax 1.0e-11 --tag smoke
```

---

## 4. 目录结构（分门别类）

```
t005/
├── run_t005.py            ← 薄驱动（唯一脚本）
├── scene/                 ← 生成的场景（F90/par，不入库）
│   ├── sim_snb/flash_input/    {snb_radon.par, snb_radoff.par, Config, Makefile,
│   │                            Simulation_*.F90, 9 覆盖 F90, *.cn4}
│   ├── sim_flsh/flash_input/   {flsh_radon.par, flsh_radoff.par, Config, ...}
│   └── flash_output/sim_{snb,flsh}/{radon,radoff}/   ← chk/plt/日志
├── images/                ← ★ 对比图
│   ├── pcolor/    xt4_<var>_<tag>.png    2×2 四联时空彩图（7 张）
│   ├── profiles/  prof4_<var>_<tag>.png  2×2 四联 10 时刻剖面（7 张）
│   ├── ablation/  ablation_4way_<tag>.csv
│   └── compare/   summary_4way_<tag>.md
├── results/               ← 定量表副本（csv/md）
├── logs/                  ← 各阶段日志
└── README.md
```

物理量（7 个）：`tele[eV]` `tion[eV]` `trad[eV]` `dens[g/cm³]` `pele[Mbar]` `pres[Mbar]`
`nele[cm⁻³]`（`nele` 对数色标）。数据源 **chk**。

绘图规范：全英文标签、字号 ≥18 pt、DPI 450、线宽 ≥2.4。

---

## 5. 关键参数（由核心模块 `snb_params.py` 提供）

| 项 | 值 |
|---|---|
| 网格 | `+ug` 固定块 `iProcs=8 × nxb=128` = 1024 格，dx≈0.293 µm |
| 域 | [−50, 250] µm（CH 靶 [−50,0] + He 腔 [0,250]） |
| 物种 | cham, tar1, tar2, tar3 |
| 激光 | 4 段梯形 0/0.2/0.99/1.0 ns，1.5e14 W/cm²，0.351 µm |
| 辐射 | MGD 10 群（边界 0.1…1e5 eV） |
| 热传导 | `fl_harmonic` / 0.06 |
| 时间 | **`dtmax=2.0e-14`** ★、`tmax=0.8e-9`、`tstep=1.10`、`cfl=0.2` |
| 输出 | `chk` 5e-11（密）、`plt` 4e-10（疏） |

---

## 6. 排查记录（首次搭建时踩到的坑，均已修复在核心模块内）

| 现象 | 根因 | 修复位置 |
|---|---|---|
| `MGD Error: Bad group boundary` | `rt_mgdBounds` 是**列表**，被直接写成一行 Python 列表字面量 | `gen_scene.build_par`：展开为 `rt_mgdBounds_1..N+1` |
| `ed_setupBeams: invalid pulse number!` | 漏了把 beam 绑定到 pulse | `gen_scene.build_par`：补 `ed_pulseNumber_1 = 1` |
| `Negative 3T internal energy`（启动即失稳） | 生成的 par **缺流体/EOS 块**（`smallt`/`eosModeInit`/`slopeLimiter`/`shockDetect`/`RiemannSolver` 等） | `snb_params.HYDRO_EOS` + `gen_scene` 引入 |
| 读不到 chk 变量（"need at least one array"） | `unknown names` 的元素是 **repr 定宽字符串**（如 `"[b'absr']"`），与变量名不相等 → 存在性判断恒失败 | `compare_4way.load_chk`：改用 `key in f` |
| `NameError: s_` | 路径/参数补丁引入的笔误 | `run_scene.main` |

---

## 7. 与 t004 的关系

| 项 | t004（旧） | t005（本场景） |
|---|---|---|
| 工具来源 | 场景内自带脚本（`gen_t004_inputs.py` 等） | **调用 SNB/SNB 核心模块** |
| 受控矩阵 | 手写 4 腿 | `gen_scene.py --radiation both` 自动生成 |
| F90 来源 | 从 `SNBtest/src` 复制 | 从 `SNB/SNB/source/` 复制 |
| 出图 | `compare_4way.py`（t004 内） | `SNB/SNB/scripts/analysis/compare_4way.py` |

t005 的物理设置与 t004 **一致**，因此两者的定量结果应可比对
（可作为核心模块正确性的交叉验证）。
