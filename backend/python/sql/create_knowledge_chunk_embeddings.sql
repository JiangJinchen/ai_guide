CREATE TABLE IF NOT EXISTS knowledge_chunk_embeddings (
    id SERIAL PRIMARY KEY,
    chunk_id INTEGER NOT NULL,
    model_name VARCHAR(255) NOT NULL,
    content_hash VARCHAR(64) NOT NULL,
    dimensions INTEGER NOT NULL,
    embedding_json TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ,
    CONSTRAINT uq_knowledge_chunk_embeddings_chunk_model
        UNIQUE (chunk_id, model_name)
);

CREATE INDEX IF NOT EXISTS ix_knowledge_chunk_embeddings_chunk_id
    ON knowledge_chunk_embeddings (chunk_id);
CREATE INDEX IF NOT EXISTS ix_knowledge_chunk_embeddings_model_name
    ON knowledge_chunk_embeddings (model_name);
CREATE INDEX IF NOT EXISTS ix_knowledge_chunk_embeddings_content_hash
    ON knowledge_chunk_embeddings (content_hash);
