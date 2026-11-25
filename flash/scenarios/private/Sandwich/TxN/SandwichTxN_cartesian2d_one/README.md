# SandwichTxN_cartesian2d_one

二维笛卡尔 CH/Si/CH 三明治靶每侧单束（共 2 束）正入射场景，完全自包含。

## 几何与单位
- 域：x（横向）±900 µm，y（层堆叠）±450 µm；靶在 y=0 水平，激光沿 ±y 从上下入射。
- 材料与层厚沿用 1D；CH/Si 横向直径 1300 µm。
- ed_power 输入值：W（3D 等效单束总功率 1600 J / 1 ns）；`ed_adjustBeamsTargetIntensity=.true.`，FLASH 内部按 2/(πr) 自动换成等效 W/cm。
- 脉冲：(0,0)、(0.3 ns,峰值)、(1.0 ns,峰值)、(1.3 ns,0)，λ=0.351 µm。
- 45° 等腰梯形收敛光斑：lens 半宽 1400 µm → 靶面半宽 400 µm（lens 距靶 1000 µm，侧壁 45°）。

## 网格与 AMR
- setup：`-2d +cartesian -nxb=12 -nyb=8 -maxblocks=8192`；par `nblockx=12, nblocky=8`。
- 高细化区：|x|≤425 µm 且 |y|≤4.5 µm；CH 降级；He 最粗；`lrefine_max=8`。

## 命令
```
python sandwich_txn_cartesian2d_one.py gen --force
python scripts/geometry_validation.py --depo <chk> --out analysis/hpc/geometry_validation_hpc.png
python -m flash.scenarios.core.entry.cli submit SandwichTxN_cartesian2d_one --run-id <id> --tmax 1e-11 --ntasks 48
```

HPC 结果：`../hpc_results/SandwichTxN_cartesian2d_one/920001/`；汇总图：`analysis/hpc/geometry_validation_hpc.png`。

## 激光功率换算公式
- 脉冲等效平顶时长：`t_eff = 1.0 ns`（0→0.3 ns 上升、0.3→1.0 ns 平顶、1.0→1.3 ns 下降；∫P dt = 峰值 × 1.0 ns）。
- 1D（W/cm²）：`ed_power = E / (A × t_eff)`，`A = π(0.04 cm)² = 5.027e-3 cm²`；单束 800 J → 1.59e14 W/cm²，1D 原场景按双束 1600 J 归一得到 3.183e14 W/cm²。
- 2D 笛卡尔、非 3Din2D：设 `ed_adjustBeamsTargetIntensity=.true.`，par 填 3D 等效总功率 `P3D[W]`。本场景 1600 J → `1.6e12 W`；FLASH 内部换算 \(2P_{\rm 3D}/(\pi r)\)，\(r=0.04\) cm，等效 `2.55e13 W/cm`。
- 2D R-Z + 3Din2D（W）：`ed_power = E / t_eff`，1600 J → `1.6e12 W`。
- 3D（W）：总功率 `E/t_eff`，靶面强度按 `P/A_spot`。

## 验证图说明
- 唯一权威汇总图为 `analysis/hpc/geometry_validation_hpc.png`。靶体颜色来自 chk species 场（`targ`=Si、`poly`=CH、`cham`=He）；无 chk 时按 par 层参数回退。新增中心数微米材料核心放大；光束子图用 par 的 lens/target 半轴画梯形收敛边缘并标注 1400 µm→400 µm 半径；旧错误 footprint 示意子图已删除。
