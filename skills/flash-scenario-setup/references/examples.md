# FLASH 端到端示例集（已按本仓现行 API 校正）

> 最后核对：2026-11-06 · commit 54a9f69
> 迁自用户级 flash-examples 技能（5 例），导入前缀/方法名已按 `flash/input_gen`、`flash/output_pro`、`flash/flash_run` 现行代码校正；示例为骨架参考，实际操作以各技能护栏为准

## 示例 1: 双光束 Al 靶仿真

```python
from flash.input_gen import create_input_files
from flash.input_gen.gen_par import ParGeneratorExtended, BeamConfig, MATERIALS, CHAMBER_GASES
from flash.input_gen.gen_shell_script import ShellScriptGenerator

sim_name = "LaserSlab1d_2beam"
setup_cmd = ShellScriptGenerator.build_setup_cmd(
    sim_path=f"QC/{sim_name}", objdir=f"QC/object_{sim_name}",
    parfile=f"{sim_name}.par",
    flags="-1d +cartesian -nxb=16 +hdf5typeio species=cham,targ +mtmmmt +laser +uhd3t +mgd mgd_meshgroups=10",
)

# ⚠️ flash_home 必须显式传入（缺省回落路径会导致脚本静默失败）
result = create_input_files(
    output_dir=f"./simulations/{sim_name}",
    dimension=1, target_material="aluminum", chamber_gas="helium",
    n_beams=2, simulation_name=sim_name,
    setup_cmd=setup_cmd,
    flash_home="~/QC/FLASH/FLASH4.8",     # 或 runner.discover_flash_home()
    platform="local",
)

# 精细定制 .par（唯一可从头生成的文件）
gen = ParGeneratorExtended(simulation_name=sim_name, dimension=1)
gen.set_material(MATERIALS["aluminum"], target=True)
gen.set_material(CHAMBER_GASES["helium"], target=False)
gen.set_beams([BeamConfig(beam_id=1, lens_x=-1.0, target_x=0.0),
               BeamConfig(beam_id=2, lens_x=1.0, target_x=0.0)])
gen.set_pulse([0.0, 40e-12, 1.04e-9, 1.08e-9],      # 旧 PulseShape 已删，直接给数组
              [0.0, 5e14, 5e14, 0.0])
gen.set_domain(xmin=-0.016, xmax=0.016, nblockx=4)
gen.set_time(tmax=1.2e-9)
gen.save(f"./simulations/{sim_name}/{sim_name}.par")
```

后续：flash-run-deploy 三模式运行 → 短时验证（tmax≈1e-11）→ flash-output-analysis。

## 示例 2: 多区密度剖面（新参数）

```python
from flash.input_gen.gen_newpara import NewParaGenerator   # 现行 API

gen = NewParaGenerator()
gen.vacuum_height = 0.014
gen.species_list = ["cham", "targ", "poly"]   # 物种名 ≤4 字符
gen.base_density = 2.7
gen.add_zone(height=0.002, profile=1, p1=5.0e-4, name="targ 指数衰减")
gen.add_zone(height=0.002, profile=0, name="poly 常数")
gen.validate()
gen.generate_all("./sim_input")   # 一键生成 par/Config/F90 全套
```

⚠️ 旧示例的 `gen.set("sim_targDensProfile", 1)` / `NewParaGenerator(output_dir=...)` API 已废弃。
网格自定义仍走 `flash.input_gen.gen_sim_initblock.grid.GridBuilder`（`set_material(species, rho=..., tele=...)` + `add_region(name, species=...)`）。完整参考 `test/newpara/`。

## 示例 3: 新增运行时参数（5 步流程）

Config `PARAMETER sim_foamDensity REAL 0.5` → Simulation_data.F90 声明 →
Simulation_init.F90 `RuntimeParameters_get` → Simulation_initBlock.F90 区域逻辑 →
.par `gen.set("sim_foamDensity", 0.5)`。
必须在已验证 LaserSlab 模板上微调；详见 flash-newpara / `gen_newpara/README.md`。

## 示例 4: 分析 HDF5 输出

```python
from flash.output_pro.loader import FlashDataLoader
from flash.output_pro.plotter import FlashPlotter

loader = FlashDataLoader("hdf5_plt_cnt_0080")
data = loader.load("dens", compute_derived=True)

print(f"仿真时间: {data.simulation_time:.4e} s")        # ⚠️ 属性是 simulation_time，非 metadata['sim_time']
print(f"密度范围: [{data.get('dens').min():.4e}, {data.get('dens').max():.4e}]")

plotter = FlashPlotter(data)
plotter.plot("dens", save_path="dens.png")
plotter.plot_all(save_dir="./analysis_plots/")
```

x-t 时空图必须 pcolormesh（见 flash-output-analysis §2）；批处理用 `load_folder_parallel`。

## 示例 5: 超算批量运行

```python
from flash.flash_run.remote.remote_deploy import FlashRemoteDeploy
from flash.flash_run.remote.route_tester import RouteTester, ROUTES_NC_E

route = RouteTester().get_best_route(ROUTES_NC_E)   # ⚠️ get_best_route（旧 find_best_route 已改名）
deploy = FlashRemoteDeploy(credential="flash_ssh")      # 构造时自动选路
deploy.connect()
deploy.upload("./simulations/power_scan", "~/flash_jobs/power_scan/")

jobs = [deploy.submit_job(f"~/flash_jobs/power_scan/power_{pf}/submit_flash.sh")
        for pf in [0.5, 1.0, 1.5, 2.0]]                 # ⚠️ submit_job（旧 submit_sbatch 已改名）
for jid in jobs:
    print(deploy.check_job(jid))                        # ⚠️ check_job（旧 poll_job 已改名）
deploy.download("~/flash_jobs/power_scan/", "./power_results/")
```

生产级批量提交优先走 `slurm_control.run_job_chain`（flash-run-deploy §4）；结果回收用 flash-hpc-fetch。
