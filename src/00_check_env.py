# -*- coding: utf-8 -*-
# 00_check_env.py —— 环境自检（必做的第一步，几秒钟跑完）
# 作用：确认 PySpark 版本、Spark Master、HDFS 数据都正常，
#       避免后面跑半小时才发现环境没通。
import os
import pyspark
from pyspark.sql import SparkSession

HDFS = os.environ.get("HDFS_BASE", "hdfs://master:9000/user/root/movielens")

spark = SparkSession.builder.appName("00-check-env").getOrCreate()
spark.sparkContext.setLogLevel("WARN")

print("[检查] PySpark 版本 :", pyspark.__version__)
print("[检查] Spark 运行模式:", spark.sparkContext.master, "(应为 local[2])")
print("[检查] PySpark 解释器:", os.environ.get("PYSPARK_PYTHON", "(未设置)"))
print("[检查] HDFS 数据目录:", HDFS)

try:
    df = spark.read.option("header", True).csv(HDFS + "/ratings/ratings.csv")
    print("[检查] ratings.csv 前 3 行：")
    df.show(3, truncate=False)
    print("[检查] ratings.csv 总行数：", df.count())
    print("[结论] 环境正常，可以继续跑 01_preprocess.py")
except Exception as e:
    print("[失败] 读不到 HDFS 上的 ratings.csv：", repr(e))
    print("[排查] 1) docker exec master hdfs dfs -ls /user/root/movielens/ratings/")
    print("       2) 确认 HDFS_BASE 是否与上传目录一致")
    print("       3) 确认 master 容器能读 HDFS：docker exec master hdfs dfs -ls /")
    print("       4) 若运行模式不是 local[2]，说明 submit.sh 是旧版，重新上传 bundle.tgz")

spark.stop()
