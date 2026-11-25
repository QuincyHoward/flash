# SandwichTxN_cartesian2d

二维笛卡尔 CH/Si/CH 三明治靶四束 45° 斜入射场景，完全自包含，不依赖其他新场景。

## 几何与单位
- 域：x（横向）±900 µm，y（层堆叠）±450 µm；靶在 y=0，水平放置，激光从 ±y 上下入射。
- 层结构沿用 1D：Si 0.92 µm / 致密 CH 1 µm×2 / CH 泡沫 50 µm×2；CH/Si 横向直径 1300 µm，He 背景 ρ=1e-6 g/cm³。
- ed_power 输入值：W（3D 等效单束总功率 800 J / 1 ns）；`ed_adjustBeamsTargetIntensity=.true.`，FLASH 内部按 2/(πr) 自动换成等效 W/cm。
- 脉冲：(0,0)、(0.3 ns,峰值)、(1.0 ns,峰值)、(1.3 ns,0)，λ=0.351 µm。
- 4 束 45°，靶面投影直径 800 µm ⇒ 束垂直截面宽 800×cos45° ≈ 565.7 µm。

## 网格与 AMR
- setup：`-2d +cartesian -nxb=12 -nyb=8 -maxblocks=8192`；par `nblockx=12, nblocky=8`。
- 高细化区：|x|≤425 µm 且 |y|≤4.5 µm；CH 泡沫中等；He 最粗；`lrefine_max=8`。

## 命令
```
python sandwich_txn_cartesian2d.py gen --force
python sandwich_txn_cartesian2d.py run --tmax 1e-11 --mode wsl --nproc 4
python scripts/geometry_validation.py --depo <chk> --out analysis/hpc/geometry_validation_hpc.png
python -m flash.scenarios.core.entry.cli submit SandwichTxN_cartesian2d --run-id <id> --tmax 1e-11 --ntasks 48
```

HPC 结果：`../hpc_results/SandwichTxN_cartesian2d/910048/`；汇总图：`analysis/hpc/geometry_validation_hpc.png`。

## 激光功率换算公式
- 脉冲等效平顶时长：`t_eff = 1.0 ns`（0→0.3 ns 线性上升、0.3→1.0 ns 平顶、1.0→1.3 ns 线性下降；∫P dt = 峰值 × 1.0 ns）。
- 1D（W/cm²）：`ed_power = E / (A × t_eff)`，`A = π(400 µm)² = π(0.04 cm)² = 5.027e-3 cm²`。单束 800 J 对应 1.59e14 W/cm²；1D 原场景按双束总能量 1600 J 归一，故 par 峰值 3.183e14 W/cm²。
- 2D 笛卡尔、非 3Din2D：设 `ed_adjustBeamsTargetIntensity=.true.`，par 直接填 3D 等效总功率 `P3D[W] = E/t_eff`。本场景 800 J → `8e11 W`。FLASH 内部用 \(P_{\rm 2D}=2P_{\rm 3D}/(\pi r)\)，\(r=0.028284\) cm，等效靶面功率约 `1.80e13 W/cm`。
- 2D R-Z + 3Din2D（W）：`ed_power = E / t_eff`。800 J → `8.0e11 W`；`_one` 1600 J → `1.6e12 W`。
- 3D（W）：同样为总功率 `E/t_eff`；靶面峰值强度另按光斑面积 `P/A_spot` 计算。

## 验证图说明
- 唯一权威汇总图为 `analysis/hpc/geometry_validation_hpc.png`：靶体色块来自 chk 的 species 场（`targ`=Si、`poly`=CH、`cham`=He），无 chk 时回退到 par 层参数；新增中心数微米材料核心放大；光束子图按 par 的 lens/target 半轴画光束边缘并标注半径与靶面投影；已删除旧的错误 footprint 示意子图。
