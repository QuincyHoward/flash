#!/usr/bin/env python3
"""修改 README.md — 开头添加 Gitee 仓库地址说明, 结尾添加英文简介

- 开头: 在标题与徽章之后插入 Gitee 仓库访问信息
- 结尾: 追加 English Overview 便于英文搜索
"""

from pathlib import Path

README = Path(__file__).resolve().parent.parent / "README.md"
text = README.read_text(encoding="utf-8")

# ============================================================
# 1. 开头: Gitee 仓库访问地址与说明
# ============================================================
gitee_section = """

## 仓库地址 (Repository)

本项目托管于 Gitee (码云), 支持 HTTPS 克隆与在线浏览:

```
https://gitee.com/physimx/flash
```

| 操作 | 命令 |
|------|------|
| **HTTPS 克隆** | `git clone https://gitee.com/physimx/flash.git` |
| **在线浏览** | https://gitee.com/physimx/flash (Code/Issues/Releases 页签) |
| **版本标签** | `0.0.000` (首次发布) — `git tag -l` 查看全部 |
| **问题反馈** | 通过 Gitee Issues 提交 (登录后新建 Issue) |

> 发布包已通过全局测试 (233 passed / 3 skipped) 与 FLASH 版权合规检查,
> 不包含 FLASH 引擎源码/分发表等受限材料 (详见 [许可](#许可) 与 [NOTICE](NOTICE))。

---

"""

# 在 "---\n\n## 目录" 之前插入 (即首个分隔线前)
anchor = "\n---\n\n## 目录\n"
assert anchor in text, "未找到插入锚点 (---\\n\\n## 目录)"
text = text.replace(anchor, gitee_section + anchor, 1)

# ============================================================
# 2. 结尾: 英文版内容简介
# ============================================================
english_overview = """

---

# flash-sim — English Overview

**flash-sim** is a full-featured Python interface and automation toolkit for the
[FLASH](https://flash.rochester.edu) high-energy-density physics (HEDP) simulation
code. It provides an end-to-end workflow: physics scenario design → `.par` file
generation → FLASH compile & run → HDF5 output processing → adaptive visualization
(1D/2D/3D) and physical analysis.

## Repository

Hosted on **Gitee (Chinese GitHub-equivalent platform)**:

```
https://gitee.com/physimx/flash
```

Clone with HTTPS: `git clone https://gitee.com/physimx/flash.git`

## Key Features

- **Scenario System** (`scenarios/`): declarative `SimulationScenario` definitions,
  a registry (`get_scenario()` / `list_scenarios()`), and a unified
  `FlashSimulatorEngine` that integrates WSL/remote execution, checkpoint
  collection, interpolation and result output.
  Built-in scenarios: `ch_center`, `grad_dens_sandwich`,
  `thin_layer_sandwich_si`, `thin_layer_sandwich_al`.
- **Input Generation** (`input_gen/`): parameter-file editor/calculator, EOS &
  opacity table tooling, Makefile generation, shell-script generation.
- **Output Processing** (`output_processors/`): HDF5 loading (1D/2D/3D), derived
  variables, unit conversion, batch/lazy loading, AMR visualization.
- **Multi-Environment Execution**: local WSL (Ubuntu) and HPC clusters over SSH
  (ParaCloud), with SLURM/SBATCH support.
- **Credential Management** (`_core/credentials/`): encrypted storage for Gitee
  tokens, SSH accounts and API keys.
- **Dual Mode**: standalone Python package (`flash.*`) or PhySimX plugin
  (`physimx_sim.flash.*`).

## Quick Start

```python
from flash.scenarios.registry import get_scenario
from flash.scenarios.simulator import FlashSimulatorEngine

scenario = get_scenario("thin_layer_sandwich_si")
engine = FlashSimulatorEngine(scenario, verbose=True)
output = engine.run(run_flash=False)   # dry-run: generate inputs only
```

See [README.md] (Chinese) for the full documentation, or run the global test
suite:

```bash
python scripts/run_global_tests.py     # framework + input + output suites
```

## License

flash-sim is dual-licensed: the Python wrapper/tool code is **Apache 2.0**
(© 2026 PhySimX Contributors); the FLASH simulation engine is governed by the
separate [FLASH License Agreement](https://flash.rochester.edu). This package
does **not** redistribute any FLASH source code, binaries, distributed EOS /
opacity tables (`*.cn4` etc.), user manuals, IONMIX sources or MultiEOS data
(per §3 of the FLASH License). Obtain FLASH independently from
[flash.rochester.edu](https://flash.rochester.edu).

**flash-sim Package — PhySimX Team Attribution (additional terms)**

*Publications Acknowledgment.* Any publication resulting from the use of
flash-sim (the flash auxiliary Python package) should acknowledge the
**PhySimX team (Mianyang, China)** for developing this auxiliary
Python package. Suggested text: "We acknowledge the PhySimX team
(Mianyang, China) for developing the flash-sim auxiliary Python
package used in this work."

*Commercial Use.* The flash-sim Python code is released under Apache 2.0,
but any commercial use must comply with all applicable licenses, including
Section 5 of the FLASH License Agreement (commercial use of FLASH requires
prior written approval from the Director of the Flash Center). flash-sim was
originally developed by the PhySimX team (Mianyang, China); commercial
licensing and liability are governed by the applicable license and any
written agreement in force at the time. The Apache 2.0 license covers only
the flash-sim Python code and does not grant any commercial rights to the
FLASH simulation engine.

## Contact

- Repository: https://gitee.com/physimx/flash
- Issues & feedback: via Gitee Issues

*English overview generated for search-engine discoverability. The authoritative
documentation remains the Chinese README above.*
"""

text = text.rstrip() + "\n" + english_overview + "\n"

README.write_text(text, encoding="utf-8")
print(f"README.md 修改完成: {len(text)} 字符")
print("  + 开头: Gitee 仓库地址与说明")
print("  + 结尾: English Overview")
