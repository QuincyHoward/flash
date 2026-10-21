"""极短验证的运行提示 —— 统一告知"这次只是试跑，正式仿真该改哪个时间参数"。

为什么需要它
------------
极短验证（tmax ~1e-11 s）只回答一个问题：**输入能不能被 FLASH 接受并启动**。
它不产生有物理意义的结果（1e-11 s 内激光还没把靶加热，流体几乎没动）。
如果不加提示，很容易把这种"跑通了"误当成"算对了"，或者下次忘了把 tmax 改回
真实值就直接当正式结果用。

用法
----
    from flash.scenarios.hints import short_validation_notice, is_short_run

    if is_short_run(tmax):
        short_validation_notice(
            tmax_s=tmax, scene_name="ch_center",
            where="ch_center/__init__.py: params['tmax'] (默认 1.2e-9 s)",
        )
"""

from __future__ import annotations

# 低于这个值一律视为"极短验证"（覆盖 1e-13 ~ 1e-10 的常见试跑刻度）。
SHORT_RUN_THRESHOLD_S = 1e-9

_BAR = "=" * 72


def is_short_run(tmax_s: float) -> bool:
    """判断给定 tmax 是否属于极短验证范畴。"""
    try:
        return float(tmax_s) < SHORT_RUN_THRESHOLD_S
    except (TypeError, ValueError):
        return False


def short_validation_notice(
    tmax_s: float,
    scene_name: str = "",
    where: str = "",
    extra: str = "",
) -> None:
    """打印极短验证横幅：当前 tmax、它保证了什么、正式仿真要改哪里。

    Args:
        tmax_s:     本次使用的仿真结束时间（秒）
        scene_name: 场景名，仅用于显示
        where:      正式仿真应修改的时间参数位置（文件:符号），越具体越好
        extra:      额外提示（如"改完记得重新生成输入"）
    """
    print()
    print(_BAR)
    print(f" ⚠ 极短验证模式  tmax = {float(tmax_s):.3e} s"
          + (f"   [{scene_name}]" if scene_name else ""))
    print(_BAR)
    print("   本次运行只用于确认：")
    print("     ① 输入文件能生成并自洽   ② FLASH setup/编译通过")
    print("     ③ 程序能启动并写出首帧   ④ 物理量没有 NaN/Inf")
    print("   ★ 它**不产生物理结果**：该时间尺度内激光尚未有效加热靶材，")
    print("     流体/温度/密度剖面都还停在初始态附近，请勿用于分析或出图。")
    if where:
        print()
        print("   正式仿真请修改时间参数：")
        print(f"     {where}")
    print()
    print("   常见做法：把 tmax 调到纳秒量级（如 1.0e-9 ~ 5.0e-9），")
    print("   或直接传 --tmax <秒> 覆盖（不传则用场景默认值）。")
    if extra:
        print(f"   注意：{extra}")
    print(_BAR)
    print()
