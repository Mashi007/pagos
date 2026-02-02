# Auditoría integral: por qué no renderiza correctamente /pagos (Configuración y logo)

**Fecha:** 2025-02-02  
**URL afectada:** `https://rapicredit.onrender.com/pagos/configuracion?tab=ai`  
**Síntomas:** Logo no encontrado (401 en HEAD logo), posible selector CSS inválido, dudas sobre renderizado.

---

## 1. Resumen ejecutivo

| Hallazgo | Severidad | Estado |
|----------|-----------|--------|
| HEAD `/api/v1/configuracion/logo/{filename}` devuelve **401** | Alta | Mitigado en frontend; backend ya público |
| Selector CSS inválido en `index-*.css` (“Juego de reglas ignoradas”) | Media | Documentado; requiere inspección del build |
| URL del logo en producción (`env.API_URL` vacío) | Baja | Correcto: se usa ruta relativa `/api/...` |

La página **sí está cargando datos** (configuración general, AI, documentos, KPIs, notificaciones). El problema visible es el **logo** que no se muestra porque el HEAD del logo devuelve 401 y el frontend interpreta “logo no encontrado”.

---

## 2. Análisis de peticiones (según tu consola)

### 2.1 Peticiones correctas (200)

- `GET /pagos/configuracion` → 200 (HTML/SPA)
- `GET /pagos/assets/index-*.js` y `index-*.css` → 200
- `GET /api/v1/auth/me` → 200
- `GET /api/v1/pagos/kpis` → 200
- `GET /api/v1/notificaciones/estadisticas/resumen` → 200
- `GET /api/v1/configuracion/ai/configuracion` → 200
- `GET /api/v1/configuracion/ai/documentos` → 200
- `GET /api/v1/configuracion/general` → 200
- `GET /pagos/logos/rAPI.png` → 200 (logo por defecto)

### 2.2 Problema: HEAD logo → 401

```
HEAD https://rapicredit.onrender.com/api/v1/configuracion/logo/logo-bcb7da1c.png?t=...
[HTTP/2 401]
```

- **Efecto:** El frontend hace HEAD para comprobar si existe el logo; al recibir 401 trata el logo como “no encontrado” y muestra el mensaje: *"Logo logo-bcb7da1c.png no encontrado en el servidor"*.
- **Backend:** En `backend/app/api/v1/endpoints/configuracion.py`, el router del logo (`router_logo`) **no tiene** `Depends(get_current_user)`. GET y HEAD `/configuracion/logo/{filename}` están pensados para ser **públicos** (login, correos, etc.).
- **Conclusión:** El 401 no debería salir de este endpoint. Posibles causas:
  1. Proxy o API Gateway delante del backend que exige auth para todas las rutas.
  2. Backend desplegado con otro prefijo o middleware que aplica auth global.
  3. En Render: si frontend y backend son el mismo servicio, comprobar que las peticiones `/api/*` llegan al backend FastAPI y no a otra ruta.

### 2.3 Redirect 302 en logo por defecto

- `GET https://rapicredit.onrender.com/logos/rAPI.png` → 302 → `/pagos/logos/rAPI.png`
- Esto es esperado: `server.js` redirige `/logos/*` sin base a `/pagos/logos/*`. No afecta al renderizado si el `<img>` usa la URL final con `/pagos/`.

---

## 3. URL del logo en producción

- En producción, `env.API_URL` está vacío (rutas relativas para que el proxy de `server.js` maneje `/api/*`).
- En `Configuracion.tsx` se usa:
  - `logoUrl = env.API_URL + '/api/v1/configuracion/logo/' + config.logo_filename + '?t=' + Date.now()`
  - Con `API_URL === ''` → `logoUrl = '/api/v1/configuracion/logo/...'` (relativa al origen).
- Esa URL es correcta: la petición va al mismo origen y el proxy la reenvía al backend. El fallo es el **401** en el backend/proxy, no la construcción de la URL.

---

## 4. Selector CSS inválido

- Mensaje: *"Juego de reglas ignoradas debido a un mal selector"* en `index-JZh5xw9Z.css:1:60004`.
- El CSS está minificado; la posición 60004 es un carácter dentro del archivo. Suele deberse a:
  - Clase o selector generado por Tailwind/librería con caracteres no válidos.
  - Variable CSS o sintaxis no soportada en algún navegador.
- **Recomendación:** Tras un build (`npm run build`), abrir `dist/assets/index-*.css`, ir a la zona del carácter ~60004 y buscar selectores raros (por ejemplo `.[...]`, `::` mal formado, o nombres de clase con caracteres especiales). No impide que la página cargue, pero puede dejar algún bloque sin estilos.

---

## 5. Base path y rutas (React Router)

- `main.tsx`: `<BrowserRouter basename="/pagos">` → correcto para `https://rapicredit.onrender.com/pagos/...`.
- `App.tsx`: rutas definidas como `path="configuracion"`, `path="login"`, etc. (relativas al basename). Coincide con `/pagos/configuracion`, `/pagos/login`, etc.
- No se ha detectado fallo de rutas que impida renderizar la SPA en `/pagos/configuracion`.

---

## 6. Acciones realizadas en código

1. **Configuracion.tsx**
   - URL del logo: se usa siempre ruta relativa cuando `env.API_URL` está vacío (ya era el caso; se deja explícito con un comentario).
   - HEAD del logo: se añade `credentials: 'same-origin'` para que, si el servidor esperara cookie de sesión, se envíe y se evite 401 por falta de credenciales.
2. **Backend**
   - Se deja documentado en el endpoint que GET/HEAD logo son **públicos** (sin auth) para que no se les añada dependencia de `get_current_user` por error.

---

## 7. Comprobaciones recomendadas en Render

1. **Variables de entorno del frontend (Node):**
   - `API_BASE_URL` debe apuntar al backend (ej. `https://tu-backend.onrender.com` o la URL del servicio backend). Sin esto, el proxy de `server.js` no reenvía `/api/*` correctamente.
2. **Backend (FastAPI):**
   - Probar directamente:  
     `curl -I https://<BACKEND_URL>/api/v1/configuracion/logo/logo-bcb7da1c.png`  
     Debe devolver **200** (o 404 si no existe el logo), **nunca 401**.
   - Si devuelve 401, revisar middlewares y que no se aplique auth a `router_logo`.
3. **Mismo servicio para frontend y API:**
   - Si en un solo servicio se sirve la SPA y se hace proxy a otro backend, confirmar que las peticiones a `/api/v1/...` llegan al backend y no a una ruta que exija JWT para todo.

---

## 8. Resumen de causas del “no renderiza”

- **Logo que no se muestra:** Causado por **401** en HEAD del logo. La página sí renderiza; el bloqueo es que el frontend considera “logo no encontrado” y muestra el aviso. Con el backend devolviendo 200/404 para GET/HEAD logo y el frontend usando URL relativa + `credentials: 'same-origin'`, el logo debería mostrarse cuando exista.
- **Selector CSS:** Afecta solo a un conjunto de reglas; no suele impedir que la página se pinte. Conviene localizar y corregir el selector en el CSS generado.
- **Resto de la página:** Las XHR de configuración general, AI, documentos, KPIs y notificaciones responden 200; la carga de datos y el renderizado de la vista Configuración (incl. tab AI) deberían ser correctos una vez resuelto el 401 del logo y revisado el CSS si se observan bloques sin estilo.

---

## 9. /pagos/cobranzas — "no renderiza"

**URL:** `https://rapicredit.onrender.com/pagos/cobranzas`

**Cambios realizados (2025-02-02):**

1. **server.js**
   - Ruta explícita `GET /pagos/cobranzas` que sirve `index.html` (igual que `/pagos/chat-ai` y `/pagos/notificaciones`).
   - Redirección `GET /cobranzas` → `302 /pagos/cobranzas`.
   - Redirección `GET /pagos/cobranzas/` → `302 /pagos/cobranzas` (sin barra final).

2. **Si sigue sin verse contenido, comprobar:**
   - **Auth:** Cobranzas está detrás de `SimpleProtectedRoute`; sin sesión se redirige a login.
   - **API:** La página llama a resumen, clientes atrasados y por analista. En Render el frontend debe tener `API_BASE_URL` apuntando al backend; si no, las peticiones `/api/*` fallan y la vista puede quedar en loading o con toasts de error.
   - **Chunks 404:** El build usa `base: '/pagos/'` en vite.config.ts; si aún hay 404 en `/assets/*`, revisar que el HTML servido tenga rutas con prefijo `/pagos/assets/` (sendSpaIndex ya reescribe).
   - **Pantalla en blanco:** `#root` está oculto hasta añadir `styles-loaded` (máx. 2 s). Si hay error de JS antes, revisar consola (F12).
