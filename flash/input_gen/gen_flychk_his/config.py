"""
gen_flychk_his.config — 生成配置对象
====================================

`FlychkHisConfig` 汇集从 FLASH 数据到 FLYCHK history 输入 zip 的全部可调项。
所有默认值都在本文件集中定义，调用方通过关键字参数或 `dataclasses.replace`
派生新配置（配置对象本身不可变 `frozen=True`，避免跨调用污染）。

关键参数分组:
  元素/谱窗    element, z, atomic_weight, zeff
  列组合       columns, density_mode
  区域聚合     agg, weight, dens_cut
  物理钳位     te_floor/te_ceil, dens_floor/dens_ceil
  size 策略    size_mode, size_value, size_scale
  时间处理     time_unit, time_stride, n_time_max, tmin, tmax,
               drop_nonpositive_time
  输出控制     output_dir, zip_name_template, write_manifest, write_table,
               write_preview, self_check, strict
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field, replace
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from . import units

# ── FLYCHK history 数据文件允许的列 ─────────────────────────
# 依据 FLYCHK history 模式官方输入约束 (见 zip_writer.FORMAT_CONTRACT_ID):
#   - 必须含 'time' 与 'te'
#   - rho / ne / ni 三者最多出现其一
BASE_COLUMNS: Tuple[str, ...] = ("time", "size", "te", "ti", "tr")
DENSITY_COLUMNS: Tuple[str, ...] = ("rho", "ne", "ni")
ALLOWED_COLUMNS: Tuple[str, ...] = BASE_COLUMNS + DENSITY_COLUMNS
REQUIRED_COLUMNS: Tuple[str, ...] = ("time", "te")

DEFAULT_COLUMNS: Tuple[str, ...] = ("time", "size", "te", "ti", "tr", "rho")

# 聚合方式注册表 (extract.py 中实现具体函数，这里只声明可用名称)
AGG_MODES: Tuple[str, ...] = (
    "mean",        # 算术平均
    "median",      # 中位数 (抗离群)
    "mass",        # 质量加权平均 (权重 = dens * dx)
    "volume",      # 体积加权平均 (权重 = dx)
    "max",         # 极大值
    "min",         # 极小值
    "center",      # 区域几何中心最近单元
    "peak_dens",   # 区域密度最大处单元
)

SIZE_MODES: Tuple[str, ...] = (
    "extent",            # 区域物理厚度 (cm)
    "scale_length_ne",   # 电子密度梯度标长 ne/|dne/dx|
    "scale_length_te",   # 电子温度梯度标长 te/|dte/dx|
    "fixed",             # 固定值 (size_value)
)


class ConfigError(ValueError):
    """配置非法。"""


@dataclass(frozen=True)
class ValidationReport:
    """校验结果。`ok` 为 True 表示无 error (warning 允许存在)。"""

    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    info: Dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.errors

    def raise_if_bad(self) -> "ValidationReport":
        if self.errors:
            raise ConfigError("；".join(self.errors))
        return self

    def summary(self) -> str:
        parts = []
        if self.errors:
            parts.append(f"{len(self.errors)} error(s)")
        if self.warnings:
            parts.append(f"{len(self.warnings)} warning(s)")
        return "OK" if not parts else "，".join(parts)


@dataclass(frozen=True)
class FlychkHisConfig:
    """FLYCHK history 输入生成配置 (不可变)。"""

    # ── 元素 ────────────────────────────────────────────────
    element: str = "Ti"
    z: Optional[int] = None                 # None -> 查表
    atomic_weight: Optional[float] = None   # None -> 查表 (g/mol)
    zeff: Optional[float] = None            # rho->ne 换算用 (None -> 用 z)
    window: Optional[Tuple[float, float]] = None  # 谱窗记录 (eV)，仅入 manifest

    # ── 列组合 ──────────────────────────────────────────────
    columns: Sequence[str] = DEFAULT_COLUMNS
    density_mode: Optional[str] = None      # None -> 由 columns 推断

    # ── 区域聚合 ────────────────────────────────────────────
    agg: str = "mass"
    dens_cut: float = 0.0                   # 低于该质量密度的单元剔除 (g/cm^3)

    # ── 物理钳位 ────────────────────────────────────────────
    te_floor: float = 1.0                   # eV
    te_ceil: float = 1.0e5                  # eV
    dens_floor: float = 1.0e-9              # g/cm^3
    dens_ceil: float = 1.0e3                # g/cm^3

    # ── size 策略 ───────────────────────────────────────────
    size_mode: str = "extent"
    size_value: float = 1.0e-4              # cm, size_mode="fixed" 时生效
    size_scale: float = 1.0                 # 统一乘性修正
    size_floor: float = 1.0e-7              # cm, 下限保护
    size_cap_extent: bool = True            # 标长策略以区域厚度为上限

    # ── 时间处理 ────────────────────────────────────────────
    time_unit: str = "s"
    time_stride: int = 1
    n_time_max: int = 0                     # 0 = 不限制
    tmin: Optional[float] = None            # 与 time_unit 一致
    tmax: Optional[float] = None
    drop_nonpositive_time: bool = True      # FLYCHK history 需要 t > 0

    # ── 输入单位覆盖 (默认按 FLASH cgs/K) ───────────────────
    # 例: {"tele": "eV", "time": "ps", "nele": "m^-3"}
    input_units: Dict[str, str] = field(default_factory=dict)

    # ── 输出控制 ────────────────────────────────────────────
    output_dir: Optional[str] = None
    zip_name_template: str = "history_{label}_{element}_Z{z}_in_.zip"
    write_manifest: bool = True
    write_table: bool = True
    write_preview: bool = False

    # ── 严格模式: warning 提升为 error ──────────────────────
    strict: bool = False

    # ══════════════════════════════════════════════════════
    # 派生属性
    # ══════════════════════════════════════════════════════
    @property
    def resolved_z(self) -> int:
        if self.z is not None:
            return int(self.z)
        return units.element_z(self.element)

    @property
    def resolved_a(self) -> float:
        if self.atomic_weight is not None:
            return float(self.atomic_weight)
        return units.element_a(self.element)

    @property
    def resolved_zeff(self) -> float:
        """rho -> ne 换算所用的 Z_eff (默认取原子序数, 即全剥离)。"""
        return float(self.zeff) if self.zeff is not None else float(self.resolved_z)

    @property
    def resolved_density_mode(self) -> Optional[str]:
        """当前列组合使用的密度列 (无则 None)。"""
        if self.density_mode is not None:
            return self.density_mode
        present = [c for c in self.columns if c in DENSITY_COLUMNS]
        return present[0] if present else None

    @property
    def resolved_window(self) -> Optional[Tuple[float, float]]:
        if self.window is not None:
            return tuple(self.window)  # type: ignore[return-value]
        return units.element_window(self.element, "he")

    def column_unit(self, column: str) -> str:
        """返回列在 FLYCHK 输入中的输出单位 (固定, 不因输入单位改变)。"""
        return {
            "time": "s", "size": "cm", "te": "eV", "ti": "eV", "tr": "eV",
            "rho": "g/cm^3", "ne": "cm^-3", "ni": "cm^-3",
        }[column]

    def source_unit(self, field_name: str, default: str) -> str:
        """返回某物理量在**输入数据**中的单位 (可被 input_units 覆盖)。"""
        return self.input_units.get(field_name, default)

    # ══════════════════════════════════════════════════════
    # 校验
    # ══════════════════════════════════════════════════════
    def validate(self) -> ValidationReport:
        errors: List[str] = []
        warnings: List[str] = []

        # 列的合法性
        cols = [str(c).strip().lower() for c in self.columns]
        if not cols:
            errors.append("columns 不能为空")
        unknown = [c for c in cols if c not in ALLOWED_COLUMNS]
        if unknown:
            errors.append(
                f"未知列 {unknown}；FLYCHK history 允许: {list(ALLOWED_COLUMNS)}"
            )
        for req in REQUIRED_COLUMNS:
            if req not in cols:
                errors.append(f"columns 必须包含 '{req}'")
        dens_present = [c for c in cols if c in DENSITY_COLUMNS]
        if len(dens_present) > 1:
            errors.append(
                f"rho/ne/ni 只能出现一种，当前包含 {dens_present}"
                "（FLYCHK runfile 仅接受单一密度基准）"
            )
        if len(set(cols)) != len(cols):
            errors.append(f"columns 存在重复项: {cols}")

        # 元素
        try:
            self.resolved_z
        except ValueError as exc:
            errors.append(f"元素解析失败: {exc}")
        try:
            self.resolved_a
        except ValueError as exc:
            warnings.append(f"原子量解析失败，rho->ne 换算将不可用: {exc}")

        # 聚合 / size / 后端
        if self.agg not in AGG_MODES:
            errors.append(f"agg='{self.agg}' 不合法，可选: {list(AGG_MODES)}")
        if self.size_mode not in SIZE_MODES:
            errors.append(f"size_mode='{self.size_mode}' 不合法，可选: {list(SIZE_MODES)}")

        # 数值范围
        if self.te_floor <= 0:
            errors.append(f"te_floor 必须 > 0，当前 {self.te_floor}")
        if self.te_ceil <= self.te_floor:
            errors.append("te_ceil 必须大于 te_floor")
        if self.dens_floor <= 0:
            errors.append(f"dens_floor 必须 > 0，当前 {self.dens_floor}")
        if self.dens_ceil <= self.dens_floor:
            errors.append("dens_ceil 必须大于 dens_floor")
        if self.dens_cut < 0:
            errors.append(f"dens_cut 不能为负，当前 {self.dens_cut}")
        if self.dens_cut and self.dens_cut < self.dens_floor:
            warnings.append(
                f"dens_cut ({self.dens_cut:g}) < dens_floor ({self.dens_floor:g})，"
                "剔除阈值实际不会生效"
            )
        if self.size_scale <= 0:
            errors.append(f"size_scale 必须 > 0，当前 {self.size_scale}")
        if self.size_mode == "fixed" and self.size_value <= 0:
            errors.append(f"size_mode='fixed' 时 size_value 必须 > 0，"
                          f"当前 {self.size_value}")
        if self.time_stride < 1:
            errors.append(f"time_stride 必须 >= 1，当前 {self.time_stride}")
        if self.n_time_max < 0:
            errors.append(f"n_time_max 不能为负，当前 {self.n_time_max}")
        if self.tmin is not None and self.tmax is not None and self.tmax <= self.tmin:
            errors.append("tmax 必须大于 tmin")

        # 时间单位 / 输入单位
        try:
            units.to_s(1.0, self.time_unit)
        except ValueError as exc:
            errors.append(str(exc))
        for fname, unit in self.input_units.items():
            try:
                if fname in ("tele", "tion", "trad", "te", "ti", "tr"):
                    units.to_ev(1.0, unit)
                elif fname in ("dens", "rho"):
                    units.to_dens_cgs(1.0, unit)
                elif fname in ("nele", "nion", "ne", "ni"):
                    units.to_numdens_cgs(1.0, unit)
                elif fname in ("x", "size"):
                    units.to_cm(1.0, unit)
                elif fname == "time":
                    units.to_s(1.0, unit)
                else:
                    warnings.append(f"input_units 中的 '{fname}' 不是已知物理量，将被忽略")
            except ValueError as exc:
                errors.append(f"input_units['{fname}'] 非法: {exc}")

        # 提示性告警
        if self.resolved_density_mode is None:
            # 必需: 无密度列时 runfile 不会写出 'history <data> <mode>' 行,
            # FLYCHK 根本不会读取数据文件 -> 输入无效
            errors.append(
                "columns 必须包含 rho/ne/ni 之一：FLYCHK runfile 通过 "
                "'history <datafile> <mode>' 关联数据文件，缺密度列时数据文件不会被读取"
            )
        if "size" not in cols:
            warnings.append(
                "列组合中不含 'size'：runfile 不会写 'opacity file'，"
                "FLYCHK 无法输出不透明度 (tau)"
            )
        if self.n_time_max == 0:
            warnings.append(
                "n_time_max=0（不限制时间步数）：FLYCHK 网站对 history 时间步数"
                "有限制，建议通过 n_time_max 控制（经验上限 ~50）"
            )
        if self.size_mode.startswith("scale_length"):
            warnings.append(
                f"size_mode='{self.size_mode}' 时非单调/近平坦剖面会给出极大标长，"
                "输出已按 size_floor 与区域厚度双重保护，建议核对 manifest 中的 size 值"
            )

        if self.strict:
            errors.extend(warnings)
            warnings = []

        return ValidationReport(errors=errors, warnings=warnings,
                                info=self.to_dict())

    # ══════════════════════════════════════════════════════
    # 序列化
    # ══════════════════════════════════════════════════════
    def to_dict(self) -> Dict[str, Any]:
        d = dataclasses.asdict(self)
        d["columns"] = list(self.columns)
        d["resolved"] = {
            "z": self.resolved_z if self.z is not None or _z_ok(self.element) else None,
            "atomic_weight": self.resolved_a if _a_ok(self) else None,
            "density_mode": self.resolved_density_mode,
            "window": list(self.resolved_window) if self.resolved_window else None,
        }
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FlychkHisConfig":
        """从字典构造 (忽略 'resolved' 等只读派生键)。"""
        payload = {k: v for k, v in dict(data).items()
                   if k in {f.name for f in dataclasses.fields(cls)}}
        if "columns" in payload and payload["columns"] is not None:
            payload["columns"] = list(payload["columns"])
        if "input_units" in payload and payload["input_units"] is None:
            payload["input_units"] = {}
        return cls(**payload)

    def evolve(self, **changes: Any) -> "FlychkHisConfig":
        """派生新配置 (不可变语义的安全修改入口)。"""
        return replace(self, **changes)

    def with_density(self, mode: str,
                     drop: bool = True) -> "FlychkHisConfig":
        """切换密度列 (rho/ne/ni)，自动替换 columns 中原密度列。"""
        mode = str(mode).strip().lower()
        if mode not in DENSITY_COLUMNS:
            raise ConfigError(f"密度模式必须是 {list(DENSITY_COLUMNS)}，当前 '{mode}'")
        cols = [c for c in self.columns]
        others = [c for c in cols if c not in DENSITY_COLUMNS]
        if drop:
            new_cols = others + [mode]
        else:
            new_cols = cols + [mode] if mode not in cols else cols
        return replace(self, columns=new_cols, density_mode=mode)

    def with_size(self, mode: str, **kw: Any) -> "FlychkHisConfig":
        """切换 size 策略；mode='fixed' 时可用 value=... 指定数值 (cm)。"""
        if mode not in SIZE_MODES:
            raise ConfigError(f"size_mode 必须是 {list(SIZE_MODES)}，当前 '{mode}'")
        cols = list(self.columns)
        if "size" not in cols:
            cols.insert(1, "size")
        return replace(self, columns=cols, size_mode=mode, **kw)


def _z_ok(element: str) -> bool:
    try:
        units.element_z(element)
        return True
    except ValueError:
        return False


def _a_ok(cfg: FlychkHisConfig) -> bool:
    try:
        cfg.resolved_a
        return True
    except ValueError:
        return False


__all__ = [
    "FlychkHisConfig", "ValidationReport", "ConfigError",
    "ALLOWED_COLUMNS", "BASE_COLUMNS", "DENSITY_COLUMNS", "REQUIRED_COLUMNS",
    "DEFAULT_COLUMNS", "AGG_MODES", "SIZE_MODES",
]
