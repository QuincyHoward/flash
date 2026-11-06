---
name: flash-input-gen
description: FLASH 仿真输入文件生成器全流程（input_gen v2.0 的 12 个 gen_* 子包）：一键 create_input_files 或逐个调用 gen_par/gen_config/gen_makefile/gen_sim_data/gen_sim_init/gen_sim_initblock/gen_eos_op/gen_shell_script/gen_checker 生成 8+ 种输入文件与运行脚本。生成新仿真输入文件、搭建新场景目录时使用。触发词：生成输入文件、create_input_files、ParGeneratorExtended、Config 生成、Makefile 生成、Simulation_initBlock、运行脚本、依赖检查、BeamConfig、GridBuilder。
---

> 最后核对：2026-11-06 · commit 54a9f69
> 来源：用户级 flash-input-gen + input-gen-generator 技能吸收（API 已按本仓现行代码校正）

# FLASH 标准输入文件生成（flash-input-gen）

## 适用场景

- 从零搭建新仿真目录：一键生成 .par / Config / Makefile / Simulation_*.F90 / .cn4 / 运行脚本
- 精细定制：逐个调用生成器（脉冲、光束、多区材料、平台脚本）
- 生成后完整性检查与预诊断图

与 `flash-par-gen` 分工：本技能管**全子包生成流程**；`flash-par-gen` 管 **.par 排版规范**（10 section 顺序、对齐、数值格式）。与 `flash-newpara` 分工：标准参数用本技能；新增 `sim_*` 参数/多区剖面用 `flash-newpara`。

## 前置条件

- 本仓 venv 已激活；`flash.input_gen` 可导入（自包含，无外部模板依赖）
- 材料默认值权威：`flash/input_gen/gen_par/defaults.py`（`PARAMS_1D/2D/3D`）

## 操作步骤

### 1. 一键生成（最快路径）

```python
from flash.input_gen import create_input_files

result = create_input_files(
    output_dir="./sim_input",
    dimension=1,
    simulation_name="MySim",
    target_material="aluminum",
    chamber_gas="helium",
    n_beams=1,
    flash_home="~/QC/FLASH/FLASH4.8",   # ★ 必须显式传入（见护栏 2）
    platform="local",                    # 中性路由："local"/"local/wsl_ubuntu22"/"hpc"/"hpc/nc_e"
)
# result: {"par": ..., "config": ..., "makefile": ..., "sim_data": ...,
#          "sim_init": ..., "sim_initblock": ..., "eos_<material>": ...,
#          "script_windows/wsl/slurm": ...}
```

### 2. 逐个生成（灵活路径）

```python
from flash.input_gen.gen_par import ParGeneratorExtended, BeamConfig, MATERIALS, CHAMBER_GASES

gen = ParGeneratorExtended(simulation_name="MySim", dimension=1)
gen.set_material(MATERIALS["aluminum"], target=True)
gen.set_material(CHAMBER_GASES["helium"], target=False)
gen.set_pulse(times, powers)            # 时间(s)/功率(W) 数组；多脉冲用 set_pulses/add_pulse
gen.set_beams([BeamConfig(beam_id=1, lens_x=-1.0, target_x=0.0)])
gen.set_domain(xmin=0.0, xmax=160e-4, nblockx=4)
gen.set_time(tmax=1e-9)
gen.set("lrefine_max", 5)               # 覆盖 defaults.py 单个参数
gen.save("mysim.par")
```

其余生成器（均为 `flash.input_gen.<pkg>` 导入，`save()` 为主出口）：

| 子包 | 类 | 要点 |
|---|---|---|
| `gen_config` | `ConfigGenerator` | `save(path, simulation_path=..., target_material=..., chamber_gas=..., extra_datafiles=[...])`；新材料必须进 DATAFILES |
| `gen_makefile` | `MakefileGenerator` | `save(path, extra_f90_files=[...])` |
| `gen_sim_data` / `gen_sim_init` | `SimDataGenerator` / `SimInitGenerator` | 新参数 5 步流程的 2/3 步（见 flash-newpara） |
| `gen_sim_initblock` | `BlockGenerator` + `GridBuilder`（`grid.py`） | `GridBuilder(dim, geometry, domain)` → `set_material(species, **props)` → `add_region(name, species=...)`；快捷 `GridBuilder.from_laserslab_1d()`；`BlockGenerator(simulation_name).build(builder).save(path)`，另有 `preview()/code()` |
| `gen_eos_op` | `EOSOpacityGenerator` | `copy_eos_file(material, dest_dir)` 自动查表复制 .cn4 |
| `gen_shell_script` | `ShellScriptGenerator` | `build_setup_cmd(...)` + `save(path, "wsl"/"windows"/"slurm", par_file=...)` |
| `gen_checker` | `DependencyChecker`（`checker.py`） | `run_all()` → `summary()/report()`；绘图类在 `gen_checker/ploter`（PulsePlotter/DensityPlotter/RayPlotter） |

### 3. 完整 API 速查

见 `references/api-reference.md`（已按本仓代码校正）。

## 护栏与铁律

1. **Config/F90 禁止从零编写**：必须以 WSL 中已验证的 LaserSlab 模板为基准微调（Config 尾部追加 PARAMETER、检查 DATAFILES；F90 只改区域逻辑）。只有 .par 可由 `ParGeneratorExtended` 从头生成。Python 字符串模板拼 Config/F90 会漏掉 REQUIRES/DATAFILES/数百行配置，明令禁止。
2. **`flash_home` 必须显式传入** `create_input_files`：缺省回落 `$HOME/FLASH/FLASH4.8`（不含用户名），脚本 [1/5] 环境检查直接 exit 1 但管道返回码为 0 → 假"完成"零输出。建议传 `runner.discover_flash_home()` 探测结果。
3. **平台标识用中性路由**（`"local"` / `"hpc/nc_e"`），勿硬编码具体超算机名/账号；用户名一律经 `flash._core.credentials` 读取。
4. **.sh 文件必须 LF 换行**：Windows 写文件先 `content.replace("\r\n", "\n")`，否则 WSL shebang 损坏。
5. **必须实际运行验证**：setup → make → run 缺一不可；静态检查发现不了参数名不匹配/F90 语法错误。
6. 生成产物保存到项目 `sim_input/` 并附预诊断图（`laser_pulse.png`、`initial_density.png`）。

## 常见坑

- 旧路径 `physimx_sim.flash.*` / `input_gen.par`（v1.x）已废弃，一律 `from flash.input_gen...`
- 旧 `PulseShape.trapezoid` 类已删除：脉冲形状自行构造 times/powers 数组后 `set_pulse()`
- `gen_checker` 绘图子模块拼写是 `ploter`（单 t），别写成 `plotter`
- Config 漏 DATAFILES → setup 不复制 .cn4 → 运行时找不到 EOS 表

## 关联资源

- `flash/input_gen/README.md`（子包总览）、`flash/input_gen/gen_par/README.md`、`flash/input_gen/gen_checker/README.md`
- `docs/par_format_guide.md`、`flash-par-gen`（排版规范）、`flash-newpara`（新参数/多区剖面）
- `flash-run-deploy`（三模式运行）、本技能 `references/api-reference.md`
