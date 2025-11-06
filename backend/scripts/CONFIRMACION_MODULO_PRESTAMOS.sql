-- ============================================================================
-- CONFIRMACIÓN: MÓDULO PRÉSTAMOS - TABLAS Y CAMPOS UTILIZADOS
-- ============================================================================
-- Este documento confirma de qué tablas y campos toma datos el módulo de préstamos
--
-- Autor: Sistema de Pagos
-- Fecha: 2025
-- ============================================================================

-- ============================================================================
-- 📊 RESUMEN EJECUTIVO
-- ============================================================================
-- El módulo de préstamos consulta MÚLTIPLES tablas:
--
-- TABLA PRINCIPAL:
--   ✅ prestamos           → Tabla principal para todas las operaciones
--
-- TABLAS SECUNDARIAS:
--   ✅ clientes             → Para validar que el cliente existe
--   ✅ cuotas               → Para obtener cuotas del préstamo y calcular resúmenes
--   ✅ modelo_vehiculo      → Para validar modelo de vehículo
--   ✅ prestamos_auditoria  → Para registrar cambios y auditoría
--   ✅ prestamos_evaluacion → Para evaluaciones de riesgo (si existe)
--
-- ============================================================================

-- ============================================================================
-- 🗄️ TABLA 1: prestamos (TABLA PRINCIPAL)
-- ============================================================================
-- Ubicación del modelo: backend/app/models/prestamo.py
-- Nombre SQL: prestamos
-- Uso: Todas las operaciones CRUD del módulo

-- Campos utilizados:
--   ✅ id                       → PK, filtros
--   ✅ cliente_id               → FK a clientes.id
--   ✅ cedula                   → Búsqueda, filtros, JOIN con clientes
--   ✅ nombres                  → Búsqueda, visualización
--   ✅ total_financiamiento     → Cálculos, estadísticas, filtros
--   ✅ fecha_requerimiento     → Filtros por fecha
--   ✅ modalidad_pago           → Cálculo de cuotas, filtros
--   ✅ numero_cuotas            → Información, recálculo
--   ✅ cuota_periodo            → Información, recálculo
--   ✅ tasa_interes             → Cálculos, actualización
--   ✅ fecha_base_calculo       → Generación de amortización
--   ✅ producto                 → Filtros, visualización
--   ✅ producto_financiero      → Filtros (analista)
--   ✅ concesionario            → Filtros
--   ✅ analista                 → Filtros
--   ✅ modelo_vehiculo          → Filtros, validación
--   ✅ estado                   → Filtros, control de flujo
--   ✅ usuario_proponente       → Filtros, auditoría
--   ✅ usuario_aprobador        → Auditoría
--   ✅ usuario_autoriza         → Validaciones
--   ✅ observaciones            → Visualización, actualización
--   ✅ fecha_registro           → Filtros por fecha, ordenamiento
--   ✅ fecha_aprobacion         → Visualización, auditoría
--   ✅ fecha_actualizacion      → Auditoría

-- ============================================================================
-- 🗄️ TABLA 2: clientes (VALIDACIONES)
-- ============================================================================
-- Ubicación del modelo: backend/app/models/cliente.py
-- Nombre SQL: clientes
-- Uso: Validar que el cliente existe antes de crear un préstamo

-- Campos utilizados:
--   ✅ id                       → FK desde prestamos.cliente_id
--   ✅ cedula                   → Validación con prestamos.cedula
--   ✅ nombres                  → Copiar a prestamos.nombres

-- ============================================================================
-- 🗄️ TABLA 3: cuotas (CÁLCULOS Y RESUMENES)
-- ============================================================================
-- Ubicación del modelo: backend/app/models/amortizacion.py
-- Nombre SQL: cuotas
-- Uso: Obtener cuotas del préstamo, calcular saldos pendientes, cuotas en mora

-- Campos utilizados:
--   ✅ id                       → Contar cuotas
--   ✅ prestamo_id              → JOIN con prestamos.id
--   ✅ numero_cuota             → Ordenamiento
--   ✅ fecha_vencimiento        → Calcular cuotas en mora
--   ✅ estado                   → Filtrar cuotas pendientes
--   ✅ capital_pendiente        → Calcular saldo pendiente
--   ✅ interes_pendiente        → Calcular saldo pendiente
--   ✅ monto_mora               → Calcular saldo pendiente
--   ✅ total_pagado             → Calcular si está pagada
--   ✅ monto_cuota              → Validaciones

-- ============================================================================
-- 🗄️ TABLA 4: modelo_vehiculo (VALIDACIONES)
-- ============================================================================
-- Ubicación del modelo: backend/app/models/modelo_vehiculo.py
-- Nombre SQL: modelo_vehiculo
-- Uso: Validar que el modelo existe, está activo y tiene precio

-- Campos utilizados:
--   ✅ modelo                   → Validación con prestamos.modelo_vehiculo
--   ✅ activo                   → Solo modelos activos
--   ✅ precio                   → Verificar que tiene precio configurado

-- ============================================================================
-- 🗄️ TABLA 5: prestamos_auditoria (AUDITORÍA)
-- ============================================================================
-- Ubicación del modelo: backend/app/models/prestamo_auditoria.py
-- Nombre SQL: prestamos_auditoria
-- Uso: Registrar cambios y auditoría de préstamos

-- Campos utilizados:
--   ✅ prestamo_id              → FK a prestamos.id
--   ✅ cedula                   → Cédula del cliente
--   ✅ usuario                  → Usuario que hizo el cambio
--   ✅ campo_modificado         → Campo que cambió
--   ✅ valor_anterior           → Valor anterior
--   ✅ valor_nuevo              → Valor nuevo
--   ✅ accion                   → CREAR, EDITAR, ELIMINAR, CAMBIAR_ESTADO
--   ✅ estado_anterior          → Estado anterior (si cambió estado)
--   ✅ estado_nuevo             → Estado nuevo (si cambió estado)
--   ✅ observaciones            → Observaciones adicionales
--   ✅ fecha_cambio             → Fecha del cambio

-- ============================================================================
-- 🗄️ TABLA 6: prestamos_evaluacion (EVALUACIÓN DE RIESGO)
-- ============================================================================
-- Ubicación del modelo: backend/app/models/prestamo_evaluacion.py
-- Nombre SQL: prestamos_evaluacion
-- Uso: Almacenar evaluaciones de riesgo de préstamos

-- Campos utilizados:
--   ✅ prestamo_id              → FK a prestamos.id
--   ✅ puntuacion_total         → Puntuación de 100 puntos
--   ✅ clasificacion_riesgo     → BAJO, MEDIO, ALTO
--   ✅ decision_final           → APROBADO_AUTOMATICO, RECHAZADO, etc.
--   ✅ plazo_maximo             → Plazo máximo en meses
--   ✅ tasa_interes_aplicada    → Tasa de interés según evaluación
--   ✅ enganche_minimo          → Enganche mínimo requerido

-- ============================================================================
-- 📝 ENDPOINTS DEL MÓDULO PRÉSTAMOS Y SUS TABLAS
-- ============================================================================
-- Ubicación: backend/app/api/v1/endpoints/prestamos.py

-- ============================================================================
-- 1. GET /api/v1/prestamos/
-- ============================================================================
-- Descripción: Listar préstamos con filtros y paginación
-- Tablas consultadas:
--   ✅ prestamos (PRINCIPAL) → Para obtener la lista de préstamos

-- Query SQL equivalente:
SELECT 
    id, cliente_id, cedula, nombres,
    total_financiamiento, fecha_requerimiento, modalidad_pago,
    numero_cuotas, cuota_periodo, tasa_interes, fecha_base_calculo,
    producto, producto_financiero, concesionario, analista, modelo_vehiculo,
    estado, usuario_proponente, usuario_aprobador, usuario_autoriza,
    observaciones, fecha_registro, fecha_aprobacion, fecha_actualizacion
FROM prestamos
WHERE 
    (nombres ILIKE '%:search%' OR cedula ILIKE '%:search%' OR :search IS NULL)
    AND (estado = :estado OR :estado IS NULL)
    AND (cedula = :cedula OR :cedula IS NULL)
    AND (analista = :analista OR :analista IS NULL)
    AND (concesionario = :concesionario OR :concesionario IS NULL)
    AND (modelo_vehiculo = :modelo OR :modelo IS NULL)
    AND (fecha_registro >= :fecha_inicio OR :fecha_inicio IS NULL)
    AND (fecha_registro <= :fecha_fin OR :fecha_fin IS NULL)
ORDER BY fecha_registro DESC
LIMIT :per_page OFFSET :offset;

-- ============================================================================
-- 2. GET /api/v1/prestamos/stats
-- ============================================================================
-- Descripción: Obtener estadísticas de préstamos
-- Tablas consultadas:
--   ✅ prestamos (PRINCIPAL) → Para contar y sumar préstamos

-- Query SQL equivalente:
SELECT 
    COUNT(*) as total_prestamos,
    estado,
    COUNT(*) as cantidad_por_estado
FROM prestamos
GROUP BY estado;

SELECT COALESCE(SUM(total_financiamiento), 0) as total_financiado
FROM prestamos;

-- ============================================================================
-- 3. POST /api/v1/prestamos/
-- ============================================================================
-- Descripción: Crear nuevo préstamo
-- Tablas utilizadas:
--   ✅ clientes (VALIDACIÓN)     → Verificar que el cliente existe
--   ✅ modelo_vehiculo (VALIDACIÓN) → Verificar que el modelo existe y está activo
--   ✅ prestamos (INSERT)         → Insertar el nuevo préstamo
--   ✅ prestamos_auditoria (INSERT) → Registrar creación

-- Query SQL equivalente (validación cliente):
SELECT *
FROM clientes
WHERE cedula = :cedula;

-- Query SQL equivalente (validación modelo):
SELECT *
FROM modelo_vehiculo
WHERE modelo = :modelo_vehiculo
  AND activo = TRUE
  AND precio IS NOT NULL;

-- Query SQL equivalente (inserción):
INSERT INTO prestamos (
    cliente_id, cedula, nombres,
    total_financiamiento, fecha_requerimiento, modalidad_pago,
    numero_cuotas, cuota_periodo, tasa_interes, fecha_base_calculo,
    producto, producto_financiero, concesionario, analista, modelo_vehiculo,
    estado, usuario_proponente, usuario_autoriza, observaciones,
    fecha_registro, fecha_actualizacion
) VALUES (
    :cliente_id, :cedula, :nombres,
    :total_financiamiento, :fecha_requerimiento, :modalidad_pago,
    :numero_cuotas, :cuota_periodo, 0.00, NULL,
    :producto, :producto_financiero, :concesionario, :analista, :modelo_vehiculo,
    'DRAFT', :usuario_proponente, :usuario_autoriza, :observaciones,
    NOW(), NOW()
);

-- ============================================================================
-- 4. GET /api/v1/prestamos/{prestamo_id}
-- ============================================================================
-- Descripción: Obtener un préstamo por ID
-- Tablas consultadas:
--   ✅ prestamos (PRINCIPAL) → Para obtener el préstamo

-- Query SQL equivalente:
SELECT *
FROM prestamos
WHERE id = :prestamo_id;

-- ============================================================================
-- 5. PUT /api/v1/prestamos/{prestamo_id}
-- ============================================================================
-- Descripción: Actualizar préstamo existente
-- Tablas utilizadas:
--   ✅ prestamos (UPDATE)            → Actualizar el préstamo
--   ✅ prestamos_auditoria (INSERT)  → Registrar cambios
--   ✅ cuotas (UPDATE)               → Si se recalcula cuotas

-- Query SQL equivalente:
UPDATE prestamos
SET 
    total_financiamiento = :total_financiamiento,
    modalidad_pago = :modalidad_pago,
    numero_cuotas = :numero_cuotas,
    cuota_periodo = :cuota_periodo,
    tasa_interes = :tasa_interes,
    fecha_base_calculo = :fecha_base_calculo,
    observaciones = :observaciones,
    fecha_actualizacion = NOW()
WHERE id = :prestamo_id;

-- ============================================================================
-- 6. DELETE /api/v1/prestamos/{prestamo_id}
-- ============================================================================
-- Descripción: Eliminar préstamo (hard delete)
-- Tablas utilizadas:
--   ✅ prestamos (DELETE)            → Eliminar el préstamo
--   ✅ prestamos_auditoria (INSERT)  → Registrar eliminación

-- Query SQL equivalente:
DELETE FROM prestamos
WHERE id = :prestamo_id;

-- ============================================================================
-- 7. GET /api/v1/prestamos/cedula/{cedula}
-- ============================================================================
-- Descripción: Buscar préstamos por cédula del cliente
-- Tablas consultadas:
--   ✅ prestamos (PRINCIPAL) → Para buscar préstamos por cédula

-- Query SQL equivalente:
SELECT 
    id, producto, total_financiamiento, estado, fecha_registro
FROM prestamos
WHERE cedula = :cedula;

-- ============================================================================
-- 8. GET /api/v1/prestamos/cedula/{cedula}/resumen
-- ============================================================================
-- Descripción: Obtener resumen de préstamos del cliente (saldo, cuotas en mora)
-- Tablas consultadas:
--   ✅ prestamos (PRINCIPAL) → Para obtener préstamos del cliente
--   ✅ cuotas (SECUNDARIA)   → Para calcular saldos y cuotas en mora

-- Query SQL equivalente:
SELECT *
FROM prestamos
WHERE cedula = :cedula;

SELECT *
FROM cuotas
WHERE prestamo_id = :prestamo_id;

-- Cálculo de saldo pendiente:
SELECT 
    COALESCE(SUM(capital_pendiente + interes_pendiente + monto_mora), 0) as saldo_pendiente,
    COUNT(*) FILTER (
        WHERE fecha_vencimiento < CURRENT_DATE 
        AND estado != 'PAGADO'
    ) as cuotas_en_mora
FROM cuotas
WHERE prestamo_id = :prestamo_id;

-- ============================================================================
-- 9. GET /api/v1/prestamos/{prestamo_id}/cuotas
-- ============================================================================
-- Descripción: Obtener cuotas de un préstamo
-- Tablas consultadas:
--   ✅ cuotas (PRINCIPAL) → Para obtener las cuotas del préstamo

-- Query SQL equivalente:
SELECT *
FROM cuotas
WHERE prestamo_id = :prestamo_id
ORDER BY numero_cuota ASC;

-- ============================================================================
-- 10. POST /api/v1/prestamos/{prestamo_id}/generar-amortizacion
-- ============================================================================
-- Descripción: Generar tabla de amortización (cuotas) para un préstamo
-- Tablas utilizadas:
--   ✅ prestamos (SELECT)            → Obtener datos del préstamo
--   ✅ cuotas (INSERT)               → Crear las cuotas de amortización

-- Query SQL equivalente:
SELECT *
FROM prestamos
WHERE id = :prestamo_id;

-- Generación de cuotas (múltiples INSERT):
INSERT INTO cuotas (
    prestamo_id, numero_cuota, fecha_vencimiento,
    monto_cuota, monto_capital, monto_interes,
    saldo_capital_inicial, saldo_capital_final,
    capital_pendiente, interes_pendiente,
    estado
) VALUES (
    :prestamo_id, :numero_cuota, :fecha_vencimiento,
    :monto_cuota, :monto_capital, :monto_interes,
    :saldo_capital_inicial, :saldo_capital_final,
    :capital_pendiente, :interes_pendiente,
    'PENDIENTE'
);

-- ============================================================================
-- 11. POST /api/v1/prestamos/{prestamo_id}/evaluar-riesgo
-- ============================================================================
-- Descripción: Evaluar riesgo de un préstamo
-- Tablas utilizadas:
--   ✅ prestamos (SELECT)            → Obtener datos del préstamo
--   ✅ prestamos_evaluacion (INSERT) → Guardar evaluación de riesgo
--   ✅ prestamos (UPDATE)            → Actualizar estado a EVALUADO

-- Query SQL equivalente:
SELECT *
FROM prestamos
WHERE id = :prestamo_id;

INSERT INTO prestamos_evaluacion (
    prestamo_id, puntuacion_total, clasificacion_riesgo,
    decision_final, plazo_maximo, tasa_interes_aplicada,
    enganche_minimo, fecha_evaluacion
) VALUES (
    :prestamo_id, :puntuacion_total, :clasificacion_riesgo,
    :decision_final, :plazo_maximo, :tasa_interes_aplicada,
    :enganche_minimo, NOW()
);

UPDATE prestamos
SET estado = 'EVALUADO'
WHERE id = :prestamo_id;

-- ============================================================================
-- 12. POST /api/v1/prestamos/{prestamo_id}/aplicar-condiciones-aprobacion
-- ============================================================================
-- Descripción: Aplicar condiciones de aprobación (después de evaluación)
-- Tablas utilizadas:
--   ✅ prestamos (UPDATE)            → Actualizar condiciones y estado
--   ✅ cuotas (UPDATE/DELETE/INSERT) → Recalcular cuotas según plazo máximo
--   ✅ prestamos_auditoria (INSERT)  → Registrar aprobación

-- Query SQL equivalente:
UPDATE prestamos
SET 
    numero_cuotas = :numero_cuotas,
    cuota_periodo = :cuota_periodo,
    tasa_interes = :tasa_interes,
    fecha_base_calculo = :fecha_base_calculo,
    estado = 'APROBADO',
    usuario_aprobador = :usuario_aprobador,
    fecha_aprobacion = NOW(),
    fecha_actualizacion = NOW()
WHERE id = :prestamo_id;

-- Eliminar cuotas antiguas y crear nuevas (si se recalcula):
DELETE FROM cuotas
WHERE prestamo_id = :prestamo_id;

-- Insertar nuevas cuotas recalculadas...

-- ============================================================================
-- 13. GET /api/v1/prestamos/auditoria/{prestamo_id}
-- ============================================================================
-- Descripción: Obtener historial de auditoría de un préstamo
-- Tablas consultadas:
--   ✅ prestamos_auditoria (PRINCIPAL) → Para obtener historial de cambios

-- Query SQL equivalente:
SELECT *
FROM prestamos_auditoria
WHERE prestamo_id = :prestamo_id
ORDER BY fecha_cambio DESC
LIMIT :per_page OFFSET :offset;

-- ============================================================================
-- ⚠️ RELACIONES ENTRE TABLAS
-- ============================================================================
-- 
-- prestamos → clientes:
--   prestamos.cliente_id = clientes.id
--   prestamos.cedula = clientes.cedula
--
-- prestamos → cuotas:
--   cuotas.prestamo_id = prestamos.id
--
-- prestamos → prestamos_auditoria:
--   prestamos_auditoria.prestamo_id = prestamos.id
--
-- prestamos → prestamos_evaluacion:
--   prestamos_evaluacion.prestamo_id = prestamos.id
--
-- prestamos → modelo_vehiculo:
--   prestamos.modelo_vehiculo = modelo_vehiculo.modelo

-- ============================================================================
-- ✅ RESUMEN FINAL
-- ============================================================================
-- El módulo de préstamos consulta las siguientes tablas:
--
-- Tabla principal:
--   ⭐ prestamos           → Todas las operaciones CRUD
--
-- Tablas secundarias:
--   ⭐ clientes            → Validaciones
--   ⭐ cuotas              → Cálculos y resúmenes
--   ⭐ modelo_vehiculo     → Validaciones
--   ⭐ prestamos_auditoria → Auditoría
--   ⭐ prestamos_evaluacion → Evaluaciones de riesgo
--
-- Endpoints y sus tablas principales:
--   ✅ GET /api/v1/prestamos/                          → prestamos
--   ✅ GET /api/v1/prestamos/stats                     → prestamos
--   ✅ POST /api/v1/prestamos/                         → prestamos + clientes + modelo_vehiculo
--   ✅ GET /api/v1/prestamos/{id}                      → prestamos
--   ✅ PUT /api/v1/prestamos/{id}                      → prestamos + cuotas
--   ✅ DELETE /api/v1/prestamos/{id}                   → prestamos
--   ✅ GET /api/v1/prestamos/cedula/{cedula}           → prestamos
--   ✅ GET /api/v1/prestamos/cedula/{cedula}/resumen    → prestamos + cuotas
--   ✅ GET /api/v1/prestamos/{id}/cuotas               → cuotas
--   ✅ POST /api/v1/prestamos/{id}/generar-amortizacion → prestamos + cuotas
--   ✅ POST /api/v1/prestamos/{id}/evaluar-riesgo      → prestamos + prestamos_evaluacion
--   ✅ POST /api/v1/prestamos/{id}/aplicar-condiciones → prestamos + cuotas
--   ✅ GET /api/v1/prestamos/auditoria/{id}            → prestamos_auditoria
--
-- ============================================================================
-- FIN DEL DOCUMENTO
-- ============================================================================

