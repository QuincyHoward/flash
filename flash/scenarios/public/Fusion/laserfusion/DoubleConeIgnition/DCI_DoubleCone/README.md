# DCI_DoubleCone — 双锥对撞点火构型 (2D 柱坐标 r-z)

> 最后核对：2026-11-08 · commit 96aa10d

FLASH4.8 SimulationMain 场景：双锥对撞点火（double-cone ignition, DCI）
几何构型验证。**对向放置 Au 开口双锥 + 中心 CH 燃料球 + 锥内 CH 燃料填充
+ He 真空示踪**。

> 状态: ★ 极短几何验证通过（2026-11-08, 7/7 采样点; 首版编译因 FLASH constants.h `#define PI` 宏冲突修正后通过）★ 锥顶镂空修正 + 物理全开验证通过（2026-11-09：9/9 采样点含镂空区校验，加热束 2 + 轴向快点火占位束 2 + 电子传导 + 热交换）
> 运行入口: `run_dci_verify.py`（模式 auto/wsl）

## 1. 几何构型（DCI 参考设计，简化 2D）

2D 柱坐标 `geometry="cylindrical"`：x = r（半径，r=0 为对称轴，边界
`axisymmetric`），y = z（轴向）。燃料球置于坐标原点（两锥顶几何中心）。

| 部件 | 材料 | 几何判据 | 密度 |
|---|---|---|---|
| Au 锥壳 ×2 | Au (`gold`) | 内表面 r=(\|z\|−0.06)·tan35°，径向厚 30 µm，壳体 \|z\|≥1.0 mm（顶点镂空段 0.4 mm 之后）至锥口 | 19.32 g/cc |
| 锥顶镂空腔 ×2 | — | \|z\| ∈ [0.6, 1.0] mm 锥顶段无 Au（`sim_coneTipHollowLen`），燃料可推进的预留腔 | — |
| 锥内燃料填充 | CH (`caps`) | 锥内表面以内（含镂空顶段；燃料贴锥内壁，"球冠靶"近似） | 1.0 g/cc |
| 中心燃料球壳 | CH (`caps`) | 0.10 mm < rr ≤ 1.2 mm（rr=√(r²+z²)） | 1.0 g/cc |
| 燃料球内气 | He (`cgas`) | rr < 1.0 mm | 1e-3 g/cc |
| 锥外真空 | He (`cham`) | 其余区域 | 1e-6 g/cc |

几何要点：
- 锥半角 35°（自 z 轴，`sim_coneHalfAngDeg`），锥顶虚拟点位于 ±0.6 mm
  （`sim_coneApexZ`），锥口半径 1.5 mm（`sim_coneOpenR`，锥口轴向
  z ≈ ±2.74 mm）；
- **顶点镂空**（2026-11-09 修正）：壳体从 \|z\| = apex + `sim_coneTipHollowLen`
  （0.6+0.4=1.0 mm）开始，Au 不再落到中轴线——顶段预留空腔供燃料推进，
  锥内燃料填充覆盖镂空区；
- 初始化优先级：Au 锥壳（自镂空段起点向锥口）→ 球内气 → 锥内燃料 →
  燃料球壳 → 真空。

DCI 物理背景（张杰 2020 方案）：
- 氘氚燃料壳置于两个相向开口金锥中，高能纳秒激光沿锥内壁对燃料做
  准等熵压缩 + 加速，在锥口形成高密度超音速喷流；
- 两锥顶几何中心对撞：定向动能高效转化为内能（实验 ~90% 转换率，
  物理学报 71, 20220361），随后皮秒拍瓦激光经磁场引导快点火；
- 分解中心点火"压缩-加速-对撞-快加热"四过程，规避减速阶段 RT 不稳定性；
- 神光 II 升级实验：8 束 351 nm 加热激光（与竖直 50° 夹角，上下各 4 束
  环向错开 45°），焦斑 700 µm，单束 ~1.75 kJ，~1.8×10¹⁴ W/cm²
  （物理学报 72, 20230442）；本场景 DT 以 CH/He 代理（表兼容）。

## 2. 文件清单

| 文件 | 说明 |
|---|---|
| `flash_input/Config` | 模块配置（物种 cham,cgas,caps,gold；sim_* 锥几何参数声明） |
| `flash_input/Makefile` | `Simulation += Simulation_data.o` |
| `flash_input/Simulation_data.F90` / `Simulation_init.F90` | 参数模块与读取 |
| `flash_input/Simulation_initBlock.F90` | ★ 几何初始化核心：r-z 锥面判据（锥壳 + 锥内燃料 + 燃料球 + 内气 + 真空） |
| `flash_input/dci.par` | 运行参数（tmax=1e-13 s 验证；辐射 MGD 10 群 + 激光沉积 + 电子传导 + 热交换全开） |
| `flash_input/run_flash.sh` | WSL 全流水线（setup→make→run→收集），模块 `QC/DCI_DoubleCone` |
| `flash_input/*.cn4` + `*.eosmeta.json` | 10 群统一表 ×3（he_10g / ch_10g / au_10g，与 Hohlraum_AuCH 同源，缺失时自动从注册表复制） |
| `run_dci_verify.py` | 场景 runner：表复制 → 运行 → 出图 + 定量核对 |
| `scene.json` / `__init__.py` | 场景注册（含声明式 `scenario` 对象） |
| `README.md` | 本文档 |
| `outputfiles/run_NNNNNN/` | chk/plt 产物 + 输入快照（运行后生成，gitignored） |
| `flash_output/` | 几何分布图 + `geometry_check.json` 核对报告（gitignored） |

## 3. setup / EOS 表

```bash
./setup -auto QC/DCI_DoubleCone -2d +cylindrical -nxb=16 -nyb=16 +hdf5typeio \
        species=cham,cgas,caps,gold +mtmmmt +laser +uhd3t +mgd mgd_meshgroups=10 \
        -objdir=QC/DCI_DoubleCone -parfile=dci.par
```

EOS/不透明度表与 `Hohlraum_AuCH` 完全同源（10 群统一表，He/CH/Au）。
辐射配置相同：MGD 10 群三开关 `.true.` + `gr_hypreUseFloor=.false.`
（★0 铁律）+ `rt_dtFactor=0.02`。

**物理模型（2026-11-09 全部开启）**：

| 模型 | 配置 |
|---|---|
| 激光沉积 | `useEnergyDeposition=.true.`，3Din2D 束表示（wedge 0.1°）、gaussian2D 焦斑（super-Gaussian n=4）、0.351 µm（3ω）、4096 rays/束 |
| 加热束 ×2 | pulse 1（~6.3e11 W ≈ 5e14 W/cm² @ 200 µm 焦斑）：经锥口 25° 入射锥内壁（神光 II 升级 8 束 50° 型的简化 2D） |
| 快点火束 ×2 | pulse 2（~1.6e11 W @ 100 µm）：轴向占位束经镂空顶腔入射（拍瓦快点火占位） |
| 电子传导 | `useDiffuse/useConductivity/diff_useEleCond=.true.`，FL-minmax α=0.08（与全仓 FL-SH 约定一致），轴 neumann、其余 vacuum |
| 电子-离子热交换 | `useHeatexchange=.true.`（Spitzer），`hx_dtFactor=1e100` 不限 dt |

极短验证不受影响：tmax=1e-13 s 处脉冲处于上升沿（功率 ~1e-4 峰值），
仅激活沉积/传导链路而不破坏几何构型。

## 4. 几何验证判据（run_dci_verify.py 自动执行）

| 采样点 | (r, z) cm | 期望物种 | 期望密度 g/cc |
|---|---|---|---|
| gold_cone_upper | 0.0995, +0.200 | gold | 19.32 |
| gold_cone_lower | 0.0995, −0.200 | gold | 19.32 |
| gold_shell_start | 0.0365, +0.110 | gold | 19.32（壳体起点，镂空段之后） |
| tip_hollow_cgas | 0.004, +0.080 | cgas | 1e-3（镂空区无 Au） |
| caps_fuel_ball | 0.000, +0.110 | caps | 1.0 |
| caps_cone_fuel | 0.020, +0.180 | caps | 1.0 |
| cgas_center | 0.000, 0.000 | cgas | 1e-3 |
| cham_vacuum_out | 0.200, 0.000 | cham | 1e-6 |
| cham_vacuum_beyond | 0.180, +0.250 | cham | 1e-6 |

判据：采样格心主导物种质量分数 ≥ 0.9，密度在期望值 2 倍因子内。

## 5. 后续扩展

- 正式 DCI 仿真：par 开 `useEnergyDeposition=.true.`，配置 8 束加热激光
  （50° 入射锥冠、焦斑 700 µm、递升斜坡脉冲）+ 拍瓦快点火束；
  锥内壁 CH 层厚度、DT 燃料物性（需 DT 表）按实验设计细化。
- 对撞过程物理（喷流形成、动能-内能转换）需 tmax 放至 ns/亚 ns 量级
  分阶段运行。

**上级导航**：[../README.md](../README.md)
