"""
pytest conftest.py - shared fixtures for output_pro tests.
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


# ★★ 测试数据必须在 **conftest 导入期** 生成，不能只靠 session fixture。
#   原因：pytest 的执行顺序是「收集(import 全部测试模块) → 执行 fixture → 跑用例」。
#   `test/unit_conversion/test_unit_conversion.py` 与 `test/test_extraction_modes.py`
#   在**模块导入期**就检查 inputfiles 里的文件是否存在（TEST_FILES 字典 +
#   assert "测试文件不存在"），而 session fixture 要到**第一个用例执行前**才跑
#   ⇒ 收集阶段文件还不存在 ⇒ 用例直接失败。
#   实测症状（超算离线安装 2026-10-22）：
#     ① 第一轮 40 passed / 3 failed（test_flat_plotter_1d_renders）
#     ② 重建重测 38 passed / 3 failed（test_load_extracted_yields_flat_container）
#   —— 失败用例每轮都不同，正是「数据在收集阶段尚未就位」的竞态特征。
#   ⇒ 这里在模块导入期先生成（幂等，秒级），fixture 只保留清理职责。
def _bootstrap_test_data() -> None:
    try:
        from flash.output_pro.test.gen_test_data import (
            cleanup_test_data_subprocess,
            ensure_test_data,
        )
        cleanup_test_data_subprocess()   # 清上次残留（本次尚无句柄）
        ensure_test_data()               # ★ 收集阶段之前就把数据备好
    except Exception as _exc:            # noqa: BLE001
        # 生成失败不应让整个套件无法收集（下面的用例会各自报"文件不存在"）
        print(f"[conftest] ⚠ 测试数据预生成失败: {type(_exc).__name__}: {_exc}")


_bootstrap_test_data()


@pytest.fixture(scope="session")
def sample_h5_file():
    """Fixture: path to a sample HDF5 file for testing."""
    # TODO: Add path to a small test HDF5 file
    return None


@pytest.fixture(scope="session")
def flash_data_loader():
    """Fixture: FlashDataLoader instance."""
    from flash.output_pro.loader import FlashDataLoader
    return FlashDataLoader


@pytest.fixture(scope="session")
def flash_hdf5_file():
    """Fixture: FlashHDF5File class."""
    from flash.output_pro.hdf5pro import FlashHDF5File
    return FlashHDF5File


@pytest.fixture(scope="session", autouse=True)
def _auto_generate_test_data():
    """自动生成 output_pro 测试数据 (inputfiles/ 被 .gitignore 排除)。

    生成-测试-清理 生命周期:
      1. 会话开始: 先清理上次残留 (此时无测试句柄, 可稳定删除),
         再并行快速生成合成 FLASH HDF5
         (与 FlashHDF5File/FlashDataLoader/yt 读取逻辑兼容);
      2. 会话结束: pytest_sessionfinish 钩子按结果处理 —
         全部通过 → 延迟分离子进程删除生成文件 (pytest 退出后句柄释放);
         有失败 → 打印失败信息并保留数据文件供调试。
    """
    from flash.output_pro.test.gen_test_data import (
        cleanup_test_data_subprocess, ensure_test_data,
    )
    cleanup_test_data_subprocess()   # 清理上次残留 (本次测试尚未打开文件)
    ensure_test_data()


def pytest_sessionfinish(session, exitstatus):
    """output_pro 测试收尾: 通过即删, 失败保留。

    - exitstatus == 0 (全部通过): 删除生成的 HDF5 数据文件。
      删除前多次强制 GC 释放测试残留的 yt/h5py 句柄 (Windows 文件锁)。
      仓库不发布 hdf5 源文件, 测试数据随时可由 gen_test_data.py 重新生成。
    - exitstatus != 0 (存在失败): 打印失败摘要并**保留**数据文件,
      方便本地调试 (调试完成后可运行 gen_test_data.py --cleanup 手动清理)。
    """
    from flash.output_pro.test.gen_test_data import (
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
        print(f"\n[conftest] ✅ output_pro 全部通过, 已删除 {n} 个生成的测试数据文件"
              f" (如需重新生成: python flash/output_pro/test/gen_test_data.py)")
        print(f"[conftest] 清理后状态: {data_status()}")
    else:
        print("\n[conftest] ⚠ output_pro 测试未全部通过"
              f" (failed={session.testsfailed}), 保留生成的 HDF5 数据文件供调试:")
        print(f"           目录: {_INPUTFILES}")
        print(f"           状态: {data_status()}")
        print(f"           调试完成后清理: python flash/output_pro/test/gen_test_data.py --cleanup")
