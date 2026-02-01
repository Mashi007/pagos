# ✅ Validación de Comandos Backend - Render Dashboard

## Comandos Correctos para Backend

### ❌ INCORRECTO (Lo que probablemente tienes ahora):
```
Build Command: $ pip install -r requirements.txt
Start Command: $ gunicorn app.main:app --bind 0.0.0.0:$PORT --workers 2 --tim...
```

### ✅ CORRECTO (Lo que debes poner):
```
Build Command: cd backend && pip install -r requirements.txt
Start Command: cd backend && gunicorn app.main:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120 --worker-class uvicorn.workers.UvicornWorker
```

## Explicación de los Errores

### Error 1: Prefijo `$`
- El `$` al inicio es solo el prompt del terminal
- **NO debes incluirlo** en los comandos
- Render lo muestra visualmente, pero NO es parte del comando

### Error 2: Falta `cd backend`
- Como el `rootDir` está configurado como `.` (raíz del proyecto)
- Necesitas **explícitamente** cambiar al directorio `backend`
- Sin esto, Gunicorn no encuentra el módulo `app`

## Comandos para Copiar y Pegar

### ✅ Build Command:
```
cd backend && pip install -r requirements.txt
```

### ✅ Pre-Deploy Command:
```
(Dejar completamente vacío - es opcional)
```

### ✅ Start Command (Completo):
```
cd backend && gunicorn app.main:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120 --worker-class uvicorn.workers.UvicornWorker
```

## Explicación de Parámetros del Start Command

- `cd backend`: Cambia al directorio backend (necesario porque rootDir es `.`)
- `gunicorn`: Servidor WSGI para producción
- `app.main:app`: Módulo `app.main`, objeto `app`
- `--bind 0.0.0.0:$PORT`: Escucha en todas las interfaces, puerto desde variable
- `--workers 2`: 2 procesos worker (ajusta según recursos)
- `--timeout 120`: Timeout de 120 segundos
- `--worker-class uvicorn.workers.UvicornWorker`: Usa Uvicorn como worker (necesario para FastAPI)

## Pasos para Corregir en Render Dashboard

### Paso 1: Build Command
1. Haz clic en "Edit" (lápiz) del Build Command
2. **Elimina** el `$` del inicio
3. **Agrega** `cd backend &&` al inicio
4. Deja: `cd backend && pip install -r requirements.txt`
5. Haz clic en "Save Changes"

### Paso 2: Pre-Deploy Command
1. Haz clic en "Edit" (lápiz) del Pre-Deploy Command
2. **Borra todo** el contenido (incluyendo el `$`)
3. **Deja completamente vacío**
4. Haz clic en "Save Changes"

### Paso 3: Start Command
1. Haz clic en "Edit" (lápiz) del Start Command
2. **Elimina** el `$` del inicio
3. **Agrega** `cd backend &&` al inicio
4. **Asegúrate** de que el comando completo sea:
   ```
   cd backend && gunicorn app.main:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120 --worker-class uvicorn.workers.UvicornWorker
   ```
5. Haz clic en "Save Changes"

## Verificación Post-Corrección

Después de corregir, en los logs deberías ver:

### Build:
```
==> Running build command 'cd backend && pip install -r requirements.txt'...
Collecting packages...
Successfully installed...
```

### Start:
```
[INFO] Starting gunicorn 23.0.0
[INFO] Listening at: http://0.0.0.0:10000
[INFO] Using worker: uvicorn.workers.UvicornWorker
[INFO] Booting worker with pid: [número]
[INFO] Booting worker with pid: [número]
```

**NO deberías ver:**
- ❌ `ModuleNotFoundError: No module named 'app'`
- ❌ `$` en los comandos ejecutados

## Root Directory

Si tu Root Directory está configurado como `.` (raíz del proyecto), entonces **SÍ necesitas** `cd backend` en los comandos.

Si estuviera configurado como `backend`, entonces NO necesitarías `cd backend`, pero tendrías que ajustar las rutas de `requirements.txt`.

## Troubleshooting

### Si ves "ModuleNotFoundError: No module named 'app'"
**Solución**: Asegúrate de que el Start Command tenga `cd backend &&` al inicio

### Si ves "No such file or directory: requirements.txt"
**Solución**: Asegúrate de que el Build Command tenga `cd backend &&` al inicio

### Si el comando está cortado en la interfaz
**Solución**: El campo puede tener límite de caracteres visibles, pero el comando completo se guarda. Verifica en los logs después del deploy.

---

*Documento creado el 2026-02-01*
