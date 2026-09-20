# -*- coding: utf-8 -*-
"""
_make_plot.py — 核数伸缩性能图（PPT 演讲级：全英文、字号>18pt、DPI>=450、粗线）
"""
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = Path(r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\scenarios\private\tracer\SNB\SNBOneCH_ml\flash_output\hpc_flash_ssh\cores_parallel")
CP = OUT

# ---- 权威数据 ----
cores   = np.array([131, 192, 256])
sps     = np.array([0.2878, 0.4698, 0.3508])     # s/step (纯积分)
sps_neg = np.array([0.2961, 0.5620, 0.3510])     # 早期估算（含 build 摊薄）
tend    = np.array([1.23550e-10, 1.04640e-10, 9.46600e-11])
dtend   = np.array([1.3313e-14, 1.7459e-14, 1.000e-16])
nstep   = np.array([1997, 1200, 980])
cells   = np.array([16768, 24576, 32768])
dx      = np.array([0.0298187, 0.0203451, 0.0152588])   # um
status  = ["CANCELLED\n(healthy)", "CANCELLED\n(healthy)", "ABORT\n(Neg 3T eint)"]

plt.rcParams.update({
    "font.size": 20, "axes.titlesize": 26, "axes.labelsize": 22,
    "xtick.labelsize": 20, "ytick.labelsize": 20, "legend.fontsize": 18,
    "figure.dpi": 100, "savefig.dpi": 450,
    "axes.linewidth": 2.0, "lines.linewidth": 2.6, "lines.markersize": 12,
})

fig, ax = plt.subplots(2, 3, figsize=(24, 14))

# (0,0) s/step vs cores
a = ax[0, 0]
a.plot(cores, sps, "o-", color="#c0392b", label="Pure integration")
a.plot(cores, sps_neg, "s--", color="#7f8c8d", alpha=.7, label="Incl. build amortized")
for x, y in zip(cores, sps):
    a.annotate(f"{y:.3f}", (x, y), textcoords="offset points", xytext=(0, 14),
               ha="center", fontsize=19, fontweight="bold")
a.set_xlabel("MPI process count (cores)")
a.set_ylabel("Wall clock per timestep [s]")
a.set_title("Per-step Cost vs Core Count")
a.set_xticks(cores)
a.grid(alpha=.3, lw=1.2)
a.legend(loc="upper center")

# (0,1) 物理时间推进量
a = ax[0, 1]
bars = a.bar([str(c) for c in cores], tend * 1e10,
             color=["#27ae60", "#e67e22", "#c0392b"], edgecolor="k", lw=2)
for b, v, s in zip(bars, tend * 1e10, status):
    a.text(b.get_x() + b.get_width()/2, v + 0.08, f"{v:.3f}e-10 s\n{s}",
           ha="center", va="bottom", fontsize=18, fontweight="bold")
a.axhline(2.0, color="#2980b9", ls="--", lw=2.5)
a.text(2.42, 2.03, "tmax = 2.0e-10 s", color="#2980b9", ha="right", fontsize=19, fontweight="bold")
a.set_xlabel("MPI process count (cores)")
a.set_ylabel(r"Physical time reached [$\times 10^{-10}$ s]")
a.set_title("Physical Time Advanced")
a.set_ylim(0, 2.5)
a.grid(alpha=.3, lw=1.2, axis="y")

# (0,2) dt vs step (all legs)
a = ax[0, 2]
COL = {"131": "#27ae60", "192": "#e67e22", "256": "#c0392b"}
for n, c in COL.items():
    fr = np.load(CP.parent / "cores_parallel_profiles.npz") if False else None
    pass
# 用日志重建 dt(step)
import re
for n, c in COL.items():
    lg = CP / f"n{n}" / f"wsl_run_{n}.log"
    st, dt = [], []
    for l in lg.read_text(errors="replace").splitlines():
        if "|" not in l:
            continue
        lf = l.split("|")[0].split()
        if len(lf) < 3:
            continue
        try:
            st.append(int(lf[0])); dt.append(float(lf[2]))
        except ValueError:
            continue
    a.semilogy(st, dt, "-", color=c, lw=2.4, label=f"n{n}")
a.axhline(2.0e-12, color="k", ls=":", lw=2.2)
a.text(1500, 2.4e-12, r"dtmax = 2e-12", fontsize=18)
a.set_xlabel("Timestep number")
a.set_ylabel("dt [s]")
a.set_title("Timestep Evolution (CFL-limited)")
a.grid(alpha=.3, lw=1.2, which="both")
a.legend(loc="lower right")

# (1,0) dx per core
a = ax[1, 0]
bars = a.bar([str(c) for c in cores], dx,
             color=["#27ae60", "#e67e22", "#c0392b"], edgecolor="k", lw=2)
for b, v in zip(bars, dx):
    a.text(b.get_x() + b.get_width()/2, v + 0.0005, f"{v:.5f}\nµm",
           ha="center", va="bottom", fontsize=18, fontweight="bold")
a.axhline(0.03, color="#2980b9", ls="--", lw=2.5)
a.text(2.42, 0.0303, "required ≤ 0.03 µm", color="#2980b9", ha="right",
       fontsize=19, fontweight="bold")
a.set_xlabel("MPI process count (cores)")
a.set_ylabel(r"Cell size dx [$\mu$m]")
a.set_title(r"Resolution (+ug minimum cell, 0.1 $\mu$m layer)")
a.set_ylim(0, 0.038)
a.grid(alpha=.3, lw=1.2, axis="y")

# (1,1) 到 tmax 的剩余小时
a = ax[1, 1]
hrs = np.array([0.46, 0.71, 102.66])
bars = a.bar([str(c) for c in cores], hrs,
             color=["#27ae60", "#e67e22", "#c0392b"], edgecolor="k", lw=2)
for b, v in zip(bars, hrs):
    a.text(b.get_x() + b.get_width()/2, v * 1.15, f"{v:.2f} h",
           ha="center", va="bottom", fontsize=19, fontweight="bold")
a.set_yscale("log")
a.set_xlabel("MPI process count (cores)")
a.set_ylabel("Est. hours to tmax = 2e-10 s")
a.set_title("Remaining Cost to tmax")
a.set_ylim(0.2, 400)
a.grid(alpha=.3, lw=1.2, which="both", axis="y")

# (1,2) 综合评分表
a = ax[1, 2]
a.axis("off")
tbl = [
    ["Metric", "131 cores", "192 cores", "256 cores"],
    ["s/step (pure)", "0.288", "0.470", "0.351"],
    ["nsteps in 10 min", "1997", "1200", "980"],
    ["dt_end [s]", "1.33e-14", "1.75e-14", "1.00e-16"],
    ["t reached", "1.236e-10", "1.046e-10", "9.47e-11"],
    ["dx [µm]", "0.02982", "0.02035", "0.01526"],
    ["dx ≤ 0.03 µm ?", "YES (edge)", "YES", "YES"],
    ["Health", "OK", "OK", "ABORT"],
    ["Verdict", "BEST", "2nd", "REJECT"],
]
t = a.table(cellText=tbl[1:], colLabels=tbl[0], loc="center", cellLoc="center")
t.auto_set_font_size(False)
t.set_fontsize(17)
t.scale(1, 2.3)
for (r, c), cell in t.get_celld().items():
    cell.set_linewidth(1.6)
    if r == 0:
        cell.set_facecolor("#34495e"); cell.set_text_props(color="w", fontweight="bold")
    elif c == 0:
        cell.set_facecolor("#ecf0f1"); cell.set_text_props(fontweight="bold")
    elif tbl[r][c] in ("BEST", "OK", "YES (edge)", "YES"):
        cell.set_facecolor("#d5f5e3")
    elif tbl[r][c] in ("ABORT", "REJECT") :
        cell.set_facecolor("#fadbd8")
a.set_title("Core-count Verdict Summary", fontsize=25, pad=22)

fig.suptitle("FLASH SNBOneCH_ml — NC-E Core-Count Scaling Test\n"
             r"domain 500 $\mu$m, nxb=128, +ug, tmax=2e-10 s, 3 parallel sbatch jobs",
             fontsize=27, fontweight="bold", y=0.985)
fig.tight_layout(rect=[0, 0, 1, 0.945])
p1 = OUT.parent / "cores_scaling_nce.png"
fig.savefig(p1, bbox_inches="tight", facecolor="white")
print("->", p1)
plt.close(fig)

# ---- 第二张: 物理剖面 ----
z = np.load(CP.parent / "cores_parallel_profiles.npz")
fig2, ax2 = plt.subplots(1, 2, figsize=(20, 8))
for n, c in COL.items():
    ks = sorted([k for k in z.files if k.startswith(f"n{n}__") and k.endswith("__dens")])
    if not ks:
        continue
    k = ks[-1]
    i = k.split("__")[1]
    x = z[f"n{n}__{i}___x"]; d = z[f"n{n}__{i}___dens"]; T = z[f"n{n}__{i}___tele"]
    ax2[0].plot(x, d, "-", color=c, lw=2.4, label=f"n{n} (frame {i})")
    ax2[1].semilogy(x, T, "-", color=c, lw=2.4, label=f"n{n} (frame {i})")
ax2[0].set_xlabel(r"x [$\mu$m]"); ax2[0].set_ylabel(r"Mass density [g/cm$^3$]")
ax2[0].set_title("Final-frame Density Profile"); ax2[0].grid(alpha=.3, lw=1.2)
ax2[0].legend(); ax2[0].set_xlim(-420, 120)
ax2[1].set_xlabel(r"x [$\mu$m]"); ax2[1].set_ylabel(r"$T_e$ [eV]")
ax2[1].set_title(r"Final-frame Electron Temperature"); ax2[1].grid(alpha=.3, lw=1.2, which="both")
ax2[1].legend(); ax2[1].set_xlim(-420, 120)
fig2.suptitle("SNBOneCH_ml — Last Frame Profiles by Core Count (NC-E)", fontsize=25, fontweight="bold")
fig2.tight_layout(rect=[0, 0, 1, 0.94])
p2 = OUT.parent / "cores_profiles_nce.png"
fig2.savefig(p2, bbox_inches="tight", facecolor="white")
print("->", p2)
plt.close(fig2)
