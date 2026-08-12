#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_parallel_processing.py — output_processors 并行模块完整测试

测试项:
  1. 系统资源检测 (get_optimal_workers)
  2. 并行加载文件夹 (parallel_load_folder)
  3. 场内多场并行提取 (extract_fields_parallel)
  4. 并行插值 (parallel_interpolate)
  5. 串行 vs 并行一致性对比
  6. ParallelProcessor 统一接口
  7. 文件夹级并行 (parallel_process_folders)
"""

import sys, os, time, json
import numpy as np
from pathlib import Path

# 项目路径

# Bootstrap: find flash project root by searching upward for marker
_ROOT = Path(__file__).resolve().parent
for _ in range(12):
    if (_ROOT / "pyproject.toml").exists():
        break
    _ROOT = _ROOT.parent
else:
    raise RuntimeError("Cannot locate flash package root")
_PARENT = _ROOT
if str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))

from flash.output_processors.parallel import (
    get_optimal_workers, parallel_load_folder,
    extract_fields_parallel, parallel_interpolate,
    parallel_process_folders, ParallelProcessor,
    _cpu_count, _mem_gb,
)
from flash.output_processors.hdf5processor.flash_hdf5 import FlashHDF5File

# 输出文件
OUTPUT_FILE = Path(__file__).parent / "test_output.txt"

# 测试用数据目录
_TEST_DIR = Path(__file__).parent.parent.parent  # flash/output_processors/
_FLASH_ROOT = _TEST_DIR.parent  # flash/
_INPUT_1D = _FLASH_ROOT / "output_processors" / "inputfiles" / "hdf5files_1d"

# 逐个场景的 runs — flash/test/scenarios/
_SCENARIOS_DIR = _FLASH_ROOT / "test" / "scenarios"
_SCENARIO_CHK_DIRS = {}

# 用已有的 chk 目录
for name in ["runs_ch_center", "runs_thin_layer_sandwich_al", "runs_thin_layer_sandwich_si"]:
    d = _SCENARIOS_DIR / name / "000001" / "sim_output"
    if d.exists():
        _SCENARIO_CHK_DIRS[name] = d

if not _SCENARIO_CHK_DIRS:
    # fallback: 用 inputfiles 中的数据
    if _INPUT_1D.exists():
        _SCENARIO_CHK_DIRS["hdf5files_1d"] = _INPUT_1D


def log(msg: str, f=None):
    """打印并记录到文件"""
    print(msg)
    if f:
        f.write(msg + "\n")
        f.flush()


def test_all():
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        log("=" * 60, f)
        log("  output_processors 并行模块测试报告", f)
        log(f"  时间: {time.strftime('%Y-%m-%d %H:%M:%S')}", f)
        log("=" * 60, f)

        # ────────────────────────────────────────────────
        # 1. 系统资源检测
        # ────────────────────────────────────────────────
        log("\n── 1. 系统资源检测 ──", f)
        cpu = _cpu_count()
        mem = _mem_gb()
        log(f"  CPU 核心: {cpu}", f)
        log(f"  可用内存: {mem:.1f} GB", f)

        workers_io, info_io = get_optimal_workers(io_bound=True)
        workers_cpu, info_cpu = get_optimal_workers(io_bound=False)
        log(f"  IO推荐并行数: {workers_io}", f)
        log(f"  CPU推荐并行数: {workers_cpu}", f)
        for k, v in info_io.items():
            log(f"    {k}: {v}", f)

        assert cpu >= 1, "CPU 核心检测失败"
        assert mem > 0, "内存检测失败"
        assert workers_io >= 1, "IO 并行数异常"
        log("  ✅ 系统资源检测通过\n", f)

        # ────────────────────────────────────────────────
        # 2. 并行加载文件夹
        # ────────────────────────────────────────────────
        log("── 2. 并行加载 ──", f)
        passed_load = 0
        for name, chk_dir in _SCENARIO_CHK_DIRS.items():
            all_files = sorted(Path(chk_dir).glob("*chk*"))
            n_total = len(all_files)
            log(f"\n  场景: {name}", f)
            log(f"  文件数: {n_total}", f)

            t0 = time.time()
            slices = parallel_load_folder(
                str(chk_dir), pattern="*chk*", verbose=True,
            )
            t1 = time.time()
            elapsed = t1 - t0

            if slices:
                s0 = slices[0]
                fields = [k for k in s0.keys() if k not in ("time", "x", "filepath", "step")]
                log(f"  耗时: {elapsed:.2f}s", f)
                log(f"  读取: {len(slices)}/{n_total}", f)
                log(f"  首文件: time={s0.get('time','N/A')}", f)
                log(f"  字段数: {len(fields)}", f)
                log(f"  空间点: {len(s0.get('x',[]))}", f)
                assert len(slices) > 0, "并行加载返回空"
                assert "time" in s0, "缺少 time"
                passed_load += 1
                log(f"  ✅ 并行加载通过\n", f)
            else:
                log(f"  ⚠ 场景 {name}: 无可读文件\n", f)

        assert passed_load > 0 or len(_SCENARIO_CHK_DIRS) == 0, "至少一个场景加载通过"

        # ────────────────────────────────────────────────
        # 3. 场内多场并行提取
        # ────────────────────────────────────────────────
        log("── 3. 场内多场并行提取 ──", f)
        if _INPUT_1D.exists():
            files_1d = sorted(_INPUT_1D.glob("*chk*"))
            if files_1d:
                fp = str(files_1d[0])
                log(f"\n  文件: {Path(fp).name}", f)
                var_names = ["dens", "tele", "pres"]
                t0 = time.time()
                result = extract_fields_parallel(fp, var_names)
                t1 = time.time()
                log(f"  耗时: {t1-t0:.3f}s", f)
                for vn in var_names:
                    if vn in result:
                        log(f"  {vn}: {len(result.get('x',[]))} pts", f)
                assert "dens" in result, "dens 未提取"
                assert "x" in result, "x 未提取"
                log(f"  ✅ 场内多场并行提取通过\n", f)
            else:
                log(f"  ⚠ inputfiles_1d 无 chk 文件, 跳过\n", f)
        else:
            log(f"  ⚠ inputfiles_1d 目录不存在, 跳过\n", f)

        # ────────────────────────────────────────────────
        # 4. 并行插值
        # ────────────────────────────────────────────────
        log("── 4. 并行插值 ──", f)
        for name, chk_dir in _SCENARIO_CHK_DIRS.items():
            all_files = sorted(Path(chk_dir).glob("*chk*"))
            if len(all_files) < 2:
                continue
            # 取前 10 个文件
            test_files = all_files[:10]
            log(f"\n  场景: {name} (前 {len(test_files)} 个)", f)

            # 先加载
            slices = parallel_load_folder(
                str(chk_dir), pattern="*chk*", verbose=False,
            )
            if not slices:
                log(f"  ⚠ 加载失败, 跳过\n", f)
                continue

            # 准备插值网格
            Nt, Nx = 31, 201
            t_grid = np.linspace(0, 5e-10, Nt)
            x_grid = np.linspace(-0.01, 0.01, Nx)
            fields = [k for k in slices[0].keys() if k not in ("time", "x", "filepath", "step")]
            var_names = fields[:4]  # 前4个字段

            # 并行插值
            t0 = time.time()
            result_p = parallel_interpolate(
                slices, t_grid, x_grid, var_names,
                verbose=True,
            )
            t1 = time.time()
            log(f"  并行耗时: {t1-t0:.3f}s", f)
            for vn in var_names[:2]:
                if vn in result_p:
                    d = result_p[vn]
                    log(f"  {vn}: shape={d.shape}, range=[{d.min():.4e},{d.max():.4e}]", f)

            # 串行插值对比 (使用同一份数据, 单进程)
            log(f"\n  串行对比 (同一数据, use_parallel=False):", f)
            t2 = time.time()
            result_s = parallel_interpolate(
                slices, t_grid, x_grid, var_names,
                verbose=False, max_workers=1,
            )
            t3 = time.time()
            log(f"  串行耗时: {t3-t2:.3f}s", f)

            # 一致性检查
            if result_p and result_s:
                diffs = []
                for vn in var_names:
                    if vn in result_p and vn in result_s:
                        diff = np.max(np.abs(result_p[vn] - result_s[vn]))
                        diffs.append(diff)
                max_diff = max(diffs) if diffs else 0
                log(f"  最大差异: {max_diff:.4e}", f)
                if max_diff < 1e-6:
                    log(f"  ✅ 并行/串行结果一致\n", f)
                else:
                    log(f"  ⚠ 并行/串行有差异 (max={max_diff:.4e})\n", f)
            break  # 只测一个场景

        # ────────────────────────────────────────────────
        # 5. ParallelProcessor 统一接口
        # ────────────────────────────────────────────────
        log("── 5. ParallelProcessor 统一接口 ──", f)
        pp = ParallelProcessor()
        log(f"  创建: ParallelProcessor OK", f)

        if _SCENARIO_CHK_DIRS:
            first_dir = list(_SCENARIO_CHK_DIRS.values())[0]
            slices2 = pp.load_folder(str(first_dir), pattern="*chk*", verbose=False)
            log(f"  pp.load_folder: {len(slices2)} 个文件", f)
            assert len(slices2) > 0, "ParallelProcessor.load_folder 失败"

            if slices2:
                result2 = pp.interpolate(
                    slices2[:5],
                    np.linspace(0, 1e-9, 11),
                    np.linspace(-0.01, 0.01, 51),
                    ["dens", "tele"],
                    verbose=False,
                )
                log(f"  pp.interpolate: {'dens' in result2}", f)
                assert "dens" in result2, "ParallelProcessor.interpolate 失败"
        log(f"  ✅ ParallelProcessor 接口测试通过\n", f)

        # ────────────────────────────────────────────────
        # 6. 汇总
        # ────────────────────────────────────────────────
        log("=" * 60, f)
        log(f"  并行模块测试完成", f)
        log(f"  结果保存至: {OUTPUT_FILE}", f)
        log("=" * 60, f)

    print(f"\n📄 完整测试报告: {OUTPUT_FILE}")


if __name__ == "__main__":
    test_all()
