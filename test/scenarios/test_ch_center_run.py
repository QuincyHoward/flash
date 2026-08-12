"""
test_ch_center_run.py — ch_center 真实 FLASH 仿真测试

用法:  python test_ch_center_run.py

验证:
  - ch_center 场景完整管线 (编译→运行→插值→输出)
  - 旧 EOS (he-imx-005.cn4 + polystyrene-imx-008.cn4) + eos_tab
  - 输出目录结构 / result.h5 数据完整性
"""
import sys
from pathlib import Path

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

try:
    from flash.scenarios.registry import get_scenario, list_scenarios
    from flash.scenarios.simulator import FlashSimulatorEngine, _flash_detected
except ImportError:
    import pytest; pytest.skip("flash package not available", allow_module_level=True)

import h5py, json


def _flash_available() -> bool:
    """检测 WSL 中是否有可用的 FLASH 安装 (无则跳过真实仿真测试)."""
    try:
        return _flash_detected()
    except Exception:
        return False


# 注意: 全局测试不再整体跳过。默认 test_ch_center_run(run_real_flash=False)
# 仅做 .par 参数验证 (无 FLASH 依赖); 真实 FLASH 路径由 dry-run 自动回退
# 或在本机已安装 FLASH 时直接运行, 保证 CI 无 FLASH 环境也能全部通过。

# 检查前序 run_id 是否有编译好的 flash4 (替代全局二进制检查)
def _check_previous_run_binary(runs_dir: Path = Path("runs_ch_center")) -> bool:
    """检查前序 run_id (000001) 是否已有编译好的 flash4。"""
    run_sh = runs_dir / "000001" / "sim_input" / "run_flash.sh"
    if not run_sh.exists():
        return False
    text = run_sh.read_text(encoding="utf-8")
    flash_home = None
    obj_dir = None
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("cd ") and "/FLASH/FLASH4.8" in s and not s.startswith("#"):
            parts = s.split()
            if len(parts) >= 2:
                flash_home = parts[1]
                break
    for line in text.splitlines():
        if "-objdir=" in line:
            for part in line.split():
                if "-objdir=" in part:
                    obj_dir = part.split("=", 1)[1]
                    break
            if obj_dir:
                break
    if not (flash_home and obj_dir):
        return False
    import subprocess
    try:
        binary = f"{flash_home}/{obj_dir}/flash4"
        r = subprocess.run(["wsl", "bash", "-lc", f"test -f {binary} && echo OK"],
                           capture_output=True, text=True, timeout=5)
        return r.returncode == 0 and "OK" in r.stdout
    except Exception:
        return False

if not _check_previous_run_binary():
    print("ℹ 前序无 flash4 二进制, FLASH 引擎将自动编译")

def test_ch_center_run(run_real_flash: bool = False):
    """ch_center 场景测试

    默认 (run_real_flash=False): 仅验证 .par 生成 + 参数正确性 (快速, 无 FLASH 依赖)。
    run_real_flash=True (--real): 运行真实 FLASH 仿真 (耗时, 需 WSL+FLASH)。

    全局测试默认走快速路径; 真实仿真由 thin_layer_sandwich_si 覆盖,
    或显式 `pytest test_ch_center_run.py --real` 触发。
    """
    sc = get_scenario("ch_center")
    engine = FlashSimulatorEngine(sc, verbose=True)
    print(f"\n{'='*60}")
    print(f"  ch_center — {sc.description}")
    print(f"  sim_name: {sc.sim_name}")
    print(f"  mode: {'真实 FLASH 仿真' if run_real_flash else '参数生成验证 (快速)'}")
    print(f"{'='*60}\n")

    # 加速参数: 短激光脉冲 + 小 tmax → 快速仿真
    FAST_PARAMS = {
        "laser_times": [0, 0.3e-10],      # 30ps 短脉冲
        "laser_powers": [0, 5e14],
        "tmax": 0.13e-9,                  # 0.13ns
        "dtmax": 0.13e-9 * 1.05,          # 1.05*tmax (用户约定)
    }

    # 快速模式: 仅生成 .par 验证参数, 不运行 FLASH
    if not run_real_flash:
        par_content = sc.build_par(dict(sc.default_params, **FAST_PARAMS))
        assert "tmax" in par_content, "par 应包含 tmax"
        assert "eos_tab" in par_content, "cham 应为 eos_tab"
        assert "Z02_1.00-20260708_0851.cn4" in par_content, "应使用自研 He EOS (helium_hires)"
        assert "Z06_0.50-Z01_0.50-20260708_0850.cn4" in par_content, "应使用自研 CH EOS (ch_mix)"
        assert str(FAST_PARAMS["tmax"])[:6] in par_content or "1.3e-10" in par_content \
            or "1.300000e-10" in par_content, "tmax 应写入加速值"
        print("  ✅ .par 生成正确 (tmax/dtmax/EOS 验证通过)")
        print("  ℹ 真实 FLASH 仿真请运行: pytest test_ch_center_run.py --real")
        print(f"\n  ✅ ch_center 参数验证通过 (快速模式)")
        return

    out = engine.run(
        params_override=FAST_PARAMS,
        flash_timeout=300, keep_flash_raw=True,
    )
    run_dir = Path(out.run_dir)

    # 1. 运行状态
    print(f"\n── 1. 仿真状态 ──")
    assert out.success, f"FLASH 运行失败"
    print(f"  ✅ result.h5: {out.result_h5_path}")
    print(f"  ✅ 运行目录: {out.run_dir}")

    # 2. 目录结构
    print(f"\n── 2. 目录结构 ──")
    for d in ["sim_input", "sim_output", "database/flash_in", "database/flash_out"]:
        p = run_dir / d
        assert p.exists(), f"缺少目录 {d}"
        n = len(list(p.iterdir()))
        print(f"  ✅ {d}/ ({n} 项)")
    chk = list((run_dir / "sim_output").glob("lasslab_hdf5_chk_*"))
    assert len(chk) > 0
    print(f"     其中 chk: {len(chk)}")

    # 3. EOS 文件验证
    print(f"\n── 3. EOS 验证 ──")
    par = (run_dir / "sim_input" / sc.sim_name).with_suffix(".par").read_text()
    assert "Z02_1.00-20260708_0851.cn4" in par, "应使用自研 He EOS"
    assert "Z06_0.50-Z01_0.50-20260708_0850.cn4" in par, "应使用自研 CH EOS"
    assert "eos_tab" in par, "cham 应为 eos_tab"
    print(f"  ✅ cham: Z02_1.00-20260708_0851.cn4 (eos_tab)")
    print(f"  ✅ targ: Z06_0.50-Z01_0.50-20260708_0850.cn4")
    assert "sim_teleCham = 290.11375" in par or "2.901137e+02" in par
    print(f"  ✅ 初始温度: 290.11375K")

    # 4. result.h5
    print(f"\n── 4. 输出数据 ──")
    with h5py.File(out.result_h5_path, "r") as f:
        t, x = f["t"][:], f["x"][:]
        print(f"  ✅ t: {len(t)} pts [{t[0]:.2e}, {t[-1]:.2e}] s")
        print(f"  ✅ x: {len(x)} pts [{x[0]*1e4:.1f}, {x[-1]*1e4:.1f}] um")
        for v in out.fields:
            d = f[v][()]
            print(f"  ✅ {v}: shape={d.shape} range=[{d.min():.4e},{d.max():.4e}]")

    # 5. input_params.json
    print(f"\n── 5. 输入参数 ──")
    with open(run_dir / "database" / "flash_in" / "input_params.json") as fp:
        p = json.load(fp)
    print(f"  ✅ scenario: {p['scenario']}")

    print(f"\n  ✅ ch_center 测试通过")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="ch_center 场景测试")
    parser.add_argument("--real", action="store_true", help="运行真实 FLASH 仿真 (默认仅参数验证)")
    args = parser.parse_args()
    test_ch_center_run(run_real_flash=args.real)
