# -*- coding: utf-8 -*-
# streamlit_app.py —— 交互式推荐演示页（本方案必做模块）
# 运行位置：Windows 本机 PowerShell
#   python -m pip install streamlit pandas
#   python -m streamlit run app/streamlit_app.py
# 浏览器打开 http://localhost:8501 ，用 Win + Shift + S 截图放进 PPT。
# 它只读 CSV，不连集群，所以不会消耗虚拟机内存。
#
# 三个页签分别对应本方案的三个产物：
#   ① 个性化推荐 recs.csv   —— ALS 为全部 610 个用户生成的 Top10
#   ② 相似电影   similar_all.csv —— 每一部电影的 Top10 相似结果（余弦相似度）
#   ③ 热门电影   popular.csv —— 02_eda.py 的评分次数 Top20 统计
import os
import streamlit as st
import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(BASE, "results")

st.set_page_config(page_title="电影推荐系统演示", layout="wide")
st.title("基于 Spark MLlib ALS 的电影推荐系统")
st.caption("离线训练：Hadoop 3.3.6 + Spark 3.5.5 | 数据：MovieLens ml-latest-small | 演示：Streamlit")


def load(name):
    path = os.path.join(RES, name)
    if not os.path.exists(path):
        return None
    try:
        return pd.read_csv(path)
    except Exception:
        return None


recs = load("recs.csv")
similar_all = load("similar_all.csv")   # 全量：每一部电影的 Top10 相似结果
similar = load("similar.csv")           # 单部案例（PPT 用），可选
pop = load("popular.csv")

if recs is None and similar_all is None and pop is None:
    st.error("results/ 下没有任何 CSV，请先跑 07_export.py 并按手册取回结果。")
    st.stop()

tab1, tab2, tab3 = st.tabs(["个性化推荐", "相似电影", "热门电影 Top20"])

with tab1:
    if recs is None:
        st.warning("缺少 recs.csv，请运行 03_train_als.py + 07_export.py 并取回结果")
    else:
        ids = sorted(recs["userId"].dropna().unique().tolist())
        st.caption("ALS 已为全部 %d 个用户生成 Top10 推荐" % len(ids))
        uid = st.selectbox("选择用户 ID", ids)
        hit = recs[recs["userId"] == uid]
        cols = [c for c in ["title", "genres", "pred_rating"] if c in hit.columns]
        st.dataframe(hit[cols].rename(columns={
            "title": "电影", "genres": "类型", "pred_rating": "预测评分"
        }), use_container_width=True)

with tab2:
    if similar_all is None:
        st.warning("缺少 similar_all.csv，请运行 06_similarity.py + 07_export.py 并取回结果")
        if similar is not None:
            st.caption("下面是单部电影案例（旧版产物）")
            cols = [c for c in ["sim_title", "title", "sim"] if c in similar.columns]
            st.dataframe(similar[cols], use_container_width=True)
    else:
        idx = similar_all.drop_duplicates("movieId")[["movieId", "title"]]
        st.caption("已为 %d 部电影各生成 Top10 相似电影；可按片名搜索或输入 ID" % len(idx))
        title_map = dict(zip(idx["movieId"], idx["title"]))
        kw = st.text_input("输入片名关键词（留空则用下方 ID）", "")
        if kw:
            matched = idx[idx["title"].str.contains(kw, case=False, na=False, regex=False)].head(50)
            if matched.empty:
                st.info("没有匹配的片名，请换关键词")
                mid = None
            else:
                mid = st.selectbox("选择电影", matched["movieId"].tolist(),
                                   format_func=lambda i: "%s · %s" % (i, title_map.get(i, "")))
        else:
            mid = st.number_input("输入电影 ID", min_value=1,
                                  value=int(idx["movieId"].min()), step=1)
        if mid is not None:
            hit = similar_all[similar_all["movieId"] == mid].sort_values("rk")
            if hit.empty:
                st.warning("该电影没有隐向量（未被任何用户评分），换一个 ID 试试")
            else:
                st.caption("源电影：%s" % title_map.get(mid, str(mid)))
                cols = [c for c in ["rk", "sim_title", "sim"] if c in hit.columns]
                st.dataframe(hit[cols].rename(columns={
                    "rk": "排名", "sim_title": "相似电影", "sim": "余弦相似度"
                }), use_container_width=True)

with tab3:
    if pop is None:
        st.warning("缺少 popular.csv，请从 HDFS 的 eda/popular 取回（见手册取回步骤）")
    else:
        st.caption("评分次数最多的 20 部电影（探索性分析结果，非推荐算法输出）")
        cols = [c for c in ["title", "n", "avg_r"] if c in pop.columns]
        st.dataframe(pop[cols].rename(columns={
            "title": "电影", "n": "评分次数", "avg_r": "平均分"
        }), use_container_width=True)

st.sidebar.metric("模型", "ALS")
st.sidebar.metric("计算引擎", "Spark 3.5.5")
st.sidebar.metric("存储", "HDFS 3.3.6")
st.sidebar.metric("数据集", "ml-latest-small")
