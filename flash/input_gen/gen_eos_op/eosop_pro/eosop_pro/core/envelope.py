"""⑤ 物理包络与单位裁决 —— 自洽性校验的最后一关。

包络（全部来自 ``config.py``，**显式可配**并在报告中打印）
---------------------------------------------------------
=================  ==========================  =========================
量                  范围                        出处
=================  ==========================  =========================
``rho``            ``[1e-8, 1e6] g/cm³``        config.RHO_MIN/MAX_G_CM3
``Te``             ``[1e-2, 1e6] eV``           config.TE_MIN/MAX_EV
``P``              ``[1e-12, 1e12] Mbar``       config.P_MIN/MAX_MBAR
=================  ==========================  =========================

★ 诚实声明（写进文档与报告）
----------------------------
**这些阈值是预设的**，不是物理定律。极端条件（相对论简并）下可能误判 ——
所以：① 全部走 ``config`` 可配；② 报告里显式打印所用阈值；
③ 越界只标 ``suspect``，不擅自改数据。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .. import config

__all__ = ["Envelope", "EnvelopeCheck", "DEFAULT_ENVELOPE", "check_values"]


@dataclass(frozen=True)
class Envelope:
    """一组物理包络阈值（可配）。"""

    rho_min: float = config.RHO_MIN_G_CM3
    rho_max: float = config.RHO_MAX_G_CM3
    te_min: float = config.TE_MIN_EV
    te_max: float = config.TE_MAX_EV
    p_min: float = config.P_MIN_MBAR
    p_max: float = config.P_MAX_MBAR

    def describe(self) -> str:
        return (f"rho∈[{self.rho_min:g},{self.rho_max:g}] g/cm3, "
                f"Te∈[{self.te_min:g},{self.te_max:g}] eV, "
                f"P∈[{self.p_min:g},{self.p_max:g}] Mbar")


DEFAULT_ENVELOPE = Envelope()


@dataclass
class EnvelopeCheck:
    """一次包络校验的结果。"""

    ok: bool = True
    n_checked: int = 0
    n_outside: int = 0
    offenders: list[tuple[str, int, float]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def add(self, name: str, idx: int, value: float) -> None:
        self.n_outside += 1
        if len(self.offenders) < 20:
            self.offenders.append((name, idx, value))

    def describe(self) -> str:
        head = "OK" if self.ok else f"⚠️ {self.n_outside}/{self.n_checked} 越界"
        return (f"{head}; offenders={[(n, i, round(v, 4)) for n, i, v in self.offenders[:5]]}")


def check_values(axes: dict | None = None, fields: dict | None = None, *,
                 envelope: Envelope | None = None,
                 log10_flags: dict | None = None) -> EnvelopeCheck:
    """校验轴与场的量级是否落在包络内。

    :param log10_flags: ``{name: bool}`` —— 标记该量是**以 log10 存储**的
      （此时先 ``10**`` 还原成物理量再比）
    """
    env = envelope or DEFAULT_ENVELOPE
    res = EnvelopeCheck()
    flags = log10_flags or {}

    ranges = {
        "rho": (env.rho_min, env.rho_max),
        "Te": (env.te_min, env.te_max),
        "T": (env.te_min, env.te_max),
        "P": (env.p_min, env.p_max),
    }
    for src in (axes or {}, fields or {}):
        for name, values in src.items():
            if name not in ranges:
                continue
            lo, hi = ranges[name]
            for i, v in enumerate(values):
                res.n_checked += 1
                if flags.get(name):
                    # log10 存储 → 先还原成物理量；溢出/下溢按越界处理，不抛异常
                    try:
                        x = 10.0 ** v if -320.0 < v < 320.0 else (
                            float("inf") if v >= 320.0 else 0.0)
                    except OverflowError:  # pragma: no cover
                        x = float("inf")
                else:
                    x = v
                if x != x or x in (float("inf"), float("-inf")):
                    if x in (float("inf"), float("-inf")):
                        res.add(name, i, x)
                    continue
                if not (lo <= x <= hi):
                    res.add(name, i, x)
            if res.n_outside:
                res.ok = False
                res.notes.append(
                    f"{name} 有 {res.n_outside} 个点越出 [{lo:g},{hi:g}]"
                )
    if not res.n_checked:
        res.notes.append("无可校验的量（包络未参与判定）")
    res.notes.append(f"所用包络: {env.describe()}")
    return res
