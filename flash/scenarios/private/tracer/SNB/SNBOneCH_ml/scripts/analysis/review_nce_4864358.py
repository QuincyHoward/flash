"""NC-E job 4864358 短时测试物理质量审查 (tmax=2e-10 s, 131 核 +ug)。

数据: flash_output/hpc_flash_ssh/ 下 chk_0012..0023 (10.1 MB each, 16768 格)。

体检项:
  A. 帧清单 / 尺寸 / nxb / 域范围 (防陈旧或半截文件)
  B. 逐帧 t / dt -> 判断 dt 是否被钳位 (dt 实测值才是权威)
  C. rho_max 演化 + 单帧相对跌幅 (异常判据 |.| > 0.30)
  D. 前沿位置: 密度阈值法 + 临界密度面 (n_c = 9.05e21 cm^-3)
  E. 8 层 (species) 的空间跨度 -> 确认几何与分层完好
  F. 极值: tele / |v| / pres

★ 绘图: 全英文, 字号 > 18 pt, DPI >= 450。
★ 所有取数一律经 chk_io (record-array 与逐格坐标的正确处理)。
"""
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import chk_io  # noqa: E402

D = os.path.dirname(os.path.abspath(__file__))
SCENE = os.path.abspath(os.path.join(D, "..", ".."))
HPC = os.path.join(SCENE, "flash_output", "hpc_flash_ssh")
OUTDIR = os.path.join(SCENE, "docs_diag", "nce_4864358_review")
os.makedirs(OUTDIR, exist_ok=True)

LAYERS = ["shld", "tar1", "tar2", "tar3", "tar4", "tar6"]
N_C = 9.05e21          # 临界密度 cm^-3


def um(x):
    return x * 1e4 if x is not None else None


def main():
    chks = sorted([f for f in os.listdir(HPC)
                   if "_chk_" in f and not f.endswith(".part")])
    print("=" * 88)
    print("NC-E 4864358 物理质量审查    帧数 =", len(chks))
    print("=" * 88)
    if not chks:
        return 1

    # A
    print("\n[A] 帧清单 / 尺寸 / nxb / 域范围")
    sizes = {c: os.path.getsize(os.path.join(HPC, c)) for c in chks}
    uniq = sorted(set(sizes.values()))
    print("    尺寸档位:", uniq)
    full = [c for c in chks if sizes[c] == max(uniq)]
    print("    完整帧 %d / 总 %d" % (len(full), len(chks)))

    rows, frames = [], {}
    for c in full:
        d = chk_io.frame(os.path.join(HPC, c))
        frames[c] = d
        x = d["x"]
        dm = d["dens"]
        if x is None or dm is None or x.size != dm.size:
            print("    [!] 跳过 (坐标/密度维度不符):", c)
            continue
        x, dm = chk_io.sort_by_x(x, dm)

        dmax = float(np.max(dm))
        above = np.where(dm > 0.5 * dmax)[0]
        x_lo = x[above[0]] if above.size else np.nan
        x_hi = x[above[-1]] if above.size else np.nan

        x_nc = np.nan
        ne = d["nele"]
        if ne is not None and ne.size == dm.size:
            ne = ne[np.argsort(d["x"])]
            aa = np.where(ne >= N_C)[0]
            if aa.size:
                x_nc = x[aa[-1]]

        # 各层空间跨度 (用质量分数相对阈值, 避开 1e-99 地板)
        spans = {}
        for s in LAYERS + ["cham", "samp"]:
            v = d[s]
            if v is None or v.size != dm.size:
                spans[s] = (np.nan, np.nan, 0)
                continue
            v = v[np.argsort(d["x"])]
            m = v > max(1e-6 * float(np.max(v)), 1e-30)
            if m.any():
                spans[s] = (x[m][0], x[m][-1], int(m.sum()))
            else:
                spans[s] = (np.nan, np.nan, 0)

        rows.append(dict(
            name=c, t=d["t"], dt=d["dt"], nxb=d["nxb"],
            x_min=float(x.min()), x_max=float(x.max()),
            rho_max=dmax, x_lo=x_lo, x_hi=x_hi, x_nc=x_nc, spans=spans,
            tm=float(np.nanmax(d["tele"])) if d["tele"] is not None else np.nan,
            vm=float(np.nanmax(np.abs(d["velx"])))
            if d["velx"] is not None else np.nan,
            pm=float(np.nanmax(d["pres"])) if d["pres"] is not None
            else np.nan,
            setup=d.get("setup_call", "")[:90]))

    if not rows:
        print("无可用帧")
        return 1
    print("    nxb=%s  域 x=[%.2f, %.2f] um  格数=%d"
          % (rows[0]["nxb"], um(rows[0]["x_min"]), um(rows[0]["x_max"]),
             int(rows[0]["nxb"]) * 131))
    print("    setup:", rows[0]["setup"])

    # B/C
    print("\n[B/C] 逐帧 时间 / dt / rho_max / 单帧相对跌幅")
    print("  %-6s %14s %14s %12s %12s" %
          ("frame", "t [s]", "dt [s]", "rho_max", "d(rho)/rho"))
    prev, worst = None, 0.0
    for r in rows:
        s = "-"
        if prev is not None and prev["rho_max"] > 0:
            rel = (r["rho_max"] - prev["rho_max"]) / prev["rho_max"]
            s = "%+.4f" % rel
            if abs(rel) > abs(worst):
                worst = rel
        print("  %-6s %14.6e %14.6e %12.4e %12s" %
              (r["name"][-4:], r["t"], r["dt"], r["rho_max"], s))
        prev = r
    print("    单帧最大相对变化 = %+.4f    (异常判据: |.| > 0.30)" % worst)
    dt0, dtN = rows[0]["dt"], rows[-1]["dt"]
    print("    dt: %.4e -> %.4e  (增长 %.2fx; 若全程=dtmax 则说明被钳位)"
          % (dt0, dtN, dtN / dt0 if dt0 else float("nan")))

    # D
    print("\n[D] 前沿位置 [um]  (密度阈值 0.5*rho_max; n_c = 9.05e21)")
    print("  %-6s %14s %14s %14s" % ("frame", "x_lo", "x_hi", "x(n_c)"))
    for r in rows:
        xnc = ("%.4f" % um(r["x_nc"])) if not np.isnan(r["x_nc"]) else "n/a"
        print("  %-6s %14.4f %14.4f %14s" %
              (r["name"][-4:], um(r["x_lo"]), um(r["x_hi"]), xnc))

    # E
    print("\n[E] 各层空间跨度 [um] (质量分数 > 1e-6*max 的区间)")
    print("  %-6s" % "frame" + "".join("%18s" % s for s in LAYERS))
    for r in rows:
        cells = ""
        for s in LAYERS:
            a, b, n = r["spans"][s]
            cells += "%18s" % ("%.3f~%.3f" % (um(a), um(b))
                               if n else "gone")
        print("  %-6s" % r["name"][-4:] + cells)

    print("\n[E2] cham/samp 跨度 [um]")
    print("  %-6s %18s %18s" % ("frame", "cham", "samp"))
    for r in rows:
        def f2(s):
            a, b, n = r["spans"][s]
            return "%.2f~%.2f" % (um(a), um(b)) if n else "gone"
        print("  %-6s %18s %18s" % (r["name"][-4:], f2("cham"), f2("samp")))

    # F
    print("\n[F] 极值")
    print("  %-6s %14s %16s %14s" %
          ("frame", "tele_max[K]", "|v|_max[cm/s]", "pres_max"))
    for r in rows:
        print("  %-6s %14.4e %16.4e %14.4e" %
              (r["name"][-4:], r["tm"], r["vm"], r["pm"]))

    # ── 绘图 ──
    t_ns = np.array([r["t"] for r in rows]) * 1e9
    fig, ax = plt.subplots(2, 1, figsize=(11, 11))
    ax[0].plot(t_ns, [r["rho_max"] for r in rows], "o-", lw=2.6, ms=9,
               color="#c0392b")
    ax[0].set_xlabel("Time [ns]", fontsize=22)
    ax[0].set_ylabel("Peak Density [g/cm$^3$]", fontsize=22)
    ax[0].set_title("NC-E Job 4864358: Peak Density Evolution",
                    fontsize=24, fontweight="bold")
    ax[0].tick_params(labelsize=20)
    ax[0].grid(alpha=0.35)
    ax[1].semilogy(t_ns, [r["dt"] for r in rows], "s-", lw=2.6, ms=9,
                   color="#2980b9")
    ax[1].set_xlabel("Time [ns]", fontsize=22)
    ax[1].set_ylabel("Time Step dt [s]", fontsize=22)
    ax[1].set_title("Time Step Evolution", fontsize=24, fontweight="bold")
    ax[1].tick_params(labelsize=20)
    ax[1].grid(alpha=0.35, which="both")
    fig.tight_layout()
    p1 = os.path.join(OUTDIR, "nce_rho_dt_evolution.png")
    fig.savefig(p1, dpi=450)
    plt.close(fig)
    print("\n图1:", p1)

    # 末帧剖面
    last = rows[-1]["name"]
    d = frames[last]
    x, dm, te, ne = chk_io.sort_by_x(d["x"], d["dens"], d["tele"],
                                     d["nele"])
    fig, ax = plt.subplots(3, 1, figsize=(13, 15))
    ax[0].semilogy(um(x), dm, "-", lw=2.6, color="#c0392b")
    ax[0].set_ylabel("Density [g/cm$^3$]", fontsize=22)
    ax[0].set_title("Final Frame (%s): Density" % last[-4:], fontsize=24,
                    fontweight="bold")
    ax[0].tick_params(labelsize=20)
    ax[0].grid(alpha=0.35, which="both")
    if te is not None:
        ax[1].semilogy(um(x), te, "-", lw=2.6, color="#27ae60")
        ax[1].set_ylabel("Te [K]", fontsize=22)
        ax[1].set_title("Electron Temperature", fontsize=24,
                        fontweight="bold")
        ax[1].tick_params(labelsize=20)
        ax[1].grid(alpha=0.35, which="both")
    if ne is not None:
        ax[2].semilogy(um(x), np.maximum(ne, 1e1), "-", lw=2.6,
                       color="#8e44ad")
        ax[2].axhline(N_C, color="k", ls="--", lw=2.4,
                      label="n$_c$ = 9.05e21")
        ax[2].set_xlabel("Position [um]", fontsize=22)
        ax[2].set_ylabel("n$_e$ [cm$^{-3}$]", fontsize=22)
        ax[2].set_title("Electron Density (critical surface marked)",
                        fontsize=24, fontweight="bold")
        ax[2].tick_params(labelsize=20)
        ax[2].legend(fontsize=18)
        ax[2].grid(alpha=0.35, which="both")
    fig.tight_layout()
    p2 = os.path.join(OUTDIR, "nce_final_profile.png")
    fig.savefig(p2, dpi=450)
    plt.close(fig)
    print("图2:", p2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
