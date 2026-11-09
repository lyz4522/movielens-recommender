# -*- coding: utf-8 -*-
# 06_similarity.py —— 基于 ALS 物品隐向量的相似电影（本方案必做模块）
# 输入：model/als_best（网格调参的最优模型；若无则自动回退 model/als_baseline）、clean/movies
# 输出：
#   out/similar_all —— 【全量】每一部有隐向量的电影各 10 条最相似电影（约 9.7 万行）
#   out/similar     —— 【案例】由 TARGET_MOVIE 指定电影的 10 条结果，供 PPT 案例表
#
# 做法：itemFactors 只有约 9700 行 × rank(10~30) 列，collect 到 driver 后用 numpy
#       做「单位向量 × 单位向量转置」的分块矩阵乘法，逐行取 Top10。
#       分块是为了不一次性申请 9700×9700 的相似矩阵（约 380MB），每块只占约 10MB。
#       numpy 已由 install_numpy.sh 离线装入容器，pyspark.ml 本身也依赖它。
import os
import numpy as np
from pyspark.sql import SparkSession, functions as F
from pyspark.ml.recommendation import ALSModel

HDFS = os.environ.get("HDFS_BASE", "hdfs://master:9000/user/root/movielens")
MODEL = os.environ.get("MODEL_NAME", "als_best")
TARGET = int(os.environ.get("TARGET_MOVIE", "1"))  # 单部案例：1 = Toy Story (1995)
TOPK = 10

spark = SparkSession.builder.appName("06-similar-all").getOrCreate()
spark.sparkContext.setLogLevel("WARN")

model_path = HDFS + "/model/" + MODEL
try:
    model = ALSModel.load(model_path)
except Exception:
    print("[提示] 找不到 " + model_path + "（尚未跑网格调参），改用基线模型")
    model = ALSModel.load(HDFS + "/model/als_baseline")

factors = model.itemFactors.collect()
ids = [int(r["id"]) for r in factors]
V = np.asarray([list(r["features"]) for r in factors], dtype=np.float32)
norm = np.linalg.norm(V, axis=1, keepdims=True)
V = V / np.where(norm > 0, norm, 1.0)          # 归一化后点积 = 余弦相似度
N = len(ids)
print("[相似度] 载入 %d 部电影的隐向量，rank=%d" % (N, V.shape[1]))
print("[相似度] 将为【每一部】电影计算 Top%d 相似电影，请稍候..." % TOPK)


def cosine(a, b):
    """保留给外部复用：两个隐向量的余弦相似度"""
    na = np.linalg.norm(a)
    nb = np.linalg.norm(b)
    return float(np.dot(a, b) / (na * nb + 1e-9))


# 分块计算：S = V_chunk @ V.T，形状 (chunk, N)，每块约 10MB
BLOCK = 256
rows = []
for st in range(0, N, BLOCK):
    ed = min(st + BLOCK, N)
    S = V[st:ed] @ V.T
    for i in range(ed - st):
        k = min(TOPK + 1, N)                    # 多取 1 个，方便排除自身
        cand = np.argpartition(-S[i], k - 1)[:k]
        cand = cand[np.argsort(-S[i, cand])]
        base_id = ids[st + i]
        rk = 0
        for j in cand:
            sid = ids[int(j)]
            if sid == base_id:
                continue
            rk += 1
            rows.append((base_id, sid, float(round(float(S[i, j]), 4)), rk))
            if rk >= TOPK:
                break
    if (st // BLOCK) % 4 == 0:
        print("[相似度] 进度 %d / %d" % (ed, N))

print("[相似度] 生成结果行数：%d" % len(rows))

schema = "movieId int, sim_movieId int, sim double, rk int"
sim_df = spark.createDataFrame(rows, schema)

movies = spark.read.parquet(HDFS + "/clean/movies")
base = movies.select("movieId", "title", "genres")
sim_titles = movies.select(F.col("movieId").alias("sim_movieId"),
                           F.col("title").alias("sim_title"))

full = (sim_df.join(base, "movieId")
        .join(sim_titles, "sim_movieId")
        .select("movieId", "title", "genres", "sim_movieId", "sim_title", "sim", "rk"))

# ① 全量结果：演示页可按任意电影查询
full.write.mode("overwrite").parquet(HDFS + "/out/similar_all")
print("[完成] 全量相似表 -> out/similar_all（%d 行）" % len(rows))

# ② 单部案例：PPT「相似电影案例表」用，取 TARGET_MOVIE 的 10 条
case = full.filter(F.col("movieId") == TARGET).orderBy("rk")
if case.limit(1).count() == 0:
    print("[提示] 目标电影 movieId=%d 没有隐向量，自动改用表里的第一部电影" % TARGET)
    first_id = sim_df.select("movieId").orderBy("movieId").first()[0]
    case = full.filter(F.col("movieId") == first_id).orderBy("rk")
case.write.mode("overwrite").parquet(HDFS + "/out/similar")
print("[相似度] 案例 movieId=%d 的 Top%d：" % (TARGET, TOPK))
case.select("title", "sim_title", "sim").show(TOPK, truncate=False)
print("[完成] 案例结果 -> out/similar")
spark.stop()
