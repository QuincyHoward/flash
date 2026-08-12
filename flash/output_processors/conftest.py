"""
pytest conftest.py - shared fixtures for output_processors tests.
"""
import pytest
import sys
from pathlib import Path

# Add project root to path

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


@pytest.fixture(scope="session")
def sample_h5_file():
    """Fixture: path to a sample HDF5 file for testing."""
    # TODO: Add path to a small test HDF5 file
    return None


@pytest.fixture(scope="session")
def flash_data_loader():
    """Fixture: FlashDataLoader instance."""
    from flash.output_processors.loader import FlashDataLoader
    return FlashDataLoader


@pytest.fixture(scope="session")
def flash_hdf5_file():
    """Fixture: FlashHDF5File class."""
    from flash.output_processors.hdf5processor import FlashHDF5File
    return FlashHDF5File


@pytest.fixture(scope="session", autouse=True)
def _auto_generate_test_data():
    """自动生成 output_processors 测试数据 (inputfiles/ 被 .gitignore 排除)。

    生成-测试-清理 生命周期:
      1. 会话开始: 先清理上次残留 (此时无测试句柄, 可稳定删除),
         再并行快速生成合成 FLASH HDF5
         (与 FlashHDF5File/FlashDataLoader/yt 读取逻辑兼容);
      2. 会话结束: pytest_sessionfinish 钩子按结果处理 —
         全部通过 → 延迟分离子进程删除生成文件 (pytest 退出后句柄释放);
         有失败 → 打印失败信息并保留数据文件供调试。
    """
    from flash.output_processors.test.gen_test_data import (
        cleanup_test_data_subprocess, ensure_test_data,
    )
    cleanup_test_data_subprocess()   # 清理上次残留 (本次测试尚未打开文件)
    ensure_test_data()


def pytest_sessionfinish(session, exitstatus):
    """output_processors 测试收尾: 通过即删, 失败保留。

    - exitstatus == 0 (全部通过): 删除生成的 HDF5 数据文件。
      删除前多次强制 GC 释放测试残留的 yt/h5py 句柄 (Windows 文件锁)。
      仓库不发布 hdf5 源文件, 测试数据随时可由 gen_test_data.py 重新生成。
    - exitstatus != 0 (存在失败): 打印失败摘要并**保留**数据文件,
      方便本地调试 (调试完成后可运行 gen_test_data.py --cleanup 手动清理)。
    """
    from flash.output_processors.test.gen_test_data import (
        cleanup_test_data_subprocess, data_status, _INPUTFILES,
    )

    if exitstatus == 0:
        # 1) 多次强制 GC: 释放测试残留的 yt/h5py 句柄 (含循环引用)
        import gc
        for _ in range(4):
            gc.collect()
        # 2) clean_env 子进程原生删除 (规避 WorkBuddy sitecustomize 对
        #    os.unlink 的重定向; 子进程无测试句柄残留)
        n = cleanup_test_data_subprocess()
        print(f"\n[conftest] ✅ output_processors 全部通过, 已删除 {n} 个生成的测试数据文件"
              f" (如需重新生成: python flash/output_processors/test/gen_test_data.py)")
        print(f"[conftest] 清理后状态: {data_status()}")
    else:
        print("\n[conftest] ⚠ output_processors 测试未全部通过"
              f" (failed={session.testsfailed}), 保留生成的 HDF5 数据文件供调试:")
        print(f"           目录: {_INPUTFILES}")
        print(f"           状态: {data_status()}")
        print(f"           调试完成后清理: python flash/output_processors/test/gen_test_data.py --cleanup")
