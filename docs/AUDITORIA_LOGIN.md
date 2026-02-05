# Auditoría integral de login

**Fecha:** 2026-02-03  
**Alcance:** Flujo de autenticación (login, refresh, olvido de contraseña, protección de rutas, almacenamiento de tokens y seguridad backend).

---

## 1. Resumen ejecutivo

| Área              | Estado   | Observaciones principales |
|-------------------|----------|---------------------------|
| Frontend (UI/UX)  | ✅ Bueno | Validación, Recordarme, Olvido contraseña, manejo de errores |
| Frontend (tokens) | ✅ Bueno | Refresh automático, expiración, limpieza en 401 |
| Backend (auth)    | ✅ Bueno | Rate limit, bcrypt, JWT, usuario inactivo rechazado |
| Seguridad         | ✅ Bueno | Sin contraseñas en logs, mensaje genérico 401, SECRET_KEY validada |
| Mejoras sugeridas | 🟡 Menor | 429 en frontend, HTTPS, posible rate limit en forgot-password |

---

## 2. Frontend

### 2.1 Formulario de login (`LoginForm.tsx`)

| Aspecto | Implementación | Valoración |
|---------|----------------|------------|
| Validación cliente | Zod: email obligatorio y formato, password mín. 6 caracteres | ✅ |
| Recordarme | Controller (react-hook-form), valor booleano, default true | ✅ |
| Olvido contraseña | Modal, email validado, envío a itmaster@rapicreditca.com | ✅ |
| Errores | 401, 422, red: mensajes desde backend o genéricos | ✅ |
| Redirección post-login | `location.state?.from` o `/dashboard/menu` | ✅ |
| Contraseña en UI | type="password", opción mostrar/ocultar | ✅ |
| autocomplete | email, current-password | ✅ |
| Logo en login | forceDefault para no llamar API en ruta pública | ✅ |

**Recomendación:** Mostrar mensaje específico cuando el backend devuelva 429 (rate limit), por ejemplo: "Demasiados intentos. Espere un minuto e intente de nuevo."

### 2.2 Store de autenticación (`simpleAuthStore.ts`)

| Aspecto | Implementación | Valoración |
|---------|----------------|------------|
| Inicialización | `initializeAuth()` verifica token con GET /auth/me, timeout 8s | ✅ |
| Sesión inconsistente | Si hay user pero no token → clearAuthStorage | ✅ |
| Login exitoso | Guarda user en estado, toast de bienvenida | ✅ |
| Error de login | Mensaje en estado, extracción de detail/message/array | ✅ |
| Evitar doble init | App.tsx usa flag `_authInitDone` | ✅ |

### 2.3 AuthService (`authService.ts`)

| Aspecto | Implementación | Valoración |
|---------|----------------|------------|
| Login | POST /auth/login, normaliza email, clearAuthStorage antes de guardar | ✅ |
| Persistencia | remember → localStorage (+ remember_me); si no → sessionStorage | ✅ |
| Respuesta envuelta | Acepta response directa o response.data | ✅ |
| Falta access_token | Lanza error claro, no guarda nada | ✅ |
| resetRefreshTokenExpired | Llamado tras login exitoso | ✅ |
| Logout | POST /auth/logout (silencioso) + clearAuthStorage | ✅ |
| Refresh | Lee refresh_token, POST /auth/refresh, actualiza storage | ✅ |
| getCurrentUser | GET /auth/me, actualiza user en storage | ✅ |
| changePassword | Redirige a login con BASE_URL; ideal usar BASE_PATH | 🟡 |

**Recomendación:** En `changePassword`, usar `BASE_PATH + '/login'` (como en Usuarios.tsx) en lugar de `import.meta.env.BASE_URL` para coherencia con basename.

### 2.4 Cliente API e interceptores (`api.ts`)

| Aspecto | Implementación | Valoración |
|---------|----------------|------------|
| Endpoints sin token | login, refresh, forgot-password | ✅ |
| Token expirado | isTokenExpired con margen 5s, cancelar requests, clearAuthStorage, redirect | ✅ |
| Token malformado | Menos de 3 segmentos JWT → limpiar y redirigir | ✅ |
| 401 en no-auth | Intento de refresh, cola de peticiones, reintento con nuevo token | ✅ |
| Refresh fallido | refreshTokenExpired = true, cancelar pendientes, clearAuthStorage, redirect | ✅ |
| LOGIN_PATH | BASE_PATH + '/login' | ✅ |
| AbortController | Limpieza en éxito y error para evitar fugas | ✅ |

### 2.5 Almacenamiento y token (`storage.ts`, `token.ts`)

| Aspecto | Implementación | Valoración |
|---------|----------------|------------|
| localStorage/sessionStorage | Comprobación una vez, manejo de SecurityError / QuotaExceeded | ✅ |
| Valores inválidos | '', 'undefined', 'null' tratados como fallback | ✅ |
| clearAuthStorage | Limpia access_token, refresh_token, user, remember_me en ambos | ✅ |
| isTokenExpired | Decodifica JWT, exp en segundos, margen 5s | ✅ |
| hasValidToken | Lee según remember_me, comprueba expiración | ✅ |

### 2.6 Rutas protegidas (`SimpleProtectedRoute.tsx`, `App.tsx`)

| Aspecto | Implementación | Valoración |
|---------|----------------|------------|
| Rutas públicas | `/`, `/login` sin Layout ni protección | ✅ |
| Rutas privadas | Envueltas en SimpleProtectedRoute + Layout | ✅ |
| Redirect si no autenticado | Navigate a /login con state.from | ✅ |
| Timeout de carga | 10s → mensaje y botón a login | ✅ |
| requireAdmin | Comprueba user.rol === 'administrador' | ✅ |

---

## 3. Backend

### 3.1 Login (`auth.py`)

| Aspecto | Implementación | Valoración |
|---------|----------------|------------|
| Rate limit | Por IP, 5 intentos / 60s, 429 con mensaje claro | ✅ |
| IP del cliente | X-Forwarded-For (proxy) o request.client.host | ✅ |
| Usuario en BD | Por email, verifica is_active y contraseña | ✅ |
| Mensaje 401 | "Credenciales incorrectas" (sin revelar si existe el usuario) | ✅ |
| Fallback admin | ADMIN_EMAIL + ADMIN_PASSWORD desde env | ✅ |
| Tokens | create_access_token, create_refresh_token (sub = email) | ✅ |
| last_login | Actualizado en BD en login exitoso | ✅ |
| Logs | No se registra email ni contraseña en logs de login | ✅ |

### 3.2 Refresh y /me

| Aspecto | Implementación | Valoración |
|---------|----------------|------------|
| Refresh | Decodifica refresh_token, type=refresh, usuario en BD o _fake_user | ✅ |
| Usuario inactivo | Refresh devuelve _fake_user (admin env); /me igual | ✅ |
| /me | Bearer obligatorio, type=access, usuario desde BD o _fake_user | ✅ |

### 3.3 Olvido de contraseña

| Aspecto | Implementación | Valoración |
|---------|----------------|------------|
| Respuesta fija | Siempre 200, mismo mensaje (no revela si el email existe) | ✅ |
| Destino | FORGOT_PASSWORD_NOTIFY_EMAIL (default itmaster@rapicreditca.com) | ✅ |
| Contenido del correo | Email solicitante, nombre si existe, indicación "existe en BD" | ✅ |
| SMTP | Mismo send_email que el resto de la app | ✅ |

**Recomendación:** Valorar rate limit para POST /forgot-password por IP (p. ej. 3 solicitudes / 15 min) para evitar abuso.

### 3.4 Seguridad (`security.py`, `config.py`)

| Aspecto | Implementación | Valoración |
|---------|----------------|------------|
| Contraseñas | bcrypt (passlib), verify_password / get_password_hash | ✅ |
| JWT | HS256, exp en access (minutos) y refresh (días) | ✅ |
| SECRET_KEY | Obligatoria, ≥32 caracteres, no valores débiles | ✅ |
| ACCESS_TOKEN_EXPIRE_MINUTES | 240 (4 h), configurable | ✅ |
| REFRESH_TOKEN_EXPIRE_DAYS | 7, configurable | ✅ |

### 3.5 Dependencia get_current_user (`deps.py`)

| Aspecto | Implementación | Valoración |
|---------|----------------|------------|
| Token | HTTPBearer, decode_token, type=access | ✅ |
| Usuario en BD | Por email (sub), solo si is_active | ✅ |
| Fallback | _fake_user_response para admin desde env | ✅ |

---

## 4. Flujo de datos (resumen)

1. Usuario envía email + password + remember.
2. Frontend normaliza email, no envía token; backend aplica rate limit, busca usuario, verifica contraseña (o admin env).
3. Backend devuelve access_token, refresh_token, user; frontend hace clearAuthStorage y guarda en localStorage o sessionStorage según remember.
4. En cada request no-auth el interceptor añade Bearer; si el token está expirado, intenta refresh; si falla, limpia y redirige a login.
5. initializeAuth llama a GET /auth/me con el token guardado; si falla o timeout, limpia storage y marca no autenticado.
6. Rutas privadas pasan por SimpleProtectedRoute; si !isAuthenticated o !user → Navigate a /login.

---

## 5. Recomendaciones prioritarias (aplicadas)

1. **Frontend – 429:** ✅ En LoginForm se detecta status 429 y se muestra: "Demasiados intentos de inicio de sesión. Espere un minuto e intente de nuevo."
2. **Frontend – changePassword:** ✅ Redirección a login usa BASE_PATH (import desde config/env).
3. **Backend – forgot-password:** ✅ Rate limit por IP: 3 solicitudes cada 15 minutos (429 si se supera).
4. **Producción:** Asegurar HTTPS en producción (Render y proxy); no afecta al código revisado pero es requisito para tokens en tránsito.
5. **Opcional:** Añadir en backend un endpoint de salud que no requiera auth (p. ej. GET /health) para monitoreo sin token.

---

## 6. Conclusión

El flujo de login está bien estructurado: validación cliente y servidor, persistencia según "Recordarme", refresh automático, manejo de expiración y 401, limpieza de almacenamiento y protección de rutas. La seguridad backend (rate limit, bcrypt, JWT, mensajes 401 genéricos, SECRET_KEY) es adecuada. Las mejoras sugeridas son menores y de refuerzo (429 en UI, rate limit en olvido de contraseña, uso consistente de BASE_PATH).
