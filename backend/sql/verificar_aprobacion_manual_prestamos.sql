-- =============================================================================
-- DBeaver: Verificación de tablas para APROBACIÓN MANUAL de préstamos
-- =============================================================================
-- El proceso anterior (Evaluar riesgo 7 criterios → Aprobar condiciones → Asignar
-- fecha) ha sido ELIMINADO y REEMPLAZADO por un único flujo: "Aprobar préstamo"
-- (riesgo manual): una fecha, datos editables, confirmación de documentos y
-- declaración de políticas. Estado resultante: APROBADO. Auditoría en tabla
-- auditoria (accion = APROBACION_MANUAL).
-- Ejecutar en DBeaver contra la BD del proyecto (PostgreSQL).
-- =============================================================================

-- 1) Columnas necesarias en PRESTAMOS para el nuevo flujo
-- -------------------------------------------------------
SELECT column_name, data_type, is_nullable
  FROM information_schema.columns
 WHERE table_schema = 'public'
   AND table_name = 'prestamos'
   AND column_name IN (
     'fecha_aprobacion',   -- Fecha de aprobación (y base amortización)
     'fecha_base_calculo', -- Misma fecha que aprobación para generar cuotas
     'usuario_aprobador',  -- Quién aprobó (email)
     'estado',             -- DRAFT | EN_REVISION | APROBADO | DESEMBOLSADO
     'total_financiamiento',
     'numero_cuotas',
     'modalidad_pago',
     'cuota_periodo',
     'tasa_interes',
     'observaciones'
   )
 ORDER BY ordinal_position;

-- 2) Tabla AUDITORIA (registro de aprobación manual)
-- -------------------------------------------------
SELECT column_name, data_type, is_nullable
  FROM information_schema.columns
 WHERE table_schema = 'public'
   AND table_name = 'auditoria'
 ORDER BY ordinal_position;

-- 3) Tabla CUOTAS (generada al aprobar; requiere saldo_capital_inicial, saldo_capital_final NOT NULL)
-- ------------------------------------------------------------------------------------------------
SELECT column_name, data_type, is_nullable
  FROM information_schema.columns
 WHERE table_schema = 'public'
   AND table_name = 'cuotas'
 ORDER BY ordinal_position;

-- 4) Conteo por estado (comprobar que no queden atascados en EVALUADO)
-- --------------------------------------------------------------------
SELECT estado, COUNT(*) AS cantidad
  FROM public.prestamos
 GROUP BY estado
 ORDER BY estado;

-- 5) Últimos registros de auditoría de tipo APROBACION_MANUAL
-- ------------------------------------------------------------
-- Tu tabla auditoria tiene: id, usuario_id, accion, entidad, entidad_id, detalles (NO descripcion), exito, fecha
SELECT id, usuario_id, accion, entidad, entidad_id, detalles, exito, fecha
  FROM public.auditoria
 WHERE accion = 'APROBACION_MANUAL'
 ORDER BY fecha DESC
 LIMIT 10;

-- 6) Préstamos con usuario_aprobador y fecha_aprobacion (ejemplos)
-- ----------------------------------------------------------------
SELECT id, estado, fecha_aprobacion, fecha_base_calculo, usuario_aprobador,
       total_financiamiento, numero_cuotas, modalidad_pago
  FROM public.prestamos
 WHERE usuario_aprobador IS NOT NULL
 ORDER BY id DESC
 LIMIT 5;


-- =============================================================================
-- OPCIONAL: Migrar préstamos en EVALUADO al nuevo flujo
-- (El nuevo flujo solo usa DRAFT y EN_REVISION para "Aprobar préstamo".)
-- =============================================================================
/*
UPDATE public.prestamos
   SET estado = 'EN_REVISION'
 WHERE estado = 'EVALUADO';
*/
