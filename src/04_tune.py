# -*- coding: utf-8 -*-
# 04_tune.py —— 网格调参（本方案必做模块）
# 输入：clean/train、clean/test
# 输出：eda/tune（32 组参数的 RMSE 表格 CSV）、model/als_best（最优模型）
#
# 【为什么 regParam 网格要按对数尺度拉到 10】
# 旧版只在 0.01~0.3 内搜索，实测「regParam 越大 RMSE 越小」——这不是模型坏了，
# 而是最优点落在搜索范围之外：20% 子样本只有一万多条训练数据、rank 又给到 30，
# 模型容易过拟合，强正则一直有利；但正则无限增大时隐向量被压向 0、预测趋近常数，
# RMSE 必然回升。所以 RMSE-regParam 是一条 U 型曲线，谷底通常在 0.5~3 之间。
# 本版把上界扩到 10（跨 3 个数量级），才能把「下降段 + 谷底 + 回升段」都画出来。
#
# 网格：rank 4 档 × regParam 8 档 = 32 组；maxIter 固定 10（收敛够用，再调收益低）。
# 搜索在 20% 子样本上做，最优组合再在完整训练集上重训一次。这个设计请如实写进 PPT。
# 网格可用环境变量自定义（逗号分隔），例如时间紧时缩回 9 组：
#   GRID_RANKS=10,20,30 GRID_REGS=0.01,0.1,0.2 bash submit.sh 04_tune.py
import os
from pyspark.sql import SparkSession, functions as F
from pyspark.ml.recommendation import ALS
from pyspark.ml.evaluation import RegressionEvaluator
from pyspark.ml.tuning import ParamGridBuilder, TrainValidationSplit

HDFS = os.environ.get("HDFS_BASE", "hdfs://master:9000/user/root/movielens")

spark = SparkSession.builder.appName("04-tune").getOrCreate()
spark.sparkContext.setLogLevel("WARN")

train = spark.read.parquet(HDFS + "/clean/train")

small = train.sample(False, 0.2, seed=42).cache()
small_tr, small_va = small.randomSplit([0.8, 0.2], seed=42)
print("[调参] 子样本条数：", small.count())

als = ALS(userCol="userId", itemCol="movieId", ratingCol="rating",
          maxIter=10, coldStartStrategy="drop", seed=42)

RANKS = [int(x) for x in os.environ.get("GRID_RANKS", "5,10,20,30").split(",")]
REGS = [float(x) for x in os.environ.get(
    "GRID_REGS", "0.01,0.03,0.1,0.3,0.6,1.0,3.0,10.0").split(",")]
print("[调参] 网格 rank=%s  regParam=%s  共 %d 组" % (RANKS, REGS, len(RANKS) * len(REGS)))

grid = (ParamGridBuilder()
        .addGrid(als.rank, RANKS)
        .addGrid(als.regParam, REGS)
        .build())
print("[调参] 参数组合数：", len(grid))

ev = RegressionEvaluator(metricName="rmse", labelCol="rating",
                         predictionCol="prediction")

tvs = TrainValidationSplit(estimator=als,
                           estimatorParamMaps=grid,
                           evaluator=ev,
                           trainRatio=0.8,
                           seed=42)
tvs_model = tvs.fit(small_tr)

# 从参数映射里直接取最优组合，不依赖模型对象上的 getter（不同版本 API 不一致）
params_list = tvs_model.getEstimatorParamMaps()
metrics = list(tvs_model.validationMetrics)
rows = []
for p, m in zip(params_list, metrics):
    rank, reg = p[als.rank], p[als.regParam]
    rows.append((int(rank), float(reg), float(m)))
    print("rank=%2d  regParam=%-6s  RMSE=%.4f" % (rank, reg, m))

best_idx = min(range(len(metrics)), key=lambda i: metrics[i])
best_rank, best_reg, best_rmse = rows[best_idx]
print("[最优] rank=%d  regParam=%s  子样本 RMSE=%.4f" % (best_rank, best_reg, best_rmse))

# 【检查 1】最优点是否落在网格边界上。落在边界说明谷底还在范围外，必须外推重搜。
if best_reg <= min(REGS) or best_reg >= max(REGS):
    print("[警告] 最优 regParam=%g 落在网格边界，谷底可能仍在范围外！" % best_reg)
    print("       请把 GRID_REGS 往两侧外扩后重跑，例如 GRID_REGS=0.001,0.01,0.1,1,10,100")
else:
    print("[调参] 最优 regParam=%g 位于网格内部，已覆盖到谷底" % best_reg)
if best_rank <= min(RANKS) or best_rank >= max(RANKS):
    print("[提示] 最优 rank=%d 落在网格边界，可酌情外扩 GRID_RANKS" % best_rank)

# 把所有组合落盘，供 make_figures.py 画折线图（x 轴用对数尺度）
(spark.createDataFrame(rows, ["rank", "regParam", "rmse"])
 .coalesce(1).write.mode("overwrite").option("header", True)
 .csv(HDFS + "/eda/tune"))

# 用最优参数在完整训练集上重训一次，并在测试集上给出最终指标
final_als = ALS(userCol="userId", itemCol="movieId", ratingCol="rating",
                rank=best_rank, maxIter=10, regParam=best_reg,
                coldStartStrategy="drop", seed=42)
final = final_als.fit(train)
test = spark.read.parquet(HDFS + "/clean/test")
pred_final = final.transform(test).cache()
final_rmse = ev.evaluate(pred_final)
final_mae = RegressionEvaluator(metricName="mae", labelCol="rating",
                                predictionCol="prediction").evaluate(pred_final)
print("[最优模型] RMSE=%.4f  MAE=%.4f" % (final_rmse, final_mae))

# 【检查 2】防止「假最优」：正则太强会把预测压成常数，RMSE 看着还行但推荐失去个性化。
mu = train.agg(F.avg("rating")).first()[0]
dummy_rmse = ev.evaluate(test.withColumn("prediction", F.lit(mu)))
st = pred_final.select(F.avg("prediction").alias("mean"),
                       F.stddev("prediction").alias("std"),
                       F.min("prediction").alias("lo"),
                       F.max("prediction").alias("hi")).first()
print("[健康检查] 预测均值=%.4f  标准差=%.4f  范围=[%.2f, %.2f]" % (
    st["mean"], st["std"] or 0.0, st["lo"], st["hi"]))
print("[健康检查] 全局均值基线 RMSE=%.4f  最优模型 RMSE=%.4f  相对提升=%.1f%%" % (
    dummy_rmse, final_rmse, (dummy_rmse - final_rmse) / dummy_rmse * 100))
if st["std"] is None or st["std"] < 0.2:
    print("[警告] 预测几乎不变化，模型可能退化为常数预测，个性化推荐会失效！")
    print("       建议把超大 regParam 档位去掉后重跑（例如 GRID_REGS 上界设为 3）")
if final_rmse >= dummy_rmse:
    print("[警告] 最优模型不优于全局均值基线，请检查网格或数据！")

final.write().overwrite().save(HDFS + "/model/als_best")
print("[完成] 最优模型已保存到 model/als_best")
spark.stop()
