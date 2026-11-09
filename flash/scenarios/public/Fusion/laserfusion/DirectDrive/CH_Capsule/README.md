# CH_Capsule — 直接驱动几何构型 (2D 柱坐标 r-z)

> 最后核对：2026-11-08 · commit 96aa10d

FLASH4.8 SimulationMain 场景：直接驱动（direct drive, LDD）几何构型验证。
**自由放置 CH 球壳靶丸 + 内 He 气 + 外部 He 真空示踪**（无黑腔、无腔壁）。

> 状态: ★ 极短几何验证通过（2026-11-08, tmax=1e-13 s）★ 物理全开验证通过（2026-11-09：5 束直驱激光 + 电子传导 + 热交换，5/5 采样点 OK）
> 运行入口: `run_direct_verify.py`（模式 auto/wsl）

## 1. 几何构型（直接驱动参考设计）

2D 柱坐标 `geometry="cylindrical"`：x = r（半径，r=0 为对称轴，边界
`axisymmetric`），y = z（轴向）。靶丸置于坐标原点。

| 部件 | 材料 | 尺寸 | 密度 |
|---|---|---|---|
| 中心靶丸壳（球形） | CH (`caps`) | 外半径 1.0 mm，壳厚 150 µm | 1.0 g/cc |
| 靶丸内气体 | He (`cgas`) | rr < 0.85 mm（rr = √(r²+z²)） | 1e-3 g/cc |
| 外部真空 | He (`cham`) | 其余区域 | 1e-6 g/cc |

尺寸依据（直接驱动参考文献）：
- LLE 基线 NIF 直接驱动点火靶：3.4 mm 直径 "all-DT"（CH 壳 1–2 µm + DT 冰
  340 µm，IAEA OV3/5, McCrory et al.）；
- OMEGA 现行 LDD 靶 ~1 mm 直径（"DT-push-on-DT", PoP 31, 040501 (2024)）；
- 本场景沿用与 `Hohlraum_AuCH` 一致的 1 mm CH 壳 + 150 µm 壁厚 + He 气代理
  DT 冰（EOS 表兼容 + 跨驱动构型同尺度对照）。

## 2. 文件清单

| 文件 | 说明 |
|---|---|
| `flash_input/Config` | 模块配置（物种 cham,cgas,caps；sim_* 几何参数声明） |
| `flash_input/Makefile` | `Simulation += Simulation_data.o` |
| `flash_input/Simulation_data.F90` / `Simulation_init.F90` | 参数模块与读取 |
| `flash_input/Simulation_initBlock.F90` | ★ 几何初始化核心：r-z 球壳判据（CH 壳 + 内气 + 真空） |
| `flash_input/direct_drive_ch.par` | 运行参数（tmax=1e-13 s 验证；辐射 MGD 10 群 + 激光沉积 + 电子传导 + 热交换全开） |
| `flash_input/run_flash.sh` | WSL 全流水线（setup→make→run→收集），模块 `QC/CH_Capsule_DD` |
| `flash_input/*.cn4` + `*.eosmeta.json` | 10 群统一表 ×2（he_10g / ch_10g，与 Hohlraum_AuCH 同源，缺失时自动从注册表复制） |
| `run_direct_verify.py` | 场景 runner：表复制 → 运行 → 出图 + 定量核对 |
| `scene.json` / `__init__.py` | 场景注册（含声明式 `scenario` 对象） |
| `README.md` | 本文档 |
| `outputfiles/run_NNNNNN/` | chk/plt 产物 + 输入快照（运行后生成，gitignored） |
| `flash_output/` | 几何分布图 + `geometry_check.json` 核对报告（gitignored） |

## 3. setup / EOS 表

```bash
./setup -auto QC/CH_Capsule_DD -2d +cylindrical -nxb=16 -nyb=16 +hdf5typeio \
        species=cham,cgas,caps +mtmmmt +laser +uhd3t +mgd mgd_meshgroups=10 \
        -objdir=QC/CH_Capsule_DD -parfile=direct_drive_ch.par
```

EOS/不透明度表（10 群统一，2026-11-08 `gen_hohlraum10.py`）：
- `cham`/`cgas`（He）→ `Z02_1.00-20261108_2013.cn4`（he_10g）
- `caps`（CH）→ `Z06_0.50-Z01_0.50-20261108_2013.cn4`（ch_10g）

辐射配置与 `Hohlraum_AuCH` 相同：MGD 10 群三开关 `.true.` +
`gr_hypreUseFloor=.false.`（★0 铁律）+ `rt_dtFactor=0.02`。

**物理模型（2026-11-09 全部开启）**：

| 模型 | 配置 |
|---|---|
| 激光沉积 | `useEnergyDeposition=.true.`，3Din2D 束表示（wedge 0.1°）、gaussian2D 焦斑（super-Gaussian n=4）、0.351 µm（3ω）、4096 rays/束 |
| 直驱束 ×5 | pulse 1（~6.3e11 W ≈ 5e14 W/cm² @ 200 µm 焦斑）：轴向极点 2 束 + 斜 30° 2 束（40°N 靶点）+ 赤道环 1 束（OMEGA/NIF-DD 类多锥角直照；径向束 torsion 轴用 "z"——纯径向束 bz=0 时 "x" 轴非法） |
| 电子传导 | `useDiffuse/useConductivity/diff_useEleCond=.true.`，FL-minmax α=0.08，轴 neumann、其余 vacuum |
| 电子-离子热交换 | `useHeatexchange=.true.`（Spitzer），`hx_dtFactor=1e100` 不限 dt |

极短验证不受影响：tmax=1e-13 s 处脉冲处于上升沿（功率 ~1e-4 峰值），
仅激活沉积/传导链路而不破坏几何构型。

## 4. 几何验证判据（run_direct_verify.py 自动执行）

| 采样点 | (r, z) cm | 期望物种 | 期望密度 g/cc |
|---|---|---|---|
| caps_shell_pole | 0.000, 0.0925 | caps | 1.0 |
| caps_shell_equator | 0.0925, 0.000 | caps | 1.0 |
| cgas_center | 0.000, 0.000 | cgas | 1e-3 |
| cham_vacuum_out | 0.120, 0.000 | cham | 1e-6 |
| cham_vacuum_axial | 0.050, 0.130 | cham | 1e-6 |

判据：采样格心主导物种质量分数 ≥ 0.9，密度在期望值 2 倍因子内。

## 5. 后续扩展

- 正式直接驱动仿真：par 开 `useEnergyDeposition=.true.`，配置 OMEGA 60 束 /
  NIF DD 束组（多锥角近径向均匀辐照）与连续脉冲（picket + main），
  开 `useDiffuse/useHeatexchange=.true.`，tmax 放至 ns 量级（分阶段）。
- DT 冰层物种（需 DT EOS/不透明度表）可替换 He 气代理。

**上级导航**：[../README.md](../README.md)
