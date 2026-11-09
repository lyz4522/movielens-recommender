-- ============================================================
-- hive_ddl.sql —— Hive 外部表与统计查询（本方案必做模块）
-- 执行位置：Ubuntu 虚拟机 → 通过 beeline 在 hive 容器内执行
-- 注意：外部表只指向 HDFS 目录，DROP TABLE 不会删除原始数据。
-- ============================================================

CREATE DATABASE IF NOT EXISTS movielens;
USE movielens;

DROP TABLE IF EXISTS ratings;

CREATE EXTERNAL TABLE ratings (
  userid  INT,
  movieid INT,
  rating  FLOAT,
  ts      BIGINT
)
ROW FORMAT DELIMITED FIELDS TERMINATED BY ','
STORED AS TEXTFILE
LOCATION '/user/root/movielens/ratings/'
TBLPROPERTIES ('skip.header.line.count'='1');

-- 查询 1：数据规模概览（PPT「数据入湖」页用）
SELECT COUNT(*) AS n,
       COUNT(DISTINCT userid)  AS users,
       COUNT(DISTINCT movieid) AS movies,
       MIN(rating) AS min_r,
       MAX(rating) AS max_r
FROM ratings;

-- 查询 2：评分分布（导出成 CSV 后由 make_figures.py 画图）
SELECT rating, COUNT(*) AS cnt
FROM ratings
GROUP BY rating
ORDER BY rating;

-- 查询 3：评分最多的 10 位用户（体现长尾）
SELECT userid, COUNT(*) AS n
FROM ratings
GROUP BY userid
ORDER BY n DESC
LIMIT 10;
