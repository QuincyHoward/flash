# -*- coding: utf-8 -*-
"""chk_io — FLASH chk 帧读取与派生量 (InterfaceEvolution core).

纪律 (flash/output_pro/FLASH物理量说明.md):
  ★ chk 含全部 AMR 块 (父块 node type 2/3), 必须只留叶块 node type == 1;
  ★ 逐格 x 由 bounding box 重建: x = x_lo + W·(i+0.5)/nxb (W 为逐块真实宽度);
  ★ nele = ye·ρ·N_A, nion = sumy·ρ·N_A, zbar = ye/sumy (§2.1/§2.2);
  ★ Γ_i = Z̄²e²/(a_i k_B T_i), Θ_e = k_B T_e/E_F — 调用 hdf5pro 同款实现 (§2.6);
  ★ tele/tion 原生单位 K → eV 除以 11604.518 (勿重复除);
  ★ pres/pele 原生 dyn/cm² → Mbar ×1e-12。
"""
from __future__ import annotations

import glob
from pathlib import Path

import h5py
import numpy as np

from flash.output_pro.hdf5pro import (
    NA,
    electron_degeneracy_parameter,
    ion_coupling_parameter,
)

NXB = 16                       # Flash.h 每块单元数
K2EV = 1.0 / 11604.518         # K → eV (铁律 §0.3-2)
CM2UM = 1.0e4
MBAR = 1.0e-12                 # dyn/cm² → Mbar


def list_chk(run_dir: Path):
    """chk 帧列表 (排除 *_forced_* / *_rst_* / *_prt_*)."""
    frames = []
    for p in sorted(glob.glob(str(Path(run_dir) / "lasslab_hdf5_chk_*"))):
        if any(tag in Path(p).name for tag in ("_forced_", "_rst_", "_prt_")):
            continue
        frames.append(Path(p))
    return frames


def read_frame(path):
    """读单帧 (叶块) → dict(单位: t[s], x[µm 升序], 其余见下)."""
    with h5py.File(path, "r") as f:
        rs = f["real scalars"][:]
        hdr = {n.decode().strip(): v for n, v in zip(rs["name"], rs["value"])}
        t = float(hdr["time"])
        leaf = f["node type"][:].ravel() == 1
        bbox = f["bounding box"][leaf, 0, :]

        def var(name):
            return f[name][leaf, 0, 0, :].astype(np.float64)

        dens = var("dens")
        ye = var("ye")
        sumy = var("sumy")
        tele = var("tele")
        tion = var("tion")
        trad = var("trad")
        pres = var("pres")
        pele = var("pele")
        shok = var("shok")
        targ = var("targ")

    w = bbox[:, 1] - bbox[:, 0]
    x = (bbox[:, 0][:, None] + w[:, None] * (np.arange(NXB) + 0.5) / NXB).ravel()
    order = np.argsort(x)
    x = x[order] * CM2UM                       # µm
    dx_cm = np.repeat(w / NXB, NXB)[order]     # 逐格宽度 [cm] (面质量积分用)
    dens = dens.ravel()[order]                 # g/cm³
    ye = ye.ravel()[order]
    sumy = sumy.ravel()[order]
    tele = tele.ravel()[order]                 # K
    tion = tion.ravel()[order]                 # K
    trad = trad.ravel()[order]                 # K
    pres = pres.ravel()[order]
    pele = pele.ravel()[order]
    shok = shok.ravel()[order]
    targ = targ.ravel()[order]

    with np.errstate(divide="ignore", invalid="ignore"):
        nele = ye * dens * NA                  # 1/cm³
        nion = sumy * dens * NA                # 1/cm³
        zbar = np.where(sumy > 0, ye / np.maximum(sumy, 1e-300), 0.0)
    gamma = ion_coupling_parameter(nion, tion, zbar)     # Γ_i (无量纲)
    theta = electron_degeneracy_parameter(nele, tele)    # Θ_e (无量纲)

    return dict(
        t=t, t_ns=t * 1e9, x=x, dx_cm=dx_cm,
        dens_gcc=dens, targ=targ, shok=shok,
        dens_targ=dens * targ,
        nele=nele, nion=nion, zbar=zbar,
        tele_eV=tele * K2EV, tion_eV=tion * K2EV, trad_eV=trad * K2EV,
        pres_Mbar=pres * MBAR, pele_Mbar=pele * MBAR,
        gamma=gamma, theta=theta,
    )
