# scripts/01_env_diagnose — 环境诊断与修复

> 最后核对：2026-11-15 · commit 97d5e5d

**职责**：检查本机 Python/依赖/FLASH 安装环境、绘图规范与 MPI 资源配置，并提供对应的一次性修复工具。全部为只读诊断或显式修复，不参与仿真运行。

## 文件清单

| 文件 | 职责 |
|---|---|
| `check_env.py` | 环境自检：Python 版本、关键依赖、`--check-only` 仅检测、`--install PKG` 补装、`--test` 自检后跑全局测试 |
| `diag_flash_env.py` | 诊断 WSL 中 FLASH 安装位置、用户名与路径探测逻辑 |
| `check_plot_style.py` | 绘图合规扫描：字体 ≥18pt、全英文、`dpi>=200`、必须调用 `apply_plot_style()`；支持 `--strict` |
| `fix_plot_style.py` | 批量修复绘图脚本（注入样式引导、去除小字号、提升 DPI） |
| `fix_bootstrap.py` | 修复导入引导：把 `sys.path` 中的 `_ROOT` 改为 `_ROOT.parent` |
| `gen_resource_config.py` | 按装置核数生成资源控制文件；`--total-cpus` / `--device` / `--show` / `--dry-run` |
| `test_dual_mode.py` | 验证 standalone 与 PhySimX 双重导入模式 |

## 常用命令

```bash
python scripts/01_env_diagnose/check_env.py --check-only
python scripts/01_env_diagnose/check_plot_style.py
python scripts/01_env_diagnose/gen_resource_config.py --total-cpus 64 --device hpc --dry-run
python scripts/01_env_diagnose/test_dual_mode.py
```

## 约定

- 诊断类脚本不写仓库内产物；资源控制文件写用户目录，不入库。
- 绘图规范以英文科研插图为准，字体 ≥18pt、Times New Roman。

**上级导航**：[../README.md](../README.md)
