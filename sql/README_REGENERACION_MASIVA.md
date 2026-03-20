# Regeneración Masiva de Cuotas — Procedimiento Completo

## Resumen Ejecutivo

Este documento detalla el procedimiento operativo para regenerar la tabla de amortización (`cuotas`) según `fecha_aprobacion` y `modalidad_pago`, con aplicación automática de pagos bajo la política:

- **Tasa ≤ 0 %**: cuotas iguales
- **Tasa > 0 %**: sistema francés

**Resultado:** 5.150 préstamos, 62.491 cuotas regeneradas, 513.145,62 pagados, 100% consistencia.

---

## Prerequisitos

1. **Backup verificado**: `pg_dump -Fc` con `pg_restore -l` confirmado.
2. **Funciones creadas**: Ejecutar `sql/dbeaver_01_funciones_y_verificaciones.sql`:
   - `fn_add_months_keep_day(date, int)` — vencimiento ajustado por modalidad
   - `fn_monto_cuota_frances(capital, tasa_periódica, n)` — cuota sistema francés

3. **Permisos**: Usuario BD con permisos `DELETE`, `INSERT`, `UPDATE` en `prestamos`, `cuotas`, `cuota_pagos`.

---

## Fases del Procedimiento

### **Fase 1: Piloto (Validación en 3 Préstamos)**

**Objetivo:** Validar lógica antes de masivo.

**Archivos:**
- SQL: `sql/dbeaver_02_piloto_2_7_8.sql`
- Confirmación: `sql/dbeaver_03_piloto_2_7_8.sql`

**Pasos:**

1. **Ejecutar en DBeaver:**
   ```sql
   -- dbeaver_02_piloto_2_7_8.sql
   -- Regenera cuotas solo para prestamo_id IN (2, 7, 8)
   ```
   - Esperado: ~165 filas afectadas (borrado de viejas + inserción de nuevas)
   - Duración: < 10 segundos

2. **Aplicar pagos (Python):**
   ```bash
   cd backend
   python conciliar_amortizacion_masiva.py --ids 2,7,8
   ```
   - Esperado: ~24 pagos aplicados (9+5+10)

3. **Validar en DBeaver:**
   ```sql
   -- dbeaver_03_piloto_2_7_8.sql
   -- Comprueba §2–§4: alineación, conteo, duplicados
   ```
   - Esperado: 0 desalineados, 0 duplicados, 27 cuotas, 5.464 links

**Criterio de Éxito:**
- ✅ Cuota 1 alineada con `fecha_aprobacion` + modalidad
- ✅ Sin duplicados de `numero_cuota`
- ✅ Pagos aplicados sin error

---

### **Fase 2: Masivo (Todos los Préstamos Elegibles)**

**Objetivo:** Regenerar 5.150 préstamos con `fecha_aprobacion IS NOT NULL` y `numero_cuotas >= 1`.

**Archivos:**
- SQL: `sql/dbeaver_02_regeneracion_MASIVA.sql`
- Confirmación: `sql/dbeaver_05_confirmacion_global_post_masivo.sql`

**Pasos:**

1. **Ejecutar en DBeaver:**
   ```sql
   -- dbeaver_02_regeneracion_MASIVA.sql
   -- Regenera cuotas para TODOS los prestamos elegibles
   ```
   - Esperado: ~130.132 filas afectadas
   - Duración: ~1m 30s
   - **CRÍTICO:** Es una transacción `BEGIN...COMMIT`; si falla, no aplica

2. **Aplicar pagos (Python):**
   ```bash
   cd backend
   python conciliar_amortizacion_masiva.py
   ```
   - Procesará todos los préstamos con pagos pendientes
   - Esperado: ~9-15 minutos (5.150 préstamos)

3. **Validar global en DBeaver:**
   ```sql
   -- dbeaver_05_confirmacion_global_post_masivo.sql
   -- §1–§8: totales, alineación, estados, distribución
   ```
   - Esperado:
     - 62.491 cuotas
     - 0 desalineados
     - 5.150 completos
     - 513.145,62 pagados

**Criterio de Éxito:**
- ✅ Todas las secciones (§1–§8) sin anomalías
- ✅ 100% de cobertura (MENSUAL 59.599 + QUINCENAL 2.460 + SEMANAL 432)

---

### **Fase 3: Verificaciones de Integridad**

**Objetivo:** Auditar estados de préstamo y cobertura de cuotas.

**Archivos:**
- Estados: `sql/dbeaver_06_verificacion_estados_prestamos_CORREGIDO.sql`
- Cobertura: `sql/dbeaver_07_verificacion_cobertura_cuotas_CORREGIDO.sql`

**Pasos:**

1. **Verificar estados:**
   ```sql
   -- dbeaver_06_verificacion_estados_prestamos_CORREGIDO.sql
   -- §1–§5: distribución y anomalías por estado
   ```
   - Esperado: 5.081 APROBADO, 69 LIQUIDADO, 0 sin estado

2. **Verificar cobertura de cuotas:**
   ```sql
   -- dbeaver_07_verificacion_cobertura_cuotas_CORREGIDO.sql
   -- §1–§6: completitud y modalidades
   ```
   - Esperado: 5.150 completos, 0 parciales, 0 sin cuotas

**Criterio de Éxito:**
- ✅ 100% con estado válido
- ✅ 100% con cuotas completas

---

## Rollback (en caso de error)

Si el masivo falla **antes** del `COMMIT`, la transacción se revierte automáticamente. Si necesita deshacer manualmente:

```sql
-- Desde backup más reciente:
pg_restore -d pagos /ruta/a/backup_YYYYMMDD_HHMMSS.dump
```

---

## Monitoreo Post-Regeneración

### Alert 1: Cuotas sin `fecha_vencimiento` alineada

```sql
-- Ejecutar mensualmente
WITH p AS (
  SELECT
    pr.id AS prestamo_id,
    UPPER(COALESCE(NULLIF(TRIM(pr.modalidad_pago), ''), 'MENSUAL')) AS modalidad,
    pr.fecha_aprobacion::date AS fecha_aprob,
    c.fecha_vencimiento AS venc_actual
  FROM prestamos pr
  JOIN cuotas c ON c.prestamo_id = pr.id AND c.numero_cuota = 1
  WHERE pr.fecha_aprobacion IS NOT NULL AND pr.numero_cuotas >= 1
),
esp AS (
  SELECT
    p.*,
    CASE
      WHEN p.modalidad = 'MENSUAL' THEN fn_add_months_keep_day(p.fecha_aprob, 1)
      WHEN p.modalidad = 'QUINCENAL' THEN (p.fecha_aprob + 14 * INTERVAL '1 day')::date
      WHEN p.modalidad = 'SEMANAL' THEN (p.fecha_aprob + 6 * INTERVAL '1 day')::date
      ELSE fn_add_months_keep_day(p.fecha_aprob, 1)
    END AS venc_esperado
  FROM p
)
SELECT COUNT(*) FILTER (WHERE esp.venc_actual IS DISTINCT FROM esp.venc_esperado) AS desalineados
FROM esp;
-- Alerta si > 0
```

### Alert 2: Préstamos con `numero_cuotas` inconsistente

```sql
-- Ejecutar mensualmente
SELECT COUNT(*)
FROM prestamos p
LEFT JOIN cuotas c ON c.prestamo_id = p.id
WHERE p.numero_cuotas >= 1
GROUP BY p.id, p.numero_cuotas
HAVING COUNT(c.id) <> p.numero_cuotas;
-- Alerta si > 0
```

### Alert 3: Duplicados de `numero_cuota` por préstamo

```sql
-- Ejecutar mensualmente
SELECT COUNT(*)
FROM cuotas
GROUP BY prestamo_id, numero_cuota
HAVING COUNT(*) > 1;
-- Alerta si > 0
```

---

## Testing en QA (si aplica)

### Test 1: Flujo de pago completo (piloto 2,7,8)

1. **Acceder a app QA:**
   - Ir a "Módulo de Pagos" → "Préstamos"
   - Buscar préstamo ID 2 (debería tener 9 cuotas)

2. **Simular pago:**
   - Registrar un pago de 100 ECU en cuota 1
   - Verificar que `total_pagado` sube
   - Verificar que `estado` pasa a "PARCIALMENTE_PAGADO" o equivalente

3. **Verificar FIFO:**
   - No permitir pago en cuota 3 sin pagar primero cuotas 1 y 2
   - Verificar que aplicación respeta orden

4. **Validar reporte:**
   - Generar reporte de amortización
   - Comprobar que montos y fechas coinciden con BD

### Test 2: Performance

```bash
# Medir tiempo de conciliación
time python backend/conciliar_amortizacion_masiva.py --ids 2,7,8
# Esperado: < 30 segundos
```

---

## Troubleshooting

| Problema | Causa | Solución |
|----------|-------|----------|
| `column "X" does not exist` | Esquema BD distinto | Revisar `INFORMATION_SCHEMA.COLUMNS` |
| `BEGIN; COMMIT` falla a mitad | Constraint violation | Revisar logs de BD; ejecutar piloto primero |
| Pagos no se aplican (0 links) | `conciliar_amortizacion_masiva.py` no ejecutado | Correr script Python después del SQL |
| Cuota 1 desalineada | Modalidad no reconocida | Validar `prestamos.modalidad_pago` (MENSUAL, QUINCENAL, SEMANAL) |
| Montos cuota no cuadran | Tasa negativa o sistema francés mal configurado | Revisar `tasa_interes` en `prestamos` |

---

## Histórico de Ejecuciones

| Fecha | Fase | Préstamos | Cuotas | Pagos Aplicados | Estado |
|-------|------|-----------|--------|---|---|
| 2026-03-20 | Piloto (2,7,8) | 3 | 27 | 24 | ✅ Exitoso |
| 2026-03-20 | Masivo | 5.150 | 62.491 | 513.145,62 | ✅ Exitoso |

---

## Referencias

- **Funciones:** `sql/dbeaver_01_funciones_y_verificaciones.sql`
- **Script de conciliación:** `backend/conciliar_amortizacion_masiva.py`
- **Backup:** `scripts/backup_bd_opcion_a.py` o `scripts/backup_bd_opcion_a.ps1`
- **Política financiera:** Tasa ≤ 0 % → cuotas iguales; Tasa > 0 % → sistema francés

---

**Documentación actualizada:** 2026-03-20  
**Responsable:** Sistema Automático de Cuotas
