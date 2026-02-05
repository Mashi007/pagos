# Revisión de endpoints e integración frontend/backend

## Resumen

- **Backend**: FastAPI con routers en `app/api/v1/__init__.py`, prefijo `API_V1_STR` (ej. `/api/v1`).
- **Frontend**: Servicios en `frontend/src/services/*.ts` que llaman a `apiClient` con rutas `/api/v1/...`.

## Correcciones realizadas

### 1. Préstamos – Respuesta del backend

- **Problema**: El backend devuelve el objeto directamente (ej. `PrestamoResponse`), no `{ data: ... }`. El frontend hacía `return response.data` y podía devolver `undefined`.
- **Solución**: En `prestamoService.ts`, `getPrestamo`, `createPrestamo` y `updatePrestamo` ahora devuelven el resultado de `apiClient.get/post/put` directamente.

### 2. Préstamos por cédula

- **Problema**: El frontend llamaba a `GET /api/v1/prestamos/cedula/{cedula}` y `GET /api/v1/prestamos/cedula/{cedula}/resumen`, que no existían. La ruta `GET /{prestamo_id}` podía interpretar "cedula" como ID.
- **Solución**: En `prestamos.py` se añadieron (antes de `/{prestamo_id}`):
  - `GET /cedula/{cedula}`: listado de préstamos por cédula.
  - `GET /cedula/{cedula}/resumen`: resumen (saldo, mora, lista de préstamos) por cédula.

### 3. Auditoría por préstamo

- **Problema**: El frontend llamaba a `GET /api/v1/prestamos/auditoria/{prestamoId}`, pero la auditoría está bajo `GET /api/v1/auditoria` (sin subruta por préstamo).
- **Solución**:
  - En `auditoria.py` se añadió el filtro opcional `registro_id` a `listar_auditoria`.
  - En `useAuditoriaPrestamo.ts` se cambió la llamada a `GET /api/v1/auditoria?modulo=prestamos&registro_id={prestamoId}` y se mapea la respuesta `{ items: [] }` al tipo `AuditoriaEntry[]` que usa el componente.

---

## Endpoints de pagos (implementados)

Los siguientes métodos de `pagoService` tienen ya su ruta implementada en backend:

| Método frontend | Ruta | Implementación |
|-----------------|------|----------------|
| `aplicarPagoACuotas(pagoId)` | `POST /api/v1/pagos/{id}/aplicar-cuotas` | `pagos.py`: aplica monto del pago a cuotas pendientes del préstamo (orden por número de cuota). |
| `uploadExcel(file)` | `POST /api/v1/pagos/upload` | `pagos.py`: carga masiva Excel (columnas: cédula, prestamo_id, fecha, monto, numero_documento). |
| `uploadConciliacion(file)` | `POST /api/v1/pagos/conciliacion/upload` | `pagos.py`: Excel con Fecha Depósito y Nº Documento; marca pagos como conciliados. |
| `getUltimosPagos(...)` | `GET /api/v1/pagos/ultimos` | `pagos.py`: resumen por cédula (último pago, cuotas atrasadas, saldo vencido). |
| `descargarPagosConErrores()` | `GET /api/v1/pagos/exportar/errores` | `pagos.py`: Excel de pagos no conciliados o estado PENDIENTE/ATRASADO/REVISAR. |
| `descargarPDFPendientes(cedula)` | `GET /api/v1/reportes/cliente/{cedula}/pendientes.pdf` | `reportes.py`: PDF con cuotas pendientes del cliente (reportlab). |

---

## Endpoints correctamente integrados (referencia)

- **Auth**: login, refresh, me, logout, forgot-password.
- **Pagos**: GET/POST/PUT/DELETE listado y por ID; GET `/pagos/kpis`; GET `/pagos/stats`.
- **Préstamos**: listado, stats, por ID, por cedula, resumen por cedula, CRUD.
- **Comunicaciones**: listado, mensajes WhatsApp, por responder, enviar WhatsApp, crear cliente automático.
- **Reportes**: dashboard/resumen, cartera, pagos, morosidad, exportar (varios).
- **Dashboard**: kpis-principales, opciones-filtros, evolucion-pagos, etc.
- **Configuración**: informe-pagos (Google), AI, logo, etc.

---

## Calidad de código – buenas prácticas ya usadas

1. **Backend**
   - Uso de `Depends(get_db)` y `Depends(get_current_user)` en los routers.
   - Respuestas tipadas con `response_model` y schemas Pydantic.
   - Excepciones con `HTTPException` y mensajes claros.
   - Logging con `logger.exception` en bloques except.
   - Rollback en errores (`db.rollback()`) donde aplica.
   - Rutas con path params numéricos (ej. `prestamo_id: int`) para evitar colisiones con rutas literales (por eso `/cedula/{cedula}` va antes de `/{prestamo_id}`).

2. **Frontend**
   - Servicios centralizados y uso de `apiClient` con interceptores (token, refresh).
   - Tipos TypeScript para requests/responses.
   - Manejo de errores y toasts en `api.ts`.

---

## Cómo verificar integración

1. Revisar que la URL del frontend coincida con el prefijo y path del backend (ej. `prefix="/pagos"` → `/api/v1/pagos/...`).
2. Comprobar que el cuerpo de respuesta del backend coincida con lo que el frontend espera (objeto directo vs `{ data }`).
3. Para rutas con path params, definir antes las rutas más específicas (ej. `/cedula/{cedula}`) que las genéricas (`/{id}`).

---

## Verificación reciente (endpoints y calidad)

- **Pagos**: Rutas `/ultimos`, `/upload`, `/conciliacion/upload`, `/exportar/errores`, `/{pago_id}/aplicar-cuotas` verificadas en `pagos.py`; orden correcto (rutas fijas antes de `/{pago_id}`). Frontend `pagoService.ts` alineado.
- **Reportes**: `GET /reportes/cliente/{cedula}/pendientes.pdf` implementado en `reportes.py`.
- **Corrección en reportes**: En `get_pendientes_cliente_pdf`, el resultado de `.scalars().all()` es lista de modelos (Prestamo/Cuota), no de tuplas; se corrigió `prestamo_ids = [p.id for p in prestamos]` y el bucle de cuotas para iterar directamente sobre `cuotas_rows` (`for c in cuotas_rows`).
- **Calidad**: Los endpoints revisados usan `Depends(get_db)`, `Depends(get_current_user)` en el router, `response_model` donde aplica, `HTTPException` y en pagos/cobranzas `logger.exception` + `db.rollback()` en excepciones.
