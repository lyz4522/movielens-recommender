# results/ — 本次实验输出（数据字典）

这里的文件是**跑完流水线后从 HDFS 取回的结果**，不是源码。它们随仓库一起保留，方便直接查看实验结果、复现图表和驱动演示页；重跑流水线会覆盖同名文件。

`plot/make_figures.py` 读取本目录的 CSV，`app/streamlit_app.py` 读取 `recs.csv` / `similar_all.csv` / `popular.csv`。

## CSV 数据字典

| 文件 | 行数 | 列 | 来源 | 用途 |
|---|---|---|---|---|
| `dist.csv` | 10 | `rating, cnt` | `02_eda.py` → `eda/dist` | 评分值分布，图 1 |
| `user_longtail.csv` | 60 | `n, users` | `02_eda.py` → `eda/user_longtail` | 用户活跃度长尾，图 2 |
| `movie_longtail.csv` | 60 | `n, movies` | `02_eda.py` → `eda/movie_longtail` | 电影流行度长尾，图 3 |
| `popular.csv` | 20 | `title, n, avg_r` | `02_eda.py` → `eda/popular` | 评分次数最多的 20 部电影，图 4 + 演示页第 3 页签 |
| `genres.csv` | 19 | `genre, count` | `02_eda.py` → `eda/genres` | 类型分布，图 5 |
| `by_year.csv` | 106 | `yr, count` | `02_eda.py` → `eda/by_year` | 上映年份趋势，图 6 |
| `tune.csv` | 32 | `rank, regParam, rmse` | `04_tune.py` → `eda/tune` | 32 组网格调参结果，图 7 |
| `recs.csv` | **6,100** | `userId, movieId, title, genres, pred_rating` | `03_train_als.py` → `out/top10` | **610 个用户各 10 条**个性化推荐，演示页第 1 页签 |
| `similar_all.csv` | **89,540** | `movieId, title, genres, sim_movieId, sim_title, sim, rk` | `06_similarity.py` → `out/similar_all` | **8,954 部电影各 10 条**相似结果，演示页第 2 页签 |
| `similar.csv` | 10 | `movieId, title, genres, sim` | 早期单部案例导出 | PPT 案例表参考；现已被 `similar_all.csv` 覆盖，可用下面命令重新生成 |

### 从全量相似表提取任意电影案例

```powershell
# 在 Windows 本机（已装 pandas）执行；例：movieId=1（Toy Story）
python -c "import pandas as pd; d=pd.read_csv('results/similar_all.csv'); d[d.movieId==1].sort_values('rk').to_csv('results/similar_case.csv', index=False)"
```

不要用 `awk -F,` 直接切这个 CSV：片名字段里含逗号且被引号包住，按逗号切会串列。

> 说明：`similar.csv` 是早期版本的 4 列格式（没有 `sim_movieId` / `rk`），与当前 `06_similarity.py` 输出的 `out/similar` 列结构不同。**它不影响演示页**（演示页优先读 `similar_all.csv`），仅作历史案例保留。需要规范的单部案例时请按上面的命令从 `similar_all.csv` 提取，或重跑 `06` + `07` 并重新取回 `similar_csv`。

## 图片（`figures/`）

| 文件 | 内容 | 读自 |
|---|---|---|
| `01_rating_dist.png` | 评分值分布柱状图 | `dist.csv` |
| `02_user_longtail.png` | 用户活跃度长尾（双对数） | `user_longtail.csv` |
| `03_movie_longtail.png` | 电影流行度长尾（双对数） | `movie_longtail.csv` |
| `04_popular_movies.png` | 热门电影 Top20 横向条形图 | `popular.csv` |
| `05_genres.png` | 类型分布 Top15 | `genres.csv` |
| `06_by_year.png` | 年份趋势折线 | `by_year.csv` |
| `07_tuning.png` | 调参 RMSE 曲线（对数 x 轴，红圈标谷底） | `tune.csv` |

重画：`python plot/make_figures.py`（Windows 本机，需 `pip install -r requirements.txt`）。任何一份 CSV 缺失只会跳过对应图，不会中断。

## 不入库的中间产物

`*.tgz`（`eda.tgz` / `export.tgz`）、`*.log` 是取回过程中的临时压缩包与日志，已在 `.gitignore` 中排除，可安全删除。

## 结果口径

- 全部结果基于 `ml-latest-small`，`seed=42`，因此可复现。
- `tune.csv` 里的 RMSE 是**20% 子样本验证集**上的数值；最终最优模型在完整测试集上的 RMSE/MAE 由 `04_tune.py` 打印在运行日志中（本目录未保存日志）。
- 只有训练集中被评过分的电影才有 ALS 物品隐向量，因此相似表覆盖 8,954 / 9,742 部电影；其余为无评分长尾影片。
