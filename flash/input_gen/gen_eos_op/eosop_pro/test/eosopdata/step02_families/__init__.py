"""``eosopdata/step02_families`` —— **其他文件类型**（非 cn4）的提取、
绘图与核查状态测试包。

分组依据是**数据能力**而非扩展名 —— 同一族可能有多种表型。
2026-09-15 起按用户规约扩展为「每种文件类型一个独立文件夹一个脚本」：

* :mod:`test_family_extract` —— 各族能否正确取出场与轴
* :mod:`test_family_plots` —— 二维场彩图 / 一维曲线（qa_plots 通道）
* :mod:`test_field_checks` —— 控制字典守护（**标记只有 uk/uv 两个**：
  ``uk`` = 无来源确认、``uv`` = 未人工核查；有源且已核查则标记整体
  省略 —— 当前只有 cn4；来源白名单 = cn4 全部 + 文件内明文声明条目
  （ledcop_atomic rho/Te/Ross/Planck、coldopacity Eph/miu/"*"、
  hugoniot 全部）；未来未知格式经 ``register_family`` 注册进字典）
* ``test_plot_<type>.py`` × 11 —— 逐类型批量出图（统一绘图模块
  ``eosop_pro.plotting.gridmap``），产物落 ``_out/<type>/``，
  ``_report.txt`` 逐行给出网格点 / 物理意义 / 单位 / 认证标记
  （``tags=uk,uv`` 或 ``tags=uv``，完全核查后该键省略），供人工挨个核查
* 2026-09-15 晚新增规约：①图与报告一律带认证标记（uk/uv，全通过省略）；
  ②语义映射不可行的字段画 raw values vs index 兜底序列图（数值可读
  即可画）；③每族处理前 3 个可解析文件并把原始数据复制到
  ``_out/<type>/source_data/``（核查对照）
* 字典 Markdown 全文：``docs/eosop变量控制字典.md``（与字典逐字同步，
  ``python -m eosop_pro.registry.field_checks`` 再生成）
"""
