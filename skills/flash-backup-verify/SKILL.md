---
name: flash-backup-verify
description: FLASH 项目发布前的备份与独立使用验证工作流：scripts/04_backup/usb_backup.py 双模式（gitee/full）备份到任意目录，硬链接隔离副本验证备份包可独立 import 使用，gitignore 分发规则与发布清单。触发词：发布前备份、USB 备份、usb_backup、gitee 模式、full 模式、独立部署测试、备份验证、release。
---

> 最后核对：2026-11-06 · commit 72f6428

# FLASH 项目备份 + 独立使用验证

## 1. 适用场景

- 发布前备份 flash 包并测试其可独立使用
- 备份到 U 盘 / 任意目录（目标不存在会自动创建）
- 验证备份产物不依赖原始项目路径

## 2. 双模式备份（scripts/04_backup/usb_backup.py）

```bash
# gitee 模式（默认）: 仿 Gitee 仓库内容
python scripts/04_backup/usb_backup.py --mode gitee --dest <TARGET_DIR>
# full 模式: 几乎全量
python scripts/04_backup/usb_backup.py --mode full --dest <TARGET_DIR>
# 参数: [目标路径] 或 --dest PATH；--name PREFIX 自定义目录名；-n dry-run
```

- **gitee 模式**：文件列表 = `git ls-files --cached --others --exclude-standard`（等价 git add -A 推送内容）；不含 `.git`、不跑测试；文本按 `.gitattributes` 规范化为 LF
- **full 模式**：仅按脚本内 `EXCLUDE_DIRS` / `EXCLUDE_FILES` 排除（.git、__pycache__、build、*.pyc、*.log 等）
- 备份目录命名：`flash_backup_<mode>_<时间戳>`
- **先跑一次 `-n` dry-run 确认文件数**再正式备份

## 3. 隔离独立测试（关键步骤）

```bash
# 硬链接复制（同一卷秒级，不占双倍空间）
mkdir -p <BACKUP_PARENT>/_indep_test
cp -al <备份目录> <BACKUP_PARENT>/_indep_test/flash
```

```python
# 在隔离目录中验证（绝不把原始项目加入 sys.path）
import sys, os
sys.path.insert(0, r"<BACKUP_PARENT>/_indep_test")
os.chdir(r"<BACKUP_PARENT>/_indep_test")
import flash
print(flash.__file__)   # 必须指向 _indep_test 下的 flash
```

- **陷阱**：sys.path 含原始项目父目录时 `import flash` 会解析到原始项目，测试无效
- 验证清单：20 个核心模块 import、`EOSOpacityGenerator().list_available_materials()`、配置默认 URL
- 测试后清理用 Python `shutil.rmtree`（bash rm -rf 可能被沙箱拦截转回收站失败）
- 全局测试：`PYTHONPATH=<BACKUP_PARENT>/_indep_test python scripts/05_test/run_global_tests.py`（需 pytest）；失败基线先在原始项目跑一次对比，FLASH 真实运行类测试（需 WSL 二进制）属预存失败

## 4. 发布内容与表分发

- `Gen_eos_op_data/`（自研 `Z*.cn4` 表）**必须包含**在发布包
- `FLASH_eos_op_data/`（FLASH 版权表）按 License §3 不随包分发 → 依赖场景测试需 `pytest.skip`
- 场景 `sim_input` 的 `Config`（无扩展名）是发布包必需，dryrun 测试依赖

## 5. gitignore / git 经验教训

- `git -c core.quotepath=false` 必须放在子命令前
- `core.excludesFile` 优先级低于仓库 `.gitignore` → 测试例外规则必须直接改 `.gitignore`
- **顺序陷阱**：`*.pdf` 等排除规则若写在 `*` + `!*.*` 之前会被覆盖失效！大文件排除（*.pdf/*.pptx/*.avi/*.h5）必须放在 `!*.*` 之后
- **无扩展名文件**被 `*` 规则忽略，需显式 `!**/sim_input*/Config` 类例外
- 相对路径目录规则不匹配深层路径：`demo/xxx_*/` 不匹配 `scenarios/demo/...`，需 `**/` 前缀
- 已跟踪大文件 gitignore 无效 → `git rm --cached`（保留工作区文件）
- `git -c` 系列与 `!` 例外规则的组合改动后，用 `git ls-files` 实测核对发布清单

## 6. 凭据与用户名体系

- 凭据存储走 `MinimalCredentialManager`（physimx_core 缺失时回退），JSON 持久化于 `~/.physimx/flash/credentials.json`；排查"设置不生效"先确认 manager 是否落盘
- `get_user_name()`（本地 WSL 目录名）与 `get_ssh_username(name)`（超算账号）是**两套独立体系**，均从 credentials 动态获取；排查硬编码时保留 credentials 内的路由/账号配置，**发布包与脚本中不得出现明文账号**

## 7. FLASH 真实测试加速

- FLASH 源码唯一位置：`~/{user_name}/FLASH/FLASH4.8`（user_name 经 `get_user_name()` 动态提取）；检测函数 `_flash_detected()` 直接探测 setup 存在（勿用"返回 ≠ 默认路径"判断，会误判）
- 加速参数：`laser_times=[0, 0.3e-10]`、`tmax=0.13e-9`、`dtmax=1.05*tmax` → thin_layer 157s → 25s
- 编译缓存：`CACHE_BIN=~/<user_name>/FLASH/FLASH4.8/<user>/flash4_<sim>.bin`；`force_recompile=True` 会每次重编译（慢）
- ch_center 真实测试默认快速模式（仅 .par 验证），`--real` 触发真实仿真

## 关联资源

- `scripts/04_backup/usb_backup.py`（argparse：`--mode {gitee,full}` / `--dest` / `--name` / `-n`）
- skill `flash-eos-op`（表分发 gitignore 策略）、`flash-hpc-fetch`（凭据体系）
