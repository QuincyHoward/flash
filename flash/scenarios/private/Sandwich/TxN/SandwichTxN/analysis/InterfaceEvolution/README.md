# InterfaceEvolution — SandwichTxN 关键界面随时间演化分析

> 生成: 2026-11-11 · run 000002 · 判据来源: `flash/output_pro/FLASH物理量说明.md` §3

**一句话职责**: 从 chk 帧序列提取临界密度面 x_c、烧蚀前沿 x_a、冲击波阵面 x_s
(§3.3 物理四判据) 与 Si 区域 (dens·targ 半高) 四类界面, 产出 x(µm)-t(ns) 界面演化图、
8 物理量时空彩图、shok 核查图、Si 区平均量历史与中文 HTML 报告。

## 使用入口

```bash
# 在仓库根目录, 使用 .venv-win (Windows) 或对应 venv
python extract_interfaces.py [--run 000002] [--quiet]   # chk → data/
python plots/plot_interfaces.py                         # → figures/ 界面演化图
python plots/plot_maps.py                               # → figures/ 时空彩图 + shok 核查图
python plots/plot_si_history.py                         # → figures/ Si 区平均量历史
python plots/plot_fig_compare.py                        # → figures/ 参考 vs FLASH 对比图
python build_report.py                                  # → report.html
python flychk/make_flychk_zips.py                       # → flychk/out/ 两类 FLYCHK zip
```

## 文件树 (按功能分层)

```
core/                    提取核心库
  chk_io.py                chk 读取: 叶块过滤(node type==1) + bounding box 逐格 x
                           + 派生量 nele/nion/zbar/Γ_i/Θ_e (hdf5pro 同款实现)
  criteria.py              判据: x_c (§3.1) / x_a (§3.2 双束镜像) / Si dens·targ 半高
                           / shok 候选连续区切分 (§3.3)
  velocity.py              §3.4 统一速度差分链 (medfilt9 + savgol, 两端截 3 点)
  shock_track.py           §3.3: 贪心轨迹 + 物理筛选 (① v_s 与 v_a 同号 ② |v_s|>|v_a|
                           ③ 位于 x_a 运动方向前方 ④ 初始距 x_a≤20 µm) + 向心段截取
  fields.py                时空场采样 (MAP_FIELDS 8 场, shok 用 max-pooling) + Si 区平均
extract_interfaces.py    入口 CLI → data/ (interfaces.csv, spacetime.npz, si_history.csv)
plots/
  plot_interfaces.py       界面演化图 (Si 区域仅边界线; >15 µm 跳变断线)
  plot_maps.py             2×4 物理量时空彩图 + shok 核查图 (原始格元散点)
  plot_si_history.py       Si 区平均量 + size 时间历史 (4×2)
  plot_fig_compare.py      参考数据对比图 (fig_data/fig 数字化 csv vs 本 run)
build_report.py          中文 HTML 报告 (图片 base64 内嵌)
fig_data/fig/            另一仿真参考数据 (WebPlotDigitizer 数字化:
                         nele/tele/rho_vs_time.csv 无表头 + wpd 工程 tar + 原图 png)
flychk/
  make_flychk_zips.py     Si 区平均量 → 两类 FLYCHK history 输入 zip
                          (1.1: ne 基准 / 1.3: rho=dens·targ 基准; gen_flychk_his 包)
  out/                    两类 zip + 数据表 txt + 预诊断图 + manifest.json (归拢同目录)
data/                    interfaces.csv / spacetime.npz / si_history.csv / extraction_log.txt
figures/                 全部 png
report.html              报告
```

## FLYCHK 输入 (flychk/)

- 数据源 `data/si_history.csv` (Si 区平均, 299 帧) → 均匀重采样 175 点于
  [0, 1.6] ns (FLYCHK 需 t>0, 取 t_i = 1.6·i/175 ns, i=1..175, Δt=9.14 ps)
- `history_si1.1ne_Si_Z14_in_.zip`: time,size,te,ti,tr,**ne** (nele 平均, cm⁻³)
- `history_si1.3rho_Si_Z14_in_.zip`: time,size,te,ti,tr,**rho** (dens·targ 平均, g/cm³)
- te/ti/tr 已是 eV; size 单位 cm; te_floor=0.01 eV 保留冷态;
  写出经 `gen_flychk_his.FlychkHistoryWriter` (自包含, 回读自检 integrity_ok=True)
- 预诊断图为自定义 4 面板: 温度三线全部非实线 (TE 长虚线 / TI 密点线置顶 /
  TR 点划线, 重叠区交错可辨) + Si 面质量 ∫dens·targ dx 守恒核查
  (size 范围内 vs 全域 targ≥0.5, 初始参考线; 数据列
  si_areal_mass_gcm2 / si_areal_mass_all_gcm2)
- ⚠ FLYCHK 网站建议 history ≤50 时间步, 175 点为用户指定; 若提交超时,
  用 `n_time_max` 抽稀重跑


## 判据要点 (详见 report.html §4)

- **x_c**: N_C = 9.054e21 cm⁻³ (0.351 µm), 每侧首个欠密→过密上穿线性插值
- **x_a**: 过密 + 60–600 eV 温区带 + x_c 内侧 0.5 µm 余量, |dT/dx| 最陡格元
- **x_s**: shok=1 连续区加权质心 → 贪心轨迹 (200 µm/ns 门限, 断流≤5 帧续接) →
  向心段截取 (回弹剔除) → 四判据筛选 → SG(7,3) 平滑插值回全网格
- **Si 区域**: dens·targ ≥ 0.5×median(dens·targ|targ≥0.5) 外缘 — 体区中位数基准
  排除激波压缩壳对全局 max 的抬高
- **Si 区平均量**: 半高段内 targ≥0.5 格元算术平均 (nele/nion/tele/pres/pele/Γ/Θ)

## 关键实现纪律

- chk 含父块: 必须过滤 `node type == 1` (FLASH物理量说明 §3.0)
- 逐格 x 由 bounding box 重建; n_e = ye·ρ·N_A; T K→eV 除以 11604.518; p→Mbar ×1e-12
- pcolormesh 背景场使用帧头真实 time (Δt 不均匀, 禁 imshow)
- shok 薄层标志场用 max-pooling 采样 (线性插值整段错过), 核查图叠加原始格元散点
- 绘图端对相邻帧位移 >15 µm 的跳变断开连线 (早期电离前沿越阈伪影)

## 已知解读边界 (report.html §8)

t<0.03 ns 的 x_c 为 Si 电离前沿越阈; x_s 自泡沫外缘静态密度间断启动 (与 x_a 同点);
Si/CH 界面压缩波与远场噪声带被判据 ①④ 排除; shok 判据仅覆盖致密材料
(t>0.55 ns 无信号); 晚期 (t>1.0 ns) 左右缘数值不对称。
