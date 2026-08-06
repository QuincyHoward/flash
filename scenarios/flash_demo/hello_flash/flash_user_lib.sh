#!/bin/bash
# ============================================================
# flash_user_lib.sh — FLASH 用户名解析库 (hello_flash 共享)
# ============================================================
# 所有 hello_flash 脚本通过 `source flash_user_lib.sh` 引入,
# 统一解析 FLASH 安装用户名 (路径 ~/<用户名>/FLASH/FLASH4.8)。
#
# 用户名解析优先级:
#   1. 环境变量 FLASH_SIM_USER_DIR (显式指定优先)
#   2. 读取 flash._core.credentials 中设置的专属用户名
#      └ 设置方法: python -m flash._core.credentials user <用户名>
#         (等价: from flash._core.credentials import set_user_name)
#   3. 读取不到 → 默认用户名 hello (默认密码 123, 见 credentials 模板)
#
# ⚠️ 用户名必须通过 flash._core.credentials 设置, 不要在本库或
#    任何脚本中硬编码用户名。
# ============================================================

# 输出解析后的 FLASH 用户名 (stdout)
resolve_flash_user() {
    # 1) 环境变量优先
    if [ -n "${FLASH_SIM_USER_DIR:-}" ]; then
        printf '%s' "$FLASH_SIM_USER_DIR"
        return 0
    fi

    # 2) 读取 flash._core.credentials 中的专属用户名
    #    hello_flash 位于 .../sim/flash/scenarios/flash_demo/hello_flash
    #    flash 包根 = ../../.. ; 包入口 (import flash) = ../../../..
    local here flash_root sim_root user
    here="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd)" || here=""
    if [ -n "$here" ]; then
        flash_root="$(cd "$here/../../.." 2>/dev/null && pwd)" || flash_root=""
        sim_root="$(cd "$flash_root/.." 2>/dev/null && pwd)" || sim_root=""
        if [ -n "$flash_root" ] && [ -f "$flash_root/__init__.py" ] \
           && command -v python3 >/dev/null 2>&1; then
            user="$(PYTHONPATH="$sim_root${PYTHONPATH:+:$PYTHONPATH}" python3 -c \
                'from flash._core.credentials import get_user_name; print(get_user_name())' \
                2>/dev/null | tr -d '\r\n')"
            if [ -n "$user" ]; then
                printf '%s' "$user"
                return 0
            fi
        fi
    fi

    # 3) 默认用户名
    printf '%s' "hello"
}

# 在当前 shell 中设置 FLASH_SIM_USER_DIR (幂等)
ensure_flash_user() {
    if [ -z "${FLASH_SIM_USER_DIR:-}" ]; then
        FLASH_SIM_USER_DIR="$(resolve_flash_user)"
    fi
    export FLASH_SIM_USER_DIR
    printf '%s' "$FLASH_SIM_USER_DIR"
}
