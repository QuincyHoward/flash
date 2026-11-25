# SandwichTxN_cylindrical2d

二维柱坐标（R-Z + 3Din2D）CH/Si/CH 三明治靶四束 45° 斜入射场景，完全自包含。

## 几何与单位
- FLASH 网格 x=r∈[0,900] µm、y=z∈[-450,450] µm；靶在 z=0，水平放置，激光从 ±z 上下入射。绘图横轴 r、纵轴 z。
- 材料与层厚沿用 1D；CH/Si 半径 650 µm（直径 1300 µm）。
- ed_power 单位：W（3Din2D 总功率）；峰值 8.0e11 W/束（800 J，1 ns 等效）。
- `ed_laser3Din2D=.true.`，`ed_laser3Din2DwedgeAngle=0.1`；脉冲 (0,0)/(0.3ns,峰值)/(1.0ns,峰值)/(1.3ns,0)；λ=0.351 µm。
- 4 束 45°，靶面投影直径 800 µm，束垂直截面半径 282.8 µm。

## 网格与 AMR
- setup：`-2d +cylindrical -nxb=12 -nyb=8 -maxblocks=8192`；par `nblockx=12, nblocky=8`；`xl_boundary_type=axisymmetric`。
- 高细化区：r≤425 µm 且 |z|≤4.5 µm；CH 降级；He 最粗；`lrefine_max=8`。
- 3D 光束扭转轴不能取 z（沿传播方向会 abort），本场景用 `"x"`。

## 命令
```
python sandwich_txn_cylindrical2d.py gen --force
python scripts/geometry_validation.py --depo <chk> --out analysis/hpc/geometry_validation_hpc.png
python -m flash.scenarios.core.entry.cli submit SandwichTxN_cylindrical2d --run-id <id> --tmax 1e-11 --ntasks 48
```

HPC 结果：`../hpc_results/SandwichTxN_cylindrical2d/920002/`；汇总图：`analysis/hpc/geometry_validation_hpc.png`。

## 激光功率换算公式
- 脉冲等效平顶时长：`t_eff = 1.0 ns`；∫P dt = 峰值 × 1.0 ns。
- 1D（W/cm²）：`E / (π(0.04 cm)² × t_eff)`；3.183e14 W/cm² 对应双束合计 1600 J。
- 2D 笛卡尔非 3Din2D（W/cm）：`E / (t_eff × 1 cm)`。
- **本场景：2D R-Z + 3Din2D（W）**：`ed_power = E / t_eff`，800 J → `8.0e11 W`，`_one` 1600 J → `1.6e12 W`。
- 3D（W）：同样为总功率 `E/t_eff`。
- 源码依据（只读）：`/root/QC/FLASH/FLASH4.8/source/physics/sourceTerms/EnergyDeposition/EnergyDepositionMain/Laser/LaserPulses/ed_setupPulses.F90:96-104`
```fortran
write (parameterString,'(a,i0,a,i0)') "ed_power_", pulse, "_", 1
call RuntimeParameters_get (parameterString, pulsePower)
if (pulsePower < 0.0) then
    call Driver_abortFlash ("ed_setupPulses: negative pulse power found!")
end if
ed_pulses (1,pulse) % pulsePower = pulsePower * ed_Joule2erg  ! Watt (J/s) -> erg/s
```

## 柱坐标激光参数逐项说明
| 参数 | 取值 | 原因 / 物理含义 |
|---|---|---|
| `ed_laser3Din2D` | `.true.` | R-Z 网格中启用 3D 光线追迹，按楔角把 3D 光束体积归一到 2D 楔形；否则走普通 2D 截面追迹，单位也不是 W。 |
| `ed_laser3Din2DwedgeAngle` | `0.1°` | 楔形方位角，必须 `0<angle<180°`；源码转成弧度并预计算 sin/cos/tan(angle/2)。 |
| `geometry` | `cylindrical` | 3Din2D 校验要求网格必须是 `GRID_2DCYLINDRICAL`。 |
| `ed_gridType_*` | `radial2D` | 3D 束斑横截面用径向网格采样，适合圆对称光斑。 |
| `ed_crossSectionFunctionType_*` | `gaussian2D` | 3D 光斑横截面为 2D 高斯；2D 笛卡尔只能用 `uniform`/`gaussian1D`。 |
| `ed_numberOfRays_*` | 2048/4096 | 径向网格上追迹的光线数；越多统计噪声越小。 |
| `ed_lensX_* / ed_lensZ_*` | `±0.1 / +0.1 cm` | lens 位于 r=±1000 µm、z=+1000 µm；target 在 (0,0)，故入射方向与 z 轴成 45°。 |
| `ed_targetSemiAxisMajor_*` | `0.0283 cm` | 垂直传播方向的束半径 = 400 µm×cos45° ≈ 282.8 µm，使靶面投影直径恰为 800 µm。 |
| `ed_semiAxisMajorTorsionAxis_*` | `"x"` | 椭圆长轴参考轴；若取 `z` 且光束沿 ±z 正入射，投影 `bProj = sqrt(bx²+by²) = 0`，直接 abort。 |

源码依据（只读，均不改）：
- `/root/QC/FLASH/FLASH4.8/source/physics/sourceTerms/EnergyDeposition/EnergyDepositionMain/Laser/LaserRayTrace/ed_traceRays.F90:74-82`
```fortran
case (GRID_2DCYLINDRICAL)
  if (ed_laser3Din2D) then
      call ed_traceRays2DCyl3D (timeStep)
  else
      call ed_traceRays2DRec (timeStep)
  end if
```
- `/root/QC/FLASH/FLASH4.8/source/physics/sourceTerms/EnergyDeposition/EnergyDepositionMain/Laser/EnergyDeposition_init.F90:251-256,341-347`
```fortran
if (ed_laser3Din2D) then
    ed_laser3Din2DwedgeAngle = ed_laser3Din2DwedgeAngle * ed_degrees2rad
    ed_laser3Din2DwedgeCosine = cos (ed_laser3Din2DwedgeAngle)
    ed_laser3Din2DwedgeSine   = sin (ed_laser3Din2DwedgeAngle)
    ed_laser3Din2DwedgeSlope  = tan (ed_laser3Din2DwedgeAngle * 0.5)
end if
...
if (ed_gridGeometry /= GRID_2DCYLINDRICAL) then
    call Driver_abortFlash ('[EnergyDeposition_init] ERROR: Bad 3D in 2D grid geometry')
end if
if (ed_laser3Din2DwedgeAngle <= 0.0 .or. ed_laser3Din2DwedgeAngle >= 180.0) then
    call Driver_abortFlash ('[EnergyDeposition_init] ERROR: Bad wedge angle for 3D in 2D ray trace')
end if
```
- `/root/QC/FLASH/FLASH4.8/source/physics/sourceTerms/EnergyDeposition/EnergyDepositionMain/Laser/LaserBeams/ed_beamsInfo3DRec.F90:396-404`
```fortran
case ('z')
  bxbz  = bx * bz
  bybz  = by * bz
  bProj = sqrt (bx * bx + by * by)
  if (bProj == 0.0) then
      call Driver_abortFlash ("ed_beamsInfo3DRec: Impossible beam torsion z-axis!")
  end if
```

## 验证图说明
- 靶体来自 chk species 场（`targ`=Si、`poly`=CH、`cham`=He），无 chk 时回退 par 层；新增中心数微米材料核心放大；光束子图按 par 半轴画光线走廊并标注半径与 800 µm 靶面投影；旧 schematic 子图已删除。
