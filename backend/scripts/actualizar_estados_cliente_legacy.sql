-- =============================================================================
-- Script para actualizar estados de cliente en DBeaver
-- Ejecutar en la base de datos de RapiCredit
-- =============================================================================
-- Estados válidos: ACTIVO, INACTIVO, FINALIZADO, LEGACY
-- Este script corrige valores incorrectos o legacy en clientes.estado
-- =============================================================================

-- 1. DIAGNÓSTICO: Ver qué valores distintos existen actualmente
SELECT estado, COUNT(*) AS cantidad
FROM clientes
GROUP BY estado
ORDER BY estado;

-- 2. ACTUALIZAR valores incorrectos conocidos
-- "A" -> ACTIVO (si era abreviatura)
UPDATE clientes SET estado = 'ACTIVO' WHERE estado = 'A';

-- "F" -> FINALIZADO (si era abreviatura)
UPDATE clientes SET estado = 'FINALIZADO' WHERE estado = 'F';

-- "I" -> INACTIVO (si era abreviatura)
UPDATE clientes SET estado = 'INACTIVO' WHERE estado = 'I';

-- 3. MARCAR COMO LEGACY cualquier valor que no sea los 4 válidos
UPDATE clientes
SET estado = 'LEGACY'
WHERE estado NOT IN ('ACTIVO', 'INACTIVO', 'FINALIZADO', 'LEGACY');

-- NOTA: Ejecutar primero backend/scripts/crear_estados_cliente.sql para crear la tabla estados_cliente

-- 4. VERIFICACIÓN: Confirmar que solo quedan valores válidos
SELECT estado, COUNT(*) AS cantidad
FROM clientes
GROUP BY estado
ORDER BY estado;
