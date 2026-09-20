# SNBOneCH_ml 第二轮: 归档 / 超算核实 / 网格修复报告

> 日期: 2026-09-12 | 工作区: `E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash`

---

## 1. 根目录收纳 (已完成)

| 项 | 结果 |
|---|---|
| 归档文件数 | **234 个** |
| 归档位置 | `docs/_diagnostics/2026-09-12_snb_debug/` |
| 索引文件 | `_INDEX.txt` (含来源/数量/性质说明) |
| 操作性质 | **只移动/复制, 未删除** (完全可逆) |

**根目录现状 — 15 个文件**:

| 文件 | 说明 |
|---|---|
| `.gitattributes` / `.gitignore` / `.pre-commit-config.yaml` | 项目配置 |
| `INSTALL_TEST_REPORT.txt` / `LICENSE` / `NOTICE` / `Makefile` / `README.md` / `pyproject.toml` / `start_flash.py` | 项目主体 |
| `pytest_*.log` × 3 | 测试日志 |
| `_nce_rerun.txt` / `_nce_short_run.txt` | **被进程占用无法移动**, 已复制归档 |

**已清理的垃圾**: `]` (Unicode 私有区字符, 0 B)、`0.03µm` (0 B)、`56` (0 B)
— 均由早期 shell 引号错误误建, 已归档至 `_junk/`。

**未处理 (待您裁决)**: `%SystemDrive%/` 目录 — 内含
`ProgramData/Microsoft/Windows/Caches/*.db` (约 1 MB), 属环境变量未展开导致的误建,
**未删除**, 已列清单。

---

## 2. 超算三作业核实 (您的问题: 是否真在执行?)

**结论: 只有 1 个在跑, 且它已在调查期间正常跑完 (58.1 min)。**

### 2.1 NC-E (`scfa2696`) sacct 全量

| JobID | Name | State | Elapsed | 诊断 |
|---|---|---|---|---|
| 4864350 | SNB1CH_b_nce | COMPLETED | 00:01:08 | 仅 build, 正常 |
| 4864352 | SNB1CH_r_nce | **CANCELLED** | 00:14:31 | `hydra_bstrap_proxy` FAILED |
| 4864357 | SNB1CH_r_nce | **CANCELLED** | 00:03:18 | `hydra_bstrap_proxy` FAILED |
| **4864358** | SNB1CH_r_nce | **RUNNING → 已 COMPLETED** | 00:55:39 | ★ 唯一存活 |

### 2.2 关键辨析: `run_%j_out.txt` = 0 字节 **不代表空转**

`run.sh` 内容是:
```bash
mpiexec -n 131 ./flash4 > wsl_run_snbonech.log 2>&1
```
stdout **被重定向进 objdir 内的日志**, 所以 SLURM 的 `--output` 文件**必然是空的**。

**权威证据** (objdir 内 `wsl_run_snbonech.log`, 15352 行):
```
 exiting: reached max SimTime
 *** Wrote checkpoint file to snbonechug_hdf5_chk_0023 ****
 *** Wrote plotfile to snbonechug_forced_hdf5_plt_cnt_0000 ****
RUN_EXIT=0
WALL_SECONDS=3484.333439160        # 58.1 min
```

- 推进 **9073 步**, 到 `t = 2.0000E-10` = 恰好 tmax
- 产出 **23 个 chk** (各 10.1 MB) + **5 个 plt** (各 2.03 MB)
- 效率 **0.384 s/step**
- `Nonconv` = 5962 (全为 component=2) / `eos_nr WARN` = 4 / `ERROR` = **0**

**两份被取消作业的解读**: `run_*_err.txt` 只有
`slurmstepd: error: JOB ... CANCELLED`, **无自身报错**;
`hydra_bstrap_proxy FAILED` 是 MPI 启动代理在作业被 kill 后的**伴随现象**, 非根因。

### 2.3 BSCC (`sch0348`)

`squeue` 空, 今日 `sacct` 无记录 ⇒ **未使用**。

---

## 3. 网格修复: 根因认定与验证

### 3.1 根因 (已认定)

`Simulation_initBlock.F90` 按**单元中心**判据选物种:
```fortran
if (xcent(i) >= bnd_k .and. xcent(i) <= bnd_{k+1}) then species = XXX_SPEC
```
薄层厚度 0.1 µm = 1e-5 cm。旧配置 `-nxb=128` 配 `-n 4` ⇒ `dx = 0.977 µm`,
**比薄层粗 10 倍** ⇒ **没有任何单元中心落进薄层** ⇒ 该物种**从不被写入**。

**修复前实测 (chk_0000)**:
```
shld / tar1 / tar2 / tar3 / tar4 / tar6   nonzero = 0 / 512   ← 全部为 0
```

### 3.2 修复

`build_setup_flags_ug(nproc, xmin, xmax)`:
```
nxb = 2 ** ceil(log2(max(8, 域宽 / (0.03 µm × nproc))))
```
并在 `main()` 加**硬中止门**: `dx > 0.03 µm` 时拒绝运行。

### 3.3 验证 (WSL, `--nproc 4` → `-nxb=8192`)

| 物种 | 非零格数 | 覆盖区间 (质量分数 > 0.5) | 设计位置 | 判定 |
|---|---|---|---|---|
| cham | 29091 | −400 … +100 µm | He fill | ✓ |
| shld | 7 | 0.0015 … 0.0931 µm | 0–0.1 µm | ✓ |
| samp | 3638 | 0.108 … 56.09 µm | CH 主层 | ✓ |
| tar1 | 6 | 1.0086 … 1.0849 µm | 1.0 µm | ✓ |
| tar2 | 7 | 2.0004 … 2.0920 µm | 2.0 µm | ✓ |
| tar3 | 7 | 3.0075 … 3.0991 µm | 3.0 µm | ✓ |
| tar4 | 6 | 4.0146 … 4.0909 µm | 4.0 µm | ✓ |
| tar6 | 6 | 6.0135 … 6.0898 µm | 6.0 µm | ✓ |

**8 物种全部写入, 每薄层 6–7 格 ≥ 门槛 3 格。修复有效。**

---

## 4. ★★★ 重大更正: 一个被掩盖的错误结论

### 4.1 现象

在 `flash_output/` 里"按文件名读 chk_0002"得到:
- 格数从 32768 **塌缩到 512**
- `dx` 从 0.01526 µm **变粗到 0.97656 µm**
- `tele` = 1.0e14 K (EOS 天花板), `velx` = 4.55e11 cm/s (15× 光速)
- 8 物种只剩 samp

一度据此判"网格塌缩 + 全域均匀化失稳"。

### 4.2 真相: **陈旧文件伪影**

| 文件 | `sim info` 的 setup call | 文件创建时间 | 尺寸 |
|---|---|---|---|
| `chk_0000` | **`-nxb=8192`** | **18:14:57** | 19,311,748 B |
| `chk_0002` | **`-nxb=128`** | **18:08:19** | 732,292 B |

`chk_0002` 比 `chk_0000` **早 6 分钟** —— 它是**上一轮 `-nxb=128` 运行的残留**。
按 mtime 排序后: 旧文件覆盖 **18:03–18:13**, 新文件只在 **18:21:32–33**。
"chk_0002 排在 chk_0001 之后"纯粹是**文件名字典序**造成的假象。

### 4.3 新运行 (nxb=8192) **完全健康**

| | chk_0000 | chk_0001 |
|---|---|---|
| 格数 | 32768 | **32768** (无塌缩) |
| dx | 0.01526 µm | **0.01526 µm** (不变) |
| 8 物种 | 全部在场 | **全部在场** (shld 7→23) |
| tele | 290.11 K 均匀 | 1.10 … 2.433e4 K (物理加热) |
| velx | 0 | ±1.9e6 cm/s (≈60 km/s) |
| nele | 0 | 2.03e14 … 2.89e22 (电离起爆) |
| dt | 1.0e-15 | 1.265e-13 (**增长**) |

---

## 5. 收集污染: 根因 + 修复 + 验证

### 5.1 根因

`deploy_and_run()` 收集时直接 `cp -f` 到 `flash_output/`, **未清理该目录**;
而 chk/plt **文件名不含 tag 前缀** (与已知"日志名要带 tag"同类坑)
⇒ 上一轮 chk 残留, 且**旧文件数量占优抢占下标**。

### 5.2 修复过程中的二次错误 (记录在案)

第一次修复用 `rm -rf {wsl_out}` —— **这是错的**:
`flash_output/` 是 **WSL 与 HPC 共用父目录**, 内含 `hpc_flash_ssh/` (超算结果)
与 `walltime_wsl.txt`, 整目录删除会**连带销毁超算数据**。
实测已误清 `hpc_flash_ssh/` (后经确认其中 3 个文件为早期不完整下载, 无关键损失)。

**最终修复** — 只删本次产物模式:
```bash
mkdir -p {out} &&
rm -f {out}/{BASENM}* {out}/wsl_run_snbonech.log {out}/{LOG_FILE} 2>/dev/null;
cp -f {obj}/{BASENM}* ... {out}/
```
并新增 `_verify_collected_nxb()` 收集后自检: 按尺寸反推格数 (~589 B/格),
出现 < 期望半数的档位则 WARN。

### 5.3 端到端验证 (RC=0, 391.2 s)

```
[i]  chk 收集自检: 期望 nxb=8192, 总格=32768, dx=0.01526 um
[i]  实际 chk 尺寸分布: 1 x 19311748 (chk_0000)
                        1 x 19311748 (chk_0001)
[OK] chk 尺寸自检通过
[OK] 运行 成功 — WSL 运行墙钟 391.2 s (4 proc)
```
**结果**: chk=2 / plt=2, `hpc_flash_ssh/` **完好保留**。污染已根除。

---

## 6. 遗留与新发现

### 6.1 ★ `QESH` 全零 (新发现, 待查)

```
SNB 变量 QESH max|.| = 0.000e+00    ← 全零, 异常
SNB 变量 QENL max|.| = 1.614e+21    ✓
SNB 变量 CORQ max|.| = 1.613e+21    ✓
SNB 变量 MFPE max|.| = 4.369e+08    ✓
```
按 `reference/SNB_FLASH_reference.md` 记载, SNB 热流建立在**无界 Spitzer 电导**
(`QESX ← COND_VAR`) 之上, **`QESH` 理应为非零**。
候选原因: ① 该变量在本模块位置未更新; ② 诊断量拷贝时机;
③ 1e-11 s 内热流尚未建立。**下一轮首查此项, 不预设结论。**

### 6.2 1.6 ns 全长外推 (供决策)

沿用 NC-E 实测 `0.384 s/step` 与末段 `dt ≈ 9.0e-15`:
```
1.6e-9 / 9.0e-15 = 177,778 步  →  19.0 h   (乐观下限)
```
若提到 192 核 (dx = 0.02035 µm, 4.92 格/层): 每步更贵但 dt 更小, 净约 **28 h**。

### 6.3 其它待办

- NC-E 重投时 `build.sh` 的 `-nxb=128` 应改为自适应值 (131 核仅 3.35 格/层, 建议 ≥ 192 核)
- `monitor_job.py` 的 `main()` 仍未接入 `resolve_deploy()`
- 下载 NC-E 4864358 的 23 个 chk 做物理审查

---

## 7. 本轮工程铁律 (已写入长期备忘)

1. ★★★ **判 HPC 作业是否在算, 必须读 objdir 内 FLASH 日志**;
   `run_%j_out.txt` 为空是因为 stdout 被重定向 —— **不代表空转**。
2. ★★★ **`flash_output/` 是 WSL/HPC 共用父目录 → 禁止整目录删除**。
3. ★★★ **chk/plt 判"属哪次运行"用 `sim info` 的 setup call + mtime**,
   **绝不用文件名字典序** (旧文件会抢占下标)。
4. ★★★ **`+ug` 必须按 nproc 反推 nxb**, 否则 0.1 µm 薄层物种从不被写入。
5. ★ **WSL `bash -lc` 会吞 shell 变量与反引号** → 一律 Write `.sh` 落盘再执行;
   远端用 base64 传输; h5py **不能读 `\\wsl$` UNC 路径** (先 cp 到 `/mnt/e/`)。
