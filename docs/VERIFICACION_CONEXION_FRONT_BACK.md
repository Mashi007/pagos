# Verificación: Conexión Frontend ↔ Backend

**Fecha:** 18 de febrero de 2025  
**Alcance:** Adecuación y eficiencia de la comunicación entre frontend y backend.

---

## 1. Resumen Ejecutivo

| Aspecto | Estado | Observaciones |
|---------|--------|---------------|
| **Arquitectura** | ✅ Adecuada | Proxy en producción evita CORS; misma estrategia en desarrollo |
| **Autenticación** | ✅ Robusta | Token refresh, validación pre-request, cancelación de cola |
| **Timeouts** | ✅ Configurados | 30s base, 60s endpoints lentos, 120s clientes-atrasados |
| **Caché proxy** | ✅ Eficiente | Cache-Control por tipo de endpoint (5min / 30s / no-cache) |
| **Compresión** | ✅ Activa | Gzip en server.js (threshold 1KB, level 6) |
| **Proxy local** | ⚠️ Corregir | Condición excluía localhost:8000; ahora se aplica siempre que API_URL esté definido |

---

## 2. Flujos de Conexión

### 2.1 Producción (Render)

```
Browser (https://rapicredit.onrender.com/pagos/*)
    │
    ├─ /api/*  ──► Express (pagos-frontend) ──proxy──► FastAPI (pagos-backend)
    │                   │
    │                   └─ API_BASE_URL = RENDER_EXTERNAL_URL de pagos-backend
    │
    └─ /pagos/* ──► Express sirve SPA estática
```

- **Mismo origen:** El frontend usa `baseURL: ''` en producción, así que las peticiones van al mismo dominio.
- **Sin CORS:** El proxy hace que el navegador hable solo con el frontend; el backend no recibe peticiones cross-origin.
- **Variables:** `API_BASE_URL` se inyecta desde `pagos-backend` vía `fromService` en `render.yaml`.

### 2.2 Desarrollo (Vite)

```
Browser (http://localhost:3000)
    │
    ├─ /api/*  ──► Vite proxy ──► target: VITE_API_URL || https://rapicredit.onrender.com
    │
    └─ /*  ──► Vite dev server (SPA)
```

- **VITE_API_URL vacío:** Proxy a producción (rapicredit.onrender.com).
- **VITE_API_URL=http://localhost:8000:** Proxy al backend local; CORS permite `localhost:3000`.

### 2.3 Prueba local del build (server.js)

```
Browser (http://localhost:PORT)
    │
    ├─ /api/*  ──► Express proxy ──► API_BASE_URL (localhost:8000 o backend Render)
    │
    └─ /pagos/* ──► Express sirve dist/
```

- **Corrección:** El proxy se aplica también cuando `API_BASE_URL=http://localhost:8000`, para poder probar el build contra backend local.

---

## 3. Configuración por Componente

### 3.1 Frontend – ApiClient (`api.ts`)

| Parámetro | Valor | Uso |
|-----------|-------|-----|
| `baseURL` | `env.API_URL` ('' en prod) | Origen de las peticiones |
| `timeout` | 30s base | Evita peticiones colgadas |
| `validateStatus` | status < 500 | Manejo explícito de 4xx |
| `maxRedirects` | 5 | Redirecciones HTTP |

**Timeouts por endpoint:**
- 60s: dashboard, notificaciones, kpis, stats, cobranzas, AI
- 90s: tablas-campos
- 120s: clientes-atrasados
- 300s: ML, fine-tuning, RAG, Chat AI

### 3.2 Frontend – env.ts

| Modo | API_URL | Comportamiento |
|------|---------|----------------|
| Producción | `''` | Rutas relativas → proxy en Express |
| Desarrollo | `VITE_API_URL` o `''` | Vite proxy según `vite.config` |

### 3.3 server.js – Proxy

| Opción | Valor | Efecto |
|--------|-------|--------|
| `changeOrigin` | true | Host correcto hacia el backend |
| `xfwd` | true | Preserva IP real |
| `secure` | true | HTTPS al backend |
| `proxyReq.setTimeout` | 60000 | 60s por petición |
| `pathRewrite` | `/api${path}` | Mantiene prefijo `/api` |

### 3.4 server.js – Caché (onProxyRes)

| Endpoints | Cache-Control |
|-----------|---------------|
| modelos-vehiculos, concesionarios, analistas, configuracion | `max-age=300, stale-while-revalidate=60` |
| dashboard, kpis | `max-age=30, stale-while-revalidate=10` |
| Resto (pagos, clientes, etc.) | `no-cache, no-store, must-revalidate` |

### 3.5 Backend – CORS

Orígenes permitidos por defecto:
- `http://localhost:3000`, `http://localhost:5173`
- `https://pagos-f2qf.onrender.com`, `https://rapicredit.onrender.com`

---

## 4. Autenticación y Tokens

- **Pre-request:** Comprueba token expirado antes de enviar.
- **Refresh:** Cola de peticiones mientras se renueva el token.
- **Cancelación:** `refreshTokenExpired` cancela peticiones pendientes.
- **Endpoints sin token:** login, refresh, forgot-password.

---

## 5. Eficiencia

| Medida | Implementación |
|--------|----------------|
| Compresión | Gzip en Express (threshold 1KB) |
| Caché HTTP | Por tipo de endpoint en proxy |
| Timeouts | Evitan peticiones indefinidas |
| Chunks | Lazy loading de exceljs, jspdf, etc. |
| Tree-shaking | `moduleSideEffects: false` |

---

## 6. Corrección Aplicada

**Problema:** Con `API_BASE_URL=http://localhost:8000`, el proxy no se montaba y las peticiones `/api/*` devolvían 404.

**Solución:** Aplicar el proxy siempre que `API_URL` esté definido, incluyendo `http://localhost:8000`, para soportar pruebas locales del build.

---

## 7. Checklist de Verificación

- [ ] Producción: peticiones `/api/v1/*` responden correctamente.
- [ ] Desarrollo con Vite: proxy a backend local o producción según `VITE_API_URL`.
- [ ] Build local: `node server.js` con `API_BASE_URL` apunta al backend correcto.
- [ ] CORS: backend permite orígenes del frontend.
- [ ] Tokens: refresh automático y redirección a login cuando expiran.
- [ ] Timeouts: endpoints lentos tienen tiempo suficiente.
- [ ] Caché: datos estáticos (modelos, concesionarios) se cachean; datos dinámicos no.
