#!/usr/bin/env bash
# ============================================================
# download_data.sh —— 在 Ubuntu 虚拟机里下载 MovieLens 小样本数据集
# 本方案【只使用 ml-latest-small】（约 1MB / 100836 条评分 / 610 用户 / 9742 电影）
# 用法： bash download_data.sh        （等价于 bash download_data.sh small）
# 为什么放在虚拟机里下载：避免跨系统传文件时被 Windows 换行符/编码弄坏。
# ============================================================
set -euo pipefail

BASE="$HOME/bigdata-final"
DATA="$BASE/data"
ZIP="ml-latest-small.zip"
DIR="ml-latest-small"
URL="https://files.grouplens.org/datasets/movielens/ml-latest-small.zip"

mkdir -p "$DATA" "$BASE/src" "$BASE/sql" "$BASE/app" \
         "$BASE/results" "$BASE/results/figures"
cd "$DATA"

echo "========== 下载 $DIR =========="
if [ -s "$ZIP" ]; then
  echo "[跳过] 已存在 $ZIP，直接用；要重下请先 rm $ZIP"
else
  wget -c --show-progress -O "$ZIP" "$URL"     # -c 支持断点续传
fi

echo "========== 解压 =========="
unzip -o -q "$ZIP"

echo "========== 校验 =========="
echo "--- ratings.csv 前 3 行 ---"
head -3 "$DIR/ratings.csv"
echo "--- movies.csv 前 3 行 ---"
head -3 "$DIR/movies.csv"
echo "--- 行数 / 体积 ---"
wc -l "$DIR/ratings.csv" "$DIR/movies.csv"
du -h "$DIR/ratings.csv" "$DIR/movies.csv"
echo "========== 完成：$DATA/$DIR =========="
