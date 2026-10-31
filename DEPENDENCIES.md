# DEPENDENCIES.md — flash-sim 三平台依赖差异表（根目录唯一人读事实源）
#
# 机器可读源: deploy/env_spec.py（本表由其 diff_rows() 结构生成，两处必须一致）
# 锁定文件:   deps_lock/requirements-{win,wsl,hpc}.txt（由 deps_lock/generate_locks.py 生成）
# 生成/校验:  python deps_lock/generate_locks.py --check
#
# 基线策略: 三平台取交集版本（尽量同版本）；平台差异仅限下表所列，且必须给出原因。
# 维护规则: 改基线/差异 → 只改 deploy/env_spec.py → 重新生成 lock → 同步本表 → 三平台重验。

| 包名 | 基线版本 | Windows | WSL | HPC (NC-E) | 差异原因 |
|------|---------|---------|-----|------------|---------|
| cryptography | 41.0.7 | 41.0.7 | 41.0.7 | 41.0.7 | （无差异）凭据 Fernet 加密 |
| h5py | 3.11.0 | 3.11.0 | 3.11.0 | **3.14.0** | glibc2.17 交叉构建可用版本（2026-10-22 超算实测部署通过） |
| matplotlib | 3.8.4 | 3.8.4 | 3.8.4 | 3.8.4 | （无差异）绘图 |
| numpy | 1.26.4 | 1.26.4 | 1.26.4 | 1.26.4 | （无差异）数值核心 |
| pandas | 2.2.3 | 2.2.3 | 2.2.3 | **2.3.2** | glibc2.17 交叉构建可用版本（同上） |
| paramiko | 3.4.0 | 3.4.0 | 3.4.0 | 3.4.0 | （无差异）SSH/SFTP（超算部署与 hpc CLI） |
| pillow | 10.3.0 | 10.3.0 | 10.3.0 | **12.2.0** | glibc2.17 交叉构建可用版本（同上） |
| pytest | 8.2.0 | 8.2.0 | 8.2.0 | 8.2.0 | （无差异）测试 |
| pytest-cov | 5.0.0 | 5.0.0 | 5.0.0 | 5.0.0 | （无差异）覆盖率 |
| scipy | 1.11.4 | 1.11.4 | 1.11.4 | 1.11.4 | （无差异）插值/拟合（测试） |
| yt | 4.4.0 | 4.4.0 | 4.4.0 | 4.4.0 | ★ 基线即 4.4.0：4.3.1 在 NC-E 全节点 SIGSEGV（2026-10 实测） |

## 平台环境差异（非 pip 包层）

| 平台 | Python | FLASH 引擎 | venv 约定 | 备注 |
|------|--------|-----------|-----------|------|
| Windows | 3.13 (managed) | 无原生（仅驱动/分析） | `.venv` | 造包机；paramiko 远程驱动 |
| WSL | 3.10+ (Ubuntu) | FLASH 4.8 本地编译 | venv 路径经 **`FLASH_VENV_DIR`** 注入（用错静默回落默认 `.venv`） | FLASH 4.8 只读默认名 `flash.par` |
| HPC NC-E | module python/3.10.8 | FLASHSNB 树编译 | 命名环境 **`.venv-hpc-nce`**，离线 `--no-index` | glibc 2.17；wheelhouse 须交叉构建（deploy/build_wheelhouse_linux.py） |

## 安装命令（离线）

```bash
# 三平台统一（wheelhouse 就位后）
pip install --no-index --find-links=<wheelhouse> -r deps_lock/requirements-<platform>.txt
# 或直接走总入口
python start_flash.py --offline [--wheelhouse D] [--profile full|runtime|lite]
```

## 带外可选依赖（不入 BASELINE/lock/wheelhouse）

| 包名 | 版本 | 平台状态 | 安装方式 |
|------|------|---------|---------|
| plasmapy（可选） | 2026.2.0 | win ✅ / wsl 条件 ✅（venv 需 py≥3.12）/ hpc ✅（已并入正式 venv） | win/wsl: `python flash/output_pro/PlasmaPy/install_editable.py`; hpc: `flash/output_pro/test/hpc_plasmapy_merge.py` |

| plasmapy-dev（可选, 开发） | — | win/wsl/hpc(本地开发) | `pip install -e ".[plasmapy-dev]"` |

- **开发要求与版权合规专篇**: `docs/PLASMAPY_DEVELOPMENT.md`（BSD-3 声明链 / 上游 dev 依赖对齐表 / 升级 SOP / 平台矩阵）。
- plasmapy 本体刻意不入 extras（防 PyPI 双安装与 vendor editable 冲突）; 安装统一走 `flash/output_pro/PlasmaPy/install_editable.py`。

- 源码托管（2026-10-30 起 vendor 快照）: PlasmaPy 2026.2.0 源码（tag v2026.2.0）作为普通目录
  vendored 于 `flash/output_pro/PlasmaPy/src/PlasmaPy`，**随 flash 仓库分发**（Gitee 推送与
  HPC bundle 同步均携带；~495 文件 / ~13MB，内层 .git 已移除并归档于
  `artifacts/PlasmaPy-clone-git-backup-20261030.tar.gz`）。版本号由
  `SETUPTOOLS_SCM_PRETEND_VERSION_FOR_PLASMAPY=2026.2.0` 提供（install_editable.py 自动注入）。
  冲突治理: .gitignore 末尾"PlasmaPy vendor 冲突精确排除"章节（运行时原子数据 json/h5 反选、
  env 系泄漏恢复等）；black/ruff/wheel/sdist 均排除 vendor 目录。升级流程: 下载新 release →
  替换 vendor 目录 → commit → 重跑 install_editable.py → 跑 test_plasmapy_bridge.py。
  pyproject extras 无法跨平台引用仓库内路径，故不入 lock/wheelhouse。
- **HPC（2026-10-30 已并入正式环境）**: `.venv-hpc-nce` 基座已从 module python/3.10.8 整体切换到
  miniforge/24.11（py3.12.8, `--system-site-packages` 继承 base 科学栈），plasmapy 2026.2.0 + yt 4.4.0
  + pytest 9.1.1 经离线 wheel bundle（32 whl, `--no-index --no-deps`）装入；output_pro 源码已部署至
  `flash_sim/flash/output_pro`，全套件 52 passed。旧 py3.10 venv 保留为 `.venv-hpc-nce-py310.bak` 可回滚；
  离线 wheel 留存 `flash_sim/plasmapy_bundle/`（重装源）。编排: `flash/output_pro/test/hpc_plasmapy_merge.py`。
- ⚠ HPC mpmath 必须 pin **1.3.0**: mpmath 1.4.1 新增 `import gmp` 回退，会被 $HOME 下的
  `~/gmp/` 源码编译目录（命名空间包）误捕 → `AttributeError: module 'gmp' has no attribute 'mpz'`。
  1.3.0 后端无此回退，在任意 cwd 下均安全。
- 缺失行为: `flash/output_pro/plasmapy_bridge.py` 的 `HAS_PLASMAPY=False`，物理量函数抛
  RuntimeError（带安装指引），其余功能/测试不受影响。
- 详见 `flash/output_pro/docs/PlasmaPy在output_pro中的使用指南.md` §1/§6。
- 维护规则: 升级 PlasmaPy 需同步更新克隆 tag + 重跑桥接测试（test/test_plasmapy_bridge.py）。
