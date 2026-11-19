"""fe_file.py — FLYCHK 非麦克斯韦电子分布 (EEDF/beam) ``fe`` 文件生成器。

FLYCHK 关键字 ``fe file <filename>`` 读入非麦克斯韦电子能量分布函数，
与背景热电子 (Maxwellian, 由主输入 te/ne 给出) 叠加计算能级布居与电离速率。

官方格式契约 (NIST fe help)::

    2 3                          <- 第1行: 时间步数 能量网格数
    4.49E+03 4.50E+03 4.51E+03   <- 第2行: 能量网格[eV], 只写一次, 每行<=120字符
    0.0E+00 1.0E+11              <- time[s] 与 束电子密度[#/cm^3] 同一行
    1.0E-20 1.49071E-03 1.0E-20  <- 该时间步 fe(E) [#/cm^3/eV^0.5], 折行<=120字符
    ...                          <- 逐时间步重复 (时间+密度一行, fe 一行)

约束: 能量网格点 <=500; 每行 <=120 字符; n(E)dE = sqrt(E)*fe(E)*dE;
麦克斯韦束 fe(E) = 2/sqrt(pi) * exp(-E/Te) / Te^1.5。

★★ **fe 文件内不得含任何注释行** (以 ``c`` / ``#`` 开头) ——
   NIST fe help 文档称 "以 c/# 开头的行会被忽略", 但 FLYCHK CX (7 Aug 2018)
   **实测不成立** (2026-11-19 实站提交验证, 两种位置都失败):
     (a) 注释在**首行** → 期望读两个整数 (时间步数/能量点数) 却读到注释,
         服务端**静默中止, 不产出任何结果**;
     (b) 注释在**数据头之后** → 服务端 info.dat 明确写
         ``Warning:Error in reading Fe file`` /
         ``Exiting:Difficulty with feFILE: stop execution``。
   ⇒ 溯源信息 (comment) **不得写入 fe 文件**, 应由 manifest / 元数据承载。

本模块仅依赖标准库 (自包含纪律, 与 zip_writer 一致)。
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from ..config import ConfigError, ValidationReport
from ..builder import HistoryTable
from ..zip_writer import HistoryZipWriter

# ── 格式常量 ────────────────────────────────────────────────
MAX_ENERGY_POINTS = 500  # FLYCHK 能量网格点上限
MAX_LINE_CHARS = 120  # FLYCHK 每行字符上限
NORM_WARN_REL = 0.05  # 梯形积分归一偏差告警阈值 (5%)
VALUE_FMT = "%.6e"  # 与 zip_writer.render_data 一致的数值格式

MODELS = ("maxwell", "drift_maxwell", "mono")


class FeFileError(ValueError):
    """fe 文件构建/渲染失败。"""


# ══════════════════════════════════════════════════════════
# 输入规格 (两种模式)
# ══════════════════════════════════════════════════════════
@dataclass(frozen=True)
class FeModel:
    """解析模型输入 (模式一): 由束参数自动生成 fe(E)。

    - maxwell:       fe(E) = 2/sqrt(pi)*exp(-E/te)/te^1.5 (解析归一, 积分=n_beam)
    - drift_maxwell: E<=e0 为 0, E>e0 为 exp(-(E-e0)/te), 数值归一到 n_beam
    - mono:          以 e0 为中心、width 为标准差的高斯形状, 数值归一到 n_beam
    """

    te_beam: float  # eV, > 0
    beam_density: float  # #/cm^3, > 0 (常数束密度)
    times: Sequence[float] = ()  # s; 空 -> 单时间点 t=0
    densities: Optional[Sequence[float]] = None  # 逐时间点束密度; None -> 常数
    model: str = "maxwell"
    drift_energy: float = 0.0  # eV, drift_maxwell 的 E0
    mono_energy: float = 0.0  # eV, mono 的 E0
    mono_width: float = 1.0  # eV, mono 的高斯宽度
    normalize_to_density: bool = False  # True: 重标定到网格积分=n_beam


@dataclass(frozen=True)
class FeExplicitSeries:
    """显式数组输入 (模式二): 用户直接提供分布数据。

    records 每项为 (time[s], beam_density[#/cm^3], fe(E)[#/cm^3/eV^0.5])。
    """

    energies: Sequence[float]  # eV, 升序, <=500 点
    records: Sequence[Tuple[float, float, Sequence[float]]]


@dataclass
class FeFile:
    """构建结果容器 (可渲染、可校验)。"""

    energies: List[float]
    records: List[Tuple[float, float, List[float]]]
    comment: str = ""
    report: ValidationReport = field(default_factory=ValidationReport)
    meta: Dict[str, Any] = field(default_factory=dict)

    @property
    def n_energies(self) -> int:
        return len(self.energies)

    @property
    def n_steps(self) -> int:
        return len(self.records)

    def to_text(self) -> str:
        """渲染 fe 文件文本。

        ★ **不写入 comment** —— FLYCHK CX 不接受 fe 文件内的任何注释行
          (见模块 docstring)。comment 仅作为溯源信息保留在 ``meta["comment"]``。
        """
        return render_fe_text(self.energies, self.records)


# ══════════════════════════════════════════════════════════
# 解析模型 (纯函数)
# ══════════════════════════════════════════════════════════
def maxwell_fe(e: float, te: float) -> float:
    """麦克斯韦束分布: 2/sqrt(pi) * exp(-E/te) / te**1.5 (E, te 单位 eV)。

    解析归一性: ∫ sqrt(E) * fe dE = Γ(3/2)/Γ(3/2) = 1, 即积分 = 束密度。
    """
    if te <= 0:
        raise FeFileError(f"te_beam 必须为正, 当前 {te}")
    return 2.0 / math.sqrt(math.pi) * math.exp(-e / te) / te**1.5


def drift_maxwell_shape(e: float, te: float, e0: float) -> float:
    """漂移麦克斯韦形状 (未归一): E<=e0 为 0, E>e0 为 exp(-(E-e0)/te)。"""
    if e <= e0:
        return 0.0
    return math.exp(-(e - e0) / te)


def mono_shape(e: float, e0: float, width: float) -> float:
    """单能束高斯形状 (未归一), width 为数值化 δ 函数的标准差。"""
    if width <= 0:
        raise FeFileError(f"mono_width 必须为正, 当前 {width}")
    return math.exp(-0.5 * ((e - e0) / width) ** 2)


def _trapz_sqrt_e_fe(energies: Sequence[float], fe: Sequence[float]) -> float:
    """梯形积分 ∫ sqrt(E) * fe(E) dE (束密度估计)。"""
    total = 0.0
    for i in range(len(energies) - 1):
        e0, e1 = energies[i], energies[i + 1]
        f0 = math.sqrt(e0) * fe[i]
        f1 = math.sqrt(e1) * fe[i + 1]
        total += 0.5 * (f0 + f1) * (e1 - e0)
    return total


# ══════════════════════════════════════════════════════════
# 校验
# ══════════════════════════════════════════════════════════
def validate_fe_file(
    energies: Sequence[float],
    records: Sequence[Tuple[float, float, Sequence[float]]],
    model: str = "",
    te_beam: Optional[float] = None,
) -> ValidationReport:
    """校验 fe 数据。error 汇总进 report.errors, 由调用方 raise_if_bad() 决定。"""
    rep = ValidationReport()
    n_e = len(energies)

    if n_e == 0:
        rep.errors.append("能量网格为空")
    if n_e > MAX_ENERGY_POINTS:
        rep.errors.append(f"能量网格点数 {n_e} 超过 FLYCHK 上限 {MAX_ENERGY_POINTS}")
    for i, e in enumerate(energies):
        if not math.isfinite(e) or e <= 0:
            rep.errors.append(f"能量网格第 {i} 点非法 ({e}): 必须为正有限值")
    for i in range(n_e - 1):
        if energies[i + 1] <= energies[i]:
            rep.errors.append(f"能量网格非严格升序 (第 {i}->{i + 1} 点: " f"{energies[i]} -> {energies[i + 1]})")
            break

    if not records:
        rep.errors.append("时间步记录为空")
    prev_t: Optional[float] = None
    for k, (t, dens, fe) in enumerate(records):
        if not math.isfinite(t):
            rep.errors.append(f"时间步 {k} 的时间非法 ({t})")
        if prev_t is not None and t <= prev_t:
            rep.errors.append(f"时间步 {k} 时间 ({t}) 未严格大于前一步 ({prev_t})")
        prev_t = t
        if not math.isfinite(dens) or dens <= 0:
            rep.warnings.append(f"时间步 {k} 束密度 <= 0 ({dens}): 束关闭可能是合法物理, 请确认")
        if len(fe) != n_e:
            rep.errors.append(f"时间步 {k} fe 值个数 ({len(fe)}) 与能量点数 ({n_e}) 不一致")
            continue
        for i, v in enumerate(fe):
            if not math.isfinite(v):
                rep.errors.append(f"时间步 {k} fe 第 {i} 点非有限值 ({v})")
            elif v < 0:
                rep.errors.append(f"时间步 {k} fe 第 {i} 点为负 ({v})")

    if model and model not in MODELS:
        rep.errors.append(f"未知模型 '{model}', 可选: {MODELS}")
    if te_beam is not None and te_beam <= 0:
        rep.errors.append(f"te_beam 必须为正, 当前 {te_beam}")

    # 归一偏差检查 (梯形积分 vs 束密度); 能量网格非法时跳过 (已记 error)
    grid_ok = all(math.isfinite(e) and e > 0 for e in energies)
    devs: List[float] = []
    if grid_ok:
        for k, (t, dens, fe) in enumerate(records):
            if dens > 0 and len(fe) == n_e:
                integral = _trapz_sqrt_e_fe(energies, fe)
                dev = abs(integral - dens) / dens
                devs.append(dev)
                if dev > NORM_WARN_REL:
                    rep.warnings.append(
                        f"时间步 {k} 归一偏差 {dev:.1%} 超过 {NORM_WARN_REL:.0%}: "
                        "能量网格过粗或覆盖不足 (建议覆盖 0~10*Te 并在 E~Te 处加密)"
                    )
    if devs:
        rep.info["norm_deviation_max"] = max(devs)
    return rep


# ══════════════════════════════════════════════════════════
# 构建
# ══════════════════════════════════════════════════════════
def build_fe_file(spec: Any, energies: Optional[Sequence[float]] = None, *, comment: str = "") -> FeFile:
    """由 FeModel (解析) 或 FeExplicitSeries (显式) 构建 FeFile。

    模式一 (FeModel) 需传 energies; 模式二 (FeExplicitSeries) 从 spec 取。
    校验失败 (存在 error) 时抛 ConfigError。
    """
    if isinstance(spec, FeExplicitSeries):
        if energies is not None:
            raise FeFileError("FeExplicitSeries 模式 energies 由 spec 提供, " "不要重复传入")
        energies = list(spec.energies)
        records = [(float(t), float(d), [float(v) for v in fe]) for t, d, fe in spec.records]
        report = validate_fe_file(energies, records)
        meta: Dict[str, Any] = {"mode": "explicit"}
    elif isinstance(spec, FeModel):
        if energies is None:
            raise FeFileError("FeModel 模式必须显式传入 energies (eV)")
        energies = [float(e) for e in energies]
        records, report, meta = _build_from_model(spec, energies)
        meta["mode"] = "model"
    else:
        raise FeFileError(f"spec 必须为 FeModel 或 FeExplicitSeries, 当前 {type(spec).__name__}")

    report.raise_if_bad()
    meta.update(
        {
            "n_energies": len(energies),
            "n_steps": len(records),
            "max_line_chars": MAX_LINE_CHARS,
            # 溯源信息只进元数据, **不写入 fe 文件** (FLYCHK CX 不接受注释行)
            "comment": comment,
        }
    )
    return FeFile(energies=energies, records=records, comment=comment, report=report, meta=meta)


def _build_from_model(
    spec: FeModel,
    energies: List[float],
) -> Tuple[List[Tuple[float, float, List[float]]], ValidationReport, Dict[str, Any]]:
    """解析模型 -> fe records。maxwell 用解析归一, drift/mono 数值归一。"""
    # 模型参数预检 (走校验路径, 统一抛 ConfigError)
    pre_errors = []
    if spec.model not in MODELS:
        pre_errors.append(f"未知模型 '{spec.model}', 可选: {MODELS}")
    if spec.te_beam <= 0:
        pre_errors.append(f"te_beam 必须为正, 当前 {spec.te_beam}")
    if pre_errors:
        raise ConfigError("；".join(pre_errors))

    times = [float(t) for t in spec.times] or [0.0]
    if spec.densities is None:
        densities = [float(spec.beam_density)] * len(times)
    else:
        densities = [float(d) for d in spec.densities]
        if len(densities) != len(times):
            raise FeFileError(f"densities 长度 ({len(densities)}) 与 times ({len(times)}) 不一致")

    te = float(spec.te_beam)
    # 未乘密度的单位束密度形状 (积分应 = 1)
    if spec.model == "maxwell":
        shape = [maxwell_fe(e, te) for e in energies]
    elif spec.model == "drift_maxwell":
        if spec.drift_energy <= 0:
            raise FeFileError("drift_maxwell 需要 drift_energy > 0")
        shape = [drift_maxwell_shape(e, te, spec.drift_energy) for e in energies]
        integral = _trapz_sqrt_e_fe(energies, shape)
        if integral <= 0:
            raise FeFileError("drift_maxwell 形状积分为 0: 能量网格未覆盖 " f"(E > {spec.drift_energy} eV) 区间")
        shape = [v / integral for v in shape]
    elif spec.model == "mono":
        shape = [mono_shape(e, spec.mono_energy, spec.mono_width) for e in energies]
        integral = _trapz_sqrt_e_fe(energies, shape)
        if integral <= 0:
            raise FeFileError("mono 形状积分为 0: 能量网格未覆盖 " f"E = {spec.mono_energy} eV 附近")
        shape = [v / integral for v in shape]
    else:
        raise FeFileError(f"未知模型 '{spec.model}', 可选: {MODELS}")

    records: List[Tuple[float, float, List[float]]] = []
    for t, dens in zip(times, densities):
        fe = [dens * v for v in shape]
        if spec.normalize_to_density and dens > 0:
            integral = _trapz_sqrt_e_fe(energies, fe)
            if integral > 0:
                scale = dens / integral
                fe = [v * scale for v in fe]
        records.append((t, dens, fe))

    report = validate_fe_file(energies, records, model=spec.model, te_beam=te)
    meta = {"model": spec.model, "normalize_to_density": spec.normalize_to_density}
    return records, report, meta


# ══════════════════════════════════════════════════════════
# 渲染 (纯函数)
# ══════════════════════════════════════════════════════════
def _wrap_values(values: Sequence[float]) -> str:
    """数值序列 -> %.6e 空格分隔文本, 每行 <= MAX_LINE_CHARS (自由折行)。

    FLYCHK 按空白分隔自由格式读数, 且按首行给出的点数计数, 折行安全。
    """
    tokens = [VALUE_FMT % v for v in values]
    lines: List[str] = []
    cur: List[str] = []
    for tok in tokens:
        candidate = " ".join(cur + [tok])
        if cur and len(candidate) > MAX_LINE_CHARS:
            lines.append(" ".join(cur))
            cur = [tok]
        else:
            cur.append(tok)
    if cur:
        lines.append(" ".join(cur))
    return "\n".join(lines)


def render_fe_text(
    energies: Sequence[float], records: Sequence[Tuple[float, float, Sequence[float]]], comment: str = ""
) -> str:
    """渲染 fe 数据文件文本 (官方格式契约, 见模块 docstring)。

    ★★ **``comment`` 不写入文件**: FLYCHK CX (7 Aug 2018) 实测不接受任何注释行
      (首行注释 → 静默中止; 数据头后注释 → ``Error in reading Fe file`` 显式中止)。
      传入非空 ``comment`` 直接抛 ``FeFileError``, 强制调用方把溯源信息放进
      manifest / 元数据而非 fe 文件。保留该参数只为兼容旧调用签名。
    """
    if comment and comment.strip():
        raise FeFileError(
            "fe 文件不得含注释行 (FLYCHK CX 实测会中止执行): 请把溯源信息写入 "
            "manifest/元数据, 不要写入 fe 文件"
        )
    n_steps, n_e = len(records), len(energies)
    lines: List[str] = []
    lines.append(f"{n_steps} {n_e}")
    lines.append(_wrap_values([float(e) for e in energies]))
    for t, dens, fe in records:
        lines.append(" ".join([VALUE_FMT % float(t), VALUE_FMT % float(dens)]))
        lines.append(_wrap_values([float(v) for v in fe]))
    text = "\n".join(lines) + "\n"
    for ln in text.splitlines():
        if len(ln) > MAX_LINE_CHARS:
            raise FeFileError(f"渲染行超 {MAX_LINE_CHARS} 字符上限: {ln[:60]}...")
        if ln.lstrip()[:1] in ("c", "#"):
            raise FeFileError(f"fe 文件不得含注释行: {ln[:60]}")
    return text


def fe_filename_for(element: str, z: int) -> str:
    """fe 数据文件名 (与 history_{el}_Z{z}_input.txt 命名对齐)。"""
    return f"fe_{element}_Z{int(z)}_input.txt"


def write_history_zip_with_fe(table: HistoryTable, fe: FeFile, output_path: str) -> Path:
    """桥接便捷函数: 写出含 fe 成员的 FLYCHK history 输入 zip。

    FeFile -> 文本的转换在本侧完成, zip_writer 只接收原始字符串
    (禁止 zip_writer 反向依赖本子包)。
    """
    fe_filename = fe_filename_for(table.element, table.z)
    return HistoryZipWriter().write(table, output_path, fe_text=fe.to_text(), fe_filename=fe_filename)


__all__ = [
    "FeFileError",
    "FeModel",
    "FeExplicitSeries",
    "FeFile",
    "maxwell_fe",
    "drift_maxwell_shape",
    "mono_shape",
    "build_fe_file",
    "validate_fe_file",
    "render_fe_text",
    "fe_filename_for",
    "write_history_zip_with_fe",
    "MAX_ENERGY_POINTS",
    "MAX_LINE_CHARS",
    "NORM_WARN_REL",
    "MODELS",
]
