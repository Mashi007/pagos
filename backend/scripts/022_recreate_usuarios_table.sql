-- Migration 022: Recreate usuarios table (was accidentally deleted in cleanup)
-- Date: 2026-03-04
-- Purpose: Restore the usuarios table required by User model for authentication
-- Impact: Required for login and user management functionality

CREATE TABLE IF NOT EXISTS public.usuarios (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    apellido VARCHAR(100) NOT NULL DEFAULT '',
    cargo VARCHAR(100),
    rol VARCHAR(20) NOT NULL DEFAULT 'operativo',
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

-- Create index for email lookups
CREATE INDEX IF NOT EXISTS idx_usuarios_email ON public.usuarios(email);

-- Log migration completion
SELECT 'Migration 022: usuarios table recreated successfully' AS status;
