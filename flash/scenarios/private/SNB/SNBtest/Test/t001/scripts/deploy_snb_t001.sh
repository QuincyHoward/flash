#!/usr/bin/env bash
# deploy_snb_t001.sh - SNB t001 部署脚本（在 WSL 中执行）
# 步骤: 备份 -> 删除陈旧 objdir -> 同步 Conductivity SNB 单元 -> 部署 app(tmax=1e-11)
# 红线: 仅操作 $HOME/QC/FLASH/FLASHSNB/FLASH4.8 专用树, 不触碰常用 FLASH 树
set -euo pipefail

SNB="$HOME/QC/FLASH/FLASHSNB/FLASH4.8"
STAGE="/mnt/e/PhySimX/PhySimX/simulation/flash_test/layer3/flash/flash/scenarios/private/SNB/SNBtest/src/SNB"
PHY="$STAGE/physics/physics"
APP_SRC="$STAGE/SNB_1D_laser/SNB_1D_laser"

echo "=== [1/6] 备份 FLASHSNB 树当前状态 ==="
TS=$(date +%Y%m%d_%H%M%S)
BK="$HOME/FLASHSNB_backup_$TS.tar.gz"
if [ -f "$BK" ]; then echo "备份已存在: $BK"; else
  tar -czf "$BK" -C "$HOME/QC/FLASH/FLASHSNB" FLASH4.8
  echo "备份完成: $BK ($(du -sh "$BK" | cut -f1))"
fi

echo "=== [2/6] 确认目标树身份（防误操作常用树） ==="
if [ ! -f "$SNB/setup" ]; then echo "FATAL: $SNB 不是 FLASH 源树"; exit 1; fi
if [ ! -d "$SNB/source/physics/materialProperties/Conductivity/ConductivityMain/SpitzerHighZ" ]; then
  echo "FATAL: Conductivity 单元结构异常"; exit 1
fi
echo "目标树确认: $SNB"

echo "=== [3/6] 删除上次失败的陈旧 objdir (SNB_1D_laser, 含 .o 无可执行文件) ==="
if [ -d "$SNB/SNB_1D_laser" ]; then
  rm -rf "$SNB/SNB_1D_laser"
  echo "已删除陈旧 objdir"
fi

echo "=== [4/6] 同步完整 SNB Conductivity 单元到树 ==="
COND_T="$SNB/source/physics/materialProperties/Conductivity"
cp -rf "$PHY/materialProperties/Conductivity/." "$COND_T/"
echo "同步完成, 关键文件核对:"
for f in Conductivity_aniso.F90 Conductivity_anisoFullState.F90 Conductivity_interface.F90 mfp_ele.F90; do
  [ -f "$COND_T/$f" ] && echo "  OK $f" || { echo "  MISSING $f"; exit 1; }
done
[ -d "$COND_T/ConductivityAniso" ] && echo "  OK ConductivityAniso/" || { echo "  MISSING ConductivityAniso/"; exit 1; }
grep -c anisoFullState "$COND_T/Conductivity_interface.F90" | xargs echo "  interface anisoFullState 引用数:"

echo "=== [5/6] 部署 app 目录 (tmax=1e-11) 到树根 ==="
rm -rf "$SNB/SNB_1D_laser_app"
mkdir -p "$SNB/SNB_1D_laser_app"
cp -r "$APP_SRC/." "$SNB/SNB_1D_laser_app/"
# 仅修改 tmax (用户指定 1e-11), 其余参数一律不动
sed -i 's/^tmax[[:space:]]*=.*/tmax           = 1.0e-11/' "$SNB/SNB_1D_laser_app/flash.par"
grep -n "^tmax" "$SNB/SNB_1D_laser_app/flash.par"

echo "=== [6/6] 同步 SimulationMain 中的 app 副本 par (tmax 一致性) ==="
SIMC="$SNB/source/Simulation/SimulationMain/SNB_1D_laser"
if [ -d "$SIMC" ]; then
  # 用 staged app 完整刷新, 保证与部署源一致
  rm -rf "$SIMC"
  cp -r "$APP_SRC" "$SIMC"
  sed -i 's/^tmax[[:space:]]*=.*/tmax           = 1.0e-11/' "$SIMC/flash.par"
  grep -n "^tmax" "$SIMC/flash.par"
else
  echo "SimulationMain 无副本, setup 时会自动拷入"
fi

echo "=== 部署完成 ==="
echo "app 目录: $SNB/SNB_1D_laser_app"
echo "下一步: setup -auto SNB_1D_laser -simdir=\$SNB -objdir=SNB_1D_laser_obj"
