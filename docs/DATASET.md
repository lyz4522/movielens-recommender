# 数据集说明与引用

## 来源

本项目使用 **MovieLens ml-latest-small**，由 GroupLens Research（University of Minnesota）发布。

- 项目主页：<https://grouplens.org/datasets/movielens/>
- 下载直链：<https://files.grouplens.org/datasets/movielens/ml-latest-small.zip>
- 许可 / 使用条款：随数据集压缩包内的 `README.txt`，另见 <https://grouplens.org/datasets/movielens/latest/>

**数据集不随本仓库分发**（GroupLens 条款不允许再分发），请用 `bash download_data.sh` 自行下载，它会在 `data/` 下解压出 `ml-latest-small/`。

## 规模与字段

| 项 | 值 |
|---|---|
| 压缩包 | 约 1 MB |
| 评分 | **100,836** 条 |
| 用户 | **610** 人 |
| 电影 | **9,742** 部 |
| 评分范围 | 0.5 – 5.0，步长 0.5 |
| 时间跨度 | 1996 – 2018（本项目建模主要使用 userId / movieId / rating） |

`ratings.csv`（带表头）：

```
userId,movieId,rating,timestamp
1,1,4.0,964982703
1,3,4.0,964981247
```

`movies.csv`（带表头，**title 里含逗号，读取时必须开启 quote/escape**）：

```
movieId,title,genres
1,Toy Story (1995),Adventure|Animation|Children|Comedy|Fantasy
2,Jumanji (1995),Adventure|Children|Fantasy
```

`01_preprocess.py` 用显式 Schema 转类型、过滤 `rating ∈ [0.5, 5.0]`、按 `(userId, movieId, ts)` 去重，并派生日期列 `dt`；本次实测没有异常行被剔除。

## 使用条款要点

1. **不得再分发**原始或衍生数据集；因此仓库 `.gitignore` 排除了 `data/` 与 `*.zip`。
2. 在报告、论文、PPT 中使用该数据集，应引用下方文献。
3. 不得尝试把评分与具体自然人对应起来，或用于识别个人身份。
4. 数据集仅供研究 / 教学使用，GroupLens 不对内容准确性作担保。

## 引用（PPT / 报告「相关资源」页可直接用）

> F. Maxwell Harper and Joseph A. Konstan. 2015. **The MovieLens Datasets: History and Context**. *ACM Transactions on Interactive Intelligent Systems (TiiS)* 5, 4, Article 19 (December 2015), 19 pages. DOI: <https://doi.org/10.1145/2827872>

BibTeX：

```bibtex
@article{10.1145/2827872,
  author  = {Harper, F. Maxwell and Konstan, Joseph A.},
  title   = {The MovieLens Datasets: History and Context},
  journal = {ACM Transactions on Interactive Intelligent Systems (TiiS)},
  volume  = {5}, number = {4}, pages = {19:1--19:19}, year = {2015},
  doi     = {10.1145/2827872}
}
```

## 下载与入湖

```bash
# [Ubuntu 虚拟机]
cd ~/bigdata-final
bash download_data.sh                 # wget 下载 + unzip + 打印校验信息

docker exec master hdfs dfs -mkdir -p /user/root/movielens/ratings /user/root/movielens/movies
docker cp data/ml-latest-small/ratings.csv master:/tmp/ratings.csv
docker cp data/ml-latest-small/movies.csv  master:/tmp/movies.csv
docker exec master hdfs dfs -put -f /tmp/ratings.csv /user/root/movielens/ratings/
docker exec master hdfs dfs -put -f /tmp/movies.csv  /user/root/movielens/movies/
docker exec master hdfs dfs -ls /user/root/movielens/ratings/
```

`bash submit.sh 00_check_env.py` 应打印 `ratings.csv 总行数： 100836`，即可继续跑 `01_preprocess.py`。

> 本项目**只使用 small 数据集**，不使用 `ml-32m` 全量。这样选择的原因是课程虚拟机只有 4–6 GB、`local[2]` 单机计算，小样本能稳定跑完整条流水线；PPT「不足」页如实写明。
