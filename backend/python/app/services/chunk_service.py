from dataclasses import asdict, dataclass
import hashlib
import json
import re
from typing import Iterable

from sqlalchemy.orm import Session

from app.models import FAQItem, Knowledge, KnowledgeChunk, Spot
from app.rag_config import get_chunk_overlap, get_chunk_size
from app.services.retrieval_cache import clear_retrieval_cache


SUPPORTED_SOURCE_TYPES = {"knowledge", "spot", "faq"}
SENTENCE_SPLIT_PATTERN = re.compile(
    r"(?<=[\u3002\uff01\uff1f.!?;\uff1b])|\n+"
)
SENTENCE_BOUNDARY_PATTERN = re.compile(
    r"[\u3002\uff01\uff1f.!?;\uff1b\n]"
)


@dataclass(frozen=True)
class SourceDocument:
    source_type: str
    source_id: int
    title: str
    body: str
    metadata: dict


@dataclass
class ChunkSyncStats:
    sources: int = 0
    chunks: int = 0
    created: int = 0
    updated: int = 0
    deleted: int = 0
    unchanged: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


def split_text(text: str, chunk_size: int = 500, overlap: int = 80) -> list[str]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be non-negative and smaller than chunk_size")

    normalized = _normalize_text(text)
    if not normalized:
        return []

    segments = [
        segment.strip()
        for segment in SENTENCE_SPLIT_PATTERN.split(normalized)
        if segment.strip()
    ]
    core_chunks: list[str] = []
    current = ""

    for segment in segments:
        separator = "\n" if current else ""
        if current and len(current) + len(separator) + len(segment) > chunk_size:
            core_chunks.append(current)
            current = ""

        if len(segment) <= chunk_size:
            separator = "\n" if current else ""
            current = f"{current}{separator}{segment}"
            continue

        if current:
            core_chunks.append(current)
            current = ""
        core_chunks.extend(
            segment[index:index + chunk_size]
            for index in range(0, len(segment), chunk_size)
        )

    if current:
        core_chunks.append(current)

    chunks: list[str] = []
    for index, core_chunk in enumerate(core_chunks):
        if index == 0 or overlap == 0:
            chunks.append(core_chunk)
            continue
        prefix = _overlap_tail(core_chunks[index - 1], overlap)
        chunks.append(f"{prefix}\n{core_chunk}" if prefix else core_chunk)
    return chunks


def iter_source_documents(db: Session) -> Iterable[SourceDocument]:
    for item in db.query(Knowledge).order_by(Knowledge.id.asc()).all():
        yield SourceDocument(
            source_type="knowledge",
            source_id=item.id,
            title=item.title or "",
            body=item.content or "",
            metadata={"category": item.category or ""},
        )

    for spot in db.query(Spot).order_by(Spot.id.asc()).all():
        fields = [
            ("scenic_area", spot.scenic_area_name),
            ("location", spot.location),
            ("description", spot.description),
            ("architecture", spot.architecture_params),
            ("function", spot.core_function),
            ("culture", spot.culture_connotation),
            ("highlights", spot.highlights),
            ("open_info", spot.open_info),
            ("remark", spot.remark),
        ]
        body = "\n".join(f"{label}: {value}" for label, value in fields if value)
        yield SourceDocument(
            source_type="spot",
            source_id=spot.id,
            title=spot.spot_name or "",
            body=body,
            metadata={"scenic_area_name": spot.scenic_area_name or ""},
        )

    for faq in db.query(FAQItem).filter(FAQItem.is_active.is_(True)).order_by(FAQItem.id.asc()).all():
        body = f"question: {faq.question}\nanswer: {faq.answer}"
        yield SourceDocument(
            source_type="faq",
            source_id=faq.id,
            title=faq.question or "",
            body=body,
            metadata={"category": faq.category or "", "source_name": faq.source_name or ""},
        )


def sync_chunks_from_database(
    db: Session,
    chunk_size: int | None = None,
    overlap: int | None = None,
    commit: bool = True,
) -> ChunkSyncStats:
    chunk_size = chunk_size if chunk_size is not None else get_chunk_size()
    overlap = overlap if overlap is not None else get_chunk_overlap()
    stats = ChunkSyncStats()

    existing_chunks = db.query(KnowledgeChunk).filter(
        KnowledgeChunk.source_type.in_(SUPPORTED_SOURCE_TYPES)
    ).all()
    existing_by_key = {
        (item.source_type, item.source_id, item.chunk_index): item
        for item in existing_chunks
    }
    desired_keys: set[tuple[str, int, int]] = set()

    for source in iter_source_documents(db):
        stats.sources += 1
        metadata_json = json.dumps(source.metadata, ensure_ascii=False, sort_keys=True)
        body_chunks = split_text(
            source.body or source.title,
            chunk_size=chunk_size,
            overlap=overlap,
        )
        for chunk_index, body_chunk in enumerate(body_chunks):
            content = _format_chunk(source, body_chunk)
            content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
            key = (source.source_type, source.source_id, chunk_index)
            desired_keys.add(key)
            stats.chunks += 1

            existing = existing_by_key.get(key)
            if existing is None:
                db.add(
                    KnowledgeChunk(
                        source_type=source.source_type,
                        source_id=source.source_id,
                        chunk_index=chunk_index,
                        title=source.title,
                        content=content,
                        content_hash=content_hash,
                        metadata_json=metadata_json,
                        char_count=len(content),
                    )
                )
                stats.created += 1
                continue

            changed = (
                existing.title != source.title
                or existing.content_hash != content_hash
                or existing.metadata_json != metadata_json
                or existing.char_count != len(content)
            )
            if changed:
                existing.title = source.title
                existing.content = content
                existing.content_hash = content_hash
                existing.metadata_json = metadata_json
                existing.char_count = len(content)
                stats.updated += 1
            else:
                stats.unchanged += 1

    for key, existing in existing_by_key.items():
        if key not in desired_keys:
            db.delete(existing)
            stats.deleted += 1

    if commit:
        db.commit()
    else:
        db.flush()
    clear_retrieval_cache()
    return stats


def _normalize_text(text: str) -> str:
    text = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]
    return "\n".join(line for line in lines if line).strip()


def _overlap_tail(text: str, overlap: int) -> str:
    if overlap == 0:
        return ""
    tail = text[-overlap:]
    boundary = SENTENCE_BOUNDARY_PATTERN.search(tail)
    if boundary and boundary.end() < len(tail):
        return tail[boundary.end():].lstrip()
    return tail


def _format_chunk(source: SourceDocument, body_chunk: str) -> str:
    return (
        f"source: {source.source_type}\n"
        f"title: {source.title}\n"
        f"content: {body_chunk}"
    )
