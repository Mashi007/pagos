# 🚨 INSTRUCCIONES URGENTES: Actualizar NODE_VERSION en Render

## ⚠️ PROBLEMA CRÍTICO

Render está usando **Node.js 20.11.0** pero Vite 7.2.2 requiere **Node.js 20.19+**.

El build está fallando con el error:
```
crypto.hash is not a function
```

## ✅ SOLUCIÓN INMEDIATA (5 minutos)

### Paso 1: Ir al Dashboard de Render
1. Abre: https://dashboard.render.com
2. Inicia sesión

### Paso 2: Seleccionar el Servicio
1. Busca y haz clic en: **`rapicredit-frontend`**

### Paso 3: Ir a Environment Variables
1. En el menú lateral, haz clic en: **"Environment"**
2. O busca la sección: **"Environment Variables"**

### Paso 4: Actualizar NODE_VERSION
1. Busca la variable: **`NODE_VERSION`**
2. Haz clic en el valor actual: **`20.11.0`**
3. Cambia el valor a: **`20.19.0`**
4. Haz clic en **"Save Changes"** o **"Update"**

### Paso 5: Iniciar Nuevo Deploy
1. Ve a la pestaña: **"Events"** o **"Deploys"**
2. Haz clic en: **"Manual Deploy"**
3. Selecciona: **"Deploy latest commit"**
4. Espera a que termine el deploy

### Paso 6: Verificar
En los logs del nuevo deploy, deberías ver:
```
==> Using Node.js version 20.19.0 via environment variable NODE_VERSION
```

**Si ves esto, el problema está resuelto ✅**

## 📋 Orden de Prioridad de Render

Render lee la versión de Node.js en este orden (de mayor a menor prioridad):

1. ✅ **Variable de entorno `NODE_VERSION` en el dashboard** ← **ACTUALIZAR AQUÍ**
2. Archivo `.node-version` en la raíz del proyecto
3. Archivo `.nvmrc` en la raíz del proyecto
4. Propiedad `engines.node` en `package.json`

**Por eso la variable de entorno del dashboard tiene prioridad y debe actualizarse manualmente.**

## 🔍 Verificación Rápida

Después de actualizar, en los logs deberías ver:
- ✅ `==> Using Node.js version 20.19.0`
- ✅ `vite v7.2.2 building client environment for production...`
- ✅ `✓ X modules transformed.`
- ✅ `Build completed successfully`

## ⚠️ Si No Puedes Acceder al Dashboard

Si no tienes acceso al dashboard de Render, contacta al administrador del proyecto para que actualice la variable de entorno `NODE_VERSION` a `20.19.0`.

## 📝 Archivos Ya Actualizados (No Requieren Cambios)

Los siguientes archivos ya están actualizados correctamente:
- ✅ `render.yaml` → `NODE_VERSION: 20.19.0`
- ✅ `frontend/render.yaml` → `NODE_VERSION: 20.19.0`
- ✅ `frontend/package.json` → `"node": ">=20.19.0"`
- ✅ `frontend/.nvmrc` → `20.19.0`
- ✅ `frontend/.node-version` → `20.19.0` (nuevo)

**Pero la variable de entorno del dashboard tiene prioridad y debe actualizarse manualmente.**

