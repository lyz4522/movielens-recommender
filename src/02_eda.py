# -*- coding: utf-8 -*-
# 02_eda.py —— 探索性分析，导出 6 组小 CSV 供 Windows 本机画图（必做）
# 输入：clean/ 下的 Parquet
# 输出：HDFS 上 eda/<图名>/part-*.csv
# 说明：结果统一写回 HDFS（而非容器本地 file://），保持「入湖→计算→回湖」链路完整，
#       也方便用 hdfs dfs -getmerge 一次取回；local 模式下同样成立。
import os
from pyspark.sql import SparkSession, functions as F

HDFS = os.environ.get("HDFS_BASE", "hdfs://master:9000/user/root/movielens")

spark = SparkSession.builder.appName("02-eda").getOrCreate()
spark.sparkContext.setLogLevel("WARN")

r = spark.read.parquet(HDFS + "/clean/ratings")
m = spark.read.parquet(HDFS + "/clean/movies")
r.createOrReplaceTempView("r")
m.createOrReplaceTempView("m")


def dump(df, name):
    """把聚合结果合并成 1 个 CSV 写回 HDFS；聚合结果很小，coalesce(1) 没有性能问题"""
    (df.coalesce(1).write.mode("overwrite")
       .option("header", True)
       .csv(HDFS + "/eda/" + name))
    print("[导出] eda/" + name)


# 图 1：评分分布 —— 说明评分集中在 3~4 分
dump(spark.sql("""
    SELECT rating, COUNT(*) AS cnt
    FROM r GROUP BY rating ORDER BY rating
"""), "dist")

# 图 2：用户活跃度长尾 —— 少数用户贡献大量评分
dump(spark.sql("""
    SELECT n, COUNT(*) AS users FROM
      (SELECT userId, COUNT(*) AS n FROM r GROUP BY userId) t
    GROUP BY n ORDER BY n LIMIT 60
"""), "user_longtail")

# 图 3：电影流行度长尾 —— 大部分电影只有极少评分
dump(spark.sql("""
    SELECT n, COUNT(*) AS movies FROM
      (SELECT movieId, COUNT(*) AS n FROM r GROUP BY movieId) t
    GROUP BY n ORDER BY n LIMIT 60
"""), "movie_longtail")

# 图 4：评分最多的 20 部电影
dump(spark.sql("""
    SELECT m.title, COUNT(*) AS n, ROUND(AVG(r.rating), 2) AS avg_r
    FROM r JOIN m ON r.movieId = m.movieId
    GROUP BY m.title ORDER BY n DESC LIMIT 20
"""), "popular")

# 图 5：类型分布 —— 用 DataFrame API 拆 genres，避开 SQL 里反斜杠转义的坑
genres = (m.select(F.explode(F.split(F.col("genres"), r"\|")).alias("genre"))
          .filter((F.col("genre") != "") & (F.col("genre") != "(no genres listed)"))
          .groupBy("genre").count()
          .orderBy(F.desc("count")))
dump(genres, "genres")

# 图 6：按电影上映年份统计评分数 —— 从 title 末尾的 (1995) 抽年份
years = (r.join(m, "movieId")
         .withColumn("yr", F.regexp_extract(F.col("title"), r"\((\d{4})\)$", 1))
         .filter(F.col("yr") != "")
         .groupBy("yr").count()
         .orderBy("yr"))
dump(years, "by_year")

print("[完成] 6 组统计全部写入 " + HDFS + "/eda/")
spark.stop()
