# Verificación: conexión Backend ↔ Frontend

**Objetivo:** Asegurar que la comunicación entre frontend y backend sea adecuada y eficiente.

---

## 1. Arquitectura de la conexión

```
┌─────────────────┐     /api/* (relativo)      ┌──────────────────┐
│   Navegador     │ ─────────────────────────► │  Express (Node)   │
│   (React SPA)   │     same-origin             │  server.js        │
└─────────────────┘                            └────────┬─────────┘
                                                         │ proxy
                                                         │ changeOrigin
                                                         ▼
                                                ┌──────────────────┐
                                                │  Backend FastAPI │
                                                │  (Python/Gunicorn)│
                                                └──────────────────┘
```

**Flujo:**
1. Frontend usa `baseURL: ''` en producción → peticiones relativas (`/api/v1/...`)
2. El navegador envía a mismo origen (frontend Express)
3. Express proxy reenvía a `API_BASE_URL` (backend)
4. Respuesta fluye en sentido inverso

---

## 2. Puntos verificados

### 2.1 Configuración de URLs

| Componente | Variable | Producción | Desarrollo |
|------------|----------|------------|------------|
| Frontend (api.ts) | `env.API_URL` | `''` (relativo) | `VITE_API_URL` o `''` |
| server.js | `API_BASE_URL` | URL backend (Render) | `localhost:8000` |
| Vite dev | proxy target | - | `VITE_API_URL` |

**Resultado:** Correcto. En producción las peticiones van al mismo origen y el proxy las reenvía.

### 2.2 Proxy (server.js)

| Aspecto | Estado | Detalle |
|---------|--------|---------|
| pathRewrite | ✅ | `/v1/...` → `/api/v1/...` (reconstruye path) |
| Headers | ✅ | `Authorization`, `Cookie` se copian |
| Timeout | ✅ | 60 s en proxyReq |
| changeOrigin | ✅ | Necesario para backend en otro host |
| Compresión | ✅ | Gzip (threshold 1KB, level 6) |

### 2.3 Cache de respuestas (proxy)

| Endpoint | Cache | Duración |
|----------|-------|----------|
| modelos-vehiculos, concesionarios, analistas, configuracion | ✅ | 5 min + stale 60 s |
| dashboard, kpis | ✅ | 30 s + stale 10 s |
| Resto (prestamos, pagos, etc.) | No cache | `no-cache, no-store` |

### 2.4 Cliente API (api.ts)

| Aspecto | Estado | Detalle |
|---------|--------|---------|
| Timeout por defecto | ✅ | 30 s |
| Endpoints lentos | ✅ | 60 s (dashboard, cobranzas, etc.) |
| clientes-atrasados | ✅ | 120 s |
| tablas-campos | ✅ | 90 s |
| Refresh token | ✅ | Cola de peticiones, evita race conditions |
| AbortController | ✅ | Cancelación de peticiones pendientes |
| Token expirado | ✅ | Verificación previa, redirección inmediata |

### 2.5 CORS

- El frontend usa rutas relativas → no hay peticiones cross-origin directas al backend
- CSP `connect-src`: `'self'` + URL backend (por si hay peticiones directas)

---

## 3. Eficiencia

### 3.1 Optimizaciones presentes

- **Compresión gzip** en respuestas del proxy (reduce ~70% tamaño)
- **Cache HTTP** para catálogos y dashboard
- **Timeouts diferenciados** según tipo de endpoint
- **Singleton** del cliente API (una instancia compartida)
- **Logging reducido** en producción

### 3.2 Posibles mejoras

| Mejora | Impacto | Complejidad |
|--------|---------|-------------|
| Agent keepAlive (proxy→backend) | Medio: reutiliza conexiones TCP | Media (nueva dep) |
| HTTP/2 | Bajo en este contexto | Alta |
| Preconnect hints | Bajo | Baja |

---

## 4. Correcciones aplicadas

1. **Cache path:** Uso de `req.originalUrl` para detectar endpoints cacheados (más fiable que `req.path` en rutas montadas).
2. **Proxy con localhost:** El proxy se registra también cuando `API_BASE_URL` es `localhost:8000` para pruebas locales del build de producción.

---

## 5. Checklist de verificación

- [ ] Login funciona (frontend → proxy → backend)
- [ ] Listado de préstamos carga
- [ ] Dashboard muestra KPIs
- [ ] No hay errores CORS en consola
- [ ] Respuestas de catálogos (modelos, concesionarios) tienen header `Cache-Control`
- [ ] Peticiones con token expirado redirigen a login sin loops
