# flash_run/remote — 远程超算层

> 最后核对：2026-11-05 · commit 7e04857 · 维护规则：改动本目录下 .py 后必须同步本文模块表

## 1. 职责定位

超算远程执行的全部实现：SSH 会话（**全仓唯一实现** `RemoteSession`）、统一命令执行器、SLURM 作业控制、作业目录拓扑/脚本生成/提交服务、chk-only 产物回收策略。**本包不硬编码任何主机/端口/线路**——路由与账户信息一律来自 `~/.physimx/flash/hpc_accounts.json`（权威声明见 [`../../_core/credentials/README.md`](../../_core/credentials/README.md) §4）。

## 2. 模块清单

| 文件 | 行数 | 职责 | 关键入口 |
|---|---|---|---|
| `__init__.py` | 21 | 子包声明 | — |
| `session.py` | 719 | ★ **RemoteSession 唯一实现**（ssh CLI / paramiko 双通道 + 动态路由）；15 个场景/框架消费方的唯一 SSH 底座 | `RemoteSession` |
| `executors.py` | 288 | 统一命令执行器：local/wsl/ssh/hpc 四 target 共用唯一命令面 | `make_executor`、`CommandExecutor` 族 |
| `slurm_control.py` | 322 | SLURM 作业控制薄层（三模式统一） | `submit`、`job_state`、`latest_job_by_name` |
| `job_layout.py` | 427 | 超算作业**目录拓扑**与**资源规格**唯一实现点 | `JobLayout`、`ResourceSpec`、`resolve_layout` |
| `job_scripts.py` | 271 | 超算作业体生成器（stage → build → run → archive） | `render_job_body` |
| `job_submit.py` | 224 | 通用作业提交服务（不含场景信息） | `JobRequest`、`render_job`、`submit_job` |
| `fetch_policy.py` | 139 | chk-only 下载策略——全场景唯一来源（plt 默认不回传） | `classify_names`、`pick_frames` |
| `artifacts.py` | 79 | 产物回收——`fetch_policy` 的唯一执行器 | `fetch_artifacts` |
| `route_tester.py` | 485 | SSH 多路由 TCP 延迟实测与自动择优（缓存 `~/.physimx/route_cache/`） | `RouteTester`、`main()` |
| `remote_deploy.py` | 811 | ⚠️ **兼容壳**：旧 `FlashRemoteDeploy` 门面，内部已委托新模块；不推荐新代码使用 | `FlashRemoteDeploy`（历史 API） |
| `remote_workflow.py` | 143 | 超算完整工作流脚本（临时调试用） | CLI |
| `remote_check.py` | 71 | 远程环境检查（临时调试用） | CLI |
| `ssh_check.py` | 108 | 连接→检查→分析→绘图→下载 调试链（临时） | CLI |

## 3. 作业提交链（新主线）

```
job_layout.resolve_layout()      目录拓扑 + ResourceSpec（scratch 探测/输入暂存/并行编译）
        ↓
job_scripts.render_job_body()    生成 stage→build→run→archive 作业体
        ↓
job_submit.submit_job()          sbatch 提交（通用, 无场景信息）
        ↓
slurm_control                     作业状态/取消/按名回查
        ↓
fetch_policy → artifacts         chk-only 回收（完整 md5 校验后才删远端）
```

## 4. 路径解析（★ 高频踩坑区，实战沉淀）

### SFTP 不展开 `~`

SFTP 协议**没有 shell**，`~` 在 `sftp.put()/get()/stat()` 中是普通字符——"上传成功却找不到文件"的经典来源。`session.py` 的 `_resolve_path()` 已统一处理：`~/` 前缀经同一连接 `printf '%s' "$HOME"` 展开（★ 不要用 `echo ~`，部分环境返回字面 `~`）；但新代码仍建议**一律绝对路径**。

### 远端文件清单：`find -printf`，不要 `ls -la | awk`

文件名含空格/中文时后者会截断错位：`find <dir> -maxdepth 1 -type f -printf '%s %f\n'`，或走 Python `sftp.listdir_attr()`。

### 下载完整性判据

FLASH `chk` 完整性**只认 md5**——"h5py 能打开"与"文件完整"正交（截断的 HDF5 有时仍可打开但数据是错的）。**逐文件核对 md5 后再删远端源**。

### 断网重试

长传输应**每文件独立建连 + 指数退避**，而非整批失败退出（参考 `scenarios/private/tracer/SNB/SNBOneCH_ml/scripts/longrun/03_run_16ns_pipeline.py` 的 `_run_with_net_retry()`）。

## 5. 快速上手

```bash
python -m flash.flash_run.hpc route-test                  # 路由实测择优（推荐入口）
python -m flash.flash_run.remote.route_tester             # 模块直跑同上
```

```python
from flash.flash_run.remote.session import RemoteSession

with RemoteSession(credential_name="flash_ssh") as s:     # 路由自动实测择优
    out, rc = s.run("squeue -u $USER")
    s.upload("a.tar.gz", "/abs/path/a.tar.gz")            # 绝对路径
```

## 6. 注意事项

1. 每次连接都**重新实测路由**——最优线路随网络波动变化（实测 201ms~4582ms 抖动，历史数据见 git 历史），且部分 v6/cstnet 线路常不可达；
2. TCP 通 ≠ SSH 认证成功；默认超算账户 `flash_ssh`（第二账户 `flash_ssh_2`），凭据管理见 `_core/credentials`；
3. `install_flash()` 在兼容壳中为占位实现，真实部署走 `job_scripts` 编译链；
4. 作业监控用 `sacct`，需超算已装 SLURM。

## 7. 测试入口

路由测试命令见 §5；`route_tester.py` 有 `--dry-run` 类自检；产物回收策略由 `fetch_policy.pick_frames` 纯函数可单测。完整链路验证走场景 `hpc-remote` 模式。

## 8. 导航

上级：[../README.md](../README.md)（含工程铁律 §8——SFTP/SLURM/insitu 实战事故） · 相邻：[../modes/README.md](../modes/README.md)、[../env/README.md](../env/README.md) · 凭据权威：[../../_core/credentials/README.md](../../_core/credentials/README.md)
