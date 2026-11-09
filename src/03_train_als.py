# -*- coding: utf-8 -*-
# 03_train_als.py —— ALS 基线模型 + 评估 + Top-N 推荐（必做，本项目核心）
# 输入：clean/train、clean/test、clean/movies
# 输出：model/als_baseline（模型）、out/top10（推荐结果）、日志里的 RMSE / MAE
import os
from pyspark.sql import SparkSession, functions as F
from pyspark.ml.recommendation import ALS
from pyspark.ml.evaluation import RegressionEvaluator

HDFS = os.environ.get("HDFS_BASE", "hdfs://master:9000/user/root/movielens")

spark = SparkSession.builder.appName("03-als-baseline").getOrCreate()
spark.sparkContext.setLogLevel("WARN")

train = spark.read.parquet(HDFS + "/clean/train")
test = spark.read.parquet(HDFS + "/clean/test")

# coldStartStrategy="drop" 必须写：测试集里出现训练集没见过的用户/电影时，
# ALS 会给出 NaN，不丢弃的话 RegressionEvaluator 直接返回 null。
als = ALS(userCol="userId", itemCol="movieId", ratingCol="rating",
          rank=20, maxIter=10, regParam=0.1,
          coldStartStrategy="drop", implicitPrefs=False, seed=42)

print("[训练] ALS rank=20 maxIter=10 regParam=0.1 ...")
model = als.fit(train)

pred = model.transform(test)
pred = pred.filter(F.col("prediction").isNotNull())

rmse = RegressionEvaluator(metricName="rmse", labelCol="rating",
                           predictionCol="prediction").evaluate(pred)
mae = RegressionEvaluator(metricName="mae", labelCol="rating",
                          predictionCol="prediction").evaluate(pred)
print("[基线] RMSE=%.4f  MAE=%.4f  参与评估条数=%d" % (rmse, mae, pred.count()))

# 【对照基线】把预测值恒等于训练集平均分，证明 ALS 确实学到了东西。
# 只需要几行代码，却能在 PPT「结果分析」页多一行有说服力的对照。
mu = train.agg(F.avg("rating")).first()[0]
dummy = test.withColumn("prediction", F.lit(mu))
dummy_rmse = RegressionEvaluator(metricName="rmse", labelCol="rating",
                                 predictionCol="prediction").evaluate(dummy)
print("[对照] 全局均值 mu=%.4f  RMSE=%.4f（ALS 应明显低于它）" % (mu, dummy_rmse))

# 保存模型：04_tune.py / 06_similarity.py / 演示页都从这里读
model.write().overwrite().save(HDFS + "/model/als_baseline")

# 生成 Top10 推荐：本方案只用 ml-latest-small（约 610 个用户），
# 给训练集里出现过的【每一个用户】都生成 10 条推荐，不做抽样。
# 可选 REC_USER_LIMIT=N 临时只取前 N 个用户（调试用，正式跑不要设）。
movies = spark.read.parquet(HDFS + "/clean/movies")
all_users = train.select("userId").distinct()
REC_LIMIT = int(os.environ.get("REC_USER_LIMIT", "0"))
users = (all_users.orderBy("userId").limit(REC_LIMIT) if REC_LIMIT > 0
         else all_users)
n_users = users.count()
print("[推荐] 本数据集用户总数：%d，全部生成 Top10，共 %d 行" % (n_users, n_users * 10))
recs = (model.recommendForUserSubset(users, 10)
        .withColumn("r", F.explode("recommendations"))
        .select("userId",
                F.col("r.movieId").alias("movieId"),
                F.round(F.col("r.rating"), 3).alias("pred_rating"))
        .join(movies, "movieId")
        .select("userId", "movieId", "title", "genres", "pred_rating"))
recs.write.mode("overwrite").parquet(HDFS + "/out/top10")
print("[推荐] 样例（前 20 行）：")
recs.orderBy("userId", F.desc("pred_rating")).show(20, truncate=False)

print("[完成] 模型与推荐结果已保存")
spark.stop()
