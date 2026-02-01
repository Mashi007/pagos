# ❌ Error: Comando de Backend en Frontend

## Problema Identificado

El servicio **frontend** está intentando ejecutar el comando del **backend**:

```
==> Running build command 'cd backend && pip install -r requirements.txt'...
bash: line 1: cd: backend: No such file or directory
```

## Causa

El Build Command del frontend está configurado incorrectamente con el comando del backend.

## Solución

### ❌ INCORRECTO (Lo que tiene ahora):
```
Build Command: cd backend && pip install -r requirements.txt
```

### ✅ CORRECTO (Lo que debe tener):
```
Build Command: npm install && npm run build
```

## Comandos Correctos para Frontend

### ✅ Build Command:
```
npm install && npm run build
```

### ✅ Pre-Deploy Command:
```
(Dejar completamente vacío)
```

### ✅ Start Command:
```
node server.js
```

## Pasos para Corregir en Render Dashboard

1. Ve a tu servicio **pagos-frontend** (NO el backend)
2. Ve a la sección **"Build Command"**
3. Haz clic en **"Edit"** (lápiz)
4. **Borra** `cd backend && pip install -r requirements.txt`
5. **Escribe**: `npm install && npm run build`
6. Haz clic en **"Save Changes"**
7. Verifica que el **Start Command** sea: `node server.js`
8. Render hará un nuevo deploy automáticamente

## Verificación Post-Corrección

Después de corregir, en los logs deberías ver:

### Build:
```
==> Running build command 'npm install && npm run build'...
added 137 packages
> vite build
✓ built in Xms
dist/index.html                  3.63 kB
dist/assets/index-[hash].js     144.40 kB
dist/assets/index-[hash].css     1.04 kB
```

### Start:
```
==> Running 'node server.js'
========================================
🚀 Servidor iniciado correctamente
📦 Puerto: 10000
✅ Dist existe: true
========================================
```

## Resumen de Configuración

### Frontend (pagos-frontend):
- **Build Command**: `npm install && npm run build`
- **Start Command**: `node server.js`
- **Root Directory**: `frontend`

### Backend (pagos-backend):
- **Build Command**: `cd backend && pip install -r requirements.txt`
- **Start Command**: `cd backend && gunicorn app.main:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120 --worker-class uvicorn.workers.UvicornWorker`
- **Root Directory**: `.`

---

*Documento creado el 2026-02-01*
