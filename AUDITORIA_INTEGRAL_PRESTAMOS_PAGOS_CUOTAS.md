# Auditoría integral: Módulos Préstamos, Pagos y Cuotas

**Fecha:** 22 de febrero de 2026  
**Alcance:** Integración entre préstamos, pagos, cuotas, carga masiva y conciliación.

---

## 1. Estructura del proyecto

| Capa | Ubicación | Componentes clave |
|------|-----------|-------------------|
| **Backend** | `backend/app/` | FastAPI, SQLAlchemy |
| **Modelos** | `app/models/` | `pago.py`, `cuota.py`, `prestamo.py`, `cliente.py` |
| **Endpoints** | `app/api/v1/endpoints/` | `pagos.py`, `prestamos.py` |
| **Frontend** | `frontend/src/` | React, Vite |
| **Carga masiva** | `hooks/useExcelUploadPagos.ts`, `components/pagos/ExcelUploaderPagosUI.tsx` | Excel → preview → guardado individual |

---

## 2. Modelo de datos y relaciones

```
Cliente (1) ──< Prestamo (N)
                    │
                    ├──< Cuota (N)  [prestamo_id, pago_id]
                    │
Pago (N) ───────────┘  [prestamo_id, cedula_cliente]
```

- **Pago** → **Prestamo**: `pago.prestamo_id` (nullable)
- **Cuota** → **Pago**: `cuota.pago_id` (nullable) — vincula cuota con el pago que la cubrió
- **Cuota** → **Prestamo**: `cuota.prestamo_id` (obligatorio)

---

## 3. Reglas de negocio existentes

### 3.1 Función `_aplicar_pago_a_cuotas_interno` (pagos.py)

**Ubicación:** `backend/app/api/v1/endpoints/pagos.py` líneas ~677-724

**Lógica:**
1. Cuotas pendientes: `fecha_pago IS NULL` y `total_pagado < monto`
2. Orden: `numero_cuota` ascendente (FIFO por cuota)
3. Distribución: aplica el monto del pago a cuotas en orden hasta agotar
4. Actualiza: `total_pagado`, `pago_id`, `fecha_pago`, `estado` en cada cuota
5. Estados de cuota: `PAGADO` (100% cubierta), `PAGO_ADELANTADO` o `PENDIENTE` (parcial)

**Criterio:** FIFO por préstamo (primera cuota pendiente primero). No usa cédula explícitamente; la cédula se usa para identificar cliente/préstamo.

### 3.2 Dónde se invocan las reglas

| Acción | ¿Aplica a cuotas? | Observación |
|--------|-------------------|-------------|
| **POST /pagos** (crear_pago) | ✅ Sí | Solo si `conciliado=True` y `prestamo_id` y `monto > 0` |
| **POST /pagos/{id}/aplicar-cuotas** | ✅ Sí | Endpoint manual |
| **PUT /pagos/{id}** (actualizar_pago) | ❌ No | Aunque se cambie `conciliado` a True |
| **POST /pagos/upload** (carga masiva backend) | ❌ No | No setea `conciliado`, no aplica a cuotas |
| **POST /pagos/conciliacion/upload** | ❌ No | Solo marca `conciliado=True`, no aplica a cuotas |

---

## 4. Carga masiva: dos flujos distintos

### 4.1 Frontend (Excel → guardado individual)

**Flujo:** `useExcelUploadPagos` → `saveIndividualPago` → `pagoService.createPago` → **POST /pagos**

- Usa **POST /pagos** (crear_pago) por cada fila válida
- Envía `conciliado` (por defecto `true` si no viene "NO" en Excel)
- Si `conciliado=true` y `prestamo_id` existe → **sí se aplican las reglas de negocio**

### 4.2 Backend (upload directo)

**Flujo:** `POST /pagos/upload` → inserta directamente en BD

- No setea `conciliado` (queda `NULL` o `False`)
- No llama a `_aplicar_pago_a_cuotas_interno`
- Los pagos quedan sin asignar a cuotas

### 4.3 Conciliación por archivo

**Flujo:** `POST /pagos/conciliacion/upload` → busca por `numero_documento` → `conciliado=True`

- Solo actualiza `conciliado` y `fecha_conciliacion`
- No aplica a cuotas

---

## 5. Gaps e inconsistencias

### 5.1 Críticos

| # | Gap | Impacto |
|---|-----|---------|
| 1 | **Carga masiva backend** (`POST /upload`) no aplica reglas de negocio | Pagos cargados por este endpoint nunca se asignan a cuotas |
| 2 | **Conciliación por archivo** no aplica a cuotas | Pagos marcados conciliados no se vinculan a cuotas |
| 3 | **Actualizar pago** (PUT) al cambiar `conciliado` a True no aplica a cuotas | Conciliación manual desde formulario no dispara asignación |

### 5.2 Importantes

| # | Gap | Impacto |
|---|-----|---------|
| 4 | Criterio por cédula no está explícito | La lógica actual usa `prestamo_id`; si falta, no hay asignación |
| 5 | 179 pagos sin `prestamo_id` | No se pueden asignar automáticamente (requieren identificación manual) |
| 6 | `actualizar_pago` no recalcula `pago_id` en cuotas si se cambia `prestamo_id` | Posible inconsistencia |

### 5.3 Menores

| # | Gap | Impacto |
|---|-----|---------|
| 7 | `auditoria_pagos_conciliados.py` usa `pago.cuota_id` | El modelo no tiene `cuota_id`; la relación es cuota→pago |
| 8 | `backfill_pago_id_en_cuotas.py` trabaja con cuotas que ya tienen `fecha_pago` | No cubre pagos conciliados sin asignar |

---

## 6. Resumen de flujos

```
┌─────────────────────────────────────────────────────────────────────────┐
│ CUÁNDO SE APLICAN REGLAS DE NEGOCIO (asignar pago → cuotas)             │
├─────────────────────────────────────────────────────────────────────────┤
│ ✅ POST /pagos (crear) con conciliado=true y prestamo_id                │
│ ✅ POST /pagos/{id}/aplicar-cuotas (manual)                             │
├─────────────────────────────────────────────────────────────────────────┤
│ ❌ POST /pagos/upload (carga masiva backend)                            │
│ ❌ POST /pagos/conciliacion/upload                                       │
│ ❌ PUT /pagos/{id} al cambiar conciliado a True                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 7. Recomendaciones

### 7.1 Prioridad alta — IMPLEMENTADAS (22/02/2026)

1. **POST /pagos/upload** — IMPLEMENTADO  
   - Tras insertar pagos, se hace `db.flush()` y para cada pago con `prestamo_id` y `monto > 0` se llama a `_aplicar_pago_a_cuotas_interno`
   - La respuesta incluye `cuotas_aplicadas`

2. **POST /pagos/conciliacion/upload** — IMPLEMENTADO  
   - Tras marcar `conciliado=True`, para cada pago con `prestamo_id` se invoca `_aplicar_pago_a_cuotas_interno`
   - La respuesta incluye `cuotas_aplicadas`

3. **PUT /pagos/{id}** — IMPLEMENTADO  
   - Al cambiar `conciliado` de False/Null a True, se invoca `_aplicar_pago_a_cuotas_interno` si el pago tiene `prestamo_id`

### 7.2 Prioridad media

4. **Documentar criterio por cédula**  
   - Si el cliente tiene varios préstamos y el pago no trae `prestamo_id`, definir regla (ej. préstamo con cuota más antigua vencida, menor saldo, etc.)

5. **Script de asignación masiva**  
   - Usar el SQL FIFO por `prestamo_id` y `fecha_pago` para los 43 pagos con `prestamo_id` sin asignar

### 7.3 Prioridad baja

6. Corregir `auditoria_pagos_conciliados.py` (eliminar referencia a `pago.cuota_id` si no existe)  
7. Extender `backfill_pago_id_en_cuotas.py` para cubrir pagos conciliados sin cuota asignada

---

## 8. Conclusión

**¿Existen reglas de negocio?** Sí, en `_aplicar_pago_a_cuotas_interno` (FIFO por cuota dentro del préstamo).

**¿Se aplican en carga masiva?**  
- Frontend (guardado individual): **sí**, si `conciliado=true` y `prestamo_id`  
- Backend (POST /upload): **no**  
- Conciliación por archivo: **no**  
- Actualización manual de conciliado: **no**

**¿Se articulan por cédula?**  
- Indirectamente: la cédula se usa para buscar préstamos y validar `prestamo_id`  
- No hay regla explícita para elegir préstamo cuando hay varios por cédula

---

*Documento generado a partir de la revisión del código en backend y frontend.*
