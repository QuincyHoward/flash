# flash-input-gen API 参考（已按本仓代码校正）

> 最后核对：2026-11-06 · commit 54a9f69 · 逐项核对自 `flash/input_gen/*/generator.py`
> 迁自用户级 flash-input-gen 技能 references/api-reference.md；⚠️ 标注项为相对旧版的变更。

## 统一入口

- `from flash.input_gen import create_input_files`
- 签名：`create_input_files(output_dir, dimension=1, simulation_name="LaserSlab", target_material="aluminum", chamber_gas="helium", n_beams=1, par_filename="laserslab.par", generate_scripts=True, copy_eos_files=True, setup_cmd=None, sim_user_dir=None, platform="local", flash_home=None)`
- ⚠️ `platform` 为中性路由标识：`"local"` / `"local/wsl_ubuntu22"` / `"hpc"` / `"hpc/nc_e"`（旧 scfa2696 等机名已废弃）
- ⚠️ `flash_home` 必须显式传入（见 SKILL.md 护栏 2）

## ParGeneratorExtended（`gen_par/generator.py`）

- 构造：`ParGeneratorExtended(simulation_name="LaserSlab", dimension=1)`
- `.set(key, value)` / `.unset(*keys)` / `.get(key, default)`
- `.set_dimension(dim)`
- `.set_material(material, target=True/False)`
- `.set_pulse(times, powers)` — 单脉冲时间(s)/功率(W)数组；`.set_pulses(list)` / `.add_pulse(dict)` 多脉冲
- ⚠️ 旧 `PulseShape` 类已删除：梯形/平顶等形状自行构造数组
- `.set_beams([BeamConfig])` / `.add_beam(beam)`
- `.set_species_material(...)` / `.set_species_materials([...])` / `.retain_species(names)` / `.assert_material_binding(...)`（物质绑定校验）
- `.set_domain(xmin, xmax, nblockx)` / `.set_time(tmax, ...)`
- `.reset_to(params_dict)` — 从已有 .par 参数字典重建
- `.generate() -> str` / `.save(filepath)`

## BeamConfig（`gen_par/generator.py`）

- `BeamConfig(beam_id, lens_x, target_x, wavelength=1.053, ...)`

## 材料数据库（`gen_par/materials.py`）

- `MATERIALS["aluminum"]`、`CHAMBER_GASES["helium"]`、`Material(name, file, rho, A, Z, ...)`
- `get_material(name)` / `list_materials()`

## ConfigGenerator（`gen_config/generator.py`）

- `save(output_path, simulation_path="hello/LaserSlab1d_new", target_material=None, chamber_gas=None, extra_datafiles=None, include_thomson=False, species_defs=None)`

## MakefileGenerator（`gen_makefile/generator.py`）

- `save(filepath, extra_f90_files=[])`

## SimDataGenerator / SimInitGenerator（`gen_sim_data` / `gen_sim_init`）

- `save(filepath, parameters=[...])`

## BlockGenerator + GridBuilder（`gen_sim_initblock/generator.py` + `grid.py`）

- `GridBuilder(dim=1, geometry="cartesian", domain={...})`
- `.set_material(species, **props)`（rho/tele/tion/trad 等）
- `.add_region(name, species="cham", **kwargs)`（含 x_range/is_target）
- `.from_laserslab_1d()` / `.from_laserslab_2d()` — 快捷模板；`.sample_1d/sample_2d/copy`
- `BlockGenerator(simulation_name=...)`：`.build(builder)` → `.save(filepath)`；`.preview()` / `.code()`
- ⚠️ 旧 `.visualize(builder)` 已由 `preview()` 取代（以源码为准）

## EOSOpacityGenerator（`gen_eos_op`）

- `copy_eos_file(material_name, dest_dir)`；材料映射见包内 `MATERIAL_EOS_MAP`

## ShellScriptGenerator（`gen_shell_script/generator.py`）

- `ShellScriptGenerator(config_dict)`；`build_setup_cmd(sim_path, objdir, parfile, flags)`
- `.save(filepath, platform, par_file=...)` — platform：`"wsl"` / `"windows"` / `"slurm"`

## DependencyChecker（`gen_checker/checker.py`）

- `DependencyChecker(sim_dir)`；`.run_all()` → `CheckResult`（`.summary()` / `.report()`）

## 绘图（`gen_checker/ploter/` — 注意拼写单 t）

- `DensityPlotter(generator=block_gen, builder=builder).plot().save(path)`
- `PulsePlotter(par_gen=gen, pulse_id=1).plot().save(path)`；另有 `RayPlotter`

## 已废弃路径（勿用）

- `from input_gen.par import ...` / `input_gen.par_calculator`（v1.x）
- `physimx_sim.flash.*` 前缀（旧仓库布局）→ 一律 `from flash.input_gen...`
- `PulseShape`、`BlockGenerator.visualize`、scfa2696 机名路由
