"""
gen_flychk_his.writer — 写出 FLYCHK 输入 zip 与清单
====================================================

负责把多区域表写出成 FLYCHK 可上传的 zip 文件，并生成:

- ``manifest.json``  全量可追溯信息 (源文件、区域定义、配置、写出器与格式契约、
  时间步统计、钳位/插值计数、校验结果、zip 自检结论)
- ``<label>_history.txt``  表文本 (便于人工核查)
- ``<label>_preview.png``  输入预诊断图 (见 `preview.py`)

写出与自检均由 `zip_writer.HistoryZipWriter` 完成 —— **完全自包含**，
不依赖任何外部 FLYCHK Python 包。

两种目录布局 (`layout`):

``flat``   全部 zip 平铺在 output_dir
``batch``  按 FLYCHK 场景约定放入 ``input/batch_0000/``
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import numpy as np

from .builder import HistoryTable, validate_table
from .config import FlychkHisConfig, ValidationReport
from .extract import RegionSeries
from .zip_writer import (FORMAT_CONTRACT_ID, WRITER_ID, HistoryZipWriter,
                         ZipWriterError)

LAYOUTS = ("flat", "batch")


class WriterError(RuntimeError):
    """写出过程失败。"""


def _jsonable(obj: Any) -> Any:
    """把 numpy / Path 等转为 JSON 可序列化对象。"""
    if isinstance(obj, dict):
        return {str(k): _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, Path):
        return str(obj)
    return obj


# ══════════════════════════════════════════════════════════
# 结果容器
# ══════════════════════════════════════════════════════════
@dataclass
class RegionResult:
    """单区域写出结果。"""

    region: str
    table: HistoryTable
    report: ValidationReport
    zip_path: Optional[Path] = None
    table_path: Optional[Path] = None
    preview_path: Optional[Path] = None
    skipped: bool = False
    error: Optional[str] = None
    integrity: Dict[str, Any] = field(default_factory=dict)
    diagnostics: Dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return (not self.skipped and self.error is None and self.report.ok
                and self.integrity.get("ok", True))

    def to_dict(self) -> Dict[str, Any]:
        return _jsonable({
            "region": self.region,
            "zip_path": self.zip_path,
            "table_path": self.table_path,
            "preview_path": self.preview_path,
            "n_steps": self.table.n_steps if self.table else 0,
            "columns": self.table.columns if self.table else [],
            "table_meta": self.table.meta if self.table else {},
            "validation": {
                "ok": self.report.ok,
                "errors": self.report.errors,
                "warnings": self.report.warnings,
                "info": self.report.info,
            },
            "zip_integrity": self.integrity,
            "skipped": self.skipped,
            "error": self.error,
            "diagnostics": self.diagnostics,
        })


@dataclass
class GenerationReport:
    """整批写出结果。"""

    results: List[RegionResult]
    output_dir: Path
    config: FlychkHisConfig
    manifest_path: Optional[Path] = None
    source_meta: Dict[str, Any] = field(default_factory=dict)
    writer: Dict[str, Any] = field(default_factory=lambda: {
        "id": WRITER_ID, "format_contract": FORMAT_CONTRACT_ID,
        "self_contained": True,
    })

    @property
    def ok(self) -> bool:
        return bool(self.results) and all(r.ok for r in self.results)

    @property
    def zip_paths(self) -> List[Path]:
        return [r.zip_path for r in self.results if r.zip_path]

    @property
    def integrity_ok(self) -> Optional[bool]:
        """全部 zip 自检是否通过 (无 zip 被写出时返回 None)。"""
        checked = [r.integrity for r in self.results if r.integrity]
        if not checked:
            return None
        return all(bool(c.get("ok")) for c in checked)

    @property
    def errors(self) -> List[str]:
        out: List[str] = []
        for r in self.results:
            out.extend(f"[{r.region}] {e}" for e in r.report.errors)
            if r.error:
                out.append(f"[{r.region}] {r.error}")
            if r.integrity and not r.integrity.get("ok", True):
                out.append(f"[{r.region}] zip 自检失败: {r.integrity.get('detail')}")
        return out

    def to_dict(self) -> Dict[str, Any]:
        return _jsonable({
            "generator": WRITER_ID,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "output_dir": self.output_dir,
            "writer": self.writer,
            "config": self.config.to_dict(),
            "source": self.source_meta,
            "n_regions": len(self.results),
            "ok": self.ok,
            "zip_integrity_ok": self.integrity_ok,
            "regions": [r.to_dict() for r in self.results],
        })

    def summary(self) -> str:
        integ = self.integrity_ok
        lines = [f"GenerationReport: {len(self.results)} 区域, "
                 f"写出器={self.writer['id']} (自包含), "
                 f"zip 自检={'OK' if integ else ('-' if integ is None else 'FAIL')}, "
                 f"整体 {'OK' if self.ok else 'FAIL'}"]
        for r in self.results:
            status = "OK " if r.ok else "ERR"
            n = r.table.n_steps if r.table else 0
            lines.append(f"  [{status}] {r.region:<24s} {n:>3d} 步 → "
                         f"{Path(r.zip_path).name if r.zip_path else '-'}")
            for e in r.report.errors:
                lines.append(f"         ! {e}")
            for w in r.report.warnings:
                lines.append(f"         ~ {w}")
            if r.error:
                lines.append(f"         ! {r.error}")
        return "\n".join(lines)


# ══════════════════════════════════════════════════════════
# 写出器
# ══════════════════════════════════════════════════════════
class FlychkHistoryWriter:
    """把区域表批量写出为 FLYCHK 输入 zip + 清单 (自包含)。"""

    def __init__(self, config: Optional[FlychkHisConfig] = None,
                 zip_writer: Optional[HistoryZipWriter] = None):
        self.config = config or FlychkHisConfig()
        self.zip_writer = zip_writer or HistoryZipWriter()

    # ── 命名 ────────────────────────────────────────────────
    def zip_name(self, label: str) -> str:
        return self.config.zip_name_template.format(
            label=label, element=self.config.element, z=self.config.resolved_z)

    def _target_dir(self, output_dir: Path, index: int, layout: str) -> Path:
        if layout == "batch":
            return output_dir / "input" / f"batch_{index:04d}"
        if layout != "flat":
            raise WriterError(f"未知布局 '{layout}'，可选: {list(LAYOUTS)}")
        return output_dir

    # ── 主写出 ──────────────────────────────────────────────
    def write(self, region_series: Sequence[RegionSeries],
              output_dir: str,
              layout: str = "flat",
              source_meta: Optional[Dict[str, Any]] = None,
              write_zip: bool = True,
              write_table: Optional[bool] = None,
              write_manifest: Optional[bool] = None,
              write_preview: Optional[bool] = None,
              self_check: bool = True,
              strict: Optional[bool] = None) -> GenerationReport:
        """写出全部区域。

        Args:
            region_series: `extract.RegionSeries` 列表
            output_dir: 输出根目录
            layout: "flat" | "batch"
            source_meta: 源信息 (进 manifest)
            write_zip / write_table / write_manifest / write_preview:
                None → 取 config 中的对应开关
            self_check: 写出后回读 zip 并与表内容逐字符核对 (自包含完整性检查)
            strict: 覆盖 config.strict (校验告警是否升级为错误)
        """
        cfg = self.config if strict is None else self.config.evolve(strict=strict)
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        write_table = cfg.write_table if write_table is None else write_table
        write_manifest = cfg.write_manifest if write_manifest is None else write_manifest
        write_preview = cfg.write_preview if write_preview is None else write_preview

        results: List[RegionResult] = []
        for i, rs in enumerate(region_series):
            label = rs.spec.name
            target = self._target_dir(out, i, layout)
            target.mkdir(parents=True, exist_ok=True)
            res = self._write_one(rs, cfg, target, write_zip=write_zip,
                                  write_table=write_table,
                                  write_preview=write_preview,
                                  self_check=self_check)
            results.append(res)

        report = GenerationReport(results=results, output_dir=out, config=cfg,
                                  source_meta=dict(source_meta or {}))
        if write_manifest:
            report.manifest_path = self._write_manifest(report)
        return report

    # ── 单区域 ──────────────────────────────────────────────
    def _write_one(self, rs: RegionSeries, cfg: FlychkHisConfig, target: Path,
                   write_zip: bool, write_table: bool, write_preview: bool,
                   self_check: bool = True) -> RegionResult:
        label = rs.spec.name
        diagnostics = rs.diagnostics()
        try:
            table = self._build(rs, cfg)
        except Exception as exc:                       # noqa: BLE001
            return RegionResult(
                region=label, table=None,                 # type: ignore[arg-type]
                report=ValidationReport(errors=[f"{type(exc).__name__}: {exc}"]),
                error=str(exc), diagnostics=diagnostics, skipped=True,
            )

        report = validate_table(table, cfg)
        res = RegionResult(region=label, table=table, report=report,
                           diagnostics=diagnostics)

        base = self.zip_name(label).replace(".zip", "").rstrip("_")

        if write_table:
            tp = target / f"{base}.txt"
            tp.write_text(table.to_text(), encoding="utf-8", newline="\n")
            res.table_path = tp

        if write_zip and report.ok:
            try:
                res.zip_path = self.zip_writer.write(
                    table, str(target / self.zip_name(label)))
                if self_check:
                    res.integrity = self.zip_writer.verify_zip(
                        table, str(res.zip_path))
            except (ZipWriterError, OSError) as exc:
                res.error = f"{type(exc).__name__}: {exc}"
        elif write_zip:
            res.error = "校验未通过，已跳过 zip 写出"

        if write_preview and report.ok:
            try:
                from .preview import plot_input_preview
                res.preview_path = plot_input_preview(
                    table, target / f"{base}_preview.png",
                    element=cfg.element, z=cfg.resolved_z)
            except Exception as exc:                   # noqa: BLE001
                res.report.warnings.append(f"预览图生成失败: {exc}")

        return res

    def _build(self, rs: RegionSeries, cfg: FlychkHisConfig) -> HistoryTable:
        from .builder import build_table
        # 允许 per-call 覆盖列组合: RegionSeries 可能缺少某些列
        avail = set(rs.values)
        missing = [c for c in cfg.columns if c not in avail]
        if missing:
            raise WriterError(
                f"区域 '{rs.spec.name}' 缺少列 {missing}；该区域可用列 {sorted(avail)}"
            )
        return build_table(rs, cfg)

    # ── manifest ────────────────────────────────────────────
    def _write_manifest(self, report: GenerationReport) -> Path:
        path = report.output_dir / "manifest.json"
        path.write_text(
            json.dumps(report.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8", newline="\n")
        return path

    # ── 复制到 zipfiles/ (FLYCHK 场景约定) ──────────────────
    @staticmethod
    def stage_zipfiles(report: GenerationReport,
                       dest_dir: Optional[str] = None) -> List[Path]:
        """把生成的 zip 复制到 ``<output_dir>/zipfiles/`` (自动化脚本中转目录)。"""
        dest = Path(dest_dir) if dest_dir else report.output_dir / "zipfiles"
        dest.mkdir(parents=True, exist_ok=True)
        copied = []
        for p in report.zip_paths:
            tgt = dest / Path(p).name
            shutil.copy2(p, tgt)
            copied.append(tgt)
        return copied


__all__ = ["RegionResult", "GenerationReport", "FlychkHistoryWriter", "WriterError"]
