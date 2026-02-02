# Auditoría integral del flujo de Módulos de Configuración (backend y frontend)

**Fecha:** 2025-02-02  
**Alcance:** Todos los módulos de configuración: General, Logo, Email, WhatsApp, AI, Validadores, Notificaciones/envíos, Concesionarios, Asesores, Modelos de vehículos, Usuarios.

---

## 1. Resumen ejecutivo

| Aspecto | Estado | Notas |
|---------|--------|--------|
| **Backend – persistencia** | ✅ BD | General, logo, email, WhatsApp, notificaciones/envíos y validadores usan tabla `configuracion` (clave-valor). |
| **Backend – seguridad** | ✅ OK | Router principal con `Depends(get_current_user)`; sub-routers heredan. API key AI solo en backend (OPENROUTER_API_KEY). Contraseñas/tokens enmascarados en GET. |
| **Frontend – servicios** | ✅ Mayoría apiClient | Config general, email, WhatsApp y validadores usan `apiClient` (base URL correcta). |
| **Frontend – fetch relativos** | ⚠️ 3 usos | `Configuracion.tsx`, `Logo.tsx` y `UsuariosConfig.tsx` usan `fetch('/api/...')` sin base URL; fallan si el API está en otro host. |
| **Consistencia datos** | ⚠️ Mock + BD | Página Configuracion mezcla estado desde BD (general, logo) con `mockConfiguracion` para secciones no persistidas (notificaciones, seguridad, baseDatos, etc.). |

---

## 2. Backend

### 2.1 Estructura y rutas

- **Router principal:** `app/api/v1/endpoints/configuracion.py`
- **Prefijo:** `/api/v1/configuracion`
- **Protección:** `router = APIRouter(dependencies=[Depends(get_current_user)])` — todos los endpoints exigen autenticación.
- **Sub-routers incluidos:**
  - `configuracion_ai.router` → `/api/v1/configuracion/ai`
  - `configuracion_email.router` → `/api/v1/configuracion/email`
  - `configuracion_whatsapp.router` → `/api/v1/configuracion/whatsapp`

### 2.2 Modelo de datos

- **Tabla:** `app/models/configuracion.py` — `Configuracion(clave, valor)` (clave PK, valor TEXT).
- **Claves usadas:**
  - `configuracion_general` — JSON con nombre_empresa, logo_filename, zona_horaria, idioma, moneda, etc.
  - `logo_imagen` — Contenido del logo en base64 (cuando no hay LOGO_UPLOAD_DIR).
  - `notificaciones_envios` — JSON con configuración de envíos por tipo (habilitado, cco).
  - `email_config` — JSON SMTP/IMAP y tickets_notify_emails.
  - `whatsapp_config` — JSON api_url, access_token (enmascarado en GET), phone_number_id, etc.
  - `configuracion_validadores` — JSON de reglas de validadores (usado por endpoint en `validadores.py`).

### 2.3 Endpoints del router principal (`configuracion.py`)

| Método y ruta | Origen datos | Uso frontend |
|---------------|--------------|--------------|
| `GET /general` | BD (clave configuracion_general) + stub en memoria | configuracionGeneralService.obtenerConfiguracionGeneral() |
| `PUT /general` | Body → stub → BD | configuracionGeneralService.actualizarConfiguracionGeneral() |
| `GET /logo/{filename}` | Disco (LOGO_UPLOAD_DIR) o BD (logo_imagen) | Imagen del logo, preview |
| `HEAD /logo/{filename}` | Idem | Comprobar existencia sin descargar |
| `POST /upload-logo` | Body (archivo) → disco o BD + actualiza general | Configuracion.tsx handleCargarLogo |
| `DELETE /logo` | Borra disco/BD y actualiza general | Configuracion.tsx handleEliminarLogo |
| `GET /notificaciones/envios` | BD (clave notificaciones_envios) | emailConfigService.obtenerConfiguracionEnvios() |
| `PUT /notificaciones/envios` | Body → BD | emailConfigService.actualizarConfiguracionEnvios() |
| `POST /validadores/probar` | Body (datos prueba) → respuesta stub (resultados vacíos) | configuracionService.probarValidadores() |
| `GET /sistema/completa` | General desde BD | configuracionService.obtenerConfiguracionCompleta() |
| `GET /sistema/categoria/{categoria}` | General desde BD | configuracionService.obtenerConfiguracionCategoria() |

### 2.4 Sub-router AI (`configuracion_ai.py`)

- **Autenticación:** Heredada del router principal (get_current_user).
- **Persistencia:** Stub en memoria (`_ai_config_stub`: modelo, temperatura, max_tokens, activo). No persiste en BD; la API key se lee solo de `OPENROUTER_API_KEY` (nunca se expone al frontend).
- **Endpoints:**
  - `GET /configuracion` — Devuelve configured, provider, modelo, temperatura, max_tokens, activo; openai_api_key como "***" si hay clave.
  - `PUT /configuracion` — Actualiza modelo, temperatura, max_tokens, activo (nunca acepta API key).
  - `POST /chat` — Chat completions vía OpenRouter (usa clave del servidor).
  - `POST /probar` — Prueba de conexión OpenRouter.
  - `GET /documentos` — Listado RAG; sin persistencia devuelve `{ total: 0, documentos: [] }`.

### 2.5 Sub-router Email (`configuracion_email.py`)

- **Persistencia:** BD (clave `email_config`). Stub en memoria sincronizado con BD; opcionalmente rellenado desde `settings` (SMTP_*).
- **Seguridad:** GET no expone smtp_password ni imap_password (se devuelve "***"). PUT no sobrescribe contraseña si el frontend envía "***" o vacío.
- **Endpoints:**
  - `GET /configuracion` — Config SMTP/IMAP/tickets; contraseñas enmascaradas.
  - `PUT /configuracion` — Actualiza y persiste en BD; actualiza `email_config_holder` para envíos.
  - `GET /estado` — configurada, mensaje, problemas, conexion_smtp, modo_pruebas, email_pruebas.
  - `POST /probar` — Prueba de envío (stub: no envía correo real).
  - `POST /probar-imap` — Valida que imap_* estén configurados; no abre conexión IMAP real.

### 2.6 Sub-router WhatsApp (`configuracion_whatsapp.py`)

- **Persistencia:** BD (clave `whatsapp_config`). Stub sincronizado con BD; valores por defecto desde settings (WHATSAPP_*).
- **Seguridad:** GET no expone access_token ni webhook_verify_token ("***"). PUT no sobrescribe token si el frontend envía "***" o vacío.
- **Endpoints:**
  - `GET /configuracion` — Config con tokens enmascarados.
  - `PUT /configuracion` — Actualiza y persiste en BD.

### 2.7 Módulo Validadores (usado desde Configuración)

- **Router:** `app/api/v1/endpoints/validadores.py` (prefijo `/api/v1/validadores`).
- **Protección:** `Depends(get_current_user)`.
- **Endpoint relevante para configuración:** `GET /configuracion-validadores` — Devuelve configuración desde BD (clave `configuracion_validadores`) o estructura por defecto.
- **Uso frontend:** `configuracionService.obtenerValidadores()` → `apiClient.get('/api/v1/validadores/configuracion-validadores')`.

### 2.8 Concesionarios, Asesores, Modelos de vehículos, Usuarios

- No son “configuración” en el sentido de clave-valor; son entidades con sus propios routers:
  - Concesionarios: API bajo `/api/v1/...` (concesionarioService / useConcesionarios).
  - Asesores (Analistas): API de analistas.
  - Modelos de vehículos: API de modelos.
  - Usuarios: API de usuarios (listado desde ADMIN_EMAIL, etc.).
- En la página Configuración se muestran como pestañas (ConcesionariosConfig, AnalistasConfig, ModelosVehiculosConfig, UsuariosConfig) que consumen esos APIs.

---

## 3. Frontend

### 3.1 Página principal: `Configuracion.tsx`

- **Ruta:** Definida en App (ej. `/configuracion`).
- **Auth:** Contenido bajo ruta protegida; llamadas con Bearer vía apiClient o fetch.
- **Estado:**
  - `configuracionGeneral` — Datos de BD (configuracionGeneralService).
  - `configuracion` — Objeto amplio que mezcla general (sincronizado con BD) con **mockConfiguracion** para notificaciones, seguridad, baseDatos, integraciones, facturacion, inteligenciaArtificial (estos no se persisten en los endpoints actuales).
- **Secciones con contenido desde API/BD:**
  - **General:** GET/PUT `/configuracion/general`, upload/delete logo.
  - **Email:** Componente `<EmailConfig />` (configuración email desde API).
  - **WhatsApp:** Componente `<WhatsAppConfig />` (configuración WhatsApp desde API).
  - **AI:** Componente `<AIConfig />` (configuración AI desde API).
  - **Validadores:** `<ValidadoresConfig />` (configuracionService → validadores).
  - **Concesionarios / Asesores / Modelos / Usuarios:** Componentes que usan sus respectivos servicios/hooks (datos reales de sus APIs).

### 3.2 Servicios

| Servicio | Base URL / cliente | Endpoints usados |
|----------|--------------------|-------------------|
| configuracionGeneralService | apiClient, `/api/v1/configuracion` | GET/PUT `/general` |
| configuracionService | apiClient, `/api/v1/configuracion` y `/api/v1/validadores` | GET validadores/configuracion-validadores, POST configuracion/validadores/probar, GET sistema/completa, GET sistema/categoria/:cat |
| notificacionService (EmailConfigService) | apiClient, `/api/v1/configuracion` | GET/PUT email/configuracion, GET email/estado, POST email/probar, POST email/probar-imap, GET/PUT notificaciones/envios |
| notificacionService (WhatsAppConfigService) | apiClient, `/api/v1/configuracion` | GET/PUT whatsapp/configuracion, POST whatsapp/probar, GET whatsapp/test-completo |
| AIConfig (inline) | apiClient | GET/PUT /api/v1/configuracion/ai/configuracion, POST ai/probar, GET ai/documentos |
| ConcesionariosConfig | useConcesionarios, concesionarioService | API concesionarios |
| AnalistasConfig | useAnalistas, analistaService | API analistas |
| ModelosVehiculosConfig | useModelosVehiculos, modeloVehiculoService | API modelos |
| UsuariosConfig | fetch directo + posiblemente usuarios API | Ver hallazgo fetch relativo |

### 3.3 Constantes y navegación

- **configuracionSecciones.ts:** Define `SECCIONES_CONFIGURACION` (General, Herramientas con submenú Notificaciones/Email/WhatsApp/Plantillas/Programador/Auditoría, Base de datos, Facturación, IA, Validadores, Concesionarios, Asesores, Modelos, Usuarios) y `NOMBRES_SECCION_ESPECIAL` para emailConfig, whatsappConfig, aiConfig.
- **URL ?tab=:** `tab=email`, `tab=whatsapp`, `tab=ai` sincronizados con sección activa para enlaces directos.

---

## 4. Hallazgos y recomendaciones

### 4.1 Crítico: `fetch` con URL relativa (sin base del API)

En tres sitios se usa `fetch('/api/...')` sin prefijo con `env.API_URL` (o apiClient), por lo que la petición va al mismo origen que sirve el frontend. Si el API está en otro host (ej. backend en Render, front en Netlify), estas llamadas fallan o apuntan al host equivocado.

| Archivo | Línea (aprox.) | Uso |
|---------|----------------|-----|
| **Configuracion.tsx** | ~321 | `fetch('/api/v1/configuracion/general')` al verificar logo tras guardar. |
| **Logo.tsx** | ~210, ~478 | `fetch('/api/v1/configuracion/general')` para cargar logo/config. |
| **UsuariosConfig.tsx** | ~41 | `fetch('/api/v1/validadores/validar-campo')` para validar campo. |

**Recomendación:** Sustituir por `apiClient.get(...)` o por `fetch(\`${env.API_URL}/api/v1/...\`, ...)` con headers de autorización consistentes, para que todas las llamadas usen la misma base URL que el resto de la app.

### 4.2 Consistencia: mock vs datos reales

- La página Configuracion inicializa `configuracion` con `mockConfiguracion` y solo sobrescribe `general` con datos de BD. Las secciones notificaciones, seguridad, baseDatos, integraciones, facturacion, inteligenciaArtificial se editan en UI pero **no se persisten** en los endpoints actuales (no hay PUT por categoría para esas claves).
- **Recomendación:** Documentar qué secciones son solo UI/mock y cuáles están conectadas a BD; o implementar persistencia por categoría en backend (claves en tabla configuracion) y consumirlas en frontend.

### 4.3 Configuración AI en memoria

- `configuracion_ai` guarda modelo, temperatura, max_tokens y activo en un stub en memoria; no hay clave en tabla `configuracion`. Tras reinicio o varios workers, la config AI vuelve a valores por defecto.
- **Recomendación:** Persistir configuración AI en BD (ej. clave `ai_config`) y cargar/guardar desde ahí, manteniendo la API key solo en entorno.

### 4.4 Pruebas Email/IMAP

- `POST /configuracion/email/probar` no envía correo real; devuelve mensaje fijo.
- `POST /configuracion/email/probar-imap` no abre conexión IMAP; solo valida que estén rellenados imap_host, imap_user, imap_password.
- **Recomendación:** Documentar como “stub” o implementar prueba SMTP/IMAP real si se requiere.

### 4.5 Validadores: probar

- `POST /configuracion/validadores/probar` devuelve estructura con `resultados: {}` y resumen en cero; no ejecuta validaciones reales contra los endpoints de validadores.
- **Recomendación:** Conectar este endpoint con la lógica de validación real (validar-campo, etc.) o documentar como stub.

### 4.6 Console.log en producción

- Varios componentes (Configuracion.tsx, EmailConfig, WhatsAppConfigService, etc.) tienen `console.log` / `console.warn` / `console.error`. En producción conviene reducirlos o usar un logger condicional.

### 4.7 Seguridad

- **General:** Correcto uso de `get_current_user` en router de configuración y en validadores; API key AI solo en backend; contraseñas y tokens enmascarados en GET y no sobrescritos con "***" en PUT.
- **Logo:** Validación de nombre de archivo (`_safe_filename`) y comprobación de path para evitar path traversal cuando se usa disco.

---

## 5. Checklist de verificación

- [x] Todos los endpoints de configuración exigen autenticación.
- [x] Configuración general, logo, email, WhatsApp y notificaciones/envíos persisten en BD (tabla configuracion).
- [x] Contraseñas y tokens no se exponen en GET y no se sobrescriben con valor enmascarado en PUT.
- [x] API key de OpenRouter solo se usa en backend.
- [ ] **Pendiente:** Sustituir `fetch('/api/...')` por apiClient o fetch con base URL del API en Configuracion.tsx, Logo.tsx y UsuariosConfig.tsx.
- [ ] **Opcional:** Persistir configuración AI en BD.
- [ ] **Opcional:** Documentar o implementar persistencia para secciones actualmente mock (notificaciones, seguridad, baseDatos, etc.).
- [ ] **Opcional:** Reducir o condicionar console.log en módulos de configuración.

---

## 6. Flujo resumido por módulo

| Módulo | Backend | Frontend | Persistencia |
|--------|---------|----------|---------------|
| General | GET/PUT /configuracion/general | configuracionGeneralService, Configuracion.tsx | BD (configuracion_general) |
| Logo | GET/HEAD/upload/delete logo | Configuracion.tsx (fetch + apiClient en upload/delete) | Disco o BD (logo_imagen) |
| Email | GET/PUT /email/configuracion, GET /email/estado, POST probar/probar-imap | EmailConfigService, EmailConfig.tsx | BD (email_config) |
| WhatsApp | GET/PUT /whatsapp/configuracion | WhatsAppConfigService, WhatsAppConfig.tsx | BD (whatsapp_config) |
| AI | GET/PUT /ai/configuracion, POST chat, POST probar, GET documentos | apiClient en AIConfig.tsx | Memoria (stub) |
| Notificaciones envíos | GET/PUT /notificaciones/envios | emailConfigService, ConfiguracionNotificaciones | BD (notificaciones_envios) |
| Validadores (config) | GET /validadores/configuracion-validadores | configuracionService, ValidadoresConfig | BD (configuracion_validadores) |
| Validadores (probar) | POST /configuracion/validadores/probar | configuracionService.probarValidadores | Stub (no valida real) |
| Concesionarios / Asesores / Modelos / Usuarios | Sus propios routers | useConcesionarios, useAnalistas, etc. | Sus propias tablas |
