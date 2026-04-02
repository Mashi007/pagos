# Integridad préstamos, cuotas y pagos

Resumen de lo que está integrado en la aplicación (automático o por flujo) y cómo verificar/mantener integridad.

## Verificaciones que ya están integradas

### 1. Cédula de préstamo debe existir en clientes
- **Frontend (carga masiva préstamos):** Tras cargar el Excel se llama `checkCedulas`; las filas con cédula que no existe en clientes se marcan con error y no se pueden guardar.
- **Frontend (guardar préstamo):** Si la cédula no existe en clientes, se rechaza con mensaje "Cédula no existe en tabla clientes".
- **Backend:** Al crear préstamo se valida que `cliente_id` exista (404 si no).

### 2. Cuotas con prestamo_id válido
- **BD:** La tabla `cuotas` tiene FK `prestamo_id` → `prestamos.id` (no nullable), por tanto la BD no permite cuotas huérfanas.
- **App:** Las cuotas se crean siempre desde un préstamo existente (`_generar_cuotas_amortizacion` en crear préstamo, asignar fecha, aprobar manual).

### 3. Pagos con prestamo_id válido
- **BD:** FK `pagos.prestamo_id` → `prestamos.id` (nullable). La BD puede permitir NULL; si se asigna un valor, el motor puede validar la FK según configuración.
- **App:** Al asignar préstamo a un pago se usa un `cliente_id`/préstamo existente; no se escribe un `prestamo_id` inexistente desde la API.

### 4. Préstamos con cuotas (generación automática)
- **Automático:** Al **crear** un préstamo (POST `/prestamos`), al **asignar fecha de aprobación** y al **aprobar manual** se llama `_generar_cuotas_amortizacion` y se crean las cuotas si no existen.
- **No automático:** Préstamos que quedaron en APROBADO sin cuotas (p. ej. datos legacy) no se rellenan solos; se pueden generar desde **Revisión Manual** (Reportes > Tabla amortización completa: "Generar Tabla de Amortización" para préstamos aprobados sin cuotas) o asignando fecha al préstamo.

### 5. Número de cuotas (1–50)
- **Backend:** Schemas y endpoints validan `numero_cuotas` entre 1 y 50.
- **BD:** CHECK `ck_prestamos_numero_cuotas_rango` (1–50) si se aplicó la migración 026/010.

### 6. Generar cuotas para APROBADO sin cuotas (mantenimiento)
- **POST `/api/v1/prestamos/generar-cuotas-aprobados-sin-cuotas`** (solo administrador).
- Busca todos los préstamos en estado APROBADO que no tienen ninguna cuota.
- Para cada uno: usa **fecha_base_calculo** alineada con **fecha_aprobacion** (`_fecha_para_amortizacion`); si no hay ninguna, se omite con error en el listado de errores (no se usa **fecha_registro** como sustituto).
- Genera la tabla de amortización con la misma lógica que “Asignar fecha” / “Aprobar manual” (monto según tasa, modalidad, numero_cuotas).
- Respuesta: `{ "procesados", "cuotas_creadas", "errores", "mensaje" }`.
- Útil para regularizar datos legacy o préstamos que quedaron sin cuotas.

### 7. Estado DESEMBOLSADO eliminado
- El flujo deja los préstamos en **APROBADO** (con `fecha_aprobacion`); no se usa el estado DESEMBOLSADO.

---

## Endpoint de verificación automática

**GET `/api/v1/health/integrity`** (y en muchos entornos **GET `/health/integrity`** si se monta el router en la raíz)

Ejecuta las mismas comprobaciones que los SQL de análisis:

| Campo | Significado |
|-------|-------------|
| `total_prestamos` | Cantidad de préstamos |
| `prestamos_sin_cliente_o_sin_cedula` | Préstamos sin cliente o con cliente sin cédula (debe ser 0) |
| `cuotas_sin_prestamo_id` | Cuotas huérfanas (debe ser 0) |
| `cuotas_con_prestamo_id_invalido` | Cuotas con prestamo_id inexistente (debe ser 0) |
| `pagos_con_prestamo_id` | Pagos que tienen prestamo_id asignado |
| `pagos_con_prestamo_id_invalido` | Pagos con prestamo_id inexistente (debe ser 0) |
| `prestamos_sin_cuotas` | Préstamos sin ninguna cuota |
| `prestamos_aprobado_sin_cuotas` | Préstamos APROBADO sin cuotas |

- **status: "ok"** → Integridad correcta.
- **status: "degraded"** → Hay préstamos APROBADO sin cuotas (informativo).
- **status: "error"** → Hay préstamos sin cliente/cédula, cuotas huérfanas o pagos con prestamo_id inválido.

Puedes llamar a este endpoint desde un **cron** o un **monitor (p. ej. Uptime Robot)** para alertar si `status != "ok"`.

---

## Mejoras posibles

1. **Cron / tarea programada:** Ejecutar `GET /health/integrity` cada X minutos y enviar correo o notificación si `status == "error"`.
2. **Generar cuotas para APROBADO sin cuotas (implementado):** Un script o endpoint de mantenimiento (protegido) que, para cada préstamo APROBADO sin cuotas, llame a la misma lógica que “Asignar fecha” Ver endpoint en sección 6 arriba.
3. **Dashboard o panel admin:** Mostrar un resumen de `GET /health/integrity` en una pantalla de administración.
4. **Constraint en BD para pagos:** Asegurar que `pagos.prestamo_id` tenga FK con `ON DELETE SET NULL` para que, si se borrara un préstamo, los pagos no queden con ID inválido (ya suele estar así; verificar en la BD).
5. **Migración 026:** Si aún hay préstamos en estado DESEMBOLSADO, ejecutar `backend/scripts/026_remove_estado_desembolsado.sql` para pasarlos a APROBADO y actualizar el CHECK de estado.

---

## SQL de referencia (verificación manual)

Los mismos criterios que usa `GET /health/integrity` se pueden ejecutar en DBeaver con los SQL indicados en las conversaciones anteriores (préstamos con cédula en clientes, préstamos sin cuotas, cuotas/pagos con prestamo_id inválido, resumen de integridad).
