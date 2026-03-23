# Auditoría: proceso de actualización de pagos y transición a cuotas

**Objetivo:** Verificar que todas las vías de ingreso de pagos en RAPICREDIT ([/pagos/pagos](https://rapicredit.onrender.com/pagos/pagos)) aplican correctamente el pago a cuotas según la regla de negocio y que no existen vacíos en el flujo.

**Fecha:** 2025-03-18

---

## 1. Vías de ingreso de pagos (UI)

| # | Opción en pantalla | Acción técnica | Backend |
|---|--------------------|----------------|---------|
| 1 | **Registrar un pago** (Formulario) | Formulario manual | `POST /api/v1/pagos` → `crear_pago` |
| 2 | **Pagos desde Excel** (Revisar y editar) | Subir Excel → revisar → guardar | `POST /api/v1/pagos/upload` + `POST /api/v1/pagos/batch` o `guardar-fila-editable` |
| 3 | **Generar Excel desde email** | Email → Excel (origen de datos) | No crea pagos; el Excel se usa en la opción 2 |
| 4 | **Importar reportados aprobados (Cobros)** | Importar desde módulo Cobros | `POST /api/v1/pagos/importar-desde-cobros` y/o Cobros `POST .../aprobar` |

---

## 2. Lógica única: aplicar pago a cuotas

- **Función central:** `_aplicar_pago_a_cuotas_interno(pago, db)` en `backend/app/api/v1/endpoints/pagos.py`.
- **Comportamiento:** Aplica el `monto` del pago a las cuotas del mismo `prestamo_id` en orden **Cascada** (por `numero_cuota`). Actualiza `Cuota.total_pagado`, `fecha_pago`, `estado`; crea registros en `CuotaPago`; marca el préstamo como **LIQUIDADO** cuando todas las cuotas quedan pagadas. No hace `commit` (lo hace quien llama).
- **Endpoint público:** `POST /pagos/{pago_id}/aplicar-cuotas` también usa esta función y hace commit.

No existe otra implementación paralela de “aplicar a cuotas”; toda la asignación pasa por esta función.

---

## 3. Resultado por vía de ingreso

| Vía de ingreso | Endpoint / flujo | ¿Aplica a cuotas? | Observación |
|----------------|------------------|--------------------|-------------|
| **Formulario** | `POST /pagos` → `crear_pago` | **Sí** | Tras crear el pago se llama `_aplicar_pago_a_cuotas_interno`. |
| **Guardar fila editable** | `POST /pagos/guardar-fila-editable` | **Sí** | Misma lógica. |
| **Pagos desde Excel** | `POST /pagos/upload` (preview) + `POST /pagos/batch` o guardar fila | **Sí** | Batch y guardar-fila crean el pago y aplican a cuotas en la misma transacción. |
| **Generar Excel desde email** | Solo genera archivo | N/A | No crea pagos; el usuario importa ese Excel con la opción “Pagos desde Excel”. Sin vacío en backend. |
| **Importar desde Cobros** | `POST /pagos/importar-desde-cobros` | **Sí** | Crea pagos y aplica a cuotas. |
| **Cobros – Aprobar reportado** | `POST /cobros/.../pagos-reportados/{id}/aprobar` | **Sí** | Crea el pago y aplica a cuotas vía `_crear_pago_desde_reportado_y_aplicar_cuotas` → `_aplicar_pago_a_cuotas_interno`. |

**Conclusión:** Todas las vías que **crean** un pago con `prestamo_id` y monto > 0 utilizan la misma función `_aplicar_pago_a_cuotas_interno`. No hay vía que cree pagos y omita la aplicación a cuotas.

---

## 4. Otros flujos relacionados

- **Conciliación (upload):** `POST /pagos/conciliacion/upload` marca pagos existentes como conciliados y **vuelve a aplicar** a cuotas. No crea pagos nuevos. Útil si en algún momento un pago existía sin aplicar (por ejemplo datos legacy o correcciones).
- **Aplicar a cuotas manual:** `POST /pagos/{pago_id}/aplicar-cuotas` permite re-aplicar un pago ya creado. Consistente con la misma lógica interna.

---

## 5. Riesgos y vacíos identificados

| Riesgo | Nivel | Comentario |
|--------|--------|------------|
| Doble aplicación a cuotas | Bajo | Si se llama dos veces “aplicar a cuotas” sobre el mismo pago, podría haber doble asignación. Mitigación: la lógica debe ser idempotente o usarse solo tras creación; revisar que no se invoque aplicar-cuotas dos veces en el mismo flujo. |
| Excel → mapeo de columnas | Medio | Si el Excel (o el generado desde email) tiene columnas mal mapeadas (documento, monto, préstamo), se pueden crear pagos con préstamo erróneo. La validación en batch (crédito existe, cliente existe) reduce pero no elimina el riesgo; conviene validar en front y back. |
| Cobros vs Pagos – doble conteo | Bajo | Importar “reportados aprobados” y además aprobar manualmente el mismo reporte podría duplicar pagos. Mitigación: flujos excluyentes en negocio (o importación masiva **o** aprobaciones puntuales) y/o constraint/validación por referencia única. |
| Generar Excel desde email | Bajo | Si el pipeline email→Excel introduce errores (fechas, montos, identificación), esos errores llegan a “Pagos desde Excel”. No hay vacío en “aplicar a cuotas”, pero la calidad del dato de entrada depende de ese pipeline. |

---

## 6. Recomendaciones

1. **Mantener una sola función de aplicación a cuotas**  
   Seguir usando `_aplicar_pago_a_cuotas_interno` para todos los flujos; no duplicar lógica.

2. **Validaciones en batch (Excel / importación)**  
   Reforzar que documento + préstamo (o clave única de negocio) no generen pago duplicado en la misma carga.

3. **Idempotencia de “aplicar a cuotas”**  
   Documentar o garantizar que aplicar dos veces el mismo pago no duplique `total_pagado` en cuotas (por ejemplo recalculando desde CuotaPago o comprobando que el pago ya fue aplicado).

4. **Generar Excel desde email**  
   Si existe código o servicio para “Generar Excel desde email”, revisar mapeo de campos y formatos para evitar errores que luego se carguen como pagos.

5. **Conciliación**  
   Mantener el flujo de conciliación (upload) para marcar conciliados y (re)aplicar a cuotas cuando corresponda; asegurar que no se re-aplique de forma duplicada si ya estaba aplicado.

---

## 7. Resumen ejecutivo

- **Proceso de actualización de pagos:** Todas las opciones de ingreso (Formulario, Excel, Cobros, guardar fila) que crean un pago utilizan la **misma** lógica para aplicar el pago a cuotas (`_aplicar_pago_a_cuotas_interno`). No se detectan vacíos en la transición **pagos → cuotas** por vía de ingreso.
- **Generar Excel desde email:** No crea pagos en backend; es origen de datos para “Pagos desde Excel”. El riesgo está en la calidad del mapeo email→Excel, no en “aplicar a cuotas”.
- **Recomendaciones prioritarias:** validación anti-duplicados en cargas masivas, idempotencia al aplicar a cuotas y revisión del pipeline email→Excel.
