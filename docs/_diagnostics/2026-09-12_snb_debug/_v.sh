#!/bin/bash
OBJ=/root/QC/FLASH/FLASHSNB/FLASH4.8/SNBOneCH_ml_ug_obj
L=/wsl_run_snbonech.log
echo '=== STEPS ==='; grep -cE '^ *[0-9]+ ' ""
echo '=== LAST 6 ==='; grep -E '^ *[0-9]+ ' "" | tail -6
echo '=== NONCONV ==='; grep -c Nonconv ""
echo '=== ERR/ABORT ==='; grep -cE 'ERROR|ABORT' ""
echo '=== EOS_NR WARN ==='; grep -c 'eos_nr WARN' ""
echo '=== dt min/max ==='; grep -E '^ *[0-9]+ ' "" | awk '{print $3}' | sort -g | sed -n '1p;$p'
echo '=== CHK ==='; ls ""/snbonechug_hdf5_chk_* 2>/dev/null | wc -l
echo '=== NXB ==='; grep -m1 -oE 'DNXB=[0-9]+' "/Makefile"
echo '=== tele range (last chk) ==='
