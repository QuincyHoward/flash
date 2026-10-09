#!/usr/bin/env python
"""wheel/sdist 泄漏审计：找出 git 忽略却被打进包里的文件。

为什么需要它
------------
`.gitignore` 只管 git，wheel/sdist 由 hatchling 的 `exclude` 决定，两者**独立**。
本仓库根 `.gitignore:11`有一条裸 `*`，而 hatchling 的 VCS 排除有安全阀::

    exclude_spec = pathspec.GitIgnoreSpec.from_lines(patterns)
    if exclude_spec.match_file(self.root):
        return []      # ← 静默丢弃**全部** VCS 规则

裸 `*` 匹配到项目根自身 ⇒ 命中安全阀 ⇒ 536 条 .gitignore 规则**全部失效**。
于是 git 忽略的测试产物、FLASH 引擎源码（License §3）会被一并打包。
⇒ 本脚本是**回归护栏**：构建后跑一次，越界即非零退出。

用法::

    python scripts/08_offline_install/wheel_leak_audit.py            # 默认 wheelhouse
    python scripts/08_offline_install/wheel_leak_audit.py <wheel>     # 指定 wheel

退出码：0 = 通过（残余在容差内）；1 = 超容差；2 = 用法/环境错误。

★★ **报喜不报忧的护栏比没有护栏更危险**（09-10 教训）
   本脚本首版用 `subprocess.run(text=True)` 喂 `git check-ignore`，Windows 走
   ANSI 代码页（GBK/cp1252），CJK 路径被弄坏 ⇒ 同一输入报 1733 条 vs 正确
   1855 条，**漏报 94.5%**，差点让一个 100.5MB 的 wheel 通过审计。
   ⇒ 必须喂 **bytes** 并自行 UTF-8 解码（见 `git_ignored`）。改此处务必重测。
"""
from __future__ import annotations

import collections
import subprocess
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent

#: 默认 wheelhouse（造包脚本的默认输出位置）
DEFAULT_DIRS = (
    ROOT / ".workbuddy/tmp/_whv3/wheelhouse",
    ROOT / ".workbuddy/tmp/_whv2/wheelhouse",
    ROOT / ".workbuddy/tmp/_whcheck",
)

# ---------------------------------------------------------------- 容差
#: git-ignored 残余的**体积**容差。09-10 第三轮实测：修正 private/tracer 整目录
#: 误排除后，残余54 个文件 / 554KB（占 wheel 0.1%），全是 results/*.json、
#: metrics_*.csv 这类**科研结果快照**——它们 git 不跟踪，但体积可忽略，
#: 且对离线使用者有参考价值。⇒ 按**体积**判定，不按文件数判定。
LEAK_BYTES_OK = 2 * 1024 * 1024      # 2 MB

#: 单文件体积上限：超过这个数说明 exclude 又漏了整目录（09-10 的 275MB _out/）
LEAK_FILE_BYTES_OK = 256 * 1024      # 256 KB

#: 正常 wheel 体积区间（09-10 实测 4.76MB；修正误排除后 5.5MB / 1028 条目）
WHEEL_BYTES_OK = (1 * 1024 * 1024, 20 * 1024 * 1024)
WHEEL_ENTRIES_OK = (400, 4000)

# FLASH License §3：引擎源码 / EOS 分发表绝不可随 release 分发。
#
# ★★ 必须按**路径分量**（path part）精确匹配，不能用 `in name` 子串 ——
#   09-10 实测误报：`MultiEOSOP格式说明.md`（自研文档，git 已跟踪）因文件名
#   含 "MultiEOS" 子串被判成 §3 材料。子串匹配会把 `helm_table.dat.example`、
#   `notes_about_Multi1D.md` 之类一并误报。
#   正确判据：这些名字必须是**独立的路径分量或带分隔符的目录名**。
FLASH_STRONG_PARTS = frozenset({
    "flash_src",
    "SimulationMain",
    "MultiEOS",
    "helm_table.dat",
    "abjt_03.f",
    "FLASH_eos_op_data",
})
#: 需要整体目录名匹配的（便携包/二进制目录）
FLASH_STRONG_DIRS = ("Multi1D++",)

#: 打包元数据目录：由hatchling 在构建时生成，天然不在 git 里，
#   不算「泄漏」（否则每次审计都报2 条假阳性）。
DIST_INFO = ".dist-info/"


def git_ignored(paths: list[str]) -> set[str]:
    """返回被 git 忽略的路径集合（一次调用批量查 N 条）。

    ★ MUST feed **bytes**, not str: on Windows `text=True` decodes with the
      ANSI code page (GBK/cp1252), which both mangles the CJK paths and
      silently drops matches — measured 1733 matched vs 1855 for the same
      input. A guard that under-reports is worse than no guard, because it
      green-lights a bloated wheel. Decode the response as UTF-8 ourselves.
    """
    if not paths:
        return set()
    r = subprocess.run(
        ["git", "check-ignore", "--stdin", "-z", "--no-index"],
        input=b"\0".join(p.encode("utf-8") for p in paths),
        capture_output=True,
        cwd=ROOT,
    )
    if r.returncode not in (0, 1):
        raise RuntimeError(f"git check-ignore 失败 rc={r.returncode}: {r.stderr[:200]!r}")
    return {b.decode("utf-8", "replace") for b in r.stdout.split(b"\0") if b.strip()}


def is_flash_material(name: str) -> bool:
    """是否含 FLASH License §3 强证据材料（**按路径分量**判定，见 FLASH_STRONG_PARTS）。"""
    parts = name.split("/")
    if any(p in FLASH_STRONG_PARTS for p in parts):
        return True
    # 带扩展名/后缀的目录名（如 Multi1D++Portable3.0/）
    return any(p.startswith(FLASH_STRONG_DIRS) for p in parts[:-1])


def pick_wheel(explicit: str | None) -> Path:
    if explicit:
        p = Path(explicit)
        if p.is_file():
            return p
        cands = sorted(p.glob("flash_sim-*.whl")) if p.is_dir() else []
        if cands:
            return cands[-1]
        raise SystemExit(f"[FATAL] 找不到 wheel: {explicit}")
    for d in DEFAULT_DIRS:
        if d.is_dir():
            c = sorted(d.glob("flash_sim-*.whl"))
            if c:
                return c[-1]
    raise SystemExit("[FATAL] 未找到 wheel，请先跑 build_wheelhouse.py 或显式给路径")


def main() -> int:
    wh = pick_wheel(sys.argv[1] if len(sys.argv) > 1 else None)
    with zipfile.ZipFile(wh) as z:
        # dist-info/ 是 hatchling 构建时生成的打包元数据，天然不在 git 里，
        # 不属于「泄漏」，须先剔除，否则每次审计都有 2 条假阳性。
        infos = [
            i for i in z.infolist()
            if not i.is_dir() and DIST_INFO not in i.filename
        ]
    names = [i.filename for i in infos]
    total = sum(i.file_size for i in infos)
    wsize = wh.stat().st_size

    print(f"wheel   : {wh}")
    print(f"entries : {len(infos)}")
    print(f"压缩/解压: {wsize/1048576:.2f} MB / {total/1048576:.1f} MB")
    print()

    fails: list[str] = []

    # ---- 1. 体积 / 条目哨兵 ----------------------------------------
    ok_lo, ok_hi = WHEEL_BYTES_OK
    if not (ok_lo <= wsize <= ok_hi):
        fails.append(f"wheel 体积 {wsize/1048576:.2f}MB 越界 "
                     f"[{ok_lo/1048576:.0f}, {ok_hi/1048576:.0f}]MB")
    lo, hi = WHEEL_ENTRIES_OK
    if not (lo <= len(infos) <= hi):
        fails.append(f"条目数 {len(infos)} 越界 [{lo}, {hi}]")

    # ---- 2. FLASH License §3 ---------------------------------------
    flash_hits = [n for n in names if is_flash_material(n)]
    if flash_hits:
        fails.append(f"FLASH License §3 材料入包 {len(flash_hits)} 个")

    # ---- 3. git-ignored 泄漏（按体积，不按文件数）-------------------
    ignored = git_ignored(names)
    leak_by_dir: collections.Counter = collections.Counter()
    leak_bytes: collections.Counter = collections.Counter()
    big = []
    for i in infos:
        if i.filename not in ignored:
            continue
        key = "/".join(i.filename.split("/")[:5])
        leak_by_dir[key] += 1
        leak_bytes[key] += i.file_size
        if i.file_size > LEAK_FILE_BYTES_OK:
            big.append((i.file_size, i.filename))
    leak_total = sum(leak_bytes.values())
    if leak_total > LEAK_BYTES_OK:
        fails.append(f"git-ignored 残余 {leak_total/1024:.0f}KB "
                     f"超容差 {LEAK_BYTES_OK/1024:.0f}KB")
    if big:
        big.sort(reverse=True)
        fails.append(f"{len(big)} 个单文件超{LEAK_FILE_BYTES_OK/1024:.0f}KB")

    # ---- 报告 ------------------------------------------------------
    print(f"★ FLASH License §3 材料入包: {len(flash_hits)}")
    for n in flash_hits[:10]:
        print("   -", n)

    print(f"★ git-ignored 但入包: {len(ignored)} 个文件 / "
          f"{leak_total/1024:.1f} KB "
          f"({leak_total*100.0/max(total,1):.2f}% of wheel, "
          f"容差 {LEAK_BYTES_OK/1024:.0f}KB)")
    for k, v in leak_bytes.most_common(8):
        print(f"   {v/1024:8.1f} KB  x{leak_by_dir[k]:4d}  {k}")
    if big:
        print("   ★ 超大单文件:")
        for s, n in big[:8]:
            print(f"     {s/1024:9.1f} KB  {n}")

    print()
    if fails:
        print("[FAIL] " + "; ".join(fails))
        return 1
    print("[ok] 体积/条目/§3/泄漏 四项均在容差内")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
