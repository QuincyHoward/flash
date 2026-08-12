"""parallel.py — output_processors 并行处理工具

提供并行读取 FLASH HDF5 文件、并行提取多物理场、并行多文件夹处理的能力。
自动检测 CPU 核心数和可用内存，自适应选择最优并行度。

核心函数:
  get_optimal_workers()    — 系统资源检测, 返回推荐并行数
  parallel_load_folder()   — 并行加载文件夹中所有 chk 文件
  parallel_extract_fields()— 从单个文件并行提取多个物理场
  parallel_interpolate()   — 并行时空插值 (时间步维)
"""

import os
# ── 限制 BLAS 线程数, 防止多进程 OpenBLAS 内存爆炸 ──
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")

import gc
import time
import math
import platform
from concurrent.futures import (
    ProcessPoolExecutor, ThreadPoolExecutor,
    as_completed, wait, FIRST_EXCEPTION
)
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Tuple, Union, Any
import functools
import warnings

import numpy as np
from .hdf5processor.flash_hdf5 import FlashHDF5File


# ── 系统资源检测 ────────────────────────────────────────────


def _cpu_count() -> int:
    """返回可用 CPU 核心数（安全兜底）"""
    try:
        return os.cpu_count() or 4
    except Exception:
        return 4


def _mem_gb() -> float:
    """返回可用物理内存 (GB)，兜底 4GB"""
    try:
        import psutil
        return psutil.virtual_memory().available / (1024 ** 3)
    except ImportError:
        pass
    # 跨平台 fallback
    try:
        if platform.system() == "Linux":
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemAvailable:"):
                        return int(line.split()[1]) / 1e6
        elif platform.system() == "Windows":
            import ctypes
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]
            mem = MEMORYSTATUSEX()
            mem.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(mem)):
                return mem.ullAvailPhys / (1024 ** 3)
    except Exception:
        pass
    return 4.0


def _avg_chk_size_mb(folder: Optional[Path] = None) -> float:
    """估算单个 chk 文件的平均大小 (MB)，默认 5MB"""
    if folder is not None and folder.exists():
        try:
            chk_files = sorted(folder.glob("*chk*"))
            if chk_files:
                sizes = [f.stat().st_size for f in chk_files[:10]]
                return sum(sizes) / len(sizes) / (1024 ** 2)
        except Exception:
            pass
    return 5.0


def get_optimal_workers(
    io_bound: bool = True,
    max_mem_per_worker_mb: float = 500.0,
    folder: Optional[Path] = None,
) -> int:
    """根据系统资源自动计算最优并行工作数

    Args:
        io_bound: True=IO密集型(推荐 max_workers=CPU×2~4),
                  False=CPU密集型(推荐 max_workers=CPU)
        max_mem_per_worker_mb: 每个worker预计占用内存(MB)
        folder: 可选, 用于估算chk文件大小

    Returns:
        推荐的工作进程/线程数 (至少 1)
    """
    cpu = _cpu_count()
    mem_gb = _mem_gb()
    chk_mb = _avg_chk_size_mb(folder)

    # 内存限制: 最多使用 70% 可用内存
    mem_limit = max(1, int(mem_gb * 0.7 * 1024 / max(chk_mb, max_mem_per_worker_mb)))

    if io_bound:
        # IO密集型: 使用更多并发以隐藏IO延迟
        cpu_limit = cpu * 3
    else:
        # CPU密集型: 不超过物理核心数
        cpu_limit = cpu

    workers = min(mem_limit, cpu_limit)

    # 记录最终选择
    _optimal = {
        "cpu_cores": cpu,
        "mem_gb": round(mem_gb, 1),
        "chk_mb": round(chk_mb, 1),
        "mem_limit_workers": mem_limit,
        "cpu_limit_workers": cpu_limit,
        "selected": max(1, workers),
    }
    return max(1, workers), _optimal


# ── 并行文件加载 ────────────────────────────────────────────


def _load_single_chk(filepath: str, var_names: Optional[List[str]] = None) -> Optional[Dict]:
    """加载单个 chk 文件并提取数据（供多进程调用）"""
    try:
        ff = FlashHDF5File(filepath)
        result = {"time": ff.simulation_time, "step": ff.simulation_step, "filepath": filepath}

        if ff.ndim == 1:
            grid = ff.read_grid()
            result["x"] = grid["x_1d"]
            vnames = var_names if var_names else list(ff.varnames)
            for vn in vnames:
                if vn in ff.varnames:
                    _, y = ff.slice_1d(vn, grid=grid)
                    result[vn] = y
                else:
                    result[vn] = np.zeros_like(result["x"])
        else:
            # 2D/3D 简化为读原始数据（保持varnames可用）
            result["x"] = np.array([])
            vnames = var_names if var_names else list(ff.varnames)
            for vn in vnames:
                if vn in ff.varnames:
                    arr = ff.read_var(vn)
                    result[vn] = arr
        ff.close()
        return result
    except Exception as e:
        warnings.warn(f"并行加载失败: {filepath}: {e}")
        return None


def parallel_load_folder(
    folder_path: Union[str, Path],
    pattern: str = "*chk*",
    var_names: Optional[List[str]] = None,
    max_workers: Optional[int] = None,
    verbose: bool = True,
) -> List[Dict]:
    """并行加载文件夹中所有匹配的 HDF5 文件

    Args:
        folder_path: 文件夹路径
        pattern: 文件通配模式, 默认 "*chk*"
        var_names: 需要提取的变量列表 (None=全部)
        max_workers: 最大并行数 (None=自动)
        verbose: 是否打印进度

    Returns:
        [{time, step, x, var1, var2, ...}, ...] 按时间排序
    """
    folder = Path(folder_path)
    files = sorted(folder.glob(pattern))
    if not files:
        warnings.warn(f"文件夹中无匹配文件: {folder} / {pattern}")
        return []

    if max_workers is None:
        # IO密集: ThreadPoolExecutor + 较低并发防内存爆炸
        cpu = _cpu_count()
        workers = min(cpu * 2, 12)
    else:
        workers = max_workers
    workers = min(workers, len(files))

    if verbose:
        print(f"  [并行] 加载 {len(files)} 个文件, workers={workers}")

    results = []
    if workers <= 1 or len(files) <= 1:
        # 串行 fallback
        for f in files:
            r = _load_single_chk(str(f), var_names)
            if r:
                results.append(r)
    else:
        # IO密集型 → ThreadPoolExecutor (h5py 释放 GIL, 避免 OpenBLAS 内存爆炸)
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futs = [pool.submit(_load_single_chk, str(f), var_names) for f in files]
            for i, fut in enumerate(as_completed(futs)):
                r = fut.result()
                if r:
                    results.append(r)
                if verbose and (i + 1) % max(1, len(files) // 10) == 0:
                    print(f"    [并行] 已加载 {i+1}/{len(files)}")

    # 按时间排序
    results.sort(key=lambda x: x.get("time", 0))
    if verbose:
        print(f"  [并行] 完成: {len(results)} 个文件")

    return results


# ── 单文件内多物理场并行提取 ─────────────────────────────


def _extract_field(args: tuple) -> Tuple[str, np.ndarray, np.ndarray]:
    """提取单个物理场并返回 (varname, x_1d, y_1d)"""
    filepath, varname = args
    ff = FlashHDF5File(filepath)
    try:
        if varname in ff.varnames:
            x, y = ff.slice_1d(varname)
        else:
            grid = ff.read_grid()
            x = grid.get("x_1d", np.array([]))
            y = np.zeros_like(x)
        return (varname, x, y)
    finally:
        ff.close()


def extract_fields_parallel(
    filepath: str,
    var_names: List[str],
    max_workers: Optional[int] = None,
) -> Dict[str, np.ndarray]:
    """从单个 HDF5 文件并行提取多个物理场

    每个物理场在一个独立进程中提取，充分利用多核。

    Args:
        filepath: HDF5 文件路径
        var_names: 需要提取的物理场列表
        max_workers: 最大并行数 (None=自动)

    Returns:
        {varname: ndarray} 以及 "x" 和 "time"
    """
    n_vars = len(var_names)
    if n_vars == 0:
        return {}

    if max_workers is None:
        # CPU密集型: 不超过物理核心数, 上限8防OpenBLAS爆炸
        cpu = _cpu_count()
        workers = min(cpu, 8)
    else:
        workers = max_workers
    workers = min(workers, n_vars)

    # 先获取 time 和基础信息
    ff = FlashHDF5File(filepath)
    sim_time = ff.simulation_time
    ff.close()

    if workers <= 1 or n_vars <= 1:
        # 串行 fallback
        result: Dict[str, Any] = {"time": sim_time}
        ff = FlashHDF5File(filepath)
        try:
            for vn in var_names:
                if vn in ff.varnames:
                    x, y = ff.slice_1d(vn)
                    if "x" not in result:
                        result["x"] = x
                    result[vn] = y
                else:
                    if "x" not in result:
                        grid = ff.read_grid()
                        result["x"] = grid.get("x_1d", np.array([]))
                    result[vn] = np.zeros_like(result["x"])
        finally:
            ff.close()
        return result

    # 并行提取
    args_list = [(filepath, vn) for vn in var_names]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futs = [pool.submit(_extract_field, args) for args in args_list]
        results = {}
        for fut in as_completed(futs):
            vn, x, y = fut.result()
            if "x" not in results:
                results["x"] = x
            results[vn] = y
        results["time"] = sim_time
        return results


# ── 并行插值 ──────────────────────────────────────────────


def _interpolate_time_chunk(args: tuple) -> Dict[str, np.ndarray]:
    """插值一个时间块（供并行调用）

    Args:
        args: (t_start_idx, t_end_idx, t_grid, x_grid, flash_data, var_names, flash_times)

    Returns:
        {varname: ndarray chunk of shape (chunk_size, Nx)}
    """
    t_start, t_end, t_grid, x_grid, flash_data, var_names, flash_times = args
    chunk_size = t_end - t_start
    Nx = len(x_grid)
    result = {vn: np.zeros((chunk_size, Nx), dtype=np.float32) for vn in var_names}
    n_flash = len(flash_times)

    for ti in range(t_start, t_end):
        t_target = t_grid[ti]
        if t_target <= flash_times[0]:
            ta = tb = 0
            alpha = 0.0
        elif t_target >= flash_times[-1]:
            ta = tb = n_flash - 1
            alpha = 0.0
        else:
            tb = np.searchsorted(flash_times, t_target, side="right")
            ta = tb - 1
            dt = flash_times[tb] - flash_times[ta]
            alpha = (t_target - flash_times[ta]) / dt if dt > 0 else 0.0

        local_ti = ti - t_start
        for vn in var_names:
            fa = np.interp(x_grid, flash_data[ta]["x"], flash_data[ta][vn], left=0.0, right=0.0)
            if ta == tb:
                fb = fa
            else:
                fb = np.interp(x_grid, flash_data[tb]["x"], flash_data[tb][vn], left=0.0, right=0.0)
            result[vn][local_ti, :] = (1.0 - alpha) * fa + alpha * fb

    return result


def parallel_interpolate(
    flash_slices: List[Dict],
    t_grid: np.ndarray,
    x_grid: np.ndarray,
    var_names: List[str],
    max_workers: Optional[int] = None,
    verbose: bool = True,
) -> Dict[str, np.ndarray]:
    """并行时空插值 — 将时间步分块并行处理

    Args:
        flash_slices: [{time, x, var1, var2, ...}, ...] 按时间排序
        t_grid: 目标时间网格 [Nt]
        x_grid: 目标空间网格 [Nx]
        var_names: 需要插值的变量列表
        max_workers: 并行数 (None=自动)
        verbose: 是否打印进度

    Returns:
        {varname: ndarray of shape (Nt, Nx)}
    """
    n_flash = len(flash_slices)
    Nt = len(t_grid)
    Nx = len(x_grid)

    if n_flash == 0 or Nt == 0:
        return {vn: np.zeros((Nt, Nx), dtype=np.float32) for vn in var_names}

    flash_times = np.array([s["time"] for s in flash_slices])

    # 构建 flash_data (格式统一为字典)
    flash_data = []
    for sl in flash_slices:
        entry = {"x": sl["x"]}
        for vn in var_names:
            entry[vn] = sl.get(vn, np.zeros_like(sl.get("x", np.array([]))))
        flash_data.append(entry)

    if max_workers is None:
        # CPU密集型: 不超过物理核心数, 上限6防OpenBLAS爆炸
        cpu = _cpu_count()
        workers = min(cpu, 6)
    else:
        workers = max_workers

    # 将时间步分块
    n_chunks = min(workers, Nt)
    chunk_size = max(1, Nt // n_chunks)
    chunks = []
    for i in range(0, Nt, chunk_size):
        end = min(i + chunk_size, Nt)
        chunks.append((i, end, t_grid, x_grid, flash_data, var_names, flash_times))

    if verbose:
        print(f"  [并行] 插值 {Nt} 时间步, {len(chunks)} 块, workers={len(chunks)}")

    if len(chunks) <= 1:
        # 串行 fallback
        result = _interpolate_time_chunk(chunks[0])
        if verbose:
            print(f"  [并行] 插值完成")
        return result

    # 并行插值
    from concurrent.futures import ProcessPoolExecutor, as_completed
    results_list = [None] * len(chunks)
    with ProcessPoolExecutor(max_workers=min(workers, len(chunks))) as pool:
        futs = {pool.submit(_interpolate_time_chunk, ch): i for i, ch in enumerate(chunks)}
        for fut in as_completed(futs):
            idx = futs[fut]
            chunk_result = fut.result()
            results_list[idx] = chunk_result
            if verbose:
                chunk_t0, chunk_t1 = chunks[idx][0], chunks[idx][1]
                print(f"    [并行] 时间步 {chunk_t0+1}~{chunk_t1}/{Nt} 完成")

    # 合并结果
    merged = {vn: np.zeros((Nt, Nx), dtype=np.float32) for vn in var_names}
    for idx, chunk_result in enumerate(results_list):
        if chunk_result is None:
            continue
        t_start = chunks[idx][0]
        t_end = chunks[idx][1]
        chunk_size_local = t_end - t_start
        for vn in var_names:
            merged[vn][t_start:t_end] = chunk_result[vn][:chunk_size_local]

    if verbose:
        print(f"  [并行] 插值完成")

    return merged


# ── 文件夹级并行 ──────────────────────────────────────────


def parallel_process_folders(
    folder_list: List[Union[str, Path]],
    process_fn: Callable[[Dict], Any],
    pattern: str = "*chk*",
    var_names: Optional[List[str]] = None,
    max_workers_per_folder: Optional[int] = None,
    max_workers_folder: Optional[int] = None,
    verbose: bool = True,
) -> Dict[str, Any]:
    """并行处理多个文件夹，每个文件夹又并行加载内部文件

    两层并行:
      - 外层: 不同文件夹之间并行 (文件夹级)
      - 内层: 每个文件夹内多文件并行

    Args:
        folder_list: 文件夹路径列表
        process_fn: 处理函数, 接收 {time, x, var1, ...} 返回结果
        pattern: 文件匹配模式
        var_names: 提取的变量列表
        max_workers_per_folder: 每文件夹内并行数
        max_workers_folder: 文件夹间并行数
        verbose: 是否打印进度

    Returns:
        {folder_name: processed_result, ...}
    """
    from concurrent.futures import ProcessPoolExecutor, as_completed

    if max_workers_folder is None:
        cpu = _cpu_count()
        max_workers_folder = max(1, cpu // 2)
    if max_workers_per_folder is None:
        max_workers_per_folder = max(1, _cpu_count() // max(1, max_workers_folder))

    if verbose:
        print(f"  [并行-文件夹] {len(folder_list)} 个文件夹, "
              f"外层={max_workers_folder}, 内层={max_workers_per_folder}")

    def _process_one_folder(folder_path: str) -> Tuple[str, Any]:
        """处理单个文件夹: 加载+处理"""
        folder = Path(folder_path)
        slices = parallel_load_folder(
            folder, pattern=pattern, var_names=var_names,
            max_workers=max_workers_per_folder, verbose=False,
        )
        if not slices:
            return (folder.name, None)
        try:
            result = process_fn(slices)
        except Exception as e:
            warnings.warn(f"  文件夹处理失败 {folder.name}: {e}")
            result = None
        return (folder.name, result)

    results = {}
    # 少于2个文件夹不并行
    if len(folder_list) <= 1 or max_workers_folder <= 1:
        for fp in folder_list:
            name, res = _process_one_folder(str(fp))
            results[name] = res
            if verbose:
                print(f"    [文件夹] {name}: {'✅' if res is not None else '❌'}")
    else:
        with ProcessPoolExecutor(max_workers=max_workers_folder) as pool:
            futs = {pool.submit(_process_one_folder, str(fp)): fp for fp in folder_list}
            for fut in as_completed(futs):
                name, res = fut.result()
                results[name] = res
                if verbose:
                    print(f"    [文件夹] {name}: {'✅' if res is not None else '❌'}")

    return results


# ── 快捷 API ──────────────────────────────────────────────


class ParallelProcessor:
    """并行处理器 — 统一接口

    用法:
        pp = ParallelProcessor()
        pp.load_folder("./chk_files/")         # 并行加载文件夹
        pp.extract_fields("file.h5", ["dens", "tele"])  # 并行提取多场
        pp.interpolate(slices, t_grid, x_grid)  # 并行插值
        pp.process_folders([...], fn)           # 并行处理多文件夹
    """

    def __init__(self, max_workers: Optional[int] = None):
        self.max_workers = max_workers
        self._stats: Dict[str, Any] = {"calls": 0}

    @property
    def stats(self) -> Dict:
        return dict(self._stats)

    def load_folder(self, folder_path: Union[str, Path], **kwargs) -> List[Dict]:
        self._stats["calls"] += 1
        return parallel_load_folder(folder_path, max_workers=self.max_workers, **kwargs)

    def extract_fields(self, filepath: str, var_names: List[str]) -> Dict:
        return extract_fields_parallel(filepath, var_names, max_workers=self.max_workers)

    def interpolate(self, flash_slices, t_grid, x_grid, var_names, **kwargs) -> Dict:
        return parallel_interpolate(
            flash_slices, t_grid, x_grid, var_names,
            max_workers=self.max_workers, **kwargs
        )

    def process_folders(self, folder_list, process_fn, **kwargs) -> Dict:
        return parallel_process_folders(
            folder_list, process_fn,
            max_workers_per_folder=self.max_workers,
            **kwargs
        )
