# SNBVTi2um — V+Ti 多层示踪 + SNB（0.02µm 精确网格 + ★辐射开启）
> 最后核对：2026-11-05 · commit 7e04857


## 定位

由 **SNBVTi2**（0.02µm 精确网格版）派生（2026-09-24）。
**几何/材料/激光/网格/SNB 参数与 SNBVTi2 完全一致**，唯一差异：

| 项 | SNBVTi2 | 本场景 SNBVTi2um |
|---|---|---|
| 网格 | iProcs=125 × nxb=200，dx=0.02µm 精确（0.1µm 薄层=5 整格） | 同 |
| 材料 | shld=V 6.11，tar2=Ti 4.54，其余 tar*=CH 1.0；cham=He 1e-6 | 同 |
| Driver | 作者原版（`call RadTrans` 被注释 → 辐射永不推进） | **radON 变体**（活 call RadTrans ×2） |
| par 三开关 | rt_useMGD=.true.（useOpacity 靠基线；**useRadTrans 缺失**） | **三开关全 .true.（显式）** |
| 辐射实际状态 | ❌ 实际关（trad 冻结在初值 290K） | ✅ 真正开启 |

依据：`SNB/SNB/docs/04_辐射开关.md` §2（三开关形同虚设陷阱 + radON 判据）；
2026-09-24 四场景核查结论（SNBOneCH_ml/SNBVTi2/SNBVTi2_ml 辐射实际未推进）。

## 与核心模块的联动（2026-09-24 起）

核心模块 `SNB/SNB` 已把"辐射开 ↔ radON 驱动"固化为默认行为：
- `snb_params.py`：`RADIATION` 三开关默认全 `.true.`；新增 `RADIATION_SWITCHES`。
- `gen_scene.py`：默认 `--driver-variant radon` + `--radiation on`；
  生成时断言 Driver 活 `call RadTrans`，拒绝"辐射开+作者原版驱动"组合。
- `run_scene.py`：运行前 `radiation_linkage_check()` 闸门（par 开关 ↔ Driver 变体）。

本场景自包含脚本沿用同一联动逻辑（`_deploy_snb_overrides` 强制 radON +
静态核验断言），与核心模块护栏互为冗余。

## 用法

```bash
cd <flash 包根目录>
PY=%USERPROFILE%/.workbuddy/binaries/python/envs/default/Scripts/python.exe

# ① 只生成输入文件（含辐射三开关 + radON 驱动静态断言）
$PY flash/scenarios/private/tracer/SNB/SNBVTi2um/SNBVTi2um.py --generate-only

# ② 本地 WSL 极短冒烟（tmax=1e-13；首次完整 setup+make）
cd flash/scenarios/private/tracer/SNB/SNBVTi2um/flash_input
TMAX=1.0e-13 bash run_flash.sh

# ③ 超算 NC-E 正式（极短验证 1e-11 / 全长 1.6ns 用 --tmax 覆写）
$PY flash/scenarios/private/tracer/SNB/SNBVTi2um/SNBVTi2um.py \
    --tmax 1.0e-11 --nproc 125 --account flash_ssh
```

## 辐射生效判据（跑完必查）

1. par 三开关：`grep -E "^(rt_useMGD|useOpacity|useRadTrans)" flash_input/snbvti2um.par`
   → 三行全 `.true.`；
2. Driver：`grep -c "call RadTrans(" flash_input/Driver_evolveFlash.F90` 且行首无 `!`；
3. **chk 实测**：`trad` 末帧明显高于初值 0.025 eV（辐射 ON 的铁判据，docs/04 §5）；
   SNBVTi2 同窗口对照 trad 应仍 ≈ 初值（两场景辐射差异的直接证据）。

## 文件

- `SNBVTi2um.py` — 自包含场景脚本（生成/静态核验/WSL 流水线/HPC 委托）
- `flash_input/` — 生成产物（Config/Makefile/Simulation_*/9 F90/cn4/par/run_flash.sh）
- `flash_output/` — 运行输出（按 tag 分目录）
- `scripts/download_16ns_all.py` / `scripts/download_partial_chk.py` — 1.6 ns 主跑结果批量下载
- `watch_16ns.py` — 1.6 ns 长跑作业看护（JobID 4946680）
- `plots/` — 已有成果图（密度剖面/物种放大/x-t 图/热流摘要 CSV）+ `plots/electron_maps/`（175×2 张 fe/Q_g 彩图）

## scripts/analysis/ — Ti 轨迹与热电子分群分析（2026-11-15 新增）

基于 1.6 ns 主跑（`flash_output/hpc_flash_ssh_16ns_gpon/`，1163 chk，gpDump ON）的后处理套件：

```bash
PY=<repo>/.venv-win/Scripts/python.exe
cd flash/scenarios/private/tracer/SNB/SNBVTi2um_hot/scripts/analysis
$PY run_all.py --smoke                 # 5 帧端到端冒烟 + 断言
$PY run_all.py --all                   # 全量: track → maps → temps → diag → fefits → flychk → report
$PY run_all.py --step track|maps|temps|fefits|diag|flychk|report
```

| 模块 | 功能 | 产物 |
|---|---|---|
| `snb_io.py` | 读帧（块排序展平, 无逐帧 md5 重读）/时间轴缓存/派生量 | `data/times.csv` |
| `ti_track.py` | FWHM 窗口 + dens·tar2 质心轨迹 + medfilt/savgol 速度链 | `figures/fig_ti_track.png` `fig_ti_velocity.png` |
| `fields_sample.py` | 1163 帧一次扫描: 轨迹 + 12 项物理量采样 | `data/track_series.csv` `figures/fig_track_series.png` |
| `electron_maps.py` | 175 均匀时刻 fe(E,x) + Q_g 彩图（最近帧匹配, 冷启动帧跳过） | `plots/electron_maps/`×346 + 2 contact sheet |
| `temp_fit.py` | **v2 对数网格**双麦氏拟合: f_hot/T_hot + 等效 1σ 误差带 + 拟合误差分解; tele/T_eff 对比 | `data/temps_track_logfit.csv` `data/fe_fit_frames.npz` `data/fit_quality_summary.json` `figures/fig_temp_compare.png` `figures/fig_fhot_thot_fit.png` |
| `fe_fit_frames.py` | **175 幅** fe(E) 重建 vs 双麦氏拟合逐帧对比图（上: 曲线+误差带, 下: log 残差+误差带） | `plots/fe_fits/`×175 + 1 contact sheet; `data/fe_fit_records.json` |
| `diagnose_fhot.py` | v1 线性网格伪影成因诊断（内嵌 legacy 线性拟合作对照, 14 帧独立细网格 + EDF 尾巴占比） | `data/fhot_diagnosis.json` `figures/fig_fhot_diagnosis.png` |
| `flychk_history_175.py` | 175 均匀时刻 FLYCHK history 上传包（8 列, `fhot file` 模式, v2 口径） | `flychk_history_175/`（上传 zip + 交付压缩包 + 表/CSV/预览/manifest） |
| `build_report.py` | 中文 HTML 报告（58 图 base64 内嵌, 含 5.1/5.2/5.3/8 章） | `scripts/analysis/热电子分群统计及其分析报告.html` |

要点：本 run 无 `targ` 物种，Ti 示踪层 = `tar2`（chk_0000 实测 x∈[4.000,4.100] µm,
ρ=4.54 g/cc）；SNB 19 群变量 `cg01–19/mp01–19/mr01–19` 小写平铺；
闸门 A(ΣMR·CG==corq) 与 C(fe 归一化) 全量通过；
复用 `SNB/SNB/scripts/analysis/{snb_group_pipeline,fe_maps_partial}.py` 与
InterfaceEvolution `core/velocity.py`。

### v2 对数网格拟合、误差带与 175 幅对比图（2026-11-15 晚）

- **口径变更**: `fhot_grid` 由 `np.linspace(0,0.95,501)` 改为
  「精确 0 点 + `np.geomspace(1e-12,0.5,240)`」; T_hot 保持
  `np.geomspace(1.2*Te,200*Te,200)`。v1 线性网格把连续最优 ~1e-8 一律量化到
  第一个非零点 0.0019, 造成「f_hot 后期恒定」伪影; v2 后 f_hot 中位 3.6e-8
  （t>0.1 ns 中位 1.3e-8, 范围 1e-12…8e-6）且随时间真实变化。
  旧 `data/temps_track.csv`（v1）保留作对照, v2 正式数据在
  `data/temps_track_logfit.csv`。
- **拟合误差**: 窗口内 log-RMSE 中位 2.28（t>0.1 ns 2.23）, 其中约 4.6×
  的**全局幅度偏置**占主导（fe 经 f₁ 重归一化 vs 钉死 n_e 的麦氏核）,
  去除偏置后的形状 log-RMSE 仅 1.71; 相对单麦氏误差改善中位 80.8%。
  偏置对所有能量点为常数, 不改变 (f_hot, T_hot) 最优点。
- **误差带**: profile-SSE 等效 1σ 区间 `SSE <= SSE_min*(1+1/(N-2))`,
  f_hot 带中位跨 0.69 个数量级, T_hot 带仅 0.078 个数量级;
  22.5% 帧 T_hot 命中搜索上界 → 两参数弱可辨识, 只作定性参考。
- **175 幅图**: `plots/fe_fits/fe_fit_t000…t174_chk*.png`, 编号与
  `plots/electron_maps/` 的 175 个均匀时刻逐一对应（t000/t001 为冷启动英文占位图）;
  每张上子图 = fe 重建/双麦氏拟合/纯冷麦氏 + ±1 形状 log-RMSE 误差带,
  下子图 = ln(fit/fe) 残差 + 幅度偏置线 + 误差带; 另有
  `fe_fit_contact_sheet.png` 全时序缩略。
- **FLYCHK 包同步 v2**: `gen_flychk_his` 已扩展双麦氏热电子模式
  （`fhot`/`thot` 成对列、runfile 的 `fhot file`、[0,1] 钳位与回读自检）,
  `python -m pytest flash/input_gen/gen_flychk_his/test -q` 223 项全通过;
  上传包 175 行 × 8 列 `time size rho te ti tr fhot thot`,
  manifest 的 `fit_quality` 字段含全量误差统计。
- 冷启动段（t≲0.1 ns）拟合退化（f_hot 顶到 0.5、T_hot 顶到 200×T_e、
  log-RMSE>40）, 无物理意义; 高能区若干残差尖刺来自 SNB 19 群 f₁,g
  分段常值造成的群边界台阶。
