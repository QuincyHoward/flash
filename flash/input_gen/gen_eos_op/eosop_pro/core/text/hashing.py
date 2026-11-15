"""文件哈希（流式分块，避免大文件整读入内存）。"""

from __future__ import annotations

import hashlib
from pathlib import Path

_CHUNK = 1 << 20  # 1 MiB


def sha256_file(path: str | Path) -> str:
    """分块计算 SHA-256，返回十六进制摘要（小写）。"""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            block = fh.read(_CHUNK)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def short8(digest: str) -> str:
    """取摘要前 8 位（用于报告文件名）。"""
    return digest[:8]
