# MovieLens 电影推荐系统

2026 秋《大数据处理》课程大作业。使用 Hadoop HDFS 存储数据、Spark MLlib ALS 做协同过滤推荐，完成数据清洗、统计分析、网格调参、推荐生成与可视化，并提供 Hive 统计和 Streamlit 演示页。

数据集为 MovieLens ml-latest-small，100836 条评分、610 个用户、9742 部电影。集群复用课程实验一~四搭建的 VMware 虚拟机与 Docker 三节点环境。

## 做了什么

- 数据入湖，用显式 Schema 清洗并做 8:2 划分，结果存为 Parquet
- 6 组探索性统计，输出评分分布、长尾、热门电影、类型与年份分布
- ALS 基线模型，用 RMSE 和 MAE 评估，并与全局均值对照
- 32 组网格调参，用最优参数重训模型
- 为全部 610 个用户生成 Top10 推荐
- 按物品隐向量余弦相似度，为 8954 部电影各生成 Top10 相似电影
- Hive 外部表统计
- matplotlib 出图，Streamlit 三页签交互演示

课程集群每个 Spark Worker 只有 512 MiB，低于 Spark 3.5 的 executor 内存下限，因此计算在 master 容器内以 `local[2]` 运行。HDFS 仍是三节点分布式存储。

## 环境

| 组件 | 版本 |
| --- | --- |
| Ubuntu Server | 24.04.5 LTS |
| Docker | 29.8.1 |
| Hadoop | 3.3.6 |
| Spark | 3.5.5 |
| Hive | 4.0.1 |
| Python | 3.12 |

集群用课程实验四的 `~/lab04/start-spark.sh` 启动，不需要另搭。

## 文件构成

```
src/                 7 个 PySpark 作业脚本，按编号顺序执行
sql/                 Hive 建表与统计 SQL
app/                 Streamlit 演示页
plot/                画图脚本
scripts/             离线依赖下载、打包工具
results/             本次实验的 CSV 与 7 张统计图
submit.sh            统一的 spark-submit 封装
download_data.sh     下载数据集
install_numpy.sh     离线安装容器依赖
check_deps.py        容器依赖自检
requirements.txt     Windows 本机画图与演示依赖
```

`bundle.tgz` 和 `wheels/` 下的 whl 文件体积较大，不入库，分别用 `bash scripts/make_bundle.sh` 和 `python3 scripts/fetch_wheels.py` 生成。数据集也不入库，用 `bash download_data.sh` 下载。

## 使用方式

Windows 本机安装画图与演示依赖：

```powershell
python -m pip install -r requirements.txt
```

把本项目放到 Ubuntu 虚拟机的 `~/bigdata-final`，按顺序执行：

```bash
cd ~/bigdata-final
bash download_data.sh
python3 scripts/fetch_wheels.py
bash install_numpy.sh

docker exec master mkdir -p /opt/final
docker cp src/. master:/opt/final/

docker exec master hdfs dfs -mkdir -p /user/root/movielens/ratings /user/root/movielens/movies
docker cp data/ml-latest-small/ratings.csv master:/tmp/ratings.csv
docker cp data/ml-latest-small/movies.csv master:/tmp/movies.csv
docker exec master hdfs dfs -put -f /tmp/ratings.csv /user/root/movielens/ratings/
docker exec master hdfs dfs -put -f /tmp/movies.csv /user/root/movielens/movies/

bash submit.sh 00_check_env.py
bash submit.sh 01_preprocess.py
bash submit.sh 02_eda.py
bash submit.sh 03_train_als.py
bash submit.sh 04_tune.py
bash submit.sh 06_similarity.py
bash submit.sh 07_export.py
```

Hive 与 Spark 共用容器名，分阶段执行：

```bash
cd ~/lab04 && bash stop-spark.sh
cd ~/lab03 && bash start-hadoop.sh && bash start-hive.sh
docker cp ~/bigdata-final/sql/hive_ddl.sql hive:/tmp/hive_ddl.sql
docker exec hive /usr/local/hive/bin/beeline -u 'jdbc:hive2://localhost:10000/default' -f /tmp/hive_ddl.sql
cd ~/lab03 && bash stop-hive.sh
cd ~/lab04 && bash start-spark.sh
docker cp ~/bigdata-final/src/. master:/opt/final/
```

取回结果并画图：

```bash
docker exec master bash -lc 'rm -f /tmp/*.csv'
for n in dist user_longtail movie_longtail popular genres by_year; do
  docker exec master hdfs dfs -getmerge /user/root/movielens/eda/$n /tmp/$n.csv
done
for n in recs similar similar_all tune; do
  docker exec master hdfs dfs -getmerge /user/root/movielens/export/${n}_csv /tmp/$n.csv
done
docker exec master bash -lc 'cd /tmp && tar czf export.tgz *.csv'
docker cp master:/tmp/export.tgz ~/bigdata-final/results/
```

```powershell
cd results
scp bigdata@<虚拟机IP>:~/bigdata-final/results/export.tgz .
tar -xzf export.tgz
cd ..
python plot\make_figures.py
python -m streamlit run app\streamlit_app.py
```

容器重建后需要重新执行 `docker cp src/.` 和 `bash install_numpy.sh`。

## 结果

| 文件 | 内容 |
| --- | --- |
| `results/recs.csv` | 610 个用户各 10 条推荐，6100 行 |
| `results/similar_all.csv` | 8954 部电影各 10 条相似结果，89540 行 |
| `results/tune.csv` | 32 组参数与对应 RMSE |
| `results/figures/` | 7 张统计图 |

32 组网格中最低点为 rank=5、regParam=0.3，子样本 RMSE 1.0917。

![评分分布](results/figures/01_rating_dist.png)

![网格调参](results/figures/07_tuning.png)

## 数据集

MovieLens ml-latest-small 由 GroupLens Research 提供，按其使用条款不在仓库内分发。下载地址 <https://grouplens.org/datasets/movielens/latest/>。

F. Maxwell Harper, Joseph A. Konstan. 2015. The MovieLens Datasets: History and Context. ACM TiiS 5, 4.

## License

MIT，见 [LICENSE](LICENSE)。
