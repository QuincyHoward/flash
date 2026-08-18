"""MinimalCredentialManager — 内置的最小化凭据管理器

- 存储位置: ~/.physimx/flash/credentials.enc (Fernet 密文)
- 密钥文件: ~/.physimx/flash/.secret_key
- 旧版明文 credentials.json 自动迁移到加密存储
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from cryptography.fernet import Fernet


class MinimalCredentialManager:
    """最小化凭据管理器 — Fernet 加密持久化。

    存储路径: {HOME}/.physimx/{subdir}/credentials.enc + .secret_key
    与旧版 _core/credentials.py 的 CredentialManager 加密方案一致。
    """

    def __init__(self, subdir: str = "flash"):
        self._subdir = subdir
        self._store: Dict[str, Any] = {}
        self._cred_dir = self._resolve_dir()
        self._enc_file = self._cred_dir / "credentials.enc"
        self._key_file = self._cred_dir / ".secret_key"
        self._fernet: Optional[Fernet] = None
        self._init_fernet()
        self._maybe_migrate_legacy()
        self._load()

    # ── 文件路径 ──
    def _resolve_dir(self) -> Path:
        home = Path(os.path.expanduser("~"))
        return home / ".physimx" / self._subdir

    def _lock_down(self, path: Path) -> None:
        """设置文件/目录为仅所有者可读写 (600/700)。"""
        try:
            if os.name == "posix":
                if path.is_dir():
                    path.chmod(0o700)
                else:
                    path.chmod(0o600)
        except OSError:
            pass

    def _init_fernet(self) -> None:
        """从密钥文件初始化 Fernet 实例 (无则自动生成)。"""
        if self._key_file.exists():
            key = self._key_file.read_bytes()
        else:
            key = Fernet.generate_key()
            self._cred_dir.mkdir(parents=True, exist_ok=True)
            tmp = self._key_file.with_suffix(".tmp")
            tmp.write_bytes(key)
            tmp.replace(self._key_file)
            self._lock_down(self._key_file)
        self._fernet = Fernet(key)
        self._lock_down(self._cred_dir)

    def _maybe_migrate_legacy(self) -> None:
        """将旧版明文 credentials.json 迁移到加密存储并删除明文。"""
        legacy = self._cred_dir / "credentials.json"
        if not legacy.exists():
            return
        try:
            data = json.loads(legacy.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data:
                self._save_raw(data)
            legacy.unlink()
        except (json.JSONDecodeError, OSError):
            pass

    def _load(self) -> None:
        """从磁盘加载并解密凭据。文件不存在时使用空存储 + 默认 __meta__。"""
        try:
            if self._enc_file.exists():
                data = self._decrypt_file()
                self._store = data if isinstance(data, dict) else {}
            else:
                self._store = {}
        except Exception:
            self._store = {}
        # 确保 __meta__ 存在
        self._store.setdefault("__meta__", {"default_user_name": "hello"})

    def _decrypt_file(self) -> Dict[str, Any]:
        """从磁盘解密读取凭据数据。"""
        if not self._enc_file.exists():
            return {}
        try:
            ciphertext = self._enc_file.read_bytes()
            if not ciphertext:
                return {}
            plaintext = self._fernet.decrypt(ciphertext)
            return json.loads(plaintext.decode("utf-8"))
        except Exception:
            return {}

    def _save(self) -> None:
        """持久化到磁盘 (加密, 原子写入)。"""
        try:
            self._save_raw(self._store)
        except OSError:
            pass

    def _save_raw(self, data: Dict[str, Any]) -> None:
        """加密并保存凭据数据。"""
        self._cred_dir.mkdir(parents=True, exist_ok=True)
        plaintext = json.dumps(data, ensure_ascii=False).encode("utf-8")
        ciphertext = self._fernet.encrypt(plaintext)
        tmp = self._enc_file.with_suffix(".tmp")
        tmp.write_bytes(ciphertext)
        tmp.replace(self._enc_file)
        self._lock_down(self._enc_file)

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
