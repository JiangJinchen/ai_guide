import os
import sys
import types
import unittest
from unittest.mock import Mock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.rag_config import get_rag_mode


test_database = types.ModuleType("app.database")
test_database.Base = declarative_base()
with patch.dict(sys.modules, {"app.database": test_database}):
    from app.models import Knowledge, KnowledgeChunk, KnowledgeChunkEmbedding, Spot
    from app.services.chunk_service import split_text, sync_chunks_from_database
    from app.services.embedding_service import sync_embeddings_from_database
    from app.services.evaluation_service import evaluate_search
    from app.services.faiss_index_service import get_faiss_status
    from app.services.knowledge_service import KnowledgeService
    from app.services.retrieval_cache import (
        clear_retrieval_cache,
        get_cache_status,
    )
    from app.services.retrieval_postprocessor import (
        calibrate_confidence,
        estimate_tokens,
        postprocess_results,
        truncate_to_token_budget,
    )

Base = test_database.Base


class FakeEmbeddingProvider:
    model_name = "fake-embedding-model"
    batch_size = 16

    def embed_documents(self, texts):
        return [self._vector(text) for text in texts]

    def embed_query(self, text):
        return self._vector(text)

    def _vector(self, text):
        text = text.lower()
        if "open" in text or "visit" in text or "daily" in text:
            return [1.0, 0.0, 0.0]
        if "history" in text or "ancient" in text:
            return [0.0, 1.0, 0.0]
        return [0.0, 0.0, 1.0]


class FailingEmbeddingProvider(FakeEmbeddingProvider):
    def embed_query(self, text):
        raise RuntimeError("model unavailable")


class FakeReranker:
    model_name = "fake-reranker"

    def score(self, query, documents):
        return [float(index) for index, _ in enumerate(documents)]


class RagConfigTests(unittest.TestCase):
    def test_rag_mode_defaults_to_legacy(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(get_rag_mode(), "legacy")

    def test_invalid_rag_mode_falls_back_to_legacy(self):
        with patch.dict(os.environ, {"RAG_MODE": "invalid"}, clear=True):
            self.assertEqual(get_rag_mode(), "legacy")


class KnowledgeSearchDispatcherTests(unittest.TestCase):
    def test_default_mode_delegates_to_legacy_search(self):
        service = KnowledgeService()
        service.search_legacy = Mock(return_value=[{"content": "legacy", "score": 1}])

        with patch.dict(os.environ, {}, clear=True):
            result = service.search("query", top_k=7)

        self.assertEqual(result, [{"content": "legacy", "score": 1}])
        service.search_legacy.assert_called_once_with("query", top_k=7)

    def test_hybrid_mode_uses_hybrid_retrieval(self):
        service = KnowledgeService()
        service.db = Mock()
        service.search_hybrid = Mock(return_value=[{"content": "hybrid", "score": 1}])

        with patch.dict(
            os.environ,
            {"RAG_MODE": "hybrid", "RAG_POSTPROCESS_ENABLED": "false"},
            clear=True,
        ):
            result = service.search("query")

        self.assertEqual(result, [{"content": "hybrid", "score": 1}])
        service.search_hybrid.assert_called_once_with("query", top_k=3)

    def test_chunk_mode_uses_chunk_retrieval(self):
        service = KnowledgeService()
        service.db = Mock()
        service.search_chunks = Mock(return_value=[{"content": "chunk", "score": 2}])

        with patch.dict(
            os.environ,
            {"RAG_MODE": "chunk", "RAG_POSTPROCESS_ENABLED": "false"},
            clear=True,
        ):
            result = service.search("query", top_k=5)

        self.assertEqual(result, [{"content": "chunk", "score": 2}])
        service.search_chunks.assert_called_once_with("query", top_k=5)

    def test_chunk_retrieval_error_falls_back_to_legacy_search(self):
        service = KnowledgeService()
        service.search_chunks = Mock(side_effect=RuntimeError("missing table"))
        service.search_legacy = Mock(return_value=[])

        with self.assertLogs("app.services.knowledge_service", level="ERROR"):
            with patch.dict(os.environ, {"RAG_MODE": "chunk"}, clear=True):
                result = service.search("query")

        self.assertEqual(result, [])
        service.search_legacy.assert_called_once_with("query", top_k=3)

    def test_semantic_retrieval_error_falls_back_to_legacy_search(self):
        service = KnowledgeService()
        service.search_semantic = Mock(side_effect=RuntimeError("missing model"))
        service.search_legacy = Mock(return_value=[])

        with self.assertLogs("app.services.knowledge_service", level="ERROR"):
            with patch.dict(os.environ, {"RAG_MODE": "semantic"}, clear=True):
                result = service.search("query")

        self.assertEqual(result, [])
        service.search_legacy.assert_called_once_with("query", top_k=3)

class SplitTextTests(unittest.TestCase):
    def test_prefers_sentence_boundaries_and_adds_overlap(self):
        text = "first sentence. second sentence. third sentence."
        chunks = split_text(text, chunk_size=24, overlap=5)

        self.assertGreater(len(chunks), 1)
        self.assertTrue(chunks[0].endswith("."))
        self.assertIn(chunks[0][-5:], chunks[1])

    def test_supports_chinese_sentence_boundaries(self):
        text = "\u7b2c\u4e00\u6bb5\u3002\u7b2c\u4e8c\u6bb5\u3002\u7b2c\u4e09\u6bb5\u3002"
        chunks = split_text(text, chunk_size=8, overlap=2)

        self.assertGreater(len(chunks), 1)
        self.assertTrue(chunks[0].endswith("\u3002"))

    def test_long_sentence_is_split_without_looping(self):
        chunks = split_text("x" * 1000, chunk_size=200, overlap=40)

        self.assertEqual(len(chunks), 5)
        self.assertLessEqual(max(map(len, chunks)), 241)


class ChunkSyncTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(
            engine,
            tables=[
                Knowledge.__table__,
                Spot.__table__,
                KnowledgeChunk.__table__,
                KnowledgeChunkEmbedding.__table__,
            ],
        )
        self.db = sessionmaker(bind=engine)()

    def tearDown(self):
        self.db.close()

    def test_sync_is_idempotent_and_updates_changed_sources(self):
        knowledge = Knowledge(
            title="Opening hours",
            content="The area opens daily. Holiday hours follow notices.",
            category="service",
        )
        spot = Spot(
            scenic_area_name="Test area",
            spot_name="Test spot",
            description="This is the spot description. " * 30,
        )
        self.db.add_all([knowledge, spot])
        self.db.commit()

        first = sync_chunks_from_database(self.db, chunk_size=200, overlap=40)
        second = sync_chunks_from_database(self.db, chunk_size=200, overlap=40)

        self.assertGreater(first.created, 0)
        self.assertEqual(second.created, 0)
        self.assertEqual(second.updated, 0)
        self.assertEqual(second.unchanged, first.chunks)

        knowledge.content = "The area now opens at 08:00 daily."
        self.db.commit()
        third = sync_chunks_from_database(self.db, chunk_size=200, overlap=40)

        self.assertGreater(third.updated + third.deleted, 0)

    def test_chunk_search_returns_source_metadata(self):
        knowledge = Knowledge(
            title="Opening hours",
            content="The area opens daily.",
            category="service",
        )
        self.db.add(knowledge)
        self.db.commit()
        sync_chunks_from_database(self.db, chunk_size=200, overlap=40)

        service = KnowledgeService()
        service.sync_from_database(self.db)
        with patch.dict(os.environ, {"RAG_MODE": "chunk"}, clear=True):
            results = service.search("Opening hours", top_k=1)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["source_type"], "knowledge")
        self.assertEqual(results[0]["source_id"], knowledge.id)
        self.assertEqual(results[0]["chunk_index"], 0)

    def test_chunk_search_supports_chinese_fragments(self):
        knowledge = Knowledge(
            title="\u5f00\u653e\u65f6\u95f4",
            content="\u666f\u533a\u6bcf\u65e5\u516b\u70b9\u5f00\u653e\u3002",
            category="service",
        )
        self.db.add(knowledge)
        self.db.commit()
        sync_chunks_from_database(self.db, chunk_size=200, overlap=40)

        service = KnowledgeService()
        service.sync_from_database(self.db)
        with patch.dict(os.environ, {"RAG_MODE": "chunk"}, clear=True):
            results = service.search("\u51e0\u70b9\u5f00\u653e", top_k=1)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["source_id"], knowledge.id)

    def test_embedding_sync_is_idempotent_and_refreshes_changed_chunks(self):
        knowledge = Knowledge(
            title="Opening hours",
            content="The area opens daily.",
            category="service",
        )
        self.db.add(knowledge)
        self.db.commit()
        sync_chunks_from_database(self.db, chunk_size=200, overlap=40)
        provider = FakeEmbeddingProvider()

        first = sync_embeddings_from_database(self.db, provider=provider)
        second = sync_embeddings_from_database(self.db, provider=provider)

        self.assertEqual(first.created, 1)
        self.assertEqual(second.created, 0)
        self.assertEqual(second.unchanged, 1)

        knowledge.content = "The area opens daily at 08:00."
        self.db.commit()
        sync_chunks_from_database(self.db, chunk_size=200, overlap=40)
        third = sync_embeddings_from_database(self.db, provider=provider)

        self.assertEqual(third.updated, 1)

    def test_semantic_search_ranks_by_vector_similarity(self):
        self.db.add_all([
            Knowledge(
                title="Opening hours",
                content="The area opens daily.",
                category="service",
            ),
            Knowledge(
                title="Ancient history",
                content="The site has a long history.",
                category="culture",
            ),
        ])
        self.db.commit()
        sync_chunks_from_database(self.db, chunk_size=200, overlap=40)
        provider = FakeEmbeddingProvider()
        sync_embeddings_from_database(self.db, provider=provider)

        service = KnowledgeService(embedding_provider=provider)
        service.sync_from_database(self.db)
        with patch.dict(os.environ, {"RAG_MODE": "semantic"}, clear=True):
            results = service.search("When can I visit?", top_k=1)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Opening hours")
        self.assertEqual(results[0]["retrieval_mode"], "semantic")

    def test_hybrid_search_fuses_keyword_and_semantic_results(self):
        self.db.add(Knowledge(
            title="Opening hours",
            content="The area opens daily.",
            category="service",
        ))
        self.db.commit()
        sync_chunks_from_database(self.db, chunk_size=200, overlap=40)
        provider = FakeEmbeddingProvider()
        sync_embeddings_from_database(self.db, provider=provider)

        service = KnowledgeService(embedding_provider=provider)
        service.sync_from_database(self.db)
        with patch.dict(os.environ, {"RAG_MODE": "hybrid"}, clear=True):
            results = service.search("opening", top_k=1)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["retrieval_mode"], "hybrid")
        self.assertIsNotNone(results[0]["keyword_score"])
        self.assertIsNotNone(results[0]["semantic_score"])
        self.assertGreater(results[0]["confidence"], 0)
        self.assertEqual(results[0]["chunk_indices"], [0])

    def test_hybrid_search_degrades_to_chunks_when_model_is_unavailable(self):
        self.db.add(Knowledge(
            title="Opening hours",
            content="The area opens daily.",
            category="service",
        ))
        self.db.commit()
        sync_chunks_from_database(self.db, chunk_size=200, overlap=40)

        service = KnowledgeService(embedding_provider=FailingEmbeddingProvider())
        service.sync_from_database(self.db)
        with self.assertLogs("app.services.knowledge_service", level="WARNING"):
            with patch.dict(os.environ, {"RAG_MODE": "hybrid"}, clear=True):
                results = service.search("opening", top_k=1)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["retrieval_mode"], "chunk")

    def test_confidence_calibration_uses_retrieval_specific_scores(self):
        keyword = calibrate_confidence({
            "retrieval_mode": "chunk",
            "score": 8,
            "keyword_score": 8,
        })
        semantic = calibrate_confidence({
            "retrieval_mode": "semantic",
            "score": 1.0,
            "semantic_score": 1.0,
        })
        hybrid = calibrate_confidence({
            "retrieval_mode": "hybrid",
            "keyword_score": 8,
            "semantic_score": 1.0,
        })

        self.assertGreater(keyword, 0.5)
        self.assertEqual(semantic, 1.0)
        self.assertGreater(hybrid, keyword)

    def test_postprocessor_stitches_neighbors_and_removes_overlap(self):
        chunks = [
            KnowledgeChunk(
                source_type="knowledge",
                source_id=99,
                chunk_index=0,
                title="Guide",
                content="source: knowledge\ntitle: Guide\ncontent: alpha shared",
                content_hash="a" * 64,
                char_count=55,
            ),
            KnowledgeChunk(
                source_type="knowledge",
                source_id=99,
                chunk_index=1,
                title="Guide",
                content="source: knowledge\ntitle: Guide\ncontent: shared beta shared2",
                content_hash="b" * 64,
                char_count=62,
            ),
            KnowledgeChunk(
                source_type="knowledge",
                source_id=99,
                chunk_index=2,
                title="Guide",
                content="source: knowledge\ntitle: Guide\ncontent: shared2 gamma",
                content_hash="c" * 64,
                char_count=56,
            ),
        ]
        self.db.add_all(chunks)
        self.db.commit()
        raw_result = {
            "content": chunks[1].content,
            "score": 8,
            "keyword_score": 8,
            "source_type": "knowledge",
            "source_id": 99,
            "chunk_index": 1,
            "title": "Guide",
            "retrieval_mode": "chunk",
        }

        with patch.dict(
            os.environ,
            {
                "RAG_ADJACENT_CHUNK_WINDOW": "1",
                "RAG_CONTEXT_MAX_CHUNKS": "3",
                "RAG_CONTEXT_MAX_TOKENS": "1000",
            },
            clear=True,
        ):
            results = postprocess_results(self.db, [raw_result], top_k=1)

        self.assertEqual(results[0]["chunk_indices"], [0, 1, 2])
        self.assertTrue(results[0]["stitched"])
        self.assertIn("alpha shared beta shared2 gamma", results[0]["content"])

        with patch.dict(
            os.environ,
            {
                "RAG_ADJACENT_CHUNK_WINDOW": "1",
                "RAG_CONTEXT_MAX_CHUNKS": "1",
                "RAG_CONTEXT_MAX_TOKENS": "1000",
            },
            clear=True,
        ):
            limited = postprocess_results(self.db, [raw_result], top_k=1)

        self.assertEqual(limited[0]["chunk_indices"], [1])

    def test_postprocessor_filters_low_confidence_results(self):
        raw_result = {
            "content": "weak match",
            "score": 1,
            "keyword_score": 1,
            "retrieval_mode": "chunk",
        }
        with patch.dict(
            os.environ,
            {"RAG_MIN_CONFIDENCE": "0.5"},
            clear=True,
        ):
            results = postprocess_results(self.db, [raw_result], top_k=1)

        self.assertEqual(results, [])

    def test_token_estimate_and_truncation_enforce_budget(self):
        text = "\u4e2d\u6587" * 20 + "a" * 80
        truncated = truncate_to_token_budget(text, max_tokens=10)

        self.assertLessEqual(estimate_tokens(truncated), 10)
        self.assertLess(len(truncated), len(text))

    def test_cache_hits_and_sync_invalidation(self):
        knowledge = Knowledge(
            title="Opening hours",
            content="The area opens daily.",
            category="service",
        )
        self.db.add(knowledge)
        self.db.commit()
        sync_chunks_from_database(self.db, chunk_size=200, overlap=40)
        clear_retrieval_cache()
        service = KnowledgeService()
        service.sync_from_database(self.db)

        with patch.dict(os.environ, {"RAG_MODE": "chunk"}, clear=True):
            service.search("opening", top_k=1)
            service.search("opening", top_k=1)

        self.assertGreaterEqual(get_cache_status()["hits"], 1)
        sync_chunks_from_database(self.db, chunk_size=200, overlap=40)
        self.assertEqual(get_cache_status()["entries"], 0)

    def test_reranker_reorders_candidates_when_enabled(self):
        service = KnowledgeService(reranker=FakeReranker())
        service.db = self.db
        raw_results = [
            {
                "content": "first",
                "score": 8,
                "keyword_score": 8,
                "source_type": "knowledge",
                "source_id": 1,
                "chunk_index": 0,
                "retrieval_mode": "chunk",
            },
            {
                "content": "second",
                "score": 7,
                "keyword_score": 7,
                "source_type": "knowledge",
                "source_id": 2,
                "chunk_index": 0,
                "retrieval_mode": "chunk",
            },
        ]

        with patch.dict(
            os.environ,
            {"RAG_RERANK_ENABLED": "true", "RAG_POSTPROCESS_ENABLED": "false"},
            clear=True,
        ):
            results = service._finalize_results("query", raw_results, top_k=2)

        self.assertEqual(results[0]["content"], "second")
        self.assertEqual(results[0]["rerank_score"], 1.0)

    def test_faiss_backend_falls_back_to_exact_search(self):
        knowledge = Knowledge(
            title="Opening hours",
            content="The area opens daily.",
            category="service",
        )
        self.db.add(knowledge)
        self.db.commit()
        sync_chunks_from_database(self.db, chunk_size=200, overlap=40)
        provider = FakeEmbeddingProvider()
        sync_embeddings_from_database(self.db, provider=provider)
        service = KnowledgeService(embedding_provider=provider)
        service.sync_from_database(self.db)

        with self.assertLogs("app.services.embedding_service", level="WARNING"):
            with patch.dict(
                os.environ,
                {"RAG_VECTOR_BACKEND": "faiss", "RAG_POSTPROCESS_ENABLED": "false"},
                clear=True,
            ):
                results = service.search_semantic("opening", top_k=1)

        self.assertEqual(results[0]["vector_backend"], "exact")

    def test_evaluation_report_calculates_hit_rate_and_mrr(self):
        cases = [
            {"query": "first", "expected": [{"source_id": 1}]},
            {"query": "second", "expected": [{"source_id": 2}]},
        ]

        def search(query, top_k):
            source_id = 1 if query == "first" else 2
            return [{"source_id": source_id}]

        report = evaluate_search(
            search,
            cases,
            mode="test",
            top_k=1,
            min_hit_rate=1.0,
            min_mrr=1.0,
        )

        self.assertTrue(report.passed)
        self.assertEqual(report.hit_rate, 1.0)
        self.assertEqual(report.mrr, 1.0)

    def test_faiss_status_is_not_ready_without_index_files(self):
        with patch.dict(os.environ, {"RAG_FAISS_DIR": "tests/nonexistent-faiss"}, clear=True):
            status = get_faiss_status("missing-model")

        self.assertFalse(status["ready"])


if __name__ == "__main__":
    unittest.main()
