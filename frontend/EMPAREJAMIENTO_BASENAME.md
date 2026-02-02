# Emparejamiento con basename

**Objetivo:** Que la app se sirva correctamente en `https://rapicredit.onrender.com/pagos` y que rutas, assets y redirecciones usen el mismo base path.

## Fuente de verdad

| Origen | Valor | Uso |
|--------|--------|-----|
| **Vite** | `base: '/pagos/'` | `vite.config.ts` y `vite.config.js`. Define `import.meta.env.BASE_URL` (con barra final). |
| **Frontend (runtime)** | `BASE_PATH = (import.meta.env.BASE_URL \|\| '/').replace(/\/$/, '') \|\| ''` | Sin barra final → `/pagos`. Definido en `src/config/env.ts`. |
| **React Router** | `basename={BASE_PATH \|\| '/'}` | `src/main.tsx`. Debe usar `BASE_PATH` (no hardcodear `/pagos`). |
| **Servidor (Node)** | `FRONTEND_BASE = '/pagos'` | `server.js`. Sin barra final; debe coincidir con `BASE_PATH` en producción. |

## Reglas de emparejamiento

1. **Vite**  
   - En `vite.config.ts`: `base: '/pagos/'`.  
   - En `vite.config.js`: `base: '/pagos/'` (mismo valor para evitar builds con base distinta).

2. **React**  
   - `BrowserRouter basename` debe ser `BASE_PATH || '/'` (importado de `config/env.ts`), no un literal `/pagos`.

3. **Rutas en la app**  
   - Rutas de React Router (p. ej. en Sidebar): sin prefijo de dominio, relativas al basename: `/dashboard/menu`, `/cobranzas`, `/pagos` (página de Pagos), etc.  
   - Con basename `/pagos`, la URL final es `https://dominio.com/pagos` + path → ej. `/pagos/cobranzas`.

4. **Links y redirecciones (window.location / href)**  
   - Usar `BASE_PATH + '/ruta'` (ej. `BASE_PATH + '/login'`, `BASE_PATH + '/notificaciones'`) para que funcionen con cualquier base.  
   - Archivos que ya lo hacen: `api.ts`, `SimpleProtectedRoute.tsx`, `Cobranzas.tsx`, `ChatAI.tsx`, `Usuarios.tsx`, `EmailConfig.tsx`, `ConversacionesWhatsApp.tsx`, `EntrenamientoMejorado.tsx`, `authService.ts`.  
   - Logo: `Logo.tsx` usa `import.meta.env.BASE_URL` para el path del logo por defecto.

5. **server.js**  
   - `FRONTEND_BASE = '/pagos'` (sin barra).  
   - Estáticos: `app.use(FRONTEND_BASE, express.static(distPath))` → `/pagos/*` sirve `dist/*`.  
   - SPA fallback: rutas como `/pagos`, `/pagos/cobranzas`, etc. sirven `index.html` con reemplazo `src="/assets/` → `src="/pagos/assets/` para que los chunks carguen bien.

## Comprobación rápida

- Build: `npm run build` → en `dist/index.html` los scripts deben tener `src="/pagos/assets/...` (o el reemplazo en `sendSpaIndex` lo corrige).  
- Desarrollo: con `base: '/pagos/'` la app se abre en `http://localhost:3000/pagos/`.  
- Producción: `https://rapicredit.onrender.com/pagos` y `https://rapicredit.onrender.com/pagos/cobranzas` deben mostrar la SPA; `/pagos/assets/*.js` debe devolver 200.

## Resumen

| Concepto | Valor |
|---------|--------|
| Base path (sin barra final) | `/pagos` |
| Base URL (Vite, con barra final) | `/pagos/` |
| Única fuente de verdad en código | `import.meta.env.BASE_URL` (Vite) → `BASE_PATH` (env.ts) → `basename` (main.tsx) |
| Servidor | `FRONTEND_BASE = '/pagos'` debe coincidir con lo anterior en producción |
