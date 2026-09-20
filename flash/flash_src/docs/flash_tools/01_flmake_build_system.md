# FLASH flmake 构建系统

## 概述

flmake 是 FLASH 4.8 的现代构建与运行管理系统，位于 `tools/python/flmake/`。它提供了一套命令行工具，覆盖 FLASH 仿真从**配置(setup)**、**编译(build)**、**运行(run)**到**清理(clean)**的完整生命周期。

## 架构设计

flmake 采用模块化架构，通过 `main.py` 统一调度所有子命令：

```
flash.flmake
├── main.py              # 主入口, 命令派发
├── setup.py             # 仿真配置
├── build.py             # 编译构建
├── run.py               # 运行执行
├── restart.py           # 重启仿真
├── clean.py             # 清理目录
├── merge.py             # 合并运行目录
├── diffpar.py           # 参数文件比较
├── reproduce.py         # 重现运行
├── qsub.py              # 作业提交
├── sweep.py             # 参数扫描
├── help_cmd.py          # 帮助系统
├── log.py               # 日志查看
├── lsruns.py            # 运行历史浏览
├── mv.py                # 运行目录移动
├── rm.py                # 运行目录删除
├── metadata.py          # 元数据编辑
├── pargen.py            # 参数文件生成
├── flmail.py            # 邮件通知
├── template.py          # 模板引擎
├── gen_files.py         # 自动文件生成
├── lib_union.py          # 库依赖管理
├── link_file_list.py     # 源文件链接
├── flash_lib.py          # 库配置解析
├── lazy_file.py          # 惰性文件写入
├── rp_info.py            # 运行时参数追踪
├── var_info.py           # 变量追踪
├── setup_globals.py      # 全局变量
├── setup_configuration.py # 单元配置管理
├── setup_parse.py        # 命令行解析
├── utils.py              # 工具函数
└── logger.py             # 日志记录
```

## 命令参考

### `flmake setup` — 初始化仿真

配置一个新的 FLASH 仿真项目。

```bash
flmake setup [options] <simulation_name>
```

**功能**:
- 解析命令行参数（维度、块大小、单元选择等）
- 读取仿真 `Config` 文件，构建单元依赖树（`ConfigurationList`）
- 解析 `REQUIRES`/`REQUESTS`/`EXCLUSIVE`/`CONFLICTS` 约束
- 通过符号链接/复制将源文件链接到 setup 目录
- 生成 `Makefile`、`Flash.h`（预处理定义）、运行时参数初始化代码
- 生成仿真映射文件（如 `Simulation_mapIntToStr.F90`）
- 写入 `flash_desc.json` 元数据

**常用选项**:
```
--auto          自动解析依赖
--1d/--2d/--3d  设置维度
--nxb=N         设置 x 方向块大小
--maxblocks=N   设置最大块数
+unitname       添加单元
-without-unit   排除单元
-debug/-opt/-test 构建模式
```

**依赖**: `setup_parse`, `setup_globals`, `setup_configuration`, `lib_union`, `link_file_list`, `gen_files`, `template`, `rp_info`, `var_info`, `utils`, `dsl.configuration`

### `flmake build` — 编译仿真

```bash
flmake build [-j N]
```

**功能**:
- 在 setup 目录中执行 `make -j N`
- 将生成的对象文件移动到 build 目录
- 计算可执行文件的 SHA1 哈希值
- 将构建元数据写入 `flash_desc.json`

**依赖**: 需先执行 `flmake setup`

### `flmake run` — 运行仿真

```bash
flmake run [options] [-- <mpirun_args>]
```

**功能**:
- 创建唯一运行目录 ID（格式 `run-XXXX-XX-XX--XX-XX-XX--NNNN`）
- 从构建目录复制 `flash4` 可执行文件和数据文件
- 应用 run-control 参数覆盖 `flash.par`
- 执行 `mpirun -n NPROCS ... ./flash4`
- 写入运行元数据

### `flmake restart` — 重启仿真

```bash
flmake restart <previous_run_dir>
```

**功能**:
- 将前次运行的数据文件符号链接到新运行目录
- 自动计算并设置 `checkpointFileNumber`、`plotFileNumber`
- 设置 `restart = .true.`

### `flmake clean` — 清理目录

```bash
flmake clean [--level N]
```

| 级别 | 删除内容 |
|------|---------|
| 1 | 运行目录 (`run-*`) 和 VCS 临时目录 |
| 2 | 级别1 + 构建目录 |
| 3 | 级别2 + setup 目录 + `flash_desc.json` |

### `flmake merge` — 合并运行

```bash
flmake merge <run1> <run2> ...
```

将多个运行目录及其历史合并到新目录，保留所有元数据文件（带后缀重命名）。

### `flmake diffpar` — 参数比较

```bash
flmake diffpar <file1.par> <file2.par>
```

比较两个运行时参数文件，显示：
- 值不同的共同参数
- 仅在文件1中的参数
- 仅在文件2中的参数
- 退出码 1 表示有差异（UNIX diff 兼容）

### `flmake reproduce` — 重现运行

```bash
flmake reproduce <run_dir>
```

从 `flash_desc.json` 读取描述，检出之前版本的源代码，应用补丁，重新执行 setup → build → run。

**支持**: git, hg, svn, release（平面文件）

### `flmake qsub` — 作业提交

```bash
flmake qsub [qsub_options] [-- run_options]
```

先以 `--dry-run` 模式执行 run/restart，然后通过 `qsub` 提交到调度系统。

**主机特定**: 支持 `eureka_mod()` 和 `beagle_mod()` 生成包装脚本。

### `flmake sweep` — 参数扫描

```bash
flmake sweep
```

从 run-control 文件读取 `sweep` 配置，对每组参数自动调用 `flmake run`。

### `flmake mv` / `flmake rm` — 移动/删除运行

```bash
flmake mv <src> <dst>
flmake rm <run_dir>
```

移动或删除运行目录，自动记录操作日志。

### `flmake ls-runs` — 列出运行

```bash
flmake ls-runs
```

将本地运行目录显示为基于历史的树状结构。

### `flmake log` — 查看日志

```bash
flmake log [-n N]
```

显示最后 N 条 flmake 命令历史记录（运行 ID、目录、命令、用户、时间戳）。

### `flmake help` — 帮助

```bash
flmake help [command]
```

显示所有命令列表或特定命令的详细用法。

### `flmake metadata` — 元数据

```bash
flmake metadata [-e]
```

显示或编辑（`-e`）FLASH 工具的 `metadata.json` 文件。

### `flmake pargen` — 参数生成

```bash
flmake pargen
```

从 run-control 文件提取 `parameters` 字典并输出为 `flash.par` 格式。

### `flmake email` — 邮件通知

```bash
flmake email --start|--stop <recipient>
```

通过 SMTP（Gmail）发送仿真启动/停止通知。

## 核心模块解析

### `setup_globals.py` — 全局状态

单例类 `GVarsClass` 管理所有全局状态:
- 项目目录路径
- 仿真维度 (NDIM)
- 块大小 (NXB, NYB, NZB)
- 预处理器定义列表
- 日志级别 (DEBUG/INFO/WARN/ERROR)
- 几何类型、网格类型、编译器

### `setup_configuration.py` — 单元配置

`ConfigurationList` 类封装 FLASH 单元集合:
- `add_units()` / `remove_units()` — 增删单元
- `populate()` — 主入口: 读取 Units 文件，添加仿真单元，解析依赖
- `generate_units_file()` — 生成 Units 文件
- `check_exclusivity()` / `check_conflicts()` — 验证约束
- `get_link_order()` — 基于层次排序（CHILDORDER）
- `get_rp_info()` / `get_var_info()` — 聚合运行时参数和变量
- `create_makefiles()` — 生成 Makefile 存根

### `dsl/configuration.py` — Config 文件 DSL 解析器

解析 FLASH 的 `Config` 文件，支持:
- `D`, `PARAMETER`, `VARIABLE` 等配置指令
- `IF`/`ELSE`/`ENDIF` 预处理
- `REQUIRES`, `REQUESTS`, `EXCLUSIVE`, `CONFLICTS` 约束
- `LINKIF`, `CHILDORDER`, `DATAFILES` 等
- Python 生成式 Config 文件 (`##python:genLines`)

### `rp_info.py` — 运行时参数追踪

`RPInfo` 类:
- 解析 `Config` 文件中的 `RUNTIMEPARAMETERS`
- 生成 `rp_initParameters.F90` 初始化代码
- 生成 `default.par` 默认参数文件
- 参数类型验证（REAL/INTEGER/BOOLEAN/STRING）和范围检查

### `gen_files.py` — 自动文件生成

生成所有自动生成的文件:
- `Flash.h` — 预处理定义（变量计数、物种数等）
- `Makefile` — 主 Makefile（TAU 仪器、OpenMP、库标志）
- 仿真映射文件（`Simulation_mapIntToStr.F90` 等）
- EOS 映射文件
- 构建戳生成器

---

## 安装

```bash
cd FLASH4.8
python tools/setup.py install
```

安装过程:
1. 生成 `metadata.json`
2. 通过 distutils 安装 `flash` 包（含 `flash.flmake`, `flash.dsl`, `flash.flashfile`）
3. 安装命令行脚本：`flmake`, `consdat`, `convertspect3d`, `flashtimes`, `symmetry`
4. 生成 bash 自动补全脚本
5. 清理 `metadata.json`

## 配置文件

**`flashrc.py`** — 运行控制文件，包含:
- `parameters` — 覆盖 `flash.par` 默认值
- `sweep` — 参数扫描定义
- `mail` — 邮件通知配置
- 自定义回调函数

**`flash_desc.json`** — 运行元数据文件，包含:
- 仿真名、版本、Git 哈希
- 调用命令、环境变量
- 运行目录、运行 ID
- 时间戳
