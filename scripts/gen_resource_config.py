#!/usr/bin/env python3
"""生成 FLASH 资源配置控制文件 (脚本)

作用
====
按当前装置 (笔记本 / 台式机 / 超算) 自动探测总核数 → 分类装置 →
计算各维度的 MPI 进程数，并生成 flash 包运行时所读取的**控制文件**:

    ~/.physimx/flash_resource/resource_config.json

flash 包读取路径:
    flash.flash_run.env.resource_config.get_resource_config()   (场景引擎 simulator.py)
    flash.flash_run.env.env_manager.FlashEnvironment.get_effective_nproc()

装置分类 (按总核数):
    total_cpus < 10        → laptop   (笔记本)
    10 ≤ total_cpus < 30   → desktop  (台式机)
    total_cpus >= 30       → hpc      (超算/集群节点)

每装置每维度默认配置 (统一 80% CPU):

    device    1D             2D             3D
    --------  -------------  -------------  -------------
    laptop    80% / 1 并行   80% / 1 并行   80% / 1 并行
    desktop   80% / 2 并行   80% / 1 并行   80% / 1 并行
    hpc       80% / 3 并行   80% / 2 并行   80% / 1 并行

MPI 进程数公式 (每仿真作业):
    nproc = max(1, int(总核数 × CPU% / 100) ÷ 并行数)      # 取整

存放位置说明
============
本脚本位于仓库 `scripts/gen_resource_config.py` (与 check_env.py 等同级,
属环境工具脚本)。生成的控制文件写入用户级路径
`~/.physimx/flash_resource/resource_config.json`, 不进入版本库。

用法
====
    # 1) 探测本机并生成控制文件 (默认写入 ~/.physimx/...)
    python scripts/gen_resource_config.py

    # 2) 指定核数 / 强制装置类型
    python scripts/gen_resource_config.py --total-cpus 64 --device hpc

    # 3) 自定义 CPU 百分比 (覆盖所有装置, 默认 80)
    python scripts/gen_resource_config.py --cpu-percent 85

    # 4) 只预览不写入
    python scripts/gen_resource_config.py --dry-run

    # 5) 写入后显示摘要
    python scripts/gen_resource_config.py --show
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# 确保 flash 包可导入 (flash_run/env/resource_config 为唯一配置来源)
# flash 包根为 .../sim/flash, 其父目录 .../sim 才是 sys.path 入口
_HERE = Path(__file__).resolve()  # .../sim/flash/scripts/gen_resource_config.py
for _cand in (_HERE.parents[2], _HERE.parents[1]):
    if str(_cand) not in sys.path:
        sys.path.insert(0, str(_cand))

try:
    from flash.flash_run.env.resource_config import (
        FlashResourceConfig,
        classify_device,
        DEVICE_THRESHOLDS,
        VALID_DEVICES,
        DEFAULT_CPU_PERCENT,
    )

    _HAS_MODULE = True
except Exception as _e:  # pragma: no cover — 仅兜底
    _HAS_MODULE = False
    _IMPORT_ERR = _e


# ── 装置默认配置 (与 resource_config.py 保持一致, 兜底用) ──
_FALLBACK_DEVICES = {
    "laptop": {"1d": {"max_cpu_percent": 80, "max_parallel": 1},
               "2d": {"max_cpu_percent": 80, "max_parallel": 1},
               "3d": {"max_cpu_percent": 80, "max_parallel": 1}},
    "desktop": {"1d": {"max_cpu_percent": 80, "max_parallel": 2},
                "2d": {"max_cpu_percent": 80, "max_parallel": 1},
                "3d": {"max_cpu_percent": 80, "max_parallel": 1}},
    "hpc": {"1d": {"max_cpu_percent": 80, "max_parallel": 3},
            "2d": {"max_cpu_percent": 80, "max_parallel": 2},
            "3d": {"max_cpu_percent": 80, "max_parallel": 1}},
}
_FALLBACK_THRESHOLDS = {"laptop": 10, "desktop": 30}

# 默认控制文件路径 (与 resource_config.py 的 CONFIG_FILE 一致)
DEFAULT_OUTPUT = Path.home() / ".physimx" / "flash_resource" / "resource_config.json"


def detect_total_cpus() -> int:
    """探测装置总核数。

    FLASH 实际运行于 WSL, 优先取 `wsl nproc` (与 WSL 侧一致,
    受 .wslconfig 限制影响); 失败则回退 os.cpu_count()。
    """
    try:
        r = subprocess.run(
            ["wsl", "nproc"],
            capture_output=True, text=True, timeout=8,
        )
        if r.returncode == 0 and r.stdout.strip().isdigit():
            return max(1, int(r.stdout.strip()))
    except Exception:
        pass
    return os.cpu_count() or 8


def build_control_file(
    total_cpus: int,
    device: str,
    cpu_percent: int,
    output: Path,
) -> dict:
    """构建控制文件内容并写入 output。

    Returns:
        完整控制文件字典
    """
    if _HAS_MODULE:
        rc = FlashResourceConfig()  # 加载当前配置 (或默认)
        if cpu_percent != DEFAULT_CPU_PERCENT:
            # 覆盖所有装置 × 维度的 CPU 百分比 (内存中修改, 不触发保存)
            for _dev in rc._devices.values():
                for _cfg in _dev.values():
                    _cfg.max_cpu_percent = cpu_percent
        data = rc.to_dict()
    else:  # pragma: no cover — 模块不可用时兜底
        data = {
            "version": 2,
            "device_classification": {
                "method": "total_cores",
                "thresholds": dict(_FALLBACK_THRESHOLDS),
                "formula": "nproc = max(1, int(total_cpus * max_cpu_percent / 100) // max_parallel)",
            },
            "devices": _FALLBACK_DEVICES,
            "local": {}, "hpc": {},
        }
        if cpu_percent != DEFAULT_CPU_PERCENT:
            for _dev in data["devices"].values():
                for _d in _dev.values():
                    _d["max_cpu_percent"] = cpu_percent

    # 写入探测信息
    data["detected"] = {
        "total_cores": total_cpus,
        "device": device,
        "generated_by": "scripts/gen_resource_config.py",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }

    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    tmp = output.with_name(output.name + ".tmp")
    tmp.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    tmp.replace(output)
    return data


def print_summary(data: dict, total_cpus: int, device: str) -> None:
    """打印配置摘要与各维度 nproc 计算。"""
    devices = data.get("devices", {})
    th = data.get("device_classification", {}).get("thresholds", {})
    line = "=" * 62
    print(line)
    print("FLASH 资源配置控制文件已生成")
    print(line)
    print(f"  装置分类阈值: 总核数 < {th.get('laptop', 10)} → 笔记本; "
          f"< {th.get('desktop', 30)} → 台式机; ≥ {th.get('desktop', 30)} → 超算")
    print(f"  探测总核数: {total_cpus}  →  装置类型: {device}")
    print(f"  控制文件: {DEFAULT_OUTPUT}")
    print()
    for dev in VALID_DEVICES:
        print(f"  [{dev}]")
        for dim_key in ("1d", "2d", "3d"):
            cfg = devices.get(dev, {}).get(dim_key, {})
            pct = cfg.get("max_cpu_percent", DEFAULT_CPU_PERCENT)
            par = cfg.get("max_parallel", 1)
            par_txt = f"{par} 个并行" if par > 1 else "不支持并行"
            nproc = max(1, int(total_cpus * pct / 100) // par)
            marker = "  ← 本机" if dev == device else ""
            print(f"    {dim_key.upper()}: CPU {pct}%, {par_txt}  →  nproc={nproc}{marker}")
    print()


def main() -> int:
    ap = argparse.ArgumentParser(
        description="生成 FLASH 资源配置控制文件 (~/.physimx/flash_resource/resource_config.json)",
    )
    ap.add_argument("--total-cpus", type=int, default=None,
                    help="指定装置总核数 (默认自动探测, 优先 wsl nproc)")
    ap.add_argument("--device", choices=list(VALID_DEVICES), default=None,
                    help="强制指定装置类型 (默认按总核数自动分类)")
    ap.add_argument("--cpu-percent", type=int, default=DEFAULT_CPU_PERCENT,
                    help=f"覆盖所有装置的 CPU 占用百分比 (默认 {DEFAULT_CPU_PERCENT})")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUTPUT,
                    help=f"控制文件输出路径 (默认 {DEFAULT_OUTPUT})")
    ap.add_argument("--dry-run", action="store_true",
                    help="只打印控制文件内容, 不写入磁盘")
    ap.add_argument("--show", action="store_true",
                    help="写入后显示配置摘要")
    args = ap.parse_args()

    if not _HAS_MODULE:
        print(f"  [警告] 无法导入 flash.flash_run.env.resource_config: {_IMPORT_ERR}")
        print(f"         将使用内置兜底默认值生成控制文件。")

    total_cpus = args.total_cpus or detect_total_cpus()
    device = args.device or classify_device(total_cpus)

    data = build_control_file(
        total_cpus=total_cpus,
        device=device,
        cpu_percent=args.cpu_percent,
        output=args.output,
    )

    if args.dry_run:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print(f"  [OK] 控制文件已写入: {args.output}")
        if args.show:
            print_summary(data, total_cpus, device)
    return 0


if __name__ == "__main__":
    sys.exit(main())
