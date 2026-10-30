# PlasmaPy 在 output_pro 中的使用指南

> 适用: `flash/flash/output_pro`（方案 A 适配层架构）· PlasmaPy 2026.2.0 · 2026-10-30
> 关联文档: `docs/PlasmaPy在后处理分析的使用方案.html`（四方案选型）、`docs/PlasmaPy_bridge_测试报告.md`（12 项用例实测）

---

## 0. 30 秒上手

```python
from flash.output_pro.loader import FlashDataLoader
from flash.output_pro import plasmapy_bridge as pb

c = FlashDataLoader("path/to/hdf5_chk_0005").load(compute_derived=True)

lnL  = pb.coulomb_log_profile(c)      # 逐网格库仑对数 (无量纲 ndarray)
lD   = pb.debye_length_profile(c)     # 德拜长度 (astropy Quantity [m])
x_c, nc = pb.critical_surface(c)      # 临界密度面位置 + n_c(0.351μm) 复核
kn   = pb.knudsen_number_e(c)         # 电子 Knudsen 层数 λ_mfp/L_Te (>1 ⇒ SNB 主导)
kap  = pb.spitzer_kappa_e(c)          # Spitzer/Braginskii κ_e^SH [W/(m·K)]
Te   = pb.to_quantity(c, "tele")      # 任意 DATA_CONFIG 变量 → SI Quantity
```

plasmapy 未安装时：`import` 本模块不报错，物理量函数抛带安装指引的 `RuntimeError`（优雅降级，HPC 安全）。

---

## 1. 安装（editable，source of truth = output_pro 内克隆）

PlasmaPy 源码托管在 `flash/flash/output_pro/PlasmaPy/src/PlasmaPy`（git clone, tag v2026.2.0，
**`.git` 目录不可删**——setuptools-scm 从中读版本号）。

### Windows（分析机 / 项目 venv，需联网）

```bash
# 装进当前解释器
python flash/output_pro/PlasmaPy/install_editable.py
# 或指定目标解释器
python flash/output_pro/PlasmaPy/install_editable.py --python .venv-win/Scripts/python.exe
# 只验证不安装 / 卸载
python flash/output_pro/PlasmaPy/install_editable.py --check
python flash/output_pro/PlasmaPy/install_editable.py --uninstall
```

安装器内置两道闸门：① 源码克隆完整性（pyproject.toml + src/plasmapy + .git）；
② 目标解释器 `python >= 3.12`。装完自动冒烟：`plasmapy.__file__` 必须落在
output_pro 克隆内 + `thermal_speed(1 keV, "e-")` 数值断言。

### WSL（条件支持）

```bash
# venv 的 python 必须 >= 3.12 (FLASH_VENV_DIR 注入的那个默认 venv 是 3.10 → 会被闸门拒绝)
python3.12 -m venv ~/.venv-py312
FLASH_VENV_DIR=~/.venv-py312
"$FLASH_VENV_DIR/bin/python" -m pip install -e \
  /mnt/e/PhySimX/PhySimX/simulation/flash_test/sandwich/flash/flash/output_pro/PlasmaPy/src/PlasmaPy
```

### HPC NC-E（✅ 已实测并并入正式 venv，miniforge/24.11 py3.12.8 基座）

2026-10-30 实测通过。探测发现 `module load miniforge/24.11` 提供 **Python 3.12.8**
（module python/3.10.8 不满足 requires-python，不可用），且 miniforge base 已带
numpy 2.1.3 / scipy 1.14.1 / pandas 2.2.3 / matplotlib / h5py。

安装方式（不是 editable —— 离线无法走 pip 构建隔离；用 `--target` 隔离目录）：

```bash
# 本机 (联网) 交叉下载 cp312/manylinux_2_17 wheel (19 whl / 21MB):
pip download --no-deps plasmapy==2026.2.0 astropy==8.0.2 pyerfa astropy-iers-data \
    xarray lmfit asteval dill uncertainties mpmath tqdm wrapt h5py \
    requests urllib3 idna charset-normalizer certifi packaging \
    -d <dir> --only-binary=:all: --python-version 3.12 --implementation cp \
    --platform manylinux_2_17_x86_64 --platform manylinux2014_x86_64 --platform any
# 上传后远端 (全自动编排: flash/output_pro/test/hpc_plasmapy_install.py):
module load miniforge/24.11
python -m pip install --no-index --no-deps \
    --target=$HOME/PhySimX/PhySimX/simulation/flash/flash_sim/plasmapy_site_test \
    <wheel_dir>/*.whl
# 运行: PYTHONPATH=<target> python ...
```

实测冒烟（ln162 节点）: thermal_speed 1.8755e7 m/s ✓ / Debye 6.9009e-6 m ✓ /
lnΛ=7.638 ✓ / n_c(0.351μm)=9.0491e21 cm⁻³ ✓ / κ_e(Braginskii) 2.8073e4 W/(m·K)
**与 Windows 同状态逐位一致**。离线 GitHub API 版本检查警告为良性（已捕获）。

**2026-10-30 后续**: plasmapy 已从 `--target` 旁路（PYTHONPATH 方式）正式并入
`.venv-hpc-nce`——venv 基座整体切换 miniforge py3.12.8（`--system-site-packages`），
wheel bundle `--no-index --no-deps` 装入，`plasmapy_site_test` 已删除；output_pro 源码
部署至 `flash_sim/flash/output_pro`，pytest 全套件 **52 passed**（含 12 bridge 用例）。
旧 py3.10 venv 保留 `.venv-hpc-nce-py310.bak` 可回滚。编排脚本
`flash/output_pro/test/hpc_plasmapy_merge.py`（阶段一 build+test / `--swap` 切换）。
⚠ mpmath 已 pin 1.3.0（1.4.1 的 `import gmp` 回退会被 `~/gmp/` 编译目录命名空间包
误捕，见 DEPENDENCIES.md）。

> 陷阱: ① `--target=~/...` 中 bash 不展开参数 `=` 后的 `~`，必须用 `$HOME/...`；
> ② pip `--target` 模式不认基座已装包，必须 `--no-deps`（否则要求 90MB 科学栈全在
> find-links 内，且 plasmapy 元数据 jupyter 链会让解析器回退死循环）；③ SFTP 不经
> shell，路径不能用 `~`。

### 依赖声明说明（为什么 pyproject.toml 里没有 plasmapy）

plasmapy 是**源码托管的带外可选依赖**：editable 安装自仓库内路径，pyproject extras 无法
跨平台引用该路径（`file:///E:/...` 在 WSL 失效）；写 PyPI 包名则违背 source-of-truth 约定。
因此 `pyproject.toml` / `deploy/env_spec.py` / wheelhouse 均不感知 plasmapy，
安装是显式的带外步骤（本指南 §1）。`deploy/env_spec.py` 顶部有注释说明此策略。

---

## 2. bridge API 参考（`flash/output_pro/plasmapy_bridge.py`）

| 函数 | 输入 → 输出 | 说明 |
|---|---|---|
| `to_quantity(container, varname)` | 容器+变量名 → SI `Quantity` | 复用 DATA_CONFIG 单位表做 CGS→SI；未注册单位/未注册映射抛 `ValueError` |
| `coulomb_log_profile(container, ion="Ti 3+", z_mean=3.0, method="GMS-6")` | → 无量纲 ndarray | 逐网格库仑对数；FL-SH/SNB 非局域判定核心输入 |
| `debye_length_profile(container)` | → Quantity [m] | 电子德拜长度 |
| `critical_density_351(wavelength_um=0.351)` | → Quantity [1/m³] | 激光临界密度；0.351 μm → 9.0491e21 cm⁻³（实测） |
| `critical_surface(container, wavelength_um=0.351)` | → (x_c, n_c) | 临界密度面位置（优先读容器坐标变量，无坐标返回扁平索引） |
| `mean_free_path_profile(container, ion="Ti 3+")` | → Quantity [m] | 电子平均自由程 |
| `knudsen_number_e(container)` | → 无量纲 ndarray | K_n = λ_mfp/L_Te，依赖派生变量 `ls_tele`；**>1 即非局域/SNB 主导区** |
| `spitzer_kappa_e(container, ion="p+", z_mean=3.0, model="Braginskii")` | → Quantity [W/(m·K)] | 平行电子热导率，FL-SH α=0.08 对照基准；逐点循环（交互级） |
| `saha_zbar(container)` | → Quantity 无量纲 | Saha 平衡 Z̄；**仅作 IONMIX 对照下界**（强耦合/快加热区失真） |
| `quantum_theta_profile(container)` | → 无量纲 ndarray | Θ_e = k_BT_e/E_F；与手写派生变量 `Theta_e` 已做 1e-6 级交叉验证 |
| `coupling_profile(species_pair)` | → 闭包 (T_K, n_m3)→Γ | 标量参考实现；逐网格 Γ_i 沿用手写 `Gamma_i` |
| `require_plasmapy()` | — | 门控；缺席时抛 `RuntimeError`（含安装指引） |

**字段纪律（重要）**：bridge 只依赖原始守恒量场（`tele/tion/nele/nion/zbar/dens/velx/ls_tele`），
**禁止读取 `fllm` 与 `q_fs`** —— FL-SH 的 `fllm` 已被覆写为 λ₃、SNB 保留自由流 `q_fs`，
语义跨模型不一致，混用即错（2026-10-30 结论）。

---

## 3. 如何新增一个 PlasmaPy 物理量（标准流程）

以「离子声速 `ion_sound_speed`」为例，四步：

### Step 1 — 在 bridge 中添加函数

```python
# flash/flash/output_pro/plasmapy_bridge.py
def ion_sound_speed_profile(container, gamma_e=5/3, gamma_i=3.0, ion="Ti 3+", z_mean=3.0):
    """离子声速 c_s(T_e, T_i, n_e)。返回 SI Quantity [m/s]。

    plasma 域 FLASH 1D 激光等离子体: γ_e 取 5/3 (全电离单原子),
    γ_i 取 3 (1D 冲击绝热) —— 与项目自相似/膨胀理论约定一致。
    """
    require_plasmapy()
    from plasmapy.formulary import ion_sound_speed
    Te = _si(container, "tele")
    Ti = _si(container, "tion")
    ne = _si(container, "nele")
    return ion_sound_speed(T_e=Te, T_i=Ti, ion=ion, z_mean=z_mean,
                           gamma_e=gamma_e, gamma_i=gamma_i)
```

并把它加进文件顶部 `__all__` 列表。

### Step 2 — 编写测试（模板）

```python
# flash/flash/output_pro/test/test_plasmapy_bridge.py 追加
def test_ion_sound_speed_vs_analytic():
    """c_s vs 解析式 sqrt((γ_e Z k_BT_e + γ_i k_BT_i)/m_i), rtol<1e-4。"""
    if not pb.HAS_PLASMAPY:
        pytest.skip("plasmapy 未安装")
    import astropy.units as u
    c = _FakeContainer(
        {"tele": np.full(4, 1e7), "tion": np.full(4, 1e6), "nele": np.full(4, 1e21)},
        {"tele": "K", "tion": "K", "nele": "1/cm^3"})
    cs = pb.ion_sound_speed_profile(c)
    # 手算: Z=3, m_Ti = 47.87 u
    m_i = 47.87 * 1.66053906660e-27
    kB = 1.380649e-23
    cs_manual = np.sqrt((5/3 * 3 * kB * 1e7 + 3.0 * kB * 1e6) / m_i)
    assert np.allclose(cs.value, cs_manual, rtol=1e-4)
```

要点：
- 测试一律用 `_FakeContainer`（受控物理工况）做数值验证——gen_test_data 的合成数据处于
  强耦合非物理区（Te=100–500 K, ne=8e23 cm⁻³, lnΛ<1），只用于**单位换算/降级路径**测试；
- Fake 容器的**值必须按 DATA_CONFIG 的 CGS 单位制存储**（nele 1/cm³、ls_tele cm、tele K），
  这是最易踩的坑（存储 SI 值 + 声明 CGS 单位 = 差 1e6 倍）；
- 降级路径测试参照 `test_graceful_degradation`（monkeypatch `pb.HAS_PLASMAPY=False`）。

### Step 3 — 运行

```bash
cd flash/flash/output_pro
python -m pytest test/test_plasmapy_bridge.py -v -s   # 新用例
python -m pytest test/ -v -s                          # 全套件回归
```

### Step 4 — 文档同步

- `__init__.py` docstring 用法示例追加一行；
- 本指南 §2 API 表添加条目；
- 若发现新的 PlasmaPy 陷阱（参照 §5 格式），记入 `docs/PlasmaPy_bridge_测试报告.md` §3。

### 何时该走方案 B（DataCalculator 派生变量）而不是 bridge？

- 交互/单文件探索 → **bridge**（本方案 A）；
- 批量 10⁵–10⁶ 网格 × 多文件随 `load(compute_derived=True)` 自动计算 →
  方案 B：在 `hdf5pro/` 新增 `_calc_xxx(data)`（SI 裸数组进出）注册进
  `_CALC_FUNCS` + `DATA_CONFIG`，性能敏感量用 PlasmaPy `*_lite` 接口。
  两方案可共存：bridge 是方案 B 的原型孵化器。

---

## 4. 现有派生变量与 PlasmaPy 的交叉验证对照

| 量 | 手写实现（hdf5pro/flash_hdf5.py） | PlasmaPy 实现（bridge） | 实测偏差 |
|---|---|---|---|
| 电子简并参数 Θ_e | `electron_degeneracy_parameter` | `quantum_theta_profile` | < 1e-6 |
| 离子耦合参数 Γ_i | `ion_coupling_parameter` | `coupling_profile` | < 1e-3 |
| 临界密度 n_c | （项目常数 9.05e21 cm⁻³） | `critical_density_351` | 0.01% |
| Spitzer κ_e | （无，FL-SH α=0.08 隐含） | `spitzer_kappa_e` | —（新增基准） |

---

## 5. 已知陷阱与性能约定（2026.2.0 实测）

1. **离子记法**：`"Ti 3+"` ✔ / `"Ti+3"` ✘（InvalidParticleError）；
2. **ClassicalTransport**：不接受数组 → bridge 逐点循环（交互级）；
   批量请走 `*_lite` 或方案 B；
3. **Spitzer 模型 Z 表**：仅 {1,2,4,16,∞}；任意 Z̄ 用 `model="Braginskii"`（bridge 默认）；
4. **多电荷 ion**：`ClassicalTransport(ion="Ti 3+")` 触发内部 Z 推断缺陷 →
   统一 `ion="p+", Z=z_mean`；
5. **coulomb_log_method="GMS-6"** 在 ClassicalTransport 内部崩溃（np.isnan(Particle)）→
   bridge 先自算 lnΛ 再显式传 `coulomb_log_ei`，保证与 `coulomb_log_profile` 一致
   （否则 'classical' vs GMS-6 差 ~13%，破坏 T^2.5/lnΛ 自洽性）；
6. **性能**：带单位版 formulary 比裸 numpy 慢 5–20×；批量路径用
   `plasma_frequency_lite(n, mass, Z)` / `thermal_speed_lite(T, mass, coeff)` 等
   SI 裸数值接口（与带单位版数值一致）；
7. **pytest**：本机沙箱下需 `-s`（`--capture=no`），否则 conftest 子进程报
   `WinError 6 句柄无效`（环境问题，非代码 bug）。

---

## 6. 三平台可用性速查

| 平台 | python | 状态 | 说明 |
|---|---|---|---|
| Windows managed | 3.14.6 | ✅ 已装 | `install_editable.py` 默认目标 |
| Windows .venv-win | 3.13.9 | ✅ 已装 | start_flash 全局测试环境 |
| WSL | ≥3.12 venv | 条件 ✅ | 默认 venv 3.10 会被闸门拒绝，需专用 py3.12 venv |
| HPC NC-E | miniforge 3.12.8 | ✅ 已并入正式 venv | `.venv-hpc-nce` 直接可用（基座已切 miniforge py3.12.8）；mpmath pin 1.3.0；旧 venv 备份 `.venv-hpc-nce-py310.bak` |
