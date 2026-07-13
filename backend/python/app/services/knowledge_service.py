from sqlalchemy.orm import Session
from app.models import Knowledge, Spot
import re

class KnowledgeService:
    def __init__(self):
        self.db = None

    def sync_from_database(self, db: Session):
        self.db = db
        return 0

    def search(self, query: str, top_k=3):
        if not self.db:
            return []

        # 1. 预处理查询
        query = re.sub(r'[^\w\s\u4e00-\u9fff]', '', query)
        query = query.lower().strip()
        if not query:
            return []

        query_words = set(query.split())
        query_fragments = set()
        for i in range(len(query) - 1):
            query_fragments.add(query[i:i+2])

        # ======================
        # 全部结果
        # ======================
        scored_results = []

        # ----------------------
        # 1. 读取 Knowledge 表
        # ----------------------
        knowledges = self.db.query(Knowledge).all()
        for item in knowledges:
            title = item.title or ""
            content = item.content or ""
            category = item.category or ""

            # 全字段合并成一段文本
            full_text = f"""
知识点：{title}
内容：{content}
分类：{category}
            """.strip()

            # 计算匹配分数，标题匹配权重更高
            score = self.calculate_score(
                full_text, query_words, query_fragments
            )
            
            title_lower = title.lower()
            for word in query_words:
                if word in title_lower:
                    score += 8
            
            if score > 0:
                scored_results.append({
                    "content": full_text,
                    "score": score
                })

        # ----------------------
        # 2. 读取 Spot 景点表
        # ----------------------
        spots = self.db.query(Spot).all()
        for spot in spots:
            spot_name = spot.spot_name or ''
            # 全字段合并成一段完整讲解文本
            full_text = f"""
景点名称：{spot_name}
景区：{spot.scenic_area_name or ''}
介绍：{spot.description or ''}
文化内涵：{spot.culture_connotation or ''}
亮点：{spot.highlights or ''}
开放信息：{spot.open_info or ''}
位置：{spot.location or ''}
            """.strip()

            # 计算匹配分数
            score = self.calculate_score(
                full_text, query_words, query_fragments
            )
            
            spot_name_lower = spot_name.lower()
            for word in query_words:
                if word in spot_name_lower:
                    score += 10
            
            if score > 0:
                scored_results.append({
                    "content": full_text,
                    "score": score
                })

        # 排序 + 取TOP
        scored_results = sorted(
            scored_results,
            key=lambda x: x["score"],
            reverse=True
        )[:top_k]

        return scored_results

    # ======================
    # 统一打分函数（全文匹配）
    # ======================
    def calculate_score(self, text, query_words, query_fragments):
        text = text.lower()
        score = 0

        # 关键词匹配
        for word in query_words:
            if word in text:
                score += 4

        # 中文双字片段匹配
        for frag in query_fragments:
            if frag in text:
                score += 2

        return score