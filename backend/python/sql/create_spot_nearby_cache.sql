CREATE TABLE IF NOT EXISTS spot_nearby_cache (
    id SERIAL PRIMARY KEY,
    cache_key VARCHAR(255) NOT NULL UNIQUE,
    spot_id INTEGER NOT NULL,
    scenic_area_name VARCHAR(255),
    center_lat DOUBLE PRECISION NOT NULL,
    center_lon DOUBLE PRECISION NOT NULL,
    radius_km DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    payload_json TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'ready',
    source VARCHAR(50) NOT NULL DEFAULT 'local',
    error_message TEXT,
    refreshed_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_spot_nearby_cache_spot_id ON spot_nearby_cache (spot_id);
CREATE INDEX IF NOT EXISTS ix_spot_nearby_cache_scenic_area_name ON spot_nearby_cache (scenic_area_name);
CREATE INDEX IF NOT EXISTS ix_spot_nearby_cache_status ON spot_nearby_cache (status);
CREATE INDEX IF NOT EXISTS ix_spot_nearby_cache_refreshed_at ON spot_nearby_cache (refreshed_at);
