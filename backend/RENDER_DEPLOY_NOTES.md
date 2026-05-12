# Notas de despliegue en Render para `pagos-backend`

Este documento es la referencia operacional para el servicio web `pagos-backend` en
Render. Cubre **Start Command, comportamiento esperado, diagnóstico de 502 y operaciones
seguras**. La intención es evitar que un cambio bien intencionado en el Dashboard genere
restarts espontáneos por OOM o cortes de requests largos.

---

## 1. Start Command vigente (fuente de la verdad: `render.yaml`)

```
gunicorn app.main:app --bind 0.0.0.0:$PORT --workers 1 --timeout 920 --graceful-timeout 60 --max-requests 1500 --max-requests-jitter 300 --worker-class uvicorn.workers.UvicornWorker
```

### Justificación, flag por flag

| Flag | Valor | Por qué este valor concreto |
| --- | --- | --- |
| `--workers` | `1` | La app importa SDKs pesados (`google.generativeai`, `googleapiclient`, `google.auth`), 90+ modelos SQLAlchemy, `openpyxl`/`reportlab`/`weasyprint`/`Pillow` (PDF + Excel) y servicios `app.services.pagos_gmail.*`. Cada worker reserva 180-280 MB residentes solo por imports. `--workers 2` duplica esa línea base **y** duplica caches en proceso (`_cobros_listado_kpis_cache`, `cedulas_en_clientes`, `load_autorizados_bs_claves`, single-flight de `listado-y-kpis`). En plan con RAM ajustada (Starter 512 MB), esto causa OOM y `==> Instance restarted` espontáneos. |
| `--timeout` | `920` | El proxy Express (`frontend/server.js`) está configurado para esperar **hasta 900 s** en flujos largos (`notificaciones-prejudicial`, envíos masivos de notificaciones, Drive import bulk, exports Excel). Con `--timeout` menor, gunicorn mata al worker antes de que el flujo termine y el usuario ve un 502 falso (el job no continuó). Lista exacta de flujos largos: ver `is_long_job_path` en `backend/app/main.py` y la cascada `proxyTimeoutMs` en `frontend/server.js`. |
| `--graceful-timeout` | `60` | Tiempo que gunicorn da a workers para terminar requests activos cuando recibe `SIGTERM` (deploys, autosuspend, scale). Default es 30 s. PATCH `cobros/pagos-reportados/*/estado` con generación de PDF firmado o `aprobar` con envío de correo pueden tardar entre 5 y 40 s; 60 s evita que un deploy normal corte requests legítimas en curso. |
| `--max-requests` + `--max-requests-jitter` | `1500` / `300` | Recicla el worker cada ~1500-1800 peticiones para liberar RSS acumulado (allocations residuales después de barridos masivos, importadores Excel, conversiones PDF, sesiones SQLAlchemy con muchos detached objects). Gunicorn arranca el reemplazo, drena el viejo y reenruta sin downtime visible al usuario. Defensa frente a *memory creep* en uptime largo. |
| `--worker-class uvicorn.workers.UvicornWorker` | obligatorio | FastAPI es ASGI; sin esta clase los endpoints async no funcionan. |

### Lo que **no** se debe poner en el Start Command

- `--workers 2` o superior: ver tabla. La única excepción razonable sería subir el plan
  del servicio a Standard (≥2 GB RAM) Y validar que las caches en proceso no causan
  inconsistencias visibles entre workers; hoy no se ha probado.
- `--timeout 120` (o cualquier valor < 600): rompe los flujos largos catalogados en
  `is_long_job_path`. Si quieres limitar requests cortos, hazlo en el proxy Express
  por endpoint, no en gunicorn.
- `--preload`: en esta app no es seguro. Hay servicios que abren conexiones HTTP/SMTP/SQL
  en el import; `--preload` las comparte entre workers y rompe el patrón fork-safe.

### Cómo verificar el comando real en Render

1. Render Dashboard → `pagos-backend` → **Settings** → **Build & Deploy** → **Start Command**.
2. En los logs, al arrancar verás:
   ```
   ==> Running 'gunicorn app.main:app --bind 0.0.0.0:$PORT --workers 1 --timeout 920 ...'
   ```
   Si esa línea no coincide con la tabla anterior, hay un override manual en el panel.
3. La app **también lo detecta sola**: `_log_runtime_startcmd_diagnostics()` en
   `backend/app/main.py` inspecciona el cmdline del master gunicorn y emite un
   `[RuntimeConfig]` WARNING listando las diferencias. Buscar en logs:
   ```
   [RuntimeConfig] Start Command difiere de render.yaml. Editar en Render Dashboard...
   ```

---

## 2. Variables de entorno mínimas

Las que **deben** estar configuradas (manuales en el Dashboard, no en `render.yaml` por
seguridad):

- `DATABASE_URL` — Postgres de Render (interno o gestionado externo).
- `SECRET_KEY` — JWT signing.
- `RENDER` — Render la inyecta sola; la app la usa en `_startup_db_with_retry` para
  acortar reintentos cuando sabe que está sobre Render (acota timeout de deploy).

Las opcionales con efecto operacional importante:

- `ENABLE_AUTOMATIC_SCHEDULED_JOBS` (default `false` en este servicio): si `true` activa
  APScheduler (cron interno), refresco de dashboard a las 1:00/13:00 y proceso LIQUIDADO
  a las 21:00. Por defecto se deja desactivado en Render para no consumir RAM/CPU; los
  jobs se ejecutan manualmente desde la UI.
- `BACKEND_WARMUP_DELAY_MS`, `BACKEND_WARMUP_TIMEOUT_MS`,
  `DISABLE_BACKEND_WARMUP` — del lado del **frontend** (`server.js`), controlan el ping
  inicial al backend para reducir 502 en el primer request tras dormir el dyno.
- `RENDER_API_FALLBACK_URL` — fallback de URL del backend si el frontend pierde
  `API_BASE_URL` (raro, ya hay default).

---

## 3. Flujos largos catalogados (no acortar `--timeout` por debajo de estos)

| Endpoint | `proxyTimeoutMs` en `server.js` | Tiempo típico |
| --- | --- | --- |
| `notificaciones/enviar-caso-manual`, `notificaciones/enviar-todas` | 900 s (15 min) | Envíos masivos SMTP |
| `clientes/drive-import/importar` (bulk) | 600 s | Lectura completa de Drive |
| `clientes/drive-import/importar-fila`, `refresh-cache` | 300 s | Drive por fila / refresh |
| `conciliacion-sheet/sync-now`, `sync` | 300 s | Google Sheets + snapshot BD |
| `prestamos/candidatos-drive/refrescar`, `guardar-validados-100` | 300 s | Drive masivo |
| `cobros/public/enviar-reporte`, `infopagos/enviar-reporte`, `solicitar-codigo`, `cobros/escaner/extraer-comprobante`, `estado-cuenta/public/(solicitar\|verificar)-codigo` | 180 s | Gemini + SMTP + OTP |
| `exportar/*`, `drive-import/exportar-excel` | 180 s | Reportes Excel |
| `cobros/pagos-reportados/listado-y-kpis`, `.../{id}/estado`, `.../{id}` (PATCH editar y GET detalle), `.../{id}/comprobante`, `.../{id}/recibo.pdf` | 120 s | Listado con barrido, aprobar/rechazar, edición con dedup, descarga comprobante/recibo |
| Resto (CRUD normal) | 60 s | < 5 s |

Si añades un endpoint que puede superar 60 s, hay que extender la cascada en
`frontend/server.js` (variables `is*SlowPost`, `is*ReadHeavyGet`) **y** asegurarse de
que `--timeout` de gunicorn lo permite.

---

## 4. Cómo diagnosticar un 502 en producción

Orden de exploración recomendado:

1. **¿La instancia está viva ahora?**
   ```
   curl -i https://pagos-f2qf.onrender.com/api/v1/health/
   ```
   - 200 → backend OK; el 502 fue transitorio (deploy, restart, OOM puntual).
   - 502/timeout → el dyno está caído o reiniciándose ahora mismo.

2. **¿El proxy está vivo?**
   ```
   curl -i https://rapicredit.onrender.com/health
   ```
   Debe responder `{"status":"healthy","service":"rapicredit-frontend"}` instantáneo.
   Si tarda, el proxy Node está saturado o reiniciando (raro).

3. **¿Hay restart reciente?** En logs de `pagos-backend` buscar:
   ```
   ==> Instance srv-xxxxxxxxxx restarted
   ```
   Si aparece, el siguiente paso es ver **por qué**:
   - Justo antes hay slowdowns progresivos en endpoints sin relación → memoria
     (GC thrashing antes de OOM kill).
   - Hay `Worker (pid:XX) was sent SIGTERM!` precedido de `[CRITICAL] WORKER TIMEOUT` →
     algún request superó `--timeout` (revisar si llegó a `--timeout 120` por override).
   - Hay `[Errno 12] Cannot allocate memory` o se ve el cartel `Out of memory` → OOM,
     subir plan o reducir workers.
   - No hay nada → restart manual o por Render mantenimiento.

4. **¿Coincide con un deploy?** Buscar en logs `==> Deploying...` ± 1 min del 502.
   Durante deploy hay siempre 5-15 s de ventana 502. El cliente axios ya tiene retries
   para los endpoints más visibles (ver lista en `frontend/src/services/api.ts`,
   `isSafeTransientRetryGet`, `isCobrosPagoReportadoEstadoPatch`,
   `isCobrosPagoReportadoEditarPatch`).

5. **¿Es un endpoint lento que llega a `--timeout`?** Buscar el `request_id` en logs
   ANTES del 502:
   ```
   request method=POST path=/api/v1/notificaciones/enviar-todas status=200 elapsed_ms=140000 ...
   ```
   Si supera `--timeout`, gunicorn mata al worker. Solución: subir `--timeout` (la app
   ya lo tiene en 920 s), o mover el job a background con confirmación posterior.

---

## 5. Cambios de configuración seguros (sin reescribir lógica)

- **Subir plan**: si la RAM sigue ajustada con `--workers 1`, subir el servicio a un plan
  con más memoria. No requiere cambios de código.
- **Reducir auto-deploys**: en Settings, deshabilitar `Auto-Deploy` si haces deploys
  manuales para evitar restarts no planificados durante horas pico.
- **Ajustar `--max-requests` y `--max-requests-jitter`**: si los reciclajes son demasiado
  frecuentes (verás más mensajes `Booting worker` en logs), subir a `2500/500`.
  Si la RAM crece sin control entre reciclajes, bajar a `1000/200`.

## 6. Cambios que **no** son seguros sin coordinación

- Cambiar `--workers` a >1 sin antes verificar:
  - Plan con ≥2 GB RAM real disponible.
  - Que las caches en proceso (single-flight, `_cobros_listado_kpis_cache`,
    `load_autorizados_bs_claves`) no causen inconsistencias visibles cuando viven
    duplicadas en varios workers (algunas se invalidan vía función Python, no vía BD).
- `--preload`: ver sección 1.
- Activar `ENABLE_AUTOMATIC_SCHEDULED_JOBS=true` sin antes confirmar que el `scheduler_leader`
  está limpio en BD; si hay dos servicios apuntando al mismo Postgres, ambos pueden
  intentar ser leader.

---

## 7. Checklist breve cuando edites algo de Render

- [ ] Cambio aplicado en **`render.yaml`** (commit y push).
- [ ] Si afecta a `Start Command`, **también** actualizado en Render Dashboard
      (Settings → Build & Deploy → Start Command) **o** "Sync from render.yaml"
      activado en el blueprint.
- [ ] Variables sensibles añadidas en Dashboard (no en `render.yaml`).
- [ ] Deploy realizado.
- [ ] Logs revisados los primeros 2 min: aparece `Application startup complete` para el
      worker y `[RuntimeConfig] Start Command alineado con render.yaml.` (o el WARNING
      si todavía hay override).
- [ ] Health check OK: `curl https://pagos-f2qf.onrender.com/api/v1/health/`.
- [ ] Smoke desde el frontend: cargar listado de pagos-reportados, abrir un detalle,
      revisar que no hay 502 en consola del navegador.

---

## 8. Archivos relacionados

- `render.yaml` — Blueprint maestro.
- `backend/app/main.py` — `on_startup`, `_log_runtime_startcmd_diagnostics`, `is_long_job_path`.
- `frontend/server.js` — Proxy Express, cascada `proxyTimeoutMs` por endpoint.
- `frontend/src/services/api.ts` — Retries 502/503 con backoff por endpoint.
- `backend/RENDER_CONFIGURACION.md` — Notas operativas de WhatsApp (Meta callbacks).
