# Auditoría integral con trazabilidad: /pagos/rapicredit-estadocuenta

**URL auditada:** https://rapicredit.onrender.com/pagos/rapicredit-estadocuenta  
**Alcance:** Trazabilidad de inicio a fin, paso a paso, desde la entrada del usuario hasta la visualización/descarga del PDF de estado de cuenta (flujo con código por email).

---

## 1. Resumen ejecutivo

| Aspecto | Detalle |
|--------|--------|
| **URL producción** | `https://rapicredit.onrender.com/pagos/rapicredit-estadocuenta` |
| **Ruta frontend** | Path relativo al basename: `rapicredit-estadocuenta` (basename `/pagos` en Vite/React Router) |
| **Tipo** | Flujo público, sin login; validación por cédula + código enviado al email |
| **Pasos usuario** | 0: Bienvenida → 1: Ingresar cédula y solicitar código → 2: Ingresar código → 3: Ver/descargar PDF |
| **APIs usadas** | `POST /api/v1/estado-cuenta/public/solicitar-codigo`, `POST /api/v1/estado-cuenta/public/verificar-codigo` |
| **BD** | `clientes`, `prestamos`, `cuota`, `estado_cuenta_codigos` |
| **Seguridad** | Sin auth; rate limit por IP; código de un solo uso con expiración 2 h |

---

## 2. Diagrama de flujo (inicio a fin)

```mermaid
sequenceDiagram
    participant U as Usuario
    participant Nav as Navegador
    participant Server as server.js (Express)
    participant SPA as React (index.html)
    participant App as App.tsx
    participant Page as EstadoCuentaPublicoPage
    participant API as estadoCuentaService
    participant Backend as FastAPI
    participant DB as Base de datos
    participant Email as send_email

    Note over U,Email: PASO 0 — Entrada
    U->>Nav: Abre https://rapicredit.onrender.com/pagos/rapicredit-estadocuenta
    Nav->>Server: GET /pagos/rapicredit-estadocuenta
    Server->>Server: No es estático → SPA fallback
    Server->>Nav: 200 index.html (base /pagos/, assets reescritos)
    Nav->>SPA: Carga React
    App->>App: pathname = rapicredit-estadocuenta ∈ PUBLIC_PATHS → sin redirect login
    App->>Page: Route rapicredit-estadocuenta → EstadoCuentaPublicoPage
    Page->>Page: useEffect: sessionStorage PUBLIC_FLOW_SESSION_KEY + _path
    Page->>U: Pantalla bienvenida (step 0)
    U->>Page: Clic "Iniciar" → setStep(1)

    Note over U,Email: PASO 1 — Solicitar código
    U->>Page: Ingresa cédula, clic "Enviar código al correo"
    Page->>Page: normalizarCedulaParaProcesar() → handleSolicitarCodigo()
    Page->>API: solicitarCodigo(cedula)
    API->>Server: POST /api/v1/estado-cuenta/public/solicitar-codigo { cedula }
    Server->>Backend: Proxy /api → API_BASE_URL
    Backend->>Backend: check_rate_limit_estado_cuenta_solicitar(ip)
    Backend->>Backend: validate_cedula, _cedula_lookup, _obtener_datos_pdf
    Backend->>DB: SELECT clientes; INSERT estado_cuenta_codigos
    Backend->>Email: send_email(código 6 dígitos)
    Backend->>API: 200 { ok: true, mensaje }
    Page->>Page: setStep(2), setCedula, setMensajeEnvio
    Page->>U: Pantalla "Ingrese código de 6 dígitos"

    Note over U,Email: PASO 2 — Verificar código y obtener PDF
    U->>Page: Ingresa código, clic "Ver estado de cuenta"
    Page->>API: verificarCodigo(cedula, codigo)
    API->>Server: POST /api/v1/estado-cuenta/public/verificar-codigo { cedula, codigo }
    Server->>Backend: Proxy
    Backend->>Backend: check_rate_limit_estado_cuenta_verificar(ip)
    Backend->>DB: SELECT EstadoCuentaCodigo (cedula, codigo, no expirado, no usado)
    Backend->>DB: _obtener_datos_pdf → clientes, prestamos, cuota
    Backend->>Backend: generar_pdf_estado_cuenta(...) → bytes
    Backend->>DB: UPDATE estado_cuenta_codigos SET usado = true
    Backend->>API: 200 { ok: true, pdf_base64 }
    Page->>Page: setPdfDataUrl, setPdfBlobUrl, setStep(3)
    Page->>U: iframe PDF + botón Descargar PDF

    Note over U,Email: PASO 3 — Solo cliente (sin más llamadas)
    U->>Page: Ver PDF, "Descargar PDF", "Termina" o "Consultar otra cédula"
```

---

## 3. Trazabilidad paso a paso (detalle)

### Paso 0 — Entrada y bienvenida

| # | Componente | Archivo / Ubicación | Línea aprox. | Acción |
|---|------------|---------------------|--------------|--------|
| 0.1 | URL | Navegador | — | Usuario abre `https://rapicredit.onrender.com/pagos/rapicredit-estadocuenta` |
| 0.2 | Servidor estático | `frontend/server.js` | 399-430 | Request a `/pagos/rapicredit-estadocuenta` no coincide con estáticos; SPA fallback sirve `index.html` (reemplazo `/assets/` → `/pagos/assets/`) |
| 0.3 | Router React | `frontend/src/App.tsx` | 14, 21-24 | `PUBLIC_PATHS` incluye `'/rapicredit-estadocuenta'`; `pathname` normalizado con `BASE_PATH` → no redirige a login |
| 0.4 | Ruta | `frontend/src/App.tsx` | 148 | `<Route path="rapicredit-estadocuenta" element={<EstadoCuentaPublicoPage />} />` |
| 0.5 | Página | `frontend/src/pages/EstadoCuentaPublicoPage.tsx` | 71-218 | Monta componente; `step === 0` → pantalla de bienvenida (logo, texto, botón "Iniciar") |
| 0.6 | Sesión pública | `EstadoCuentaPublicoPage.tsx` | 112-115 | `useEffect`: `sessionStorage.setItem(PUBLIC_FLOW_SESSION_KEY, '1')` y `_path` = `'rapicredit-estadocuenta'` |

**Configuración relevante:**

- `frontend/src/config/env.ts`: `BASE_PATH` (desde `import.meta.env.BASE_URL` o `/pagos`), `PUBLIC_FLOW_SESSION_KEY = 'public_flow_active'`, `env.API_URL` (en producción `''` para usar proxy).
- `frontend/server.js`: `FRONTEND_BASE = '/pagos'` (334), proxy `/api` → `API_BASE_URL` (119-250), pathRewrite `/api${path}` (142).

**Salida paso 0:** Usuario ve bienvenida y pulsa "Iniciar" → `setStep(1)`.

---

### Paso 1 — Ingresar cédula y solicitar código

| # | Componente | Archivo / Ubicación | Línea aprox. | Acción |
|---|------------|---------------------|--------------|--------|
| 1.1 | UI | `EstadoCuentaPublicoPage.tsx` | 219-255 | `step === 1`: input cédula, botones "Atrás" y "Enviar código al correo" |
| 1.2 | Normalización | `EstadoCuentaPublicoPage.tsx` | 16-24 | `normalizarCedulaParaProcesar()`: quita espacios, guiones, puntos; V/E/G/J + 6–11 dígitos; si solo dígitos antepone "V" |
| 1.3 | Submit | `EstadoCuentaPublicoPage.tsx` | 116-140 | `handleSolicitarCodigo()`: si válido → `solicitarCodigo(cedulaEnviar)` |
| 1.4 | Servicio frontend | `frontend/src/services/estadoCuentaService.ts` | 46-60 | `solicitarCodigo(cedula)` → `POST ${API}/api/v1/estado-cuenta/public/solicitar-codigo` con body `{ cedula }` |
| 1.5 | Proxy | `frontend/server.js` | 119-250 | Rutas `/api/*` → `createProxyMiddleware` hacia `API_BASE_URL`; path reescrito como `/api/v1/estado-cuenta/public/solicitar-codigo` |
| 1.6 | Backend router | `backend/app/api/v1/__init__.py` | 50-53 | Incluye `estado_cuenta_publico.router` con `prefix="/estado-cuenta/public"` |
| 1.7 | Endpoint | `backend/app/api/v1/endpoints/estado_cuenta_publico.py` | 253-307 | `solicitar_codigo_estado_cuenta()`: `POST /solicitar-codigo`; body `SolicitarCodigoRequest(cedula)` |
| 1.8 | Rate limit | `backend/app/core/cobros_public_rate_limit.py` | 97-109 | `check_rate_limit_estado_cuenta_solicitar(ip)`: 5 solicitudes/hora por IP; 429 si exceso |
| 1.9 | Validación cédula | `estado_cuenta_publico.py` + `validadores.py` | 270-274, 84-90 | `validate_cedula(cedula)`, `_cedula_lookup(cedula)` |
| 1.10 | BD – cliente | `estado_cuenta_publico.py` | 96-102, 276-281 | `_obtener_datos_pdf(db, cedula_lookup)`; si no hay cliente o no hay email → respuesta OK genérica (no revela existencia) |
| 1.11 | Código y persistencia | `estado_cuenta_publico.py` | 283-295 | `_generar_codigo_6()`, `EstadoCuentaCodigo(...)`, `db.add(row)`, `db.commit()` |
| 1.12 | Email | `estado_cuenta_publico.py` | 296-303 | `send_email([email], "Codigo para estado de cuenta - RapiCredit", cuerpo)`; si falla, solo log warning |
| 1.13 | Respuesta | `estado_cuenta_publico.py` | 305-307 | `SolicitarCodigoResponse(ok=True, mensaje="Si la cedula...")`; frontend `setStep(2)`, `setCedula`, `setMensajeEnvio` |

**Tablas BD en paso 1:** `estado_cuenta_codigos` (INSERT). Lectura: `clientes` (y en `_obtener_datos_pdf` se usan también para verificar email).

**Salida paso 1:** Usuario en paso 2 (pantalla para ingresar código de 6 dígitos).

---

### Paso 2 — Ingresar código y verificar

| # | Componente | Archivo / Ubicación | Línea aprox. | Acción |
|---|------------|---------------------|--------------|--------|
| 2.1 | UI | `EstadoCuentaPublicoPage.tsx` | 257-292 | `step === 2`: input código 6 dígitos, "Atrás", "Ver estado de cuenta" |
| 2.2 | Submit | `EstadoCuentaPublicoPage.tsx` | 145-174 | `handleVerificarCodigo()` → `verificarCodigo(cedula, codigo.trim())` |
| 2.3 | Servicio frontend | `estadoCuentaService.ts` | 63-76 | `POST /api/v1/estado-cuenta/public/verificar-codigo` body `{ cedula, codigo }` |
| 2.4 | Proxy | `frontend/server.js` | (igual que 1.5) | `/api` → backend |
| 2.5 | Endpoint | `estado_cuenta_publico.py` | 312-371 | `verificar_codigo_estado_cuenta()`: body `VerificarCodigoRequest(cedula, codigo)` |
| 2.6 | Rate limit | `cobros_public_rate_limit.py` | 36-42 | `check_rate_limit_estado_cuenta_verificar(ip)`: 15 intentos / 15 min por IP; 429 si exceso |
| 2.7 | Buscar código | `estado_cuenta_publico.py` | 331-344 | `select(EstadoCuentaCodigo).where(cedula_normalizada, codigo, expira_en > now, usado == False)`; si no hay fila → `ok=False, error="Codigo invalido o expirado..."` |
| 2.8 | Datos para PDF | `estado_cuenta_publico.py` | 347-356 | `_obtener_datos_pdf(db, cedula_lookup)` → cliente, préstamos, cuotas pendientes, total_pendiente, amortizaciones |
| 2.9 | Generar PDF | `backend/app/services/estado_cuenta_pdf.py` | 22-288 | `generar_pdf_estado_cuenta(...)` (ReportLab: logo, datos cliente, tablas, amortización) → bytes |
| 2.10 | Marcar código usado | `estado_cuenta_publico.py` | 368-369 | `rec.usado = True`; `db.commit()` |
| 2.11 | Respuesta | `estado_cuenta_publico.py` | 371 | `VerificarCodigoResponse(ok=True, pdf_base64=base64.encode(pdf_bytes))` |
| 2.12 | Frontend | `EstadoCuentaPublicoPage.tsx` | 157-168 | `setPdfDataUrl('data:application/pdf;base64,'+res.pdf_base64)`; opcional blob URL para iframe; `setStep(3)` |

**Tablas BD en paso 2:** Lectura: `clientes`, `prestamos`, `cuota`. Lectura/escritura: `estado_cuenta_codigos` (UPDATE `usado=true`).

**Salida paso 2:** Usuario en paso 3 (pantalla con PDF).

---

### Paso 3 — Visualización y descarga del PDF

| # | Componente | Archivo / Ubicación | Línea aprox. | Acción |
|---|------------|---------------------|--------------|--------|
| 3.1 | UI | `EstadoCuentaPublicoPage.tsx` | 295-341 | iframe `src={pdfBlobUrl \|\| pdfDataUrl}`; botones "Termina", "Consultar otra cédula"; enlace "Descargar PDF" con `download="estado_cuenta_....pdf"` |
| 3.2 | Sin llamadas API | — | — | Todo el contenido del PDF está en memoria (base64/blob); no hay nuevas peticiones al backend |

---

## 4. Cadena de archivos y dependencias

### Frontend

```
URL /pagos/rapicredit-estadocuenta
  → frontend/server.js (SPA fallback sendSpaIndex, FRONTEND_BASE=/pagos)
  → index.html → React app
  → main.tsx (BrowserRouter basename=BASE_PATH)
  → App.tsx (Route rapicredit-estadocuenta → EstadoCuentaPublicoPage)
  → pages/EstadoCuentaPublicoPage.tsx
       ├─ config/env.ts (PUBLIC_FLOW_SESSION_KEY, BASE_PATH, env.API_URL)
       └─ services/estadoCuentaService.ts
            ├─ solicitarCodigo() → POST /api/v1/estado-cuenta/public/solicitar-codigo
            └─ verificarCodigo()  → POST /api/v1/estado-cuenta/public/verificar-codigo
```

### Backend

```
Request /api/v1/estado-cuenta/public/*
  → backend app (FastAPI)
  → api/v1/__init__.py (include_router estado_cuenta_publico, prefix /estado-cuenta/public)
  → endpoints/estado_cuenta_publico.py
       ├─ validadores.validate_cedula (validadores.py)
       ├─ app.core.cobros_public_rate_limit (get_client_ip, check_rate_limit_*)
       ├─ app.core.database.get_db
       ├─ app.models: Cliente, Prestamo, Cuota, EstadoCuentaCodigo
       ├─ app.core.email.send_email
       └─ app.services.estado_cuenta_pdf.generar_pdf_estado_cuenta
  → estado_cuenta_pdf.py (ReportLab, backend/static/logo.png)
```

### Base de datos

| Tabla | Uso en flujo estado de cuenta público |
|-------|----------------------------------------|
| `clientes` | Lookup por cédula normalizada; nombre, email para código y PDF |
| `prestamos` | Lista de préstamos del cliente; estado para filtrar amortizaciones |
| `cuota` | Cuotas pendientes (`fecha_pago` IS NULL); amortización por préstamo |
| `estado_cuenta_codigos` | INSERT al solicitar código; SELECT + UPDATE(usado) al verificar |

---

## 5. Endpoints API (prefijo `/api/v1/estado-cuenta/public`)

| Método | Ruta | Rate limit | Descripción |
|--------|------|------------|-------------|
| GET | `/validar-cedula?cedula=...` | 30/min IP | Valida formato y existencia en `clientes`; retorna nombre, email. No usado en flujo actual (flujo con código). |
| POST | `/solicitar-codigo` | 5/hora IP | Body `{ cedula }`. Genera código 6 dígitos, guarda en `estado_cuenta_codigos`, envía por email. Respuesta genérica. |
| POST | `/verificar-codigo` | 15/15 min IP | Body `{ cedula, codigo }`. Verifica código, genera PDF, marca código usado, devuelve `pdf_base64`. |
| POST | `/solicitar-estado-cuenta` | 5/hora IP | Body `{ cedula }`. Flujo alternativo: genera PDF, envía al email, devuelve base64 (sin código). No usado en la UI actual. |

---

## 6. Seguridad y limitaciones

- **Sin autenticación:** `estado_cuenta_publico` usa `APIRouter(dependencies=[])`; no se usa `get_current_user`.
- **Datos por cédula:** Solo se exponen datos del cliente identificado por la cédula consultada; el código asegura que quien descarga el PDF tiene acceso al email del cliente.
- **Rate limits:** Por IP; ventanas y máximos en `backend/app/core/cobros_public_rate_limit.py` (ESTADO_CUENTA_SOLICITAR_*, ESTADO_CUENTA_VERIFICAR_*).
- **Código de un solo uso y expiración:** 2 horas (`CODIGO_EXPIRA_MINUTES = 120`); `usado = True` tras verificar.
- **Mensajes genéricos:** En solicitar-codigo no se revela si la cédula existe o si el email falló.

---

## 7. Ejemplos de request/response

### POST solicitar-codigo

**Request:**  
`POST /api/v1/estado-cuenta/public/solicitar-codigo`  
`Content-Type: application/json`  
`Body: { "cedula": "V12345678" }`

**Response 200:**  
`{ "ok": true, "mensaje": "Si la cedula esta registrada, recibiras un codigo en tu correo en los proximos minutos." }`

**Response 429:**  
`{ "detail": "Ha alcanzado el límite de consultas por hora. Intente más tarde." }`

### POST verificar-codigo

**Request:**  
`POST /api/v1/estado-cuenta/public/verificar-codigo`  
`Content-Type: application/json`  
`Body: { "cedula": "V12345678", "codigo": "123456" }`

**Response 200:**  
`{ "ok": true, "pdf_base64": "JVBERi0xLjQK..." }`

**Response 200 (error):**  
`{ "ok": false, "error": "Codigo invalido o expirado. Solicite uno nuevo." }`

---

## 8. Comprobaciones rápidas (checklist)

1. **Ruta pública:** En `App.tsx`, `PUBLIC_PATHS` contiene `'/rapicredit-estadocuenta'` y la ruta renderiza `EstadoCuentaPublicoPage`.
2. **Proxy /api:** En producción, `API_BASE_URL` está configurado en Render; peticiones a `/api/v1/estado-cuenta/public/*` pasan por el proxy en `server.js`.
3. **Backend:** El router `estado_cuenta_publico` está registrado con prefix `/estado-cuenta/public` y sin dependencia de auth.
4. **BD:** Tabla `estado_cuenta_codigos` existe (migración `011_estado_cuenta_codigos`); columnas: id, cedula_normalizada, email, codigo, expira_en, usado, creado_en.
5. **Email:** Configuración en `/pagos/configuracion?tab=email` (o variables de entorno) usada por `send_email` para el envío del código.

---

## 9. Referencias de código (índice)

| Qué | Dónde |
|-----|--------|
| Ruta pública y Route | `frontend/src/App.tsx` líneas 14, 148 |
| Página estado de cuenta público | `frontend/src/pages/EstadoCuentaPublicoPage.tsx` |
| Servicio API estado de cuenta | `frontend/src/services/estadoCuentaService.ts` (solicitarCodigo, verificarCodigo) |
| Config base path y session key | `frontend/src/config/env.ts` (BASE_PATH, PUBLIC_FLOW_SESSION_KEY, env.API_URL) |
| SPA fallback y proxy | `frontend/server.js` (FRONTEND_BASE, sendSpaIndex, app.use('/api', proxy)) |
| Registro router backend | `backend/app/api/v1/__init__.py` líneas 50-53 |
| Endpoints solicitar-codigo / verificar-codigo | `backend/app/api/v1/endpoints/estado_cuenta_publico.py` líneas 253-371 |
| Rate limits estado de cuenta | `backend/app/core/cobros_public_rate_limit.py` líneas 20-26, 36-42, 83-109 |
| Modelo EstadoCuentaCodigo | `backend/app/models/estado_cuenta_codigo.py` |
| Generación PDF | `backend/app/services/estado_cuenta_pdf.py` (generar_pdf_estado_cuenta) |
| Validación cédula | `backend/app/api/v1/endpoints/validadores.py` (validate_cedula) |
| Migración tabla códigos | `backend/alembic/versions/011_estado_cuenta_codigos.py` |

---

## 10. Mejoras implementadas (recientes)

| Mejora | Dónde | Descripción |
|--------|--------|-------------|
| Texto UI en español | `EstadoCuentaPublicoPage.tsx` | "Atras" → "Atrás", "Verificacion" → "Verificación", "Codigo" → "Código" en títulos y placeholders. |
| Limpieza de notificaciones al cambiar paso | `EstadoCuentaPublicoPage.tsx` | `goToStep()` y `resetForm()` limpian `notification` para evitar mensajes residuales al navegar entre pasos. |
| Aviso paso 2 (spam / límite) | `EstadoCuentaPublicoPage.tsx` | Texto breve: revisar carpeta spam y límite 5/hora al solicitar otro código. |
| Imports backend | `estado_cuenta_publico.py` | `import base64` al inicio del módulo; eliminados imports inline dentro de funciones. |
| Timer de notificación | `EstadoCuentaPublicoPage.tsx` | `showNotification` usa `useRef` para el timeout y se limpia en `useEffect` cleanup al desmontar; evita actualizar estado tras unmount. |

---

## 11. Mejoras propuestas (estado)

| Prioridad | Mejora | Estado |
|-----------|--------|--------|
| ~~Alta~~ | ~~Limpieza periódica de códigos expirados~~ | **Implementado:** job diario 4:00 en `scheduler.py`; `app.services.estado_cuenta_cleanup.limpiar_estado_cuenta_codigos()` borra filas con `expira_en < now` o (usado y creado_en &lt; 24 h). |
| ~~Media~~ | ~~Retorno opcional `expira_en` (ISO)~~ | **Implementado:** `SolicitarCodigoResponse` y `VerificarCodigoResponse` incluyen `expira_en`; frontend muestra "Código válido hasta las HH:MM" en paso 2. |
| ~~Media~~ | ~~Manejo de timeout en `showNotification`~~ | **Implementado:** timer en `useRef` + cleanup al desmontar. |
| ~~Baja~~ | ~~Plantilla de email configurable~~ | **Implementado:** clave BD `estado_cuenta_codigo_email` (JSON asunto/cuerpo); variables `{{nombre}}`, `{{codigo}}`, `{{minutos_valido}}`. GET/PUT en `GET/PUT /api/v1/notificaciones/plantilla-estado-cuenta-codigo-email`. |
| ~~Baja~~ | ~~Métricas/logs por IP~~ | **Implementado:** logs estructurados `estado_cuenta solicitar ip=%s outcome=ok|fail reason=...` y `estado_cuenta verificar ip=%s outcome=ok|fail reason=...` (incl. rate_limit). |

---

*Documento de auditoría integral con trazabilidad de inicio a fin para https://rapicredit.onrender.com/pagos/rapicredit-estadocuenta.*
