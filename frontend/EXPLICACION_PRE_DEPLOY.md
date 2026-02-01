# 📝 Explicación: Pre-Deploy Command en Render

## Entendiendo el Prefijo `frontend/ $`

### ❌ Lo que NO es:
- NO es parte del comando real
- NO es un prefijo del sistema que debas incluir
- NO es obligatorio

### ✅ Lo que SÍ es:
- Es solo un **indicador visual** del directorio de trabajo
- Render lo muestra para que sepas desde dónde se ejecuta el comando
- Es equivalente al prompt `$` en tu terminal local

## Pre-Deploy Command: Opcional

El **Pre-Deploy Command** es completamente **opcional**. Puedes:

### Opción 1: Dejarlo Vacío (Recomendado para tu caso)
```
(Dejar el campo completamente vacío)
```

### Opción 2: Usarlo Solo Si Necesitas
Ejemplos de cuándo usarlo:
- Migraciones de base de datos: `npm run migrate`
- Subir assets estáticos: `npm run upload-assets`
- Ejecutar tests antes de deploy: `npm test`

**Para tu frontend actual:** NO lo necesitas, déjalo vacío.

## Cómo Configurar Correctamente

### Paso 1: Build Command
1. Haz clic en "Edit" del Build Command
2. **Elimina** `frontend/ $` del inicio
3. Deja solo: `npm install && npm run build`
4. Haz clic en "Save Changes"

### Paso 2: Pre-Deploy Command
1. Haz clic en "Edit" del Pre-Deploy Command
2. **Borra todo** el contenido (incluyendo `frontend/ $`)
3. **Deja el campo completamente vacío**
4. Haz clic en "Save Changes"

### Paso 3: Start Command
1. Haz clic en "Edit" del Start Command
2. **Elimina** `frontend/ $` del inicio
3. Deja solo: `node server.js`
4. Haz clic en "Save Changes"

## Comandos Finales Correctos

### Build Command:
```
npm install && npm run build
```

### Pre-Deploy Command:
```
(Completamente vacío)
```

### Start Command:
```
node server.js
```

## Por Qué Render Muestra `frontend/ $`

Render muestra `frontend/ $` porque:
- Tu `rootDir` está configurado como `frontend`
- Es equivalente a hacer `cd frontend` en tu terminal
- El `$` es solo el prompt visual
- **NO debes incluirlo en tus comandos**

## Analogía con Terminal Local

En tu terminal local sería:
```bash
$ cd frontend
frontend/ $ npm install && npm run build
```

En Render Dashboard, solo pones:
```
npm install && npm run build
```

Render ya sabe que está en `frontend` por el `rootDir` configurado.

## Verificación

Después de configurar correctamente, los logs deberían mostrar:

```
==> Running build command 'npm install && npm run build'...
added 137 packages
> vite build
✓ built in Xms
```

**Sin** el prefijo `frontend/ $` en los logs reales.

---

*Documento creado el 2026-02-01*
