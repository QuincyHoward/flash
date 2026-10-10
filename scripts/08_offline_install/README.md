# 离线安装（Offline Install）指南

本项目**同一个入口**支持两种安装方式，联网机与离线机各走一条：

| 你的情况 | 走哪条 | 命令 |
|---------|-------|------|
| **有网络** | 直接在线安装 | `python start_flash.py` |
| **无网络**，但手上有U 盘包 | 离线安装 | `python start_flash.py --offline` |

---

## 目录

- [一、联网机：直接开始（最常用）](#一联网机直接开始最常用)
- [二、联网机：造 U 盘离线包](#二联网机造-u-盘离线包)
- [三、拷贝到 U 盘（尽量轻量）](#三拷贝到-u-盘尽量轻量)
- [四、离线机：安装](#四离线机安装)
- [★ 三道安装前闸门](#--三道安装前闸门)
- [常见问题](#常见问题)
- [目录收纳](#目录收纳)
- [换机 / 升级](#换机--升级)

---

## 一、联网机：直接开始（最常用）

**有网络就不需要 U 盘、不需要造包**，直接跑：

```bash
# Windows
python start_flash.py

# 或双击项目根目录下的 start_flash.bat
```

它会自动完成：

1. 检查 Python 版本 → 建虚拟环境 `.venv\`（已存在则复用）
2. `pip install -e ".[full,dev]" scipy paramiko` 装全部依赖
3. 健康检查；不合格则**自动清零重建**
4. 跑三套测试，生成 `INSTALL_TEST_REPORT.txt`

> **首次约需 3–5 分钟**（要下载 70+ 个包）；之后重跑约 20 秒（跳过已装依赖）。

### 联网机常用参数

```bash
python start_flash.py --help        # 看全部选项
python start_flash.py --quick       # 装完不跑测试，快
python start_flash.py --reinstall   # 强制重建环境
```

### 想手动控制档位（体积更小）

`full` 档带开发工具链（pytest/black/ruff），日常只出图不需要：

```bash
python start_flash.py --profile runtime   # 保留 yt 出图，去掉 dev 工具
python start_flash.py --profile lite      # 再去掉 yt/matplotlib/pandas
```

| 档位 | 内容 | 装完占用 | 适用 |
|------|------|---------|------|
| `full`（默认） | base + `[full]` + `[dev]`，可跑三套测试 | ~632 MB | 开发/测试 |
| `runtime` | base + `[full]`，保留 yt，**无 pytest/black/ruff** | ~480 MB | 日常出图 |
| `lite` | 无 yt/matplotlib/pandas | ~180 MB | 只需数值与 HDF5 读取 |

> 三套测试只在 `full` 档下运行；`runtime`/`lite` 档会跳过测试并给出提示。

---

## 二、联网机：造 U 盘离线包

只有在**目标电脑无网络**时才需要这一步。

双击 `scripts\08_offline_install\build_wheelhouse.bat`，或命令行：

```bash
# 默认：full 档 + 附带 Python 安装程序（离线机没Python 时需要）
python scripts/08_offline_install/build_wheelhouse.py

# 精简档（保留 yt 出图，去掉 dev 工具链）
python scripts/08_offline_install/build_wheelhouse.py --profile runtime

# 最精简（无 yt/matplotlib/pandas）
python scripts/08_offline_install/build_wheelhouse.py --profile lite

# 离线机已有 Python，不要附带安装程序（省 25MB）
python scripts/08_offline_install/build_wheelhouse.py --no-interpreter

# 只看计划不实际下载
python scripts/08_offline_install/build_wheelhouse.py --dry-run
```

### 产物结构

```
offline_pkg/wheelhouse/          ← ★ 只拷这个目录
├── flash_sim-0.1.7-py3-none-any.whl    ← 项目本体（本地构建，约 5MB）
├── numpy-*.whl / scipy-*.whl
├── yt-*.whl / matplotlib-*.whl / ...
├── python-3.13.9-amd64.exe      ← 离线机无 Python 时才需要（25MB）
├── MANIFEST.json                ← size + SHA256 全清单
└── .stale/                      ← 上一轮被隔离的旧包（可删）
```

### 实测体积（09-10，两平台实测）

| 档位 | Windows / Py 3.13 | Linux / Py 3.10 | 装完 `.venv` | 备注 |
|------|-------------------|-----------------|-----------|------|
| `full` | **130 MB**（71 包） | **165 MB**（78 包） | **647 MB**（Win 实测） | 可跑三套测试 |
| `runtime` | 约 100 MB | 约 130 MB | ~480 MB | 去 dev 工具链 |
| `lite` | **56 MB**（14 包） | 约 70 MB | ~180 MB | 无 yt/matplotlib/pandas |
| `--no-interpreter` | 少 25 MB | 不适用 | — | 离线机已有 Python 时用 |

> ★ 上表 `full` 两列与 `lite` 均为09-10 **实测值**，`runtime` 为估算。

### ★★ 为什么两平台包数不同（71 vs 78）—— 主因是 **Python 版本**，不是平台

逐包对比结论：

| 差异包 | 归属 | 原因 |
|--------|------|------|
| `colorama`、`pywin32-ctypes` | 平台 | Windows 终端 ANSI 色彩 / Win32API ctypes |
| `jeepney`、`secretstorage` | 平台 | paramiko 的 Linux 密钥后端 |
| `typing-extensions`、`tomli`、`exceptiongroup`、`importlib-metadata`、`zipp`、`backports.tarfile` | **Python 3.10** | 3.11+ 才内置 `tomllib`/`exceptiongroup`，3.10 需外部垫片 |
| `pytz` | **Python 3.10** | 被 pandas 2.x 依赖（pandas 3.x 已不需） |

另：`numpy`/`scipy`/`matplotlib`/`pandas` 在 3.10 上只能取到较旧版本
（如 numpy 2.2.6 vs 3.13 上的 2.5.3），体积也随之不同。

⇒ **同一 Python 版本下，Windows/Linux 的包集合应当一致**（pip 会为当前解释器
选到对应平台 wheel）。**联网机与离线机请使用同Python 版本**。

### 平台一致性闸门（09-10 新增）

`MANIFEST.json` 现在记录 `platform_tag` / `python_tag` / `platform_extra_pkgs`。
离线机安装前会比对，**不匹配直接中止并给出可操作提示**：

```
[FATAL] wheelhouse 与本机平台/Python 版本不匹配:
   - Python 版本不匹配：wheelhouse 造于 **3.10**，本机是 **3.13**。
     wheel 带 cp3XX ABI 标签，跨小版本无法安装。
     ⇒ 请用 Python 3.10 造包，或在 3.13 机器上重造：
       python scripts/08_offline_install/build_wheelhouse.py
```

> ★ 为什么需要：wheel 文件名带 `cp3XX-` **ABI 标签**，跨版本根本装不上，
> 而 pip 只会说 "No matching distribution found"，**不会告诉你是版本问题**。
> 旧版 MANIFEST 无这两个字段时会**跳过检查并提示重造**（向后兼容）。

> ★ **体积大头**是 `scipy`、`yt`、`numpy`、`pandas`、`matplotlib`。
> **若离线机只需要跑仿真、不需要出图，选 `lite` 档最省**（Win 实测 56MB，是 full 的 43%）。

> ★★ **本体 wheel 只有 5.5 MB**（1028 条目），造包耗时 4 s。
> 09-10 修复前是 **100.5 MB**（2873 条目）——`.gitignore` 管不到 wheel，
> 详见下方「为什么 wheel 会变大」。

### 为什么 wheel 会变大（09-10 血泪教训）

根 `.gitignore:11` 有一条裸 `*`（忽略所有无扩展名文件）。git 能正确处理它，
但 **hatchling 的 VCS 排除有个安全阀**：

```python
exclude_spec = pathspec.GitIgnoreSpec.from_lines(patterns)
if exclude_spec.match_file(self.root):
    return []          # ← 静默丢弃**全部** VCS 规则
```

裸 `*` 匹配到项目根自身 ⇒ 命中安全阀 ⇒ **536 条 .gitignore 规则全部失效**。
于是 git 忽略的 336.8MB 测试产物 + FLASH 引擎源码（License §3 违规）
被一并打进 wheel（占 94.5%）。

⇒ **本仓库的 `.gitignore` 无法充当 wheel 排除规则**，两者必须成对手写
（写在 `pyproject.toml` 的 `[tool.hatch.build.targets.wheel/sdist].exclude`）。

### 泄漏审计（构建后自动跑）

```bash
python scripts/08_offline_install/wheel_leak_audit.py            # 审计默认 wheelhouse
python scripts/08_offline_install/wheel_leak_audit.py <wheel>     # 指定 wheel
```

检查四项：**体积 / 条目数 / FLASH License §3 材料 / git-ignored 泄漏**。
`build_wheelhouse.py` 在写完 MANIFEST 后会自动跑它，不通过即**中止造包**
（`--no-audit` 可逃逸，但不建议）。

> ★ 判据按**体积**而非文件数：修正误排除后残余 50 个文件 / 384KB
> （`results/*.json`、`metrics_*.csv` 等科研快照），对离线使用者有参考价值，
> 不必为 0.1% 的体积把它们全砍掉。
> ★ 审计器自身已做两次修复：`text=True` 漏报 94.5%（Windows ANSI 代码页
> 弄坏 CJK 路径）、`§3` 子串匹配误报自研文档（`MultiEOSOP格式说明.md`）。
> **报喜不报忧的护栏比没有护栏更危险** —— 改它务必重跑负向样本。

---

## 三、拷贝到 U 盘（尽量轻量）

### ★ 只拷这些

| 拷什么 | 大小 | 为什么 |
|--------|------|-------|
| `wheelhouse/` | 130 MB | **必需**（含 `MANIFEST.json`，一个都不能少） |
| 项目源码 | **17.2 MB**（1391 文件） | 离线机要用 `start_flash.py` 和 `test/` |

源码用现成脚本导出（只拷 git 跟踪的内容，自动排除所有数据/产物）：

```bash
python scripts/04_backup/usb_backup.py --mode gitee E:\usb_target
```

> ★ 该脚本的文件列表来自 `git ls-files --cached --others --exclude-standard`
> ⇒ **git 忽略的一律不拷**。09-10 实测：导出 1391 文件 / 17.2 MB，
> 而 `flash/` 目录在磁盘上是 71 GB。

### ✗ 千万不要拷这些

| 别拷 | 磁盘实测 | 原因 |
|------|---------|------|
| 场景数据 `flash_output/`、`flash_input/` | **~62 GB** | 仿真产物，可重新生成 |
| `SNBtest/src/`（FLASH 引擎源码） | **1.3 GB** | FLASH 版权材料，且体积巨大 |
| `Multi1D++Portable*` | ~1.5 GB | 第三方参考解，非自研代码 |
| `.venv/` | 647 MB | 离线机自己会建 |
| `eosop_pro/test/**/_out/` | 275 MB | 测试过程产物 |
| `dist/`、`build/` | 变化 | 造包中间产物 |

> ★ `flash/` 整个目录在磁盘上是 **71 GB**，但 `usb_backup.py --mode gitee`
> 只导 **17.2 MB**（1391 文件）。差别全在上面这张表里。
> **务必用该脚本导出源码**，手工整目录拷会把 71 GB 全带走。

> ★ 上述目录**已在 `pyproject.toml` 的 exclude 中排除**，所以不会进 wheel ——
> 但如果你手工整目录拷到 U 盘，它们仍会被一并带走。

### 一条命令搞定（推荐）

```bash
# 联网机：造包 + 导出源码，一起放到 U 盘
python scripts/08_offline_install/build_wheelhouse.py --zip
```

`--zip` 会额外生成 `wheelhouse.zip`（约 90MB），单个文件拷 U 盘更省事，
且能在传输后校验完整性。

---

## 四、离线机：安装

1. 若离线机**没有 Python**，先双击 `wheelhouse\python-*-amd64.exe`
   安装（建议勾选 *Add Python to PATH*）。
   —— 脚本**不会自动运行**安装程序：装解释器属系统级变更，必须用户亲自确认。

2. **Linux / WSL 无需任何前置操作** ★（09-10 起）

   Ubuntu 默认**不装** `python3.x-venv`，此时 `python3 -m venv` 会失败并提示
   `apt install python3.10-venv`。很多用户第一反应是「先去联网 apt install」
   —— 这违背离线部署初衷。

   **本脚本已内置离线自举**：检测到缺 `ensurepip` 时，自动
   1. 用 `python3 -m venv --without-pip` 建骨架
   2. 从 **wheelhouse 里自带的 `pip-*.whl`** 把 pip 装进新 venv
   3. 继续正常流程（装 setuptools → 装 flash 包 → 跑三套测试）

   全程 `--no-index`，**不联网、不碰 apt**。日志形如：

   ```
   [warn] venv 创建失败：base 解释器缺 ensurepip 模块（Ubuntu/WSL 默认不装 python3.x-venv）
   [info] 改用--without-pip 建骨架 + wheelhouse 离线自举 pip ...
         ★ 无需联网 apt install —— wheelhouse 内已含 pip wheel
   [ok] venv 骨架已创建（无 pip）: /path/.venv/bin/python
   [info] 用 wheelhouse 里的 pip 自举（pip-26.2.1-py3-none-any.whl）...
   [ok] pip 自举成功（无需 apt install python3.x-venv）
   ```

   ⇒ **所以「1.1 前置检查」这一步在 Linux/WSL 上已经不需要了，直接跑第 3 步即可。**

   > 若 wheelhouse 不完整（缺 `pip-*.whl`），脚本会明确提示重新造包。

3. 双击 `scripts\08_offline_install\install_offline.bat`，或：

```bash
python scripts/08_offline_install/install_offline.py            # 自动找 wheelhouse/
python scripts/08_offline_install/install_offline.py D:\pkg\wheelhouse   # 显式指定
python scripts/08_offline_install/install_offline.py --check-only# 只校验不安装
python scripts/08_offline_install/install_offline.py --quick     # 快速装环境不跑测试
```

或走统一入口（等价于上面第 3 步）：

```bash
python start_flash.py --offline --wheelhouse D:\pkg\wheelhouse
```

安装完成后：
- 虚拟环境：`.venv\`（Windows）/ `.venv/`（Linux，项目根专属，与其他项目完全隔离）
- 测试报告：`INSTALL_TEST_REPORT.txt`
- 激活：`.venv\Scripts\activate`（Windows）/ `source .venv/bin/activate`（Linux）

> **离线模式一律装真 wheel，不用 `-e .`**：editable 会往 `.venv` 写指向
> 源码树的**绝对路径**，换机即失效。

---

## ★ 四道安装前闸门

`install_offline.py` / `start_flash.py --offline` 在安装**前**依次把四道关，
任一不过即中止，**绝不产出半残 venv**：

1. **wheelhouse 目录存在** —— 找不到就打印已尝试的路径并给可操作指引。
2. **MANIFEST 校验** —— 每个归档的存在性 + 大小 + **SHA256**。
   U 盘拷贝是最容易静默损坏的传输环节，必须先于 pip 拦截。
3. **平台 / Python 版本一致性**（09-10 新增）—— 比对 `MANIFEST.json` 里的
   `platform_tag` / `python_tag` 与本机。wheel 带 `cp3XX-` ABI 标签，
   跨版本装不上时 pip 只会说 "No matching distribution found"，
   **不会告诉你是版本问题** ⇒ 这里提前拦下并给出重造指引。
4. **依赖覆盖度预检** —— 比对 `pyproject.toml` 的依赖闭包 ⊆ wheelhouse 实际
   文件，缺一个就报**全清单**并指出该用哪个档位重造包。

`--no-index` 是硬闸门：pip 物理上无法访问 PyPI，缺包会**立即失败**并指名缺哪个包，
而不会静默联网补装。离线部署最常见的翻车点就是"装到一半才发现漏包，
venv 半残，必须从头再来"。

---

## ★ 双模式实现要点

```
                start_flash.py（唯一入口）
                          │
            ──────────────┴──────────────
                       run_pip()      ← 唯一分叉点
              ┌──────────────┴──────────────┐
          在线（默认）                 离线
  pip install -e ".[full,dev]"    pip install --no-index
          scipy paramiko          --find-links=<wheelhouse>
              │            │
              └──────┬───────────────┘
                     ▼
    check_env_health → 自愈重建 → 三套测试 → INSTALL_TEST_REPORT.txt
                  （两模式共用同一套校验与报告）
```

切换开关（三选一，优先级从上到下）：

| 方式 | 在线 | 离线 |
|------|------|------|
| 命令行 | 默认 | `python start_flash.py --offline` |
| 环境变量 | 默认 | `set FLASH_OFFLINE=1` |
| 自动探测 | 强制 `FLASH_FORCE_ONLINE=1` | 项目根有 `wheelhouse/MANIFEST.json` → 自动转离线 |

> **自动探测的判据只能是 `wheelhouse/MANIFEST.json` 本身**，绝不能用
> 「`scripts/08_offline_install/` 目录存在」这类间接信号 —— 该目录随仓库分发，
> 联网机上永远存在，拿它当判据会把**所有在线用户**误切成离线模式。

在线路径行为**完全不变**（仍为 `pip install -e ".[full,dev]" scipy paramiko`）。

---

## 常见问题

| 现象 | 根因 | 处理 |
|------|------|------|
| `[FATAL] 找不到 wheelhouse 目录` | 没拷目录，或路径不对 | 用 `--wheelhouse <路径>` 显式指定 |
| `[FATAL] 缺少 N 个直接依赖` | 造包与安装档位不一致 | 联网机用相同 `--profile` 重造包 |
| `[SHA256 不符]` | U 盘拷贝损坏 | 重新拷贝整个目录 |
| `No matching distribution found` | wheelhouse 缺传递依赖 | 联网机重跑 `build_wheelhouse.py` |
| 离线机没 Python | 造包时加了 `--no-interpreter` | 双击 wheelhouse 内安装程序，或重造包 |
| `[stale] 已隔离上一轮产物` | 正常提示：造包前会挪走旧 wheel | 无需处理；`.stale/` 可删 |
| `[WARN] wheel 体积 ... 偏大/偏小` | pyproject exclude 可能漏了新目录 | 核对 `pyproject.toml` 的 `[wheel].exclude` |
| `build 未产出 wheel` 中止 | 构建失败（磁盘满/语法错/exclude 排太狠） | 看上方 build 报错；确认后可加 `--allow-legacy-dist` |

---

## 目录收纳

本方案全部脚本收纳在 `scripts/08_offline_install/`，**根目录不新增文件**
（符合项目"根目录保持纯净、仅放 `*.md` 与 `bat` 启动器"的约定）：

```
scripts/08_offline_install/
├── _wh_common.py        公共工具：依赖解析 / 文件名归一化 / MANIFEST / 预检
├── build_wheelhouse.py  联网机：造离线包
├── install_offline.py   离线机：一键安装 + 校验
├── build_wheelhouse.bat 联网机启动器
├── install_offline.bat  离线机启动器
└── README.md            本文档
```

回归自检（64 项断言，不需要网络）：

```bash
python scripts/08_offline_install/test_offline_install.py
```

---

## 换机 / 升级

- **换机**：把 `wheelhouse/` + 项目源码一起拷到新机，重跑
  `install_offline.py` 即可。
- **升级依赖**：联网机重跑 `build_wheelhouse.py`，**重新拷贝整个 wheelhouse
  目录**（含新的 `MANIFEST.json`），离线机重跑 `install_offline.py`。
