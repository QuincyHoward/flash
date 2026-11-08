# Hohlraum_AuCH — 间接驱动黑腔几何构型 (2D 柱坐标 r-z)

> 最后核对：2026-11-08 · commit 96aa10d

FLASH4.8 SimulationMain 场景：间接驱动（indirect drive）几何构型验证。
**Au 圆柱黑腔 + 中心 CH 球形靶丸 + 低密度 He 充气**。

> 状态: ★ 几何验证通过（run_000001，辐射关）★ 开辐射 MGD 10 群验证通过
> （run_000002，2026-11-08：三开关 .true. + gr_hypreUseFloor=.false.，
> 27 步达 tmax=1e-13 s，9/9 采样点吻合，trad≈231 K 自洽）
> 运行入口: `run_hohlraum_verify.py`（模式 auto/wsl）

## 1. 几何构型（NIF 间接驱动参考设计）

2D 柱坐标 `geometry="cylindrical"`：x = r（半径，r=0 为对称轴，边界
`axisymmetric`），y = z（圆柱轴向）。靶丸置于坐标原点（腔中心）。

| 部件 | 材料 | 尺寸 | 密度 |
|---|---|---|---|
| 黑腔圆柱侧壁 | Au (`gold`) | 内半径 2.72 mm，壁厚 30 µm，半长 5.005 mm | 19.32 g/cc |
| 端盖（含 LEH） | Au | 厚 30 µm，z ∈ ±[5.005, 5.035] mm，r ∈ [1.43, 2.75] mm | 19.32 g/cc |
| LEH 激光入射孔 | 开孔，充气延伸 | 半径 1.43 mm（≈52% 腔直径） | — |
| 中心靶丸壳（球形） | CH (`caps`) | 外半径 1.0 mm，壳厚 150 µm | 1.0 g/cc |
| 靶丸内气体 | He (`cgas`) | rr < 0.85 mm（rr = √(r²+z²)） | 1e-3 g/cc |
| 腔内充气 | He (`cham`) | 腔空腔 + LEH 孔内 | 0.96 mg/cm³ = 9.6e-4 g/cc |
| 腔外真空 | He (`cham`) | 其余区域 | 1e-6 g/cc |

尺寸依据（NIF 标准构型，LLNL 公开资料）：
- 黑腔：5.44 mm 直径 × 10.01 mm 长，Au 衬里（JSPF 2011, Progress Toward
  Ignition on NIF: "5.44 mm in diameter and 10.01 mm long, Au-lined U walls"）
- 充气：0.9–1.6 mg/cm³ He（低足/高足平台）
- LEH：50–55% 腔直径
- 靶丸：~2 mm 直径 CH/Be/HDC 壳

## 2. 文件清单

| 文件 | 说明 |
|---|---|
| `input/Config` | 模块配置（物种 cham,cgas,caps,gold；sim_* 几何参数声明） |
| `input/Makefile` | `Simulation += Simulation_data.o` |
| `input/Simulation_data.F90` / `Simulation_init.F90` | 参数模块与读取 |
| `input/Simulation_initBlock.F90` | ★ 几何初始化核心：r-z 四材料判据（球壳 + 圆柱壁 + 端盖 + LEH） |
| `input/hohlraum_auch.par` | 运行参数（tmax=1e-13 s 验证；辐射 MGD 10 群开，激光/传导关） |
| `input/run_flash.sh` | WSL 全流水线（setup→make→run→收集），模块 `QC/Hohlraum_AuCH` |
| `input/*.cn4` + `*.eosmeta.json` | 10 群统一表 ×3（he_10g / ch_10g / au_10g，见 §3） |
| `run_hohlraum_verify.py` | 场景 runner：表复制 → 运行 → 出图 + 定量核对 |
| `scene.json` / `__init__.py` | 场景注册（含声明式 `scenario` 对象） |
| `README.md` | 本文档 |
| `outputfiles/run_NNNNNN/` | chk/plt 产物 + 输入快照（运行后生成，gitignored） |
| `flash_output/` | 几何分布图 + `geometry_check.json` 核对报告（gitignored） |
| `temp_delete/` | 归档收纳（gitignored）：旧 6 群表 `eos_tables_old6g/`、运行日志 `logs/`、输入快照 `run_snapshots/`、历史产物 `outputfiles_run1_run2/` |

## 3. setup / EOS 表

```bash
./setup -auto QC/Hohlraum_AuCH -2d +cylindrical -nxb=16 -nyb=16 +hdf5typeio \
        species=cham,cgas,caps,gold +mtmmmt +laser +uhd3t +mgd mgd_meshgroups=10 \
        -objdir=QC/Hohlraum_AuCH -parfile=hohlraum_auch.par
```

EOS/不透明度表（10 群统一再生，2026-11-08 `gen_hohlraum10.py`，全部来自
Gen_eos_op_data 注册表随 Gitee 分发）：
- `cham`/`cgas`（He）→ `Z02_1.00-20261108_2013.cn4`（he_10g）
- `caps`（CH）→ `Z06_0.50-Z01_0.50-20261108_2013.cn4`（ch_10g）
- `gold`（Au）→ `Z79_1.00-20261108_2014.cn4`（au_10g）

★ 三张表 T/D 网格与 2026-07-08 Gen 表逐点一致（ntemp=51, 1→2e4 eV;
ndens=31; densnn He=1e13, CH/Au=1e16），仅能群统一为 **10 群**
（grupbd = layer_tracer rt_mgdBounds_1..11，0.1→1e5 eV），
与 `mgd_meshgroups=10`、par `rt_mgdBounds_1..11` 逐值一致
（FLASH op_readIonmix4Tables 校验相对误差 <1e-4）。

辐射配置（run_000002 已验证）：`rt_useMGD/useOpacity/useRadTrans=.true.` +
`gr_hypreUseFloor=.false.`（★0 铁律）+ 4 物种 op_ 表 + `rt_dtFactor=0.02`。

## 4. 几何验证判据（run_hohlraum_verify.py 自动执行）

| 采样点 | (r, z) cm | 期望物种 | 期望密度 g/cc |
|---|---|---|---|
| gold_side_wall | 0.2735, 0.000 | gold | 19.32 |
| gold_end_cap | 0.200, 0.502 | gold | 19.32 |
| caps_shell_pole | 0.000, 0.0925 | caps | 1.0 |
| caps_shell_equator | 0.0925, 0.000 | caps | 1.0 |
| cgas_center | 0.000, 0.000 | cgas | 1e-3 |
| cham_fill | 0.150, 0.300 | cham | 9.6e-4 |
| cham_leh_hole | 0.100, 0.502 | cham | 9.6e-4 |
| cham_vacuum_out | 0.300, 0.000 | cham | 1e-6 |
| cham_vacuum_axial | 0.150, 0.55 | cham | 1e-6 |

判据：采样格心主导物种质量分数 ≥ 0.9，密度在期望值 2 倍因子内
（AMR 格心可能落在界面半格内）。

## 5. 首轮验证实录（2026-11-08, run_000001）

- FLASH exit=0，26+1 步到达 tmax=1e-13 s；产物 27 plt + 2 chk。
- 定量采样 9/9 OK（判据: 主导物种分数 ≥0.9 且密度 2 倍因子内），
  见 `flash_output/geometry_check.json`。
- 射线剖面（plt_cnt_0026, t≈1.09e-13 s）:
  - z=0 径向: cgas(1e-3) → caps(1.0, 0.086–0.099) → cham 充气(9.6e-4)
    → gold(19.32, 0.272–0.275) → 真空(1e-6)，边界偏差 ≤1 格；
  - r=0 轴向: 靶丸对称、LEH 孔内充气延伸至 |z|≈0.503、|z|>0.5035 真空；
  - 端盖行 z=0.502: r<0.143 充气(LEH 开孔) / 0.143–0.275 Au / >0.275 真空。
- 分布图: `flash_output/plots/material_map.png`（材料分类）与
  `geometry_maps.png`（dens log + 4 物种分数面板）。
- 工程备注: FLASH4.8 plotfile 的 `coordinates` 数据集为**块中心**而非
  左下角（轴线块 coords[0]==size/2 实测确认）；变量数据集无 guard cell，
  逐块 shape=(1,16,16)。(j,i)=(JAXIS=z, IAXIS=r)。

## 6. 后续扩展

- 正式驱动仿真：par 三辐射开关改 `.true.`、配置激光锥束与脉冲、
  `useDiffuse/useHeatexchange=.true.`、恢复 tmax 至 ns 量级（分阶段，
  先短时验证 dtmax 判据再放行）。
- LEH 上的窗膜（poppy membrane）、外真空区缩小以省网格、AMR
  refine_region 约束（flash-grid-refine-constraint）可按需加入。
