# SNBVTi3umx — SNB 版 V 屏蔽 + 3 µm Ti 示踪（域扩展）

> 最后核对：2026-11-08 · commit c77b564

**一句话职责**：SNB 非局域热传导 VTi 示踪（**3 µm Ti 层 + 域扩展**；仅超算，175 进程=网格定义；本地生成+SFTP 上传）

- 与 [SNBVTi3um](../SNBVTi3um/README.md) 物理构型一致，差异是**计算域扩展**（x 后缀语义）——**进程数 175**（125→175 = 网格定义的一部分，不可改）
- `gen_mode=local_upload`；仅超算运行；辐射开 ↔ radON 联动护栏同 SNB 家族（详见 [SNBVTi2um](../SNBVTi2um/README.md)）

```bash
python -m flash.scenarios.core.entry.cli run SNBVTi3umx
```

家族对照表见 [SNBVTi1um](../SNBVTi1um/README.md)。

**上级导航**：[../README.md](../../../../README.md)
