# ZPinch_BeLiner — Z 箍缩 Be-liner 构型 (1D 圆柱, MHD)

> 最后核对：2026-11-08 · commit 96aa10d

FLASH4.8 场景：Z 箍缩（Z-pinch）几何构型验证。**复用官方模块
`magnetoHD/ZPinch`（Config/F90/EOS 表/电流波形零修改）**：
Be liner + DD 充气 + 真空三区阶跃构型，+usm3t MHD + MGD 6 群 +
Circuit FileInput 电流驱动。

> 状态: ★ 极短几何验证通过（2026-11-08, 4/4 采样点 OK, tmax=1e-12 s）
> 运行入口: `run_zpinch_verify.py`（模式 auto/wsl）
> ★ 输入由场景装配脚本 `gen_inputs.py` 经 `flash/input_gen` 各隔离模块生成

## 1. 几何构型（官方 ZPinch 示例，1D 圆柱 r ∈ [0, 0.5] cm）

UG 均匀网格 128 格（`iGridSize=128, iProcs=8 → setup -nxb=16`）。

| 区域 | 物种 | 范围 | 密度 | 温度 |
|---|---|---|---|---|
| 充气 | fill (DD 气) | r < 0.29 cm | 3e-2 g/cc | 100 eV（tele/tion/trad 同温预热，stock） |
| Be 套筒 | line (Be) | 0.29 ≤ r ≤ 0.348 cm（厚 0.058 cm） | 1.848 g/cc | 0.5 eV |
| 真空 | vacu (示踪) | r > 0.348 cm | 1e-5 g/cc | 0.5 eV（maxTemp=minTemp 锁定，stock） |

`sim_rhoType=0`（阶跃三区，无高斯剖面）、`sim_pert=0`（无扰动纯净构型）。
物理配置（官方 stock）：`+usm3t`（无分裂 MHD 3T）+ `+mgd mgd_meshgroups=6`
（0.1–1e5 eV 十进制 6 群）+ `Circuit/CircuitMain/FileInput`（`current.dat`
电流波形，ns vs. MA；t=0 电流为 0）+ JiHeld 传导 + DaviesWen 磁阻 + HLLD
Riemann 求解器；`diff_magzXrBoundaryType="circuit"`（B_z 外边界电流驱动）、
`xl_boundary_type="axisymmetric"`。

极短验证时间参数：`tmax=1e-12 s`（远小于首个电流上升沿 20 ns ⇒ 电流≈0，
纯初始构型 + 少量流体步）；`dtinit=1e-14, dtmax=1e-12, nend=200`。

## 2. 文件清单

| 文件 | 说明 |
|---|---|
| `gen_inputs.py` | ★ 场景专用装配脚本：调用 input_gen 各隔离模块生成 `flash_input/` 全部输入——Config（`gen_config/zpinch_config.py`）、Makefile（`gen_makefile` 直接复用）、Simulation_{data,init,initBlock}.F90（对应包内 zpinch_* 隔离文件）、Simulation_adjustEvolution.F90（**`gen_sim_adjustevo` 子包**，仅负责此文件）、`zpinch_be.par`（`gen_par/zpinch_par.py` 隔离基线 + `build_zpinch_par`）；`current.dat` 由本脚本生成（*.dat 按约定留场景） |
| `flash_input/Config` · `Makefile` · `Simulation_*.F90` | 生成产物（run_flash.sh 复制进模块目录后 setup 编译；官方 stock 逐字快照） |
| `flash_input/zpinch_be.par` | 运行参数（生成产物；与激光系 gen_par 零共享） |
| `flash_input/current.dat` | 电流波形（生成产物，Circuit FileInput 读取） |
| `flash_input/run_flash.sh` | WSL 全流水线（setup→make→run→收集），模块 `magnetoHD/ZPinch` |
| `run_zpinch_verify.py` | 场景 runner：调 gen_inputs → 运行 → 1D 剖面出图 + 定量核对 |
| `scene.json` / `__init__.py` | 场景注册（含声明式 `scenario` 对象） |
| `README.md` | 本文档 |
| `outputfiles/run_NNNNNN/` | chk/plt 产物 + 输入快照（运行后生成，gitignored） |
| `flash_output/` | 径向剖面图 + `geometry_check.json` 核对报告（gitignored） |

场景自包含：全部输入由 `gen_inputs.py` 装配生成（gitignored，克隆后一键再生）；
仅 **EOS/不透明度表**（Be-006-imx.cn4 / DD-006-imx.cn4）随 setup `DATAFILES`
机制从 FLASH 源码树获取（表来自 FLASH 分发，禁止再分发）。

## 3. setup / EOS 表

```bash
./setup -auto magnetoHD/ZPinch -1d +cylindrical +ug -nxb=16 \
        species=fill,line,vacu +mtmmmt +usm3t +mgd mgd_meshgroups=6 \
        +hdf5typeio -objdir=magnetoHD/ZPinch -parfile=zpinch_be.par
```

EOS/不透明度表：FLASH4.8 分发 ionmix4 表（随 setup DATAFILES 自动复制，
gitignored）：
- fill (DD) → `DD-006-imx.cn4`
- line / vacu (Be) → `Be-006-imx.cn4`（vacu 吸收/发射取 op_constant=0）

## 4. 几何验证判据（run_zpinch_verify.py 自动执行）

| 采样点 | r [cm] | 期望物种 | 期望密度 g/cc |
|---|---|---|---|
| fill_axis | 0.15 | fill | 3e-2 |
| fill_mid | 0.25 | fill | 3e-2 |
| liner_shell | 0.3175 | line | 1.848 |
| vacuum_out | 0.45 | vacu | 1e-5 |

判据：采样格心主导物种质量分数 ≥ 0.9，密度在期望值 2 倍因子内。

## 5. 后续扩展

- 正式电流驱动仿真：tmax 放至 ~200 ns（stock），Circuit 波形按装置实测
  替换（gen_inputs.py 中 CURRENT_DAT 可参数化）；
- `sim_rhoType=11` 双高斯剖面、`sim_pert` 随机扰动（RT 不稳定性研究）
  可经 gen_inputs.py 开关；
- 二维（r-θ / r-z）MHD 扩展参考官方 `flash_amr_2d.par`。

**上级导航**：[../README.md](../README.md)
