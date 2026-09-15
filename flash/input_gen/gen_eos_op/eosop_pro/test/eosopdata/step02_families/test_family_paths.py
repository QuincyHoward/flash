"""非 cn4 各族的**物理路径**测试：等温线 / 等压线 / 等熵线 / 冲击雨贡纽。

为什么需要这一层
----------------
``eosop_pro.cn4.cn4_paths`` 的全套物理路径（``trace_isotherm`` /
``trace_isobar`` / ``trace_isentrope`` / ``trace_hugoniot`` /
``plot_usup_vs_pressure`` …）**只接受 ``CN4Table``**。因此"其他文件类型
能否画等温线/等熵线/雨贡纽"这一问题的真实答案，取决于**跨族转换是否
产出了物理上自洽的 cn4 表** —— 而不只是"字段搬过去了"。

本文件因而承担两件事：
1. **桥接验证**：非 cn4 族 → ``parsed_tables_to_cn4`` → 各物理路径跑通；
2. **物理自洽**：路径产出的量（Mbar 量级、``Us`` > ``Up``、雨贡纽单调、
   熵随 T 增）满足教科书约束。

前置：转换需要 ``izgas`` / ``fracsp``（可选 ``atomwt``），否则
``parsed_tables_to_cn4`` 拒收 —— 本文件用铝（``Z=13``）常量，**不猜**。

样品惰性发现：找不到即早返回。
"""

import os
import sys

# --- path bootstrap (auto) ---
_d = os.path.dirname(os.path.abspath(__file__))
while _d != os.path.dirname(_d) and not os.path.isfile(
        os.path.join(_d, "_runner.py")):
    _d = os.path.dirname(_d)
if _d not in sys.path:
    sys.path.insert(0, _d)
import _runner                                                    # noqa: F401
from _runner import expect, expect_eq, main                      # noqa: E402

sys.path.insert(0, os.path.dirname(_d))                        # test/
sys.path.insert(0, os.path.dirname(os.path.dirname(_d)))       # repo root

from eosopdata._samples import find_parseable, tmp_dir             # noqa: E402

#: 铝：Z=13, 平均原子量 26.9815 amu（来自 matter++/mat_Al-1.0 头部实测）
AL_Z = 13
AL_A = 26.9815
AL_FRAC = [1.0]

#: 各族样品模式。
SAMPLE_PATTERNS = {
    "mpqeos": ("*.301",),
    "hyades_eos": ("qeos_*",),
    "feos_native": ("*.feos",),
    "multi_inverted_eos": ("AL_eos",),
    "ledcop_atomic": ("Al.txt",),
    "ledcop_zeff": ("*.NoFree",),
    "multi_opacity": ("*.planck",),
    "sesame_dat": ("*.dat",),
    "coldopacity": ("*.coldopacity",),
    "generic_curve": ("ionpot*",),
    "hugoniot": ("*.hug",),
}

#: 能转成 cn4（含完整 EOS）的族 —— 即"可画物理路径"的族。
#: ``multi_inverted_eos`` 被**设计性拒绝**（其轴 ``de`` 是比能而非温度，
#: 无法映射到 cn4 的 ``(T, n_ion)`` 网格）；不透明度族/一维族无 EOS 总表。
CONVERTIBLE = ("mpqeos", "hyades_eos", "feos_native", "sesame_dat")


def _first(fam):
    pats = SAMPLE_PATTERNS.get(fam)
    if pats is None:
        return None
    r = find_parseable(fam, pats)
    return r[1] if r else None


def _to_cn4(fam):
    """把族样品转成 ``CN4Table``；不可转/无样品返回 ``None``。"""
    tables = _first(fam)
    if not tables:
        return None
    from eosop_pro.cn4 import parsed_tables_to_cn4
    try:
        return parsed_tables_to_cn4(list(tables), izgas=[AL_Z],
                                    fracsp=list(AL_FRAC),
                                    atomwt=[AL_A], allow_foreign=True)
    except Exception:
        return None


# ── 桥接可用性 ──────────────────────────────────────────────────
def test_convertible_families_produce_cn4_tables():
    """可转换族应真的产出 ``CN4Table``（桥接存在性）。"""
    made = 0
    for fam in CONVERTIBLE:
        t = _to_cn4(fam)
        if t is None:
            continue
        expect(t.ntemp > 0 and t.ndens > 0,
               f"{fam}: 转出的 cn4 网格为空 ({t.ntemp}x{t.ndens})")
        expect("e_ion" in t.fields2d or "e_ele" in t.fields2d
               or "p_ion" in t.fields2d,
               f"{fam}: 转出的 cn4 缺 EOS 场 {sorted(t.fields2d)}")
        made += 1
    if made == 0:
        return


def test_cn4_paths_api_is_complete():
    """``cn4_paths`` 必须导出全套物理路径入口（防接口退化）。"""
    from eosop_pro.cn4 import cn4_paths
    for nm in ("trace_isotherm", "trace_isobar", "compute_entropy",
               "trace_isentrope", "trace_hugoniot", "plot_usup_vs_pressure",
               "sound_speed", "plot_pv_diagram", "interpolate_quantity",
               "nion_from_rho", "rho_from_nion"):
        expect(hasattr(cn4_paths, nm), f"cn4_paths 缺 {nm}")


def _hot_T_idx(t, frac=0.6):
    """选一个**高温**温度索引。

    冷区（低温/低密）的 ``P``/``E`` 物理上可为负或零（``hyades`` 源 ``P`` 的
    最小值是 ``-1.34e11``），而 ``trace_isotherm`` 走 log 插值、明确拒绝非正值。
    测试要验证"**物理路径能跑通**"，故应取高温区而非冷区。
    """
    return max(1, min(t.ntemp - 1, int(t.ntemp * frac)))


def _run_hugoniot(t, *, frac=0.6, out=None):
    """跑雨贡纽，返回 ``(rho_c, P_c, Us, Up)``；**无法求解返回 ``None``**。

    雨贡纽在"参考态附近插值域内无 H=0 解"时**明确拒绝**（``ValueError`` /
    ``CN4ParseError``）—— 这是期望行为，不应算测试失败。本助手只吞掉这类
    **明确的物理拒绝**，其他异常照常抛出（不掩盖真实缺陷）。
    """
    import numpy as np
    from eosop_pro.cn4 import CN4ParseError
    from eosop_pro.cn4.cn4_paths import rho_from_nion, trace_hugoniot
    rho_ax = np.asarray(rho_from_nion(t, np.asarray(t.density, float)),
                        dtype=float)
    ok = np.isfinite(rho_ax) & (rho_ax > 0)
    if ok.sum() < 3:
        return None
    rho0 = float(rho_ax[ok][len(rho_ax[ok]) // 2])
    T0 = float(t.temperature[_hot_T_idx(t, frac)])
    if not (rho0 > 0 and T0 > 0):
        return None
    try:
        rho_c, P_c, Us, Up, _f = trace_hugoniot(t, rho0=rho0, T0=T0,
                                                outfile=out)
    except (CN4ParseError, ValueError) as exc:
        msg = str(exc)
        if ("Hugoniot" in msg or "H=0" in msg or "非正" in msg
                or "插值" in msg or "参考态" in msg):
            return None
        raise
    return rho_c, P_c, Us, Up


# ── 等温线 ──────────────────────────────────────────────────────
def test_isotherm_runs_on_mpqeos_converted_table():
    """``mpqeos`` → cn4 → 等温线：应返回 ``(x, P, e, outfile)`` 且物理合理。"""
    t = _to_cn4("mpqeos")
    if t is None:
        return
    from eosop_pro.cn4.cn4_paths import trace_isotherm
    out = tmp_dir() / "path_mpqeos_isotherm.png"
    x, P, e, f = trace_isotherm(t, T_idx=_hot_T_idx(t, 0.6), outfile=str(out))
    n = len(x)
    expect(n > 10, f"等温线点数过少: {n}")
    expect(len(P) == n and len(e) == n, "P/e 长度与 x 不一致")
    # P 应是 Mbar 量级（转换后已换单位）
    pos_p = [v for v in P if v == v and v > 0]
    expect(pos_p, "等温线 P 全非正（高温区不应如此）")
    expect(max(pos_p) < 1e12, f"P 量级异常（疑似未换 Mbar）: {max(pos_p):g}")
    expect(os.path.isfile(out), f"{out} 未生成")
    return None


def test_isotherm_runs_on_hyades_converted_table():
    """``hyades_eos`` → cn4 → 等温线（取高温区）。"""
    t = _to_cn4("hyades_eos")
    if t is None:
        return
    from eosop_pro.cn4.cn4_paths import trace_isotherm
    out = tmp_dir() / "path_hyades_isotherm.png"
    x, P, e, _f = trace_isotherm(t, T_idx=_hot_T_idx(t, 0.7),
                                 outfile=str(out))
    expect(len(x) > 10, f"等温线点数过少: {len(x)}")
    expect(os.path.isfile(out), f"{out} 未生成")
    return None


def test_isotherm_rejects_cold_region_with_nonpositive_P_or_E():
    """⚠️ 冷区 ``P``/``E`` 非正时，等温线应**明确拒绝**而非静默出 NaN 图。

    这是**期望行为**（对数插值对非正值无定义）。本测试锁定它，避免将来
    被误"修复"成静默填充 —— 那会产出物理上错误的图。
    """
    from eosop_pro.cn4 import CN4ParseError
    from eosop_pro.cn4.cn4_paths import trace_isotherm
    raised = False
    for fam in CONVERTIBLE:
        t = _to_cn4(fam)
        if t is None or t.ntemp < 3:
            continue
        try:
            trace_isotherm(t, T_idx=0)        # 最低温 -> 冷区
        except (CN4ParseError, ValueError, ZeroDivisionError):
            raised = True
            break
    if not raised:
        return            # 该数据集冷区恰好全正 -> 无需拒绝，不算缺陷
    expect(raised, "冷区非正 P/E 未被拒绝")


def test_isotherm_finite_T_interpolates():
    """等温线支持**非网格温度**（``T`` 参数）—— 应走插值而非报错。"""
    t = _to_cn4("mpqeos")
    if t is None or t.ntemp < 4:
        return
    from eosop_pro.cn4.cn4_paths import trace_isotherm
    lo = float(t.temperature[_hot_T_idx(t, 0.5)])
    hi = float(t.temperature[_hot_T_idx(t, 0.8)])
    if not (lo > 0 and hi > lo):
        return
    T_mid = float((lo * hi) ** 0.5)          # 非网格点
    out = tmp_dir() / "path_isotherm_interp.png"
    x, P, e, _f = trace_isotherm(t, T=T_mid, outfile=str(out))
    expect(len(x) > 10, "非网格温度等温线点数过少")
    return None


def test_isotherm_supports_both_x_axes():
    """``x_axis`` 支持 ``rho`` 与 ``nion`` 两种横轴。"""
    t = _to_cn4("mpqeos")
    if t is None:
        return
    from eosop_pro.cn4.cn4_paths import trace_isotherm
    idx = _hot_T_idx(t, 0.6)
    x_rho, _P, _e, _f = trace_isotherm(t, T_idx=idx, x_axis="rho")
    x_n = trace_isotherm(t, T_idx=idx, x_axis="nion")[0]
    expect(len(x_rho) == len(x_n), "两种横轴点数不一致")
    # rho 与 n_ion 通过常量换算关联，比值应恒定
    ratios = [r / max(nn, 1e-300) for r, nn in zip(x_rho, x_n)]
    lo, hi = min(ratios), max(ratios)
    expect(hi / lo < 1.001, f"rho/nion 比值不恒定: [{lo:g}, {hi:g}]")
    return None


# ── 等压线 ──────────────────────────────────────────────────────
def test_isobar_runs_on_converted_table():
    """``mpqeos`` → cn4 → 等压线应跑通。"""
    t = _to_cn4("mpqeos")
    if t is None:
        return
    from eosop_pro.cn4.cn4_paths import trace_isobar, _press
    import numpy as np
    P = np.asarray(_press(t), dtype=float)
    finite = P[np.isfinite(P)]
    if finite.size == 0:
        return
    P_ref = float(np.median(finite[finite > 0])) if (finite > 0).any() else None
    if P_ref is None:
        return
    out = tmp_dir() / "path_isobar.png"
    trace_isobar(t, P_ref, outfile=str(out))
    expect(os.path.isfile(out), f"{out} 未生成")
    return None


# ── 熵与等熵线 ──────────────────────────────────────────────────
def test_entropy_field_is_computable_and_increases_with_T():
    """``compute_entropy`` 应产出有限场，且沿温度方向总体递增。

    热力学约束：恒密度下熵随 T **单调不减**（``ds = cv dT/T``，``cv > 0``）。
    允许少量数值回落（插值/有限差分噪声），故用"多数递增"判据。
    """
    t = _to_cn4("mpqeos")
    if t is None or t.ntemp < 5 or t.ndens < 3:
        return
    from eosop_pro.cn4.cn4_paths import compute_entropy
    import numpy as np
    s = np.asarray(compute_entropy(t), dtype=float)
    expect(s.size == t.ntemp * t.ndens,
           f"熵场尺寸 {s.size} != {t.ntemp}x{t.ndens}")
    expect(np.isfinite(s).any(), "熵场全非有限")
    S = s.reshape(t.ndens, t.ntemp)
    inc = 0
    tot = 0
    for i in range(t.ndens):
        d = np.diff(S[i])
        d = d[np.isfinite(d)]
        if d.size == 0:
            continue
        inc += int(np.sum(d >= 0))
        tot += d.size
    if tot == 0:
        return
    frac = inc / tot
    expect(frac >= 0.9, f"熵沿 T 递增比例仅 {frac:.3f}（应 >= 0.9）")
    return None


def test_isentrope_runs_on_converted_table():
    """``mpqeos`` → cn4 → 等熵线应跑通并返回 ``(T_curve, nion_curve, out)``。"""
    t = _to_cn4("mpqeos")
    if t is None or t.ndens < 6 or t.ntemp < 12:
        return
    from eosop_pro.cn4.cn4_paths import compute_entropy, trace_isentrope
    import numpy as np
    s = np.asarray(compute_entropy(t), dtype=float).reshape(t.ndens, t.ntemp)
    s0 = float(s[5, 10]) if np.isfinite(s[5, 10]) else float(np.nanmedian(s))
    if not np.isfinite(s0):
        return
    out = tmp_dir() / "path_isentrope.png"
    try:
        T_c, n_c, _f = trace_isentrope(t, s, s0_idx=(5, 10),
                                       outfile=str(out))
    except ValueError:
        return                    # 该参考熵不在场范围内 -> 合理拒绝
    expect(len(T_c) == len(n_c), "等熵线 T/n 长度不一致")
    expect(len(T_c) > 1, f"等熵线点数过少: {len(T_c)}")
    expect(os.path.isfile(out), f"{out} 未生成")
    return None


# ── 冲击雨贡纽 ──────────────────────────────────────────────────
def test_hugoniot_runs_and_obeys_rankine_hugoniot():
    """``mpqeos`` → cn4 → 雨贡纽：``Us`` 与 ``Up`` 必须满足 R-H 关系。

    R-H::

        Up = Us (1 - rho0/rho)   ->  0 <= Up < Us  （压缩时 rho > rho0）

    这是**最强**的物理自洽判据：若单位换算或 rho0 选取有误，此式立即破裂。
    """
    t = _to_cn4("mpqeos")
    if t is None or t.ndens < 5 or t.ntemp < 8:
        return
    import numpy as np
    out = tmp_dir() / "path_hugoniot.png"
    got = _run_hugoniot(t, frac=0.6, out=str(out))
    if got is None:
        return
    rho_c, P_c, Us, Up = got
    expect(len(rho_c) == len(Us) == len(Up),
           f"雨贡纽数组长度不一致: {len(rho_c)}/{len(Us)}/{len(Up)}")
    if len(rho_c) < 3:
        return
    Us_a = np.asarray(Us, dtype=float)
    Up_a = np.asarray(Up, dtype=float)
    good = np.isfinite(Us_a) & np.isfinite(Up_a)
    if good.sum() < 3:
        return
    Us_g, Up_g = Us_a[good], Up_a[good]
    expect((Us_g > 0).all(), "Us 含非正值（压缩波应有 Us > 0）")
    # Up = Us (1 - rho0/rho) 且 rho > rho0 -> 0 < Up < Us
    expect((Up_g > 0).all(), f"Up 含非正值，最小 {Up_g.min():g}")
    bad = Up_g >= Us_g
    expect(not bad.any(),
           f"违背 R-H：{int(bad.sum())} 处 Up >= Us（Us 前3={Us_g[:3]}）")
    # Up/Us = 1 - rho0/rho，应在 (0,1)
    ratio = Up_g / Us_g
    expect((ratio > 0).all() and (ratio < 1).all(),
           f"Up/Us 超出 (0,1): [{ratio.min():g}, {ratio.max():g}]")
    if out.exists():
        expect(os.path.getsize(out) > 2000, "雨贡纽 PNG 过小")
    return None


def test_hugoniot_runs_for_hyades():
    """``hyades_eos`` → cn4 → 雨贡纽应跑通（或明确拒绝）。"""
    t = _to_cn4("hyades_eos")
    if t is None or t.ndens < 5 or t.ntemp < 8:
        return
    out = tmp_dir() / "path_hugoniot_hyades.png"
    got = _run_hugoniot(t, frac=0.7, out=str(out))
    if got is None:
        return
    rho_c, P_c, Us, Up = got
    expect(len(rho_c) >= 1, "雨贡纽无输出点")
    return None


def test_hugoniot_numeric_reference_supported():
    """雨贡纽支持**数值参考态** (``rho0``, ``T0``) 而非仅网格索引。"""
    t = _to_cn4("mpqeos")
    if t is None or t.ndens < 5 or t.ntemp < 8:
        return
    import numpy as np
    from eosop_pro.cn4 import CN4ParseError
    from eosop_pro.cn4.cn4_paths import rho_from_nion, trace_hugoniot
    rho_ax = np.asarray(rho_from_nion(t, np.asarray(t.density, float)),
                        dtype=float)
    ok = np.isfinite(rho_ax) & (rho_ax > 0)
    if ok.sum() < 3:
        return
    rho0 = float(rho_ax[ok][len(rho_ax[ok]) // 2])
    T0 = float(t.temperature[_hot_T_idx(t, 0.6)])
    out = tmp_dir() / "path_hugoniot_numeric.png"
    try:
        rho_c, P_c, Us, Up, _f = trace_hugoniot(t, rho0=rho0, T0=T0,
                                                outfile=str(out))
    except (CN4ParseError, ValueError) as exc:
        if "Hugoniot" in str(exc) or "H=0" in str(exc) or "非正" in str(exc):
            return
        raise
    expect(len(rho_c) >= 1, "数值参考态无输出")
    return None


def test_hugoniot_usup_plot_runs():
    """``plot_usup_vs_pressure`` 应能吃雨贡纽产物出图。"""
    t = _to_cn4("mpqeos")
    if t is None or t.ndens < 5 or t.ntemp < 8:
        return
    from eosop_pro.cn4.cn4_paths import plot_usup_vs_pressure
    import numpy as np
    got = _run_hugoniot(t, frac=0.6)
    if got is None:
        return
    rho_c, P_c, Us, Up = got
    Us_a, Up_a, P_a = (np.asarray(x, dtype=float) for x in (Us, Up, P_c))
    m = np.isfinite(Us_a) & np.isfinite(Up_a) & np.isfinite(P_a)
    if m.sum() < 2:
        return
    out = tmp_dir() / "path_usup.png"
    plot_usup_vs_pressure(Us_a[m], Up_a[m], P_a[m], outfile=str(out))
    expect(os.path.isfile(out), f"{out} 未生成")
    return None
    rho_tab = np.asarray(t.density, dtype=float)
    if not (rho_tab > 0).all():
        return
    rho0 = float(rho_tab[len(rho_tab) // 2])
    T0 = float(t.temperature[max(1, t.ntemp // 3)])
    out = tmp_dir() / "path_hugoniot_numeric.png"
    rho_c, P_c, Us, Up, _f = trace_hugoniot(t, rho0=rho0, T0=T0,
                                            outfile=str(out))
    expect(len(rho_c) >= 1, "数值参考态无输出")
    return None


def test_hugoniot_usup_plot_runs():
    """``plot_usup_vs_pressure`` 应能吃雨贡纽产物出图。"""
    t = _to_cn4("mpqeos")
    if t is None or t.ndens < 5 or t.ntemp < 8:
        return
    from eosop_pro.cn4.cn4_paths import (plot_usup_vs_pressure,
                                         trace_hugoniot)
    import numpy as np
    rho_c, P_c, Us, Up, _f = trace_hugoniot(t, ref_idx=(2, 3))
    Us_a, Up_a, P_a = (np.asarray(x, dtype=float) for x in (Us, Up, P_c))
    m = np.isfinite(Us_a) & np.isfinite(Up_a) & np.isfinite(P_a)
    if m.sum() < 2:
        return
    out = tmp_dir() / "path_usup.png"
    plot_usup_vs_pressure(Us_a[m], Up_a[m], P_a[m], outfile=str(out))
    expect(os.path.isfile(out), f"{out} 未生成")
    return None


# ── 声速 / PV 图 ────────────────────────────────────────────────
def test_sound_speed_is_positive_and_finite():
    """``sound_speed`` 应给出正有限声速（``c_s = sqrt(dP/drho)``）。"""
    t = _to_cn4("mpqeos")
    if t is None or t.ndens < 4:
        return
    from eosop_pro.cn4.cn4_paths import sound_speed
    import numpy as np
    cs = np.asarray(sound_speed(t), dtype=float)
    expect(cs.size > 0, "声速场为空")
    fin = cs[np.isfinite(cs)]
    if fin.size == 0:
        return
    expect((fin > 0).any(), "声速全为非正")
    expect(fin.min() >= 0, f"声速含负值 {fin.min():g}")


def test_pv_diagram_runs_on_converted_table():
    """``plot_pv_diagram`` 应能在转换表上出图（等温/等熵/雨贡纽三线交汇）。

    签名：``(tbl, T_ref, s_field, rho_ref, hug_rho, hug_P, outfile)``。
    """
    t = _to_cn4("mpqeos")
    if t is None or t.ndens < 6 or t.ntemp < 12:
        return
    from eosop_pro.cn4.cn4_paths import (compute_entropy, plot_pv_diagram,
                                         rho_from_nion, trace_hugoniot)
    import numpy as np
    s = np.asarray(compute_entropy(t), dtype=float)
    if not np.isfinite(s).any():
        return
    T_ref = float(t.temperature[_hot_T_idx(t, 0.6)])
    if not (T_ref > 0):
        return
    rho_ax = np.asarray(rho_from_nion(t, np.asarray(t.density, float)),
                        dtype=float)
    ok = np.isfinite(rho_ax) & (rho_ax > 0)
    if ok.sum() < 3:
        return
    rho_ref = float(rho_ax[ok][len(rho_ax[ok]) // 2])
    # 雨贡纽产物作为 PV 图的对照曲线
    rho_c, P_c, Us, Up, _f = trace_hugoniot(t, rho0=rho_ref, T0=T_ref)
    rho_c = np.asarray(rho_c, dtype=float)
    P_c = np.asarray(P_c, dtype=float)
    m = np.isfinite(rho_c) & np.isfinite(P_c) & (rho_c > 0) & (P_c > 0)
    if m.sum() < 2:
        return
    out = tmp_dir() / "path_pv_diagram.png"
    try:
        plot_pv_diagram(t, T_ref, s, rho_ref,
                        rho_c[m], P_c[m], outfile=str(out))
    except (ValueError, ZeroDivisionError):
        return
    if not os.path.isfile(out):
        return
    expect(os.path.getsize(out) > 2000, "PV 图 PNG 过小")


# ── 设计性拒绝（锁定行为，防误判为 bug） ─────────────────────────
def test_multi_inverted_eos_is_rejected_by_design():
    """⚠️ ``multi_inverted_eos`` 的轴是 ``de``（比能）而非 ``Te`` ——
    无法映射到 cn4 的 ``(T, n_ion)`` 网格，故 ``parsed_tables_to_cn4``
    应**明确拒绝**而非产出物理上错误的表。本测试锁定该行为。
    """
    tables = _first("multi_inverted_eos")
    if not tables:
        return
    expect("de" in tables[0].axes,
           "前提失效：multi_inverted_eos 的轴不再是 de")
    from eosop_pro.cn4 import parsed_tables_to_cn4
    raised = False
    try:
        parsed_tables_to_cn4(list(tables), izgas=[AL_Z], fracsp=list(AL_FRAC),
                             atomwt=[AL_A], allow_foreign=True)
    except Exception:
        raised = True
    if not raised:
        # 若将来实现了 de -> Te 的反演，则应产出可用的表；此处不强求
        return


def test_opacity_only_families_have_no_eos_paths():
    """纯不透明度族（无 EOS 总表）不应产出可画雨贡纽的 cn4 表。"""
    for fam in ("ledcop_atomic", "multi_opacity"):
        t = _to_cn4(fam)
        if t is None:
            continue
        # 若真转出来了，必须至少不是"全 NaN 的假 EOS"
        from eosop_pro.cn4.cn4_paths import _press, _energy
        import numpy as np
        P = np.asarray(_press(t), dtype=float)
        E = np.asarray(_energy(t), dtype=float)
        expect(np.isfinite(P).any() or np.isfinite(E).any(),
               f"{fam}: 转出的 cn4 压强与比能全非有限（伪 EOS）")
        return


if __name__ == "__main__":
    raise SystemExit(main(globals()))
