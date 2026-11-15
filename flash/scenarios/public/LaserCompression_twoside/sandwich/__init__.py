"""Sandwich 场景家族分类目录。

收录场景（历史记录，清单以 discovery 实时扫描为准）:
  - grad_dens_sandwich   — HE-CH-Si-CH-HE 渐变密度 CH
  - thin_layer_sandwich  — Si/CH/He 薄层三层靶 (sim_input_si)

★ 2026-11-04 任意移动改造：本文件不再急切导入任何场景子包。历史上
  「不导入子包 → register() 不执行 → list_scenarios 看不到场景」的问题
  已随去注册化（manifest 驱动发现 + registry 惰性导入）彻底消失 ——
  场景发现由 core/discovery.py 纯文件扫描完成，与本文件无关。

  场景目录在本分类内增删、改名、移动均无需修改本文件。
"""
