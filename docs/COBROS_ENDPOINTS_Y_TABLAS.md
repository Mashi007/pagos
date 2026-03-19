# Verificación: Endpoints Cobros y conexión a tablas

Router montado en **`/api/v1/cobros`** (tags: `cobros`). Todos los endpoints usan **`Depends(get_db)`** y consultas reales a la BD (sin stubs).

---

## Tablas utilizadas por el módulo Cobros

| Tabla (modelo) | Uso |
|----------------|-----|
| **pagos_reportados** (`PagoReportado`) | Listado, detalle, aprobar, rechazar, editar, eliminar, comprobante, recibo, historial por cédula |
| **pagos_reportados_historial** (`PagoReportadoHistorial`) | Registro de cambios de estado; detalle de un pago reportado |
| **cedulas_reportar_bs** (`CedulaReportarBs`) | Regla “solo Bs si está en lista Bolívares” (listado y edición) |
| **clientes** (`Cliente`) | Email para recibo; validación NO CLIENTES; aprobar (crear pago y aplicar cuotas) |
| **prestamos** (`Prestamo`) | Aprobar: buscar préstamo APROBADO del cliente para aplicar pago |
| **pagos** (`Pago`) | Regla DUPLICADO DOC (numero_documento); crear pago al aprobar; enviar recibo |
| **cuotas** / **cuota_pagos** | Vía `_aplicar_pago_a_cuotas_interno` (pagos.py) al aprobar |

---

## Endpoints (método, ruta, tablas)

| # | Método | Ruta | Tablas (lectura/escritura) |
|---|--------|------|----------------------------|
| 1 | GET | `/pagos-reportados` | **pagos_reportados** (L), **clientes** (L cedulas), **cedulas_reportar_bs** (L), **pagos** (L numero_documento) |
| 2 | GET | `/pagos-reportados/kpis` | **pagos_reportados** (L, agrupado por estado) |
| 3 | GET | `/pagos-reportados/{pago_id}` | **pagos_reportados** (L), **pagos_reportados_historial** (L) |
| 4 | POST | `/pagos-reportados/{pago_id}/aprobar` | **pagos_reportados** (L,E), **clientes** (L), **prestamos** (L), **pagos** (L,E), **pagos_reportados_historial** (E). Cuotas vía `_aplicar_pago_a_cuotas_interno` (cuotas, cuota_pagos, prestamos E) |
| 5 | POST | `/pagos-reportados/{pago_id}/rechazar` | **pagos_reportados** (L,E), **clientes** (L para email). Historial (E) |
| 6 | DELETE | `/pagos-reportados/{pago_id}` | **pagos_reportados** (L,E delete) |
| 7 | GET | `/historico-cliente` | **pagos_reportados** (L, por tipo_cedula+numero_cedula o numero_cedula) |
| 8 | GET | `/pagos-reportados/{pago_id}/comprobante` | **pagos_reportados** (L, campo comprobante) |
| 9 | GET | `/pagos-reportados/{pago_id}/recibo.pdf` | **pagos_reportados** (L, campo recibo_pdf) |
| 10 | POST | `/pagos-reportados/{pago_id}/enviar-recibo` | **pagos_reportados** (L,E), **clientes** (L para email). Opcional commit recibo_pdf |
| 11 | PATCH | `/pagos-reportados/{pago_id}` | **pagos_reportados** (L,E), **cedulas_reportar_bs** (L), **pagos** (L numero_documento para duplicado) |
| 12 | PATCH | `/pagos-reportados/{pago_id}/estado` | **pagos_reportados** (L,E), **clientes** (L), **prestamos** (L), **pagos** (L,E), historial (E). Si aprobado: igual que #4. Si rechazado: email (notificaciones) |

L = lectura, E = escritura.

---

## Conexión a BD

- **Inyección de sesión:** todos los endpoints declaran `db: Session = Depends(get_db)`.
- **Origen de la sesión:** `app.core.database.get_db` → `SessionLocal()` → `settings.DATABASE_URL` (`.env` / entorno).
- **Transacciones:** los que modifican datos llaman `db.commit()` (o `db.rollback()` en caso de error); los de solo lectura no hacen commit.

---

## Resumen

- **12 endpoints** en el router Cobros (pagos reportados, KPIs, detalle, aprobar, rechazar, eliminar, histórico, comprobante, recibo, enviar recibo, editar, cambiar estado).
- **7 tablas** involucradas: `pagos_reportados`, `pagos_reportados_historial`, `cedulas_reportar_bs`, `clientes`, `prestamos`, `pagos`, y vía `pagos.py`: `cuotas` / `cuota_pagos` (y actualización `prestamos.estado` a LIQUIDADO cuando aplica).
- **Conexión:** todos usan la BD configurada en `DATABASE_URL`; no hay respuestas stub con datos falsos.
