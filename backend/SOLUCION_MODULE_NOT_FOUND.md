# 🔧 Solución: ModuleNotFoundError: No module named 'app'

## Problema Identificado

El error ocurre porque Gunicorn está intentando ejecutarse desde el directorio raíz del proyecto (`/opt/render/project/src/`) en lugar del directorio `backend/`.

### Error en los Logs:
```
==> Running 'gunicorn app.main:app --bind 0.0.0.0:$PORT ...'
ModuleNotFoundError: No module named 'app'
```

## Solución

### ❌ Comando Actual (INCORRECTO):
```
gunicorn app.main:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120 --worker-class uvicorn.workers.UvicornWorker
```

### ✅ Comando Correcto (CON `cd backend &&`):
```
cd backend && gunicorn app.main:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120 --worker-class uvicorn.workers.UvicornWorker
```

## Pasos para Corregir en Render Dashboard

1. Ve a tu servicio **pagos-backend** en Render Dashboard
2. Ve a la sección **"Start Command"**
3. Haz clic en **"Edit"** (lápiz)
4. **Agrega** `cd backend &&` al **inicio** del comando
5. El comando completo debe ser:
   ```
   cd backend && gunicorn app.main:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120 --worker-class uvicorn.workers.UvicornWorker
   ```
6. Haz clic en **"Save Changes"**
7. Render hará un nuevo deploy automáticamente

## Verificación Post-Corrección

Después de corregir, en los logs deberías ver:

### ✅ CORRECTO:
```
==> Running 'cd backend && gunicorn app.main:app --bind 0.0.0.0:$PORT ...'
[INFO] Starting gunicorn 23.0.0
[INFO] Listening at: http://0.0.0.0:10000
[INFO] Using worker: uvicorn.workers.UvicornWorker
[INFO] Booting worker with pid: [número]
[INFO] Application startup complete.
```

### ❌ Ya NO deberías ver:
```
ModuleNotFoundError: No module named 'app'
```

## Por Qué Necesitas `cd backend &&`

Tu configuración tiene:
- **Root Directory**: `.` (raíz del proyecto)
- **Estructura**: `backend/app/main.py`

Por lo tanto:
- Render ejecuta comandos desde: `/opt/render/project/src/`
- Pero el módulo `app` está en: `/opt/render/project/src/backend/app/`
- Necesitas cambiar al directorio `backend` antes de ejecutar Gunicorn

## Alternativa (Si Prefieres)

Si no quieres usar `cd backend &&`, puedes cambiar el Root Directory a `backend`:

1. En Render Dashboard, ve a **"Root Directory"**
2. Cambia de `.` a `backend`
3. Entonces el Start Command sería solo:
   ```
   gunicorn app.main:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120 --worker-class uvicorn.workers.UvicornWorker
   ```
4. Y el Build Command sería solo:
   ```
   pip install -r requirements.txt
   ```

**Pero la solución con `cd backend &&` es más simple y no requiere cambiar el Root Directory.**

---

*Documento creado el 2026-02-01*
