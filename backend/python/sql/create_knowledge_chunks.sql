CREATE TABLE IF NOT EXISTS knowledge_chunks (
    id SERIAL PRIMARY KEY,
    source_type VARCHAR(32) NOT NULL,
    source_id INTEGER NOT NULL,
    chunk_index INTEGER NOT NULL,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    content_hash VARCHAR(64) NOT NULL,
    metadata_json TEXT,
    char_count INTEGER NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ,
    CONSTRAINT uq_knowledge_chunks_source_position
        UNIQUE (source_type, source_id, chunk_index)
);

CREATE INDEX IF NOT EXISTS ix_knowledge_chunks_source_type
    ON knowledge_chunks (source_type);
CREATE INDEX IF NOT EXISTS ix_knowledge_chunks_source_id
    ON knowledge_chunks (source_id);
CREATE INDEX IF NOT EXISTS ix_knowledge_chunks_content_hash
    ON knowledge_chunks (content_hash);
