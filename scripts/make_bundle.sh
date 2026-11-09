#!/usr/bin/env bash
# 重新生成 bundle.tgz —— 一次性上传到 Ubuntu 虚拟机的脚本包。
# 用法： bash scripts/make_bundle.sh
# 注意：bundle.tgz 是打包产物，不纳入 git（见 .gitignore），随时可重建。
set -euo pipefail

cd "$(dirname "$0")/.."

if ! ls wheels/*.whl >/dev/null 2>&1; then
  echo "[WARN] wheels/ 下没有 .whl，生成的包不含离线依赖"
  echo "       请在有网机器先执行：python scripts/fetch_wheels.py"
fi

tar -czf bundle.tgz \
  src sql app plot wheels \
  download_data.sh submit.sh install_numpy.sh check_deps.py

echo "[OK] bundle.tgz 已生成："
ls -lh bundle.tgz
echo "[OK] 包内文件："
tar -tzf bundle.tgz | grep -v '/$' | sed 's/^/  /'
echo
echo "下一步上传：scp bundle.tgz bigdata@<虚拟机IP>:~/bigdata-final/"
