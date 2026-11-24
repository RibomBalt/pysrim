# PySRIM 项目说明（供 AI 代理 / 协作者阅读）

用 Python 驱动 SRIM/TRIM 做离子输运仿真（溅射、射程、离位损伤、电离/声子分布）。

**动手前先读 [`docs/usage.md`](docs/usage.md)** —— 里面是环境准备、三种调用层次
（`SRIM` 直接调用 / `routine` 批量助手 / 自写扫描循环）、结果字段单位、全部设置项
和实测踩坑清单。下面只列代理最容易被绊倒的几条。

## 运行时环境

- 计算**只能在 Windows 侧解释器**里跑：`.venv\Scripts\python.exe`（uv 建的 Windows
  venv，Python 3.13）。TRIM.exe 是 Windows 程序，Linux 解释器即使装了依赖也调不动它。
- WSL 的 bash 里跑 `python` / `pytest` 是 Linux 解释器，**没有装依赖**，只能用于阅读代码。
- 从 WSL 调 Windows 解释器时环境变量**不传递**（interop 只共享 `WSLENV`），要么用
  `cmd.exe /c`，要么在脚本里 `os.environ["SRIM_PATH"] = ...`。
- SRIM 安装目录：`SRIM_PATH` 指向含 `TRIM.exe` 的目录。**TRIM.exe 必须在其安装目录内
  执行**（依赖同目录 `Data` 等伴随文件），单独复制 exe 出去会「跑完零输出」。
- 本机有一份完整副本在 `vendor/SRIM`（90 MB，已 gitignore），测试会优先复用它。
- **同一 SRIM 目录不能并行算**：所有运行共用 `TRIM.IN` 和输出文件名。要并行就复制多份
  目录，一进程一份。
- 辅助输出（`SPUTTER/TRANSMIT/BACKSCAT/COLLISON/EXYZ`）落在 `SRIM Outputs\` 子目录，
  主表（`RANGE/VACANCY/IONIZ/PHONON/NOVAC/E2RECOIL/LATERAL/TDATA`）在安装根目录。

## 常用命令

```bash
# 依赖同步（Windows uv；WSL 里的 uv 会建 Linux 环境，别用）
cmd.exe /c "cd /d D:\opt\msys64\home\yangf\proj\pysrim && uv sync"

# 单元测试（不需要 SRIM，< 2 s）
cmd.exe /c "cd /d D:\opt\msys64\home\yangf\proj\pysrim && .venv\Scripts\python.exe -X utf8 -m pytest -q"

# 含真实 TRIM 调用的集成测试（会改写 SRIM 目录里的 TRIM.IN 和输出文件）
cmd.exe /c "cd /d D:\opt\msys64\home\yangf\proj\pysrim && .venv\Scripts\python.exe -X utf8 -m pytest -q --srim"

# lint / 格式
cmd.exe /c "cd /d D:\opt\msys64\home\yangf\proj\pysrim && .venv\Scripts\python.exe -X utf8 -m ruff check . && .venv\Scripts\python.exe -X utf8 -m ruff format --check ."
```

`-X utf8` 是为了让中文/法文日志在 Windows 控制台不乱码。

## 代码结构

```
srim/srim.py       SRIM / SR 计算驱动，resolve_srim_directory()，copy_output_files()
srim/input.py      TRIM.IN / SR.IN 生成（字段顺序是唯一契约，改动要同步测试）
srim/output.py     RANGE/VACANCY/IONIZ/PHONON/NOVAC/E2RECOIL 解析 → numpy 数组
srim/routine.py    run_calculation / auto_steps / auto_ions / auto_angle / merge_results
srim/core/         Element(DB) / Material / Layer / Target / Ion / units / utils
tests/             单元测试 + 可选集成测试（见上）
example/           example_2.py（中文注释）与 exemple.py（法文）两个等价起点
```

## 约定

- 不要在无关目录里创建或修改文件；临时产物放 `tmp/`（已 gitignore），不要污染
  `vendor/SRIM` 之外的位置。测试写 SRIM 目录是已知且可接受的副作用。
- 不要引入 `pip install`；依赖用 `uv add`（Windows uv）。禁止自动装 PyTorch 系列。
- 新增/修改解析逻辑时，同步更新 `tests/test_input.py`（输入格式）或
  `tests/test_integration.py`（真实输出），并把已知限制写进 `docs/usage.md`。
- 结果对象是 numpy 数组，不是 DataFrame；`depth` 恒为 100 个分箱。
- `random_seed` 决定可复现性；`routine.run_calculation()` 内部用随机种子，批量扫描要
  可复现就自己写循环直接调 `SRIM`。
