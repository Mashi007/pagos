# ✅ Validación de Comandos Frontend - Render Dashboard

## Comandos Correctos para Render Dashboard

### ❌ INCORRECTO (Lo que tienes ahora):
```
frontend/ $ npm install && npm run build
frontend/ $ node server.js
```

### ✅ CORRECTO (Lo que debes poner):
```
npm install && npm run build
node server.js
```

## Explicación del Error

El prefijo `frontend/ $` es solo el **prompt del terminal**, NO es parte del comando. Render lo muestra para indicar el directorio, pero NO debes incluirlo en el comando real.

## Comandos para Copiar y Pegar

### ✅ Build Command:
```
npm install && npm run build
```

### ✅ Pre-Deploy Command:
```
(Dejar vacío - es opcional)
```

### ✅ Start Command:
```
node server.js
```

## Verificación Post-Corrección

Después de corregir los comandos, en los logs deberías ver:

### Build:
```
added 137 packages
> vite build
✓ built in Xms
dist/index.html                  3.63 kB
dist/assets/index-[hash].js     144.40 kB
dist/assets/index-[hash].css     1.04 kB
```

### Start:
```
========================================
🚀 Servidor iniciado correctamente
📦 Puerto: [número]
📁 Directorio dist: [ruta]
✅ Dist existe: true
========================================
```

## Pasos para Corregir en Render Dashboard

1. **Build Command:**
   - Haz clic en "Edit" (lápiz)
   - Elimina `frontend/ $` del inicio
   - Deja solo: `npm install && npm run build`
   - Haz clic en "Save Changes"

2. **Start Command:**
   - Haz clic en "Edit" (lápiz)
   - Elimina `frontend/ $` del inicio
   - Deja solo: `node server.js`
   - Haz clic en "Save Changes"

3. **Pre-Deploy Command:**
   - Puedes dejarlo vacío (es opcional)

## Nota Importante

Render ejecuta los comandos desde el `rootDir` configurado (`frontend`), por lo que NO necesitas incluir `cd frontend` en los comandos. El `rootDir: frontend` en `render.yaml` ya maneja eso automáticamente.

---

*Documento creado el 2026-02-01*
