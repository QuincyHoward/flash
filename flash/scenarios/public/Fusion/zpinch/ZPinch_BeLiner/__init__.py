"""zpinch_beliner — Z 箍缩 Be-liner 几何验证场景 (1D 圆柱)。

复用 FLASH4.8 官方模块 magnetoHD/ZPinch（零修改）：Be liner + DD 充气 +
真空三区阶跃构型, +usm3t MHD + MGD 6 群 + Circuit FileInput 电流驱动。
运行输入 (zpinch_be.par / current.dat) 由场景专用 gen_inputs.py 生成
（暂不并入 input_gen/ 模块）。
入口: run_zpinch_verify.py (tmax=1e-12 s 极短验证, t≈0 电流≈0)。
"""

from pathlib import Path

from flash.scenarios.core.engine.base import SimulationScenario

_HERE = Path(__file__).resolve().parent

scenario = SimulationScenario(
    name="zpinch_beliner",
    description="Z 箍缩 Be-liner 几何验证 1D 圆柱 (官方 magnetoHD/ZPinch stock; MHD+MGD6+Circuit)",
    scenario_dir=_HERE,
    sim_input_dir=_HERE / "flash_input",   # gen_inputs.py 生成的 par/current.dat
    sim_name="magnetoHD/ZPinch",
    run_dir_name="outputfiles",
    basenm="zpbe_",
    flash_setup_args=(
        "-1d +cylindrical +ug -nxb=16 "
        "species=fill,line,vacu "
        "+mtmmmt +usm3t +mgd mgd_meshgroups=6"
    ),
    default_params={
        "tmax": 1.0e-12,
        "dtinit": 1.0e-14,
        "dtmax": 1.0e-12,
        "nend": 200,
        # ── 三区构型 (官方 stock) ──
        "sim_rhoType": 0,
        "sim_innerRadius": 0.29,
        "sim_thickness": 0.058,
        "sim_fill_dens": 3.0e-2,
        "sim_line_dens": 1.848,
        "sim_vacu_dens": 1.0e-5,
        # ── 网格 ──
        "xmin": 0.0,
        "xmax": 0.5,
        "iGridSize": 128,
        "iProcs": 8,
    },
)
