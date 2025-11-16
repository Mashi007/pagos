# 🔧 Actualizar NODE_VERSION en Render Dashboard

## ⚠️ Problema

Render está usando Node.js 20.11.0 desde la variable de entorno del dashboard, que tiene **prioridad sobre el render.yaml**.

El log muestra:
```
==> Using Node.js version 20.11.0 via environment variable NODE_VERSION
```

## ✅ Solución: Actualizar Variable de Entorno en Dashboard

**Las variables de entorno del dashboard tienen PRIORIDAD sobre render.yaml**, por lo que debes actualizarla manualmente.

### Pasos:

1. **Ve al Dashboard de Render**: https://dashboard.render.com

2. **Selecciona el servicio**: `rapicredit-frontend`

3. **Ve a la sección "Environment"** o **"Environment Variables"**

4. **Busca la variable `NODE_VERSION`**

5. **Actualiza el valor de `20.11.0` a `20.19.0`**

6. **Guarda los cambios**

7. **Inicia un nuevo deploy manual**:
   - Ve a la sección **"Events"** o **"Deploys"**
   - Haz clic en **"Manual Deploy"** → **"Deploy latest commit"**

### Verificación

Después del deploy, en los logs deberías ver:
```
==> Using Node.js version 20.19.0 via environment variable NODE_VERSION
```

En lugar de:
```
==> Using Node.js version 20.11.0 via environment variable NODE_VERSION
```

## 📋 Variables de Entorno Requeridas

Asegúrate de que estas variables estén configuradas en el dashboard:

| Variable | Valor |
|----------|-------|
| `NODE_VERSION` | `20.19.0` ⚠️ **ACTUALIZAR** |
| `NODE_ENV` | `production` |
| `VITE_API_URL` | `https://pagos-f2qf.onrender.com` |
| `API_BASE_URL` | `https://pagos-f2qf.onrender.com` |
| `PORT` | (asignado automáticamente por Render) |

## 🔍 Nota Importante

- ✅ El `render.yaml` está actualizado correctamente con `NODE_VERSION: 20.19.0`
- ✅ El `package.json` tiene `"node": ">=20.19.0"` en engines
- ✅ El `.nvmrc` tiene `20.19.0`
- ⚠️ **PERO** la variable de entorno del dashboard tiene prioridad y debe actualizarse manualmente

## 🎯 Resultado Esperado

Después de actualizar la variable de entorno y hacer un nuevo deploy:
- ✅ Node.js 20.19.0 será usado
- ✅ Vite 7.2.2 funcionará correctamente
- ✅ El build se completará sin errores

