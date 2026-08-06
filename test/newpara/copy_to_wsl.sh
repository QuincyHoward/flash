#!/bin/bash
# copy_to_wsl.sh — 将所有 flash_input 文件复制到 WSL
FLASH_HOME="$HOME/${FLASH_SIM_USER_DIR:-QC}/FLASH/FLASH4.8"
SIM_SRC_DIR="$FLASH_HOME/source/Simulation/SimulationMain/QC/LaserSlab_newpara_test"
SRC="/mnt/e/ProgramsPATH/AI/WorkBuddy/WorkBuddyFiles/AItest/Plan_for_py/PhySimX/physimx_sim/src/physimx_sim/flash/test/newpara/flash_input"

mkdir -p "$SIM_SRC_DIR"

cp "$SRC/Config" "$SIM_SRC_DIR/"
cp "$SRC/Makefile" "$SIM_SRC_DIR/"
cp "$SRC/Simulation_data.F90" "$SIM_SRC_DIR/"
cp "$SRC/Simulation_init.F90" "$SIM_SRC_DIR/"
cp "$SRC/Simulation_initBlock.F90" "$SIM_SRC_DIR/"
cp "$SRC"/*.cn4 "$SIM_SRC_DIR/"
cp "$SRC/laserslab_newpara.par" "$SIM_SRC_DIR/"

# Also copy deploy script
cp "/mnt/e/ProgramsPATH/AI/WorkBuddy/WorkBuddyFiles/AItest/Plan_for_py/PhySimX/physimx_sim/src/physimx_sim/flash/test/newpara/wsl_deploy.sh" "$FLASH_HOME/"
chmod +x "$FLASH_HOME/wsl_deploy.sh"

echo "OK: all files copied"
ls -la "$SIM_SRC_DIR/"
