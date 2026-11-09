# -*- coding: utf-8 -*-
# make_figures.py —— 在 Windows 本机把 CSV 画成 PNG（必做，PPT 的图从这里来）
# 运行位置：Windows PowerShell / Git Bash，不是在虚拟机里
#   python plot/make_figures.py
# 依赖：pip install pandas matplotlib
# 读：大作业-完整版/results/*.csv
# 写：大作业-完整版/results/figures/*.png
#
# 设计原则：任何一份 CSV 缺失都只跳过对应图，不中断整个脚本。
# 本方案共 7 张图：6 张 EDA 图 + 1 张网格调参折线图。
import os
import matplotlib
matplotlib.use("Agg")          # 无界面环境也能保存图片
import matplotlib.pyplot as plt
import pandas as pd

# Windows 中文字体：优先微软雅黑，其次黑体/宋体；负号单独处理避免显示成方块
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "SimSun", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(BASE, "results")
FIG = os.path.join(RES, "figures")
os.makedirs(FIG, exist_ok=True)


def read(name):
    path = os.path.join(RES, name)
    if not os.path.exists(path):
        print("[跳过] 找不到", name, "（对应模块可能没跑）")
        return None
    try:
        df = pd.read_csv(path, on_bad_lines="skip")
    except Exception as e:
        print("[跳过]", name, "读取失败：", e)
        return None
    if df.empty:
        print("[跳过]", name, "是空表")
        return None
    return df


def save(fig, name):
    fig.tight_layout()
    path = os.path.join(FIG, name)
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print("[图片]", path)


def col(df, *candidates):
    """兼容 Hive 导出与 Spark 导出的列名差异（大小写/别名）"""
    lower = {c.lower(): c for c in df.columns}
    for c in candidates:
        if c.lower() in lower:
            return lower[c.lower()]
    return None


# ---------- 图 1：评分分布 ----------
df = read("dist.csv")
if df is not None:
    x, y = col(df, "rating"), col(df, "cnt", "count")
    if x and y:
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.bar(df[x].astype(str), df[y], color="#3b73c4")
        ax.set_title("评分值分布")
        ax.set_xlabel("评分")
        ax.set_ylabel("评分数")
        save(fig, "01_rating_dist.png")

# ---------- 图 2 / 图 3：长尾（双对数） ----------
for fname, out, title, label in [
    ("user_longtail.csv", "02_user_longtail.png", "用户活跃度长尾", "用户数"),
    ("movie_longtail.csv", "03_movie_longtail.png", "电影流行度长尾", "电影数"),
]:
    df = read(fname)
    if df is not None:
        x = col(df, "n")
        y = col(df, "users", "movies", "cnt", "count")
        if x and y:
            fig, ax = plt.subplots(figsize=(7, 4))
            ax.plot(df[x], df[y], marker="o", ms=3, color="#c4513b")
            ax.set_xscale("log")
            ax.set_yscale("log")
            ax.set_title(title + "（双对数）")
            ax.set_xlabel("评分次数 n")
            ax.set_ylabel(label)
            ax.grid(alpha=.3, which="both")
            save(fig, out)

# ---------- 图 4：热门电影 Top20 ----------
df = read("popular.csv")
if df is not None:
    t = col(df, "title")
    n = col(df, "n", "cnt", "count")
    if t and n:
        d = df.nlargest(20, n).iloc[::-1]
        fig, ax = plt.subplots(figsize=(9, 7))
        ax.barh(d[t].astype(str), d[n], color="#2e8b6d")
        ax.set_title("评分次数最多的 20 部电影")
        ax.set_xlabel("评分次数")
        save(fig, "04_popular_movies.png")

# ---------- 图 5：类型分布 ----------
df = read("genres.csv")
if df is not None:
    g = col(df, "genre")
    n = col(df, "count", "cnt", "n")
    if g and n:
        d = df.head(15).iloc[::-1]
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.barh(d[g].astype(str), d[n], color="#7a5bc4")
        ax.set_title("电影类型分布（Top15）")
        ax.set_xlabel("电影数")
        save(fig, "05_genres.png")

# ---------- 图 6：年份趋势 ----------
df = read("by_year.csv")
if df is not None:
    x = col(df, "yr", "year")
    y = col(df, "count", "cnt", "n")
    if x and y:
        fig, ax = plt.subplots(figsize=(9, 4))
        ax.plot(df[x].astype(str), df[y], color="#c48a1b")
        ax.set_title("按上映年份的评分数趋势")
        ax.set_xlabel("年份")
        ax.set_ylabel("评分数")
        ax.tick_params(axis="x", rotation=60, labelsize=7)
        save(fig, "06_by_year.png")

# ---------- 图 7：网格调参折线（regParam 对数轴，标出谷底） ----------
# 注意：regParam 是跨数量级的数值，必须转成 float 并按数值排序，
# 若按字符串排序会出现 "10" 排在 "3" 前面的错图。
df = read("tune.csv")
if df is not None:
    r, g, m = col(df, "rank"), col(df, "regparam", "reg"), col(df, "rmse")
    if r and g and m:
        d = df.copy()
        d[g] = pd.to_numeric(d[g], errors="coerce")
        d[m] = pd.to_numeric(d[m], errors="coerce")
        d = d.dropna(subset=[g, m])
        fig, ax = plt.subplots(figsize=(8, 4.5))
        for rank, part in d.groupby(r):
            part = part.sort_values(g)
            ax.plot(part[g], part[m], marker="o", ms=4, label="rank=%s" % rank)
        if not d.empty:
            best = d.loc[d[m].idxmin()]
            ax.scatter([best[g]], [best[m]], s=110, facecolors="none",
                       edgecolors="#c0392b", linewidths=1.8, zorder=5,
                       label="最优 regParam=%g" % best[g])
        ax.set_xscale("log")
        ax.set_title("网格调参：RMSE 随正则强度变化（对数轴）")
        ax.set_xlabel("regParam（对数尺度）")
        ax.set_ylabel("RMSE")
        ax.legend(fontsize=8)
        ax.grid(alpha=.3, which="both")
        save(fig, "07_tuning.png")

print("[完成] 图片目录：", FIG)
