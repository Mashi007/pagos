# Auditoría integral: proceso Pagos Gmail (pipeline, endpoints, BD, scheduler)

**Alcance:** Pipeline Gmail → Drive → Gemini → Sheets; endpoints bajo `/api/v1/pagos/gmail`; conexión BD; credenciales; scheduler.

---

## 1. Endpoints

| Método | Ruta (base: `/api/v1`) | Auth | Descripción |
|--------|-------------------------|------|-------------|
| POST   | `/pagos/gmail/run-now`  | Sí (Bearer) | Ejecuta el pipeline una vez. Query: `force` (default true). 409 si ya hay sync en curso; 503 si no hay credenciales. |
| GET    | `/pagos/gmail/status`   | Sí | Devuelve última ejecución y próxima aproximada (por intervalo cron). |
| GET    | `/pagos/gmail/download-excel` | Sí | Excel del día (por defecto hoy America/Caracas). Query: `fecha` (YYYY-MM-DD) opcional. |
| POST   | `/pagos/gmail/confirmar-dia`  | Sí | Body: `confirmado`, `fecha` opcional. Si confirmado=true, borra ítems del día en BD. |

**Seguridad:** Todos los endpoints del router usan `dependencies=[Depends(get_current_user)]`; sin token válido se devuelve 401.

**Observaciones:**
- `run-now` puede tardar 20–120 s; el middleware no lo marca como "slow" para no generar WARNING en logs.
- `download-excel` lee solo de BD (`pagos_gmail_sync_item`); no accede a Google Sheets en la descarga.
- `confirmar-dia` hace `DELETE` por `sheet_name`; no toca `pagos_gmail_sync` (los registros de ejecución se mantienen).

---

## 2. Base de datos

### 2.1 Conexión (`app/core/database.py`)

- **Engine:** `create_engine(DATABASE_URL)` con:
  - `pool_pre_ping=True` (comprueba conexión antes de usar).
  - `pool_size=10`, `max_overflow=20`, `pool_recycle=1800`, `pool_timeout=30`.
  - `connect_args`: timeout 15 s, keepalives TCP, `application_name=rapicredit_backend`.
- **URL:** Se normaliza `postgres://` → `postgresql://` para compatibilidad con SQLAlchemy.
- **Sesión:** `SessionLocal(autocommit=False, autoflush=False, expire_on_commit=False)`.
- **Dependencia:** `get_db()` abre una sesión por request y la cierra en un `finally` (patrón correcto).

### 2.2 Modelos (`app/models/pagos_gmail_sync.py`)

| Tabla                 | Uso |
|-----------------------|-----|
| `pagos_gmail_sync`    | Una fila por ejecución del pipeline: `id`, `started_at`, `finished_at`, `status` (running/success/error), `emails_processed`, `files_processed`, `error_message`. |
| `pagos_gmail_sync_item` | Una fila por archivo/correo procesado: `sync_id` (FK a `pagos_gmail_sync.id` con `ondelete="CASCADE"`), `correo_origen`, `asunto`, `fecha_pago`, `cedula`, `monto`, `numero_referencia`, `drive_file_id`, `drive_link`, `sheet_name`, `created_at`. |

**Integridad:** La FK con CASCADE evita ítems huérfanos si se borrara un sync (en la práctica no se borran syncs; `confirmar-dia` solo borra ítems por `sheet_name`).

### 2.3 Uso de la sesión

- **Endpoints:** Reciben `db: Session = Depends(get_db)`; una sesión por request; se cierra al terminar la petición.
- **Pipeline (`run_pipeline(db)`):** Usa la misma sesión durante toda la ejecución; hace `db.add(sync)`, `db.commit()`, `db.refresh(sync)` al inicio; al final (éxito o excepción) actualiza `sync` y hace `db.commit()`. Correcto.
- **Scheduler:** `_job_pagos_gmail_pipeline()` crea una sesión con `SessionLocal()`, la pasa a `run_pipeline(db)` y llama a `db.close()` en un `finally`. No usa `get_db` (no hay request). Correcto.

### 2.4 Health check BD

- **GET `/health/db`:** Abre una conexión con `engine.connect()`, ejecuta `SELECT 1`, cierra. Responde 200 con `{"database": "connected"}` o 503 con error. No usa sesión ORM; adecuado para comprobar conectividad.

---

## 3. Pipeline (Gmail → Drive → Gemini → Sheets)

**Entrada:** `run_pipeline(db: Session)`.

**Flujo resumido:**
1. Obtener credenciales (archivo de tokens con env `GOOGLE_*` o fallback a BD Informe de pagos).
2. Construir clientes Gmail, Drive y Sheets con las mismas credenciales.
3. Crear fila en `pagos_gmail_sync` (status=running) y hacer commit.
4. Listar correos no leídos con adjuntos y cuyo asunto contiene un email (`list_unread_with_attachments`).
5. Opcionalmente limitar a `PAGOS_GMAIL_MAX_EMAILS_PER_RUN` (0 = sin límite).
6. Por cada mensaje: obtener fecha del mensaje, crear/obtener carpeta Drive y hoja Sheets por fecha; extraer adjuntos/imágenes (incl. inline y base64 en HTML); por cada adjunto: subir a Drive, extraer datos con Gemini, escribir fila en Sheets y en `pagos_gmail_sync_item`; pausa `PAGOS_GMAIL_DELAY_BETWEEN_GEMINI_SECONDS` entre llamadas a Gemini; marcar correo como leído.
7. Actualizar `pagos_gmail_sync` (finished_at, status success/error, contadores, error_message) y commit.

**Manejo de errores:** Cualquier excepción se captura; se actualiza el sync a status=error y se hace commit. No se hace rollback de la sesión entera (los ítems ya guardados se mantienen; el sync queda con estado de error). Aceptable para trazabilidad.

**Datos sensibles:** Credenciales y tokens no se escriben en BD en este flujo; las credenciales vienen de env o de la configuración de Informe de pagos en BD (encriptada si está configurado).

---

## 4. Credenciales

- **Origen 1:** Variables de entorno `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` y archivo en `GMAIL_TOKENS_PATH` (con `refresh_token`). Scopes: Gmail readonly/modify, Drive, Drive.file, Sheets.
- **Origen 2 (fallback):** Configuración Informe de pagos en BD (OAuth); scopes compatibles con "Conectar con Google" (`SCOPES_INFORME_PAGOS_GMAIL`). Se registra en log INFO cuando se usan credenciales desde BD.
- Si no hay credenciales válidas, el pipeline devuelve `(None, "no_credentials")` y el endpoint responde 503 con mensaje orientativo.
- **Gemini:** `GEMINI_API_KEY` y `GEMINI_MODEL` desde settings; necesarios para extraer datos de comprobantes. Sin clave, los campos extraídos quedan en "No encontrado" pero el pipeline sigue (sube a Drive y escribe fila).

---

## 5. Scheduler

- **Inicio:** `start_scheduler()` se llama en el lifespan de la aplicación (al arrancar).
- **Job relevante:** `_job_pagos_gmail_pipeline`, con `IntervalTrigger(minutes=settings.PAGOS_GMAIL_CRON_MINUTES)` (ej. 15).
- **Lógica del job:** Abre sesión con `SessionLocal()`, comprueba `_is_pipeline_running(db)` y `_last_run_too_recent(db)`; si todo OK llama a `run_pipeline(db)`; cierra la sesión en `finally`. No hace rollback explícito; el pipeline ya hace commit en todos los casos.
- **Parada:** En el shutdown del lifespan se llama a `stop_scheduler()`; el scheduler se apaga correctamente.

---

## 6. Configuración (variables de entorno)

| Variable | Uso |
|----------|-----|
| `DATABASE_URL` | Conexión PostgreSQL (obligatoria). |
| `PAGOS_GMAIL_CRON_MINUTES` | Intervalo del cron (minutos). |
| `PAGOS_GMAIL_DELAY_BETWEEN_GEMINI_SECONDS` | Pausa entre llamadas a Gemini. |
| `PAGOS_GMAIL_MAX_EMAILS_PER_RUN` | Límite de correos por ejecución (0 = sin límite). |
| `GEMINI_API_KEY`, `GEMINI_MODEL` | Extracción de datos en comprobantes. |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GMAIL_TOKENS_PATH` | Opcional si se usan credenciales desde BD (Informe de pagos). |
| `DRIVE_ROOT_FOLDER_ID` | Carpeta raíz en Drive para carpetas por fecha. |

---

## 7. Recomendaciones

1. **BD:** Mantener `pool_pre_ping` y `pool_recycle`; en Render/entornos cloud evita conexiones rotas. Ya está bien configurado.
2. **Pipeline:** Si se desea "todo o nada" por ejecución, se podría envolver el cuerpo del pipeline en un único try/except y hacer rollback en caso de error (y no persistir ítems parciales); hoy el diseño prioriza no perder lo ya procesado y dejar el sync en error.
3. **Confirmar-día:** Solo borra ítems; no borra filas de `pagos_gmail_sync`. Los registros de ejecución quedan para auditoría; correcto.
4. **Logs:** Credenciales desde BD se registran a nivel INFO; mensajes de "no archivo de tokens" están a DEBUG para no generar ruido cuando la configuración es solo por BD.
5. **Health:** `/health/db` es adecuado para comprobar la BD; no incluye comprobación de tablas `pagos_gmail_*` (no necesario para "conectividad").

---

## 8. Resumen de estado

| Área | Estado | Notas |
|------|--------|--------|
| Endpoints | OK | Auth, códigos HTTP y uso de BD correctos. |
| Conexión BD | OK | Pool, timezone, get_db y cierre de sesión correctos. |
| Modelos / FK | OK | CASCADE en sync_item; tablas alineadas con uso. |
| Pipeline | OK | Sesión única, commit en éxito y error, credenciales y Gemini integrados. |
| Scheduler | OK | Sesión propia, cierre en finally, intervalo configurable. |
| Credenciales | OK | Env + fallback BD; log claro cuando se usa BD. |
| Health BD | OK | GET /health/db verifica conexión. |

**Conclusión:** El proceso está bien alineado con los requisitos (datos reales desde BD, sin stubs en estos endpoints). No se detectan fallos de integridad ni fugas de sesión. Las mejoras sugeridas son opcionales (rollback atómico por ejecución y/o health más específico si se desea).
