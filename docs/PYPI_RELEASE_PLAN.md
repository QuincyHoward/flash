# flash-sim PyPI 发布调整计划

> 状态: 草案 (待用户确认关键决策后执行)
> 日期: 2026-08-06
> 目标: 将 `flash-sim` 包正式发布到 PyPI (pypi.org), 保留现有 Gitee 推送 + GitHub 同步工作流

---

## 1. 目标

1. `pip install flash-sim` 可用: wheel 安装后 `import flash` 正常工作
2. 发布内容合规: 不含 FLASH 版权材料、不含用户名/本机路径等隐私泄漏
3. 元数据规范: 版本号统一、SPDX license、项目 URL 齐备
4. 发布后 Gitee/GitHub 同步流程不受影响 (git tag + push 到 Gitee, Gitee 平台侧镜像到 GitHub)

---

## 2. 现状调研结论

### 2.1 构建系统现状 (已验证)

| 项目 | 现状 | 问题 |
|------|------|------|
| 包布局 | **项目根目录即 flash 包** (根目录含 `__init__.py`) | 非标准布局 |
| `pyproject.toml` wheel | `packages = ["flash"]` (指向不存在的子目录) | **wheel 构建产物为空** (仅 6 个 dist-info 文件, 0 个 .py) |
| 实测 wheel 1 | 默认配置构建 | ❌ `flash_sim-1.0.0-py3-none-any.whl` 无任何代码 |
| 实测 wheel 2 | 改用 `packages = ["."]` | ❌ 文件落在 `.` 前缀下, `import flash` 失败 |
| 实测 wheel 3 | 改用 `force-include = {"." = "flash"}` | ❌ **绕过 exclude 过滤**, 混入 .git/.idea/test/docs/scripts 及 1.7GB 二进制 (FLASH4.8.tar.gz 等) |
| sdist | include/exclude 部分生效 | ⚠️ 仍含 docs/、test/ 等杂项; 顶层结构被打散 |

**结论: 当前 wheel 产物不可用, 发布前必须修复构建配置或目录布局。**

> 补充: 开发环境一直可用是因为用 `pip install -e .` (editable 模式, .pth 指向项目根), 掩盖了 wheel 构建缺陷。

### 2.2 版本状态不一致

| 位置 | 当前值 |
|------|--------|
| `pyproject.toml` | `1.0.0` |
| `flash/__init__.py` (`__version__`) | `1.0.0` |
| README badge | `0.0.000` |
| git tag | `0.0.000` |

需按 `docs/VERSIONING.md` 协议统一。

### 2.3 隐私与合规风险 (发布前必须清理)

1. **用户名硬编码**: `input_gen/gen_config/generator.py` 等默认 `sim_path="QC/LaserSlab1d_new"` (QC = 本机用户名)
2. **本机路径泄漏**: `projects/projects_demo/.../run_flash.sh` 硬编码 `~/QC/FLASH/...` 与 `/mnt/d/PhySimX/...`
3. **FLASH 版权材料**: sdist exclude 已配置, 但需在最终产物中**逐一验证** (flash_src/*.gz、EOS 表、ref_f90s、手册等)
4. **凭据**: `~/.physimx/flash/credentials.json` 在项目外, 不随包发布 ✓; git remote URL 中 token 仅存于本地 `.git/config` ✓

### 2.4 远程仓库与同步现状

- 本地仅一个 remote: `origin` → Gitee (`gitee.com/physimx/flash`), URL 内嵌 token
- "同步 GitHub" = Gitee 平台侧的**仓库镜像功能** (非本地 remote), 发布流程无需改动
- 无 `.github/workflows` (无 CI), PyPI 发布采用**手动 twine 上传**即可

### 2.5 其他元数据问题

- `license` 字段使用 `{text = "..."}` 旧格式; PyPI 新版要求 **SPDX 表达式** (PEP 639)
- 无 `[project.urls]` (Homepage/Repository/Issues)
- README 无 PyPI 安装章节 (目前仅 Gitee 克隆方式)

---

## 3. 方案选择

### 方案 A: 目录重组为标准包布局 (推荐)

将根目录下的模块整体移入 `flash/` 子目录, 恢复 `packages = ["flash"]`:

```
flash/            ← 原项目根目录内容 (git mv)
  __init__.py
  _core/  config/  flash_run/  flash_src/  input_gen/  interface.py
  output_processors/  physics/  projects/  scenarios/  utils/
pyproject.toml    ← 留在项目根
scripts/ test/ docs/ README.md LICENSE NOTICE Makefile  ← 留在项目根
```

**优点**: 标准布局一劳永逸; `pip install .`、wheel、editable 全部正常; 社区与 PyPI 惯例
**成本**: 需同步修复 49 处 bootstrap (向上搜索 `__init__.py + pyproject.toml` 的逻辑改为仅搜索 `pyproject.toml`) 与 test/ 中约 10+ 处 `sys.path.insert` 指向 (由"父目录"改为"项目根"); 全量回归测试
**风险**: 中 — 均为机械修改, 但改动面广, 需完整跑一遍全局测试

### 方案 B: staging 镜像构建 (零源码改动, 备选)

新增 `scripts/build_release.py`: 发布时把根目录内容复制到临时 `flash/` 镜像 + 专用 pyproject 构建, 源码布局不动。

**优点**: 源码零风险
**缺点**: `pip install .` (从 git 直接装) 依然坏; 每次发布依赖脚本; 治标不治本

> **推荐方案 A**。本项目以发布 PyPI 为里程碑, 标准布局是长期价值; 方案 B 仅作为时间紧迫时的退路。

---

## 4. 执行阶段 (方案 A)

### 阶段 0: 前置决策 (需用户确认)

- [ ] 包名: `flash-sim` (PyPI 已验证可用, 404) — 沿用现状
- [ ] 版本号: 建议 `1.0.0` (与 pyproject 现状一致, git tag `v1.0.0`)
- [ ] PyPI API token: 用户在 https://pypi.org/manage/account/token/ 创建, 配置到 `~/.pypirc` 或环境变量
- [ ] 是否先发 TestPyPI 验证 (建议)

### 阶段 1: 源码结构重组

1. `git mv` 13 个顶级条目 → `flash/` 子目录
2. 批量修正 49 处 bootstrap: 判定条件由「`__init__.py` + `pyproject.toml` 同时存在」改为「`pyproject.toml` 存在」(scripts/ 位于项目根, 向上搜索第一层即命中)
3. 修正 test/ 中 `sys.path.insert` 目标: `_PARENT` 由「项目根的父目录」改为「项目根」
4. 更新 `pyproject.toml`:
   - wheel 恢复 `packages = ["flash"]`
   - sdist exclude 全部模式加 `flash/` 前缀 (或改 `**/flash_src/**` 风格)
5. 更新 `.gitignore` 相关路径模式
6. **回归**: 全局测试 (`scripts/run_global_tests.py`), 基线 132 passed

### 阶段 2: 元数据与隐私清理

1. `pyproject.toml`:
   - `license = "Apache-2.0"` (SPDX, PEP 639) + 保留 FLASH 声明到 NOTICE
   - 新增 `[project.urls]`: Homepage (Gitee/GitHub)、Issues
   - classifiers 精简为 PyPI 合法值
2. 统一版本: pyproject / `__init__.py` / README badge / git tag 全部 `1.0.0` / `v1.0.0`
3. 隐私清理:
   - `input_gen/gen_config/generator.py` 等: 默认 `sim_path` 参数化, 去掉 `QC/` 前缀
   - `projects/projects_demo/.../run_flash.sh` 等 demo 产物: 改用 `FLASH_USER_HOME` 变量或排除发布
4. README: 增加 PyPI 安装章节 (`pip install flash-sim`), 保留 Gitee 仓库说明

### 阶段 3: 构建与安装验证

1. `python -m build` (sdist + wheel)
2. 产物审计脚本: 检查 wheel 无 `.git/ test/ docs/ *.h5 *.gz *.cn4` 等; 无 `QC/ quincy` 等字符串
3. 干净 venv 安装 wheel → `import flash` + 冒烟测试 (FlashSimulator(mock=True) + dry-run 引擎)
4. 干净 venv 安装 sdist → 同上
5. editable 安装回归 → 同上

### 阶段 4: 发布

1. 代码与文档提交, 推送 Gitee (触发 GitHub 同步)
2. `scripts/tag-release.sh v1.0.0` (跑格式/lint/全局测试/构建) → `git push origin v1.0.0`
3. TestPyPI 试传: `twine upload --repository testpypi dist/*` → 试装验证
4. 正式发布: `twine upload dist/*` (需要 PyPI token)
5. 验证: `pip install flash-sim` (公开索引)

---

## 5. 风险与回滚

| 风险 | 等级 | 缓解 |
|------|------|------|
| 目录重组破坏现有脚本/测试 | 中 | 阶段 1 逐项回归; git 可完整回退 (`git revert` 或 reset) |
| PyPI 发布后发现问题 | 低 | 发布前 TestPyPI + 双 venv 验证; PyPI 支持 yank 版本 |
| 隐私泄漏 (QC 等) 进包 | 中 | 阶段 2 清理 + 阶段 3 产物字符串审计 |
| 依赖 `physimx-core` 未发布导致 `[full]` 装不上 | 低 | `[full]` 为 optional; 基础依赖 (numpy/cryptography/pydantic) 均在 PyPI |

**回滚**: 目录重组全程使用 `git mv`, 若测试失败可在任意阶段 `git checkout .` 恢复; 已发布的 PyPI 版本可 yank。

---

## 6. 待用户确认

1. **方案**: A (目录重组, 推荐) 还是 B (staging 构建)?
2. **版本号**: 1.0.0 (推荐) / 0.1.0 / 其他?
3. **PyPI token**: 是否已创建? 将配置到 `~/.pypirc`
4. **TestPyPI 试发**: 是否需要 (建议先试发)
5. **包内 demo/项目文件**: `projects/`、`scenarios/flash_demo/` 是否随包发布 (涉及 QC 硬编码清理范围)
