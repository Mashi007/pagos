# ✅ Validación de Comandos para Render Dashboard

## Comandos Correctos para Render Dashboard

### ✅ Build Command
```
pip install -r requirements.txt
```
**Nota**: NO incluyas el `$` al inicio (ese es solo el prompt del terminal)

### ✅ Pre-Deploy Command (Opcional)
```
(Dejar vacío o agregar comandos como migraciones de base de datos)
```

### ✅ Start Command
```
gunicorn app.main:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120 --worker-class uvicorn.workers.UvicornWorker
```

**IMPORTANTE**: 
- ❌ NO incluyas `startCommand:` al inicio (eso es solo para el archivo YAML)
- ❌ NO incluyas el `$` al inicio
- ✅ Solo el comando directamente

## Errores Comunes

### ❌ INCORRECTO:
```
$ startCommand: gunicorn app.main:app --bind 0.0.0.0:$PORT
```

### ✅ CORRECTO:
```
gunicorn app.main:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120 --worker-class uvicorn.workers.UvicornWorker
```

## Explicación de Parámetros

- `gunicorn`: Servidor WSGI para producción
- `app.main:app`: Módulo `app.main`, objeto `app`
- `--bind 0.0.0.0:$PORT`: Escucha en todas las interfaces, puerto desde variable de entorno
- `--workers 2`: 2 procesos worker (ajusta según recursos)
- `--timeout 120`: Timeout de 120 segundos
- `--worker-class uvicorn.workers.UvicornWorker`: Usa Uvicorn como worker (necesario para FastAPI)

## Verificación Post-Deploy

Después de actualizar los comandos, verifica en los logs:

```
[INFO] Starting gunicorn 23.0.0
[INFO] Listening at: http://0.0.0.0:10000
[INFO] Using worker: uvicorn.workers.UvicornWorker
[INFO] Booting worker with pid: [número]
[INFO] Booting worker with pid: [número]
```

Deberías ver múltiples workers iniciándose.

---

*Documento creado el 2026-02-01*
