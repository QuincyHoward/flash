# 参考: SNB 场景端到端流程（setup → 编译 → 运行 → 分析 → 分享）

> 从  §5 下沉（2026-09-12），为控制 SKILL.md 体量。

---

## 5. 端到端流程

```
[0] 前置检查 → [1] 准备单元 → [2] setup → [3] make
    → [4] 短时验证 tmax≈1e-11（必做）→ [5] 正式跑 dtmax=2e-14
    → [6] 收集（先校验后删）→ [7] ★ dt 健康检查 → [8] 绘图/定量 → [9] 分享前自检
```

**短时验证判据**（全满足才算过）：
`exiting: reached max SimTime` / chk ≥ 2 帧 / 步长未坍缩到 `dtmin` /
**无** `Negative 3T internal energy` / `eos_nr WARN` 很少。

**★ 步骤 [7]：dt 健康检查（必做，独立复核 `dtmax`）**

```bash
# 模块自带工具；退出码 0=健康 1=异常 2=无法判定
$PY <SNB>/scripts/analysis/chk_probe.py \
    --dir <含chk目录> --expect-dtmax 2e-14 --brief
```

`run_scene.py` 也内建了该检查（每腿结束自动跑）。三种 `dt` 形态：

| `dt` 形态 | 结论 |
|---|---|
| 全程 = 2.000e-14（钉死） | ✓ `dtmax` 生效 |
| 单调增长（2.88e-14 → 4.56e-14） | ✗ 未生效 → 即将/已经崩塌 |
| 随 `dtmin` 坍缩 | ✗ 早期瞬态失稳 |

**数据源优先 chk**：71 键 vs plt ~25 键，float64，**不受 `plot_var` 12 项限制**。
`nele` 统一**离线推导** `Ye·6.02e23·ρ`（避免两腿口径不一致）。

**收集铁律**：**先校验后删**。以本地 chk 帧数 > 0 为成功判据；
不要写 `cp ... 2>/dev/null; rm -f ...`（复制失败会**静默丢数据**）。

### 5b. ★ 新场景一律用「薄驱动」模式

**不要**在新场景里重新实现算法、复制 F90 或重写参数源。
新场景只应有**一个自有文件**：`run_tNNN.py`，它编排核心模块的四个脚本：

```
t006/run_t006.py
  ├─ generate : SNB/SNB/scripts/generate/gen_scene.py
  ├─ run      : SNB/SNB/scripts/run/run_scene.py
  ├─ check    : SNB/SNB/scripts/analysis/chk_probe.py
  └─ plot     : SNB/SNB/scripts/analysis/compare_4way.py
```

**薄驱动必备要素**：

| 要素 | 说明 |
|---|---|
| 核心模块定位 | 向上逐级找「名为 `SNB` 且含 `scripts/`+`source/` 的目录」，**不写死层数**（场景可整体搬迁） |
| **前置护栏** | 把血泪教训做成**硬拒绝**：`dtmax > 1e-13` 直接退出；`--driver-variant != radon` 直接退出。错误信息里带**具体后果数字**（ρmax 12.11→0.26），比"请勿修改"有效 |
| `--stage all\|generate\|run\|check\|plot` | 分步执行，便于排错与复用 |
| `--smoke` | 一键短时验证 |
| 每侧只 setup/make 一次 | 首腿部署编译，次腿 `--skip-deploy --skip-setup --skip-make`（只换 par） |
| 分层输出 | `scene/`（生成物，可删重建）\| `images/` \| `results/` \| `logs/` |

**参考实现**：`SNBtest/Test/t006/run_t006.py`（配套 `README.md` + `docs/构建说明.md`）。
它等价于 t004，但用核心模块从零搭建 —— 可作为新场景的模板直接复制改名。

> **演进注记**：t004 用早期自带脚本（继承 t003 参数源）；t005 是薄驱动的第一次尝试但
> 因 `dtmax` 误用而失败；**t006 是薄驱动的成功范式**。三者关系与差异见
> `t006/docs/构建说明.md`。

---

### 5c. ★★ 腿间比对的两条护栏（2026-09-12 血泪，缺一不可）

做"改一个键 → 两腿对比"这类单变量 A/B 时，必须在比对**之前**加两道门：

1. **帧按时间戳配对，不能按帧序号。** chk 间隔是纯 IO 参数，两腿可以不同
   （短测常加密到 `1e-12`）。按序号配对会把**不同时刻**对在一起 ——
   实测曾把 `t=1e-12` 与 `t=1e-11` 相比，得出 `tele` 相对差 **0.97** 的
   **完全虚假的"存在差异"结论**。
   **暴露它的线索 = 输出里的「帧时间戳最大偏移」**（当时为 9e-12 s）。
2. **比对前先做 par 键级差分（受控性检查）。** 两腿的配置差异必须**恰好**是
   声明允许的那几个键，否则**拒绝比对并报错**。
   实测曾拿 `sim_snb/smoke_radon` 当基线，而那份 par **缺 `gr_hypreUseFloor`**
   （= 修复前的数据）→ 一次改了两个变量 → 同样得到虚假差异。

> ⇒ **时间戳**证明"比的是同一时刻"，**键级差分**证明"基线干净"。缺一不可。
>
> 另：`dt` 钳位判据只能查"步长是否用了 `dtmax`"；**结果是否健康**必须另查
> ρmax 走势与守恒（判据 A 与 B）。
>
> **参考实现**：`SNBtest/Test/t006/flnone_test/run_flnone_test.py` ——
> `_compare_dirs`（按时间戳配对）＋ `_par_pair_guard`（受控性检查）
> ＋ `_classify`（按整体最大相对差分量级分类，避免"非零即失败"的粗糙判读）。

