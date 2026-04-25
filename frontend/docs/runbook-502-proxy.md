# Runbook 502 Proxy (`rapicredit` -> `pagos`)

Guia operativa para incidentes `502` en rutas `/api/...` servidas por el frontend Node (`rapicredit.onrender.com`) que proxya al API Python (`pagos-f2qf.onrender.com`).

## Objetivo

- Identificar rapidamente si el `502` viene de reinicio, timeout, DNS/TLS o configuracion.
- Aplicar una accion segura sin tocar logica de negocio.

## Contexto de arquitectura

- Navegador consume `https://rapicredit.onrender.com/api/...`.
- `frontend/server.js` hace proxy al API (`API_BASE_URL` o `BACKEND_URL`).
- Si falla el enlace proxy -> API, el cliente recibe `502`.

## Deteccion minima

1. Confirmar timestamp exacto del `502` en navegador.
2. Buscar en logs de `rapicredit`:
   - `Error en proxy para ...`
   - `ERROR en proxy durante la peticion ...`
   - campo `code` (agregado en respuesta JSON 502).
3. Cruce inmediato con logs/events de `pagos` en el mismo minuto.

## Diccionario de codigos

### `ECONNRESET`

- **Significa:** el upstream cerro socket durante la peticion.
- **Causas comunes:** deploy/restart, worker reciclado, saturacion puntual.
- **Accion:** revisar Events de `pagos` (restart/deploy) y confirmar estabilidad post-arranque.

### `ETIMEDOUT`

- **Significa:** el proxy espero respuesta y expiro.
- **Causas comunes:** endpoint pesado, DB lenta, locks, alto backlog.
- **Accion:** revisar endpoint afectado (latencia p95/p99, SQL lenta, volumen) y reducir carga transitoria.

### `ECONNREFUSED`

- **Significa:** no se pudo abrir conexion TCP al API.
- **Causas comunes:** API abajo o target incorrecto.
- **Accion:** validar `API_BASE_URL/BACKEND_URL`, health del servicio `pagos`, estado del dyno.

### `ENOTFOUND` / `EAI_AGAIN`

- **Significa:** fallo de resolucion DNS.
- **Causas comunes:** hostname mal escrito o error DNS temporal.
- **Accion:** corregir URL del API en entorno y redeploy del frontend Node.

### Errores TLS (`ERR_TLS_*`, `CERT_*`)

- **Significa:** handshake/certificado invalido.
- **Causas comunes:** URL no publica o dominio no coincidente.
- **Accion:** usar URL publica HTTPS valida del servicio API en Render.

## Checklist de triage (2 minutos)

1. **Leer `code`** del 502 en logs `rapicredit`.
2. **Cruzar con Events** de `pagos` en el mismo minuto.
3. **Clasificar incidente:**
   - `ECONNRESET` + restart -> reinicio upstream.
   - `ETIMEDOUT` sin restart -> rendimiento/consulta.
   - `ECONNREFUSED` -> indisponibilidad o URL mal configurada.
4. **Aplicar accion minima segura** (reinicio controlado, ajuste de variables, esperar warmup).

## Verificaciones de configuracion

- En servicio **rapicredit** (Node):
  - `API_BASE_URL=https://pagos-f2qf.onrender.com`
  - o `BACKEND_URL` equivalente.
- Evitar que `API_BASE_URL` apunte al mismo origen del frontend (autobucle).

## Indicadores de salud esperados

- `GET /api/v1/auth/me` sin 502 repetidos.
- `GET /api/v1/admin/tasas-cambio/estado` y `/hoy` estables.
- Para endpoints pesados (`listado-y-kpis`), reintentos ocasionales aceptables, pero no persistentes.

## Escalacion

Escalar a backend cuando:

- `ETIMEDOUT` recurrente en el mismo endpoint.
- `500` recurrentes del API (con tracebacks).
- reinicios frecuentes sin deploy planificado.

## Notas de seguridad operativa

- No habilitar reintentos automaticos en `POST` no idempotentes (riesgo de duplicar procesos).
- Priorizar mitigaciones de infraestructura/observabilidad antes de cambiar reglas de negocio.
