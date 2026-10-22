#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""patch_job.py — 超算 public 场景作业脚本补丁器（远端执行，纯标准库）。

★ 为什么不用 sed：三个 public 场景的 ``submit_flash.sh`` 形态差异极大 ——
  - ``ch_center``          ：``#SBATCH --output=FILE``（长选项，无 --partition? 有）
  - ``grad_dens_sandwich`` ：``#SBATCH -o NAME_%%j.out``（短选项 + ``%%j``）
  - ``thin_layer_sandwich``：``#SBATCH --job-name=grid_rede --output=... --partition=...
                              --ntasks=4 --time=01:00:00``（★ 一行多个选项）
  行级 sed 无法可靠处理「一行多选项」，且 ``(`` ``)`` 转义在远端 shell 里极易报错。
  ⇒ 统一在本脚本里用 shlex 解析 #SBATCH 指令，逐指令改写。

补丁内容（只改「跑在哪、跑到哪、多久」，**不改物理**）：
  ① ``--output/--error``  → 并行盘（★ 绝不用 /tmp，作业结束即丢且跨节点不可见）
  ② 运行目录（``R=`` / ``OUTPUT_DIR=``）→ 并行盘
  ③ ``--time`` 统一 01:00:00；补 ``--partition``（默认分区在本站点 inactive）
  ④ 删除 ``module purge``（会清掉 hdf5/oneAPI 路径 —— 2026-10-22 in-situ 实测铁律）
  ⑤ 环境块插到 **所有 #SBATCH 之后、正文之前**
     （★ SLURM 只在脚本首个非注释行之前解析 #SBATCH ⇒ 环境块放最前面会让
      所有调度指令失效：作业落默认分区、无时限。）

用法（远端）：
  python patch_job.py --in submit_flash.sh --out job.sh \
      --work /publicfs01/.../flash_sim_public_runs --tag ch_center \
      --partition v5_192 --time 01:00:00
"""
from __future__ import annotations

import argparse
import re
import shlex
import sys
from pathlib import Path

#: 取值型 #SBATCH 选项（值可能独立成一个 token，也可能 ``=`` 紧跟）
VALUE_OPTS = {
    "-o", "--output", "-e", "--error", "-J", "--job-name", "-p", "--partition",
    "-t", "--time", "-n", "--ntasks", "-N", "--nodes", "--mem", "--gres",
    "--cpus-per-task", "--exclude", "--nodelist", "--account", "-D",
    "--chdir", "--output-dir", "--mail-user", "--dependency",
}

#: 环境块模板（插在 #SBATCH 之后、正文之前）
#:
#: ★★★ 2026-10-23 定位的 QC 树运行期环境铁律（探针实测，见 docs/FLASH三模式运行体系.md §8）
#:
#: 站点 `module load mpich/3.2-gcc9.3` **实际解析到 Intel 2018 MPI**
#: （/public1/soft/intel/2018/.../mpi/intel64/bin/mpirun），其 libmpi.so.12
#: **不含 `MPII_F_TRUE` 符号** ⇒ 链接期有、运行期无 ⇒
#: `libmpifort.so.12: undefined symbol: MPII_F_TRUE`。
#: 此前误判为「oneAPI 2022.1 安装错配（Frankenstein）」，实为**两个真因叠加**：
#:   ① 注入的 oneAPI 库路径写错（`oneAPI/2022.1/lib` 不存在，真实在
#:      `oneAPI/2022.1/mpi/latest/lib`），oneAPI 的 libmpi 与站点默认的
#:      Intel 2018 libmpi **同名 soname 互相覆盖**；
#:   ② flash4 还需 `libgfortran.so.5`（gcc 8.1.0）与 Intel compiler runtime
#:      `libimf.so`（oneAPI/compiler/2022.0.0/.../intel64_lin），缺一即
#:      `error while loading shared libraries`。
#:
#: ✅ 探针实测通过的组合（**不要**注入 oneAPI MPI 路径！）：
#:    module load mpich/3.2-gcc9.3   → 站点 mpich（配套 libmpi 含 MPII_F_TRUE）
#:    module load hdf5/1.8.18        → libhdf5.so.10
#:    + gcc/9.3.0-new/lib64          → libgfortran.so.5（★ 必须 ≥9.3）
#:    ⇒ FLASH 完整初始化 → 推进时间步 → 写出 hdf5 chk（计算节点实测通过）
#:
#: ★ 为何不用 gcc/8.1.0：mpich/3.2 的 libmpifort.so.12 需要 `GFORTRAN_9`
#:   符号版本，gcc 8.1.0 的 libgfortran.so.5 只到 GFORTRAN_5 ⇒
#:   "version `GFORTRAN_9' not found"。
#: ★ 为何不用 oneAPI MPI：oneAPI 与站点 mpich 提供**同名 soname**
#:   (libmpi.so.12 / libmpifort.so.12)，同时进 LD_LIBRARY_PATH 会互相覆盖，
#:   混用即产生 undefined symbol。
ENV_BLOCK = """\
# ── flash-sim 超算部署链：环境补丁（由 patch_job.py 插入）──────────
# ★ 禁 module purge：会清掉 hdf5 / compiler runtime 路径（2026-10-22 实测铁律）
source /public1/soft/modules/module.sh 2>/dev/null || true
module load hdf5/1.8.18 2>/dev/null || true
module load mpich/3.2-gcc9.3 2>/dev/null || true
# ★ gfortran 5（gcc ≥9.3）—— flash4 依赖 libgfortran.so.5
for _d in /public1/soft/gcc/9.3.0-new/lib64 /public1/soft/gcc/9.1.0/lib64; do
  if [ -d "$_d" ]; then export LD_LIBRARY_PATH="$_d:$LD_LIBRARY_PATH"; break; fi
done
unset _d
# ── end env ─────────────────────────────────────────────────────────
"""


def _parse_sbatch(line: str) -> list[str]:
    """把一行 ``#SBATCH ...`` 拆成 (option, value) 之外的 token 列表。"""
    body = line.strip()[len("#SBATCH"):].strip()
    try:
        return shlex.split(body)
    except ValueError:
        return body.split()


def _split_opts(tokens: list[str]) -> list[tuple[str, str | None]]:
    """token 列表 → [(opt, value|None)]，处理 ``--opt=v`` 与 ``--opt v`` 两种形态。"""
    out: list[tuple[str, str | None]] = []
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if "=" in tok and tok.startswith("-"):
            k, _, v = tok.partition("=")
            out.append((k, v))
        elif tok in VALUE_OPTS and i + 1 < len(tokens):
            out.append((tok, tokens[i + 1]))
            i += 1
        else:
            out.append((tok, None))
        i += 1
    return out


def _fmt_opt(k: str, v: str | None) -> str:
    """格式化一条 #SBATCH 指令。

    ★ SLURM **短选项不接受 ``=`` 形式**（``-N=1`` 会被拒）⇒ 单字符选项用空格分隔，
      长选项用 ``--opt=value``。
    """
    if v is None:
        return f"#SBATCH {k}"
    if k.startswith("--"):
        return f"#SBATCH {k}={v}"
    return f"#SBATCH {k} {v}"


def patch_sbatch(lines: list[str], work: Path, tag: str,
                 partition: str, time_limit: str) -> list[str]:
    """重写所有 #SBATCH 行（★ 支持一行多选项）。"""
    out: list[str] = []
    seen: set[str] = set()
    for line in lines:
        if not line.startswith("#SBATCH"):
            out.append(line)
            continue
        opts = _split_opts(_parse_sbatch(line))
        new: list[tuple[str, str | None]] = []
        for k, v in opts:
            if k in ("-o", "--output"):
                new.append(("-o", str(work / "out" / f"{tag}_%j.out")))
            elif k in ("-e", "--error"):
                new.append(("-e", str(work / "out" / f"{tag}_%j.err")))
            elif k in ("-t", "--time"):
                new.append(("--time", time_limit))
            elif k in ("-p", "--partition"):
                new.append(("--partition", partition))
            else:
                new.append((k, v))
        for k, _v in new:
            seen.add(k)
        # 每个选项单独成行（SLURM 允许一行多选项，但拆开更易读与排查）
        for k, v in new:
            out.append(_fmt_opt(k, v))
    # 补齐缺失项
    if "--partition" not in seen and "-p" not in seen:
        out.insert(0, f"#SBATCH --partition={partition}")
    if "--time" not in seen and "-t" not in seen:
        out.insert(0, f"#SBATCH --time={time_limit}")
    return out


#: 运行目录 / 输出目录相关行的替换规则（正则 → 替换模板）
BODY_RULES: list[tuple[re.Pattern[str], str]] = [
    # R=/tmp/flash_xxx  /  R=$SLURM_SUBMIT_DIR/xxx
    (re.compile(r'^(\s*R=)\S+', re.M), r'\1"{RUN}"'),
    # ch_center: OUTPUT_DIR="$SCRIPT_DIR/outputfiles_$(date ...)"
    (re.compile(r'^(\s*OUTPUT_DIR=).+$', re.M), r'\1"{OUT}"'),
    # mkdir -p "$OUTPUT_DIR" → 保留（变量已指向并行盘），无需改
]


def patch_body(text: str, run_dir: Path, out_dir: Path,
               input_dir: Path | None = None) -> str:
    """改写正文：运行目录/输出目录 → 并行盘；删 module purge。

    ``input_dir`` 给定时，额外做两件事：
    ① **输入目录锚定** —— 三个场景取输入目录的写法完全不同：
       ch_center  ``SCRIPT_DIR="${SLURM_SUBMIT_DIR:-$PWD}"``（可用）
       grad_dens  ``SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"``
       thin_layer ``D=$(dirname "$0")``
       ★ `dirname "$0"` 在 sbatch 下指向 **/var/spool/slurm/d/jobXXXX**
         ⇒ 作业里 `cp "$SCRIPT_DIR"/*.par` 必然失败（实测 grad_dens 报
         `cp: cannot stat '/var/spool/slurm/d/job4918047/*.par'`）。
       ⇒ 统一改写为固定的输入目录（并行盘）。
    ② **MPI 环境归一** —— thin_layer 原本 `module load mpi/hpcx/2.17.1`
       （Intel HPC-X），用它编译 FLASH 会报 Fortran 语法错
       （`error #6404: This name does not have a type`）⇒ 统一改用
       站点已验证的 `mpich/3.2-gcc9.3`。
    """
    # ① module purge —— 铁律：会清掉 hdf5 / oneAPI 路径
    text = re.sub(r'(?m)^[ \t]*module[ \t]+purge\b.*$', '# [patched] module purge removed', text)
    # ② 运行目录 / 输出目录
    #    ★ 用 lambda 替换而非 \1 模板：Windows 下路径含反斜杠会被 re 当转义序列
    #      （bad escape \P）—— 远端虽无此问题，但本地干跑必须能过。
    #    ★ R= 可能出现在**行中**（thin_layer 是一行多命令的紧凑写法）：
    #      所以锚点取「行首」或「分号后」，值到分号/行尾为止。
    text = re.sub(r'(?m)(^|;)([ \t]*)R=[^;\n]*',
                  lambda m: f'{m.group(1)}{m.group(2)}R="{run_dir}"', text)
    text = re.sub(r'(?m)^(\s*OUTPUT_DIR=).+$',
                  lambda m: f'{m.group(1)}"{out_dir}"', text)
    # ③ MPI 环境归一：Intel HPC-X → 站点 mpich（编译 Fortran 才不报语法错）
    text = re.sub(r'(?m)^([ \t]*module[ \t]+load[ \t]+)mpi/hpcx/[\w.\-]+',
                  r'\1mpich/3.2-gcc9.3', text)
    text = re.sub(r'(?m)(^|;)([ \t]*)module[ \t]+load[ \t]+mpi/hpcx/[\w.\-]+',
                  lambda m: f'{m.group(1)}{m.group(2)}module load mpich/3.2-gcc9.3', text)
    # ④ 输入目录锚定
    if input_dir is not None:
        ind = str(input_dir)
        # SCRIPT_DIR=...  →  SCRIPT_DIR="<ind>"
        text = re.sub(r'(?m)^(\s*SCRIPT_DIR=).+$',
                      lambda m: f'{m.group(1)}"{ind}"', text)
        # D=$(dirname "$0")  →  D="<ind>"
        text = re.sub(r'(?m)^(\s*D=)\$\(dirname\s+"\$0"\)\s*$',
                      lambda m: f'{m.group(1)}"{ind}"', text)
        # 行内形式（thin_layer: F=...;D=$(dirname "$0");R=...）
        text = re.sub(r'(?m)(^|;)([ \t]*)D=\$\(dirname\s+"\$0"\)',
                      lambda m: f'{m.group(1)}{m.group(2)}D="{ind}"', text)
    return text


def assemble(sbatch_lines: list[str], body_lines: list[str]) -> str:
    """拼装：shebang → 全部 #SBATCH → 环境块 → 正文。"""
    head = ["#!/bin/bash"]
    head += sbatch_lines
    head.append(ENV_BLOCK.rstrip("\n"))
    return "\n".join(head + body_lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="超算 public 场景作业脚本补丁器")
    ap.add_argument("--in", dest="src", required=True, help="原始 submit_flash.sh")
    ap.add_argument("--out", dest="dst", required=True, help="补丁后作业脚本")
    ap.add_argument("--work", required=True, help="并行盘工作区（out/ inputs/ 都在其下）")
    ap.add_argument("--tag", required=True, help="场景标签（用于输出文件名）")
    ap.add_argument("--partition", default="v5_192")
    ap.add_argument("--time", dest="time_limit", default="01:00:00")
    ap.add_argument("--input-dir", dest="input_dir", default="",
                    help="输入目录（并行盘绝对路径）：把 `dirname \"$0\"` / "
                         "SCRIPT_DIR 锚定到它（sbatch 下 $0 指向 /var/spool/slurm）")
    args = ap.parse_args()

    src = Path(args.src)
    dst = Path(args.dst)
    work = Path(args.work)
    run_dir = work / "out" / f"{args.tag}_run"
    out_dir = work / "out" / f"{args.tag}_outputs"
    input_dir = Path(args.input_dir) if args.input_dir else None

    text = src.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    sbatch_idx = [i for i, l in enumerate(lines) if l.startswith("#SBATCH")]
    if not sbatch_idx:
        print(f"[FATAL] {src} 里没有 #SBATCH 指令", file=sys.stderr)
        return 2
    sbatch_lines = [lines[i] for i in sbatch_idx]
    body_lines = [l for i, l in enumerate(lines) if i not in set(sbatch_idx)]

    # 正文里的 shebang 去掉（assemble 会补）
    body_lines = [l for l in body_lines if not l.startswith("#!")]

    new_sbatch = patch_sbatch(sbatch_lines, work, args.tag, args.partition, args.time_limit)
    new_body = patch_body("\n".join(body_lines), run_dir, out_dir,
                           input_dir=input_dir).splitlines()
    # 正文里若残留 module purge（多行写法），再兜一次
    new_body = [l for l in new_body if not re.match(r'^\s*module\s+purge\b', l)]

    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(assemble(new_sbatch, new_body), encoding="utf-8", newline="\n")
    dst.chmod(0o755)

    print(f"[patch_job] {src} -> {dst}")
    print(f"[patch_job] 运行目录 -> {run_dir}")
    print(f"[patch_job] 输出目录 -> {out_dir}")
    if input_dir:
        print(f"[patch_job] 输入目录 -> {input_dir}")
    for l in new_sbatch:
        print(f"  {l}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
