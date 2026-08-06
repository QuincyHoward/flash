#!/bin/sh

#### 基础设置与更新
# 首先更新系统！！！
# 请注意有些文件不能放在共享文件夹，尤其是链接文件
sudo apt upgrade 


sudo apt install gcc-9 g++-9 gfortran-9
#如果系统里有多个版本的gcc，可以通过以下方式切换版本
sudo update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-9 50
sudo update-alternatives --install /usr/bin/g++ g++ /usr/bin/g++-9 50
sudo update-alternatives --install /usr/bin/gfortran gfortran /usr/bin/gfortran-9 50

sudo update-alternatives --config gcc
sudo update-alternatives --config g++
sudo update-alternatives --config gfortran

gcc --version


#### 安装FLASH
sudo apt install make       
sudo apt install make-guile  
 
 
 
#!/bin/bash

# 创建临时编译目录
echo "创建临时编译目录..."
mkdir -p ~/tmp
cd ~/tmp

# 复制压缩包到临时目录（从Windows文件系统）
echo "复制压缩包到临时目录..."
cp /mnt/d/WSL/WorkSpace/mainPATH/FLASH/FLASH_need/*.tar.gz .
cp /mnt/d/WSL/WorkSpace/mainPATH/FLASH/FLASH_need/*.tar .

# 解压所有压缩包
echo "解压压缩包..."
for file in *.tar.gz *.tar; do
    if [ -f "$file" ]; then
        echo "解压 $file..."
        if [[ "$file" == *.tar.gz ]]; then
            tar -zxvf "$file"
        else
            tar -xvf "$file"
        fi
    fi
done

# 创建安装目录
echo "创建安装目录..."
sudo mkdir -p /usr/local/mpich
sudo mkdir -p /usr/local/hdf5
sudo mkdir -p /usr/local/hypre

# 检查必要的编译工具
echo "检查编译工具..."
command -v gcc >/dev/null 2>&1 || { echo "安装gcc..."; sudo apt install gcc; }
command -v g++ >/dev/null 2>&1 || { echo "安装g++..."; sudo apt install g++; }
command -v gfortran >/dev/null 2>&1 || { echo "安装gfortran..."; sudo apt install gfortran; }
command -v make >/dev/null 2>&1 || { echo "安装make..."; sudo apt install make; }

# 1. 安装MPICH
echo "=================== 安装MPICH ==================="
cd ~/tmp
if [ -d "mpich-3.2" ]; then
    cd mpich-3.2
    # 清理之前可能存在的配置
    make clean 2>/dev/null || true
    make distclean 2>/dev/null || true
    
    # 配置
    echo "配置MPICH..."
    ./configure --prefix=/usr/local/mpich CC=gcc CXX=g++ FC=gfortran F77=gfortran
    
    if [ $? -eq 0 ]; then
        # 编译
        echo "编译MPICH..."
        make -j$(nproc)
        
        # 安装
        echo "安装MPICH..."
        sudo make install
        
        # 设置环境变量
        echo "设置MPICH环境变量..."
        cat >> ~/.bashrc << 'EOF'
# MPICH环境变量
export MPI_HOME=/usr/local/mpich
export PATH=$MPI_HOME/bin:$PATH
export LD_LIBRARY_PATH=$MPI_HOME/lib:$LD_LIBRARY_PATH
export C_INCLUDE_PATH=$MPI_HOME/include:$C_INCLUDE_PATH
EOF
        
        echo "MPICH安装完成！"
    else
        echo "MPICH配置失败！"
        exit 1
    fi
else
    echo "未找到mpich-3.2目录！"
    exit 1
fi

# 重新加载环境变量以便后续使用
source ~/.bashrc

# 2. 安装HDF5
echo "=================== 安装HDF5 ==================="
cd ~/tmp
if [ -d "hdf5-1.8.12" ]; then
    cd hdf5-1.8.12
    
    # 清理之前可能存在的配置
    make clean 2>/dev/null || true
    make distclean 2>/dev/null || true
    
    # 配置
    echo "配置HDF5..."
    ./configure --prefix=/usr/local/hdf5 --enable-parallel --enable-fortran
    
    if [ $? -eq 0 ]; then
        # 编译
        echo "编译HDF5..."
        make -j$(nproc)
        
        # 安装
        echo "安装HDF5..."
        sudo make install
        
        # 设置环境变量
        echo "设置HDF5环境变量..."
        cat >> ~/.bashrc << 'EOF'
# HDF5环境变量
export HDF5_HOME=/usr/local/hdf5
export PATH=$HDF5_HOME/bin:$PATH
export LD_LIBRARY_PATH=$HDF5_HOME/lib:$LD_LIBRARY_PATH
export C_INCLUDE_PATH=$HDF5_HOME/include:$C_INCLUDE_PATH
export HDF5_ROOT=$HDF5_HOME
EOF
        
        echo "HDF5安装完成！"
    else
        echo "HDF5配置失败！"
        exit 1
    fi
else
    echo "未找到hdf5-1.8.12目录！"
    exit 1
fi

# 重新加载环境变量以便后续使用
source ~/.bashrc

# 3. 安装Hypre
echo "=================== 安装Hypre ==================="
cd ~/tmp
if [ -d "hypre-2.9.0b" ]; then
    cd hypre-2.9.0b/src
    
    # 清理之前可能存在的配置
    make clean 2>/dev/null || true
    make distclean 2>/dev/null || true
    
    # 配置
    echo "配置Hypre..."
    ./configure --prefix=/usr/local/hypre CC=mpicc CXX=mpic++ FC=mpif90 F77=mpif90
    
    if [ $? -eq 0 ]; then
        # 编译
        echo "编译Hypre..."
        make -j$(nproc)
        
        # 安装
        echo "安装Hypre..."
        sudo make install
        
        # 设置环境变量
        echo "设置Hypre环境变量..."
        cat >> ~/.bashrc << 'EOF'
# Hypre环境变量
export HYPRE_HOME=/usr/local/hypre
export LD_LIBRARY_PATH=$HYPRE_HOME/lib:$LD_LIBRARY_PATH
export C_INCLUDE_PATH=$HYPRE_HOME/include:$C_INCLUDE_PATH
EOF
        
        echo "Hypre安装完成！"
    else
        echo "Hypre配置失败！"
        exit 1
    fi
else
    echo "未找到hypre-2.9.0b目录！"
    exit 1
fi

# 重新加载所有环境变量
source ~/.bashrc

echo "=================== 安装完成 ==================="
echo ""
echo "安装目录:"
echo "  MPICH:  /usr/local/mpich"
echo "  HDF5:   /usr/local/hdf5"
echo "  Hypre:  /usr/local/hypre"
echo ""
echo "编译临时目录: ~/tmp (可以随时删除)"
echo ""
echo "测试安装:"
echo "  1. MPICH: mpicc --version"
echo "  2. HDF5:  h5pcc --version"
echo "  3. Hypre: ls /usr/local/hypre/lib/libHYPRE*"
echo ""
echo "清理编译文件: rm -rf ~/tmp"


#############
nano ~/.bashrc
#mpich
export MPI_HOME=/mnt/d/WSL/WorkSpace/mainPATH/FLASH/FLASH_local/mpich
export PATH=$MPI_HOME/bin:$PATH
export LD_LIBRARY_PATH=$MPI_HOME/lib:$LD_LIBRARY_PATH
export C_INCLUDE_PATH=$MPI_HOME/include:$C_INCLUDE_PATH
#hdf5
export HDF5_HOME=/mnt/d/WSL/WorkSpace/mainPATH/FLASH/FLASH_local/hdf5
export PATH=$HDF5_HOME/bin:$PATH
export LD_LIBRARY_PATH=$HDF5_HOME/lib:$LD_LIBRARY_PATH
export C_INCLUDE_PATH=$HDF5_HOME/include:$C_INCLUDE_PATH
#hypre
export HYPRE_HOME=/mnt/d/WSL/WorkSpace/mainPATH/FLASH/FLASH_local/hypre
export LD_LIBRARY_PATH=$HYPRE_HOME/lib:$LD_LIBRARY_PATH
export C_INCLUDE_PATH=$HYPRE_HOME/include:$C_INCLUDE_PATH




#### 其他依赖
sudo apt update
sudo apt-get install python-is-python3
sudo apt install zlib1g-dev  # 安装开发包，包含头文件和库文件
sudo apt-get install libblas-dev liblapack-dev
sudo apt install liblapack-dev libblas-dev  # 安装BLAS和LAPACK的Fortran接口
sudo apt install liblapacke-dev            # 安装C语言接口（如需C语言支持）



########################################
# 1. 获取当前目录路径
CURRENT_DIR=$(pwd)
echo "当前目录: $CURRENT_DIR"

# 2. 检查文件是否存在
if [ ! -f "FLASH4.8.tar.gz" ]; then
    echo "错误: 当前目录中未找到FLASH4.8.tar.gz文件"
    exit 1
fi

if [ ! -f "Makefile.h" ]; then
    echo "错误: 当前目录中未找到Makefile.h文件"
    exit 1
fi

# 3. 移动并解压
echo "移动并解压文件..."
mv FLASH4.8.tar.gz ~/
cd ~/
tar -zxvf FLASH4.8.tar.gz
mv "$CURRENT_DIR/Makefile.h" ~/FLASH4.8/

echo "完成！"
echo "文件位置:"
echo "  FLASH4.8.tar.gz: ~/FLASH4.8.tar.gz"
echo "  FLASH4.8目录: ~/FLASH4.8/"
echo "  Makefile.h: ~/FLASH4.8/Makefile.h"

#Makefile.h
#LIB_LAPACK = -llapack -lblas -lgfortran
#注释掉最后的特殊if结构


########################################

cd ../../FLASH4.8

########################
#     一维快速仿真      #
########################
#使用LaserSlab1D进行测试，该仿真会只运行几分钟
##################AItest##################
cd ..
rm -rf object



cd 
clear
pwd
cd FLASH4.8

./setup -auto LaserSlab -1d +cartesian -nxb=16  +hdf5typeio  species=cham,targ +mtmmmt +laser +uhd3t +mgd mgd_meshgroups=10 \
 -objdir=object -parfile=example1d.par

cd object/
make -j16

mpiexec -n 16  ./flash4

ls *chk*
########################












#########################################
# 现在，开始你的FLAH之旅吧～～～
 

