#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""下载离线依赖 wheel 到 wheels/（在【有外网】的机器上执行）。

背景：课程 master 容器是 Python 3.12 + Spark 3.5.5，既没有 pip 也没有外网，
而 pyspark.ml（ALS）需要 numpy，且 Spark 3.5.5 的 ml/image.py 仍导入了
Python 3.12 已移除的 distutils。install_numpy.sh 用标准库 zipfile 直接解压
wheel 到 site-packages，因此需要事先把 wheel 文件准备好。

用法（仓库根目录）：
    python scripts/fetch_wheels.py
    # 国内下载慢时改用清华镜像：
    #   PYPI_MIRROR=https://pypi.tuna.tsinghua.edu.cn python scripts/fetch_wheels.py

只依赖 Python 标准库，不需要预先安装 requests / pip。
"""
import json
import os
import sys
import urllib.request

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "wheels")
PYPI_JSON = os.environ.get("PYPI_JSON", "https://pypi.org/pypi")
MIRROR = os.environ.get("PYPI_MIRROR", "").rstrip("/")

# (包名, 版本, 文件名筛选函数)
TARGETS = [
    ("numpy", "1.26.4",
     lambda n: n.endswith(".whl")
     and "manylinux_2_17_x86_64" in n
     and any(cp in n for cp in ("cp310", "cp311", "cp312"))),
    ("setuptools", "75.8.0",
     lambda n: n.endswith("py3-none-any.whl")),
]


def download(url, dest, expected):
    """分块下载并打印进度，避免 18MB 文件时终端没有任何反馈。"""
    if MIRROR:
        url = url.replace("https://files.pythonhosted.org", MIRROR)
    tmp = dest + ".part"
    got = 0
    step = 4 * 1024 * 1024
    next_report = step
    with urllib.request.urlopen(url, timeout=60) as r, open(tmp, "wb") as f:
        while True:
            chunk = r.read(256 * 1024)
            if not chunk:
                break
            f.write(chunk)
            got += len(chunk)
            if got >= next_report:
                print("      %.1f / %.1f MB" % (got / 1048576.0, expected / 1048576.0))
                next_report += step
    actual = os.path.getsize(tmp)
    if expected and actual != expected:
        os.remove(tmp)
        raise RuntimeError("size mismatch: %d != %d" % (actual, expected))
    os.replace(tmp, dest)


def main():
    os.makedirs(OUT, exist_ok=True)
    print("[info] output dir:", OUT)
    print("[info] index     :", PYPI_JSON)
    if MIRROR:
        print("[info] mirror    :", MIRROR)
    ok = True
    for pkg, ver, match in TARGETS:
        print("[1/2] query %s == %s" % (pkg, ver))
        try:
            with urllib.request.urlopen("%s/%s/%s/json" % (PYPI_JSON, pkg, ver),
                                       timeout=30) as r:
                data = json.load(r)
        except Exception as e:
            print("      ERROR: cannot reach PyPI JSON API:", repr(e))
            print("      可改用 PYPI_JSON 指向可访问的镜像，或手动下载（见 wheels/README.md）")
            ok = False
            continue

        picked = [f for f in data.get("urls", []) if match(f["filename"])]
        if not picked:
            print("      ERROR: no matching wheel found")
            ok = False
            continue
        for f in picked:
            dest = os.path.join(OUT, f["filename"])
            size = int(f.get("size", 0))
            if os.path.exists(dest) and (not size or os.path.getsize(dest) == size):
                print("      SKIP  %s (already exists)" % f["filename"])
                continue
            print("[2/2] GET   %s" % f["filename"])
            try:
                download(f["url"], dest, size)
                print("      OK    %.2f MB" % (os.path.getsize(dest) / 1048576.0))
            except Exception as e:
                print("      ERROR:", repr(e))
                ok = False

    print("-" * 60)
    if not ok:
        print("[FAIL] 部分 wheel 未下载成功，详见 wheels/README.md 的手动下载方式")
        return 1
    print("[DONE] wheels/ 已就绪，下一步在虚拟机执行：bash install_numpy.sh")
    return 0


if __name__ == "__main__":
    sys.exit(main())
