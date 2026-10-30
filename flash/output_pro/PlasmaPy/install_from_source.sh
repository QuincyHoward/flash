#!/usr/bin/env bash
# ==============================================================================
# ★ 2026-10-30: 本脚本仅服务于旧工作区 E:/PhySimX/PhySimX/simulation/PlasmaPy/。
#   flash/output_pro 内的 PlasmaPy 请改用同目录 install_editable.py
#   (安装进 flash 包所在环境, 版本闸门 py>=3.12, 不再自建 .venv)。
# install_from_source.sh — PlasmaPy source-code based installation manager
#
# Usage (run from the workspace root E:/PhySimX/PhySimX/simulation/PlasmaPy/PlasmaPy):
#   bash install_from_source.sh              # install/repair: clone v2026.2.0 + editable install
#   bash install_from_source.sh --update     # pull latest code for the pinned tag and reinstall
#   bash install_from_source.sh --tag vX.Y.Z # switch to another release tag
#   bash install_from_source.sh --latest     # switch to latest main branch (dev version)
#
# Layout produced:
#   ./PlasmaPy/   <- git clone of the PlasmaPy repository (source of truth)
#   ./.venv/      <- virtual environment; plasmapy installed in EDITABLE mode
#                    so that any edit under PlasmaPy/src/plasmapy takes effect
#                    immediately (no reinstall needed).
# ==============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_URL="https://github.com/PlasmaPy/PlasmaPy.git"
DEFAULT_TAG="v2026.2.0"

SRC_DIR="$ROOT/PlasmaPy"
VENV_DIR="$ROOT/.venv"
PY="$VENV_DIR/Scripts/python.exe"
PIP_INDEX="https://pypi.org/simple"

MODE="install"
TAG="$DEFAULT_TAG"
for arg in "$@"; do
    case "$arg" in
        --update) MODE="update" ;;
        --latest) MODE="latest" ;;
        --tag)    TAG_PENDING=1 ;;
        *)
            if [ "${TAG_PENDING:-0}" = "1" ]; then TAG="$arg"; TAG_PENDING=0; MODE="tag";
            else echo "Unknown argument: $arg"; exit 1; fi
            ;;
    esac
done

log() { printf '\n=== %s ===\n' "$*"; }

# ---------------------------------------------------------------- 1. venv
log "Step 1: virtual environment"
if [ ! -f "$PY" ]; then
    echo "Creating venv at $VENV_DIR ..."
    python -m venv "$VENV_DIR"
fi
"$PY" -m pip install --upgrade pip -i "$PIP_INDEX" -q

# ---------------------------------------------------------------- 2. source
log "Step 2: source code ($SRC_DIR)"
git_clone_tag() {  # $1 = tag or branch
    echo "Cloning $REPO_URL ($1) ..."
    git clone --depth 1 --branch "$1" "$REPO_URL" "$SRC_DIR"
}

case "$MODE" in
    install|tag)
        if [ -d "$SRC_DIR/.git" ]; then
            echo "Source dir exists; fetching requested ref '$TAG' ..."
            git -C "$SRC_DIR" fetch --depth 1 origin "refs/tags/$TAG:refs/tags/$TAG" 2>/dev/null \
                || git -C "$SRC_DIR" fetch --depth 1 origin "$TAG"
            git -C "$SRC_DIR" checkout -f "$TAG"
        else
            git_clone_tag "$TAG"
        fi
        ;;
    update)
        [ -d "$SRC_DIR/.git" ] || { echo "No existing clone; run without --update first."; exit 1; }
        REF=$(git -C "$SRC_DIR" describe --tags 2>/dev/null | sed 's/-.*//' || echo "$DEFAULT_TAG")
        echo "Pulling latest commit for current ref ($REF) ..."
        git -C "$SRC_DIR" fetch --depth 1 origin "$REF" || true
        git -C "$SRC_DIR" pull --ff-only origin "$REF" 2>/dev/null \
            || git -C "$SRC_DIR" reset --hard "origin/$REF" 2>/dev/null \
            || echo "pull skipped (shallow clone); source kept as-is"
        ;;
    latest)
        if [ -d "$SRC_DIR/.git" ]; then
            git -C "$SRC_DIR" fetch --depth 1 origin main
            git -C "$SRC_DIR" checkout -f FETCH_HEAD
        else
            git clone --depth 1 --branch main "$REPO_URL" "$SRC_DIR"
        fi
        ;;
esac

echo "Source version: $(git -C "$SRC_DIR" describe --tags --always 2>/dev/null || echo unknown)"

# ---------------------------------------------------------------- 3. editable install
log "Step 3: editable install (replaces any wheel install)"
# Remove wheel install if present (editable install would override anyway,
# but an explicit uninstall keeps the environment clean).
"$PY" -m pip uninstall -y plasmapy >/dev/null 2>&1 || true
"$PY" -m pip install -e "$SRC_DIR" -i "$PIP_INDEX"

# ---------------------------------------------------------------- 4. verify
log "Step 4: verification"
"$PY" - <<'EOF'
import os
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
import astropy.units as u
import plasmapy
from plasmapy.formulary.speeds import thermal_speed
print("plasmapy version :", plasmapy.__version__)
print("imported from    :", plasmapy.__file__)
v = thermal_speed(1 * u.keV, "e-")
assert plasmapy.__file__.replace("\\", "/").find("/PlasmaPy/src/plasmapy") > 0, \
    "ERROR: plasmapy is NOT imported from the local source tree!"
assert 1.8e7 < v.value < 2.0e7, "smoke test value out of range"
print("smoke test       : thermal_speed(1 keV, e-) =", v)
print("VERIFY OK: editable source install is active.")
EOF

log "Done. Edit sources under PlasmaPy/src/plasmapy/ — changes apply immediately."
