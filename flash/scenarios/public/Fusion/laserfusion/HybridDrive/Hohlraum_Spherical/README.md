# Hohlraum_Spherical — 混合驱动球形黑腔构型 (2D 柱坐标 r-z)

> 最后核对：2026-11-08 · commit 96aa10d

FLASH4.8 SimulationMain 场景：混合驱动（hybrid drive, HD）几何构型验证。
**Au 球形黑腔（两极 LEH）+ 中心 CH 球形靶丸 + 低密度 He 充气**。

> 状态: ★ 极短几何验证通过（2026-11-08, tmax=1e-13 s）★ 物理全开验证通过（2026-11-09：ID+DD 双束组激光 + 电子传导 + 热交换，9/9 采样点 OK）
> 运行入口: `run_hybrid_verify.py`（模式 auto/wsl）

## 1. 几何构型（混合驱动 HD 参考设计）

2D 柱坐标 `geometry="cylindrical"`：x = r（半径，r=0 为对称轴，边界
`axisymmetric`），y = z（轴向）。靶丸置于坐标原点（球腔中心）。

| 部件 | 材料 | 尺寸 | 密度 |
|---|---|---|---|
| Au 球壳 | Au (`gold`) | 内半径 2.72 mm，壁厚 30 µm | 19.32 g/cc |
| 双极 LEH 开孔 | 开孔，充气延伸 | 极帽判据 \|z\|/rr ≥ 0.851（≈ LEH 半径 1.43 mm） | — |
| 中心靶丸壳（球形） | CH (`caps`) | 外半径 1.0 mm，壳厚 150 µm | 1.0 g/cc |
| 靶丸内气体 | He (`cgas`) | rr < 0.85 mm | 1e-3 g/cc |
| 腔内充气 | He (`cham`) | 球腔内 + LEH 孔延伸 | 0.96 mg/cm³ |
| 腔外真空 | He (`cham`) | 球壳外 | 1e-6 g/cc |

混合驱动（HD）物理背景（贺贤土院士方案）：
- ID 激光预脉冲 + 主脉冲经 LEH 进入**球形黑腔**（非 NIF 柱腔）内壁吸收
  转热 X 射线，辐射烧蚀预压缩靶丸并形成大尺度低密度冕区；
- DD 激光沿靶丸半径反方向进入球腔，在 ID 冕区临界面处吸收，超声电子
  热波"推土机"式堆积等离子体形成远高于烧蚀压的 **HD 压**，热匀滑后
  驱动对称内爆（中国激光杂志社月报；MRE 10, 057401 (2025) 神光-100kJ
  SRS 实验；Nat. Commun. HD 原理实验）。
- 本场景用与 `Hohlraum_AuCH` 一致的 2.72 mm 腔半径做同尺度跨构型对照。

## 2. 文件清单

| 文件 | 说明 |
|---|---|
| `flash_input/Config` | 模块配置（物种 cham,cgas,caps,gold；sim_* 几何参数声明） |
| `flash_input/Makefile` | `Simulation += Simulation_data.o` |
| `flash_input/Simulation_data.F90` / `Simulation_init.F90` | 参数模块与读取 |
| `flash_input/Simulation_initBlock.F90` | ★ 几何初始化核心：r-z 球壳判据（球壳 + 极帽 LEH + 靶丸 + 充气/真空） |
| `flash_input/hyhohl.par` | 运行参数（tmax=1e-13 s 验证；辐射 MGD 10 群 + 激光沉积 + 电子传导 + 热交换全开） |
| `flash_input/run_flash.sh` | WSL 全流水线（setup→make→run→收集），模块 `QC/Hohlraum_Spherical_HD` |
| `flash_input/*.cn4` + `*.eosmeta.json` | 10 群统一表 ×3（he_10g / ch_10g / au_10g，与 Hohlraum_AuCH 同源，缺失时自动从注册表复制） |
| `run_hybrid_verify.py` | 场景 runner：表复制 → 运行 → 出图 + 定量核对 |
| `scene.json` / `__init__.py` | 场景注册（含声明式 `scenario` 对象） |
| `README.md` | 本文档 |
| `outputfiles/run_NNNNNN/` | chk/plt 产物 + 输入快照（运行后生成，gitignored） |
| `flash_output/` | 几何分布图 + `geometry_check.json` 核对报告（gitignored） |

## 3. setup / EOS 表

```bash
./setup -auto QC/Hohlraum_Spherical_HD -2d +cylindrical -nxb=16 -nyb=16 +hdf5typeio \
        species=cham,cgas,caps,gold +mtmmmt +laser +uhd3t +mgd mgd_meshgroups=10 \
        -objdir=QC/Hohlraum_Spherical_HD -parfile=hyhohl.par
```

EOS/不透明度表与 `Hohlraum_AuCH` 完全同源（10 群统一表，He/CH/Au）。
辐射配置相同：MGD 10 群三开关 `.true.` + `gr_hypreUseFloor=.false.`
（★0 铁律）+ `rt_dtFactor=0.02`。

**物理模型（2026-11-09 全部开启）**：

| 模型 | 配置 |
|---|---|
| 激光沉积 | `useEnergyDeposition=.true.`，3Din2D 束表示（wedge 0.1°）、gaussian2D 焦斑（super-Gaussian n=4）、0.351 µm（3ω）、4096 rays/束 |
| ID 束 ×2 | pulse 1（~2.5e12 W ≈ 5e14 W/cm² @ 400 µm 焦斑）：经极区 LEH（入射穿越点 φ=29° 孔内）→ 低纬腔内壁转 X 射线；lens 置于域外（z=±0.385，FLASH 要求 lens 焦斑整体在域外） |
| DD 束 ×2 | pulse 2（~6.3e11 W @ 200 µm）：沿轴经 LEH 直照靶丸两极（"推土机"增压占位） |
| 电子传导 | `useDiffuse/useConductivity/diff_useEleCond=.true.`，FL-minmax α=0.08，轴 neumann、其余 vacuum |
| 电子-离子热交换 | `useHeatexchange=.true.`（Spitzer），`hx_dtFactor=1e100` 不限 dt |

极短验证不受影响：tmax=1e-13 s 处脉冲处于上升沿（功率 ~1e-4 峰值），
仅激活沉积/传导链路而不破坏几何构型。

## 4. 几何验证判据（run_hybrid_verify.py 自动执行）

| 采样点 | (r, z) cm | 期望物种 | 期望密度 g/cc |
|---|---|---|---|
| gold_wall_equator | 0.2735, 0.000 | gold | 19.32 |
| gold_wall_45deg | 0.1934, 0.1934 | gold | 19.32 |
| leh_fill_hole | 0.140, 0.236 | cham | 9.6e-4 |
| caps_shell_pole | 0.000, 0.0925 | caps | 1.0 |
| caps_shell_equator | 0.0925, 0.000 | caps | 1.0 |
| cgas_center | 0.000, 0.000 | cgas | 1e-3 |
| cham_fill_cavity | 0.150, 0.150 | cham | 9.6e-4 |
| cham_vacuum_out | 0.320, 0.000 | cham | 1e-6 |
| cham_vacuum_polar | 0.050, 0.300 | cham | 1e-6 |

判据：采样格心主导物种质量分数 ≥ 0.9，密度在期望值 2 倍因子内。

## 5. 后续扩展

- 正式 HD 仿真：par 开 `useEnergyDeposition=.true.`，配置双束组
  （ID 束经 LEH 打球腔内壁 + DD 束沿径向直照靶丸）、分阶段脉冲
  （ID 预脉冲/主脉冲 → DD 主脉冲），开 `useDiffuse/useHeatexchange=.true.`，
  tmax 放至 ns 量级（分阶段，先短时验证再放行）。
- 三维八极/六极 LEH 球腔（octahedral hohlraum）需 3D 网格，超出本 2D 场景。

**上级导航**：[../README.md](../README.md)
