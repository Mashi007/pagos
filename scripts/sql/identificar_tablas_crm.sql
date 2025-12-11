-- =====================================================
-- SCRIPT PARA IDENTIFICAR TABLAS QUE APOYAN PROCESOS DE CRM
-- Customer Relationship Management
-- =====================================================
-- 
-- Este script identifica todas las tablas relacionadas con:
-- - Gestión de clientes
-- - Atención al cliente (tickets)
-- - Comunicaciones (WhatsApp, Email)
-- - Conversaciones con IA
-- - Notificaciones
-- - Embudo de ventas (préstamos)
-- - Seguimiento de pagos
--
-- Fecha: 2025-01-27
-- Compatible con DBeaver, pgAdmin y otros clientes SQL estándar
-- =====================================================

-- =====================================================
-- 1. TABLAS PRINCIPALES DE CRM
-- =====================================================
-- Ejecutar esta consulta para ver las tablas principales de CRM

SELECT 
    'clientes' as tabla,
    'Tabla principal de clientes - Información demográfica y de contacto' as descripcion,
    'CORE' as categoria,
    COUNT(*) as total_registros
FROM clientes
WHERE EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'clientes')

UNION ALL

SELECT 
    'tickets' as tabla,
    'Tickets de atención al cliente - Gestión de consultas, incidencias y reclamos' as descripcion,
    'ATENCION' as categoria,
    COUNT(*) as total_registros
FROM tickets
WHERE EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'tickets')

UNION ALL

SELECT 
    'conversaciones_whatsapp' as tabla,
    'Conversaciones de WhatsApp - Mensajes entre clientes y bot/sistema' as descripcion,
    'COMUNICACION' as categoria,
    COUNT(*) as total_registros
FROM conversaciones_whatsapp
WHERE EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'conversaciones_whatsapp')

UNION ALL

SELECT 
    'comunicaciones_email' as tabla,
    'Comunicaciones por Email - Emails recibidos y enviados' as descripcion,
    'COMUNICACION' as categoria,
    COUNT(*) as total_registros
FROM comunicaciones_email
WHERE EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'comunicaciones_email')

UNION ALL

SELECT 
    'conversaciones_ai' as tabla,
    'Conversaciones con IA - Interacciones con asistente virtual' as descripcion,
    'IA' as categoria,
    COUNT(*) as total_registros
FROM conversaciones_ai
WHERE EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'conversaciones_ai')

UNION ALL

SELECT 
    'notificaciones' as tabla,
    'Notificaciones - Recordatorios y alertas enviadas a clientes' as descripcion,
    'COMUNICACION' as categoria,
    COUNT(*) as total_registros
FROM notificaciones
WHERE EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'notificaciones')

UNION ALL

SELECT 
    'prestamos' as tabla,
    'Préstamos - Embudo de ventas y gestión de créditos' as descripcion,
    'VENTAS' as categoria,
    COUNT(*) as total_registros
FROM prestamos
WHERE EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'prestamos')

UNION ALL

SELECT 
    'pagos' as tabla,
    'Pagos - Seguimiento de pagos y cobranza' as descripcion,
    'COBRANZA' as categoria,
    COUNT(*) as total_registros
FROM pagos
WHERE EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'pagos')

ORDER BY categoria, tabla;

-- =====================================================
-- 2. RELACIONES ENTRE TABLAS CRM (Foreign Keys)
-- =====================================================
-- Ejecutar esta consulta para ver las relaciones entre tablas CRM

SELECT 
    tc.table_name as tabla_origen,
    kcu.column_name as columna_fk,
    ccu.table_name as tabla_destino,
    ccu.column_name as columna_referenciada,
    CASE 
        WHEN tc.table_name = 'clientes' THEN 'TABLA PRINCIPAL'
        WHEN tc.table_name IN ('tickets', 'conversaciones_whatsapp', 'comunicaciones_email', 
                               'conversaciones_ai', 'notificaciones') THEN 'COMUNICACION'
        WHEN tc.table_name IN ('prestamos', 'pagos') THEN 'NEGOCIO'
        ELSE 'OTRA'
    END as tipo_relacion
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
  ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu
  ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND (
    -- Tablas que referencian a clientes (CRM core)
    ccu.table_name = 'clientes'
    OR tc.table_name IN ('clientes', 'tickets', 'conversaciones_whatsapp', 
                         'comunicaciones_email', 'conversaciones_ai', 
                         'notificaciones', 'prestamos', 'pagos')
    -- Relaciones entre tablas CRM
    OR (tc.table_name = 'tickets' AND ccu.table_name IN ('conversaciones_whatsapp', 'comunicaciones_email'))
    OR (tc.table_name = 'conversaciones_whatsapp' AND ccu.table_name = 'tickets')
    OR (tc.table_name = 'comunicaciones_email' AND ccu.table_name = 'tickets')
  )
ORDER BY tabla_origen, tabla_destino;

-- =====================================================
-- 3. ESTADÍSTICAS DE USO DE CRM POR CLIENTE
-- =====================================================
-- Ejecutar esta consulta para ver estadísticas de uso por cliente

SELECT 
    c.id as cliente_id,
    c.cedula,
    c.nombres,
    COUNT(DISTINCT t.id) as total_tickets,
    COUNT(DISTINCT cw.id) as total_conversaciones_whatsapp,
    COUNT(DISTINCT ce.id) as total_comunicaciones_email,
    COUNT(DISTINCT ca.id) as total_conversaciones_ai,
    COUNT(DISTINCT n.id) as total_notificaciones,
    COUNT(DISTINCT p.id) as total_prestamos,
    COUNT(DISTINCT pg.id) as total_pagos
FROM clientes c
LEFT JOIN tickets t ON t.cliente_id = c.id
LEFT JOIN conversaciones_whatsapp cw ON cw.cliente_id = c.id
LEFT JOIN comunicaciones_email ce ON ce.cliente_id = c.id
LEFT JOIN conversaciones_ai ca ON ca.cliente_id = c.id
LEFT JOIN notificaciones n ON n.cliente_id = c.id
LEFT JOIN prestamos p ON p.cliente_id = c.id
LEFT JOIN pagos pg ON pg.cedula = c.cedula
GROUP BY c.id, c.cedula, c.nombres
HAVING 
    COUNT(DISTINCT t.id) > 0 
    OR COUNT(DISTINCT cw.id) > 0 
    OR COUNT(DISTINCT ce.id) > 0 
    OR COUNT(DISTINCT ca.id) > 0 
    OR COUNT(DISTINCT n.id) > 0
ORDER BY 
    (COUNT(DISTINCT t.id) + COUNT(DISTINCT cw.id) + COUNT(DISTINCT ce.id) + 
     COUNT(DISTINCT ca.id) + COUNT(DISTINCT n.id)) DESC
LIMIT 20;

-- =====================================================
-- 4. TABLAS RELACIONADAS (CATÁLOGOS Y CONFIGURACIÓN)
-- =====================================================
-- Ejecutar esta consulta para ver tablas de catálogo relacionadas

SELECT 
    t.tabla,
    t.descripcion,
    t.categoria
FROM (
    VALUES 
        ('concesionarios', 'Catálogo de concesionarios - Usado en préstamos', 'CATALOGO'),
        ('analistas', 'Catálogo de analistas - Usado en préstamos', 'CATALOGO'),
        ('modelos_vehiculos', 'Catálogo de modelos de vehículos - Usado en préstamos', 'CATALOGO'),
        ('users', 'Usuarios del sistema - Asignación de tickets y gestión', 'SISTEMA'),
        ('notificacion_plantillas', 'Plantillas de notificaciones - Templates para comunicaciones', 'CONFIGURACION')
) AS t(tabla, descripcion, categoria)
WHERE EXISTS (
    SELECT 1 FROM information_schema.tables 
    WHERE table_schema = 'public' AND table_name = t.tabla
)

ORDER BY categoria, tabla;

-- =====================================================
-- 5. RESUMEN DE TABLAS CRM Y SUS FUNCIONES
-- =====================================================
-- Ejecutar esta consulta para ver el resumen de funciones de cada tabla

SELECT 
    t.modulo,
    t.tabla,
    t.funcion
FROM (
    VALUES 
        ('GESTIÓN DE CLIENTES', 'clientes', 'Almacena información demográfica, de contacto y estado de clientes'),
        ('ATENCIÓN AL CLIENTE', 'tickets', 'Gestiona consultas, incidencias, reclamos y solicitudes de clientes'),
        ('COMUNICACIONES', 'conversaciones_whatsapp', 'Almacena conversaciones de WhatsApp entre clientes y sistema'),
        ('COMUNICACIONES', 'comunicaciones_email', 'Almacena emails recibidos y enviados a clientes'),
        ('COMUNICACIONES', 'notificaciones', 'Gestiona notificaciones automáticas (recordatorios, alertas)'),
        ('INTELIGENCIA ARTIFICIAL', 'conversaciones_ai', 'Almacena conversaciones con asistente virtual para análisis y mejora'),
        ('EMBUDO DE VENTAS', 'prestamos', 'Gestiona el ciclo de vida de préstamos desde solicitud hasta aprobación'),
        ('COBRANZA', 'pagos', 'Registra y gestiona pagos de clientes para seguimiento de cobranza')
) AS t(modulo, tabla, funcion)
WHERE EXISTS (
    SELECT 1 FROM information_schema.tables 
    WHERE table_schema = 'public' AND table_name = t.tabla
)

ORDER BY modulo, tabla;

-- =====================================================
-- 6. VERIFICAR EXISTENCIA DE TABLAS CRM
-- =====================================================
-- Ejecutar esta consulta para verificar qué tablas CRM existen

SELECT 
    table_name as tabla,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name = t.table_name
        ) THEN '✅ EXISTE'
        ELSE '❌ NO EXISTE'
    END as estado
FROM (
    VALUES 
        ('clientes'),
        ('tickets'),
        ('conversaciones_whatsapp'),
        ('comunicaciones_email'),
        ('conversaciones_ai'),
        ('notificaciones'),
        ('prestamos'),
        ('pagos')
) AS t(table_name)
ORDER BY estado DESC, tabla;

-- =====================================================
-- 7. ÍNDICES EN TABLAS CRM (Para optimización)
-- =====================================================
-- Ejecutar esta consulta para ver los índices en tablas CRM

SELECT 
    tablename as tabla,
    indexname as indice,
    indexdef as definicion
FROM pg_indexes
WHERE schemaname = 'public'
  AND tablename IN (
      'clientes', 'tickets', 'conversaciones_whatsapp', 
      'comunicaciones_email', 'conversaciones_ai', 
      'notificaciones', 'prestamos', 'pagos'
  )
ORDER BY tablename, indexname;

-- =====================================================
-- 8. ESTADÍSTICAS DE ACTIVIDAD CRM (Últimos 30 días)
-- =====================================================
-- Ejecutar esta consulta para ver estadísticas de actividad reciente

-- Nota: Si alguna tabla no existe, esa parte de la consulta fallará
-- Ejecuta la consulta 6 primero para verificar qué tablas existen

SELECT 
    'Tickets creados' as actividad,
    COUNT(*) as total,
    COUNT(DISTINCT cliente_id) as clientes_unicos
FROM tickets
WHERE creado_en >= NOW() - INTERVAL '30 days'

UNION ALL

SELECT 
    'Conversaciones WhatsApp' as actividad,
    COUNT(*) as total,
    COUNT(DISTINCT cliente_id) as clientes_unicos
FROM conversaciones_whatsapp
WHERE timestamp >= NOW() - INTERVAL '30 days'

UNION ALL

SELECT 
    'Comunicaciones Email' as actividad,
    COUNT(*) as total,
    COUNT(DISTINCT cliente_id) as clientes_unicos
FROM comunicaciones_email
WHERE timestamp >= NOW() - INTERVAL '30 days'

UNION ALL

SELECT 
    'Conversaciones IA' as actividad,
    COUNT(*) as total,
    COUNT(DISTINCT cliente_id) as clientes_unicos
FROM conversaciones_ai
WHERE creado_en >= NOW() - INTERVAL '30 days'

UNION ALL

SELECT 
    'Notificaciones enviadas' as actividad,
    COUNT(*) as total,
    COUNT(DISTINCT cliente_id) as clientes_unicos
FROM notificaciones
WHERE enviada_en >= NOW() - INTERVAL '30 days'

ORDER BY actividad;

-- =====================================================
-- FIN DEL SCRIPT
-- =====================================================
-- Todas las consultas han sido ejecutadas
-- Revisa los resultados de cada sección arriba

