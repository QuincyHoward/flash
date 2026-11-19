# -*- coding: utf-8 -*-
"""make_fe_group_zips — SNB 19 群台阶 fe(E) → FLYCHK 输入 zip（含/不含 fe 成对生成）。

分群表达与 fe 文件格式一一对应：
  能量网格 = 19 个群上边界（去掉 E=0 非法点）: E_g = 0.1 eV × 10^((g-1)/3), g=1..19
  每群一个 fe 值: fe(E_g) = (n0(E_g) + n1_g) / sqrt(E_g)
    n0(E)   = ne (2/sqrt(pi)) sqrt(E) exp(-E/Te) / Te^1.5   （各向同性麦氏核心，平滑）
    n1_g    = (4 pi / m_e) sqrt(2 E_g^erg / m_e) |f1_g| 1.602e-12
              f1_g = q_g / W_g,  W_g = (4 pi/3)(2/m_e^2)(E_{g+1}^3 - E_g^3)/3
    探针格点 = argmax(tele)（与 fe_fit_frames / t12 重建同一约定）
  密度列（时间行第二列）= 探针处 ne + n1_tot（n1_tot 在 121 点细网格积分，
    与 t12 口径一致），使密度列与 fe(E) 的真实积分一致。

时间：[0, 1.6] ns 内 175 个均匀采样点（与 electron_map_records.json /
flychk_history_175 完全同一套采样与 chk 映射；冷启动 nele==0 行按既有约定
由首个有效帧前向填充）。

产物（out/）：
  history_SNBVTi2um_hot_Ti_Z22_fe_groups_in_.zip   含 fe：runfile(fe file 行)
                                                   + history 数据 + fe 数据（三成员）
  history_SNBVTi2um_hot_Ti_Z22_fe_none_in_.zip     不含 fe：两成员（history 与含版逐字节相同）
  fe_group_data.npz                                逐帧分群数据（供 plot_fe_groups.py）
  manifest.json / README.txt

history 列: time rho size te ti tr —— fhot/thot 移除（用户约定: 非麦氏
部分直接由 fe(E) 描述; runfile 含 opacity file 行, 无 fhot file 行）。

用法：
  python make_fe_group_zips.py                  # fe = n0+n1（默认，台阶全分布）
  python make_fe_group_zips.py --fe-content excess   # fe = 仅 n1 超额部分（密度列 = n1_tot）
"""
from __future__ import annotations

import argparse
import json
import sys
import time as _time
from datetime import datetime
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[6]                    # flash-sim 工作区根（含 flash/ 包）
ANALYSIS = HERE.parent / "scripts" / "analysis"
for p in (str(ROOT), str(ANALYSIS)):
    if p not in sys.path:
        sys.path.insert(0, p)

from flash.input_gen.gen_flychk_his.builder import HistoryTable          # noqa: E402
from flash.input_gen.gen_flychk_his.zip_writer import (          # noqa: E402
    FE_CONTRACT_ID, FORMAT_CONTRACT_ID, HistoryZipWriter)
from flash.input_gen.gen_flychk_his.gen_fe_file import (         # noqa: E402
    FeExplicitSeries, build_fe_file, write_history_zip_with_fe)
from flash.input_gen.gen_flychk_his.gen_fe_file.fe_file import (  # noqa: E402
    _trapz_sqrt_e_fe)

import snb_io                              # noqa: E402  (analysis 目录共用 IO)
import flychk_history_175 as fh175         # noqa: E402  (175 帧 history 表复用)

sgp = snb_io.sgp
EV2ERG = 1.602176634e-12
ME_G = sgp.ME_G
KB_EV = sgp.KB_EV
NE_G = sgp.NE_G                            # 19

OUT = HERE / "out"
PLOT_DATA = OUT / "fe_group_data.npz"

# 与 t12_phase_anatomy 相同的细网格（n1_tot 积分口径一致）
R_BIN = 10.0 ** (1.0 / 20.0)
E_EV_FINE = np.geomspace(0.1, 1e5, 121)
DE_FINE = E_EV_FINE * (np.sqrt(R_BIN) - 1.0 / np.sqrt(R_BIN))


def fe_group_frame(fr: dict, gd: dict) -> dict:
    """单帧 19 群台阶 fe(E) 数据（探针 = argmax tele）。"""
    i = int(np.argmax(fr["tele"]))
    Te = max(float(fr["tele"][i]) * KB_EV, 1e-3)       # eV（防冷启动除零）
    ne = float(fr["nele"][i])
    E_erg = gd["E_erg"]                                # (20,) erg, E[0]=0
    E_eV = E_erg[1:] / EV2ERG                          # (19,) 群上边界 = fe 能量网格
    E_erg_pts = E_erg[1:]                              # 与 E_eV 一一对应

    # f1_g = q_g / W_g（带号，每群常值）
    W = (4 * np.pi / 3) * (2 / ME_G ** 2) * (E_erg[1:] ** 3 - E_erg[:-1] ** 3) / 3
    f1_g = gd["qg"][:, i] / W                          # (19,)

    # 群值放到其上边界 E_g：n1(E_g) = (4pi/m_e) sqrt(2 E_g^erg/m_e) |f1_g| 1.602e-12
    n1 = (4 * np.pi / ME_G) * np.sqrt(2 * E_erg_pts / ME_G) * np.abs(f1_g) * EV2ERG
    n0 = ne * (2 / np.sqrt(np.pi)) * np.sqrt(E_eV) * np.exp(-E_eV / Te) / Te ** 1.5

    # 细网格 n1_iso（n1_tot 密度口径，与 t12 一致）
    gid = np.clip(np.searchsorted(E_erg[1:] / EV2ERG, E_EV_FINE), 0, NE_G - 1)
    E_erg_fine = E_EV_FINE * EV2ERG
    n1_fine = (4 * np.pi / ME_G) * np.sqrt(2 * E_erg_fine / ME_G) \
        * np.abs(f1_g[gid]) * EV2ERG
    n1_tot = float(np.sum(n1_fine * DE_FINE))

    fe_total = (n0 + n1) / np.sqrt(E_eV)
    fe_excess = n1 / np.sqrt(E_eV)

    qsh = float(fr["qesx"][i])
    qg_frac = gd["qg"][:, i] / qsh if abs(qsh) > 0 else np.zeros(NE_G)

    # 细网格 fe_snb 连续参考线（stairs 表达质量的对照）
    n0_fine = ne * (2 / np.sqrt(np.pi)) * np.sqrt(E_EV_FINE) \
        * np.exp(-E_EV_FINE / Te) / Te ** 1.5
    fe_fine = (n0_fine + n1_fine) / np.sqrt(E_EV_FINE)

    return {
        "i_probe": i, "x_um": float(fr["x"][i] * 1e4),
        "Te_eV": Te, "ne": ne, "n1_tot": n1_tot, "qsh": qsh,
        "E_eV": E_eV, "n0": n0, "n1": n1, "f1_g": f1_g,
        "fe_total": fe_total, "fe_excess": fe_excess,
        "fe0_stairs": n0 / np.sqrt(E_eV),
        "ratio": n1 / np.maximum(n0, 1e-300),
        "qg_frac": qg_frac,
        "fe_fine": fe_fine,
        "norm_dev_total": _norm_dev(E_eV, fe_total, ne + n1_tot),
        "norm_dev_excess": _norm_dev(E_eV, fe_excess, max(n1_tot, 1e-300)),
    }


def _norm_dev(E_eV: np.ndarray, fe: np.ndarray, dens: float) -> float:
    """19 点梯形积分 sqrt(E)*fe dE 与密度列的相对偏差（与 gen_fe_file 校验同口径）。"""
    if dens <= 0:
        return float("nan")
    return abs(_trapz_sqrt_e_fe(E_eV, fe) - dens) / dens


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--fe-content", choices=["total", "excess"], default="total",
                    help="fe 值内容: total=(n0+n1)/sqrt(E)（默认, 全分布台阶）; "
                         "excess=仅 n1/sqrt(E)（密度列=n1_tot）")
    args = ap.parse_args()
    t0 = _time.time()

    print("[fegroups] (1/4) 复用 flychk_history_175 构建 175 帧 history 表 ...")
    table, report, extra = fh175.build_table_175()
    if not report.ok:
        raise RuntimeError("history 表校验失败: " + "; ".join(report.errors))
    # 用户约定: history 仅保留 time/rho/size/te/ti/tr —— 非麦氏部分直接由
    # fe(E) 描述, fhot/thot 列移除（runfile 保留 opacity file 行, 无 fhot file 行）。
    KEEP_COLS = ("time", "rho", "size", "te", "ti", "tr")
    drop = [c for c in table.columns if c not in KEEP_COLS]
    if drop:
        idx = [table.columns.index(c) for c in KEEP_COLS]
        table = HistoryTable(columns=list(KEEP_COLS),
                             rows=[[r[i] for i in idx] for r in table.rows],
                             meta=dict(table.meta))
        print(f"[fegroups] history 列已裁剪为 {list(KEEP_COLS)}（移除 {drop}）")
    times = table.column("time")                       # (175,) s, 与 history 完全一致
    recs = json.loads((snb_io.DATA_DIR / "electron_map_records.json")
                      .read_text(encoding="utf-8"))
    rec_list, skipped = recs["records"], recs["skipped"]
    if len(rec_list) != 175:
        raise RuntimeError(f"记录数 {len(rec_list)} != 175")
    first_valid = next(r for r in rec_list if "skipped" not in r)

    print("[fegroups] (2/4) 逐帧读取 chk 并重建 19 群台阶 fe(E) ...")
    cache: dict[str, dict] = {}
    frames: list[dict] = []
    for k, rec in enumerate(rec_list):
        chk = rec["chk"]
        if chk not in cache:
            fr = snb_io.read_frame(snb_io.RUN_DIR / chk, snb_io.GROUP_BASE)
            cache[chk] = fe_group_frame(fr, sgp.group_diagnostics(fr))
        frames.append(cache[chk])
        if (k + 1) % 25 == 0 or k + 1 == len(rec_list):
            print(f"    {k + 1}/175 帧  ({_time.time() - t0:.0f}s)")

    # 冷启动 nele==0 行：前向填充（与 flychk_history_175 temps 填充同一约定）
    filled_rows = [r["idx"] for r in skipped]
    for idx in filled_rows:
        frames[idx] = cache[first_valid["chk"]]

    E_eV = frames[0]["E_eV"]
    fe_arr = np.stack([f["fe_total"] if args.fe_content == "total"
                       else f["fe_excess"] for f in frames])
    dens_arr = np.array([f["ne"] + f["n1_tot"] if args.fe_content == "total"
                         else max(f["n1_tot"], 1e-300) for f in frames])

    print("[fegroups] (3/4) 构建 fe 文本并写出含/不含两套 zip ...")
    comment = (f"SNB 19-group staircase fe(E) ({args.fe_content}), "
               f"probe = max-tele cell, E_g = 0.1eV*10^((g-1)/3); "
               f"density column = {'ne + n1_tot' if args.fe_content == 'total' else 'n1_tot'}")
    fe = build_fe_file(
        FeExplicitSeries(
            energies=E_eV.tolist(),
            records=[(float(times[k]), float(dens_arr[k]), fe_arr[k].tolist())
                     for k in range(175)],
        ),
        comment=comment,
    )

    OUT.mkdir(parents=True, exist_ok=True)
    zip_fe = OUT / "history_SNBVTi2um_hot_Ti_Z22_fe_groups_in_.zip"
    zip_none = OUT / "history_SNBVTi2um_hot_Ti_Z22_fe_none_in_.zip"
    write_history_zip_with_fe(table, fe, str(zip_fe))
    HistoryZipWriter().write(table, str(zip_none))

    v_fe = HistoryZipWriter().verify_zip(table, str(zip_fe),
                                         fe_text=fe.to_text(),
                                         fe_filename="fe_Ti_Z22_input.txt")
    v_none = HistoryZipWriter().verify_zip(table, str(zip_none))
    if not (v_fe.get("ok") and v_none.get("ok")):
        raise RuntimeError(f"zip 回读自检失败: fe={v_fe} none={v_none}")

    print("[fegroups] (4/4) 落盘 npz / manifest / README ...")
    np.savez_compressed(
        PLOT_DATA,
        E_eV=E_eV, t_ns=times * 1e9,
        fe_stairs=fe_arr, dens_col=dens_arr,
        n0_stairs=np.stack([f["n0"] for f in frames]),
        n1_stairs=np.stack([f["n1"] for f in frames]),
        ratio=np.stack([f["ratio"] for f in frames]),
        qg_frac=np.stack([f["qg_frac"] for f in frames]),
        f1_g=np.stack([f["f1_g"] for f in frames]),
        fe_fine=np.stack([f["fe_fine"] for f in frames]),
        fe0_stairs=np.stack([f["fe0_stairs"] for f in frames]),
        Te_eV=np.array([f["Te_eV"] for f in frames]),
        ne=np.array([f["ne"] for f in frames]),
        n1_tot=np.array([f["n1_tot"] for f in frames]),
        qsh=np.array([f["qsh"] for f in frames]),
        norm_dev=np.array([f[f"norm_dev_{args.fe_content}"] for f in frames]),
        chk=np.array([r["chk"] for r in rec_list]),
        filled_idx=np.array(filled_rows, dtype=int),
        allow_pickle=False,
    )

    d = table.as_dict()
    manifest = {
        "generator": "flash/scenarios/private/tracer/SNB/SNBVTi2um_hot/"
                     "flychk_fe_groups/make_fe_group_zips.py",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "format_contract": FORMAT_CONTRACT_ID,
        "fe_contract": FE_CONTRACT_ID,
        "fe_content": args.fe_content,
        "fe_formula": "fe(E_g) = (n0(E_g) + n1_g)/sqrt(E_g), E_g = 0.1eV*10^((g-1)/3)"
                      if args.fe_content == "total"
                      else "fe(E_g) = n1_g/sqrt(E_g) (excess only)",
        "density_column": "ne(probe) + n1_tot(fine 121-pt grid)"
                          if args.fe_content == "total" else "n1_tot(fine grid)",
        "probe_rule": "argmax(tele) per frame (same as fe_fit_frames/t12)",
        "energy_grid": {"n": 19, "eV_min": float(E_eV[0]),
                        "eV_max": float(E_eV[-1]),
                        "note": "19 group upper boundaries (E=0 dropped, illegal)"},
        "time_sampling": extra["time_sampling"],
        "zips": {"with_fe": zip_fe.name, "without_fe": zip_none.name,
                 "fe_member": "fe_Ti_Z22_input.txt"},
        "zip_integrity": {"with_fe": v_fe, "without_fe": v_none},
        "n_steps": int(table.n_steps), "n_energies": 19,
        "history_source": "flychk_history_175.build_table_175() (identical "
                          "history data in both zips; columns trimmed to "
                          "time/rho/size/te/ti/tr — fhot/thot dropped, the "
                          "non-Maxwellian part is described by the fe file)",
        "forward_filled_rows": filled_rows,
        "ranges": {c: [float(np.nanmin(v)), float(np.nanmax(v))]
                   for c, v in d.items()},
        "norm_deviation": {"median": float(np.nanmedian(
            np.load(PLOT_DATA)["norm_dev"])),
            "note": "coarse 19-pt trapezoid vs density column; large for "
                    "cold frames (Te << 0.1 eV grid floor) — inherent to the "
                    "SNB group grid, warnings recorded not blocking"},
        "caveats": [
            "fe file is the SNB f0+f1 staircase at the max-tele probe cell, "
            "NOT the Ti-track cell used by the history columns (documented "
            "convention of the fe_fit series).",
            "Group grid starts at 0.1 eV: cold-start Maxwellians (Te ~ 0.02 "
            "eV) lie mostly below the grid — fe under-represents the core "
            "for t < ~0.1 ns.",
            "fe_content=total writes the FULL distribution; if the FLYCHK "
            "fe mode is strictly additive to the Maxwellian background, use "
            "--fe-content excess instead (beam = n1 only).",
            "n1_tot/ne spans 3e-5 .. ~3e4 (median 5e-3): the SNB |f1| "
            "directional excess is perturbative and unbounded (no particle-"
            "number constraint), so fe(E) strongly exceeds the Maxwellian "
            "core in the early nonlocal regime (t < ~0.5 ns). The pipeline's "
            "renormalized fe_snb (norm to ne) uses a different convention.",
            "175 time steps exceeds the FLYCHK website recommended limit "
            "(~50); thin if the submission is rejected.",
        ],
    }
    (OUT / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8", newline="\n")
    (OUT / "README.txt").write_text(
        "SNBVTi2um_hot — FLYCHK 输入 zip 对：19 群台阶 fe(E)（含 / 不含 fe）\n"
        "================================================================\n"
        f"含 fe: {zip_fe.name}\n"
        "  成员: runfile.txt(含 fe file fe_Ti_Z22_input.txt) + "
        "history_Ti_Z22_input.txt + fe_Ti_Z22_input.txt\n"
        f"不含 fe: {zip_none.name}\n"
        "  成员: runfile.txt + history_Ti_Z22_input.txt（与含版逐字节相同）\n\n"
        "history 列: time rho size te ti tr（fhot/thot 已移除, 非麦氏部分\n"
        "由 fe(E) 直接描述）。\n"
        "fe 文件: 175 个时间步 x 19 个能量点（群上边界 0.1 eV ~ 1e5 eV）,\n"
        f"fe(E_g) = ({'n0(E_g) + n1_g' if args.fe_content == 'total' else 'n1_g'})"
        "/sqrt(E_g), 密度列 = "
        f"{'ne + n1_tot' if args.fe_content == 'total' else 'n1_tot'}。\n"
        "绘图: plots/fig1_fe_group_evolution.png（台阶高度演化热图）,\n"
        "      plots/fig2_fe_stairs_keyframes.png（特征帧 stairs vs 连续参考）,\n"
        "      plots/fig3_contact_sheet_fe_stairs.png（175 帧总览）,\n"
        "      plots/fig4_history_none_preview.png（不含版 history 内容）。\n"
        "注意事项见 manifest.json 的 caveats。\n",
        encoding="utf-8", newline="\n")

    print(f"[fegroups] fe zip : {zip_fe}  ({zip_fe.stat().st_size} B)")
    print(f"[fegroups] none zip: {zip_none}  ({zip_none.stat().st_size} B)")
    print(f"[fegroups] integrity ok: fe={v_fe['ok']} none={v_none['ok']}")
    print(f"[fegroups] fe 校验: {fe.report.summary()}; "
          f"norm_dev median = {manifest['norm_deviation']['median']:.3g}")
    print(f"[fegroups] 总耗时 {_time.time() - t0:.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
