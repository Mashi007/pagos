# Estado de cuenta: fuente única de datos y consumidores

## Rol del módulo

La **definición operativa** del estado de cuenta (prestamos del cliente, cuotas pendientes, totales, tablas de amortización con columnas alineadas a la app) vive en el servicio:

- `app/services/estado_cuenta_pdf.py`
  - `obtener_datos_estado_cuenta_prestamo(db, prestamo_id, sincronizar=True)` — un préstamo.
  - `obtener_datos_estado_cuenta_cliente(db, cedula_lookup)` — todos los préstamos del cliente (cedula sin guiones).
  - `generar_pdf_estado_cuenta(...)` — solo renderiza PDF a partir del dict anterior (ReportLab).

**Reglas de etiqueta de cuota** (Caracas, mora, etc.): `app/services/cuota_estado.py` (`estado_cuota_para_mostrar`, `etiqueta_estado_cuota`). Los listados de cuotas en `prestamos` deben seguir usando la misma función para no divergir del PDF.

**Sincronización pagos → cuotas** antes de armar datos: `app/services/pagos_cuotas_sincronizacion.py` (`sincronizar_pagos_pendientes_a_prestamos`), invocada desde `obtener_datos_estado_cuenta_*`.

## Tablas de base de datos involucradas

- `clientes`, `prestamos`, `cuotas`, `pagos` (y compatibilidad de columnas vía `prestamo_db_compat` para `fecha_liquidado`).
- Flujo público adicional para sección “recibos” en PDF: `pagos_reportados`, `pagos` (conciliación `COB-` + `estado == PAGADO`) — lógica hoy en `estado_cuenta_publico._obtener_recibos_cliente`.

## Consumidores autorizados (deben usar el servicio)

| Consumidor | Uso |
|------------|-----|
| `GET /api/v1/prestamos/{id}/estado-cuenta/pdf` | `obtener_datos_estado_cuenta_prestamo` + `generar_pdf_estado_cuenta` |
| `app/api/v1/endpoints/estado_cuenta_publico.py` | `obtener_datos_estado_cuenta_cliente` + PDF; códigos en `estado_cuenta_codigos` |
| `app/services/liquidado_notificacion_service.py` | Mismo origen que el PDF por préstamo (adjunto email liquidado) |

**No** duplicar en otros endpoints la construcción de `amortizaciones_por_prestamo` / `cuotas_pendientes` con consultas paralelas: extender `obtener_datos_estado_cuenta_*` o exponer un endpoint JSON que reutilice esas funciones.

## Informes / SQL ad-hoc

Reportes por cédula o hojas de cálculo que necesiten la misma semántica que el PDF deben **documentar** que la referencia de negocio es este servicio (o reutilizarlo vía API interna), para evitar divergencia con consultas SQL sueltas.
