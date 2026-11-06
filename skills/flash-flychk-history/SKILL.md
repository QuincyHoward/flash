---
name: flash-flychk-history
description: 由 FLASH 1D chk/plt HDF5 输出生成 NIST FLYCHK history 模式上传 zip 的完整工作流（gen_flychk_his 包）：数据源加载、区域选择 DSL、单位换算、聚合、自包含 zip 写出与回读自检。触发词：FLASH 转 FLYCHK、FLYCHK history 输入、gen_flychk_his、flychk 输入 zip、history 模式输入、区域聚合、示踪层。
---

> 最后核对：2026-11-06 · commit 72f6428

# FLASH 数据 → FLYCHK history 输入 zip

## 1. 何时用

要把 FLASH（1D）剖面的时间序列做成 NIST FLYCHK 网站可上传的 **history 模式输入 zip**（每个空间区域一个 zip）时使用。只负责**生成输入**，不涉及 FLYCHK 光谱窗口/重试流程。

## 2. 实现位置（优先复用而非重写）

```
flash/input_gen/gen_flychk_his/
├── units.py      单位换算(K⇄eV 等) + 元素表    config.py    FlychkHisConfig(不可变)
├── sources.py    8 类数据源统一加载 + 合成模型  regions.py   9 类区域 + 字符串 DSL
├── extract.py    聚合注册表 + size 策略         builder.py   表构建/校验
├── zip_writer.py 自包含 zip 写出器 + 回读自检   writer.py    zip/manifest/表/预览
├── preview.py    PPT 级预诊断图                 cli.py       命令行
└── test/         make_test_data.py + run_test.py + pytest 文件
```

## 3. 最短可用路径

```python
from flash.input_gen.gen_flychk_his import generate_history_zip
generate_history_zip(source="run_dir/", element="Ti", region="label:trac=2",
                     output_dir="out/", agg="mass", n_time_max=8, dens_cut=1e-6)
```

```bash
python -m flash.input_gen.gen_flychk_his.cli --demo --out out/   # 合成数据自检
python flash/input_gen/gen_flychk_his/test/run_test.py           # 端到端用例
python -m pytest flash/input_gen/gen_flychk_his/test -q          # 全量测试
```

## 4. FLYCHK history 格式契约（勿改）

zip 成员顺序固定：`runfile.txt` + `history_{el}_Z{z}_input.txt`。

```
z 22 / initial ss / evolve ss / history
opacity file        # 仅当含 size 列
ti file             # 仅当含 ti 列
tr file             # 仅当含 tr 列
history <数据文件名> rho|ne|ni     # 密度列三选一
end
```

数据文件首行为列名（空格分隔），数据行 `%.6e`。**缺密度列 = 数据文件不会被读取**（列为硬错误而非告警）。

## 5. 必守的工程要点（踩过的坑）

1. **发布包必须自包含**：写出由 `zip_writer.HistoryZipWriter` 完成，仅依赖标准库；包内不导入、不搜索任何外部 FLYCHK Python 包（旧版四级解析 + 目录启发式搜索已删除）。与外部包的对拍能力下沉为 `test/cross_check_external.py`（显式 `--flychk-root` 才运行），不是发布依赖。
2. **若仍需调用外部 `FlychkInputGenerator`（对拍脚本中）**：其 `__init__` 会在外部仓库内 mkdir `templates/`/`work/`，必须传 `tempfile.TemporaryDirectory()`，并用 `contextlib.redirect_stdout(io.StringIO())` 静默其日志。
3. **单位是最容易静默出错的地方**：FLASH 原生温度是 **K**，FLYCHK 要 **eV**（÷11604.5181）。若数据本身已是 eV 而没声明 `input_units={"tele":"eV"}`，结果会被钳到 `te_floor`（典型症状：整列 te 恰好 = 1 eV）。发布前核对 te 量级，或依赖内置 K⇄eV 数量级告警（`Snapshot.meta["unit_warnings"]`）。
4. **区域掩码必须逐时间步重算**：否则示踪层不会随烧蚀面移动。
5. **`dens_cut` 要设**：FLASH 本底填充气体会把区域平均拖成无意义的低温低密。
6. **窄层 `size` 会量化跳变**：`size_mode="extent"` 取离散单元覆盖宽度，3~4 个单元的示踪层有一个网格间距的抖动；需平滑用 `size_mode="fixed"` + `size_value=<层厚>` 或 `scale_length_ne|te`。
7. **示踪带在粗网格上会落空**：构造标签带时用 `band_half = max(0.45µm, 0.75·dx)`，并对空带做最近单元兜底。
8. FLASH 变量名 ≤4 字符（`trac` 而非 `matid`）；HDF5 取数用 `FlashDataLoader(compute_derived=False, extraction_mode="h5py")` 只取叶子块。

## 6. 验证（发布前必做）

```bash
python flash/input_gen/gen_flychk_his/test/verify_decoupled.py   # 解耦证明: 封锁 flychk* 导入 → 全量测试
python -m pytest flash/input_gen/gen_flychk_his/test -q
```

自检（默认开启，无需外部包）：`generate(..., self_check=True)` 回读 zip 并逐字符核对，结论写入 manifest 的 `zip_integrity` / `zip_integrity_ok`。

## 7. 分发要点

- 包内无外部 backend、无 `flychk_root`/`FLYCHK_SIM_ROOT`/`allow_fallback` 配置；manifest 的 `backend` 段已改为 `writer` 段（`self_contained: true`）。
- 改完务必跑 `verify_decoupled.py`：它在 `sys.meta_path` 上拦截外部包导入，任何残留依赖都会立刻失败（而非静默回退）。

## 关联资源

- `flash/input_gen/gen_flychk_his/README.md`（完整接口与 FAQ）、`test/README.md`（测试数据与用例矩阵）
- skill `flash-data-extract`（h5py 提取 AMR 块结构）
