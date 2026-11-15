# SNBVTi1um — SNB 版 V 屏蔽 + 1 µm Ti 示踪

> 最后核对：2026-11-08 · commit c77b564

**一句话职责**：SNB 非局域热传导 VTi 示踪（**1 µm Ti 层**；仅超算，125 进程=网格定义；本地生成+SFTP 上传）

## 定位与运行约束

- VTi 构型（V 屏蔽 + Ti 示踪）的 **SNB 热传导版本**，与 FL-SH 版 [VTi](../../VTi/README.md)1 物理构型对应；网格与进程数绑定（125 进程 = 网格定义的一部分，不可改）
- `gen_mode=local_upload`：本地生成输入 + SFTP 上传（远端树无 snb_package 镜像）；**仅超算运行**（scene.json kind=script）
- 辐射开 ↔ radON 驱动联动护栏同 SNB 家族约定（见 [SNBVTi2um](../SNBVTi2um/README.md) 详版说明）

```bash
python -m flash.scenarios.core.entry.cli run SNBVTi1um    # 统一 CLI 提交
```

## 家族对照

| 场景 | Ti 层 | 域 | 进程 |
|---|---|---|---|
| **本场景** | 1 µm | 标准 | 125 |
| [SNBVTi1umx](../SNBVTi1umx/README.md) | 1 µm | 扩展 | 175 |
| [SNBVTi2um](../SNBVTi2um/README.md) | 2 µm | 标准 | 125 |
| [SNBVTi2umx](../SNBVTi2umx/README.md) | 2 µm | 扩展 | 175 |
| [SNBVTi3um](../SNBVTi3um/README.md) / [SNBVTi3umx](../SNBVTi3umx/README.md) | 3 µm | 标准/扩展 | 125/175 |

**上级导航**：[../README.md](../../../../README.md)
