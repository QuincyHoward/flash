# SNBOneCH — 最小两区 SNB 场景（+ug 均匀网格分辨率研究）

**派生**: SNBOneCH_ml → 简化 (2026-09-08)
**单元**: FLASHSNB `SimulationMain/SNBOneCH`
**驱动**: `SNBOneCH.py`（wsl 一键；--generate-only / --sweep / --skip-*）

## 1. 场景定义

★ **SNB 铁律：SNB 模式必须 +ug 均匀网格**（非局域热流跨平均自由程积分，
AMR 粗细界面是破缺点；t001 与本场景全部 +ug 稳定，SNBOneCH_ml AMR 1e-10 失稳）。

- 几何（1D 笛卡尔，域 [-0.04, 0.01] cm，界面 x=0）：

| 区间 | 物种 | 材料 | ρ [g/cm³] | EOS/op 表 |
|------|------|------|-----------|-----------|
| x < 0 | cham | 氦 He | 1e-6 | He-BADGER-TOPS-Final.cn4 |
| x > 0 | targ | CH | 1.0 | CH-BADGER-TOPS-Final.cn4 |

- 仅 2 个物种标记 cham/targ；initBlock 默认物种 cham，x∈[0,xmax] 区域 targ
  （无运行时几何参数，界面写死 x=0）。
- 激光：0.351 µm 单束，透镜 x=-1.0，82 段功率脉冲（同 CH_FLASH_PAR 模板）。
- 运行控制（t001 +ug 验证基线）：tstep_change_factor=1.10，cfl=0.2，
  dtmax=2e-12，T_init=290.11375 K，plotFileIntervalTime=1e-11。

## 2. +ug 分辨率控制

+ug 只建 iProcs 块 level-1 网格（par nblockx/lrefine 无视）：

```
dx = 0.05 cm / (iProcs × nxb=8)
iProcs:  4 → 15.6 µm   8 → 7.8 µm   16 → 3.9 µm   32 → 2.0 µm   64 → 0.98 µm
```

**档位受物理核数约束**（本机 24 核，MPI 自旋等待超订会减速 1~2 个量级：
ip32 单点 747s 未完成 vs ip16 1.7s）——本地 sweep 建议 ≤16；32/64 走 HPC。

## 3. 用法

```bash
python SNBOneCH.py --generate-only            # 只生成 flash_input/
python SNBOneCH.py --tmax 1.0e-11             # 首跑验证规范
python SNBOneCH.py --tmax 1.0e-10             # 单跑 (默认 iprocs=8)
python SNBOneCH.py --skip-deploy --skip-setup --skip-make --sweep 4,8,16 \
       --tmax 1.0e-10                          # 分辨率扫描 (二进制复用)
```

扫描产物：`flash_output/sweep_ip<N>/`（plt + par_ip<N>.par + walltime.txt），
对比图 `flash_output/sweep_dens_compare.png` + 汇总表（stdout）。

## 4. 实测记录 (2026-09-08)

| iProcs | dx [µm] | tmax=1e-10 | walltime |
|--------|---------|------------|----------|
| 4 | 15.625 | reached max SimTime ✓ | 0.9 s |
| 8 | 7.812 | reached max SimTime ✓ | 1.2 s |
| 16 | 3.906 | reached max SimTime ✓ | 1.7 s |
| 32 | 1.953 | 本地超订未完成 (747s, step18 仅 4.6e-14) | — |

+ug + BADGER + t001 运行控制下 1e-10 全部稳定 — 与 SNBOneCH_ml (AMR)
1e-10 失稳形成对照，支持"SNB 必须 +ug"结论。

## 5. 文件结构

```
SNBOneCH/
├── SNBOneCH.py          # 一键驱动 (生成/部署/编译/运行/扫描/分析)
├── flash_input/         # 生成 5 件套 + 2 cn4 + 9 个 SNB 覆盖 F90 (工作树权威版)
│   ├── snbonech.par / Config / Makefile / Simulation_{data,init,initBlock}.F90
│   ├── run_flash.sh     # WSL 手动一键 (SKIP_SETUP/MAKE/DEPLOY, TMAX, NPROC)
│   └── pre_diag_{laser_pulse,initial_density}.png
└── flash_output/        # 输出用后即转 (sweep_ip<N>/ 子目录分档)
```
