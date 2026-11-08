# SNBVTi3um — SNB 版 V 屏蔽 + 3 µm Ti 示踪

> 最后核对：2026-11-08 · commit c77b564

**一句话职责**：SNB 非局域热传导 VTi 示踪（**3 µm Ti 层**；仅超算，125 进程=网格定义；本地生成+SFTP 上传）

- VTi 构型（V 屏蔽 + Ti 示踪）的 SNB 热传导版本，**3 µm Ti 层**；网格与进程数绑定（125 进程 = 网格定义的一部分，不可改）
- `gen_mode=local_upload`（本地生成 + SFTP 上传）；仅超算运行；辐射开 ↔ radON 联动护栏同 SNB 家族（详见 [SNBVTi2um](../SNBVTi2um/README.md)）

```bash
python -m flash.scenarios.core.entry.cli run SNBVTi3um
```

家族对照表见 [SNBVTi1um](../SNBVTi1um/README.md)；同型域扩展版 [SNBVTi3umx](../SNBVTi3umx/README.md)。

**上级导航**：[../README.md](../../../../README.md)
