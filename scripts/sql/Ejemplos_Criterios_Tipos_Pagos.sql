-- ================================================================
-- EJEMPLOS: Criterios Aplicados a Diferentes Tipos de Pagos
-- ================================================================
-- Este script muestra ejemplos prácticos de cómo se aplican
-- los criterios según el tipo de pago
-- ================================================================

-- ================================================================
-- EJEMPLO 1: Pago Completo (Monto = Cuota)
-- ================================================================
-- Escenario: Cuota de $500, pago de $500
-- Criterios aplicados:
-- 1. Verificación de cédula
-- 2. Orden por fecha_vencimiento
-- 3. Aplicación completa
-- 4. Distribución proporcional capital/interés
-- 5. Estado: PAGADO (si conciliado) o PENDIENTE (si no conciliado)
SELECT 
    'EJEMPLO 1: Pago Completo' AS tipo_ejemplo,
    'Cuota: $500, Pago: $500' AS escenario,
    'Aplicación: $500 a cuota actual' AS aplicacion,
    'Estado: PAGADO (si conciliado)' AS estado_final;

-- ================================================================
-- EJEMPLO 2: Pago Parcial (Monto < Cuota)
-- ================================================================
-- Escenario: Cuota de $500, pago de $200
-- Criterios aplicados:
-- 1. Verificación de cédula
-- 2. Orden por fecha_vencimiento
-- 3. Aplicación parcial ($200)
-- 4. Distribución proporcional: ~$160 capital, ~$40 interés
-- 5. Estado: PARCIAL (si vencida) o PENDIENTE (si no vencida)
SELECT 
    'EJEMPLO 2: Pago Parcial' AS tipo_ejemplo,
    'Cuota: $500, Pago: $200' AS escenario,
    'Aplicación: $200 a cuota actual (proporcional)' AS aplicacion,
    'Estado: PARCIAL (vencida) o PENDIENTE (no vencida)' AS estado_final;

-- ================================================================
-- EJEMPLO 3: Pago Excesivo (Monto > Cuota)
-- ================================================================
-- Escenario: Cuota de $500, pago de $800
-- Criterios aplicados:
-- 1. Verificación de cédula
-- 2. Orden por fecha_vencimiento
-- 3. Aplicación: $500 a cuota actual, $300 a siguiente cuota
-- 4. Distribución proporcional en ambas cuotas
-- 5. Estado: Cuota actual PAGADO, siguiente ADELANTADO/PENDIENTE
SELECT 
    'EJEMPLO 3: Pago Excesivo' AS tipo_ejemplo,
    'Cuota: $500, Pago: $800' AS escenario,
    'Aplicación: $500 a cuota actual, $300 a siguiente cuota' AS aplicacion,
    'Estado: PAGADO (actual), ADELANTADO/PENDIENTE (siguiente)' AS estado_final;

-- ================================================================
-- EJEMPLO 4: Pago Múltiple (Varias cuotas)
-- ================================================================
-- Escenario: Pago de $1,500 para 3 cuotas de $500
-- Criterios aplicados:
-- 1. Verificación de cédula
-- 2. Orden por fecha_vencimiento
-- 3. Aplicación secuencial: $500 a cada cuota
-- 4. Distribución proporcional en cada cuota
-- 5. Estado: Todas PAGADO (si conciliadas)
SELECT 
    'EJEMPLO 4: Pago Múltiple' AS tipo_ejemplo,
    'Pago: $1,500, Cuotas: 3x $500' AS escenario,
    'Aplicación: $500 a cada cuota (secuencial)' AS aplicacion,
    'Estado: Todas PAGADO (si conciliadas)' AS estado_final;

-- ================================================================
-- EJEMPLO 5: Distribución Capital vs Interés
-- ================================================================
-- Escenario: Cuota con $400 capital pendiente, $100 interés pendiente
-- Pago de $200
-- Criterios aplicados:
-- 1. Total pendiente: $500
-- 2. Proporción capital: $400 / $500 = 80%
-- 3. Proporción interés: $100 / $500 = 20%
-- 4. Distribución: $160 capital, $40 interés
SELECT 
    'EJEMPLO 5: Distribución Capital/Interés' AS tipo_ejemplo,
    'Capital pendiente: $400, Interés pendiente: $100, Pago: $200' AS escenario,
    'Distribución: $160 capital (80%), $40 interés (20%)' AS aplicacion,
    'Proporción: Mantiene relación original capital/interés' AS estado_final;

-- ================================================================
-- EJEMPLO 6: Pago con Conciliación
-- ================================================================
-- Escenario: Cuota 100% pagada pero no conciliada
-- Criterios aplicados:
-- 1. total_pagado >= monto_cuota ✅
-- 2. Verificación de conciliación: NO todos conciliados ❌
-- 3. Estado: PENDIENTE (aunque esté pagada)
-- 4. Solo cambia a PAGADO cuando todos los pagos estén conciliados
SELECT 
    'EJEMPLO 6: Pago con Conciliación' AS tipo_ejemplo,
    'Cuota: 100% pagada pero no conciliada' AS escenario,
    'Estado: PENDIENTE (hasta que todos conciliados)' AS aplicacion,
    'Cambio a PAGADO: Solo cuando todos los pagos conciliados' AS estado_final;

-- ================================================================
-- RESUMEN: Criterios Aplicados a Todos los Tipos
-- ================================================================
SELECT 
    'CRITERIOS COMUNES' AS tipo,
    '1. Verificación de cédula' AS criterio,
    'El pago solo se aplica si cedula_pago == cedula_prestamo' AS descripcion
UNION ALL
SELECT 
    'CRITERIOS COMUNES',
    '2. Orden de aplicación',
    'Por fecha_vencimiento (más antigua primero), luego numero_cuota'
UNION ALL
SELECT 
    'CRITERIOS COMUNES',
    '3. Solo cuotas no pagadas',
    'Solo se aplican a cuotas con estado != "PAGADO"'
UNION ALL
SELECT 
    'CRITERIOS COMUNES',
    '4. Distribución proporcional',
    'Capital e interés se distribuyen según proporción pendiente'
UNION ALL
SELECT 
    'CRITERIOS COMUNES',
    '5. Actualización automática',
    'Estado y fecha_pago se actualizan automáticamente'
ORDER BY tipo, criterio;

