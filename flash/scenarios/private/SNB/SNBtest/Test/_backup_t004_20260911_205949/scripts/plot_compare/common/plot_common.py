"""t004 绘图对比 —— 共享层 (数据加载 / 单位换算 / 绘图规范)

本模块是 t004 所有**绘图脚本**的唯一公共依赖, 不产生任何图像文件。

数据源策略 (2026-09-10 用户指定)
--------------------------------
**绘图一律读 chk 文件, 不使用 plt。**

| 维度        | chk                                   | plt                        |
|-------------|---------------------------------------|----------------------------|
| 键数        | 71 (实测, 512 格 FL-SH 腿)            | ~25                        |
| 变量上限    | 无 (完整重启快照, 全部 UNK + 标量)    | plot_var 白名单硬上限 12   |
| dtype       | float64                               | float32                    |
| 覆盖量      | 含 pion/eele/ye/sumy/gamc/game/qenl/mfpe | 仅白名单项              |

chk 与 plt 的**布局完全相同**, 均为 `+ug` 一块一进程的扁平结构:

    coordinates  (nblocks, 3)          ← 每块**块中心**坐标, 非节点坐标
    block size   (nblocks, 3)          ← 每块边长
    bounding box (nblocks, 3, 2)       ← 每块 [lo, hi] 包围盒
    <var>        (nblocks, 1, 1, nxb)  ← 每块沿 x 的 nxb 个格点值
    node type    (nblocks,) int32      ← **标量/块** (chk 与 plt 均如此)

★ 关键事实: `+ug` 均匀网格下**所有块都是叶子块** (node type = 1),
  因此**无需** leaf 过滤 —— 这一点与 AMR 场景 (SNBOneCH_ml) 根本不同,
  直接按 gid 排序拼接即可, 与 yt/h5py 提取模式天然一致。

网格构造 (精确复原 FLASH 节点坐标)
----------------------------------
FLASH 存的是**块中心**, 重建节点坐标需从 bounding box 推:

    x_lo_block = bounding_box[b, 0, 0]
    x_hi_block = bounding_box[b, 0, 1]
    x_nodes    = linspace(x_lo_block, x_hi_block, nxb + 1)
    x_centers  = 0.5 * (x_nodes[:-1] + x_nodes[1:])

因 `+ug` 均匀网格邻块共享界面节点, 拼接时对**每块取左闭右开**即可避免重复。

单位换算 (FLASH 原生 = CGS)
---------------------------
| 目标量      | 单位     | 来源                              | 换算                                  |
|-------------|----------|-----------------------------------|---------------------------------------|
| tele        | eV       | tele [K]                          | / K_PER_EV                            |
| tion        | eV       | tion [K]                          | / K_PER_EV                            |
| trad        | eV       | trad [K]                          | / K_PER_EV                            |
| dens        | g/cm^3   | dens [g/cm^3]                     | 原样                                  |
| pele        | Mbar     | pele [erg/cm^3]                   | * ERG_CM3_TO_MBAR                     |
| pres        | Mbar     | pres [erg/cm^3]                   | * ERG_CM3_TO_MBAR                     |
| nele        | cm^-3    | Ye * 6.02e23 * dens (离线推导)    | 见 electron_number_density()          |

nele 推导依据 (源码级)
---------------------
FLASH 的 `Eos_getAbarZbar` 在 FLASH_MULTISPECIES 路径下 (Eos_getAbarZbar.F90:130-152):

    abarInv  = SumInv(A)  = Σ_s X_s / A_s
    zbarFrac = SumFrac(Z) = Σ_s X_s · Z_s / A_s
    abar     = 1 / abarInv
    zbar     = abar · zbarFrac
    Ye       = zbar / abar = zbarFrac / abarInv

SNB 源码 (diff_advanceTherm.F90:432-433) 给出电子数密度的权威定义:

    nele = Ye * 6.02e23 * dens

其中 X_s 是物种质量分数 (chk 里的 `cham` / `tar1` / `tar2` / `tar3`)。本模块对该式做
**离线复现**, 两腿口径完全一致。理由是 t004 的特殊情形:

  t004 两腿共用同一份 Config (含作者声明的 `NELE` VARIABLE), 因此 chk 里两腿
  **都有** `nele` 字段 —— 但只有 SNB 腿的 `diff_advanceTherm.F90` 会写它;
  FL-SH 腿用标准树原生实现, 该字段**从不更新**, 是启动初值/陈旧值。
  → 若直接用原生 `nele`, 两腿口径将严重不对称; 离线推导对两腿完全同源。

绘图规范 (用户要求 + 项目规约)
-----------------------------
全英文标签、字号 >= 18 pt、DPI >= 450、线宽 >= 2。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

# ── t004 common 层 (参数唯一来源) ─────────────────────────────
_T004 = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_T004 / "common"))

import t004_common as C  # noqa: E402

import numpy as np                      # noqa: E402
import matplotlib                       # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt         # noqa: E402

# 仓库根 (pyproject.toml 锚点) 已由 t004_common 注入 sys.path
import h5py                             # noqa: E402

# ══════════════════════════════════════════════════════════════
# 单位换算常数
# ══════════════════════════════════════════════════════════════
K_PER_EV = 1.1604519e4        # 1 eV = 11604.519 K  (k_B/e)
ERG_CM3_TO_MBAR = 1.0e-12     # 1 Mbar = 1e12 erg/cm^3 = 1e11 Pa
CM_TO_UM = 1.0e4              # 1 cm = 1e4 µm
NS_PER_S = 1.0e9              # 1 s = 1e9 ns
NA_APPROX = 6.02e23           # FLASH 源码硬编码值 (diff_advanceTherm.F90:432)

# 物种 A / Z (权威来源: t004_common.PARAMS)
# ★ t004 为示例的 4 物种体系: cham(He) 腔体 + tar1/tar2/tar3(CH 靶与示踪层)。
#   tar1/tar2/tar3 三者组分相同 (A=6.5, Z=3.5), 仅承载示踪层区分。
SPECIES_A_Z: Dict[str, Tuple[float, float]] = {
    sp: (C.PARAMS[sp]["A"], C.PARAMS[sp]["Z"])
    for sp in ("cham", "tar1", "tar2", "tar3")
    if sp in C.PARAMS
}

# 两腿配色 / 标签
COLORS = {"flsh": "tab:blue", "snb": "tab:red"}
LABELS = {"flsh": "FL-SH (flux-limited, local)", "snb": "SNB (nonlocal, multigroup)"}
SHORT_LABELS = {"flsh": "FL-SH", "snb": "SNB"}

# ── 绘图规范 (全英文 / >=18pt / 高 DPI / 粗线) ────────────────
plt.rcParams.update({
    "font.size": 20, "axes.titlesize": 24, "axes.labelsize": 22,
    "xtick.labelsize": 20, "ytick.labelsize": 20, "legend.fontsize": 18,
    "axes.linewidth": 2.0, "xtick.major.width": 2.0, "ytick.major.width": 2.0,
    "lines.linewidth": 2.4, "font.family": "DejaVu Sans",
    "figure.max_open_warning": 0,
})
DPI = 450


# ══════════════════════════════════════════════════════════════
# 物理量定义表 (绘图需求驱动)
# ══════════════════════════════════════════════════════════════
# 每项: key -> 显示名 / 单位 / 颜色映射 / 是否对数色标 / 标题
#   cmap 选择理由: "inferno" 感知均匀且在两端均有高对比 → 适合跨 6 个数量级的
#   温度场; "viridis" 同理适合密度/压力/数密度。
QUANTITIES: Dict[str, Dict[str, Any]] = {
    "tele": {"label": r"$T_e$", "unit": "eV", "cmap": "inferno",
             "log": False, "title": r"Electron temperature"},
    "tion": {"label": r"$T_i$", "unit": "eV", "cmap": "inferno",
             "log": False, "title": r"Ion temperature"},
    "trad": {"label": r"$T_r$", "unit": "eV", "cmap": "inferno",
             "log": False, "title": r"Radiation temperature"},
    "dens": {"label": r"$\rho$", "unit": r"g/cm$^3$", "cmap": "viridis",
             "log": False, "title": r"Mass density"},
    "pele": {"label": r"$P_e$", "unit": "Mbar", "cmap": "viridis",
             "log": False, "title": r"Electron pressure"},
    "pres": {"label": r"$P$", "unit": "Mbar", "cmap": "viridis",
             "log": False, "title": r"Total pressure"},
    "nele": {"label": r"$n_e$", "unit": r"cm$^{-3}$", "cmap": "viridis",
             "log": True, "title": r"Electron number density"},
}

# 图像内插值方式 / 色标扩展 (默认值, 可被调用方覆盖)
DEFAULT_SHADING = "nearest"

# ★ 色标共享判据 (重要物理陷阱)
# ---------------------------------
# 默认两联**共享**色标 (对比的前提)。但当两腿量值相差若干数量级时共享色标会让
# 弱的一腿全糊成一个颜色, 完全看不出结构 —— 实测案例: `trad` 在 FL-SH 腿
# erad ~1e12 erg/cm^3, 而 SNB 腿 ~1e-5 erg/cm^3 (辐射在 SNB 腿基本解耦),
# 共享色标下 SNB 联全黑, 信息量为零。
# 因此提供 --per-leg 模式: 每联独立自动定标, 并在 title 上显式标注 (independent scale)。
SCALE_SHARE_DECADES = 66.0     # 两腿动态范围中心相差 > 此值(以 10^d 计) 则提示分scale


# ══════════════════════════════════════════════════════════════
# 帧发现
# ══════════════════════════════════════════════════════════════
_CHK_RE = re.compile(r"hdf5_chk_(\d+)$")


def list_chk(outdir: Path) -> List[Path]:
    """列出目录下全部 chk 帧, 按**帧号数值**升序 (而非字典序)。

    ★ 不能用 sorted() 直接排字符串: `_chk_0010` < `_chk_0009` 在字典序下为假,
      但 `_chk_0100` vs `_chk_0099` 之类跨位数仍会错。一律按解析出的整数排。
    """
    out: List[Tuple[int, Path]] = []
    for p in outdir.iterdir() if outdir.is_dir() else []:
        m = _CHK_RE.search(p.name)
        if m:
            out.append((int(m.group(1)), p))
    out.sort(key=lambda r: r[0])
    return [p for _, p in out]


def list_plt(outdir: Path) -> List[Path]:
    """列出 plt 帧 (排除 forced; 无普通帧则回退包含 forced)。仅作健全性检查用。"""
    files = [p for p in sorted(outdir.glob("*hdf5_plt_cnt_*"))
             if "forced" not in p.name]
    return files or sorted(outdir.glob("*hdf5_plt_cnt_*"))


# ══════════════════════════════════════════════════════════════
# 帧读取 (chk/plt 通用, 直读 HDF5 — 不走 FlashDataLoader)
# ══════════════════════════════════════════════════════════════
def _real_scalars(h: h5py.File) -> Dict[str, float]:
    """读 `real scalars` → {name: value}。"""
    out: Dict[str, float] = {}
    if "real scalars" not in h:
        return out
    names = h["real scalars"]["name"][:]
    vals = h["real scalars"]["value"][:]
    for n, v in zip(names, vals):
        key = n.decode() if isinstance(n, (bytes, bytearray)) else str(n)
        out[key.strip()] = float(v)
    return out


def _unknown_names(h: h5py.File) -> List[str]:
    """读 `unknown names` → 变量名列表 (FLASH 权威的 UNK 顺序表)。"""
    if "unknown names" not in h:
        return []
    raw = h["unknown names"][:]
    out: List[str] = []
    for item in raw:
        if isinstance(item, (bytes, bytearray)):
            out.append(item.decode().strip())
        elif isinstance(item, np.ndarray):
            out.append(item.ravel()[0].decode().strip())
        else:
            out.append(str(item).strip())
    return [n for n in out if n]


def load_frame(path: Path, variables: Optional[Iterable[str]] = None
               ) -> Optional[Dict[str, Any]]:
    """读单帧 (chk 或 plt) → {t, x_um, <变量名小写>: ndarray, ...}。

    返回键
    ------
    t        : float   仿真时刻 [s]      (取自 real scalars["time"])
    x_um     : ndarray 节点单元中心 x [µm], 已按空间升序
    <var>    : ndarray 各变量在 x_um 上的值 (原生 CGS)
    _path    : Path    源文件
    _nblocks : int     块数
    _vars    : list    本帧含有的全部变量名 (小写)

    Args:
        variables: 若给定, 只读取这些变量 (省 IO); None = 全部读。

    ★ 两腿变量不对称的处理: FL-SH 腿无 `nele`/`qenl` 等 SNB 专有量, 缺失的键
      直接不放入返回字典 —— 调用方须用 `var in frame` 判定, 或用 has_var()。
    """
    path = Path(path)
    try:
        with h5py.File(str(path), "r") as h:
            rs = _real_scalars(h)
            t = rs.get("time", float("nan"))

            if "coordinates" not in h:
                C.log(f"    无 coordinates: {path.name}", "WARN")
                return None
            coords = np.asarray(h["coordinates"][:], dtype=float)   # (nb, 3)

            # ── 块排序: 按块中心 x 升序 (+ug 下等价于 gid 顺序, 已实测) ──
            order = np.argsort(coords[:, 0], kind="stable")

            # ── 逐块重建节点坐标 ────────────────────────────────
            if "bounding box" in h:
                bb = np.asarray(h["bounding box"][:], dtype=float)   # (nb, 3, 2)
                b_lo, b_hi = bb[:, 0, 0], bb[:, 0, 1]
            else:                                   # 退化路径: 用 coordinates 推
                b_lo, b_hi = coords[:, 0], coords[:, 0]

            names = _unknown_names(h)
            if variables is not None:
                want = {v.lower() for v in variables}
                names = [n for n in names if n.lower() in want]

            # 先探明每块沿 x 的格点数 (取第一个变量)
            probe = None
            for nm in names:
                if nm in h:
                    probe = np.asarray(h[nm].shape)
                    break
            if probe is None or probe.size < 4:
                C.log(f"    无法确定块内格点数: {path.name}", "WARN")
                return None
            nxb = int(probe[-1])

            xs: List[np.ndarray] = []
            for b in order:
                xs.append(np.linspace(b_lo[b], b_hi[b], nxb + 1)[:-1])
            x_nodes = np.concatenate(xs)                       # 每块左闭右开
            dx = (b_hi[order[0]] - b_lo[order[0]]) / nxb
            x_um = (x_nodes + 0.5 * dx) * CM_TO_UM             # 块中心 → µm

            frame: Dict[str, Any] = {
                "t": float(t), "x_um": x_um,
                "_path": path, "_nblocks": int(coords.shape[0]),
                "_vars": [n.lower() for n in _unknown_names(h)],
                "_dx_um": float(dx * CM_TO_UM),
                "_t_end": t,
            }

            for nm in names:
                if nm not in h:
                    continue
                arr = np.asarray(h[nm][:])
                if arr.ndim < 4:
                    continue                       # 标量场 (node type 等) 跳过
                a = arr.reshape(arr.shape[0], -1)  # (nb, nxb*ny*nz)
                if a.shape[1] != nxb:
                    continue                       # 非纯 1D-x 布局, 跳过
                frame[nm.lower()] = np.concatenate([a[b] for b in order])
            return frame
    except Exception as exc:  # noqa: BLE001
        C.log(f"    读取失败 {path.name}: {exc}", "WARN")
        return None


def load_series(outdir: Path, max_frames: int = 0,
                variables: Optional[Iterable[str]] = None
                ) -> List[Dict[str, Any]]:
    """读取目录下全部 chk 帧 (按时间升序)。max_frames>0 → 等间隔抽样。

    ★ 必须按时间升序返回: chk 帧号与时间是单调对应的, 但重组后仍显式排序,
      以免后续 pair_frames / 剖面插值依赖帧号顺序。
    """
    out: List[Dict[str, Any]] = []
    files = list_chk(outdir)
    if not files:
        return out
    if max_frames and len(files) > max_frames:
        idx = np.unique(np.linspace(0, len(files) - 1, max_frames)
                        .round().astype(int))
        files = [files[i] for i in idx]
    for f in files:
        fr = load_frame(f, variables)
        if fr is not None:
            out.append(fr)
    out.sort(key=lambda r: r["t"])
    return out


def load_leg(model: str, tag: str = "", max_frames: int = 0,
             variables: Optional[Iterable[str]] = None
             ) -> List[Dict[str, Any]]:
    """按腿名读整段时间序列 (自动解析输出目录)。"""
    return load_series(resolve_outdir(model, tag), max_frames, variables)


def load_both(tag: str = "", max_frames: int = 0,
              variables: Optional[Iterable[str]] = None
              ) -> Dict[str, List[Dict[str, Any]]]:
    """一次读两腿 → {"flsh": [...], "snb": [...]}。"""
    return {m: load_leg(m, tag, max_frames, variables) for m in ("flsh", "snb")}


# ══════════════════════════════════════════════════════════════
# 派生量
# ══════════════════════════════════════════════════════════════
def has_var(frame: Dict[str, Any], var: str) -> bool:
    """判定该帧能否提供某物理量 (含 nele 的离线可推导性)。"""
    if var == "nele":
        return "dens" in frame and any(sp in frame for sp in SPECIES_A_Z)
    return var in frame


def electron_number_density(frame: Dict[str, Any]) -> Optional[np.ndarray]:
    """nele [cm^-3] = Ye · 6.02e23 · dens  (FLASH 源码同式离线复现)。

    Ye = zbarFrac / abarInv,  abarInv = Σ_s X_s/A_s,
    zbarFrac = Σ_s X_s·Z_s/A_s    (X_s: 帧内物种质量分数)
    """
    if "dens" not in frame:
        return None
    dens = np.asarray(frame["dens"], dtype=float)
    abar_inv = np.zeros_like(dens)
    zbar_frac = np.zeros_like(dens)
    got = False
    for sp, (A, Z) in SPECIES_A_Z.items():
        if sp in frame:
            X = np.asarray(frame[sp], dtype=float)
            abar_inv += X / A
            zbar_frac += X * Z / A
            got = True
    if not got:
        return None
    with np.errstate(divide="ignore", invalid="ignore"):
        Ye = np.where(abar_inv > 0.0, zbar_frac / abar_inv, 0.0)
    return Ye * NA_APPROX * dens


def convert(frame: Dict[str, Any], var: str) -> Optional[np.ndarray]:
    """按 QUANTITIES 表把帧内原生 CGS 量换算成绘图单位。"""
    if var == "nele":
        return electron_number_density(frame)
    if var not in frame:
        return None
    a = np.asarray(frame[var], dtype=float)
    if var in ("tele", "tion", "trad"):
        return a / K_PER_EV                      # K -> eV
    if var in ("pele", "pres"):
        return a * ERG_CM3_TO_MBAR               # erg/cm^3 -> Mbar
    return a                                     # dens: 原样


def unit_of(var: str) -> str:
    return QUANTITIES[var]["unit"]


def axis_label(var: str) -> str:
    q = QUANTITIES[var]
    return f"{q['label']}  [{q['unit']}]"


def color_scale_label(var: str) -> str:
    q = QUANTITIES[var]
    return f"{q['label']}  [{q['unit']}]"


# ══════════════════════════════════════════════════════════════
# 时间轴 / 抽样
# ══════════════════════════════════════════════════════════════
def even_times(t0: float, t1: float, n: int = 10) -> np.ndarray:
    """在 [t0, t1] 上等间隔取 n 个时刻 (含端点)。"""
    n = max(2, int(n))
    return np.linspace(float(t0), float(t1), n)


def common_time_window(series: Dict[str, List[Dict[str, Any]]],
                       margin: float = 0.02) -> Tuple[float, float]:
    """两腿共同的时间交集 [t0, t1] (默认内缩 2% 边距)。

    两腿末帧时刻可能略有差异; 取交集可保证上下两联的时间范围严格一致,
    避免视觉上的"错位对比"。margin=0.02 → 两端各缩 2%。
    """
    starts, ends = [], []
    for frs in series.values():
        if frs:
            starts.append(frs[0]["t"])
            ends.append(frs[-1]["t"])
    if not starts:
        return 0.0, 1.0
    t0, t1 = max(starts), min(ends)
    if t1 <= t0:
        t0, t1 = min(starts), max(ends)
    span = t1 - t0
    return t0 + margin * span, t1 - margin * span


def nearest(series: List[Dict[str, Any]],
            t_target: float) -> Optional[Dict[str, Any]]:
    """按最近时刻挑帧。"""
    if not series:
        return None
    return min(series, key=lambda r: abs(r["t"] - t_target))


def pick_even(series: List[Dict[str, Any]], n: int = 10,
              t_range: Optional[Tuple[float, float]] = None
              ) -> List[Tuple[float, Dict[str, Any]]]:
    """在时间轴上**平均取 n 个时刻**, 每点返回其最近的实际帧。

    Returns:
        [(t_target, frame), ...], 按 t_target 升序; frame 为最近的真实帧。
    """
    if not series:
        return []
    t0, t1 = t_range if t_range else (series[0]["t"], series[-1]["t"])
    out: List[Tuple[float, Dict[str, Any]]] = []
    for tt in even_times(t0, t1, n):
        fr = nearest(series, float(tt))
        if fr is not None:
            out.append((float(tt), fr))
    return out


# ══════════════════════════════════════════════════════════════
# 网格构造 (时空图用)
# ══════════════════════════════════════════════════════════════
def build_xt(frames: List[Dict[str, Any]], var: str
             ) -> Optional[Tuple[np.ndarray, np.ndarray, np.ndarray]]:
    """把一串帧堆成时空矩阵 → (t_ns, x_um, Z)。

    Z.shape = (nt, nx), 单位已按 QUANTITIES 换算。
    ★ x 轴取**所有帧 x 的并集网格**: chk 帧的 x 网格在 +ug 下恒定不变, 但为稳健
      (将来若引入 AMR/重映射) 仍统一插值到公共网格。
    """
    rows, ts = [], []
    for fr in frames:
        v = convert(fr, var)
        if v is None:
            continue
        rows.append(np.asarray(v, dtype=float))
        ts.append(fr["t"])
    if not rows:
        return None
    x_ref = np.asarray(frames[0]["x_um"], dtype=float)
    Z = np.vstack([r if r.size == x_ref.size else
                   np.interp(x_ref, np.asarray(frames[i]["x_um"], dtype=float), r)
                   for i, r in enumerate(rows)])
    t_arr = np.asarray(ts, dtype=float)
    idx = np.argsort(t_arr)
    return t_arr[idx] * NS_PER_S, x_ref, Z[idx]


# ══════════════════════════════════════════════════════════════
# 目录解析
# ══════════════════════════════════════════════════════════════
def resolve_outdir(model: str, tag: str = "") -> Path:
    """解析某腿输出目录: 优先 <flash_output>/<tag>, 回退 <flash_output>。"""
    base = C.leg_output_dir(model)
    if tag:
        d = base / tag
        if d.exists():
            return d
    return base


def latest_tag(model: str) -> str:
    """返回 flash_output 下**最近的**含 chk 的子目录名 (无则 '')。"""
    base = C.leg_output_dir(model)
    if not base.is_dir():
        return ""
    cands = [d for d in base.iterdir()
             if d.is_dir() and list_chk(d)]
    if not cands:
        return ""
    return max(cands, key=lambda d: d.stat().st_mtime).name


def results_dir(sub: str = "") -> Path:
    """绘图输出目录: t004/results/[<sub>/], 不存在则创建。"""
    d = C.RESULT_DIR / sub if sub else C.RESULT_DIR
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_fig(fig, out_path: Path, note: str = "") -> Path:
    """统一存图 (高 DPI, 紧边界) 并打印相对路径。"""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(str(out_path), dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    size_kb = out_path.stat().st_size / 1024.0
    C.log(f"写出 {out_path.name}  ({size_kb:.0f} KB){('  ' + note) if note else ''}",
          "OK")
    return out_path
