-- ============================================================================
-- EXPLICACIÓN: CÓMO SE CALCULA LA MOROSIDAD
-- ============================================================================
-- Este documento explica de qué tablas y campos se toma la información
-- para calcular la morosidad en el sistema
--
-- Autor: Sistema de Pagos
-- Fecha: 2025
-- ============================================================================

-- ============================================================================
-- 📊 RESUMEN EJECUTIVO
-- ============================================================================
-- La morosidad se calcula sumando el monto_cuota de todas las cuotas que:
-- 1. ✅ Pertenecen a préstamos APROBADOS
-- 2. ✅ Tienen fecha_vencimiento menor a la fecha actual (vencidas)
-- 3. ✅ Tienen estado != 'PAGADO' (no pagadas)
-- 4. ✅ Se agrupan por mes y año de su fecha de vencimiento
--
-- ============================================================================

-- ============================================================================
-- 🗄️ TABLAS Y CAMPOS UTILIZADOS
-- ============================================================================

-- TABLA 1: cuotas (TABLA PRINCIPAL)
-- Ubicación: backend/app/models/amortizacion.py
-- Nombre SQL: cuotas
--
-- Campos utilizados:
--   ✅ prestamo_id      → Para hacer JOIN con tabla prestamos
--   ✅ fecha_vencimiento → Para filtrar cuotas vencidas y agrupar por mes
--   ✅ monto_cuota      → CAMPO CRÍTICO: Este es el valor que se SUMA
--   ✅ estado           → Para filtrar solo cuotas NO pagadas (estado != 'PAGADO')
--
-- Campos NO utilizados:
--   ❌ numero_cuota, fecha_pago, monto_capital, monto_interes
--   ❌ capital_pagado, interes_pagado, mora_pagada, total_pagado
--   ❌ capital_pendiente, interes_pendiente, dias_mora, monto_mora, tasa_mora

-- TABLA 2: prestamos (TABLA SECUNDARIA - Solo para filtros)
-- Ubicación: backend/app/models/prestamo.py
-- Nombre SQL: prestamos
--
-- Campos utilizados:
--   ✅ id               → Para hacer JOIN con cuotas.prestamo_id
--   ✅ estado           → Para filtrar solo préstamos APROBADOS (estado = 'APROBADO')
--
-- Campos opcionales (solo si se aplican filtros):
--   ⚠️ analista         → Filtro opcional por analista
--   ⚠️ concesionario   → Filtro opcional por concesionario
--   ⚠️ producto         → Filtro opcional por producto
--   ⚠️ modelo_vehiculo   → Filtro opcional por modelo

-- ============================================================================
-- 📝 QUERY SQL EXACTA DEL CÁLCULO
-- ============================================================================
-- Esta es la query que se ejecuta en el código (líneas 3405-3421 de dashboard.py)

SELECT 
    EXTRACT(YEAR FROM c.fecha_vencimiento)::int as año,
    EXTRACT(MONTH FROM c.fecha_vencimiento)::int as mes,
    COALESCE(SUM(c.monto_cuota), 0) as morosidad
FROM cuotas c
INNER JOIN prestamos p ON c.prestamo_id = p.id
WHERE 
    p.estado = 'APROBADO'                    -- Solo préstamos aprobados
    AND c.fecha_vencimiento >= :fecha_inicio  -- Desde fecha inicio (ej: 2024-08-01)
    AND c.fecha_vencimiento < :fecha_fin_total -- Hasta hoy (sin incluir)
    AND c.estado != 'PAGADO'                 -- Solo cuotas NO pagadas
GROUP BY 
    EXTRACT(YEAR FROM c.fecha_vencimiento), 
    EXTRACT(MONTH FROM c.fecha_vencimiento)
ORDER BY año, mes;

-- ============================================================================
-- 🔍 DESGLOSE DE LA QUERY
-- ============================================================================

-- 1. SELECT - Campos Extraídos:
--    ┌─────────────────────────────────────────────────────────────┐
--    │ EXTRACT(YEAR FROM c.fecha_vencimiento)::int as año          │
--    │ Tabla: cuotas (alias c)                                     │
--    │ Campo: fecha_vencimiento                                     │
--    │ Uso: Extraer año para agrupar                               │
--    └─────────────────────────────────────────────────────────────┘
--
--    ┌─────────────────────────────────────────────────────────────┐
--    │ EXTRACT(MONTH FROM c.fecha_vencimiento)::int as mes         │
--    │ Tabla: cuotas (alias c)                                     │
--    │ Campo: fecha_vencimiento                                    │
--    │ Uso: Extraer mes (1-12) para agrupar                       │
--    └─────────────────────────────────────────────────────────────┘
--
--    ┌─────────────────────────────────────────────────────────────┐
--    │ COALESCE(SUM(c.monto_cuota), 0) as morosidad                │
--    │ Tabla: cuotas (alias c)                                     │
--    │ Campo: monto_cuota ⭐⭐⭐ CAMPO CRÍTICO                        │
--    │ Uso: Suma todos los montos de cuotas que cumplen condiciones│
--    │ Resultado: Este es el valor final de morosidad por mes      │
--    └─────────────────────────────────────────────────────────────┘

-- 2. FROM - Tablas Consultadas:
--    ┌─────────────────────────────────────────────────────────────┐
--    │ FROM cuotas c                                                │
--    │ Tabla: cuotas                                                │
--    │ Alias: c                                                     │
--    │ Razón: Tabla principal donde están los datos de las cuotas   │
--    └─────────────────────────────────────────────────────────────┘
--
--    ┌─────────────────────────────────────────────────────────────┐
--    │ INNER JOIN prestamos p ON c.prestamo_id = p.id              │
--    │ Tabla: prestamos                                             │
--    │ Alias: p                                                     │
--    │ Join: cuotas.prestamo_id = prestamos.id                      │
--    │ Razón: Para acceder a los campos del préstamo (estado)       │
--    └─────────────────────────────────────────────────────────────┘

-- 3. WHERE - Condiciones (CRÍTICAS):
--    ┌─────────────────────────────────────────────────────────────┐
--    │ p.estado = 'APROBADO'                                       │
--    │ Tabla: prestamos                                             │
--    │ Campo: estado                                                │
--    │ Condición: Solo préstamos aprobados                          │
--    │ Razón: No contar préstamos en borrador, rechazados, etc.     │
--    └─────────────────────────────────────────────────────────────┘
--
--    ┌─────────────────────────────────────────────────────────────┐
--    │ c.fecha_vencimiento >= :fecha_inicio                         │
--    │ Tabla: cuotas                                                │
--    │ Campo: fecha_vencimiento                                    │
--    │ Condición: Desde fecha inicio (ej: 2024-08-01)              │
--    │ Razón: Limitar el rango de meses a mostrar                   │
--    └─────────────────────────────────────────────────────────────┘
--
--    ┌─────────────────────────────────────────────────────────────┐
--    │ c.fecha_vencimiento < :fecha_fin_total                       │
--    │ Tabla: cuotas                                                │
--    │ Campo: fecha_vencimiento                                    │
--    │ Condición: Hasta hoy (sin incluir)                           │
--    │ Razón: Solo cuotas que ya vencieron, no futuras              │
--    └─────────────────────────────────────────────────────────────┘
--
--    ┌─────────────────────────────────────────────────────────────┐
--    │ c.estado != 'PAGADO' ⭐⭐⭐ CONDICIÓN CRÍTICA                  │
--    │ Tabla: cuotas                                                │
--    │ Campo: estado                                               │
--    │ Condición: Solo cuotas NO pagadas                            │
--    │ Razón: Si la cuota está pagada, NO es morosidad              │
--    └─────────────────────────────────────────────────────────────┘

-- 4. GROUP BY - Agrupación:
--    ┌─────────────────────────────────────────────────────────────┐
--    │ GROUP BY EXTRACT(YEAR FROM c.fecha_vencimiento),            │
--    │          EXTRACT(MONTH FROM c.fecha_vencimiento)             │
--    │ Agrupa por: Año y mes de fecha_vencimiento                   │
--    │ Resultado: Un registro por cada mes/año con la suma            │
--    └─────────────────────────────────────────────────────────────┘

-- ============================================================================
-- 💡 EJEMPLO PRÁCTICO
-- ============================================================================
-- Supongamos que tenemos estas cuotas en la base de datos:
--
-- Prestamo ID: 1 (Estado: APROBADO)
--   Cuota 1: fecha_vencimiento = 2024-08-15, monto_cuota = 5000, estado = 'VENCIDA'
--   Cuota 2: fecha_vencimiento = 2024-09-15, monto_cuota = 5000, estado = 'VENCIDA'
--   Cuota 3: fecha_vencimiento = 2024-10-15, monto_cuota = 5000, estado = 'PAGADO'
--
-- Prestamo ID: 2 (Estado: APROBADO)
--   Cuota 1: fecha_vencimiento = 2024-08-20, monto_cuota = 7000, estado = 'VENCIDA'
--
-- Prestamo ID: 3 (Estado: PENDIENTE)  ← NO CUENTA (no está aprobado)
--   Cuota 1: fecha_vencimiento = 2024-08-10, monto_cuota = 3000, estado = 'VENCIDA'
--
-- Resultado de la query:
--   Año: 2024, Mes: 8 (Agosto)
--     - Cuota 1 Prestamo 1: 5000 (cumple: APROBADO, vencida, no pagada)
--     - Cuota 1 Prestamo 2: 7000 (cumple: APROBADO, vencida, no pagada)
--     - Cuota 1 Prestamo 3: NO CUENTA (préstamo no aprobado)
--     → Total Agosto 2024: 12000
--
--   Año: 2024, Mes: 9 (Septiembre)
--     - Cuota 2 Prestamo 1: 5000 (cumple: APROBADO, vencida, no pagada)
--     → Total Septiembre 2024: 5000
--
--   Año: 2024, Mes: 10 (Octubre)
--     - Cuota 3 Prestamo 1: NO CUENTA (está PAGADA)
--     → Total Octubre 2024: 0

-- ============================================================================
-- ⚠️ PUNTOS CRÍTICOS
-- ============================================================================
-- 1. ¿Qué es "Morosidad"?
--    Morosidad = Suma de montos de cuotas vencidas que NO están pagadas
--    ✅ Cuenta: Cuotas con estado != 'PAGADO' y fecha_vencimiento < hoy
--    ❌ No cuenta: Cuotas con estado = 'PAGADO' (aunque hayan vencido)
--    ❌ No cuenta: Cuotas con fecha_vencimiento >= hoy (aún no vencen)
--
-- 2. ¿Por qué se agrupa por mes de vencimiento?
--    Porque queremos ver cuánta morosidad se GENERÓ cada mes,
--    no cuánto se acumuló.
--
-- 3. ¿Por qué no se consulta tabla de cobros?
--    Porque la morosidad se determina ÚNICAMENTE por el estado de la cuota:
--    - Si cuota.estado = 'PAGADO' → No es morosidad
--    - Si cuota.estado != 'PAGADO' → Es morosidad
--    No importa si hay un registro de cobro en otra tabla.

-- ============================================================================
-- 📋 TABLAS QUE NO SE CONSULTAN
-- ============================================================================
-- ❌ pagos_staging   → No se usa para calcular morosidad
-- ❌ pagos           → No se usa para calcular morosidad
-- ❌ cobros          → No se usa para calcular morosidad
-- ❌ pago_cuotas     → No se usa para calcular morosidad
-- ❌ clientes        → No se usa para calcular morosidad
-- ❌ Cualquier otra tabla → No se usa

-- ============================================================================
-- ✅ RESUMEN FINAL
-- ============================================================================
-- Los datos se toman EXCLUSIVAMENTE de:
--
-- 1. ✅ Tabla cuotas:
--    - monto_cuota → Se SUMA (campo principal)
--    - fecha_vencimiento → Se usa para filtrar y agrupar
--    - estado → Se usa para filtrar (estado != 'PAGADO')
--
-- 2. ✅ Tabla prestamos:
--    - estado → Se usa para filtrar (estado = 'APROBADO')
--
-- El cálculo es DIRECTO y SIMPLE:
-- Solo suma montos de cuotas no pagadas, agrupadas por mes de vencimiento.

-- ============================================================================
-- FIN DEL DOCUMENTO
-- ============================================================================

