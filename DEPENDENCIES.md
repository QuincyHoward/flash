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
