# ==============================
# 自动标签聚类生成工具
# 读取 Spot + Knowledge 表 → 分词 → TF-IDF → KMeans聚类 → 输出关键词组
# ==============================
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import jieba
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
import numpy as np
from collections import Counter
import re

# 你的数据库依赖
from app.database import get_db
from app.models import Spot, Knowledge

# ----------------------
# 1. 从数据库读取所有文本
# ----------------------
def load_all_texts(db):
    texts = []

    # 读取 Spot 表文本
    spots = db.query(Spot).all()
    for s in spots:
        content = " ".join([
            s.spot_name or "",
            s.culture_connotation or "",
            s.description or "",
            s.highlights or ""
        ])
        texts.append(content)

    # 读取 Knowledge 表文本
    knowledges = db.query(Knowledge).all()
    for k in knowledges:
        content = " ".join([
            k.title or "",
            k.category or "",
            k.content or ""
        ])
        texts.append(content)

    return texts

# ----------------------
# 2. 中文分词 + 清洗
# ----------------------
def tokenize(text):
    # 只保留中文
    text = re.sub(r"[^\u4e00-\u9fa5]", "", text)
    words = jieba.lcut(text)
    # 过滤短词
    return [w for w in words if len(w) >= 2]

# ----------------------
# 3. 关键词聚类
# ----------------------
def cluster_keywords(texts, n_clusters=5):
    # 分词后拼接成句子
    corpus = [" ".join(tokenize(t)) for t in texts]

    # TF-IDF向量化
    vec = TfidfVectorizer(max_features=300)
    X = vec.fit_transform(corpus)
    words = vec.get_feature_names_out()

    # K-Means聚类
    kmeans = KMeans(n_clusters=n_clusters, random_state=42)
    labels = kmeans.fit_predict(X.T)  # 对词语聚类

    # 按簇分组
    clusters = {i: [] for i in range(n_clusters)}
    for word, label in zip(words, labels):
        clusters[label].append(word)

    return clusters

# ----------------------
# 4. 运行输出结果
# ----------------------
if __name__ == "__main__":
    db = next(get_db())
    print("正在读取 Spot + Knowledge 表...")
    texts = load_all_texts(db)

    print("正在分词 & 聚类...")
    clusters = cluster_keywords(texts, n_clusters=8)  # 8组标签

    print("\n===== 自动聚类结果 =====\n")
    for i, words in clusters.items():
        print(f"聚类 {i}: {', '.join(words[:20])}")  # 显示前20个关键词