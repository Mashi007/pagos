-- Migration 021: Cleanup unused tables and consolidate database schema
-- Date: 2026-03-04
-- Purpose: Remove backup, temporary, testing, and obsolete tables to streamline the database
-- Result: 68 tables removed, 29 tables retained (core + support)

-- This migration documents the cleanup already executed:
-- - Removed all backup tables (26 tables)
-- - Removed all temporary/raw tables (15 tables)
-- - Removed all testing tables (7 tables)
-- - Removed all obsolete tables (20 tables)
-- - Removed unused views (2 views)

-- Retained tables (29 total):
-- Core: User, clientes, prestamos, cuotas, cuota_pagos, pagos, users, auditoria
-- Support: configuracion, modelo_vehiculos, tickets, pagos_whatsapp, conversacion_cobranza,
--          conversaciones_ai, mensaje_whatsapp, plantillas_notificacion, variables_notificacion,
--          definiciones_campos, diccionario_semantico, reporte_contable_cache, revisar_pagos,
--          revision_manual_prestamos, concesionarios, pagos_con_errores, pagos_informes,
--          notificacion_plantillas, notificacion_variables, conciliacion_temporal,
--          alembic_version

-- Cleanup already completed via direct SQL execution
-- This migration file serves as documentation and audit trail
SELECT 'Migration 021: Database cleanup completed successfully' AS status;
