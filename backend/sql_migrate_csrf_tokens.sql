-- Script de Migración: Crear tabla CSRF_TOKENS
-- Ejecutar en la base de datos para almacenar tokens CSRF

CREATE TABLE IF NOT EXISTS csrf_tokens (
    session_id VARCHAR(255) PRIMARY KEY COMMENT 'ID único de sesión del usuario',
    token VARCHAR(255) UNIQUE NOT NULL COMMENT 'Token CSRF criptográficamente seguro',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Timestamp de creación del token',
    expires_at TIMESTAMP NOT NULL COMMENT 'Timestamp de expiración del token',
    INDEX idx_token (token) COMMENT 'Índice para búsqueda rápida de tokens',
    INDEX idx_expires (expires_at) COMMENT 'Índice para limpieza de tokens expirados'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci 
  COMMENT='Tokens CSRF para protección contra ataques Cross-Site Request Forgery';

-- Nota: Los tokens son one-time use (se eliminan después de validarse)
-- Los tokens expirados se limpian automáticamente cada hora

-- Verificación
SELECT COUNT(*) as csrf_tokens_count FROM csrf_tokens;
SELECT 'Tabla csrf_tokens creada exitosamente' as status;
