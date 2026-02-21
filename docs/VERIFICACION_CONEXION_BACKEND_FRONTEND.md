# Verificación: Conexión Backend ↔ Frontend

## Arquitectura (https://rapicredit.onrender.com/pagos/prestamos)

```
Usuario → https://rapicredit.onrender.com/pagos/prestamos (Frontend SPA)
                ↓
         Peticiones /api/v1/prestamos (relativas)
                ↓
         server.js (Express) - Proxy /api/* → API_BASE_URL
                ↓
         Backend (pagos-backend) - FastAPI
                ↓
         PostgreSQL (BD)
```

## Configuración Verificada

| Componente | Configuración | Estado |
|------------|---------------|--------|
| **Frontend** | `env.API_URL = ''` (producción) → rutas relativas | ✅ |
| **prestamoService** | `baseUrl = '/api/v1/prestamos'` | ✅ |
| **apiClient** | `baseURL = env.API_URL` (vacío → mismo origen) | ✅ |
| **server.js** | Proxy `/api` → `API_BASE_URL` | ✅ |
| **render.yaml** | `API_BASE_URL` desde `pagos-backend.RENDER_EXTERNAL_URL` | ✅ |
| **Backend** | `GET/POST /api/v1/prestamos` (prefix `/api/v1` + router `/prestamos`) | ✅ |

## Endpoints Préstamos (Frontend → Backend)

| Frontend | Backend | Método |
|----------|---------|--------|
| `prestamoService.getPrestamos()` | `GET /api/v1/prestamos` | ✅ |
| `prestamoService.createPrestamo()` | `POST /api/v1/prestamos` | ✅ |
| `prestamoService.updatePrestamo()` | `PUT /api/v1/prestamos/{id}` | ✅ |
| `prestamoService.deletePrestamo()` | `DELETE /api/v1/prestamos/{id}` | ✅ |

## Cómo Verificar la Conexión

### 1. Health check del backend (vía proxy)

El proxy reescribe `/api/health` y `/api/health/db` a la raíz del backend (`/health`, `/health/db`):

```bash
# Frontend (Express)
curl -s https://rapicredit.onrender.com/health

# Backend (vía proxy) - verifica BD
curl -s https://rapicredit.onrender.com/api/health/db
# Respuesta esperada: {"status":"healthy","database":"connected"}
```

### 2. Desde la consola del navegador (en /pagos/prestamos)

```javascript
// Debe devolver datos (requiere estar logueado)
fetch('/api/v1/prestamos?page=1&per_page=5', {
  headers: { 'Authorization': 'Bearer ' + (localStorage.getItem('access_token') || sessionStorage.getItem('access_token')) }
}).then(r => r.json()).then(console.log)
```

### 3. Logs en Render

- **pagos-frontend**: Buscar `➡️  Proxy de /api hacia: https://...` al iniciar
- **pagos-backend**: Ver requests `GET /api/v1/prestamos` en los logs

## Checklist de Diagnóstico

Si la página no carga datos:

1. [ ] ¿API_BASE_URL está configurado en pagos-frontend? (Render Dashboard → pagos-frontend → Environment)
2. [ ] ¿El backend está activo? (Render puede poner servicios free en sleep)
3. [ ] ¿Hay errores 401/403? (token expirado → hacer login de nuevo)
4. [ ] ¿Hay errores 502? (proxy no puede conectar al backend)
5. [ ] ¿Hay errores 404? (ruta incorrecta o backend no tiene el endpoint)

## Variables de Entorno Requeridas (Render)

| Servicio | Variable | Origen |
|----------|---------|--------|
| pagos-frontend | API_BASE_URL | fromService: pagos-backend.RENDER_EXTERNAL_URL |
| pagos-backend | DATABASE_URL | Manual |
| pagos-backend | SECRET_KEY | Manual |
