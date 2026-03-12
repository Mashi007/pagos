# Fases y logs de notificaciones

Logs estructurados por fase para detectar fallas e indicadores de funcionamiento.

## Fases del envío (flujo por lote)

| Fase (buscar en logs) | Descripción | Indicadores |
|----------------------|-------------|-------------|
| `notif_envio_inicio` | Inicio del envío por lote | `total_items`, `origen` |
| `notif_envio_config` | Configuración cargada | `modo_pruebas`, `email_pruebas_ok`, `tipos_habilitados` |
| `notif_envio_contexto_cobranza` | Construcción de contexto cobranza por ítem | `item_id`, `ok`, `motivo` (si falla) |
| `notif_envio_adjuntos` | Generación de adjuntos (PDF anexo / fijos) | `item_id`, `cantidad`, `error` (si falla) |
| `notif_envio_email` | Envío de cada email | `item_id`, `email`, `exito`, `error` (si falla) |
| `notif_envio_persistencia` | Guardado en BD (envios_notificacion) | `registros`, `ok`, `error` (si falla) |
| `notif_envio_resumen` | Resumen del lote | `enviados`, `fallidos`, `sin_email`, `omitidos_config`, `enviados_whatsapp`, `fallidos_whatsapp` |
| `notif_envio_fallo` | Falla en alguna fase | `fase`, `detalle` |

## Fases del historial por cédula

| Fase (buscar en logs) | Descripción | Indicadores |
|----------------------|-------------|-------------|
| `notif_historial_consulta` | Consulta historial por cédula | `cedula`, `total`, `tiempo_ms` |
| `notif_historial_excel` | Descarga Excel historial | `cedula`, `filas`, `ok`, `error` (si falla) |
| `notif_historial_comprobante` | Comprobante de envío (por id) | `envio_id`, `ok`, `error` (si falla) |
| `notif_historial_fallo` | Falla en historial | `fase`, `detalle` |

## Cómo buscar en logs

```bash
# Fallas en envío
grep "notif_envio_fallo" app.log
grep "notif_envio_email" app.log | grep "fallido"

# Indicadores de resumen (éxito/fallo por lote)
grep "notif_envio_resumen" app.log

# Persistencia en BD fallida
grep "notif_envio_persistencia" app.log | grep "fallida"

# Historial: consultas y tiempo
grep "notif_historial_consulta" app.log

# Fallas en historial
grep "notif_historial_fallo" app.log
```

## Tests

- **Envío (flags/config):** `pytest tests/test_config_notificaciones_envios.py -v`
- **Historial y comprobante:** `pytest tests/test_notificaciones_historial.py -v`

Los tests de historial validan: historial por cédula (vacío, con datos, normalización), descarga Excel y comprobante por id (200/404).
