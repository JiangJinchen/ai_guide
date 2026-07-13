from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.models import Knowledge, KnowledgeChunk, Spot
from app.rag_config import (
    RAG_MODE_CHUNK,
    RAG_MODE_HYBRID,
    RAG_MODE_LEGACY,
    RAG_MODE_SEMANTIC,
    get_hybrid_rrf_k,
    get_postprocess_enabled,
    get_rag_mode,
    get_rerank_candidate_count,
    get_rerank_enabled,
)
from app.services.embedding_service import search_semantic_chunks
from app.services.retrieval_cache import (
    build_cache_key,
    get_cached_results,
    set_cached_results,
)
from app.services.retrieval_postprocessor import postprocess_results
from app.services.rerank_service import rerank_results
import logging
import re


logger = logging.getLogger(__name__)

class KnowledgeService:
    def __init__(self, embedding_provider=None, reranker=None):
        self.db = None
        self.embedding_provider = embedding_provider
        self.reranker = reranker

    def sync_from_database(self, db: Session):
        self.db = db
        return 0

    def search(self, query: str, top_k=3):
        mode = get_rag_mode()
        cache_key = None
        if mode in {RAG_MODE_CHUNK, RAG_MODE_SEMANTIC, RAG_MODE_HYBRID}:
            cache_key = build_cache_key(mode, query, top_k)
            if self.embedding_provider is None and self.reranker is None:
                found, cached = get_cached_results(cache_key)
                if found:
                    return cached
        retrieval_k = (
            max(top_k, get_rerank_candidate_count())
            if get_rerank_enabled()
            else top_k
        )
        if mode == RAG_MODE_CHUNK:
            try:
                results = self.search_chunks(query, top_k=retrieval_k)
                return self._complete_rag_search(query, results, top_k, cache_key)
            except Exception:
                logger.exception("Chunk retrieval failed; falling back to legacy search")
                return self.search_legacy(query, top_k=top_k)
        if mode == RAG_MODE_SEMANTIC:
            try:
                results = self.search_semantic(query, top_k=retrieval_k)
                return self._complete_rag_search(query, results, top_k, cache_key)
            except Exception:
                logger.exception("Semantic retrieval failed; falling back to legacy search")
                return self.search_legacy(query, top_k=top_k)
        if mode == RAG_MODE_HYBRID:
            try:
                results = self.search_hybrid(query, top_k=retrieval_k)
                return self._complete_rag_search(query, results, top_k, cache_key)
            except Exception:
                logger.exception("Hybrid retrieval failed; falling back to legacy search")
                return self.search_legacy(query, top_k=top_k)
        if mode != RAG_MODE_LEGACY:
            logger.warning(
                "RAG mode '%s' is not active yet; falling back to legacy search",
                mode,
            )
        return self.search_legacy(query, top_k=top_k)

    def _complete_rag_search(
        self,
        query: str,
        results: list[dict],
        top_k: int,
        cache_key: tuple | None,
    ) -> list[dict]:
        final_results = self._finalize_results(query, results, top_k=top_k)
        if (
            cache_key is not None
            and self.embedding_provider is None
            and self.reranker is None
        ):
            set_cached_results(cache_key, final_results)
        return final_results

    def _finalize_results(
        self,
        query: str,
        results: list[dict],
        top_k: int,
    ) -> list[dict]:
        if get_rerank_enabled():
            try:
                results = rerank_results(
                    query,
                    results,
                    top_k=top_k,
                    reranker=self.reranker,
                )
            except Exception as exc:
                logger.warning("Reranking unavailable; using recall order: %s", exc)
                results = results[:top_k]
        else:
            results = results[:top_k]
        if not get_postprocess_enabled():
            return results
        try:
            return postprocess_results(self.db, results, top_k=top_k)
        except Exception:
            logger.exception("RAG post-processing failed; using raw retrieval results")
            return results[:top_k]

    def search_chunks(self, query: str, top_k=3):
        if not self.db or top_k <= 0:
            return []

        query = re.sub(r"[^\w\s\u4e00-\u9fff]", "", query or "")
        query = query.lower().strip()
        if not query:
            return []

        query_tokens = query.split()
        query_words = set(query_tokens)
        query_fragment_list = [
            query[index:index + 2]
            for index in range(len(query) - 1)
        ]
        query_fragments = set(query_fragment_list)
        match_terms = list(dict.fromkeys(query_tokens + query_fragment_list))[:64]

        chunk_query = self.db.query(KnowledgeChunk)
        if match_terms:
            chunk_query = chunk_query.filter(
                or_(*[
                    KnowledgeChunk.content.ilike(f"%{term}%")
                    for term in match_terms
                ])
            )
        chunks = chunk_query.all()

        scored_results = []
        for item in chunks:
            score = self.calculate_score(
                item.content or "",
                query_words,
                query_fragments,
            )
            title_lower = (item.title or "").lower()
            for word in query_words:
                if word in title_lower:
                    score += 10 if item.source_type == "spot" else 8

            if score > 0:
                scored_results.append({
                    "content": item.content,
                    "score": score,
                    "keyword_score": score,
                    "source_type": item.source_type,
                    "source_id": item.source_id,
                    "chunk_index": item.chunk_index,
                    "title": item.title,
                    "retrieval_mode": "chunk",
                })

        return sorted(
            scored_results,
            key=lambda item: item["score"],
            reverse=True,
        )[:top_k]

    def search_semantic(self, query: str, top_k=3):
        if not self.db:
            return []
        return search_semantic_chunks(
            self.db,
            query,
            top_k=top_k,
            provider=self.embedding_provider,
        )

    def search_hybrid(self, query: str, top_k=3):
        if not self.db or top_k <= 0:
            return []

        recall_k = max(20, top_k * 4)
        keyword_results = self.search_chunks(query, top_k=recall_k)
        try:
            semantic_results = self.search_semantic(query, top_k=recall_k)
        except Exception as exc:
            logger.warning(
                "Semantic retrieval unavailable in hybrid mode; using chunks: %s",
                exc,
            )
            return keyword_results[:top_k]

        if not semantic_results:
            return keyword_results[:top_k]
        return self._fuse_hybrid_results(
            keyword_results,
            semantic_results,
            top_k=top_k,
        )

    def _fuse_hybrid_results(
        self,
        keyword_results: list[dict],
        semantic_results: list[dict],
        top_k: int,
    ) -> list[dict]:
        fused: dict[tuple, dict] = {}
        rrf_k = get_hybrid_rrf_k()

        for result_type, results in (
            ("keyword", keyword_results),
            ("semantic", semantic_results),
        ):
            for rank, item in enumerate(results, start=1):
                key = (
                    item.get("source_type"),
                    item.get("source_id"),
                    item.get("chunk_index"),
                )
                if key not in fused:
                    fused[key] = {
                        **item,
                        "keyword_score": None,
                        "semantic_score": None,
                        "retrieval_mode": "hybrid",
                        "_rrf_score": 0.0,
                    }
                fused[key]["_rrf_score"] += 1.0 / (rrf_k + rank)
                fused[key][f"{result_type}_score"] = item.get("score")

        results = []
        for item in fused.values():
            item["score"] = round(item.pop("_rrf_score"), 6)
            results.append(item)
        return sorted(results, key=lambda item: item["score"], reverse=True)[:top_k]

    def search_legacy(self, query: str, top_k=3):
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
