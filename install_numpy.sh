#!/usr/bin/env bash
# 离线补齐 master 容器里 PySpark MLlib 所需的 Python 依赖
#   numpy      —— ALS 的 Python 端需要（课程镜像没带）
#   setuptools —— Python 3.12 移除了 distutils，Spark 3.5.5 的 ml/image.py 仍 import distutils.version
# 全部用 Python 标准库 zipfile 解压 wheel，不需要 pip / apt / 外网
# 用法：cd ~/bigdata-final && bash install_numpy.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WHEEL_DIR="$SCRIPT_DIR/wheels"

echo "[1/6] 读取容器内 Python 版本，选对应的 numpy wheel"
PYV="$(docker exec master python3 -c 'import sys; print("cp%d%d" % sys.version_info[:2])')"
docker exec master python3 -V
echo "      Python ABI: $PYV"
NUMPY_WHL="$(ls "$WHEEL_DIR"/numpy-1.26.4-${PYV}-${PYV}-*.whl 2>/dev/null | head -1 || true)"
SETUPTOOLS_WHL="$(ls "$WHEEL_DIR"/setuptools-*.whl 2>/dev/null | head -1 || true)"
if [ -z "$NUMPY_WHL" ] || [ -z "$SETUPTOOLS_WHL" ]; then
  echo "[错误] wheels/ 下缺少 wheel，现有文件："
  ls -1 "$WHEEL_DIR" || true
  echo "       需要 numpy-1.26.4-${PYV}-${PYV}-*.whl 和 setuptools-*.whl，请重新上传并解包 bundle.tgz"
  exit 1
fi
echo "      numpy    : $(basename "$NUMPY_WHL")"
echo "      setuptools: $(basename "$SETUPTOOLS_WHL")"

echo "[2/6] 把两个 wheel 拷进 master 容器"
docker cp "$NUMPY_WHL" master:/tmp/numpy.whl
docker cp "$SETUPTOOLS_WHL" master:/tmp/setuptools.whl

echo "[3/6] 查询容器内的 site-packages 路径"
DEST="$(docker exec master python3 -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')"
echo "      目标目录: $DEST"

echo "[4/6] 解压（不需要 pip、不需要联网）"
docker exec master python3 -m zipfile -e /tmp/numpy.whl "$DEST"
docker exec master python3 -m zipfile -e /tmp/setuptools.whl "$DEST"

echo "[5/6] 确认 distutils 可用（setuptools 的 .pth 兼容层）"
if ! docker exec master python3 -c 'from distutils.version import LooseVersion' >/dev/null 2>&1; then
  echo "      .pth 兼容层未生效，改用真实目录：删除 .pth 并把 setuptools/_distutils 复制为顶层 distutils"
  docker exec master bash -lc "rm -f '$DEST/distutils-precedence.pth'; cp -r '$DEST/setuptools/_distutils' '$DEST/distutils'"
fi
docker exec master python3 -c 'from distutils.version import LooseVersion; print("      distutils OK :", LooseVersion("1.26.4") >= LooseVersion("1.9"))'

echo "[6/6] 依赖自检（不启动 Spark，逐个 import）"
docker cp "$SCRIPT_DIR/check_deps.py" master:/tmp/check_deps.py
docker exec master python3 /tmp/check_deps.py

echo "[完成] 现在可以执行：bash submit.sh 03_train_als.py"
echo "[注意] 每次 bash start-spark.sh 重建容器后，重新运行本脚本一次即可"
