# SNB 非局域电子热传导 —— FLASH 场景设置方法（可分享文档集）

本目录是 SNB（Schurtz–Nicolaï–Busquet 多群非局域电子热传导）FLASH 场景的
**核心处理模块** —— 场景生成、F90 代码复制、运行、分析、分享前检查均以本目录为根。

> ⚠️ **本目录是两层混合体**：可分享层（文档/脚本）+ **本地保留层**（F90 实现包，
> 存在但不入库）。分层细节见 `docs/07_核心模块与工具.md`。

> **一句话**：把 FLASH 的电子热传导从「限流 Spitzer-Härm」换成「多群非局域」，
> 需要一套**场景覆盖 F90 + 特定 par 配置 + 特定网格/时间积分设置**。本文档集
> 只描述**方法与参数**，**不包含也不描述 SNB 的 F90 实现**。

---

## 1. 目录结构

```
SNB/                                     ← 核心模块根
├── README.md                            ← 总览与分享规则（本文）        [分享]
├── .gitignore                           ← 本地保留层排除               [分享]
├── manifest.json                        ← 源文件清单 + sha256          [分享]
├── docs/
│   ├── 01_设置方法.md            ← ★ 参数清单、开关、几何/网格/时间设置
│   ├── 02_端到端流程.md          ← 从零到出图的完整工作流
│   ├── 03_编译与依赖.md          ← 编译要求、必需补丁（只描述，不含源码）
│   ├── 04_辐射开关.md            ← par 三开关方法 + SNB 侧驱动要求（radON）
│   ├── 05_坑位清单.md            ← 实测坑位与规避（P2/P5/P23 关键）
│   ├── 06_分享与保密规则.md      ← 可分享 / 不可分享清单
│   ├── 07_核心模块与工具.md      ← ★ 模块结构 + 工作流 + 薄驱动模式
│   ├── 08_故障案例_SNB崩塌.md      ← ★★ 错误说明：dtmax 崩塌完整复盘
│   └── 09_原始参考实现与当前设置.md ← ★★ 作者原版 par 全设置 + 我们改了什么/为什么
├── scripts/                                                           [分享]
│   ├── snb_params.py            ← 参数参考 + par 关键设置校验器
│   ├── check_share_safety.py    ← ★ 提交前强制自检（三闸门 + 内容黑名单扫描）
│   ├── generate/
│   │   ├── import_sources.py    ← 源文件导入/重建（只复制，不含 F90 文本）
│   │   └── gen_scene.py         ← ★ 场景生成（F90 复制 + par 生成 + 受控自检）
│   ├── run/
│   │   └── run_scene.py         ← ★ 运行驱动（部署→setup→make→run→收集+健康检查）
│   └── analysis/
│       ├── compare_4way.py      ← ★ 四腿 2×2 对比图 + 定量表
│       └── chk_probe.py         ← ★ chk 健康检查（dtmax 钳位判据）
├── source/                                                            [本地保留]
│   ├── snb_package/             ← 作者 SNB 实现包（9 覆盖 F90 + Config/Makefile
│   │                               + Simulation_*.F90）
│   ├── stock_sh/                ← 限流 Spitzer-Härm 参考版（对照腿用）
│   ├── tables/                  ← EOS/opacity 表（*.cn4）
│   └── example/flash.par        ← 作者示例 par（仅参考）
├── variants/                  ← F90 诊断变体                          [本地保留]
└── tools_local/               ← 会写入 F90 的脚本                     [本地保留]
```

**两层说明**：`[分享]` = 入库；`[本地保留]` = 存在但不入库（F90 实现包，
受分享规则与 FLASH License §3 约束）。

**本地保留、不入库**（分享规则见 `docs/06`）：

- `source/` — SNB 实现 F90 源码 + 参考版 + 表 + 示例 par
- `variants/` — F90 诊断变体
- `tools_local/` — **会写入 F90** 的脚本（脚本即等价于源码）

---

## 2. 快速上手（四条命令）

```bash
cd <flash 包目录>
PY=python
M=flash/scenarios/private/SNB/SNB

# ① 导入/重建源文件（新环境一次性；只复制，不含 F90 文本）
$PY $M/scripts/generate/import_sources.py \
      --from <作者SNB实现包目录> --also-stock <限流SH参考版目录>

# ② 生成诊断变体（可选，产物在 variants/）
$PY $M/tools_local/make_variants.py

# ③ 生成场景（F90 复制 + par 生成 + 受控性自检）
$PY $M/scripts/generate/gen_scene.py --out <场景目录>
#    可选: --legs snb,flsh  --radiation on|off|both   ★ radiation 默认 on
#          --driver-variant radon    ★ SNB 腿推荐(默认), 见 §3
#          --ele-fl-mode fl_none     ★ 默认 fl_none(项目约定; 该键在 SNB 上是 no-op)
#          --therm-variant limiter  --flsh-mode native|stock
#          --nxb 128 --iprocs 8 --dtmax 2.0e-14   ★★ dtmax 必须 2e-14
#          --verify-keys-against <作者示例 par>   ★ 键集差分校验

# ④ 运行 + 提交前自检
$PY $M/scripts/run/run_scene.py --scene <场景目录>
#    可选: --par <腿>_radon.par  --tag radon      (2×2 矩阵下选腿)
#          --species a,b,c  --tables T1.cn4,T2.cn4   ★ 物种/表清单须与场景一致
#          --pulse-sections 300               ★ 多段激光(如 82 段)必需
#          --skip-setup --skip-make           ⚠ 见下方"构建指纹"
#   ★★ 构建指纹: objdir 名固定 → 不同场景**复用同一 objdir**; 沿用旧 flash4
#      会把别的场景的二进制当成当前结果(静默错误)。故脚本以 flash_input/ 全文件
#      + setup 参数的 SHA256 记入 objdir; **不一致或缺 flash4 → 无视 --skip-* 强制重建**。
$PY $M/scripts/check_share_safety.py

# ⑤ 健康检查（★ 判 dtmax 是否生效 —— 依据 chk 的 dt 实测值）
$PY $M/scripts/analysis/chk_probe.py --dir <含chk目录> --expect-dtmax 2e-14
```

参数速查 / 校验自己的 par：
```bash
$PY $M/scripts/snb_params.py --show
$PY $M/scripts/snb_params.py --check <你的.par>
```

详见 `docs/07_核心模块与工具.md`（模块结构 + 工具职责 + 薄驱动模式）。

---

## 3. SNB 场景的五个关键设置（速查）

| 维度 | 设置 | 备注 |
|---|---|---|
| **求解器** | `+uhd3t`（3 温度）+ `+mtmmmt` + `+laser` + `+mgd mgd_meshgroups=N` | 3T 是 SNB 的前提 |
| **网格** | **必须 `+ug` 均匀网格** | SNB 跨平均自由程积分，AMR 粗细界面会破缺 |
| **限流器** | `diff_eleFlMode = "fl_none"`（**默认**），`diff_eleFlCoef = 0.06` | ★ 2026-09-12 实测更正：该键在 **SNB 电子路径上是 no-op**（各向同性电子分支的限流器调用被注释），`fl_none` 与 `fl_harmonic` **逐位相同**。**保护 SNB 守恒的不是限流器**，是多群非局域公式本身。见坑位 P1 更正块 |
| ★★ **时间积分** | **`dtmax = 2.0e-14`** | `2e-12` 会**非物理崩塌**（ρmax 12.11→0.26）。<br>**判据：看 chk 的 `dt` 实测值，不看 par 文本** —— 见 `docs/08` |
| ★ **驱动（辐射）** | SNB 腿用 **`--driver-variant radon`** | 作者原版注释了 `call RadTrans` → 辐射永不推进、par 三开关失效。见 `docs/04` §2 |
| **辐射群数** | `rt_mgdNumGroups` 必须等于 setup 的 `mgd_meshgroups` | 不一致直接报错 |
| **EOS/opacity 表** | 全体物种**群数必须一致** | 不一致会 abort |

> ★ 上述"时间积分"与"驱动"是**并列前提**：缺任一项，2×2 辐射矩阵都会失真。

详见 `docs/01_设置方法.md`、`docs/08_故障案例_SNB崩塌.md`。

---

## 4. 分享规则（**必读**）

### 两层设计（本模块特有）

| 层 | 目录 | 入库 |
|---|---|---|
| 可分享层 | `README.md` `docs/` `scripts/` `manifest.json` | ✅ |
| **本地保留层** | `source/` `variants/` `tools_local/` | ❌ |

> `tools_local/` 里是 `.py`（扩展名在放行列表内），但**会写入 F90** →
> 必须**整目录**排除。只按扩展名放行/拦截是挡不住的，
> 这就是检查器里"**目录闸门**"与"类型/内容闸门"并列的原因。

| 类别 | 可分享 | 说明 |
|---|---|---|
| SNB 场景 **par**（参数配置） | ✅ | 参数本身是方法，不是源码 |
| 场景 **Python 驱动/分析/绘图脚本** | ✅ | 只要**不写入/内嵌 F90 源码** |
| **说明文档 / 流程文档** | ✅ | 描述方法与参数即可 |
| **F90 源码**（SNB 覆盖文件及其变体） | ❌ | 见 `docs/06` |
| **会生成 F90 的 py 脚本** | ❌ | 脚本本身即等价于源码 |
| **引用算法片段的文档** | ❌ | 逐字引用等同分享源码 |
| 凭据 / 密钥 / 账号 | ❌ | 永不入库 |

**执行方式**：
1. `.gitignore` 已配置白名单（只放行 `*.py` / `*.md` / `*.par` / `Config` 等非源码类型），
   并对 `**/*.F90` 施加全局忽略；
2. 每次提交前运行 `scripts/check_share_safety.py`（它用 `git add -n` 干跑 + 内容扫描双重校验）。

---

## 5. 相关场景索引

| 场景 | 用途 | 建法 |
|---|---|---|
| `Test/t001` | SNB 首个跑通场景（谱 + 编译基线） | 早期自带脚本 |
| `Test/t002` | SNB vs FL-SH 受控对比 + `+ug` 分辨率矩阵 | 早期自带脚本 |
| `Test/t003` | 复现作者示例 `SNB_1D_laser`；源码级缺陷诊断 | 早期自带脚本 |
| `Test/t004` | 辐射开/关 2×2 矩阵（**首次成功**，含复现验证记录） | 早期自带脚本 |
| `Test/t005` | 辐射 2×2 的**薄驱动**版本 | ⚠ **失败案例**：`dtmax` 误用 `2e-12` → SNB 崩塌（见 `docs/08`） |
| **`Test/t006`** | **辐射 2×2，等价于 t004，用本模块从零搭建** | ★ **薄驱动**（推荐范式，见 `docs/07` §7） |

**tracer 家族里基于本模块的场景**（几何/材料来自 `tracer/`，热传导换成 SNB）：

| 场景 | 用途 | 备注 |
|---|---|---|
| `tracer/SNB/SNBOneCH_ml` | OneCH_ml 几何/材料 + SNB（8 标记多层） | 与 `tracer/OneCH_ml` 构成 local vs nonlocal 对照 |
| **`tracer/SNB/SNBOneCH`** | 同上但**只用 cham+targ 两标记**；`+ug` 2048 格 | ★ 2026-09-12 新建；tmax=1.6 ns；对比图 `plot_compare_onech.py` |

**建议**：新场景一律照 `t006` 的薄驱动模式建（`run_t006.py` 为模板），
不再复制 F90、不重新实现算法。

场景产出目录（`Test/t00*/`）与本文档集互补：前者是**实验记录**，后者是**可复用的方法**。
