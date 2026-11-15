"""hohlraum_auch — 间接驱动黑腔几何验证场景 (2D rz)。

Au 圆柱黑腔 + 中心 CH 靶丸 + 低密度 He 充气。
入口: run_hohlraum_verify.py (tmax=1e-13 s 极短验证; 辐射 MGD 10 群已开)。
FLASH 源文件 (Config/F90/par/cn4) 直接存放于本场景目录。
"""

from pathlib import Path

from flash.scenarios.core.engine.base import SimulationScenario

_HERE = Path(__file__).resolve().parent

scenario = SimulationScenario(
    name="hohlraum_auch",
    description="间接驱动黑腔几何验证 2D rz (Au 腔 + CH 靶丸 + He 充气, MGD 10 群)",
    scenario_dir=_HERE,
    sim_input_dir=_HERE / "flash_input",   # FLASH 源文件在 flash_input/ 子目录
    sim_name="QC/Hohlraum_AuCH",
    run_dir_name="outputfiles",
    basenm="hohlraum_",
    flash_setup_args=(
        "-2d +cylindrical -nxb=16 -nyb=16 "
        "+hdf5typeio species=cham,cgas,caps,gold "
        "+mtmmmt +laser +uhd3t +mgd mgd_meshgroups=10"
    ),
    default_params={
        "tmax": 1.0e-13,
        "dtinit": 1.0e-15,
        "dtmax": 1.0e-13,
        "nend": 500,
        # ── 黑腔几何 (cm) ──
        "sim_hohlInnerR": 0.272,
        "sim_hohlOuterR": 0.275,
        "sim_hohlHalfLen": 0.5005,
        "sim_capThick": 3.0e-3,
        "sim_lehRadius": 0.143,
        "sim_capRadius": 0.1,
        "sim_capShellThick": 1.5e-2,
        # ── 材料密度 (g/cm^3) ──
        "sim_rhoGold": 19.32,
        "sim_rhoCaps": 1.0,
        "sim_rhoGas": 1.0e-3,
        "sim_rhoFill": 9.6e-4,
        "sim_rhoVacuum": 1.0e-6,
        # ── 初始温度 (K) ──
        "sim_teleGold": 290.11375,
        "sim_teleCaps": 290.11375,
        "sim_teleGas": 290.11375,
        "sim_teleCham": 290.11375,
        # ── 网格 ──
        "xmin": 0.0,
        "xmax": 0.34,
        "ymin": -0.62,
        "ymax": 0.62,
        "nblockx": 2,
        "nblocky": 7,
        "lrefine_min": 1,
        "lrefine_max": 5,
    },
)
