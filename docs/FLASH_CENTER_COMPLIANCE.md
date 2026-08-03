# FLASH Center 合规排除机制

## 法律依据

FLASH License Agreement §3 明确规定：

> "Users of the FLASH Code pursuant to this License Agreement agree that the FLASH Code,
> or any part of the code, can only be released and distributed by the Flash Center;
> **individual users of the FLASH Code are not free to re-distribute the FLASH Code,
> or any of its components, outside the Center.**"

违反此条款将构成对 University of Chicago / University of Rochester 版权的侵犯。

## 排除范围

以下文件/目录包含 FLASH Center 版权材料，已通过 `.gitignore` 和 `pyproject.toml` 双重排除：

| 类别 | 路径规则 | 说明 |
|------|---------|------|
| **FLASH 源码包** | `**/flash_src/`, `**/FLASH4.8/`, `**/FLASH4.8.tar.gz` | FLASH4.8 + mpich/hdf5/hypre 源码 (任意层级) |
| **FLASH 示例源码** | `**/SimulationMain/` | FLASH 4.8 全部 55 个示例问题源码 |
| **FLASH LaserSlab 示例** | `**/flash_demo/LaserSlab/`, `**/LaserSlabPAR.xlsx` | 官方示例完整文件集 (根目录与 scenarios 下均覆盖) |
| **FLASH 物性表** | `*.cn4`, `*.cnr`, `*.imx`, `*.imx.gz`, `*.ses`, `*.epsi` | IONMIX4 格式 EOS/不透明度表全局排除; 自研 `Z*.cn4` 例外保留 |
| **FLASH 参考源码** | `**/ref_f90s/`, `**/refs/`, `**/abjt_03.f` | 从 FLASH4.8 源码树复制的参考文件 |
| **IONMIX 源码 / MultiEOS 数据** | `**/MultiEOS/` | FLASH 分发组件 (ionmix 自研 Python 包装除外) |
| **FLASH 用户手册** | `docs/flash4_ug_4p8.md`, `docs/flash4_ug_4p8_temp.txt` | FLASH 4.8 User's Guide (含 .pdf, 由 `*.pdf` 排除) |
| **FLASH 官网存档** | `**/para_doc/` | Flash Center 官网页面/图片存档 |
| **FLASH 协议原文** | `license_agreement_FLASH.txt` | 旧版协议副本; 官方协议文本保留于 `docs/license_agreement.txt` |
| **HDF5 输出** | `*.h5`, `*.hdf5`, `*_hdf5_chk_*`, `*_hdf5_plt_cnt_*` | FLASH checkpoint/plot 文件 |
| **运行产物** | `**/demo_task/`, `**/runs/`, `**/outputfiles/`, `**/output/`, `**/inputfiles/`, `**/temp/`, `runs_*/`, `test/scenarios/runs_*/`, `**/run_tools/runs_*/`, `test/grid_rede*/`, `test/newpara/{flash_input,flash_profile,output}/` | FLASH 编译输出 + HDF5 + 中间产物 |
| **旧副本/内部** | `output_processors_copy/`, `input_gen/gen_eos_op_copy/`, `scenarios - 副本/`, `.workbuddy/`, `.codebuddy/`, `*.bak` | 未迁移旧目录与内部工作区 |

**自研 EOS 表例外**（`Z*.cn4` = ionmix 自生成，发布包必需）：
```
!**/Gen_eos_op_data/**/Z*.cn4
!**/sim_input*/Z*.cn4
```

## 保留的原创内容

以下内容为 PhySimX Contributors 原创，不受 FLASH License 限制，**可以公开分发**：

| 路径 | 说明 |
|------|------|
| `flash/` (.py) | Python 包核心代码 |
| `input_gen/gen_par/` | .par 参数生成器（原创） |
| `input_gen/gen_config/` | Config 编译配置生成器（原创） |
| `input_gen/gen_makefile/` | Makefile 生成器（原创） |
| `input_gen/gen_sim_init/` | Simulation_init.F90 生成器（原创） |
| `input_gen/gen_sim_initblock/` | Simulation_initBlock.F90 生成器（原创） |
| `input_gen/gen_sim_data/` | Simulation_data.F90 生成器（原创） |
| `input_gen/gen_eos_op/generator.py` | EOS 材料注册表（原创） |
| `input_gen/gen_eos_op/eos_op_data/Gen_eos_op_data/` | IONMIX 自生成物性表（原创） |
| `input_gen/gen_shell_script/` | 运行脚本生成器（原创） |
| `input_gen/gen_Grid_markRefineDerefine/` | 网格细化生成器（原创，不含 `refs/` 参考源码） |
| `input_gen/gen_checker/` | 诊断检查器（原创） |
| `output_processors/` (.py) | HDF5 输出分析器（原创） |
| `flash_run/` (.py) | 运行管理器（原创） |
| `scenarios/` (.py + 场景 .F90/.cn4) | 场景系统（原创，场景 .F90 为 FLASH 示例修改版，见 LICENSE §4） |
| `_core/` (.py) | 核心抽象层（原创） |
| `scripts/` | 工具脚本（原创） |
| `docs/` (.md) | 文档（原创，不含 FLASH User's Guide） |

## 合规验证

### 推送到 Gitee 前的检查清单

```bash
# 1. 确认 .gitignore 生效
git status

# 2. 确认 FLASH 文件已从索引中移除 (以下命令均应无输出)
git ls-files input_gen/SimulationMain/              # 应为空
git ls-files flash_src/                              # 应为空
git ls-files | grep -E "LaserSlab/LaserSlab|ReDo"    # 应为空
git ls-files | grep -E "\.(cn4|cnr|imx|ses|h5|hdf5)$" # 应为空 (自研 Z*.cn4 需单独确认)
git ls-files | grep -E "ref_f90s|/refs/|flash4_ug"   # 应为空

# 3. 全库 add 预演: 确认未来新增也不会混入 FLASH 材料
git add -n . | grep -E "\.(cn4|cnr|imx|ses|h5)$"     # 应仅剩自研 Z*.cn4

# 4. 构建 sdist 并检查内容
python -m build --sdist
tar -tzf dist/flash_sim-*.tar.gz | grep -E "(SimulationMain|flash_src|FLASH_eos_op_data|LaserSlab/LaserSlab|ReDo|\.h5|\.cn4)"
# 以上命令应无输出

# 5. 确认场景 .F90 修改声明完整 (FLASH 协议 §4(a))
#    每个源自 FLASH 示例的修改文件头部应含 "MODIFIED BY: PhySimX Contributors"
grep -L "MODIFIED BY: PhySimX Contributors" scenarios --include="*.F90"   # 应为空
```

### 从 Git 历史中清除（可选）

如果 Git 历史中包含侵权文件，建议使用 `git filter-branch` 或 `BFG Repo-Cleaner` 清除：

```bash
# 方案A: git filter-branch (适合小仓库)
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch -r input_gen/SimulationMain/ flash_src/ scenarios/flash_demo/LaserSlab/LaserSlab/ scenarios/flash_demo/LaserSlab/LaserSlabca1d/ scenarios/flash_demo/LaserSlab/LaserSlabpy/ scenarios/flash_demo/LaserSlab/ReDo*/" \
  --prune-empty --tag-name-filter cat -- --all

# 方案B: BFG Repo-Cleaner (适合大仓库)
# java -jar bfg.jar --delete-folders "SimulationMain" --delete-folders "flash_src" ...
```

## PhySimX 团队署名与 flash-sim 商用说明

flash-sim（flash 仿真辅助 Python 包）由**绵阳市的 PhySimX 团队**原创开发。除 FLASH Center 的合规要求外，相关署名与商用事宜如下：

### 出版物致谢

使用 flash-sim 产生的任何出版物，须在致谢部分感谢**绵阳市的 PhySimX 团队**开发了该仿真辅助 Python 包。建议文案：

> "We acknowledge the PhySimX team (Mianyang, China) for developing the flash-sim auxiliary Python package used in this work."

### 商用说明

flash-sim 的 Python 代码以 Apache 2.0 许可，但其商用须遵守所有适用许可，包括 FLASH 仿真引擎的 [FLASH License Agreement](https://flash.rochester.edu) §5（商用须获 Flash Center 主任书面批准）。商用场景下的授权与责任，以届时适用的许可及书面约定为准。

> Apache 2.0 仅覆盖本包 Python 代码，不授予 FLASH 仿真引擎的商用权利。

---

## 免责声明

本合规机制尽力确保 flash-sim 包不包含 FLASH Center 的版权材料。

---

*最后更新: 2026-08-03*
*依据: FLASH License Agreement v4.8*
