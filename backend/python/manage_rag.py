import argparse
import json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage staged RAG data")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("status", help="Show current chunk counts")

    sync_parser = subparsers.add_parser("sync-chunks", help="Rebuild changed chunks")
    sync_parser.add_argument("--chunk-size", type=int, default=None)
    sync_parser.add_argument("--overlap", type=int, default=None)
    subparsers.add_parser(
        "embedding-status",
        help="Show embedding counts by model",
    )
    embedding_parser = subparsers.add_parser(
        "sync-embeddings",
        help="Build missing or changed chunk embeddings",
    )
    embedding_parser.add_argument("--model", default=None)
    embedding_parser.add_argument("--batch-size", type=int, default=None)
    faiss_parser = subparsers.add_parser(
        "build-faiss",
        help="Build a FAISS index from current embeddings",
    )
    faiss_parser.add_argument("--model", default=None)
    faiss_status_parser = subparsers.add_parser(
        "faiss-status",
        help="Show FAISS index metadata",
    )
    faiss_status_parser.add_argument("--model", default=None)
    evaluation_parser = subparsers.add_parser(
        "evaluate-rag",
        help="Evaluate retrieval against a JSONL dataset",
    )
    evaluation_parser.add_argument("--dataset", required=True)
    evaluation_parser.add_argument("--mode", default="hybrid")
    evaluation_parser.add_argument("--top-k", type=int, default=3)
    evaluation_parser.add_argument("--min-hit-rate", type=float, default=0.0)
    evaluation_parser.add_argument("--min-mrr", type=float, default=0.0)
    return parser


def main() -> None:
    args = build_parser().parse_args()

    if args.command == "faiss-status":
        from app.rag_config import get_embedding_model_name
        from app.services.faiss_index_service import get_faiss_status

        model_name = args.model or get_embedding_model_name()
        print(json.dumps(get_faiss_status(model_name), ensure_ascii=False))
        return

    if args.command == "evaluate-rag":
        import os

        from app.database import SessionLocal
        from app.services.evaluation_service import (
            evaluate_search,
            load_evaluation_cases,
        )
        from app.services.knowledge_service import KnowledgeService

        cases = load_evaluation_cases(args.dataset)
        previous_mode = os.environ.get("RAG_MODE")
        os.environ["RAG_MODE"] = args.mode
        try:
            with SessionLocal() as db:
                service = KnowledgeService()
                service.sync_from_database(db)
                report = evaluate_search(
                    service.search,
                    cases,
                    mode=args.mode,
                    top_k=args.top_k,
                    min_hit_rate=args.min_hit_rate,
                    min_mrr=args.min_mrr,
                )
        finally:
            if previous_mode is None:
                os.environ.pop("RAG_MODE", None)
            else:
                os.environ["RAG_MODE"] = previous_mode
        print(json.dumps(report.to_dict(), ensure_ascii=False))
        if not report.passed:
            raise SystemExit(1)
        return

    from app.database import SessionLocal, engine
    from app.models import KnowledgeChunk, KnowledgeChunkEmbedding
    from app.services.chunk_service import sync_chunks_from_database
    from app.services.embedding_service import (
        SentenceTransformerEmbeddingProvider,
        sync_embeddings_from_database,
    )
    from app.services.faiss_index_service import build_faiss_index
    from app.rag_config import get_embedding_model_name

    KnowledgeChunk.__table__.create(bind=engine, checkfirst=True)
    if args.command in {"embedding-status", "sync-embeddings", "build-faiss"}:
        KnowledgeChunkEmbedding.__table__.create(bind=engine, checkfirst=True)

    with SessionLocal() as db:
        if args.command == "status":
            rows = (
                db.query(KnowledgeChunk.source_type, KnowledgeChunk.id)
                .order_by(KnowledgeChunk.source_type.asc())
                .all()
            )
            counts: dict[str, int] = {}
            for source_type, _ in rows:
                counts[source_type] = counts.get(source_type, 0) + 1
            print(json.dumps({"chunks": counts, "total": len(rows)}, ensure_ascii=False))
            return

        if args.command == "sync-chunks":
            stats = sync_chunks_from_database(
                db,
                chunk_size=args.chunk_size,
                overlap=args.overlap,
            )
            print(json.dumps(stats.to_dict(), ensure_ascii=False))
            return

        if args.command == "embedding-status":
            rows = db.query(
                KnowledgeChunkEmbedding.model_name,
                KnowledgeChunkEmbedding.id,
            ).all()
            counts: dict[str, int] = {}
            for model_name, _ in rows:
                counts[model_name] = counts.get(model_name, 0) + 1
            print(json.dumps({"embeddings": counts, "total": len(rows)}))
            return

        if args.command == "build-faiss":
            model_name = args.model or get_embedding_model_name()
            stats = build_faiss_index(db, model_name=model_name)
            print(json.dumps(stats.to_dict(), ensure_ascii=False))
            return

        provider = SentenceTransformerEmbeddingProvider(
            model_name=args.model,
            batch_size=args.batch_size,
        )
        stats = sync_embeddings_from_database(db, provider=provider)
        print(json.dumps(stats.to_dict(), ensure_ascii=False))


if __name__ == "__main__":
    main()
