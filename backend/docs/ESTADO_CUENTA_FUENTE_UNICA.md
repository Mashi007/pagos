# Estado de cuenta: fuente unica de datos y consumidores

Panorama junto con recibos: `backend/docs/DOCUMENTOS_CLIENTE_CENTRO_UNICO.md`.

## Modulos

| Archivo | Responsabilidad |
|---------|-----------------|
| `app/services/estado_cuenta_datos.py` | **Fuente unica**: carga desde BD, sync pagos, `obtener_datos_estado_cuenta_prestamo`, `obtener_datos_estado_cuenta_cliente`, `obtener_recibos_cliente_estado_cuenta`, `serializar_estado_cuenta_payload_json`. |
| `app/services/estado_cuenta_pdf.py` | Solo generacion PDF (`generar_pdf_estado_cuenta`) y re-export de las funciones de datos (compatibilidad con imports existentes). |

## Tabla de amortizacion en PDF / JSON

Se incluye cuando el prestamo esta en `ESTADOS_PRESTAMO_TABLA_AMORTIZACION` (`APROBADO`, `LIQUIDADO`). Otros estados: sin bloque de amortizacion completa (cuotas pendientes siguen calculandose).

## Reglas de etiqueta de cuota

`app/services/cuota_estado.py` (`estado_cuota_para_mostrar`, `etiqueta_estado_cuota`). El listado `GET /prestamos/{id}/cuotas` y el estado de cuenta deben coincidir; test: `tests/test_estado_cuenta_contract.py`.

## Tablas de base de datos

- `clientes`, `prestamos`, `cuotas`, `pagos`, `pagos_reportados` (recibos publicos), `estado_cuenta_codigos` (flujo codigo email).

## Consumidores

| Consumidor | Uso |
|------------|-----|
| `GET /api/v1/prestamos/{id}/estado-cuenta` | JSON del mismo payload que el PDF (`serializar_estado_cuenta_payload_json`). |
| `GET /api/v1/prestamos/{id}/estado-cuenta/pdf` | PDF |
| `app/api/v1/endpoints/estado_cuenta_publico.py` | PDF por cedula + `obtener_recibos_cliente_estado_cuenta` |
| `app/services/liquidado_notificacion_service.py` | PDF adjunto (datos via `obtener_datos_estado_cuenta_prestamo`) |

No duplicar la construccion de `amortizaciones_por_prestamo` en otros servicios: extender `estado_cuenta_datos` o consumir el endpoint JSON.

## Informes / SQL ad-hoc

Los reportes que deban reflejar la misma semantica que el PDF deben reutilizar `estado_cuenta_datos` o el endpoint JSON, y documentar esta dependencia.
