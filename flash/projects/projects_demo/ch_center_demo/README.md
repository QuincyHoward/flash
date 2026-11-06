> 最后核对：2026-11-06 · commit 20337b6（flash-readme-sync 首轮补写）

# ch_center 双密度对比演示工程

## 职责

对 ch_center 场景用两种 CH 靶密度（`sim_rhoTarg`）分别运行 FLASH 并对比结果，
演示 projects/ 工程化用法的最小范例。

## 内容清单

| 文件 | 说明 |
|---|---|
| `run_compare.py` | 本地 WSL 双密度仿真运行器 |
| `plot_compare.py` | 双密度结果对比绘图 |

## 关联资源

- `flash/scenarios/public/center_evolution/ch_center/`（被对比的场景）、`projects/`（工程体系）
