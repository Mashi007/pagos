-- ============================================
-- Crear Tabla de Calificaciones del Chat AI
-- ============================================
-- Este script crea la tabla necesaria para almacenar
-- las calificaciones (pulgar arriba/abajo) de las respuestas del Chat AI

-- Tabla: ai_calificaciones_chat
CREATE TABLE IF NOT EXISTS ai_calificaciones_chat (
    id SERIAL PRIMARY KEY,
    pregunta TEXT NOT NULL,
    respuesta_ai TEXT NOT NULL,
    calificacion VARCHAR(20) NOT NULL CHECK (calificacion IN ('arriba', 'abajo')),
    usuario_email VARCHAR(255),
    procesado BOOLEAN NOT NULL DEFAULT FALSE,
    notas_procesamiento TEXT,
    mejorado BOOLEAN NOT NULL DEFAULT FALSE,
    creado_en TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    actualizado_en TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Índices para búsquedas rápidas
CREATE INDEX IF NOT EXISTS idx_ai_calificaciones_chat_calificacion ON ai_calificaciones_chat(calificacion);
CREATE INDEX IF NOT EXISTS idx_ai_calificaciones_chat_usuario_email ON ai_calificaciones_chat(usuario_email);
CREATE INDEX IF NOT EXISTS idx_ai_calificaciones_chat_procesado ON ai_calificaciones_chat(procesado);
CREATE INDEX IF NOT EXISTS idx_ai_calificaciones_chat_creado_en ON ai_calificaciones_chat(creado_en);

-- Índice compuesto para consultas comunes
CREATE INDEX IF NOT EXISTS idx_ai_calificaciones_chat_procesado_calificacion ON ai_calificaciones_chat(procesado, calificacion);

-- Comentarios descriptivos
COMMENT ON TABLE ai_calificaciones_chat IS 'Calificaciones de respuestas del Chat AI (pulgar arriba/abajo)';
COMMENT ON COLUMN ai_calificaciones_chat.pregunta IS 'Pregunta del usuario que generó la respuesta';
COMMENT ON COLUMN ai_calificaciones_chat.respuesta_ai IS 'Respuesta del AI que fue calificada';
COMMENT ON COLUMN ai_calificaciones_chat.calificacion IS 'Calificación: "arriba" (positiva) o "abajo" (negativa)';
COMMENT ON COLUMN ai_calificaciones_chat.usuario_email IS 'Email del usuario que realizó la calificación';
COMMENT ON COLUMN ai_calificaciones_chat.procesado IS 'Si la calificación negativa ya fue procesada para mejorar el sistema';
COMMENT ON COLUMN ai_calificaciones_chat.notas_procesamiento IS 'Notas sobre cómo se procesó esta calificación y qué mejoras se implementaron';
COMMENT ON COLUMN ai_calificaciones_chat.mejorado IS 'Si el sistema fue mejorado basado en esta calificación';

-- Verificar que la tabla se creó correctamente
DO $$
BEGIN
    IF EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name = 'ai_calificaciones_chat'
    ) THEN
        RAISE NOTICE '✅ Tabla ai_calificaciones_chat creada exitosamente';
    ELSE
        RAISE EXCEPTION '❌ Error: La tabla ai_calificaciones_chat no se pudo crear';
    END IF;
END $$;
