# ⚠️ VERIFICACIÓN CRÍTICA: Web Service vs Static Site

## 🔴 Problema Identificado

Si Render está configurado como **"Static Site"** en lugar de **"Web Service"**, el `server.js` NO se ejecutará y verás errores 404.

## ✅ Configuración Correcta en Render Dashboard

### 1. Verificar Tipo de Servicio

En Render Dashboard → `rapicredit-frontend`:

1. Ve a **"Settings"**
2. Verifica que el servicio sea tipo: **"Web Service"** (NO "Static Site")
3. Si dice "Static Site", necesitas:
   - Crear un **nuevo Web Service**
   - O cambiar la configuración (si es posible)

### 2. Configuración Requerida para Web Service

En **Settings** → **Build & Deploy**:

| Campo | Valor Requerido |
|-------|----------------|
| **Environment** | `Node` |
| **Root Directory** | `frontend` |
| **Build Command** | `npm install && npm run build` |
| **Start Command** | `npm run render-start` |

### 3. Verificar Variables de Entorno

Deberían estar todas configuradas:
- ✅ `API_BASE_URL` = `https://pagos-f2qf.onrender.com`
- ✅ `VITE_API_URL` = `https://pagos-f2qf.onrender.com`
- ✅ `NODE_VERSION` = `18.17.0`
- ✅ `NODE_ENV` = `production`
- ✅ `PORT` = (asignado automáticamente por Render)

### 4. Verificación en Logs

Después del deploy, en los logs deberías ver:

```
🚀 Servidor SPA rapicredit-frontend iniciado
🔍 API_URL configurado: https://pagos-f2qf.onrender.com
➡️  Proxy de /api hacia: https://pagos-f2qf.onrender.com
✅ Proxy middleware registrado para rutas /api/*
📡 Puerto: 10000 (o el que Render asigne)
```

**Si NO ves estos logs**, significa que:
- ❌ El servicio está configurado como "Static Site"
- ❌ El `server.js` NO se está ejecutando
- ❌ Render está sirviendo solo archivos estáticos del `dist/`

## 🔧 Solución si está como Static Site

### Opción 1: Cambiar a Web Service (si es posible)

1. Ve a Settings
2. Busca opción para cambiar tipo de servicio
3. Cambia a "Web Service" con Environment: Node

### Opción 2: Crear Nuevo Web Service

Si no se puede cambiar:

1. **Crear nuevo servicio:**
   - Tipo: **Web Service**
   - Name: `rapicredit-frontend`
   - Environment: **Node**
   - Root Directory: `frontend`
   - Build Command: `npm install && npm run build`
   - Start Command: `npm run render-start`
   - Branch: `main`

2. **Copiar todas las variables de entorno** del servicio anterior

3. **Eliminar el servicio "Static Site"** (si existe)

4. **Actualizar el dominio/CNAME** si es necesario

## 📋 Checklist Final

- [ ] Servicio es tipo **"Web Service"** (NO "Static Site")
- [ ] Environment es **"Node"**
- [ ] Start Command es **`npm run render-start`**
- [ ] Variable `API_BASE_URL` está configurada
- [ ] Logs muestran inicio de `server.js`
- [ ] Logs muestran "Proxy middleware registrado"

## ⚠️ Diferencia Clave

| Static Site | Web Service |
|------------|-------------|
| ❌ No ejecuta `server.js` | ✅ Ejecuta `server.js` |
| ❌ Solo sirve archivos estáticos | ✅ Tiene proxy activo |
| ❌ 404 en `/api/*` | ✅ Proxy redirige a backend |
| ❌ No puede hacer rewrites | ✅ Puede hacer proxy |

