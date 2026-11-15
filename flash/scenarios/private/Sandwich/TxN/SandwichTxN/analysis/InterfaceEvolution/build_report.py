#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_report — 生成中文 HTML 分析报告 report.html (自包含, 图片 base64 内嵌).

内容: FLASH 输出位置 / 文件树 / 初始参数与预诊断图 / 界面判据 (含 §3.3 物理筛选) /
      界面演化图 / shok 核查图 / 8 场时空彩图 / Si 区平均量历史 / 注意事项 / 产物清单。
用法: python build_report.py
"""
from __future__ import annotations

import base64
import csv
import html
import json
from datetime import datetime
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent          # InterfaceEvolution/
SCEN = HERE.parent.parent                       # SandwichTxN
RUN = SCEN / "runs" / "000002"
SIM_OUTPUT = RUN / "sim_output"
SIM_INPUT = RUN / "sim_input"
DATA = HERE / "data"
FIGS = HERE / "figures"

N_C = 1.1155e21 / 0.351**2


def b64img(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


def col(rows, k):
    return np.array([float(r[k]) if r.get(k, "") not in ("", "nan") else np.nan
                     for r in rows])


def fmt(v, unit="", nd=3):
    return "—" if v is None else f"{v:.{nd}f}{unit}"


def main():
    with open(DATA / "interfaces.csv", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    t = col(rows, "time_ns")
    g = lambda k: col(rows, k)

    info = {}
    for side in ("left", "right"):
        xs = g(f"xs_{side}_um")
        vs = g(f"vs_{side}_um_ns")
        va = g(f"va_{side}_um_ns")
        m = np.isfinite(xs)
        info[side] = dict(
            t0=float(t[m][0]) if m.any() else None,
            t1=float(t[m][-1]) if m.any() else None,
            n=int(m.sum()),
            t_conv=float(t[m][-1]) if m.any() else None,
            vs_med=float(np.nanmedian(vs[m])) if m.any() else None,
            va_med=float(np.nanmedian(va[m])) if m.any() else None,
        )

    si_w = g("si_right_um") - g("si_left_um")
    i_w = int(np.nanargmin(si_w))
    si_wmin, si_wmin_t = float(si_w[i_w]), float(t[i_w])
    si_wmax = float(np.nanmax(si_w))
    si_wmax_t = float(t[int(np.nanargmax(si_w))])

    with open(DATA / "si_history.csv", encoding="utf-8") as fh:
        hrows = list(csv.DictReader(fh))
    hist = {}
    for k in ("nele_mean", "tele_eV_mean", "pres_Mbar_mean", "gamma_mean",
              "theta_mean", "size_um"):
        v = col(hrows, k)
        m = np.isfinite(v)
        hist[k] = (float(v[m][0]), float(v[m][-1])) if m.any() else (None, None)

    with open(RUN / "database" / "flash_in" / "input_params.json",
              encoding="utf-8") as fh:
        prm = json.load(fh)
    n_chk = len(list(SIM_OUTPUT.glob("lasslab_hdf5_chk_*")))

    rows_param = [
        ("计算域", "±450 µm (1D 笛卡尔, xmin=-0.045 cm, xmax=+0.045 cm)"),
        ("Si 芯层 (targ)", f"|x| ≤ 0.46 µm, ρ = {prm['sim_rhoTarg']} g/cm³ (总厚 0.92 µm)"),
        ("CH 致密层 (poly)", f"0.46 < |x| ≤ 1.46 µm, ρ = {prm['sim_rhoPoly']} g/cm³ (两侧各 1 µm)"),
        ("CH 泡沫 (poly)", f"1.46 < |x| ≤ 51.46 µm, ρ = {prm['sim_rhoFoam']} g/cm³ (两侧各 50 µm)"),
        ("He 填充 (cham)", f"|x| > 51.46 µm, ρ = {prm['sim_rhoCham']} g/cm³ (极低密度)"),
        ("初始温度", "T_e = T_i = T_r = 290.11375 K (常温固态密度)"),
        ("EOS / 不透明度表",
         "Si: Z14_1.00-20260708_0850.cn4 · CH: Z06_0.50-Z01_0.50-20260708_0850.cn4 · "
         "He: Z02_1.00-20260708_0851.cn4 (IONMIX cn4)"),
        ("激光", f"双束对打 0.351 µm (3ω), 透镜 x = ∓0.1 cm, 靶点 x = 0; "
                 f"单束峰值 {prm['laser_powers'][1]:.3e} W/cm² (= 2×800 J / (π×(400 µm)²×1.0 ns))"),
        ("脉冲波形", "梯形 4 点: 0 → 0.3 ns 升至峰值, 平顶 0.7 ns, 1.3 ns 降为 0 (FWHM = 1.0 ns)"),
        ("仿真终止", f"tmax = {prm['tmax']*1e9:.1f} ns, nend = 1×10⁷ 步, "
                     f"dt_init = dt_min = {prm['dtinit']:.1e} s, dt_max = 1e-9 s"),
        ("AMR 网格", "nxb = 16, 初始 8 块, lrefine = 1–10 (最细 Δx ≈ 0.0137 µm), "
                    "自定义 Grid_markRefineDerefine 逐材料分层细化"),
        ("输出频率", f"chk 每 100 步 (实际 Δt 不均匀), plot 每 1000 步; "
                    f"目标采样 output_t_step = {prm['output_t_step']*1e12:.0f} ps"),
        ("物种标记", "cham (He) / poly (CH) / targ (Si), ΣY = 1; 派生 dens_targ = dens × targ"),
        ("热传导模型", "FL-SH 基线 (限流 Spitzer-Härm); 场景族另含 SNB 19 群变体"),
    ]
    tr_rows = "".join(
        f"<tr><td style='white-space:nowrap;font-weight:600'>{html.escape(k)}</td>"
        f"<td>{html.escape(v)}</td></tr>" for k, v in rows_param)

    crit = [
        ("临界密度面 x_c(t)",
         f"N_C = 1.1155×10²¹/λ² ≈ {N_C:.2e} cm⁻³ (λ=0.351 µm)。每侧取 n_e 首个"
         "欠密→过密向上穿越, 两格元线性插值 (§3.1)。",
         "298/299 帧有效; t=0 冷材近中性 (max n_e ≈ 9.9×10²⁰ < N_C) 故无解"),
        ("烧蚀前沿 x_a(t)",
         "n_e > N_C 且 60 eV < T_e < 600 eV 且位于 x_c 内侧过密一方 (余量 0.5 µm) "
         "的格元中取 |dT/dx| 最陡处; 左半域 argmin(dT/dx), 右半域 argmax(dT/dx) (§3.2 镜像)。",
         "293/299 帧有效"),
        ("冲击波阵面 x_s(t)",
         "§3.3 完整链: shok=1 连续区 (索引间隔>2) 取 shok 加权质心 → 贪心最近邻成轨迹 "
         "(门限 200 µm/ns·dt, 断流≤5 帧续接) → 每条轨迹截取<b>向心发展段</b> (回弹段剔除) → "
         "<b>物理筛选四判据</b>: ① med(v_s) 与 med(v_a) 同号; ② |med(v_s)| &gt; |med(v_a)|; "
         "③ med(x_s−x_a)·med(v_a) &gt; 0 (位于 x_a 运动方向前方); ④ 起点 |x_s−x_a| ≤ 20 µm "
         "(排除 Si/CH 材料界面静压触发伪迹)。速度统一 §3.4 差分链 "
         "(medfilt9 + savgol, w=min(51,max(7,n/4)) 取奇, 两端截 3 点); "
         "位置 SG(7,3) 预平滑后插值回全网格。",
         f"左: {info['left']['n']} 帧 [{fmt(info['left']['t0'])}, {fmt(info['left']['t1'])}] ns, "
         f"v_s = {fmt(info['left']['vs_med'], '', 1)} vs v_a = {fmt(info['left']['va_med'], '', 1)} µm/ns; "
         f"右: {info['right']['n']} 帧 [{fmt(info['right']['t0'])}, {fmt(info['right']['t1'])}] ns, "
         f"v_s = {fmt(info['right']['vs_med'], '', 1)} vs v_a = {fmt(info['right']['va_med'], '', 1)} µm/ns"),
        ("Si 区域 (dens·targ 半高)",
         "dens×targ ≥ 半高的区段外缘 (线性插值)。半高基准 = 0.5 × "
         "median(dens·targ | targ≥0.5), 以体区中位数排除激波压缩壳 (targ≈1 但 ρ 数倍) "
         "对全局 max 的抬高; 与 analyze_output.py fig7 的 targ≥0.5 约定兼容。",
         "299/299 帧有效; 初始 ±0.453 µm (真值 ±0.46 µm)"),
        ("Si 区平均量",
         "x ∈ [si_left, si_right] 且 targ≥0.5 的格元算术平均: "
         "n_e, n_i, T_e, p, p_e, Γ_i, Θ_e; Γ_i = Z̄²e²/(a_i k_B T_i), "
         "Θ_e = k_B T_e/E_F (hdf5pro 同款实现)。",
         "299/299 帧有效"),
    ]
    crit_rows = "".join(
        f"<tr><td style='font-weight:600'>{a}</td><td>{b}</td><td>{c}</td></tr>"
        for a, b, c in crit)

    t_gen = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    html_doc = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>SandwichTxN 界面演化分析报告 (run 000002)</title>
<style>
  body {{ font-family: "Microsoft YaHei", "PingFang SC", sans-serif; max-width: 1080px;
         margin: 24px auto; padding: 0 20px; color: #222; line-height: 1.65; }}
  h1 {{ font-size: 26px; border-bottom: 3px solid #2c6fbb; padding-bottom: 8px; }}
  h2 {{ font-size: 21px; color: #2c6fbb; margin-top: 34px; border-left: 5px solid #2c6fbb;
        padding-left: 10px; }}
  h3 {{ font-size: 18px; margin-top: 24px; }}
  table {{ border-collapse: collapse; width: 100%; margin: 12px 0; font-size: 14.5px; }}
  th, td {{ border: 1px solid #c9c9c9; padding: 7px 10px; text-align: left;
            vertical-align: top; }}
  th {{ background: #eef3fa; }}
  tr:nth-child(even) td {{ background: #fafcff; }}
  img {{ max-width: 100%; border: 1px solid #ddd; border-radius: 6px; margin: 8px 0; }}
  .meta {{ color: #666; font-size: 14px; }}
  code, pre {{ background: #f4f4f4; border-radius: 4px; font-family: Consolas, monospace;
               font-size: 13.5px; }}
  pre {{ padding: 10px 12px; overflow-x: auto; line-height: 1.5; }}
  .warn {{ background: #fff7e6; border-left: 4px solid #e6a23c; padding: 10px 14px;
           border-radius: 4px; }}
  .figure p {{ text-align: center; color: #555; font-size: 14px; margin: 4px 0 18px; }}
</style>
</head>
<body>

<h1>SandwichTxN 关键界面随时间演化分析报告</h1>
<p class="meta">生成时间: {t_gen} · 场景: sandwich_txn (CH/Si/CH 三明治靶, FL-SH 基线) ·
运行: runs/000002 · 分析目录: analysis/InterfaceEvolution/ (core + 入口 + plots 分层)</p>

<h2>1. FLASH 输出位置与数据规模</h2>
<table>
<tr><th style="width:220px">项目</th><th>路径 / 说明</th></tr>
<tr><td>FLASH 输出文件夹 (chk)</td>
<td><code>{SIM_OUTPUT}</code></td></tr>
<tr><td>chk 帧序列</td>
<td>lasslab_hdf5_chk_0000 – {n_chk-1:04d} (共 {n_chk} 帧, 每 100 步一帧,
    实际 Δt 不均匀, 分析均使用帧头真实 time)</td></tr>
<tr><td>运行参数快照</td><td><code>{RUN / 'database' / 'flash_in' / 'input_params.json'}</code></td></tr>
<tr><td>输入文件 (par/Config/EOS 表)</td><td><code>{SIM_INPUT}</code></td></tr>
</table>

<h2>2. 文件树 (按功能分层)</h2>
<pre>analysis/InterfaceEvolution/
├── core/                    # 提取核心库 (可复用)
│   ├── chk_io.py            #   chk 读取: 叶块过滤 + bounding box 逐格 x + 派生量 (nele/nion/Γ/Θ)
│   ├── criteria.py          #   界面判据: x_c (§3.1) / x_a (§3.2 镜像) / Si 半高 / shok 候选切分
│   ├── velocity.py          #   §3.4 统一速度差分链 (medfilt + savgol)
│   ├── shock_track.py       #   §3.3 冲击波轨迹: 贪心跟踪 + 物理四判据 + 向心段截取
│   └── fields.py            #   时空场统一网格采样 (shok 用 max-pooling) + Si 区平均
├── extract_interfaces.py    # 入口 CLI: chk → data/ (interfaces.csv, spacetime.npz, si_history.csv)
├── plots/                   # 绘图脚本 (全英文, Times New Roman, ≥18 pt)
│   ├── plot_interfaces.py   #   → figures/interface_evolution_full.png / _zoom.png
│   ├── plot_maps.py         #   → figures/spacetime_maps.png (2×4) + map_shok.png (核查)
│   └── plot_si_history.py   #   → figures/si_history.png (4×2 Si 区平均量)
├── build_report.py          # → report.html (本报告)
├── data/                    # 中间数据 (csv / npz / log)
├── figures/                 # 图片产物
└── report.html              # 本报告</pre>

<h2>3. 初始参数设置</h2>
<table>
<tr><th style="width:220px">参数</th><th>取值</th></tr>
{tr_rows}
</table>

<div class="figure">
<img src="data:image/png;base64,{b64img(SIM_INPUT / 'initial_density.png')}" alt="initial density">
<p>预诊断图 1: 初始密度剖面 (sim_input/initial_density.png) —
Si 芯 2.3 / CH 致密层 1.0 / CH 泡沫 0.294 / He 填充 1e-6 g/cm³</p>
</div>

<div class="figure">
<img src="data:image/png;base64,{b64img(SIM_INPUT / 'laser_pulse.png')}" alt="laser pulse">
<p>预诊断图 2: 激光脉冲波形 (sim_input/laser_pulse.png) —
梯形脉冲, FWHM 1.0 ns, 单束峰值 3.183×10¹⁴ W/cm²</p>
</div>

<h2>4. 界面提取判据 (依据 flash/output_pro/FLASH物理量说明.md §3)</h2>
<table>
<tr><th style="width:190px">界面 / 量</th><th>判据与算法</th><th style="width:300px">有效性 / 校验</th></tr>
{crit_rows}
</table>
<p>数据处理纪律: chk 含全部 AMR 块 (含父块), 仅保留 <code>node type == 1</code> 叶块;
逐格 x 由 bounding box 重建 <code>x = x_lo + W·(i+0.5)/16</code>;
n_e = ye·ρ·N_A, n_i = sumy·ρ·N_A; T [K] → [eV] 除以 11604.518;
p/pe [dyn/cm²] → [Mbar] ×1e-12; 帧序列排除 *_forced_*/*_rst_*。</p>

<h2>5. 界面演化结果</h2>

<div class="figure">
<img src="data:image/png;base64,{b64img(FIGS / 'interface_evolution_full.png')}" alt="full">
<p>图 1: 全域 (±100 µm) 界面时空演化。x 轴位置 (µm), y 轴时间 (ns);
背景 log₁₀ρ (pcolormesh 真实逐帧时间); 白色点线为初始几何
(±0.46 µm Si 半厚, ±51.46 µm 泡沫外边界); Si 区域仅绘边界线 (无阴影)。</p>
</div>

<div class="figure">
<img src="data:image/png;base64,{b64img(FIGS / 'interface_evolution_zoom.png')}" alt="zoom">
<p>图 2: 近靶区 (±20 µm) 放大 — Si 层膨胀 → 激波/热波向心汇聚 (t ≈ 0.5 ns) → 压缩再膨胀;
绿色 x_s 略超前于橙色 x_a (v_s &gt; v_a, 判据 ②)。</p>
</div>

<h3>5.1 冲击波物理筛选结果 (§3.3)</h3>
<table>
<tr><th style="width:100px">侧</th><th>有效段</th><th>v_s 中位</th><th>v_a 中位</th><th>判据</th><th>轨迹来源</th></tr>
<tr><td>左</td><td>{fmt(info['left']['t0'])} – {fmt(info['left']['t1'])} ns ({info['left']['n']} 帧)</td>
<td>{fmt(info['left']['vs_med'], ' µm/ns', 1)}</td><td>{fmt(info['left']['va_med'], ' µm/ns', 1)}</td>
<td>①②③④ 全过</td><td>激光驱动激波, 自泡沫外缘 (≈−51 µm, 与 x_a 同点) 向心发展</td></tr>
<tr><td>右</td><td>{fmt(info['right']['t0'])} – {fmt(info['right']['t1'])} ns ({info['right']['n']} 帧)</td>
<td>{fmt(info['right']['vs_med'], ' µm/ns', 1)}</td><td>{fmt(info['right']['va_med'], ' µm/ns', 1)}</td>
<td>①②③④ 全过</td><td>镜像, 向心发展至 {fmt(info['right']['t_conv'])} ns</td></tr>
<tr><td colspan="6">被排除轨迹: Si/CH 材料界面压缩波 (v_s ≈ +9 µm/ns, 与 v_a 反号 → ①④ 不过);
远场噪声带 (|x| ≈ 80–100 µm, 距 x_a 过远 → ④ 不过); 回弹段 (向心截断剔除)。</td></tr>
</table>

<div class="figure">
<img src="data:image/png;base64,{b64img(FIGS / 'map_shok.png')}" alt="shok map">
<p>图 3: shok 标志时空核查图 — 黄色方块为原始 shok&gt;0.5 格元, 白色 × 为全部候选区质心,
橙色 x_a, 绿色 x_s (筛选后)。可见三类候选: 外侧 Λ 形汇聚激波 (选中)、中心 V 形
Si/CH 界面压缩波 (④ 排除)、静态泡沫/He 界面与远场噪声带 (t &lt; 0.2 ns, |x| &gt; 50 µm)。</p>
</div>

<h2>6. 物理量时空彩图</h2>
<div class="figure">
<img src="data:image/png;base64,{b64img(FIGS / 'spacetime_maps.png')}" alt="maps">
<p>图 4: 2×4 物理量时空彩图 (log₁₀ 色标, 全量程) —
ρ / n_e / n_i / T_e / p / p_e / 离子耦合参数 Γ_i / 电子简并参数 Θ_e。
n_e = ye·ρ·N_A, n_i = sumy·ρ·N_A, Z̄ = ye/sumy,
Γ_i = Z̄²e²/(a_i k_B T_i), Θ_e = k_B T_e/E_F。</p>
</div>

<h2>7. 中心 Si 区域平均量随时间演化</h2>
<div class="figure">
<img src="data:image/png;base64,{b64img(FIGS / 'si_history.png')}" alt="si history">
<p>图 5: Si 区域 (dens·targ 半高段内 targ≥0.5 格元) 平均量 + 区域尺寸随时间,
3×3 共 9 面板 — size / ρ_Si (dens·targ) / n_e / n_i / T_e / p / p_e / Γ_i / Θ_e,
全部线性坐标。</p>
</div>

<h3>7.1 关键数值摘要</h3>
<table>
<tr><th style="width:300px">物理事件 / 量</th><th>数值</th></tr>
<tr><td>热波/激波向心汇聚</td>
<td>x_a 与 x_s 自泡沫外缘 (±51 µm) 向心发展, t ≈ 0.49–0.52 ns 抵达中心;
左 v_s = {fmt(info['left']['vs_med'], '', 1)} &gt; v_a = {fmt(info['left']['va_med'], '', 1)} µm/ns,
右 |v_s| = {fmt(abs(info['right']['vs_med']), '', 1)} &gt; |v_a| = {fmt(abs(info['right']['va_med']), '', 1)} µm/ns
(§3.4 差分链平滑后中位数)</td></tr>
<tr><td>临界密度面 x_c 活动</td>
<td>初始位于泡沫外缘 ±51.5 µm, 0.56 ns 前略向内移至 ±42.8; 0.73 ns 冠层电离扩张后
外跳至 ±93.7, 随后 ±63–84 µm 振荡</td></tr>
<tr><td>Si 区域尺寸</td>
<td>初始 {fmt(hist['size_um'][0], ' µm')} → 膨胀至最大 {fmt(si_wmax, ' µm')} (t = {fmt(si_wmax_t, ' ns')},
体密度 ≈ 0.6 g/cm³) → 激波汇聚压缩至最小 {fmt(si_wmin, ' µm')} (t = {fmt(si_wmin_t, ' ns')}) →
再膨胀至 {fmt(hist['size_um'][1], ' µm')} (t = 1.6 ns)</td></tr>
<tr><td>Si 区平均 T_e</td>
<td>{fmt(hist['tele_eV_mean'][0], ' eV')} (冷态) → 5 eV (膨胀期) → 汇聚压缩峰值 ≈150 eV (t ≈ 0.52 ns)
→ 尾段 ≈{fmt(hist['tele_eV_mean'][1], ' eV')}</td></tr>
<tr><td>Si 区平均 p</td>
<td>{fmt(hist['pres_Mbar_mean'][0], ' Mbar')} → 汇聚峰值 ≈400 Mbar → 尾段 ≈{fmt(hist['pres_Mbar_mean'][1], ' Mbar')}</td></tr>
<tr><td>Si 区 Γ_i / Θ_e</td>
<td>Γ_i: {fmt(hist['gamma_mean'][0], '', 2)} → 峰值 3.7 (强耦合) → {fmt(hist['gamma_mean'][1], '', 2)};
Θ_e: {fmt(hist['theta_mean'][0], '', 2)} (弱简并) → {fmt(hist['theta_mean'][1], '', 2)} (经典极限);
汇聚瞬间 n_e 由 ~1e22 跳升至 ~2e24 cm⁻³, 简并性解除</td></tr>
<tr><td>Si 面质量 (∫dens·targ dx)</td>
<td>初始 2.085×10⁻⁴ g/cm² (理论 2.3×0.92 µm = 2.116×10⁻⁴ 的 98.5%, 差值为
targ≥0.5 掩膜截除界面混合格元); size 范围内积分在激波压缩后半高区段收窄,
降至最低 1.822×10⁻⁴; 全域 targ≥0.5 积分末期保持 1.978×10⁻⁴ (≈93.5%),
其余 ~6.5% 为界面混合 (targ&lt;0.5) 部分 — 1D 物种质量基本守恒</td></tr>
<tr><td>冷材初始电离度</td>
<td>t = 0 全域 n_e,max ≈ 9.86×10²⁰ cm⁻³ &lt; N_C = {N_C:.2e} cm⁻³ (IONMIX 室温近中性),
最初数十 ps x_c/x_a 无定义</td></tr>
</table>

<h2>8. FLYCHK history 输入 (Si 区平均, 两类)</h2>
<p>由 <code>data/si_history.csv</code> (Si 区平均, 299 帧) 经
<code>flash/input_gen/gen_flychk_his</code> 包生成 NIST FLYCHK history 模式上传 zip
(格式契约 flychk-history-v1, 元素 Si, Z=14; 时间 [0, 1.6] ns 均匀 175 点,
FLYCHK 要求 t&gt;0, 取 t_i = 1.6·i/175 ns, i=1..175, Δt ≈ 9.14 ps;
各列由 299 帧线性插值; te_floor = 0.01 eV 保留冷态)。两类 zip 归拢于
<code>analysis/InterfaceEvolution/flychk/out/</code>, 回读自检 integrity_ok = True:</p>
<table>
<tr><th style="width:280px">类型</th><th>列</th><th>密度基准</th><th>文件</th></tr>
<tr><td><b>1.1</b></td><td>time, size, te, ti, tr, ne</td>
<td>ne = Si 区平均电子数密度 (cm⁻³)</td><td><code>history_si1.1ne_Si_Z14_in_.zip</code></td></tr>
<tr><td><b>1.3</b></td><td>time, size, te, ti, tr, rho</td>
<td>rho = dens·targ (Si 组分质量密度平均, g/cm³)</td><td><code>history_si1.3rho_Si_Z14_in_.zip</code></td></tr>
</table>
<div class="warn">注意: FLYCHK 网站对 history 提供建议 ≤ 50 时间步, 本输入按需求取 175 点;
若网站提交超时, 在 <code>flychk/make_flychk_zips.py</code> 中设
<code>n_time_max</code> 抽稀重跑。</div>

<div class="figure">
<img src="data:image/png;base64,{b64img(FIGS / 'flychk_si1.1ne_preview.png')}" alt="flychk 1.1">
<p>图 6: 1.1 类输入预诊断图, 4 面板 — ① 温度 (TE 红长虚线 / TI 蓝密点线 / 
TR 绿点划线, 三线全部非实线, 重叠区交错可辨); ② 电子数密度 (log 轴);
③ size 路径长度 (log 轴); ④ Si 面质量 ∫ρ_Si dx (g/cm²): size 范围内积分 vs
全域 targ≥0.5 积分, 黑色点线为初始值 2.085×10⁻⁴ g/cm² (质量守恒核查)。</p>
</div>

<div class="figure">
<img src="data:image/png;base64,{b64img(FIGS / 'flychk_si1.3rho_preview.png')}" alt="flychk 1.3">
<p>图 7: 1.3 类输入预诊断图 — 密度面板为 ρ_Si = dens·targ (g/cm³, 线性轴);
其余面板约定同图 6 (含第 4 面板 Si 面质量守恒核查)。</p>
</div>

<h2>9. 注意事项与解读边界</h2>
<div class="warn">
<ul>
<li><b>x_s 轨迹起点</b>: 激波在泡沫外缘 (±51 µm) 自静态 foam/He 密度间断处启动
(t ≈ 0.01 ns 即有 shok 信号), 该处恰与 x_a 重合, 判据 ④ (起点距 x_a ≤ 20 µm) 通过;
t &lt; 0.1 ns 段反映尚未加速的静压间断, 解读时注意。</li>
<li><b>shok 检测偏置</b>: gradP 判据仅在致密材料 (CH 致密层/Si 及压缩壳) 内触发,
泡沫与冠层中的弱激波不入检 (图 3 中 t &gt; 0.55 ns 无任何 shok 信号);
泡沫段激波需改用密度/速度跃变判据。</li>
<li><b>Si/CH 界面压缩波</b>: 中心 V 形候选轨迹 (图 3) 为 Si 膨胀推动的界面压缩区,
v_s ≈ +9 µm/ns 与 v_a 反号, 已被判据 ①④ 正确排除。</li>
<li><b>远场噪声带</b>: t &lt; 0.2 ns、|x| ≈ 80–100 µm 的 shok 信号为 He 填充区
激光传播路径上的数值伪迹, 距 x_a 过远, 已由判据 ④ 排除。</li>
<li><b>x_c 早期 (t &lt; 0.03 ns)</b>: 冷 Si 初始 n_e (9.86×10²⁰) 距 N_C 仅差 9%,
轻微加热即先于泡沫越过 N_C, 最初 2–3 帧 x_c 位于 Si 边缘, 属"电离前沿越阈";
绘图已对相邻帧位移 &gt; 15 µm 的跳变断开连线。</li>
<li><b>Si 半高基准</b>: 激波压缩壳 (targ≈1, ρ 达 4.2 g/cm³) 会使全局 max 半高判据
只抓到 ~0.04 µm 窄壳; 本报告采用体区 (targ≥0.5) 中位数×0.5 作基准。</li>
<li><b>晚期不对称</b>: t &gt; 1.0 ns 后 Si 区域左右缘出现不对称 (右缘膨胀滞后),
双束几何对称, 差异源于 AMR 布局/射线沉积的数值不对称。</li>
<li><b>烧蚀前沿定义域</b>: x_a 判据依赖 60–600 eV 温区带; 激光关闭 (t &gt; 1.3 ns) 后
x_a 退化为"最陡 T_e 梯度位置", 与烧蚀物理的对应关系减弱。</li>
<li><b>He 填充早期温升</b>: t ≈ 0.05 ns 时 He 区 T_e 已达 ~17 eV (辐射/传导加热),
非初始温度, 读图时注意。</li>
</ul>
</div>

<h2>10. 产物清单</h2>
<table>
<tr><th>文件</th><th>内容</th></tr>
<tr><td><code>data/interfaces.csv</code></td>
<td>逐帧界面位置 + 速度: xc/xa/xs (左右), va/vs (左右, §3.4 差分链, µm/ns), si 缘, si_ref</td></tr>
<tr><td><code>data/spacetime.npz</code></td>
<td>统一网格时空场 (t_ns, x_um, 8 物理量 + shok[max-pool] + targ + dens_targ;
801 点 × {n_chk} 帧, 真实逐帧时间) + shok 原始格元/候选质心散点数据</td></tr>
<tr><td><code>data/si_history.csv</code></td>
<td>Si 区域尺寸 + 平均物理量逐帧时间序列
(含 FLYCHK 所需 tion/trad/dens·targ 平均, 及面质量
si_areal_mass_gcm2 / si_areal_mass_all_gcm2)</td></tr>
<tr><td><code>flychk/out/</code></td>
<td>两类 FLYCHK history 输入 zip (1.1 ne / 1.3 rho=dens·targ) + 数据表 txt +
预诊断图 + 合并 manifest.json (175 点, [0,1.6] ns, 回读自检通过)</td></tr>
<tr><td><code>figures/</code></td>
<td>interface_evolution_full/zoom.png · spacetime_maps.png · map_shok.png · si_history.png ·
fig_compare_nele_tele_rho.png (全英文, Times New Roman, 字号 ≥ 18 pt)</td></tr>
<tr><td><code>fig_data/fig/</code></td>
<td>参考仿真数字化数据 (WebPlotDigitizer 工程 tar + csv + 原图 png):
nele/tele/rho_vs_time.csv (无表头, 时间 ns + 数值)</td></tr>
<tr><td><code>data/extraction_log.txt</code></td><td>提取运行日志 (轨迹筛选逐条诊断)</td></tr>
<tr><td><code>report.html</code></td><td>本报告</td></tr>
</table>

<h2>11. 与参考数据对比 (Si 区平均: n_e / T_e / ρ_Si)</h2>
<p>参考数据取自 <code>fig_data/fig/</code> 中另一仿真的数字化曲线
(WebPlotDigitizer 工程, 无表头 csv: 时间 ns + 数值; nele 面板 y 轴 log
3×10²²–10²⁴ cm⁻³)。图中参考数据以红色空心小散点绘制 (不连线),
当前 FLASH run 000002 的 Si 区平均 (<code>data/si_history.csv</code>:
nele_mean / tele_eV_mean / dens_targ_mean) 以蓝色实线绘制。</p>
<img src="data:image/png;base64,{b64img(FIGS / 'fig_compare_nele_tele_rho.png')}"
     alt="reference vs FLASH comparison" style="max-width:100%;border:1px solid #999">
<p>图 8: Si 区平均 n_e (log 轴) / T_e / ρ_Si = dens·targ 随时间对比 —
参考 csv (红空心散点) vs FLASH run 000002 (蓝实线)。</p>
<p>对比要点: 两组数据整体演化形态一致 (初始常态 → 激波压缩尖峰 → 缓慢膨胀),
但存在系统性差异 — ① 参考数据压缩峰出现于 t≈0.40–0.45 ns,
早于本 run 的 t≈0.52 ns; ② 峰值幅度参考数据偏低
(T_e 峰 ≈95 eV vs 152 eV; ρ_Si 峰 ≈11 vs 14.7 g/cm³;
n_e 峰 ≈2×10²³ vs ~10²⁴ cm⁻³); ③ t&gt;0.7 ns 后两者衰减趋势与量级趋于接近。
差异可能来自参考源的驱动条件/靶参数不同, 或 Si 区平均的提取定义差异,
仅供趋势对照。</p>

</body>
</html>
"""
    out = HERE / "report.html"
    out.write_text(html_doc, encoding="utf-8")
    print(f"[report] OK  {out}")


if __name__ == "__main__":
    main()
