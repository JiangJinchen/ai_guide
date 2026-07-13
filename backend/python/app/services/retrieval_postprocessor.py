import math

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.models import KnowledgeChunk
from app.rag_config import (
    get_adjacent_chunk_window,
    get_context_max_chunks,
    get_context_max_tokens,
    get_keyword_score_scale,
    get_min_confidence,
    get_semantic_min_score,
)


def postprocess_results(
    db: Session,
    results: list[dict],
    top_k: int,
) -> list[dict]:
    if not results or top_k <= 0:
        return []

    calibrated = []
    min_confidence = get_min_confidence()
    for source_result in results:
        result = dict(source_result)
        result["confidence"] = round(calibrate_confidence(result), 6)
        if result["confidence"] >= min_confidence:
            calibrated.append(result)

    if not calibrated:
        return []
    return stitch_and_budget_results(db, calibrated, top_k=top_k)


def calibrate_confidence(result: dict) -> float:
    mode = result.get("retrieval_mode")
    keyword_score = result.get("keyword_score")
    semantic_score = result.get("semantic_score")

    if keyword_score is None and mode == "chunk":
        keyword_score = result.get("score")
    if semantic_score is None and mode == "semantic":
        semantic_score = result.get("score")

    keyword_confidence = (
        _keyword_confidence(keyword_score)
        if keyword_score is not None
        else None
    )
    semantic_confidence = (
        _semantic_confidence(semantic_score)
        if semantic_score is not None
        else None
    )

    if keyword_confidence is not None and semantic_confidence is not None:
        agreement_bonus = 0.10 * min(keyword_confidence, semantic_confidence)
        retrieval_confidence = min(
            1.0,
            0.45 * keyword_confidence
            + 0.55 * semantic_confidence
            + agreement_bonus,
        )
    elif semantic_confidence is not None:
        retrieval_confidence = semantic_confidence
    elif keyword_confidence is not None:
        retrieval_confidence = keyword_confidence
    else:
        retrieval_confidence = 0.0

    rerank_confidence = result.get("rerank_confidence")
    if rerank_confidence is None:
        return retrieval_confidence
    rerank_confidence = max(0.0, min(1.0, float(rerank_confidence)))
    return 0.40 * retrieval_confidence + 0.60 * rerank_confidence


def stitch_and_budget_results(
    db: Session,
    results: list[dict],
    top_k: int,
) -> list[dict]:
    window = get_adjacent_chunk_window()
    max_chunks = get_context_max_chunks()
    remaining_tokens = get_context_max_tokens()
    chunks_by_source = _load_source_chunks(db, results)
    hit_indices_by_source: dict[tuple, set[int]] = {}
    confidence_by_chunk: dict[tuple, float] = {}

    for result in results:
        source_key = (result.get("source_type"), result.get("source_id"))
        chunk_index = result.get("chunk_index")
        if source_key[0] is None or source_key[1] is None or chunk_index is None:
            continue
        hit_indices_by_source.setdefault(source_key, set()).add(chunk_index)
        confidence_by_chunk[(source_key, chunk_index)] = result["confidence"]

    output = []
    used_chunks: set[tuple] = set()
    used_chunk_count = 0

    for result in results:
        if len(output) >= top_k or remaining_tokens <= 0:
            break

        source_key = (result.get("source_type"), result.get("source_id"))
        hit_index = result.get("chunk_index")
        selected = []
        if source_key in chunks_by_source and hit_index is not None:
            if (source_key, hit_index) in used_chunks:
                continue
            candidates = [
                chunk
                for chunk in chunks_by_source[source_key]
                if hit_index - window <= chunk.chunk_index <= hit_index + window
                and (source_key, chunk.chunk_index) not in used_chunks
            ]
            available_chunks = max_chunks - used_chunk_count
            selected = sorted(
                sorted(
                    candidates,
                    key=lambda chunk: (abs(chunk.chunk_index - hit_index), chunk.chunk_index),
                )[:max(0, available_chunks)],
                key=lambda chunk: chunk.chunk_index,
            )

        if selected:
            content = _merge_chunk_contents([chunk.content for chunk in selected])
            chunk_indices = [chunk.chunk_index for chunk in selected]
            for chunk_index in chunk_indices:
                used_chunks.add((source_key, chunk_index))
            used_chunk_count += len(selected)
        else:
            if used_chunk_count >= max_chunks:
                break
            content = result.get("content", "")
            chunk_indices = [hit_index] if hit_index is not None else []
            used_chunk_count += 1

        original_content = content
        content = truncate_to_token_budget(content, remaining_tokens)
        if not content:
            continue
        token_estimate = estimate_tokens(content)
        remaining_tokens -= token_estimate

        matched_indices = sorted(
            hit_indices_by_source.get(source_key, set()).intersection(chunk_indices)
        )
        related_confidences = [
            confidence_by_chunk[(source_key, chunk_index)]
            for chunk_index in matched_indices
            if (source_key, chunk_index) in confidence_by_chunk
        ]
        final_result = dict(result)
        if related_confidences:
            final_result["confidence"] = round(max(related_confidences), 6)
        final_result["content"] = content
        final_result["chunk_indices"] = chunk_indices
        final_result["matched_chunk_indices"] = matched_indices
        final_result["stitched"] = len(chunk_indices) > 1
        final_result["context_truncated"] = content != original_content
        final_result["context_token_estimate"] = token_estimate
        output.append(final_result)

    return output


def estimate_tokens(text: str) -> int:
    units = sum(4 if "\u4e00" <= char <= "\u9fff" else 1 for char in text or "")
    return math.ceil(units / 4)


def truncate_to_token_budget(text: str, max_tokens: int) -> str:
    if max_tokens <= 0:
        return ""
    max_units = max_tokens * 4
    used_units = 0
    output = []
    for char in text or "":
        char_units = 4 if "\u4e00" <= char <= "\u9fff" else 1
        if used_units + char_units > max_units:
            break
        output.append(char)
        used_units += char_units
    return "".join(output).rstrip()


def _keyword_confidence(score) -> float:
    value = max(0.0, float(score))
    return 1.0 - math.exp(-value / get_keyword_score_scale())


def _semantic_confidence(score) -> float:
    value = max(-1.0, min(1.0, float(score)))
    minimum = get_semantic_min_score()
    if minimum >= 1.0:
        return 1.0 if value >= 1.0 else 0.0
    return max(0.0, min(1.0, (value - minimum) / (1.0 - minimum)))


def _load_source_chunks(db: Session, results: list[dict]) -> dict[tuple, list]:
    sources = {
        (result.get("source_type"), result.get("source_id"))
        for result in results
        if result.get("source_type") is not None
        and result.get("source_id") is not None
    }
    if not sources:
        return {}

    conditions = [
        and_(
            KnowledgeChunk.source_type == source_type,
            KnowledgeChunk.source_id == source_id,
        )
        for source_type, source_id in sources
    ]
    chunks = (
        db.query(KnowledgeChunk)
        .filter(or_(*conditions))
        .order_by(
            KnowledgeChunk.source_type.asc(),
            KnowledgeChunk.source_id.asc(),
            KnowledgeChunk.chunk_index.asc(),
        )
        .all()
    )
    chunks_by_source: dict[tuple, list] = {}
    for chunk in chunks:
        chunks_by_source.setdefault(
            (chunk.source_type, chunk.source_id),
            [],
        ).append(chunk)
    return chunks_by_source


def _merge_chunk_contents(contents: list[str]) -> str:
    if not contents:
        return ""
    parsed = [_split_chunk_content(content) for content in contents]
    if any(body is None for _, body in parsed):
        return "\n\n".join(contents)

    header = parsed[0][0]
    merged_body = parsed[0][1] or ""
    for _, body in parsed[1:]:
        merged_body = _merge_overlap(merged_body, body or "")
    return f"{header}\ncontent: {merged_body}" if header else merged_body


def _split_chunk_content(content: str) -> tuple[str, str | None]:
    marker = "\ncontent: "
    if marker not in content:
        return "", None
    return tuple(content.split(marker, 1))


def _merge_overlap(left: str, right: str) -> str:
    max_overlap = min(200, len(left), len(right))
    for size in range(max_overlap, 0, -1):
        if left.endswith(right[:size]):
            return f"{left}{right[size:]}"
    separator = "\n" if left and right else ""
    return f"{left}{separator}{right}"
