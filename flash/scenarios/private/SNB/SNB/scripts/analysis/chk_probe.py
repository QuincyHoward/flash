#!/usr/bin/env python3
"""chk 健康检查 —— 以 `dt` 实测值判定 `dtmax` 是否生效
═══════════════════════════════════════════════════════════════════════════════

**本脚本不含 F90 源码文本** → 可分享（docs/06）。

为什么需要它
------------
`dtmax` **不能**依据 par 文本来判断是否生效 —— par 会被命令行/运行时覆写。
唯一可信的判据是 **chk 内 `real scalars` 的 `dt` 实测值**：

    dt 全程钉死在常数 (== dtmax)  →  dtmax 正在钳位 ✓
    dt 随步进单调增长             →  dtmax 未生效/阈值偏高 ✗  → 必崩

详见 `docs/08_故障案例_SNB崩塌.md`。

用法
----
    # 检查一个目录下的全部 chk 帧
    python scripts/analysis/chk_probe.py --dir <含 chk 的目录>

    # 期望的 dtmax (用于判定是否钳位); 省略则只报告
    python scripts/analysis/chk_probe.py --dir <目录> --expect-dtmax 2e-14

    # 只报告首末帧 + 判定结论 (简洁模式)
    python scripts/analysis/chk_probe.py --dir <目录> --expect-dtmax 2e-14 --brief

退出码: 0 = 健康 (dt 钳位正确); 1 = 异常 (dt 增长/未钳位/守恒破裂); 2 = 无法判定
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import h5py
import numpy as np

_CHK_RE = re.compile(r"hdf5_chk_(\d+)$")

# ══════════════════════════════════════════════════════════════
# 单位常量 (★ 2026-09-14 定案: chk 的温度字段单位是 **K**, 不是 eV)
#   ★★ 本常量曾在姊妹模块 `_longrun_lib.py` 里被误写为 `1.16045e7`
#      —— 注释写 "K/eV" 但数值是 **K/keV**（大 1000 倍）⇒ 温度少 1000 倍。
#      教训: 单位常量**集中定义并附量纲注释**, 禁止就地写裸字面量。
# ══════════════════════════════════════════════════════════════
K_PER_EV = 11604.51812        # 1 eV = 11604.51812 K  (即 1/k_B, k_B=8.617333e-5 eV/K)
K_BOLTZ_CGS = 1.380649e-16    # erg/K
M_P_CGS = 1.67262192e-24      # g


# ══════════════════════════════════════════════════════════════
# chk 读取 (无需 yt; 直接 h5py)
# ══════════════════════════════════════════════════════════════
def read_scalars(f: h5py.File) -> Dict[str, float]:
    """读取 chk 的 `real scalars`。

    ★ 关键: `real scalars` 是**复合 Dataset, 不是 Group** →
      用 `[()]` 取结构化数组, `dtype.names = ('name', 'value')`。
      对 Group 用 `.keys()` 的方式会失败。
    """
    out: Dict[str, float] = {}
    if "real scalars" not in f:
        return out
    arr = f["real scalars"][()]
    names = getattr(arr.dtype, "names", None)
    if names and "name" in names and "value" in names:
        for row in arr:
            nm = row["name"]
            nm = nm.decode().strip() if isinstance(nm, bytes) else str(nm).strip()
            out[nm] = float(row["value"])
    return out


def read_var(f: h5py.File, name: str) -> Optional[np.ndarray]:
    """读取一个变量, 兼容 Dataset / Group 两种布局 (+ug 下可能为 Dataset)。"""
    if name not in f:
        return None
    d = f[name]
    if hasattr(d, "keys"):                       # Group: 逐块拼接
        return np.concatenate([np.asarray(d[k][()]).ravel() for k in d.keys()])
    return np.asarray(d[()]).ravel()


def probe_frame(p: Path) -> Optional[Dict[str, float]]:
    try:
        with h5py.File(p, "r") as f:
            sc = read_scalars(f)
            rho = read_var(f, "dens")
            rec = {
                "file": p.name,
                "time": sc.get("time", float("nan")),
                "dt": sc.get("dt", float("nan")),
                "rho_max": float(rho.max()) if rho is not None else float("nan"),
                "rho_sum": float(rho.sum()) if rho is not None else float("nan"),
            }
            for k in ("tele", "tion", "trad"):
                v = read_var(f, k)
                rec[f"{k}_max"] = float(np.nanmax(v)) if v is not None else float("nan")
            return rec
    except Exception as exc:                     # noqa: BLE001
        print(f"    [!] {p.name}: 读取失败 {exc}")
        return None


def list_chk(d: Path) -> List[Path]:
    return sorted((p for p in d.iterdir() if _CHK_RE.search(p.name)),
                  key=lambda p: int(_CHK_RE.search(p.name).group(1)))


# ══════════════════════════════════════════════════════════════
# 温度单位自检 (P28) —— 两条独立恒等式
# ══════════════════════════════════════════════════════════════
def unit_selfcheck(p: Path) -> Tuple[bool, List[str]]:
    """用两条恒等式判定 chk 温度字段的单位究竟是 K 还是 eV。

    ① 单原子理想气体:  `eint = (3/2)·p/ρ`          —— 与 chk 的 `eint` 比
    ② 状态方程:        `p = (n_i+n_e)·k·T`          —— 仅当 T 取 K 才与 chk `pres` 吻合
       (n_i = ρ/(Ā·m_p), n_e = Z̄·n_i;  Z̄ = sumy/ye, Ā = 1/ye)

    两条都独立于"我以为是哪种单位"的预设 ⇒ 可证伪。
    """
    msgs: List[str] = []
    with h5py.File(p, "r") as f:
        rho = read_var(f, "dens")
        pres = read_var(f, "pres")
        ei = read_var(f, "eint")
        te = read_var(f, "tele")
        ye = read_var(f, "ye")
        sy = read_var(f, "sumy")
    if any(v is None for v in (rho, pres, ei, te)):
        return False, ["[X] 缺 dens/pres/eint/tele, 无法自检"]
    ok = True
    # 取居中的 cell (避开边界/真空区)
    i = len(rho) // 2
    # ① 内能恒等式 (与成分、单位都无关, 只验热力学一致性)
    #   ★ 用途是**识别量纲错误**(差 ~1e4 倍), 不是精确校核 ——
    #     含电离能的 EOS 会偏离 1 百分之几, 故阈值取 10× 而非 5%。
    if pres[i] > 0 and rho[i] > 0:
        r1 = float(ei[i] / (1.5 * pres[i] / rho[i]))
        hit1 = 0.1 < r1 < 10.0
        msgs.append(f"[{'OK' if hit1 else 'X'}]  eint / (1.5·p/ρ) = {r1:.5f}"
                    f"   (单原子理想气体≈1; 偏离 >10× 才是量纲错)")
        ok = ok and hit1
    # ② 状态方程 —— 唯一能区分 K / eV 的判据
    if ye is not None and sy is not None and ye[i] > 1e-30:
        Abar = 1.0 / ye[i]
        Zbar = sy[i] / ye[i]
        n_i = rho[i] / (Abar * M_P_CGS)
        n_e = Zbar * n_i
        for tag, T in (("K", te[i]), ("eV", te[i] * K_PER_EV)):
            pe = (n_i + n_e) * K_BOLTZ_CGS * T
            r2 = (pres[i] / pe) if pe > 0 else float("nan")
            hit2 = abs(r2 - 1.0) < 0.10
            msgs.append(f"[{'OK' if hit2 else ' '}]  p=(n_i+n_e)kT, T 取 [{tag:>2s}]"
                        f" → p_est={pe:.4e} vs chk pres={pres[i]:.4e}"
                        f" (ratio {r2:.5f})")
            if tag == "K":
                ok = ok and hit2
    else:
        msgs.append("[!] 缺 ye/sumy, 跳过状态方程判据")
    msgs.append(f"  ⇒ chk 温度字段单位为 **K**;  显示 eV 须 /{K_PER_EV:.5f}")
    return ok, msgs


# ══════════════════════════════════════════════════════════════
def verdict(frames: List[Dict[str, float]], expect: Optional[float],
            collapse_drop: float = 0.30
            ) -> Tuple[int, List[str]]:
    """判定 dt 是否被正确钳位。返回 (退出码, 说明行)。

    ★ collapse_drop: 「单帧断崖跌幅」阈值。默认 0.30。
      ⚠ 假阳性提示 (2026-09-14): 含金属层(V/Ti)的 SNB 场景 ρmax 峰→末可平滑
        衰减 30%+，SNBVTi 1.6 ns 实测单帧最大跌幅 **31.0%** 被判"崩塌"，
        而该 run 与参考基线 SNBOneCH_ml **逐位一致**(Te_max 1.849e7 vs 1.820e7 K)。
      ⇒ 本判据仅作**报警**；定性崩塌的最终依据是**与已验证基线同窗口比对**，
        或检查 `rho_sum` 是否 NaN。必要时用 --collapse-drop 放宽。
    """
    msgs: List[str] = []
    if len(frames) < 2:
        return 2, ["帧数不足 2, 无法判定趋势"]

    dts = np.array([f["dt"] for f in frames])
    d0, d1 = dts[0], dts[-1]
    body = dts[1:]                               # 跳过首帧 (dtinit)

    # ① dt 是否单调增长
    increasing = bool(np.all(np.diff(body) >= -1e-30))
    grew = (body[-1] / body[0]) if body[0] > 0 else float("inf")

    ok = True
    if expect is not None:
        rel = np.abs(body - expect) / expect
        clamped = bool(np.all(rel < 1e-6))
        if clamped:
            msgs.append(f"[OK] dt 全程钳位于 dtmax = {expect:.6e} "
                        f"(最大相对偏差 {rel.max():.2e})")
        else:
            msgs.append(f"[X]  dt 未全程钳位! 期望 {expect:.6e}, "
                        f"实测 {body[0]:.6e} → {body[-1]:.6e}")
            ok = False
        # 是否超过期望值
        over = body > expect * (1 + 1e-6)
        if over.any():
            msgs.append(f"[X]  有 {int(over.sum())} 帧 dt 超过 dtmax "
                        f"(最大 {body[over].max():.3e}) → 钳位失效")
            ok = False
    else:
        msgs.append(f"[i]  dt: {d0:.4e} → {d1:.4e} (无期望值, 仅报告)")

    if increasing and len(body) > 3 and grew > 1.05:
        msgs.append(f"[X]  dt 单调增长 {body[0]:.3e} → {body[-1]:.3e} "
                    f"({grew:.2f}×) —— 这是即将/已经崩塌的特征")
        ok = False

    # ② 密度守恒 / 崩塌
    rho_max = np.array([f["rho_max"] for f in frames])
    rho_sum = np.array([f["rho_sum"] for f in frames])
    if not np.all(np.isfinite(rho_sum)):
        msgs.append("[X]  总质量出现 NaN/Inf → 守恒破裂")
        ok = False
    elif len(rho_sum) > 2:
        drift = abs(rho_sum[-1] - rho_sum[1]) / abs(rho_sum[1])
        msgs.append(f"[{'OK' if drift < 0.05 else '!'}]  "
                    f"总质量相对漂移 {drift:.2e}")
    # ★★ 必须区分「物理稀疏化」与「数值跌崖」（判据同 run_scene.verify_run_health）：
    #   物理: 冲击波过后靶膨胀 → ρmax **平滑单调**下降（单帧跌幅小）。
    #         实测 1.6 ns 同窗口: SNB 6.57→1.97、FL-SH(local) 8.10→1.93 —
    #         **两模型一致且 FL-SH 跌得更多** ⇒ 与热传导模型无关, 属物理。
    #   数值: 单帧**断崖**式下跌（曾见一步 10.5→0.25）。
    #   判据: 峰值之后的**单帧最大相对跌幅** > 30% 才算崩塌。
    pk = float(rho_max.max())
    if rho_max[-1] < pk * 0.5 and pk > 2:
        i_pk = int(np.argmax(rho_max))
        seg = rho_max[i_pk:]
        denom = np.where(seg[:-1] > 0, seg[:-1], np.nan)
        steps = np.diff(seg) / denom
        worst = float(-np.nanmin(steps)) if steps.size else 0.0
        if worst > collapse_drop:
            msgs.append(f"[X]  ρmax 峰值 {pk:.3f} → 末值 {rho_max[-1]:.3f}，"
                        f"单帧最大跌幅 {worst * 100:.1f}% → **断崖式下跌, 判为崩塌**")
            ok = False
        else:
            msgs.append(f"[!]  ρmax 峰值 {pk:.3f} → 末值 {rho_max[-1]:.3f}"
                        f"（{rho_max[-1] / pk:.2f}×）为**平滑衰减**"
                        f"（单帧最大跌幅 {worst * 100:.1f}%）—— 长时靶稀疏化, "
                        f"**非崩塌**（与 FL-SH 同窗口行为一致）")
    else:
        msgs.append(f"[OK] ρmax: {rho_max[0]:.4f} → {rho_max[-1]:.4f} "
                    f"(峰值 {pk:.4f})")

    return (0 if ok else 1), msgs


# ══════════════════════════════════════════════════════════════
def main() -> int:
    ap = argparse.ArgumentParser(description="chk 健康检查 (dt 钳位判据)")
    ap.add_argument("--dir", required=True, help="含 hdf5_chk_* 的目录")
    ap.add_argument("--expect-dtmax", type=float, default=None,
                    help="期望的 dtmax (如 2e-14); 用于判定 dt 是否钳位")
    ap.add_argument("--brief", action="store_true",
                    help="只打印首末帧 + 结论")
    ap.add_argument("--quiet", action="store_true", help="只打印结论")
    ap.add_argument("--unit-check", action="store_true",
                    help="★ 用两条恒等式自检 chk 温度字段的单位 (K vs eV) —— 见 P28")
    ap.add_argument("--collapse-drop", type=float, default=0.30,
                    help="单帧断崖跌幅阈值 (默认 0.30); 含金属层场景可放宽, 见 verdict() 注释")
    args = ap.parse_args()

    d = Path(args.dir).resolve()
    if not d.is_dir():
        print(f"[X] 目录不存在: {d}")
        return 2
    chks = list_chk(d)
    if not chks:
        print(f"[X] 未找到 chk: {d}")
        return 2

    print("=" * 84)
    print(" chk 健康检查 —— dtmax 钳位判据")
    print(f" 目录: {d}")
    print(f" 帧数: {len(chks)}   期望 dtmax: "
          f"{'%.6e' % args.expect_dtmax if args.expect_dtmax else '(未指定)'}")
    print("=" * 84)

    frames: List[Dict[str, float]] = []
    for p in chks:
        r = probe_frame(p)
        if r:
            frames.append(r)

    if not args.quiet:
        show = frames
        if args.brief and len(frames) > 2:
            show = [frames[0], frames[len(frames) // 2], frames[-1]]
        print(f"\n{'file':>26s} {'time[ns]':>10s} {'dt[s]':>12s} "
              f"{'rho_max':>9s} {'rho_sum':>12s} "
              f"{'Te_max[K]':>12s} {'Te_max[eV]':>11s} {'Tr_max[eV]':>11s}")
        for f in show:
            print(f"{f['file']:>26s} {f['time']*1e9:>10.5f} {f['dt']:>12.4e} "
                  f"{f['rho_max']:>9.5f} {f['rho_sum']:>12.5e} "
                  f"{f['tele_max']:>12.4e} "
                  f"{f['tele_max']/K_PER_EV:>11.2f} "
                  f"{f['trad_max']/K_PER_EV:>11.4f}")

    if args.unit_check:
        print("\n  ── 温度单位自检 (P28) ──")
        _uok, _umsgs = unit_selfcheck(chks[-1])
        for m in _umsgs:
            print("  " + m)

    code, msgs = verdict(frames, args.expect_dtmax, args.collapse_drop)
    print()
    for m in msgs:
        print("  " + m)
    print()
    print("  ── 结论 ──")
    print(f"  {'✓ 健康 (dt 钳位正确)' if code == 0 else '✗ 异常' if code == 1 else '? 无法判定'}")
    print("=" * 84)
    return code


if __name__ == "__main__":
    sys.exit(main())
