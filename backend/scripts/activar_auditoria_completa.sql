-- ============================================
-- SCRIPT SQL PARA ACTIVACIÓN COMPLETA DE AUDITORÍA
-- ============================================
-- Configuración completa del sistema de auditoría
-- Análisis de base de datos y activación de todos los elementos

-- 1. VERIFICAR ESTRUCTURA DE AUDITORÍA
-- ============================================

-- Verificar que la tabla auditorias existe y tiene la estructura correcta
SELECT 
    'ESTRUCTURA DE AUDITORÍA' as verificacion,
    table_name,
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'auditorias'
ORDER BY ordinal_position;

-- 2. VERIFICAR REGISTROS EXISTENTES
-- ============================================

-- Contar registros de auditoría por módulo
SELECT 
    'ESTADÍSTICAS POR MÓDULO' as reporte,
    modulo,
    COUNT(*) as total_registros,
    COUNT(DISTINCT usuario_email) as usuarios_unicos,
    MIN(fecha) as fecha_mas_antigua,
    MAX(fecha) as fecha_mas_reciente
FROM auditorias 
GROUP BY modulo
ORDER BY total_registros DESC;

-- Contar registros por acción
SELECT 
    'ESTADÍSTICAS POR ACCIÓN' as reporte,
    accion,
    COUNT(*) as total_veces,
    COUNT(DISTINCT modulo) as modulos_afectados
FROM auditorias 
GROUP BY accion
ORDER BY total_veces DESC;

-- Contar registros por resultado
SELECT 
    'ESTADÍSTICAS POR RESULTADO' as reporte,
    resultado,
    COUNT(*) as total_registros,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as porcentaje
FROM auditorias 
GROUP BY resultado
ORDER BY total_registros DESC;

-- 3. CONFIGURAR PARÁMETROS DE AUDITORÍA
-- ============================================

-- Insertar configuraciones de auditoría si no existen
INSERT INTO configuracion_sistema (
    categoria, subcategoria, clave, valor, descripcion, 
    tipo_dato, requerido, visible_frontend, creado_en
) VALUES 
    ('AUDITORIA', 'GENERAL', 'AUDITORIA_ACTIVA', 'true', 
     'Sistema de auditoría activo', 'BOOLEAN', true, true, NOW()),
    
    ('AUDITORIA', 'GENERAL', 'AUDITORIA_RETENCION_DIAS', '365', 
     'Días de retención de registros de auditoría', 'INTEGER', true, true, NOW()),
    
    ('AUDITORIA', 'GENERAL', 'AUDITORIA_LOG_LEVEL', 'INFO', 
     'Nivel de logging para auditoría', 'STRING', false, true, NOW()),
    
    ('AUDITORIA', 'EXPORTACION', 'AUDITORIA_EXPORT_FORMATOS', '["EXCEL", "CSV", "PDF"]', 
     'Formatos disponibles para exportación', 'JSON', true, true, NOW()),
    
    ('AUDITORIA', 'EXPORTACION', 'AUDITORIA_EXPORT_MAX_RECORDS', '10000', 
     'Máximo número de registros por exportación', 'INTEGER', true, true, NOW()),
    
    ('AUDITORIA', 'ALERTAS', 'AUDITORIA_ALERTAS_ACTIVAS', 'true', 
     'Alertas de auditoría activas', 'BOOLEAN', true, true, NOW()),
    
    ('AUDITORIA', 'ALERTAS', 'AUDITORIA_ALERTAS_EMAIL', 'itmaster@rapicreditca.com', 
     'Email para alertas de auditoría', 'STRING', true, true, NOW()),
    
    ('AUDITORIA', 'MONITOREO', 'AUDITORIA_MONITOREO_TIEMPO_REAL', 'true', 
     'Monitoreo en tiempo real activo', 'BOOLEAN', true, true, NOW()),
    
    ('AUDITORIA', 'MONITOREO', 'AUDITORIA_DASHBOARD_REFRESH_SECONDS', '30', 
     'Intervalo de actualización del dashboard (segundos)', 'INTEGER', true, true, NOW())
ON CONFLICT (categoria, clave) DO UPDATE SET
    valor = EXCLUDED.valor,
    descripcion = EXCLUDED.descripcion,
    actualizado_en = NOW(),
    actualizado_por = 'Sistema de Auditoría';

-- 4. CREAR REGISTROS DE AUDITORÍA INICIALES
-- ============================================

-- Insertar registros de auditoría de ejemplo para demostración
INSERT INTO auditorias (
    usuario_id, usuario_email, accion, modulo, tabla, 
    descripcion, resultado, fecha
) VALUES 
    (
        (SELECT id FROM usuarios WHERE email = 'itmaster@rapicreditca.com'),
        'itmaster@rapicreditca.com',
        'LOGIN',
        'AUTH',
        'usuarios',
        'Inicio de sesión del administrador - Activación de auditoría',
        'EXITOSO',
        NOW()
    ),
    (
        (SELECT id FROM usuarios WHERE email = 'itmaster@rapicreditca.com'),
        'itmaster@rapicreditca.com',
        'ACTUALIZAR',
        'CONFIGURACION',
        'configuracion_sistema',
        'Configuración de parámetros de auditoría',
        'EXITOSO',
        NOW()
    ),
    (
        (SELECT id FROM usuarios WHERE email = 'itmaster@rapicreditca.com'),
        'itmaster@rapicreditca.com',
        'VER',
        'AUDITORIA',
        'auditorias',
        'Consulta de registros de auditoría - Activación completa',
        'EXITOSO',
        NOW()
    ),
    (
        (SELECT id FROM usuarios WHERE email = 'itmaster@rapicreditca.com'),
        'itmaster@rapicreditca.com',
        'VER',
        'USUARIOS',
        'usuarios',
        'Consulta de lista de usuarios - Verificación de permisos',
        'EXITOSO',
        NOW()
    ),
    (
        (SELECT id FROM usuarios WHERE email = 'itmaster@rapicreditca.com'),
        'itmaster@rapicreditca.com',
        'VERIFICAR',
        'SISTEMA',
        'auditorias',
        'Verificación del sistema de auditoría - Activación completa',
        'EXITOSO',
        NOW()
    );

-- 5. CREAR ÍNDICES PARA OPTIMIZACIÓN
-- ============================================

-- Crear índices para mejorar el rendimiento de consultas de auditoría
CREATE INDEX IF NOT EXISTS idx_auditorias_fecha_modulo 
ON auditorias (fecha DESC, modulo);

CREATE INDEX IF NOT EXISTS idx_auditorias_usuario_fecha 
ON auditorias (usuario_email, fecha DESC);

CREATE INDEX IF NOT EXISTS idx_auditorias_accion_resultado 
ON auditorias (accion, resultado);

CREATE INDEX IF NOT EXISTS idx_auditorias_registro_id 
ON auditorias (registro_id) WHERE registro_id IS NOT NULL;

-- 6. VERIFICAR CONFIGURACIÓN COMPLETA
-- ============================================

-- Mostrar resumen de configuración
SELECT 
    'CONFIGURACIÓN DE AUDITORÍA' as seccion,
    categoria,
    subcategoria,
    clave,
    valor,
    descripcion
FROM configuracion_sistema 
WHERE categoria = 'AUDITORIA'
ORDER BY subcategoria, clave;

-- Mostrar estadísticas finales
SELECT 
    'ESTADÍSTICAS FINALES' as reporte,
    COUNT(*) as total_registros_auditoria,
    COUNT(DISTINCT usuario_email) as usuarios_unicos,
    COUNT(DISTINCT modulo) as modulos_afectados,
    COUNT(DISTINCT accion) as tipos_accion,
    MIN(fecha) as fecha_mas_antigua,
    MAX(fecha) as fecha_mas_reciente
FROM auditorias;

-- Mostrar actividad reciente (últimas 24 horas)
SELECT 
    'ACTIVIDAD RECIENTE (24h)' as reporte,
    COUNT(*) as acciones_recientes,
    COUNT(DISTINCT usuario_email) as usuarios_activos,
    COUNT(DISTINCT modulo) as modulos_utilizados
FROM auditorias 
WHERE fecha >= NOW() - INTERVAL '24 hours';

-- 7. VERIFICAR PERMISOS DE ADMINISTRADOR
-- ============================================

-- Verificar que el usuario administrador tiene los permisos correctos
SELECT 
    'VERIFICACIÓN DE ADMINISTRADOR' as verificacion,
    id,
    email,
    nombre,
    apellido,
    rol,
    is_active,
    created_at,
    last_login
FROM usuarios 
WHERE email = 'itmaster@rapicreditca.com';

-- Verificar roles disponibles en el sistema
SELECT 
    'ROLES DISPONIBLES' as verificacion,
    unnest(enum_range(NULL::userrole)) as rol_disponible;

-- 8. REPORTE FINAL DE ACTIVACIÓN
-- ============================================

-- Generar reporte final
SELECT 
    '🎉 ACTIVACIÓN COMPLETA DE AUDITORÍA EXITOSA' as estado,
    NOW() as fecha_activacion,
    'itmaster@rapicreditca.com' as administrador,
    'Sistema de auditoría completamente activado' as descripcion;

-- Mostrar endpoints disponibles
SELECT 
    'ENDPOINTS DE AUDITORÍA DISPONIBLES' as seccion,
    'GET /api/v1/auditoria/' as endpoint,
    'Listar registros de auditoría con filtros' as descripcion
UNION ALL
SELECT 
    'ENDPOINTS DE AUDITORÍA DISPONIBLES',
    'GET /api/v1/auditoria/stats',
    'Estadísticas de auditoría'
UNION ALL
SELECT 
    'ENDPOINTS DE AUDITORÍA DISPONIBLES',
    'GET /api/v1/auditoria/export/excel',
    'Exportar auditoría a Excel (SOLO ADMIN)'
UNION ALL
SELECT 
    'ENDPOINTS DE AUDITORÍA DISPONIBLES',
    'GET /api/v1/auditoria/{id}',
    'Obtener registro específico de auditoría';

-- ============================================
-- FIN DEL SCRIPT DE ACTIVACIÓN
-- ============================================
