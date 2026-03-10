# Auditoría de seguridad: enlaces públicos

Este documento describe las medidas de seguridad que impiden que el acceso desde los enlaces públicos (reporte de pago y estado de cuenta) permita acceder al resto del sistema, y la auditoría de las mismas.

---

## 1. Enlaces públicos

| Ruta frontend | URL ejemplo | Uso |
|---------------|-------------|-----|
| `/rapicredit-cobros` | `https://rapicredit.onrender.com/pagos/rapicredit-cobros` | Formulario público de reporte de pago |
| `/rapicredit-estadocuenta` | `https://rapicredit.onrender.com/pagos/rapicredit-estadocuenta` | Consulta pública de estado de cuenta (PDF + envío al email) |

Ambas rutas están en `PUBLIC_PATHS`: no requieren token ni login.

---

## 2. Medidas implementadas

### 2.1 Frontend

- **Rutas públicas aisladas**: Solo `PUBLIC_PATHS` se sirven sin token. Cualquier otra ruta (dashboard, clientes, pagos, etc.) redirige a `/login` si no hay token.
- **Marcado de flujo público**: Al entrar en `rapicredit-cobros` o `rapicredit-estadocuenta` se escribe en `sessionStorage` la clave `public_flow_active` y la ruta (`_path`) para poder volver.
- **Pantalla "Acceso prohibido"**: Si el usuario llega a `/login` y existe `public_flow_active`, no se muestra el formulario de login sino una pantalla con el mensaje "Acceso prohibido" y un botón "Continuar" que lo devuelve al flujo público (cobros o estado de cuenta, según el que tuviera activo). Así no se expone la pantalla de login a quien llegó por error desde un enlace público.
- **Constante compartida**: La clave de sesión (`PUBLIC_FLOW_SESSION_KEY`) está centralizada en `frontend/src/config/env.ts` y se usa en Login y en ambas páginas públicas.

### 2.2 Backend – Endpoints públicos sin autenticación

Solo los siguientes prefijos son accesibles sin token:

| Prefijo | Archivo | Uso |
|---------|---------|-----|
| (sin prefijo) | `health.router` | Health check (monitoreo) |
| `/auth` | `auth.router` | Login, refresh, me (login/refresh requieren credenciales) |
| `/configuracion` (solo logo) | `configuracion.router_logo` | Logo público |
| `/configuracion/informe-pagos` (callback) | `configuracion_informe_pagos.router_google_callback` | OAuth Google |
| `/cobros/public` | `cobros_publico.py` | Validar cédula, enviar reporte de pago |
| `/estado-cuenta/public` | `estado_cuenta_publico.py` | Validar cédula, solicitar estado de cuenta (PDF + email) |

En `cobros_publico` y `estado_cuenta_publico` el router se crea con `APIRouter(dependencies=[])`: **no se usa `get_current_user`**. No hay forma de acceder con token a funciones “privilegiadas” desde estos módulos.

### 2.3 Backend – Alcance de datos

- **Cobros público**  
  - `GET /cobros/public/validar-cedula?cedula=...`: solo comprueba formato, existencia en `clientes` y que tenga préstamo; devuelve `nombre` y `email` (completo para verificación) de **ese** cliente.  
  - `POST /cobros/public/enviar-reporte`: crea un `PagoReportado` asociado a la cédula enviada; no permite operaciones sobre otros clientes.

- **Estado de cuenta público**  
  - `GET /estado-cuenta/public/validar-cedula?cedula=...`: solo comprueba formato y existencia en `clientes`; devuelve `nombre` y `email` de **ese** cliente.  
  - `POST /estado-cuenta/public/solicitar-estado-cuenta`: genera el PDF de estado de cuenta **solo para la cédula enviada** y lo envía al email registrado de ese cliente. No expone datos de otros.

En ambos módulos las consultas a BD filtran por la cédula recibida (normalizada); no hay listados globales ni acceso por ID de cliente/prestamo arbitrario.

### 2.4 Backend – Rate limiting

- **Cobros público**: validar cédula 30 req/min por IP; enviar reporte 5/hora por IP.  
- **Estado de cuenta público**: validar cédula 30 req/min por IP; solicitar estado de cuenta 5/hora por IP.

Definido en `app/core/cobros_public_rate_limit.py`. Reduce abuso y fuerza bruta por IP.

### 2.5 Backend – Otras protecciones (Cobros)

- Honeypot en `enviar-reporte`: campo oculto que, si viene rellenado, rechaza la petición.  
- Validación de archivo por magic bytes (no solo por Content-Type).  
- Límites de longitud en cédula, institución, número de operación.

---

## 3. Checklist de auditoría

| # | Verificación | Estado |
|---|----------------|--------|
| 1 | Rutas públicas solo son `/`, `/login`, `/reporte-pago`, `/rapicredit-cobros`, `/rapicredit-estadocuenta` | OK (`App.tsx` `PUBLIC_PATHS`) |
| 2 | Cualquier otra ruta sin token redirige a `/login` | OK (`RootLayoutWrapper`) |
| 3 | En `/login`, si `public_flow_active` está activo, se muestra "Acceso prohibido" y no el formulario de login | OK (`Login.tsx`) |
| 4 | "Continuar" en Acceso prohibido redirige al flujo público correcto (cobros o estado de cuenta) | OK (usa `_path` en sessionStorage) |
| 5 | `cobros_publico` no usa `get_current_user` | OK (`dependencies=[]`) |
| 6 | `estado_cuenta_publico` no usa `get_current_user` | OK (`dependencies=[]`) |
| 7 | Cobros público solo devuelve/opera con datos del cliente de la cédula consultada | OK (validar + enviar filtran por cédula) |
| 8 | Estado de cuenta público solo devuelve PDF/datos del cliente de la cédula consultada | OK (validar + solicitar filtran por cédula) |
| 9 | Rate limiting activo en todos los endpoints públicos de cobros y estado de cuenta | OK (`cobros_public_rate_limit`) |
| 10 | No hay rutas internas (dashboard, clientes, pagos, reportes, etc.) accesibles sin token | OK (todas bajo dependencia de auth o redirección a login) |

---

## 4. Resumen

- **Desde un enlace público** el usuario solo puede: (1) reportar un pago (`rapicredit-cobros`) o (2) consultar su estado de cuenta (`rapicredit-estadocuenta`).  
- **No puede** acceder al login “real” si viene de ese flujo (ve “Acceso prohibido” y “Continuar”).  
- **No puede** acceder a dashboard, clientes, pagos ni ningún otro módulo sin un token válido obtenido por login.  
- **Backend**: los endpoints públicos no usan autenticación, están limitados por IP y solo exponen/operan con el cliente identificado por la cédula enviada.

Si se añaden nuevos endpoints o rutas públicas, deben revisarse contra este documento y el checklist anterior.
