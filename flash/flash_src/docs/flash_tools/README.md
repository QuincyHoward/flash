# FLASH 4.8 工具文档索引

## 概述

本文档目录包含 `FLASH4.8/tools/` 目录下所有脚本和工具的功能说明。根据功能分类，共 11 篇独立的 Markdown 文档。

## 文档列表

| # | 文档 | 内容 |
|---|------|------|
| 01 | [flmake 构建系统](01_flmake_build_system.md) | FLASH 核心构建与运行管理系统（setup/build/run/restart/clean 等 20+ 命令） |
| 02 | [Python 数据分析库](02_python_analysis_library.md) | Python 后处理库：物理分析、HDF5 读取、DSL 解析、yt 集成 |
| 03 | [输出文件比较工具](03_output_comparison_tools.md) | sfocu/pfocu/cmpExpIO/GridDumpCompare：串行和并行 checkpoint 比较 |
| 04 | [粒子与轨迹工具](04_particle_and_trajectory_tools.md) | 粒子排序、轨迹聚合、可视化、切片 |
| 05 | [脚本工具](05_script_tools.md) | 代码质量检查、运行管理、性能分析、后处理、文档生成等 20+ 脚本 |
| 06 | [VisIt 可视化脚本](06_visit_visualization_scripts.md) | 电影生成、相机快照、AMR 网格可视化的 VisIt CLI 脚本 |
| 07 | [IDL 可视化库](07_idl_visualization_libraries.md) | FIDL v3.0 (79 文件) 和 IDL-AMR (97 文件) 两个 IDL 可视化库 |
| 08 | [紧致应用构建系统](08_compact_app_build_system.md) | 迷你应用生成、单元引用清理、批量构建 |
| 09 | [文件转换与缝合](09_file_conversion_and_stitching.md) | FLASH2→FLASH3 映射、flashStitch 缝合、Spect3D 转换 |
| 10 | [质子射线照相工具](10_proton_radiography_tools.md) | PRaLine/PRadReader 质子射线照相重建与分析 |
| 11 | [其他工具](11_other_tools.md) | Stencillator、CMake、漂移分析、Tau、testSuite、pyFlash、setup.py |

## 工具目录文件树

```
tools/
├── setup.py                     # → 文档 01 (flmake 安装)/文档 11 (安装脚本)
├── GridDumpCompare.py/.F90      # → 文档 03 (网格转储比较)
│
├── cmake/                       # → 文档 11 (CMake 模块)
├── cmpExpIO/                    # → 文档 03 (并行比较)
├── cmp_chombo/                  # → 文档 11 (Chombo 比较)
├── converterTools/              # → 文档 09 (格式转换)
├── diagnosticsTools/            # → 文档 11 (诊断)
├── driftDee/                    # → 文档 11 (漂移分析)
├── fidlr3.0/                    # → 文档 07 (IDL 可视化)
├── idlamrlib/                   # → 文档 07 (IDL AMR 可视化)
├── fileTools/flashStitch/      # → 文档 09 (文件缝合)
├── particleTools/               # → 文档 04 (粒子工具)
├── pfocu/                       # → 文档 03 (并行比较)
├── protonRad/                   # → 文档 10 (质子射线照相)
├── python/                      # → 文档 02 (Python 库)
├── scripts/                     # → 文档 05 (脚本工具)
│   ├── visitScripts/            # → 文档 06 (VisIt 脚本)
│   ├── setup_compact_app/       # → 文档 08 (紧致应用)
│   ├── pyFlash/                 # → 文档 11 (Python 绑定文档)
│   ├── HPCToolkit/              # → 文档 05 (性能分析)
│   ├── plot_integrated_quantities/ # → 文档 05 (集成量绘图)
│   └── thread_speedup/          # → 文档 05 (线程加速)
├── sfocu/                       # → 文档 03 (串行比较)
├── Stencillator/                # → 文档 11 (模板生成)
├── tau/                         # → 文档 11 (Tau 性能)
├── testSuite/                   # → 文档 11 (测试套件)
└── trajectoryFile/              # → 文档 04 (轨迹工具)
```

## 工具依赖关系图

```
flmake 构建系统 (01)
  ├──→ Python 数据分析库 (02)     [运行时参数解析/文件读取]
  ├──→ 输出比较工具 (03)          [回归测试]
  ├──→ 脚本工具 (05)              [代码质量/性能分析]
  └──→ 紧致应用构建 (08)          [应用简化]

数据分析 (02)
  ├──→ yt 可视化
  ├──→ IDL 可视化 (07)           [数据后处理]
  ├──→ 文件转换 (09)              [格式互转]
  ├──→ VisIt 可视化 (06)          [大规模可视化]
  └──→ 质子射线照相 (10)          [专业分析]

粒子工具 (04)
  └──→ 轨迹工具 (04)             [时间序列聚合]
```

## 快速导航

| 我要做什么？ | 看哪篇文档 |
|-------------|-----------|
| 编译 FLASH 仿真 | `01_flmake_build_system.md` → `flmake setup` + `flmake build` |
| 运行 FLASH 仿真 | `01_flmake_build_system.md` → `flmake run` |
| 读取 HDF5 输出数据 | `02_python_analysis_library.md` → flashfile |
| 比较两个 checkpoint | `03_output_comparison_tools.md` → sfocu |
| 可视化仿真结果 | `06_visit_visualization_scripts.md` 或 `07_idl_visualization_libraries.md` |
| 分析粒子轨迹 | `04_particle_and_trajectory_tools.md` |
| 检查代码质量 | `05_script_tools.md` → codeCheck.py |
| 性能分析 | `05_script_tools.md` → steptime.py / HPCToolkit |
| 生成迷你应用 | `08_compact_app_build_system.md` |
| 格式转换 (→Spect3D) | `09_file_conversion_and_stitching.md` → convertspect3d |
| 质子射线照相分析 | `10_proton_radiography_tools.md` |
| 安装 Python 工具链 | `11_other_tools.md` → setup.py |
