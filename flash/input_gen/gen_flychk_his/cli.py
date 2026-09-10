"""
gen_flychk_his.cli — 命令行入口
================================

示例::

    # 合成数据自检 (无需任何 FLASH 输出)
    python -m flash.input_gen.gen_flychk_his.cli --demo --out out/

    # 真实 FLASH 输出目录 + 多个区域
    python -m flash.input_gen.gen_flychk_his.cli \
        --source path/to/flash_output/ \
        --element Ti --columns time,size,te,ti,tr,rho \
        --region "x:-40..0um" --region "label:matid=2" \
        --agg mass --n-time-max 8 --dens-cut 1e-6 \
        --out out/ --preview --self-check

    # 只诊断不写盘
    python -m flash.input_gen.gen_flychk_his.cli --source out/ --inspect

    # 查看元素表 / 接口清单
    python -m flash.input_gen.gen_flychk_his.cli --list-elements
    python -m flash.input_gen.gen_flychk_his.cli --interfaces
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import __version__, describe_interfaces
from .config import AGG_MODES, SIZE_MODES
from .writer import FlychkHistoryWriter


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m flash.input_gen.gen_flychk_his.cli",
        description="由 FLASH 仿真数据生成 FLYCHK history 输入 zip",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=describe_interfaces(),
    )
    p.add_argument("--version", action="version", version=f"gen_flychk_his {__version__}")

    src = p.add_argument_group("数据源")
    src.add_argument("--source", default=None,
                     help="FLASH 输出 (文件/目录/glob) 或 npz/csv/json 文件; "
                          "省略则用合成数据")
    src.add_argument("--extraction-mode", default="h5py", choices=["h5py", "yt"],
                     help="FLASH HDF5 提取模式 (默认 h5py, 不需 yt)")
    src.add_argument("--pattern", default=None, help="目录源的 glob 覆盖")
    src.add_argument("--demo", action="store_true", help="使用合成数据 (等价 --source 省略)")
    src.add_argument("--n-time-demo", type=int, default=8,
                     help="合成数据的时间点数 (默认 8)")

    elem = p.add_argument_group("元素与列")
    elem.add_argument("--element", default="Ti", help="元素符号 (默认 Ti)")
    elem.add_argument("--z", type=int, default=None, help="原子序数 (默认查表)")
    elem.add_argument("--atomic-weight", type=float, default=None,
                      help="原子量 g/mol (rho->ne 换算用)")
    elem.add_argument("--zeff", type=float, default=None,
                      help="rho->ne 换算的平均电离电荷 (默认取 Z)")
    elem.add_argument("--columns", default="time,size,te,ti,tr,rho",
                      help="FLYCHK 列组合 (逗号分隔; rho/ne/ni 三选一)")
    elem.add_argument("--density-mode", default=None, choices=["rho", "ne", "ni"],
                      help="显式指定密度列 (默认由 --columns 推断)")

    reg = p.add_argument_group("区域与聚合")
    reg.add_argument("--region", action="append", default=None,
                     help="区域描述, 可重复 (DSL/字符串); 默认 whole。"
                          "例: 'x:-40..0um' 'label:matid=2' 'layer:1/4' 'top:10%'")
    reg.add_argument("--agg", default="mass",
                     help=f"聚合方式 {list(AGG_MODES)} 或 percentile:NN (默认 mass)")
    reg.add_argument("--dens-cut", type=float, default=0.0,
                     help="剔除低于该质量密度的单元 (g/cm^3, 默认 0=不剔除)")
    reg.add_argument("--size-mode", default="extent", choices=list(SIZE_MODES),
                     help="size 列策略 (默认 extent=区域厚度)")
    reg.add_argument("--size-value", type=float, default=None,
                     help="size_mode=fixed 时的 size 值 (cm)")
    reg.add_argument("--size-scale", type=float, default=None, help="size 乘性修正")

    tim = p.add_argument_group("时间处理")
    tim.add_argument("--time-unit", default="s",
                     help="输出时间单位 s/ps/ns/fs (默认 s, 与 FLYCHK 示例一致)")
    tim.add_argument("--time-stride", type=int, default=None, help="时间步抽稀步长")
    tim.add_argument("--n-time-max", type=int, default=None, help="时间步数上限")
    tim.add_argument("--tmin", type=float, default=None, help="时间下限 (同 --time-unit)")
    tim.add_argument("--tmax", type=float, default=None, help="时间上限 (同 --time-unit)")
    tim.add_argument("--keep-zero-time", action="store_true",
                     help="保留 t<=0 的时间点 (默认剔除, FLYCHK 需要 t>0)")

    ctl = p.add_argument_group("数值钳位")
    ctl.add_argument("--te-floor", type=float, default=None, help="Te 下限 (eV)")
    ctl.add_argument("--te-ceil", type=float, default=None, help="Te 上限 (eV)")
    ctl.add_argument("--dens-floor", type=float, default=None, help="密度下限 (g/cm^3)")
    ctl.add_argument("--dens-ceil", type=float, default=None, help="密度上限 (g/cm^3)")

    out = p.add_argument_group("输出")
    out.add_argument("--out", dest="output_dir", default=None, help="输出目录")
    out.add_argument("--layout", default="flat", choices=["flat", "batch"],
                     help="目录布局 (batch = input/batch_0000/)")
    out.add_argument("--zip-name", dest="zip_name_template", default=None,
                     help="zip 命名模板 (默认 history_{label}_{element}_Z{z}_in_.zip)")
    out.add_argument("--no-zip", action="store_true", help="只写表/清单, 不写 zip")
    out.add_argument("--no-manifest", action="store_true", help="不写 manifest.json")
    out.add_argument("--no-table", action="store_true", help="不写表文本")
    out.add_argument("--preview", action="store_true", help="生成预诊断图 png")
    out.add_argument("--stage-zipfiles", action="store_true",
                     help="额外复制 zip 到 <out>/zipfiles/")
    out.add_argument("--no-self-check", action="store_true",
                     help="关闭写出后回读 zip 的完整性自检 (默认开启)")
    out.add_argument("--strict", action="store_true", help="校验告警升级为错误")

    act = p.add_argument_group("自检动作 (不写盘)")
    act.add_argument("--inspect", action="store_true", help="打印诊断信息 (JSON)")
    act.add_argument("--list-elements", action="store_true", help="打印元素表")
    act.add_argument("--list-regions", action="store_true", help="打印可用区域类型")
    act.add_argument("--interfaces", action="store_true", help="打印接口清单")
    act.add_argument("--quiet", action="store_true", help="静默")
    return p


def _config_from_args(args: argparse.Namespace):
    from .config import FlychkHisConfig

    overrides: Dict[str, Any] = {
        "element": args.element,
    }
    if args.z is not None:
        overrides["z"] = args.z
    if args.atomic_weight is not None:
        overrides["atomic_weight"] = args.atomic_weight
    if args.zeff is not None:
        overrides["zeff"] = args.zeff
    if args.columns:
        overrides["columns"] = [c.strip() for c in args.columns.split(",") if c.strip()]
    if args.density_mode:
        overrides["density_mode"] = args.density_mode
    overrides["agg"] = args.agg
    overrides["dens_cut"] = args.dens_cut
    overrides["size_mode"] = args.size_mode
    if args.size_value is not None:
        overrides["size_value"] = args.size_value
    if args.size_scale is not None:
        overrides["size_scale"] = args.size_scale
    overrides["time_unit"] = args.time_unit
    if args.time_stride is not None:
        overrides["time_stride"] = args.time_stride
    if args.n_time_max is not None:
        overrides["n_time_max"] = args.n_time_max
    if args.tmin is not None:
        overrides["tmin"] = args.tmin
    if args.tmax is not None:
        overrides["tmax"] = args.tmax
    overrides["drop_nonpositive_time"] = not args.keep_zero_time
    if args.te_floor is not None:
        overrides["te_floor"] = args.te_floor
    if args.te_ceil is not None:
        overrides["te_ceil"] = args.te_ceil
    if args.dens_floor is not None:
        overrides["dens_floor"] = args.dens_floor
    if args.dens_ceil is not None:
        overrides["dens_ceil"] = args.dens_ceil
    if args.output_dir:
        overrides["output_dir"] = args.output_dir
    if args.zip_name_template:
        overrides["zip_name_template"] = args.zip_name_template
    overrides["write_manifest"] = not args.no_manifest
    overrides["write_table"] = not args.no_table
    overrides["write_preview"] = bool(args.preview)
    overrides["strict"] = bool(args.strict)
    return FlychkHisConfig(**overrides)


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)

    # ── 自检动作 ──
    if args.interfaces:
        print(describe_interfaces())
        return 0
    if args.list_regions:
        print(describe_interfaces())
        return 0
    if args.list_elements:
        from .units import element_table
        for el, info in element_table().items():
            win = info["window"] or {}
            wtxt = ", ".join(f"{k}=[{v[0]:g},{v[1]:g}]" for k, v in win.items()) or "-"
            print(f"{el:>3s}  Z={info['z']:>3d}  A={info['a']:<9g} window: {wtxt}")
        return 0
    cfg = _config_from_args(args)
    verbose = not args.quiet

    # ── 诊断 ──
    if args.inspect:
        from . import FlychkHistoryGenerator
        source = None if (args.demo or args.source is None) else args.source
        kwargs: Dict[str, Any] = {}
        if source is None:
            kwargs["n_time"] = args.n_time_demo
        gen = FlychkHistoryGenerator(cfg)
        info = gen.inspect(source=source, region=args.region or None,
                           verbose=False, **kwargs)
        print(json.dumps(info, indent=2, ensure_ascii=False, default=str))
        return 0

    # ── 生成 ──
    from . import FlychkHistoryGenerator

    if args.source is None and not args.demo:
        if verbose:
            print("[提示] 未给出 --source，使用合成数据 (解析模型) 自检")
    source = None if (args.demo or args.source is None) else args.source
    load_kwargs: Dict[str, Any] = {"extraction_mode": args.extraction_mode,
                                   "pattern": args.pattern}
    if source is None:
        load_kwargs["n_time"] = args.n_time_demo

    if args.output_dir is None:
        print("[错误] 需要 --out 指定输出目录", file=sys.stderr)
        return 2

    gen = FlychkHistoryGenerator(cfg)
    report = gen.generate(source=source, region=args.region or None,
                          output_dir=args.output_dir, layout=args.layout,
                          write_zip=not args.no_zip,
                          self_check=not args.no_self_check,
                          stage_zipfiles=args.stage_zipfiles,
                          verbose=verbose, **load_kwargs)

    if verbose:
        print(f"\n[完成] {len(report.zip_paths)} 个 zip → {Path(args.output_dir)}")
        if report.manifest_path:
            print(f"[清单] {report.manifest_path}")
    if report.integrity_ok is not None:
        print(f"[自检] zip 回读与表内容一致: {report.integrity_ok}")
    return 0 if report.ok else 1


if __name__ == "__main__":       # pragma: no cover
    sys.exit(main())
