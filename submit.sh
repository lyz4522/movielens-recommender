#!/usr/bin/env bash
# ============================================================
# submit.sh —— 把 src/ 里的脚本提交到 Spark 执行（通用封装）
# 在 Ubuntu 虚拟机里执行，不是 Windows，也不是容器里。
#
# 【为什么默认用 local[2]，而不是课程集群】
# 实验四手册第 4 节：3 个 Spark Worker，每个只有 1 核 + 512 MiB。
# Spark 3.5 硬性要求 spark.executor.memory >= 450 MiB
#   （报错 INVALID_EXECUTOR_MEMORY: must be at least 471859200）
# 而 450 MiB + memoryOverhead 必然超过 512 MiB，Master 永远分不出 executor。
# 也就是说：按课程默认配置，Standalone 模式跑不了 PySpark（调大 Worker 额度可恢复）。
# 因此默认改成「master 容器内 local[2] 单机多线程」：
#   HDFS 照读、Spark SQL / MLlib 照用，项目依然完整。本项目不采用集群模式。
#
# 用法（本方案只使用 ml-latest-small，HDFS_BASE 固定，不要改）：
#   bash submit.sh 01_preprocess.py
#   bash submit.sh 03_train_als.py
#   DRIVER_MEM=2g bash submit.sh 04_tune.py        # 内存吃紧时加大 driver
#   GRID_RANKS=10,20,30 GRID_REGS=0.01,0.1,0.2 bash submit.sh 04_tune.py   # 快速 9 组
# ============================================================
set -euo pipefail

SCRIPT="${1:?用法: bash submit.sh <脚本文件名.py>，例如 bash submit.sh 01_preprocess.py}"
HDFS_BASE="${HDFS_BASE:-hdfs://master:9000/user/root/movielens}"
SPARK_MASTER="${SPARK_MASTER:-local[2]}"
DRIVER_MEM="${DRIVER_MEM:-1g}"
PARTITIONS="${PARTITIONS:-4}"
# 下面三个只在 SPARK_MASTER 是 spark:// 时生效
EXEC_MEM="${EXEC_MEM:-1g}"
EXEC_OVERHEAD="${EXEC_OVERHEAD:-384m}"
CORES_MAX="${CORES_MAX:-2}"

echo "[提交] 脚本=$SCRIPT"
echo "[提交] HDFS=$HDFS_BASE"
echo "[提交] master=$SPARK_MASTER  driver=$DRIVER_MEM  partitions=$PARTITIONS"
if [[ "$SPARK_MASTER" == spark://* ]]; then
  echo "[提交] 集群模式：executor=$EXEC_MEM + overhead=$EXEC_OVERHEAD  cores.max=$CORES_MAX"
else
  echo "[提示] local 模式：不申请 executor，不受课程 512MiB Worker 限制"
fi

docker exec \
  -e RUN_SCRIPT="$SCRIPT" \
  -e HDFS_BASE="$HDFS_BASE" \
  -e SPARK_MASTER="$SPARK_MASTER" \
  -e MODEL_NAME="${MODEL_NAME:-als_best}" \
  -e TARGET_MOVIE="${TARGET_MOVIE:-1}" \
  -e REC_USER_LIMIT="${REC_USER_LIMIT:-0}" \
  -e GRID_RANKS="${GRID_RANKS:-5,10,20,30}" \
  -e GRID_REGS="${GRID_REGS:-0.01,0.03,0.1,0.3,0.6,1.0,3.0,10.0}" \
  -e DRIVER_MEM="$DRIVER_MEM" \
  -e PARTITIONS="$PARTITIONS" \
  -e EXEC_MEM="$EXEC_MEM" \
  -e EXEC_OVERHEAD="$EXEC_OVERHEAD" \
  -e CORES_MAX="$CORES_MAX" \
  master bash -lc '
    set -e
    export SPARK_HOME=/usr/local/spark
    export PYTHONPATH="$SPARK_HOME/python:$(ls $SPARK_HOME/python/lib/py4j-*.zip | head -1)"
    export PYSPARK_PYTHON=python3
    cd /opt/final
    ARGS=(--master "$SPARK_MASTER" --driver-memory "$DRIVER_MEM" \
          --conf "spark.sql.shuffle.partitions=$PARTITIONS")
    case "$SPARK_MASTER" in
      spark://*)
        ARGS+=(--deploy-mode client \
               --executor-memory "$EXEC_MEM" --executor-cores 1 \
               --conf "spark.executor.memoryOverhead=$EXEC_OVERHEAD" \
               --conf "spark.cores.max=$CORES_MAX")
        ;;
    esac
    exec $SPARK_HOME/bin/spark-submit "${ARGS[@]}" "/opt/final/$RUN_SCRIPT"
  '
