> 最后核对：2026-11-14 · commit ba2981e（其后含功能树重组，代码为准）

# scripts/ —— Windows 双击启动器（12 个 .bat）与薄包装（10 个 .py）

**10 个 py 薄包装**只做一件事：把 `gen_eos_op` 根目录插进 `sys.path` 后调用
`eosop_pro.pipeline.cli.main([["<子命令>"]])`——真正的实现全在包内（便于单测与
复用），这是 cli docstring 写明的分工纪律。**12 个 bat** 是双击一步启动器：
ASCII-only（Windows cmd GBK 安全）、CRLF 行尾（cmd.exe 多行块要求）、
`pause` 停窗看结果。

**ROOT 上溯机制**：bat 里 `set ROOT=%~dp0..\..`——从 `eosop_pro/scripts/` 上溯
两级即指向 `gen_eos_op`（包父目录），随后 `cd /d "%ROOT%"` 保证 `-m eosop_pro.*`
可导入。解释器固定为受管 venv：
`%USERPROFILE%\.workbuddy\binaries\python\envs\default\Scripts\python.exe`，
缺失时提示先跑 `env_setup.bat`。

## bat ↔ py ↔ cli 子命令对照表

| bat（双击启动器） | py（薄包装） | 实际执行的 cli 子命令 / 动作 | 步骤号 |
| --- | --- | --- | --- |
| `env_setup.bat` | — | 创建受管 venv + 安装 numpy/h5py/scipy/cryptography/matplotlib | 前置 |
| `01_extract_docs.bat` | `01_extract_docs.py` | `extract-docs`（doc/docx/pptx/xlsx/pdf/xmind → docs/extracted） | ① |
| `02_inventory.bat` | `02_inventory.py` | `inventory`（matter++ 全量清单与目录画像） | ② |
| `03_audit.bat` | `03_audit_sweep.py` | `audit`；⚠️ 该 py 自带 argparse，**直接调** `batch.audit_sweep`（可 `--limit/--multigroup/--matter-dir`） | ③ |
| `04_zeff.bat` | `04_zeff_inventory.py` | `zeff`（Z̄ 盘点并写报告） | A4 |
| `05_convert_all.bat` | `05_convert_all.py` | `convert-all`（批量双轨 HDF5） | A5 |
| `06_plot_qa.bat` | `06_plot_qa.py` | `plot-all`（批量 QA 出图） | ⑥ |
| `08_identify.bat` | `08_identify.py` | `identify`（声明 vs 内容 全量比对） | B2 |
| `09_infer_unknown.bat` | `09_infer_unknown.py` | `infer-unknown`（零先验反演） | B1 |
| `10_prune_reports.bat` | —（无 py 包装，bat 直调 cli） | `prune-reports`（每类报告只留最新一批） | ① |
| `git_publish.bat` | `07_gitee_publish.py` | Gitee 私有仓库创建 + 推送（非 cli 子命令） | ⑦ |
| `run_all.bat` | — | 一键全流程 10 步：extract-docs → inventory → audit → zeff → identify → convert-all → plot-all → infer-unknown → prune-reports → `eosop_pro\test\run_all.py` | 全部 |

## 模块（py 清单）

### 薄包装（调用 cli.main）
`01_extract_docs.py`、`02_inventory.py`、`03_parse_declared.py`、
`04_zeff_inventory.py`、`05_convert_all.py`、`06_plot_qa.py`、`08_identify.py`、
`09_infer_unknown.py` —— 同构模板：`_ROOT = Path(__file__).resolve().parents[2]`
插入 sys.path → `from eosop_pro.pipeline.cli import main` →
`main([["<子命令>"]])`。其中 `03_parse_declared.py` 与 `03_audit_sweep.py` 都对应
阶段 A：前者走 cli 的 `audit` 子命令，后者自带参数直调 batch。

### 03_audit_sweep.py
阶段 A 收官审计薄包装（**唯一自带 argparse 的包装**）：`--multigroup`（额外解析
LEDCOP 多群段，慢）/ `--limit N` / `--outdir` / `--matter-dir`，调
`batch.audit_sweep` 后按闸口 `r["pass"]` 退出（闸口：已解析 + 已跳过 == 样本数，
error/count_mismatch 清单可逐条定性）。产出 `audit_all.<ts>.{csv,json,md}`。

### 07_gitee_publish.py
Gitee 私有仓库创建 + 推送（**凭据只读**）。`--check` / `--ensure-repo` /
`--push` / 无参全流程。凭据来源（只读，绝不修改）：`~/.physimx/flash/
credentials.enc` + `.secret_key`（Fernet，键 `gitee`）或环境变量
`GITEE_TOKEN`/`GITEE_LOGIN`（优先级更高，便于 CI）。三条安全纪律写进代码：
① 只读凭据（永不调用 set/delete/_save）；② token 不进磁盘（放命令行 URL，
推完重置干净 remote 并断言 `.git/config` 无 token）；③ token 不进日志（输出
一律经 mask）。

用法示例：
```bash
# 等价的三种跑法（以审计为例）
scripts\03_audit.bat                          # 双击
python scripts/03_audit_sweep.py --limit 40   # 薄包装直跑
python -m eosop_pro.pipeline.cli audit --limit 40   # cli 直跑（推荐）
```

> ✅ 已核实（2026-11-14）：全部 10 个步骤 bat 内部命令行已统一为
> `python -m eosop_pro.pipeline.cli <子命令>`（重组时同步修正），
> 与 py 薄包装、cli 直跑三种跑法路径一致。
