BEGIN;

CREATE TABLE IF NOT EXISTS admin_roles (
    id SERIAL PRIMARY KEY,
    role_key VARCHAR(50) NOT NULL UNIQUE,
    label VARCHAR(100) NOT NULL,
    permissions TEXT NOT NULL DEFAULT '[]',
    is_system BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_admin_roles_is_system ON admin_roles (is_system);

INSERT INTO admin_roles (role_key, label, permissions, is_system)
VALUES
    ('admin', '系统管理员', '["*"]', TRUE),
    ('content_operator', '内容运营', '["content.read", "content.write"]', TRUE),
    ('analyst', '数据分析', '["analytics.read"]', TRUE),
    ('digital_operator', '数字人运营', '["digital_human.read", "digital_human.write"]', TRUE)
ON CONFLICT (role_key) DO UPDATE SET
    label = EXCLUDED.label,
    permissions = EXCLUDED.permissions,
    is_system = TRUE;

COMMIT;
