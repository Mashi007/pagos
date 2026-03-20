# Corrección masiva: `PAGADO` sin `cuota_pagos` (cola FIFO bloqueada)

## Hallazgo de causa raíz (código)

Varios endpoints en `backend/app/api/v1/endpoints/pagos.py` marcaban **`pago.estado = "PAGADO"`** aunque **`_aplicar_pago_a_cuotas_interno`** no creara filas en **`cuota_pagos`** (sin cupo en cuotas, préstamo ya cubierto por otros pagos, etc.):

| Flujo | Comportamiento anterior (incorrecto) |
|--------|----------------------------------------|
| `POST /pagos/guardar-fila-editable` | Insertaba el pago ya como **`PAGADO`** y luego aplicaba FIFO. |
| `POST` creación de pago, `PUT` actualización, lote JSON batch | Tras FIFO, **`PAGADO` siempre** si había `prestamo_id`, aunque **cc=cp=0**. |
| `POST /pagos/{id}/aplicar-cuotas` | Comentario explícito: PAGADO “aunque no hubiera cuotas pendientes”. |

**Corrección implementada:** función `_estado_pago_tras_aplicar_fifo(cc, cp)` — solo **`PAGADO`** si `cuotas_completadas > 0` o `cuotas_parciales > 0`; en caso contrario **`PENDIENTE`**.

Así se alinea el estado del pago con la existencia real de articulación en **`cuota_pagos`** y se reduce la cola “fantasma” que satura el job de 200 filas.

---

## Identificar el proceso del 21–22 feb 2026 (auditoría en BD)

Objetivo: saber **usuario**, **ventana horaria** y volumen para cruzar con despliegues / cargas.

```sql
-- Distribución por día y usuario_registro (ajusta fechas)
SELECT
  date_trunc('day', p.fecha_registro AT TIME ZONE 'America/Caracas') AS dia,
  COALESCE(NULLIF(trim(p.usuario_registro), ''), '(vacío)') AS usuario,
  COUNT(*) AS n,
  SUM(p.monto_pagado) AS suma_montos
FROM pagos p
WHERE p.fecha_registro >= '2026-02-21'
  AND p.fecha_registro < '2026-02-23'
  AND NOT EXISTS (SELECT 1 FROM cuota_pagos cp WHERE cp.pago_id = p.id)
  AND COALESCE(p.monto_pagado, 0) > 0
GROUP BY 1, 2
ORDER BY n DESC;
```

```sql
-- Misma cohorte “sin cupo aplicable” que usaste en diagnóstico (opcional)
-- (pega aquí el WHERE completo de pagos_sin_saldo_aplicable_en_cuotas)
```

Criterio de negocio: si el pico coincide con **email de servicio** o **usuario concreto**, acota el origen (Excel upload, tabla editable, API batch, etc.).

---

## Respaldo antes de corrección masiva

1. **Dump solo tabla `pagos`** (o full) en ventana de mantenimiento:

```bash
pg_dump "$DATABASE_URL" -t pagos --data-only --column-inserts -f backup_pagos_$(date +%F).sql
```

2. Opcional: tabla temporal con los IDs afectados:

```sql
CREATE TABLE backup_pagos_correccion_20260320 AS
SELECT p.*
FROM pagos p
WHERE /* mismos filtros que la corrección */;
```

---

## Criterios de negocio para la corrección (elegir UNA estrategia por cohorte)

| Estrategia | Cuándo usar | Acción SQL típica (ejemplo) |
|------------|-------------|-----------------------------|
| **A. Reclasificar estado** | El dinero es válido pero aún no hay cupo; no debe mostrarse como “pagado contable” hasta aplicar. | `UPDATE pagos SET estado = 'PENDIENTE' WHERE id IN (...)` |
| **B. Anular import** | Duplicado, error de carga, mismo comprobante dos veces. | `UPDATE pagos SET estado = 'ANULADO_IMPORT', notas = coalesce(notas,'') || ' ...' WHERE ...` |
| **C. Ajuste manual / otro concepto** | Sobrepago real; no va a cuotas del plan. | Documentar fuera de SQL o tabla de ajustes; no solo `PAGADO` en `pagos`. |

**No ejecutar** `UPDATE` masivo sin: respaldo, lista de IDs revisada y firma de negocio.

---

## Script SQL de plantilla (comentado)

Ver `sql/correccion_pagos_pagado_sin_aplicacion_template.sql`.

---

## Seguimiento

1. Desplegar backend con `_estado_pago_tras_aplicar_fifo`.
2. Corregir histórico con criterio A/B y respaldo.
3. Verificar KPIs y `GET /health` (integridad pagos/cuotas) si está habilitado.
4. Dejar el job `aplicar_pagos_pendientes` procesar primero pagos con cupo real (`PENDIENTE` con aplicación posible).
