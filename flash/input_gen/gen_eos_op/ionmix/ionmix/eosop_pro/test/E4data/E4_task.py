# -*- coding: utf-8 -*-
"""
E4 任务脚本 (冲击雨贡纽 / Hugoniot)
====================================

复刻 test_all.py 任务 E 中的 E4 子任务, 在统一参考态 (rho_ref, T_ref) 下:

  E4  : 冲击雨贡纽 Hugoniot        -> E4_hugoniot.png
        (三幅子图: rho-P / Us-Up 线性拟合 / P-V)
  E4b : Us, Up 随压力 P 的关系     -> E4b_usup_vs_P.png
  E4c : P-V 图 (等温线 + 等熵线 + Hugoniot, 同一参考态出发)
                                  -> E4c_pv_diagram.png

同时把每张图对应的数据导出为同名 CSV:

  E4_hugoniot_data.csv      : Hugoniot 曲线点 (rho, P, Us, Up, V) 及参考态/fit 注释
  E4b_usup_vs_P_data.csv    : 窗口 [0,100] um/ns 内的 (P, Us, Up)
  E4c_pv_diagram_data.csv   : 三条路径 (isotherm/isentrope/hugoniot/reference) 的 (V, P)

约束:
  - 全程复用 core/ 下经校验的 eos_paths / cn4_parser, 不重复实现物理;
  - 绘图沿用 PPT 演讲级风格 (全英文标签, 字号 >=20pt, DPI=450);
  - 脚本与产物均落在本目录 E4data/ 内 (每材料一个子目录)。

用法:
    python E4_task.py                 # 处理 Gen_eos_op_data 下全部 .cn4
    python E4_task.py --only CH       # 仅文件名含 'CH' 的材料
    python E4_task.py --cn4 path.cn4  # 仅单个文件
"""

import argparse
import csv
import glob
import os
import sys

import numpy as np
from scipy.interpolate import RegularGridInterpolator

# ---- 路径设置: 允许从 E4data/ 导入 core/ 与 eosop_pro 根模块 ----
HERE = os.path.dirname(os.path.abspath(__file__))          # .../eosop_pro/test/E4data
TEST_DIR = os.path.dirname(HERE)                           # .../eosop_pro/test
EOSOP_PRO = os.path.dirname(TEST_DIR)                      # .../eosop_pro
CORE = os.path.join(EOSOP_PRO, "core")                     # .../eosop_pro/core
for _p in (CORE, EOSOP_PRO, TEST_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from cn4_parser import load_cn4                            # noqa: E402
import eos_paths as E                                       # noqa: E402
from eos_paths import (                                    # noqa: E402
    compute_entropy, interpolate_quantity, rho_from_nion,
    _press, _NAV,
)
from units import pressure_mbar, velocity_umns             # noqa: E402

_NA = 6.02214076e23


# ---------------------------------------------------------------
# 参考态选择 (与 test_all.task_E_eospaths 完全一致)
# ---------------------------------------------------------------
def _reference_state(data):
    """返回 (T_ref_eV, rho_ref_gcm3, is_CH)。"""
    T_ref = float(data.temperature[0])                     # 表最低温 (eV)
    avgatw = data.avgatw
    if avgatw is None:
        raise ValueError("原子量未知, E4 需要 rho<->nion 换算")
    is_ch = (6 in data.izgas) and (1 in data.izgas)        # C + H -> CH
    rho_geom = (float(np.sqrt(data.density[0] * data.density[-1]))
                * avgatw / _NA)
    rho_ref = 1.0 if is_ch else rho_geom                   # g/cm^3
    return T_ref, rho_ref, is_ch


# ---------------------------------------------------------------
# P-V 图三条路径的数据提取 (用于 CSV, 与 plot_pv_diagram 内部逻辑一致)
# ---------------------------------------------------------------
def _extract_pv_arrays(data, T_ref, s_field, rho_ref):
    """返回 (V_dense, P_iso, V_ent, P_ent)。

    等温线: T=T_ref 固定, 沿加密 rho 轴插值 P;
    等熵线: s_rel = s_field - s(rho_ref,T_ref)=0 的双方向扫描曲线。
    """
    rho_axis = rho_from_nion(data, data.density)           # (ndens,)
    rho_dense = 10 ** np.linspace(np.log10(rho_axis[0]),
                                  np.log10(rho_axis[-1]), 200)
    T_dense = 10 ** np.linspace(np.log10(data.temperature[0]),
                                np.log10(data.temperature[-1]), 120)
    V_dense = 1.0 / rho_dense

    # 等温线 P
    P_iso = interpolate_quantity(data, "p", rho_dense, T_ref,
                                 field=_press(data))

    # 等熵线 s_rel=0 扫描
    s_gi = RegularGridInterpolator(
        (np.log10(data.density), np.log10(data.temperature)),
        s_field, bounds_error=False, fill_value=None)
    nion_ref = float(rho_ref) * _NAV / data.avgatw
    s_ref = float(s_gi([np.log10(nion_ref), np.log10(float(T_ref))])[0])
    Rg, Tg = np.meshgrid(rho_dense, T_dense, indexing="ij")
    nion_grid = Rg * _NAV / data.avgatw
    s_fine = s_gi(np.stack([np.log10(nion_grid.ravel()),
                            np.log10(Tg.ravel())], axis=1)).reshape(Rg.shape)
    s_rel = s_fine - s_ref

    n_rho, n_T = s_rel.shape
    rho_pts, T_pts = [], []
    for i in range(n_rho):                                 # 固定 rho 沿 T
        row = s_rel[i]
        for j in range(n_T - 1):
            if row[j] * row[j + 1] < 0:
                fr = row[j] / (row[j] - row[j + 1])
                T_c = 10 ** (np.log10(T_dense[j]) +
                             fr * (np.log10(T_dense[j + 1]) -
                                   np.log10(T_dense[j])))
                rho_pts.append(rho_dense[i]); T_pts.append(T_c)
    for j in range(n_T):                                   # 固定 T 沿 rho
        col = s_rel[:, j]
        for i in range(n_rho - 1):
            if col[i] * col[i + 1] < 0:
                fr = col[i] / (col[i] - col[i + 1])
                rho_c = 10 ** (np.log10(rho_dense[i]) +
                               fr * (np.log10(rho_dense[i + 1]) -
                                     np.log10(rho_dense[i])))
                rho_pts.append(rho_c); T_pts.append(T_dense[j])

    if rho_pts:
        rho_ent = np.array(rho_pts, dtype=float)
        T_ent = np.array(T_pts, dtype=float)
        P_ent = interpolate_quantity(data, "p", rho_ent, T_ent,
                                     field=_press(data))
        V_ent = 1.0 / rho_ent
    else:
        V_ent = P_ent = np.array([], dtype=float)
    return V_dense, P_iso, V_ent, P_ent


# ---------------------------------------------------------------
# CSV 写出辅助
# ---------------------------------------------------------------
def _write_csv(path, header, rows, comment_lines=None):
    with open(path, "w", newline="", encoding="utf-8") as f:
        if comment_lines:
            for c in comment_lines:
                f.write(f"# {c}\n")
        w = csv.writer(f)
        w.writerow(header)
        for r in rows:
            w.writerow(r)
    print(f"[csv] {path}  ({len(rows)} data rows)")


# ---------------------------------------------------------------
# 单个材料的 E4 任务
# ---------------------------------------------------------------
def run_E4(data, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    T_ref, rho_ref, is_ch = _reference_state(data)

    # ── E4: 冲击雨贡纽曲线 (返回 rho_c, P_c, Us, Up, png) ──
    rho_c, P_c, Us, Up, f_hug = E.trace_hugoniot(
        data, rho0=rho_ref, T0=T_ref,
        outfile=os.path.join(out_dir, "E4_hugoniot.png"))

    V_c = 1.0 / rho_c
    Us_u = velocity_umns(Us)
    Up_u = velocity_umns(Up)
    P_mbar = pressure_mbar(P_c)

    # Us-Up 线性拟合 (面板 2 显示窗口 Up<=80 um/ns)
    fit_win = 80.0
    m_fit = Up_u <= fit_win
    if m_fit.sum() >= 2:
        k, b = np.polyfit(Up_u[m_fit], Us_u[m_fit], 1)
        yfit = k * Up_u[m_fit] + b
        ss_res = float(np.sum((Us_u[m_fit] - yfit) ** 2))
        ss_tot = float(np.sum((Us_u[m_fit] - np.mean(Us_u[m_fit])) ** 2))
        r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    else:
        k, b, r2 = float("nan"), float("nan"), float("nan")

    c_hug = [
        "# E4_hugoniot.png : shock Hugoniot curve (three panels)",
        f"# material={data.basename}  species={data.species_label}",
        f"# ref_state: rho0={rho_ref:.6e} g/cm^3, T0={T_ref:.6e} eV",
        f"# n_points={len(rho_c)}  (compression branch rho>rho0)",
        f"# panel2 Us-Up linear fit (Up<=80 um/ns): Us={k:.6f}*Up+{b:.6e}"
        f"  R2={r2:.6f}",
        "# columns: mass density rho (g/cm^3), pressure P (Mbar),",
        "#          shock velocity Us (um/ns), particle velocity Up (um/ns),",
        "#          specific volume V=1/rho (cm^3/g)",
    ]
    rows_hug = [[f"{rho_c[i]:.10e}", f"{P_mbar[i]:.10e}",
                 f"{Us_u[i]:.10e}", f"{Up_u[i]:.10e}",
                 f"{V_c[i]:.10e}"] for i in range(len(rho_c))]
    _write_csv(os.path.join(out_dir, "E4_hugoniot_data.csv"),
               ["rho_gcm3", "P_Mbar", "Us_umns", "Up_umns", "V_cm3g"],
               rows_hug, comment_lines=c_hug)

    # ── E4b: Us/Up vs P (窗口 [0,100] um/ns) ──
    keep = (Us_u >= 0) & (Us_u <= 100.0) & (Up_u >= 0) & (Up_u <= 100.0)
    if keep.sum() == 0:
        keep = np.ones_like(keep, dtype=bool)
    f_b = E.plot_usup_vs_pressure(
        Us, Up, P_c,
        outfile=os.path.join(out_dir, "E4b_usup_vs_P.png"))
    c_b = [
        "# E4b_usup_vs_P.png : Us/Up vs pressure P (linear y, window [0,100] um/ns)",
        f"# material={data.basename}",
        f"# n_points(plotted)={int(keep.sum())} of {len(Us_u)} total",
        "# columns: pressure P (Mbar), shock velocity Us (um/ns),",
        "#          particle velocity Up (um/ns)",
    ]
    rows_b = [[f"{P_mbar[i]:.10e}", f"{Us_u[i]:.10e}", f"{Up_u[i]:.10e}"]
              for i in np.where(keep)[0]]
    _write_csv(os.path.join(out_dir, "E4b_usup_vs_P_data.csv"),
               ["P_Mbar", "Us_umns", "Up_umns"],
               rows_b, comment_lines=c_b)

    # ── E4c: P-V 图 (等温 + 等熵 + Hugoniot; V=1/rho) ──
    s_field = compute_entropy(data)
    f_c = E.plot_pv_diagram(
        data, T_ref, s_field, rho_ref, rho_c, P_c,
        outfile=os.path.join(out_dir, "E4c_pv_diagram.png"))

    V_dense, P_iso, V_ent, P_ent = _extract_pv_arrays(
        data, T_ref, s_field, rho_ref)
    V0 = 1.0 / float(rho_ref)
    P0 = interpolate_quantity(data, "p", rho_ref, T_ref, field=_press(data))
    V_h = 1.0 / rho_c
    P_h = P_c

    rows_c = []
    for v, p in zip(V_dense, P_iso):
        rows_c.append(["isotherm", f"{v:.10e}", f"{pressure_mbar(p):.10e}"])
    for v, p in zip(V_ent, P_ent):
        rows_c.append(["isentrope", f"{v:.10e}", f"{pressure_mbar(p):.10e}"])
    for v, p in zip(V_h, P_h):
        rows_c.append(["hugoniot", f"{v:.10e}", f"{pressure_mbar(p):.10e}"])
    rows_c.append(["reference", f"{V0:.10e}", f"{pressure_mbar(P0):.10e}"])
    c_c = [
        "# E4c_pv_diagram.png : EOS paths in P-V plane from common reference state",
        f"# material={data.basename}  T_ref={T_ref:.6e} eV  rho_ref={rho_ref:.6e} g/cm^3",
        "# columns: path (isotherm/isentrope/hugoniot/reference),",
        "#          specific volume V=1/rho (cm^3/g), pressure P (Mbar)",
    ]
    _write_csv(os.path.join(out_dir, "E4c_pv_diagram_data.csv"),
               ["path", "V_cm3g", "P_Mbar"],
               rows_c, comment_lines=c_c)

    return {
        "material": data.basename,
        "species": data.species_label,
        "T_ref_eV": T_ref, "rho_ref_gcm3": rho_ref, "is_CH": is_ch,
        "hugoniot_points": len(rho_c),
        "png": [f_hug, f_b, f_c],
    }


# ---------------------------------------------------------------
# 材料发现
# ---------------------------------------------------------------
def discover_cn4(only=None, cn4_path=None):
    if cn4_path:
        return [os.path.abspath(cn4_path)]
    base = os.path.normpath(os.path.join(
        EOSOP_PRO, "..", "..", "..", "eos_op_data", "Gen_eos_op_data"))
    cn4s = sorted(glob.glob(os.path.join(base, "**", "*.cn4"),
                            recursive=True))
    if only:
        cn4s = [c for c in cn4s if only.lower() in os.path.basename(c).lower()]
    return cn4s


def main():
    ap = argparse.ArgumentParser(description="E4 Hugoniot task")
    ap.add_argument("--only", default=None,
                    help="仅处理文件名包含此子串的材料 (如 CH)")
    ap.add_argument("--cn4", default=None, help="仅处理单个 .cn4 文件")
    args = ap.parse_args()

    cn4s = discover_cn4(only=args.only, cn4_path=args.cn4)
    if not cn4s:
        print("[!] 未发现任何 .cn4 文件")
        sys.exit(1)
    print(f"发现 {len(cn4s)} 个材料文件, 输出目录: {HERE}")

    summary = []
    for cn4 in cn4s:
        try:
            data = load_cn4(cn4)
            out_dir = os.path.join(HERE, data.basename)
            print(f"\n=== 材料: {data.basename} ({data.species_label}) ===")
            rec = run_E4(data, out_dir)
            rec["file"] = cn4
            summary.append(rec)
            print(f"  [OK] {rec['hugoniot_points']} Hugoniot 点 -> {out_dir}")
        except Exception as ex:                         # noqa: BLE001
            import traceback
            print(f"  [FAIL] {cn4}: {type(ex).__name__}: {ex}")
            traceback.print_exc()
            summary.append({"file": cn4, "error": str(ex)})

    ok = sum(1 for s in summary if "error" not in s)
    print(f"\n==== E4 任务完成: {ok}/{len(summary)} 材料成功 ====")
    return summary


if __name__ == "__main__":
    main()
