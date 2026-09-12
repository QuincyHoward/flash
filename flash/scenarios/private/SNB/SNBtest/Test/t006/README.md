# t006 —— 辐射开关 2×2 矩阵（薄驱动，调用 `SNB/SNB` 核心模块从零搭建）

**t006 与 t004 是同一件事**：同样的几何/激光/材料/网格/时间积分、同样的四腿矩阵。
区别只在**搭建方式**：

| | t004 | **t006** |
|---|---|---|
| 建法 | 早期自带脚本（`common/t004_common.py` + 自有 F90 复制逻辑） | ★ **薄驱动**，全部调用 `SNB/SNB` 核心模块 |
| 自有文件 | 参数源 + 生成器 + 运行器 + 绘图 + 大量临时脚本 | **仅 `run_t006.py`** |
| 依赖 `SNBtest/` | 是（继承 `t003/common`） | **否**（自包含） |
| 可否整体搬迁 | 需连带 t003 | **可**（核心模块位置自动搜索） |

**验证目标**：若本薄驱动能一次跑通四腿、受控性自检通过、且结果与 t004 数值一致，
则说明 `SNB/SNB` 核心模块**已可独立复用**，`SNBtest/` 可以安全删除。

---

## 1. 三条并列前提（缺一不可）

> ★★★ **2026-09-12 更正**：t006 首轮运行**仍然崩塌**（`dt` 已正确钳位 2e-14）。
> 经单变量 A/B 实测，真因是 **`gr_hypreUseFloor` 未写入 par**（FLASH 默认 `.true.`）。
> 详见 `SNB/docs/08_故障案例_SNB崩塌.md` §0。**前提由两条更正为三条。**

| # | 前提 | 违反后果 | 把关位置 |
|---|---|---|---|
| **1** | **`gr_hypreUseFloor = .false.`** | ★★★ **真正主因**。FLASH 默认 `.true.` → HYPRE 隐式扩散解失真 → 过度压缩 → ρmax 冲高后**崩塌**（12.1 → 0.26、质量守恒破裂） | `snb_params.py` 写入 + `gen_scene.py` 的 `NUMERIC_CRITICAL_KEYS` **硬校验** |
| **2** | **`dtmax = 2.0e-14`** | `dt` 从 2e-14 自由增长到 4.6e-14 → 越过稳定阈值（**必要条件，非充分条件**） | `preflight()` 拒绝 `dtmax > 1e-13` |
| **3** | **SNB 腿 `--driver-variant radon`** | 作者原版把两处 `call RadTrans` 注释 → 辐射**永不推进**、par 三开关失效（`trad` 差 1700×）→ 2×2 矩阵失去意义 | `preflight()` 拒绝非 `radon` |

> ★ **两条判据铁律**
> 1. `dtmax` 是否生效**不能看 par 文本**（会被命令行覆写），
>    必须读 chk 里 `real scalars` 的 `dt` 实测值。
> 2. **`dt` 钳位正确 ≠ 结果正确** —— 还必须检查 **ρmax 走势**与**总质量守恒**。
>    t006 曾出现 `dt` 全程钳位 2.000e-14 却依然崩塌的情形（即前提 1 缺失）。
> 3. 配置溯源最可靠的手段：与参考日志做**参数回显差分**。

**两道护栏实测有效**：

```
$ python run_t006.py --stage generate --dtmax 2e-12
  [X] dtmax=2.000e-12 超过安全护栏 1.0e-13。
      ★ 本场景必须 dtmax=2.000e-14，否则 SNB 腿会非物理崩塌
        (t005 实测: dt 增长到 4.6e-14 → ρmax 12.11→0.26, 质量守恒破裂)
      → exit 2

$ python run_t006.py --stage generate --driver-variant none
  [X] driver-variant=none 不可用于本场景。
      ★ SNB 腿必须用 radon: 作者原版把 call RadTrans 注释了
        → 辐射永不推进、par 三开关失效 → 2×2 矩阵失去意义
      → exit 2
```

---

## 2. 四腿矩阵（受控）

| 腿 | 树 | 驱动 | 热传导源 | 辐射三开关 |
|---|---|---|---|---|
| FL-SH radON  | 标准 FLASH | 树原生（本就调用 `RadTrans`） | 树原生 | `.true.` ×3 |
| FL-SH radOFF | 标准 FLASH | 树原生 | 树原生 | `.false.` ×3 |
| SNB radON    | FLASHSNB   | **radON 变体** | 作者 SNB 版 | `.true.` ×3 |
| SNB radOFF   | FLASHSNB   | **radON 变体**（与上行**逐字节同一份**） | 作者 SNB 版 | `.false.` ×3 |

**受控性由生成器自动断言**（`gen_scene.py --radiation both`）：

```
[同腿 snb]  snb_radon.par vs snb_radoff.par: 差异键
            ['basenm','log_file','rt_useMGD','useOpacity','useRadTrans']
[同腿 flsh] flsh_radon.par vs flsh_radoff.par: 同上
[跨腿 snb vs flsh] 逐字节相同 8 个; 其余为腿特有覆盖件与 par
→ 受控性自检通过 ✓（同腿两状态只差辐射开关；跨腿只差腿标识）
```

**效率设计**：辐射是纯 par 开关 → **同侧两腿共用 objdir 与二进制**，
每侧只 deploy/setup/make 一次，换 par 跑两次。

---

## 3. 目录结构

```
t006/
├── run_t006.py                 ← ★ 四腿主流程薄驱动
├── README.md                   ← 本文
├── flnone_test/                ← ★ fl_none 限流模式可行性验证（子实验，自成一包）
│   ├── run_flnone_test.py      ← 驱动: par 生成 / 运行 / 逐帧比对 / 编排
│   ├── plot_5leg.py            ← SNB×3 + FL-SH×2 五腿绘图
│   ├── verify_md_images.py     ← md 图片引用校验器（提交前门禁）
│   ├── results/                ← 逐帧比对报告（md + csv）
│   └── logs/
├── scene/                      ← 生成物（F90 + par），可删除重建
│   ├── sim_snb/flash_input/{snb_radon.par, snb_radoff.par, snb_flnone.par,
│   │                        snb_harm_smoke.par, snb_flnone_smoke.par, *.F90, *.cn4}
│   └── sim_flsh/flash_input/{flsh_radon.par, flsh_radoff.par,
│                             flsh_hT_smoke.par, flsh_hF_smoke.par}
│       + flash_output/sim_{snb,flsh}/{radon,radoff,flnone,...}/   ← chk 等输出
├── images/                     ← 对比图（pcolor/ profiles/ ablation/ compare/ flnone5/）
├── results/                    ← 定量表（csv + md）
├── logs/                       ← 生成/运行/绘图日志
└── docs/                       ← 说明文档
    ├── 构建说明.md
    └── 对比_SNB3_SH2.md        ← ★ SNB×3 + FL-SH×2 五腿对比（含图）
```

**分层原则**：`scene/`（生成物，可重建）与 `images/`+`results/`（结论）分开，
`logs/` 保留可追溯性。

> ★ **`flnone_test` 的核心结论**（2026-09-12 实测）：
> `diff_eleFlMode` 在 SNB 电子路径上是 **no-op** ——
> 改成 `"fl_none"` 后六个物理量逐帧最大绝对差**全为 0（逐位相同）**。
> 原因是 `snb_package/diff_advanceTherm.F90` 的各向同性电子分支里
> 限流器调用与 SH 传导解**都被注释**（`:839`/`:847`），且
> `diff_anisoCondForEle=.false.` 不进入各向异性分支。
> 详见 `docs/对比_SNB3_SH2.md` §2 与 `SNB/SNB/docs/05_坑位清单.md` 的 P1 更正块。

---

## 4. 用法

```bash
PY=C:/Users/Administrator/.workbuddy/binaries/python/envs/default/Scripts/python.exe
cd flash/scenarios/private/SNB/SNBtest/Test/t006

$PY run_t006.py                   # 全流程: generate → run → check → plot
$PY run_t006.py --stage generate  # 只生成场景（约 2 s）
$PY run_t006.py --stage run       # 只跑仿真（四腿）
$PY run_t006.py --stage check     # ★ 只做 chk 健康检查（dt 钳位判据）
$PY run_t006.py --stage plot      # 只出图
$PY run_t006.py --smoke           # 短时验证（tmax=1e-11，快速排除配置错误）

# 复用已编译二进制重跑（改 par 后）:
$PY run_t006.py --stage generate
$PY run_t006.py --stage run --skip-setup --skip-make
```

### 4.1 `flnone_test` —— 限流模式可行性验证（独立子实验）

```bash
cd flash/scenarios/private/SNB/SNBtest/Test/t006/flnone_test

$PY run_flnone_test.py --stage prep            # 生成 fl_none par + 键级差分自检
$PY run_flnone_test.py --stage smoke           # ★ 先短时（~15 s）验证可跑通、无异常
$PY run_flnone_test.py --stage smoke-base      # 受控短时基线（fl_harmonic, 同设置）
$PY run_flnone_test.py --stage smoke-compare   # 短时早期判决
$PY run_flnone_test.py --stage full            # ★ 再正常时间（~23 min）
$PY run_flnone_test.py --stage check           # chk 健康检查
$PY run_flnone_test.py --stage compare         # 与基线逐帧逐位比对
$PY run_flnone_test.py --stage sh-hypre-ab     # 附录: SH 侧 gr_hypreUseFloor A/B
$PY run_flnone_test.py --stage plot            # 五腿出图 → images/flnone5/

$PY verify_md_images.py ../docs/对比_SNB3_SH2.md   # 校验 md 图片引用可显示
```

> **两条纪律**（`flnone_test` 内置，避免重蹈覆辙）：
> 1. **比对前先做受控性检查** —— 两腿 par 的差异必须恰好是声明的那几个键，
>    否则拒绝比对（曾因基线 par 缺 `gr_hypreUseFloor` 而得出虚假的"存在差异"）。
> 2. **帧必须按时间戳配对**，不能按序号（chk 间隔是纯 IO 参数，各腿可以不同）。

常用参数：

| 参数 | 默认 | 说明 |
|---|---|---|
| `--dtmax` | **2.0e-14** | ★★ 不可放宽（有护栏） |
| `--driver-variant` | **radon** | ★★ 不可改（有护栏） |
| `--tmax` | 0.8e-9 | 与 t004 一致 |
| `--nxb` / `--iprocs` | 128 / 8 | = 1024 格，dx ≈ 0.293 µm |
| `--chk-dt` | 5e-11 | 0.8 ns / 5e-11 = **17 帧**（与 t004 一致） |
| `--tag` | full | 绘图/输出命名标记 |

---

## 5. 判据与数据源

- **数据源一律用 chk**（71 键、float64）；plt 受 `plot_var` 12 项上限，仅作快检。
- `+ug` 下 chk 布局：`coordinates` 是**块中心**；`node type` 是每块标量恒 = 1
  → **所有块都是叶子块，无需 leaf 过滤**。
- 单位：`K → eV`（/1.1604519e4）；`erg/cm³ → Mbar`（×1e-12）；
  `nele` 按 `Ye·6.02e23·ρ` 离线推导（两腿口径一致）。
- 烧蚀面 `x_a` = ρ 剖面最陡处；`Ṁ_abl = −dM_dense/dt`，取**后 30% 时段**线性拟合。

---

## 6. 已知注意事项

1. **`SNB` 侧必须 `+ug` 均匀网格**，且 `mpiexec -n` 严格等于 `iProcs`。
2. **`rt_mgdNumGroups` 必须等于 setup 的 `mgd_meshgroups`**（此处均为 10）。
3. **生成时务必带 `--verify-keys-against <作者示例 par>`**
   —— 漏掉"看似无关"的边界键会让 SNB 腿失真（详见 `docs/07` §4）。
4. 本场景**不修改核心模块的任何文件**；所有 F90 均从
   `SNB/source/` 与 `SNB/variants/` **复制**而来。
5. 绘图前若改了 `--chk-dt`，帧数会变，剖面图的时间点分布随之改变。
