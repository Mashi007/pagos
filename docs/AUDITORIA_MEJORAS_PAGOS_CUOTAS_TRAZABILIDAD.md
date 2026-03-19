# Auditoría: mejoras pagos, cuotas y trazabilidad

**Fecha:** 2026-03-18  
**Alcance:** Autoconciliación, integración pagos→cuotas, trazabilidad `cuota_pagos`, backfill y verificaciones SQL.

---

## 1. Mejoras ya implementadas (verificadas)

### 1.1 Autoconciliación en todas las formas de carga de pagos

| Origen del pago | Archivo / endpoint | ¿Conciliado + fecha + verificado? |
|-----------------|-------------------|------------------------------------|
| POST `/pagos` (crear) | `pagos.py` | ✅ Backend y front envían `conciliado`; si hay `prestamo_id` se marca conciliado |
| POST `/pagos/batch` | `pagos.py` | ✅ Por fila con `prestamo_id` |
| POST `/pagos/upload` (Excel) | `pagos.py` ~L779-792 | ✅ `conciliado=True`, `fecha_conciliacion`, `verificado_concordancia="SI"` |
| POST `/pagos/importar-desde-cobros` | `pagos.py` ~L1095-1112 | ✅ Idem |
| Conciliación por documento | `pagos.py` | ✅ Marca conciliado y aplica a cuotas |
| Cobros: aprobar reportado | `cobros.py` | ✅ Crea pago con conciliado y aplica a cuotas |
| Guardar fila editable (tabla) | `pagos.py` | ✅ Asigna conciliado/fecha/verificado |

**Conclusión:** Todas las formas de ingreso de pagos en `/pagos/pagos` marcan conciliado cuando corresponde.

---

### 1.2 Integración automática de pagos conciliados a cuotas

| Mecanismo | Dónde | Estado |
|-----------|--------|--------|
| En el mismo request (al crear pago) | `_aplicar_pago_a_cuotas_interno` en upload, batch, crear, importar-cobros, conciliación, cobros aprobar | ✅ |
| Al consultar cuotas del préstamo | `get_cuotas_prestamo` → `aplicar_pagos_pendientes_prestamo` | ✅ |
| Endpoint explícito masivo | POST `/prestamos/conciliar-amortizacion-masiva` | ✅ |
| Revisión manual | Tras marcar conciliado → `aplicar_pagos_pendientes_prestamo` | ✅ |

**No existe:** job/cron que ejecute periódicamente la integración para todos los préstamos (solo al abrir préstamo o al llamar al endpoint masivo).

---

### 1.3 Trazabilidad: tabla `cuota_pagos` y orden FIFO

- **Tabla:** `cuota_pagos` (cuota_id, pago_id, monto_aplicado, fecha_aplicacion, orden_aplicacion, es_pago_completo). ✅
- **Orden:** FIFO por `numero_cuota`; `orden_aplicacion` 0, 1, 2… por pago. ✅
- **Verificaciones SQL:** `sql/verificar_trazabilidad_pagos_cuotas_prestamos.sql` (resumen, integridad pago/cuota, orden, cadena, por préstamo). ✅

---

### 1.4 Scripts SQL de verificación

| Archivo | Propósito |
|---------|-----------|
| `sql/verificar_pagos_conciliados.sql` | Total conciliados / no conciliados |
| `sql/verificar_pagos_integrados_cuotas.sql` | Pagos con préstamo y monto: cuántos tienen al menos una fila en `cuota_pagos`; listado no integrados; desfase monto; por préstamo |
| `sql/verificar_trazabilidad_pagos_cuotas_prestamos.sql` | Resumen trazabilidad, integridad pago/cuota, orden FIFO, cadena pago→cuota→préstamo, por préstamo |
| `sql/backfill_cuota_pagos.sql` | Conteo e INSERT para rellenar `cuota_pagos` desde cuotas legacy (total_pagado + pago_id). ✅ Ejecutado: 2050 filas insertadas |

---

### 1.5 Backfill de trazabilidad (ejecutado)

- **Reglas:** Solo cuotas con `total_pagado > 0`, `pago_id NOT NULL` y sin filas en `cuota_pagos`; una fila por cuota; idempotente.
- **Herramientas:** `sql/backfill_cuota_pagos.sql` y `backend/scripts/backfill_cuota_pagos.py` (--dry-run, --limit).
- **Resultado:** 2050 filas insertadas. Consulta 2 (integridad por pago) mostró: mayoría de pagos con 0 en `cuota_pagos` (ninguna cuota los tiene en `pago_id`); 2 pagos con suma > monto (31440, 31698) por doble asignación legacy.

---

## 2. Mejoras pendientes o opcionales

### 2.1 Prioridad alta / consistencia

| Mejora | Descripción | Dónde / cómo |
|--------|-------------|--------------|
| **Corregir 2 pagos con desfase negativo** | pago_id 31440 (monto 57, suma 114) y 31698 (monto 100, suma 200): dos cuotas con el mismo pago_id; ajustar `monto_aplicado` en una fila por pago para que la suma = monto_pagado. | SQL de UPDATE puntual en `cuota_pagos` (ej. dejar en la fila de menor id el monto real y en la otra 0, o repartir). |
| **Pagos con error → normales** | Al mover de `pagos_con_errores` a `pagos`, si `row.conciliado` es True no se setean `fecha_conciliacion` ni `verificado_concordancia`. | En `pagos_con_errores.py` en `mover_a_pagos_normales`: si `row.conciliado`, asignar `fecha_conciliacion=now`, `verificado_concordancia="SI"` al crear el `Pago`. |

### 2.2 Prioridad media

| Mejora | Descripción |
|--------|-------------|
| **Health /integrity: indicador de trazabilidad** | Añadir en `GET /health/integrity` un contador opcional: pagos con prestamo_id y monto > 0 sin ninguna fila en `cuota_pagos` (para monitoreo). |
| **Job periódico de integración** | Cron o tarea en el scheduler que llame a la lógica de “conciliar amortización masiva” (aplicar pagos conciliados pendientes a cuotas) para todos los préstamos con pagos sin `cuota_pagos`, por ejemplo una vez al día. |

### 2.3 Prioridad baja / operativa

| Mejora | Descripción |
|--------|-------------|
| **Scripts SQL en cron/CI** | Ejecutar periódicamente (cron o CI) los SQL de verificación (`verificar_pagos_conciliados`, `verificar_pagos_integrados_cuotas`, `verificar_trazabilidad_...`) y alertar si hay indicadores en rojo (p. ej. muchos no conciliados o muchos sin trazabilidad). Ver `docs/MEJORAS_PROPUESTAS.md` §7. |
| **Origen de creación del pago** | Campo o auditoría: `origen_creacion` (formulario, batch_excel, importar_cobros, cobros_aprobar, etc.) para depuración. Ver `docs/MEJORAS_PROPUESTAS.md` §8. |
| **Runbook / documentación** | Breve guía: “Cómo verificar que todos los pagos están conciliados/integrados/trazabilidad”, enlazando a los SQL y al endpoint de conciliación masiva. Ver `docs/MEJORAS_PROPUESTAS.md` §10. |

---

## 3. Resumen

- **Implementado y verificado:** Autoconciliación en todos los flujos de carga, integración a cuotas (en request + al abrir préstamo + endpoint masivo), trazabilidad en `cuota_pagos` con FIFO, SQL de verificación y backfill ejecutado (2050 filas).
- **Pendiente recomendado:** Corrección de los 2 pagos con doble asignación (31440, 31698); completar `fecha_conciliacion`/`verificado_concordancia` al mover desde pagos_con_errores cuando conciliado=True.
- **Opcional:** Indicador de trazabilidad en health, job diario de integración, scripts SQL en cron/alertas, origen de creación, runbook.
