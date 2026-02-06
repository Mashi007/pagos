# Auditoría integral: Aprobación manual de riesgo y alineación de esquemas BD

**Fecha:** 2025-02-05  
**Alcance:** Cambios introducidos por el proceso de aprobación manual de riesgo (reemplazo de Evaluar riesgo + Aplicar condiciones + Asignar fecha), alineación del modelo **Auditoria** con la tabla real `auditoria` (entidad, entidad_id, detalles, exito) y del modelo **Cuota** con la tabla real `cuotas` (saldo_capital_inicial, saldo_capital_final, etc.).

---

## 1. Resumen ejecutivo

| Área | Estado | Notas |
|------|--------|--------|
| Proceso aprobación manual | Implementado | Un solo flujo: botón "Aprobar préstamo" → modal con fecha, datos editables, 2 checkboxes → estado APROBADO + auditoría |
| Modelo Auditoria | Alineado a BD real | Columnas: entidad, entidad_id, detalles, exito; sin modulo/registro_id/descripcion/resultado en BD |
| Modelo Cuota | Alineado a BD real | saldo_capital_inicial, saldo_capital_final obligatorios; generación los rellena (amortización plana) |
| Endpoints prestamos | OK | aprobar-manual con rol admin; get auditoría por entidad/entidad_id |
| Endpoints auditoría | OK | Listado/stats/exportar/registrar usan entidad, entidad_id, detalles, exito; API sigue exponiendo modulo/registro_id/descripcion vía mapeo |
| Frontend lista préstamos | OK | Solo AprobarPrestamoManualModal para DRAFT/EN_REVISION; flujo antiguo retirado de la lista |
| SQL verificación | OK | verificar_aprobacion_manual_prestamos.sql usa columnas reales (detalles, entidad, exito) |
| Código obsoleto / compatibilidad | Documentado | EvaluacionRiesgoForm, FormularioAprobacionCondiciones, AsignarFechaAprobacionModal y endpoints evaluar-riesgo, aplicar-condiciones, asignar-fecha siguen en código pero la UI de lista no los usa |

---

## 2. Cambios por componente

### 2.1 Backend – Modelo Auditoria

**Archivo:** `backend/app/models/auditoria.py`

- **Antes:** modulo, tabla, registro_id, descripcion, resultado, usuario_email (entre otros).
- **Ahora (alineado a BD real):**
  - `id`, `usuario_id` (NOT NULL), `accion`, `entidad`, `entidad_id`, `detalles`, `ip_address`, `user_agent`, `exito` (Boolean), `mensaje_error`, `fecha` (DateTime con timezone).
- **Eliminado en modelo:** usuario_email, modulo, tabla, registro_id, descripcion, resultado, campo, datos_anteriores, datos_nuevos.

**Verificación:** El modelo solo declara columnas que existen en la tabla `auditoria` de la BD.

---

### 2.2 Backend – Modelo Cuota

**Archivo:** `backend/app/models/cuota.py`

- **Alineado a BD real:** id, prestamo_id, cliente_id, numero_cuota, fecha_vencimiento, fecha_pago, monto (columna `monto_cuota`), **saldo_capital_inicial**, **saldo_capital_final**, total_pagado, dias_mora, dias_morosidad, estado, observaciones, es_cuota_especial, creado_en, actualizado_en.
- **Obligatorios en BD:** saldo_capital_inicial y saldo_capital_final (NOT NULL) están en el modelo y se rellenan en la generación de cuotas.

**Verificación:** No se insertan cuotas sin saldo_capital_inicial/saldo_capital_final.

---

### 2.3 Backend – Generación de cuotas

**Archivo:** `backend/app/api/v1/endpoints/prestamos.py` → `_generar_cuotas_amortización`

- Calcula para cada cuota n de N (amortización plana):
  - `saldo_capital_inicial = total - (n-1) * monto_cuota`
  - `saldo_capital_final = total - n * monto_cuota` (última cuota: 0).
- Inserta Cuota con: prestamo_id, cliente_id, numero_cuota, fecha_vencimiento, monto, saldo_capital_inicial, saldo_capital_final, estado=PENDIENTE.

**Verificación:** Coherente con modelo Cuota y con columnas NOT NULL de la tabla `cuotas`.

---

### 2.4 Backend – Aprobación manual

**Archivo:** `backend/app/api/v1/endpoints/prestamos.py`

- **Endpoint:** `POST /api/v1/prestamos/{prestamo_id}/aprobar-manual`
- **Seguridad:** Solo rol `administrador` (403 si no).
- **Validaciones:** Préstamo en DRAFT o EN_REVISION; acepta_declaracion y documentos_analizados true.
- **Lógica:** Actualiza préstamo (total_financiamiento, numero_cuotas, modalidad_pago, cuota_periodo, tasa_interes, observaciones, fecha_aprobacion, fecha_base_calculo, usuario_aprobador, estado=APROBADO); borra cuotas existentes; genera nuevas cuotas con saldos; inserta en **auditoria** con columnas reales:
  - usuario_id, accion=APROBACION_MANUAL, entidad=prestamos, entidad_id=prestamo_id, detalles=texto resumen, exito=True.
- **GET auditoría por préstamo:** Filtro por `Auditoria.entidad == "prestamos"` y `Auditoria.entidad_id == prestamo_id`; respuesta expone `modulo`/`descripcion` mapeados desde entidad/detalles para no romper frontend.

**Verificación:** No se usa ninguna columna inexistente en la tabla `auditoria`.

---

### 2.5 Backend – Endpoints de auditoría

**Archivo:** `backend/app/api/v1/endpoints/auditoria.py`

- **Listado y filtros:** Filtros por `modulo`/`registro_id` en query params se traducen a `entidad`/`entidad_id`. Ordenación: si se pide por `modulo` o `registro_id`, se ordena por `entidad` o `entidad_id`.
- **_row_to_item:** Lee de la fila: entidad→modulo, entidad_id→registro_id, detalles→descripcion, exito→resultado (EXITOSO/ERROR). usuario_email en respuesta queda None (no existe en BD).
- **Estadísticas:** Agrupación por `entidad` y por `usuario_id`.
- **Export Excel:** Cabeceras y celdas usan entidad, entidad_id, detalles, exito.
- **POST /registrar:** Requiere usuario autenticado; escribe usuario_id, entidad=body.modulo, entidad_id=body.registro_id, detalles=body.descripcion, exito=True.

**Verificación:** Toda lectura/escritura a BD usa solo columnas existentes; la API mantiene nombres antiguos en el contrato (modulo, registro_id, descripcion, resultado) vía mapeo.

---

### 2.6 Frontend – Lista de préstamos y modal de aprobación

**Archivos:** `frontend/src/components/prestamos/PrestamosList.tsx`, `AprobarPrestamoManualModal.tsx`

- **PrestamosList:** Para DRAFT y EN_REVISION solo se muestra el botón "Aprobar préstamo" (icono CheckCircle2), que abre `AprobarPrestamoManualModal`. No se usan EvaluacionRiesgoForm, FormularioAprobacionCondiciones ni AsignarFechaAprobacionModal en este flujo.
- **AprobarPrestamoManualModal:** Inicializa con datos del préstamo (total_financiamiento, numero_cuotas, modalidad_pago, cuota_periodo, tasa_interes, observaciones); una fecha (fecha de aprobación); dos checkboxes (documentos analizados y declaración fija); envía todo a `prestamoService.aprobarManual(prestamo.id, body)`.

**Verificación:** Flujo único de aprobación en lista; declaración fija; permisos vía canViewEvaluacionRiesgo() (admin).

---

### 2.7 Frontend – Servicio de préstamos

**Archivo:** `frontend/src/services/prestamoService.ts`

- **Nuevo:** `aprobarManual(prestamoId, body)` → POST a `/{id}/aprobar-manual` con fecha_aprobacion, acepta_declaracion, documentos_analizados y campos editables.
- **Mantenidos (no usados por el flujo de lista):** evaluarRiesgo, aplicarCondicionesAprobacion, asignarFechaAprobacion; pueden seguir para compatibilidad o llamadas desde otras pantallas.

---

### 2.8 SQL de verificación

**Archivo:** `backend/sql/verificar_aprobacion_manual_prestamos.sql`

- Consultas 1–4: prestamos, auditoria, cuotas (columnas), conteo por estado.
- **Consulta 5:** Últimos APROBACION_MANUAL usando solo columnas reales: id, usuario_id, accion, entidad, entidad_id, **detalles**, exito, fecha (sin `descripcion`).
- Consulta 6: Préstamos con usuario_aprobador.
- Opcional: UPDATE para migrar EVALUADO → EN_REVISION.

**Verificación:** No se referencia ninguna columna inexistente (modulo, registro_id, descripcion) en la tabla auditoria.

---

## 3. Esquemas de BD de referencia (auditados)

### 3.1 Tabla `auditoria`

- id (integer, NO)
- usuario_id (integer, NO)
- accion (character varying, NO)
- entidad (character varying, NO)
- entidad_id (integer, YES)
- detalles (text, YES)
- ip_address, user_agent (varchar/text, YES)
- exito (boolean, NO)
- mensaje_error (text, YES)
- fecha (timestamp with time zone, NO)

### 3.2 Tabla `cuotas`

- id, prestamo_id, numero_cuota, fecha_vencimiento, monto_cuota (NO)
- saldo_capital_inicial, saldo_capital_final (NO)
- fecha_pago, total_pagado, dias_mora, dias_morosidad, estado (según esquema)
- observaciones, es_cuota_especial, creado_en, actualizado_en, cliente_id (YES donde aplica)

### 3.3 Tabla `prestamos` (columnas usadas en aprobación)

- fecha_aprobacion, fecha_base_calculo, usuario_aprobador, estado
- total_financiamiento, numero_cuotas, modalidad_pago, cuota_periodo, tasa_interes, observaciones

---

## 4. Riesgos y recomendaciones

| Riesgo | Mitigación / Recomendación |
|--------|----------------------------|
| Usuario no administrador llama por API a aprobar-manual | Endpoint devuelve 403; solo rol administrador. |
| Préstamos en EVALUADO sin nuevo flujo | Opcional: ejecutar UPDATE EVALUADO→EN_REVISION (script en SQL); o dejar como histórico. |
| Componentes antiguos (EvaluacionRiesgoForm, etc.) siguen en repo | No se usan en lista; se pueden eliminar o conservar por si otra pantalla los usa (p. ej. detalle). Revisar PrestamoDetalleModal y eliminarlos si no hay referencias. |
| Frontend espera usuario_email en auditoría | La API devuelve usuario_email=None; si se necesita mostrar “quién”, obtener usuario por usuario_id desde API de usuarios o añadir join en backend. |
| Filtro por usuario_email en listar_auditoria | Actualmente no aplica (no hay columna usuario_email); se puede implementar join con tabla usuarios por usuario_id si se requiere. |

---

## 5. Checklist de coherencia

- [x] Modelo Auditoria solo usa columnas existentes en BD (entidad, entidad_id, detalles, exito).
- [x] Modelo Cuota incluye saldo_capital_inicial y saldo_capital_final y se rellenan al generar cuotas.
- [x] aprobar-manual escribe en auditoria con entidad, entidad_id, detalles, exito, usuario_id.
- [x] get_auditoria_prestamo filtra por entidad y entidad_id; respuesta con modulo/descripcion mapeados.
- [x] Endpoints de auditoría (listar, stats, exportar, registrar) usan entidad/detalles/exito; API mantiene contrato con modulo/registro_id/descripcion/resultado.
- [x] Lista de préstamos: un solo botón "Aprobar préstamo" para DRAFT/EN_REVISION; modal con fecha, datos editables y dos checkboxes.
- [x] SQL de verificación sin columnas inexistentes (detalles en lugar de descripcion en auditoria).

---

## 6. Documentos relacionados

- `docs/PROCESO_APROBACION_RIESGO_MANUAL_SIMPLIFICADO.md` – Diseño del proceso.
- `docs/VERIFICACION_APROBACION_MANUAL_RIESGO.md` – Verificación de los 6 requisitos del usuario.
- `backend/sql/verificar_aprobacion_manual_prestamos.sql` – Script DBeaver para comprobar tablas y datos.
