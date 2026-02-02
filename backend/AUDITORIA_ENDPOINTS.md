# Auditoría integral de endpoints – Backend FastAPI

**Fecha:** 2025-02-02  
**Prefijo API:** `/api/v1`  
**Total de endpoints revisados:** ~99 (incluyendo GET "" y GET "/" donde aplica)

---

## 1. Resumen ejecutivo

| Área | Estado | Observaciones |
|------|--------|---------------|
| **Datos reales vs stub** | Parcial | Clientes, tickets, notificaciones (clientes-retrasados, actualizar), configuración general/logo, dashboard (varios), notificaciones_tabs usan BD. Resto: pagos, kpis, cobranzas, auditoría, usuarios (env), validadores y varios de config/dashboard son stub. |
| **Uso de `get_db`** | Parcial | Módulos stub (pagos, kpis, cobranzas, auditoría, validadores, usuarios) no inyectan sesión. Configuración (notificaciones/envíos, sistema/completa, validadores/probar) y 7 endpoints finales del dashboard no usan `get_db`. |
| **Autenticación** | Crítico | No existe dependencia `get_current_user`. Solo `/auth/me` valida Bearer. Toda la API de negocio es accesible sin token. |
| **Consistencia** | Aceptable | Doble ruta `""` y `"/"` en listados; mezcla de `response_model` y respuestas sin tipar. |
| **Seguridad adicional** | Revisar | WhatsApp POST webhook con verificación de firma; auth sin rate limit; un endpoint con `body: dict` sin validación. |

---

## 2. Inventario por módulo

### 2.1 Raíz y salud (`main.py`)

| Método | Ruta | Auth | BD | Notas |
|--------|------|------|-----|-------|
| GET | `/` | No | No | Mensaje bienvenida |
| HEAD | `/` | No | No | Health |
| GET | `/health` | No | No | Salud básica |
| GET | `/health/db` | No | Sí (engine) | Verifica BD; 503 si falla |
| HEAD | `/health` | No | No | Salud |

**Observación:** Health sin auth es adecuado para probes.

---

### 2.2 Auth (`/api/v1/auth`)

| Método | Ruta | Auth | BD | Notas |
|--------|------|------|-----|-------|
| GET | `/status` | No | No | Indica si auth está configurado |
| POST | `/login` | No | No | Usuario desde env (ADMIN_EMAIL/PASSWORD) |
| POST | `/refresh` | No | No | Refresh token → access token |
| GET | `/me` | Bearer | No | Único endpoint que exige token |

**Observación:** No hay dependencia reutilizable tipo `get_current_user` para proteger el resto de la API.

---

### 2.3 WhatsApp (`/api/v1/whatsapp`)

| Método | Ruta | Auth | BD | Notas |
|--------|------|------|-----|-------|
| GET | `/webhook` | Query (hub) | No | Verificación Meta; token desde env |
| POST | `/webhook` | Firma X-Hub-Signature-256 | Sí | Procesa mensajes; usa `get_db` |

**Observación:** POST webhook verifica firma cuando `WHATSAPP_APP_SECRET` está configurado. Correcto.

---

### 2.4 Configuración (`/api/v1/configuracion`)

| Método | Ruta | Auth | BD | Notas |
|--------|------|------|-----|-------|
| GET | `/general` | No | Sí | Config general desde BD |
| PUT | `/general` | No | Sí | Actualiza config general |
| GET | `/logo/{filename}` | No | Sí | Logo desde BD (o disco si existe) |
| HEAD | `/logo/{filename}` | No | Sí | Idem |
| POST | `/upload-logo` | No | Sí | Sube logo |
| DELETE | `/logo` | No | Sí | Borra logo |
| GET | `/notificaciones/envios` | No | **No** | Stub en memoria |
| PUT | `/notificaciones/envios` | No | **No** | Stub en memoria |
| POST | `/validadores/probar` | No | **No** | Stub |
| GET | `/sistema/completa` | No | **No** | Usa `_config_stub` (no BD) |
| GET | `/sistema/categoria/{categoria}` | No | **No** | Idem |

Sub-routers:

- **AI** (`/configuracion/ai`): GET/PUT `/configuracion`, POST `/chat`, POST `/probar`, GET `/documentos`. Ninguno usa BD; config en memoria. API key solo desde env.
- **Email** (`/configuracion/email`): GET/PUT config, GET estado, POST probar, POST probar-imap. Todos con `get_db`.
- **WhatsApp** (`/configuracion/whatsapp`): GET/PUT `/configuracion`. Con `get_db`.

**Observación:** `/sistema/completa` y `/sistema/categoria/{categoria}` no cargan desde BD (usan stub). Para alinear con “datos reales”, convendría que al menos `/general` y sistema compartan origen (ej. BD).

---

### 2.5 Pagos (`/api/v1/pagos`)

| Método | Ruta | Auth | BD | Notas |
|--------|------|------|-----|-------|
| GET | `/kpis` | No | **No** | Stub (ceros) |
| GET | `/stats` | No | **No** | Stub (ceros) |

**Observación:** Contraviene la regla de “datos reales”. Deberían usar `Depends(get_db)` y consultar tablas de pagos/cuotas cuando existan.

---

### 2.6 Notificaciones (`/api/v1/notificaciones`)

| Método | Ruta | Auth | BD | Notas |
|--------|------|------|-----|-------|
| GET | `` | No | **No** | Lista vacía (sin tabla envíos) |
| GET | `/estadisticas/resumen` | No | **No** | Stub (no_leidas, total 0) |
| GET | `/clientes-retrasados` | No | Sí | Datos reales (Cuota, Cliente) |
| POST | `/actualizar` | No | Sí | Recalcula mora desde cuotas |

**Observación:** Lista y resumen son stub hasta tener tabla de notificaciones/envíos. `clientes-retrasados` y `actualizar` correctos.

---

### 2.7 Notificaciones por pestaña (previas, día-pago, retrasadas, prejudicial, mora-61)

Cada uno: GET (listado) y POST (enviar). Todos usan `get_db` y datos reales (Cuota, Cliente). Correcto.

---

### 2.8 Dashboard (`/api/v1/dashboard`)

| Con `get_db` | Sin `get_db` (stub) |
|--------------|----------------------|
| `/opciones-filtros`, `/kpis-principales`, `/admin`, `/financiamiento-tendencia-mensual`, `/morosidad-por-dia`, `/prestamos-por-concesionario`, `/prestamos-por-modelo`, `/financiamiento-por-rangos`, `/composicion-morosidad`, `/cobranza-fechas-especificas`, `/cobranzas-semanales`, `/morosidad-por-analista`, `/evolucion-morosidad`, `/evolucion-pagos` | `/cobranza-por-dia`, `/cobranzas-mensuales`, `/cobros-por-analista`, `/cobros-diarios`, `/cuentas-cobrar-tendencias`, `/distribucion-prestamos`, `/metricas-acumuladas` |

**Observación:** Los 7 últimos devuelven listas vacías y no reciben `db`. Para datos reales habría que inyectar `get_db` y consultar cuando existan modelos.

---

### 2.9 KPIs (`/api/v1/kpis`)

| Método | Ruta | Auth | BD | Notas |
|--------|------|------|-----|-------|
| GET | `/dashboard` | No | **No** | Stub (kpis [], totales 0) |

**Observación:** Mismo criterio que pagos: usar BD cuando exista modelo de negocio.

---

### 2.10 Auditoría (`/api/v1/auditoria`)

| Método | Ruta | Auth | BD | Notas |
|--------|------|------|-----|-------|
| GET | `` | No | **No** | Lista vacía, paginación stub |
| GET | `/stats` | No | **No** | Ceros |
| GET | `/exportar` | No | **No** | XLSX mínimo (stub) |
| GET | `/{auditoria_id}` | No | **No** | Siempre 404 (stub) |
| POST | `/registrar` | No | **No** | Acepta body, no persiste; devuelve item simulado |

**Observación:** Comentarios en código indican uso futuro de `Depends(get_db)` y tabla auditoría. Hoy todo es stub.

---

### 2.11 Cobranzas (`/api/v1/cobranzas`)

Todos los endpoints (GET resumen, diagnostico, clientes-atrasados, por-analista, montos-por-mes, informes/*, POST notificaciones/atrasos, PUT/DELETE prestamos/…/ml-impago) son **stub** y **no usan `get_db`**.

**Observación:** El docstring indica reemplazar por consultas reales cuando exista BD. Además, `PUT /prestamos/{prestamo_id}/ml-impago` recibe `body: dict` sin modelo Pydantic: riesgo de validación y documentación.

---

### 2.12 Clientes (`/api/v1/clientes`)

| Método | Ruta | Auth | BD | Notas |
|--------|------|------|-----|-------|
| GET | `` / `/` | No | Sí | Listado paginado real |
| GET | `/stats` | No | Sí | Estadísticas reales |
| GET | `/{cliente_id}` | No | Sí | Detalle |
| PATCH | `/{cliente_id}/estado` | No | Sí | Cambio estado |
| POST | `` | No | Sí | Crear (201) |
| PUT | `/{cliente_id}` | No | Sí | Actualizar |
| DELETE | `/{cliente_id}` | No | Sí | 204 |

**Observación:** Totalmente alineado con “datos reales” y uso de `get_db`. Sin protección por token.

---

### 2.13 Tickets (`/api/v1/tickets`)

| Método | Ruta | Auth | BD | Notas |
|--------|------|------|-----|-------|
| GET | `` / `/` | No | Sí | Listado real |
| GET | `/{ticket_id}` | No | Sí | Detalle |
| POST | `` | No | Sí | Crear + notificación email |
| PUT | `/{ticket_id}` | No | Sí | Actualizar + notificación |

**Observación:** Correcto uso de BD. Sin auth.

---

### 2.14 Comunicaciones (`/api/v1/comunicaciones`)

| Método | Ruta | Auth | BD | Notas |
|--------|------|------|-----|-------|
| GET | `` / `/` | No | Sí | Lista vacía (stub) pero inyecta `get_db` |
| GET | `/por-responder` | No | Sí | Lista vacía (stub), `get_db` |
| POST | `/crear-cliente-automatico` | No | Sí | Crea cliente real en BD |

**Observación:** Listados stub pero con sesión; crear-cliente correcto.

---

### 2.15 Validadores (`/api/v1/validadores`)

| Método | Ruta | Auth | BD | Notas |
|--------|------|------|-----|-------|
| GET | `/configuracion-validadores` | No | **No** | Stub (config estática) |

**Observación:** Aceptable como config de front; no requiere BD necesariamente.

---

### 2.16 Usuarios (`/api/v1/usuarios`)

| Método | Ruta | Auth | BD | Notas |
|--------|------|------|-----|-------|
| GET | `` / `/` | No | No | Lista desde env (ADMIN_EMAIL); paginación simbólica |

**Observación:** Diseño consciente “sin tabla users”. No requiere BD.

---

## 3. Hallazgos por categoría

### 3.1 Datos reales (regla workspace)

- **Cumplen:** clientes, tickets, notificaciones (clientes-retrasados, actualizar), notificaciones_tabs, configuración general y logo, dashboard (la mayoría con `get_db`), comunicaciones crear-cliente.
- **No cumplen (stub sin BD):** pagos (kpis, stats), kpis (dashboard), cobranzas (todos), auditoría (todos), notificaciones (lista y estadisticas/resumen), configuración (notificaciones/envíos, sistema/completa, sistema/categoria), validadores (config), dashboard (cobranza-por-dia, cobranzas-mensuales, cobros-por-analista, cobros-diarios, cuentas-cobrar-tendencias, distribucion-prestamos, metricas-acumuladas).

### 3.2 Inyección de sesión `get_db`

- **Faltan `get_db`** donde se esperaría BD para datos reales:
  - `pagos.py`: ambos endpoints.
  - `kpis.py`: dashboard.
  - `cobranzas.py`: todos.
  - `auditoria.py`: todos.
  - `notificaciones.py`: GET `` y GET `/estadisticas/resumen`.
  - `configuracion.py`: GET/PUT `/notificaciones/envios`, POST `/validadores/probar`, GET `/sistema/completa`, GET `/sistema/categoria/{categoria}`.
  - `dashboard.py`: los 7 endpoints finales (cobranza-por-dia, cobranzas-mensuales, etc.).
- **Config AI:** en memoria por diseño; persistencia futura podría usar BD.

### 3.3 Autenticación y autorización

- **Crítico:** No existe una dependencia `get_current_user` (o similar) que valide el Bearer y devuelva el usuario. Solo `/auth/me` usa `HTTPBearer`.
- **Consecuencia:** Cualquier cliente puede llamar sin token a:
  - clientes (CRUD, stats),
  - tickets (CRUD),
  - configuración (general, logo, envíos, sistema),
  - dashboard, kpis, pagos, cobranzas, auditoría, notificaciones, comunicaciones, usuarios, validadores.
- **Recomendación:** Introducir `get_current_user` (o equivalente) y aplicarlo a todos los endpoints de negocio excepto auth, health y webhooks externos (WhatsApp).

### 3.4 Consistencia de API

- **Rutas:** Varios listados exponen `""` y `"/"` (clientes, tickets, usuarios, comunicaciones, notificaciones). Útil para compatibilidad; `include_in_schema=False` en `"/"` está bien.
- **Respuestas:** Mezcla de `response_model=dict` vs modelos Pydantic (p. ej. ClienteResponse, AuditoriaListResponse). Unificar cuando sea posible mejora OpenAPI y tipo.
- **Paginación:** Distintos nombres: `page`/`per_page`, `page`/`page_size`, `skip`/`limit`. Estandarizar (p. ej. `page`, `page_size`) facilita al frontend.

### 3.5 Seguridad y validación

- **WhatsApp:** Verificación de firma en POST webhook cuando hay `WHATSAPP_APP_SECRET`. Correcto.
- **Auth:** Login/refresh sin rate limiting; vulnerable a fuerza bruta si se expone.
- **Cobranzas:** `PUT /prestamos/{prestamo_id}/ml-impago` con `body: dict` sin modelo: definir Pydantic (p. ej. nivel_riesgo, probabilidad_impago) y usarlo como body.
- **Path/query:** Uso de `Query` y path params en general correcto; validación de IDs (positivos, existencia) ya aplicada donde se ha revisado (p. ej. clientes, tickets).

### 3.6 Documentación y códigos HTTP

- **Docs:** Varios endpoints tienen docstring; otros son mínimos. Añadir `summary`/`description` en los que falte mejora /docs y /redoc.
- **Códigos:** 201 en creaciones, 204 en eliminaciones, 404 en recurso no encontrado, 503 en health/db. Coherente en lo revisado. Auditoría devuelve 404 en `GET /{id}` por diseño (stub).

---

## 4. Recomendaciones prioritarias

1. **Alta – Autenticación**
   - Crear dependencia `get_current_user` que decodifique el Bearer (reutilizando lógica de `/auth/me`) y opcionalmente `get_current_user_optional` para rutas mixtas.
   - Proteger con `Depends(get_current_user)` todos los endpoints de negocio (clientes, tickets, dashboard, configuración, cobranzas, auditoría, notificaciones, comunicaciones, usuarios, pagos, kpis), dejando públicos: `/`, `/health`, `/health/db`, `/api/v1/auth/*`, `/api/v1/whatsapp/webhook`.

2. **Alta – Datos reales y `get_db`**
   - En **pagos** y **kpis**: inyectar `get_db` y, cuando existan tablas de pagos/cuotas/prestamos, devolver KPIs y stats desde BD.
   - En **cobranzas**: inyectar `get_db` en todos los endpoints y sustituir stubs por consultas reales según modelos disponibles.
   - En **auditoría**: crear modelo/tabla de auditoría, inyectar `get_db` en listado, stats, exportar, GET por id y POST registrar; persistir en BD.
   - En **dashboard**: añadir `get_db` a los 7 endpoints que hoy no lo tienen y, cuando haya datos, devolver series reales en lugar de listas vacías.
   - En **configuracion**: si “sistema/completa” y “sistema/categoria” deben ser datos reales, cargarlos desde BD (o desde la misma fuente que `/general`).

3. **Media – Validación y tipos**
   - Reemplazar `body: dict` en `PUT /cobranzas/prestamos/{prestamo_id}/ml-impago` por un modelo Pydantic y usarlo en el endpoint.
   - Revisar otros bodies que puedan estar como `dict` y tiparlos con Pydantic.

4. **Media – Seguridad**
   - Valorar rate limiting en `/auth/login` (y opcionalmente `/auth/refresh`) para mitigar fuerza bruta.
   - Mantener y documentar que la API key de AI/OpenRouter solo se usa en backend y nunca se expone al frontend.

5. **Baja – Consistencia**
   - Estandarizar nombres de paginación en toda la API (p. ej. `page`, `page_size`).
   - Donde tenga sentido, unificar `response_model` con esquemas Pydantic en lugar de `dict`.

---

## 5. Checklist rápido por endpoint

Para cada endpoint nuevo o modificado, comprobar:

- [ ] ¿Debe devolver datos reales? → Usar `Depends(get_db)` y consultas a BD.
- [ ] ¿Debe estar protegido? → Usar `Depends(get_current_user)` (cuando exista).
- [ ] Body de entrada → Modelo Pydantic, no `dict` genérico.
- [ ] Respuesta → Preferir `response_model` con tipo conocido.
- [ ] Docstring o `summary` para documentación.
- [ ] Código HTTP adecuado (201 creación, 204 borrado, 404 no encontrado, 503 indisponibilidad).

---

*Documento generado a partir del análisis del código en `backend/app`.*
