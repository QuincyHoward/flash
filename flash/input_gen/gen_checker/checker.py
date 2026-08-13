"""
FLASH 仿真依赖检查器 — DependencyChecker
═══════════════════════════════════════

检查指定目录中 FLASH 仿真所需的全部关键文件是否存在。
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

try:
    import numpy as np
except ImportError:
    np = None  # type: ignore

try:
    import h5py
except ImportError:
    h5py = None  # type: ignore


@dataclass
class CheckResult:
    """单项检查结果。

    Attributes:
        name: 检查项名称
        status: True=通过, False=失败
        message: 描述信息
        details: 额外细节（可选）
    """
    name: str
    status: bool
    message: str
    details: Optional[Dict[str, Any]] = None


class DependencyChecker:
    """FLASH 仿真依赖检查器。

    检查指定仿真目录中以下 7 项依赖是否完整:
        1. .par 文件是否存在
        2. .cn4 EOS 表文件是否存在
        3. Config 文件是否存在
        4. Simulation_initBlock.F90 是否存在
        5. Simulation_init.F90 是否存在
        6. Simulation_data.F90 是否存在
        7. Makefile 是否存在

    可选检查（适用于特定环境）:
        8. FLASH 二进制是否存在（需提供路径）
        9. Python 依赖 (numpy, matplotlib, h5py)
        10. MPI 是否可用

    Example:
        >>> checker = DependencyChecker("/path/to/sim_dir")
        >>> results = checker.check_all()
        >>> print(checker.summary())
    """

    REQUIRED_FILES = [
        ".par",
        ".cn4",
        "Config",
        "Simulation_initBlock.F90",
        "Simulation_init.F90",
        "Simulation_data.F90",
        "Makefile",
    ]

    PYTHON_DEPS = ["numpy", "matplotlib", "h5py"]

    def __init__(self, sim_dir: Union[str, Path]):
        """
        Args:
            sim_dir: 仿真文件所在目录路径
        """
        self.sim_dir = Path(sim_dir)
        self._results: List[CheckResult] = []

    # ── 7 项标准文件检查 ───────────────────────────────

    def check_par_file(self) -> CheckResult:
        """检查 .par 文件是否存在。"""
        par_files = list(self.sim_dir.glob("*.par"))
        if par_files:
            return CheckResult(
                name="par_file",
                status=True,
                message=f"Found {len(par_files)} .par file(s): {[f.name for f in par_files[:3]]}",
                details={"files": [f.name for f in par_files]},
            )
        return CheckResult(
            name="par_file",
            status=False,
            message="No .par file found in sim_dir",
        )

    def check_eos_files(self) -> CheckResult:
        """检查 .cn4 EOS 表文件是否存在。"""
        cn4_files = list(self.sim_dir.glob("*.cn4"))
        if cn4_files:
            return CheckResult(
                name="eos_files",
                status=True,
                message=f"Found {len(cn4_files)} .cn4 file(s): {[f.name for f in cn4_files]}",
                details={"files": [f.name for f in cn4_files]},
            )
        return CheckResult(
            name="eos_files",
            status=False,
            message="No .cn4 EOS table file found",
        )

    def check_file_exists(self, filename: str) -> CheckResult:
        """检查指定文件是否存在。"""
        fpath = self.sim_dir / filename
        exists = fpath.exists() and fpath.is_file()
        return CheckResult(
            name=f"file_{filename}",
            status=exists,
            message=f"{filename}: {'found' if exists else 'NOT found'}",
        )

    def check_config_file(self) -> CheckResult:
        return self.check_file_exists("Config")

    def check_init_block(self) -> CheckResult:
        return self.check_file_exists("Simulation_initBlock.F90")

    def check_init(self) -> CheckResult:
        return self.check_file_exists("Simulation_init.F90")

    def check_sim_data(self) -> CheckResult:
        return self.check_file_exists("Simulation_data.F90")

    def check_makefile(self) -> CheckResult:
        return self.check_file_exists("Makefile")

    # ── 可选环境检查 ────────────────────────────────────

    def check_flash_binary(self, binary_path: Optional[Union[str, Path]] = None) -> CheckResult:
        """检查 FLASH 二进制是否存在。

        Args:
            binary_path: 二进制文件路径。为 None 时跳过。
        """
        if binary_path is None:
            return CheckResult(
                name="flash_binary",
                status=True,
                message="Skipped (no binary_path provided)",
            )
        bpath = Path(binary_path)
        exists = bpath.exists() and bpath.is_file()
        return CheckResult(
            name="flash_binary",
            status=exists,
            message=f"FLASH binary: {bpath} {'found' if exists else 'NOT found'}",
        )

    def check_python_deps(self, deps: Optional[List[str]] = None) -> CheckResult:
        """检查 Python 依赖是否可用。

        Args:
            deps: 依赖模块名列表
        """
        if deps is None:
            deps = self.PYTHON_DEPS
        missing = []
        for mod in deps:
            try:
                __import__(mod)
            except ImportError:
                missing.append(mod)
        ok = len(missing) == 0
        return CheckResult(
            name="python_deps",
            status=ok,
            message=f"Python deps: {'all OK' if ok else f'missing: {missing}'}",
            details={"checked": deps, "missing": missing},
        )

    def check_mpi(self) -> CheckResult:
        """检查 MPI 是否可用。"""
        import shutil
        mpi_bins = ["mpirun", "mpiexec", "srun"]
        found = []
        for bin_name in mpi_bins:
            if shutil.which(bin_name):
                found.append(bin_name)
        ok = len(found) > 0
        return CheckResult(
            name="mpi",
            status=ok,
            message=f"MPI: {'found: ' + ', '.join(found) if ok else 'NOT found (mpirun/mpiexec/srun)'}",
            details={"found": found},
        )

    # ── 聚合方法 ────────────────────────────────────────

    def check_standard(self) -> List[CheckResult]:
        """只检查 7 项 FLASH 仿真必须文件（不含可选环境检查）。

        供场景脚本 / 生成器在运行前调用：.par / .cn4 / Config /
        Simulation_initBlock.F90 / Simulation_init.F90 / Simulation_data.F90 / Makefile。
        """
        self._results = [
            self.check_par_file(),
            self.check_eos_files(),
            self.check_config_file(),
            self.check_init_block(),
            self.check_init(),
            self.check_sim_data(),
            self.check_makefile(),
        ]
        return self._results

    def missing_standard(self) -> List[str]:
        """检查 7 项必须文件并返回缺失项名称列表（空 = 全部就绪）。

        等价于 check_standard() + 筛选 status=False 的结果，
        供"检查 → 缺失则生成"流程直接使用。
        """
        results = self.check_standard()
        return [r.name for r in results if not r.status]

    def check_all(self, binary_path: Optional[Union[str, Path]] = None) -> List[CheckResult]:
        """运行所有 10 项检查。

        Args:
            binary_path: FLASH 二进制路径（可选）

        Returns:
            全部检查结果列表
        """
        self._results = [
            self.check_par_file(),
            self.check_eos_files(),
            self.check_config_file(),
            self.check_init_block(),
            self.check_init(),
            self.check_sim_data(),
            self.check_makefile(),
            self.check_flash_binary(binary_path),
            self.check_python_deps(),
            self.check_mpi(),
        ]
        return self._results

    def summary(self) -> str:
        """生成检查摘要文本。

        Returns:
            格式化的检查报告字符串
        """
        if not self._results:
            return "No checks have been run yet. Call check_all() first."

        lines = []
        lines.append("=" * 50)
        lines.append("FLASH Dependency Check Report")
        lines.append(f"  Directory: {self.sim_dir}")
        lines.append("=" * 50)

        passed = 0
        failed = 0
        skipped = 0

        for r in self._results:
            if r.status:
                status_str = "  OK"
                passed += 1
            elif "Skipped" in r.message or "binary_path" in r.message:
                status_str = "  --"
                skipped += 1
            else:
                status_str = "FAIL"
                failed += 1
            lines.append(f"  [{status_str}] {r.name}: {r.message}")

        lines.append("-" * 50)
        lines.append(f"  Summary: {passed} passed, {failed} failed, {skipped} skipped")
        lines.append("=" * 50)

        return "\n".join(lines)

    def is_all_pass(self) -> bool:
        """检查是否所有非可选检查均已通过。

        Returns:
            True 所有标准检查通过
        """
        if not self._results:
            return False
        for r in self._results:
            if not r.status and "Skipped" not in r.message and "binary_path" not in r.message:
                return False
        return True
