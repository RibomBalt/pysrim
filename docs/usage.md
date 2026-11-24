# PySRIM 使用指南

本文档面向「用这套环境做 TRIM（SRIM）仿真」的实际操作：从环境准备、三种调用层次、
结果字段含义，到已经踩过的坑。文中所有数字与行为都在本项目当前的代码（Windows +
SRIM-2013）上实测过。

---

## 1. 环境准备

### 1.1 解释器

项目 `.venv` 是 **Windows 虚拟环境**（`uv` 创建，Python 3.13）。TRIM.exe 只能由
Windows 进程调用，所以计算必须用这个解释器：

```bash
cd /mnt/d/opt/msys64/home/yangf/proj/pysrim
uv sync                                              # 安装运行时 + dev 依赖
.venv\Scripts\python.exe -c "import srim; print('ok')"
```

WSL 里直接 `pytest` / `python` 走的是 Linux 解释器，**没有装依赖也无法调用 TRIM**，
只能用于纯静态阅读。

### 1.2 指向 SRIM 安装目录

```cmd
set SRIM_PATH=D:\opt\SRIM
```

或者在脚本里、导入 `srim` 之前设置：

```python
import os

os.environ["SRIM_PATH"] = r"D:\opt\SRIM"
```

校验（`SRIM_PATH` 只在真正计算时才被解析，`import srim` 不再要求它存在）：

```python
from srim.srim import resolve_srim_directory

print(resolve_srim_directory())  # 找不到会抛 ValueError，消息里带尝试过的路径
```

### 1.3 三条硬约束

| 约束 | 后果 / 原因 |
|---|---|
| **TRIM.exe 必须在其安装目录内执行** | 依赖同目录的 `Data`、`TRIM.dat` 等伴随文件。只把 `TRIM.exe` 复制到别处会**跑完零输出**，`Results()` 随后 `FileNotFoundError` |
| **WSL → Windows 解释器不传递环境变量** | interop 只共享 `WSLENV` 白名单。用 `cmd.exe /c` 启动，或在脚本里设 `os.environ` |
| **同一 SRIM 目录不能并行跑** | 所有计算共用 `TRIM.IN` 与 `RANGE.txt` 等输出文件名。并行必须复制多份 SRIM 目录（每份 90 MB），一进程一份 |

`vendor/SRIM` 是项目内的本地全量副本（已 gitignore），测试会优先复用它，也可以直接
当作计算目录——实践上把它当「实验台目录」，把结果拷到自己的数据目录里。

---

## 2. 三种调用层次

### 2.1 直接使用 `SRIM`（推荐，控制最完整）

```python
import os

os.environ["SRIM_PATH"] = r"D:\opt\SRIM"

from srim.core.layer import Layer
from srim.core.target import Target
from srim.core.ion import Ion
from srim.srim import SRIM

target = Target(
    [
        Layer(
            {"Zr": {"stoich": 0.34, "E_d": 20.0, "surface": 3.0}, "O": {"stoich": 0.66, "E_d": 60.0, "surface": 3.0}},
            density=5.68,
            width=64_000.0,
            name="Oxyde",
        ),
        Layer({"Zr": 1.0}, density=6.52, width=36_000.0, name="Metal"),
    ]
)

ion = Ion("H", energy=1.0e5)  # 能量单位 eV

sim = SRIM(
    target,
    ion,
    number_ions=1000,
    calculation=2,  # 1 = Kinchin-Pease(快) / 2 = Full Cascade(有反冲)
    ranges=1,  # 要 RANGE.txt
    collisions=2,  # 0=不输出 1=仅离子 2=离子+反冲
    random_seed=12345,  # 可复现的关键
    plot_xmin=0,
    plot_xmax=50_000,  # 可选：只看 0~5 um 窗口（会重新分箱）
    angle_ions=15,  # 0 <= θ < 90
)

results = sim.run()  # 不传目录则用 SRIM_PATH
```

要点：

* `Layer(elements, density, width, phase=0, name=None)`；元素既可写 `{"Si": 1.0}`
  也可写 `{"Zr": {"stoich": 0.34, "E_d": 20.0, "lattice": 0.0, "surface": 3.0}}`，
  `stoich` 会被自动归一化到 1.0。
* `Target([layer1, layer2, ...])` —— 必须传**列表**。
* `Layer.from_formula("SiO2", density=2.32, width=1000)` 可从化学式建层。
* 每次 `run()` 都覆盖 SRIM 目录里的 `TRIM.IN` 与输出文件；要留档就配
  `SRIM.copy_output_files(src, dest)`（按白名单复制，不含无关文件）。

### 2.2 `routine` 批量助手（做参数扫描）

```python
from srim.routine import auto_steps, auto_ions, auto_angle, merge_results

out, SRIM_DIR = r"D:\data\run", r"D:\opt\SRIM"
target = ...  # 同上

# 能量扫描
auto_ions(
    [{"identifier": "H", "energy": e} for e in (5e4, 1e5, 2e5)],
    target,
    num_ions=1000,
    calculation=2,
    save_directory=out,
    SRIM_dir=SRIM_DIR,
    subbing=False,
    steps=None,
    angle_ions=0,
)
# → out/H-50000.0/、out/H-100000.0/ …

# 分步窗口扫描（厚靶提高空间分辨率），之后合并
auto_steps(
    {"identifier": "He", "energy": 1e3},
    target,
    1000,
    1,
    out,
    SRIM_DIR,
    False,
    [(0, 20000), (20000, 40000), (40000, 60000)],
    15,
)
# → out/He-1000.0-0-20000/ …
merge_results(out)  # → out/total_range.txt、out/total_vacancy.txt

# 角度扫描
auto_angle({"identifier": "He", "energy": 1e5}, target, 1000, 1, out, SRIM_DIR, False, None, [0, 15, 30, 45])
```

结果目录命名规则：无 `plot_limits` 时 `<符号>-<能量eV>`，分步时
`<符号>-<能量eV>-<xmin>-<xmax>`。三个助手都返回所创建目录的列表。

**注意**：`run_calculation()` 内部固定 `random_seed=randint(0, 100000)`，批量结果
不可复现。需要可复现就用 2.3。

### 2.3 自己写扫描循环（正式数据推荐）

```python
import json, pathlib, time
from srim.core.layer import Layer, Target, Ion
from srim.srim import SRIM

SRIM_DIR = pathlib.Path(r"D:\opt\SRIM")
out = pathlib.Path(r"D:\data\scan")
out.mkdir(parents=True, exist_ok=True)
target = Target([Layer({"Si": 1.0}, 2.32, 100_000.0)])

rows = []
for energy in (5e4, 1e5, 2e5):
    sim = SRIM(target, Ion("H", energy=energy), number_ions=2000, calculation=2, ranges=1, collisions=2, random_seed=42)
    t0 = time.time()
    res = sim.run()

    dest = out / f"H-{energy:.0f}"
    dest.mkdir(exist_ok=True)
    SRIM.copy_output_files(str(SRIM_DIR), str(dest))

    rows.append(
        {
            "energy_eV": energy,
            "seconds": round(time.time() - t0, 1),
            "peak_depth_A": float(res.range.depth[res.range.ions.argmax()]),
            "vacancies": float(res.vacancy.vacancies.sum()),
            "phonon_eV": float(res.phonons.ions.sum()),
        }
    )

(out / "summary.json").write_text(json.dumps(rows, indent=2))
```

---

## 3. 结果对象参考

`sim.run()` / `Results(directory)` 返回 `Results`，各字段都是 **numpy 数组**
（不是 DataFrame），深度分箱**恒为 100 个**。

| 属性 | 常用字段 | 含义 / 单位 |
|---|---|---|
| `results.range` | `depth`, `ions`, `elements`, `num_ions`, `ion` | `depth` 分箱深度 [Å]；`ions` 离子最终分布 [(atoms/cm³)/(atoms/cm²)]；`elements` shape `(100, n_elements)`，**按元素种类而非按层**给出（ZrO/Zr 双层靶的 `n_elements` 是 1） |
| `results.vacancy` | `depth`, `vacancies`, `knock_ons`, `num_ions`, `ion` | 空位 [Vacancies/(Å·ion)] |
| `results.ioniz` | `depth`, `ions`, `recoils`, `num_ions`, `ion` | 电子阻止造成的电离能损 [eV/(Å·ion)] |
| `results.phonons` | `depth`, `ions`, `recoils`, `num_ions`, `ion` | 声子数 [Phonons/(Å·ion)] |
| `results.novac` | `depth`, `number`, `num_ions`, `ion` | 置换碰撞 [Number/(Å·ion)]；文件缺失时为 `None` |
| `results.etorecoils` | `depth`, `ions`, `absorbed`, `num_ions`, `ion` | 传给反冲的能量 [eV/(Å·ion)]；文件缺失时为 `None` |

读取输出目录（不重算）：

```python
from srim.output import Results

r = Results(r"D:\data\scan\H-100000")  # 目录里必须有 RANGE/VACANCY/IONIZ/PHONON.txt
r.range.ion.symbol, r.range.num_ions
```

---

## 4. 参数参考

### 4.1 `SRIM(target, ion, calculation=1, number_ions=1000, **settings)`

| 参数 | 取值 | 说明 |
|---|---|---|
| `calculation` | 1–7 | 1=Kinchin-Pease，2=Full Cascade（其余为溅射/离子/中子变体） |
| `number_ions` | > 0 | 请求的离子数 |

### 4.2 设置项（`SRIMSettings`）

| 键 | 默认 | 取值 / 说明 |
|---|---|---|
| `description` | `"srim-python run"` | 写入 TRIM.IN 标题，不允许含双引号 |
| `ranges` | 0 | 1 → 输出 `RANGE.txt` |
| `backscattered` | 0 | 1 → `SRIM Outputs\BACKSCAT.txt` |
| `transmit` | 0 | 1 → `SRIM Outputs\TRANSMIT.txt`（无透射离子时不生成） |
| `sputtered` | 0 | 1 → `SRIM Outputs\SPUTTER.txt`（无溅射事件时不生成） |
| `collisions` | 0 | 0=不输出，1=仅离子，2=离子+反冲 → `SRIM Outputs\COLLISON.txt`（**单个 S**） |
| `exyz` | 0 | 1 → 特殊 EXYZ 轨迹文件 |
| `plot_mode` | 5 | 作图类型 0–5 |
| `plot_xmin` / `plot_xmax` | 0.0 / 0.0 | 作图深度窗口 [Å]，`0 0` 表示整靶；要求 `xmin <= xmax` |
| `angle_ions` | 0.0 | 入射角 [度]，`0 <= θ < 90` |
| `bragg_correction` | 1.0 | 化合物 Bragg 修正系数 |
| `random_seed` | 0 | 随机种子（可复现性来源） |
| `reminders` | 0 | 0/1，TRIM 运行提示 |
| `autosave` | 0 | TRIM 自动保存编号 |
| `version` | 0 | 阻止本领版本（1=2011） |

### 4.3 输出文件分布（实测）

| 位置 | 文件 | 触发条件 |
|---|---|---|
| SRIM 安装根目录 | `RANGE.txt`、`VACANCY.txt`、`IONIZ.txt`、`PHONON.txt`、`NOVAC.txt`、`E2RECOIL.txt`、`LATERAL.txt`、`TDATA.txt` | 随计算模式自动生成 |
| `SRIM Outputs\` 子目录 | `SPUTTER.txt` / `TRANSMIT.txt` / `BACKSCAT.txt` / `COLLISON.txt` / `EXYZ.txt` | 仅当对应开关为 1（且该次计算确实产生相应事件） |
| `SRIM Outputs\` 子目录 | `RANGE_3D.txt`、`TRIMOUT.txt` | 基本总会生成 |

`SRIM.copy_output_files(src, dest)` 两个位置都认（自带白名单），`check_srim_output=False`
则只从根目录拷。注意碰撞日志的拼写是 `COLLISON.txt`，本项目早期白名单里漏了这一项，
现在两种拼写都接受。

---

## 5. 实操要点与已踩过的坑

| 现象 | 说明与处理 |
|---|---|
| 深度分箱**恒为 100 个** | TRIM 自适应分箱：10 µm 靶 → bin 1000 Å；2 µm 窗口 → bin 200 Å。解析层 `max_rows=100` 不构成截断 |
| `plot_xmin/plot_xmax` 是**缩放**而非截取 | 会重新分箱，不改变物理结果 |
| 1 MeV H 在 Si 里**穿靶** | 10 µm 靶几乎全透过 → `RANGE.txt` 离子列全是 `0.0000E+00`。要么让射程 < 靶厚，要么用 `transmit=1` 另存透射信息 |
| `results.range.num_ions` 可能小于请求值 | 它是 TRIM 回写的 `Total Ions calculated`，穿过靶的离子未必计入（20 → 19 实测过） |
| `calculation=1` 没有反冲 | K-P 模式只给估算空位，`NOVAC/E2RECOIL` 里会写 "There are NO RECOILS"。要损伤级联必须 `calculation=2` |
| 角度 90° 或负值报错 | `is_srim_degrees` 要求 `0 <= θ < 90`，`ValueError: type of argument does not satisfy condition` |
| 输出开关彼此独立 | `ranges/backscattered/transmit/sputtered/collisions/exyz` 互不影响（`sputtered` 曾被 `ranges` 覆盖，已在 `caf07fb` 修复）。**辅助输出不在 SRIM 根目录**，而在 `SRIM Outputs\` 子目录 |
| 碰撞文件叫 `COLLISON.txt` | 不是 `COLLISIONS.txt`（SRIM 自己拼错），复制结果时按白名单匹配，已在白名单里兼容两种拼写 |
| 中文/法文控制台乱码 | 用 `python -X utf8`；`routine` 的日志表头是法文，乱码不影响数值结果 |
| `SR`（Stopping/Range 模块） | 代码路径可用但**未在真实 SRIM 上验证**，不要依赖 |
| TRIM 跑完没有任何输出 | 九成是没在 SRIM 安装目录内执行，或 `TRIM.exe` 是从别处复制的孤零零一份 |

---

## 6. 性能参考

本机（Si 靶，100 keV H）：

| 配置 | 1000 ions |
|---|---|
| `calculation=1`（K-P） | ≈ **8.6 s** |
| `calculation=2`（Full Cascade） | ≈ **15.0 s** |

即常规 1000–5000 ions 扫描是分钟级；1e4 以上建议分批，或复制多份 SRIM 目录并行
（一进程一份）。

---

## 7. 起步点

* `example/example_2.py`（中文注释）—— ZrO/金属双层靶 + `auto_steps` + `merge_results`
  的完整脚本，改参数即可用。
* `example/exemple.py` —— 同一逻辑的法文版。
* `tests/test_integration.py` —— 真实 TRIM 调用的最小可读范例（`pytest --srim` 运行）。
* `tests/test_input.py` —— 想确认 `TRIM.IN` 各字段含义时看这里。
