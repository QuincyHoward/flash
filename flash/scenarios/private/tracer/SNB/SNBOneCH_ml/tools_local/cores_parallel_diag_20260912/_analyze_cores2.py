# -*- coding: utf-8 -*-
"""
_analyze_cores2.py — FLASH +ug chk 健康判据分析器（修正版）
==========================================================
★ 关键修正（相对第一版）:
  1. `coordinates` 是 **块中心 x (cm)**；块宽 W = dir_delta/nblocks（均匀），
     **W 不等于** nxb*dx（dx = x_hi-x_lo 是最近邻块中心距，而块之间存在边界点的
     重复计数），故不能用 x_block ± (nxb-1)/2*dx 重建 → 会外扩 ~2% 并使
     "argmax@x=0 / 质量恒定" 两项判据失效。
  2. +ug 下 refine level 全为 1（实测），所有块同宽 → 直接按块序拼接即得全局一致的
     单调 x 序列；x_lo = bbox[:,x,0], x_hi = bbox[:,x,1]（逐块真实边界）。
"""
import os, json, sys
from pathlib import Path
import numpy as np
import h5py

CP = Path(r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\scenarios\private\tracer\SNB\SNBOneCH_ml\flash_output\hpc_flash_ssh\cores_parallel")
OUT = CP.parent / "cores_parallel_health2.json"

NA = 6.02214076e23

def rs(h, key):
    for n, v in h[key][:]:
        if (n.decode().strip() if isinstance(n, bytes) else str(n)).strip() == "name":
            pass
    return None

def scalar_map(h):
    """返回 {'real scalars': {k:v}, 'integer scalars': {k:v}}"""
    out = {}
    for grp, dt in (("real scalars", float), ("integer scalars", int)):
        d = {}
        for n, v in h[grp][:]:
            k = n.decode().strip() if isinstance(n, bytes) else str(n).strip()
            d[k] = dt(v)
        out[grp] = d
    return out


def load_frame(path):
    with h5py.File(str(path), "r") as h:
        sm = scalar_map(h)
        bb = h["bounding box"][:]                    # (nb,3,2) cm
        x_lo = bb[:, 0, 0]
        x_hi = bb[:, 0, 1]
        W = x_hi - x_lo
        nxb = int(sm["integer scalars"]["nxb"])
        nb = int(sm["integer scalars"]["globalnumblocks"])

        def var(name):
            return h[name][:, 0, 0, :]               # (nb, nxb)

        dens = var("dens")
        tele = var("tele")
        temp = var("temp")
        eint = var("eint")
        ye = var("ye")
        sumy = var("sumy")
        nele = var("nele")
        velx = var("velx")

        # ★ 逐格 x: 块内均匀插值
        j = np.arange(nxb)
        t = (j + 0.5) / nxb
        xc = x_lo[:, None] + W[:, None] * t[None, :]   # (nb,nxb) cm

        # 逐格宽度（保证与块边界一致）
        wcell = (W / nxb)[:, None] * np.ones((1, nxb))
        wcell = np.repeat((W / nxb)[:, None], nxb, axis=1)

        # 质量面密度 M = Σ ρ_i * dx_i  [g/cm^2]  (1D 柱/平面: g/cm^2)
        M = float(np.sum(dens * wcell))

        # 展平为全局单调序列
        xf = xc.ravel() * 1e4                        # um
        order = np.argsort(xf)
        xf = xf[order]

        out = {
            "file": path.name,
            "time": sm["real scalars"]["time"],
            "dt": sm["real scalars"]["dt"],
            "nstep": int(sm["integer scalars"]["nstep"]),
            "iprocs": int(sm["integer scalars"]["iprocs"]),
            "nxb": nxb, "nblocks": nb, "ncells": nb * nxb,
            "xlo_um": float(x_lo.min() * 1e4),
            "xhi_um": float(x_hi.max() * 1e4),
            "x_contiguous": bool(np.all(np.abs(np.diff(xf) - np.diff(xf).mean()) < 1e-6)),
            "dens_max": float(dens.max()),
            "dens_min": float(dens.min()),
            "dens_argmax_x_um": float(xc.ravel()[np.argmax(dens)] * 1e4),
            "temp_max": float(temp.max()),
            "tele_max": float(tele.max()),
            "eint_min": float(eint.min()),
            "ye_max": float(ye.max()),
            "sumy_max": float(sumy.max()),
            "nele_max": float(nele.max()),
            "nion_max": float(sumy.max() * dens.max() * NA),
            "velx_absmax": float(np.abs(velx).max()),
            "mass_per_area": M,
            # 轻量数组供绘图用
            "_x": xf,
            "_dens": dens.ravel()[order],
            "_tele": tele.ravel()[order],
        }
        return out


def main():
    res = {}
    for nd in sorted(CP.iterdir(), key=lambda p: p.name):
        if not nd.is_dir():
            continue
        chks = sorted([p for p in nd.iterdir()
                       if p.name.startswith("snbonechug_hdf5_chk_") and p.suffix == ""])
        if not chks:
            continue
        frames = []
        for c in chks:
            try:
                frames.append(load_frame(c))
            except Exception as e:
                print(f"  [{nd.name}] {c.name}: SKIP ({type(e).__name__}: {e})")
        if frames:
            res[nd.name] = frames

    print("=" * 132)
    print(f"{'cores':>5} {'frm':>4} {'t[s]':>13} {'dt[s]':>11} {'nstep':>6} {'ncells':>7} "
          f"{'rho_max':>9} {'Temax[eV]':>10} {'tele_max':>11} {'nele_max':>10} {'|v|max':>10} "
          f"{'x(argmax)':>10} {'M[g/cm2]':>11}")
    print("-" * 132)
    for k, frs in res.items():
        n = k.lstrip("n")
        for fr in frs:
            print(f"{n:>5} {fr['file'][-4:]:>4} {fr['time']:>13.5e} {fr['dt']:>11.4e} "
                  f"{fr['nstep']:>6} {fr['ncells']:>7} {fr['dens_max']:>9.4f} {fr['temp_max']:>10.4e} "
                  f"{fr['tele_max']:>11.4e} {fr['nele_max']:>10.3e} {fr['velx_absmax']:>10.3e} "
                  f"{fr['dens_argmax_x_um']:>10.3f} {fr['mass_per_area']:>11.6e}")
        print("-" * 132)

    print("\n--- 健康判据（修正版）---")
    verdict = {}
    for k, frs in res.items():
        ts = np.array([f["time"] for f in frs])
        mono = bool(np.all(np.diff(ts) > 0))
        epos = all(f["eint_min"] > 0 for f in frs)
        xa = [f["dens_argmax_x_um"] for f in frs]
        ms = np.array([f["mass_per_area"] for f in frs])
        mdrift = float(np.abs(ms / ms[0] - 1).max())
        contig = all(f["x_contiguous"] for f in frs)
        nxb_ok = all(f["nxb"] == frs[0]["nxb"] for f in frs)
        v = {
            "frames": len(frs),
            "x_contiguous": contig,
            "nxb_consistent": nxb_ok,
            "t_monotonic": mono,
            "eint_min_positive": epos,
            "mass_rel_drift_max": mdrift,
            "mass_conserved_lt_1e-6": bool(mdrift < 1e-6),
            "dens_argmax_x_um_track": [round(v, 3) for v in xa],
        }
        verdict[k] = v
        print(f"{k}: frames={len(frs)} ncells={frs[0]['ncells']} nxb={frs[0]['nxb']} "
              f"blocks={frs[0]['nblocks']}  x范围=[{frs[0]['xlo_um']:.2f},{frs[0]['xhi_um']:.2f}]um")
        print(f"     x连续={contig}  nxb一致={nxb_ok}  t单调={mono}  eint_min>0={epos}")
        print(f"     质量相对漂移 max = {mdrift:.3e}  (<1e-6 ? {mdrift < 1e-6})")
        print(f"     dens 峰位 x 轨迹 (um) = {[round(v,1) for v in xa]}")

    # 保存（去掉大数组）
    slim = {k: [{kk: vv for kk, vv in f.items() if not kk.startswith("_")} for f in frs]
            for k, frs in res.items()}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"frames": slim, "verdict": verdict}, indent=2), encoding="utf-8")
    print(f"\n-> {OUT}")

    # 供绘图使用
    np.savez_compressed(CP.parent / "cores_parallel_profiles.npz",
                        **{f"{k}__{i}__{a}": f[a]
                           for k, frs in res.items() for i, f in enumerate(frs)
                           for a in ("_x", "_dens", "_tele")})
    print(f"-> {CP.parent / 'cores_parallel_profiles.npz'}")


if __name__ == "__main__":
    main()
