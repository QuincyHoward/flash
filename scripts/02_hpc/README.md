# scripts/02_hpc — 超算部署与结果回传

> 最后核对：2026-11-15 · commit 97d5e5d

**职责**：经 SSH/SFTP 在超算（NC-E 等）编译、提交、回收 FLASH 1D 场景运行结果；本目录只做「传输与远程执行」，不含仿真物理逻辑。

## 文件清单

| 文件 | 职责 |
|---|---|
| `hpc_laserslab_test.py` | 远程编译（Makefile.h 缓存）+ 准备运行目录 + mpirun + 检查 HDF5 输出并报告 |
| `hpc_run_laserslab.sh` | 上传到超算后执行的运行脚本 |
| `hpc_run_uploader.py` | 运行脚本上传与远程执行器 |
| `hpc_download_results.py` | SFTP 打包下载 HDF5 结果到本地场景输出目录 |
| `probes/` | 一次性诊断探针集合，见 [probes/README.md](probes/README.md) |

## 常用命令

```bash
python scripts/02_hpc/hpc_laserslab_test.py
python scripts/02_hpc/hpc_run_uploader.py
python scripts/02_hpc/hpc_download_results.py
```

## 约定

- SSH 凭据统一从加密存储读取，禁止硬编码用户名/主机/口令。
- 用户名由环境变量 `FLASH_SIM_USER_DIR` 控制（默认 `hello`）。
- SNB 场景族禁止本地/WSL 执行，只能提交超算；本目录工具只做静态核验与传输。
- 大批量下载与连接级重试策略见 `flash-hpc-fetch` skill。

**上级导航**：[../README.md](../README.md)
