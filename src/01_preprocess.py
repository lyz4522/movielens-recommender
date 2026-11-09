# -*- coding: utf-8 -*-
# 01_preprocess.py —— 数据清洗、类型规整、训练测试划分（必做）
# 输入：HDFS 上的 ratings/ratings.csv、movies/movies.csv
# 输出：HDFS 上的 clean/ratings、clean/train、clean/test、clean/movies（Parquet）
import os
from pyspark.sql import SparkSession, functions as F
from pyspark.sql.types import (StructType, StructField,
                               IntegerType, FloatType, LongType, StringType)

# HDFS_BASE 由 submit.sh 通过 docker exec -e 传入，本方案固定指向 small 数据目录
HDFS = os.environ.get("HDFS_BASE", "hdfs://master:9000/user/root/movielens")

spark = SparkSession.builder.appName("01-preprocess").getOrCreate()
spark.sparkContext.setLogLevel("WARN")

# 显式定义 Schema：避免 Spark 额外全表扫描推断类型，也让脏数据能被 dropna 识别
r_schema = StructType([
    StructField("userId",  IntegerType(), True),
    StructField("movieId", IntegerType(), True),
    StructField("rating",  FloatType(),   True),
    StructField("ts",      LongType(),    True)])

m_schema = StructType([
    StructField("movieId", IntegerType(), True),
    StructField("title",   StringType(),  True),
    StructField("genres",  StringType(),  True)])

# movies.csv 的 title 里有逗号（如 "Toy Story, The (1995)"），
# 必须开启 quote / escape，否则列会串位
ratings_raw = (spark.read.option("header", True)
               .schema(r_schema)
               .csv(HDFS + "/ratings/ratings.csv"))

movies = (spark.read.option("header", True)
          .option("quote", '"')
          .option("escape", '"')
          .schema(m_schema)
          .csv(HDFS + "/movies/movies.csv"))

before = ratings_raw.count()

ratings = (ratings_raw
           .dropna()                                          # 丢弃类型转换失败的行
           .filter((F.col("rating") >= 0.5) & (F.col("rating") <= 5.0))
           .dropDuplicates(["userId", "movieId", "ts"])       # 去重
           .withColumn("dt", F.to_date(F.to_timestamp(F.from_unixtime("ts")))))

after = ratings.count()
print("[清洗] 原始 %d 条 -> 有效 %d 条，去除 %d 条" % (before, after, before - after))
print("[规模] 用户数=%d  电影数=%d  平均评分=%.4f" % (
    ratings.select("userId").distinct().count(),
    ratings.select("movieId").distinct().count(),
    ratings.agg(F.avg("rating")).first()[0]))

# 8:2 随机划分，seed 固定保证每次结果一致
train, test = ratings.randomSplit([0.8, 0.2], seed=42)

# 落盘成 Parquet：列式压缩，后面的脚本不必重复解析 CSV
ratings.write.mode("overwrite").parquet(HDFS + "/clean/ratings")
train.write.mode("overwrite").parquet(HDFS + "/clean/train")
test.write.mode("overwrite").parquet(HDFS + "/clean/test")
movies.write.mode("overwrite").parquet(HDFS + "/clean/movies")

print("[划分] train=%d  test=%d" % (train.count(), test.count()))
print("[完成] 清洗结果写入：" + HDFS + "/clean/")
spark.stop()
