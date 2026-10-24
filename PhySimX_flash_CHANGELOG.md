# PhySimX flash 版本更新日志

> 本文件记录 `flash-sim`（FLASH 4.8 Python 接口）的版本变更。
> 格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
> 版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。
>
> **发版一致性命律**：`pyproject.toml [project].version` = git tag = PyPI 版本 =
> `flash.__version__`，四者必须同号（详见 README「版本维护策略」）。
> 历史条目由 `git tag` 与提交记录回溯，未收录的零散提交归入「维护」。

---

## [Unreleased]

### 新增

- **`flash/flash_run/env/venv_paths.py`**：虚拟环境路径的**唯一事实源**。纯 stdlib、
  零 flash 依赖，供部署侧在 `pip install` 之前按文件路径加载。API：
  `repo_root()` / `venv_dir(root, kind)` / `venv_python(root, kind)` / `candidates()`。
  `kind="local"|"hpc"` 两维度正交（不用平台名，避免 WSL 上无法区分本机/超算 venv）。
- `--check-env` 新增 `--strict`：存在待修项时返回非零，可作为部署门禁；
  并新增「已注册场景数」报告项。
- `HpcSpec` 新增产物回收字段：`basenm` / `with_plt` / `frames` / `log_names`。
- `flash.scenarios.registered_packages()`：报告已加载的场景包（供自检与排障）。
- 文档：`docs/功能模块解耦与流程梳理计划.md`、本更新日志。

### 变更

- **`resolve_venv_python()` 改由 `repo_root()` 驱动**：旧实现用 `package_root()`
  （= 包目录 `.../flash/flash`）拼 `.venv-*`，路径恒不存在，本机实测永远返回 `None`。
- `package_root()` **保持原值并标注 `misnamed, load-bearing`**：`runs_root()` 依赖
  `package_root().parent` 才得到正确的 `flash_sim_runs`，修改它会让既有 run 目录搬家。
- `HpcRunner.download()` 改为**统一走 `fetch_policy`**（chk-only 唯一策略源）：
  此前只下载 `dens_timespace.png`/`summary.json`/`flash_run.log` 三个固定文件，
  **完全不回收 chk/plt**，HDF5 全部滞留超算。
- `insitu_runner.resolve_hpc_python()`：改用 `venv_paths(kind="hpc")`；回落
  `sys.executable` 时必须 WARN 且校验解释器 ≥3.10，低于则明确拒绝。
- SNB 场景 `--mode` 改为走全仓统一别名归一（`normalize_run_mode`），并显式拒绝
  `local`（`nprocs=131` 本地会严重超订）。

### 修复

- **引擎"静默造假"（最严重）**：`FlashSimulatorEngine` 在 FLASH 编译/运行失败时
  会回退 dry-run 合成数据并最终返回 `success=True`，等于把「FLASH 根本没跑」
  报成成功；在 Linux/HPC（无 `wsl` 命令）上必然触发。现改为：真实运行失败一律
  返回 `success=False`，合成数据只允许显式 `dry_run=True`。
- **两个 `demo_hpc` 入口恒返回 `False`**：模式名归一（`hpc → hpc-remote`）后，
  旧判断 `run_mode != "hpc"` 恒为真，入口直接退出。
- **insitu 收集 0 个文件仍判成功**：objdir 缺失时仅 WARN，`state.json` 仍写 `ok=True`。
- **sdist 含整个 Linux 虚拟环境**：实测 `flash_sim-0.1.11.tar.gz` 为 11103 条 /
  37.5 MB，其中 `.venv-linux` 占 **10074 条（90.7%）**，另有 `temp_delete/` 28 条。
  修复后 **1006 条 / 4.6 MB**，`.venv*` 与 `temp_delete` 均为 0。
  （根因：`include` 的 `**/*.py` 把 site-packages 全卷进来，而 `.gitignore`
  对打包器无效；且 hatchling 的 **exclude 优先于 include**。）
- **sdist 缺失 `deploy/` 导致离线安装必失败**：`start_flash.py` 依赖
  `deploy/_wh_common.py`，而 `/deploy/**` 被整目录排除 ⇒ 解包后离线预检直接 FATAL。
  现改为精确排除（仅排除 `hpc_deploy/`、造包与构建期护栏脚本）。
- **`rt_mgdFlMode` 自相矛盾**：`SNBOneCH_m/_ml` 的配置默认为 `fl_harmonic`，而值级
  守卫要求 `fl_larsen` ⇒ 每次运行都判"陈旧"并重复重生成。已按实测结论（`fl_harmonic`
  是 HYPRE `ierr=256` 非收敛与负内能的来源）统一为 `fl_larsen`。
- **场景包加载失败被静默吞掉**：`flash/scenarios/__init__.py` 对所有 `ImportError`
  一律 `warnings.warn` ⇒ wheel 安装态下 `import flash.scenarios` 成功但场景未注册，
  随后 `get_scenario()` 报"未知场景"，完全看不出是打包缺文件。现区分：本包自身缺
  文件 → `raise`；第三方可选依赖缺失 → `warn`。

### 移除

- `deploy/hpc_deploy/wait_install.py`：一次性会话脚本，不在 `STEPS` 链路内、
  全仓无引用，且写死本机路径 `E:\PhySimX\...` 与安装时间戳/PID。

### 文档

- `docs/功能模块解耦与流程梳理计划.md`：三模块耦合实证、目标分层、四目标模型、
  `auto` 判定表、批次计划、护栏纪律与风险清单。
- README 中英文同步：模块地图、部署 `--target`、场景 `--mode auto`、目录地图、
  本更新日志入口。

---

## [Unreleased] — 2026-10-24 第二批：执行层解耦 B0–B4

### 新增

- **`flash/flash_run/execution.py`**：场景层与执行层之间的**唯一契约**。
  `EXEC_TARGETS = local | wsl | hpc-remote | hpc-insitu`、`resolve_target()`
  判定表（逐条判据轨迹打印）、`SceneSpec` / `ExecutionPolicy` / `NprocRule` /
  `ExecOptions` / `RunResult`、`run_scene()`（失败一律 `ok=False`，绝不吞错）。
- **`flash/scenarios/cli.py`**：`python -m flash.scenarios.cli list|explain|run <scene>`，
  `--mode` 默认 `auto`；`explain` 只打印判定轨迹不执行。
- **`flash/scenarios/catalog.py`**：可执行场景目录（与引擎用的 `registry.py` 分开，
  避免"新增一个能跑的算例"必须改引擎注册表）。
- **`flash/flash_run/remote/session.py`**：**全仓唯一 SSH 实现**（原 597 行住在
  `scenarios/flash_demo/demo_hpc/remote_ssh_helper.py`，属层次倒置）；新增
  `probe()/listdir()/exists()/mkdir_p()/put_dir()/get_many()`。
- **`flash/flash_run/remote/executors.py`**：`LocalExecutor` / `WslExecutor` /
  `SSHExecutor` 统一命令面。`WslExecutor` 用 **rc 哨兵**取退出码（`wsl.exe` 会吞码），
  `listdir` 不用 shell glob（Windows 侧会把 `*` 吃掉且无报错）。
- **`flash/flash_run/remote/artifacts.py`**：`fetch_artifacts()` —— 让
  `fetch_policy`（"该拿哪些文件"的唯一策略源）终于有了**唯一执行点**，
  四个 target 共用（本地 copy / wsl cp / sftp）。
- **`flash/flash_run/modes/hpc_insitu.py`**：hpc-insitu 编排从场景层迁入执行层，
  消除 `modes → scenarios → modes` 循环（旧路径保留转发壳）。
- **`deploy/targets.py`**：部署目标解析，复用执行侧判定（按路径加载
  `execution.py`，纯 stdlib，安装前即可用）。
- `start_flash.py --target auto|win|wsl|hpc`：**统一部署入口**，
  `--target hpc` 委托 `deploy/hpc_deploy/run_all.py`，`--` 之后透传参数。
- **分层护栏升级**：`check_scene_sources` 由单 token 扫描升级为规则引擎
  （`R-SCENE-02..07` + `R-LAYER-01/02a`），基线 `baseline_guards.txt` 由
  `--freeze` **自动生成**（98 条 `规则×文件`），只降不升。

### 变更

- **`flash/__init__.py` 与 `flash_run/__init__.py` 改 PEP 562 惰性导出**：
  此前 `from flash.flash_run.execution import SceneSpec`（只要一个 dataclass）
  会强制拉起 paramiko + cryptography。实测本地与超算均 `paramiko not in sys.modules`，
  而 `from flash.flash_run import FlashRemoteDeploy` 仍照常可用。
- **`modes/runner.Remote` 降级为 `RemoteSession` 适配器**（保留 8 个方法）：
  5 个工具脚本从 `flash.scenarios.runner` 导入它且不在 CI 内，删类会静默失联。
- **6 个部署脚本改 `from flash.flash_run.remote.session import RemoteSession`** ⇒
  `R-LAYER-01`（deploy 依赖场景层）**归零**；旧 `remote_ssh_helper` 保留为 re-export 壳。
- **`scenarios/__init__.py` 改惰性 `warm_registry()`**：原先 import 即全量导入
  public/flash_demo/private；`registry.get_scenario()` 首次调用自动预热，语义不变。
- **`run_all.pick_py()` 改走 `venv_paths` 并认 `FLASH_VENV_DIR`**，删除写死
  `C:\Users\Administrator\...python.exe` 的 `MANAGED_PY`。
- `RUN_MODES` 旧三元组**保持不动**（`test_scenarios_modes.py:39` 断言零改动），
  `EXEC_TARGETS` 为新增 canonical。

### 修复

- `Path.is_file()` 对 Windows 上的 `.venv-linux/bin/python` 符号链接抛
  `OSError: [WinError 1920]`（不是返回 False）⇒ 解释器探测整体崩溃。
  已在 `venv_paths._is_file` 与 `run_all.pick_py` 加安全包装。
- **`sbatch` 提交假失败**：`run_flash_on_hpc` 的超时 30 s 短于 NC-E
  `module load` 的 40~60 s ⇒ 作业**已提交并在跑**、封装层却报 `TimeoutExpired`。
  改为 180 s，且失败时回查 `squeue`（按 job-name）确认是否已提交。
- `flash.__version__` 在 Python 3.10（HPC venv）读不到 `tomllib` ⇒ 静默落到
  dist-info，源码树 0.1.11 却报 0.1.7。补最小 `[project].version` 解析。
- `main_hpc_insitu` 成功判据 `or (run_dir/"output").is_dir()` 恒真（目录前文已建）
  ⇒ 分析失败也报成功。改为要求确有 chk/plt 落地。

### 超算实测（NC-E scfa2696，2026-10-24）

- 增量同步 42.2 MB，双端 SHA256 一致；三套全局测试 **221 + 86 + 45 全绿**。
- `ch_center`（laserslab1d）**hpc-insitu 真跑**：JOBID 4921460，6795 步到
  `t=1.188162e-09 s`，`exit code 0`，341 chk + 1361 plt；分析出 3 张 PNG 并回收本地。

### 文档

- `docs/功能模块解耦与流程梳理计划.md`：批次状态更新 + §8 超算实测记录 +
  G11–G14 四个新暴露缺陷。
- README：场景执行改用统一 CLI（并纠正"脚本支持 `--mode`"的错误说法 ——
  `ch_center` 无 argparse，模式只能由 `FLASH_RUN_MODE` 指定）；补 `--target`、
  `flash.scenarios.cli`、护栏 `--freeze`。

---

## [0.1.11] - 2026-10-22

### 新增

- 超算离线部署链（`deploy/hpc_deploy/`，00–08 步）：远端归档清理、本地双环境预演、
  跨机构建 Linux wheelhouse、git bundle、打包上传、增量同步、命名环境离线安装、
  SNB 冒烟、public 场景 sbatch 真跑。
- `mcp_server` 与 `docs_index` 工具（去硬编码绝对路径）。
- `start_flash.py` 统一入口 + venv 按平台隔离（`.venv-win` / `.venv-linux`），
  解决 Windows 与 WSL 来回切换时 venv 互相破坏的问题。

### 变更

- 运行模式规范名统一为 `wsl` / `hpc-remote` / `hpc-insitu`（`hpc` 作为永久别名）。
- 物性绑定改为**场景自声明**（`par_gen.set_species_materials` + 断言），
  修复 V/Ti 层被按 CH 物性误算（V 层 t=0 压强曾偏差 15.1 倍）。

### 修复

- 超算 public 测试多处缺陷：并发/轮询/锁、输入目录锚定、MPI 运行时归一、
  产物统计深度（`_run`/`_outputs`/`$DST` 三处）、僵尸实例守卫。
- `ch_center` 跑成功却判 FAIL（chk 统计未覆盖 `_outputs` 目录）。

---

## [0.1.10] - 2026-10-21

- `scenarios/` 公开示例目录整理收尾（`public/` 容器化）。
- 新增 VAuTi 场景；修复其 `plot_var` 段错误。
- 极短验证提示机制（`--tmax 1e-11` 一跑定生死）。
- MCP 文档服务与工作流主题扩充。

---

## [0.1.9] - 2026-09-20

- `eosop` / `output_processors` 的 chk 处理升级。
- `cn4_thermo` 模块固化声速计算，修复 `cn4_paths` 声速公式漏 `ln(10)` 因子。
- 清理被 `cn4_thermo` 取代的 `sv_physics` / `sv_plots`。

---

## [0.1.8] - 2026-09-16

- 新增 `eosop_pro` 多类型文件处理模块（EOS/不透明度数据工具包）。
- `cn4/` 扁平化泛化、`uk`/`uv` 散点规约、绘图标签统一 `:.1e`。
- Git 推送脚本新增「删除护栏」（防文件系统间歇不可见导致 `git add -A` 误提交大规模删除）；
  Gitee API 鉴权改走请求头，token 不再出现在 URL。

---

## [0.1.7] - 2026-09-08

- 版本号占位发布：`0.1.6` 的 wheel 文件名因 PyPI 的 file-name-reuse 策略
  永久不可复用，故跳过 `0.1.6` 发布并直接发布 `0.1.7`。

---

## [0.1.6] - 2026-09-08

- 移除 `thin_layer_sandwich_al` 场景与 `tables_imx.py`（imx 系表内嵌）。

---

## [0.1.5] - 2026-08-26

- `gen_checker` 新增文件内在关联检查 `check_relations.py`（检查器升级）。

---

## [0.1.3] / [0.1.2] / [0.1.1] / [0.1.0] / [0.0.1] / [0.0.0]

早期版本，未单独维护条目。查阅方式：

```bash
git log --oneline 0.1.3..0.1.5     # 或对应 tag 区间
```
