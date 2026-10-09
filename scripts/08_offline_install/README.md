# 离线安装（Offline Install）指南

**适用场景**：目标电脑**无网络**（内网/涉密/物理隔离），但需要部署本仓库的
`flash-sim` 包及其全部依赖。

**核心思路**：在**联网机**上把包下载到一个自包含目录（wheelhouse），经U 盘
拷贝到**离线机**，用 `pip --no-index --find-links` 本地安装，全程不联网。

---

## ★ 设计要点：在线/离线双模式

改造后 `start_flash.py` **同时支持在线与离线**，共用同一套逻辑，仅一个开关之差：

```
                    start_flash.py（唯一入口）
                              │
                ──────────────┴──────────────
                             run_pip()← 唯一分叉点
                  ┌──────────────┴──────────────┐
              在线（默认）│                     │ 离线
  pip install -e ".[full,dev]"      pip install --no-index
          scipy paramiko            --find-links=<wheelhouse>
                  │                     │
                  └──────────────┬──────────────┘
                                 ▼
        check_env_health → 自愈重建 → 三套测试 → INSTALL_TEST_REPORT.txt
                        （两模式共用同一套校验与报告）
```

切换开关（三选一，优先级从上到下）：

| 方式 | 在线 | 离线 |
|------|------|------|
| 命令行 | `python start_flash.py` | `python start_flash.py --offline` |
| 环境变量 | 默认 | `set FLASH_OFFLINE=1` |
| 自动探测 | 强制 `FLASH_FORCE_ONLINE=1` | 项目根有 `wheelhouse/MANIFEST.json` → 自动转离线 |

> **为什么不自动跑**：`--no-index` 是硬闸门，pip 物理上无法访问 PyPI，缺包会
> **立即失败**并指名缺哪个包，而不会静默联网补装。离线部署最常见的翻车点就是
> "装到一半才发现漏包，venv 半残，必须从头再来"。

---

## 一、联网机：造包

双击 `scripts\08_offline_install\build_wheelhouse.bat`，或命令行：

```bash
# 默认：full 档 + 附带 Python 安装程序（推荐）
python scripts/08_offline_install/build_wheelhouse.py

# 精简档（保留 yt 出图，去掉 dev 工具链）
python scripts/08_offline_install/build_wheelhouse.py --profile runtime

# 最精简（无 yt/matplotlib/pandas）
python scripts/08_offline_install/build_wheelhouse.py --profile lite

# 离线机已有Python，不要附带安装程序
python scripts/08_offline_install/build_wheelhouse.py --no-interpreter

# 只看计划不实际下载
python scripts/08_offline_install/build_wheelhouse.py --dry-run
```

产物结构：

```
offline_pkg/wheelhouse/          ← 拷这个目录
├── flash_sim-0.1.7-py3-none-any.whl    ← 项目本体（本地构建）
├── numpy-*.whl / scipy-*.whl
├── yt-*.whl / matplotlib-*.whl / ...
├── python-3.13.9-amd64.exe      ← 离线机无 Python 时才需要
└── MANIFEST.json                ← size + SHA256 全清单
```

三档profile 对比：

| 档位 | 内容 | 典型体积 | 适用 |
|------|------|---------|------|
| `full`（默认） | base + `[full]` + `[dev]`，可跑三套测试 | ~1GB | 开发/测试机 |
| `runtime` | base + `[full]`，无 pytest/black/ruff，保留 yt | ~600MB | 日常出图 |
| `lite` | 精简（无 yt/matplotlib/pandas） | ~200MB | 只需数值与 HDF5 读取 |

> **注意**：档位必须**造包与安装两端一致**，否则预检会拦下。

---

## 二、拷贝到U 盘

必须拷**整个 `wheelhouse/` 目录**（含 `MANIFEST.json`），**不能只拷 `.whl`**。
建议同时拷项目源码（离线机要用 `start_flash.py` 和 `tests/`）：

```bash
python scripts/04_backup/usb_backup.py E:\usb_src
```

---

## 三、离线机：安装

1. 若离线机**没有 Python**，先双击 `wheelhouse\python-*-amd64.exe`
   安装（建议勾选 *Add Python to PATH*）。
   —— 脚本**不会自动运行**安装程序：装解释器属系统级变更，必须用户亲自确认。

2. 双击 `scripts\08_offline_install\install_offline.bat`，或：

```bash
python scripts/08_offline_install/install_offline.py            # 自动找 wheelhouse/
python scripts/08_offline_install/install_offline.py D:\pkg\wheelhouse   # 显式指定
python scripts/08_offline_install/install_offline.py --check-only       # 只校验不安装
python scripts/08_offline_install/install_offline.py --no-tests# 快速装环境不跑测试
```

安装完成后：
- 虚拟环境：`.venv\`（项目根专属，与其他项目完全隔离）
- 测试报告：`INSTALL_TEST_REPORT.txt`
- 激活：`.venv\Scripts\activate`

---

## ★ 三道安装前闸门

`install_offline.py` / `start_flash.py --offline` 在安装**前**依次把三道关，
任一不过即中止，**绝不产出半残 venv**：

1. **wheelhouse 目录存在** —— 找不到就打印已尝试的路径并给可操作指引。
2. **MANIFEST 校验** —— 每个归档的存在性 + 大小 + **SHA256**。
   U 盘拷贝是最容易静默损坏的传输环节，必须先于 pip 拦截。
3. **依赖覆盖度预检** —— 比对 `pyproject.toml` 的依赖闭包 ⊆ wheelhouse 实际
   文件，缺一个就报**全清单**并指出该用哪个档位重造包。

---

## 常见问题

| 现象 | 根因 | 处理 |
|------|------|------|
| `[FATAL] 找不到 wheelhouse 目录` | 没拷目录，或路径不对 | 用 `--wheelhouse <路径>` 显式指定 |
| `[FATAL] 缺少 N 个直接依赖` | 造包与安装档位不一致 | 联网机用相同 `--profile` 重造包 |
| `[SHA256 不符]` | U 盘拷贝损坏 | 重新拷贝整个目录 |
| `No matching distribution found` | wheelhouse 缺传递依赖 | 联网机重跑 `build_wheelhouse.py` |
| 离线机没 Python | 造包时加了 `--no-interpreter` | 双击 wheelhouse 内安装程序，或重造包 |

---

## 目录收纳

本方案全部脚本收纳在 `scripts/08_offline_install/`，**根目录不新增文件**
（符合项目"根目录保持纯净、仅放 `*.md` 与 `bat` 启动器"的约定）：

```
scripts/08_offline_install/
├── _wh_common.py        公共工具：依赖解析 / 文件名归一化 / MANIFEST / 预检
├── build_wheelhouse.py  联网机：造离线包
├── install_offline.py   离线机：一键安装 + 校验
├── build_wheelhouse.bat 联网机启动器（ASCII/CRLF）
├── install_offline.bat  离线机启动器（ASCII/CRLF）
└── README.md            本文档
```

对 `start_flash.py` 的改动是**最小侵入**的：仅在 `run_pip()` 加离线分支、
新增 `--offline/--wheelhouse/--profile` 参数、离线前置校验，以及报告里
多记录安装模式；在线路径行为**保持不变**。

---

## 换机/ 升级

- **换机**：把 `wheelhouse/` + 项目源码一起拷到新机，重跑
  `install_offline.py` 即可。
- **升级依赖**：联网机重跑 `build_wheelhouse.py`，**重新拷贝整个 wheelhouse
  目录**（含新的 `MANIFEST.json`），离线机重跑 `install_offline.py`。