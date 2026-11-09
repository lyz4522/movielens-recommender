# 环境约束与工程取舍记录

本文记录课程集群的真实配置和本项目在实操中遇到的限制。它既是复现说明，也是 PPT「实验设置 / 不足」页的事实依据。**所有数字均来自课程实验一~四手册或实际运行日志**。

## 1. 三层运行环境

| 层 | 配置 | 说明 |
|---|---|---|
| 宿主 | Windows + VMware Workstation，NAT，虚拟机 2 核 / 4–6 GB / 50 GB | 课程实验一搭建，本项目不重搭 |
| 虚拟机 | Ubuntu Server 24.04.5 LTS，主机名 `ubuntu-bigdata`，用户 `bigdata` | 所有 `docker` / `bash submit.sh` 命令都在这一层敲 |
| 容器 | Docker 29.8.1，`master` / `worker1` / `worker2` | Hadoop / Spark / Hive 都跑在容器里，Windows 侧不装 Docker |

版本：Hadoop 3.3.6（`hdfs://master:9000`，`dfs.replication=2`，2 个 DataNode）、Spark 3.5.5、Hive 4.0.1 + MySQL 8.0.43 metastore、Python 3.12。

课程目录（固定，不用 `find` 猜）：

| 实验 | 目录 | 关键脚本 |
|---|---|---|
| 实验二 Hadoop | `~/lab02-student` | `start-hadoop.sh` / `stop-hadoop.sh` / `compose.yaml` |
| 实验三 Hive/HBase | `~/lab03` | `start-hive.sh` / `stop-hive.sh` / `start-hbase.sh` / `stop-hbase.sh` |
| 实验四 Spark | `~/lab04` | **`start-spark.sh` / `stop-spark.sh` / `compose.yaml`** |
| 本大作业 | `~/bigdata-final` | `submit.sh` / `src/` / `results/` |

网络 `lab02-student_hadoopnet`，数据卷 `lab02-student_hadoop-{master,worker1,worker2}-data`。**停止容器绝不能加 `-v`**，那会删掉 HDFS 上的全部数据。收工用 `cd ~/lab04 && bash stop-spark.sh`，它只停容器、保留数据卷。

## 2. 为什么计算层用 `local[2]`（512 MiB 红线）

实验四手册第 4 节：Spark Master UI 显示 **Workers = 3**（master、worker1、worker2 各跑一个 Worker），**每个 1 核 / 512 MiB**。

Spark Standalone 分配 executor 的条件是：

```
spark.executor.memory + spark.executor.memoryOverhead ≤ 512 MiB
```

而 Spark 3.5 有硬性下限（实测报错原文）：

```
[INVALID_EXECUTOR_MEMORY] Executor memory 268435456 must be at least 471859200.
```

即 `spark.executor.memory ≥ 450 MiB`（471859200 字节）。450 MiB 再加上堆外内存**必然超过 512 MiB**，于是：

- 申请 `2g`（旧版默认值）→ 三个 Worker 都放不下 → 日志每 15 秒刷 `WARN TaskSchedulerImpl: Initial job has not accepted any resources`，任务无限排队；
- 压到 `256m` → 直接 `INVALID_EXECUTOR_MEMORY`，SparkContext 启动失败。

**结论：在课程默认配置下，Standalone 集群模式无法为 PySpark 分配 executor。** 把课程 `~/lab04/compose.yaml` 里的 `SPARK_WORKER_MEMORY` 调到 2g 以上可以恢复分布式，但虚拟机只有 4–6 GB，同时还要跑 NameNode / ResourceManager / Hive，容易 OOM，性价比很低。

本项目的 `submit.sh` 默认：

```bash
SPARK_MASTER=local[2]        # master 容器内单机 2 线程，不申请 executor
DRIVER_MEM=1g
spark.sql.shuffle.partitions=4
```

`local[2]` 下 HDFS 照读、Spark SQL / MLlib 的 API 与执行计划不变，只是不跨节点并行。需要更大内存时用 `DRIVER_MEM=2g PARTITIONS=8 bash submit.sh 04_tune.py`。

> **报告口径**：「架构与数据入湖基于 Hadoop 三节点 HDFS（双副本），计算层因课程 Worker 仅 512 MiB、低于 Spark 3.5 的 450 MiB executor 下限，采用同一 master 容器的 Spark local 模式。」**不写「在三节点集群上分布式训练」。**

## 3. 容器 Python 依赖：无 pip、无外网

课程镜像以 Scala/Java 为主，用 `PYTHONPATH` 指向 `$SPARK_HOME/python` + py4j zip 即可跑 PySpark，但 MLlib 还缺两样：

| 依赖 | 缺失原因 | 报错 |
|---|---|---|
| `numpy` | 镜像的精简 Python 没带 | `ModuleNotFoundError: No module named 'numpy'` |
| `distutils` | Python 3.12 按 PEP 632 移除；Spark 3.5.5 的 `pyspark/ml/image.py` 仍 `from distutils.version import LooseVersion` | `ModuleNotFoundError: No module named 'distutils'` |

容器里 `python3 -m pip` 报 `No module named pip`，`apt-get` 连清华源报 `No route to host`，**在线安装这条路完全走不通**。解决办法是 [wheels/README.md](../wheels/README.md) 描述的离线方案：`install_numpy.sh` 把 numpy 与 setuptools 的 wheel 拷进容器，用标准库 `zipfile` 解压到 `site-packages`，setuptools 提供 distutils 兼容层，最后跑 `check_deps.py` 逐个 import 自检。

`pyspark.ml` 顶层的第三方依赖只有 numpy 和 distutils；`pandas` / `pyarrow` 是延迟导入的可选项，本项目用不到。

## 4. 每次重建容器都要重做的两件事

容器文件系统（非数据卷）里的东西，`bash start-spark.sh` 重建容器后会丢：

```bash
docker exec master mkdir -p /opt/final
docker cp ~/bigdata-final/src/. master:/opt/final/     # 7 个 PySpark 脚本
bash install_numpy.sh                                   # numpy + distutils 兼容层
```

否则会分别报 `cd: /opt/final: No such file or directory` 和 `No module named 'numpy'`。

## 5. 其它实操坑

| 现象 | 原因 / 处理 |
|---|---|
| `: invalid option name: pipefail` | `.sh` 被 Windows 存成 CRLF。虚拟机里 `sed -i 's/\r$//' *.sh`；本仓库 `.gitattributes` 已强制 `*.sh eol=lf` |
| 所有 Web UI 打不开 | 课程 compose 已把端口映射到虚拟机，Windows 浏览器要开 `http://<虚拟机IP>:8080`（Spark）/ `:9870`（HDFS）/ `:8088`（YARN），**不是 `localhost`**，也无需 SSH 端口转发 |
| UI 仍打不开 | 用 `docker ps --format 'table {{.Names}}\t{{.Ports}}'` 看映射；也可用 `docker exec master python3 -c "import json,urllib.request; ... 'http://localhost:8080/json/'"` 直接读 Master 的 JSON 接口当证据。流水线不依赖任何网页 |
| Hive 与 Spark 抢内存 | 虚拟机 4–6 GB，两者不要同时全开，分阶段执行 |
| HDFS `-ls` 副本数列是 2 | 课程配置 `dfs.replication=2`，2 个 DataNode，不是默认的 3 |
| 调参改了但相似结果没变 | `06_similarity.py` 读 `model/als_best`，必须按 `04 → 06 → 07` 顺序重跑 |
