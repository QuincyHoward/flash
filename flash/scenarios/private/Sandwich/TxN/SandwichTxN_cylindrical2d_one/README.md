# SandwichTxN_cylindrical2d_one

二维柱坐标（R-Z + 3Din2D）每侧单束（共 2 束）正入射场景，完全自包含。

## 几何与单位
- FLASH 网格 x=r∈[0,900] µm、y=z∈[-450,450] µm；靶在 z=0 水平，激光沿 ±z 从上下入射。绘图横轴 r、纵轴 z。
- 材料与层厚沿用 1D；CH/Si 半径 650 µm。
- ed_power 单位：W（3Din2D）；峰值 1.6e12 W/束（1600 J/束，两束共 3200 J）。
- 45° 等腰梯形收敛：lens 半径 1400 µm → 靶面半径 400 µm（lens 距靶 1000 µm）。
- `ed_semiAxisMajorTorsionAxis="x"`（不能用 z，否则沿传播方向 abort）。

## 网格与 AMR
- setup：`-2d +cylindrical -nxb=12 -nyb=8 -maxblocks=8192`；par `nblockx=12, nblocky=8`；`xl_boundary_type=axisymmetric`。
- 高细化区：r≤425 µm 且 |z|≤4.5 µm；CH 降级；He 最粗；`lrefine_max=8`。

## 命令
```
python sandwich_txn_cylindrical2d_one.py gen --force
python scripts/geometry_validation.py --depo <chk> --out analysis/hpc/geometry_validation_hpc.png
python -m flash.scenarios.core.entry.cli submit SandwichTxN_cylindrical2d_one --run-id <id> --tmax 1e-11 --ntasks 48
```

HPC 结果：`../hpc_results/SandwichTxN_cylindrical2d_one/920003/`；汇总图：`analysis/hpc/geometry_validation_hpc.png`。

## 激光功率换算公式
- 脉冲等效平顶时长 `t_eff = 1.0 ns`；∫P dt = 峰值 × 1.0 ns。
- 1D（W/cm²）：`E / (π(0.04 cm)² × t_eff)`；3.183e14 W/cm² 对应双束 1600 J 归一。
- 2D 笛卡尔非 3Din2D（W/cm）：`E / (t_eff × 1 cm)`。
- **本场景：2D R-Z + 3Din2D（W）**：`ed_power = E / t_eff`，1600 J → `1.6e12 W`。
- 3D（W）：总功率 `E/t_eff`。
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
| `ed_laser3Din2D` | `.true.` | R-Z 网格中用 3D 光线追迹并按楔角归一到 2D，功率单位为 W。 |
| `ed_laser3Din2DwedgeAngle` | `0.1°` | 楔形方位角；源码校验必须 `0<angle<180°` 并转弧度。 |
| `geometry` | `cylindrical` | 3Din2D 必须是 `GRID_2DCYLINDRICAL`。 |
| `ed_gridType_*` | `radial2D` | 圆对称 3D 光斑的径向采样网格。 |
| `ed_crossSectionFunctionType_*` | `gaussian2D` | 3D 截面高斯分布；2D 笛卡尔不支持。 |
| `ed_numberOfRays_*` | 4096 | 单束径向采样光线数。 |
| `ed_lensX_* / ed_lensZ_*` | `0 / ±0.1 cm` | 两束沿 ±z 正入射，lens 距靶 1000 µm，target 在原点。 |
| `ed_lensSemiAxisMajor_*` → `ed_targetSemiAxisMajor_*` | `0.14 cm → 0.04 cm` | 45° 等腰梯形收敛；侧壁斜率 tan45°=1，靶面半径 400 µm（直径 800 µm）。 |
| `ed_semiAxisMajorTorsionAxis_*` | `"x"` | 沿 z 传播时 `bProj=sqrt(bx²+by²)=0`，取 z 会触发 torsion abort；x 轴与束方向垂直，可用。 |

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
- 靶体来自 chk species 场；新增中心材料核心放大；光束子图按 par 半轴画梯形边界并标注 1400 µm→400 µm 半径；旧 schematic 子图已删除。
