# -*- coding: utf-8 -*-
# 07_export.py —— 把 Parquet 结果转成文本 CSV，方便取回 Windows（必做）
# 输入：out/top10、out/similar_all、out/similar、eda/tune
# 输出：export/recs_csv、export/similar_all_csv、export/similar_csv、export/tune_csv
# 说明：getmerge 只能合并文本 CSV，不能直接合并 Parquet 目录，所以先转一次。
#       某个模块还没跑时，缺失的结果会被自动跳过，不会让整个脚本失败。
#       注意：popular.csv 来自 02_eda.py 的 eda/popular（热门电影 Top20 统计），
#       由取回命令直接从 eda/ 目录 getmerge，不在这里导出。
import os
from pyspark.sql import SparkSession

HDFS = os.environ.get("HDFS_BASE", "hdfs://master:9000/user/root/movielens")

spark = SparkSession.builder.appName("07-export").getOrCreate()
spark.sparkContext.setLogLevel("WARN")


def safe_export(src, dst):
    path = HDFS + "/" + src
    try:
        df = spark.read.parquet(path)
        df.limit(1).count()          # 触发一次读取，路径不存在会在这里抛异常
    except Exception as e:
        print("[跳过] %s 不存在或不可读（对应模块尚未运行）" % src)
        return
    (df.coalesce(1).write.mode("overwrite")
       .option("header", True)
       .csv(HDFS + "/export/" + dst + "_csv"))
    print("[导出] %s -> export/%s_csv" % (src, dst))


def safe_export_csv(src, dst):
    """源本身已经是文本 CSV（例如 04_tune.py 写的 eda/tune），转存到 export/ 统一取回"""
    path = HDFS + "/" + src
    try:
        df = spark.read.option("header", True).csv(path)
        df.limit(1).count()
    except Exception:
        print("[跳过] %s 不存在（多半是 04_tune.py 尚未运行）" % src)
        return
    (df.coalesce(1).write.mode("overwrite")
       .option("header", True)
       .csv(HDFS + "/export/" + dst + "_csv"))
    print("[导出] %s -> export/%s_csv" % (src, dst))


safe_export("out/top10", "recs")
safe_export("out/similar_all", "similar_all")
safe_export("out/similar", "similar")
safe_export_csv("eda/tune", "tune")

print("[完成] 用 getmerge 把 export/*_csv 与 eda/popular 取回本机即可")
spark.stop()
