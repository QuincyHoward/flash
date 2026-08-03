"""MinimalCredentialManager — 最小化凭据管理器 (physimx_core 不可用时的回退)

- 存储位置: ~/.physimx/flash/credentials.json (与 physimx_core 的 subdir="flash" 对齐)
- 简单 JSON 持久化，无加密 (仅作为 physimx_core 缺失时的回退)
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional


class MinimalCredentialManager:
    """最小化凭据管理器 — JSON 文件持久化，无加密。

    存储路径: {HOME}/.physimx/{subdir}/credentials.json
    """

    def __init__(self, subdir: str = "flash"):
        self._subdir = subdir
        self._store: Dict[str, Any] = {}
        self._file = self._resolve_file()
        self._load()

    # ── 文件路径 ──
    def _resolve_file(self) -> Path:
        home = Path(os.path.expanduser("~"))
        return home / ".physimx" / self._subdir / "credentials.json"

    def _load(self) -> None:
        """从磁盘加载凭据。文件不存在时使用空存储 + 默认 __meta__。"""
        try:
            if self._file.exists():
                data = json.loads(self._file.read_text(encoding="utf-8"))
                self._store = data if isinstance(data, dict) else {}
            else:
                self._store = {}
        except (json.JSONDecodeError, OSError):
            self._store = {}
        # 确保 __meta__ 存在
        self._store.setdefault("__meta__", {"default_user_name": "hello"})

    def _save(self) -> None:
        """持久化到磁盘 (原子写入)。"""
        try:
            self._file.parent.mkdir(parents=True, exist_ok=True)
            tmp = self._file.with_suffix(".json.tmp")
            tmp.write_text(
                json.dumps(self._store, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            os.replace(tmp, self._file)
        except OSError:
            # 磁盘写入失败时静默降级为内存存储 (不崩溃)
            pass

    # ── 公开 API ──
    def get(self, key: str, default=None) -> Optional[Any]:
        return self._store.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._store[key] = value
        self._save()

    def delete(self, key: str) -> None:
        self._store.pop(key, None)
        self._save()

    def list_all(self) -> Dict[str, Any]:
        return dict(self._store)

    def _load_raw(self) -> Dict[str, Any]:
        return dict(self._store)
