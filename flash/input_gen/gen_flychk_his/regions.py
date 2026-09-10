"""
gen_flychk_his.regions — 区域 (空间子域) 选择策略
================================================

FLYCHK history 模式每次提交只能描述**一个**空间点的时间演化，因此必须先把
FLASH 的 1D 剖面按物理意义切成区域（如"示踪层"、"烧蚀区"、"电晕区"），
每个区域聚合出一条 (t, te, rho, ...) 曲线。

本模块提供**三种接口**描述同一个区域:

1. 对象式: ``RegionSpec`` (显式、可序列化，进 manifest)
2. 工厂函数式: ``whole() / x_range() / dens_range() / mass_range() /
   label() / layer() / top_fraction() / index_slice() / custom()``
3. 字符串 DSL 式: ``parse_region("x:[-40,0]um")`` —— 便于 CLI / 配置文件

DSL 一览 (区域按**逐时间步重新计算**，故材料/波前会随之移动)::

    whole                    全部单元
    x:-40..0um               坐标区间 (支持 cm/mm/um/nm, 默认 cm)
    rho:0.1..10              质量密度区间 (g/cm^3)
    mass:0..0.5              归一化质量坐标区间 (0~1, 由左端累计)
    label:matid=2            材料标签等值选择 (可多值 2,3)
    label:cham>=0.5          质量分数阈值选择
    layer:1/4                等厚分层中的第 1 层 (1-based, 共 4 层)
    top:10%                  密度最高的 10% 单元 (可 top:10%@tele)
    index:0:60               按 x 升序的索引切片 (start:stop[:step])
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np

from . import units
from .sources import Snapshot

# 支持的区域类型
REGION_KINDS = (
    "whole",        # 全部
    "x_range",      # 坐标区间
    "dens_range",   # 质量密度区间
    "mass_range",   # 归一化质量坐标区间
    "label",        # 材料标签 / 质量分数
    "layer",        # 等厚分层
    "top_fraction",  # top-N% 单元
    "index_slice",  # 索引切片
    "custom",       # 自定义回调
)


class RegionError(ValueError):
    """区域定义或选择非法。"""


# ══════════════════════════════════════════════════════════
# RegionSpec
# ══════════════════════════════════════════════════════════
@dataclass(frozen=True)
class RegionSpec:
    """区域定义 (与时间无关的声明; 实际掩码逐时间步计算)。"""

    name: str
    kind: str
    params: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.kind not in REGION_KINDS:
            raise RegionError(
                f"未知区域类型 '{self.kind}'，可选: {list(REGION_KINDS)}"
            )

    # ── 掩码计算 ────────────────────────────────────────────
    def mask(self, snap: Snapshot,
             dens_cut: float = 0.0) -> np.ndarray:
        """返回该快照上的布尔掩码。区域为空时抛 `RegionError`。"""
        m = self._raw_mask(snap)
        if dens_cut > 0:
            dens = snap.get("dens")
            if dens is not None:
                m = m & (dens >= dens_cut)
        if not np.any(m):
            raise RegionError(
                f"区域 '{self.name}' ({self.kind} {self.params}) 在 "
                f"t={snap.time:.4e}s 处为空。诊断: x∈"
                f"[{snap.x[0]:.4e},{snap.x[-1]:.4e}]cm, "
                f"dens∈[{np.nanmin(snap.get('dens', np.array([np.nan]))):.3e},"
                f"{np.nanmax(snap.get('dens', np.array([np.nan]))):.3e}]g/cc, "
                f"变量={sorted(snap.fields)}"
            )
        return m

    def _raw_mask(self, snap: Snapshot) -> np.ndarray:
        x = snap.x
        k = self.kind
        p = self.params

        if k == "whole":
            return np.ones(x.size, dtype=bool)

        if k == "x_range":
            return (x >= p["lo"]) & (x <= p["hi"])

        if k == "dens_range":
            dens = snap.get("dens")
            if dens is None:
                raise RegionError(f"区域 '{self.name}' 需要 'dens' 变量，但数据中不存在")
            return (dens >= p["lo"]) & (dens <= p["hi"])

        if k == "mass_range":
            m = mass_coordinate(snap)
            frac = np.concatenate(([0.0], np.cumsum(m))) 
            total = frac[-1]
            if total <= 0:
                raise RegionError(f"区域 '{self.name}': 总质量为零，无法定义质量坐标")
            frac = frac[:-1] / total          # 左端累计分数 (单元左边界)
            return (frac >= p["lo"]) & (frac < p["hi"]) if p["hi"] < 1.0 else \
                (frac >= p["lo"]) & (frac <= p["hi"])

        if k == "label":
            field_name = p["field"]
            arr = snap.get(field_name)
            if arr is None:
                raise RegionError(
                    f"区域 '{self.name}' 需要变量 '{field_name}'，"
                    f"数据中只有 {sorted(snap.fields)}"
                )
            if "values" in p:
                tol = float(p.get("tol", 1e-6))
                mask = np.zeros(x.size, dtype=bool)
                for v in p["values"]:
                    mask |= np.abs(arr - float(v)) <= tol
                return mask
            if "above" in p:
                return arr >= float(p["above"])
            if "below" in p:
                return arr <= float(p["below"])
            raise RegionError(f"区域 '{self.name}': label 需给出 values/above/below")

        if k == "layer":
            n = int(p["n_layers"])
            i = int(p["index"])
            if not (0 <= i < n):
                raise RegionError(f"层索引 {i} 超出 [0, {n - 1}]")
            lo = x[0] + (x[-1] - x[0]) * i / n
            hi = x[0] + (x[-1] - x[0]) * (i + 1) / n
            return (x >= lo) & (x < hi if i < n - 1 else x <= hi)

        if k == "top_fraction":
            by = p.get("by", "dens")
            arr = snap.get(by)
            if arr is None:
                raise RegionError(f"区域 '{self.name}' 需要变量 '{by}'")
            frac = float(p["frac"])
            if not (0 < frac <= 1):
                raise RegionError(f"top_fraction 的 frac 必须在 (0,1]，当前 {frac}")
            n_keep = max(1, int(round(frac * x.size)))
            order = np.argsort(-arr, kind="stable")[:n_keep]
            mask = np.zeros(x.size, dtype=bool)
            mask[order] = True
            return mask

        if k == "index_slice":
            mask = np.zeros(x.size, dtype=bool)
            idx = np.arange(x.size)[slice(p.get("start"), p.get("stop"), p.get("step"))]
            mask[idx] = True
            return mask

        if k == "custom":
            fn = p["fn"]
            mask = np.asarray(fn(snap), dtype=bool).ravel()
            if mask.size != x.size:
                raise RegionError(
                    f"区域 '{self.name}': 自定义掩码长度 {mask.size} ≠ 单元数 {x.size}"
                )
            return mask

        raise RegionError(f"未实现区域类型 '{k}'")   # pragma: no cover

    # ── 序列化 ──────────────────────────────────────────────
    def to_dict(self) -> Dict[str, Any]:
        p = {k: (v if not callable(v) else f"<callable {getattr(v, '__name__', 'fn')}>")
             for k, v in self.params.items()}
        return {"name": self.name, "kind": self.kind, "params": p}

    @classmethod
    def from_dict(cls, doc: Dict[str, Any]) -> "RegionSpec":
        return cls(name=doc.get("name", "region"), kind=doc["kind"],
                   params=dict(doc.get("params", {})))

    def describe(self) -> str:
        return f"{self.name} [{self.kind}: {self.params}]"


# ══════════════════════════════════════════════════════════
# 物理辅助
# ══════════════════════════════════════════════════════════
def mass_coordinate(snap: Snapshot, per_area: bool = True) -> np.ndarray:
    """单元质量 (g/cm^2, 1D 单位面积) = dens * width。"""
    dens = snap.get("dens")
    if dens is None:
        raise RegionError("质量坐标需要 'dens' 变量")
    return dens * snap.cell_widths()


# ══════════════════════════════════════════════════════════
# 工厂函数
# ══════════════════════════════════════════════════════════
def whole(name: str = "whole") -> RegionSpec:
    """全区域。"""
    return RegionSpec(name=name, kind="whole")


def x_range(lo: float, hi: float, unit: str = "cm",
            name: Optional[str] = None) -> RegionSpec:
    """坐标区间 [lo, hi] (默认 cm)。"""
    lo_cm = float(units.to_cm(lo, unit))
    hi_cm = float(units.to_cm(hi, unit))
    if hi_cm <= lo_cm:
        raise RegionError(f"x_range 上界必须大于下界: {lo_cm} -> {hi_cm} cm")
    return RegionSpec(name=name or f"x_{lo:g}_{hi:g}{unit}",
                      kind="x_range", params={"lo": lo_cm, "hi": hi_cm, "unit": unit})


def dens_range(lo: float, hi: float = np.inf,
               name: Optional[str] = None) -> RegionSpec:
    """质量密度区间 [lo, hi] (g/cm^3)。"""
    return RegionSpec(name=name or f"rho_{lo:g}_{hi:g}",
                      kind="dens_range", params={"lo": float(lo), "hi": float(hi)})


def mass_range(lo: float = 0.0, hi: float = 1.0,
               name: Optional[str] = None) -> RegionSpec:
    """归一化质量坐标区间 (0~1，自左端累计)。"""
    if not (0.0 <= lo < hi <= 1.0):
        raise RegionError(f"mass_range 需满足 0<=lo<hi<=1，当前 {lo}..{hi}")
    return RegionSpec(name=name or f"mass_{lo:g}_{hi:g}",
                      kind="mass_range", params={"lo": float(lo), "hi": float(hi)})


def label(field_name: str, values: Optional[Sequence[float]] = None,
          above: Optional[float] = None, below: Optional[float] = None,
          tol: float = 1e-6, name: Optional[str] = None) -> RegionSpec:
    """按材料标签 (等值) 或质量分数 (阈值) 选择。"""
    params: Dict[str, Any] = {"field": field_name, "tol": tol}
    if values is not None:
        vals = [float(v) for v in np.atleast_1d(values)]
        params["values"] = vals
        label_name = name or f"{field_name}_{'-'.join(f'{v:g}' for v in vals)}"
    elif above is not None:
        params["above"] = float(above)
        label_name = name or f"{field_name}_ge{above:g}"
    elif below is not None:
        params["below"] = float(below)
        label_name = name or f"{field_name}_le{below:g}"
    else:
        raise RegionError("label() 需给出 values / above / below 之一")
    return RegionSpec(name=label_name, kind="label", params=params)


def layer(index: int, n_layers: int,
          name: Optional[str] = None) -> RegionSpec:
    """等厚分层中的第 index 层 (0-based)。"""
    if n_layers < 1:
        raise RegionError("n_layers 必须 >= 1")
    if not (0 <= int(index) < int(n_layers)):
        raise RegionError(f"层索引 {index} 超出 [0, {n_layers - 1}]")
    return RegionSpec(name=name or f"layer{index + 1}of{n_layers}", kind="layer",
                      params={"index": int(index), "n_layers": int(n_layers)})


def top_fraction(frac: float, by: str = "dens",
                 name: Optional[str] = None) -> RegionSpec:
    """按 `by` 变量取前 frac 比例的单元 (frac ∈ (0,1])。"""
    frac = float(frac)
    if not (0.0 < frac <= 1.0):
        raise RegionError(f"top_fraction 的 frac 必须在 (0,1]，当前 {frac}")
    return RegionSpec(name=name or f"top{frac:g}_{by}", kind="top_fraction",
                      params={"frac": frac, "by": by})


def index_slice(start: Optional[int] = None, stop: Optional[int] = None,
                step: Optional[int] = None,
                name: Optional[str] = None) -> RegionSpec:
    """按 x 升序的索引切片。"""
    return RegionSpec(name=name or "index_slice", kind="index_slice",
                      params={"start": start, "stop": stop, "step": step})


def custom(fn: Callable[[Snapshot], np.ndarray],
           name: str = "custom") -> RegionSpec:
    """自定义掩码回调: ``fn(snapshot) -> bool 数组``。"""
    if not callable(fn):
        raise RegionError("custom() 需要可调用对象")
    return RegionSpec(name=name, kind="custom", params={"fn": fn})


# ══════════════════════════════════════════════════════════
# 字符串 DSL 解析
# ══════════════════════════════════════════════════════════
_UNIT_RE = re.compile(r"(cm|mm|um|nm|micron)$", re.IGNORECASE)


def _parse_number(text: str) -> float:
    t = text.strip().replace("_", "").strip("[](){} \t")
    if t == "-":
        return -np.inf
    if t in ("", "+"):
        return np.inf
    try:
        return float(t)
    except ValueError:
        raise RegionError(f"无法解析数值 '{text}'")


def _split_range(spec: str) -> Tuple[float, float, str]:
    """解析 'lo..hi' / 'lo:hi' / 'lo,hi'，返回 (lo, hi, unit)。"""
    txt = spec.strip()
    unit = "cm"
    m = _UNIT_RE.search(txt)
    if m:
        unit = m.group(1)
        txt = txt[: m.start()].strip()
    for sep in ("..", ":", ","):
        if sep in txt:
            lo_s, hi_s = txt.split(sep, 1)
            lo = -np.inf if lo_s.strip() in ("", "-") else _parse_number(lo_s)
            hi = np.inf if hi_s.strip() in ("", "+") else _parse_number(hi_s)
            return lo, hi, unit
    val = _parse_number(txt)
    return val, val, unit


def parse_region(spec: Union[str, RegionSpec, Dict[str, Any], tuple, Callable],
                 name: Optional[str] = None) -> RegionSpec:
    """把多种描述形式统一解析为 `RegionSpec`。

    支持: RegionSpec (透传) / str DSL / dict / (lo, hi) 元组 (坐标区间 um? 否,
    默认 cm) / callable (自定义掩码)。
    """
    if isinstance(spec, RegionSpec):
        return spec
    if callable(spec) and not isinstance(spec, (str, dict, tuple)):
        return custom(spec, name=name or "custom")
    if isinstance(spec, dict):
        if "kind" in spec:
            r = RegionSpec.from_dict(spec)
            return r if name is None else RegionSpec(name=name, kind=r.kind,
                                                     params=r.params)
        # 形如 {"x": (-0.01, 0.0)} / {"dens": (0.1, 1.0)} 的简写
        for key, val in spec.items():
            k = str(key).lower()
            if k in ("x", "x_range"):
                lo, hi = val
                return x_range(lo, hi, unit=spec.get("unit", "cm"), name=name)
            if k in ("rho", "dens", "dens_range"):
                lo, hi = val
                return dens_range(lo, hi, name=name)
            if k in ("mass", "mass_range"):
                lo, hi = val
                return mass_range(lo, hi, name=name)
        raise RegionError(f"无法解析区域字典: {spec}")
    if isinstance(spec, tuple) and len(spec) == 2:
        return x_range(float(spec[0]), float(spec[1]), name=name)
    if not isinstance(spec, str):
        raise RegionError(f"无法解析区域定义: {spec!r}")

    # ── DSL ──
    txt = spec.strip()
    low = txt.lower()
    if low in ("whole", "all", "*", ""):
        return whole(name or "whole")

    if ":" not in txt:
        raise RegionError(
            f"无法解析区域字符串 '{spec}'；示例: 'whole' / 'x:-40..0um' / "
            "'rho:0.1..10' / 'mass:0..0.5' / 'label:matid=2' / 'layer:1/4' / "
            "'top:10%' / 'index:0:60'"
        )

    head, body = txt.split(":", 1)
    key = head.strip().lower()
    body = body.strip()

    if key == "x":
        lo, hi, unit = _split_range(body)
        return x_range(lo, hi, unit=unit, name=name)
    if key in ("rho", "dens"):
        lo, hi = _split_range(body)[:2]
        return dens_range(lo, hi, name=name)
    if key == "mass":
        lo, hi = _split_range(body)[:2]
        return mass_range(0.0 if np.isneginf(lo) else lo,
                          1.0 if np.isposinf(hi) else hi, name=name)
    if key == "label":
        m = re.match(r"^([A-Za-z_]\w*)\s*(==|>=|<=|=|>|<)\s*(.+)$", body)
        if not m:
            raise RegionError(f"label 语法应为 'label:field=value' / 'label:field>=thr'，"
                              f"当前 '{body}'")
        field_name, op, rhs = m.group(1), m.group(2), m.group(3)
        if op in ("=", "=="):
            vals = [float(v) for v in re.split(r"[,\s]+", rhs.strip()) if v]
            return label(field_name, values=vals, name=name)
        if op in (">=", ">"):
            return label(field_name, above=float(rhs), name=name)
        return label(field_name, below=float(rhs), name=name)
    if key == "layer":
        m = re.match(r"^(\d+)\s*/\s*(\d+)$", body)
        if not m:
            raise RegionError(f"layer 语法应为 'layer:1/4'，当前 '{body}'")
        return layer(int(m.group(1)) - 1, int(m.group(2)), name=name)
    if key == "top":
        m = re.match(r"^([\d.eE+-]+)\s*(%?)(?:\s*@\s*([A-Za-z_]\w*))?$", body)
        if not m:
            raise RegionError(f"top 语法应为 'top:10%' 或 'top:10%@tele'，当前 '{body}'")
        frac = float(m.group(1))
        if m.group(2) == "%":
            frac /= 100.0
        return top_fraction(frac, by=m.group(3) or "dens", name=name)
    if key == "index":
        parts = body.split(":")
        def _opt(s: str):
            s = s.strip()
            return None if s == "" else int(s)
        parts += [""] * (3 - len(parts))
        return index_slice(_opt(parts[0]), _opt(parts[1]), _opt(parts[2]), name=name)

    raise RegionError(f"未知区域前缀 '{key}'；支持 whole/x/rho/dens/mass/label/"
                      f"layer/top/index")


def resolve_regions(region: Any = None,
                    config: Optional[Any] = None) -> List[RegionSpec]:
    """把任意区域描述解析为 `RegionSpec` 列表。

    - None            → [whole()]
    - RegionSpec      → [spec]
    - str/dict/tuple/callable → 单个
    - 列表/元组序列    → 逐个解析
    - 多元素、元素为 dict 且含 'name' → 批量区域
    """
    if region is None:
        return [whole()]
    if isinstance(region, (list, tuple)) and not (
            isinstance(region, tuple) and len(region) == 2
            and all(isinstance(v, (int, float)) for v in region)):
        specs = [parse_region(r) for r in region]
        if not specs:
            raise RegionError("区域列表为空")
        return specs
    return [parse_region(region)]


__all__ = [
    "RegionSpec", "RegionError", "REGION_KINDS", "parse_region",
    "resolve_regions", "mass_coordinate",
    "whole", "x_range", "dens_range", "mass_range", "label", "layer",
    "top_fraction", "index_slice", "custom",
]
