"""
test_engine_dryrun.py — 测试 FlashSimulatorEngine dry-run

验证:
  - 引擎可创建正确的目录结构
  - 输入参数 JSON 正确
  - .par 文件复制到运行目录
  - sim_input/ 完整复制
  - run() 失败模式正确处理
"""

import sys, tempfile, json
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


from flash.scenarios.registry import get_scenario, list_scenarios
from flash.scenarios.simulator import FlashSimulatorEngine

# 私有场景 (仅本地): 缺失时跳过整个模块 (发布环境无 thin_layer/grad_dens)
_PRIVATE_REQUIRED = ["thin_layer_sandwich_si", "thin_layer_sandwich_al"]
_available = [s[0] for s in list_scenarios()]
if not all(n in _available for n in _PRIVATE_REQUIRED):
    import pytest
    pytest.skip(
        "私有场景未注册 (发布环境, 仅本地包含 thin_layer_sandwich)",
        allow_module_level=True,
    )


def test_engine_dry_run():
    """测试引擎 dry-run (不执行 FLASH)"""
    sc = get_scenario("thin_layer_sandwich_si")
    engine = FlashSimulatorEngine(sc, verbose=False)

    with tempfile.TemporaryDirectory() as td:
        out = engine.run(
            runs_dir=td,
            run_flash=False,
            run_id="000999",
        )

        run_dir = Path(out.run_dir)
        print(f"\n── dry-run 结果 ──")
        print(f"  运行目录: {run_dir}")

        # 验证目录结构
        dirs = ["sim_input", "sim_output", "database/flash_in", "database/flash_out"]
        for d in dirs:
            assert (run_dir / d).exists(), f"缺少目录: {d}"
            print(f"  ✔ {d}/")

        # 验证 sim_input/ 内容
        sim_input = run_dir / "sim_input"
        assert list(sim_input.glob("*.F90")), "缺少 .F90 源文件"
        assert list(sim_input.glob("*.cn4")), "缺少 .cn4 EOS 文件"
        assert (sim_input / "Config").exists(), "缺少 Config"
        assert (sim_input / "Makefile").exists(), "缺少 Makefile"
        assert (sim_input / f"{sc.sim_name}.par").exists(), "缺少 .par 文件"
        print(f"  ✔ sim_input/: {len(list(sim_input.iterdir()))} 文件")

        # 验证 flash_in/
        params_path = run_dir / "database" / "flash_in" / "input_params.json"
        assert params_path.exists(), "缺少 input_params.json"
        with open(params_path) as f:
            params = json.load(f)
        assert "scenario" in params
        assert params["scenario"] == "thin_layer_sandwich_si"
        assert "laser_powers" in params
        print(f"  ✔ input_params.json: 场景={params['scenario']}")

        # 验证输出 (无 FLASH = 失败)
        assert out.success == False
        assert out.run_dir == str(run_dir)
        print(f"  ✔ out.success={out.success} (期望无 FLASH 失败)")
        print(f"  ✔ out.run_dir={out.run_dir}")


def test_engine_with_al_scenario():
    """测试 Al 场景的引擎 dry-run

    注意: al-imx-003.cn4 是 FLASH 分发的 EOS 表 (License §3 禁止再分发),
    发布包不包含。若缺失 (用户需从 FLASH Center 自备) 则跳过, 仅验证 .par 参数。
    """
    import pytest
    sc = get_scenario("thin_layer_sandwich_al")
    engine = FlashSimulatorEngine(sc, verbose=False)

    # Al EOS 表为 FLASH 分发表, 发布包可能缺失 → 跳过文件存在性断言
    al_eos = sc.sim_input_dir / "al-imx-003.cn4"
    has_al_eos = al_eos.exists()

    with tempfile.TemporaryDirectory() as td:
        out = engine.run(runs_dir=td, run_flash=False, run_id="000001")
        run_dir = Path(out.run_dir)

        # 检查 sim_input 中有 Al 特定的 EOS 文件 (若源表存在)
        sim_input = run_dir / "sim_input"
        if has_al_eos:
            assert (sim_input / "al-imx-003.cn4").exists(), "缺少 Al EOS 文件"
        else:
            pytest.skip("al-imx-003.cn4 为 FLASH 分发表 (License §3 不可再分发), 发布包不含; 用户需自备")

        # 检查 .par 中为 Al (规范空格后比较)
        with open(sim_input / f"{sc.sim_name}.par") as f:
            par = f.read()
        normalized_par = " ".join(par.split())
        assert "ms_targA = 26.9815" in normalized_par, ".par 中应含 Al 原子量"
        print(f"\n  ✔ Al 场景: .par 含 Al 参数, EOS 文件存在")


def test_engine_plot():
    """测试引擎 plot 方法 (读取 Si 场景已有 result.h5)"""
    from flash.scenarios.registry import get_scenario
    from flash.scenarios.simulator import FlashSimulatorEngine

    sc = get_scenario("thin_layer_sandwich_si")
    engine = FlashSimulatorEngine(sc, verbose=False)

    # 查找已有 result.h5
    existing_results = sorted(
        Path(sc.scenario_dir / "runs").glob("*/database/flash_out/result.h5")
        if (sc.scenario_dir / "runs").exists() else []
    )

    if not existing_results:
        print("\n  ⚠ 无已有 result.h5, 跳过 plot 测试")
        print("  (首次需先运行仿真生成结果)")
        return

    latest = existing_results[-1]
    print(f"\n  ✔ 找到已有 result.h5: {latest}")

    # 测试 plot
    from flash.scenarios.simulator import SimulationOutput
    mock_output = SimulationOutput(
        result_h5_path=str(latest),
        run_dir=str(latest.parent.parent.parent),
        n_chk=100, n_timesteps=100,
        fields=["dens", "tele", "tion", "pres"],
        input_params={}, success=True,
    )

    with tempfile.TemporaryDirectory() as td:
        engine.plot(mock_output, out_dir=td)
        plot_files = list(Path(td).glob("*.png"))
        assert len(plot_files) >= 1, "应至少生成一张图"
        print(f"  ✔ 生成 {len(plot_files)} 张图: {[p.name for p in plot_files]}")


if __name__ == "__main__":
    test_engine_dry_run()
    test_engine_with_al_scenario()
    test_engine_plot()
    print("\n✅ 所有引擎测试通过")
