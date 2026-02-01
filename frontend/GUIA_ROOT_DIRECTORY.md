# 📁 Guía: Root Directory en Render

## Entendiendo Root Directory

### ✅ Lo que hace Root Directory:
- Render ejecuta **todos los comandos** desde ese directorio automáticamente
- Es como hacer `cd frontend` antes de cada comando
- **NO necesitas** incluir `cd frontend` en tus comandos

### ❌ Lo que NO debes hacer:
- **NO incluyas** `frontend/ $` en tus comandos
- **NO incluyas** `cd frontend` en tus comandos
- El `frontend/ $` es solo un **indicador visual**

## Cómo Funciona

### Configuración Actual:
```
Root Directory: frontend
```

### Lo que Render hace automáticamente:
```bash
# Render internamente hace esto:
cd frontend
npm install && npm run build  # Tu comando
```

### Lo que tú escribes en los campos:
```
npm install && npm run build
```

**NO escribes:**
```
frontend/ $ npm install && npm run build  ❌ INCORRECTO
cd frontend && npm install && npm run build  ❌ INCORRECTO
```

## Comandos Correctos

### Build Command:
```
npm install && npm run build
```

### Pre-Deploy Command:
```
(Dejar vacío)
```

### Start Command:
```
node server.js
```

## Por Qué Render Muestra `frontend/ $`

Render muestra `frontend/ $` como **ayuda visual** para que sepas:
- Desde qué directorio se ejecuta el comando
- Es equivalente al prompt `$` en tu terminal

**Pero NO es parte del comando real que debes escribir.**

## Analogía con Terminal

### En tu terminal local harías:
```bash
$ cd frontend
frontend/ $ npm install && npm run build
```

### En Render Dashboard escribes:
```
npm install && npm run build
```

Render ya hace el `cd frontend` automáticamente por el Root Directory.

## Verificación

### ✅ CORRECTO (Lo que debes escribir):
```
Build Command: npm install && npm run build
Start Command: node server.js
```

### ❌ INCORRECTO (Lo que NO debes escribir):
```
Build Command: frontend/ $ npm install && npm run build
Start Command: frontend/ $ node server.js
```

## Pasos para Configurar Correctamente

1. **Root Directory**: Déjalo como `frontend` (está bien)

2. **Build Command**:
   - Haz clic en "Edit"
   - **Borra** `frontend/ $` del inicio
   - Escribe solo: `npm install && npm run build`
   - Guarda

3. **Pre-Deploy Command**:
   - Haz clic en "Edit"
   - **Borra todo** (incluyendo `frontend/ $`)
   - **Deja vacío**
   - Guarda

4. **Start Command**:
   - Haz clic en "Edit"
   - **Borra** `frontend/ $` del inicio
   - Escribe solo: `node server.js`
   - Guarda

## Resumen Visual

```
Root Directory: frontend
    ↓
Render ejecuta: cd frontend (automáticamente)
    ↓
Tus comandos se ejecutan desde: /opt/render/project/src/frontend/
    ↓
Por eso Render muestra: frontend/ $ (solo visual)
    ↓
Tú escribes: npm install && npm run build (sin prefijo)
```

---

*Documento creado el 2026-02-01*
