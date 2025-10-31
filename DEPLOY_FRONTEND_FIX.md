# 🔧 Guía para Corregir el Despliegue del Frontend en Render

## Problema
El frontend no está desplegando los cambios en `server.js` y las variables de entorno no están configuradas correctamente.

## ✅ Solución: Verificación Manual en Render Dashboard

### 1. Verificar Variables de Entorno

1. Ve al dashboard de Render: https://dashboard.render.com
2. Selecciona el servicio `rapicredit-frontend`
3. Ve a la sección **"Environment"** o **"Environment Variables"**
4. **Verifica/Agrega** las siguientes variables:

```
NODE_VERSION = 18.17.0
VITE_API_URL = https://pagos-f2qf.onrender.com
API_BASE_URL = https://pagos-f2qf.onrender.com
NODE_ENV = production
PORT = (Render lo asigna automáticamente, no modificar)
```

### 2. Verificar Build Command

En la sección **"Settings"** → **"Build & Deploy"**, verifica que el comando de build sea:

```bash
npm install && npm run build
```

### 3. Verificar Start Command

En la misma sección, verifica que el comando de inicio sea:

```bash
npm run render-start
```

### 4. Forzar Nuevo Deploy

1. Ve a la sección **"Events"** o **"Deploys"**
2. Haz clic en **"Manual Deploy"** → **"Deploy latest commit"**
3. Esto forzará un nuevo deploy con todos los cambios recientes

### 5. Verificar Logs

Después del deploy, ve a **"Logs"** y busca:

```
🔍 API_URL configurado: https://pagos-f2qf.onrender.com
➡️  Proxy de /api hacia: https://pagos-f2qf.onrender.com
✅ Proxy middleware registrado para rutas /api/*
```

Si ves estos mensajes, el proxy está configurado correctamente.

## ⚠️ Si Render no usa render.yaml

Si Render no está usando el archivo `render.yaml` automáticamente:

1. Ve a **"Settings"** → **"Build & Deploy"**
2. Configura manualmente:
   - **Root Directory**: `frontend`
   - **Build Command**: `npm install && npm run build`
   - **Start Command**: `npm run render-start`
   - **Environment**: `Node`
   - **Node Version**: `18.17.0`

## 🚨 Verificación de Cambios

Para verificar que los cambios están en el código:

```bash
# En local, verifica que el commit existe
git log --oneline -5

# Deberías ver:
# 987144c0 fix: Mejorar logging y pathRewrite del proxy para diagnóstico de 404
# 1819081c fix: Configurar API_BASE_URL para proxy del frontend en runtime (Render)
```

## 📝 Notas Importantes

1. **Variables VITE_***: Solo funcionan durante el build de Vite, NO en runtime de Node.js
2. **API_BASE_URL**: Debe estar sin el prefijo `VITE_` para que funcione en `server.js` en runtime
3. **rootDir**: Render debe ejecutar los comandos desde el directorio `frontend/`

## 🔍 Troubleshooting

Si después de estos pasos sigue sin funcionar:

1. **Verifica los logs de Render** para ver si hay errores
2. **Verifica que el commit está en el branch `main`**:
   ```bash
   git log origin/main --oneline -5
   ```
3. **Fuerza un rebuild limpio**: En Render, ve a Settings → Clear Build Cache → Manual Deploy

