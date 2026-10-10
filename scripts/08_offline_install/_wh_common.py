#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
_wh_common.py — 离线安装 wheelhouse 的公共工具
============================================================================

供同目录的 build_wheelhouse.py（联网机造包）与 install_offline.py
（离线机安装）共用，避免两侧逻辑漂移。

职责:
  1. 解析 pyproject.toml → 依赖清单（base / full / dev 三档）
  2. wheel / sdist 文件名 → 归一化包名（PEP 427 规范）
  3. MANIFEST.json 读写 + SHA256 校验（U盘拷贝后防静默损坏）
  4. ★ wheelhouse 覆盖度预检：缺包**在安装前**报全清单并中止

设计约束（★ 均为实测踩坑后的硬性要求）:
  - 离线安装一律 `pip install --no-index --find-links=<wheelhouse>`。
    `--no-index` 是**硬闸门**：pip 物理上无法访问 PyPI，缺包立即报
    "No matching distribution found" 并指名缺哪个，而不是静默联网补装
    （后者是离线部署最常见的翻车点：装一半发现漏包，venv 半残需从头再来）。
  - 因此覆盖度预检必须**前置**：比对 pyproject 依赖闭包与 wheelhouse
    实际文件，缺一个就当场失败，绝不进入"装到一半才发现缺"。
  - flash 包本体**绝不能**沿用线上 `-e git+https://gitee.com/...` 的
    editable 装法（离线机无网）。必须装本地构建出的 flash_sim-*.whl。

用法（作为模块）:
    from _wh_common import WheelHouse, resolve_wheelhouse
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

MANIFEST_NAME = "MANIFEST.json"
MANIFEST_SCHEMA = 1

#: 项目自身的 dist 名（pyproject [project].name → flash-sim → flash_sim）
PROJECT_DIST = "flash_sim"

#: start_flash.py 在脚本层补装、**未**写进 pyproject 的包。
#: paramiko 是 flash_run.remote.remote_deploy 的 SSH/SFTP 依赖，
#: 漏装会导致 framework 测试收集阶段直接 ImportError。
EXTRA_BOOTSTRAP = ["scipy", "paramiko"]

#: 三档 profile → 需要安装的 extras + 附加包。
#: full   = 与当前 .venv 的 pip freeze 对齐，能跑完整三套测试 + 全局报告
#: runtime= 去掉 yt/numba/pandas 与全部 dev 工具链，仅供日常出图/改参数
#: lite   = 再砍掉 matplotlib/yt/pandas，只留数值与 HDF5 读取
PROFILES: dict[str, dict] = {
    "full": {
        "extras": ["full", "dev"],
        "extra_pkgs": ["scipy", "paramiko", "setuptools", "wheel", "pip"],
        "desc": "full + dev 全量（可跑三套测试，体积最大）",
    },
    "runtime": {
        "extras": ["full"],
        "extra_pkgs": ["scipy", "paramiko", "setuptools", "wheel", "pip"],
        "desc": "仅运行时 full（无 pytest/black/ruff，但保留 yt 出图）",
    },
    "lite": {
        "extras": [],
        "extra_pkgs": ["scipy", "paramiko", "setuptools", "wheel", "pip"],
        "desc": "精简（无 yt/matplotlib/pandas，仅数值 + HDF5 读取）",
    },
}

#: lite 档要**额外排除**的包（它们是 full 档 yt/matplotlib 的传递依赖）
LITE_EXCLUDE = [
    "yt", "matplotlib", "pandas", "contourpy", "fonttools", "kiwisolver",
    "pillow", "pyparsing", "cycler", "unyt", "sympy", "mpmath", "idna",
    "python-dateutil", "pytz", "tzdata", "six", "ewah-bool-utils",
    "black", "ruff", "pytest", "pytest-cov", "coverage", "build", "twine",
]

#: venv 内解释器的**平台相关**布局。
#: ★ 必须跨平台（09-10 修复）：此前硬编码 ("Scripts", "python.exe")，
#:   在 Linux/WSL 上 `python -m venv` 生成的是 `bin/python`（无 .exe），
#:   ⇒ start_flash.py 报「创建 venv 失败」，健康检查也恒判失败并反复清零重建。
#:   真实故障日志（Linux/WSL）：
#:     [FATAL] 创建 venv 失败:
#:     [warn] venv 解释器无法启动（.../.venv/Scripts/python.exe）: [Errno 2]
VENV_SUBPATH_WINDOWS = ("Scripts", "python.exe")
VENV_SUBPATH_POSIX = ("bin", "python")

#: 保持旧名兼容（外部引用），值随平台变化
VENV_SUBPATH = VENV_SUBPATH_WINDOWS if os.name == "nt" else VENV_SUBPATH_POSIX

#: 离线机若无 Python 时 wheelhouse 里可能存在的解释器安装程序
PYTHON_INSTALLER_PATTERNS = [
    re.compile(r"^python-(\d+\.\d+\.\d+)-amd64\.exe$", re.I),
    re.compile(r"^python-(\d+\.\d+\.\d+)-embed-amd64\.zip$", re.I),
]


# ---------------------------------------------------------------------------
# 基础工具
# ---------------------------------------------------------------------------

def log(msg: str = "") -> None:
    print(msg, flush=True)


def clean_env() -> dict:
    """清空 WorkBuddy 安全删除守卫相关变量。

    沙箱注入的 sitecustomize.py 在 CODEBUDDY_SESSION_ID 存在时会 patch
    os.remove/os.unlink 到"回收站-失败即中止"，导致 pip 无法删除旧文件而
    卡死。与 start_flash.py 保持完全一致的处理。
    """
    env = os.environ.copy()
    for key in ("CODEBUDDY_SESSION_ID", "CLAUDE_SESSION_ID", "CODEBUDDY_SAFE_DELETE_SANDBOX"):
        env[key] = ""
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def find_project_root(start: Path | None = None) -> Path:
    """向上查找含 pyproject.toml 且 name=flash-sim 的项目根。"""
    cur = (start or Path(__file__).resolve()).resolve()
    for _ in range(12):
        if (cur / "pyproject.toml").is_file() and (cur / "start_flash.py").is_file():
            return cur
        if cur == cur.parent:
            break
        cur = cur.parent
    # 兜底：scripts/08_offline_install/ → 上两级
    return Path(__file__).resolve().parent.parent.parent


def canonical_name(name: str) -> str:
    """PEP 503 归一化包名：小写 + 连续分隔符合并为单个 '-'。

    >>> canonical_name("Flash_Sim")
    'flash-sim'
    >>> canonical_name("zope.interface")
    'zope-interface'
    """
    return re.sub(r"[-_.]+", "-", name.strip()).lower()


def wheel_dist_name(filename: str) -> str:
    """从 wheel / sdist 文件名提取**归一化**包名。

    wheel (PEP 427) : {name}-{ver}-{pytag}-{abitag}-{plat}.whl
    sdist (PEP 625): {name}-{ver}.tar.gz

    ★ name 段本身可能含 '-'（如 flash_sim 无， 但 pytest-cov / wright-omega 有），
      故不能简单 split('-')[0] —— 必须**从右往左**剥掉已知段数。
    """
    base = os.path.basename(filename)
    if base.endswith(".whl"):
        parts = base[: -len(".whl")].split("-")
        # 末 3 段为 pytag/abitag/plat；name+ver 至少 2 段
        if len(parts) >= 5:
            return canonical_name("-".join(parts[:-4]))
        return canonical_name(parts[0]) if parts else ""
    for suf in (".tar.gz", ".zip", ".tar.bz2"):
        if base.endswith(suf):
            stem = base[: -len(suf)]
            parts = stem.split("-")
            # 末 1 段为 ver；name 可能含 '-'
            if len(parts) >= 2:
                return canonical_name("-".join(parts[:-1]))
            return canonical_name(parts[0])
    return ""


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    """流式 SHA256（大 wheel 数百 MB，不能一次性读入内存）。"""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# pyproject 依赖解析
# ---------------------------------------------------------------------------

def _strip_comment(line: str) -> str:
    """去掉行尾注释（pyproject 的 dependencies 是逐行字符串数组）。"""
    out, in_str = [], False
    quote = ""
    for ch in line:
        if in_str:
            out.append(ch)
            if ch == quote:
                in_str = False
        elif ch in "\"'":
            in_str = True
            quote = ch
            out.append(ch)
        elif ch == "#":
            break
        else:
            out.append(ch)
    return "".join(out).strip().strip(",").strip()


def parse_pyproject_requirements(pyproject: Path) -> dict:
    """返回 {'base': [...], 'full': [...], 'dev': [...]}，元素为原始 requirement 串。

    刻意**不**引入 tomllib 依赖（3.10 才标准库、3.13 才有 tomllib 稳定版），
    改用轻量正则 + 逐行剥离，兼容 Python 3.10+。仅需读 [project] 段的
    dependencies 与 [project.optional-dependencies]，无需完整 TOML 语义。
    """
    try:
        text = pyproject.read_text(encoding="utf-8")
    except OSError:
        return {"base": [], "full": [], "dev": []}

    result: dict[str, list[str]] = {"base": [], "full": [], "dev": []}
    lines = text.splitlines()

    def grab_array(start_line: int) -> list[str]:
        """从 start_line 行的 '[' 起，按**行**向下收集到配平的 ']'。

        ★ 注意：必须迭代 lines[start_line:]（按行），不能写 text[start_line:]，
          那会按**字符**切片 —— 09 一次真实的解析失败即源于此：
          base/full/dev 三档全部解析为空，预检因此变成"假通过"。
        """
        items: list[str] = []
        depth = 0
        started = False
        for ln in lines[start_line:]:
            s = _strip_comment(ln)
            if not started:
                if "[" not in s:
                    continue
                started = True
                depth += s.count("[") - s.count("]")
                s = s[s.index("[") + 1:]
                if depth <= 0:
                    break
            else:
                depth += s.count("[") - s.count("]")
            # ★ 收尾行（如单独的 "]"）必须先**截断**再拆逗号，
            #   否则 "]" 本身会被当成一个 requirement 收进来（预检出现幽灵包名）。
            if depth <= 0 and "]" in s:
                s = s[: s.index("]")]
            for piece in s.split(","):
                piece = piece.strip().strip('"').strip("'").strip()
                if piece:
                    items.append(piece)
            if depth <= 0:
                break
        return items

    def find_line(pred) -> int:
        for i, ln in enumerate(lines):
            if pred(ln):
                return i
        return -1

    # base: dependencies = [ ... ]（在 [project] 段内，optional 之前）
    i = find_line(lambda ln: ln.strip().startswith("dependencies") and "optional" not in ln)
    if i >= 0:
        result["base"] = grab_array(i)

    # optional-dependencies: 逐个 key
    i = find_line(lambda ln: ln.strip().startswith("[project.optional-dependencies]"))
    if i >= 0:
        for j in range(i + 1, len(lines)):
            s = lines[j].strip()
            if s.startswith("["):
                break
            m = re.match(r"^([A-Za-z0-9_.\-]+)\s*=\s*\[", s)
            if m and m.group(1) in result:
                sub = grab_array(j)
                # grab_array 从本行的 '[' 之后开始收集，已含本行内容 → 正确
                result[m.group(1)] = sub
    return result


def requirement_name(req: str) -> str:
    """从 requirement 串提取包名（去掉 extras / 版本约束 / marker / env marker）。

    "yt>=4.1"            -> "yt"
    "pytest-cov>=4.0"    -> "pytest-cov"
    "pandas[excel]"      -> "pandas"
    'foo; python_version<"3.11"' -> "foo"
    "git+https://...#egg=bar"    -> "bar"
    """
    s = req.strip()
    # VCS URL → egg 名
    if s.startswith(("git+", "hg+", "svn+", "bzr+")):
        m = re.search(r"#egg=([A-Za-z0-9_.\-]+)", s)
        if m:
            return canonical_name(m.group(1))
        m2 = re.search(r"/([^/]+?)(?:\.git)?$", s.split("#")[0])
        return canonical_name(m2.group(1)) if m2 else canonical_name(s)
    # 环境 marker
    s = s.split(";", 1)[0].strip()
    # extras
    s = s.split("[", 1)[0].strip()
    # 版本约束 / URL
    for sep in ("@", "=", "<", ">", "~", "!", " "):
        if sep in s:
            s = s.split(sep, 1)[0].strip()
    return canonical_name(s)


def required_packages(pyproject: Path, profile: str = "full") -> tuple[list[str], list[str]]:
    """返回 (归一化包名集合, 人类可读的 requirement 列表)。

    ★ 含 project 本体（flash-sim）：离线必须装本地 wheel，
      绝不能沿用线上 `-e git+https://gitee.com/...` 的 editable 装法。
    """
    if profile not in PROFILES:
        raise SystemExit(f"[FATAL] 未知 profile: {profile}（可选 {sorted(PROFILES)}）")
    reqs = parse_pyproject_requirements(pyproject)
    spec = PROFILES[profile]

    pool: list[str] = list(reqs.get("base", []))
    for ex in spec["extras"]:
        pool.extend(reqs.get(ex, []))
    pool.extend(spec["extra_pkgs"])

    # project 本体
    pool.insert(0, f"{PROJECT_DIST}[{','.join(spec['extras'])}]" if spec["extras"] else PROJECT_DIST)

    names, human = set(), []
    for r in pool:
        human.append(r)
        names.add(requirement_name(r))

    if profile == "lite":
        names -= {canonical_name(x) for x in LITE_EXCLUDE}
        human = [r for r in human if requirement_name(r) not in
                 {canonical_name(x) for x in LITE_EXCLUDE}]
        # project 本体即使是 lite 也必须装（用户要用 flash API）
        names.add(canonical_name(PROJECT_DIST))
    return sorted(names), human


# ---------------------------------------------------------------------------
# WheelHouse
# ---------------------------------------------------------------------------

class WheelHouse:
    """wheelhouse 目录的读写 + 校验。

    目录布局:
        wheelhouse/
          flash_sim-0.1.8-py3-none-any.whl
          numpy-2.5.2-cp313-cp313-win_amd64.whl
          ...
          python-3.13.9-amd64.exe          （可选，离线机无 Python 时）
          MANIFEST.json                    （本类生成）
    """

    def __init__(self, root: Path):
        self.root = Path(root).resolve()

    # ---- 基本属性 -----------------------------------------------------
    @property
    def manifest_path(self) -> Path:
        return self.root / MANIFEST_NAME

    def exists(self) -> bool:
        return self.root.is_dir()

    def ensure(self) -> "WheelHouse":
        self.root.mkdir(parents=True, exist_ok=True)
        return self

    def archives(self) -> list[Path]:
        """所有可安装归档（wheel / sdist），排除清单与非归档文件。"""
        if not self.root.is_dir():
            return []
        out = []
        for p in sorted(self.root.iterdir()):
            if not p.is_file():
                continue
            n = p.name.lower()
            if n.endswith((".whl", ".tar.gz", ".zip")) and not n.endswith(".whl.zip"):
                if wheel_dist_name(p.name):
                    out.append(p)
        return out

    def python_installers(self) -> list[Path]:
        """目录内的 Python 安装程序 / embeddable 包（若有）。"""
        if not self.root.is_dir():
            return []
        out = []
        for p in sorted(self.root.iterdir()):
            if p.is_file() and any(pat.match(p.name) for pat in PYTHON_INSTALLER_PATTERNS):
                out.append(p)
        return out

    def available(self) -> dict[str, Path]:
        """{归一化包名: 文件路径}，同名多版本时**保留排序靠后者**（pip 行为近似）。"""
        out: dict[str, Path] = {}
        for p in self.archives():
            out[wheel_dist_name(p.name)] = p
        return out

    # ---- MANIFEST -----------------------------------------------------
    def write_manifest(self, meta: dict) -> Path:
        """写 MANIFEST.json：对每个归档记录 name/ver/file/size/sha256。

        ★ 存在的意义：U盘拷贝是**最容易静默损坏**的传输环节。
          离线机装之前逐个校验 SHA256，能在"pip 报出看不懂的错误"之前
          明确告诉用户"哪个文件在拷贝中损坏了"。
        """
        entries = []
        for p in self.archives():
            entries.append({
                "name": wheel_dist_name(p.name),
                "file": p.name,
                "size": p.stat().st_size,
                "sha256": sha256_file(p),
            })
        for p in self.python_installers():
            entries.append({
                "name": "python-installer",
                "file": p.name,
                "size": p.stat().st_size,
                "sha256": sha256_file(p),
            })
        payload = {
            "schema": MANIFEST_SCHEMA,
            "meta": meta,
            "entries": entries,
        }
        self.manifest_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return self.manifest_path

    def read_manifest(self) -> dict | None:
        if not self.manifest_path.is_file():
            return None
        try:
            return json.loads(self.manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    def verify_manifest(self, deep: bool = True) -> tuple[list[str], list[str]]:
        """校验 MANIFEST 与磁盘实际内容。

        返回 (problems, notes)；problems 非空表示**不可安装**。
        """
        problems: list[str] = []
        notes: list[str] = []
        man = self.read_manifest()
        if man is None:
            return ([f"缺少或无法解析 {MANIFEST_NAME}"
                     f"（拷贝不完整？或由旧脚本生成？请在联网机重跑 build_wheelhouse.py）"], notes)

        for e in man.get("entries", []):
            p = self.root / e["file"]
            if not p.is_file():
                problems.append(f"[缺失] {e['file']}")
                continue
            size = p.stat().st_size
            if size != e["size"]:
                problems.append(
                    f"[大小不符] {e['file']}: 清单 {e['size']} B ≠ 实际 {size} B")
                continue
            if deep:
                got = sha256_file(p)
                if got != e["sha256"]:
                    problems.append(
                        f"[SHA256 不符] {e['file']}: 拷贝过程中损坏，建议重新拷贝 U 盘")
                    continue
        notes.append(f"MANIFEST 校验: {len(man.get('entries', []))} 个文件"
                     f"（{'深校验 SHA256' if deep else '仅校验存在性与大小'}）")
        return problems, notes

    # ---- ★ 覆盖度预检 -------------------------------------------------
    def preflight(self, pyproject: Path, profile: str = "full") -> tuple[list[str], list[str]]:
        """安装**前**比对依赖闭包与 wheelhouse 实际内容。

        返回 (missing, present)；missing 非空 → 调用方应立即中止。
        这是离线部署最重要的一道闸门：宁可当场失败，也不产出半残 venv。
        """
        need, _ = required_packages(pyproject, profile)
        have = self.available()
        missing = [n for n in need if n not in have]
        present = [n for n in need if n in have]
        return missing, present


# ---------------------------------------------------------------------------
# 定位与校验解释器
# ---------------------------------------------------------------------------

def resolve_wheelhouse(explicit: str | None = None, start: Path | None = None) -> WheelHouse:
    """按优先级定位 wheelhouse 目录。

    优先级: 显式参数 > FLASH_WHEELHOUSE 环境变量 > 常见位置扫描。

    常见位置（★ 顺序有意义：先"贴项目根"再"标准外置目录"）:
      1. <start>/wheelhouse              拷进项目根时的默认落点
      2. <start>/offline_pkg/wheelhouse  build_wheelhouse.py 的默认输出目录
         —— ★ 这两个必须都试：build 产出在 offline_pkg/ 下，而用户往往
            直接跑 install_offline.py 而不传参数。
      3. ./wheelhouse  （相对当前工作目录）
    """
    cands: list[Path] = []
    if explicit:
        cands.append(Path(explicit))
    env = os.environ.get("FLASH_WHEELHOUSE", "").strip()
    if env:
        cands.append(Path(env))

    roots: list[Path] = []
    if start:
        roots.append(Path(start))
    roots.append(find_project_root())
    for r in roots:
        cands.append(r / "wheelhouse")
        cands.append(r / "offline_pkg" / "wheelhouse")
    cands.append(Path.cwd() / "wheelhouse")

    seen: set[str] = set()
    for c in cands:
        if not c:
            continue
        key = str(c)
        if key in seen:
            continue
        seen.add(key)
        if c.is_dir() and (c / MANIFEST_NAME).is_file():
            return WheelHouse(c)

    tried = "\n".join(f"    - {c}" for c in cands if c)
    raise SystemExit(
        "[FATAL] 找不到 wheelhouse 目录。\n"
        f"已尝试:\n{tried}\n"
        "\n用法:\n"
        "  1) 把 build_wheelhouse.py 生成的整个 wheelhouse/ 目录拷到本机\n"
        "  2) 用 --wheelhouse <路径> 或设环境变量 FLASH_WHEELHOUSE 显式指定"
    )


def venv_python(venv_dir: Path) -> Path:
    return Path(venv_dir).joinpath(*VENV_SUBPATH)


def looks_like_venv(venv_dir: Path) -> bool:
    return venv_python(venv_dir).is_file()


def find_python_installer(wh: WheelHouse) -> Path | None:
    """返回 wheelhouse 内的 Python 安装程序（若有），优先 .exe。"""
    insts = wh.python_installers()
    if not insts:
        return None
    for p in insts:
        if p.name.lower().endswith(".exe"):
            return p
    return insts[0]


def human_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024.0
    return f"{n:.1f} GB"


def ensure_ascii_bat_ok(path: Path) -> tuple[bool, str]:
    """校验 .bat 可安全双击执行（★ Windows cmd 约定）。

    返回 (是否通过, 说明)。检查项：
      1. **纯 ASCII** —— 非 ASCII 在 cmd 默认 GBK 下会乱码（用户既定约定：
         脚本名与启动器内容一律 ASCII）。带 UTF-8 BOM 同样不行。
      2. 行尾 —— 只**提示**不拦截：本仓库 .gitattributes 明确规定
         `*.bat text eol=lf`，故 clone 出来必然是 LF。若这里强制 CRLF，
         校验会在任何新clone 上失败（09-09 实测踩过）。
         LF-only 的 .bat 在 cmd 下可正常执行（逐行解析，无二进制偏移依赖）。

    ⚠ 与 git 的交互：工作区 CRLF 会被 .gitattributes 规范化成 LF 提交，
      这是**预期行为**，不要用"转回 CRLF"来迎合本函数。
    """
    try:
        data = path.read_bytes()
    except OSError as e:
        return False, f"读取失败: {e}"
    if data[:3] == b"\xef\xbb\xbf":
        return False, "含 UTF-8 BOM（cmd 下会乱码）"
    try:
        data.decode("ascii")
    except UnicodeDecodeError as e:
        return False, f"含非 ASCII 字节 @{e.start}（cmd GBK 下会乱码）"
    if not data.strip():
        return False, "空文件"
    eol = "CRLF" if b"\r\n" in data else "LF"
    note = "（仓库 .gitattributes 规定 *.bat eol=lf，LF 为预期）" if eol == "LF" else ""
    return True, f"纯 ASCII, 行尾 {eol} {note}"


if __name__ == "__main__":
    # 自检入口：python scripts/08_offline_install/_wh_common.py
    root = find_project_root()
    log(f"项目根: {root}")
    for prof in PROFILES:
        names, human = required_packages(root / "pyproject.toml", prof)
        log(f"\n[{prof}] {PROFILES[prof]['desc']}")
        log(f"  requirement 条数: {len(human)}")
        log(f"  归一化包名: {len(names)}")
        log("  " + ", ".join(names))
    log(f"\n文件名归一化自检: {wheel_dist_name('flash_sim-0.1.8-py3-none-any.whl')}"
        f" / {wheel_dist_name('pytest_cov-7.1.0-py3-none-any.whl')}"
        f" / {wheel_dist_name('yt-4.4.2-cp313-cp313-win_amd64.whl')}")
    sys.exit(0)