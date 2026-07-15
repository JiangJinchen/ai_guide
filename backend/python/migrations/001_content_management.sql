BEGIN;

CREATE TABLE IF NOT EXISTS faq_items (
    id SERIAL PRIMARY KEY,
    question VARCHAR(500) NOT NULL,
    answer TEXT NOT NULL,
    category VARCHAR(100),
    sort_order INTEGER DEFAULT 100,
    is_active BOOLEAN DEFAULT TRUE,
    source_name VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_faq_items_category ON faq_items (category);
CREATE INDEX IF NOT EXISTS ix_faq_items_sort_order ON faq_items (sort_order);
CREATE INDEX IF NOT EXISTS ix_faq_items_is_active ON faq_items (is_active);

COMMIT;
