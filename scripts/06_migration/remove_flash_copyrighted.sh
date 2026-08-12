#!/bin/bash
# ================================================================
# FLASH Center 版权文件 Git 索引清除脚本
# ================================================================
# 用途: 从Git索引中移除FLASH Center版权文件，但保留本地副本
# 安全: 使用 --cached 仅从索引移除，不删除本地文件
# 执行: bash scripts/06_migration/remove_flash_copyrighted.sh
# ================================================================
set -e

echo "============================================"
echo " FLASH Center 版权文件 Git 索引清除"
echo "============================================"
echo ""
echo "警告: 此操作将从Git索引中移除以下类别的文件:"
echo "  - FLASH 源码包 (flash_src/)"
echo "  - FLASH SimulationMain 示例源码 (~1000 .F90)"
echo "  - FLASH 分发的 EOS/不透明度表 (.cn4)"
echo "  - FLASH LaserSlab 示例文件"
echo "  - FLASH HDF5 输出文件"
echo "  - FLASH 编译运行产物"
echo ""
echo "本地文件将保留，仅从Git追踪中移除。"
echo ""
read -p "是否继续? (输入 yes 确认): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "已取消。"
    exit 0
fi

echo ""
echo "正在清除..."

# --- FLASH 源码包 ---
echo "[1/8] 清除 flash_src/ ..."
git rm -r --cached flash_src/ 2>/dev/null || echo "  (无文件或已清除)"

echo "[2/8] 清除 FLASH4.8/ ..."
git rm -r --cached FLASH4.8/ 2>/dev/null || echo "  (无文件或已清除)"

# --- FLASH SimulationMain 示例源码 ---
echo "[3/8] 清除 input_gen/SimulationMain/ ..."
git rm -r --cached input_gen/SimulationMain/ 2>/dev/null || echo "  (无文件或已清除)"

# --- FLASH 分发的 EOS/不透明度表 ---
echo "[4/8] 清除 FLASH_eos_op_data/ ..."
git rm -r --cached input_gen/gen_eos_op/eos_op_data/FLASH_eos_op_data/ 2>/dev/null || echo "  (无文件或已清除)"

# --- FLASH LaserSlab 示例 ---
echo "[5/8] 清除 LaserSlab 示例目录 ..."
git rm -r --cached scenarios/flash_demo/LaserSlab/LaserSlab/ 2>/dev/null || echo "  (无文件或已清除)"
git rm -r --cached scenarios/flash_demo/LaserSlab/LaserSlabca1d/ 2>/dev/null || echo "  (无文件或已清除)"
git rm -r --cached scenarios/flash_demo/LaserSlab/LaserSlabpy/ 2>/dev/null || echo "  (无文件或已清除)"

# --- ReDo 研究目录 ---
echo "[6/8] 清除 ReDo 目录 ..."
git rm -r --cached scenarios/flash_demo/LaserSlab/ReDo042sp_CH042sp2umL8.00e-02/ 2>/dev/null || echo "  (无文件或已清除)"
git rm -r --cached scenarios/flash_demo/LaserSlab/ReDo042sp_CH042sp3umF8.00e-02/ 2>/dev/null || echo "  (无文件或已清除)"

# --- HDF5 输出和运行产物 ---
echo "[7/8] 清除 HDF5 文件和运行产物 ..."
git ls-files --cached "*.h5" 2>/dev/null | while read f; do
    git rm --cached "$f" 2>/dev/null
done
git rm -r --cached scenarios/flash_demo/demo_hpc/demo_task/ 2>/dev/null || echo "  (无文件或已清除)"
git rm -r --cached scenarios/flash_demo/demo_local/demo_task/ 2>/dev/null || echo "  (无文件或已清除)"
git rm -r --cached scenarios/flash_demo/demo_task/ 2>/dev/null || echo "  (无文件或已清除)"

# --- 场景运行产物 ---
echo "[8/8] 清除场景运行产物 ..."
for d in scenarios/flash_demo/new_struture/*/runs/ test/scenarios/runs_*/ test/temp_delete/ test/grid_rede/ scenarios/chsich_grad/run_tools/runs_*/ scenarios/chsich/run_tools/runs_*/; do
    git rm -r --cached "$d" 2>/dev/null || true
done

echo ""
echo "============================================"
echo " 清除完成!"
echo "============================================"
echo ""
echo "下一步:"
echo "  1. git add .gitignore scripts/06_migration/remove_flash_copyrighted.sh"
echo "  2. git commit -m 'Compliance: remove FLASH Center copyrighted files from tracking'"
echo "  3. git push (到 Gitee)"
echo ""
echo "验证 (以下命令应无输出):"
echo "  git ls-files input_gen/SimulationMain/"
echo "  git ls-files flash_src/"
echo "  git ls-files '*.h5'"
