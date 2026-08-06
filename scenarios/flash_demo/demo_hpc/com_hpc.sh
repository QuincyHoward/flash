#!/bin/bash
#SBATCH -p v5_192
#SBATCH --job-name=test
#SBATCH --partition=cpu
#SBATCH -N 1
#SBATCH --ntasks-per-node=40
#SBATCH --time=1-00:00:00
#SBATCH --output=%j.out
#SBATCH --error=%j.err

######################################



# 查看运行时间状态等 北京
sacct -u sch0348 -S 2025-08-25 -E 2025-09-10 \
      --format=jobid,jobname,partition,alloccpus,start,end,elapsed,state -X

#
# 查看运行时间状态等 宁夏
sacct -u scfa2696 -S 2026-07-02 -E 2026-07-28 \
  --format=jobid,jobname,partition,alloccpus,start,end,elapsed,state,nodelist -X


#


sbatch FirstFLASH.sh


scontrol show job


sacct

module avail

