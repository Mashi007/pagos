# 🔧 Solución: Error "Cannot find module server.js" en Render

## 🔍 Problema

Render está intentando ejecutar `node server.js` cuando debería servir archivos estáticos. Esto ocurre porque el servicio está configurado como `type: web` en lugar de `type: static`.

## ✅ Solución

Tienes dos opciones:

### Opción 1: Actualizar en Render Dashboard (RECOMENDADO)

1. Ve a [Render Dashboard](https://dashboard.render.com/)
2. Selecciona tu servicio `pagos-frontend`
3. Ve a **Settings**
4. Busca la sección **Service Type** o **Type**
5. Cambia de **Web Service** a **Static Site**
6. Guarda los cambios
7. Render reiniciará el servicio automáticamente

### Opción 2: Eliminar y Recrear el Servicio

Si la opción 1 no funciona:

1. Ve a Render Dashboard
2. Selecciona `pagos-frontend`
3. Ve a **Settings** > **Delete Service**
4. Confirma la eliminación
5. Ve a **New** > **Static Site**
6. Conecta tu repositorio de GitHub
7. Render debería detectar automáticamente el `render.yaml` y crear el servicio correctamente

### Opción 3: Verificar que Render use render.yaml

1. Ve a Render Dashboard
2. Selecciona `pagos-frontend`
3. Ve a **Settings**
4. Busca **"Render Configuration File"** o similar
5. Asegúrate de que esté configurado para usar `render.yaml`
6. Si no existe esta opción, Render debería detectarlo automáticamente

## 📋 Configuración Correcta en Render Dashboard

Para un **Static Site**, la configuración debe ser:

- **Type**: Static Site (NO Web Service)
- **Build Command**: `npm install && npm run build`
- **Publish Directory**: `dist`
- **Root Directory**: `frontend` (si aplica)

## ⚠️ Importante

- Los servicios **Static Site** NO ejecutan comandos de inicio (`startCommand`)
- Solo construyen y sirven archivos estáticos
- No necesitan un servidor Node.js corriendo

## 🧪 Verificar que Funciona

Una vez configurado correctamente, deberías ver en los logs:

```
✓ built in XXXms
==> Uploading build...
==> Uploaded in X.Xs
==> Build successful 🎉
==> Deploying...
```

Y NO deberías ver:
```
==> Running 'node server.js'
Error: Cannot find module 'server.js'
```

## 📝 Nota sobre render.yaml

El archivo `render.yaml` está correctamente configurado con `type: static`. Si Render no lo está usando, puede ser que:

1. El servicio se creó antes del `render.yaml`
2. Render necesita que se sincronice manualmente
3. Necesitas actualizar la configuración en el dashboard
