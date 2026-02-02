# Auditoría integral de login

**Fecha:** 2025-02-02  
**Ámbito:** Backend (FastAPI) + Frontend (React/Vite)

---

## 1. Resumen ejecutivo

| Área | Estado | Prioridad |
|------|--------|-----------|
| **Backend: endpoints y flujo** | Aceptable | — |
| **Backend: validación y seguridad** | Mejorable | Alta |
| **Backend: logout** | Falta endpoint | Media |
| **Frontend: formulario y UX** | Bueno | — |
| **Frontend: almacenamiento y API** | Bueno | — |
| **Frontend: redirecciones con BASE_PATH** | Bug en api.ts | Alta |
| **Seguridad: rate limiting** | No implementado | Alta |
| **Seguridad: timing / enumeración** | Riesgo bajo | Media |

---

## 2. Backend – Auth

### 2.1 Endpoints

| Método | Ruta | Descripción | Observaciones |
|--------|------|-------------|---------------|
| GET | `/api/v1/auth/status` | Indica si auth está configurado | No revela credenciales. Público. |
| POST | `/api/v1/auth/login` | Login con email y contraseña | Sin rate limit. Ver apartado 2.4. |
| POST | `/api/v1/auth/refresh` | Renovar access_token con refresh_token | Sin rate limit. |
| GET | `/api/v1/auth/me` | Usuario actual (Bearer) | Requiere token. Correcto. |

**Falta:** `POST /api/v1/auth/logout`. El frontend llama a esta ruta; el backend no la define → respuesta 404. El cliente hace `clearAuthStorage()` en `finally`, por lo que el logout “funciona” en UX pero la petición falla. Conviene implementar el endpoint (aunque sea vacío) para coherencia y posibles invalidaciones futuras.

### 2.2 Esquemas (Pydantic)

- **LoginRequest:** `email: str`, `password: str`, `remember: Optional[bool] = True`.
- No hay validación de formato de email (p. ej. `EmailStr`) ni longitud mínima de contraseña en el backend.
- La validación fuerte está en el frontend (Zod: email válido, contraseña ≥ 6 caracteres). Para defensa en profundidad, el backend debería validar también (email formato válido, password longitud mínima).

### 2.3 Flujo de login (backend)

1. Comprueba que existan `ADMIN_EMAIL` y `ADMIN_PASSWORD`; si no → 503.
2. Normaliza email (`lower().strip`) y lo compara con `ADMIN_EMAIL`.
3. Hash de la contraseña: `hashed = get_password_hash(settings.ADMIN_PASSWORD)` y `verify_password(credentials.password, hashed)`.
4. Genera access_token (30 min) y refresh_token (7 días) con PyJWT (HS256).
5. Devuelve `LoginResponse` (tokens + user).

Observación: se hace `get_password_hash(ADMIN_PASSWORD)` en cada login. Funcionalmente correcto; si se quisiera optimizar, se podría cachear el hash (misma seguridad, menos coste CPU).

### 2.4 Seguridad backend

- **Rate limiting:** No hay límite de intentos en `/login` ni `/refresh`. Riesgo de fuerza bruta si el endpoint es accesible. Recomendación: limitar intentos por IP (y/o por email) por ventana de tiempo.
- **Timing / enumeración:** Se valida primero el email y luego la contraseña. Un atacante podría medir tiempos para inferir si el email existe. Mitigación: ejecutar siempre ambas comprobaciones (comparar email y verificar contraseña) para que el tiempo de respuesta sea similar en éxito y fallo.
- **Mensaje de error:** Se devuelve "Credenciales incorrectas" tanto para email incorrecto como para contraseña incorrecta. Correcto (no revelar qué falló).
- **Contraseña en env:** `ADMIN_PASSWORD` en variables de entorno. Asegurar que no se registre en logs ni se exponga en respuestas.

### 2.5 JWT (security.py)

- Access: expiración con `ACCESS_TOKEN_EXPIRE_MINUTES` (30 min).
- Refresh: 7 días.
- Payload: `sub`, `exp`, `type` ("access" | "refresh"); en access se añade `email` en `extra`.
- Algoritmo HS256, clave desde `SECRET_KEY`. La validación de longitud y fortaleza de `SECRET_KEY` en config está bien.

---

## 3. Frontend – Flujo de login

### 3.1 Formulario (LoginForm.tsx)

- Validación con **Zod**: email obligatorio y formato email; contraseña obligatoria y mínimo 6 caracteres.
- **react-hook-form** + `zodResolver`; mensajes de error por campo y error global (root).
- Manejo de errores HTTP: 401 (mensaje del backend o "Credenciales incorrectas"), 422 (detalle de validación), otros (mensaje genérico o del servidor).
- Checkbox "Recordarme" y enlace "¿Olvidó su contraseña?" (actualmente `alert`; pendiente de implementar).
- Botón con estado de carga y deshabilitado mientras `isLoading`.
- Mostrar/ocultar contraseña (ícono ojo).
- `autoComplete="email"` y `"current-password"`; `autoFocus` en email.

Aspectos positivos: validación clara, feedback de errores, accesibilidad básica.

### 3.2 Store (simpleAuthStore.ts)

- Estado: `user`, `isAuthenticated`, `isLoading`, `error`.
- **initializeAuth:** al cargar la app, si hay user + token en storage, llama a `authService.getCurrentUser()` para validar con el backend; si falla o timeout (8 s), limpia storage y marca no autenticado. Evita confiar solo en datos locales.
- **login:** llama a `authService.login`, persiste tokens y user según "recordarme" (localStorage vs sessionStorage), actualiza estado y muestra toast de bienvenida.
- **logout:** llama a `authService.logout()` y limpia estado; toast de cierre de sesión.
- Uso de `safeGetItem` / `safeSetItem` y equivalentes para sessionStorage, con manejo de contextos donde storage no está disponible o falla.

### 3.3 Servicio (authService.ts)

- **login:** POST a `/api/v1/auth/login` con email normalizado (lower, trim). Guarda `access_token`, `refresh_token` y `user` en localStorage o sessionStorage según `remember`; guarda `remember_me`. Tras login exitoso llama a `apiClient.resetRefreshTokenExpired()`.
- **logout:** POST a `/api/v1/auth/logout` (endpoint inexistente → 404) y en `finally` ejecuta `clearAuthStorage()`. Efecto: sesión se cierra correctamente en el cliente.
- **getCurrentUser:** GET `/api/v1/auth/me` con token; actualiza user en storage.
- **refreshToken:** POST `/api/v1/auth/refresh` con `refresh_token`; actualiza tokens en storage según `remember_me`.

Almacenamiento consistente con "recordarme" y limpieza centralizada en `clearAuthStorage()`.

### 3.4 Cliente HTTP (api.ts)

- Interceptor de request: no añade Authorization a `/api/v1/auth/login` ni `/api/v1/auth/refresh`. Para el resto de rutas, toma token de localStorage o sessionStorage según `remember_me`, limpia espacios y prefijo "Bearer ", comprueba formato JWT (3 segmentos) y expiración (decodificación de payload y margen 5 s). Si el token es inválido o expirado, limpia storage, marca `refreshTokenExpired`, cancela cola y redirige a login.
- Interceptor de response: ante 401 (excepto en login/refresh), intenta refresh con una sola petición en vuelo y cola el resto; si el refresh falla, limpia storage y redirige a login.
- Redirección a login: se usa **`window.location.replace('/login')`** (y comprobaciones con `window.location.pathname !== '/login'`). Con la app bajo un subpath (p. ej. `basename="/pagos"`), la URL real de login es `/pagos/login`, pero el replace va a `/login`. **Bug:** en despliegues con base path (p. ej. `/pagos`), al expirar el token o fallar el refresh el usuario termina en la raíz `/login` en lugar de `/pagos/login`. **Recomendación:** usar `BASE_PATH` (o equivalente) para construir la ruta de login en todos los `replace`/redirect (api.ts y cualquier otro sitio que redirija a login).

### 3.5 Rutas y protección (App.tsx, SimpleProtectedRoute)

- Rutas públicas: `/` (Welcome) y `/login`. Si el usuario está autenticado y está en `/` o `/login`, se redirige a `/dashboard/menu`.
- El resto de rutas pasan por `SimpleProtectedRoute`: si no hay usuario autenticado (o no hay user), redirige a `fallbackPath` (por defecto `/login`). Con `basename="/pagos"`, React Router resuelve `/login` como `/pagos/login`, por lo que la protección en sí es correcta.
- Timeout de 10 s en la verificación inicial; si no se completa, se muestra mensaje y botón "Ir al Login" que usa `BASE_PATH + fallbackPath` (correcto para subpath).

Inconsistencia: en `SimpleProtectedRoute` el redirect con botón usa `BASE_PATH`; en api.ts el redirect automático no, de ahí el bug comentado.

### 3.6 Almacenamiento (storage.ts)

- Wrappers seguros para localStorage y sessionStorage: comprobación de disponibilidad, manejo de excepciones (SecurityError, QuotaExceededError), valores por defecto.
- `clearAuthStorage()` elimina access_token, refresh_token, user y remember_me en ambos storages.
- Los tokens no se envían a terceros; solo se usan en llamadas al mismo origen (o proxy configurado).

---

## 4. Hallazgos y recomendaciones

### 4.1 Crítico / Alta prioridad

1. **Rate limiting en login (backend)**  
   Implementar límite de intentos por IP (y opcionalmente por email) en `POST /api/v1/auth/login` (y valorar en `/refresh`) para mitigar fuerza bruta. Ej.: máximo N intentos por minuto; tras superar, 429 o bloqueo temporal.

2. **Redirección a login con BASE_PATH (frontend)**  
   En `api.ts`, sustituir todas las redirecciones a login por una URL que use el base path de la app (p. ej. `BASE_PATH + '/login'` o helper que centralice la ruta de login). Revisar también cualquier otro `window.location.replace('/login')` o `pathname === '/login'` que deba tener en cuenta el subpath.

### 4.2 Media prioridad

3. **Endpoint POST /api/v1/auth/logout (backend)**  
   Añadir el endpoint aunque solo devuelva 200. Permite coherencia con el frontend y deja la puerta abierta a invalidar refresh tokens o registrar cierres de sesión.

4. **Validación en backend de LoginRequest**  
   Añadir en el schema: email con formato válido (p. ej. `EmailStr` de Pydantic) y longitud mínima de contraseña (p. ej. 6). Respuesta 422 con detalle si no se cumple.

5. **Mitigación de timing en login (backend)**  
   Hacer que el tiempo de respuesta sea similar cuando el email no existe y cuando la contraseña es incorrecta (siempre ejecutar comparación de email y verificación de contraseña, sin salir antes por email incorrecto).

6. **Recuperación de contraseña (frontend)**  
   El enlace "¿Olvidó su contraseña?" muestra un alert. Definir si habrá flujo de recuperación (backend + frontend) o sustituir por mensaje estático (p. ej. "Contacte al administrador") hasta que exista la funcionalidad.

### 4.3 Baja prioridad

7. **Cache del hash de ADMIN_PASSWORD (backend)**  
   Opcional: calcular una sola vez el hash de `ADMIN_PASSWORD` al cargar la app y reutilizarlo en login para reducir coste CPU.

8. **Documentación de auth en OpenAPI**  
   Revisar descripciones y ejemplos de los endpoints de auth en FastAPI para que en /docs quede claro qué espera cada uno y qué devuelve en éxito y error.

---

## 5. Checklist rápido – Login

**Backend**

- [ ] Rate limiting en POST /login (y opcionalmente /refresh).
- [ ] POST /auth/logout implementado (aunque sea vacío).
- [ ] LoginRequest con validación de email (formato) y longitud mínima de contraseña.
- [ ] Mismo tiempo de respuesta en login para email inexistente y contraseña incorrecta (mitigación timing).

**Frontend**

- [ ] Todas las redirecciones a login usan BASE_PATH (o ruta de login centralizada).
- [ ] Logout: manejar 404 de /auth/logout sin impacto en UX (ya se hace con `finally` + clearAuthStorage).
- [ ] "Olvidó su contraseña": implementar flujo o mensaje claro hasta que exista.

**General**

- [ ] No loguear ni exponer ADMIN_PASSWORD ni tokens en respuestas.
- [ ] Revisar que SECRET_KEY sea fuerte y no esté en repositorio.

---

*Documento generado a partir del análisis del código en backend (auth, security, schemas) y frontend (LoginForm, authService, simpleAuthStore, api, App, SimpleProtectedRoute, storage).*
