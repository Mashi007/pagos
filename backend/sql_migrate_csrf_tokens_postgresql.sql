-- Script de Migracion: Crear tabla CSRF_TOKENS
-- Para PostgreSQL (usado en Render)

CREATE TABLE IF NOT EXISTS csrf_tokens (
    session_id VARCHAR(255) PRIMARY KEY,
    token VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL
);

-- Crear indices para optimizar busquedas
CREATE INDEX IF NOT EXISTS idx_csrf_token ON csrf_tokens(token);
CREATE INDEX IF NOT EXISTS idx_csrf_expires ON csrf_tokens(expires_at);

-- Comentarios (PostgreSQL)
COMMENT ON TABLE csrf_tokens IS 'Tokens CSRF para proteccion contra ataques Cross-Site Request Forgery';
COMMENT ON COLUMN csrf_tokens.session_id IS 'ID unico de sesion del usuario';
COMMENT ON COLUMN csrf_tokens.token IS 'Token CSRF criptograficamente seguro';
COMMENT ON COLUMN csrf_tokens.created_at IS 'Timestamp de creacion del token';
COMMENT ON COLUMN csrf_tokens.expires_at IS 'Timestamp de expiracion del token';

-- Verificacion
SELECT COUNT(*) as csrf_tokens_count FROM csrf_tokens;
SELECT 'Tabla csrf_tokens creada exitosamente' as status;
