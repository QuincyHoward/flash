"""
gen_flychk_his — 由 FLASH 仿真数据生成 FLYCHK history 输入压缩包
================================================================

把 FLASH (1D) 剖面的时间序列转成 NIST FLYCHK 网站可上传的 **history 模式
输入 zip**（`runfile.txt` + 历史数据 txt），支持多区域批量与全流程可追溯。

依赖关系
--------
**完全自包含**：zip 写出由 `zip_writer.HistoryZipWriter` 独立完成，仅依赖
Python 标准库，不导入也不搜索任何外部 FLYCHK Python 包，便于 flash-sim
单独分发。写出格式遵循 FLYCHK history 模式官方输入契约
（``FORMAT_CONTRACT_ID = "flychk-history-v1"``，见 `zip_writer.py`）。

若本地另有 FLYCHK 官方小包并希望做**格式对拍**，可使用测试目录下的可选脚本
``test/cross_check_external.py``（该脚本不属于发布包，默认不参与测试）。

核心接口
--------
面向对象::

    from flash.input_gen.gen_flychk_his import FlychkHistoryGenerator

    gen = FlychkHistoryGenerator(element="Ti", agg="mass", n_time_max=8)
    report = gen.generate(source="run_dir/", region="x:-40..0um",
                          output_dir="out/")

一键函数::

    from flash.input_gen.gen_flychk_his import generate_history_zip

    zip_path = generate_history_zip(
        source="run_dir/", element="Ti", region="label:matid=2",
        output_dir="out/", columns=["time", "size", "te", "ti", "tr", "rho"])

命令行::

    python -m flash.input_gen.gen_flychk_his.cli --demo --out out/

接口多样性 (细节见 `README.md`)
-------------------------------
1. 数据源: FLASH HDF5 (文件/目录/glob/列表) / npz / csv / json / 内存字典 /
   快照列表 / callable / 合成数据
2. 区域: 对象 / 工厂函数 / 字符串 DSL / dict / 元组 / 自定义回调
3. 聚合: mean / median / mass / volume / max / min / center / peak_dens /
   percentile:NN / 自定义回调
4. 列组合: rho / ne / ni 三选一，size / ti / tr 可选，列序可自定义
5. size 策略: extent / scale_length_ne / scale_length_te / fixed
6. 时间: 单位换算 / 步长抽稀 / 上限抽稀 / 时间窗裁剪 / 非正时间剔除
7. 输出: flat / batch 布局，manifest.json，表文本，预诊断图，zipfiles 中转
8. 自检: 写出后回读 zip 与表内容逐字符核对 (``self_check=True``)，
   结论写入 manifest (`zip_integrity`)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union

from . import builder as _builder
from . import config as _config
from . import extract as _extract
from . import preview as _preview
from . import regions as _regions
from . import sources as _sources
from . import units as _units
from . import writer as _writer
from .builder import BuilderError, HistoryTable, build_table, validate_table
from .config import ConfigError, FlychkHisConfig, ValidationReport
from .extract import ExtractError, RegionSeries, extract_all, extract_region
from .preview import plot_input_preview, plot_region_overview
from .regions import RegionError, RegionSpec, parse_region, resolve_regions
from .sources import Snapshot, SnapshotSeries, load_series, synthetic_ch_ti_slab
from .writer import FlychkHistoryWriter, GenerationReport, RegionResult, WriterError
from .zip_writer import (FORMAT_CONTRACT_ID, WRITER_ID, HistoryZipWriter,
                         ZipWriterError, render_data, render_runfile,
                         verify_history_zip, write_history_zip)

__version__ = "0.1.0"

_CONFIG_FIELDS = {f for f in FlychkHisConfig.__dataclass_fields__}   # type: ignore[attr-defined]


def make_config(base: Optional[FlychkHisConfig] = None,
                **overrides: Any) -> FlychkHisConfig:
    """构造/派生配置；未知键给出明确错误 (避免静默忽略)。"""
    cfg = base or FlychkHisConfig()
    if not overrides:
        return cfg
    unknown = sorted(set(overrides) - _CONFIG_FIELDS)
    if unknown:
        raise ConfigError(
            f"未知配置项 {unknown}；可用: {sorted(_CONFIG_FIELDS)}"
        )
    return cfg.evolve(**overrides)


# ══════════════════════════════════════════════════════════
# 主门面
# ══════════════════════════════════════════════════════════
class FlychkHistoryGenerator:
    """FLASH 数据 → FLYCHK history 输入 zip 的最高层门面。

    典型用法::

        gen = FlychkHistoryGenerator(element="Ti", agg="mass")
        gen.load("run_dir/")                    # 只加载一次, 复用
        print(gen.inspect(region="whole"))      # 先诊断
        report = gen.generate(region=["x:-40..0um", "label:matid=2"],
                              output_dir="out/")
    """

    def __init__(self, config: Optional[FlychkHisConfig] = None, **overrides: Any):
        self.config = make_config(config, **overrides)
        self._series: Optional[SnapshotSeries] = None
        self._load_kwargs: Dict[str, Any] = {}

    # ── 配置 ────────────────────────────────────────────────
    def with_config(self, **overrides: Any) -> "FlychkHistoryGenerator":
        """返回带新配置的**新**生成器 (保持原对象不变)。"""
        new = FlychkHistoryGenerator(make_config(self.config, **overrides))
        new._series = self._series
        new._load_kwargs = dict(self._load_kwargs)
        return new

    # ── 数据 ────────────────────────────────────────────────
    def load(self, source: Any = None, *, force: bool = False,
             extraction_mode: str = "h5py", pattern: Optional[str] = None,
             times: Optional[Sequence[float]] = None,
             verbose: bool = True, **synthetic_kwargs) -> SnapshotSeries:
        """加载数据源 (带缓存; force=True 强制重载)。"""
        if self._series is not None and not force:
            return self._series
        self._load_kwargs = {"source": source, "extraction_mode": extraction_mode,
                             "pattern": pattern, "times": times,
                             "synthetic_kwargs": synthetic_kwargs}
        self._series = load_series(source, config=self.config,
                                   extraction_mode=extraction_mode,
                                   pattern=pattern, times=times,
                                   verbose=verbose, **synthetic_kwargs)
        return self._series

    @property
    def series(self) -> SnapshotSeries:
        if self._series is None:
            raise RuntimeError("尚未加载数据源，请先调用 load(source=...)")
        return self._series

    # ── 区域与表格 ──────────────────────────────────────────
    def region_specs(self, region: Any = None) -> List[RegionSpec]:
        return resolve_regions(region)

    def region_series(self, region: Any = None,
                      keep_masks: bool = False) -> List[RegionSeries]:
        specs = self.region_specs(region)
        return extract_all(self.series, specs, self.config, keep_masks=keep_masks)

    def tables(self, region: Any = None, source: Any = None,
               **load_kwargs: Any) -> List[HistoryTable]:
        """构建 (不写盘) 指定区域的 FLYCHK 表。"""
        if source is not None or self._series is None:
            self.load(source, **load_kwargs)
        return [build_table(rs, self.config) for rs in self.region_series(region)]

    def table_text(self, region: Any = None, source: Any = None,
                   **load_kwargs: Any) -> str:
        """返回首个区域的数据表文本 (FLYCHK 数据文件内容)。"""
        return self.tables(region, source=source, **load_kwargs)[0].to_text()

    def validate(self, region: Any = None, source: Any = None,
                 **load_kwargs: Any) -> List[ValidationReport]:
        """仅做校验 (不写盘)，返回每区域的校验报告。"""
        reports = [self.config.validate()]
        for tb in self.tables(region, source=source, **load_kwargs):
            reports.append(validate_table(tb, self.config))
        return reports

    # ── 诊断 ────────────────────────────────────────────────
    def inspect(self, region: Any = None, source: Any = None,
                show: int = 5, **load_kwargs: Any) -> Dict[str, Any]:
        """快速诊断: 数据源概况 + 每区域列范围 + 表预览 (不写盘)。"""
        if source is not None or self._series is None:
            self.load(source, **load_kwargs)
        s = self.series
        out: Dict[str, Any] = {
            "source": dict(s.meta),
            "n_time": s.n_time,
            "variables": s.variables,
            "time_span_s": [float(s.times[0]), float(s.times[-1])] if s.n_time else [],
            "x_range_cm": [float(s[0].x[0]), float(s[0].x[-1])] if s.n_time else [],
            "config": self.config.to_dict(),
            "config_report": self.config.validate().summary(),
            "regions": [],
        }
        for rs in self.region_series(region):
            entry = rs.diagnostics()
            try:
                tb = build_table(rs, self.config)
                rep = validate_table(tb, self.config)
                entry["table"] = {
                    "n_steps": tb.n_steps,
                    "columns": tb.columns,
                    "summary": tb.summary(),
                    "preview": tb.preview(show).splitlines(),
                }
                entry["validation"] = {"ok": rep.ok, "errors": rep.errors,
                                       "warnings": rep.warnings}
            except Exception as exc:                        # noqa: BLE001
                entry["table_error"] = f"{type(exc).__name__}: {exc}"
            out["regions"].append(entry)
        out["writer"] = {"id": WRITER_ID, "format_contract": FORMAT_CONTRACT_ID,
                         "self_contained": True}
        return out

    # ── 生成 ────────────────────────────────────────────────
    def generate(self, source: Any = None, region: Any = None,
                 output_dir: Optional[str] = None,
                 layout: str = "flat",
                 write_zip: bool = True,
                 write_table: Optional[bool] = None,
                 write_manifest: Optional[bool] = None,
                 write_preview: Optional[bool] = None,
                 self_check: bool = True,
                 strict: Optional[bool] = None,
                 stage_zipfiles: bool = False,
                 verbose: bool = True,
                 **load_kwargs: Any) -> GenerationReport:
        """端到端生成: 加载 → 区域 → 聚合 → 建表 → 写 zip + 清单。

        Args:
            source: 数据源 (None 且已 load 则复用缓存; 两者皆无 → 合成数据)
            region: 区域描述 (None → whole)
            output_dir: 输出目录 (None → config.output_dir, 仍为空则报错)
            layout: "flat" | "batch"
            self_check: 写出后回读 zip 并与表内容逐字符核对
            stage_zipfiles: 额外复制 zip 到 ``<output_dir>/zipfiles/``
        """
        if source is not None or self._series is None:
            self.load(source, verbose=verbose, **load_kwargs)
        out_dir = output_dir or self.config.output_dir
        if not out_dir:
            raise WriterError(
                "必须给出 output_dir (参数或 config.output_dir)"
            )
        if verbose:
            print(f"  [配置] element={self.config.element} Z={self.config.resolved_z} "
                  f"columns={list(self.config.columns)} agg={self.config.agg} "
                  f"size={self.config.size_mode}")
        rseries = self.region_series(region)
        if verbose:
            for rs in rseries:
                print(f"  [区域] {rs.spec.describe()} → {len(rs)} 时间点, "
                      f"列 {sorted(rs.values)}")
        w = FlychkHistoryWriter(self.config)
        report = w.write(rseries, output_dir=str(out_dir), layout=layout,
                         source_meta=self.series.meta,
                         write_zip=write_zip, write_table=write_table,
                         write_manifest=write_manifest,
                         write_preview=write_preview,
                         self_check=self_check, strict=strict)
        if stage_zipfiles:
            FlychkHistoryWriter.stage_zipfiles(report)
        if verbose:
            print(report.summary())
        return report

    # ── 便捷: 单区域取首个 zip ──────────────────────────────
    def generate_zip(self, source: Any = None, region: Any = None,
                     output_dir: Optional[str] = None, **kwargs: Any) -> Path:
        """生成并返回**首个** zip 路径 (单区域场景最常用)。"""
        report = self.generate(source=source, region=region,
                               output_dir=output_dir, **kwargs)
        if not report.zip_paths:
            raise WriterError("未生成任何 zip：\n" + report.summary())
        return report.zip_paths[0]


# ══════════════════════════════════════════════════════════
# 一键函数
# ══════════════════════════════════════════════════════════
def generate_history_zip(source: Any = None, region: Any = None,
                         output_dir: Optional[str] = None,
                         config: Optional[FlychkHisConfig] = None,
                         layout: str = "flat",
                         data_kwargs: Optional[Dict[str, Any]] = None,
                         **overrides: Any) -> Path:
    """一键生成单个 FLYCHK history 输入 zip，返回 zip 路径。

    Args:
        source: 数据源 (None → 合成数据)
        region: 区域描述
        output_dir: 输出目录
        config: 基础配置 (None → 默认)
        layout: "flat" | "batch"
        data_kwargs: 透传给数据加载的参数 (如 ``{"n_time": 8}`` 给合成数据、
            ``{"extraction_mode": "yt"}`` 给 FLASH HDF5)
        **overrides: `FlychkHisConfig` 字段覆盖 (如 element/agg/n_time_max)

    示例::

        generate_history_zip("run_dir/", element="Ti", region="x:-40..0um",
                             output_dir="out/", n_time_max=8, agg="median")
    """
    gen = FlychkHistoryGenerator(config, **overrides)
    return gen.generate_zip(source=source, region=region,
                            output_dir=output_dir, layout=layout,
                            **(data_kwargs or {}))


def generate_history_zips(source: Any = None, region: Any = None,
                          output_dir: Optional[str] = None,
                          config: Optional[FlychkHisConfig] = None,
                          layout: str = "flat",
                          data_kwargs: Optional[Dict[str, Any]] = None,
                          **overrides: Any) -> List[Path]:
    """一键生成多区域 zip，返回 zip 路径列表。"""
    gen = FlychkHistoryGenerator(config, **overrides)
    report = gen.generate(source=source, region=region,
                          output_dir=output_dir, layout=layout,
                          **(data_kwargs or {}))
    return report.zip_paths


def generate_history_report(source: Any = None, region: Any = None,
                            output_dir: Optional[str] = None,
                            config: Optional[FlychkHisConfig] = None,
                            data_kwargs: Optional[Dict[str, Any]] = None,
                            **overrides: Any) -> GenerationReport:
    """一键生成并返回完整 `GenerationReport` (含 manifest 路径与校验)。"""
    gen = FlychkHistoryGenerator(config, **overrides)
    return gen.generate(source=source, region=region, output_dir=output_dir,
                        **(data_kwargs or {}))


def build_history_table(source: Any = None, region: Any = None,
                        config: Optional[FlychkHisConfig] = None,
                        data_kwargs: Optional[Dict[str, Any]] = None,
                        **overrides: Any) -> HistoryTable:
    """只建表不写盘，返回 `HistoryTable` (便于自检/单元测试)。"""
    gen = FlychkHistoryGenerator(config, **overrides)
    return gen.tables(region, source=source, **(data_kwargs or {}))[0]


def history_table_text(source: Any = None, region: Any = None,
                       config: Optional[FlychkHisConfig] = None,
                       data_kwargs: Optional[Dict[str, Any]] = None,
                       **overrides: Any) -> str:
    """返回 FLYCHK 数据文件文本 (不写盘)。"""
    return build_history_table(source, region, config,
                               data_kwargs=data_kwargs, **overrides).to_text()


def inspect_source(source: Any = None,
                   config: Optional[FlychkHisConfig] = None,
                   data_kwargs: Optional[Dict[str, Any]] = None,
                   **overrides: Any) -> Dict[str, Any]:
    """数据源 + 区域 + 表的快速诊断 (不写盘)。"""
    gen = FlychkHistoryGenerator(config, **overrides)
    return gen.inspect(source=source, **(data_kwargs or {}))


def preview_input(table: HistoryTable, output_path,
                  element: Optional[str] = None,
                  z: Optional[int] = None) -> Path:
    """为一张表绘制预诊断图。"""
    return plot_input_preview(table, output_path, element=element, z=z)


# ══════════════════════════════════════════════════════════
# 区域预设
# ══════════════════════════════════════════════════════════
def layered_regions(n_layers: int = 4,
                    names: Optional[Sequence[str]] = None) -> List[RegionSpec]:
    """等厚分层区域预设 (由左到右)。"""
    if names is not None and len(names) != n_layers:
        raise RegionError(f"names 长度 {len(names)} ≠ n_layers {n_layers}")
    return [_regions.layer(i, n_layers,
                           name=(names[i] if names else f"layer{i + 1}"))
            for i in range(n_layers)]


def tracer_regions(field: str = "matid", values: Sequence[float] = (2,),
                   names: Optional[Sequence[str]] = None,
                   extra: Optional[Sequence[Any]] = None) -> List[RegionSpec]:
    """材料示踪层区域预设 (+ 可选附加区域)。"""
    vals = _atleast_1d(values)
    out: List[RegionSpec] = []
    for i, v in enumerate(vals):
        nm = names[i] if names and i < len(names) else f"{field}{v:g}"
        out.append(_regions.label(field, values=[v], name=nm))
    if extra:
        out.extend(parse_region(e) for e in extra)
    return out


def _atleast_1d(values: Any) -> List[float]:
    if isinstance(values, (int, float)):
        return [float(values)]
    return [float(v) for v in values]


# ══════════════════════════════════════════════════════════
# 接口目录 (自描述)
# ══════════════════════════════════════════════════════════
def describe_interfaces() -> str:
    """返回本包的接口清单 (便于自查"接口多样性"是否被满足)。"""
    import inspect as _inspect
    from . import extract as ex
    from .regions import REGION_KINDS
    from .sources import FIELD_ALIASES
    from .config import AGG_MODES, ALLOWED_COLUMNS, SIZE_MODES

    lines = [
        "=" * 76,
        "gen_flychk_his — 接口清单",
        "=" * 76,
        f"[一键函数] generate_history_zip / generate_history_zips / "
        f"generate_history_report / build_history_table / history_table_text / "
        f"inspect_source / preview_input",
        f"[类门面]  FlychkHistoryGenerator(config, **overrides) → "
        f"load / series / region_specs / region_series / tables / table_text / "
        f"validate / inspect / generate / generate_zip / with_config",
        f"[低层]    sources.load_series / extract.extract_all / "
        f"builder.build_table / writer.FlychkHistoryWriter / zip_writer.HistoryZipWriter",
        "",
        f"[数据源]  FLASH HDF5 (文件/目录/glob/路径列表) | npz | csv | json | "
        f"内存字典 | 快照字典列表 | callable | 合成数据(None)",
        f"          变量别名: {sorted(set(FIELD_ALIASES))}",
        f"[区域]    {list(REGION_KINDS)}",
        f"          DSL: whole | x:-40..0um | rho:0.1..10 | mass:0..0.5 | "
        f"label:matid=2 | label:cham>=0.5 | layer:1/4 | top:10% | index:0:60",
        f"[聚合]    {list(AGG_MODES)} | percentile:NN | 自定义 callable",
        f"[列]      {list(ALLOWED_COLUMNS)} (rho/ne/ni 三选一, 必含 time+te)",
        f"[size]    {list(SIZE_MODES)}",
        f"[时间]    time_unit / time_stride / n_time_max / tmin / tmax / "
        f"drop_nonpositive_time",
        f"[输出]    layout=flat|batch, manifest.json, 表文本, 预诊断图, "
        f"zipfiles 中转",
        f"[写出]    自包含 zip 写出器 (zip_writer, 仅标准库) + 回读自检 self_check\n"
        f"          格式契约: {FORMAT_CONTRACT_ID} (FLYCHK history 模式)",
        "=" * 76,
    ]
    return "\n".join(lines)


__all__ = [
    # 版本
    "__version__",
    # 配置
    "FlychkHisConfig", "ValidationReport", "ConfigError", "make_config",
    # 数据源
    "Snapshot", "SnapshotSeries", "load_series", "synthetic_ch_ti_slab",
    # 区域
    "RegionSpec", "RegionError", "parse_region", "resolve_regions",
    "layered_regions", "tracer_regions",
    # 提取 / 表
    "RegionSeries", "ExtractError", "extract_region", "extract_all",
    "HistoryTable", "BuilderError", "build_table", "validate_table",
    # 写出 (自包含)
    "HistoryZipWriter", "ZipWriterError", "write_history_zip",
    "verify_history_zip", "render_runfile", "render_data",
    "FORMAT_CONTRACT_ID", "WRITER_ID",
    "FlychkHistoryWriter", "GenerationReport", "RegionResult", "WriterError",
    # 绘图
    "plot_input_preview", "plot_region_overview", "preview_input",
    # 主入口
    "FlychkHistoryGenerator",
    "generate_history_zip", "generate_history_zips",
    "generate_history_report", "build_history_table", "history_table_text",
    "inspect_source", "describe_interfaces",
]
