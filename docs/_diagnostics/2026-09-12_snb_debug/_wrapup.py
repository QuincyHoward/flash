# -*- coding: utf-8 -*-
"""收尾: 归档本轮根目录脚本 + 追加最终结论到日志 + 更新长期备忘。"""
import io
import os
import shutil
import re

ROOT = r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash"
DEST = os.path.join(ROOT, "docs", "_diagnostics", "2026-09-12_snb_debug")
MEM = os.path.join(ROOT, ".workbuddy", "memory")

# ---- 1) 追加最终结论 ----
ADD = """
## 80. ★★★ 收集污染修复 + 端到端验证通过 (最终)

### 修复内容 (`SNBOneCH_ml.py`)

**Bug**: `deploy_and_run()` 收集时直接
`cp -f {obj}/{BASENM}* ... {wsl_out}/`, **未清理 `flash_output/`**;
而 chk/plt 文件名不含 tag 前缀 → **上一轮 chk 残留混杂**。

**第一次修复尝试 (错误!)**: 用 `rm -rf {wsl_out}` —— 但这会**连带删除
`flash_output/hpc_flash_ssh/` (超算结果) 与 `walltime_wsl.txt`**。
实测已造成 `hpc_flash_ssh/` 下 3 个文件的目录被清空重建。
★ 教训: **`OUTPUT_DIR` 是被 WSL 与 HPC 共用的父目录**, 不能整目录删。

**最终修复 (正确)**: 只删**本次运行的产物模式**, 保留子目录与无关文件:
```
mkdir -p {wsl_out} &&
rm -f {wsl_out}/{BASENM}* {wsl_out}/wsl_run_snbonech.log {wsl_out}/{LOG_FILE} 2>/dev/null;
cp -f {obj}/{BASENM}* ... {wsl_out}/ 2>/dev/null;
```
并新增 `_verify_collected_nxb()` 收集后自检: 按文件尺寸反推格数
(~589 B/格), 若存在 < 期望半数的档位则 WARN "疑似陈旧文件混杂"。

### 端到端验证 (RC=0, 墙钟 391.2 s)

```
[i]     chk 收集自检: 期望 nxb=8192, 总格=32768, dx=0.01526 um
[i]     实际 chk 尺寸分布: 1 x 19311748 (chk_0000)
                           1 x 19311748 (chk_0001)
[OK]    chk 尺寸自检通过 (无小于期望半数的档位)
[OK]    运行 成功 — WSL 运行墙钟 391.2 s (4 proc)
```

**收集结果 (干净)**: chk=2, plt=2, 子目录 `hpc_flash_ssh/` **完好保留**。

| chk | 尺寸 | 格数 | dx | dt | 8 物种 |
|---|---|---|---|---|---|
| 0000 | 19,311,748 B | 32768 | 0.01526 um | 1.0e-15 | 29091/7/3638/6/7/7/6/6 ✓ |
| 0001 | 19,311,748 B | 32768 | 0.01526 um | 1.265e-13 | 29091/23/3653/6/7/7/6/6 ✓ |

chk_0001: tele 1.10..2.4334e4 K, velx ±1.9e6 cm/s —— **物理正常, 网格不塌缩**。

### ★★★ 本轮最终定论 (四条)

1. **网格修复有效**: `build_setup_flags_ug()` 按 nproc 反推 nxb,
   8 物种全部写入且每薄层 6-7 格。**这是本轮最具价值的修复。**
2. **第 78 节的"均匀化失稳"结论完全错误** —— 纯属**陈旧文件伪影**。
   新运行 (nxb=8192) 在 chk_0000/0001 上**完全健康**。
3. **收集污染是本轮暴露的最危险工程坑**: 它**静默**地把旧运行结果当新结果,
   且因旧文件数量占优而**抢占文件下标**, 使"按名字读第 N 帧"必然拿到错误数据。
   ★ 判据: **`sim info` 的 `setup call` + 文件 mtime**, 绝不用文件名字典序。
4. **`flash_output/` 是 WSL 与 HPC 共用父目录** → **禁止整目录删除**。

### SNB 激活状态 (新发现, 待查)

`SNB 变量 QESH max|.| = 0.000e+00` —— **QESH 全零**。
`QENL`/`CORQ`/`MFPE` 均非零 (1.6e21 / 1.6e21 / 4.37e8)。
★ 与 `reference/SNB_FLASH_reference.md` 里"SNB 热流建立在无界 Spitzer 电导
(QESX ← COND_VAR)之上"的描述不符, **QESH 应为非零**。
⇒ 下一轮首要排查: **QESH 为何全零** (可能 ① 该变量在本模块位置未更新;
② 诊断变量拷贝时机; ③ 1e-11 s 内热流尚未建立)。**不要急着下结论。**
"""

with io.open(os.path.join(MEM, "2026-09-12.md"), "a", encoding="utf-8") as fh:
    fh.write(ADD)
print("log appended", len(ADD))

# ---- 2) 长期备忘记入新铁律 ----
P = os.path.join(MEM, "MEMORY.md")
t = io.open(P, encoding="utf-8").read()
NEW = """
12. ★★★ **禁止整目录删除 `flash_output/`** —— 它是 **WSL 与 HPC 共用父目录**
    (`hpc_<account>/` 子目录存超算结果)。收集 WSL 结果时只删本次产物模式:
    `rm -f {out}/{BASENM}* {out}/wsl_run_snbonech.log`, **保留子目录**。
    2026-09-12 曾用 `rm -rf` 误清 `hpc_flash_ssh/`。
13. ★★★ **chk/plt 收集后必须校验"是否陈旧"**: 文件名**不含 tag 前缀**,
    而 `flash_output/` 会跨运行累积 → 旧 chk 残留且**数量占优抢占下标**,
    使"按文件名读第 N 帧"**静默拿到旧运行数据** (曾据此得出"网格塌缩 +
    全域均匀化"的完全错误结论)。
    ★ 权威判据 = **`sim info` 的 `setup call` (含 `-nxb`) + 文件 mtime**,
    **绝不能用文件名字典序**。快速粗筛: 尺寸档位 (32768 格 ≈ 19.3 MB;
    512 格 ≈ 0.73 MB; ~589 B/格)。
"""
marker = "## ⚠ 待用户决策的历史遗留"
t = t.replace(marker, NEW.strip() + "\n\n---\n\n" + marker, 1)
t = re.sub(r"最近更新: [^\n]*", "最近更新: 2026-09-12（第六轮 + 第二轮归档/超算核实/收集污染修复）", t)
io.open(P, "w", encoding="utf-8").write(t)
print("MEMORY.md", len(t), "chars")

# ---- 3) 归档根目录脚本 ----
n = 0
for f in sorted(os.listdir(ROOT)):
    p = os.path.join(ROOT, f)
    if os.path.isfile(p) and f.startswith("_"):
        shutil.move(p, os.path.join(DEST, f)); n += 1
print("archived", n, "scripts")

files = sorted(f for f in os.listdir(ROOT) if os.path.isfile(os.path.join(ROOT, f)))
print("\n根目录文件 (%d):" % len(files))
for f in files:
    print("  %10d  %s" % (os.path.getsize(os.path.join(ROOT, f)), f))
