"""``eosopdata/transcn4`` —— **其他格式族 -> cn4** 转换测试包。

被测对象：``eosop_pro.cn4.cn4_io`` 的

* :func:`parsed_tables_to_cn4` —— 低层组装（``allow_foreign=True`` 时跨族）
* :func:`convert_foreign_to_cn4` —— 高层"文件 -> 文件"入口
* :func:`write_cn4` / :func:`load_cn4` —— 定宽 ``4e12.6`` 编码往返

核心验收点（对应用户要求"不存在的数据使用 NAN 占位，注意 NAN 也需要对齐格式"）：

1. 缺失数据写 :data:`NAN_PLACEHOLDER_FIELD`（``-9.99999+990``，**恒 12 列**）
2. 每行恒为 ``4 * 12 = 48`` 列（含 NaN 占位行）
3. 读回后 :func:`is_nan_placeholder` 能把占位还原为 ``nan``
4. 跨族密度轴归一化（``g/cm3`` -> ``cm^-3``）
"""
