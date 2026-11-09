"""direct_drive_ch — 直接驱动 CH 靶丸几何验证场景 (2D rz)。

自由放置 CH 球壳靶丸 + 内 He 气 + 外部 He 真空示踪 (无黑腔)。
直接驱动参考: LLE 基线 NIF DD 靶 (3.4mm 直径 CH/DT, OV3/5) 与 OMEGA
1mm 级靶; 本场景用与 hohlraum_auch 一致的 1mm CH 壳 + He 气便于跨场景对照。
入口: run_direct_verify.py (tmax=1e-13 s 极短验证; 辐射 MGD 10 群已开)。
FLASH 源文件 (Config/F90/par/cn4) 直接存放于 flash_input/ 子目录。
"""

from pathlib import Path

from flash.scenarios.core.engine.base import SimulationScenario

_HERE = Path(__file__).resolve().parent

scenario = SimulationScenario(
    name="direct_drive_ch",
    description="直接驱动 CH 靶丸几何验证 2D rz (自由 CH 壳 + He 气 + 真空, MGD 10 群)",
    scenario_dir=_HERE,
    sim_input_dir=_HERE / "flash_input",   # FLASH 源文件在 flash_input/ 子目录
    sim_name="QC/CH_Capsule_DD",
    run_dir_name="outputfiles",
    basenm="ddch_",
    flash_setup_args=(
        "-2d +cylindrical -nxb=16 -nyb=16 "
        "+hdf5typeio species=cham,cgas,caps "
        "+mtmmmt +laser +uhd3t +mgd mgd_meshgroups=10"
    ),
    default_params={
        "tmax": 1.0e-13,
        "dtinit": 1.0e-15,
        "dtmax": 1.0e-13,
        "nend": 500,
        # ── 靶丸几何 (cm) ──
        "sim_capRadius": 0.1,
        "sim_capShellThick": 1.5e-2,
        # ── 材料密度 (g/cm^3) ──
        "sim_rhoCaps": 1.0,
        "sim_rhoGas": 1.0e-3,
        "sim_rhoVacuum": 1.0e-6,
        # ── 初始温度 (K) ──
        "sim_teleCaps": 290.11375,
        "sim_teleGas": 290.11375,
        "sim_teleCham": 290.11375,
        # ── 网格 ──
        "xmin": 0.0,
        "xmax": 0.14,
        "ymin": -0.14,
        "ymax": 0.14,
        "nblockx": 1,
        "nblocky": 2,
        "lrefine_min": 1,
        "lrefine_max": 5,
    },
)
