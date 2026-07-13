CREATE TABLE IF NOT EXISTS spot_guide_assets (
    id SERIAL PRIMARY KEY,
    spot_id INTEGER NOT NULL,
    style VARCHAR(50) NOT NULL DEFAULT 'standard',
    voice VARCHAR(50) NOT NULL DEFAULT 'female',
    script_text TEXT NOT NULL,
    audio_url VARCHAR(500),
    audio_path VARCHAR(500),
    source_hash VARCHAR(64) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'ready',
    error_message TEXT,
    duration_seconds INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ,
    CONSTRAINT uq_spot_guide_assets_spot_style_voice UNIQUE (spot_id, style, voice)
);

CREATE INDEX IF NOT EXISTS ix_spot_guide_assets_spot_id
    ON spot_guide_assets (spot_id);

CREATE INDEX IF NOT EXISTS ix_spot_guide_assets_style
    ON spot_guide_assets (style);

CREATE INDEX IF NOT EXISTS ix_spot_guide_assets_voice
    ON spot_guide_assets (voice);

CREATE INDEX IF NOT EXISTS ix_spot_guide_assets_source_hash
    ON spot_guide_assets (source_hash);

CREATE INDEX IF NOT EXISTS ix_spot_guide_assets_status
    ON spot_guide_assets (status);
