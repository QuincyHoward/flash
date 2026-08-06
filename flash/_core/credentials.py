"""
FLASH Sim standalone 凭据管理器 (自动加密版 + SSH 账户管理)

This is a vendored copy of physimx_core.credentials for standalone mode.
When physimx_core is installed, flash/__init__.py will import from
physimx_core.credentials instead.

设计原则:
  1. 凭据存储于项目外部 (~/.physimx/), 绝不进入项目目录
  2. 所有密码/密钥通过 Fernet 对称加密存储, 磁盘上为密文
  3. 加密密钥自动生成并保存, 无需用户输入主密码
  4. 凭据文件权限限制为仅所有者可读写
  5. 备份、Git 提交、项目迁移均不受影响

存储结构 (分层设计):
  ├─ PhySimX 父级存储 (~/.physimx/)
  │   ├── credentials.enc          # 父级凭据 (包含 user_name)
  │   └── .secret_key
  │
  └─ Flash 独立存储 (~/.physimx/flash/)
      ├── credentials.enc          # Flash 独立凭据
      └── .secret_key

继承逻辑:
  - 如果 ~/.physimx/credentials.enc 存在且有 user_name → 继承模式
    - get_user_name() 从父级读取
    - set_user_name() 写入父级文件
  - 否则 → 独立模式
    - 使用 ~/.physimx/flash/credentials.enc
    - 默认用户名: hello

默认值:
  - 用户名: hello
  - 密码: 123

用法:
  # 凭据管理
  from flash._core.credentials import CredentialManager
  cm = CredentialManager()

  # SSH 账户管理
  from flash._core.credentials import (
      add_account, modify_account, delete_account,
      show_account, list_accounts, set_primary,
      interactive_menu, load_ssh_credentials, get_user_name
  )
"""

import base64
import getpass
import json
import os
import stat
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from cryptography.fernet import Fernet


# ── 存储位置: 用户主目录, 不在项目内 ──
# Flash 独立存储 (standalone 模式)
FLASH_CREDENTIAL_DIR = Path.home() / ".physimx" / "flash"
FLASH_CREDENTIAL_ENC_FILE = FLASH_CREDENTIAL_DIR / "credentials.enc"
FLASH_SECRET_KEY_FILE = FLASH_CREDENTIAL_DIR / ".secret_key"

# PhySimX 父级存储 (用于继承用户名)
PARENT_CREDENTIAL_DIR = Path.home() / ".physimx"
PARENT_CREDENTIAL_ENC_FILE = PARENT_CREDENTIAL_DIR / "credentials.enc"
PARENT_SECRET_KEY_FILE = PARENT_CREDENTIAL_DIR / ".secret_key"

# 兼容旧代码: 默认使用 Flash 独立存储
CREDENTIAL_DIR = FLASH_CREDENTIAL_DIR
CREDENTIAL_ENC_FILE = FLASH_CREDENTIAL_ENC_FILE
SECRET_KEY_FILE = FLASH_SECRET_KEY_FILE

# 旧版文件 (自动迁移支持)
_KEY_SALT_FILE_LEGACY = CREDENTIAL_DIR / "key_salt.bin"
_KEY_VERIFY_FILE_LEGACY = CREDENTIAL_DIR / "key_verify.bin"
_OLD_CREDENTIAL_FILE = CREDENTIAL_DIR / "credentials.json"

# 默认用户名
DEFAULT_USER_NAME = "hello"


# 预定义的凭据模板
CREDENTIAL_TEMPLATES = {
    "flash_ssh": {
        "description": "FLASH 超算 SSH 连接 (主机/端口由 route_tester 自动选择)",
        "fields": {
            "password": {
                "description": "SSH 密码",
                "secret": True,
                "required": True,
                "default": "123",  # 默认密码
            },
        },
    },
    "flychk": {
        "description": "Flychk 仿真账户",
        "fields": {
            "username": {
                "description": "用户名",
                "default": "hello",  # 默认用户名
                "required": True,
            },
            "password": {
                "description": "密码",
                "secret": True,
                "required": True,
                "default": "123",  # 默认密码
            },
        },
    },
    "deepseek_api": {
        "description": "DeepSeek API (太极网关)",
        "fields": {
            "base_url": {
                "description": "API 基础 URL",
                "default": "https://gateway.taichuai.cn/modelhub/api/v1",
                "required": True,
                "field_type": "url",
            },
            "api_key": {
                "description": "API Key",
                "secret": True,
                "required": True,
            },
        },
    },
    "gitee": {
        "description": "Gitee 代码仓库认证",
        "fields": {
            "username": {
                "description": "Gitee 用户名",
                "default": "hello",  # 默认用户名
                "required": True,
            },
            "token": {
                "description": "个人访问令牌 (PAT)",
                "secret": True,
                "required": True,
                "default": "123",  # 默认令牌
            },
            "repo_url": {
                "description": "仓库 URL (不含认证信息)",
                "default": "https://gitee.com/physimx/flash.git",
                "required": True,
            },
            "repo_name": {
                "description": "仓库名称",
                "default": "flash",
                "required": True,
            },
            "private": {
                "description": "是否私有仓库 (true/false)",
                "default": "true",
                "required": False,
            },
        },
    },
}

# 敏感字段名: 这些字段的值会被加密存储
_SECRET_FIELDS = {"password", "api_key", "secret", "token", "access_key", "private_key"}

# 继承模式缓存
_INHERITANCE_CHECKED = False
_INHERITANCE_MODE = False  # True = 继承父级, False = 独立模式

# ── 加密核心 ──────────────────────────────────────────

def _get_or_create_key() -> bytes:
    """获取或自动生成 Fernet 加密密钥。"""
    if SECRET_KEY_FILE.exists():
        return SECRET_KEY_FILE.read_bytes()

    key = Fernet.generate_key()
    CREDENTIAL_DIR.mkdir(parents=True, exist_ok=True)
    _tmp = SECRET_KEY_FILE.with_suffix(".tmp")
    _tmp.write_bytes(key)
    _tmp.replace(SECRET_KEY_FILE)
    _lock_down(SECRET_KEY_FILE)
    return key


def _encrypt_data(data: bytes, fernet: Fernet) -> bytes:
    """加密数据。"""
    return fernet.encrypt(data)


def _decrypt_data(ciphertext: bytes, fernet: Fernet) -> bytes:
    """解密数据。"""
    return fernet.decrypt(ciphertext)


def _lock_down(path: Path) -> None:
    """设置文件/目录为仅所有者可读写 (600/700)。"""
    try:
        if os.name == "posix":
            if path.is_dir():
                path.chmod(stat.S_IRWXU)  # 700
            else:
                path.chmod(stat.S_IRUSR | stat.S_IWUSR)  # 600
    except OSError:
        pass


# ── 兼容旧版: getpass ──

def _safe_getpass(prompt: str) -> str:
    """安全地获取密码输入。"""
    try:
        return getpass.getpass(prompt)
    except (KeyboardInterrupt, EOFError, OSError):
        print(f"\n  [提示] 输入时字符将可见, 请注意周围环境")
        return input(prompt)


class CredentialManager:
    """安全凭据管理器 (自动 Fernet 加密存储, 无需主密码)。

    支持自定义存储路径, 用于实现分层继承:
    - 默认: 使用 Flash 独立存储 (~/.physimx/flash/)
    - 继承模式: 可指向父级存储 (~/.physimx/)
    """

    def __init__(
        self,
        enc_file: Optional[Path] = None,
        key_file: Optional[Path] = None
    ) -> None:
        """初始化凭据管理器。

        Args:
            enc_file: 加密凭据文件路径 (默认: FLASH_CREDENTIAL_ENC_FILE)
            key_file: 密钥文件路径 (默认: FLASH_SECRET_KEY_FILE)
        """
        self._enc_file = enc_file or FLASH_CREDENTIAL_ENC_FILE
        self._key_file = key_file or FLASH_SECRET_KEY_FILE
        self._fernet: Optional[Fernet] = None
        self._ensure_dir()
        self._init_fernet()
        self._maybe_migrate_legacy()

    def _ensure_dir(self) -> None:
        """确保凭据目录存在。"""
        self._enc_file.parent.mkdir(parents=True, exist_ok=True)
        _lock_down(self._enc_file.parent)

    def _init_fernet(self) -> None:
        """从密钥文件初始化 Fernet 实例。"""
        key = self._get_or_create_key()
        self._fernet = Fernet(key)

    def _get_or_create_key(self) -> bytes:
        """获取或自动生成 Fernet 加密密钥。"""
        if self._key_file.exists():
            return self._key_file.read_bytes()

        key = Fernet.generate_key()
        self._key_file.parent.mkdir(parents=True, exist_ok=True)
        self._key_file.write_bytes(key)
        _lock_down(self._key_file)
        return key

    def _maybe_migrate_legacy(self) -> None:
        """检测并清理旧版主密码体系的残留文件。"""
        cleaned = []
        for legacy_file in [_KEY_SALT_FILE_LEGACY, _KEY_VERIFY_FILE_LEGACY]:
            if legacy_file.exists():
                try:
                    legacy_file.unlink()
                    cleaned.append(legacy_file.name)
                except OSError:
                    pass
        if _OLD_CREDENTIAL_FILE.exists():
            try:
                with open(_OLD_CREDENTIAL_FILE, "r", encoding="utf-8") as f:
                    old_data = json.load(f)
                if isinstance(old_data, dict) and old_data:
                    self._save_raw(old_data)
                    print(f"  [迁移] 已将 {len(old_data)} 组旧凭据迁移到加密存储")
                _OLD_CREDENTIAL_FILE.unlink()
                cleaned.append(_OLD_CREDENTIAL_FILE.name)
            except (json.JSONDecodeError, OSError):
                pass

    def _load_raw(self) -> Dict[str, Any]:
        """加载并解密凭据数据。"""
        if not self._enc_file.exists():
            return {}
        try:
            ciphertext = self._enc_file.read_bytes()
            if not ciphertext:
                return {}
            plaintext = _decrypt_data(ciphertext, self._fernet)
            return json.loads(plaintext.decode("utf-8"))
        except Exception:
            return {}

    def _save_raw(self, data: Dict[str, Any]) -> None:
        """加密并保存凭据数据。"""
        self._ensure_dir()
        plaintext = json.dumps(data, ensure_ascii=False).encode("utf-8")
        ciphertext = _encrypt_data(plaintext, self._fernet)
        tmp = self._enc_file.with_suffix(".tmp")
        tmp.write_bytes(ciphertext)
        tmp.replace(self._enc_file)
        _lock_down(self._enc_file)

    def get(self, name: str) -> Optional[Dict[str, Any]]:
        """读取某个凭据, 不存在时返回 None。"""
        return self._load_raw().get(name)

    def set(self, name: str, data: Dict[str, Any]) -> None:
        """设置或更新某个凭据 (自动加密存储)。"""
        all_creds = self._load_raw()
        all_creds[name] = data
        self._save_raw(all_creds)

    def delete(self, name: str) -> bool:
        """删除某个凭据, 返回是否成功。"""
        all_creds = self._load_raw()
        if name not in all_creds:
            return False
        del all_creds[name]
        self._save_raw(all_creds)
        return True

    def delete_all(self) -> int:
        """删除所有凭据, 返回删除数量。"""
        all_creds = self._load_raw()
        count = len(all_creds)
        self._save_raw({})
        return count

    def list_all(self) -> Dict[str, Any]:
        """列出所有凭据 (密码字段已掩码)。"""
        all_creds = self._load_raw()
        result = {}
        for name, data in all_creds.items():
            masked = dict(data)
            for k, v in masked.items():
                if k in _SECRET_FIELDS:
                    if isinstance(v, str) and len(v) > 4:
                        masked[k] = v[:2] + "*" * (len(v) - 4) + v[-2:]
                    elif isinstance(v, str):
                        masked[k] = "****"
            result[name] = masked
        return result

    def interactive_set(self, name: Optional[str] = None) -> None:
        """交互式设置凭据。"""
        templates = CREDENTIAL_TEMPLATES

        if name is None:
            print("\n可设置的凭据类型:")
            for key, tmpl in templates.items():
                print(f"  [{key}]  {tmpl['description']}")
            print()
            available = list(templates.keys())
            name = input(f"请选择 [{'/'.join(available)}]: ").strip()

        if name not in templates:
            print(f"[错误] 未知凭据类型: {name}")
            print(f"可用: {', '.join(templates.keys())}")
            return

        tmpl = templates[name]
        print(f"\n{'─' * 50}")
        print(f"  设置 {tmpl['description']}")
        print(f"{'─' * 50}")
        print("  (直接回车使用默认值, 输入空白跳过可选字段)")
        print()

        existing = self.get(name)
        if existing:
            print(f"  [提示] {name} 已有凭据, 将覆盖")
            print()

        data = {}
        for field_name, field_info in tmpl["fields"].items():
            default_val = field_info.get("default", "")
            required = field_info.get("required", False)
            is_secret = field_info.get("secret", False)
            field_type = field_info.get("field_type", "")

            prompt = f"  {field_info['description']}"
            if default_val:
                prompt += f" [{default_val}]"
            prompt += ": "

            if is_secret:
                value = _safe_getpass(prompt)
            else:
                value = input(prompt)

            value = value.strip()

            if field_type == "url" and value:
                if not value.startswith("http"):
                    print(f"  [警告] URL 应以 http:// 或 https:// 开头")
                    confirm = input(f"  确认使用此 URL? [y/N]: ").strip().lower()
                    if confirm != "y":
                        value = ""
                elif value.startswith("sk-"):
                    print(f"  [警告] 这看起来是 API Key, 不是 URL!")
                    confirm = input(f"  仍然使用此值? [y/N]: ").strip().lower()
                    if confirm != "y":
                        value = ""

            if not value and default_val:
                value = default_val
            elif not value and required:
                while not value:
                    print(f"  此项为必填, 请重新输入")
                    if is_secret:
                        value = _safe_getpass(prompt).strip()
                    else:
                        value = input(prompt).strip()
                    if not value and default_val:
                        value = default_val
            elif not value and not required:
                continue

            data[field_name] = value

        self.set(name, data)
        print(f"\n  [完成] {tmpl['description']} 已加密保存")
        print(f"  存储位置: {self._enc_file.parent}/")
        print(f"  文件为 Fernet 密文, 磁盘上非明文")


# ── 便捷函数 ───────────────────────────────────────────────
_manager: Optional[CredentialManager] = None


def _get_manager() -> CredentialManager:
    """获取全局单例管理器。"""
    global _manager
    if _manager is None:
        _manager = CredentialManager()
    return _manager


def load_ssh_credentials(name: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """加载 FLASH SSH 凭据。"""
    cm = _get_manager()
    if name is not None:
        return cm.get(name)
    meta = cm.get("__meta__") or {}
    primary = meta.get("primary_ssh", "flash_ssh")
    cred = cm.get(primary)
    if cred is None:
        cred = cm.get("flash_ssh")
    return cred


def load_all_ssh_credentials() -> Dict[str, Dict[str, Any]]:
    """加载所有超算 SSH 凭据。"""
    cm = _get_manager()
    all_creds = cm._load_raw()
    result = {}
    for name, data in all_creds.items():
        if name.startswith("flash_ssh") and isinstance(data, dict) and data.get("host"):
            result[name] = data
    return result


def _check_inheritance() -> bool:
    """检查是否应该继承父级 (PhySimX) 凭据。

    继承条件:
    1. 父级凭据文件存在 (~/.physimx/credentials.enc)
    2. 父级文件包含 user_name 字段

    Returns:
        True: 继承模式, 用户名操作应指向父级文件
        False: 独立模式, 用户名操作使用 Flash 独立存储
    """
    global _INHERITANCE_CHECKED, _INHERITANCE_MODE

    if _INHERITANCE_CHECKED:
        return _INHERITANCE_MODE

    # 检查父级凭据文件是否存在
    if not PARENT_CREDENTIAL_ENC_FILE.exists():
        _INHERITANCE_MODE = False
        _INHERITANCE_CHECKED = True
        return False

    # 尝试读取父级文件的 user_name
    try:
        parent_cm = CredentialManager(
            enc_file=PARENT_CREDENTIAL_ENC_FILE,
            key_file=PARENT_SECRET_KEY_FILE
        )
        meta = parent_cm.get("__meta__") or {}
        if "user_name" in meta:
            _INHERITANCE_MODE = True
            _INHERITANCE_CHECKED = True
            return True
    except Exception:
        pass

    _INHERITANCE_MODE = False
    _INHERITANCE_CHECKED = True
    return False


def _get_user_name_cm() -> CredentialManager:
    """获取用于用户名读写的 CredentialManager 实例。

    根据继承模式返回:
    - 继承模式: 返回父级 CredentialManager
    - 独立模式: 返回 Flash 独立 CredentialManager
    """
    if _check_inheritance():
        return CredentialManager(
            enc_file=PARENT_CREDENTIAL_ENC_FILE,
            key_file=PARENT_SECRET_KEY_FILE
        )
    else:
        return CredentialManager()


def get_user_name() -> str:
    """获取当前用户名 (默认: hello)。

    继承逻辑:
    - 如果父级 (~/.physimx/) 存在且有用户名, 则继承
    - 否则使用 Flash 独立存储 (~/.physimx/flash/)
    """
    cm = _get_user_name_cm()
    meta = cm.get("__meta__") or {}
    return meta.get("user_name", DEFAULT_USER_NAME)


def set_user_name(name: str) -> None:
    """设置用户名。

    继承逻辑:
    - 如果当前是继承模式, 修改父级文件 (~/.physimx/credentials.enc)
    - 如果是独立模式, 修改 Flash 独立文件 (~/.physimx/flash/credentials.enc)
    """
    cm = _get_user_name_cm()
    meta = cm.get("__meta__") or {}
    meta["user_name"] = name
    cm.set("__meta__", meta)


def get_best_route(cred_name: str) -> Optional[Dict[str, Any]]:
    """获取凭据已缓存的最佳路由。"""
    cm = _get_manager()
    cred = cm.get(cred_name)
    if cred is None:
        return None
    return cred.get("best_route")


def get_gitee_credentials() -> Optional[Dict[str, Any]]:
    """获取 Gitee 凭据，如果不存在则返回 None。"""
    cm = _get_manager()
    return cm.get("gitee")


def get_gitee_auth_url() -> str:
    """生成带认证的 Gitee URL。

    返回:
        如果凭据存在: https://username:token@gitee.com/user/repo.git
        如果凭据不存在: 默认 URL (需要用户先设置凭据)
    """
    cred = get_gitee_credentials()
    if not cred:
        return "https://gitee.com/physimx/flash.git"

    username = cred.get("username", "")
    token = cred.get("token", "")
    repo_url = cred.get("repo_url", "")

    # 从 repo_url 提取仓库路径
    # 例如: https://gitee.com/physimx/flash.git
    if "gitee.com/" in repo_url:
        repo_path = repo_url.split("gitee.com/")[-1]
    else:
        repo_path = "physimx/flash.git"

    return f"https://{username}:{token}@gitee.com/{repo_path}"


# ── SSH 账户管理功能 ───────────────────────────────────────

# 主账户默认名
_DEFAULT_PRIMARY_SSH = "flash_ssh"

# SSH 字段定义
SSH_FIELDS = [
    ("connection_mode", "连接模式 [auto/manual]", "auto"),
    ("password", "密码", "123"),  # 默认密码
]

# 手动模式时的额外字段
MANUAL_FIELDS = [
    ("host",     "SSH 主机", "ssh.cn-zhongwei-1.paracloud.com"),
    ("port",     "SSH 端口", 22),
    ("username", "用户名",   "hello@NC-E"),  # 默认用户名
]


def ask_one(label: str, default) -> str:
    """询问一个字段，回车返回默认值。"""
    val = input(f"  {label:12s} [{default}]: ").strip()
    return val if val else str(default)


def mask_secret(data: Dict[str, Any]) -> Dict[str, Any]:
    """对敏感字段进行掩码处理，返回安全可展示的副本。"""
    masked = dict(data)
    for k, v in masked.items():
        if k in _SECRET_FIELDS:
            if isinstance(v, str) and len(v) > 4:
                masked[k] = v[:2] + "*" * (len(v) - 4) + v[-2:]
            elif isinstance(v, str):
                masked[k] = "****"
    return masked


def collect_ssh_accounts(cm) -> List[str]:
    """收集所有 flash_ssh 开头的凭据名，排序返回。"""
    all_creds = cm._load_raw()
    return sorted([k for k in all_creds if k.startswith("flash_ssh")])


def get_primary_ssh(cm) -> str:
    """获取主 SSH 账户名。"""
    meta = cm.get("__meta__") or {}
    return meta.get("primary_ssh", _DEFAULT_PRIMARY_SSH)


def set_primary_ssh(cm, account_name: str) -> None:
    """设置主 SSH 账户。"""
    meta = cm.get("__meta__") or {}
    meta["primary_ssh"] = account_name
    cm.set("__meta__", meta)


def next_ssh_number(cm) -> int:
    """计算下一个可用的 SSH 账户编号。"""
    existing = collect_ssh_accounts(cm)
    used = set()
    for name in existing:
        if name == "flash_ssh":
            used.add(1)
        elif name.startswith("flash_ssh_"):
            try:
                used.add(int(name.split("_")[-1]))
            except ValueError:
                pass
    n = 1
    while n in used:
        n += 1
    return n


def ssh_account_name(num: int) -> str:
    """根据编号生成 SSH 账户名 (1 -> flash_ssh, 2+ -> flash_ssh_N)。"""
    return "flash_ssh" if num == 1 else f"flash_ssh_{num}"


def _pick_account(cm, accounts=None) -> Optional[str]:
    """让用户选择一个 SSH 账户，返回账户名。"""
    if accounts is None:
        accounts = collect_ssh_accounts(cm)
    if not accounts:
        print("\n  [提示] 尚未设置任何超算 SSH 账户。")
        return None

    primary = get_primary_ssh(cm)
    print("\n  可选超算账户:")
    for i, name in enumerate(accounts, 1):
        label = _account_label(name, cm)
        marker = " <-- 主账户" if name == primary else ""
        print(f"    [{i}] {name}  ({label}){marker}")

    choice = input(f"\n  选择账户编号 [1-{len(accounts)}, 0=取消]: ").strip()
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(accounts):
            return accounts[idx]
    except ValueError:
        pass
    return None


def _account_label(name: str, cm=None) -> str:
    """获取账户的人类可读标签（用于显示）。"""
    try:
        from flash.flash_run.remote.route_tester import RouteTester
        return RouteTester.account_label(name, cm.get(name) if cm else None)
    except ImportError:
        return f"(账户 #{name})"


# ── 增 ──

def add_account() -> bool:
    """添加新的超算 SSH 账户。"""
    cm = _get_manager()
    num = next_ssh_number(cm)
    name = ssh_account_name(num)

    # 确定账户类型
    if num == 1:
        route_key = "scfa2696"
        label = "scfa2696@NC-E"
    else:
        route_key = "sch0348"
        label = "sch0348@BSCC-T6"

    print(f"\n  添加新超算账户: {name} ({label})")
    print(f"  连接模式: auto=自动选路, manual=手动指定")
    print(f"  {'─' * 50}")

    data = {}
    for key, field_label, default in SSH_FIELDS:
        val = ask_one(field_label, default)
        data[key] = val

    # 如果是 manual 模式，额外问主机/端口/用户名
    mode = data.get("connection_mode", "auto")
    if mode.lower() == "manual":
        for m_key, m_label, m_default in MANUAL_FIELDS:
            m_val = ask_one(m_label, str(m_default))
            if m_key == "port":
                try:
                    m_val = int(m_val)
                except ValueError:
                    m_val = m_default
            data[m_key] = m_val

    # 自动存储 route_key
    data["route_key"] = route_key

    if not data.get("password"):
        print("  [取消] 密码不能为空。")
        return False

    cm.set(name, data)
    print(f"  -> 已保存 {name} ({label}), 模式={mode}")

    ssh_accounts = collect_ssh_accounts(cm)
    if len(ssh_accounts) == 1:
        set_primary_ssh(cm, name)
        print(f"  -> 已自动设为主账户。")
    else:
        set_p = input("  设为主账户? [y/N]: ").strip().lower()
        if set_p in ("y", "yes"):
            set_primary_ssh(cm, name)
            print(f"  -> 主账户已设为: {name}")

    return True


# ── 改 ──

def modify_account(name: Optional[str] = None) -> bool:
    """修改已有的超算 SSH 账户。"""
    cm = _get_manager()
    accounts = collect_ssh_accounts(cm)

    if not accounts:
        print("\n  [提示] 尚未设置任何超算 SSH 账户。")
        return False

    if name is None:
        name = _pick_account(cm, accounts)
    if name is None:
        return False

    existing = cm.get(name)
    if not existing:
        print(f"\n  [错误] 未找到账户: {name}")
        return False

    label = _account_label(name, cm)
    current_mode = existing.get("connection_mode", "auto")
    print(f"\n  {'─' * 50}")
    print(f"  修改超算账户: {name} ({label})")
    print(f"  当前模式: {current_mode}")
    print(f"  {'─' * 50}")
    print("  (直接回车保留当前值)\n")

    data = dict(existing)

    # 连接模式
    val = input(f"  {'连接模式':12s} [auto/manual, 当前={current_mode}]: ").strip()
    if val in ("auto", "manual"):
        data["connection_mode"] = val
        if val == "manual":
            # 如果是 manual，确保有 host/port/username
            for m_key, m_label, m_default in MANUAL_FIELDS:
                current = existing.get(m_key, str(m_default))
                m_val = input(f"  {m_label:12s} [当前={current}]: ").strip()
                if m_val:
                    data[m_key] = int(m_val) if m_key == "port" else m_val

    # 密码
    current_pw = existing.get("password", "")
    display = "****" if current_pw else "(未设置)"
    val = input(f"  {'密码':12s} [{display}]: ").strip()
    if val:
        data["password"] = val

    cm.set(name, data)
    print(f"\n  -> {name} 已更新。")
    return True


# ── 删 ──

def delete_account(name: Optional[str] = None) -> bool:
    """删除超算 SSH 账户。"""
    cm = _get_manager()
    accounts = collect_ssh_accounts(cm)

    if not accounts:
        print("\n  [提示] 尚未设置任何超算 SSH 账户。")
        return False

    if name is None:
        name = _pick_account(cm, accounts)
    if name is None:
        return False

    primary = get_primary_ssh(cm)
    warn = ""
    if name == primary and len(accounts) > 1:
        warn = " (当前主账户!)"

    confirm = input(f"\n  确认删除 {name}{warn}? [y/N]: ").strip().lower()
    if confirm not in ("y", "yes"):
        print("  [取消] 未删除。")
        return False

    cm.delete(name)
    print(f"  -> {name} 已删除。")

    # 如果删除的是主账户，自动切换到第一个剩余账户
    if name == primary:
        remaining = collect_ssh_accounts(cm)
        if remaining:
            new_primary = remaining[0]
            set_primary_ssh(cm, new_primary)
            print(f"  -> 主账户已自动切换为: {new_primary}")

    return True


# ── 查 ──

def show_account(name: Optional[str] = None, raw: bool = False) -> None:
    """查看超算 SSH 账户详情。"""
    cm = _get_manager()
    accounts = collect_ssh_accounts(cm)

    if not accounts:
        print("\n  [提示] 尚未设置任何超算 SSH 账户。")
        return

    if name is None:
        name = _pick_account(cm, accounts)
    if name is None:
        return

    data = cm.get(name)
    if not data:
        print(f"\n  [错误] 未找到账户: {name}")
        return

    primary = get_primary_ssh(cm)
    label = _account_label(name, cm)
    is_p = " (主账户)" if name == primary else ""
    display = data if raw else mask_secret(data)

    print(f"\n  [{name}]{is_p}  ({label})")
    for k, v in display.items():
        print(f"    {k:12s}: {v}")
    # 显示路由管理器标识
    best = data.get("best_route", {})
    if best:
        print(f"    {'上次最佳路由':12s}: {best.get('host','?')}:{best.get('port','?')} ({best.get('latency_ms',0):.0f}ms)")


def list_accounts() -> None:
    """列出所有超算 SSH 账户。"""
    cm = _get_manager()
    accounts = collect_ssh_accounts(cm)

    if not accounts:
        print("\n  当前没有保存任何超算 SSH 账户。")
        return

    primary = get_primary_ssh(cm)
    print(f"\n  {'─' * 55}")
    print(f"  FLASH 超算 SSH 账户列表 ({len(accounts)} 个)")
    print(f"  {'─' * 55}")

    for name in accounts:
        label = _account_label(name, cm)
        cred = cm.get(name) or {}
        best = cred.get("best_route", {})
        route_info = ""
        if best:
            route_info = f" → {best.get('host','?')}:{best.get('port','?')} ({best.get('latency_ms',0):.0f}ms)"
        marker = " <-- 主账户" if name == primary else ""
        print(f"\n  [{name}]{marker}")
        print(f"    账户: {label}{route_info}")

    if len(accounts) > 1:
        print(f"\n  并行调度: 可同时向 {len(accounts)} 个超算提交任务")
    print(f"\n  {'─' * 55}")


# ── 主账户管理 ──

def set_primary(name: Optional[str] = None) -> bool:
    """设置主超算账户。"""
    cm = _get_manager()
    accounts = collect_ssh_accounts(cm)

    if not accounts:
        print("\n  [提示] 尚未设置任何超算 SSH 账户。")
        return False

    if name is None:
        name = _pick_account(cm, accounts)
    if name is None:
        return False

    if name not in accounts:
        print(f"\n  [错误] 未找到账户: {name}")
        return False

    old_primary = get_primary_ssh(cm)
    set_primary_ssh(cm, name)
    print(f"\n  -> 主账户已从 {old_primary} 切换为: {name}")
    return True


# ── 交互菜单 ──

def _route_test_menu(cm, accounts):
    """测试 SSH 路由并选择最佳线路。"""
    try:
        from flash.flash_run.remote.route_tester import (
            RouteTester, test_and_select_best_route
        )
        # Try to import save_best_route (from physimx_core or flash._core)
        try:
            from physimx_core.credentials import save_best_route
        except ImportError:
            from flash._core.credentials import save_best_route
    except ImportError:
        print("\n  [WARN] 无法导入 route_tester 模块")
        return

    primary = get_primary_ssh(cm)
    print("\n  测试所有 SSH 账户的路由...")

    for cred_name in accounts:
        cred = cm.get(cred_name) or {}
        label = _account_label(cred_name, cm)
        print(f"\n  [{cred_name}] {label}:")
        # 使用 route_key 确定路由列表
        route_key = RouteTester.resolve_route_key(cred_name, cred)
        if route_key == "scfa2696":
            from flash.flash_run.remote.route_tester import ROUTES_SCFA2696 as routes
        else:
            from flash.flash_run.remote.route_tester import ROUTES_SCH0348 as routes
        best = test_and_select_best_route(label, routes)
        if best:
            save_best_route(cred_name, best)
            print(f"  -> 已保存最佳路由")


def interactive_menu() -> None:
    """FLASH SSH 凭据交互菜单。"""
    while True:
        cm = _get_manager()
        accounts = collect_ssh_accounts(cm)
        primary = get_primary_ssh(cm)
        count = len(accounts)
        current_user = get_user_name()

        print(f"\n  {'=' * 50}")
        print(f"  FLASH 超算 SSH 账户管理 [共 {count} 个账户]")
        if primary:
            print(f"  当前主账户: {primary}")
        print(f"  用户名: {current_user} (用于路径 ~/{current_user}/FLASH/...)")
        print(f"  {'=' * 50}")
        print("  [1] 添加新账户   (add)")
        print("  [2] 修改账户     (mod)")
        print("  [3] 删除账户     (del)")
        print("  [4] 查看账户     (show)")
        print("  [5] 列出全部     (list)")
        print("  [6] 设置主账户   (primary)")
        print("  [7] 测试路由     (route)")
        print("  [8] 设置用户名   (user)")
        print("  [0] 返回")

        choice = input("\n  请选择 [0-8]: ").strip()

        if choice == "1":
            add_account()
        elif choice == "2":
            modify_account()
        elif choice == "3":
            delete_account()
        elif choice == "4":
            show_account()
        elif choice == "5":
            list_accounts()
        elif choice == "6":
            set_primary()
        elif choice == "7":
            _route_test_menu(cm, accounts)
        elif choice == "8":
            current = get_user_name()
            new_name = input(f"  输入新用户名 [当前: {current}]: ").strip()
            if new_name:
                set_user_name(new_name)
                print(f"  -> 用户名已设为: {new_name}")
            else:
                print(f"  -> 保持: {current}")
        elif choice == "0":
            break
        else:
            print("  [无效选择]")


def main():
    """CLI 入口。"""
    args = sys.argv[1:]

    if not args:
        interactive_menu()
        return

    cmd = args[0].lower()
    name = args[1] if len(args) > 1 else None

    if cmd in ("add", "new", "create"):
        add_account()
    elif cmd in ("mod", "modify", "edit"):
        modify_account(name)
    elif cmd in ("del", "delete", "rm", "remove"):
        delete_account(name)
    elif cmd in ("show", "view", "detail"):
        raw = "--raw" in args
        show_account(name, raw=raw)
    elif cmd in ("list", "ls"):
        list_accounts()
    elif cmd in ("primary", "set-primary", "main"):
        set_primary(name)
    elif cmd in ("route", "routes", "test-route"):
        cm = _get_manager()
        accounts = collect_ssh_accounts(cm)
        _route_test_menu(cm, accounts)
    elif cmd in ("user", "username"):
        if name:
            set_user_name(name)
            print(f"  用户名已设为: {name}")
        else:
            print(f"  当前用户名: {get_user_name()}")
    elif cmd in ("menu", "interactive"):
        interactive_menu()
    elif cmd in ("-h", "--help", "help"):
        print(__doc__)
    else:
        # 尝试作为账户名直接查看
        cm = _get_manager()
        if cm.get(cmd):
            show_account(cmd)
        else:
            print(f"  未知命令: {cmd}")
            print(__doc__)


if __name__ == "__main__":
    main()


__all__ = [
    "CredentialManager",
    "load_ssh_credentials", "load_all_ssh_credentials",
    "get_user_name", "set_user_name",
    "get_best_route", "get_gitee_credentials", "get_gitee_auth_url",
    "add_account", "modify_account", "delete_account",
    "show_account", "list_accounts", "set_primary",
    "interactive_menu", "main",
]
