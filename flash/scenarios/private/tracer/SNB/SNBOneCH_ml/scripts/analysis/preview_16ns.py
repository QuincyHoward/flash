"""1.6ns 预览: 抓最后 forced plt + log 采样 → 本地出快速分析图 (全量收集等待期)。"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
# 脚本位于 SNBOneCH_ml/scripts/analysis/: 上溯 7 级 = 内层 flash, 8 级 = 外层根
_INNER = os.path.abspath(os.path.join(_HERE, "..", "..", "..", "..", "..", "..", ".."))
_ROOT = os.path.abspath(os.path.join(_INNER, ".."))
sys.path.insert(0, os.path.join(_INNER, "scenarios", "flash_demo", "demo_hpc"))
sys.path.insert(0, _ROOT)

from remote_ssh_helper import (  # noqa: E402
    _resolve_route_and_credential, quick_run, scp_download)

OBJ = "~/QC/FLASH/FLASHSNB/FLASH4.8/SNBOneCH_ml_ug_obj"
OUT = os.path.join(_HERE, "..", "..", "flash_output")


def main() -> int:
    route = _resolve_route_and_credential("flash_ssh")

    # 1) 最后 forced plt
    out, _, _ = quick_run(
        f"ls -t {OBJ}/snbonechug_forced_hdf5_plt_cnt_* 2>/dev/null | head -1",
        credential_name="flash_ssh", timeout=60)
    last_plt = out.strip().splitlines()[-1] if out.strip() else ""
    print("last forced plt:", last_plt)
    if last_plt:
        quick_run(f"cp -f {last_plt} ~/SNB1CH_out_lastplt",
                  credential_name="flash_ssh", timeout=60)
        ok = scp_download(route, "~/SNB1CH_out_lastplt",
                          os.path.join(OUT, "_preview_lastplt"))
        print("plt dl:", ok)
        quick_run("rm -f ~/SNB1CH_out_lastplt", credential_name="flash_ssh",
                  timeout=30)

    # 2) log 采样 (每 500 行取 1 行, 远端单引号 awk, 本地再解析)
    quick_run(
        f"awk 'NR%500==1' {OBJ}/wsl_run_snbonech.log | "
        f"grep -E '^ +[0-9]+ ' > ~/SNB1CH_log_sample.csv; "
        f"wc -l ~/SNB1CH_log_sample.csv",
        credential_name="flash_ssh", timeout=120)
    ok = scp_download(route, "~/SNB1CH_log_sample.csv",
                      os.path.join(OUT, "_preview_log.csv"))
    print("csv dl:", ok)
    quick_run("rm -f ~/SNB1CH_log_sample.csv", credential_name="flash_ssh",
              timeout=30)
    return 0


if __name__ == "__main__":
    sys.exit(main())
