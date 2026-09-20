"""从 FLASH chk 正确提取帧数据的公共工具。

★★★ 2026-09-12 教训 (三个都曾导致错误结论):
 1. `real scalars` / `integer scalars` 是 **record array** `(name, value)`,
    **不是** dict-of-arrays。必须:
        d = f["real scalars"][()]
        val = d["value"][np.char.strip(d["name"]) == b"time"]
    之前写 `a["time"]` 会静默失败 -> t/dt 读出 nan, 却"看起来"跑通了。
 2. `coordinates` 是 **(nblk, 3)** 的**块中心**, 只有 131 个值!
    逐格坐标必须用 `bounding box` (nblk,3,2) + nxb 重建:
        <ug> 下 blocksize = (bb[1]-bb[0])/nxb, x_cell = bb[0] + (i+0.5)*dx
 3. species 数组是**质量分数**, 内部填充值 **1e-99**(负指数地板), 故
    `v > 0` 恒真 -> "存活格数"无意义。正确判据: 用**相对阈值**
    (如 v > 1e-6 * v.max()) 或直接看该层的**空间跨度**。
    `dens` 才是判断几何的主量。
"""
import numpy as np
import h5py


def scalars(f, kind="real scalars"):
    """返回 {name: value} —— 正确处理 record array。"""
    out = {}
    if kind not in f:
        return out
    d = f[kind][()]
    try:
        names = d.dtype.names or ()
    except AttributeError:
        return out
    if "name" not in names or "value" not in names:
        return out
    nm = d["name"]
    vl = d["value"]
    for i in range(len(nm)):
        try:
            k = nm[i]
            k = k.decode() if isinstance(k, (bytes, bytearray)) else str(k)
            out[k.strip()] = vl[i]
        except Exception:  # noqa: BLE001
            pass
    return out


def cell_coords(f, nxb=None):
    """重建**逐格**物理坐标 (cm), 按块序拼接。

    <ug> 固定块: 每块 nxb 格, 块内均匀。
    x_cell = bb_min + (i + 0.5) * dx,  dx = (bb_max - bb_min) / nxb
    """
    if "bounding box" not in f:
        return None
    bb = np.asarray(f["bounding box"][()], dtype=np.float64)  # (nblk,3,2)
    if nxb is None:
        isc = scalars(f, "integer scalars")
        nxb = int(isc.get("nxb", 0))
    if nxb <= 0:
        # 退路: 用 dens 的最后一维
        nxb = int(f["dens"].shape[-1]) if "dens" in f else 0
    if nxb <= 0:
        return None
    nblk = bb.shape[0]
    out = np.empty(nblk * nxb, dtype=np.float64)
    for b in range(nblk):
        x0, x1 = bb[b, 0, 0], bb[b, 0, 1]
        dx = (x1 - x0) / nxb
        out[b * nxb:(b + 1) * nxb] = x0 + (np.arange(nxb) + 0.5) * dx
    return out


def cell_var(f, name, nxb=None):
    """取某个逐格变量, 展平为 (nblk*nxb,) 并与 cell_coords 对齐。"""
    if name not in f:
        return None
    v = np.asarray(f[name][()], dtype=np.float64)
    return v.reshape(-1)


def frame(path):
    """读取一帧的完整、正确对齐的数据。"""
    with h5py.File(path, "r") as f:
        rs = scalars(f, "real scalars")
        isc = scalars(f, "integer scalars")
        nxb = int(isc.get("nxb", 0)) or None
        x = cell_coords(f, nxb)
        out = {"t": float(rs.get("time", np.nan)),
               "dt": float(rs.get("dt", np.nan)),
               "nxb": nxb, "x": x}
        for k in ("dens", "tele", "tion", "trad", "pres", "velx", "ye",
                  "nele", "sumy", "qesx", "qenl", "corq", "mfpe", "cond",
                  "eint", "eele", "erad", "depo", "lase", "qesh", "fllm"):
            out[k] = cell_var(f, k, nxb)
        for s in ("cham", "shld", "samp", "tar1", "tar2", "tar3", "tar4",
                  "tar6"):
            out[s] = cell_var(f, s, nxb)
        if "sim info" in f:
            si = f["sim info"][()]
            try:
                sc = si["setup call"][0]
                out["setup_call"] = (sc.decode(errors="replace")
                                     if isinstance(sc, (bytes, bytearray))
                                     else str(sc))
            except Exception:  # noqa: BLE001
                pass
        return out


def sort_by_x(x, *arrs):
    """按 x 升序排序 x 与所有伴随数组。"""
    if x is None:
        return (x,) + arrs
    o = np.argsort(x)
    res = [x[o]]
    for a in arrs:
        res.append(a[o] if a is not None and a.size == x.size else a)
    return tuple(res)
