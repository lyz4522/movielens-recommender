#!/usr/bin/env python3
"""容器内依赖自检：不启动 Spark，只逐个 import，列出还缺什么。

运行方式（Ubuntu 虚拟机）：
    docker cp ~/bigdata-final/check_deps.py master:/tmp/check_deps.py
    docker exec master python3 /tmp/check_deps.py
install_numpy.sh 会自动执行本脚本。
"""
import glob
import importlib
import os
import sys

SPARK_HOME = os.environ.get("SPARK_HOME", "/usr/local/spark")
paths = [os.path.join(SPARK_HOME, "python"),
         os.path.join(SPARK_HOME, "python", "lib", "pyspark.zip")]
paths += glob.glob(os.path.join(SPARK_HOME, "python", "lib", "py4j-*.zip"))
for p in paths:
    if os.path.exists(p) and p not in sys.path:
        sys.path.insert(0, p)

# (显示名, 模块名, 是否必需)
CHECKS = [
    ("numpy", "numpy", True),
    ("distutils.version.LooseVersion", "distutils.version", True),
    ("setuptools", "setuptools", True),
    ("pyspark", "pyspark", True),
    ("pyspark.sql", "pyspark.sql", True),
    ("pyspark.ml.recommendation (ALS)", "pyspark.ml.recommendation", True),
    ("pyspark.ml.evaluation", "pyspark.ml.evaluation", True),
    ("pyspark.ml.tuning (网格调参用)", "pyspark.ml.tuning", True),
    ("pandas（本项目不必需）", "pandas", False),
    ("pyarrow（本项目不必需）", "pyarrow", False),
]

print("Python      :", sys.version.split()[0])
print("SPARK_HOME  :", SPARK_HOME)
print("-" * 62)
missing = 0
for label, mod, required in CHECKS:
    try:
        m = importlib.import_module(mod)
        ver = getattr(m, "__version__", "")
        print("  OK    %-38s %s" % (label, ver))
    except Exception as e:
        tag = "MISS" if required else "SKIP"
        print("  %-6s %-38s %s: %s" % (tag, label, type(e).__name__, e))
        if required:
            missing += 1
print("-" * 62)
if missing:
    print("[结论] 还有 %d 个必需依赖缺失，请把本输出贴给助手" % missing)
    sys.exit(1)
print("[结论] 必需依赖全部可用，可以执行 bash submit.sh 03_train_als.py")
