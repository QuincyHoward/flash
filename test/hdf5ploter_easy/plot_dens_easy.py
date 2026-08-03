"""使用 yt 极简绘制密度剖面"""
import yt, matplotlib.pyplot as plt, numpy as np

# PPT-friendly plot style (fonts >= 18, English only)
try:
    from output_processors.plotter.plot_style import apply_plot_style
    apply_plot_style()
except ImportError:
    pass

ds = yt.load("lasslab_hdf5_plt_cnt_0066")                     # 加载数据
ray = ds.ray(ds.domain_left_edge, ds.domain_right_edge)        # 沿 x 方向采样
x = ray[("index", "x")].to("cm").d                             # 位置 (cm)
d = ray[("flash", "dens")].to("g/cm**3").d                    # 密度

idx = np.argsort(x)
plt.plot(x[idx], d[idx])
plt.xlabel("x (cm)")
plt.ylabel(r"density (g/cm$^3$)")
plt.savefig("dens_plot_yt.png", dpi=200)




