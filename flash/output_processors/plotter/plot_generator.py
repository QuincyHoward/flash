"""
plot_generator.py — FLASH 数据自适应维度绘图器

FlashPlotter 根据数据的维度自动选择适当的绘图类型:
  - 1D: 线图 (x vs value)
  - 2D: 伪彩色图 (2D colormap)
  - 3D: 切片伪彩色图 (通过固定一个维度取切片)
  - AMR 网格图
  - 文件夹批量绘图
"""

import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from ..hdf5processor import DATA_CONFIG, DataCalculator
from ..loader import FlashDataContainer

# ── PPT 友好绘图规范 (字体≥18, 全英文, dpi=200) ──
from .plot_style import apply_plot_style, english, save_figure, setup_legend
apply_plot_style()


class FlashPlotter:
    """FLASH 自适应维度绘图器

    用法:
        container = loader.load()
        plotter = FlashPlotter(container)
        plotter.plot("dens", save_path="output/dens.png")
        plotter.plot_all(save_dir="output/plots/")
        plotter.plot_amr_grid("dens", save_path="amr_dens.png")

    class method:
        FlashPlotter.plot_folder("folder/", "dens", save_dir="output/")
    """

    def __init__(self, container: FlashDataContainer):
        self.container = container
        self.ndim = container.ndim

    def _get_label(self, varname: str) -> str:
        """获取物理量的绘图标签（含单位）"""
        cfg = DATA_CONFIG.get(varname, {})
        label = cfg.get("description", varname)
        unit = cfg.get("unit", "")
        if unit:
            return f"{label} [{unit}]"
        return label

    # ── 主绘制接口 ────────────────────────────────────────────

    def plot(self, varname: str, save_path: str = None,
             title: str = None, show: bool = False, use_derived: bool = False,
             **kwargs):
        """自适应维度的主绘图接口

        参数:
            varname:       物理量名（先查 data 再查 derived）
            save_path:     保存路径
            title:         图像标题
            show:          是否显示
            use_derived:   是否优先从 derived 中查找
            **kwargs:      传递给底层绘图函数
        """
        if use_derived:
            arr = self.container.derived.get(varname)
        else:
            arr = self.container.data.get(varname, self.container.derived.get(varname))

        if arr is None:
            raise KeyError(f"变量 '{varname}' 不存在于 data 或 derived 中")

        if self.ndim == 1:
            return self._plot_1d(varname, save_path, title, show, data_arr=arr, **kwargs)
        elif self.ndim == 2:
            return self._plot_2d(varname, save_path, title, show, data_arr=arr, **kwargs)
        elif self.ndim == 3:
            return self._plot_3d(varname, save_path, title, show, data_arr=arr, **kwargs)

    def plot_all(self, save_dir: str = "output_processors_plots",
                 var_names: list = None, include_derived: bool = True):
        """绘制所有（或指定）物理量并保存"""
        if var_names is None:
            var_names = list(self.container.data.keys())
            if include_derived:
                var_names += list(self.container.derived.keys())

        os.makedirs(save_dir, exist_ok=True)
        saved_files = []
        for vname in var_names:
            if vname in self.container.data:
                arr = self.container.data[vname]
            elif vname in self.container.derived:
                arr = self.container.derived[vname]
            else:
                continue
            fname = f"{vname}_{self.ndim}d.png"
            fpath = os.path.join(save_dir, fname)
            try:
                self.plot(vname, save_path=fpath, title=f"{vname} ({self.ndim}D)")
                saved_files.append(fpath)
                print(f"  [OK] {fpath}")
            except Exception as e:
                print(f"  [FAIL] {vname}: {e}")
        return saved_files

    # ── 1D 绘图 ───────────────────────────────────────────────

    def _plot_1d(self, varname: str, save_path: str, title: str,
                 show: bool, data_arr: np.ndarray = None, **kwargs):
        # 扁平化容器 (extract_var 模式, yt/h5py 提取): 直接使用全局坐标
        if getattr(self.container, "flat", False):
            arr = data_arr if data_arr is not None else self.container.data[varname]
            x = np.asarray(self.container.x)
            y = np.asarray(arr)
            idx = np.argsort(x)

            fig, ax = plt.subplots(figsize=(10, 5))
            ax.plot(x[idx], y[idx], "b-", linewidth=1.5, **kwargs)
            ax.set_xlabel("x [cm]")
            ax.set_ylabel(self._get_label(varname))
            ax.set_title(title or f"{varname} (1D, t={self.container.simulation_time:.3e}s)")
            ax.grid(True, alpha=0.3)

            if save_path:
                plt.savefig(save_path, dpi=200, bbox_inches="tight")
            if show:
                plt.show()
            plt.close(fig)
            return

        g = self.container.grid
        x_list = g["x_global"]
        arr = data_arr if data_arr is not None else self.container.data[varname]

        all_x, all_y = [], []
        for b in range(self.container.nblocks):
            all_x.extend(x_list[b])
            all_y.extend(arr[b])
        idx = np.argsort(all_x)

        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(np.array(all_x)[idx], np.array(all_y)[idx], "b-",
                linewidth=1.5, **kwargs)
        ax.set_xlabel("x [cm]")
        ax.set_ylabel(self._get_label(varname))
        ax.set_title(title or f"{varname} (1D, t={self.container.simulation_time:.3e}s)")
        ax.grid(True, alpha=0.3)

        if save_path:
            plt.savefig(save_path, dpi=200, bbox_inches="tight")
        if show:
            plt.show()
        plt.close(fig)

    # ── 2D 绘图 ───────────────────────────────────────────────

    def _plot_2d(self, varname: str, save_path: str, title: str,
                 show: bool, data_arr: np.ndarray = None, **kwargs):
        # 扁平化容器 (extract_var 模式): 直接使用全局坐标重建网格
        if getattr(self.container, "flat", False):
            arr = data_arr if data_arr is not None else self.container.data[varname]
            x = np.asarray(self.container.x)
            y = np.asarray(self.container.y)
            v = np.asarray(arr)
            idx = np.argsort(np.lexsort((y, x)))
            x_unique = sorted(set(np.round(x[idx], 10)))
            y_unique = sorted(set(np.round(y[idx], 10)))
            Z = v[idx].reshape(len(y_unique), len(x_unique))

            fig, ax = plt.subplots(figsize=(7, 6))
            im = ax.pcolormesh(x_unique, y_unique, Z, shading="auto",
                               cmap="inferno", **kwargs)
            cb = plt.colorbar(im, ax=ax)
            cb.set_label(self._get_label(varname))
            ax.set_xlabel("x [cm]")
            ax.set_ylabel("y [cm]")
            ax.set_title(title or f"{varname} (2D, t={self.container.simulation_time:.3e}s)")

            if save_path:
                plt.savefig(save_path, dpi=200, bbox_inches="tight")
            if show:
                plt.show()
            plt.close(fig)
            return

        g = self.container.grid
        x_list, y_list = g["x_global"], g["y_global"]
        arr = data_arr if data_arr is not None else self.container.data[varname]

        all_x, all_y, all_v = [], [], []
        for b in range(self.container.nblocks):
            ny, nx = arr[b].shape
            xv, yv = np.meshgrid(x_list[b], y_list[b])
            all_x.extend(xv.ravel())
            all_y.extend(yv.ravel())
            all_v.extend(arr[b].ravel())

        x_unique = sorted(set(np.round(all_x, 10)))
        y_unique = sorted(set(np.round(all_y, 10)))

        fig, ax = plt.subplots(figsize=(7, 6))
        Z = np.array(all_v).reshape(len(y_unique), len(x_unique))
        im = ax.pcolormesh(x_unique, y_unique, Z, shading="auto",
                           cmap="inferno", **kwargs)
        cb = plt.colorbar(im, ax=ax)
        cb.set_label(self._get_label(varname))
        ax.set_xlabel("x [cm]")
        ax.set_ylabel("y [cm]")
        ax.set_title(title or f"{varname} (2D, t={self.container.simulation_time:.3e}s)")

        if save_path:
            plt.savefig(save_path, dpi=200, bbox_inches="tight")
        if show:
            plt.show()
        plt.close(fig)

    # ── 3D 绘图（切片）─────────────────────────────────────────

    def _plot_3d(self, varname: str, save_path: str, title: str,
                 show: bool, data_arr: np.ndarray = None, **kwargs):
        g = self.container.grid
        x_list, y_list, z_list = g["x_global"], g["y_global"], g["z_global"]
        arr = data_arr if data_arr is not None else self.container.data[varname]
        nz, ny, nx = arr.shape[1:]

        # 默认取 z 方向中平面（仅用 block 0，多块坐标重叠时取第一块）
        mid = nz // 2
        if nz == 1:
            mid = 0

        b0 = 0
        sliced = arr[b0][mid, :, :]
        xu = x_list[b0]
        yu = y_list[b0]

        fig, ax = plt.subplots(figsize=(7, 6))
        im = ax.pcolormesh(xu, yu, sliced, shading="auto", cmap="inferno", **kwargs)
        cb = plt.colorbar(im, ax=ax)
        cb.set_label(self._get_label(varname))
        ax.set_xlabel("x [cm]")
        ax.set_ylabel("y [cm]")
        if z_list and z_list[0] is not None and len(z_list[0]) > mid:
            zval = z_list[0][mid]
        else:
            zval = "mid"
        ax.set_title(title or f"{varname} (3D z-slice z={zval:.3e} cm, "
                            f"t={self.container.simulation_time:.3e}s)")
        if save_path:
            plt.savefig(save_path, dpi=200, bbox_inches="tight")
        if show:
            plt.show()
        plt.close(fig)

    # ── AMR 网格结构图 ─────────────────────────────────────────

    def plot_amr_grid(self, varname: str = None, save_path: str = None,
                      title: str = None, show: bool = False):
        """绘制 AMR 块网格结构，可选覆盖物理量伪彩色

        对 1D: 显示块边界 + 物理量线图
        对 2D: 显示块边界框网格 + 物理量伪彩色（可选）
        对 3D: 显示块边界投影 + 物理量值（第一块中间切片）
        """
        g = self.container.grid
        bbox_block = None
        arr = None

        # 需要从 HDF5 获取完整 bounding box
        if varname:
            arr = self.container.data.get(varname, self.container.derived.get(varname))
            if arr is None:
                print(f"  [警告] 变量 '{varname}' 不可用，仅绘制网格")
                varname = None

        fig = plt.figure(figsize=(10, 8))

        if self.ndim == 1:
            ax = fig.add_subplot(111)
            # 先绘物理量
            if varname:
                x_list = g["x_global"]
                all_x, all_y = [], []
                for b in range(self.container.nblocks):
                    all_x.extend(x_list[b])
                    all_y.extend(arr[b])
                idx = np.argsort(all_x)
                ax.plot(np.array(all_x)[idx], np.array(all_y)[idx],
                        "b-", linewidth=1.5, label=varname)

            # 叠加块边界垂直线
            x_edges = g["x_edges"]
            ymin, ymax = ax.get_ylim() if varname else (0, 1)
            for b_edges in x_edges:
                for xe in b_edges:
                    ax.axvline(xe, color="red", linestyle="--", alpha=0.5, linewidth=0.8)
            if not varname:
                ax.set_ylim(ymin, ymax)

            ax.set_xlabel("x [cm]")
            ax.set_ylabel(self._get_label(varname) if varname else "")
            ax.set_title(title or f"AMR Grid (1D, {self.container.nblocks} blocks)")
            ax.grid(True, alpha=0.2)
            if varname:
                ax.legend()

        elif self.ndim == 2:
            ax = fig.add_subplot(111)
            # 需从 HDF5 获取原始完整 bounding box（所有块）
            x_list, y_list, x_edges = g["x_global"], g["y_global"], g["x_edges"]

            if varname:
                all_x, all_y, all_v = [], [], []
                for b in range(self.container.nblocks):
                    ny, nx = arr[b].shape
                    xv, yv = np.meshgrid(x_list[b], y_list[b])
                    all_x.extend(xv.ravel())
                    all_y.extend(yv.ravel())
                    all_v.extend(arr[b].ravel())
                xu = sorted(set(np.round(all_x, 10)))
                yu = sorted(set(np.round(all_y, 10)))
                Z = np.array(all_v).reshape(len(yu), len(xu))
                im = ax.pcolormesh(xu, yu, Z, shading="auto", cmap="inferno", alpha=0.8)
                plt.colorbar(im, ax=ax, label=self._get_label(varname))

            # 绘制块边界
            for b in range(self.container.nblocks):
                xmin, xmax = x_list[b][0], x_list[b][-1]
                ymin, ymax = y_list[b][0], y_list[b][-1]
                dx = (xmax - xmin) / (len(x_list[b]) - 1) if len(x_list[b]) > 1 else 1
                dy = (ymax - ymin) / (len(y_list[b]) - 1) if len(y_list[b]) > 1 else 1
                rect = plt.Rectangle(
                    (xmin - dx/2, ymin - dy/2),
                    xmax - xmin + dx, ymax - ymin + dy,
                    fill=False, edgecolor="red", linewidth=1.0, linestyle="--"
                )
                ax.add_patch(rect)
                # 块编号
                ax.text((xmin + xmax) / 2, (ymin + ymax) / 2,
                        str(b), color="white",
                        ha="center", va="center",
                        bbox=dict(boxstyle="round,pad=0.2", facecolor="red", alpha=0.6))

            ax.set_xlabel("x [cm]")
            ax.set_ylabel("y [cm]")
            ax.set_title(title or f"AMR Grid (2D, {self.container.nblocks} blocks)")

        elif self.ndim == 3:
            # 3D 块边界投影到 xy 平面（仅用 block 0 绘制）
            ax = fig.add_subplot(111)
            x_list, y_list, z_list = g["x_global"], g["y_global"], g["z_global"]

            if varname:
                nz = arr.shape[1]
                mid = nz // 2
                # 仅用第一块，因为多块在同一细化层级时坐标重叠
                b0 = 0
                sliced = arr[b0][mid, :, :]
                xu = x_list[b0]
                yu = y_list[b0]
                im = ax.pcolormesh(xu, yu, sliced, shading="auto",
                                   cmap="inferno", alpha=0.8)
                plt.colorbar(im, ax=ax, label=self._get_label(varname))

            for b in range(self.container.nblocks):
                xmin, xmax = x_list[b][0], x_list[b][-1]
                ymin, ymax = y_list[b][0], y_list[b][-1]
                dx = (xmax - xmin) / (len(x_list[b]) - 1) if len(x_list[b]) > 1 else 1
                dy = (ymax - ymin) / (len(y_list[b]) - 1) if len(y_list[b]) > 1 else 1
                rect = plt.Rectangle(
                    (xmin - dx/2, ymin - dy/2),
                    xmax - xmin + dx, ymax - ymin + dy,
                    fill=False, edgecolor="red", linewidth=0.8, linestyle="--"
                )
                ax.add_patch(rect)

            ax.set_xlabel("x [cm]")
            ax.set_ylabel("y [cm]")
            ax.set_title(title or f"AMR Grid (3D xy-proj, {self.container.nblocks} blocks)")

        if save_path:
            plt.savefig(save_path, dpi=200, bbox_inches="tight")
        if show:
            plt.show()
        plt.close(fig)

    # ── 文件夹批量处理 ─────────────────────────────────────────

    @classmethod
    def plot_folder(cls, folder_path: str, var_name: str = "dens",
                    save_dir: str = None, pattern: str = "*chk*",
                    compute_derived: bool = True):
        """批量处理文件夹中所有 HDF5 文件并绘图

        参数:
            folder_path:  HDF5 文件所在文件夹
            var_name:     要绘制的变量
            save_dir:     图像保存目录（默认 folder_path/plots/）
            pattern:      文件匹配模式
            compute_derived: 是否计算派生变量
        返回:
            保存的文件路径列表
        """
        from ..loader import FlashDataLoader

        if save_dir is None:
            save_dir = os.path.join(folder_path, "plots")
        os.makedirs(save_dir, exist_ok=True)

        containers = FlashDataLoader.load_folder(folder_path, pattern=pattern,
                                                  compute_derived=compute_derived)

        saved = []
        for c in containers:
            plotter = cls(c)
            # 优先从 derived 查找
            arr = c.data.get(var_name, c.derived.get(var_name))
            if arr is None:
                print(f"  [跳过] {os.path.basename(c.filepath)}: 无变量 {var_name}")
                continue
            fname = f"{os.path.basename(c.filepath)}_{var_name}.png"
            fpath = os.path.join(save_dir, fname)
            try:
                plotter.plot(var_name, save_path=fpath,
                             title=f"{var_name} ({c.ndim}D, "
                                   f"t={c.simulation_time:.3e}s)")
                saved.append(fpath)
                print(f"  [OK] {fname}")
            except Exception as e:
                print(f"  [FAIL] {fname}: {e}")

        print(f"  共处理 {len(containers)} 个文件, 保存 {len(saved)} 张图")
        return saved

    @classmethod
    def plot_folder_all_vars(cls, folder_path: str,
                              save_dir: str = None,
                              pattern: str = "*chk*",
                              var_names: list = None):
        """批量处理文件夹，每个文件绘制多个变量"""
        from ..loader import FlashDataLoader

        if save_dir is None:
            save_dir = os.path.join(folder_path, "plots")
        os.makedirs(save_dir, exist_ok=True)

        containers = FlashDataLoader.load_folder(folder_path, pattern=pattern)

        saved = []
        for c in containers:
            plotter = cls(c)
            if var_names is None:
                vars_to_plot = list(c.data.keys()) + list(c.derived.keys())
            else:
                vars_to_plot = var_names

            for vname in vars_to_plot:
                if vname not in c.data and vname not in c.derived:
                    continue
                fname = f"{os.path.basename(c.filepath)}_{vname}.png"
                fpath = os.path.join(save_dir, fname)
                try:
                    plotter.plot(vname, save_path=fpath)
                    saved.append(fpath)
                except Exception:
                    pass
        return saved

    # ── 时空（x-t）图 ─────────────────────────────────────────
    #
    # ★★ 为什么必须单独提供：FLASH 的 chk 由 `checkpointFileIntervalStep`
    #    触发，**Δt 随 dt 变化 → 帧在时间轴上高度不均匀**。实测同一台仿真：
    #      +ug 腿   81 帧  Δt ≡ 2.000e-11            (1.00×)
    #      AMR 腿  317 帧  Δt 1.36e-12 … 7.19e-11   (52.7×)
    #    用 `imshow(..., extent=(x0,x1,t0,t1))` 会把**各行按等间距铺开**，
    #    时间轴被局部拉偏可达数千个百分点（实测 ~3576%），
    #    从而让"同一物理运动在不同算例上显得前沿速度不同"（纯假象）。
    #    ⇒ 必须 `pcolormesh` + **真实逐帧时间坐标**。

    @staticmethod
    def time_uniformity(times) -> dict:
        """检查帧时间间隔是否均匀（用于判断能否用 imshow 类渲染）。

        返回:
            {"n", "dt_min", "dt_max", "dt_med", "ratio", "uniform", "max_distort_pct"}
            `max_distort_pct` = 按等间距假设时时间轴的最大局部畸变百分比。
        """
        t = np.asarray(times, float)
        out = {"n": int(t.size), "dt_min": float("nan"), "dt_max": float("nan"),
               "dt_med": float("nan"), "ratio": float("nan"),
               "uniform": False, "max_distort_pct": float("nan")}
        if t.size < 3:
            return out
        dt = np.diff(t)
        dt = dt[np.isfinite(dt) & (dt > 0)]
        if dt.size == 0:
            return out
        out.update(dt_min=float(dt.min()), dt_max=float(dt.max()),
                   dt_med=float(np.median(dt)))
        out["ratio"] = out["dt_max"] / out["dt_min"]
        out["uniform"] = out["ratio"] <= 1.05
        out["max_distort_pct"] = (out["dt_max"] / out["dt_med"] - 1.0) * 100.0
        return out

    @staticmethod
    def collect_xt(folder_path: str, var_name: str = "dens",
                   pattern: str = "*chk*", compute_derived: bool = True,
                   grid_n: int = 900, verbose: bool = True):
        """把文件夹内所有帧堆叠成时空数据 `(times, x, Z)`。

        ★ 返回的 `times` 是**每帧的真实仿真时间 [s]**，**不是帧序号**。
          调用方（含本类的 `plot_xt_map`）必须用它作为时间坐标。

        参数:
            grid_n: 公共 x 网格点数（各帧 AMR 网格不同 → 需插值到公共网格）

        返回:
            (times, x_common, Z[n_t, n_x])；无数据返回 (None, None, None)
        """
        from ..loader import FlashDataLoader

        containers = FlashDataLoader.load_folder(
            folder_path, pattern=pattern, compute_derived=compute_derived)
        recs = []
        for c in containers:
            arr = c.data.get(var_name, c.derived.get(var_name))
            if arr is None or c.x is None:
                continue
            x = np.asarray(c.x).ravel()
            v = np.asarray(arr).ravel()
            if x.size == 0 or x.size != v.size:
                # 广播维度（如 (nx,1) / (nx,ny)）→ 取第 0 行（1D 常用）
                v = v.reshape(x.size, -1)[:, 0] if v.size % x.size == 0 else v
                if v.size != x.size:
                    continue
            o = np.argsort(x)
            recs.append((float(c.simulation_time), x[o], v[o]))

        if not recs:
            return None, None, None
        recs.sort(key=lambda r: r[0])
        times = np.array([r[0] for r in recs], float)

        x0 = max(r[1].min() for r in recs)
        x1 = min(r[1].max() for r in recs)
        xg = np.linspace(x0, x1, grid_n)
        Z = np.vstack([np.interp(xg, x, v, left=np.nan, right=np.nan)
                       for _, x, v in recs])

        if verbose:
            u = FlashPlotter.time_uniformity(times)
            print(f"  [x-t] {var_name}: {u['n']} 帧, "
                  f"t = {times[0]:.4e} … {times[-1]:.4e} s")
            if np.isfinite(u["ratio"]):
                msg = ("均匀" if u["uniform"]
                       else f"**非均匀** (最大/最小 = {u['ratio']:.2f}×)")
                print(f"        Δt: {u['dt_min']:.3e} … {u['dt_max']:.3e}  {msg}")
                if not u["uniform"]:
                    print(f"        ★ 不可用 imshow(等间距假设); "
                          f"本函数已按真实时间坐标构建, 请配合 pcolormesh")
        return times, xg, Z

    @classmethod
    def plot_xt_map(cls, folder_path: str, var_name: str = "dens",
                    save_path: str = None, pattern: str = "*chk*",
                    xlim=None, ylim=None, use_log: bool = None,
                    cmap: str = "viridis", vmin=None, vmax=None,
                    compute_derived: bool = True, grid_n: int = 900,
                    add_dimension: bool = False, figsize=(11, 7)):
        """绘制单个物理量的**时空（x-t）图**。

        与 `plot_folder` 的区别：`plot_folder` 是**逐帧各出一张图**；
        本函数把多帧**沿时间堆叠**成一张时空图（多文件 → 一张图）。

        ★ 用 `pcolormesh` + **真实逐帧时间坐标**渲染 —— 对时间间隔不均匀的
          chk 序列（FLASH 常态）是**唯一正确**的做法；`imshow` 会歪曲时间轴。

        参数:
            use_log: None = 按量级自动判断（跨 >2 个十进则用对数）
            xlim / ylim: 形如 (min, max)，单位 µm / ns
            add_dimension: True 时把 x 轴换算成 µm（默认按容器单位 cm → µm）
        """
        times, xg, Z = cls.collect_xt(
            folder_path, var_name, pattern=pattern,
            compute_derived=compute_derived, grid_n=grid_n)
        if times is None:
            print(f"  [X] 无可用数据: {folder_path} ({var_name})")
            return None

        # 单位：x [cm] → µm；t [s] → ns
        x_plot = xg * 1e4
        t_plot = times * 1e9

        fin = Z[np.isfinite(Z)]
        if fin.size == 0:
            print("  [X] 数据全为 NaN")
            return None
        if use_log is None:
            pos = fin[fin > 0]
            use_log = bool(pos.size and pos.size > fin.size * 0.5
                           and fin.max() / max(pos.min(), 1e-300) > 1e2)
        if use_log:
            pos = fin[fin > 0]
            floor = float(pos.min()) * 0.5 if pos.size else 1e-30
            Zp = np.where(np.isfinite(Z) & (Z > 0), Z, floor)
            from matplotlib.colors import LogNorm
            if vmin is None:
                vmin = floor * 1.0000001
            if vmax is None:
                vmax = float(Zp.max())
            norm = LogNorm(vmin=vmin, vmax=vmax)
        else:
            Zp = Z
            if vmin is None:
                vmin = float(fin.min())
            if vmax is None:
                vmax = float(fin.max())
            from matplotlib.colors import Normalize
            norm = Normalize(vmin=vmin, vmax=vmax)

        cfg = DATA_CONFIG.get(var_name, {})
        clabel = f"{cfg.get('description', var_name)} [{cfg.get('unit', '')}]"

        fig, ax = plt.subplots(figsize=figsize)
        X, T = np.meshgrid(x_plot, t_plot)
        im = ax.pcolormesh(X, T, Zp, shading="auto", cmap=cmap,
                           norm=norm, rasterized=True)
        ax.set_xlabel(r"Position  $x$  [$\mu$m]", fontsize=20)
        ax.set_ylabel("Time  $t$  [ns]", fontsize=20)
        ax.set_title(f"{var_name}  x-t  ({os.path.basename(folder_path.rstrip(os.sep))})",
                     fontsize=22, pad=10)
        ax.tick_params(labelsize=17, width=1.8)
        for s in ax.spines.values():
            s.set_linewidth(1.8)
        if xlim is not None:
            ax.set_xlim(*xlim)
        if ylim is not None:
            ax.set_ylim(*ylim)
        cb = fig.colorbar(im, ax=ax, pad=0.02)
        cb.set_label(clabel + ("  (log)" if use_log else ""), fontsize=17)
        cb.ax.tick_params(labelsize=15, width=1.6)
        cb.outline.set_linewidth(1.6)

        if save_path:
            os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
            fig.savefig(save_path, dpi=300, bbox_inches="tight")
            print(f"  [OK] {os.path.basename(save_path)}")
        plt.close(fig)
        return save_path

    # ── 多子图复合绘图 ─────────────────────────────────────────

    def plot_multi_panel(self, var_names: list, save_path: str = None):
        """多物理量并排比较图"""
        n = len(var_names)
        fig, axes = plt.subplots(1, n, figsize=(5 * n, 4))
        if n == 1:
            axes = [axes]

        for ax, vname in zip(axes, var_names):
            arr = self.container.data.get(vname, self.container.derived.get(vname))
            if arr is None:
                ax.text(0.5, 0.5, f"No {vname}", ha="center", va="center")
                continue

            if self.ndim == 1:
                g = self.container.grid
                x_list = g["x_global"]
                all_x, all_y = [], []
                for b in range(self.container.nblocks):
                    all_x.extend(x_list[b])
                    all_y.extend(arr[b])
                idx = np.argsort(all_x)
                ax.plot(np.array(all_x)[idx], np.array(all_y)[idx])
                ax.set_xlabel("x [cm]")
            elif self.ndim == 2:
                g = self.container.grid
                xf, yf, vf = [], [], []
                for b in range(self.container.nblocks):
                    ny, nx = arr[b].shape
                    xv, yv = np.meshgrid(g["x_global"][b], g["y_global"][b])
                    xf.extend(xv.ravel())
                    yf.extend(yv.ravel())
                    vf.extend(arr[b].ravel())
                xu = sorted(set(np.round(xf, 10)))
                yu = sorted(set(np.round(yf, 10)))
                im = ax.pcolormesh(xu, yu, np.array(vf).reshape(len(yu), len(xu)),
                                   shading="auto", cmap="inferno")
                plt.colorbar(im, ax=ax)
                ax.set_xlabel("x [cm]")
                ax.set_ylabel("y [cm]")
            ax.set_title(self._get_label(vname))
            ax.grid(True, alpha=0.3)

        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, dpi=200, bbox_inches="tight")
        plt.close(fig)
        return fig
