# PlasmaPy 内嵌开发要求与合规声明

> 适用范围：flash 包内嵌的 PlasmaPy vendor 快照（`flash/output_pro/PlasmaPy/src/PlasmaPy/`）
> 与桥接层 `flash/output_pro/plasmapy_bridge.py`。
> 建立日期：2026-10-30（flash-sim 0.1.15）。

---

## 1. 版权与许可边界（BSD-3 合规）

| 组件 | 许可 | 版权归属 | 再分发要求 |
|------|------|---------|-----------|
| vendored PlasmaPy v2026.2.0 | **BSD 3-Clause** | © 2015–2026 PlasmaPy Developers | 保留版权声明、许可文本与免责声明（已随 vendor 目录携带 `LICENSE.md`，并在根 [NOTICE](../NOTICE) 声明） |
| `plasmapy_bridge.py` 集成层 | Apache 2.0 | PhySimX Contributors | 随 flash-sim 正常分发 |
| flash-sim 其余代码 | Apache 2.0 | PhySimX Contributors | 随 flash-sim 正常分发 |
| FLASH 引擎 | FLASH License Agreement | Flash Center | **不再分发**（与 PlasmaPy 无关，见 NOTICE） |

### 硬性规则（BSD-3 合规前提）

1. **vendor 源码保持未修改**。任何对 PlasmaPy 行为的定制一律经
   `plasmapy_bridge.py` 包装实现；确需改上游源码时，必须：
   - 在 vendor 目录内的修改处以注释标明修改者与日期；
   - 在根 `NOTICE` 的 PlasmaPy 节删除 "unmodified" 表述并逐条列出修改；
   - 在 `PhySimX_flash_CHANGELOG.md` 记录。
2. **许可文件随分发**：wheel/sdist 已包含 vendor 目录（含 `LICENSE.md`、
   `CITATION.cff`），构建护栏（pyproject exclude、`wheel_leak_audit.py`）禁止把
   vendor 排除出包——否则构成 BSD-3 再分发违约。
3. **声明链**：`README.md`（中/英许可节）→ `NOTICE` → vendor `LICENSE.md`
   三级声明必须同步维护；出版物依赖 PlasmaPy 功能时引用
   `CITATION.cff`（Bibtex 条目见该文件）。
4. **不受 FLASH License 约束**：PlasmaPy 是 PlasmaPy Developers 的独立项目
   （https://www.plasmapy.org），与 Flash Center 无关联、无背书关系。

## 2. 开发环境要求（对齐 PlasmaPy 上游开发要求）

PlasmaPy 上游（v2026.2.0）的开发要求与 flash 侧对齐措施：

| 上游要求 | 上游配置 | flash 侧对齐 |
|---------|---------|-------------|
| Python ≥ 3.12 | `requires-python = ">=3.12"` | editable 安装器 `install_editable.py` 版本闸门（py≥3.12）；flash 本体保持 ≥3.10 |
| pytest ≥ 9.0.2 | PEP 735 `dependency-groups.test` | 根 extras `plasmapy-dev`（`pytest>=9.0`） |
| 并行测试 | `pytest-xdist>=3.8` | 同入 `plasmapy-dev` |
| 拼写检查 | `[tool.codespell]` + `_typos.toml` | 根 `[tool.codespell]`（skip vendor——上游 `_typos.toml` 自治） |
| Lint | `[tool.ruff]`（上游独立配置） | flash 的 black/ruff **exclude vendor**（不交叉检查，避免风格冲突） |
| 任务编排 | nox + uv（`noxfile.py`） | 不引入 nox——用根 `Makefile` 的 `plasmapy-*` 目标承担同等动作 |
| 锁文件 | `uv.lock` + `nox -s lock` | 不适用（flash 不重建 PlasmaPy 依赖锁；运行依赖由 plasmapy 元数据声明） |
| editable 安装 | `pip install -e .`（setuptools-scm） | `install_editable.py`（vendor 无 `.git`，经 `SETUPTOOLS_SCM_PRETEND_VERSION_FOR_PLASMAPY=2026.2.0` 注入版本） |

安装：

```bash
# 开发工具链（pytest 9 栈 + codespell）
pip install -e ".[plasmapy-dev]"
# PlasmaPy 本体 editable（source of truth = vendor 目录; 需 py≥3.12）
python flash/output_pro/PlasmaPy/install_editable.py
```

> ⚠ **禁止 `pip install plasmapy`（PyPI 路线）**：会与 vendor editable 双安装冲突
> （`plasmapy.__file__` 不再指向 vendor，冒烟检查会拦截并提示先卸载）。
> plasmapy 本体刻意**不入**任何 extras——见 `pyproject.toml` 注释与 `DEPENDENCIES.md`。

## 3. 平台支持（flash 三平台 × PlasmaPy）

| 平台 | Python | 方式 | 状态 |
|------|--------|------|------|
| Windows (managed / .venv-win) | 3.14 / 3.13 | editable (`install_editable.py`) | ✅ |
| WSL | ≥3.12 venv | editable | ✅（条件：venv 基座 ≥3.12） |
| HPC NC-E | miniforge 3.12.8 | 离线 wheel bundle `--target` / 已并入 `.venv-hpc-nce` | ✅（见 `DEPENDENCIES.md` 与 `hpc_plasmapy_merge.py`） |

HPC 注意：`mpmath` 必须 pin **1.3.0**（1.4.1 的 `import gmp` 回退会被 `~/gmp/`
目录命名空间包误捕，详见 DEPENDENCIES.md）。

## 4. 开发工作流（Makefile 目标）

```bash
make plasmapy-install   # editable 安装 + 冒烟（__file__ 归属 + thermal_speed 数值）
make plasmapy-test      # 桥接层 12 项物理交叉验证 + PlasmaPy 冒烟
make plasmapy-check     # codespell + 桥接层 black/ruff + 快速 pytest
```

### 新增桥接物理量的四步流程（摘要）

1. 在 `plasmapy_bridge.py` 增加函数（要求：输入取 `container` + `to_quantity`、
   带单位返回 / 纯数组返回须注明、`require_plasmapy()` 门控、docstring 标注
   PlasmaPy 2026.2.0 实测约定与陷阱）；
2. `test/test_plasmapy_bridge.py` 增加 FakeContainer 用例（值按 DATA_CONFIG 的
   CGS 制存储——勿存 SI 值配 CGS 单位）+ 解析解/理论值交叉验证；
3. `make plasmapy-test` + 全套件回归（`pytest flash/output_pro/test`）；
4. 同步 `output_pro/docs/PlasmaPy在output_pro中的使用指南.md` API 表
   （详细流程与示例见该指南）。

## 5. 上游升级 SOP

```bash
# ① 下载新 release（保留其 .git 亦可，vendor 后删除）
# ② 替换 vendor 目录（flash/output_pro/PlasmaPy/src/PlasmaPy）
# ③ 核对/更新版本注入: install_editable.py 的 PRETEND_VERSION
# ④ 重装 + 全量验证:
make plasmapy-install && make plasmapy-test
pytest flash/output_pro/test -q          # 57+ 项全过
# ⑤ 同步声明链: NOTICE 版本号 / README 中英 / CHANGELOG / DEPENDENCIES.md
# ⑥ git commit（vendor 目录整体替换）
```

## 6. 检查清单（PR 含 PlasmaPy 相关改动时）

- [ ] 未修改 vendor 源码（或已按 §1.1 声明修改）
- [ ] `make plasmapy-test` 全过
- [ ] `make plasmapy-check` 全过
- [ ] NOTICE / CHANGELOG / DEPENDENCIES.md 声明同步
- [ ] 新物理量已录入使用指南 API 表
- [ ] HPC 路线可用性评估（wheel bundle 是否需更新）
