# -*- coding: utf-8 -*-
"""
eosop_pro 全局测试脚本 (覆盖任务 A/B/C/D/E)
==========================================

自动发现 eos_op_data/Gen_eos_op_data 下所有 .cn4 材料文件,
对每个材料生成全部 5 类任务的图像:

  任务A  二维彩图 (任意 x/y 轴组合: T/nion/nele/rho, 及群不透明度/透射率)
  任务B  一维变化曲线 (物理量随 T 或 n_i)
  任务C  时间序列图 (合成 FLASH 风格数据, 验证绘图管线)
  任务D  函数拟合 (幂律/指数/理想气体/通用)
  任务E  物态方程路径 (等温/等压/等熵/冲击雨贡纽)

所有输出统一落在 test/output/<材料名>/ 下, 并生成测试摘要 JSON,
供 generate_report.py 生成 HTML 报告。

不硬编码任何材料: 材料成分、原子量、能群均从 .cn4 自动派生。

用法:
    python test_all.py                 # 测试所有自动发现的 cn4
    python test_all.py --only CH       # 仅测试含 'CH' 的文件名
    python test_all.py --cn4 path      # 仅测试单个文件
"""

import argparse
import glob
import json
import os
import sys
import traceback
import time
import numpy as np

# ---- 路径设置: 允许从 test/ 导入 core/ 下所有模块 ----
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)                     # eosop_pro/
CORE = os.path.join(ROOT, "core")               # eosop_pro/core/ (所有绘图脚本已收纳于此)
for _p in (CORE, ROOT, HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from cn4_parser import load_cn4                 # noqa: E402
import plot_heatmaps as H                        # noqa: E402
import plot_curves as C                          # noqa: E402
import plot_time_series as TS                    # noqa: E402
import fit_relations as F                        # noqa: E402
import eos_paths as E                            # noqa: E402

OUTPUT_ROOT = os.path.join(HERE, "output")


# ---------------------------------------------------------------
# 工具: 安全执行单步并捕获异常
# ---------------------------------------------------------------
def _run_step(results, task, name, func):
    """执行 func, 记录成功/失败、产物路径、附加信息到 results"""
    rec = {"task": task, "name": name, "ok": False,
           "files": [], "info": {}, "error": None}
    t0 = time.time()
    try:
        ret = func()
        # 统一返回约定: (files_list, info_dict) 或 files_list 或 None
        if isinstance(ret, tuple) and len(ret) == 2 and isinstance(ret[1], dict):
            files, info = ret
            rec["files"] = files if isinstance(files, list) else [files]
            rec["info"] = info
        elif isinstance(ret, list):
            rec["files"] = ret
        elif isinstance(ret, str):
            rec["files"] = [ret]
        rec["ok"] = True
    except Exception as ex:                      # noqa: BLE001
        rec["error"] = f"{type(ex).__name__}: {ex}"
        rec["trace"] = traceback.format_exc()
    rec["elapsed_s"] = round(time.time() - t0, 2)
    results.append(rec)
    status = "OK " if rec["ok"] else "FAIL"
    print(f"  [{status}] {task}/{name} ({rec['elapsed_s']}s)")
    return rec


# ---------------------------------------------------------------
# 各任务测试函数 (返回 (files, info))
# ---------------------------------------------------------------

def task_A_heatmaps(data, out_dir):
    """任务A: 任意轴二维彩图 + 群不透明度/透射率"""
    files = []
    # A1: EOS 物理量彩图, 多种轴组合
    combos = [
        ("zbar", "T", "nion"),
        ("zbar", "T", "nele"),
        ("rho", "T", "nion"),
        ("nele", "T", "nion"),
        ("p_ion", "T", "nion"),
        ("e_ele", "T", "nele"),
    ]
    for q, x, y in combos:
        f = H.plot_quantity_heatmap(
            data, q, x_axis=x, y_axis=y,
            outfile=os.path.join(out_dir, f"A1_{q}_{x}-{y}.png"))
        files.append(f)
    # A2: 群不透明度 + 透射率 (每群一张 2x2 大图)
    grp_files = H.plot_all_opacity_figures(
        data, outdir=out_dir, transmission_L=0.01)
    files.extend(grp_files)
    info = {"material": data.species_label,
            "combos": len(combos), "group_figures": len(grp_files),
            "ngroups": data.ngrups}
    return files, info


def task_B_curves(data, out_dir):
    """任务B: 一维变化曲线 (随 T / 随 n_i)"""
    files = []
    # B1: zbar 随 T (多条密度曲线)
    f1 = C.plot_vs_temperature(
        data, "zbar", density_idx=[0, 10, 20, 30],
        outfile=os.path.join(out_dir, "B1_zbar_vs_T.png"))
    # B2: Rosseland 不透明度随 n_i (多条温度曲线)
    f2 = C.plot_vs_density(
        data, "opac_rosseland", ig=1, temp_idx=[0, 20, 40],
        outfile=os.path.join(out_dir, "B2_rosseland_g1_vs_nion.png"))
    # B3: zbar 随 n_i
    f3 = C.plot_vs_density(
        data, "zbar", temp_idx=[0, 20, 40],
        outfile=os.path.join(out_dir, "B3_zbar_vs_nion.png"))
    files.extend([f1, f2, f3])
    return files, {"curves": 3}


def task_C_timeseries(data, out_dir):
    """任务C: 时间序列图 (合成 FLASH 风格高斯波包, 验证绘图管线)"""
    t = np.linspace(0, 3.1e-9, 40)
    x = np.linspace(-50e-4, 50e-4, 100)
    T, X = np.meshgrid(t, x)
    # 空间波前随时间推进 + 量纲取 nele 量级
    field = np.exp(-((X - 1e-3 * T / 3.1e-9) ** 2) / (2 * (8e-4) ** 2)) \
        * data.nele.max()
    f1 = TS.plot_time_series(
        t, x, field.T,
        xlabel="x (cm)",
        quantity_label="Electron density (cm$^{-3}$)",
        outfile=os.path.join(out_dir, "C1_timespace_nele.png"))
    f2 = TS.plot_center_series(
        t, x, field.T, x_center=0.0,
        quantity_label="Electron density (cm$^{-3}$)",
        outfile=os.path.join(out_dir, "C2_center_nele.png"))
    return [f1, f2], {"synthetic": True, "nt": len(t), "nx": len(x)}


def task_D_fit(data, out_dir):
    """任务D: 函数拟合 (幂律/指数/理想气体/通用)"""
    files = []
    info = {}
    # D1: 幂律 E_e ~ T^b (固定某密度行)
    a, b, r2, f1 = F.fit_power_law(
        data.temperature, data.e_ele[10],
        xlabel="Temperature T (eV)", ylabel="Electron energy e_e (J/g)",
        outfile=os.path.join(out_dir, "D1_powerlaw_eele.png"))
    info["powerlaw_e_ele"] = {"a": a, "b": b, "R2": round(r2, 4)}
    # D2: 指数 zbar ~ exp(-B/T) (固定某密度行)
    ae, be, r2e, f2 = F.fit_exponential(
        data.temperature, data.zbar[10],
        xlabel="Temperature T (eV)", ylabel="Average charge <Z>",
        outfile=os.path.join(out_dir, "D2_exp_zbar.png"))
    info["exponential_zbar"] = {"a": ae, "b": be, "R2": round(r2e, 4)}
    # D3: 理想气体检验 P = (1+<Z>) n k_B T
    slope, r2i, f3 = F.fit_ideal_gas(
        data, T_idx=10,
        outfile=os.path.join(out_dir, "D3_ideal_gas.png"))
    info["ideal_gas"] = {"slope": round(slope, 4), "R2": round(r2i, 4)}
    # D4: 通用 Saha 型 Z(T) = A/(1+exp(B/T))
    popt, pcov, r2g, f4 = F.fit_generic(
        data.temperature, data.zbar[10],
        lambda T, A, B: A / (1.0 + np.exp(B / T)),
        p0=[data.zbar[10].max(), 10.0],
        xlabel="Temperature T (eV)", ylabel="Average charge <Z>",
        outfile=os.path.join(out_dir, "D4_generic_saha.png"))
    info["generic_saha"] = {"params": [round(v, 4) for v in popt],
                            "R2": round(r2g, 4)}
    files.extend([f1, f2, f3, f4])
    return files, info


def task_E_eospaths(data, out_dir):
    """
    任务E: 物态方程路径 (等温/等压/等熵/冲击雨贡纽 + 插值探针)。
    默认以 (rho, T) 数值为输入 (cn4 表格为 nion,T 网格, 内部自动换算 + 插值):
      - 参考温度 T_ref = 表最低温 (≈ IONMIX 低温下限 1 eV; 常温 0.025 eV 会 clamp)
      - 参考密度 rho_ref: CH (含 C+H) 用常温常压固定密度 1.0 g/cm^3;
        其他材料用表 nion 几何中值对应的质量密度 (保证在表范围内)
    """
    files = []
    info = {}
    T_ref = float(data.temperature[0])   # 表最低温 (eV)

    # ── 参考密度选择 ──
    avgatw = data.avgatw
    if avgatw is None:
        raise ValueError("原子量未知, 任务E需要 rho<->nion 换算")
    is_ch = (6 in data.izgas) and (1 in data.izgas)   # C + H -> CH
    rho_geom = (float(np.sqrt(data.density[0] * data.density[-1]))
                * avgatw / 6.02214076e23)
    rho_ref = 1.0 if is_ch else rho_geom              # g/cm^3
    info["input_mode"] = "rho,T (interpolated)"
    info["T_ref_eV"] = T_ref
    info["rho_ref_gcm3"] = rho_ref
    info["is_CH"] = is_ch

    # E1: 等温线 (T 数值输入, rho 轴)
    x, P, e, f1 = E.trace_isotherm(
        data, T=T_ref, x_axis="rho",
        outfile=os.path.join(out_dir, "E1_isotherm_rho.png"))
    # E2: 等压线 (取压力范围中部)
    P_grid = (data.p_ion + data.p_ele)
    Pmid = float(np.sqrt(P_grid.min() * P_grid.max()))   # 几何中值
    try:
        T_c, n_c, f2 = E.trace_isobar(
            data, P=Pmid, outfile=os.path.join(out_dir, "E2_isobar.png"))
        info["isobar"] = {"P_target": Pmid, "n_points": len(T_c)}
    except Exception as ex:                              # noqa: BLE001
        f2 = None
        info["isobar"] = {"error": str(ex)}
    # E3: 等熵线
    s = E.compute_entropy(data)
    try:
        T_c, n_c, f3 = E.trace_isentrope(
            data, s, s0_idx=(10, 10),
            outfile=os.path.join(out_dir, "E3_isentrope.png"))
        info["isentrope"] = {"n_points": len(T_c)}
    except Exception as ex:                              # noqa: BLE001
        f3 = None
        info["isentrope"] = {"error": str(ex)}
    # E4: 冲击雨贡纽 (rho0/T0 数值输入, 非网格点参考态经插值)
    try:
        rho_c, P_c, Us, Up, f4 = E.trace_hugoniot(
            data, rho0=rho_ref, T0=T_ref,
            outfile=os.path.join(out_dir, "E4_hugoniot.png"))
        info["hugoniot"] = {"n_points": len(rho_c),
                            "rho0": rho_ref, "T0": T_ref}
        # E4b: Us/Up 随压力 P 的关系图
        f4b = E.plot_usup_vs_pressure(
            Us, Up, P_c,
            outfile=os.path.join(out_dir, "E4b_usup_vs_P.png"))
        info["usup_vs_P"] = {"n_points": len(P_c)}
    except Exception as ex:                              # noqa: BLE001
        f4 = f4b = None
        info["hugoniot"] = {"error": str(ex)}
    # E5: 插值探针 (固定 rho_ref, 沿 T 插值; 验证非网格点求值)
    try:
        T_probe = min(float(data.temperature[-1]),
                      max(float(data.temperature[0]),
                          float(data.temperature[0])))
        f5, probe_info = E.plot_interpolated_probe(
            data, rho_probe=rho_ref, T_probe=T_ref,
            outfile=os.path.join(out_dir, "E5_interp_probe.png"))
        info["interp_probe"] = probe_info
    except Exception as ex:                              # noqa: BLE001
        f5 = None
        info["interp_probe"] = {"error": str(ex)}

    files.extend([f for f in [f1, f2, f3, f4, f4b, f5] if f])
    return files, info


TASK_FUNCS = {
    "A": ("Heatmaps (2D color maps)", task_A_heatmaps),
    "B": ("1D curves", task_B_curves),
    "C": ("Time series", task_C_timeseries),
    "D": ("Fittings", task_D_fit),
    "E": ("EOS paths", task_E_eospaths),
}


# ---------------------------------------------------------------
# 主测试流程
# ---------------------------------------------------------------
def discover_cn4(only=None, cn4_path=None):
    """发现待测试 cn4 文件列表"""
    if cn4_path:
        return [os.path.abspath(cn4_path)]
    base = os.path.normpath(os.path.join(
        ROOT, "..", "..", "..", "eos_op_data", "Gen_eos_op_data"))
    cn4s = sorted(glob.glob(os.path.join(base, "**", "*.cn4"),
                            recursive=True))
    if only:
        cn4s = [c for c in cn4s if only.lower() in os.path.basename(c).lower()]
    return cn4s


def run_one_material(cn4_path, selected_tasks=None):
    """对单个材料运行所选任务, 返回 material 记录 dict.

    注意: 函数名不以 test_ 开头, 避免被 pytest 误收集为测试函数
    (旧名 test_one_material 曾导致 'fixture cn4_path not found' 报错)。
    pytest 入口见 test_eosop_all_tasks。
    """
    print(f"\n=== 材料: {os.path.basename(cn4_path)} ===")
    data = load_cn4(cn4_path)
    mat_name = data.basename
    out_dir = os.path.join(OUTPUT_ROOT, mat_name)
    os.makedirs(out_dir, exist_ok=True)

    mat_rec = {
        "file": cn4_path,
        "name": mat_name,
        "species": data.species_label,
        "atomwt": None if data.atomwt is None else data.atomwt.tolist(),
        "ntemp": data.ntemp,
        "ndens": data.ndens,
        "ngrups": data.ngrups,
        "T_range": [float(data.temperature[0]), float(data.temperature[-1])],
        "nion_range": [float(data.density[0]), float(data.density[-1])],
        "group_bounds": data.group_bounds.tolist(),
        "results": [],
    }

    for key, (desc, func) in TASK_FUNCS.items():
        if selected_tasks and key not in selected_tasks:
            continue
        print(f"-- 任务 {key}: {desc} --")
        _run_step(mat_rec["results"], key, desc,
                  lambda d=data, o=out_dir, fn=func: fn(d, o))
    return mat_rec


def main():
    ap = argparse.ArgumentParser(description="eosop_pro global test")
    ap.add_argument("--only", default=None,
                    help="仅测试文件名包含此子串的材料 (如 CH)")
    ap.add_argument("--cn4", default=None, help="仅测试单个 .cn4 文件")
    ap.add_argument("--tasks", default="A,B,C,D,E",
                    help="逗号分隔的任务键 (A/B/C/D/E), 默认全部")
    args = ap.parse_args()

    selected = [t.strip().upper() for t in args.tasks.split(",") if t.strip()]
    cn4s = discover_cn4(only=args.only, cn4_path=args.cn4)
    if not cn4s:
        print("[!] 未发现任何 .cn4 文件")
        sys.exit(1)
    print(f"发现 {len(cn4s)} 个材料文件, 任务集: {selected}")

    all_recs = []
    t_start = time.time()
    for cn4 in cn4s:
        try:
            rec = run_one_material(cn4, selected_tasks=selected)
            all_recs.append(rec)
        except Exception as ex:                          # noqa: BLE001
            print(f"  [FATAL] 材料 {cn4} 加载失败: {ex}")
            all_recs.append({"name": os.path.basename(cn4),
                             "file": cn4, "error": str(ex), "results": []})

    summary = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "python": sys.version.split()[0],
        "output_root": OUTPUT_ROOT,
        "n_materials": len(all_recs),
        "tasks": selected,
        "materials": all_recs,
        "total_elapsed_s": round(time.time() - t_start, 2),
    }
    # 统计
    n_ok = sum(1 for m in all_recs for r in m["results"] if r["ok"])
    n_fail = sum(1 for m in all_recs for r in m["results"] if not r["ok"])
    n_files = sum(len(r["files"]) for m in all_recs for r in m["results"])
    summary["n_steps_ok"] = n_ok
    summary["n_steps_fail"] = n_fail
    summary["n_images"] = n_files

    out_json = os.path.join(HERE, "test_summary.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"\n==== 测试完成 ====")
    print(f"材料数: {summary['n_materials']}")
    print(f"步骤成功/失败: {n_ok} / {n_fail}")
    print(f"生成图像: {n_files}")
    print(f"耗时: {summary['total_elapsed_s']}s")
    print(f"摘要: {out_json}")
    return summary


if __name__ == "__main__":
    main()


# ---------------------------------------------------------------
# pytest 入口 (修复: 旧版 test_one_material 被 pytest 误收集,
# cn4_path 被当作 fixture 解析 -> 'fixture not found' 报错)
# 在 PyCharm / pytest 中运行本文件时执行真实全任务:
#   环境变量 EOSOP_ONLY / EOSOP_TASKS 可选过滤 (如 --only CH 等价行为)
# ---------------------------------------------------------------
def test_eosop_all_tasks():
    """pytest 入口: 对全部自动发现的 cn4 材料执行 A-E 任务, 断言无失败步骤。"""
    only = os.environ.get("EOSOP_ONLY")
    tasks_env = os.environ.get("EOSOP_TASKS", "A,B,C,D,E")
    selected = [t.strip().upper() for t in tasks_env.split(",") if t.strip()]

    cn4s = discover_cn4(only=only, cn4_path=None)
    assert cn4s, "未发现任何 .cn4 材料文件"
    print(f"[pytest] 发现 {len(cn4s)} 个材料, 任务集: {selected}")

    n_fail = 0
    fail_msgs = []
    for cn4 in cn4s:
        print(f"[pytest] 运行材料: {os.path.basename(cn4)}")
        rec = run_one_material(cn4, selected_tasks=selected)
        for r in rec["results"]:
            if not r["ok"]:
                n_fail += 1
                fail_msgs.append(f"{rec['name']}/{r['task']}: {r['error']}")

    assert n_fail == 0, \
        f"{n_fail} 个任务步骤失败:\n" + "\n".join(fail_msgs[:20])
