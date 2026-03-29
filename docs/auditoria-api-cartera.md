# API: auditoria de cartera (`/api/v1/auditoria/prestamos/cartera`)

Datos reales desde BD (`prestamos`, `clientes`, `cuotas`, `pagos`, `cuota_pagos`). OpenAPI en `/docs` amplia descripciones en los modelos `PrestamoCarteraChequeoResponse` y `AuditoriaCarteraResumenResponse`.

## Rutas

| Metodo | Ruta | Proposito |
|--------|------|------------|
| GET | `/prestamos/cartera/meta` | JSON ultima corrida guardada en `configuracion` (clave `auditoria_cartera_ultima_resumen`). Puede incluir `conteos_por_control` y `reglas_version` si la corrida los persistio. |
| GET | `/prestamos/cartera/resumen` | Totales y `conteos_por_control` **sin** lista de prestamos (`incluir_filas=false` en servidor). Query opcional: `prestamo_id`, `cedula` (misma semantica que chequeos). |
| GET | `/prestamos/cartera/chequeos` | Lista paginada de prestamos con al menos un control en alerta SI. Query: `skip`, `limit`, `prestamo_id`, `cedula`, `solo_alertas` (ver abajo). |
| POST | `/prestamos/cartera/ejecutar` | Sincroniza `cuotas.estado`, recalcula, persiste meta ampliada, devuelve **todos** los prestamos con alerta (sin paginar en la respuesta). |
| POST | `/prestamos/cartera/corregir` | Solo administrador; opciones de sincronizar estados y/o reaplicar cascada pagos; persiste meta ampliada. |
| POST | `/prestamos/cartera/revisiones` | Bitacora: registrar revision (por defecto `MARCAR_OK`). `codigo_control` debe ser uno de los controles del catalogo (`CONTROLES_CARTERA_VALIDOS`; ver `prestamo_cartera_auditoria.py`). |
| POST | `/prestamos/cartera/revisiones/ocultos` | Body `{ "prestamo_ids": number[] }` (max 5000). Devuelve pares cuyo **ultimo** evento es `MARCAR_OK` (la UI los oculta). |
| GET | `/prestamos/cartera/revisiones/historial` | Query `prestamo_id`, `limit`. Historial descendente con email de usuario si existe. |

Migracion: `030_auditoria_cartera_revision` (tabla `auditoria_cartera_revision`).

## Parametro `solo_alertas` (GET chequeos, POST ejecutar)

Historico: **no cambia el resultado**. Siempre se devuelven solo prestamos con algun control en SI y, por fila, solo controles en SI. Mantener en clientes antiguos si lo envian.

## Campo `resumen` (JSON)

Campos habituales:

- `prestamos_evaluados`: filas evaluadas tras filtros `prestamo_id` / `cedula`.
- `prestamos_con_alerta`: cantidad con al menos un SI.
- `prestamos_listados_total`: igual a `prestamos_con_alerta` en la corrida actual.
- `prestamos_listados`: tamano de la pagina devuelta (GET chequeos); 0 en GET resumen.
- `conteos_por_control`: mapa `codigo_control -> cantidad de prestamos` con esa alerta SI.
- `reglas_version`: identificador de la definicion de reglas en codigo (`AUDITORIA_CARTERA_REGLAS_VERSION` en `prestamo_cartera_auditoria.py`). Subir cuando se agregue o quite un control.

## LIQUIDADO vs cuadre pagos / aplicado

- El flujo que marca **LIQUIDADO** (`_marcar_prestamo_liquidado_si_corresponde` en `pagos.py`) usa **cobertura de cuotas** (tolerancia 0.01 sobre `total_pagado` vs `monto_cuota`), no la suma agregada de `pagos.monto_pagado`, porque puede haber exceso operativo o registros que no impactan cupo.
- El control **`total_pagado_vs_aplicado_cuotas`** compara suma de pagos operativos vs suma aplicada vía `cuota_pagos` (tol 0.02 USD).
- El control **`liquidado_descuadre_total_pagos_vs_aplicado_cuotas`** repite el mismo umbral **solo** cuando `prestamos.estado = LIQUIDADO`, para filtrar en KPIs y revision los liquidados con descuadre operativo.
- Variable de entorno **`LIQUIDACION_REQUIERE_CUADRE_PAGOS_VS_CUOTAS`** (defecto `false`): si `true`, no se asigna LIQUIDADO hasta que pagos operativos y aplicado cuadren (misma SQL/tolerancia que auditoria).
- `fecha_referencia`, `pagina_skip`, `pagina_limit` segun corresponda.

## Conciliación externa (decisión 3.5)

El control **`total_pagado_vs_aplicado_cuotas`** se valida frente a la operación real mediante **conciliación bancaria** (extracto / movimientos del banco vs pagos en sistema y su trazabilidad hacia `cuota_pagos`).

## Procesos que escriben en BD

- Job 03:00 y POST **ejecutar** / **corregir**: pueden actualizar `cuotas.estado` y/o aplicacion de pagos (corregir); persisten meta en `configuracion`.

## Frontend

- Servicio: `listarCarteraChequeos`, `obtenerCarteraResumen`, `ejecutarCartera`, `corregirCartera`, `listarRevisionesOcultos`, `crearRevisionCartera`, `historialRevisionesCartera`.
- Pestaña Revision de cartera: **OK** persiste en BD; carga ocultos tras listar chequeos; enlace **Historial revisiones** por prestamo.
