# wheels/ — 离线依赖包（二进制文件不入库）

本目录存放 `install_numpy.sh` 需要的 4 个 `.whl` 文件。**这些文件不在 Git 仓库里**（合计约 55 MB，且属于第三方发行物），克隆仓库后需要按下面的方式补一次。

## 为什么需要它们

课程 `master` 容器是 Ubuntu 24.04 / Python 3.12 + Spark 3.5.5：

- 容器**没有 pip**，也**连不上外网**（`apt` 访问清华源报 `No route to host`）；
- `pyspark.ml` 顶层导入 `numpy`，否则 `from pyspark.ml.recommendation import ALS` 报 `No module named 'numpy'`；
- Python 3.12 按 PEP 632 移除了标准库 `distutils`，而 Spark 3.5.5 的 `ml/image.py` 仍写有 `from distutils.version import LooseVersion`，否则报 `No module named 'distutils'`。

`install_numpy.sh` 的做法是：把 wheel 拷进容器，用 Python **标准库 `zipfile`** 解压到 `site-packages`（wheel 本质就是 zip），`setuptools` 里的 `setuptools/_distutils` 提供 distutils 兼容层。全程不需要 pip / apt / 网络。

## 文件清单

| 文件 | 约大小 | 适用容器 Python |
|---|---|---|
| `numpy-1.26.4-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl` | 18 MB | 3.10 |
| `numpy-1.26.4-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl` | 18 MB | 3.11 |
| `numpy-1.26.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl` | 18 MB | 3.12（课程容器实测值） |
| `setuptools-75.8.0-py3-none-any.whl` | 1.2 MB | 任意 Python 3 |

`install_numpy.sh` 会先读容器的 `sys.version_info`，拼出 `cp312` 之类的 ABI，再按 `numpy-1.26.4-<ABI>-<ABI>-*.whl` 自动选文件。所以三个 numpy 版本放全最省事；只放实际需要的那一个也可以。

## 方式 A：脚本自动下载（推荐，在有外网的机器上执行）

在仓库根目录（Windows PowerShell 或 Ubuntu 虚拟机均可，只要有 Python 3）：

```powershell
python scripts\fetch_wheels.py
```

国内访问 pypi.org 慢时改用镜像：

```powershell
$env:PYPI_MIRROR="https://pypi.tuna.tsinghua.edu.cn"
python scripts\fetch_wheels.py
```

Ubuntu 虚拟机则写成 `PYPI_MIRROR=https://pypi.tuna.tsinghua.edu.cn python3 scripts/fetch_wheels.py`。

脚本只用标准库 `urllib`/`json`，会打印每个文件的下载进度与大小校验，已存在且大小正确的文件会自动跳过。

## 方式 B：用 pip download（有 pip 的机器）

```bash
mkdir -p wheels
# 课程容器实测为 Python 3.12；只需准备这一个 numpy 即可
python -m pip download "numpy==1.26.4" \
  --only-binary=:all: --python-version 3.12 \
  --abi cp312 --platform manylinux_2_17_x86_64 -d wheels
python -m pip download "setuptools==75.8.0" --only-binary=:all: -d wheels
```

若容器是 3.10 / 3.11，把上面两处 `3.12` / `cp312` 换成 `3.10` / `cp310` 或 `3.11` / `cp311` 再跑一次即可。

若 pip 生成的 numpy 文件名带 `manylinux2014_x86_64` 之外的后缀也没关系，只要包含 `cp312-cp312` 和 `manylinux_2_17_x86_64` 即可被脚本匹配。

## 方式 C：手动下载

打开 <https://pypi.org/project/numpy/1.26.4/#files> 与 <https://pypi.org/project/setuptools/75.8.0/#files>，下载上表四个文件，直接放进本目录，**不要改名**。

## 校验与使用

```bash
ls -lh wheels/*.whl          # 应看到 4 个文件
python scripts/make_bundle.sh   # 可选：重新打进 bundle.tgz
bash install_numpy.sh          # 在虚拟机执行，安装进 master 容器
```

`install_numpy.sh` 最后会自动运行 `check_deps.py`，看到 `[结论] 必需依赖全部可用` 即成功。

> **每次 `bash start-spark.sh` 重建容器后都要重跑 `bash install_numpy.sh`**：wheel 解压在容器文件系统里，不在 Docker 数据卷中，容器重建即丢失。
